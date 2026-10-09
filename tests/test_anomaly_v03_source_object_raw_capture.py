"""Original bounded read returns and same object-batch owner retention."""
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from banto_ai import _anomaly_v03_reader_dependencies as objects
from banto_ai import anomaly_v03_preformal_reader_git_worker as reader
from tests import test_anomaly_v03_source_object_batch_contract as fixtures

OBSERVATIONS = []


class Stream:
    def __init__(self, returns):
        self.returns = iter(returns)
        self.calls = []
        self.closed = False

    def read(self, size):
        self.calls.append(size)
        value = next(self.returns)
        if isinstance(value, BaseException):
            raise value
        return value


class SourceObjectRawCaptureTests(unittest.TestCase):
    def held(self, stdout_cap=None):
        raw, sources, bodies, maxima, storage = fixtures.fixture()
        if stdout_cap is not None:
            maxima[0]['stdout'] = stdout_cap
        clock = Mock()
        held = objects.SourceObjectBatchContractPreparation(owner=SimpleNamespace(), checkpoint=clock,
            request_raw=raw, expected_sources=sources, source_bodies=bodies,
            raw_maxima=maxima, storage_maxima=storage)
        return held, raw, sources, bodies, maxima, storage, clock

    def observe(self, held):
        captures = held._SourceObjectBatchContractPreparation__captures
        rows = []
        for capture in captures:
            rows.append({'reads':len(capture.operations), 'prefix_sizes':
                [sum(len(p) for p in parts if type(p) is bytes) for parts in capture.prefixes],
                'pending':capture.pending is not None, 'unresolved':capture.unresolved(),
                'closed_by_capture':False})
        OBSERVATIONS.append({'test':self.id(), 'captures':rows, 'unresolved':held.unresolved(),
            'native_authenticated':False, 'formal_permission':False})

    def test_real_fileio_metadata_bytes_bind_same_owner_without_closing_input_streams(self):
        held, raw, sources, _, _, _, clock = self.held()
        held.retain_raw(0,b'1'*40+b'\n',b'',b'r',exit_code=0)
        held.retain_raw(1,b'',b'',b'r',exit_code=0)
        expected=fixtures.metadata(sources)
        with tempfile.TemporaryDirectory() as directory:
            outpath=Path(directory)/'out';errpath=Path(directory)/'err'
            outpath.write_bytes(expected);errpath.write_bytes(b'')
            with outpath.open('rb',buffering=0) as out,errpath.open('rb',buffering=0) as err:
                receipt=b'opaque receipt';partial=b'separate partial'
                result=held.capture_raw(2,out,err,receipt,exit_code=0,partial=partial)
                capture=held.raw_captures[0]
                self.assertIs(capture.original_inputs[0],held)
                self.assertIs(capture.original_inputs[2],out)
                self.assertIs(result[0][3],receipt);self.assertIs(result[0][5],partial)
                self.assertEqual(result[0][1],expected)
                self.assertFalse(out.closed);self.assertFalse(err.closed)
                proof=json.loads(result[1]);self.assertTrue(all(x is False for x in proof['scope'].values()))
                self.assertFalse(json.loads(held.records[2]['metadata_proof_raw'])['git_body_returned'])
        clock.assert_not_called();self.observe(held)

    def test_all_call_capture_full_pack_readback_and_cached_result_do_not_repeat_reads(self):
        held,raw,sources,_,_,_,clock=self.held()
        request=json.loads(raw)
        for index,call in enumerate(request['calls']):
            data=b'1'*40+b'\n' if call['operation']=='head' else b''
            if call['operation']=='source_blob_metadata_batch':
                data=fixtures.metadata(sources)
            out=io.BytesIO(data);err=io.BytesIO();receipt=b'opaque'
            result=held.capture_raw(index,out,err,receipt,exit_code=0)
            positions=(out.tell(),err.tell())
            self.assertIs(held.capture_raw(index,out,err,receipt,exit_code=0),result)
            self.assertEqual((out.tell(),err.tell()),positions)
        pack=held.prepare_pack()
        self.assertIn(fixtures.metadata(sources),pack[0]);self.assertTrue(pack[0].startswith(b'SOM1'))
        clock.assert_not_called();self.observe(held)

    def test_declared_failure_keeps_completed_reads_receipt_partial_and_original_error(self):
        held,_,_,_,_,_,_=self.held()
        out=Stream([b'failed',b'']);err=Stream([b'error',b''])
        receipt=b'original receipt';partial=b'original partial'
        with self.assertRaises(ValueError) as first:
            held.capture_raw(0,out,err,receipt,exit_code=17,partial=partial)
        captured=held.raw_captures[0]
        self.assertEqual(held.pending['incoming'],(0,b'failed',b'error',receipt,17,partial))
        self.assertIs(captured.error,first.exception)
        reads=(tuple(out.calls),tuple(err.calls))
        held.error=None;captured.error=None
        with self.assertRaises(ValueError) as again:
            held.capture_raw(0,out,err,receipt,exit_code=17,partial=partial)
        self.assertIs(first.exception,again.exception);self.assertEqual((tuple(out.calls),tuple(err.calls)),reads)
        self.observe(held)

    def test_zero_stdout_maximum_retains_one_detection_byte_before_stderr_read(self):
        held,_,_,_,_,_,_=self.held()
        held.retain_raw(0,b'1'*40+b'\n',b'',b'r',exit_code=0)
        out=Stream([b'x']);err=Stream([b''])
        with self.assertRaisesRegex(ValueError,'exceeds independent maximum'):
            held.capture_raw(1,out,err,b'r',exit_code=0)
        self.assertEqual(out.calls,[1]);self.assertEqual(err.calls,[])
        self.assertEqual(held.raw_captures[0].prefixes[0],(b'x',));self.observe(held)

    def test_stderr_detection_prefix_is_distinct_from_completed_stdout_and_partial(self):
        held,_,_,_,_,_,_=self.held()
        out=io.BytesIO(b'1'*40+b'\n');err=Stream([b'e'*33])
        with self.assertRaisesRegex(ValueError,'exceeds independent maximum'):
            held.capture_raw(0,out,err,b'r',exit_code=0,partial=b'p')
        capture=held.raw_captures[0]
        self.assertEqual(b''.join(capture.prefixes[0]),b'1'*40+b'\n')
        self.assertEqual(capture.prefixes[1],(b'e'*33,));self.assertIs(capture.original_inputs[6],b'p')
        self.observe(held)

    def test_unknown_none_return_is_observed_literal_and_never_reissued(self):
        held,_,_,_,_,_,_=self.held();out=Stream([None]);err=Stream([b''])
        with self.assertRaises(ValueError):held.capture_raw(0,out,err,b'r',exit_code=0)
        capture=held.raw_captures[0]
        self.assertTrue(capture.operations[0][1]);self.assertIsNone(capture.operations[0][2])
        self.assertEqual(out.calls,[42]);self.assertEqual(err.calls,[])
        self.assertIsNotNone(capture.pending);self.observe(held)

    def test_read_exception_after_prefix_preserves_unobserved_return_and_original_stream(self):
        held,_,_,_,_,_,_=self.held();error=KeyboardInterrupt('read')
        out=Stream([b'prefix',error]);err=Stream([b''])
        with self.assertRaises(KeyboardInterrupt) as caught:held.capture_raw(0,out,err,b'r',exit_code=0)
        capture=held.raw_captures[0]
        self.assertIs(caught.exception,error);self.assertFalse(capture.operations[-1][1])
        self.assertIs(capture.operations[-1][3],error);self.assertEqual(capture.prefixes[0],(b'prefix',))
        self.assertIs(capture.original_inputs[2],out);self.assertFalse(out.closed);self.observe(held)

    def test_callback_return_larger_than_requested_is_retained_before_rejection(self):
        held,_,_,_,_,_,_=self.held();literal=b'x'*43;out=Stream([literal])
        with self.assertRaisesRegex(ValueError,'bounded literal read return'):
            held.capture_raw(0,out,Stream([b'']),b'r',exit_code=0)
        capture=held.raw_captures[0]
        self.assertIs(capture.operations[0][2],literal);self.assertIs(capture.prefixes[0][0],literal)
        self.observe(held)

    def test_tiny_returns_hit_attempt_bound_with_all_original_prefix_and_no_stderr(self):
        held,_,_,_,_,_,_=self.held(stdout_cap=512)
        out=Stream([b'x']*128);err=Stream([b''])
        with self.assertRaisesRegex(ValueError,'attempt bound'):
            held.capture_raw(0,out,err,b'r',exit_code=17)
        self.assertEqual(len(out.calls),128);self.assertEqual(err.calls,[])
        self.assertEqual(len(held.raw_captures[0].prefixes[0]),128);self.observe(held)

    def test_read_callback_reentry_that_swallows_refusal_keeps_original_return_and_first_error(self):
        held,_,_,_,_,_,_=self.held();errors=[]
        class Reentrant(Stream):
            def read(self,size):
                self.calls.append(size)
                try:held.capture_raw(0,self,err,receipt,exit_code=0)
                except ValueError as error:errors.append(error)
                return b'original outer'
        out=Reentrant([]);err=Stream([b'']);receipt=b'r'
        with self.assertRaises(ValueError) as first:held.capture_raw(0,out,err,receipt,exit_code=0)
        self.assertIs(first.exception,errors[0])
        capture=held.raw_captures[0]
        self.assertEqual(capture.operations[0][2],b'original outer')
        self.assertEqual(len(out.calls),1);self.assertEqual(err.calls,[]);self.observe(held)

    def test_read_getter_interrupt_holds_stream_and_pending_before_getter(self):
        held,_,_,_,_,_,_=self.held()
        class Interrupted:
            @property
            def read(self):raise KeyboardInterrupt('getter')
        out=Interrupted()
        with self.assertRaises(KeyboardInterrupt):held.capture_raw(0,out,Stream([b'']),b'r',exit_code=0)
        capture=held.raw_captures[0]
        self.assertEqual(capture.pending,('read-getter',out));self.assertIs(capture.original_inputs[2],out)
        self.assertEqual(capture.operations,());self.observe(held)

    def test_cached_ledger_alias_erasure_latches_refusal_even_after_alias_restoration(self):
        for alias in ('original_inputs','operations','prefixes','pending','descriptor_raw'):
            held,_,_,_,_,_,_=self.held();out=io.BytesIO(b'1'*40+b'\n');err=io.BytesIO();receipt=b'r'
            result=held.capture_raw(0,out,err,receipt,exit_code=0);capture=held.raw_captures[0]
            original=getattr(capture,alias);setattr(capture,alias,object() if alias=='pending' else None)
            with self.assertRaises(ValueError) as first:held.capture_raw(0,out,err,receipt,exit_code=0)
            setattr(capture,alias,original)
            with self.assertRaises(ValueError) as again:held.capture_raw(0,out,err,receipt,exit_code=0)
            self.assertIs(first.exception,again.exception);self.assertIs(capture._SourceObjectBatchRawCapture__result,result)

    def test_parent_alias_erasure_retains_original_capture_under_same_parent_keeper(self):
        parent=reader.ReaderGitParent.__new__(reader.ReaderGitParent);parent.inventory_checkpoint=Mock()
        raw,sources,bodies,maxima,storage=fixtures.fixture()
        held=parent.prepare_source_object_batch_contract(request_raw=raw,expected_sources=sources,
            source_bodies=bodies,raw_maxima=maxima,storage_maxima=storage)
        out=Stream([None])
        with self.assertRaises(ValueError):held.capture_raw(0,out,Stream([b'']),b'r',exit_code=0)
        parent.source_object_batch_owner=None;held.raw_captures=None
        parent.original_bootstrap_inputs=(None,)*11;parent.worker=None;parent.error=None
        error=ValueError('caller')
        class Escape(BaseException):pass
        with patch.object(reader.ParentPublicationRetention,'_pause',side_effect=Escape),self.assertRaises(Escape):
            reader.retain_parent_publications(error,parent)
        self.assertIn(held,parent.original_publication_retention.owners)
        self.assertIs(parent.original_publication_retention,error.parent_publication_retention)
        self.assertIs(held._SourceObjectBatchContractPreparation__captures[0].original_inputs[2],out)

    def test_failed_reentry_does_not_grow_capture_or_operation_ledgers(self):
        held,_,_,_,_,_,_=self.held();out=Stream([None])
        with self.assertRaises(ValueError) as first:held.capture_raw(0,out,Stream([b'']),b'r',exit_code=0)
        ledger=held._SourceObjectBatchContractPreparation__captures;operations=ledger[0].operations
        for index in range(4):
            with self.assertRaises(ValueError) as again:
                held.capture_raw(index,Stream([]),Stream([]),b'new',exit_code=0)
            self.assertIs(first.exception,again.exception)
        self.assertIs(held._SourceObjectBatchContractPreparation__captures,ledger)
        self.assertIs(ledger[0].operations,operations);self.observe(held)

    def test_receipt_and_partial_independent_limits_refuse_before_stream_getter(self):
        for receipt,partial in ((b'r'*65,b''),(b'r',b'p'*17)):
            held,_,_,_,_,_,_=self.held()
            class Getter:
                @property
                def read(self):raise AssertionError('must not get read')
            out=Getter()
            with self.assertRaisesRegex(ValueError,'independent opaque raw bound'):
                held.capture_raw(0,out,Getter(),receipt,exit_code=0,partial=partial)
            capture=held.raw_captures[0]
            self.assertIs(capture.original_inputs[4],receipt);self.assertIs(capture.original_inputs[6],partial)
            self.assertEqual(capture.operations,())

    def test_cached_foreign_stream_is_retained_without_reading_or_replacing_original(self):
        held,_,_,_,_,_,_=self.held();out=io.BytesIO(b'1'*40+b'\n');err=io.BytesIO();receipt=b'r'
        original=held.capture_raw(0,out,err,receipt,exit_code=0);foreign=Stream([])
        with self.assertRaisesRegex(ValueError,'same original inputs'):
            held.capture_raw(0,foreign,err,receipt,exit_code=0)
        capture=held.raw_captures[0]
        self.assertIs(capture._SourceObjectBatchRawCapture__rejected_inputs[2],foreign)
        self.assertIs(capture._SourceObjectBatchRawCapture__result,original);self.assertEqual(foreign.calls,[])

    def test_read_callback_alias_erasure_is_not_masked_by_return_ledger_update(self):
        for alias in ('operations','prefixes','pending'):
            held,_,_,_,_,_,_=self.held();literal=b'original return'
            class Mutation(Stream):
                def read(self,size):
                    self.calls.append(size)
                    setattr(held.raw_captures[0],alias,None)
                    return literal
            out=Mutation([]);err=Stream([b''])
            with self.assertRaises(ValueError):held.capture_raw(0,out,err,b'r',exit_code=0)
            capture=held._SourceObjectBatchContractPreparation__captures[0]
            self.assertIs(capture._SourceObjectBatchRawCapture__operations[0][2],literal)
            self.assertEqual(len(out.calls),1);self.assertEqual(err.calls,[])

    def test_next_capture_retains_incoming_before_rejecting_erased_original_capture_ledger(self):
        held,_,_,_,_,_,_=self.held()
        held.capture_raw(0,io.BytesIO(b'1'*40+b'\n'),io.BytesIO(),b'r',exit_code=0)
        original=held._SourceObjectBatchContractPreparation__captures;held.raw_captures=None
        out=Stream([]);err=Stream([])
        with self.assertRaises(ValueError):held.capture_raw(1,out,err,b'r',exit_code=0)
        rejected=held._SourceObjectBatchContractPreparation__capture_attempt
        self.assertIs(rejected.original_inputs[2],out)
        self.assertIs(held._SourceObjectBatchContractPreparation__captures,original)
        self.assertEqual(out.calls,[]);self.assertEqual(err.calls,[])

    def test_read_callback_cannot_replace_same_call_raw_forward(self):
        held,_,_,_,_,_,_=self.held();errors=[]
        class Injection(Stream):
            def read(self,size):
                self.calls.append(size)
                try:held.retain_raw(0,b'1'*40+b'\n',b'',b'foreign',exit_code=0)
                except ValueError as error:errors.append(error)
                return b'original outer'
        out=Injection([]);err=Stream([b''])
        with self.assertRaises(ValueError) as caught:held.capture_raw(0,out,err,b'r',exit_code=0)
        self.assertIs(caught.exception,errors[0]);self.assertEqual(held.records,())
        self.assertEqual(held.raw_captures[0].operations[0][2],b'original outer')
        self.assertEqual(err.calls,[])
