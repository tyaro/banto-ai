"""Preformal semantic checks for caller-pinned registered evaluation bytes.

This layer consumes the raw-byte candidate boundary.  It does not read paths,
authenticate a producer process, or infer a profile or score from observations.
In particular, the dev/smoke observation auditor is deliberately not applied to
holdout identities.  A passing fixture remains a closed, supplied-byte claim.
"""
from __future__ import annotations

from . import anomaly_v03 as v
from . import anomaly_v03_consumer_evidence as evidence
from . import anomaly_v03_inference_audit as arithmetic
from . import anomaly_v03_ledger_audit as ledger
from . import anomaly_v03_registered_saved_summary as saved


FORMAT = 'anomaly-v03-registered-evaluation-contract-candidate-v1'


def check_evaluation_contract_bytes(raw, *, identity, input_hashes, outcome,
                                    source_snapshots=None):
    """Check a single invented evaluation's schema and declared state.

    ``not_started`` is accepted solely to exercise the registered schema with
    a hand-written no-run specimen.  The saved candidate wrapper selects only
    success/inconclusive slots and requires complete rows there.
    """
    v.require(type(outcome) is str and outcome in ('success', 'inconclusive', 'not_started'),
              'registered contract outcome')
    v.validate_identity(identity)
    v.require(identity['role'] == 'holdout', 'registered contract requires holdout identity')
    v.require(type(raw) is bytes and 0 < len(raw) <= saved.MAX_PAYLOAD,
              'registered evaluation byte bound')
    value = v.strict_json(raw)
    v.require(raw == v.canonical_json(value), 'canonical registered evaluation bytes')
    v.require(type(value) is dict and value.get('result_type') == 'event-aware-anomaly-v03',
              'registered evaluation result type')
    evidence._same(value.get('identity'), identity, 'registered evaluation identity')
    evidence._same(value.get('input_hashes'), input_hashes, 'registered evaluation input hashes')
    contract = v.validate_result_contract(value, source_snapshots=source_snapshots)
    status = value['status']
    if outcome == 'not_started':
        evidence._same(status, {'run_status': 'not_run', 'engineering_status': 'not_evaluated',
                                'performance_status': 'not_evaluated'},
                       'registered no-run status')
        return {'value': value, 'contract': contract, 'ledger': None}
    evidence._same(status, {'run_status': 'complete',
                            'engineering_status': 'pass' if outcome == 'success' else 'inconclusive',
                            'performance_status': 'not_evaluated'},
                   'registered completed status')
    evidence._same(value['events'], v.event_inventory(identity),
                   'registered completed event inventory')
    profiles = value['profiles']
    v.require(type(profiles) is list and len(profiles) == 48, '48 registered profiles')
    statuses = [profile['status'] for profile in profiles]
    v.require(all(s in ('calibrated', 'inconclusive') for s in statuses),
              'registered profile state')
    evidence._same('inconclusive' if 'inconclusive' in statuses else 'success', outcome,
                   'registered profile/outcome state')
    independent_ledger = ledger.audit_evaluation(value)
    return {'value': value, 'contract': contract, 'ledger': independent_ledger}


def _compare_primary(row, evaluation, ledger_report):
    """Rebuild summary counts from the reported score/ledger, not observations."""
    metrics = ledger_report['metrics']
    counts = {}
    for kind in arithmetic.METRICS[:5]:
        metric = metrics[kind]
        counts[kind] = list(arithmetic.counts([metric['numerator'], metric['denominator']], kind))
    evidence._same([item['full_target'] for item in metrics['availability']],
                   list(arithmetic.TARGETS), 'registered availability order')
    for item, kind in zip(metrics['availability'], arithmetic.AVAILABILITY):
        metric = item['metric']
        counts[kind] = list(arithmetic.counts([metric['numerator'], metric['denominator']], kind))
    evidence._same(row['primary']['counts'], counts,
                   'registered primary counts from reported scores')
    evidence._same(row['primary']['effective_clean_seconds'],
                   metrics['effective_clean_seconds'], 'registered effective clean exposure')
    histogram = [0] * 5
    for incident in evaluation['incidents']:
        if incident['causal_detected']:
            delay = incident['delay_seconds']
            v.require(type(delay) in (int, float) and delay in (1, 2, 3, 4, 5),
                      'registered detected delay')
            histogram[int(delay) - 1] += 1
    evidence._same(row['primary']['delay_histogram'], histogram,
                   'registered delay histogram from reported incidents')


def audit_saved_contract_candidate(registry_raw, receipt_raw, report_raw, payloads, *,
                                   expected_mode, chunk_index, expected_registry_pin,
                                   expected_receipt_pin, expected_report_pin,
                                   expected_savepoint_pin, expected_payload_pins,
                                   source_snapshots):
    """Apply the registered contract and reported-score ledger after byte checks.

    Source snapshots must be supplied by the caller; matching them to a claimed
    revision here does not authenticate Git history or execution provenance.
    """
    v.require(type(source_snapshots) is dict, 'caller-captured source snapshots required')
    base = saved.bind_saved_chunk_candidate(
        registry_raw, receipt_raw, report_raw, payloads,
        expected_mode=expected_mode, chunk_index=chunk_index,
        expected_registry_pin=expected_registry_pin,
        expected_receipt_pin=expected_receipt_pin,
        expected_report_pin=expected_report_pin,
        expected_savepoint_pin=expected_savepoint_pin,
        expected_payload_pins=expected_payload_pins)
    receipt = v.strict_json(receipt_raw)
    latest = receipt['attempts'][-1] if receipt['attempts'] else None
    selected = [slot for slot in latest['evaluations']
                if slot['status'] in ('success', 'inconclusive')] if latest else []
    rows = v.strict_json(report_raw)['rows'] if selected else []
    for row, slot in zip(rows, selected):
        identity = slot['identity']
        raw = payloads[saved._payload_path(identity)]
        checked = check_evaluation_contract_bytes(
            raw, identity=identity, input_hashes=slot['input_hashes'],
            outcome=slot['status'], source_snapshots=source_snapshots)
        _compare_primary(row, checked['value'], checked['ledger'])
    return {**base, 'format': FORMAT,
            'scope': 'supplied-registered-format-semantic-fixture',
            'registered_evaluation_contracts_checked': len(rows),
            'reported_score_ledger_recomputed': bool(rows),
            'reported_score_to_primary_summary_checked': bool(rows),
            'reported_score_to_slice_summary_recomputed': False,
            'source_snapshots_caller_supplied': bool(rows),
            'observation_to_profile_recomputed': False,
            'observation_to_score_recomputed': False,
            'observation_to_summary_recomputed': False,
            'registered_observations_read': False,
            'real_saved_chunk_reader_used': False,
            'actual_worker_exit_authenticated': False,
            'campaign_evaluations_credited': 0,
            'formal_permission': False, 'analysis_authorized': False,
            'promotion_allowed': False, 'independent_s6_complete': False}
