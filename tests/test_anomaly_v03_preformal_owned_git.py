"""The unintegrated Git helper rejects PATH changes and owned call failures."""
from __future__ import annotations

import copy
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_preformal_owned_git as owned


ROOT = Path(__file__).resolve().parents[1]


class OwnedGitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        command = 'git.exe' if os.name == 'nt' else 'git'
        found = shutil.which(command)
        if found is None:
            raise unittest.SkipTest('Git unavailable')
        cls.executable = Path(found).resolve()
        cls.revision = subprocess.check_output(
            [str(cls.executable), '-C', str(ROOT), 'rev-parse', 'HEAD'],
            stderr=subprocess.DEVNULL, timeout=10).decode().strip()
        cls.exe_pin = owned.dependencies.file_observation(
            cls.executable, native=True, maximum=owned.MAX_EXE)['pin']

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='banto-owned-git-')
        self.addCleanup(temporary.cleanup)
        self.target = Path(temporary.name).resolve()
        environment = dict(owned.FIXED_ENV)
        environment['PATH'] = str(self.executable.parent)
        if os.name == 'nt':
            for name in ('SystemRoot', 'WINDIR', 'TEMP', 'TMP'):
                if name in os.environ:
                    environment[name] = os.environ[name]
        self.policy = {'executable_path': str(self.executable),
                       'executable_pin': self.exe_pin,
                       'executable_links': self.executable.stat().st_nlink,
                       'revision': self.revision,
                       'environment': environment}

    def _fake_policy(self, name):
        directory = self.target / name
        directory.mkdir()
        executable = directory / ('git.exe' if os.name == 'nt' else 'git')
        executable.write_bytes(b'original fake git\n')
        if os.name != 'nt':
            executable.chmod(0o700)
        policy = {**self.policy,
                  'executable_path': str(executable),
                  'executable_links': executable.stat().st_nlink,
                  'executable_pin': owned.dependencies.file_observation(
                      executable, native=True, maximum=owned.MAX_EXE)['pin'],
                  'environment': {**self.policy['environment'],
                                  'PATH': str(directory)}}
        return executable, policy

    def test_owned_head_roundtrip_retains_direct_handle_facts(self):
        receipt_root = self.target / 'head'
        result = owned.run_owned(root=ROOT, policy=self.policy,
                                 operation='head', receipt_root=receipt_root)
        receipt = result['receipt']
        self.assertEqual(receipt['status'], 'verified',
                         (receipt['reason'],
                          (receipt_root / 'stderr.bin').read_bytes()))
        self.assertEqual(result['stdout'].strip().decode(), self.revision)
        self.assertEqual(receipt['exit_code'], 0)
        self.assertTrue(receipt['direct_process_handle_exit_confirmed'])
        self.assertGreater(receipt['process_identity']['pid'], 0)
        self.assertEqual(receipt['executable_before'],
                         receipt['executable_after'])
        self.assertTrue(receipt['integration_pending'])
        for key in ('formal_permission', 'source_closure_complete',
                    'runtime_closure_complete', 'execution_authenticated'):
            self.assertFalse(receipt[key])
        retained = owned.verify_retained(receipt_root, result['receipt_pin'],
                                         root=ROOT, policy=self.policy)
        self.assertEqual(retained['call_status'], 'verified')
        (receipt_root / 'stdout.bin').write_bytes(b'wrong\n')
        with self.assertRaises(ValueError):
            owned.verify_retained(receipt_root, result['receipt_pin'],
                                  root=ROOT, policy=self.policy)

    def test_fake_git_first_in_path_stops_before_spawn(self):
        fake_dir = self.target / 'fake'
        fake_dir.mkdir()
        fake = fake_dir / ('git.exe' if os.name == 'nt' else 'git')
        fake.write_bytes(b'fake git executable\n')
        if os.name != 'nt':
            fake.chmod(0o700)
        self.policy['environment']['PATH'] = os.pathsep.join(
            (str(fake_dir), str(self.executable.parent)))
        receipt_root = self.target / 'injected'
        with self.assertRaises(ValueError):
            owned.run_owned(root=ROOT, policy=self.policy, operation='head',
                            receipt_root=receipt_root)
        self.assertFalse(receipt_root.exists())

    def test_nonzero_git_is_failed_but_reaped_and_retained(self):
        receipt_root = self.target / 'missing'
        result = owned.run_owned(
            root=ROOT, policy=self.policy, operation='source_blob',
            source_path='src/banto_ai/__missing_owned_git_fixture__.py',
            expected_output_pin={'bytes': 0,
                                 'sha256': hashlib.sha256(b'').hexdigest()},
            receipt_root=receipt_root)
        receipt = result['receipt']
        self.assertEqual(receipt['status'], 'failed')
        self.assertEqual(receipt['reason'], 'exit_nonzero')
        self.assertNotEqual(receipt['exit_code'], 0)
        self.assertTrue(receipt['direct_process_handle_exit_confirmed'])
        self.assertGreater(receipt['stderr_bytes'], 0)
        self.assertEqual(owned.verify_retained(
            receipt_root, result['receipt_pin'], root=ROOT,
            policy=self.policy)['call_status'], 'failed')

    def test_unknown_command_and_unpinned_blob_stop_before_spawn(self):
        with self.assertRaises(ValueError):
            owned.run_owned(root=ROOT, policy=self.policy,
                            operation='config', receipt_root=self.target / 'bad')
        self.assertFalse((self.target / 'bad').exists())
        with self.assertRaises(ValueError):
            owned.run_owned(root=ROOT, policy=self.policy,
                            operation='source_blob', source_path='src/x.py',
                            receipt_root=self.target / 'unbound')
        self.assertFalse((self.target / 'unbound').exists())

    def test_executable_changed_during_owned_call_saves_failed_receipt(self):
        executable, policy = self._fake_policy('trusted')
        receipt_root = self.target / 'changed'

        class Reaped:
            pid = 12345

            def poll(self):
                return 0

            def wait(self, timeout):
                return 0

        def mutate(*args, **kwargs):
            executable.write_bytes(b'mutated fake git\n')
            return Reaped()

        with patch.object(owned.subprocess, 'Popen', side_effect=mutate), \
             patch.object(owned, '_identity', return_value={
                 'pid': 12345, 'start_token': 'test',
                 'native_start_identity_authenticated': False}):
            result = owned.run_owned(root=ROOT, policy=policy,
                                     operation='head', receipt_root=receipt_root)
        receipt = result['receipt']
        self.assertEqual(receipt['status'], 'failed')
        self.assertEqual(receipt['reason'], 'executable_changed')
        self.assertNotEqual(receipt['executable_before'],
                            receipt['executable_after'])
        self.assertEqual(owned.verify_retained(
            receipt_root, result['receipt_pin'], root=ROOT,
            policy=policy)['call_status'], 'failed')

    def test_executable_removed_during_owned_call_saves_failed_receipt(self):
        executable, policy = self._fake_policy('removed-trusted')
        receipt_root = self.target / 'removed'

        class Reaped:
            pid = 12346

            def poll(self):
                return 0

            def wait(self, timeout):
                return 0

        def remove(*args, **kwargs):
            executable.unlink()
            return Reaped()

        with patch.object(owned.subprocess, 'Popen', side_effect=remove), \
             patch.object(owned, '_identity', return_value={
                 'pid': 12346, 'start_token': 'test',
                 'native_start_identity_authenticated': False}):
            result = owned.run_owned(root=ROOT, policy=policy,
                                     operation='head', receipt_root=receipt_root)
        receipt = result['receipt']
        self.assertEqual(receipt['status'], 'failed')
        self.assertEqual(receipt['reason'], 'executable_after_unavailable')
        self.assertIn('observation_error_type', receipt['executable_after'])
        self.assertEqual(owned.verify_retained(
            receipt_root, result['receipt_pin'], root=ROOT,
            policy=policy)['call_status'], 'failed')

    def test_kill_failure_preserves_live_process_handle(self):
        _, policy = self._fake_policy('unreaped-trusted')
        receipt_root = self.target / 'unreaped'

        class Live:
            pid = 12347
            kill_calls = 0

            def poll(self):
                return None

            def kill(self):
                self.kill_calls += 1
                raise OSError('fixture denied kill')

        process = Live()
        with patch.object(owned.subprocess, 'Popen', return_value=process), \
             patch.object(owned, '_identity', return_value={
                 'pid': process.pid, 'start_token': 'test',
                 'native_start_identity_authenticated': False}):
            with self.assertRaises(owned.UnreapedGit) as raised:
                owned.run_owned(root=ROOT, policy=policy, operation='head',
                                receipt_root=receipt_root,
                                timeout_seconds=0.001)
        self.assertIs(raised.exception.process, process)
        self.assertEqual(process.kill_calls, 1)
        self.assertFalse((receipt_root / 'receipt.json').exists())

    def test_repinning_bad_saved_start_identity_cannot_make_success(self):
        receipt_root = self.target / 'identity'
        result = owned.run_owned(root=ROOT, policy=self.policy,
                                 operation='head', receipt_root=receipt_root)
        receipt_path = receipt_root / 'receipt.json'
        original = result['receipt']
        variants = []
        if os.name == 'nt':
            bad_token = copy.deepcopy(original)
            bad_token['process_identity']['start_token'] = 'a' * 64
            variants.append(bad_token)
            bad_token_type = copy.deepcopy(original)
            bad_token_type['process_identity']['start_token'] = 7
            variants.append(bad_token_type)
            bad_native = copy.deepcopy(original)
            bad_native['process_identity'][
                'native_start_identity_authenticated'] = False
            variants.append(bad_native)
        else:
            bad_token = copy.deepcopy(original)
            bad_token['process_identity']['start_token'] = 'forged'
            variants.append(bad_token)
            bad_native = copy.deepcopy(original)
            bad_native['process_identity'][
                'native_start_identity_authenticated'] = True
            variants.append(bad_native)
        for altered in variants:
            raw = owned.io.json_bytes(altered)
            receipt_path.write_bytes(raw)
            with self.assertRaises(ValueError):
                owned.verify_retained(receipt_root, owned.observed._pin(raw),
                                      root=ROOT, policy=self.policy)


if __name__ == '__main__':
    unittest.main()
