"""Real exclusive FileIO/root measurements; no Job, pipe or native worker."""
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_preformal_owned_git_job as git


class GitSinkAdmissionTests(unittest.TestCase):
    def prepare(self, *, limits=None, checkpoint=lambda:None):
        temporary = tempfile.TemporaryDirectory(prefix='banto-git-sink-')
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)/'outer';root.mkdir()
        identity = (root.stat().st_dev,root.stat().st_ino)
        call = {'lease':0,'phase':'pre','operation':'source_blob',
            'source_path':'src/banto_ai/anomaly_v03.py',
            'expected_output_pin':{'bytes':48839,'sha256':'a'*64},
            'raw_inventory':limits or {'receipt.json':16384,'stdout.bin':32,
                'stderr.bin':16,'partial-archive.bin':4096}}
        args = dict(root=root,root_identity=identity,revision='b'*40,
                    call=call,checkpoint=checkpoint)
        return root,call,args

    def keep_cleanup(self, held):
        for stream in held.streams.values():
            self.addCleanup(stream.close)

    def test_exclusive_empty_fileio_and_original_call_caps(self):
        root,call,args=self.prepare();held=git.GitSinkAdmission(**args).create()
        self.keep_cleanup(held)
        self.assertEqual(set(held.streams),{'stdout','stderr'})
        self.assertTrue(all(type(s) is io.FileIO and s.closefd for s in held.streams.values()))
        self.assertEqual(held.paths['stdout'].read_bytes(),b'')
        self.assertEqual(held.spools['stdout'].maximum_stored_bytes,32)
        self.assertEqual(held.call,call);self.assertIs(held.native.git_sink_admission,held)

    def test_caller_mutation_cannot_change_retained_call_or_caps(self):
        root,call,args=self.prepare();held=git.GitSinkAdmission(**args)
        call['raw_inventory']['stdout.bin']=1024**2;call['phase']='post'
        held.create();self.keep_cleanup(held)
        self.assertEqual(held.call['phase'],'pre')
        self.assertEqual(held.spools['stdout'].maximum_stored_bytes,32)

    def test_generic_failure_stdout_is_refused_before_inflight(self):
        root,call,args=self.prepare(limits={'receipt.json':16384,'stdout.bin':1024**2,
            'stderr.bin':65536,'partial-archive.bin':524288})
        with self.assertRaises(git.owner.UnreapedJob) as raised:git.GitSinkAdmission(**args)
        self.assertIs(raised.exception.git_sink_admission.original_call,call)
        self.assertFalse((root/'worker-git-inflight').exists())

    def test_measured_existing_bytes_and_reserve_are_counted(self):
        root,call,args=self.prepare();(root/'retained.bin').write_bytes(b'x'*900000)
        with self.assertRaises(git.owner.UnreapedJob):git.GitSinkAdmission(**args)
        self.assertFalse((root/'worker-git-inflight').exists())

    def test_existing_entries_include_future_raw_directory_and_diagnostics(self):
        root,call,args=self.prepare()
        for n in range(28):(root/str(n)).write_bytes(b'')
        with self.assertRaises(git.owner.UnreapedJob):git.GitSinkAdmission(**args)
        self.assertFalse((root/'worker-git-inflight').exists())

    def test_existing_inflight_raw_is_not_overwritten(self):
        root,call,args=self.prepare();old=root/'worker-git-inflight';old.mkdir()
        (old/'stdout.bin').write_bytes(b'old')
        with self.assertRaises(git.owner.UnreapedJob):git.GitSinkAdmission(**args)
        self.assertEqual((old/'stdout.bin').read_bytes(),b'old')

    def test_second_file_open_failure_keeps_first_stream_and_no_retry(self):
        root,call,args=self.prepare();held=git.GitSinkAdmission(**args)
        original=io.FileIO;failure=OSError('second sink');calls=[]
        def opened(path,mode):
            calls.append(path)
            if len(calls)==2:raise failure
            return original(path,mode)
        with patch.object(git.file_io,'FileIO',side_effect=opened):
            with self.assertRaises(git.owner.UnreapedJob) as raised:held.create()
            self.keep_cleanup(held)
            with self.assertRaises(git.owner.UnreapedJob) as again:held.create()
        self.assertIs(raised.exception,again.exception);self.assertIs(held.error,failure)
        self.assertFalse(held.streams['stdout'].closed);self.assertEqual(len(calls),2)
        self.assertEqual(held.pending['path'],root/'worker-git-inflight/stderr.bin')

    def test_post_open_checkpoint_interruption_keeps_original_stream(self):
        root,call,args=self.prepare();held=git.GitSinkAdmission(**args)
        def checkpoint():
            if held.streams:raise KeyboardInterrupt()
        held.shared_checkpoint=checkpoint
        with self.assertRaises(git.owner.UnreapedJob):held.create()
        self.keep_cleanup(held)
        self.assertIsInstance(held.error,KeyboardInterrupt)
        self.assertIs(held.pending['stream'],held.streams['stdout'])
        self.assertFalse(held.streams['stdout'].closed)

    def test_bounded_spool_stores_last_detection_byte_inside_admitted_cap(self):
        root,call,args=self.prepare(limits={'receipt.json':16384,'stdout.bin':3,'stderr.bin':1})
        held=git.GitSinkAdmission(**args).create();self.keep_cleanup(held)
        self.assertEqual(held.spools['stdout'].append(b'abc'),'output_limit')
        self.assertEqual(held.paths['stdout'].read_bytes(),b'abc')
        self.assertEqual(held.spools['stdout'].next_read_size(),0)
        self.assertIsNone(held.native.job)

    def test_later_root_growth_refuses_before_spool_write(self):
        root,call,args=self.prepare();held=git.GitSinkAdmission(**args).create()
        self.keep_cleanup(held);(root/'later.bin').write_bytes(b'x'*900000)
        with self.assertRaises(git.BoundedSpoolFailure):held.spools['stdout'].append(b'abc')
        self.assertEqual(held.paths['stdout'].read_bytes(),b'')
        self.assertEqual(held.spools['stdout'].pending_raw,b'abc')
        self.assertIsNotNone(held.error)

    def test_root_replacement_refuses_before_original_sink_creation(self):
        root,call,args=self.prepare();held=git.GitSinkAdmission(**args)
        root.rename(root.with_name('original'));root.mkdir()
        with self.assertRaises(git.owner.UnreapedJob):held.create()
        self.assertEqual(held.streams,{})
        self.assertFalse((root/'worker-git-inflight').exists())

    def test_invalid_bool_raw_cap_is_retained_before_any_file_creation(self):
        root,call,args=self.prepare();call['raw_inventory']['stdout.bin']=True
        with self.assertRaises(git.owner.UnreapedJob) as raised:git.GitSinkAdmission(**args)
        self.assertIs(raised.exception.git_sink_admission.original_call,call)
        self.assertFalse((root/'worker-git-inflight').exists())
