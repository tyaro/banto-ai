"""A completed registered-format result made only from invented ledger claims.

The holdout identity and event schedule are schema markers.  No registered
observations are generated, read, or scored by this fixture.
"""
from __future__ import annotations

import copy
import hashlib
import unittest
from pathlib import Path

from banto_ai import _anomaly_v03_contract as frozen
from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_registered_evaluation_contract as contract
from banto_ai import anomaly_v03_slices as slices
from tests.test_anomaly_v03_registered_evaluation_contract import _no_run, _source
from tests.test_anomaly_v03_registered_saved_summary import example


def _metric(denominator):
    return {'numerator': 0, 'denominator': denominator,
            'value': 0.0 if denominator else None,
            'ci_status': 'not_evaluated' if denominator else 'inconclusive',
            'ci_lower': None, 'ci_upper': None, 'null_replicates': 0}


def invented_complete_inconclusive(identity=None, input_hashes=None):
    """Give every planned score a declared profile exclusion, with no alert."""
    value = _no_run()
    identity = value['identity'] if identity is None else identity
    value['identity'] = copy.deepcopy(identity)
    value['events'] = v.event_inventory(identity)
    if input_hashes is not None:
        value['input_hashes'] = copy.deepcopy(input_hashes)
    value['incidents'] = [{
        'dataset_id': identity['dataset_id'], 'event_id': event['event_id'],
        'status': 'processed', 'candidate_count': 0,
        'candidate_episode_ids': [], 'selected_candidate_episode_id': None,
        'selected_source_episode_id': None, 'support_score_ids': [],
        'reason': 'no_candidate_in_window', 'matched_episode_id': None,
        'causal_detected': False, 'delay_seconds': None,
        'secondary_canonical_detected': None}
        for event in value['events'] if event['event_class'] in ('machine', 'sensor')]
    value['status'] = {'run_status': 'complete', 'engineering_status': 'inconclusive',
                       'performance_status': 'not_evaluated'}
    value['profiles'] = []
    value['scores'] = []
    for target in frozen.FULL_TARGETS:
        equipment = target.split('.')[0]
        for mode, recipe in zip(frozen.MODES, frozen.RECIPES):
            value['profiles'].append({
                'profile_id': f'invented-profile-{target.replace(".", "-")}-{mode}',
                'identity': copy.deepcopy(identity), 'profile_version': '0.3',
                'equipment': equipment, 'full_target': target, 'mode': mode,
                'recipe': recipe, 'status': 'inconclusive', 'fit_samples': [],
                'calibration_samples': [], 'planned_calibration_points': 290,
                'minimum_calibration_points': 250, 'phase_medians': None,
                'center': None, 'scale': None, 'c2_state': None,
                'reason': 'insufficient_points'})
        for sample in range(7200, 9000):
            mode_index = (sample % 180) // 30
            mode = frozen.MODES[mode_index]
            value['scores'].append({
                'score_id': (f'{identity["evaluation_id"]}-score-'
                             f'{target.replace(".", "-")}-{sample:04d}'),
                'dataset_id': identity['dataset_id'],
                'candidate_id': identity['candidate_id'], 'sample': sample,
                'timestamp_ms': frozen.START_MS + sample * 1000,
                'phase': sample % 30, 'equipment': equipment,
                'full_target': target, 'mode': mode,
                'recipe': frozen.RECIPES[mode_index],
                'profile_id': f'invented-profile-{target.replace(".", "-")}-{mode}',
                'dependencies': [], 'residual': None, 'score': None,
                'available': False, 'exclusion_reason': 'profile_inconclusive',
                'exclusion_tags': ['profile_inconclusive'],
                'threshold_exceeded': False, 'streak': 0,
                'source_episode_id': None})
    value['metrics'] = {
        'machine_recall': _metric(10), 'sensor_recall': _metric(10),
        'precision': _metric(0), 'clean_rate': _metric(3365),
        'false_alert_burden': _metric(20),
        'availability': [{'full_target': target, 'metric': _metric(1800)}
                         for target in frozen.FULL_TARGETS],
        'scheduled_clean_seconds': 3365, 'effective_clean_seconds': 0,
        'effective_clean_rate': None,
        'delay_summary': {'count': 0, 'median': None, 'mean': None, 'min': None,
                          'max': None, 'conditioned_on': 'causal-detected-only',
                          'undetected_fill': 'forbidden', 'unit': 'seconds'}}
    value['row_counts'] = {name: len(value[name]) for name in
                           ('events', 'profiles', 'scores', 'source_episodes',
                            'equipment_episodes', 'incidents')}
    return value


def _zero_slices(events, stratum):
    """Hand-count fixed planned denominators, with no available score or alert."""
    raw = slices.empty_counts()
    raw['evaluations'] = 1
    raw['profile_inconclusive_evaluations'] = 1
    for event in events:
        if event['event_class'] not in ('machine', 'sensor'):
            continue
        keys = {'class': event['event_class'],
                'equipment': event['equipment'], 'mode': event['mode'],
                'class-equipment-mode': '.'.join((event['event_class'],
                                                  event['equipment'], event['mode'])),
                'test-cycle': str(event['cycle']),
                'event-start-phase': str(event['start_sample'] % 30)}
        for dimension, key in keys.items():
            raw['incident_slices'][dimension][key]['planned'] += 1
    for target in frozen.FULL_TARGETS:
        raw['score_slices']['full-target'][target].update(planned=1800, observed=1800)
        for mode in frozen.MODES:
            raw['score_slices']['signal-mode'][target + '.' + mode].update(
                planned=300, observed=300)
    for key, unit in zip(slices.PHASES, (1, 1, 1, 1, 3, 7, 7, 9)):
        raw['score_slices']['phase'][key].update(planned=480 * unit,
                                                 observed=480 * unit)
    for key, seconds in (('raw-event', 118), ('grace', 117), ('clean', 3365)):
        raw['equipment_context'][key]['planned_seconds'] = seconds
        raw['score_slices']['context'][key].update(planned=4 * seconds,
                                                   observed=4 * seconds)
    for dimension, key in (('quality-current', 'absent'),
                           ('quality-previous', 'absent'),
                           ('profile-status', 'inconclusive')):
        raw['score_slices'][dimension][key].update(planned=14400,
                                                    observed=14400)
    overlap = 6 if stratum == 'quality-stress' else 0
    raw['score_slices']['fault-quality-overlap']['no'].update(
        planned=14400 - overlap, observed=14400 - overlap)
    raw['score_slices']['fault-quality-overlap']['yes'].update(
        planned=overlap, observed=overlap)
    for offset, key in enumerate(slices.SCORE_KEYS['event-offset']):
        outside = 1 if offset in (0, 1) else 0
        raw['score_slices']['event-offset'][key].update(
            planned=40, observed=30 - outside, unscored_target=10,
            outside_test=outside)
    return raw


