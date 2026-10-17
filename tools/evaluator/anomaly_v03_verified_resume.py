"""Reuse completed audits only after streaming every byte of a pinned saved run.

External, explicit single-writer resume policy. This never changes a numerical
algorithm or the pinned checkout. New records retain the original full audit.
The caller must derive and retain the snapshot hash from a completed savepoint.
"""
from contextlib import ExitStack, contextmanager
import datetime
import hashlib
import os
from pathlib import Path
import stat
import time

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_checkpoints as checkpoints
from banto_ai import _anomaly_v03_engineering_runtime as resources
from banto_ai import _anomaly_v03_io as storage
from banto_ai import _anomaly_v03_runtime as rt

FORMAT = 'anomaly-v03-verified-resume-snapshot-v1'
BUFFER_BYTES = 1024 * 1024


def _stamp(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_nlink)


def hash_regular(path, expected):
    """Bound allocation to 1 MiB; reject changes, aliases and oversize reads."""
    links = 2 if path.name in ('.complete', 'marker-pending.json') else 1
    path = rt.regular_path(path, links=links)
    before = path.lstat()
    rt.require(before.st_size == expected['bytes'], 'saved file size changed: ' + str(path))
    digest, count = hashlib.sha256(), 0
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0))
    try:
        opened = os.fstat(fd)
        # Windows lstat/fstat can expose different ctime values. Compare ctime
        # only within the same API; identity, size, mtime and links across APIs.
        rt.require(_stamp(opened)[:4] + (opened.st_nlink,) == _stamp(before)[:4] + (before.st_nlink,),
                   'saved file replaced before read')
        with os.fdopen(fd, 'rb') as stream:
            fd = None
            while raw := stream.read(BUFFER_BYTES):
                count += len(raw)
                rt.require(count <= expected['bytes'], 'saved file grew during read')
                digest.update(raw)
            rt.require(_stamp(os.fstat(stream.fileno())) == _stamp(opened), 'saved file changed during read')
        rt.require(_stamp(rt.regular_path(path, links=links).lstat()) == _stamp(before), 'saved file replaced after read')
    finally:
        if fd is not None:
            os.close(fd)
    rt.require({'bytes': count, 'sha256': digest.hexdigest()} == expected, 'saved file hash changed: ' + str(path))
    return count


def _inventory(root):
    files, directories, pending = {}, [], [root]
    while pending:
        folder = pending.pop()
        rt.regular_path(folder, directory=True)
        directories.append(folder)
        for path in folder.iterdir():
            info = path.lstat()
            rt.require(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400,
                       'reparse path in saved run')
            if stat.S_ISDIR(info.st_mode):
                pending.append(path)
            else:
                rt.require(stat.S_ISREG(info.st_mode), 'nonregular saved file')
                files[path.relative_to(root).as_posix()] = _stamp(info)
            rt.require(len(files) + len(directories) + len(pending) <= 200000, 'saved inventory limit')
    return files, directories


