"""The Git input policy preparer stops before any five-role execution."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools import preformal_owned_git_policy_prepare as prepare


class OwnedGitPolicyPrepareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        found = shutil.which('git.exe' if os.name == 'nt' else 'git')
        if found is None:
            raise unittest.SkipTest('Git unavailable')
        cls.executable = Path(found).resolve()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='banto-git-policy-')
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
        self.output = self.artifacts / 'new-policy'

    def _git(self, *args, cwd=None):
        return subprocess.check_output([str(self.executable), *args],
                                       cwd=cwd, stderr=subprocess.DEVNULL,
                                       timeout=10)

    def _prepare(self, revision=None, output=None, path=None):
        with patch.object(prepare, 'ROOT', self.root), \
             patch.dict(os.environ, {'PATH': str(path or
                                                self.executable.parent)}):
            return prepare.prepare_policy(
                expected_revision=self.revision if revision is None else revision,
                output_root=self.output if output is None else output)

    def test_clean_checkout_saves_compatible_canonical_policy_once(self):
        result = self._prepare()
        self.assertEqual(result['status'], 'input_policy_prepared')
        self.assertFalse(result['formal_permission'])
        self.assertFalse(result['source_closure_complete'])
        self.assertFalse(result['runtime_closure_complete'])
        raw = (self.output / 'policy.json').read_bytes()
        self.assertEqual(result['policy_pin'], prepare.observed._pin(raw))
        policy = prepare.v.strict_json(raw)
        self.assertEqual(raw, prepare.io.json_bytes(policy))
        self.assertEqual(policy['revision'], self.revision)
        self.assertEqual(policy['environment']['PATH'],
                         str(self.executable.parent))
        self.assertLessEqual(set(policy['environment']),
                             set(prepare.owned_git.FIXED_ENV) |
                             prepare.owned_git.PASSTHROUGH_ENV)
        self.assertEqual(policy['executable_links'],
                         self.executable.stat().st_nlink)
        self.assertEqual(policy['executable_pin'],
                         prepare.owned_git.dependencies.file_observation(
                             self.executable, native=True,
                             maximum=prepare.owned_git.MAX_EXE)['pin'])
        with patch.object(prepare, 'ROOT', self.root):
            prepare.owned_git._policy(self.root, policy)
        with self.assertRaises(ValueError):
            self._prepare()
        self.assertEqual((self.output / 'policy.json').read_bytes(), raw)

    def test_dirty_or_wrong_revision_stops_before_output_root(self):
        (self.root / 'tracked.txt').write_text('dirty\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            self._prepare()
        self.assertFalse(self.output.exists())
        (self.root / 'tracked.txt').write_text('clean\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            self._prepare(revision='0' * 40)
        self.assertFalse(self.output.exists())

    def test_fake_git_path_or_external_output_root_is_rejected(self):
        fake_dir = self.artifacts / 'fake-bin'
        fake_dir.mkdir()
        fake = fake_dir / ('git.exe' if os.name == 'nt' else 'git')
        fake.write_bytes(b'not an executable Git program\n')
        if os.name != 'nt':
            fake.chmod(0o700)
        with patch.object(prepare, '_git', return_value=b'not Git\n') as run:
            with self.assertRaises(ValueError):
                self._prepare(path=fake_dir)
            run.assert_called_once()
        self.assertFalse(self.output.exists())
        with self.assertRaises(ValueError):
            self._prepare(output=self.root / 'wrong-place')
        self.assertFalse((self.root / 'wrong-place').exists())


if __name__ == '__main__':
    unittest.main()
