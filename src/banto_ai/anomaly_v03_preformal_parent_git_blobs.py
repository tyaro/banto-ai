"""Opt-in parent blob Jobs, phase cache and inflight retention in the outer root.

No worker Git or loaded dependency closure is asserted by this adapter.
"""
from __future__ import annotations

import copy
from collections import Counter
from pathlib import Path

from . import anomaly_v03_preformal_git_receipt_archive as archive
from . import anomaly_v03_preformal_owned_source_git_session as sessions

v, observed, evidence, owned, paths, io = (
    archive.v, archive.observed, archive.evidence, archive.owned, archive.paths, archive.io)
ROOT = Path(__file__).resolve().parents[2]
FORMAT = 'anomaly-v03-preformal-parent-git-blob-index-v1'
MAX_INDEX = 64 * 1024
SOURCE_FILES = tuple('src/banto_ai/' + name + '.py' for name in (
    'anomaly_v03_preformal_parent_git_blobs', 'anomaly_v03_preformal_git_receipt_archive'))


def _calls(source_paths, source_pins, phases):
    return [{'call_id': 'blob-' + phase + '-' + str(index).zfill(3),
             'phase': phase, 'source_path': name, 'expected_output_pin': pin}
            for phase in phases for index, (name, pin) in enumerate(zip(source_paths, source_pins))]


def verify_index(path, expected_pin, *, entry, checkout_root, expected_requests, phases):
    """Check an externally pinned index and its archive prefix without Git."""
    v.require(phases in (('preflight',), ('preflight', 'postflight')), 'parent blob index phases')
    path = Path(path)
    v.require(path.is_absolute() and path.is_relative_to(ROOT / 'artifacts') and
              path.name == 'git-blobs-' + phases[-1] + '.json', 'parent blob index measured path')
    raw = observed._file(Path(path), MAX_INDEX)
    evidence._raw(raw, expected_pin, 'parent blob index raw pin')
    value = v.strict_json(raw)
    source_paths = list(dict.fromkeys(expected_requests))
    counts = Counter(expected_requests)
    v.require(type(value) is dict and set(value) == {
        'format', 'root', 'revision', 'policy_path', 'policy_pin', 'phases', 'source_paths',
        'source_pins', 'request_counts', 'archive_pin', 'rows', 'formal_permission'} and
        value['format'] == FORMAT and value['root'] == str(path.parent) and
        value['revision'] == entry['revision'] and
        value['policy_path'] == entry['path'] and value['policy_pin'] == entry['expected_pin'] and
        value['phases'] == list(phases) and value['source_paths'] == source_paths and
        value['request_counts'] == [counts[name] for name in source_paths] and
        all(type(count) is int and count > 0 for count in value['request_counts']) and
        type(value['source_pins']) is list and len(value['source_pins']) == len(source_paths) and
        value['formal_permission'] is False, 'parent blob index exact source inventory')
    policy = sessions._policy(Path(entry['path']), entry['expected_pin'], entry['revision'],
                              Path(path).parent / 'git-blob-inflight', check_current=False)
    v.require(policy == entry['policy'], 'parent blob index held policy')
    blob = observed._file(Path(path).parent / 'git-blobs.bin', archive.MAX_BYTES)
    evidence._pin(value['archive_pin'])
    size = value['archive_pin']['bytes']
    v.require(0 < size <= len(blob), 'parent blob index archive prefix length')
    prefix = blob[:size]
    evidence._raw(prefix, value['archive_pin'], 'parent blob index archive prefix pin')
    if phases == ('preflight', 'postflight'):
        v.require(size == len(blob), 'parent blob final archive has trailing bytes')
    calls = _calls(source_paths, value['source_pins'], phases)
    outputs = archive._read(prefix, value['rows'], calls, root=checkout_root, policy=policy)
    return {'status': 'verified_retained', 'call_count': len(calls),
            'unique_stdout_records': sum(item[1] is None for item in outputs),
            'source_pins': dict(zip(source_paths, value['source_pins'])), 'formal_permission': False}


