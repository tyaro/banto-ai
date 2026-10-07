"""Bounded output sink IO/owner preservation; no native pipe or Job trial."""
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_owned_git_job as git
from banto_ai import anomaly_v03_preformal_reader_git_worker as reader


class BoundedGitSpoolTests(unittest.TestCase):
    def spool(self, stream=None, *, maximum=9, checkpoint=None, sync=None):
        return git.BoundedGitSpool(stream if stream is not None else io.BytesIO(),
            operation='source_blob', output='stdout', maximum_stored_bytes=maximum,
            checkpoint=checkpoint if checkpoint is not None else lambda: None,
            sync=sync if sync is not None else lambda: None)

    def test_actual_file_payload_and_eof_close(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'stdout.bin'
            stream=path.open('xb');spool=self.spool(stream,sync=lambda:os.fsync(stream.fileno()))
            self.assertIsNone(spool.append(b'abc'))
            self.assertIsNone(spool.append(b'defgh'))
            spool.finish_eof()
            self.assertEqual(path.read_bytes(),b'abcdefgh')
            self.assertIs(spool.stream,stream)
            self.assertTrue(spool.closed)

    def test_overflow_sentinel_stops_reads_and_retains_original_stream(self):
        stream=io.BytesIO();spool=self.spool(stream)
        self.assertEqual(spool.append(b'abcdefghi'),'output_limit')
        self.assertEqual(spool.next_read_size(),0)
        self.assertEqual(stream.getvalue(),b'abcdefghi')
        with self.assertRaises(git.BoundedSpoolFailure) as raised:spool.finish_eof()
        self.assertIs(raised.exception.spool,spool)
        self.assertFalse(stream.closed)

    def test_overlong_block_is_retained_before_write(self):
        stream=io.BytesIO();spool=self.spool(stream);raw=b'0123456789'
        with self.assertRaises(git.BoundedSpoolFailure):spool.append(raw)
        self.assertIs(spool.pending_raw,raw)
        self.assertEqual(stream.getvalue(),b'')
        self.assertFalse(stream.closed)

    def test_partial_write_is_not_retried(self):
        stream=Mock();stream.write.return_value=2;spool=self.spool(stream);raw=b'abc'
        with self.assertRaises(git.BoundedSpoolFailure) as raised:spool.append(raw)
        with self.assertRaises(git.BoundedSpoolFailure) as repeated:spool.append(b'd')
        self.assertIs(repeated.exception,raised.exception)
        self.assertIs(spool.pending_raw,raw)
        stream.write.assert_called_once_with(raw);stream.close.assert_not_called()

    def test_write_interrupt_retains_original_exception_and_stream(self):
        error=KeyboardInterrupt();stream=Mock();stream.write.side_effect=error
        spool=self.spool(stream);raw=b'abc'
        with self.assertRaises(git.BoundedSpoolFailure) as raised:spool.append(raw)
        self.assertIs(raised.exception.original_error,error)
        self.assertIs(raised.exception.spool.stream,stream)
        self.assertIs(spool.pending_raw,raw)
        stream.close.assert_not_called()

    def test_flush_failure_retains_written_block_without_more_io(self):
        stream=Mock();stream.write.return_value=3;stream.flush.side_effect=OSError('flush')
        spool=self.spool(stream);raw=b'abc'
        with self.assertRaises(git.BoundedSpoolFailure) as raised:spool.append(raw)
        with self.assertRaises(git.BoundedSpoolFailure) as repeated:spool.next_read_size()
        self.assertIs(repeated.exception,raised.exception)
        self.assertEqual(spool.committed_bytes,3)
        self.assertIs(spool.pending_raw,raw)
        stream.write.assert_called_once_with(raw);stream.close.assert_not_called()

    def test_sync_failure_retains_original_pending_raw(self):
        error=OSError('sync');stream=io.BytesIO();spool=self.spool(stream,sync=Mock(side_effect=error));raw=b'abc'
        with self.assertRaises(git.BoundedSpoolFailure) as raised:spool.append(raw)
        self.assertIs(raised.exception.original_error,error)
        self.assertEqual(stream.getvalue(),raw)
        self.assertIs(spool.pending_raw,raw);self.assertFalse(stream.closed)

    def test_shared_checkpoint_interrupt_occurs_before_write(self):
        error=KeyboardInterrupt();stream=Mock();spool=self.spool(stream,checkpoint=Mock(side_effect=error))
        with self.assertRaises(git.BoundedSpoolFailure) as raised:spool.append(b'abc')
        self.assertIs(raised.exception.original_error,error)
        stream.write.assert_not_called();stream.close.assert_not_called()

    def test_unknown_close_is_not_repeated(self):
        error=OSError('close');stream=Mock();stream.close.side_effect=error;spool=self.spool(stream)
        with self.assertRaises(git.BoundedSpoolFailure) as raised:spool.finish_eof()
        with self.assertRaises(git.BoundedSpoolFailure) as repeated:spool.finish_eof()
        self.assertIs(repeated.exception,raised.exception)
        self.assertIs(raised.exception.original_error,error)
        self.assertIs(raised.exception.spool.stream,stream)
        stream.close.assert_called_once()

    def test_invalid_cap_retains_original_stream(self):
        stream=io.BytesIO()
        with self.assertRaises(git.BoundedSpoolFailure) as raised:self.spool(stream,maximum=True)
        self.assertIs(raised.exception.spool.stream,stream)
        self.assertFalse(stream.closed)

    def test_each_pipe_read_is_bounded_before_large_cap_is_exhausted(self):
        stream=io.BytesIO();spool=self.spool(stream,maximum=9000)
        self.assertEqual(spool.next_read_size(),4096)
        spool.append(b'x'*4096);spool.append(b'y'*4096)
        self.assertEqual(spool.next_read_size(),808)
        self.assertEqual(spool.append(b'z'*808),'output_limit')
        self.assertEqual(len(stream.getvalue()),9000)
        self.assertFalse(stream.closed)

    def test_limited_native_entry_rejects_metadata_before_any_owner_or_root(self):
        with patch.object(reader.ReaderGitParent,'create') as create, \
             patch.object(reader.channel.ParentChannel,'create') as channel, \
             patch.object(reader.tree,'run_owned') as run:
            with self.assertRaises(reader.monitor.resources.ResourceStop) as raised:
                reader.ReaderGitParent.create_native(capture_bounded=True,proof={'closed':True})
            self.assertEqual(str(raised.exception),'reader_git_native_capture_not_connected')
            create.assert_not_called();channel.assert_not_called();run.assert_not_called()
