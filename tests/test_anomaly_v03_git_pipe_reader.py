"""Bounded native-call adapter and disk readback; Win API is stubbed."""
import ctypes
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_owned_git_job as git


class PipeKernel:
    def __init__(self, raw=b'abc'):
        self.raw = raw
        self.calls = []

    def PeekNamedPipe(self, handle, buffer, amount, count, available, left):
        self.calls.append(('peek', handle))
        available._obj.value = len(self.raw)
        return 1

    def ReadFile(self, handle, buffer, amount, count, overlapped):
        self.calls.append(('read', handle, amount))
        raw = self.raw[:amount]
        ctypes.memmove(buffer, raw, len(raw))
        count._obj.value = len(raw)
        self.raw = self.raw[amount:]
        return 1


class GitPipeReaderTests(unittest.TestCase):
    def make(self, raw=b'abc', cap=64, readback=None, stream_factory=None):
        directory = tempfile.TemporaryDirectory(prefix='banto-pipe-reader-')
        self.addCleanup(directory.cleanup)
        paths = {name:Path(directory.name)/name for name in ('stdout','stderr')}
        streams = {name:path.open('xb') for name,path in paths.items()}
        for stream in streams.values():
            self.addCleanup(stream.close)
        if stream_factory is not None:
            streams['stdout'] = stream_factory(streams['stdout'])
        spools = {name:git.BoundedGitSpool(stream, operation='source_blob', output=name,
            maximum_stored_bytes=cap, checkpoint=lambda:None,
            sync=lambda s=stream:os.fsync(s.fileno())) for name,stream in streams.items()}
        native = git.owner.UnreapedJob(11,22,33,{})
        held = git.GitOutputOwner(native, read_handles={'stdout':44,'stderr':55},
                                  spools=spools, checkpoint=lambda:None)
        def disk(name, amount):
            with paths[name].open('rb') as stream:
                return stream.read(amount)
        readers = {name:lambda amount,n=name:disk(n,amount) for name in paths}
        if readback is not None:
            readers['stdout'] = readback
        kernel = PipeKernel(raw)
        reader = git.GitPipeReader(held,kernel=kernel,readback=readers)
        return SimpleNamespace(native=native,held=held,reader=reader,kernel=kernel,
                               paths=paths,streams=streams,spools=spools)

    def test_exact_available_bytes_are_written_and_full_disk_checked_before_progress(self):
        f=self.make(b'abc');self.assertEqual(f.reader.read_once('stdout'),'data')
        f.kernel.raw=b'de';self.assertEqual(f.reader.read_once('stdout'),'data')
        self.assertEqual(f.kernel.calls,[('peek',44),('read',44,3),('peek',44),('read',44,2)])
        self.assertEqual(f.paths['stdout'].read_bytes(),b'abcde')
        self.assertIsNone(f.held.pending);self.assertEqual(f.spools['stdout'].committed_bytes,5)
        self.assertIs(f.native.git_output_owner.pipe_reader,f.reader)

    def test_native_read_is_at_most_4096_and_original_allowance(self):
        f=self.make(b'x'*5000,cap=6000);self.assertEqual(f.reader.read_once('stdout'),'data')
        self.assertEqual(f.kernel.calls[-1],('read',44,4096))
        self.assertEqual(f.paths['stdout'].stat().st_size,4096)

    def test_empty_availability_does_not_read_or_declare_eof(self):
        f=self.make(b'');self.assertEqual(f.reader.read_once('stdout'),'pending')
        self.assertEqual(f.kernel.calls,[('peek',44)]);self.assertEqual(f.reader.eof,{})
        self.assertIsNone(f.held.pending);self.assertFalse(f.streams['stdout'].closed)

    def test_successful_zero_byte_read_is_pending_and_keeps_original_handle(self):
        f=self.make();f.kernel.ReadFile=Mock(return_value=1)
        self.assertEqual(f.reader.read_once('stdout'),'pending');self.assertEqual(f.reader.eof,{})
        self.assertEqual(f.held.read_handles['stdout'],44);self.assertFalse(f.streams['stdout'].closed)

    def test_broken_pipe_records_eof_but_keeps_sink_and_native_owner(self):
        f=self.make();f.kernel.PeekNamedPipe=Mock(return_value=0)
        with patch.object(git.owner.ctypes,'get_last_error',return_value=109,create=True):
            self.assertEqual(f.reader.read_once('stdout'),'eof')
        self.assertEqual(f.reader.eof['stdout'],{'handle':44,'api':'PeekNamedPipe','error':109})
        self.assertFalse(f.streams['stdout'].closed);self.assertEqual(f.held.read_handles['stdout'],44)
        self.assertIs(f.native.git_output_owner,f.held)

    def test_peek_failure_preserves_original_owner_and_refuses_api_retry(self):
        f=self.make();peek=Mock(return_value=0);f.kernel.PeekNamedPipe=peek
        with patch.object(git.owner.ctypes,'get_last_error',return_value=5,create=True):
            with self.assertRaises(git.owner.UnreapedJob) as raised:f.reader.read_once('stdout')
        self.assertIs(raised.exception,f.native);self.assertEqual(f.held.pending['peek_error'],5)
        with self.assertRaises(git.owner.UnreapedJob):f.reader.read_once('stderr')
        peek.assert_called_once();self.assertEqual(f.kernel.calls,[])

    def test_read_interrupt_keeps_original_buffer_counter_and_no_second_read(self):
        f=self.make();error=KeyboardInterrupt();read=Mock(side_effect=error);f.kernel.ReadFile=read
        with self.assertRaises(git.owner.UnreapedJob) as raised:f.reader.read_once('stdout')
        self.assertIs(raised.exception,f.native);self.assertIs(f.reader.failure,error)
        self.assertEqual(len(f.held.pending['buffer']),3);self.assertIsNotNone(f.held.pending['bytes_read'])
        with self.assertRaises(git.owner.UnreapedJob):f.reader.read_once('stdout')
        read.assert_called_once();self.assertEqual(f.paths['stdout'].read_bytes(),b'')

    def test_failed_read_with_partial_bytes_keeps_raw_without_spool_write(self):
        f=self.make()
        def partial(handle,buffer,amount,count,overlapped):
            ctypes.memmove(buffer,b'abc',3);count._obj.value=3;return 0
        f.kernel.ReadFile=partial
        with patch.object(git.owner.ctypes,'get_last_error',return_value=5,create=True):
            with self.assertRaises(git.owner.UnreapedJob):f.reader.read_once('stdout')
        self.assertEqual(f.held.pending['raw'],b'abc');self.assertEqual(f.held.pending['read_error'],5)
        self.assertEqual(f.paths['stdout'].read_bytes(),b'')

    def test_changed_previous_disk_prefix_rejects_next_native_read(self):
        f=self.make();self.assertEqual(f.reader.read_once('stdout'),'data')
        f.paths['stdout'].write_bytes(b'xyz');f.kernel.raw=b'de';calls=list(f.kernel.calls)
        with self.assertRaises(git.owner.UnreapedJob):f.reader.read_once('stdout')
        self.assertEqual(f.kernel.calls,calls);self.assertEqual(f.held.pending['readback_raw'],b'xyz')

    def test_partial_sink_write_keeps_pending_buffer_raw_and_spool_failure(self):
        class Partial:
            def __init__(self,original):self.original=original
            def write(self,raw):return self.original.write(raw[:1])
            def flush(self):return self.original.flush()
            def close(self):return self.original.close()
            def fileno(self):return self.original.fileno()
        f=self.make(stream_factory=Partial)
        with self.assertRaises(git.owner.UnreapedJob):f.reader.read_once('stdout')
        self.assertEqual(f.held.pending['raw'],b'abc')
        self.assertIs(f.reader.failure,f.spools['stdout'].failure)
        self.assertEqual(f.spools['stdout'].pending_raw,b'abc')
        calls=list(f.kernel.calls)
        with self.assertRaises(git.owner.UnreapedJob):f.reader.read_once('stdout')
        self.assertEqual(f.kernel.calls,calls)

    def test_sentinel_fills_existing_cap_and_forbids_other_pipe_read(self):
        f=self.make(b'abcdefgh',cap=4)
        self.assertEqual(f.reader.read_once('stdout'),'output_limit')
        self.assertEqual(f.kernel.calls[-1],('read',44,4));self.assertEqual(f.paths['stdout'].read_bytes(),b'abcd')
        self.assertTrue(f.reader.stopped);self.assertIsNone(f.held.pending)
        with self.assertRaises(git.owner.UnreapedJob):f.reader.read_once('stderr')
        self.assertEqual(f.kernel.calls,[('peek',44),('read',44,4)])

    def test_readback_interrupt_after_write_keeps_block_and_refuses_rewrite(self):
        error=KeyboardInterrupt();readback=Mock(side_effect=[b'',error]);f=self.make(readback=readback)
        with self.assertRaises(git.owner.UnreapedJob):f.reader.read_once('stdout')
        self.assertIs(f.reader.failure,error);self.assertEqual(f.held.pending['raw'],b'abc')
        self.assertEqual(f.paths['stdout'].read_bytes(),b'abc');calls=list(f.kernel.calls)
        with self.assertRaises(git.owner.UnreapedJob):f.reader.read_once('stdout')
        self.assertEqual(f.kernel.calls,calls);self.assertEqual(readback.call_count,2)

    def test_existing_sink_bytes_are_refused_before_any_native_pipe_io(self):
        f=self.make();f.paths['stdout'].write_bytes(b'old')
        with self.assertRaises(git.owner.UnreapedJob):f.reader.read_once('stdout')
        self.assertEqual(f.kernel.calls,[]);self.assertEqual(f.held.pending['readback_raw'],b'o')
        self.assertEqual(f.spools['stdout'].committed_bytes,0)
