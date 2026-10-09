"""Original caller diagnostic candidates, bounded codec and no publication."""
import base64
import copy
from pathlib import Path
import unittest
from unittest.mock import Mock,patch

from banto_ai import anomaly_v03_preformal_reader_git_worker as reader
from tests import test_anomaly_v03_generate_auxiliary_callsite as fixtures

OBSERVATIONS=[]


class GenerateDiagnosticBytesTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.GenerateAuxiliaryCallsiteTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.parent=self.f.parent;self.writer=self.f.f.writers['diagnostic']

    def execute(self,error=None):
        error=OSError('original diagnostic caller') if error is None else error
        caller=self.f.caller(error)
        with (patch.object(reader.ParentPublicationRetention,'_pause',side_effect=fixtures.RetentionEscape()),
              self.assertRaises(fixtures.RetentionEscape)):
            caller.execute()
        held=error.parent_publication_retention;candidate=self.writer._RequestAuxiliaryWriter__diagnostic_candidate
        self.assertIs(held.original_error,error);self.assertIs(self.writer._RequestAuxiliaryWriter__failure,error)
        self.assertFalse((caller.f.attempt/'owned-generator/result.json').exists())
        self.f.f.clock.assert_not_called()
        return held,candidate

    def manual(self,result):
        error=OSError('original diagnostic fence');error.reader_git_parent=self.parent
        callsite=(error,'reader',Path('original-target'),result)
        with patch.object(reader.ParentPublicationRetention,'_pause',side_effect=fixtures.RetentionEscape()),self.assertRaises(fixtures.RetentionEscape):
            reader.retain_parent_publications(error,self.parent,caller_diagnostics=callsite)
        return error.parent_publication_retention,self.writer._RequestAuxiliaryWriter__diagnostic_candidate

    def record(self,candidate):
        OBSERVATIONS.append({'test':self.id(),'raw_base64':base64.b64encode(candidate['raw']).decode() if candidate['raw'] is not None else None,
            'prefix_base64':base64.b64encode(b''.join(candidate['parts'])).decode(),'pin':candidate['raw_pin'],
            'encoded':candidate['encoded'],'error_type':type(candidate['error']).__name__ if candidate['error'] is not None else None,
            'published':candidate['published'],'native_authorized':False,'formal_permission':False})

    def test_actual_generate_catch_produces_original_bounded_raw_candidate_before_keeper(self):
        held,candidate=self.execute()
        self.assertTrue(candidate['encoded']);self.assertIsNone(candidate['error'])
        self.assertEqual(candidate['raw'],reader.v.canonical_json(candidate['envelope']))
        self.assertIs(candidate['envelope']['result'],held.auxiliary_callsite['incoming'][0][3])
        self.assertEqual(candidate['raw_pin'],reader.observed._pin(candidate['raw']))
        self.assertFalse(candidate['published']);self.assertEqual(self.writer._RequestAuxiliaryWriter__operations,())
        self.record(candidate)

    def test_independent_text_maximum_refuses_original_large_input_before_encoder_or_io(self):
        result={'original': 'x'*2049}
        with patch.object(reader,'DIAGNOSTIC_JSON_ENCODER') as encoder:held,candidate=self.manual(result)
        encoder.assert_not_called();self.assertIs(candidate['envelope']['result'],result)
        self.assertFalse(candidate['encoded']);self.assertIsNone(candidate['raw']);self.assertIsInstance(candidate['error'],ValueError)
        self.record(candidate)

    def test_multibyte_utf8_excess_retains_original_token_and_prior_prefix(self):
        result={'original':'界'*900};held,candidate=self.manual(result)
        self.assertFalse(candidate['encoded']);self.assertIsNone(candidate['raw'])
        self.assertIsInstance(candidate['error'],ValueError);self.assertGreater(len(candidate['last_encoded_chunk']),candidate['limit'])
        self.assertTrue(candidate['parts']);self.assertIs(candidate['envelope']['result'],result);self.record(candidate)

    def test_non_json_value_is_retained_without_encoding_or_replacing_original_error(self):
        original=object();held,candidate=self.manual({'original':original})
        self.assertIs(candidate['observing_value'],original);self.assertFalse(candidate['encoded'])
        self.assertIsInstance(candidate['error'],ValueError);self.assertIs(self.writer.error,held.original_error)
        self.record(candidate)

    def test_iterator_interrupt_keeps_original_iterator_prefix_and_first_fence(self):
        secondary=KeyboardInterrupt('original encoder interrupted')
        def chunks(value):yield '{';raise secondary
        factory=Mock(return_value=Mock(iterencode=Mock(side_effect=chunks)))
        with patch.object(reader,'DIAGNOSTIC_JSON_ENCODER',factory):held,candidate=self.execute()
        self.assertIs(candidate['encoder_factory'],factory);self.assertEqual(candidate['parts'],(b'{',))
        self.assertIs(candidate['iterator'],candidate['iterator_return']);self.assertIs(candidate['error'],secondary)
        self.assertFalse(candidate['encoded']);self.record(candidate)

    def test_unknown_nontext_iterator_return_is_kept_before_shape_refusal(self):
        unknown=object();factory=Mock(return_value=Mock(iterencode=Mock(return_value=iter([unknown]))))
        with patch.object(reader,'DIAGNOSTIC_JSON_ENCODER',factory):held,candidate=self.execute()
        self.assertIs(candidate['last_chunk'],unknown);self.assertIsInstance(candidate['error'],ValueError)
        self.assertFalse(candidate['encoded']);self.record(candidate)

    def test_cached_complete_candidate_does_not_follow_display_erasure_or_reencode(self):
        held,candidate=self.execute();self.writer.diagnostic_candidate=None;self.writer.error=None
        original=candidate['incoming'];foreign=(object(),(OSError('foreign'),'reader',Path('later'),{}))
        with patch.object(reader,'DIAGNOSTIC_JSON_ENCODER') as encoder:
            result=self.writer.prepare_callsite_diagnostic(*foreign)
        encoder.assert_not_called();self.assertIs(result,candidate);self.assertIs(candidate['incoming'],original)
        self.assertEqual(self.writer.rejected_diagnostic_candidate,foreign);self.assertIs(self.writer._RequestAuxiliaryWriter__failure,held.original_error)
        self.record(candidate)

    def test_changed_maximum_denies_before_encoder_and_keeps_original_independent_raw(self):
        self.writer.limits['diagnostic.json']=8192
        with patch.object(reader,'DIAGNOSTIC_JSON_ENCODER') as encoder:held,candidate=self.execute()
        encoder.assert_not_called();self.assertFalse(candidate['encoded']);self.assertIsInstance(candidate['error'],ValueError)
        self.assertIs(candidate['binding'],self.writer._RequestAuxiliaryWriter__callsite_binding)
        self.record(candidate)

    def test_original_result_mutation_during_codec_is_retained_and_refuses_completion(self):
        original={'value':'old'}
        real=reader.v.json.JSONEncoder
        class MutatingEncoder(real):
            def iterencode(self,value,*args,**kwargs):
                original['value']='new';yield from super().iterencode(value,*args,**kwargs)
        with patch.object(reader,'DIAGNOSTIC_JSON_ENCODER',MutatingEncoder):held,candidate=self.manual(original)
        self.assertFalse(candidate['encoded']);self.assertIsNotNone(candidate['raw']);self.assertIsNotNone(candidate['decoded_return'])
        self.assertIsInstance(candidate['error'],ValueError);self.assertIs(candidate['envelope']['result'],original)
        self.record(candidate)

    def test_cached_failed_prefix_never_reencodes_after_display_erasure_and_restore(self):
        secondary=KeyboardInterrupt('original incomplete candidate')
        def chunks(value):yield '{';raise secondary
        factory=Mock(return_value=Mock(iterencode=Mock(side_effect=chunks)))
        with patch.object(reader,'DIAGNOSTIC_JSON_ENCODER',factory):held,candidate=self.execute()
        self.writer.diagnostic_candidate=None
        with patch.object(reader,'DIAGNOSTIC_JSON_ENCODER') as encoder:
            returned=self.writer.prepare_callsite_diagnostic(*candidate['incoming'])
        encoder.assert_not_called();self.assertIs(returned,candidate);self.assertIs(candidate['error'],secondary)
        self.assertEqual(candidate['parts'],(b'{',));self.assertIsNone(candidate['raw']);self.assertFalse(candidate['encoded'])
        self.assertIs(self.writer._RequestAuxiliaryWriter__failure,held.original_error);self.record(candidate)

    def test_public_prefix_codec_raw_erasure_does_not_drop_private_original_returns(self):
        held,candidate=self.execute();parts=candidate['parts'];codec=self.writer._RequestAuxiliaryWriter__diagnostic_codec
        raw=candidate['raw'];decoded=candidate['decoded_return'];owner=self.writer._RequestAuxiliaryWriter__diagnostic_owner
        candidate['parts']=();candidate['graph']=();candidate['encoder']=candidate['iterator']=None
        candidate['raw']=candidate['raw_pin']=candidate['decoded_return']=None;self.writer.diagnostic_candidate=None
        with patch.object(reader,'DIAGNOSTIC_JSON_ENCODER') as encoder:self.writer.prepare_callsite_diagnostic(*owner[0])
        encoder.assert_not_called();self.assertIs(self.writer._RequestAuxiliaryWriter__diagnostic_parts,parts)
        self.assertIs(self.writer._RequestAuxiliaryWriter__diagnostic_codec,codec)
        returns=self.writer._RequestAuxiliaryWriter__diagnostic_raw_returns
        self.assertIs(returns[0],raw);self.assertIs(returns[2],decoded);self.assertIs(owner[0][0],held)
        self.assertIs(self.writer._RequestAuxiliaryWriter__failure,held.original_error)

    def test_encoder_reentry_returns_same_inflight_holder_without_second_iterator(self):
        real=reader.DIAGNOSTIC_JSON_ENCODER;seen=[];writer=self.writer
        class Reentry(real):
            def iterencode(self,value,*args,**kwargs):
                incoming=writer._RequestAuxiliaryWriter__diagnostic_owner[0]
                seen.append(writer.prepare_callsite_diagnostic(*incoming))
                yield from super().iterencode(value,*args,**kwargs)
        with patch.object(reader,'DIAGNOSTIC_JSON_ENCODER',Reentry):held,candidate=self.execute()
        self.assertEqual(len(seen),1);self.assertIs(seen[0],candidate);self.assertTrue(candidate['encoded'])
        self.assertEqual(len(self.writer._RequestAuxiliaryWriter__diagnostic_codec),4);self.record(candidate)

    def test_deep_original_graph_is_retained_and_refused_before_encoder(self):
        original=[];value=original
        for _ in range(66):nested=[];value.append(nested);value=nested
        with patch.object(reader,'DIAGNOSTIC_JSON_ENCODER') as encoder:held,candidate=self.manual({'original':original})
        encoder.assert_not_called();self.assertFalse(candidate['encoded']);self.assertIsInstance(candidate['error'],ValueError)
        self.assertTrue(self.writer._RequestAuxiliaryWriter__diagnostic_graph)
        self.assertIs(candidate['envelope']['result']['original'],original);self.record(candidate)

    def test_cached_candidate_field_erasure_and_authority_flip_refuse_completion_without_codec(self):
        held,candidate=self.execute();state=self.writer._RequestAuxiliaryWriter__diagnostic_state
        candidate['raw']=None;candidate['parts']=();candidate['native_authorized']=candidate['formal_permission']=True
        with patch.object(reader,'DIAGNOSTIC_JSON_ENCODER') as encoder:
            returned=self.writer.prepare_callsite_diagnostic(*candidate['incoming'])
        encoder.assert_not_called();self.assertIs(returned,candidate);self.assertFalse(candidate['encoded'])
        self.assertIsInstance(candidate['error'],ValueError);self.assertFalse(candidate['native_authorized'])
        self.assertFalse(candidate['formal_permission']);self.assertIs(self.writer._RequestAuxiliaryWriter__diagnostic_state,state)
        self.assertIsNotNone(self.writer._RequestAuxiliaryWriter__diagnostic_raw_returns[0])
        self.assertIs(self.writer._RequestAuxiliaryWriter__failure,held.original_error)


if __name__=='__main__':unittest.main()
