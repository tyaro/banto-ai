"""Original clock/checkpoint returns fence further caller reads after deadlines."""
import io
import json
import tempfile
import time
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
        self.getters = 0
        self.calls = []
        self.closed = False

    @property
    def read(self):
        self.getters += 1
        return self._read

    def _read(self, size):
        self.calls.append(size)
        value = next(self.returns)
        if isinstance(value, BaseException):raise value
        return value


class SourceObjectReadWallTests(unittest.TestCase):
    def held(self, clock=None, checkpoint=None, parent=None):
        raw,sources,bodies,maxima,storage=fixtures.fixture()
        checkpoint=checkpoint if checkpoint is not None else Mock(return_value=None)
        if parent is None:
            parent=SimpleNamespace()
            held=objects.SourceObjectBatchContractPreparation(owner=parent,checkpoint=checkpoint,
                request_raw=raw,expected_sources=sources,source_bodies=bodies,
                raw_maxima=maxima,storage_maxima=storage)
        else:
            parent.inventory_checkpoint=checkpoint
            held=parent.prepare_source_object_batch_contract(request_raw=raw,expected_sources=sources,
                source_bodies=bodies,raw_maxima=maxima,storage_maxima=storage)
        clock=clock if clock is not None else Mock(return_value=100)
        return held,(clock,100,200),clock,checkpoint

    def capture(self, held, wall, out, err=None):
        err=err if err is not None else Stream([b''])
        return held.capture_raw(0,out,err,b'opaque',exit_code=0,read_wall=wall)

    def observe(self, held):
        capture=held._SourceObjectBatchContractPreparation__captures[-1]
        OBSERVATIONS.append({'test':self.id(),'read_returns':len(capture._SourceObjectBatchRawCapture__operations),
            'wall_returns':len(capture._SourceObjectBatchRawCapture__wall_operations),
            'prefix_bytes':[sum(map(len,p)) for p in capture._SourceObjectBatchRawCapture__prefixes],
            'wall_pending':capture._SourceObjectBatchRawCapture__wall_pending is not None,
            'read_interrupted':False,'native_authenticated':False,'formal_permission':False})

    def test_real_fileio_and_original_monotonic_ns_returns_cached_without_recheck_or_close(self):
        clock=time.monotonic_ns;started=clock();held,_,_,checkpoint=self.held(clock)
        wall=(clock,started,started+30000000000)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'head';path.write_bytes(b'1'*40+b'\n')
            with path.open('rb',buffering=0) as out,io.BytesIO() as err:
                result=self.capture(held,wall,out,err);capture=held.raw_captures[0]
                ops=capture.wall_operations;count=checkpoint.call_count
                self.assertIs(self.capture(held,wall,out,err),result)
                self.assertIs(capture.wall_operations,ops);self.assertEqual(checkpoint.call_count,count)
                self.assertFalse(out.closed);self.assertFalse(err.closed)
                clocks=[r[2] for r in ops if r[0][1]=='clock']
                self.assertTrue(clocks and all(started<=t<wall[2] for t in clocks))
                self.assertEqual(clocks,sorted(clocks))
                descriptor=json.loads(capture.descriptor_raw)
                self.assertTrue(descriptor['format'].endswith('v2'))
                self.assertFalse(descriptor['read_wall']['blocking_read_interrupted'])
                self.assertTrue(all(v is False for v in descriptor['scope'].values()))
        self.observe(held)

    def test_expired_absolute_window_stops_before_original_stream_getter(self):
        held,wall,clock,checkpoint=self.held(Mock(return_value=200));out=Stream([]);err=Stream([])
        with self.assertRaisesRegex(ValueError,'read wall deadline'):self.capture(held,wall,out,err)
        capture=held.raw_captures[0]
        self.assertEqual((out.getters,err.getters), (0,0));self.assertEqual(capture.operations,())
        self.assertEqual(capture.wall_operations[-1][2],200)
        self.assertIs(capture.original_inputs[2],out);self.assertIs(capture.read_wall_inputs,wall)
        self.assertEqual((clock.call_count,checkpoint.call_count),(1,1));self.observe(held)

    def test_late_read_literal_prefix_is_held_before_deadline_refusal_and_no_stderr(self):
        held,wall,clock,checkpoint=self.held(Mock(side_effect=[100,101,200]))
        literal=b'original late';out=Stream([literal]);err=Stream([])
        with self.assertRaisesRegex(ValueError,'read wall deadline'):self.capture(held,wall,out,err)
        capture=held.raw_captures[0]
        self.assertIs(capture.operations[0][2],literal);self.assertIs(capture.prefixes[0][0],literal)
        self.assertEqual((len(out.calls),err.getters,len(held.records)),(1,0,0))
        self.assertEqual(capture.wall_operations[-1][2],200);self.assertFalse(out.closed);self.observe(held)

    def test_absolute_window_is_not_reset_when_stdout_eof_precedes_stderr(self):
        held,wall,clock,_=self.held(Mock(side_effect=[100,101,102,200]))
        held.retain_raw(0,b'1'*40+b'\n',b'',b'r',exit_code=0)
        out=Stream([b'']);err=Stream([])
        with self.assertRaisesRegex(ValueError,'read wall deadline'):
            held.capture_raw(1,out,err,b'r',exit_code=0,read_wall=wall)
        self.assertEqual(out.calls,[1]);self.assertEqual(err.getters,0)
        self.assertEqual(len(held.records),1);self.observe(held)

    def test_final_stderr_eof_late_return_cannot_register_completed_raw(self):
        held,wall,_,_=self.held(Mock(side_effect=[100,101,102,103,104,105,106,200]))
        out=Stream([b'1'*40+b'\n',b'']);err=Stream([b''])
        with self.assertRaisesRegex(ValueError,'read wall deadline'):self.capture(held,wall,out,err)
        self.assertEqual(held.records,());self.assertEqual(held.raw_captures[0].prefixes[1],(b'',))
        self.assertEqual((len(out.calls),len(err.calls)),(2,1));self.observe(held)

    def test_post_read_checkpoint_exception_preserves_first_error_and_original_read_return(self):
        error=KeyboardInterrupt('original checkpoint');checkpoint=Mock(side_effect=[None,None,error])
        held,wall,clock,_=self.held(checkpoint=checkpoint);literal=b'prefix';out=Stream([literal]);err=Stream([])
        with self.assertRaises(KeyboardInterrupt) as first:self.capture(held,wall,out,err)
        capture=held.raw_captures[0];self.assertIs(first.exception,error)
        self.assertIs(capture.operations[0][2],literal);self.assertFalse(capture.wall_operations[-1][1])
        self.assertIs(capture.wall_operations[-1][3],error);self.assertEqual(clock.call_count,2)
        self.assertEqual(err.getters,0);self.observe(held)

    def test_unknown_checkpoint_return_is_literal_held_and_clock_read_never_started(self):
        literal=object();held,wall,clock,_=self.held(checkpoint=Mock(return_value=literal));out=Stream([])
        with self.assertRaisesRegex(ValueError,'checkpoint literal return'):self.capture(held,wall,out)
        self.assertIs(held.raw_captures[0].wall_operations[0][2],literal)
        self.assertEqual(clock.call_count,0);self.assertEqual(out.getters,0);self.observe(held)

    def test_unknown_or_backward_clock_returns_retained_without_next_read(self):
        for values in ([None],[True],[99],[100,101,100]):
            with self.subTest(values=values):
                held,wall,clock,_=self.held(Mock(side_effect=values));out=Stream([b'prefix']);err=Stream([])
                with self.assertRaisesRegex(ValueError,'monotonic clock return'):self.capture(held,wall,out,err)
                capture=held.raw_captures[0]
                self.assertIs(capture.wall_operations[-1][2],values[-1]);self.assertEqual(err.getters,0)
                self.assertEqual(len(out.calls),1 if len(values)==3 else 0);self.observe(held)

    def test_clock_exception_after_prefix_has_unobserved_return_and_no_failed_reentry_growth(self):
        error=KeyboardInterrupt('original clock');held,wall,clock,checkpoint=self.held(Mock(side_effect=[100,101,error]))
        out=Stream([b'prefix']);err=Stream([])
        with self.assertRaises(KeyboardInterrupt) as first:self.capture(held,wall,out,err)
        capture=held.raw_captures[0];ops=capture.wall_operations;reads=capture.operations
        self.assertIs(first.exception,error);self.assertFalse(ops[-1][1]);self.assertIs(ops[-1][3],error)
        held.error=None;capture.error=None
        with self.assertRaises(KeyboardInterrupt) as again:self.capture(held,wall,out,err)
        self.assertIs(again.exception,error);self.assertIs(capture.wall_operations,ops)
        self.assertIs(capture.operations,reads);self.assertEqual((clock.call_count,checkpoint.call_count),(3,3))
        self.observe(held)

    def test_clock_reentry_swallowed_by_callback_keeps_original_return_and_first_refusal(self):
        errors=[];out=Stream([]);err=Stream([])
        def callback():
            try:self.capture(held,wall,out,err)
            except ValueError as error:errors.append(error)
            return 100
        held,wall,clock,_=self.held(Mock(side_effect=callback))
        with self.assertRaises(ValueError) as first:self.capture(held,wall,out,err)
        self.assertIs(first.exception,errors[0]);self.assertEqual(held.raw_captures[0].wall_operations[-1][2],100)
        self.assertEqual((clock.call_count,out.getters,err.getters),(1,0,0));self.observe(held)

    def test_clock_callback_public_ledger_erasure_is_not_overwritten_by_return_storage(self):
        def callback():
            held.raw_captures[0].wall_operations=None
            return 100
        held,wall,_,_=self.held(Mock(side_effect=callback));out=Stream([])
        with self.assertRaisesRegex(ValueError,'private return bindings'):self.capture(held,wall,out)
        capture=held._SourceObjectBatchContractPreparation__captures[0]
        self.assertIsNone(capture.wall_operations)
        self.assertEqual(capture._SourceObjectBatchRawCapture__wall_operations[-1][2],100)
        self.assertEqual(out.getters,0);self.observe(held)

    def test_read_callback_private_wall_binding_erasure_keeps_raw_and_refuses_more_reads(self):
        held,wall,_,_=self.held()
        class Mutated(Stream):
            def _read(self,size):
                self.calls.append(size)
                held.raw_captures[0]._SourceObjectBatchRawCapture__wall_binding=None
                return b'prefix'
        out=Mutated([]);err=Stream([])
        with self.assertRaisesRegex(ValueError,'private return bindings'):self.capture(held,wall,out,err)
        self.assertEqual(held.raw_captures[0].prefixes[0],(b'prefix',))
        self.assertEqual((len(out.calls),err.getters),(1,0));self.observe(held)

    def test_cached_equal_foreign_wall_tuple_is_retained_and_refused_without_clock_replay(self):
        held,wall,clock,checkpoint=self.held();out=Stream([b'1'*40+b'\n',b'']);err=Stream([b''])
        result=self.capture(held,wall,out,err);capture=held.raw_captures[0]
        counts=(clock.call_count,checkpoint.call_count,len(out.calls),len(err.calls))
        foreign=tuple(list(wall));self.assertIsNot(foreign,wall)
        with self.assertRaisesRegex(ValueError,'same original inputs'):self.capture(held,foreign,out,err)
        self.assertIs(capture._SourceObjectBatchRawCapture__rejected_wall_inputs,foreign)
        self.assertIs(capture._SourceObjectBatchRawCapture__result,result)
        self.assertEqual((clock.call_count,checkpoint.call_count,len(out.calls),len(err.calls)),counts);self.observe(held)

    def test_wall_capture_foreign_stream_preserves_original_rejected_tuple_positions(self):
        held,wall,clock,checkpoint=self.held();out=Stream([b'1'*40+b'\n',b'']);err=Stream([b''])
        self.capture(held,wall,out,err);capture=held.raw_captures[0];foreign=Stream([])
        counts=(clock.call_count,checkpoint.call_count)
        with self.assertRaisesRegex(ValueError,'same original inputs'):self.capture(held,wall,foreign,err)
        rejected=capture._SourceObjectBatchRawCapture__rejected_inputs
        self.assertEqual(len(rejected),7);self.assertIs(rejected[0],held);self.assertEqual(rejected[1],0)
        self.assertIs(rejected[2],foreign);self.assertIs(rejected[3],err)
        self.assertIs(capture._SourceObjectBatchRawCapture__rejected_wall_inputs,wall)
        self.assertEqual((clock.call_count,checkpoint.call_count),counts)
        self.assertEqual(foreign.getters,0);self.observe(held)

    def test_invalid_closed_wall_windows_reject_before_checkpoint_clock_or_stream_getter(self):
        for change in ('list','arity','clock','bool','zero','reverse','duration','range'):
            held,wall,clock,checkpoint=self.held();out=Stream([])
            variants={'list':list(wall),'arity':wall[:2],'clock':(None,100,200),'bool':(clock,True,200),
                'zero':(clock,100,100),'reverse':(clock,200,100),'duration':(clock,0,30000000001),
                'range':(clock,9223372036854775807,9223372036854775808)}
            with self.subTest(change=change),self.assertRaises(ValueError):self.capture(held,variants[change],out)
            capture=held.raw_captures[0];self.assertIs(capture.read_wall_inputs,variants[change])
            self.assertEqual((clock.call_count,checkpoint.call_count,out.getters),(0,0,0));self.observe(held)

    def test_original_parent_keeper_retains_clock_late_return_and_stream_after_alias_erasure(self):
        parent=reader.ReaderGitParent.__new__(reader.ReaderGitParent)
        held,wall,clock,_=self.held(Mock(side_effect=[100,101,200]),parent=parent);out=Stream([b'prefix'])
        with self.assertRaises(ValueError) as first:self.capture(held,wall,out)
        parent.source_object_batch_owner=None;held.raw_captures=None
        parent.original_bootstrap_inputs=(None,)*11;parent.worker=None;parent.error=None
        class Escape(BaseException):pass
        with patch.object(reader.ParentPublicationRetention,'_pause',side_effect=Escape),self.assertRaises(Escape):
            reader.retain_parent_publications(first.exception,parent)
        capture=held._SourceObjectBatchContractPreparation__captures[0]
        self.assertIn(held,parent.original_publication_retention.owners)
        self.assertIs(capture.read_wall_inputs[0],clock);self.assertIs(capture.original_inputs[2],out)
        self.assertEqual(capture.wall_operations[-1][2],200);self.assertFalse(out.closed);self.observe(held)
