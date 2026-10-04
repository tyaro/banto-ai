"""Small checks for the separate 50,000-draw measurement boundary."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_inference_audit as primary
from banto_ai import anomaly_v03_preformal_draw_audit as independent
from banto_ai import anomaly_v03_preformal_draw_budget as budget


class PreformalDrawBudgetTests(unittest.TestCase):
    def test_invented_count_fixture_and_closed_claims(self):
        fixture = budget._input()
        self.assertEqual(len(fixture['clusters']), 40)
        self.assertEqual(fixture['invented_only'], True)
        self.assertEqual(fixture['registered_data_read'], False)
        self.assertTrue(all(row['cluster_id'] == f'budget-invented-{i:02d}'
                            for i, row in enumerate(fixture['clusters'])))
        primary._fixture_clusters(fixture['clusters'])
        self.assertNotIn('holdout', budget._raw(fixture).decode('utf-8'))

    def test_full_table_arithmetic_matches_on_small_nontrivial_draws(self):
        clusters = budget.invented_clusters()
        draws = [bytes((draw*13+position*7) % 40 for position in range(40))
                 for draw in range(32)]
        calculated = primary.compute_fixture_tables(clusters, draws, engineering_ready=False)
        expected = independent._expected_tables(clusters, draws)
        self.assertEqual(budget._raw(calculated['candidate_tables']), budget._raw(expected))
        self.assertEqual((len(expected), sum(len(row['gates']) for row in expected)), (9, 180))
        self.assertIsNone(calculated['selected_candidate'])
        self.assertFalse(calculated['formal_permission'])

    def test_incomplete_draws_and_tampered_calculation_cannot_pass_audit(self):
        clusters = budget.invented_clusters()
        report = primary.compute_fixture_tables(clusters, [bytes(range(40))], engineering_ready=False)
        with self.assertRaisesRegex(ValueError, '50,000'):
            independent.audit(clusters, report, [bytes(range(40))])
        with self.assertRaisesRegex(ValueError, 'calculation scope'):
            independent.audit(clusters, {'scope': 'formal'}, [bytes(range(40))]*50000)
        report['replicate_count'] = 50000
        report['registered_data_read'] = True
        with self.assertRaisesRegex(ValueError, 'calculation scope'):
            independent.audit(clusters, report, [bytes(range(40))]*50000)

    def test_role_and_audit_reports_reject_extra_claims(self):
        output_pin = {'bytes': 1, 'sha256': '0'*64}
        role = {'format': budget.FORMAT+'-role', 'role': 'calculate',
                'status': 'complete', 'draw_sha256': budget.DRAW_HASH,
                'draw_bytes': 2000000, 'replicates': 50000,
                'output_pin': output_pin, 'registered_data_read': False,
                'formal_bootstrap_performed': False, 'formal_permission': False}
        budget._verify_role_report(role, 'calculate', output_pin)
        with self.assertRaisesRegex(ValueError, 'fields'):
            budget._verify_role_report({**role, 'execution_authenticated': True}, 'calculate', output_pin)
        with self.assertRaisesRegex(ValueError, 'formal_permission'):
            budget._verify_role_report({**role, 'formal_permission': True}, 'calculate', output_pin)
        audit = {'format': independent.FORMAT,
                 'status': 'invented_primary_numerics_matched',
                 'draw_sha256': budget.DRAW_HASH, 'clusters': 40,
                 'replicates': 50000, 'candidate_tables': 9,
                 'primary_estimates': 117, 'paired_estimates': 72,
                 'gates': 180, 'calculation_sha256': output_pin['sha256'],
                 'registered_data_read': False, 'formal_bootstrap_performed': False,
                 'independent_s6_complete': False, 'formal_permission': False,
                 'promotion_allowed': False, 'performance_status': 'not_evaluated'}
        budget._verify_audit_report(audit, output_pin)
        with self.assertRaisesRegex(ValueError, 'fields'):
            budget._verify_audit_report({**audit, 'execution_authenticated': True}, output_pin)
        with self.assertRaisesRegex(ValueError, 'formal_bootstrap_performed'):
            budget._verify_audit_report({**audit, 'formal_bootstrap_performed': True}, output_pin)

    def test_preflight_shortfall_retains_failure_without_child(self):
        with tempfile.TemporaryDirectory() as temporary:
            receipt = Path(temporary)/'anomaly-v03-preformal-draw-budget-preflight'
            observation = {'commit_headroom_bytes': budget.MINIMUM_HEADROOM-1,
                           'free_ram_bytes': budget.MINIMUM_HEADROOM+1,
                           'free_disk_bytes': budget.MINIMUM_DISK+1,
                           'parent_peak_private_bytes': 1}
            with (patch.object(budget, '_source_pins', return_value={}),
                  patch.object(budget, '_runtime', return_value={'test': True}),
                  patch.object(budget, 'MEASUREMENT_PARENT', Path(temporary)),
                  patch.object(budget.budget, 'system_snapshot', return_value=observation),
                  patch.object(budget, '_supervise', side_effect=AssertionError('child launched'))):
                result = budget.run_measurement(receipt)
            self.assertEqual(result['status'], 'failed')
            self.assertIn('preflight_commit_headroom', result['reason'])
            self.assertTrue((receipt/'receipt.json').exists())
            self.assertEqual(json.loads((receipt/'receipt.json').read_text())['formal_permission'], False)
            self.assertFalse((receipt/'input.json').exists())

    def test_launch_failure_retains_failed_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            receipt = Path(temporary)/'anomaly-v03-preformal-draw-budget-launch-failure'
            observation = {'commit_headroom_bytes': budget.MINIMUM_HEADROOM+1,
                           'free_ram_bytes': budget.MINIMUM_HEADROOM+1,
                           'free_disk_bytes': budget.MINIMUM_DISK+1,
                           'parent_peak_private_bytes': 1}
            with (patch.object(budget, 'MEASUREMENT_PARENT', Path(temporary)),
                  patch.object(budget, '_source_pins', return_value={}),
                  patch.object(budget, '_runtime', return_value={'test': True}),
                  patch.object(budget.budget, 'system_snapshot', return_value=observation),
                  patch.object(budget.subprocess, 'CREATE_NO_WINDOW', 0, create=True),
                  patch.object(budget.subprocess, 'Popen', side_effect=OSError('launch denied'))):
                result = budget.run_measurement(receipt)
            self.assertEqual(result['status'], 'failed')
            self.assertIn('launch denied', result['reason'])
            self.assertTrue((receipt/'receipt.json').exists())
            self.assertFalse((receipt/'calculate-supervision.json').exists())

    def test_unreaped_owner_escapes_and_is_not_called_complete(self):
        class Handle:
            def Close(self):
                raise AssertionError('unreaped handle closed')
        class NeverReaped:
            pid = 123
            returncode = None
            _handle = Handle()
            kills = 0
            def poll(self):
                return None
            def kill(self):
                self.kills += 1
            def wait(self, timeout):
                raise subprocess.TimeoutExpired('child', timeout)
        fake = NeverReaped()
        with tempfile.TemporaryDirectory() as temporary:
            receipt = Path(temporary)
            with (patch.object(budget.subprocess, 'Popen', return_value=fake),
                  patch.object(budget.subprocess, 'CREATE_NO_WINDOW', 0, create=True),
                  patch.object(budget.resources, 'memory_bytes', return_value={'peak_private_bytes': 1}),
                  patch.object(budget.budget, 'system_snapshot', return_value={}),
                  patch.object(budget, '_check_resources', return_value='simulated_stop')):
                with self.assertRaises(budget.UnreapedMeasurement) as caught:
                    budget._supervise('calculate', receipt, {'bytes': 1, 'sha256': '0'*64})
        self.assertIs(caught.exception.process, fake)
        self.assertEqual(fake.kills, 3)

    def test_unreaped_receipt_and_owner_recovery(self):
        class Handle:
            def Close(self):
                pass
        class EventuallyReaped:
            pid = 456
            returncode = None
            _handle = Handle()
            def kill(self):
                pass
            def wait(self, timeout):
                self.returncode = -9
            def poll(self):
                return self.returncode
        owner = EventuallyReaped()
        failure = budget.UnreapedMeasurement(owner, 'calculate', {'stop_reason': 'test'})
        with tempfile.TemporaryDirectory() as temporary:
            receipt = Path(temporary)/'anomaly-v03-preformal-draw-budget-unreaped'
            observation = {'commit_headroom_bytes': budget.MINIMUM_HEADROOM+1,
                           'free_ram_bytes': budget.MINIMUM_HEADROOM+1,
                           'free_disk_bytes': budget.MINIMUM_DISK+1,
                           'parent_peak_private_bytes': 1}
            with (patch.object(budget, 'MEASUREMENT_PARENT', Path(temporary)),
                  patch.object(budget, '_source_pins', return_value={}),
                  patch.object(budget, '_runtime', return_value={'test': True}),
                  patch.object(budget.budget, 'system_snapshot', return_value=observation),
                  patch.object(budget, '_supervise', side_effect=failure)):
                with self.assertRaises(budget.UnreapedMeasurement) as caught:
                    budget.run_measurement(receipt)
            self.assertIs(caught.exception.process, owner)
            saved = json.loads((receipt/'receipt.json').read_text())
            self.assertEqual(saved['status'], 'failed')
            self.assertFalse(saved['worker_exit_confirmed'])
            budget.retain_unreaped_owner(caught.exception)
            recovery = json.loads((receipt/'owner-recovery.json').read_text())
            self.assertTrue(recovery['worker_exit_confirmed'])
            self.assertEqual(recovery['measurement_status'], 'failed')
            self.assertEqual(recovery['failed_receipt_pin'],
                             budget._pin_file(receipt/'receipt.json'))

    def test_unreaped_owner_survives_receipt_write_failure(self):
        class Owner:
            returncode = None
        failure = budget.UnreapedMeasurement(Owner(), 'calculate', {})
        with tempfile.TemporaryDirectory() as temporary:
            receipt = Path(temporary)/'anomaly-v03-preformal-draw-budget-receipt-failure'
            observation = {'commit_headroom_bytes': budget.MINIMUM_HEADROOM+1,
                           'free_ram_bytes': budget.MINIMUM_HEADROOM+1,
                           'free_disk_bytes': budget.MINIMUM_DISK+1,
                           'parent_peak_private_bytes': 1}
            real_write = budget._write
            def fail_receipt(path, raw):
                if Path(path).name == 'receipt.json':
                    raise OSError('receipt denied')
                return real_write(path, raw)
            with (patch.object(budget, 'MEASUREMENT_PARENT', Path(temporary)),
                  patch.object(budget, '_source_pins', return_value={}),
                  patch.object(budget, '_runtime', return_value={'test': True}),
                  patch.object(budget.budget, 'system_snapshot', return_value=observation),
                  patch.object(budget, '_supervise', side_effect=failure),
                  patch.object(budget, '_write', side_effect=fail_receipt)):
                with self.assertRaises(budget.UnreapedMeasurement) as caught:
                    budget.run_measurement(receipt)
            self.assertIs(caught.exception.process, failure.process)
            self.assertIsInstance(caught.exception.receipt_error, OSError)

    def test_saved_pin_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            receipt = Path(temporary)
            target = receipt/'input.json'
            target.write_bytes(b'one')
            pin = budget._pin_file(target)
            target.write_bytes(b'two')
            with self.assertRaisesRegex(ValueError, 'pin differs'):
                budget._final_pins(receipt, {'input.json': pin})

    def test_external_parent_rejected_before_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            receipt = Path(temporary)/'anomaly-v03-preformal-draw-budget-outside'
            with self.assertRaisesRegex(ValueError, 'parent differs'):
                budget.run_measurement(receipt)
            self.assertFalse(receipt.exists())


if __name__ == '__main__':
    unittest.main()
