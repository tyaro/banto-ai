"""Read one invented registered chunk from the real saved-attempt path shape.

This preformal adapter uses frozen holdout identities only as schema markers.
It never opens a campaign entry, reads an actual registered run, or authenticates
an actual producer. Every byte comes from a caller-pinned invented fixture root.
"""
from __future__ import annotations

from pathlib import Path

from . import _anomaly_v03_runtime as paths
from . import anomaly_v03 as v
from . import anomaly_v03_consumer_evidence as evidence
from . import anomaly_v03_consumer_input as metadata
from . import anomaly_v03_observation_audit as pinned
from . import anomaly_v03_registered_evaluation_contract as semantic
from . import anomaly_v03_registered_saved_summary as saved
from . import anomaly_v03_score_audit as score_audit


FORMAT = 'anomaly-v03-preformal-registered-saved-attempt-fixture-v1'
SAVEPOINT_FORMAT = 'anomaly-v03-preformal-invented-partial-savepoint-v1'
PREFIX = 'anomaly-v03-preformal-registered-attempt-'
ROOT = Path(__file__).resolve().parents[2]
MAX_SAVEPOINT = 16 * 1024
DATASET_INPUTS = pinned.DATASET_INPUTS


def _names(chunk_index, attempt):
    """Map logical candidate keys to fixed physical saved-attempt names."""
    identities = v.evaluation_inventory('holdout')[chunk_index * 6:chunk_index * 6 + 6]
    v.require(len(identities) == 6, 'six registered fixture identities')
    stem = f'run/attempts/chunks/{chunk_index:03d}/attempt-{attempt:04d}/result/payload/'
    names = {}
    for identity in identities:
        logical = saved._payload_path(identity)
        names[logical] = stem + logical
        for kind in metadata.INPUT_HASHES:
            logical = saved._payload_path(identity, kind)
            names[logical] = (stem + 'datasets/' + identity['dataset_id'] + '/' +
                              DATASET_INPUTS[kind])
    v.require(len(names) == 18 and len(set(names.values())) == 18,
              'registered fixture exact saved file inventory')
    return identities, names


def _read(root, relative, pin, maximum):
    v.safe_relative_path(relative)
    return pinned.read_pinned(root / relative, pin, maximum)