def _pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def invented_completed_chunk():
    """Reseal six invented evaluations under caller-held candidate pins."""
    receipt, report, payloads = example()
    for slot, row in zip(receipt['attempts'][0]['evaluations'], report['rows']):
        identity = slot['identity']
        value = invented_complete_inconclusive(identity, slot['input_hashes'])
        name = contract.saved._payload_path(identity)
        payloads[name] = v.canonical_json(value)
        slot.update(status='inconclusive', profile_status='inconclusive',
                    evaluation_sha256=_pin(payloads[name])['sha256'])
        row.update(evaluation_outcome='inconclusive',
                   evaluation_pin=_pin(payloads[name]),
                   primary={'counts': {
                       'machine_recall': [0, 10], 'sensor_recall': [0, 10],
                       'precision': [0, 0], 'clean_rate': [0, 3365],
                       'false_alert_burden': [0, 20],
                       **{'availability:' + target: [0, 1800]
                          for target in frozen.FULL_TARGETS}},
                       'effective_clean_seconds': 0,
                       'delay_histogram': [0] * 5},
                   slices=_zero_slices(value['events'], identity['stratum']))
    receipt_raw = v.canonical_json(receipt)
    report['receipt_pin'] = _pin(receipt_raw)
    report['payload_pins'] = {name: _pin(raw) for name, raw in payloads.items()}
    report_raw = v.canonical_json(report)
    registry_raw = (Path(__file__).resolve().parents[1] /
                    'examples/configs/anomaly-v03-freeze-registry.json').read_bytes()
    revision, _ = _source()
    return (registry_raw, receipt_raw, report_raw, payloads,
            {'expected_mode': contract.saved.MODE, 'chunk_index': 0,
             'expected_registry_pin': _pin(registry_raw),
             'expected_receipt_pin': _pin(receipt_raw),
             'expected_report_pin': _pin(report_raw),
             'expected_savepoint_pin': receipt['savepoint_pin'],
             'expected_payload_pins': dict(report['payload_pins']),
             'source_snapshots': {revision: {
                 'src/invented-specimen.py': b'# invented schema specimen source\n'}}})


class CompletedRegisteredContractFixtureTests(unittest.TestCase):
    def test_invented_completed_inconclusive_contract_and_ledger(self):
        value = invented_complete_inconclusive()
        revision, _ = _source()
        source_bytes = b'# invented schema specimen source\n'
        checked = contract.check_evaluation_contract_bytes(
            v.canonical_json(value), identity=value['identity'],
            input_hashes=value['input_hashes'], outcome='inconclusive',
            source_snapshots={revision: {'src/invented-specimen.py': source_bytes}})
        self.assertEqual(checked['contract']['validation_status'], 'result_contract_valid')
        self.assertEqual(checked['ledger']['status'], 'ledger_checks_passed')
        self.assertEqual(checked['ledger']['score_rows'], 14400)
        self.assertEqual((len(value['profiles']), len(value['incidents'])), (48, 20))
        self.assertEqual(checked['ledger']['metrics']['effective_clean_seconds'], 0)
        self.assertFalse(checked['ledger']['score_derivation_verified'])
        self.assertFalse(checked['ledger']['independent_s6_complete'])

    def test_six_slot_completed_chunk_binds_reported_scores_to_primary(self):
        args = invented_completed_chunk()
        result = contract.audit_saved_contract_candidate(*args[:4], **args[4])
        self.assertEqual(result['status'], 'latest_chunk_saved_bytes_bound')
        self.assertEqual(result['registered_evaluation_contracts_checked'], 6)
        self.assertTrue(result['reported_score_ledger_recomputed'])
        self.assertTrue(result['reported_score_to_primary_summary_checked'])
        self.assertTrue(result['reported_score_to_slice_summary_recomputed'])
        self.assertEqual(result['campaign_evaluations_credited'], 0)
        for key in ('observation_to_profile_recomputed',
                    'observation_to_score_recomputed',
                    'real_saved_chunk_reader_used', 'formal_permission'):
            self.assertFalse(result[key], key)

    def test_invented_slice_reassignment_is_rejected(self):
        args = invented_completed_chunk()
        report = v.strict_json(args[2])
        cell = report['rows'][0]['slices']['score_slices']['quality-current']
        cell['absent']['observed'] -= 1
        cell['ok']['observed'] += 1
        report_raw = v.canonical_json(report)
        opts = dict(args[4])
        opts['expected_report_pin'] = _pin(report_raw)
        with self.assertRaises(ValueError):
            contract.audit_saved_contract_candidate(
                args[0], args[1], report_raw, args[3], **opts)


if __name__ == '__main__':
    unittest.main()
