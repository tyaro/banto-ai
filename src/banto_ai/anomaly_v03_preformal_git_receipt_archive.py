"""Bounded append-only blob receipts; this module does not start Git processes.

Only verified private Job calls can be archived. Equal stdout bytes share a
prior record; every call keeps its own receipt. Failed writes stay poisoned
and retained. Production budget/worker wiring is a separate boundary.
"""
from __future__ import annotations

import base64
import copy
import gzip
import os
from pathlib import Path
import re
import zlib

from . import anomaly_v03_preformal_owned_git as owned

v, observed, evidence, paths, io = owned.v, owned.observed, owned.evidence, owned.paths, owned.io
ROOT = Path(__file__).resolve().parents[2]
FORMAT = 'anomaly-v03-preformal-git-blob-archive-record-v1'
MAX_BYTES = 512 * 1024
MAX_RECORD = 128 * 1024
MAX_RAW = 1536 * 1024
MAX_STDOUT = 1024**2
MAX_CALLS = 512
MAGIC = b'BGR1'
_NAME = re.compile(r'[a-z][a-z0-9-]{0,63}\Z')


def _call(call):
    v.require(type(call) is dict and set(call) == {
        'call_id', 'phase', 'source_path', 'expected_output_pin'}, 'blob archive call fields')
    v.require(type(call['call_id']) is str and _NAME.fullmatch(call['call_id']) is not None and
              call['phase'] in ('preflight', 'postflight'), 'blob archive call identity')
    owned._command({'revision': '0' * 40}, 'source_blob', call['source_path'], call['expected_output_pin'])
    v.require(call['expected_output_pin']['bytes'] <= MAX_STDOUT, 'blob archive source size')


