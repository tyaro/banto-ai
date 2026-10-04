"""Direct Git preflight is bound to, but cannot promote, the five-role Job."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_preformal_five_role_git_anchor as anchor


class FiveRoleGitAnchorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        found = shutil.which('git.exe' if os.name == 'nt' else 'git')
        if found is None:
            raise unittest.SkipTest('Git unavailable')
        cls.executable = Path(found).resolve()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='banto-git-anchor-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / 'repo'
        self.root.mkdir()
        self._git('init', '-q', str(self.root), cwd=self.root.parent)
        self._git('-C', str(self.root), 'config', 'core.autocrlf', 'false')
        (self.root / '.gitignore').write_text('artifacts/\n', encoding='utf-8')
        (self.root / 'tracked.txt').write_text('clean\n', encoding='utf-8')
        self._git('-C', str(self.root), 'add', '.gitignore', 'tracked.txt')
        self._git('-C', str(self.root), '-c', 'user.name=Fixture',
                  '-c', 'user.email=fixture@example.invalid',
                  'commit', '-q', '-m', 'fixture')
        self.revision = self._git('-C', str(self.root),
                                  'rev-parse', 'HEAD').decode().strip()
        self.artifacts = self.root / 'artifacts'
        self.artifacts.mkdir()
        self.parent = self.artifacts / 'git-anchor'
        self.join = self.artifacts / 'invented-join'
        self.join.mkdir()
        self.join_pin = anchor.observed._pin(b'join-fixture')
        environment = dict(anchor.owned_git.FIXED_ENV)
        environment['PATH'] = str(self.executable.parent)
        if os.name == 'nt':
            for name in ('SystemRoot', 'WINDIR', 'TEMP', 'TMP'):
                if name in os.environ:
                    environment[name] = os.environ[name]
        self.policy = {
            'executable_path': str(self.executable),
            'executable_pin': anchor.owned_git.dependencies.file_observation(
                self.executable, native=True,
                maximum=anchor.owned_git.MAX_EXE)['pin'],
            'executable_links': self.executable.stat().st_nlink,
            'revision': self.revision,
            'environment': environment}
        self.policy_path = self.artifacts / 'policy.json'
        self._save_policy()

    def _git(self, *args, cwd=None):
        return subprocess.check_output([str(self.executable), *args],
                                       cwd=cwd, stderr=subprocess.DEVNULL,
                                       timeout=10)

    def _save_policy(self):
        raw = anchor.io.json_bytes(self.policy)
        self.policy_path.write_bytes(raw)
        self.policy_pin = anchor.observed._pin(raw)

    def _run(self, name='trial'):
        with patch.object(anchor, 'ROOT', self.root):
            return anchor.run_anchored(
                expected_mode='fixture', join_root=self.join,
                expected_join_receipt_pin=self.join_pin,
                expected_revision=self.revision,
                receipt_parent=self.parent, receipt_name=name,
                git_policy_path=self.policy_path,
                expected_git_policy_pin=self.policy_pin)

    def _verify(self, result, name='trial'):
        with patch.object(anchor, 'ROOT', self.root):
            return anchor.verify_retained(self.parent / name,
                                          result['receipt_pin'])

    def _owner_result(self, status):
        def fake_owner(**kwargs):
            root = Path(kwargs['receipt_parent']) / kwargs['receipt_name']
            root.mkdir()
            receipt = {'status': status, 'formal_permission': False,
                       'source_revision': kwargs['expected_revision'],
                       'join_root': str(kwargs['join_root']),
                       'join_receipt_pin': kwargs['expected_join_receipt_pin'],
                       'candidate_set_pin':
                       kwargs['expected_candidate_set_pin']}
            raw = anchor.io.json_bytes(receipt)
            (root / 'receipt.json').write_bytes(raw)
            return {'status': status, 'receipt_pin': anchor.observed._pin(raw),
                    'check_directory': str(root)}
        return fake_owner

    @staticmethod
    def _verified_owner(*args, **kwargs):
        return {'status': 'verified_retained',
                'receipt_pin': args[1] if len(args) >= 2 else None,
                'formal_permission': False,
                'source_closure_complete': False,
                'runtime_closure_complete': False}

    def test_real_head_status_bind_owner_and_reopen_without_rerun(self):
        with patch.object(anchor.owner, 'run_owned',
                          side_effect=self._owner_result('verified')) as run, \
             patch.object(anchor.owner, 'verify_retained',
                          side_effect=self._verified_owner) as verify:
            result = self._run()
            self.assertEqual(result['status'], 'verified',
                             (result['reason'],
                              (self.parent / 'trial' / 'git' / 'status' /
                               'stdout.bin').read_bytes()))
            self.assertEqual(result['git_head_status'], 'verified')
            self.assertEqual(result['git_status_status'], 'verified')
            self.assertTrue(result['integration_pending'])
            self.assertFalse(result['formal_permission'])
            self.assertFalse(result['source_closure_complete'])
            self.assertFalse(result['runtime_closure_complete'])
            self.assertEqual(run.call_count, 1)
            with patch.object(anchor.owned_git, 'run_owned',
                              side_effect=AssertionError('Git relaunched')):
                retained = self._verify(result)
            self.assertEqual(retained['call_status'], 'verified')
            self.assertEqual(verify.call_count, 2)

    def test_fake_git_path_stops_before_owner(self):
        fake = self.artifacts / 'fake'
        fake.mkdir()
        binary = fake / ('git.exe' if os.name == 'nt' else 'git')
        binary.write_bytes(b'not the pinned Git\n')
        if os.name != 'nt':
            binary.chmod(0o700)
        self.policy['environment']['PATH'] = os.pathsep.join(
            (str(fake), str(self.executable.parent)))
        self._save_policy()
        with patch.object(anchor.owner, 'run_owned') as run:
            result = self._run()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'git_anchor_rejected')
        self.assertIsNone(result['git_head_receipt_pin'])
        run.assert_not_called()
        self.assertEqual(self._verify(result)['call_status'], 'failed')

    def test_dirty_status_stops_before_owner_and_keeps_both_git_pins(self):
        (self.root / 'tracked.txt').write_text('dirty\n', encoding='utf-8')
        with patch.object(anchor.owner, 'run_owned') as run:
            result = self._run()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'status_rejected')
        self.assertEqual(result['git_head_status'], 'verified')
        self.assertEqual(result['git_status_status'], 'failed')
        self.assertIsNotNone(result['git_head_receipt_pin'])
        self.assertIsNotNone(result['git_status_receipt_pin'])
        run.assert_not_called()
        self.assertEqual(self._verify(result)['call_status'], 'failed')

    def test_failed_owner_receipt_is_pinned_without_success_claim(self):
        with patch.object(anchor.owner, 'run_owned',
                          side_effect=self._owner_result('failed')), \
             patch.object(anchor.owner, 'verify_retained') as verify:
            result = self._run()
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(result['reason'], 'owner_failed')
            self.assertEqual(result['owner_status'], 'failed')
            self.assertIsNotNone(result['owner_receipt_pin'])
            self.assertEqual(self._verify(result)['call_status'], 'failed')
            verify.assert_not_called()

    def test_owner_verifier_must_return_closed_verified_scope(self):
        with patch.object(anchor.owner, 'run_owned',
                          side_effect=self._owner_result('verified')):
            def invalid(status=False, scope=False, pin=False):
                def verify(root, expected_pin):
                    answer = self._verified_owner(root, expected_pin)
                    if status:
                        answer['status'] = 'failed'
                    if scope:
                        answer['formal_permission'] = True
                    if pin:
                        answer['receipt_pin'] = self.join_pin
                    return answer
                return verify
            for name, verifier in (
                    ('bad-status', invalid(status=True)),
                    ('bad-scope', invalid(scope=True)),
                    ('bad-pin', invalid(pin=True))):
                with self.subTest(name=name), \
                     patch.object(anchor.owner, 'verify_retained',
                                  side_effect=verifier):
                    result = self._run(name)
                    self.assertEqual(result['status'], 'failed')
                    self.assertEqual(result['reason'], 'git_anchor_rejected')
                    self.assertEqual(result['owner_status'], 'verified')
                    self.assertIsNotNone(result['owner_receipt_pin'])
                    self.assertFalse(result['formal_permission'])

    def test_unreaped_owner_raises_same_handle_and_retains_failed_outer(self):
        process = object()
        error = anchor.owner.job_owner.UnreapedJob(
            object(), process, object(), {'formal_permission': False})
        with patch.object(anchor.owner, 'run_owned', side_effect=error):
            with self.assertRaises(anchor.owner.job_owner.UnreapedJob) as raised:
                self._run()
        self.assertIs(raised.exception, error)
        self.assertIs(raised.exception.process, process)
        target = self.parent / 'trial'
        raw = (target / 'receipt.json').read_bytes()
        self.assertEqual(anchor.v.strict_json(raw)['reason'],
                         'process_reconciliation_required')
        self.assertEqual(self._verify({'receipt_pin': anchor.observed._pin(raw)})[
            'call_status'], 'failed')

    def test_saved_policy_git_or_owner_pin_tamper_is_rejected(self):
        with patch.object(anchor.owner, 'run_owned',
                          side_effect=self._owner_result('verified')), \
             patch.object(anchor.owner, 'verify_retained',
                          side_effect=self._verified_owner):
            result = self._run()
            head_output = self.parent / 'trial' / 'git' / 'head' / 'stdout.bin'
            original = head_output.read_bytes()
            head_output.write_bytes(b'changed\n')
            with self.assertRaises(ValueError):
                self._verify(result)
            head_output.write_bytes(original)
            policy_raw = self.policy_path.read_bytes()
            self.policy_path.write_bytes(b'{}\n')
            with self.assertRaises(ValueError):
                self._verify(result)
            self.policy_path.write_bytes(policy_raw)
            owner_receipt = self.parent / 'trial' / 'attempt' / 'receipt.json'
            owner_receipt.write_bytes(b'{}\n')
            with self.assertRaises(ValueError):
                self._verify(result)

    def test_root_reuse_stops_before_git_or_owner(self):
        with patch.object(anchor.owner, 'run_owned',
                          side_effect=self._owner_result('verified')), \
             patch.object(anchor.owner, 'verify_retained',
                          side_effect=self._verified_owner):
            self._run()
        with patch.object(anchor.owned_git, 'run_owned') as git, \
             patch.object(anchor.owner, 'run_owned') as owner_run:
            with self.assertRaises(FileExistsError):
                self._run()
        git.assert_not_called()
        owner_run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
