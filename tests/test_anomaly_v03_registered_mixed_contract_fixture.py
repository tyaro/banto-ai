"""Invented mixed-profile holdout-format ledger; no registered observations."""
from __future__ import annotations

import copy
import unittest

from banto_ai import _anomaly_v03_contract as frozen
from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_registered_evaluation_contract as contract
from tests import test_anomaly_v03_registered_completed_contract_fixture as all_unavailable


TARGET = frozen.FULL_TARGETS[0]
MODE = 'startup'
SAMPLE = 7231  # Invented clean second, away from event-relative references.


def mixed_evaluation(value):
    """Calibrate one C0 profile and report one low available score by hand."""
    value = copy.deepcopy(value)
    identity = value['identity']
    assert identity['candidate_id'] == frozen.CANDIDATES[0]
    profile = next(p for p in value['profiles']
                   if p['full_target'] == TARGET and p['mode'] == MODE)
    calibration = [sample for sample in range(5400, 7200)
                   if frozen.MODES[(sample % 180) // 30] == MODE and sample % 30 > 0]
    assert len(calibration) == 290
    profile.update(status='calibrated', calibration_samples=calibration[:250],
                   center=0.0, scale=1.0, reason=None)
    score = next(row for row in value['scores']
                 if row['full_target'] == TARGET and row['sample'] == SAMPLE)
    assert score['mode'] == MODE and score['phase'] == 1
    score.update(dependencies=[
        {'full_target': TARGET, 'sample': sample,
         'timestamp_ms': frozen.START_MS + sample * 1000,
         'quality': 'ok', 'value': 1.0}
        for sample in (SAMPLE - 1, SAMPLE)],
        residual=0.0, score=0.0, available=True, exclusion_reason=None,
        exclusion_tags=[], threshold_exceeded=False, streak=0,
        source_episode_id=None)
    value['metrics']['availability'][0]['metric'] = {
        **all_unavailable._metric(1800), 'numerator': 1, 'value': 1 / 1800}
    value['metrics']['effective_clean_seconds'] = 1
    value['metrics']['effective_clean_rate'] = 0.0
    assert value['status']['engineering_status'] == 'inconclusive'
    assert value['identity'] == identity
    return value


def mixed_slices(events):
    """Hand-count only the changed cells over the all-unavailable baseline."""
    result = all_unavailable._zero_slices(events, 'core')
    by_status = result['score_slices']['profile-status']
    for field in ('planned', 'observed'):
        by_status['inconclusive'][field] -= 300
        by_status['calibrated'][field] += 300
    labels = {'full-target': TARGET, 'signal-mode': TARGET + '.' + MODE,
              'phase': '1', 'context': 'clean', 'quality-current': 'ok',
              'quality-previous': 'ok', 'fault-quality-overlap': 'no',
              'profile-status': 'calibrated'}
    for dimension in ('quality-current', 'quality-previous'):
        for field in ('planned', 'observed'):
            result['score_slices'][dimension]['absent'][field] -= 1
            result['score_slices'][dimension]['ok'][field] += 1
    for dimension, label in labels.items():
        result['score_slices'][dimension][label]['available'] += 1
    return result


def mixed_chunk():
    """Reseal six supplied invented slots; only the first has a mixed profile."""
    registry_raw, receipt_raw, report_raw, payloads, options = (
        all_unavailable.invented_completed_chunk())
    receipt, report = v.strict_json(receipt_raw), v.strict_json(report_raw)
    payloads = dict(payloads)
    slot, row = receipt['attempts'][0]['evaluations'][0], report['rows'][0]
    identity = slot['identity']
    assert identity['stratum'] == 'core' and identity['candidate_id'] == frozen.CANDIDATES[0]
    path = contract.saved._payload_path(identity)
    evaluation = mixed_evaluation(v.strict_json(payloads[path]))
    raw = v.canonical_json(evaluation)
    payloads[path] = raw
    pin = all_unavailable._pin(raw)
    slot['evaluation_sha256'] = pin['sha256']
    row['evaluation_pin'] = pin
    row['primary']['counts']['availability:' + TARGET] = [1, 1800]
    row['primary']['effective_clean_seconds'] = 1
    row['slices'] = mixed_slices(evaluation['events'])
    receipt_raw = v.canonical_json(receipt)
    report['receipt_pin'] = all_unavailable._pin(receipt_raw)
    report['payload_pins'][path] = pin
    report_raw = v.canonical_json(report)
    options = {**options, 'expected_receipt_pin': all_unavailable._pin(receipt_raw),
               'expected_report_pin': all_unavailable._pin(report_raw),
               'expected_payload_pins': dict(report['payload_pins'])}
    return registry_raw, receipt_raw, report_raw, payloads, options


class MixedRegisteredContractFixtureTests(unittest.TestCase):
    def test_mixed_profile_and_available_score_bind_ledger_primary_and_slices(self):
        args = mixed_chunk()
        result = contract.audit_saved_contract_candidate(*args[:4], **args[4])
        self.assertEqual(result['registered_evaluation_contracts_checked'], 6)
        self.assertTrue(result['reported_score_ledger_recomputed'])
        self.assertTrue(result['reported_score_to_primary_summary_checked'])
        self.assertTrue(result['reported_score_to_slice_summary_recomputed'])
        self.assertFalse(result['observation_to_profile_recomputed'])
        self.assertFalse(result['observation_to_score_recomputed'])
        self.assertFalse(result['formal_permission'])
        self.assertEqual(result['campaign_evaluations_credited'], 0)
        evaluation = v.strict_json(args[3][contract.saved._payload_path(
            v.strict_json(args[1])['attempts'][0]['evaluations'][0]['identity'])])
        self.assertEqual(sum(p['status'] == 'calibrated' for p in evaluation['profiles']), 1)
        self.assertEqual(sum(s['available'] for s in evaluation['scores']), 1)

    def test_resealed_available_quality_slice_reassignment_is_rejected(self):
        args = mixed_chunk()
        report = v.strict_json(args[2])
        cells = report['rows'][0]['slices']['score_slices']['quality-current']
        cells['ok']['available'] -= 1
        cells['absent']['available'] += 1
        report_raw = v.canonical_json(report)
        options = {**args[4], 'expected_report_pin': all_unavailable._pin(report_raw)}
        with self.assertRaisesRegex(ValueError,
                                    'registered slices from reported score ledger'):
            contract.audit_saved_contract_candidate(
                args[0], args[1], report_raw, args[3], **options)


if __name__ == '__main__':
    unittest.main()
