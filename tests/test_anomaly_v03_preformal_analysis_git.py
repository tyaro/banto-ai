"""Direct ownership and saved analysis source/dependency routing."""
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_preformal_analysis_git as owned
from banto_ai import anomaly_v03_fixture_worker as worker


REVISION = 'a' * 40
PIN = {'bytes': 1, 'sha256': 'b' * 64}


class AnalysisGitRoutingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.files = {}
        for name in owned.numeric.SOURCE_FILES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = (name + '\n').encode()
            path.write_bytes(raw)
            self.files[name] = raw
        self.calls = []

        def run(**kwargs):
            self.calls.append(kwargs)
            return ((REVISION + '\n').encode() if kwargs['operation'] == 'head' else
                    b'' if kwargs['operation'] == 'status' else self.files[kwargs['source_path']])

        self.reader = SimpleNamespace(revision=REVISION,
            policy={'executable_path': 'external-git', 'executable_pin': PIN, 'executable_links': 1}, run=run)

    def test_fixed_sources_boundary_heads_and_cached_dependency_calls(self):
        with patch.object(worker, 'ROOT', self.root), \
             patch.object(worker.observed, 'ROOT', self.root), \
             owned.numeric._numeric_scope('analysis'), \
             patch.object(worker.observed, '_git_sources', side_effect=AssertionError('bare Git')):
            source, snapshots, git = worker._git_sources(REVISION, git_reader=self.reader)
        self.assertEqual(len(self.calls), 29)
        self.assertEqual(len(source['sources']), 27)
        self.assertEqual(snapshots[REVISION], self.files)
        self.assertEqual(git.tool_record['path'], 'external-git')
        self.assertFalse(git.tool_record['full_tool_runtime_closure'])
        self.assertEqual(git('rev-parse', 'HEAD').strip(), REVISION.encode())
        self.assertEqual(git('rev-parse', 'HEAD').strip(), REVISION.encode())
        git.start_dependencies()
        name = next(iter(self.files))
        self.assertEqual(git('show', REVISION + ':' + name), self.files[name])
        self.assertEqual(git('show', REVISION + ':' + name), self.files[name])
        self.assertEqual(len(self.calls), 32)
        self.assertEqual([r['call_id'] for r in self.calls], [f'analysis-git-{i}' for i in range(32)])
        self.assertEqual(self.calls[-1]['expected_output_pin'], worker.observed._pin(self.files[name]))
        with self.assertRaisesRegex(ValueError, 'cache starts once'):
            git.start_dependencies()

    def test_unsafe_requests_wrong_revision_and_changed_source_stop(self):
        git = owned.OwnedAnalysisGit(self.reader, root=self.root, revision=REVISION)
        for args in (('show', 'c' * 40 + ':src/fixture.py'), ('show', REVISION + ':../escape'),
                     ('show', REVISION + ':docs/file.md'), ('status',)):
            with self.assertRaises(ValueError):
                git(*args)
        self.assertEqual(self.calls, [])
        with self.assertRaisesRegex(ValueError, 'owned Git revision'):
            owned.OwnedAnalysisGit(self.reader, root=self.root, revision='d' * 40)
        (self.root / next(iter(self.files))).write_bytes(b'changed working source')
        with patch.object(worker, 'ROOT', self.root), \
             patch.object(worker.observed, 'ROOT', self.root), owned.numeric._numeric_scope('analysis'):
            with self.assertRaisesRegex(ValueError, 'working/Git bytes differ'):
                worker._git_sources(REVISION, git_reader=self.reader)

    def test_owned_analysis_profile_guard_precedes_loader_and_io(self):
        with patch.object(worker, '_request'), \
             patch.object(worker.dependencies, 'load_five_role_profile', side_effect=AssertionError('profile loader')):
            with self.assertRaisesRegex(ValueError, 'excludes unowned profile'):
                worker.calculate_with_evidence({}, expected_revision=REVISION,
                    receipt_parent='unused', receipt_name='unused', git_reader=self.reader,
                    dependency_profile_raw=b'{}', expected_dependency_profile_pin=PIN)


if __name__ == '__main__':
    unittest.main()
