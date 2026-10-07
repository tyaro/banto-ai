"""Pinned parent Git identity, budget stops and saved-receipt substitution."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_preformal_parent_git_identity as parent
from banto_ai import anomaly_v03_preformal_generation_publication_budget as whole

REV = 'a' * 40


class Budget:
    def __init__(self):
        self.phases = []
        self.stop = None

    def checkpoint(self, phase):
        self.phases.append(phase)
        if self.stop:
            raise whole.monitor.resources.ResourceStop(self.stop)

    def probe(self):
        return self.stop


class ParentGitIdentityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name).resolve()
        self.artifacts = self.repo / 'artifacts'
        self.artifacts.mkdir()
        self.root = self.artifacts / 'outer'
        self.policy_path = self.artifacts / 'external/policy.json'
        self.policy_path.parent.mkdir()
        self.policy = {'revision': REV, 'process_ownership': parent.owned.JOB_OWNERSHIP}
        raw = parent.sessions.io.json_bytes(self.policy)
        self.policy_path.write_bytes(raw)
        self.policy_pin = parent.observed._pin(raw)
        self.entry = {'path': str(self.policy_path), 'expected_pin': self.policy_pin,
                      'policy': self.policy, 'revision': REV}
        self.budget, self.receipts = Budget(), {}

    def execute(self, **kw):
        self.assertEqual(kw['timeout_seconds'], 10)
        self.assertEqual(kw['stop_probe'], self.budget.probe)
        root = kw['receipt_root']
        root.mkdir()
        operation = kw['operation']
        raw = (REV + '\n').encode() if operation == 'head' else b''
        receipt = {'operation': operation, 'source_path': None, 'expected_output_pin': None,
                   'revision': REV, 'status': 'verified', 'formal_permission': False,
                   'stdout_pin': parent.observed._pin(raw),
                   'job': {'all_assigned_processes_exit_confirmed': True}}
        (root / 'stdout.bin').write_bytes(raw)
        (root / 'stderr.bin').write_bytes(b'')
        packed = parent.sessions.io.json_bytes(receipt)
        (root / 'receipt.json').write_bytes(packed)
        return {'receipt_root': str(root), 'receipt': receipt,
                'receipt_pin': parent.observed._pin(packed), 'stdout': raw}

    def check(self, phase='preflight'):
        return parent.check(self.entry, phase=phase, root=self.root,
                            checkout_root=self.repo, budget=self.budget, receipts=self.receipts)

    def patches(self):
        self.root.mkdir()
        return patch.multiple(parent.owned,
            run_owned=unittest.mock.DEFAULT, verify_retained=unittest.mock.DEFAULT)

    def test_four_calls_use_live_budget_and_fit_existing_outer_shape(self):
        with patch.object(parent.sessions, '_policy', return_value=self.policy), self.patches() as mocks:
            mocks['run_owned'].side_effect = self.execute
            mocks['verify_retained'].return_value = {'call_status': 'verified'}
            self.assertEqual(self.check()['head'], (REV + '\n').encode())
            self.check('postflight')
            parent.verify(self.entry, root=self.root, checkout_root=self.repo,
                          budget=self.budget, receipts=self.receipts)
        self.assertEqual(len(self.receipts), 4)
        self.assertEqual(len(list(self.root.rglob('*'))), 16)
        self.assertTrue(all(p.parent == self.root or p.parent.parent == self.root
                            for p in self.root.rglob('*')))
        self.assertLessEqual(len(list(self.root.rglob('*'))) + 4, whole.LEAF_LIMITS['outer'][1])

    def test_policy_raw_mismatch_rejects_without_measurement_roots(self):
        roots = {'outer': self.root, 'producer': self.artifacts / 'producer'}
        self.policy_path.write_bytes(b'{}')
        with patch.object(parent.sessions, 'ROOT', self.repo), patch.object(parent.owned, '_policy'), \
             self.assertRaisesRegex(ValueError, 'raw pin'):
            parent.validate({'path': str(self.policy_path), 'expected_pin': self.policy_pin},
                            revision=REV, roots=roots)
        self.assertFalse(self.root.exists())

    def test_direct_policy_and_policy_inside_roots_reject_before_start(self):
        with patch.object(parent.sessions, '_policy', return_value={'revision': REV}), \
             self.assertRaisesRegex(ValueError, 'private Job'):
            parent.validate({'path': str(self.policy_path), 'expected_pin': self.policy_pin},
                            revision=REV, roots={'outer': self.root})
        with self.assertRaisesRegex(ValueError, 'separate'):
            parent.validate({'path': str(self.root / 'policy.json'), 'expected_pin': self.policy_pin},
                            revision=REV, roots={'outer': self.root})
        self.assertFalse(self.root.exists())

    def test_latched_budget_stop_prevents_any_git(self):
        self.budget.stop = 'outer_time'
        with patch.object(parent.owned, 'run_owned') as execute, \
             self.assertRaises(whole.monitor.resources.ResourceStop):
            self.check()
        execute.assert_not_called()

    def test_stop_after_head_retains_pin_and_never_starts_status(self):
        def stop(**kw):
            result = self.execute(**kw)
            self.budget.stop = 'outer_time'
            return result
        with patch.object(parent.sessions, '_policy', return_value=self.policy), self.patches() as mocks:
            mocks['run_owned'].side_effect = stop
            with self.assertRaises(whole.monitor.resources.ResourceStop):
                self.check()
            self.assertEqual(mocks['run_owned'].call_count, 1)
        self.assertEqual(set(self.receipts), {'git-preflight-head'})

    def test_returned_receipt_or_stdout_cannot_substitute_saved_bytes(self):
        def changed(**kw):
            result = self.execute(**kw)
            result['receipt'] = copy.deepcopy(result['receipt'])
            result['receipt']['added'] = 'not on disk'
            return result
        with patch.object(parent.sessions, '_policy', return_value=self.policy), self.patches() as mocks:
            mocks['run_owned'].side_effect = changed
            mocks['verify_retained'].return_value = {'call_status': 'verified'}
            with self.assertRaisesRegex(ValueError, 'returned/saved'):
                self.check()
            self.assertEqual(mocks['run_owned'].call_count, 1)

    def test_unreaped_git_keeps_the_original_owner_and_stops_follow_on_calls(self):
        from banto_ai import anomaly_v03_preformal_job_tree_owner as owner
        original = owner.UnreapedJob(11, 22, 33, {'status': 'failed'})
        with patch.object(parent.sessions, '_policy', return_value=self.policy), self.patches() as mocks:
            mocks['run_owned'].side_effect = original
            with self.assertRaises(owner.UnreapedJob) as caught:
                self.check()
            self.assertIs(caught.exception, original)
            self.assertEqual(mocks['run_owned'].call_count, 1)
        self.assertFalse(self.receipts)

    def test_missing_or_modified_final_receipt_rejects(self):
        with patch.object(parent.sessions, '_policy', return_value=self.policy), self.patches() as mocks:
            mocks['run_owned'].side_effect = self.execute
            mocks['verify_retained'].return_value = {'call_status': 'verified'}
            self.check()
            with self.assertRaisesRegex(ValueError, 'four calls'):
                parent.verify(self.entry, root=self.root, checkout_root=self.repo,
                              budget=self.budget, receipts=self.receipts)
            self.check('postflight')
            (self.root / 'git-preflight-head/receipt.json').write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError, 'receipt pin'):
                parent.verify(self.entry, root=self.root, checkout_root=self.repo,
                              budget=self.budget, receipts=self.receipts)

    def test_owned_identity_replaces_only_head_status_at_actual_source_boundary(self):
        name, raw = 'src/example.py', b'example\n'
        path = self.repo / name
        path.parent.mkdir()
        path.write_bytes(raw)
        def git(argv, **kwargs):
            self.assertEqual(argv[3:], ['show', REV + ':' + name])
            return raw
        with patch.object(whole, 'ROOT', self.repo), patch.object(whole.document, 'ROOT', self.repo), \
             patch.object(whole, 'SOURCE_NAMES', (name,)), patch.object(whole.document, 'SOURCE_NAMES', (name,)), \
             patch.object(whole.generated.subprocess, 'check_output', side_effect=git) as bare:
            result = whole._source(REV, git_identity=lambda: {'head': (REV+'\n').encode(), 'status': b''})
        self.assertEqual(result, {name: parent.observed._pin(raw)})
        self.assertEqual(bare.call_count, 2)


if __name__ == '__main__':
    unittest.main()