def read_invented_registered_attempt(root, *, expected_mode, chunk_index,
                                     expected_registry_pin, expected_savepoint_pin,
                                     expected_receipt_pin, expected_report_pin,
                                     expected_payload_pins, source_snapshots):
    """Check an invented six-evaluation latest attempt and independent scores.

    The caller retains all pins outside this root. The receipt never supplies a
    physical path. A failed latest attempt stops before report or payload IO.
    """
    v.require(type(expected_mode) is str and expected_mode == saved.MODE,
              'formal/unknown registered attempt mode is closed')
    v.require(type(chunk_index) is int and 0 <= chunk_index < 480,
              'registered fixture chunk index')
    v.require(type(source_snapshots) is dict, 'caller source snapshots required')
    v.require(type(expected_payload_pins) is dict, 'external payload pins required')
    for pin in (expected_registry_pin, expected_savepoint_pin,
                expected_receipt_pin, expected_report_pin):
        evidence._pin(pin)
    v.require(expected_registry_pin['sha256'] == v.REGISTRY_RAW_SHA256,
              'frozen registry pin required')
    root = paths.regular_path(Path(root), directory=True)
    v.require(root.parent == ROOT / 'artifacts' and root.name.startswith(PREFIX),
              'dedicated invented fixture root required')
    run_root = paths.regular_path(root / 'run-root', directory=True)
    savepoint_raw = _read(root, 'saved/savepoint.json', expected_savepoint_pin,
                          MAX_SAVEPOINT)
    savepoint = v.strict_json(savepoint_raw)
    evidence._keys(savepoint,
        'format mode invented_only campaign_completed actual_registered_observations_read '
        'run_root chunk_index', 'invented partial savepoint fields')
    for key, expected in {'format': SAVEPOINT_FORMAT, 'mode': saved.MODE,
                          'invented_only': True, 'campaign_completed': False,
                          'actual_registered_observations_read': False,
                          'run_root': str(run_root), 'chunk_index': chunk_index}.items():
        evidence._same(savepoint[key], expected, 'invented partial savepoint ' + key)
    registry_raw = _read(root, 'saved/registry.json', expected_registry_pin,
                         saved.MAX_REGISTRY)
    receipt_raw = _read(root, 'saved/receipt.json', expected_receipt_pin,
                        saved.MAX_RECEIPT)
    receipt = v.strict_json(receipt_raw)
    v.require(type(receipt) is dict and receipt.get('format') == saved.RECEIPT_FORMAT
              and receipt.get('mode') == saved.MODE and receipt.get('invented_only') is True,
              'invented registered receipt required')
    evidence._same(receipt.get('savepoint_pin'), expected_savepoint_pin,
                   'receipt/partial savepoint pin')
    evidence._same(receipt.get('chunk_index'), chunk_index, 'receipt chunk index')
    attempts = receipt.get('attempts')
    v.require(type(attempts) is list and attempts and len(attempts) <= 4,
              'bounded invented attempt history required')
    latest = attempts[-1]
    v.require(type(latest) is dict and latest.get('state') == 'complete',
              'latest invented attempt is not complete')
    attempt = latest.get('attempt')
    v.require(type(attempt) is int and 1 <= attempt <= 4,
              'latest invented attempt number')
    identities, names = _names(chunk_index, attempt)
    v.require(set(expected_payload_pins) == set(names),
              'exact caller-pinned saved-attempt inventory')
    v.require(sum(pin['bytes'] for pin in expected_payload_pins.values()) +
              sum(pin['bytes'] for pin in (expected_registry_pin,
                  expected_savepoint_pin, expected_receipt_pin, expected_report_pin))
              <= saved.MAX_TOTAL, 'registered attempt total byte bound')
    report_raw = _read(root, 'saved/report.json', expected_report_pin,
                       saved.MAX_REPORT)
    payloads = {}
    for logical, physical in sorted(names.items()):
        payloads[logical] = _read(run_root, physical, expected_payload_pins[logical],
                                  saved.MAX_PAYLOAD)
    base = semantic.audit_saved_contract_candidate(
        registry_raw, receipt_raw, report_raw, payloads,
        expected_mode=expected_mode, chunk_index=chunk_index,
        expected_registry_pin=expected_registry_pin,
        expected_receipt_pin=expected_receipt_pin,
        expected_report_pin=expected_report_pin,
        expected_savepoint_pin=expected_savepoint_pin,
        expected_payload_pins=expected_payload_pins,
        source_snapshots=source_snapshots)
    v.require(base['status'] == 'latest_chunk_saved_bytes_bound' and
              base['registered_evaluation_contracts_checked'] == 6,
              'six completed invented evaluations required')
    for identity, slot in zip(identities, latest['evaluations']):
        evidence._same(slot['identity'], identity, 'registered selected identity/order')
        evaluation = v.strict_json(payloads[saved._payload_path(identity)])
        event_bytes = payloads[saved._payload_path(identity, 'events')]
        v.require(event_bytes == b''.join(v.canonical_json(event) + b'\n'
                     for event in v.event_inventory(identity)),
                  'invented full event ledger bytes')
        observations = payloads[saved._payload_path(identity, 'observations')]
        numeric = score_audit._audit_score_derivation_validated(
            evaluation, observations,
            expected_observation_sha256=slot['input_hashes']['observations'])
        evidence._same(numeric['evaluation_outcome'], slot['status'],
                       'invented observation-derived outcome')
    # The semantic binder independently rederived ledger, primary, and slices
    # from these same saved scores; the score audit above tied them to invented
    # observation bytes. All three flags below are fixture scoped.
    return {**base, 'format': FORMAT,
            'scope': 'invented-registered-format-actual-attempt-layout-only',
            'fixture_physical_layout': 'run-attempt-result-payload',
            'fixture_saved_files_read': True, 'fixture_files_read': 4 + len(payloads),
            'invented_registered_format_observations_read': True,
            'invented_observation_profile_score_recomputed': True,
            'observation_to_profile_recomputed': True,
            'observation_to_score_recomputed': True,
            'observation_to_summary_recomputed': True,
            'actual_registered_observations_read': False,
            'registered_observations_read': False,
            'actual_worker_exit_authenticated': False,
            'source_savepoint_bytes_verified': True,
            'campaign_completed': False, 'campaign_evaluations_credited': 0,
            'execution_authenticated': False, 'result_trusted': False,
            'source_closure_complete': False, 'runtime_closure_complete': False,
            'formal_permission': False, 'analysis_authorized': False,
            'promotion_allowed': False, 'independent_s6_complete': False}
