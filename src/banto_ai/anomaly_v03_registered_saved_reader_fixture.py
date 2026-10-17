"""Read pinned invented registered-format files from an explicit fixture root.

The receipt selects only frozen registered identities and fixed relative names;
no path supplied by a receipt or report is followed.  This boundary reads saved
files in an invented receipt-key layout, not the real attempt-root naming used
by saved dev/smoke runs.  It cannot prove file origin or a worker exit.
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


FORMAT = 'anomaly-v03-registered-saved-reader-fixture-v1'


def _selected_names(receipt_raw, chunk_index, registry_pin, savepoint_pin):
    receipt = v.strict_json(receipt_raw)
    v.require(type(receipt) is dict and type(receipt.get('attempts')) is list,
              'saved fixture receipt attempt inventory')
    attempts = receipt['attempts']
    v.require(receipt.get('format') == saved.RECEIPT_FORMAT and
              receipt.get('mode') == saved.MODE and
              receipt.get('invented_only') is True,
              'only invented registered saved fixture receipts')
    evidence._same(receipt.get('chunk_index'), chunk_index,
                   'saved fixture requested chunk')
    evidence._same(receipt.get('registry_pin'), registry_pin,
                   'saved fixture registry pin')
    evidence._same(receipt.get('savepoint_pin'), savepoint_pin,
                   'saved fixture savepoint pin')
    v.require(len(attempts) <= 4, 'saved fixture bounded attempts')
    latest = attempts[-1] if attempts else None
    if latest is None:
        return set()
    v.require(type(latest) is dict and type(latest.get('evaluations')) is list,
              'saved fixture latest evaluation inventory')
    v.require(all(type(slot) is dict and 'identity' in slot
                  for slot in latest['evaluations']),
              'saved fixture latest slot shape')
    identities = v.evaluation_inventory('holdout')[chunk_index * 6:chunk_index * 6 + 6]
    evidence._same([slot['identity'] for slot in latest['evaluations']], identities,
                   'saved fixture six registered identities')
    names = set()
    for slot in latest['evaluations']:
        v.require(type(slot) is dict and slot.get('status') in
                  ('success', 'inconclusive', 'partial', 'failed', 'not_started'),
                  'saved fixture slot status')
        if slot['status'] not in ('success', 'inconclusive'):
            continue
        identity = slot.get('identity')
        v.validate_identity(identity)
        v.require(identity['role'] == 'holdout', 'saved fixture registered role')
        names.add(saved._payload_path(identity))
        names.update(saved._payload_path(identity, kind) for kind in metadata.INPUT_HASHES)
    return names


def read_saved_chunk_fixture(root, *, expected_mode, chunk_index,
                             expected_registry_pin, expected_receipt_pin,
                             expected_report_pin, expected_savepoint_pin,
                             expected_payload_pins, source_snapshots=None):
    """Read fixed saved names and apply the supplied-byte candidate boundary.

    The root is an explicit caller-selected fixture directory.  All pins must
    be held independently by the caller; this function never derives trust
    anchors from the saved report.  It is not a formal/actual holdout reader.
    """
    v.require(expected_mode == saved.MODE, 'formal/unknown saved reader mode is closed')
    v.require(type(chunk_index) is int and 0 <= chunk_index < 480,
              'saved fixture registered chunk index')
    v.require(type(expected_payload_pins) is dict, 'saved fixture external pins')
    evidence._pin(expected_registry_pin)
    v.require(expected_registry_pin['sha256'] == v.REGISTRY_RAW_SHA256,
              'saved fixture frozen registry pin')
    root = paths.regular_path(Path(root), directory=True)
    registry_raw = pinned.read_pinned(root / 'registry.json', expected_registry_pin,
                                      saved.MAX_REGISTRY)
    receipt_raw = pinned.read_pinned(root / 'receipt.json', expected_receipt_pin,
                                     saved.MAX_RECEIPT)
    names = _selected_names(receipt_raw, chunk_index, expected_registry_pin,
                            expected_savepoint_pin)
    for pin in expected_payload_pins.values():
        evidence._pin(pin)
    if expected_report_pin is not None:
        evidence._pin(expected_report_pin)
    v.require(set(expected_payload_pins) == names,
              'saved fixture exact derived path inventory')
    v.require(sum(pin['bytes'] for pin in expected_payload_pins.values()) +
              len(registry_raw) + len(receipt_raw) +
              (expected_report_pin['bytes'] if expected_report_pin is not None else 0)
              <= saved.MAX_TOTAL, 'saved fixture total byte bound')
    report_raw = (pinned.read_pinned(root / 'report.json', expected_report_pin,
                                     saved.MAX_REPORT) if names else None)
    payloads = {}
    for name in sorted(names):
        v.safe_relative_path(name)
        payloads[name] = pinned.read_pinned(root / name, expected_payload_pins[name],
                                            saved.MAX_PAYLOAD)
    boundary = (saved.bind_saved_chunk_candidate if source_snapshots is None
                else semantic.audit_saved_contract_candidate)
    options = {'expected_mode': expected_mode, 'chunk_index': chunk_index,
               'expected_registry_pin': expected_registry_pin,
               'expected_receipt_pin': expected_receipt_pin,
               'expected_report_pin': expected_report_pin,
               'expected_savepoint_pin': expected_savepoint_pin,
               'expected_payload_pins': expected_payload_pins}
    if source_snapshots is not None:
        options['source_snapshots'] = source_snapshots
    base = boundary(
        registry_raw, receipt_raw, report_raw, payloads,
        **options)
    return {**base, 'format': FORMAT,
            'scope': ('read-only-caller-pinned-invented-saved-contract-files'
                      if source_snapshots is not None else
                      'read-only-caller-pinned-invented-saved-files'),
            'fixture_saved_files_read': True,
            'fixture_physical_layout': 'invented-receipt-key-layout',
            'fixture_semantic_contract_checked': bool(
                base.get('registered_evaluation_contracts_checked', 0)),
            'fixture_root': str(root),
            'fixture_files_read': 2 + int(bool(names)) + len(payloads),
            'registered_observations_read': False,
            'real_saved_chunk_reader_used': False,
            'source_savepoint_bytes_verified': False,
            'actual_worker_exit_authenticated': False,
            'campaign_evaluations_credited': 0,
            'formal_permission': False,
            'analysis_authorized': False,
            'promotion_allowed': False,
            'independent_s6_complete': False}
