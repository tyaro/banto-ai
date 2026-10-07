"""Metadata-only channel gates: no native worker, Job, or executable proof."""
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_worker_stop_channel as channel
from banto_ai import anomaly_v03_preformal_job_tree_owner as owner


def identity(pid,created):
    value={'pid':pid,'creation_time_100ns':created}
    return {**value,'start_token':channel.v.canonical_sha256(value)}


class WorkerStopChannelTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='banto-stop-channel-')
        self.addCleanup(temporary.cleanup);self.root=Path(temporary.name).resolve()
        self.enterContext(patch.object(channel,'ROOT',self.root))
        self.now=100.0;self.enterContext(patch.object(channel.time,'monotonic',side_effect=lambda:self.now))
        self.parent_id=identity(101,11);self.child_id=identity(202,22);self.current=self.parent_id
        self.process=SimpleNamespace(pid=202,_handle=object())
        def observed(pid,handle=None):
            if handle is None:return dict(self.current)
            self.assertEqual(pid,202);self.assertIs(handle,self.process._handle)
            return dict(self.child_id)
        self.enterContext(patch.object(channel.observed,'creation_observation',side_effect=observed))
        self.measured=self.root/'artifacts'/'budget';self.measured.mkdir(parents=True)
        policy_root=self.root/'artifacts'/'external-policy';policy_root.mkdir()
        self.policy_path=policy_root/'policy.json'
        self.revision='a'*40
        policy={'revision':self.revision,'process_ownership':channel.sessions.owned_git.JOB_OWNERSHIP}
        raw=channel.io.json_bytes(policy);self.policy_path.write_bytes(raw)
        self.policy={'path':str(self.policy_path),'expected_pin':channel.observed._pin(raw)}
        self.budget=SimpleNamespace(root=self.measured,started_at=100.0,limits={'wall_seconds':90},
            probe=lambda:None,_thread=SimpleNamespace(is_alive=lambda:True),_closed=None)
        self.verifier=Mock(return_value=True)
        self.parent=channel.ParentChannel.create(root=self.measured/'channel',revision=self.revision,
            policy=self.policy,budget=self.budget,verify_quiescent=self.verifier)

    def child(self,bind=True):
        if bind:self.parent.bind(self.process)
        self.current=self.child_id
        return channel.ChildChannel(self.parent.root,self.parent.request_pin)

    def proof(self):
        path=self.parent.root/'proof.json';raw=channel.io.json_bytes({'kind':'protocol-fixture-only'})
        path.write_bytes(raw)
        return {'path':str(path),'pin':channel.observed._pin(raw)}

    def rewrite(self,name,value):
        # Deliberate fixture corruption, never an actual saved evidence root.
        (self.parent.root/name).write_bytes(channel.io.json_bytes(value))

    def test_request_holds_parent_clock_root_policy_and_external_pin(self):
        value,pin=channel._read(self.parent.root/'request.json')
        self.assertEqual(pin,self.parent.request_pin);self.assertEqual(value['parent_identity'],self.parent_id)
        self.assertEqual(value['clock']['started_at'],100.0);self.assertEqual(value['clock']['wall_seconds'],90)
        self.assertEqual(value['policy_pin'],self.policy['expected_pin'])
        self.assertIs(value['formal_permission'],False)

    def test_unbound_child_cannot_start_job_and_binding_wait_does_not_rearm_stop(self):
        child=self.child(bind=False)
        self.assertEqual(child.probe(),'source_channel_binding_pending')
        with self.assertRaises(ValueError):child.begin_job()
        self.parent.bind(self.process)
        self.assertIsNone(child.probe());self.assertEqual(child.begin_job(),0)

    def test_absent_ack_returns_false_and_latches_shared_stop(self):
        child=self.child();self.assertFalse(self.parent.fence(self.process))
        self.assertEqual(child.probe(),'source_channel_stopped')
        with self.assertRaises(ValueError):child.begin_job()
        self.verifier.assert_not_called()

    def test_common_deadline_denies_new_job_without_changing_original_wall(self):
        child=self.child();self.now=190.0
        self.assertEqual(child.probe(),'source_channel_stopped')
        with self.assertRaises(ValueError):child.begin_job()
        self.assertEqual(child.request['clock']['wall_seconds'],90)

    def test_wrong_request_pin_is_rejected(self):
        self.current=self.child_id
        with self.assertRaises(ValueError):channel.ChildChannel(self.parent.root,{'bytes':1,'sha256':'b'*64})

    def test_policy_changed_stops_probe_and_prevents_ack(self):
        child=self.child();self.policy_path.write_bytes(b'changed')
        self.assertEqual(child.probe(),'source_channel_invalid');self.assertIsNotNone(child.error)
        with self.assertRaises(ValueError):child.acknowledge(self.proof())
        self.assertFalse((self.parent.root/'ack.json').exists())

    def test_request_changed_is_not_a_new_clock_or_permission(self):
        child=self.child();value,_=channel._read(self.parent.root/'request.json')
        value['clock']['wall_seconds']=1800;self.rewrite('request.json',value)
        self.assertEqual(child.probe(),'source_channel_invalid')
        with self.assertRaises(ValueError):child.begin_job()

    def test_wrong_worker_creation_cannot_use_binding(self):
        self.parent.bind(self.process);self.current=identity(202,99)
        child=channel.ChildChannel(self.parent.root,self.parent.request_pin)
        self.assertEqual(child.probe(),'source_channel_invalid')
        with self.assertRaises(ValueError):child.begin_job()

    def test_binding_tamper_or_original_creation_change_cannot_release_parent(self):
        child=self.child();proof=self.proof();child.acknowledge(proof)
        self.child_id=identity(202,99)
        with self.assertRaises(ValueError):self.parent.fence(self.process)
        self.verifier.assert_not_called()

    def test_different_popen_cannot_rebind_or_use_fence(self):
        self.parent.bind(self.process)
        different=SimpleNamespace(pid=202,_handle=self.process._handle)
        with self.assertRaises(ValueError):self.parent.bind(different)
        with self.assertRaises(ValueError):self.parent.fence(different)
        self.verifier.assert_not_called()

    def test_active_or_original_critical_owner_blocks_ack_and_is_preserved(self):
        child=self.child();lease=child.begin_job();original=owner.UnreapedJob(11,22,33,{'status':'failed'})
        child.hold_owner(lease,original)
        with self.assertRaises(ValueError):child.acknowledge(self.proof())
        self.assertIs(child.owners[lease],original);self.assertEqual((original.job,original.process,original.thread),(11,22,33))
        self.assertFalse((self.parent.root/'ack.json').exists())
        self.assertEqual(child.probe(),'source_channel_stopped')

    def test_exit_close_raw_flags_must_all_be_explicit_true(self):
        child=self.child();lease=child.begin_job()
        for field in ('exit_confirmed','handles_closed','raw_preserved'):
            options={'exit_confirmed':True,'handles_closed':True,'raw_preserved':True};options[field]=False
            with self.subTest(field=field),self.assertRaises(ValueError):child.finish_job(lease,**options)
            self.assertIn(lease,child.active)
        child.finish_job(lease,exit_confirmed=True,handles_closed=True,raw_preserved=True)
        self.assertEqual(child.finished,1)

    def test_quiescent_ack_stops_all_future_jobs_and_needs_native_proof_verifier(self):
        child=self.child();lease=child.begin_job()
        child.finish_job(lease,exit_confirmed=True,handles_closed=True,raw_preserved=True)
        proof=self.proof();child.acknowledge(proof)
        with self.assertRaises(ValueError):child.begin_job()
        self.assertTrue(self.parent.fence(self.process))
        self.verifier.assert_called_once_with(Path(proof['path']).read_bytes(),1)

    def test_rejected_or_non_bool_native_proof_never_becomes_true(self):
        child=self.child();child.acknowledge(self.proof())
        self.verifier.return_value=False;self.assertFalse(self.parent.fence(self.process))
        self.verifier.return_value=1
        with self.assertRaises(ValueError):self.parent.fence(self.process)

    def test_proof_bytes_changed_after_ack_is_rejected_before_verifier(self):
        child=self.child();proof=self.proof();child.acknowledge(proof)
        Path(proof['path']).write_bytes(b'changed')
        with self.assertRaises(ValueError):self.parent.fence(self.process)
        self.verifier.assert_not_called()

    def test_changed_proof_during_verifier_cannot_release_parent(self):
        child=self.child();proof=self.proof();child.acknowledge(proof)
        def verify(raw,count):
            Path(proof['path']).write_bytes(b'changed-during-verification')
            return True
        self.verifier.side_effect=verify
        with self.assertRaises(ValueError):self.parent.fence(self.process)

    def test_outside_or_dotdot_proof_does_not_move_receipts_out_of_measured_root(self):
        child=self.child();outside=self.measured/'outside.json';outside.write_bytes(b'{}')
        for path in (outside,self.parent.root/'..'/'outside.json'):
            with self.subTest(path=path),self.assertRaises(ValueError):
                child.acknowledge({'path':str(path),'pin':channel.observed._pin(b'{}')})
        self.assertFalse((self.parent.root/'ack.json').exists())

    def test_ack_publication_io_failure_keeps_no_new_work_latched(self):
        child=self.child();proof=self.proof();failure=OSError('invented ack output failure')
        with patch.object(channel.io,'_exclusive',side_effect=failure):
            with self.assertRaises(OSError) as caught:child.acknowledge(proof)
        self.assertIs(caught.exception,failure)
        with self.assertRaises(ValueError):child.begin_job()
        self.assertFalse(self.parent.fence(self.process))

    def test_invalid_clock_or_closed_sampler_rejects_before_new_root(self):
        for kind in ('closed','wall','future'):
            with self.subTest(kind=kind):
                target=self.measured/kind
                budget=SimpleNamespace(**vars(self.budget))
                if kind=='closed':budget._closed={}
                if kind=='wall':budget.limits={'wall_seconds':1801}
                if kind=='future':budget.started_at=101.0
                with self.assertRaises(ValueError):
                    channel.ParentChannel.create(root=target,revision=self.revision,policy=self.policy,
                        budget=budget,verify_quiescent=self.verifier)
                self.assertFalse(target.exists())

    def test_root_or_request_reuse_is_rejected_without_overwrite(self):
        old=(self.parent.root/'request.json').read_bytes()
        with self.assertRaises(ValueError):
            channel.ParentChannel.create(root=self.parent.root,revision=self.revision,policy=self.policy,
                budget=self.budget,verify_quiescent=self.verifier)
        self.assertEqual((self.parent.root/'request.json').read_bytes(),old)

    def test_missing_required_native_verifier_has_no_new_root(self):
        target=self.measured/'no-verifier'
        with self.assertRaises(ValueError):
            channel.ParentChannel.create(root=target,revision=self.revision,policy=self.policy,
                budget=self.budget,verify_quiescent=None)
        self.assertFalse(target.exists())


