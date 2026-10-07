"""Archive protocol fixtures, deliberately excluding native process execution."""
import copy
import gzip
from pathlib import Path
import tempfile
import unittest
from contextlib import ExitStack
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_git_receipt_archive as archive
from banto_ai import anomaly_v03_preformal_owned_git_job as tree
from tests.test_anomaly_v03_preformal_owned_git_job import MEMORY, ACCOUNT

owned = archive.owned


class GitReceiptArchiveTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='banto-git-archive-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        (self.root / 'artifacts').mkdir()
        self.path = self.root / 'artifacts/git-blobs.bin'
        self.exe = self.root / 'git.exe'
        self.env = {'PATH': 'fixed'}
        self.before = {'pin': owned.observed._pin(b'exe'), 'identity': {'links': 1}}
        self.policy = {'process_ownership': owned.JOB_OWNERSHIP,
            'revision': 'b' * 40, 'executable_pin': self.before['pin'], 'executable_links': 1}
        stack = ExitStack(); self.addCleanup(stack.close)
        stack.enter_context(patch.object(archive, 'ROOT', self.root))
        stack.enter_context(patch.object(owned, '_policy', return_value=(self.root, self.exe, self.env, self.before)))
        self.spawn = stack.enter_context(patch.object(owned.subprocess, 'Popen', side_effect=AssertionError('Git launched')))
        self.kernel = stack.enter_context(patch.object(tree.owner, '_kernel', side_effect=AssertionError('native Job API')))

    def arguments(self, index=0, data=b'source\n', phase='preflight', change=None,
                  source_path='src/source.py'):
        call = {'call_id': 'blob-' + str(index), 'phase': phase, 'source_path': source_path,
                'expected_output_pin': owned.observed._pin(data)}
        # Private Job receipts use Windows creation identity, including when
        # this saved-data protocol fixture runs on the Ubuntu CI host.
        identity = {'pid': 44 + index, 'creation_time_100ns': 123 + index}
        identity = {**identity, 'start_token': owned.v.canonical_sha256(identity),
                    'native_start_identity_authenticated': True}
        receipt = dict.fromkeys(tree._FIELDS)
        receipt.update(format=owned.JOB_FORMAT, status='verified', reason=None, prior_stop_reason=None,
            operation='source_blob', source_path=call['source_path'], revision=self.policy['revision'],
            executable_path=str(self.exe), executable_expected_pin=self.before['pin'],
            executable_links_expected=1, executable_before=self.before, executable_after=self.before,
            argv=[str(self.exe), '-c', 'core.fsmonitor=false', '-c', 'core.pager=cat',
                  '-c', 'safe.directory=' + str(self.root), '-C', str(self.root),
                  'show', self.policy['revision'] + ':' + call['source_path']],
            cwd=str(self.root), environment=self.env, process_identity=identity, exit_code=0,
            process_error_type=None, direct_process_handle_exit_confirmed=True, elapsed_seconds=0.1,
            stdout_pin=call['expected_output_pin'], stdout_bytes=len(data),
            stderr_pin=owned.observed._pin(b''), stderr_bytes=0, expected_output_pin=call['expected_output_pin'],
            integration_pending=True, formal_permission=False, source_closure_complete=False,
            runtime_closure_complete=False, execution_authenticated=False, job={
                'format':tree.JOB, 'assignment_confirmed':True, 'root_resumed':True,
                'accounting':ACCOUNT, 'memory':MEMORY, 'all_assigned_processes_exit_confirmed':True,
                'individual_descendant_exit_codes_authenticated':False, 'loaded_code_authenticated':False,
                'whole_tree_resource_budget_measured':False, 'observation_errors':[]})
        if change is not None:
            change(receipt)
        raw = owned.io.json_bytes(receipt)
        return {'call':call, 'receipt_raw':raw, 'expected_receipt_pin':owned.observed._pin(raw),
                'stdout_raw':data, 'stderr_raw':b''}

    def writer(self):
        return archive.ReceiptArchive(self.path, root=self.root, policy=self.policy)

    def test_roundtrip_shares_raw_but_keeps_all_call_receipts_and_external_pins(self):
        writer = self.writer()
        for i in range(3):
            writer.append(**self.arguments(i, phase='preflight' if i == 0 else 'postflight'))
        result = writer.snapshot()
        self.assertEqual(result['call_count'], 3)
        self.assertEqual(result['unique_stdout_records'], 1)
        self.assertEqual(len(set(row['sha256'] for row in result['rows'])), 3)
        self.assertFalse(result['formal_permission'])
        self.spawn.assert_not_called(); self.kernel.assert_not_called()

    def test_byte_verifier_and_existing_directory_verifier_apply_same_checks(self):
        args = self.arguments()
        target = self.root / 'retained'; target.mkdir()
        for name, raw in [('receipt.json',args['receipt_raw']),('stdout.bin',args['stdout_raw']),('stderr.bin',b'')]:
            (target/name).write_bytes(raw)
        expected = owned.verify_retained(target, args['expected_receipt_pin'], root=self.root, policy=self.policy)
        actual = owned.verify_raw(args['receipt_raw'], args['expected_receipt_pin'],
            stdout_raw=args['stdout_raw'], stderr_raw=b'', root=self.root, policy=self.policy)
        self.assertEqual(actual, expected)
        with self.assertRaises(ValueError):
            owned.verify_raw(args['receipt_raw'], args['expected_receipt_pin'], stdout_raw=b'different',
                             stderr_raw=b'', root=self.root, policy=self.policy)

    def test_wrong_source_argv_or_live_job_are_not_archived(self):
        changes = [lambda r:r.update(source_path='src/wrong.py'),
                   lambda r:r['argv'].append('extra'),
                   lambda r:r['job'].update(accounting={**ACCOUNT,'active_processes':1}),
                   lambda r:r.update(formal_permission=True)]
        for change in changes:
            with self.subTest(change=change):
                path = self.root / 'artifacts' / str(len(list((self.root/'artifacts').iterdir())))
                path.mkdir()
                writer = archive.ReceiptArchive(path/'git-blobs.bin', root=self.root, policy=self.policy)
                with self.assertRaises(ValueError):writer.append(**self.arguments(change=change))
                self.assertEqual(writer.path.read_bytes(), b'')
                with self.assertRaises(ValueError):writer.append(**self.arguments())

    def test_file_or_frame_pin_change_and_incomplete_inventory_reject(self):
        writer=self.writer(); writer.append(**self.arguments())
        saved=writer.snapshot()
        for rows,calls,pin in [(saved['rows'],saved['calls'],{**saved['pin'],'sha256':'0'*64}),
                              ([],[],saved['pin']),
                              ([{**saved['rows'][0],'sha256':'0'*64}],saved['calls'],saved['pin'])]:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                archive.verify(self.path,pin,rows=rows,calls=calls,root=self.root,policy=self.policy)

    def test_forward_reference_and_trailing_member_are_rejected(self):
        args=self.arguments(); writer=self.writer(); writer.append(**args)
        value=archive._inflate(self.path.read_bytes())
        value.update(stdout_gzip=None,stdout_ref=0)
        with self.assertRaises(ValueError):
            archive._record(value,0,args['call'],[],root=self.root,policy=self.policy)
        compressed=gzip.compress(b'{}',mtime=0)*2
        frame=archive.MAGIC+len(compressed).to_bytes(4,'big')+compressed
        with self.assertRaises(ValueError):archive._inflate(frame)

    def test_gzip_bomb_is_rejected_before_json_or_raw_allocation_grows(self):
        compressed=gzip.compress(b'x'*(archive.MAX_RAW+1),mtime=0)
        frame=archive.MAGIC+len(compressed).to_bytes(4,'big')+compressed
        with self.assertRaises(ValueError):archive._inflate(frame)

    def test_prewrite_byte_stop_keeps_prior_file_and_poisoned_writer(self):
        writer=self.writer(); writer.append(**self.arguments())
        original=self.path.read_bytes()
        with patch.object(archive,'MAX_BYTES',len(original)), self.assertRaises(ValueError):
            writer.append(**self.arguments(1))
        self.assertEqual(self.path.read_bytes(),original)
        with self.assertRaises(ValueError):writer.snapshot()

    def test_stop_after_durable_append_preserves_rows_and_original_exception(self):
        writer=self.writer(); stop=tree.owner.resources.ResourceStop('wall_seconds')
        checkpoint=Mock(side_effect=[None,stop])
        with self.assertRaises(type(stop)) as caught:
            writer.append(**self.arguments(),checkpoint=checkpoint)
        self.assertIs(caught.exception,stop)
        self.assertEqual(len(writer.rows),1)
        self.assertGreater(self.path.stat().st_size,0)
        with self.assertRaises(ValueError):writer.append(**self.arguments(1))

    def test_saved_readback_failure_retains_data_and_forbids_next_append(self):
        writer=self.writer(); original=archive.observed._file
        def read(path,maximum):
            raw=original(path,maximum)
            return raw+b'wrong' if raw else raw
        with patch.object(archive.observed,'_file',side_effect=read), self.assertRaises(ValueError):
            writer.append(**self.arguments())
        self.assertEqual(len(writer.rows),1)
        self.assertGreater(self.path.stat().st_size,0)
        with self.assertRaises(ValueError):writer.append(**self.arguments(1))

    def test_duplicate_call_and_backwards_phase_are_rejected(self):
        for second in (self.arguments(),self.arguments(1,phase='preflight')):
            with self.subTest(second=second['call']['call_id']):
                folder=self.root/'artifacts'/str(len(list((self.root/'artifacts').iterdir())))
                folder.mkdir(); writer=archive.ReceiptArchive(folder/'git-blobs.bin',root=self.root,policy=self.policy)
                writer.append(**self.arguments(phase='postflight'))
                with self.assertRaises(ValueError):writer.append(**second)

    def test_replayed_original_process_identity_is_rejected_for_new_call_id(self):
        writer=self.writer(); writer.append(**self.arguments())
        replay=self.arguments(); replay['call']['call_id']='blob-1'
        original=self.path.read_bytes()
        with self.assertRaisesRegex(ValueError,'original process identity reused'):
            writer.append(**replay)
        self.assertEqual(self.path.read_bytes(),original)

    def test_snapshot_tampering_poison_prevents_future_append(self):
        writer=self.writer(); writer.append(**self.arguments())
        writer.rows[0]['offset']=1
        with self.assertRaises(ValueError):writer.snapshot()
        with self.assertRaises(ValueError):writer.append(**self.arguments(1))

    def test_existing_file_and_non_job_policy_are_rejected(self):
        self.writer()
        with self.assertRaises(ValueError):self.writer()
        folder=self.root/'artifacts/another'; folder.mkdir()
        with self.assertRaises(ValueError):
            archive.ReceiptArchive(folder/'git-blobs.bin',root=self.root,policy={})
        self.assertFalse((folder/'git-blobs.bin').exists())

    def test_phase_cached_parent_inventory_fits_as_synthetic_receipt_fixture(self):
        from banto_ai import anomaly_v03_preformal_generation_publication_budget as whole
        writer=self.writer()
        names=whole.document.SOURCE_NAMES+whole.SOURCE_NAMES
        for phase in ('preflight','postflight'):
            for name in names:
                data=(whole.ROOT/name).read_bytes()
                cached=writer.lookup(revision=self.policy['revision'],phase=phase,source_path=name,
                                     expected_output_pin=owned.observed._pin(data))
                if cached is None:
                    writer.append(**self.arguments(len(writer.rows),data=data,phase=phase,source_path=name))
                else:
                    self.assertEqual(cached,data)
        result=writer.snapshot()
        self.assertEqual(result['call_count'],2*len(set(names)))
        self.assertLessEqual(result['unique_stdout_records'],len(set(names)))
        self.assertLessEqual(self.path.stat().st_size,archive.MAX_BYTES)
        # The process facts are synthetic protocol fixtures. This is not a
        # native peak measurement or formal capacity acceptance.
        self.spawn.assert_not_called(); self.kernel.assert_not_called()

    def test_only_explicit_parent_tool_sources_are_allowed(self):
        from banto_ai import anomaly_v03_preformal_generation_publication_budget as whole
        tools={name for name in whole.SOURCE_NAMES if name.startswith('tools/')}
        self.assertEqual(tools,owned.SOURCE_TOOLS)
        for name in tools:
            self.assertEqual(owned._command(self.policy,'source_blob',name,
                                           owned.observed._pin(b'tool')),
                             ['show',self.policy['revision']+':'+name])
        writer=self.writer()
        with self.assertRaises(ValueError):
            writer.append(**self.arguments(source_path='tools/other.py'))
        self.assertEqual(self.path.read_bytes(),b'')

    def test_cache_is_bound_to_revision_phase_path_and_pin(self):
        writer=self.writer(); args=self.arguments(); writer.append(**args)
        options={'revision':self.policy['revision'],'phase':'preflight',
                 'source_path':args['call']['source_path'],'expected_output_pin':args['call']['expected_output_pin']}
        self.assertEqual(writer.lookup(**options),args['stdout_raw'])
        self.assertIsNone(writer.lookup(**{**options,'phase':'postflight'}))
        self.assertIsNone(writer.lookup(**{**options,'source_path':'src/other.py'}))
        with self.assertRaises(ValueError):
            writer.lookup(**{**options,'expected_output_pin':owned.observed._pin(b'changed')})
        with self.assertRaises(ValueError):writer.append(**self.arguments(1))

    def test_cache_revision_change_and_checkpoint_stop_preserve_original_failure(self):
        writer=self.writer()
        with self.assertRaises(ValueError):
            writer.lookup(revision='a'*40,phase='preflight',source_path='src/source.py',
                          expected_output_pin=owned.observed._pin(b'source'))
        folder=self.root/'artifacts/stop'; folder.mkdir()
        writer=archive.ReceiptArchive(folder/'git-blobs.bin',root=self.root,policy=self.policy)
        args=self.arguments(); writer.append(**args)
        stop=tree.owner.resources.ResourceStop('wall_seconds')
        with self.assertRaises(type(stop)) as caught:
            writer.lookup(revision=self.policy['revision'],phase='preflight',
                source_path=args['call']['source_path'],expected_output_pin=args['call']['expected_output_pin'],
                checkpoint=Mock(side_effect=[None,stop]))
        self.assertIs(caught.exception,stop)
        self.assertEqual(len(writer.rows),1)
        with self.assertRaises(ValueError):writer.snapshot()

    def test_fsync_failure_keeps_unindexed_raw_and_original_exception(self):
        writer=self.writer(); error=OSError('fsync failed')
        with patch.object(archive.os,'fsync',side_effect=error), self.assertRaises(OSError) as caught:
            writer.append(**self.arguments())
        self.assertIs(caught.exception,error)
        self.assertGreater(self.path.stat().st_size,0)
        self.assertEqual(writer.rows,[])
        with self.assertRaises(ValueError):writer.append(**self.arguments(1))
        with self.assertRaises(ValueError):writer.snapshot()

    def test_cache_cannot_return_preflight_bytes_after_postflight(self):
        writer=self.writer(); args=self.arguments(); writer.append(**args)
        writer.append(**self.arguments(1,phase='postflight'))
        with self.assertRaisesRegex(ValueError,'phase moved backwards'):
            writer.lookup(revision=self.policy['revision'],phase='preflight',
                source_path=args['call']['source_path'],expected_output_pin=args['call']['expected_output_pin'])


if __name__ == '__main__':
    unittest.main()
