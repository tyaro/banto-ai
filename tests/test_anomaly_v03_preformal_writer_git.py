"""Writer ownership, seeded blob cache, and separate reader context."""
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_preformal_writer_git as owned

flow, platform = owned.publication, owned.platform
REVISION = 'a'*40
PIN = {'bytes': 1, 'sha256': 'b'*64}


class WriterGitTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.files, self.calls = {}, []
        for name in (*platform.SOURCE_FILES, 'src/banto_ai/dynamic_writer_fixture.py'):
            path = self.root/name
            path.parent.mkdir(parents=True, exist_ok=True)
            self.files[name] = (name+'\n').encode()
            path.write_bytes(self.files[name])
        def run(**kwargs):
            self.calls.append(kwargs)
            return ((REVISION+'\n').encode() if kwargs['operation'] == 'head' else
                    b'' if kwargs['operation'] == 'status' else self.files[kwargs['source_path']])
        self.reader = SimpleNamespace(revision=REVISION,
            policy={'executable_path':'external-git','executable_pin':PIN,'executable_links':1},run=run)

    def test_owned_sources_seed_cache_and_preserve_boundary_calls(self):
        with patch.object(flow,'ROOT',self.root), platform._platform_scope(), \
             patch.object(flow.observed,'_git_sources',side_effect=AssertionError('bare Git')):
            source, snapshots, git = flow._git_sources(REVISION,git_reader=self.reader)
        self.assertEqual(len(source['sources']),15)
        self.assertEqual(len(self.calls),17)
        cached = flow._cached_git(git,REVISION,snapshots)
        cached('rev-parse','HEAD');cached('status','--porcelain')
        for _ in range(3):cached('rev-parse','HEAD')
        for _ in range(2):
            for name, raw in self.files.items():
                self.assertEqual(cached('show',REVISION+':'+name),raw)
        self.assertEqual(len(self.calls),23)
        self.assertEqual([r['call_id'] for r in self.calls],[f'writer-git-{i}' for i in range(23)])
        self.assertFalse(cached.tool_record['full_tool_runtime_closure'])
        with self.assertRaises(ValueError):cached('show',REVISION+':../outside.py')

    def test_changed_working_source_is_rejected(self):
        (self.root/flow.observed.SOURCE_FILES[0]).write_bytes(b'changed')
        with patch.object(flow,'ROOT',self.root), platform._platform_scope():
            with self.assertRaisesRegex(ValueError,'working/Git bytes differ'):
                flow._git_sources(REVISION,git_reader=self.reader)

    def test_reader_context_is_separate_only_for_owned_writer(self):
        for index, reader in enumerate((None,self.reader)):
            source = {'revision':REVISION,'sources':[]}
            first, second = object(),object()
            contexts, options = [],[]
            def run(role,*args,**kwargs):
                contexts.append(args[-1][2]);options.append(kwargs)
                if role == 'reader':raise ValueError('stop at reader boundary')
                return {'status':'verified'}
            with self.subTest(owned=reader is not None), patch.object(flow,'ROOT',self.root), \
                 patch.object(flow,'_request'), patch.object(flow,'_load',return_value=({},{})), \
                 patch.object(flow,'_git_sources',side_effect=[(source,{},first),(source,{},second)]) as sources, \
                 patch.object(flow,'_cached_git',side_effect=lambda git,*args:git), \
                 patch.object(flow,'_run_role',side_effect=run), \
                 patch.object(flow.budgets,'FixtureBudget'), patch.object(flow.budgets,'finish'), \
                 patch.object(flow.budgets,'save_result'):
                result = flow.publish_with_evidence({'analysis_reference':{},'audit_reference':{},'inputs':{}},
                    expected_revision=REVISION,receipt_parent=self.root,receipt_name=f'context-{index}',
                    writer_git_reader=reader)
            self.assertEqual(result['status'],'failed')
            self.assertEqual(contexts,[first,first if reader is None else second])
            self.assertEqual(options,[{} if reader is None else {'owned_git':True},{}])
            self.assertEqual(sources.call_count,1 if reader is None else 2)
            if reader is not None:
                self.assertIs(sources.call_args_list[0].kwargs['git_reader'],reader)
                self.assertEqual(sources.call_args_list[1].kwargs,{})

    def test_profile_guard_precedes_io(self):
        with patch.object(flow,'_request'), \
             patch.object(flow.dependencies,'load_five_role_profile',side_effect=AssertionError('profile loader')):
            with self.assertRaisesRegex(ValueError,'excludes unowned profile'):
                flow.publish_with_evidence({},expected_revision=REVISION,receipt_parent='unused',
                    receipt_name='unused',dependency_profiles={'writer':{},'reader':{}},writer_git_reader=self.reader)


if __name__ == '__main__':
    unittest.main()