class ParentBlobActor:
    def __init__(self, entry, *, root, checkout_root, budget, expected_requests):
        self.root = Path(root)
        self.inflight = self.root / 'git-blob-inflight'
        v.require(self.root.is_absolute() and self.root.is_relative_to(ROOT / 'artifacts'),
                  'parent blob actor measured root')
        paths.regular_path(self.root, directory=True)
        paths.regular_path(self.inflight, directory=True, missing=True)
        v.require(not self.inflight.exists() and type(expected_requests) in (tuple, list) and
                  0 < len(expected_requests) <= archive.MAX_CALLS, 'parent blob actor new bounded inventory')
        self.entry = copy.deepcopy(entry)
        self.checkout_root, self.budget = checkout_root, budget
        self.expected_requests = tuple(expected_requests)
        self.source_paths = tuple(dict.fromkeys(expected_requests))
        v.require(2 * len(self.source_paths) <= archive.MAX_CALLS, 'parent blob actor call count')
        for name in self.source_paths:
            owned._command(entry['policy'], 'source_blob', name, observed._pin(b''))
        v.require(entry['policy'].get('process_ownership') == owned.JOB_OWNERSHIP,
                  'parent blob actor private Job policy')
        self._policy()
        budget.checkpoint('preflight')
        self.archive = archive.ReceiptArchive(self.root / 'git-blobs.bin',
                                            root=checkout_root, policy=entry['policy'])
        self.phase, self.failed = 'preflight', False
        self.requests = {'preflight': Counter(), 'postflight': Counter()}
        self.source_pins, self.indices = {}, {}
        self.pending = self.inflight_receipt_pin = None

    def _policy(self):
        policy = sessions._policy(Path(self.entry['path']), self.entry['expected_pin'],
                                  self.entry['revision'], self.inflight)
        v.require(policy == self.entry['policy'], 'parent blob actor held policy')

    def reader(self, phase):
        try:
            v.require(not self.failed and (phase == self.phase or
                      phase == 'postflight' and self.phase == 'preflight' and 'preflight' in self.indices),
                      'parent blob actor ordered verified phases')
            self.phase = phase
            return self.read
        except BaseException:
            self.failed = True
            raise

    def read(self, *, revision, source_path, expected_output_pin):
        try:
            v.require(not self.failed and revision == self.entry['revision'] and
                      source_path in self.source_paths, 'parent blob actor expected source/revision')
            evidence._pin(expected_output_pin)
            checkpoint = lambda: self.budget.checkpoint(self.phase)
            checkpoint(); self._policy()
            if source_path in self.source_pins:
                v.require(self.source_pins[source_path] == expected_output_pin,
                          'parent blob actor source pin changed')
            count = self.requests[self.phase][source_path]
            v.require(count < self.expected_requests.count(source_path), 'parent blob actor extra read')
            output = self.archive.lookup(revision=revision, phase=self.phase, source_path=source_path,
                expected_output_pin=expected_output_pin, checkpoint=checkpoint)
            self.requests[self.phase][source_path] += 1
            if output is not None:
                return output
            call = {'call_id': 'blob-' + self.phase + '-' + str(self.source_paths.index(source_path)).zfill(3),
                    'phase': self.phase, 'source_path': source_path,
                    'expected_output_pin': copy.deepcopy(expected_output_pin)}
            self.pending = copy.deepcopy(call)
            self.inflight_receipt_pin = None
            checked = owned.run_owned(root=self.checkout_root, policy=self.entry['policy'],
                operation='source_blob', source_path=source_path, expected_output_pin=expected_output_pin,
                receipt_root=self.inflight, timeout_seconds=10, stop_probe=self.budget.probe)
            self.inflight_receipt_pin = copy.deepcopy(checked['receipt_pin'])
            checkpoint()
            receipt_raw = observed._file(self.inflight / 'receipt.json', owned.MAX_RECEIPT)
            evidence._raw(receipt_raw, checked['receipt_pin'], 'parent blob direct receipt pin')
            receipt = v.strict_json(receipt_raw)
            stdout = observed._file(self.inflight / 'stdout.bin', archive.MAX_STDOUT)
            stderr = observed._file(self.inflight / 'stderr.bin', owned.MAX_STDERR)
            v.require(checked['receipt_root'] == str(self.inflight) and checked['receipt'] == receipt and
                      type(checked['stdout']) is bytes and checked['stdout'] == stdout,
                      'parent blob returned/saved receipt binding')
            self.archive.append(call=call, receipt_raw=receipt_raw, expected_receipt_pin=checked['receipt_pin'],
                                stdout_raw=stdout, stderr_raw=stderr, checkpoint=checkpoint)
            self.source_pins[source_path] = copy.deepcopy(expected_output_pin)
            self._clear_inflight({'receipt.json': checked['receipt_pin'],
                                  'stdout.bin': observed._pin(stdout), 'stderr.bin': observed._pin(stderr)})
            checkpoint()
            self.pending = self.inflight_receipt_pin = None
            return stdout
        except BaseException:
            self.failed = True
            raise  # Includes the original UnreapedJob/UnclosedHandles owner.

    def _clear_inflight(self, pins):
        # Only three newly created files, after archive readback. Never recurse.
        resolved = self.inflight.resolve()
        v.require(resolved == self.inflight and resolved.is_relative_to(ROOT / 'artifacts') and
                  resolved.is_relative_to(self.root), 'parent blob cleanup fixed measured path')
        paths.regular_path(resolved, directory=True)
        v.require({p.name for p in resolved.iterdir()} == set(pins), 'parent blob inflight exact files')
        for name, pin in pins.items():
            evidence._raw(observed._file(resolved / name, max(pin['bytes'], 1)), pin,
                          'parent blob cleanup archived raw pin')
        for name in pins:
            paths.regular_path(resolved / name).unlink()
        resolved.rmdir()

    def verify(self, phases):
        try:
            v.require(not self.failed and phases in (('preflight',), ('preflight', 'postflight')) and
                      self.pending is None and self.phase == phases[-1] and not self.inflight.exists(),
                      'parent blob actor verified terminal phase')
            expected = Counter(self.expected_requests)
            v.require(all(self.requests[phase] == expected for phase in phases) and
                      set(self.source_pins) == set(self.source_paths), 'parent blob actor exact read inventory')
            self.budget.checkpoint(self.phase); self._policy()
            saved = self.archive.snapshot()
            pins = [self.source_pins[name] for name in self.source_paths]
            v.require(saved['calls'] == _calls(self.source_paths, pins, phases),
                      'parent blob actor exact native call inventory')
            value = {'format': FORMAT, 'root': str(self.root), 'revision': self.entry['revision'],
                     'policy_path': self.entry['path'], 'policy_pin': self.entry['expected_pin'],
                     'phases': list(phases), 'source_paths': list(self.source_paths),
                     'source_pins': pins, 'request_counts': [expected[name] for name in self.source_paths],
                     'archive_pin': saved['pin'], 'rows': saved['rows'], 'formal_permission': False}
            raw = io.json_bytes(value)
            v.require(len(raw) <= MAX_INDEX, 'parent blob actor index byte limit')
            path = self.root / ('git-blobs-' + self.phase + '.json')
            io._exclusive(path, raw)
            pin = observed._pin(raw)
            checked = verify_index(path, pin, entry=self.entry, checkout_root=self.checkout_root,
                                   expected_requests=self.expected_requests, phases=phases)
            self.indices[self.phase] = {'path': str(path), 'pin': pin,
                                       'archive_pin': saved['pin'], 'call_count': checked['call_count']}
            self.budget.checkpoint(self.phase)
            return checked
        except BaseException:
            self.failed = True
            raise

    def state(self):
        return {'failed': self.failed, 'phase': self.phase, 'archive_path': str(self.archive.path),
                'source_count': len(self.source_paths), 'receipt_count': len(self.archive.rows),
                'request_counts': {phase: sum(counts.values()) for phase, counts in self.requests.items()},
                'indices': copy.deepcopy(self.indices), 'inflight_path': str(self.inflight),
                'pending_call': copy.deepcopy(self.pending),
                'inflight_receipt_pin': copy.deepcopy(self.inflight_receipt_pin),
                'formal_permission': False, 'git_loaded_code_authenticated': False}
