"""Bounded caller-held clock/stop/ack metadata; native proof verifier is required."""
from __future__ import annotations

import copy
import math
import os
from pathlib import Path
import secrets
import time

from . import anomaly_v03_preformal_owned_source_git_session as sessions

v, observed, evidence, paths, io = sessions.v, sessions.observed, sessions.evidence, sessions.paths, sessions.io
ROOT = Path(__file__).resolve().parents[2]
FORMAT = 'anomaly-v03-preformal-worker-stop-channel-v2'
MAX_CONTROL = 32 * 1024
MAX_JOBS = 64


def _inside(path, root):
    return path.is_absolute() and path == path.resolve() and path.is_relative_to(root)


def _identity(value):
    v.require(type(value) is dict and set(value) == {'pid','creation_time_100ns','start_token'} and
              type(value['pid']) is int and value['pid'] > 0 and
              type(value['creation_time_100ns']) is int and value['creation_time_100ns'] > 0,
              'channel native creation identity')
    v.require(value['start_token'] == v.canonical_sha256({key:value[key] for key in ('pid','creation_time_100ns')}),
              'channel creation token')
    return value


def _directory_identity(root):
    info = paths.regular_path(root, directory=True).lstat()
    v.require(info.st_ino > 0, 'channel directory identity')
    return [info.st_dev, info.st_ino]


def _read(path, pin=None):
    raw = observed._file(path, MAX_CONTROL)
    if pin is not None:
        evidence._raw(raw, pin, 'channel externally held raw pin')
    value = v.strict_json(raw)
    v.require(io.json_bytes(value) == raw, 'channel canonical frame')
    return value, observed._pin(raw)


def _write(path, value):
    raw = io.json_bytes(value)
    v.require(len(raw) <= MAX_CONTROL, 'channel frame byte bound')
    pin = observed._pin(raw)
    pending = path.with_name(path.name + '.pending')
    paths.regular_path(path, missing=True)
    # A failed staging write/readback remains in the measured root. Readers
    # use only the completed name, never partial bytes or a presence-only ack.
    io._exclusive(pending, raw)
    _read(pending, pin)
    io._rename_no_replace(pending, path)
    _read(path, pin)
    return pin


class _Channel:
    def __init__(self, root, request_pin):
        self.root = Path(root).absolute()
        v.require(_inside(self.root, ROOT / 'artifacts'), 'channel root under artifacts')
        self.request_pin = copy.deepcopy(request_pin)
        request, _ = _read(self.root / 'request.json', request_pin)
        v.require(type(request) is dict and set(request) == {
            'format','role','revision','root','root_identity','budget_root','parent_identity',
            'policy_path','policy_pin','nonce','clock','formal_permission'} and
            request['format'] == FORMAT + '-request' and request['role'] == 'initial-reader' and
            request['root'] == str(self.root) and request['formal_permission'] is False,
            'channel exact request')
        evidence._digest(request['revision'], 40)
        evidence._digest(request['nonce'], 32)
        _identity(request['parent_identity'])
        v.require(type(request['root_identity']) is list and len(request['root_identity']) == 2 and
                  all(type(n) is int and n >= 0 for n in request['root_identity']) and
                  request['root_identity'] == _directory_identity(self.root), 'channel held root identity')
        budget_root = Path(request['budget_root'])
        v.require(_inside(budget_root, ROOT / 'artifacts') and
                  self.root.is_relative_to(budget_root), 'channel measured budget root')
        clock = request['clock']
        v.require(type(clock) is dict and set(clock) == {'started_at','wall_seconds','implementation'} and
                  all(type(clock[key]) in (int,float) and math.isfinite(clock[key]) for key in ('started_at','wall_seconds')) and
                  clock['started_at'] > 0 and 0 < clock['wall_seconds'] <= 1800 and
                  clock['implementation'] == time.get_clock_info('monotonic').implementation,
                  'channel finite shared clock domain')
        self.request = request
        self._policy()

    def _policy(self):
        request = self.request
        policy_path = Path(request['policy_path'])
        v.require(_inside(policy_path, ROOT / 'artifacts') and policy_path.name == 'policy.json' and
                  not policy_path.is_relative_to(self.root),
                  'channel separate held policy')
        policy, _ = _read(policy_path, request['policy_pin'])
        v.require(type(policy) is dict and policy.get('revision') == request['revision'] and
                  policy.get('process_ownership') == sessions.owned_git.JOB_OWNERSHIP,
                  'channel private Job policy revision')
        return policy

    def _live(self):
        request, _ = _read(self.root / 'request.json', self.request_pin)
        v.require(request == self.request and request['root_identity'] == _directory_identity(self.root),
                  'channel request/root changed')
        self._policy()

    def _binding(self):
        path = self.root / 'binding.json'
        paths.regular_path(path, missing=True)
        if not path.exists():
            raise FileNotFoundError(path)
        binding, pin = _read(path)
        v.require(type(binding) is dict and set(binding) == {'format','request_pin','worker_identity'} and
                  binding['format'] == FORMAT + '-binding' and binding['request_pin'] == self.request_pin,
                  'channel original worker binding')
        _identity(binding['worker_identity'])
        return binding, pin

    def _stop(self):
        path = self.root / 'stop.json'
        paths.regular_path(path, missing=True)
        if not path.exists():
            return None
        stop, pin = _read(path)
        v.require(stop == {'format':FORMAT+'-stop','request_pin':self.request_pin,'no_new_jobs':True},
                  'channel latched stop request')
        return pin


