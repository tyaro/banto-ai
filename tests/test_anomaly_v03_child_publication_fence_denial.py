"""No child-local IO recovery from a complete ack/proof or a True stub verdict."""
import copy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_reader_git_worker as reader
from tests import test_anomaly_v03_parent_inventory_publication as fixtures

channel,archive=reader.channel,reader.actors.archive


class ChildPublicationFenceDenialTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ParentInventoryPublicationTests();self.f.setUp();self.addCleanup(self.f.doCleanups)

    def parent(self, *, gated=True):
        p=self.f.create() if gated else self.f.f.create()
        p.bind(self.f.f.f.process)
        return p

    def preview(self, p, *, ack=True):
        binding,_=p.parent._binding();proof_path=p.parent.root/'git-proof.json'
        pin=channel._write(proof_path,{})
        value={'format':channel.FORMAT+'-ack','request_pin':p.parent.request_pin,'binding_pin':p.parent.binding_pin,
            'worker_identity':binding['worker_identity'],'no_new_jobs':True,'jobs_finished':1,
            'proof':{'path':str(proof_path),'pin':pin}}
        if ack:channel._write(p.parent.root/'ack.json',value)
        verifier=Mock(return_value=True);p.parent.verify_quiescent=verifier  # Explicit stub; no native authorization.
        return value,verifier

    def test_exact_completed_ack_and_true_proof_keep_original_raw_context_and_refuse_parent_ack(self):
        p=self.parent();ack,verifier=self.preview(p)
        self.assertFalse(p.fence(self.f.f.f.process));verifier.assert_called_once()
        denied=p.original_child_publication_denial;obs=denied['observation']
        self.assertIs(denied['process'],self.f.f.f.process);self.assertIs(denied['endpoint'],p.parent)
        self.assertIs(obs,p.parent.pending_child_publication)
        self.assertEqual(obs['ack']['raw'],reader.io.json_bytes(ack));self.assertEqual(obs['proof_raw'],reader.io.json_bytes({}))
        context=reader.v.strict_json(denied['context_raw'])
        self.assertEqual(context['request_pin'],p.parent.request_pin);self.assertEqual(context['inventory_pin'],p.entry['inventory_pin'])
        self.assertEqual(context['root'],str(p.parent.root));self.assertEqual(context['worker_identity'],ack['worker_identity'])
        self.assertIsNone(denied['child_close_rename_owner_observation'])
        self.assertFalse(denied['parent_ack_authorized']);self.assertFalse(denied['execution_authenticated'])

    def test_missing_ack_stays_false_without_a_proof_call_or_denial_preview(self):
        p=self.parent();_,verifier=self.preview(p,ack=False)
        self.assertFalse(p.fence(self.f.f.f.process));verifier.assert_not_called()
        self.assertIsNone(p.original_child_publication_denial)

    def test_child_unknown_rename_after_actual_ack_publication_cannot_become_parent_permission(self):
        p=self.parent();_,verifier=self.preview(p,ack=False)
        self.f.f.f.current=self.f.f.f.child_id
        child=channel.ChildChannel(p.parent.root,p.parent.request_pin);child.finished=1
        owner=SimpleNamespace();gate=archive.ControlPublicationAdmission(endpoint=child,inventory_pin=p.entry['inventory_pin'],
            root_identity=tuple(p.entry['budget_root_identity']),control_limits=self.f.controls,
            checkpoint=lambda:None,owner=owner)
        rename=channel.io._rename_no_replace;failure=KeyboardInterrupt('unknown child ack rename return')
        def unknown(src,dst):
            value=rename(src,dst)
            if Path(dst)==p.parent.root/'ack.json':raise failure
            return value
        proof=p.parent.root/'git-proof.json'
        with patch.object(channel.io,'_rename_no_replace',side_effect=unknown),self.assertRaises(KeyboardInterrupt) as caught:
            child.acknowledge({'path':str(proof),'pin':reader.observed._pin(proof.read_bytes())},publication_admission=gate)
        self.assertIs(caught.exception,failure);self.assertIs(gate.error,failure)
        pending=gate.pending;self.assertTrue(pending['stream'].closed);self.assertTrue(pending['close_return_observed'])
        self.assertTrue((p.parent.root/'ack.json').exists());self.assertNotIn('rename_return',pending)
        self.assertFalse(p.fence(self.f.f.f.process));verifier.assert_called_once()
        self.assertIs(gate.pending,pending);self.assertIs(pending['owner'],owner)
        self.assertFalse(p.original_child_publication_denial['parent_ack_authorized'])

    def test_worker_exit_closed_and_success_metadata_never_supply_child_original_io_observation(self):
        p=self.parent();_,verifier=self.preview(p)
        process=self.f.f.f.process;process.returncode=0;process.closed=True;process.released=True
        p.parent.child_io_released=True;p.parent.parent_ack_authorized=True
        self.assertFalse(p.fence(process));verifier.assert_called_once()
        self.assertIsNone(p.original_child_publication_denial['child_close_rename_owner_observation'])

    def test_cached_denial_never_repeats_proof_creation_clock_raw_or_file_io(self):
        p=self.parent();_,verifier=self.preview(p);self.assertFalse(p.fence(self.f.f.f.process))
        denied=p.original_child_publication_denial;context=denied['context_raw']
        with (patch.object(channel.observed,'creation_observation') as creation,
              patch.object(channel.observed,'_file') as read,patch.object(p,'_inventory_ready') as inventory,
              patch.object(p.shared,'checkpoint') as clock):
            self.assertFalse(p.fence(self.f.f.f.process))
        creation.assert_not_called();read.assert_not_called();inventory.assert_not_called();clock.assert_not_called()
        verifier.assert_called_once();self.assertIs(p.original_child_publication_denial,denied)
        self.assertEqual(denied['context_raw'],context)

    def test_direct_channel_cached_denial_is_false_and_keeps_original_gate_without_new_io(self):
        p=self.parent();_,verifier=self.preview(p);self.assertFalse(p.fence(self.f.f.f.process))
        with patch.object(channel.observed,'_file') as read:
            self.assertFalse(p.parent.fence(self.f.f.f.process,publication_admission=p.inventory_publication))
        read.assert_not_called();verifier.assert_called_once()
        self.assertIs(p.parent.original_child_publication_denial,p.original_child_publication_denial)

    def test_foreign_popen_after_denial_is_retained_and_original_error_latched_without_reobservation(self):
        p=self.parent();_,verifier=self.preview(p);self.assertFalse(p.fence(self.f.f.f.process))
        denied=p.original_child_publication_denial;foreign=SimpleNamespace(pid=909,_handle=object())
        with self.assertRaises(ValueError) as caught:p.fence(foreign)
        self.assertEqual(p.rejected_child_publication_fence,(denied,foreign))
        with self.assertRaises(ValueError) as repeat:p.fence(self.f.f.f.process)
        self.assertIs(repeat.exception,caught.exception);self.assertIs(p.worker,self.f.f.f.process)
        verifier.assert_called_once()

    def test_inventory_context_mutation_in_true_proof_callback_refuses_and_keeps_preview_raw(self):
        p=self.parent();ack,_=self.preview(p);original=copy.deepcopy(p.entry['inventory_pin'])
        def changed(*_):p.entry['inventory_pin']=reader.observed._pin(b'foreign inventory');return True
        p.parent.verify_quiescent=changed
        with self.assertRaises(ValueError):p.fence(self.f.f.f.process)
        self.assertEqual(p.inventory_publication.inventory_pin,original)
        self.assertEqual(p.parent.pending_child_publication['ack']['raw'],reader.io.json_bytes(ack))
        self.assertIsNone(p.original_child_publication_denial)

    def test_invalid_ack_keeps_actual_changed_raw_before_json_validation_or_proof_callback(self):
        p=self.parent();_,verifier=self.preview(p);(p.parent.root/'ack.json').write_bytes(b'not canonical JSON')
        with self.assertRaises(ValueError) as caught:p.fence(self.f.f.f.process)
        self.assertEqual(p.parent.pending_child_publication['ack']['raw'],b'not canonical JSON')
        verifier.assert_not_called()
        with self.assertRaises(ValueError) as repeat:p.fence(self.f.f.f.process)
        self.assertIs(repeat.exception,caught.exception);self.assertIs(p.worker,self.f.f.f.process)

    def test_default_channel_keeps_legacy_explicit_proof_verdict_without_new_child_denial(self):
        p=self.parent(gated=False);self.preview(p)
        self.assertTrue(p.fence(self.f.f.f.process));self.assertIsNone(p.original_child_publication_denial)
        self.assertFalse(hasattr(p.parent,'pending_child_publication'))
