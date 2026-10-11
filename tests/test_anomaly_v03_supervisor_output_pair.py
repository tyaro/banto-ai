"""Supervisor module issued FileIO pair preparation; no real worker or native permission."""
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


class SupervisorOutputPairTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.native = patch.object(supervisor.subprocess,'Popen',side_effect=AssertionError('native forbidden'))
        self.native.start();self.addCleanup(self.native.stop)
        self.parent = reader.ReaderGitParent.__new__(reader.ReaderGitParent)
        self.parent.worker = object();self.parent.error = None
        self.parent.inventory_publication = self.parent.inventory_publication_error = self.parent.inventory_pending_owner = None
        self.parent.original_bootstrap_inputs = (None,)*11
        self.parent.inventory_checkpoint = Mock(return_value=None)
        raw,sources,bodies,maxima,storage = fixtures.fixture()
        self.preparation = self.parent.prepare_source_object_batch_contract(request_raw=raw,expected_sources=sources,
            source_bodies=bodies,raw_maxima=maxima,storage_maxima=storage)
        self.out = Path(self.directory.name)/'stdout.jsonl'
        self.err = Path(self.directory.name)/'stderr.json'
        self.clock = Mock(return_value=100);self.wall = (self.clock,100,200)
        self.receipt = b'opaque receipt';self.partial = b'partial'
        self.held = None
        self.addCleanup(self.cleanup_streams)

    def pair(self, factory=None):
        with patch.object(supervisor,'SOURCE_OBJECT_OUTPUT_FILEIO',factory or io.FileIO):
            self.held = self.parent.prepare_supervisor_source_object_output_pair(0,self.out,self.err,self.receipt,
                exit_code=0,partial=self.partial,read_wall=self.wall)
        return self.held

    def cleanup_streams(self):
        if self.held is None:return
        streams = list(self.held._SourceObjectOutputPairPreparation__writers)+list(self.held._SourceObjectOutputPairPreparation__readers)
        for row in self.held._SourceObjectOutputPairPreparation__operations:
            if row[3] and isinstance(row[4],io.FileIO):streams.append(row[4])
        for stream in streams:
            if not stream.closed:io.FileIO.close(stream)  # Test cleanup is not production/native recovery.

    def write(self, held):
        stdout,stderr = held.issue_writers()
        stdout.write(b'1'*40+b'\n');stderr.write(b'')
        return stdout,stderr

    def observe(self):
        held = self.held
        rows = held._SourceObjectOutputPairPreparation__operations
        OBSERVATIONS.append({'test':self.id(),'operations':len(rows),'opens':sum(r[0].startswith('open_') for r in rows),
            'close_observed':[(r[3],r[4] is None,type(r[5]).__name__ if r[5] is not None else None) for r in rows if r[0]=='close'],
            'writers':len(held._SourceObjectOutputPairPreparation__writers),'readers':len(held._SourceObjectOutputPairPreparation__readers),
            'records':len(self.preparation._SourceObjectBatchContractPreparation__records),
            'native_runs':0,'execution_authenticated':False,'formal_permission':False})

    def test_real_issued_pair_close_identity_window_receipt_and_cached_capture(self):
        start = time.monotonic_ns();self.wall = (time.monotonic_ns,start,start+30000000000)
        held = self.pair();writers = self.write(held)
        self.assertIs(held.issue_writers(),held.writers)
        closed = held.close_writers();self.assertEqual(closed,(None,None))
        self.assertIs(held.close_writers(),closed)
        returned = held.capture();count = len(held.operations);calls = self.parent.inventory_checkpoint.call_count
        self.assertIs(held.capture(),returned);self.assertEqual(len(held.operations),count)
        self.assertEqual(self.parent.inventory_checkpoint.call_count,calls)
        callsite = self.parent.source_object_supervisor_callsites[0]
        self.assertIs(callsite.original_output_pair,held)
        self.assertIs(callsite.original_inputs[-1],self.wall)
        self.assertIs(callsite.original_inputs[4],self.receipt);self.assertIs(callsite.original_inputs[6],self.partial)
        self.assertTrue(all(w.closed for w in writers));self.assertTrue(all(not r.closed for r in held.readers))
        self.assertTrue(all(value is False for value in json.loads(returned[1])['scope'].values()))
        self.observe()

    def test_unknown_close_before_return_preserves_first_error_and_existing_retention(self):
        problem = KeyboardInterrupt('original close')
        class Unknown(io.FileIO):
            def close(stream):raise problem
        held = self.pair(Unknown);self.write(held)
        with self.assertRaises(KeyboardInterrupt) as first:held.close_writers()
        self.assertIs(first.exception,problem);row = next(r for r in held.operations if r[0]=='close')
        self.assertFalse(row[3]);self.assertIs(row[5],problem);self.assertFalse(held.writers[0].closed)
        count = len(held.operations)
        with self.assertRaises(KeyboardInterrupt) as again:held.capture()
        self.assertIs(again.exception,problem);self.assertEqual(len(held.operations),count)
        original = self.parent._ReaderGitParent__source_object_output_pairs
        self.parent.source_object_output_pairs = ()
        class Escape(BaseException):pass
        with patch.object(reader.ParentPublicationRetention,'hold',side_effect=Escape):
            with self.assertRaises(Escape):reader.retain_parent_publications(problem,self.parent)
        self.assertTrue(any(o is original for o in self.parent.original_publication_retention.owners))
        self.assertIs(self.parent.original_publication_retention.original_error,problem);self.observe()

    def test_closed_flag_after_unknown_close_cannot_open_readers_or_close_stderr(self):
        problem = OSError('return unknown')
        class Unknown(io.FileIO):
            def close(stream):
                io.FileIO.close(stream)
                raise problem
        held = self.pair(Unknown);self.write(held)
        with self.assertRaises(OSError) as first:held.close_writers()
        self.assertIs(first.exception,problem);self.assertTrue(held.writers[0].closed)
        self.assertFalse(held.writers[1].closed);self.assertEqual(held.close_returns,())
        with self.assertRaises(OSError):held.capture()
        self.assertEqual(held.readers,());self.assertEqual(sum(r[0]=='close' for r in held.operations),1);self.observe()

    def test_non_none_literal_close_return_is_kept_and_stops_second_close(self):
        literal = object()
        class Invalid(io.FileIO):
            def close(stream):
                io.FileIO.close(stream);return literal
        held = self.pair(Invalid);self.write(held)
        with self.assertRaisesRegex(ValueError,'literal close return'):held.close_writers()
        row = next(r for r in held.operations if r[0]=='close')
        self.assertTrue(row[3]);self.assertIs(row[4],literal);self.assertIs(held.close_returns[0],literal)
        self.assertFalse(held.writers[1].closed);self.assertEqual(held.readers,());self.observe()

    def test_second_open_failure_keeps_first_owned_stream_without_replay_or_close(self):
        problem = OSError('second original open');created = []
        def factory(path,mode):
            if path is self.err:raise problem
            stream = io.FileIO(path,mode);created.append(stream);return stream
        held = self.pair(factory)
        with self.assertRaises(OSError) as first:held.issue_writers()
        self.assertIs(first.exception,problem);self.assertIs(held.writers[0],created[0])
        self.assertFalse(created[0].closed);count = len(held.operations)
        with self.assertRaises(OSError) as again:held.issue_writers()
        self.assertIs(again.exception,problem);self.assertEqual(len(held.operations),count);self.observe()

    def test_replaced_path_keeps_original_read_return_and_refuses_before_capture(self):
        held = self.pair();self.write(held);held.close_writers()
        self.out.rename(self.out.with_name('original'))
        self.out.write_bytes(b'1'*40+b'\n')
        with self.assertRaisesRegex(ValueError,'original read identity'):held.capture()
        self.assertEqual(len(held.readers),1);self.assertFalse(held.readers[0].closed)
        self.assertEqual(self.preparation.records,());self.assertFalse(hasattr(self.parent,'source_object_supervisor_callsites'))
        self.observe()

    def test_independent_stdout_bound_stops_before_stream_reads_or_stderr_open(self):
        held = self.pair();stdout,stderr = held.issue_writers();stdout.write(b'x'*42)
        held.close_writers()
        with self.assertRaisesRegex(ValueError,'independent raw byte bound'):held.capture()
        self.assertEqual(len(held.readers),1);self.assertEqual(self.preparation.records,())
        self.assertFalse(hasattr(self.parent,'source_object_supervisor_callsites'));self.observe()

    def test_expired_original_window_refuses_before_first_file_factory(self):
        factory = Mock(side_effect=AssertionError('no open'));self.clock.return_value = 200
        held = self.pair(factory)
        with self.assertRaisesRegex(ValueError,'original deadline'):held.issue_writers()
        factory.assert_not_called();self.assertEqual(held.writers,())
        self.assertIs(held.original_inputs[-1],self.wall);self.observe()

    def test_swallowed_factory_reentry_keeps_original_file_return_and_first_error(self):
        caught = [];created = []
        def factory(path,mode):
            try:self.held.issue_writers()
            except BaseException as error:caught.append(error)
            stream = io.FileIO(path,mode);created.append(stream);return stream
        held = self.pair(factory)
        with self.assertRaisesRegex(ValueError,'cannot reenter') as first:held.issue_writers()
        self.assertIs(first.exception,caught[0]);row = next(r for r in held.operations if r[0]=='open_xb')
        self.assertTrue(row[3]);self.assertIs(row[4],created[0]);self.assertFalse(created[0].closed)
        self.assertFalse(self.err.exists());self.observe()

    def test_pair_alias_erased_during_read_keeps_literal_prefix_and_stops_stderr(self):
        original = b'1'*40+b'\n'
        class Erase(io.FileIO):
            def read(stream,size):
                value = io.FileIO.read(stream,size)
                self.parent.source_object_output_pairs = ()
                return value
        held = self.pair(Erase);self.write(held);held.close_writers()
        with self.assertRaisesRegex(ValueError,'private original bindings'):held.capture()
        raw = self.preparation.raw_captures[0]
        self.assertEqual(raw.prefixes[0],(original,));self.assertEqual(raw.prefixes[1],())
        self.assertEqual(len(raw.operations),1);self.assertEqual(self.preparation.records,())
        self.assertIs(self.parent.source_object_supervisor_callsites[0].original_output_pair,held)
        self.observe()

    def test_deadline_after_close_return_keeps_none_and_does_not_close_next_stream(self):
        class Late(io.FileIO):
            def close(stream):
                returned = io.FileIO.close(stream);self.clock.return_value = 200;return returned
        held = self.pair(Late);self.write(held)
        with self.assertRaisesRegex(ValueError,'original deadline'):held.close_writers()
        self.assertEqual(held.close_returns,(None,));self.assertTrue(held.writers[0].closed)
        self.assertFalse(held.writers[1].closed);self.assertEqual(held.readers,());self.observe()

    def test_second_prepare_cannot_replace_worker_callback_inputs_or_issue_files(self):
        held = self.pair();inputs = held.original_inputs;worker = held.worker_getter_return;callback = held.capture_callback
        with self.assertRaisesRegex(ValueError,'prepares once'):held.prepare()
        self.assertIs(held.original_inputs,inputs);self.assertIs(held.worker_getter_return,worker)
        self.assertIs(held.capture_callback,callback);self.assertEqual(held.operations,());self.observe()

    def test_second_initialization_retains_original_writers_and_rejected_inputs(self):
        held = self.pair();writers = self.write(held);inputs = held.original_inputs;foreign = (object(),)*8
        with self.assertRaisesRegex(ValueError,'initializes once'):held._retain(foreign)
        self.assertIs(held.original_inputs,inputs);self.assertIs(held.rejected_initialization_inputs,foreign)
        self.assertTrue(all(a is b for a,b in zip(held.writers,writers)))
        self.assertTrue(all(not s.closed for s in writers));self.observe()

    def test_second_read_open_failure_retains_first_reader_without_replay_or_capture(self):
        problem = OSError('stderr read open')
        def factory(path,mode):
            if path is self.err and mode == 'rb':raise problem
            return io.FileIO(path,mode)
        held = self.pair(factory);self.write(held);held.close_writers()
        with self.assertRaises(OSError) as first:held.capture()
        self.assertIs(first.exception,problem);self.assertEqual(len(held.readers),1)
        self.assertFalse(held.readers[0].closed);self.assertEqual(held.close_returns,(None,None))
        count = len(held.operations)
        with self.assertRaises(OSError) as again:held.capture()
        self.assertIs(again.exception,problem);self.assertEqual(len(held.operations),count)
        self.assertEqual(self.preparation.records,());self.observe()
