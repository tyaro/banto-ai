"""Verified lease/compact proof gates with fake Kernel and executable facts."""
import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_worker_git_proof as proof
from tests.test_anomaly_v03_git_quiescence import GitQuiescenceTests, ACCOUNT

channel, tree, keepers = proof.channel, proof.tree, proof.keepers


def identity(pid, created):
    value = {'pid':pid,'creation_time_100ns':created}
    return {**value,'start_token':tree.v.canonical_sha256(value)}


class WorkerGitProofTests(unittest.TestCase):
    def setUp(self):
        # Only reuse fixture construction/execution helpers, never the old suite.
        GitQuiescenceTests.setUp(self)
        self.enterContext(patch.object(channel,'ROOT',self.root))
        self.now = 100.0
        self.enterContext(patch.object(channel.time,'monotonic',side_effect=lambda:self.now))
        self.parent_id, self.child_id = identity(101,11), identity(202,22)
        self.current = self.parent_id
        self.process = SimpleNamespace(pid=202,_handle=object())
        def creation(pid, handle=None):
            return dict(self.child_id if handle is not None else self.current)
        self.enterContext(patch.object(channel.observed,'creation_observation',side_effect=creation))
        self.measured = self.root/'artifacts'/'budget'; self.measured.mkdir(parents=True)
        policy_root = self.root/'artifacts'/'external-policy'; policy_root.mkdir()
        path = policy_root/'policy.json'; raw = tree.io.json_bytes(self.policy); path.write_bytes(raw)
        policy_entry = {'path':str(path),'expected_pin':tree.observed._pin(raw)}
        budget = SimpleNamespace(root=self.measured,started_at=100.0,limits={'wall_seconds':90},
            probe=lambda:None,_thread=SimpleNamespace(is_alive=lambda:True),_closed=None)
        self.parent = channel.ParentChannel.create(root=self.measured/'channel',revision=self.revision,
            policy=policy_entry,budget=budget,verify_quiescent=lambda raw,count:False)
        self.parent.bind(self.process); self.current = self.child_id
        self.child = channel.ChildChannel(self.parent.root,self.parent.request_pin)
        self.packets = {}
        request = self.parent.request
        self.inventory = {'format':proof.FORMAT+'-inventory','request_pin':self.parent.request_pin,
            'revision':self.revision,'root':request['root'],'root_identity':request['root_identity'],
            'policy_pin':request['policy_pin'],'repository':str(self.root),
            'calls':[self.call(0)],'formal_permission':False}

    def call(self, lease, phase='pre'):
        return {'lease':lease,'phase':phase,'operation':'head','source_path':None,
                'expected_output_pin':None,'raw_inventory':{'receipt.json':16384,
                    'stdout.bin':128,'stderr.bin':65536,'partial-archive.bin':524288}}

    def configure(self):
        raw = tree.io.json_bytes(self.inventory); pin = tree.observed._pin(raw)
        options = {'inventory_raw':raw,'inventory_pin':pin,'read_evidence':lambda lease:self.packets[lease]}
        self.verifier = proof.ProofVerifier(endpoint=self.child,**options)
        self.parent_verifier = proof.ProofVerifier(endpoint=self.parent,**options)
        self.parent.verify_quiescent = self.parent_verifier.verify
        self.adapter = proof.VerifiedLeases(child=self.child,verifier=self.verifier)

    def receipt(self, lease=0, code=0):
        result, target, _ = GitQuiescenceTests.run_call(self,code=code)
        self.packets[lease] = {'kind':'receipt','raw':{
            name:(target/name).read_bytes() for name in ('receipt.json','stdout.bin','stderr.bin')},
            'event':result['quiescence']}
        self.packets[lease]['raw']['partial-archive.bin'] = None
        return target

    def recovery(self):
        original = tree.owner.UnreapedJob(11,22,33,{'assignment_confirmed':True},
                                        extra_handles={'inherited_0':55})
        keeper = keepers.ChildGitKeeper(original,child=self.child,lease=0)
        kernel = SimpleNamespace(TerminateJobObject=Mock(return_value=True),CloseHandle=Mock(return_value=True))
        with patch.object(tree.owner,'_kernel',return_value=kernel), \
             patch.object(tree.owner,'_wait_empty',return_value=(ACCOUNT,17)), \
             patch.object(keepers,'_creation',return_value=identity(44,11)):
            event = keeper.reconcile_once()
        self.packets[0] = {'kind':'recovery','raw':{'receipt.json':b'{partial receipt',
            'stdout.bin':b'partial stdout','stderr.bin':b'original failure',
            'partial-archive.bin':b'partial archive'},'event':event}
        return keeper, kernel

    def test_normal_raw_close_then_lease_proof_and_real_parent_fence_path(self):
        self.configure(); self.child.begin_job(); self.receipt()
        self.adapter.finish(0); self.adapter.acknowledge()
        self.assertTrue(self.parent.fence(self.process))
        self.assertEqual(self.child.finished,1); self.assertFalse(self.child.active)
        self.assertIsNone(self.adapter.error)
        self.assertLess((self.child.root/'git-proof.json').stat().st_size,32768)
        self.assertIs(self.inventory['formal_permission'],False)

    def test_failed_receipt_can_finish_safely_but_stops_new_jobs_and_stays_failed(self):
        self.configure(); self.child.begin_job(); self.receipt(code=17)
        self.adapter.finish(0); self.adapter.acknowledge()
        self.assertTrue(self.parent.fence(self.process))
        with self.assertRaises(ValueError): self.child.begin_job()
        raw=(self.child.root/'git-proof.json').read_bytes()
        self.assertEqual(tree.v.strict_json(raw)['terminal'],'failed')

    def test_recovery_requires_exact_live_keeper_and_preserves_all_partial_raw(self):
        self.configure(); self.child.begin_job(); keeper,kernel = self.recovery()
        before = copy.deepcopy(self.packets[0]['raw'])
        self.adapter.finish(0,keeper=keeper); self.adapter.acknowledge()
        self.assertTrue(self.parent.fence(self.process))
        self.assertIs(self.adapter.kept[0],keeper); self.assertEqual(self.packets[0]['raw'],before)
        self.assertEqual(kernel.CloseHandle.call_count,4)
        self.assertIs(keeper.completion['failure_raw_verified'],False)
        self.assertIs(keeper.completion['lease_completed'],False)

    def test_recovery_metadata_without_keeper_cannot_remove_original_owner(self):
        self.configure(); self.child.begin_job(); keeper,_ = self.recovery()
        with self.assertRaises(ValueError): self.adapter.finish(0)
        self.assertIs(self.child.owners[0],keeper.original); self.assertEqual(self.child.active,{0})
        with self.assertRaises(ValueError): self.adapter.acknowledge()
        self.assertFalse((self.child.root/'ack.json').exists())

    def test_unknown_cleanup_cannot_release_even_with_copied_completion(self):
        self.configure(); self.child.begin_job(); keeper,_ = self.recovery()
        keeper.original.attribute_list_cleanup_pending = True
        with self.assertRaises(ValueError): self.adapter.finish(0,keeper=keeper)
        self.assertIs(self.child.owners[0],keeper.original)
        self.assertIs(keeper.original.proof_adapter,self.adapter)

    def test_receipt_cannot_replace_an_unresolved_original_unclosed_owner(self):
        self.configure(); self.child.begin_job(); self.receipt()
        original=tree.owner.UnclosedHandles({'job':11},{})
        self.child.hold_owner(0,original)
        with self.assertRaises(ValueError): self.adapter.finish(0)
        self.assertIs(self.child.owners[0],original); self.assertEqual(self.child.finished,0)

    def test_raw_inventory_missing_changed_or_oversized_denies_finish(self):
        self.configure(); self.child.begin_job(); self.receipt()
        original=copy.deepcopy(self.packets[0])
        for mode in ('missing','changed','oversized'):
            self.adapter=proof.VerifiedLeases(child=self.child,verifier=self.verifier)
            self.packets[0]=copy.deepcopy(original)
            if mode=='missing': del self.packets[0]['raw']['stderr.bin']
            if mode=='changed': self.packets[0]['raw']['stdout.bin']=b'changed'
            if mode=='oversized': self.packets[0]['raw']['stdout.bin']=b'x'*129
            with self.subTest(mode=mode),self.assertRaises(ValueError): self.adapter.finish(0)
            self.assertEqual(self.child.finished,0); self.assertEqual(self.child.active,{0})

    def test_wrong_phase_plan_or_inventory_pin_is_rejected_before_raw_reader(self):
        self.inventory['calls'][0]['phase']='unknown'
        with self.assertRaises(ValueError): self.configure()
        self.inventory['calls'][0]['phase']='pre'
        raw=tree.io.json_bytes(self.inventory)
        reader=Mock()
        with self.assertRaises(ValueError): proof.ProofVerifier(endpoint=self.child,inventory_raw=raw,
            inventory_pin={'bytes':1,'sha256':'b'*64},read_evidence=reader)
        reader.assert_not_called()

    def test_wrong_operation_receipt_cannot_complete_planned_call(self):
        self.inventory['calls'][0].update(operation='status')
        self.configure(); self.child.begin_job(); self.receipt()
        with self.assertRaises(ValueError): self.adapter.finish(0)
        self.assertEqual(self.child.finished,0)

    def test_read_interruption_retains_original_keeper_and_no_ack(self):
        self.configure(); self.child.begin_job(); keeper,_=self.recovery()
        failure=KeyboardInterrupt('invented raw read interruption')
        self.verifier.read_evidence=Mock(side_effect=failure)
        with self.assertRaises(KeyboardInterrupt): self.adapter.finish(0,keeper=keeper)
        self.assertIs(self.adapter.error,failure); self.assertIs(self.adapter.kept[0],keeper)
        self.assertIs(self.child.owners[0],keeper.original); self.assertEqual(self.child.active,{0})

    def test_raw_change_between_first_and_second_read_cannot_finish_lease(self):
        self.configure(); self.child.begin_job(); self.receipt()
        first=copy.deepcopy(self.packets[0]);second=copy.deepcopy(first)
        second['raw']['stderr.bin']=b'changed'
        self.verifier.read_evidence=Mock(side_effect=[first,second])
        with self.assertRaises(ValueError): self.adapter.finish(0)
        self.assertEqual(self.child.finished,0); self.assertEqual(self.child.active,{0})

    def test_raw_change_after_finish_is_rejected_by_independent_parent_verifier(self):
        self.configure(); self.child.begin_job(); self.receipt();self.adapter.finish(0)
        self.adapter.acknowledge();self.packets[0]['raw']['stdout.bin']=b'changed'
        with self.assertRaises(ValueError):self.parent.fence(self.process)

    def test_ack_publication_interruption_cannot_rearm_or_drop_partial_evidence(self):
        self.configure();self.child.begin_job();self.receipt();self.adapter.finish(0)
        failure=OSError('invented ack IO failure')
        with patch.object(self.child,'acknowledge',side_effect=failure):
            with self.assertRaises(OSError):self.adapter.acknowledge()
        self.assertIs(self.adapter.error,failure);self.assertTrue(self.child.stopped)
        self.assertTrue((self.child.root/'git-proof.json').exists())
        self.assertFalse(self.parent.fence(self.process))

    def test_successful_prefix_is_not_complete_and_wrong_count_or_flags_cannot_authorize(self):
        self.inventory['calls'].append(self.call(1,'post'))
        self.configure();self.child.begin_job();self.receipt();self.adapter.finish(0)
        with self.assertRaises(ValueError):self.adapter.acknowledge()
        self.assertFalse((self.child.root/'ack.json').exists())

    def test_reused_original_process_identity_is_rejected_in_full_proof(self):
        self.inventory['calls'].append(self.call(1,'post'))
        self.configure();self.child.begin_job();self.receipt();self.adapter.finish(0)
        self.child.begin_job();self.receipt(1);self.adapter.finish(1)
        with self.assertRaises(ValueError):self.adapter.acknowledge()
        self.assertFalse((self.child.root/'ack.json').exists())

    def test_sixty_four_distinct_saved_calls_fit_compact_bound_without_new_native_runs(self):
        self.inventory['calls']=[self.call(n,'pre' if n<32 else 'post') for n in range(64)]
        self.configure();self.receipt();template=copy.deepcopy(self.packets[0])
        for lease in range(64):
            packet=copy.deepcopy(template);saved=tree.v.strict_json(packet['raw']['receipt.json'])
            native={**identity(1000+lease,2000+lease),'native_start_identity_authenticated':True}
            saved['process_identity']=native
            packet['raw']['receipt.json']=tree.io.json_bytes(saved)
            packet['event']['process_identity']=native
            packet['event']['receipt_pin']=tree.observed._pin(packet['raw']['receipt.json'])
            self.packets[lease]=packet
            self.child.begin_job();self.adapter.finish(lease)
        self.adapter.acknowledge();self.assertTrue(self.parent.fence(self.process))
        self.assertEqual(self.child.finished,64)
        self.assertLess((self.child.root/'git-proof.json').stat().st_size,32768)
        self.assertEqual(self.number,1)  # One fake executor fixture; no native replay.

    def test_count_boolean_or_added_permission_cannot_authorize_parent_proof(self):
        self.configure();self.child.begin_job();self.receipt();self.adapter.finish(0)
        raw=self.verifier.proof(self.adapter.records)
        with self.assertRaises(ValueError):self.parent_verifier.verify(raw,True)
        with self.assertRaises(ValueError):self.parent_verifier.verify(raw,2)
        value=tree.v.strict_json(raw);value['formal_permission']=True
        self.assertFalse(self.parent_verifier.verify(tree.io.json_bytes(value),1))

    def test_failed_prefix_preserves_planned_later_calls_without_starting_them(self):
        self.inventory['calls'].append(self.call(1,'post'))
        self.configure();self.child.begin_job();self.receipt(code=17);self.adapter.finish(0)
        self.adapter.acknowledge();self.assertTrue(self.parent.fence(self.process))
        self.assertEqual(self.child.finished,1);self.assertNotIn(1,self.packets)