class ParentChannel(_Channel):
    @classmethod
    def create(cls, *, root, revision, policy, budget, verify_quiescent):
        v.require(callable(verify_quiescent), 'channel native quiescence verifier required')
        evidence._digest(revision, 40)
        target = Path(root).absolute()
        leaves = getattr(budget, 'roots', {'root':budget.root}).values()
        measured = [Path(leaf) for leaf in leaves if target.is_relative_to(Path(leaf))]
        thread = getattr(budget, '_thread', None)
        v.require(thread is not None and thread.is_alive() and getattr(budget, '_closed', None) is None,
                  'channel live sampler required')
        v.require(len(measured) == 1 and _inside(target, ROOT / 'artifacts') and
                  budget.probe() is None, 'channel live measured budget')
        v.require(type(policy) is dict and set(policy) == {'path','expected_pin'}, 'channel policy entry')
        paths.regular_path(target.parent, directory=True)
        paths.regular_path(target, directory=True, missing=True)
        v.require(not target.exists(), 'channel exclusive new root')
        clock = {'started_at':budget.started_at,'wall_seconds':budget.limits['wall_seconds'],
                 'implementation':time.get_clock_info('monotonic').implementation}
        v.require(type(clock['started_at']) in (int,float) and math.isfinite(clock['started_at']) and
                  0 < clock['started_at'] <= time.monotonic(), 'channel already started clock')
        v.require(type(clock['wall_seconds']) in (int,float) and math.isfinite(clock['wall_seconds']) and
                  0 < clock['wall_seconds'] <= 1800, 'channel existing clock bound')
        target.mkdir()
        request = {'format':FORMAT+'-request','role':'initial-reader','revision':revision,
            'root':str(target),'root_identity':_directory_identity(target),'budget_root':str(measured[0]),
            'parent_identity':observed.creation_observation(os.getpid()),
            'policy_path':policy['path'],'policy_pin':policy['expected_pin'],'nonce':secrets.token_hex(16),
            'clock':clock,'formal_permission':False}
        pin = _write(target / 'request.json', request)
        result = cls(target, pin)
        result.verify_quiescent = verify_quiescent
        result.worker = result.binding_pin = result.binding_error = None
        return result

    def bind(self, process):
        v.require(self.worker is None, 'channel bind original worker once')
        # Retain the original owner before the first fallible observation.
        self.worker = process
        try:
            self._live()
            identity = observed.creation_observation(process.pid, process._handle)
            _identity(identity)
            value = {'format':FORMAT+'-binding','request_pin':self.request_pin,'worker_identity':identity}
            self.binding_pin = observed._pin(io.json_bytes(value))
            _write(self.root / 'binding.json', value)
        except BaseException as failure:
            self.binding_error = failure
            raise

    def fence(self, process):
        v.require(process is self.worker, 'channel original Popen owner')
        self._live()
        # Also stop an unbound child after a failed binding publication.
        if self._stop() is None:
            _write(self.root / 'stop.json', {'format':FORMAT+'-stop','request_pin':self.request_pin,'no_new_jobs':True})
        if self.binding_pin is None:
            return False
        try:
            binding, pin = self._binding()
        except FileNotFoundError:
            return False
        v.require(pin == self.binding_pin and binding['worker_identity'] ==
                  observed.creation_observation(process.pid, process._handle), 'channel original creation/held binding')
        ack_path = self.root / 'ack.json'
        paths.regular_path(ack_path, missing=True)
        if not ack_path.exists():
            return False
        ack, ack_pin = _read(ack_path)
        v.require(type(ack) is dict and set(ack) == {
            'format','request_pin','binding_pin','worker_identity','no_new_jobs','jobs_finished','proof'} and
            ack['format'] == FORMAT+'-ack' and ack['request_pin'] == self.request_pin and
            ack['binding_pin'] == self.binding_pin and ack['worker_identity'] == binding['worker_identity'] and
            ack['no_new_jobs'] is True and type(ack['jobs_finished']) is int and
            0 <= ack['jobs_finished'] <= MAX_JOBS, 'channel bound quiescent ack')
        proof = ack['proof']
        v.require(type(proof) is dict and set(proof) == {'path','pin'}, 'channel external proof entry')
        path = Path(proof['path'])
        v.require(_inside(path, self.root), 'channel proof inside measured root')
        raw = observed._file(path, MAX_CONTROL)
        evidence._raw(raw, proof['pin'], 'channel retained native proof pin')
        result = self.verify_quiescent(raw, ack['jobs_finished'])
        v.require(type(result) is bool, 'channel explicit native proof verdict')
        if result:
            self._live()
            _read(ack_path, ack_pin)
            _, final_binding_pin = self._binding()
            v.require(final_binding_pin == self.binding_pin, 'channel binding changed during proof verification')
            evidence._raw(observed._file(path, MAX_CONTROL), proof['pin'], 'channel proof changed during verification')
        return result


