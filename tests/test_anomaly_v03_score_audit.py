"""Independent algebraic oracles, tamper rejection and bounded differential tests."""
import ast
import copy
import hashlib
import inspect
import math
import sys
import unittest
from dataclasses import replace
from unittest.mock import patch

from banto_ai import anomaly_v03_score_audit as audit
from banto_ai import anomaly_v03_scoring as producer
from tests.test_anomaly_v03_scoring import saved_row, encode, identity


class ScoreAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Algebraic observations, never a registered-seed generator/campaign.
        rows = [saved_row(equipment, sample) for equipment in audit.EQUIPMENT for sample in range(9000)]
        for sample in range(7208, 7211):
            rows[sample]['quality']['motor_temperature'] = 'missing'
            rows[sample]['signals']['motor_temperature']['value'] = None
        cls.raw, cls.digest = encode(rows)
        cls.observations = audit.decode_observations(cls.raw, cls.digest)
        cls.results = []
        for candidate in range(3):
            ident = identity(candidate)
            profile = producer.fit_profiles(ident, cls.raw, expected_sha256=cls.digest)
            cls.results.append({'identity': ident, 'input_hashes': {'observations': cls.digest},
                'profiles': profile.ledger_rows(), 'scores': producer.score_test(profile, cls.raw, expected_sha256=cls.digest)})

    def run_audit(self, result):
        # Decoding is exercised separately; mutation cases reuse only observations.
        with patch.object(audit, 'decode_observations', return_value=self.observations):
            return audit.audit_score_derivation(result, self.raw, expected_observation_sha256=self.digest)

    def test_stdlib_only_and_all_three_candidates_without_producer_calls(self):
        for node in ast.walk(ast.parse(inspect.getsource(audit))):
            if isinstance(node, ast.Import):
                self.assertTrue(all(alias.name.split('.')[0] in sys.stdlib_module_names for alias in node.names))
            if isinstance(node, ast.ImportFrom):
                self.assertEqual(node.level, 0)
                self.assertIn(node.module.split('.')[0], sys.stdlib_module_names)
        with patch.object(producer, 'fit_profiles', side_effect=AssertionError('producer called')), patch.object(producer, 'score_test', side_effect=AssertionError('producer called')):
            for result in self.results:
                before = copy.deepcopy(result)
                report = self.run_audit(result)
                self.assertEqual(report['score_rows_checked'], 14400)
                self.assertTrue(report['profile_derivation_verified'])
                self.assertFalse(report['independent_s6_complete'])
                self.assertFalse(report['formal_permission'])
                self.assertEqual(result, before)

    def test_median_scale_and_analytic_rank_one_shrinkage(self):
        self.assertEqual(audit.center_scale([1., 3., 5., 9.]), (4., 2.9652))
        state = audit.conditional_state([[-1.]*4, [1.]*4]*290)
        variance = 580/579/(1.4826**2)
        for i in range(4):
            for j in range(4):
                self.assertTrue(math.isclose(state['covariance'][i][j], variance*(1 if i == j else .75), rel_tol=1e-12))
                self.assertTrue(math.isclose(state['precision'][i][j], ((4 if i == j else 0)-12/13)/variance, rel_tol=1e-12))
        for values in ([1.]*20, [1., math.inf], []):
            with self.assertRaises(ValueError):
                audit.center_scale(values)
        with self.assertRaises(ValueError):
            audit.inverse([[1.]*4 for _ in range(4)])

    def test_phase_comes_from_transition_and_does_not_recover_after_gap(self):
        row = audit.Sample('motor-01', 9, 'stopped', 'stop', (1.,)*4, ('ok',)*4)
        sequence = [row, replace(row, sample=10, mode='startup', recipe='start'),
                    replace(row, sample=11, mode='startup', recipe='start'),
                    replace(row, sample=13, mode='startup', recipe='start'),
                    replace(row, sample=14, mode='startup', recipe='start'),
                    replace(row, sample=15, mode='nominal', recipe='run')]
        self.assertEqual([p for _,_,p in audit.phase_rows(sequence)], [None, 0, 1, None, None, 0])

    def test_quality_dependency_stops_c2_peers_and_preserves_previous_quality(self):
        for candidate, result in zip(audit.CANDIDATES, self.results):
            selected = {(r['sample'], r['full_target']):r for r in result['scores']}
            for sample in range(7208, 7212):
                self.assertFalse(selected[sample, 'motor-01.motor_temperature']['available'])
                self.assertEqual(selected[sample, 'motor-01.motor_current']['available'], candidate != audit.CANDIDATES[2])
            self.assertTrue(selected[7212, 'motor-01.motor_temperature']['available'])
        row = self.observations[7208]
        self.assertEqual(audit.exclusions(audit.CANDIDATES[2], row, self.observations[7207], 8, 0), ['peer_quality_or_nonfinite'])
        self.assertEqual(audit.exclusions(audit.CANDIDATES[1], self.observations[7211], self.observations[7210], 11, 1), ['previous_target_quality_or_nonfinite'])

    def test_forged_fit_scale_and_c2_precision_cannot_be_accepted(self):
        for candidate, key in ((0, 'scale'), (1, 'phase_medians'), (2, 'c2_state')):
            value = copy.deepcopy(self.results[candidate])
            p = value['profiles'][0]
            if key == 'scale': p[key] *= 1.01
            elif key == 'phase_medians': p[key][1] += .01
            else: p[key]['precision'][0][0] += .01
            with self.subTest(candidate=candidate), self.assertRaisesRegex(ValueError, 'profiles'):
                self.run_audit(value)

    def test_forged_score_phase_availability_threshold_and_dependency(self):
        changes = {'score': lambda r:r.update(score=r['score']+.01),
                   'phase': lambda r:r.update(phase=2),
                   'availability': lambda r:r.update(available=False),
                   'threshold': lambda r:r.update(threshold_exceeded=not r['threshold_exceeded']),
                   'dependency': lambda r:r['dependencies'][0].update(value=r['dependencies'][0]['value']+1e-13)}
        for name, change in changes.items():
            value = copy.deepcopy(self.results[1])
            change(value['scores'][4])
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'scores|strict threshold'):
                self.run_audit(value)

    def test_discrete_threshold_flag_is_not_masked_by_numeric_tolerance(self):
        # Keep the numerical score within tolerance but forge its discrete flag.
        result = copy.deepcopy(self.results[1])
        score = result['scores'][4]
        original = score['score']
        score['score'] = original + 1e-14
        score['threshold_exceeded'] = not score['threshold_exceeded']
        with self.assertRaisesRegex(ValueError, 'strict threshold'):
            self.run_audit(result)

    def test_reported_score_and_threshold_agree_at_float_neighbors(self):
        for limit in (4., 6.):
            for value, flag in ((None, False), (limit, False), (math.nextafter(limit, 0), False), (math.nextafter(limit, math.inf), True)):
                audit.reported_threshold(value, flag, limit)
                with self.assertRaises(ValueError):
                    audit.reported_threshold(value, not flag, limit)
        for value in (-1e-15, True, math.nan, math.inf):
            with self.assertRaises(ValueError):
                audit.reported_threshold(value, False, 6.)

    def test_duplicate_profile_missing_score_identity_and_holdout_are_rejected(self):
        for kind in ('profile', 'score', 'identity', 'holdout'):
            value = copy.deepcopy(self.results[1])
            if kind == 'profile': value['profiles'][-1] = copy.deepcopy(value['profiles'][0])
            elif kind == 'score': value['scores'].pop()
            elif kind == 'identity': value['identity']['seed'] = True
            else: value['identity']['role'] = 'holdout'
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.run_audit(value)

    def test_changed_observation_hash_and_result_binding_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            audit.decode_observations(self.raw, '0'*64)
        result = copy.deepcopy(self.results[1])
        result['input_hashes']['observations'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'binding'):
            self.run_audit(result)

    def test_noncanonical_duplicate_key_nonfinite_missing_or_reordered_observation(self):
        lines = self.raw.splitlines(keepends=True)
        cases = [b''.join(lines[:-1]), lines[1]+lines[0]+b''.join(lines[2:]),
                 self.raw.replace(b'"equipment_id":', b'"equipment_id":"motor-01","equipment_id":', 1),
                 self.raw.replace(b'"value":', b'"value":NaN,"unused":', 1), b' '+self.raw]
        for raw in cases:
            with self.subTest(prefix=raw[:20]), self.assertRaises(ValueError):
                audit.decode_observations(raw, hashlib.sha256(raw).hexdigest())

    def test_fit_is_test_blind_and_bad_normal_prefix_fails_closed(self):
        phased = list(audit.phase_rows(self.observations))
        original = audit.rebuild_profiles(self.results[2]['identity'], phased)
        altered = [(replace(r, values=(10000.,)*4) if r.sample >= 7200 else r, old, phase) for r,old,phase in phased]
        self.assertEqual(audit.rebuild_profiles(self.results[2]['identity'], altered), original)
        altered = [(replace(r, quality=('missing',)*4) if r.sample == 6000 else r, old, phase) for r,old,phase in phased]
        with self.assertRaisesRegex(ValueError, 'normal prefix quality'):
            audit.rebuild_profiles(self.results[2]['identity'], altered)


if __name__ == '__main__':
    unittest.main()
