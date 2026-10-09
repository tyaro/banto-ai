"""Original diagnostic bytes reach the fenced IO ingress without reopening it.

Upstream publication composition and fixture archive construction are stubbed.
No native process, child transport or actual diagnostic FileIO is authorized.
"""
import base64
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

from banto_ai import anomaly_v03_preformal_reader_git_worker as reader
from tests import test_anomaly_v03_generate_auxiliary_callsite as fixtures

OBSERVATIONS=[]


class GenerateDiagnosticPublicationTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.GenerateAuxiliaryCallsiteTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.parent=self.f.parent;self.writer=self.f.f.writers['diagnostic']

    def candidate(self,result=None,error=None):
        error=OSError('original diagnostic publication fence') if error is None else error
        callsite=(error,'reader',Path('original-target'),{} if result is None else result)
        keeper=reader.ParentPublicationRetention(self.parent,error,(self.writer,),None)
        with self.assertRaises(BaseException) as stopped:self.writer.retain_callsite_inputs(keeper,callsite)
        self.assertIs(stopped.exception,error)
        candidate=self.writer.prepare_callsite_diagnostic(keeper,callsite)
        return keeper,callsite,candidate

    def record(self,held):
        OBSERVATIONS.append({'test':self.id(),'raw_base64':base64.b64encode(held['raw']).decode() if type(held['raw']) is bytes else None,
            'name':held['name'],'return_observed':held['return_observed'],'error_type':type(held['error']).__name__,
            'published':held['published'],'native_authorized':False,'formal_permission':False})

    def test_actual_generate_candidate_reaches_same_publish_ingress_and_refuses_before_io(self):
        error=OSError('original generate failure');caller=self.f.caller(error);original=self.writer.publish
        with (patch.object(self.writer,'publish',wraps=original) as publish,
              patch.object(reader.actors.archive.proof.tree.file_io,'FileIO') as opened,
              patch.object(reader.ParentPublicationRetention,'_pause',side_effect=fixtures.RetentionEscape()),
              self.assertRaises(fixtures.RetentionEscape)):
            caller.execute()
        keeper=error.parent_publication_retention;candidate=self.writer._RequestAuxiliaryWriter__diagnostic_candidate
        held=self.writer._RequestAuxiliaryWriter__diagnostic_publication
        publish.assert_called_once_with('diagnostic.json',candidate['raw']);opened.assert_not_called()
        self.f.f.clock.assert_not_called();self.assertIs(held['error'],error);self.assertFalse(held['return_observed'])
        self.assertIs(held['raw'],candidate['raw']);self.assertEqual(held['path'],self.writer.storage.root/'diagnostic.json')
        self.assertIs(self.writer.rejected_publication[1],candidate['raw']);self.assertIs(self.writer.storage.original_error,error)
        self.assertEqual(self.writer._RequestAuxiliaryWriter__operations,());self.assertFalse(held['path'].exists())
        self.assertFalse((caller.f.attempt/'owned-generator/result.json').exists())
        row=keeper.auxiliary_callsite['observations'][-1];self.assertIs(row['diagnostic_publication'],held)
        self.assertTrue(row['diagnostic_publication_return_observed']);self.record(held)

    def test_unknown_callback_return_is_retained_without_publication_rights(self):
        keeper,callsite,candidate=self.candidate();unknown=object()
        with patch.object(self.writer,'publish',return_value=unknown) as publish:
            held=self.writer.prepare_callsite_diagnostic_publication(keeper,callsite,candidate)
        publish.assert_called_once_with('diagnostic.json',candidate['raw']);self.assertIs(held['return'],unknown)
        self.assertTrue(held['return_observed']);self.assertIsInstance(held['error'],ValueError)
        self.assertFalse(held['published']);self.assertIs(self.writer._RequestAuxiliaryWriter__failure,callsite[0])
        self.assertIs(self.writer._RequestAuxiliaryWriter__diagnostic_publication_state[2],unknown);self.record(held)

    def test_callback_swallowing_original_refusal_keeps_original_error_and_unknown_return(self):
        keeper,callsite,candidate=self.candidate();original=self.writer.publish;unknown=object();seen=[]
        def swallow(name,raw):
            try:original(name,raw)
            except BaseException as error:seen.append(error)
            return unknown
        with patch.object(self.writer,'publish',side_effect=swallow):
            held=self.writer.prepare_callsite_diagnostic_publication(keeper,callsite,candidate)
        self.assertEqual(seen,[callsite[0]]);self.assertIs(held['return'],unknown);self.assertFalse(held['published'])
        self.assertIs(self.writer.storage.original_error,callsite[0]);self.record(held)

    def test_foreign_candidate_is_retained_but_never_forwarded(self):
        keeper,callsite,candidate=self.candidate();foreign=dict(candidate)
        with patch.object(self.writer,'publish') as publish:
            held=self.writer.prepare_callsite_diagnostic_publication(keeper,callsite,foreign)
        publish.assert_not_called();self.assertIs(held['incoming'][2],foreign);self.assertIs(held['raw'],candidate['raw'])
        self.assertIsInstance(held['error'],ValueError);self.record(held)

    def test_candidate_raw_mutation_refuses_before_publish_and_retains_private_bytes(self):
        keeper,callsite,candidate=self.candidate();raw=candidate['raw'];candidate['raw']=b'changed'
        with patch.object(self.writer,'publish') as publish:
            held=self.writer.prepare_callsite_diagnostic_publication(keeper,callsite,candidate)
        publish.assert_not_called();self.assertIs(held['raw'],raw)
        self.assertIsInstance(held['error'],ValueError);self.record(held)

    def test_original_maximum_mutation_refuses_before_publish_without_new_codec(self):
        keeper,callsite,candidate=self.candidate();self.writer.limits['diagnostic.json']=2049
        with patch.object(self.writer,'publish') as publish,patch.object(reader,'DIAGNOSTIC_JSON_ENCODER') as encoder:
            held=self.writer.prepare_callsite_diagnostic_publication(keeper,callsite,candidate)
        publish.assert_not_called();encoder.assert_not_called();self.assertIs(held['raw'],candidate['raw'])
        self.assertIsInstance(held['error'],ValueError);self.record(held)

    def test_incomplete_codec_prefix_never_reaches_publication_callback(self):
        secondary=KeyboardInterrupt('original candidate incomplete')
        def chunks(value):yield '{';raise secondary
        factory=Mock(return_value=Mock(iterencode=Mock(side_effect=chunks)))
        with patch.object(reader,'DIAGNOSTIC_JSON_ENCODER',factory):keeper,callsite,candidate=self.candidate()
        with patch.object(self.writer,'publish') as publish:
            held=self.writer.prepare_callsite_diagnostic_publication(keeper,callsite,candidate)
        publish.assert_not_called();self.assertIs(candidate['error'],secondary);self.assertEqual(candidate['parts'],(b'{',))
        self.assertIsNone(held['raw']);self.assertIs(self.writer._RequestAuxiliaryWriter__failure,callsite[0]);self.record(held)

    def test_original_unknown_pending_blocks_new_publication_without_overwrite(self):
        error=OSError('original unknown pending');pending={'stream':SimpleNamespace(closed=True),'raw':b'original pending'}
        self.writer._RequestAuxiliaryWriter__pending=self.writer.pending=pending
        self.writer._RequestAuxiliaryWriter__operations=(pending,);self.writer._RequestAuxiliaryWriter__failure=error
        keeper,callsite,candidate=self.candidate(error=error)
        with patch.object(self.writer,'publish') as publish:
            held=self.writer.prepare_callsite_diagnostic_publication(keeper,callsite,candidate)
        publish.assert_not_called();self.assertIs(self.writer.pending,pending)
        self.assertIs(self.writer._RequestAuxiliaryWriter__diagnostic_publication_owner[3],pending)
        self.assertIsInstance(held['error'],ValueError)
        # Declared closed flag on an opaque Python fixture is not a close return.
        self.record(held)

    def test_callback_reentry_returns_original_inflight_holder_without_second_publish(self):
        keeper,callsite,candidate=self.candidate();seen=[];unknown=object()
        def reenter(name,raw):
            seen.append(self.writer.prepare_callsite_diagnostic_publication(keeper,callsite,candidate));return unknown
        with patch.object(self.writer,'publish',side_effect=reenter) as publish:
            held=self.writer.prepare_callsite_diagnostic_publication(keeper,callsite,candidate)
        publish.assert_called_once();self.assertEqual(len(seen),1);self.assertIs(seen[0],held)
        self.assertIs(held['return'],unknown);self.assertFalse(held['published']);self.record(held)

    def test_cached_field_erasure_keeps_private_returns_and_never_replays_io(self):
        keeper,callsite,candidate=self.candidate();held=self.writer.prepare_callsite_diagnostic_publication(keeper,callsite,candidate)
        state=self.writer._RequestAuxiliaryWriter__diagnostic_publication_state
        held['raw']=held['return']=held['error']=None;held['published']=held['native_authorized']=held['formal_permission']=True
        self.writer.diagnostic_publication=None;self.writer.error=None;self.f.f.clock.reset_mock()
        with patch.object(self.writer,'publish') as publish,patch.object(reader,'DIAGNOSTIC_JSON_ENCODER') as encoder:
            returned=self.writer.prepare_callsite_diagnostic_publication(object(),(),{})
        publish.assert_not_called();encoder.assert_not_called();self.f.f.clock.assert_not_called()
        self.assertIs(returned,held);self.assertIs(self.writer._RequestAuxiliaryWriter__diagnostic_publication_state,state)
        self.assertIs(state[0],candidate['raw']);self.assertIs(state[4],callsite[0]);self.assertFalse(held['published'])
        self.assertFalse(held['native_authorized']);self.assertFalse(held['formal_permission'])


if __name__=='__main__':unittest.main()
