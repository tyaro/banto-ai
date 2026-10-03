"""Registered holdout identities with invented marker bytes only."""
import copy
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_registered_fixture as fixture
from banto_ai import anomaly_v03_consumer_input as metadata


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_RAW = (ROOT / 'examples/configs/anomaly-v03-freeze-registry.json').read_bytes()


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def marker(kind, name):
    return hashlib.sha256(f'anomaly-v03-invented-{kind}-v1:{name}'.encode()).hexdigest()


def slot(identity):
    return {'identity': copy.deepcopy(identity), 'status': 'success',
        'profile_status': 'calibrated',
        'input_hashes': {kind: marker('input', identity['dataset_id'] + ':' + kind)
                         for kind in metadata.INPUT_HASHES},
        'evaluation_sha256': marker('evaluation', identity['evaluation_id'])}


def attempt(chunk, number=1):
    return {'record': {'attempt': number, 'state': 'complete', 'failure': None,
        'evaluations': [slot(i) for i in chunk['identities']]},
        'worker': {'exit_confirmed': True, 'exit_code': 0}}


def failure():
    return {'stage': 'supervision', 'reason': 'worker_exit', 'evidence_sha256': None}


def failed_attempt(chunk, number=1):
    value = attempt(chunk, number)
    value['record'].update(state='failed', failure=failure())
    value['record']['evaluations'][-1].update(status='partial', profile_status='not_evaluated',
                                             evaluation_sha256=None)
    value['worker']['exit_code'] = 1
    return value


def complete():
    value = fixture.planned_fixture(pin(REGISTRY_RAW))
    for chunk in value['chunks']:
        chunk['attempts'] = [attempt(chunk)]
    value['producer'] = {'state': 'complete', 'failure': None,
                         'worker': {'exit_confirmed': True, 'exit_code': 0}}
    value['coverage'] = {state: 2880 if state == 'success' else 0
                         for state in metadata.SLOT_STATES}
    return value


def check(value, **kwargs):
    raw = v.canonical_json(value)
    return fixture.validate_fixture(raw, REGISTRY_RAW, expected_mode=kwargs.get('mode', fixture.MODE),
        expected_manifest_pin=kwargs.get('manifest_pin', pin(raw)),
        expected_registry_pin=kwargs.get('registry_pin', pin(REGISTRY_RAW)))


class RegisteredFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.complete = complete()

    def test_fixed_holdout_inventory_is_complete_but_cannot_authorize_formal_work(self):
        with patch('builtins.open', side_effect=AssertionError('unexpected IO')):
            result = check(self.complete)
        self.assertEqual((result['planned_chunks'], result['planned_evaluations']), (480, 2880))
        self.assertEqual((result['declared_complete_chunks'], result['coverage']['success']), (480, 2880))
        self.assertEqual(result['status'], 'fixture_inventory_complete')
        self.assertTrue(result['fixture_marker_hashes_checked'])
        self.assertTrue(result['supplied_manifest_and_registry_bytes_verified'])
        for field in ('formal_permission', 'analysis_authorized', 'independent_s6_complete',
                      'actual_worker_exit_authenticated', 'registered_observations_read',
                      'registered_input_bytes_verified'):
            self.assertFalse(result[field], field)
        self.assertEqual(result['campaign_evaluations_credited'], 0)

    def test_unstarted_inventory_keeps_all_slots_unverified(self):
        result = check(fixture.planned_fixture(pin(REGISTRY_RAW)))
        self.assertEqual(result['status'], 'fixture_inventory_incomplete')
        self.assertEqual(result['coverage']['not_started'], 2880)
        self.assertEqual(result['declared_complete_chunks'], 0)
        self.assertFalse(result['producer_worker_exit_declared'])

    def test_external_pins_and_frozen_registry_are_required(self):
        raw = v.canonical_json(self.complete)
        with self.assertRaisesRegex(ValueError, 'external fixture manifest bytes'):
            fixture.validate_fixture(raw + b' ', REGISTRY_RAW, expected_mode=fixture.MODE,
                expected_manifest_pin=pin(raw), expected_registry_pin=pin(REGISTRY_RAW))
        with self.assertRaisesRegex(ValueError, 'frozen registry bytes'):
            fixture.validate_fixture(raw, REGISTRY_RAW + b' ', expected_mode=fixture.MODE,
                expected_manifest_pin=pin(raw), expected_registry_pin=pin(REGISTRY_RAW))
        wrong = dict(pin(REGISTRY_RAW), sha256='0' * 64)
        with self.assertRaisesRegex(ValueError, 'bounded external fixture pins'):
            check(self.complete, registry_pin=wrong)

    def test_formal_mode_rejected_before_decoding_or_registry_traversal(self):
        with self.assertRaisesRegex(ValueError, 'formal/unknown registered fixture mode is closed'):
            fixture.validate_fixture(b'not json', b'not json', expected_mode='formal',
                expected_manifest_pin=None, expected_registry_pin=None)
        value = copy.deepcopy(self.complete)
        value['mode'] = 'formal'
        with self.assertRaisesRegex(ValueError, 'fixture identity and registry pin'):
            check(value)

    def test_missing_reordered_or_relabelled_registered_slots_fail_even_if_resealed(self):
        for change in ('missing', 'reordered', 'seed', 'chunk'):
            value = copy.deepcopy(self.complete)
            if change == 'missing':
                value['chunks'][0]['attempts'][0]['record']['evaluations'].pop()
            elif change == 'reordered':
                rows = value['chunks'][0]['attempts'][0]['record']['evaluations']
                rows[0], rows[1] = rows[1], rows[0]
            elif change == 'seed':
                value['chunks'][0]['identities'][0]['seed'] += 1
            else:
                value['chunks'][0], value['chunks'][1] = value['chunks'][1], value['chunks'][0]
            with self.subTest(change=change), self.assertRaises(ValueError):
                check(value)

    def test_real_looking_hash_cannot_replace_invented_marker(self):
        value = copy.deepcopy(self.complete)
        for row in value['chunks'][0]['attempts'][0]['record']['evaluations'][:3]:
            row['input_hashes']['observations'] = 'a' * 64
        with self.assertRaisesRegex(ValueError, 'noninvented fixture input marker'):
            check(value)

    def test_failed_attempt_is_retained_and_latest_failure_cannot_fall_back(self):
        value = copy.deepcopy(self.complete)
        chunk = value['chunks'][0]
        chunk['attempts'] = [failed_attempt(chunk), attempt(chunk, 2)]
        result = check(value)
        self.assertEqual(result['attempt_count'], 481)
        self.assertEqual(result['coverage']['success'], 2880)
        self.assertEqual(result['failed_attempt_history'][0]['attempt'], 1)
        self.assertFalse(result['failed_attempt_history'][0]['is_latest'])

        chunk['attempts'][1] = failed_attempt(chunk, 2)
        value['producer'] = {'state': 'failed', 'failure': failure(),
                             'worker': {'exit_confirmed': True, 'exit_code': 1}}
        value['coverage']['success'] = 2879
        value['coverage']['partial'] = 1
        result = check(value)
        self.assertEqual(result['status'], 'fixture_inventory_incomplete')
        self.assertEqual(result['declared_complete_chunks'], 479)
        self.assertTrue(result['failed_attempt_history'][-1]['is_latest'])

    def test_retry_after_integrity_failure_and_false_clean_exits_fail(self):
        value = copy.deepcopy(self.complete)
        chunk = value['chunks'][0]
        first = failed_attempt(chunk)
        first['record']['failure']['reason'] = 'hash_mismatch'
        chunk['attempts'] = [first, attempt(chunk, 2)]
        with self.assertRaisesRegex(ValueError, 'retry after fixture integrity failure'):
            check(value)
        value = copy.deepcopy(self.complete)
        value['chunks'][0]['attempts'][0]['worker']['exit_confirmed'] = False
        value['chunks'][0]['attempts'][0]['worker']['exit_code'] = None
        with self.assertRaisesRegex(ValueError, 'complete fixture worker exit'):
            check(value)
        value = copy.deepcopy(self.complete)
        value['producer']['worker']['exit_code'] = 1
        with self.assertRaisesRegex(ValueError, 'complete fixture worker exit'):
            check(value)


if __name__ == '__main__':
    unittest.main()