class WorkerStopChannelPublicationTests(unittest.TestCase):
    """Only new publication/startup risks; all identities and Jobs are stubs."""
    setUp = WorkerStopChannelTests.setUp
    child = WorkerStopChannelTests.child
    proof = WorkerStopChannelTests.proof

    def test_partial_binding_stage_is_pending_until_complete_publication(self):
        child=self.child(bind=False);write=channel.io._exclusive;seen=[]
        def staging(path,raw):
            if path.name=='binding.json.pending':
                path.write_bytes(raw[:20]);seen.append(child.probe())
                self.assertFalse((self.parent.root/'binding.json').exists())
                path.write_bytes(raw)
            else:write(path,raw)
        with patch.object(channel.io,'_exclusive',side_effect=staging):self.parent.bind(self.process)
        self.assertEqual(seen,['source_channel_binding_pending']);self.assertIsNone(child.error)
        self.assertIsNone(child.wait_for_binding());self.assertEqual(child.begin_job(),0)
        self.assertFalse((self.parent.root/'binding.json.pending').exists())

    def test_partial_binding_failure_keeps_original_popen_under_supervisor_fence(self):
        from banto_ai import anomaly_v03_process_supervisor as monitor
        from tests import test_anomaly_v03_process_supervisor as helpers
        process=helpers.FakeProcess(running=True);process.pid=202;self.process=process
        child=self.child(bind=False);failure=OSError('invented partial binding write');write=channel.io._exclusive
        def staging(path,raw):
            if path.name=='binding.json.pending':path.write_bytes(raw[:20]);raise failure
            write(path,raw)
        with patch.object(channel.io,'_exclusive',side_effect=staging), \
             patch.object(monitor.subprocess,'CREATE_NO_WINDOW',0x08000000,create=True), \
             patch.object(monitor.subprocess,'Popen',return_value=process), \
             patch.object(monitor.resources,'memory_bytes',return_value={'peak_private_bytes':1000}), \
             patch.object(monitor.resources,'require_start_resources',return_value={}), \
             patch.object(monitor.resources,'free_resources',return_value={}):
            with self.assertRaises(monitor.UnreconciledWorker) as caught:
                monitor.supervise(['python','fixture-only'],self.root,self.measured/'control',
                    {'wall_seconds':60,'private_bytes':1024**3,'output_bytes':1024**2},
                    runtime_probe=lambda:helpers.fixture_context()[1],
                    on_started=self.parent.bind,stop_fence=self.parent.fence)
        self.assertIs(caught.exception.process,process);self.assertIs(self.parent.worker,process)
        self.assertIs(self.parent.binding_error,failure);self.assertIsNotNone(self.parent.binding_pin)
        self.assertEqual((process.kills,process.waits),(0,0));process._handle.Close.assert_not_called()
        self.assertTrue((self.parent.root/'binding.json.pending').exists())
        self.assertFalse((self.parent.root/'binding.json').exists());self.assertFalse((self.parent.root/'ack.json').exists())
        self.assertEqual(child.probe(),'source_channel_stopped')
        with self.assertRaises(ValueError):self.parent.bind(process)

    def test_binding_stage_readback_failure_never_publishes_and_keeps_owner(self):
        read=channel._read;failure=OSError('invented stage read failure')
        def checked(path,pin=None):
            if path.name=='binding.json.pending':raise failure
            return read(path,pin)
        with patch.object(channel,'_read',side_effect=checked):
            with self.assertRaises(OSError):self.parent.bind(self.process)
        self.assertIs(self.parent.binding_error,failure);self.assertIs(self.parent.worker,self.process)
        self.assertTrue((self.parent.root/'binding.json.pending').exists())
        self.assertFalse((self.parent.root/'binding.json').exists());self.assertFalse(self.parent.fence(self.process))

    def test_binding_final_readback_failure_still_stops_published_child(self):
        child=self.child(bind=False);read=channel._read;failure=OSError('invented final read failure')
        def checked(path,pin=None):
            if path.name=='binding.json':raise failure
            return read(path,pin)
        with patch.object(channel,'_read',side_effect=checked):
            with self.assertRaises(OSError):self.parent.bind(self.process)
        self.assertIs(self.parent.binding_error,failure);self.assertIsNone(child.probe())
        self.assertFalse(self.parent.fence(self.process));self.assertEqual(child.probe(),'source_channel_stopped')
        self.assertIs(self.parent.worker,self.process);self.verifier.assert_not_called()

    def test_live_read_failure_before_binding_keeps_original_owner_and_error(self):
        child=self.child(bind=False);failure=KeyboardInterrupt('invented request read interruption')
        with patch.object(self.parent,'_live',side_effect=failure):
            with self.assertRaises(KeyboardInterrupt):self.parent.bind(self.process)
        self.assertIs(self.parent.worker,self.process);self.assertIs(self.parent.binding_error,failure)
        self.assertFalse(self.parent.fence(self.process));self.assertEqual(child.probe(),'source_channel_stopped')

    def test_partial_stop_write_latches_child_without_ack_or_new_job(self):
        child=self.child();write=channel.io._exclusive;failure=OSError('invented stop write')
        def staging(path,raw):
            if path.name=='stop.json.pending':path.write_bytes(raw[:20]);raise failure
            write(path,raw)
        with patch.object(channel.io,'_exclusive',side_effect=staging):
            with self.assertRaises(OSError):self.parent.fence(self.process)
        self.assertEqual(child.probe(),'source_channel_stopped')
        with self.assertRaises(ValueError):child.begin_job()
        self.assertFalse((self.parent.root/'stop.json').exists());self.verifier.assert_not_called()
        # A second fence preserves the failed staging file instead of rewriting it.
        before=(self.parent.root/'stop.json.pending').read_bytes()
        with self.assertRaises(FileExistsError):self.parent.fence(self.process)
        self.assertEqual((self.parent.root/'stop.json.pending').read_bytes(),before)
        self.assertIs(self.parent.worker,self.process)

    def test_partial_ack_write_is_not_parent_cleanup_permission(self):
        child=self.child();proof=self.proof();write=channel.io._exclusive;failure=OSError('invented ack write')
        def staging(path,raw):
            if path.name=='ack.json.pending':path.write_bytes(raw[:20]);raise failure
            write(path,raw)
        with patch.object(channel.io,'_exclusive',side_effect=staging):
            with self.assertRaises(OSError):child.acknowledge(proof)
        self.assertFalse(self.parent.fence(self.process));self.verifier.assert_not_called()
        self.assertTrue(child.stopped);self.assertTrue((self.parent.root/'ack.json.pending').exists())

    def test_atomic_publish_cannot_replace_existing_frame_or_discard_new_stage(self):
        path=self.parent.root/'collision.json';old=channel.io.json_bytes({'old':True});path.write_bytes(old)
        with self.assertRaises(OSError):channel._write(path,{'new':True})
        self.assertEqual(path.read_bytes(),old)
        self.assertEqual((self.parent.root/'collision.json.pending').read_bytes(),channel.io.json_bytes({'new':True}))

    def test_rename_failure_keeps_completed_stage_and_no_new_work(self):
        child=self.child();proof=self.proof();failure=KeyboardInterrupt('invented rename interruption')
        with patch.object(channel.io,'_rename_no_replace',side_effect=failure):
            with self.assertRaises(KeyboardInterrupt):child.acknowledge(proof)
        self.assertTrue(child.stopped);self.assertFalse((self.parent.root/'ack.json').exists())
        channel._read(self.parent.root/'ack.json.pending')
        self.assertFalse(self.parent.fence(self.process));self.assertIs(self.parent.worker,self.process)

    def test_binding_wait_uses_remaining_common_clock_and_finishes_when_published(self):
        child=self.child(bind=False);sleeps=[]
        def sleep(duration):
            sleeps.append(duration);self.now+=duration;self.parent.bind(self.process)
        with patch.object(channel.time,'sleep',side_effect=sleep):self.assertIsNone(child.wait_for_binding())
        self.assertEqual(sleeps,[0.25]);self.assertEqual(child.request['clock']['started_at'],100.0)
        self.assertEqual(child.request['clock']['wall_seconds'],90)

    def test_binding_wait_deadline_has_no_new_job_or_native_proof(self):
        child=self.child(bind=False);self.now=189.9;sleeps=[]
        def sleep(duration):sleeps.append(duration);self.now+=duration
        with patch.object(channel.time,'sleep',side_effect=sleep):
            self.assertEqual(child.wait_for_binding(),'source_channel_stopped')
        self.assertEqual(len(sleeps),1);self.assertAlmostEqual(sleeps[0],0.1)
        with self.assertRaises(ValueError):child.begin_job()
        self.verifier.assert_not_called()

    def test_binding_wait_interruption_keeps_original_error_and_never_rearms(self):
        child=self.child(bind=False);failure=KeyboardInterrupt('invented startup sleep interruption')
        with patch.object(channel.time,'sleep',side_effect=failure):
            self.assertEqual(child.wait_for_binding(),'source_channel_invalid')
        self.assertIs(child.error,failure);self.parent.bind(self.process)
        self.assertEqual(child.probe(),'source_channel_stopped')
        with self.assertRaises(ValueError):child.begin_job()

    def test_ack_staging_read_failure_preserves_stage_and_child_stop_latch(self):
        child=self.child();proof=self.proof();read=channel._read;failure=OSError('invented ack stage read')
        def checked(path,pin=None):
            if path.name=='ack.json.pending':raise failure
            return read(path,pin)
        with patch.object(channel,'_read',side_effect=checked):
            with self.assertRaises(OSError):child.acknowledge(proof)
        self.assertTrue(child.stopped);self.assertTrue((self.parent.root/'ack.json.pending').exists())
        self.assertFalse(self.parent.fence(self.process));self.verifier.assert_not_called()
