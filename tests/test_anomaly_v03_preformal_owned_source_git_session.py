"""Owned source Git sessions retain direct calls without promoting closure."""
from __future__ import annotations

import copy
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_preformal_owned_source_git_session as session


class OwnedSourceGitSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        found = shutil.which('git.exe' if os.name == 'nt' else 'git')
        if found is None:
            raise unittest.SkipTest('Git unavailable')
        cls.executable = Path(found).resolve()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='banto-source-git-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / 'repo'
        (self.root / 'src').mkdir(parents=True)
        self._git('init', '-q', str(self.root), cwd=self.root.parent)
        self._git('-C', str(self.root), 'config', 'core.autocrlf', 'false')
        (self.root / '.gitignore').write_text('artifacts/\n', encoding='utf-8')
        self.source = self.root / 'src' / 'example.py'
        self.source.write_bytes(b'VALUE = 1\n')
        self._git('-C', str(self.root), 'add', '.gitignore',
                  'src/example.py')
        self._git('-C', str(self.root), '-c', 'user.name=Fixture',
                  '-c', 'user.email=fixture@example.invalid',
                  'commit', '-q', '-m', 'fixture')
        self.revision = self._git('-C', str(self.root),
                                  'rev-parse', 'HEAD').decode().strip()
        self.artifacts = self.root / 'artifacts'
        self.artifacts.mkdir()
        self.policy_dir = self.artifacts / 'external-policy'
        self.policy_dir.mkdir()
        self.policy_path = self.policy_dir / 'policy.json'
        environment = dict(session.owned_git.FIXED_ENV)
        environment['PATH'] = str(self.executable.parent)
        if os.name == 'nt':
            for key in ('SystemRoot', 'WINDIR', 'TEMP', 'TMP'):
                if os.environ.get(key):
                    environment[key] = os.environ[key]
        self.policy = {
            'executable_path': str(self.executable),
            'executable_pin':
                session.owned_git.dependencies.file_observation(
                    self.executable, native=True,
                    maximum=session.owned_git.MAX_EXE)['pin'],
            'executable_links': self.executable.stat().st_nlink,
            'revision': self.revision, 'environment': environment}
        self._save_policy()
        self.output = self.artifacts / 'owned-source-session'

    def _git(self, *arguments, cwd=None):
        return subprocess.check_output([str(self.executable), *arguments],
                                       cwd=cwd, stderr=subprocess.DEVNULL,
                                       timeout=10)

    def _save_policy(self):
        raw = session.io.json_bytes(self.policy)
        self.policy_path.write_bytes(raw)
        self.policy_pin = session.observed._pin(raw)

    def _open(self, output=None):
        return session.OwnedSourceGitSession(
            policy_path=self.policy_path,
            expected_policy_pin=self.policy_pin,
            revision=self.revision,
            receipt_root=self.output if output is None else output,
            phase='owner-source-preflight')

    def _verify(self, result, output=None):
        return session.verify_retained(
            self.output if output is None else output,
            result['manifest_pin'], policy_path=self.policy_path,
            expected_policy_pin=self.policy_pin,
            revision=self.revision, phase='owner-source-preflight')

    def test_real_head_status_blob_and_retained_raw(self):
        with patch.object(session, 'ROOT', self.root):
            with self._open() as reader:
                self.assertEqual(reader.run(call_id='head', operation='head'),
                                 (self.revision + '\n').encode())
                self.assertEqual(reader.run(call_id='status',
                                            operation='status'), b'')
                self.assertEqual(reader.run(
                    call_id='selected-source-0', operation='source_blob',
                    source_path='src/example.py',
                    expected_output_pin=session.observed._pin(
                        self.source.read_bytes())), self.source.read_bytes())
            saved = reader.manifest_result
            self.assertEqual(saved['status'], 'verified')
            self.assertEqual(saved['call_count'], 3)
            self.assertFalse(saved['formal_permission'])
            with patch.object(session.owned_git, 'run_owned',
                              side_effect=AssertionError('Git restarted')):
                retained = self._verify(saved)
            self.assertEqual(retained['status'], 'verified_retained')
            self.assertEqual(retained['call_status'], 'verified')
            self.assertEqual([row['operation'] for row in retained['calls']],
                             ['head', 'status', 'source_blob'])
            output = self.output / 'selected-source-0' / 'stdout.bin'
            raw = output.read_bytes()
            output.write_bytes(b'changed\n')
            with self.assertRaises(ValueError):
                self._verify(saved)
            output.write_bytes(raw)
            self.policy_path.write_bytes(b'{}\n')
            with self.assertRaises(ValueError):
                self._verify(saved)

    def test_dirty_or_bad_blob_saves_failed_manifest_and_stops(self):
        with patch.object(session, 'ROOT', self.root):
            self.source.write_bytes(b'changed\n')
            with self.assertRaises(ValueError):
                with self._open() as reader:
                    reader.run(call_id='head', operation='head')
                    reader.run(call_id='status', operation='status')
            self.assertEqual(reader.manifest_result['status'], 'failed')
            retained = self._verify(reader.manifest_result)
            self.assertEqual(retained['call_status'], 'failed')
            self.assertEqual(retained['call_count'], 2)
            self.source.write_bytes(b'VALUE = 1\n')
            with self.assertRaises(ValueError):
                with self._open(self.artifacts / 'bad-blob') as second:
                    second.run(call_id='blob', operation='source_blob',
                               source_path='src/example.py',
                               expected_output_pin=session.observed._pin(
                                   b'incorrect\n'))
            self.assertEqual(second.manifest_result['status'], 'failed')
            self.assertEqual(self._verify(
                second.manifest_result,
                self.artifacts / 'bad-blob')['call_status'], 'failed')

    def test_changed_executable_failure_remains_readable(self):
        actual = session.owned_git.dependencies.file_observation
        observed = 0

        def changed_after(path, **kwargs):
            nonlocal observed
            value = actual(path, **kwargs)
            if Path(path) == self.executable:
                observed += 1
                if observed == 3:  # Session, pre-spawn, post-exit.
                    value = copy.deepcopy(value)
                    value['identity']['mtime_ns'] += 1
            return value

        with patch.object(session, 'ROOT', self.root), \
             patch.object(session.owned_git.dependencies,
                          'file_observation', side_effect=changed_after):
            with self.assertRaises(ValueError):
                with self._open() as reader:
                    reader.run(call_id='head', operation='head')
            self.assertEqual(reader.manifest_result['status'], 'failed')
            retained = self._verify(reader.manifest_result)
        self.assertEqual(retained['call_status'], 'failed')
        self.assertEqual(retained['calls'][0]['reason'],
                         'executable_changed')

    def test_fake_path_and_reused_root_stop_before_git(self):
        fake = self.artifacts / 'fake'
        fake.mkdir()
        program = fake / ('git.exe' if os.name == 'nt' else 'git')
        program.write_bytes(b'not pinned Git\n')
        if os.name != 'nt':
            program.chmod(0o700)
        self.policy['environment']['PATH'] = os.pathsep.join(
            (str(fake), str(self.executable.parent)))
        self._save_policy()
        with patch.object(session, 'ROOT', self.root):
            with patch.object(session.owned_git, 'run_owned') as run:
                with self.assertRaises(ValueError):
                    self._open()
                run.assert_not_called()
            self.assertFalse(self.output.exists())
            self.policy['environment']['PATH'] = str(self.executable.parent)
            self._save_policy()
            with self._open() as reader:
                reader.run(call_id='head', operation='head')
            with self.assertRaises(ValueError):
                self._open()

    def test_post_receipt_adapter_mismatch_is_retained_as_failure(self):
        real_run = session.owned_git.run_owned

        def bad_return(**kwargs):
            checked = real_run(**kwargs)
            return {**checked, 'stdout': b'not saved output\n'}

        with patch.object(session, 'ROOT', self.root), \
             patch.object(session.owned_git, 'run_owned',
                          side_effect=bad_return):
            with self.assertRaises(ValueError):
                with self._open() as reader:
                    reader.run(call_id='head', operation='head')
        self.assertEqual(reader.manifest_result['status'], 'failed')
        with patch.object(session, 'ROOT', self.root):
            retained = self._verify(reader.manifest_result)
        self.assertEqual(retained['call_status'], 'failed')
        self.assertEqual(retained['calls'][0]['call_status'], 'verified')
        self.assertEqual(retained['calls'][0]['reason'],
                         'adapter_binding_failed')

    def test_duplicate_id_and_unreaped_handle_keep_failed_manifest(self):
        with patch.object(session, 'ROOT', self.root):
            with self.assertRaises(ValueError):
                with self._open() as reader:
                    reader.run(call_id='head', operation='head')
                    reader.run(call_id='head', operation='status')
            self.assertEqual(reader.manifest_result['status'], 'failed')
            self.assertEqual(reader.manifest_result['call_count'], 1)
            handle = object()
            error = session.owned_git.UnreapedGit(handle, 'fixture unreaped')
            with patch.object(session.owned_git, 'run_owned',
                              side_effect=error):
                with self.assertRaises(session.owned_git.UnreapedGit) as raised:
                    with self._open(self.artifacts / 'unreaped') as second:
                        second.run(call_id='head', operation='head')
            self.assertIs(raised.exception, error)
            self.assertIs(raised.exception.process, handle)
            self.assertEqual(second.manifest_result['status'], 'failed')
            self.assertEqual(self._verify(
                second.manifest_result,
                self.artifacts / 'unreaped')['call_status'], 'failed')

    def test_swallowed_unreaped_still_raises_same_live_handle(self):
        handle = object()
        error = session.owned_git.UnreapedGit(handle, 'fixture unreaped')
        with patch.object(session, 'ROOT', self.root), \
             patch.object(session.owned_git, 'run_owned', side_effect=error):
            with self.assertRaises(session.owned_git.UnreapedGit) as raised:
                with self._open() as reader:
                    try:
                        reader.run(call_id='head', operation='head')
                    except session.owned_git.UnreapedGit:
                        pass
        self.assertIs(raised.exception, error)
        self.assertIs(raised.exception.process, handle)
        self.assertEqual(reader.manifest_result['status'], 'failed')
        with patch.object(session, 'ROOT', self.root):
            self.assertEqual(self._verify(reader.manifest_result)[
                'call_status'], 'failed')

    def test_swallowed_call_validation_error_cannot_verify_manifest(self):
        with patch.object(session, 'ROOT', self.root):
            for name, invalid in (
                    ('duplicate', {'call_id': 'head',
                                   'operation': 'status'}),
                    ('operation', {'call_id': 'invalid',
                                   'operation': 'fetch'})):
                with self.subTest(name=name):
                    output = self.artifacts / name
                    with self._open(output) as reader:
                        reader.run(call_id='head', operation='head')
                        with self.assertRaises(ValueError):
                            reader.run(**invalid)
                    self.assertEqual(reader.manifest_result['status'], 'failed')
                    self.assertEqual(self._verify(
                        reader.manifest_result, output)['call_status'], 'failed')


if __name__ == '__main__':
    unittest.main()