def _decode(value, maximum):
    v.require(type(value) is str and len(value) <= 4 * ((maximum + 2) // 3),
              'blob archive encoded byte limit')
    raw = base64.b64decode(value, validate=True)
    v.require(len(raw) <= maximum, 'blob archive decoded byte limit')
    return raw


def _gunzip(compressed, maximum):
    decoder = zlib.decompressobj(31)
    raw = decoder.decompress(compressed, maximum + 1)
    v.require(len(raw) <= maximum and decoder.eof and not decoder.unused_data and
              not decoder.unconsumed_tail, 'blob archive bounded single gzip member')
    return raw


def _inflate(frame):
    v.require(frame[:4] == MAGIC and 8 <= len(frame) <= MAX_RECORD + 8 and
              int.from_bytes(frame[4:8], 'big') == len(frame) - 8,
              'blob archive frame length')
    raw = _gunzip(frame[8:], MAX_RAW)
    value = v.strict_json(raw)
    v.require(io.json_bytes(value) == raw, 'blob archive canonical record')
    return value


def _record(value, index, call, outputs, *, root, policy):
    v.require(type(value) is dict and set(value) == {
        'format', 'index', 'call_id', 'phase', 'receipt_gzip', 'receipt_pin',
        'stdout_gzip', 'stdout_ref', 'stderr_raw'} and value['format'] == FORMAT and
        type(value['index']) is int and value['index'] == index and
        value['call_id'] == call['call_id'] and value['phase'] == call['phase'],
        'blob archive ordered call binding')
    receipt_raw = _gunzip(_decode(value['receipt_gzip'], MAX_RAW), owned.MAX_RECEIPT)
    receipt = v.strict_json(receipt_raw)
    v.require(receipt['format'] == owned.JOB_FORMAT and receipt['status'] == 'verified' and
              receipt['operation'] == 'source_blob' and receipt['source_path'] == call['source_path'] and
              receipt['expected_output_pin'] == call['expected_output_pin'],
              'blob archive successful private Job source binding')
    reference = value['stdout_ref']
    if reference is None:
        stdout = _gunzip(_decode(value['stdout_gzip'], MAX_RAW), MAX_STDOUT)
    else:
        v.require(type(reference) is int and 0 <= reference < index and
                  value['stdout_gzip'] is None and outputs[reference][1] is None,
                  'blob archive prior direct stdout reference')
        stdout = outputs[reference][0]
    stderr = _decode(value['stderr_raw'], owned.MAX_STDERR)
    owned.verify_raw(receipt_raw, value['receipt_pin'], stdout_raw=stdout, stderr_raw=stderr,
                     root=root, policy=policy)
    identity = v.canonical_sha256(receipt['process_identity'])
    v.require(all(item[2] != identity for item in outputs), 'blob archive original process identity reused')
    return stdout, reference, identity


def _read(raw, rows, calls, *, root, policy):
    v.require(type(rows) is list and type(calls) is list and
              0 < len(rows) == len(calls) <= MAX_CALLS, 'blob archive exact call inventory')
    outputs, offset, ids, postflight = [], 0, set(), False
    for index, (row, call) in enumerate(zip(rows, calls)):
        _call(call)
        v.require(call['call_id'] not in ids and not (postflight and call['phase'] == 'preflight'),
                  'blob archive unique ordered phases')
        ids.add(call['call_id']); postflight |= call['phase'] == 'postflight'
        v.require(type(row) is dict and set(row) == {'offset', 'bytes', 'sha256'} and
                  type(row['offset']) is int and row['offset'] == offset and
                  type(row['bytes']) is int and 8 < row['bytes'] <= MAX_RECORD + 8 and
                  offset + row['bytes'] <= len(raw), 'blob archive exact frame coverage')
        frame = raw[offset:offset + row['bytes']]
        evidence._raw(frame, {'bytes': row['bytes'], 'sha256': row['sha256']}, 'blob archive frame pin')
        outputs.append(_record(_inflate(frame), index, call, outputs, root=root, policy=policy))
        offset += row['bytes']
    v.require(offset == len(raw), 'blob archive trailing bytes or missing records')
    return outputs


def verify(path, expected_pin, *, rows, calls, root, policy):
    """Reconstruct raw and apply the same retained checks without launching Git."""
    raw = observed._file(Path(path), MAX_BYTES)
    evidence._raw(raw, expected_pin, 'blob archive file pin')
    outputs = _read(raw, rows, calls, root=root, policy=policy)
    return {'status': 'verified_retained', 'call_count': len(rows),
            'unique_stdout_records': sum(item[1] is None for item in outputs),
            'formal_permission': False, 'execution_authenticated': False,
            'git_loaded_code_authenticated': False, 'source_closure_complete': False}


class ReceiptArchive:
    """Exclusive file creation and monotonic append, with caller-held raw pins."""

    def __init__(self, path, *, root, policy):
        self.path = Path(path)
        v.require(self.path.is_absolute() and self.path.is_relative_to(ROOT / 'artifacts') and
                  self.path.name == 'git-blobs.bin', 'blob archive measured artifact path')
        paths.regular_path(self.path.parent, directory=True)
        paths.regular_path(self.path, missing=True)
        v.require(not self.path.exists() and policy.get('process_ownership') == owned.JOB_OWNERSHIP,
                  'blob archive exclusive private Job policy')
        owned._policy(root, policy)
        self.root, self.policy = root, copy.deepcopy(policy)
        self.rows, self.calls, self._outputs = [], [], []
        self._raw, self._failed = b'', False
        io._exclusive(self.path, b'')

    def lookup(self, *, revision, phase, source_path, expected_output_pin, checkpoint=None):
        """Reuse equal source bytes within a phase, with no new process claim."""
        try:
            v.require(not self._failed and revision == self.policy['revision'],
                      'blob archive active expected revision')
            call = {'call_id': 'cache-lookup', 'phase': phase, 'source_path': source_path,
                    'expected_output_pin': expected_output_pin}
            _call(call)
            v.require(not (self.calls and self.calls[-1]['phase'] == 'postflight' and
                           phase == 'preflight'), 'blob archive cache phase moved backwards')
            v.require(checkpoint is None or callable(checkpoint), 'blob archive checkpoint')
            if checkpoint is not None:
                checkpoint()
            owned._policy(self.root, self.policy)
            v.require(observed._file(self.path, MAX_BYTES) == self._raw, 'blob archive held file changed')
            output = None
            for index, prior in enumerate(self.calls):
                if prior['phase'] == phase and prior['source_path'] == source_path:
                    v.require(prior['expected_output_pin'] == expected_output_pin,
                              'blob archive phase source pin changed')
                    output = self._outputs[index][0]
                    evidence._raw(output, expected_output_pin, 'blob archive cached source pin')
                    break
            if checkpoint is not None:
                checkpoint()
            return output
        except BaseException:
            self._failed = True
            raise

    def append(self, *, call, receipt_raw, expected_receipt_pin, stdout_raw, stderr_raw,
               checkpoint=None):
        """A failed append retains disk bytes and forbids all later appends."""
        try:
            v.require(not self._failed and len(self.rows) < MAX_CALLS,
                      'blob archive active bounded writer')
            _call(call)
            v.require(checkpoint is None or callable(checkpoint), 'blob archive checkpoint')
            if checkpoint is not None:
                checkpoint()
            v.require(type(stdout_raw) is bytes and len(stdout_raw) <= MAX_STDOUT and
                      type(stderr_raw) is bytes and len(stderr_raw) <= owned.MAX_STDERR and
                      type(receipt_raw) is bytes and len(receipt_raw) <= owned.MAX_RECEIPT,
                      'blob archive bounded raw inputs')
            v.require(all(c['call_id'] != call['call_id'] for c in self.calls) and
                      not (self.calls and self.calls[-1]['phase'] == 'postflight' and
                           call['phase'] == 'preflight'), 'blob archive unique ordered phases')
            reference = next((i for i, (raw, ref, _) in enumerate(self._outputs)
                              if ref is None and raw == stdout_raw), None)
            value = {'format': FORMAT, 'index': len(self.rows), 'call_id': call['call_id'],
                     'phase': call['phase'],
                     'receipt_gzip': base64.b64encode(gzip.compress(receipt_raw, mtime=0)).decode('ascii'),
                     'receipt_pin': copy.deepcopy(expected_receipt_pin),
                     'stdout_gzip': base64.b64encode(gzip.compress(stdout_raw, mtime=0)).decode('ascii')
                                    if reference is None else None,
                     'stdout_ref': reference, 'stderr_raw': base64.b64encode(stderr_raw).decode('ascii')}
            output = _record(value, len(self.rows), call, self._outputs, root=self.root, policy=self.policy)
            raw = io.json_bytes(value)
            v.require(len(raw) <= MAX_RAW, 'blob archive raw record size')
            compressed = gzip.compress(raw, mtime=0)
            v.require(0 < len(compressed) <= MAX_RECORD, 'blob archive compressed record size')
            frame = MAGIC + len(compressed).to_bytes(4, 'big') + compressed
            v.require(len(self._raw) + len(frame) <= MAX_BYTES, 'blob archive file byte limit')
            held = observed._file(self.path, MAX_BYTES)
            v.require(held == self._raw, 'blob archive held file changed')
            with self.path.open('ab') as stream:
                v.require(stream.write(frame) == len(frame), 'blob archive complete append')
                stream.flush(); os.fsync(stream.fileno())
            # Record the external frame pin before readback or stop can fail.
            row = {'offset': len(self._raw), **observed._pin(frame)}
            self.rows.append(row); self.calls.append(copy.deepcopy(call)); self._outputs.append(output)
            self._raw += frame
            v.require(observed._file(self.path, MAX_BYTES) == self._raw, 'blob archive saved append readback')
            _record(_inflate(frame), len(self.rows) - 1, call, self._outputs[:-1],
                    root=self.root, policy=self.policy)
            if checkpoint is not None:
                checkpoint()
            return copy.deepcopy(row)
        except BaseException:
            self._failed = True
            raise

    def snapshot(self):
        try:
            v.require(not self._failed, 'blob archive failed writer cannot finish')
            pin = observed._pin(self._raw)
            result = verify(self.path, pin, rows=self.rows, calls=self.calls, root=self.root, policy=self.policy)
            return {**result, 'path': str(self.path), 'pin': pin,
                    'rows': copy.deepcopy(self.rows), 'calls': copy.deepcopy(self.calls)}
        except BaseException:
            self._failed = True
            raise