class ChildChannel(_Channel):
    def __init__(self, root, request_pin):
        super().__init__(root, request_pin)
        self.identity = _identity(observed.creation_observation(os.getpid()))
        self.stopped, self.finished = False, 0
        self.active, self.owners, self.error = set(), {}, None

    def _own_binding(self):
        binding, pin = self._binding()
        v.require(binding['worker_identity'] == self.identity, 'channel child creation identity')
        return pin

    def probe(self):
        try:
            self._live()
            clock = self.request['clock']; now = time.monotonic()
            v.require(now >= clock['started_at'], 'channel clock moved backwards')
            # A stop write that failed before atomic publication still denies
            # new Jobs. This hint never authorizes a parent ack or cleanup.
            pending_stop = self.root / 'stop.json.pending'
            paths.regular_path(pending_stop, missing=True)
            if pending_stop.exists():
                self.stopped = True
            if self._stop() is not None or now - clock['started_at'] >= clock['wall_seconds']:
                self.stopped = True
            try:
                self._own_binding()
            except FileNotFoundError:
                return 'source_channel_stopped' if self.stopped else 'source_channel_binding_pending'
            return 'source_channel_stopped' if self.stopped else None
        except BaseException as failure:
            self.stopped = True
            if self.error is None:
                self.error = failure
            return 'source_channel_invalid'

    def wait_for_binding(self):
        """Wait inside the existing clock; interruption permanently stops work."""
        while True:
            reason = self.probe()
            if reason != 'source_channel_binding_pending':
                return reason
            try:
                remaining = self.request['clock']['wall_seconds'] - (
                    time.monotonic() - self.request['clock']['started_at'])
                if remaining <= 0:
                    self.stopped = True
                    return 'source_channel_stopped'
                time.sleep(min(0.25, remaining))
            except BaseException as failure:
                self.stopped = True
                if self.error is None:
                    self.error = failure
                return 'source_channel_invalid'

    def begin_job(self):
        v.require(self.probe() is None and self.finished + len(self.active) < MAX_JOBS,
                  'channel no new Job after stop/invalid/binding wait')
        lease = self.finished + len(self.active)
        v.require(lease not in self.active, 'channel unique Job lease')
        self.active.add(lease)
        return lease

    def hold_owner(self, lease, original):
        v.require(lease in self.active and lease not in self.owners and isinstance(original, BaseException),
                  'channel original active owner')
        self.owners[lease] = original

    def finish_job(self, lease, *, exit_confirmed, handles_closed, raw_preserved):
        v.require(lease in self.active and exit_confirmed is True and handles_closed is True and raw_preserved is True,
                  'channel confirmed Job exit/close/raw required')
        self.active.remove(lease)
        self.owners.pop(lease, None)
        self.finished += 1

    def acknowledge(self, proof):
        self.stopped = True  # Even a failed ack publication cannot rearm work.
        self._live()
        binding_pin = self._own_binding()
        v.require(not self.active and not self.owners, 'channel no ack while original Job owner active')
        v.require(type(proof) is dict and set(proof) == {'path','pin'}, 'channel quiescence proof entry')
        path = Path(proof['path'])
        v.require(_inside(path, self.root), 'channel proof in measured root')
        evidence._raw(observed._file(path, MAX_CONTROL), proof['pin'], 'channel preserved native evidence')
        return _write(self.root / 'ack.json', {'format':FORMAT+'-ack','request_pin':self.request_pin,
            'binding_pin':binding_pin,'worker_identity':self.identity,'no_new_jobs':True,
            'jobs_finished':self.finished,'proof':copy.deepcopy(proof)})