class VerifiedResume:
    def __init__(self, snapshot_path, snapshot_sha256, report_path, *, live_control=False):
        self.path = Path(snapshot_path)
        raw = self.path.read_bytes()
        rt.require(hashlib.sha256(raw).hexdigest() == snapshot_sha256, 'external resume snapshot hash mismatch')
        self.snapshot = v.strict_json(raw)
        self.snapshot_sha256 = snapshot_sha256
        self.report_path = Path(report_path)
        rt.require(not self.report_path.exists(), 'resume verification report already exists')
        s = self.snapshot
        rt.require(s['format'] == FORMAT and s['formal_permission'] is False, 'resume snapshot format/scope')
        rt.require(type(s['completed_chunks']) is int and 0 < s['completed_chunks'] < 120, 'resume chunk count')
        rt.require(type(s['files']) is dict and 0 < len(s['files']) <= 200000, 'resume file inventory')
        for name, expected in s['files'].items():
            v.safe_relative_path(name)
            rt.require(Path(name).as_posix() == name and '\\' not in name, 'noncanonical snapshot path')
            rt.require(set(expected) == {'bytes', 'sha256'} and type(expected['bytes']) is int and expected['bytes'] >= 0,
                       'invalid saved file size')
            checkpoints._hex(expected['sha256'], 64, 'saved file digest')
        self.root = Path(s['run_root']).absolute()
        self.source = Path(s['source_root']).absolute()
        rt.require(self.root == self.source / 'artifacts/v03-runs' / s['run_name'], 'snapshot run location')
        checkpoints._hex(s['source_revision'], 40, 'snapshot revision')
        checkpoints._hex(s['closed_sha256'], 64, 'snapshot closed hash')
        rt.require(type(s['closed_sequence']) is int and 0 <= s['closed_sequence'] < 4095, 'closed sequence')
        closed_name = f"run/control/{s['closed_sequence']:06d}/closed.json"
        rt.require(s['files'][closed_name]['sha256'] == s['closed_sha256'], 'closed snapshot binding')
        # A pinned, terminal first-attempt resource failure may follow the
        # verified prefix. Preserve it; it never earns an audit-cache entry.
        tail = s.get('failed_tail_records', [])
        rt.require(type(tail) is list and len(tail) in (0, 2), 'invalid failed resume tail')
        for index, row in enumerate(tail):
            rt.require(type(row) is dict and
                       row.get('sequence') == s['completed_chunks'] * 3 + index + 1 and
                       row.get('chunk_index') == s['completed_chunks'] and row.get('attempt') == 1 and
                       row.get('status') == ('running', 'failed')[index] and
                       row.get('reason') == (None, 'resource_limit')[index] and row.get('outcome') is None,
                       'failed resume tail is not a terminal first-attempt resource failure')
            rt.require(f"run/metadata/journal/{row['sequence']:06d}.json" in s['files'],
                       'failed resume tail missing from inventory')
        self.live_control = live_control
        self.controller = None
        self.report = None

    def _verify(self, controller):
        started, s = time.monotonic(), self.snapshot
        rt.require(Path(controller.root) == self.root / 'run/attempts' and
                   Path(controller.metadata_root) == self.root / 'run/metadata', 'controller run differs')
        rt.require(Path(controller.producer_root) == Path(controller.consumer_root) == self.source and
                   controller.verifier_revision == s['source_revision'], 'controller source differs')
        rt.require(not controller.verified_in_session, 'resume must precede any verification cache use')
        tail = s.get('failed_tail_records', [])
        rt.require(len(controller.records) == s['completed_chunks'] * 3 + len(tail), 'resume record count differs')
        rt.require(not tail or controller.records[-len(tail):] == tail, 'failed resume tail differs')
        rt.require(controller.state['next_unverified_chunk'] == s['completed_chunks'], 'resume next chunk differs')
        before_checkpoint = {'receipt': controller.receipt, 'descriptor_pins': controller.descriptor_pins}
        closed_name = f"run/control/{s['closed_sequence']:06d}/closed.json"
        closed_raw = storage.read_regular(self.root / closed_name)
        rt.require(hashlib.sha256(closed_raw).hexdigest() == s['closed_sha256'], 'closed state changed')
        closed = v.strict_json(closed_raw)
        rt.require(closed['checkpoint'] == before_checkpoint, 'closed checkpoint differs')
        rt.require(closed['status'] in ('yielded', 'failed') and closed['formal_permission'] is False, 'closed status not reusable')
        rt.require(not tail or closed['status'] == 'failed', 'failed tail requires failed closed state')
        prefix = [r for r in controller.records if r['status'] in checkpoints.VERIFIED]
        rt.require([r['chunk_index'] for r in prefix] == list(range(s['completed_chunks'])), 'completed prefix differs')
        for row in prefix + tail:
            name = f"run/metadata/journal/{row['sequence']:06d}.json"
            raw = storage.read_regular(self.root / name)
            rt.require(v.strict_json(raw) == row, 'controller record differs from saved journal')
        source = rt.capture_checkout(self.source, s['source_revision'])
        rt.require(resources.probe_runtime(self.source) == s['runtime'], 'cached audit runtime differs')
        before_files, directories = _inventory(self.root)
        extras = set(before_files) - set(s['files'])
        allowed = {f"run/control/{s['closed_sequence'] + 1:06d}/" + name for name in (
            'started.json', 'inspection-pin.json', 'inspection/report.json',
            'inspection/supervision.json', 'inspection/stderr.json')} if self.live_control else set()
        rt.require(extras == allowed and set(s['files']) <= set(before_files), 'saved inventory changed or unexpected invocation')
        with ExitStack() as stack:
            bindings = []
            for directory in directories:
                binding = storage.DirectoryBinding(directory)
                stack.callback(binding.close)
                bindings.append(binding)
            count = sum(hash_regular(self.root / name, expected) for name, expected in s['files'].items())
            after_files, after_directories = _inventory(self.root)
            rt.require(before_files == after_files and set(directories) == set(after_directories), 'saved run changed during verification')
            for binding in bindings:
                binding.check()
        source.recheck()
        rt.require(resources.probe_runtime(self.source) == s['runtime'], 'runtime changed during verification')
        # Write proof before granting the in-memory reuse. Failure leaves cache empty.
        report = {'format': 'anomaly-v03-verified-resume-report-v1', 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'snapshot_sha256': self.snapshot_sha256, 'source_revision': s['source_revision'],
            'closed_sha256': s['closed_sha256'], 'files_verified': len(s['files']), 'bytes_verified': count,
            'completed_chunk_audits_reused': len(prefix), 'elapsed_seconds': time.monotonic() - started,
            'failed_tail_records_preserved': len(tail), 'failed_chunk_audits_reused': 0,
            'hash_read_buffer_bytes': BUFFER_BYTES, 'runtime_unchanged': True, 'source_unchanged': True,
            'scope': 'reuse_previously_audited_unchanged_bytes_single_writer', 'existing_numerical_audits_repeated': False,
            'new_chunk_audits_unchanged': True, 'campaign_evaluations_credited': 0, 'formal_permission': False}
        storage._exclusive(self.report_path, storage.json_bytes(report))
        self.report = report
        controller.verified_in_session.update(checkpoints.record_hash(r) for r in prefix)
        self.controller = controller

    @contextmanager
    def install(self, controller_type):
        """Scope reuse to the fresh controller chosen by Run.run; restore on exit."""
        original = controller_type._revalidate_completed
        rt.require(not getattr(original, '_banto_verified_resume', False), 'verified resume already installed')

        def revalidate(controller):
            if self.controller is None:
                self._verify(controller)
            rt.require(controller is self.controller, 'unexpected controller replacement after resume proof')
            return original(controller)

        revalidate._banto_verified_resume = True
        controller_type._revalidate_completed = revalidate
        try:
            yield self
        finally:
            controller_type._revalidate_completed = original
