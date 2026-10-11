"""Same original Python worker/stdio/window; no native supervisor run."""
import io
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_reader_git_worker as reader
from banto_ai import anomaly_v03_process_supervisor as supervisor
from tests import test_anomaly_v03_source_object_batch_contract as fixtures

OBSERVATIONS = []


class Stream:
    def __init__(self, values):
        self.values = iter(values);self.getters = 0;self.calls = []

    @property
    def read(self):
        self.getters += 1
        return self._read

    def _read(self, size):
        self.calls.append(size)
        value = next(self.values)
        if callable(value):value = value()
        if isinstance(value,BaseException):raise value
        return value


class SourceObjectSupervisorCallsiteTests(unittest.TestCase):
    def held(self, clock=None):
        parent = reader.ReaderGitParent.__new__(reader.ReaderGitParent)
        parent.worker = object();parent.error = None
        parent.inventory_publication = parent.inventory_publication_error = parent.inventory_pending_owner = None
        parent.original_bootstrap_inputs = (None,)*11
        parent.inventory_checkpoint = Mock(return_value=None)
        raw,sources,bodies,maxima,storage = fixtures.fixture()
        preparation = parent.prepare_source_object_batch_contract(request_raw=raw,expected_sources=sources,
            source_bodies=bodies,raw_maxima=maxima,storage_maxima=storage)
        clock = clock if clock is not None else Mock(return_value=100)
        return parent,preparation,(clock,100,200),clock

    def capture(self, parent, wall, stdout=None, stderr=None, index=0):
        stdout = stdout if stdout is not None else Stream([b'1'*40+b'\n',b''])
        stderr = stderr if stderr is not None else Stream([b''])
        return parent.capture_supervisor_source_object(index,stdout,stderr,b'opaque',exit_code=0,read_wall=wall)

    def observe(self, parent, preparation):
        callsite = parent._ReaderGitParent__source_object_supervisor_callsites[-1]
        captures = preparation._SourceObjectBatchContractPreparation__captures
        OBSERVATIONS.append({'test':self.id(),'callsites':len(preparation._SourceObjectBatchContractPreparation__supervisor_callsites),
            'records':len(preparation._SourceObjectBatchContractPreparation__records),
            'read_returns':len(captures[-1]._SourceObjectBatchRawCapture__operations) if captures else 0,
            'wall_returns':len(captures[-1]._SourceObjectBatchRawCapture__wall_operations) if captures else 0,
            'prefix_bytes':[sum(map(len,p)) for p in captures[-1]._SourceObjectBatchRawCapture__prefixes] if captures else [],
            'call_return_observed':callsite.capture_return_observed,'original_worker_held':callsite.original_binding[1] is not None,
            'native_runs':0,'execution_authenticated':False,'formal_permission':False})

    def test_real_fileio_original_worker_window_and_cached_return_do_not_close_or_repeat(self):
        parent,preparation,_,_ = self.held();clock=time.monotonic_ns;started=clock();wall=(clock,started,started+30000000000)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'stdout';path.write_bytes(b'1'*40+b'\n')
            with path.open('rb',buffering=0) as stdout,io.BytesIO() as stderr:
                returned=self.capture(parent,wall,stdout,stderr);callsite=parent.source_object_supervisor_callsites[0]
                count=parent.inventory_checkpoint.call_count
                self.assertIs(self.capture(parent,wall,stdout,stderr),returned)
                self.assertEqual(parent.inventory_checkpoint.call_count,count)
                self.assertIs(callsite.original_binding[1],parent.worker)
                self.assertIs(preparation.raw_captures[0].read_wall_inputs,wall)
                self.assertFalse(stdout.closed);self.assertFalse(stderr.closed)
                self.assertTrue(all(value is False for value in json.loads(returned[1])['scope'].values()))
        self.observe(parent,preparation)

    def test_next_call_keeps_previous_callsite_and_absolute_window(self):
        parent,preparation,wall,clock=self.held();first=self.capture(parent,wall)
        second=self.capture(parent,wall,Stream([b'']),index=1)
        self.assertEqual(len(preparation.records),2);self.assertEqual(preparation.records[0]['incoming'],first[0])
        self.assertEqual(preparation.records[1]['incoming'],second[0]);self.assertEqual(len(parent.source_object_supervisor_callsites),2)
        self.assertTrue(all(c.read_wall_inputs is wall for c in preparation.raw_captures));self.observe(parent,preparation)

    def test_expired_supervisor_window_refuses_before_stream_getters(self):
        parent,preparation,wall,clock=self.held(Mock(return_value=200));stdout=Stream([]);stderr=Stream([])
        with self.assertRaisesRegex(ValueError,'read wall deadline'):self.capture(parent,wall,stdout,stderr)
        self.assertEqual((stdout.getters,stderr.getters),(0,0));self.assertEqual(clock.call_count,1)
        self.assertIs(parent.source_object_supervisor_callsites[0].original_inputs[2],stdout);self.observe(parent,preparation)

    def test_late_original_read_prefix_is_held_without_stderr_or_record(self):
        parent,preparation,wall,clock=self.held(Mock(side_effect=[100,101,200]));literal=b'late';stdout=Stream([literal]);stderr=Stream([])
        with self.assertRaisesRegex(ValueError,'read wall deadline'):self.capture(parent,wall,stdout,stderr)
        capture=preparation.raw_captures[0];self.assertIs(capture.operations[0][2],literal)
        self.assertIs(capture.prefixes[0][0],literal);self.assertEqual(stderr.getters,0);self.assertEqual(preparation.records,())
        self.observe(parent,preparation)

    def test_worker_replacement_during_read_retains_original_worker_and_return(self):
        parent,preparation,wall,clock=self.held();worker=parent.worker;literal=b'original'
        def replace():parent.worker=object();return literal
        stdout=Stream([replace]);stderr=Stream([])
        with self.assertRaisesRegex(ValueError,'same original parent worker'):self.capture(parent,wall,stdout,stderr)
        self.assertIs(parent.source_object_supervisor_callsites[0].original_binding[1],worker)
        self.assertIs(preparation.raw_captures[0].operations[0][2],literal);self.assertEqual(stderr.getters,0)
        self.observe(parent,preparation)

    def test_reentry_swallowed_by_read_callback_still_latches_first_error(self):
        parent,preparation,wall,clock=self.held();caught=[];literal=b'kept';stderr=Stream([])
        def reenter():
            try:self.capture(parent,wall,stdout,stderr)
            except BaseException as error:caught.append(error)
            return literal
        stdout=Stream([reenter])
        with self.assertRaisesRegex(ValueError,'cannot reenter') as outer:self.capture(parent,wall,stdout,stderr)
        self.assertIs(outer.exception,caught[0]);self.assertIs(preparation.raw_captures[0].operations[0][2],literal)
        self.assertEqual(stderr.getters,0);self.observe(parent,preparation)

    def test_parent_callsite_alias_erasure_during_read_is_not_repaired(self):
        parent,preparation,wall,clock=self.held();literal=b'kept'
        def erase():parent.source_object_supervisor_callsites=();return literal
        with self.assertRaisesRegex(ValueError,'private bindings'):self.capture(parent,wall,Stream([erase]))
        self.assertEqual(parent.source_object_supervisor_callsites,())
        self.assertEqual(len(parent._ReaderGitParent__source_object_supervisor_callsites),1)
        self.assertIs(preparation.raw_captures[0].operations[0][2],literal);self.observe(parent,preparation)

    def test_preparation_callsite_ledger_erasure_stops_after_original_return(self):
        parent,preparation,wall,clock=self.held();literal=b'kept'
        def erase():preparation.supervisor_callsites=();return literal
        with self.assertRaisesRegex(ValueError,'supervisor callsite ledger'):self.capture(parent,wall,Stream([erase]))
        self.assertEqual(preparation.supervisor_callsites,())
        self.assertIs(preparation.raw_captures[0].operations[0][2],literal);self.observe(parent,preparation)

    def test_cached_equal_but_foreign_wall_tuple_is_retained_without_repeat(self):
        parent,preparation,wall,clock=self.held();stdout=Stream([b'1'*40+b'\n',b'']);stderr=Stream([b''])
        self.capture(parent,wall,stdout,stderr);count=clock.call_count;ops=preparation.raw_captures[0].operations
        foreign=tuple(list(wall));self.assertIsNot(foreign,wall)
        with self.assertRaisesRegex(ValueError,'cannot be replaced'):self.capture(parent,foreign,stdout,stderr)
        callsite=parent.source_object_supervisor_callsites[0];self.assertIs(callsite.rejected_inputs[-1],foreign)
        self.assertEqual(clock.call_count,count);self.assertIs(preparation.raw_captures[0].operations,ops)
        self.observe(parent,preparation)

    def test_original_supervise_callsite_denies_before_clock_probe_paths_and_process(self):
        parent,preparation,wall,clock=self.held();self.capture(parent,wall);callsite=parent.source_object_supervisor_callsites[0]
        argv=['unissued'];cwd=object();root=object();limits={};probe=Mock();boundary=Mock();started=Mock();stop=Mock()
        with patch.object(supervisor.time,'monotonic',side_effect=AssertionError('clock')), \
             patch.object(supervisor.subprocess,'Popen',side_effect=AssertionError('native')), \
             patch.object(supervisor.rt,'regular_path',side_effect=AssertionError('path')):
            with self.assertRaisesRegex(ValueError,'preparation only'):
                supervisor.supervise(argv,cwd,root,limits,runtime_probe=probe,boundary=boundary,
                    on_started=started,stop_fence=stop,source_object_callsite=callsite)
        incoming=callsite.supervision_inputs
        self.assertIs(incoming[0],argv);self.assertIs(incoming[1],cwd);self.assertIs(incoming[2],root)
        self.assertIs(incoming[3],limits);probe.assert_not_called();boundary.assert_not_called();started.assert_not_called();stop.assert_not_called()
        self.assertEqual(len(preparation.records),1);self.observe(parent,preparation)

    def test_unknown_read_keeps_original_exception_streams_and_existing_parent_retention(self):
        parent,preparation,wall,clock=self.held();error=KeyboardInterrupt('original');stdout=Stream([error]);stderr=Stream([])
        with self.assertRaises(KeyboardInterrupt) as caught:self.capture(parent,wall,stdout,stderr)
        self.assertIs(caught.exception,error);capture=preparation.raw_captures[0]
        self.assertFalse(capture.operations[0][1]);self.assertIs(capture.operations[0][3],error)
        original=parent._ReaderGitParent__source_object_supervisor_callsites
        parent.source_object_supervisor_callsites=()
        class Escape(BaseException):pass
        with patch.object(reader.ParentPublicationRetention,'hold',side_effect=Escape):
            with self.assertRaises(Escape):reader.retain_parent_publications(error,parent)
        retention=parent.original_publication_retention
        self.assertTrue(any(owner is original for owner in retention.owners));self.assertIs(retention.original_error,error)
        self.assertIs(original[0].original_inputs[2],stdout);self.assertEqual(stderr.getters,0)
        self.observe(parent,preparation)

    def test_failed_reentry_does_not_add_callsites_raw_or_wall_operations(self):
        parent,preparation,wall,clock=self.held(Mock(return_value=200));stdout=Stream([]);stderr=Stream([])
        with self.assertRaises(ValueError) as first:self.capture(parent,wall,stdout,stderr)
        callsites=parent._ReaderGitParent__source_object_supervisor_callsites;capture=preparation.raw_captures[0]
        ops=capture.operations;wallops=capture.wall_operations;count=clock.call_count
        with self.assertRaises(ValueError) as second:self.capture(parent,wall,stdout,stderr)
        self.assertIs(second.exception,first.exception);self.assertIs(parent._ReaderGitParent__source_object_supervisor_callsites,callsites)
        self.assertIs(capture.operations,ops);self.assertIs(capture.wall_operations,wallops);self.assertEqual(clock.call_count,count)
        self.observe(parent,preparation)

    def test_second_initialization_keeps_original_inputs_worker_and_raw_return(self):
        parent,preparation,wall,clock=self.held();returned=self.capture(parent,wall)
        callsite=parent.source_object_supervisor_callsites[0];incoming=callsite.original_inputs;binding=callsite.original_binding
        foreign=(object(),)*8
        with self.assertRaisesRegex(ValueError,'initializes once'):callsite._retain(foreign)
        self.assertIs(callsite.original_inputs,incoming);self.assertIs(callsite.original_binding,binding)
        self.assertIs(callsite.capture_return,returned);self.assertIs(callsite.rejected_initialization_inputs,foreign)
        self.observe(parent,preparation)

    def test_second_worker_binding_cannot_replace_original_worker_or_preparation(self):
        parent,preparation,wall,clock=self.held();self.capture(parent,wall)
        callsite=parent.source_object_supervisor_callsites[0];binding=callsite.original_binding;foreign=object()
        with self.assertRaisesRegex(ValueError,'binding cannot be replaced'):callsite.bind_originals(preparation,foreign)
        self.assertIs(callsite.original_binding,binding);self.assertIs(callsite.rejected_original_binding[1],foreign)
        self.observe(parent,preparation)

    def test_worker_getter_interrupt_keeps_callsite_inputs_before_binding_and_reads(self):
        parent,preparation,wall,clock=self.held();stdout=Stream([]);stderr=Stream([]);error=KeyboardInterrupt('worker getter')
        def getter(_):raise error
        with patch.object(reader.ReaderGitParent,'worker',property(getter),create=True):
            with self.assertRaises(KeyboardInterrupt) as caught:self.capture(parent,wall,stdout,stderr)
        self.assertIs(caught.exception,error);callsite=parent._ReaderGitParent__source_object_supervisor_callsites[0]
        self.assertIs(callsite.preparation_getter_return,preparation);self.assertIs(callsite.original_inputs[2],stdout)
        self.assertIs(callsite.original_inputs[-1],wall);self.assertIs(callsite.error,error)
        self.assertIsNone(callsite.original_binding);self.assertEqual(preparation.raw_captures,())
        self.assertEqual((stdout.getters,stderr.getters),(0,0));clock.assert_not_called()
