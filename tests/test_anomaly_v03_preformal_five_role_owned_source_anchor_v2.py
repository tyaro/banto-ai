"""The v2 wrapper binds seven direct Git calls to, but does not widen, v1."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_preformal_five_role_owned_source_anchor_v2 as anchor


class FiveRoleOwnedSourceAnchorV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        found = shutil.which('git.exe' if os.name == 'nt' else 'git')
        if found is None:
            raise unittest.SkipTest('Git unavailable')
        cls.executable = Path(found).resolve()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='banto-owned-source-v2-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / 'repo'
        self.root.mkdir()
        self._git('init', '-q', str(self.root), cwd=self.root.parent)
        self._git('-C', str(self.root), 'config', 'core.autocrlf', 'false')
        (self.root / '.gitignore').write_text('artifacts/\n', encoding='utf-8')
        self.sources = {}
        for index, name in enumerate((*anchor.chain.SOURCES,
                                      anchor.owner.SOURCE)):
            raw = f'fixture source {index}\n'.encode('ascii')
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            self.sources[name] = raw
        self._git('-C', str(self.root), 'add', '.')
        self._git('-C', str(self.root), '-c', 'user.name=Fixture',
                  '-c', 'user.email=fixture@example.invalid',
                  'commit', '-q', '-m', 'fixture')
        self.revision = self._git('-C', str(self.root),
                                  'rev-parse', 'HEAD').decode().strip()
        self.artifacts = self.root / 'artifacts'
        self.artifacts.mkdir()
        self.parent = self.artifacts / 'owned-source-v2'
        self.join = self.artifacts / 'invented-join'
        self.join.mkdir()
        self.join_pin = anchor.observed._pin(b'invented join fixture')
        environment = dict(anchor.source_git.owned_git.FIXED_ENV)
        environment['PATH'] = str(self.executable.parent)
        if os.name == 'nt':
            for name in ('SystemRoot', 'WINDIR', 'TEMP', 'TMP'):
                if name in os.environ:
                    environment[name] = os.environ[name]
        self.policy = {
            'executable_path': str(self.executable),
            'executable_pin':
                anchor.source_git.owned_git.dependencies.file_observation(
                    self.executable, native=True,
                    maximum=anchor.source_git.owned_git.MAX_EXE)['pin'],
            'executable_links': self.executable.stat().st_nlink,
            'revision': self.revision, 'environment': environment}
        policy_dir = self.artifacts / 'external-policy'
        policy_dir.mkdir()
        self.policy_path = policy_dir / 'policy.json'
        self._save_policy()

    def _git(self, *args, cwd=None):
        return subprocess.check_output([str(self.executable), *args],
                                       cwd=cwd, stderr=subprocess.DEVNULL,
                                       timeout=10)

    def _save_policy(self):
        raw = anchor.io.json_bytes(self.policy)
        self.policy_path.write_bytes(raw)
        self.policy_pin = anchor.observed._pin(raw)

    def _source(self):
        return {'revision': self.revision,
                'orchestrator_selected': {
                    name: anchor.observed._pin(self.sources[name])
                    for name in anchor.chain.SOURCES},
                'owner': anchor.observed._pin(
                    self.sources[anchor.owner.SOURCE]),
                'scope': 'clean-head-selected-working-raw-not-source-closure'}

    def _fake_owner(self, status, *, invocation_path_override=None):
        def run(**kwargs):
            root = Path(kwargs['receipt_parent']) / kwargs['receipt_name']
            root.mkdir()
            receipt = {
                'format': anchor.owner.FORMAT, 'mode': 'fixture',
                'status': status, 'formal_permission': False,
                'source_revision': kwargs['expected_revision'],
                'join_root': str(kwargs['join_root']),
                'join_receipt_pin': kwargs['expected_join_receipt_pin'],
                'candidate_set_pin': kwargs['expected_candidate_set_pin'],
                'source_pins': self._source(),
            }
            if status == 'verified':
                invocation = {
                    'source_revision': kwargs['expected_revision'],
                    'join_root': str(kwargs['join_root']),
                    'join_receipt_pin': kwargs['expected_join_receipt_pin'],
                    'candidate_set_path': (
                        str(invocation_path_override)
                        if invocation_path_override is not None else
                        None if kwargs['candidate_set_path'] is None else
                        str(kwargs['candidate_set_path'])),
                    'candidate_set_pin': kwargs['expected_candidate_set_pin'],
                }
                invocation_raw = anchor.io.json_bytes(invocation)
                (root / 'invocation.json').write_bytes(invocation_raw)
                receipt['invocation_pin'] = anchor.observed._pin(invocation_raw)
            raw = anchor.io.json_bytes(receipt)
            (root / 'receipt.json').write_bytes(raw)
            return {'status': status, 'receipt_pin': anchor.observed._pin(raw),
                    'check_directory': str(root)}
        return run

    @staticmethod
    def _verified_owner(root, pin):
        return {'status': 'verified_retained', 'receipt_pin': pin,
                'formal_permission': False,
                'source_closure_complete': False,
                'runtime_closure_complete': False}

    def _patch_roots(self):
        return (patch.object(anchor, 'ROOT', self.root),
                patch.object(anchor.source_git, 'ROOT', self.root),
                patch.object(anchor.owner, 'ROOT', self.root),
                patch.object(anchor.chain, 'ROOT', self.root))

    def _run(self, name='trial'):
        roots = self._patch_roots()
        with roots[0], roots[1], roots[2], roots[3]:
            return anchor.run_anchored(
                expected_mode='fixture', join_root=self.join,
                expected_join_receipt_pin=self.join_pin,
                expected_revision=self.revision,
                receipt_parent=self.parent, receipt_name=name,
                git_policy_path=self.policy_path,
                expected_git_policy_pin=self.policy_pin)

    def _verify(self, result, name='trial'):
        roots = self._patch_roots()
        with roots[0], roots[1], roots[2], roots[3]:
            return anchor.verify_retained(self.parent / name,
                                          result['receipt_pin'])

    def test_real_seven_calls_bind_owner_and_reopen_without_git_rerun(self):
        with patch.object(anchor.owner, 'run_owned',
                          side_effect=self._fake_owner('verified')) as run, \
             patch.object(anchor.owner, 'verify_retained',
                          side_effect=self._verified_owner) as verify:
            result = self._run()
            self.assertEqual(result['status'], 'verified', result)
            self.assertEqual(result['source_git_call_count'], 7)
            self.assertEqual(result['source_git_status'], 'verified')
            self.assertEqual(result['owner_status'], 'verified')
            self.assertFalse(result['inner_v1_git_owned'])
            self.assertFalse(result['formal_permission'])
            self.assertFalse(result['source_closure_complete'])
            self.assertEqual(run.call_count, 1)
            manifest = anchor.v.strict_json((
                self.parent / 'trial' / 'git' / 'manifest.json').read_bytes())
            self.assertEqual([row['call_id'] for row in manifest['calls']],
                             ['head', 'status', 'selected-source-0',
                              'selected-source-1', 'selected-source-2',
                              'selected-source-3', 'owner-source'])
            with patch.object(anchor.source_git.owned_git, 'run_owned',
                              side_effect=AssertionError('Git restarted')):
                retained = self._verify(result)
            self.assertEqual(retained['call_status'], 'verified')
            self.assertEqual(retained['source_git_call_count'], 7)
            self.assertEqual(verify.call_count, 2)

    def test_dirty_status_stops_before_owner_with_failed_manifest(self):
        (self.root / 'src' / 'dirty.txt').write_text('dirty\n', encoding='utf-8')
        with patch.object(anchor.owner, 'run_owned') as run:
            result = self._run()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'source_preflight_rejected')
        self.assertEqual(result['source_git_status'], 'failed')
        self.assertEqual(result['source_git_call_count'], 2)
        self.assertIsNone(result['owner_receipt_pin'])
        run.assert_not_called()
        self.assertEqual(self._verify(result)['call_status'], 'failed')

    def test_wrong_source_blob_stops_before_owner(self):
        actual = anchor.source_git.owned_git.run_owned

        def wrong_adapter(**kwargs):
            checked = actual(**kwargs)
            if kwargs['source_path'] == anchor.chain.SOURCES[1]:
                return {**checked, 'stdout': b'wrong blob\n'}
            return checked

        with patch.object(anchor.owner, 'run_owned') as run, \
             patch.object(anchor.source_git.owned_git, 'run_owned',
                          side_effect=wrong_adapter):
            result = self._run()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['source_git_status'], 'failed')
        self.assertEqual(result['source_git_call_count'], 4)
        run.assert_not_called()
        self.assertEqual(self._verify(result)['call_status'], 'failed')

    def test_wrong_git_path_retains_outer_failure_without_session(self):
        fake = self.artifacts / 'fake'
        fake.mkdir()
        binary = fake / ('git.exe' if os.name == 'nt' else 'git')
        binary.write_bytes(b'wrong program\n')
        if os.name != 'nt':
            binary.chmod(0o700)
        self.policy['environment']['PATH'] = os.pathsep.join(
            (str(fake), str(self.executable.parent)))
        self._save_policy()
        with patch.object(anchor.owner, 'run_owned') as run:
            result = self._run()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'source_preflight_rejected')
        self.assertIsNone(result['source_git_manifest_pin'])
        run.assert_not_called()
        self.assertEqual(self._verify(result)['call_status'], 'failed')

    def test_failed_owner_receipt_is_pinned_without_success_claim(self):
        with patch.object(anchor.owner, 'run_owned',
                          side_effect=self._fake_owner('failed')), \
             patch.object(anchor.owner, 'verify_retained') as verify:
            result = self._run()
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(result['reason'], 'owner_failed')
            self.assertEqual(result['source_git_status'], 'verified')
            self.assertEqual(result['owner_status'], 'failed')
            self.assertIsNotNone(result['owner_receipt_pin'])
            self.assertEqual(self._verify(result)['call_status'], 'failed')
            verify.assert_not_called()

    def test_wrong_inner_candidate_path_rejects_outer_success(self):
        candidate_path = self.artifacts / 'candidate-set.json'
        candidate_pin = anchor.observed._pin(b'candidate fixture')
        with patch.object(anchor.owner, 'run_owned', side_effect=
                          self._fake_owner('verified', invocation_path_override=
                                           self.artifacts / 'wrong-set.json')), \
             patch.object(anchor.owner, 'verify_retained') as verify:
            roots = self._patch_roots()
            with roots[0], roots[1], roots[2], roots[3]:
                result = anchor.run_anchored(
                    expected_mode='fixture', join_root=self.join,
                    expected_join_receipt_pin=self.join_pin,
                    expected_revision=self.revision,
                    receipt_parent=self.parent, receipt_name='wrong-path',
                    git_policy_path=self.policy_path,
                    expected_git_policy_pin=self.policy_pin,
                    candidate_set_path=candidate_path,
                    expected_candidate_set_pin=candidate_pin)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'owner_rejected')
        self.assertEqual(result['owner_status'], 'verified')
        verify.assert_not_called()

    def test_owner_verifier_cannot_promote_scope(self):
        with patch.object(anchor.owner, 'run_owned',
                          side_effect=self._fake_owner('verified')), \
             patch.object(anchor.owner, 'verify_retained',
                          return_value={
                              'status': 'verified_retained',
                              'receipt_pin': self.join_pin,
                              'formal_permission': True,
                              'source_closure_complete': False,
                              'runtime_closure_complete': False}):
            result = self._run()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'owner_rejected')
        self.assertEqual(result['owner_status'], 'verified')
        self.assertFalse(result['formal_permission'])
        self.assertEqual(self._verify(result)['call_status'], 'failed')

    def test_unreaped_git_rethrows_same_handle_and_saves_failure(self):
        process = object()
        error = anchor.source_git.owned_git.UnreapedGit(
            process, 'fixture unreaped')
        with patch.object(anchor.owner, 'run_owned') as run, \
             patch.object(anchor.source_git.owned_git, 'run_owned',
                          side_effect=error):
            with self.assertRaises(anchor.source_git.owned_git.UnreapedGit) as raised:
                self._run()
        self.assertIs(raised.exception, error)
        self.assertIs(raised.exception.process, process)
        run.assert_not_called()
        raw = (self.parent / 'trial' / 'receipt.json').read_bytes()
        saved = anchor.v.strict_json(raw)
        self.assertEqual(saved['reason'], 'process_reconciliation_required')
        self.assertEqual(saved['source_git_status'], 'failed')
        self.assertEqual(self._verify({'receipt_pin': anchor.observed._pin(raw)})[
            'call_status'], 'failed')

    def test_saved_manifest_policy_or_inner_receipt_tamper_is_rejected(self):
        with patch.object(anchor.owner, 'run_owned',
                          side_effect=self._fake_owner('verified')), \
             patch.object(anchor.owner, 'verify_retained',
                          side_effect=self._verified_owner):
            result = self._run()
            manifest_path = self.parent / 'trial' / 'git' / 'manifest.json'
            original = manifest_path.read_bytes()
            manifest_path.write_bytes(b'{}\n')
            with self.assertRaises(ValueError):
                self._verify(result)
            manifest_path.write_bytes(original)
            policy_raw = self.policy_path.read_bytes()
            self.policy_path.write_bytes(b'{}\n')
            with self.assertRaises(ValueError):
                self._verify(result)
            self.policy_path.write_bytes(policy_raw)
            owner_path = self.parent / 'trial' / 'attempt' / 'receipt.json'
            owner_path.write_bytes(b'{}\n')
            with self.assertRaises(ValueError):
                self._verify(result)

    def test_root_reuse_stops_before_git_and_owner(self):
        with patch.object(anchor.owner, 'run_owned',
                          side_effect=self._fake_owner('verified')), \
             patch.object(anchor.owner, 'verify_retained',
                          side_effect=self._verified_owner):
            self._run()
        with patch.object(anchor.source_git.owned_git, 'run_owned') as git, \
             patch.object(anchor.owner, 'run_owned') as run:
            with self.assertRaises(FileExistsError):
                self._run()
        git.assert_not_called()
        run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
