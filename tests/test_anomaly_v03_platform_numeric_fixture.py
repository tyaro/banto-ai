"""Candidate 26H2 numeric scope is separate from the old engineering gate."""
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_engineering_contract as old_contract
from banto_ai import anomaly_v03_platform_numeric_fixture as candidate
from banto_ai import anomaly_v03_platform_fixture_runtime as runtime


def bindings(worker):
    return (worker.EXTRA_SOURCES, worker.SOURCE_FILES, worker.BOOTSTRAP,
            worker.supervisor.resources.probe_runtime, worker.supervisor.policy)


class PlatformNumericFixtureTests(unittest.TestCase):
    def test_candidate_sources_and_bootstraps_are_role_specific(self):
        self.assertEqual(candidate.POLICY_ID, 'anomaly-v03-numeric-platform-fixture-v1')
        self.assertEqual(set(candidate.SOURCE_FILES), set(candidate.analysis.SOURCE_FILES)
                         | set(candidate.audit.SOURCE_FILES) | set(candidate.ADDITIONAL_SOURCES))
        self.assertIn('banto_ai.anomaly_v03_platform_numeric_fixture',
                      candidate.BOOTSTRAP_ANALYSIS)
        self.assertIn('src/banto_ai/anomaly_v03_platform_numeric_fixture.py',
                      candidate.SOURCE_FILES)
        self.assertIn('worker_main("analysis"', candidate.BOOTSTRAP_ANALYSIS)
        self.assertIn('worker_main("audit"', candidate.BOOTSTRAP_AUDIT)
        self.assertNotEqual(candidate.BOOTSTRAP_ANALYSIS, candidate.BOOTSTRAP_AUDIT)
        with self.assertRaisesRegex(ValueError, 'unsupported engineering runtime'):
            old_contract.validate_runtime(dict(runtime.EXPECTED))

    def test_each_scope_restores_shared_runtime_and_role_bindings(self):
        analysis_before = bindings(candidate.analysis)
        audit_before = bindings(candidate.audit)
        for role, worker, bootstrap in (
                ('analysis', candidate.analysis, candidate.BOOTSTRAP_ANALYSIS),
                ('audit', candidate.audit, candidate.BOOTSTRAP_AUDIT)):
            with self.subTest(role=role):
                with candidate._numeric_scope(role):
                    self.assertEqual(worker.EXTRA_SOURCES, candidate.EXTRA_SOURCES)
                    self.assertEqual(worker.SOURCE_FILES, candidate.SOURCE_FILES)
                    self.assertEqual(worker.BOOTSTRAP, bootstrap)
                    self.assertIs(worker.supervisor.resources.probe_runtime,
                                  runtime.probe_runtime)
                    self.assertIs(worker.supervisor.policy.validate_runtime,
                                  runtime.validate_runtime)
                    with self.assertRaisesRegex(RuntimeError, 'stop'):
                        with candidate._numeric_scope(role):
                            raise RuntimeError('stop')
                    self.assertEqual(worker.BOOTSTRAP, bootstrap)
                self.assertEqual(bindings(candidate.analysis), analysis_before)
                self.assertEqual(bindings(candidate.audit), audit_before)

    def test_unknown_role_cannot_change_bindings(self):
        before = bindings(candidate.analysis), bindings(candidate.audit)
        with self.assertRaisesRegex(ValueError, 'unknown numeric fixture role'):
            with candidate._numeric_scope('writer'):
                self.fail('entered unknown role')
        self.assertEqual((bindings(candidate.analysis), bindings(candidate.audit)), before)

    def test_public_entry_points_keep_underlying_request_and_result(self):
        sentinel = object()
        options = dict(expected_revision='a'*40, receipt_parent='receipt-parent',
                       receipt_name='attempt', budget_limits={'limit': 1},
                       resource_budget=sentinel, dependency_profile_raw=None,
                       expected_dependency_profile_pin=None)
        for role, worker, method, entry, bootstrap in (
                ('analysis', candidate.analysis, 'calculate_with_evidence',
                 candidate.calculate_fixture, candidate.BOOTSTRAP_ANALYSIS),
                ('audit', candidate.audit, 'audit_with_evidence',
                 candidate.audit_fixture, candidate.BOOTSTRAP_AUDIT)):
            request = {'role': role}
            result = {'status': 'verified', 'result_pin': {'bytes': 1, 'sha256': 'a'*64}}
            def fake(given, **kwargs):
                self.assertIs(given, request)
                self.assertEqual(kwargs, options)
                self.assertEqual(worker.BOOTSTRAP, bootstrap)
                self.assertIs(worker.supervisor.policy.validate_runtime,
                              runtime.validate_runtime)
                return result
            before = bindings(worker)
            with self.subTest(role=role), patch.object(worker, method, side_effect=fake):
                self.assertIs(entry(request, **options), result)
            self.assertEqual(bindings(worker), before)

    def test_child_entry_dispatches_only_the_selected_worker(self):
        with patch.object(candidate.analysis, 'worker_main', return_value=17) as analysis, \
             patch.object(candidate.audit, 'worker_main', return_value=23) as audit:
            self.assertEqual(candidate.worker_main('analysis', ['one']), 17)
            self.assertEqual(candidate.worker_main('audit', ['two']), 23)
            analysis.assert_called_once_with(['one'])
            audit.assert_called_once_with(['two'])


if __name__ == '__main__':
    unittest.main()
