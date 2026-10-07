"""Worker source callbacks stop on mismatches and preserve original ownership."""
from contextlib import ExitStack
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_owned_generated_attempt as generated
from banto_ai import anomaly_v03_preformal_owned_saved_attempt as reader
from banto_ai import anomaly_v03_preformal_job_tree_owner as owner

REVISION = 'b' * 40
NAMES = ('src/first.py', 'src/second.py')
RAW = {name:(name+'\n').encode() for name in NAMES}


class WorkerSourceCallbacksTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='banto-worker-source-')
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name).resolve()
        (self.root/'src').mkdir()
        for name,raw in RAW.items(): (self.root/name).write_bytes(raw)

    def bound(self,module,stack,source_names=NAMES):
        stack.enter_context(patch.object(module,'ROOT',self.root))
        stack.enter_context(patch.object(module,'SOURCE_FILES',source_names))
        bare=stack.enter_context(patch.object(module.subprocess,'check_output',
            side_effect=AssertionError('unexpected bare Git fallback')))
        return bare

    def identity(self): return Mock(return_value={'head':REVISION.encode()+b'\n','status':b''})
    def blob(self,**request):
        self.assertEqual(request['revision'],REVISION)
        self.assertEqual(request['expected_output_pin'],reader._pin(RAW[request['source_path']]))
        return RAW[request['source_path']]

    def test_source_exact_path_revision_raw_pin_and_legacy_reply(self):
        for module in (generated,reader):
            with self.subTest(module=module.__name__),ExitStack() as stack:
                bare=self.bound(module,stack);identity=self.identity();blob=Mock(side_effect=self.blob)
                result=module._source(REVISION,git_identity=identity,git_blob=blob)
                self.assertEqual(result,{'revision':REVISION,'selected_files':[
                    {'path':name,'pin':reader._pin(RAW[name])} for name in NAMES],
                    'scope':'selected-working-git-raw-only-not-source-closure'})
                self.assertEqual([c.kwargs['source_path'] for c in blob.call_args_list],list(NAMES))
                identity.assert_called_once_with();bare.assert_not_called()

    def test_original_critical_owner_stops_without_fallback_or_next_read(self):
        error=owner.UnreapedJob(11,22,33,{'status':'failed'},extra_handles={'stdout':44})
        for module in (generated,reader):
            with self.subTest(module=module.__name__),ExitStack() as stack:
                bare=self.bound(module,stack);blob=Mock(side_effect=error)
                with self.assertRaises(owner.UnreapedJob) as caught:
                    module._source(REVISION,git_identity=self.identity(),git_blob=blob)
                self.assertIs(caught.exception,error)
                self.assertEqual((error.job,error.process,error.thread,error.extra_handles),(11,22,33,{'stdout':44}))
                self.assertEqual(blob.call_count,1);bare.assert_not_called()

    def test_shared_stop_exception_is_not_retried(self):
        error=generated.resources.ResourceStop('pipeline_wall_limit')
        for module in (generated,reader):
            with self.subTest(module=module.__name__),ExitStack() as stack:
                bare=self.bound(module,stack);blob=Mock(side_effect=error)
                with self.assertRaises(type(error)) as caught:
                    module._source(REVISION,git_identity=self.identity(),git_blob=blob)
                self.assertIs(caught.exception,error);self.assertEqual(blob.call_count,1);bare.assert_not_called()

    def test_identity_mismatch_or_bad_raw_blocks_blob_reads(self):
        invalid=[{'head':b'a'*40,'status':b''},{'head':REVISION.encode(),'status':b' M changed\n'},
                 {'head':REVISION,'status':b''},{'head':REVISION.encode(),'status':False},
                 {'head':REVISION.encode(),'status':b'','extra':True}]
        for module in (generated,reader):
            for identity in invalid:
                with self.subTest(module=module.__name__,identity=identity),ExitStack() as stack:
                    bare=self.bound(module,stack);blob=Mock()
                    with self.assertRaises(ValueError):
                        module._source(REVISION,git_identity=lambda:identity,git_blob=blob)
                    blob.assert_not_called();bare.assert_not_called()

    def test_blob_mismatch_or_non_bytes_stops_without_fallback(self):
        for module in (generated,reader):
            for value in (b'different',RAW[NAMES[0]].decode(),bytearray(RAW[NAMES[0]])):
                with self.subTest(module=module.__name__,value=value),ExitStack() as stack:
                    bare=self.bound(module,stack);blob=Mock(return_value=value)
                    with self.assertRaises(ValueError):
                        module._source(REVISION,git_identity=self.identity(),git_blob=blob)
                    self.assertEqual(blob.call_count,1);bare.assert_not_called()

    def test_invalid_callback_rejected_before_identity_or_git(self):
        for module in (generated,reader):
            with self.subTest(module=module.__name__),ExitStack() as stack:
                bare=self.bound(module,stack);identity=self.identity()
                with self.assertRaisesRegex(ValueError,'must be callable'):
                    module._source(REVISION,git_identity=identity,git_blob={})
                identity.assert_not_called();bare.assert_not_called()
                with self.assertRaisesRegex(ValueError,'must be callable'):
                    module._source(REVISION,git_identity=False,git_blob=self.blob)
                bare.assert_not_called()

    def test_default_commands_and_timeout_are_preserved(self):
        for module in (generated,reader):
            with self.subTest(module=module.__name__),ExitStack() as stack:
                self.bound(module,stack)
                git=stack.enter_context(patch.object(module.subprocess,'check_output',
                    side_effect=[REVISION.encode()+b'\n',b'',*RAW.values()]))
                module._source(REVISION)
                self.assertEqual([c.args[0] for c in git.call_args_list],[
                    ['git','-C',str(self.root),'rev-parse','HEAD'],
                    ['git','-c','core.fsmonitor=false','-C',str(self.root),'status','--porcelain','--untracked-files=normal'],
                    *[['git','-C',str(self.root),'show',REVISION+':'+name] for name in NAMES]])
                self.assertTrue(all(c.kwargs['timeout']==10 for c in git.call_args_list))

    def test_default_wrong_head_does_not_start_status_or_blobs(self):
        for module in (generated,reader):
            with self.subTest(module=module.__name__),ExitStack() as stack:
                self.bound(module,stack)
                git=stack.enter_context(patch.object(module.subprocess,'check_output',return_value=b'a'*40))
                with self.assertRaises(ValueError): module._source(REVISION)
                self.assertEqual(git.call_count,1)

    def test_generator_snapshots_use_exact_callback_binding(self):
        with ExitStack() as stack:
            bare=self.bound(generated,stack)
            stack.enter_context(patch.object(generated,'SNAPSHOT_FILES',NAMES))
            callback=Mock(side_effect=self.blob)
            checkout=generated._validated_snapshots({REVISION:RAW},REVISION,git_blob=callback)
            self.assertEqual(checkout.revision,REVISION)
            self.assertEqual([c.kwargs['source_path'] for c in callback.call_args_list],list(NAMES))
            bare.assert_not_called()

    def test_snapshot_changed_working_or_callback_raw_is_rejected(self):
        with ExitStack() as stack:
            bare=self.bound(generated,stack)
            stack.enter_context(patch.object(generated,'SNAPSHOT_FILES',NAMES))
            callback=Mock(return_value=b'changed')
            with self.assertRaises(ValueError):
                generated._validated_snapshots({REVISION:RAW},REVISION,git_blob=callback)
            self.assertEqual(callback.call_count,1);bare.assert_not_called()

    def reader_operation(self,stack):
        source={'revision':REVISION,'selected_files':[], 'scope':'selected-working-git-raw-only-not-source-closure'}
        request={'source_revision':REVISION,'source_snapshots':{},'chunk_index':0,
            'output_names':{},'external_pins':{},'source':source,'runtime':{},
            'expected_mode':reader.saved.MODE,'invocation_id':'test'}
        stack.enter_context(patch.object(reader,'_decode_source_snapshots',return_value={}))
        stack.enter_context(patch.object(reader,'_saved_outputs',return_value=({},1)))
        stack.enter_context(patch.object(reader,'_check_outputs'))
        stack.enter_context(patch.object(reader.runtime,'probe_runtime',return_value={}))
        stack.enter_context(patch.object(reader.observed,'creation_observation',return_value={'start_token':'test'}))
        read=stack.enter_context(patch.object(reader.fixture,'read_invented_registered_attempt',return_value={'status':'inconclusive'}))
        request['external_pins']={name:reader._pin(b'') for name in reader.SAVED}
        return request,source,read

    def test_reader_operation_routes_both_boundaries_without_replaying_read(self):
        with ExitStack() as stack:
            request,source,read=self.reader_operation(stack)
            selected=stack.enter_context(patch.object(reader,'_source',return_value=source))
            identity,blob=self.identity(),Mock()
            reply=reader._read_attempt(request,self.root,git_identity=identity,git_blob=blob)
            self.assertEqual(selected.call_count,2)
            self.assertTrue(all(c.kwargs=={'git_identity':identity,'git_blob':blob} for c in selected.call_args_list))
            read.assert_called_once();self.assertIs(reply['formal_permission'],False)

    def test_reader_postflight_owner_failure_prevents_reply_and_replay(self):
        with ExitStack() as stack:
            request,source,read=self.reader_operation(stack)
            error=owner.UnclosedHandles({'job':11},{'status':'failed'})
            stack.enter_context(patch.object(reader,'_source',side_effect=[source,error]))
            with self.assertRaises(owner.UnclosedHandles) as caught:
                reader._read_attempt(request,self.root,git_identity=self.identity(),git_blob=Mock())
            self.assertIs(caught.exception,error);self.assertEqual(error.handles,{'job':11})
            read.assert_called_once()

    def test_generator_source_stop_prevents_output_generation(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(generated,'_outputs',return_value={}))
            stack.enter_context(patch.object(generated,'_validate_pins'))
            stack.enter_context(patch.object(reader,'_decode_source_snapshots',return_value={}))
            snapshots=stack.enter_context(patch.object(generated,'_validated_snapshots'))
            error=owner.UnreapedJob(11,22,33,{'status':'failed'})
            selected=stack.enter_context(patch.object(generated,'_source',side_effect=error))
            build=stack.enter_context(patch.object(generated,'build_invented_output_bytes'))
            identity,blob=self.identity(),Mock()
            request={'source_revision':REVISION,'source_snapshots':{},'chunk_index':0,'output_names':{},'external_pins':{}}
            with self.assertRaises(owner.UnreapedJob) as caught:
                generated._generate_attempt(request,self.root,git_identity=identity,git_blob=blob)
            self.assertIs(caught.exception,error)
            snapshots.assert_called_once_with({},REVISION,git_blob=blob)
            selected.assert_called_once_with(REVISION,git_identity=identity,git_blob=blob)
            build.assert_not_called();self.assertFalse((self.root/'saved').exists())
