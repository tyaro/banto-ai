"""Retain explicit owned Git source calls for opt-in five-role entries.

The session can supply selected source bytes to the five-role parent.  It
attests only direct Git handles and saved bytes.  Git's loaded code and
descendants, inner Job Git, other processes, and complete source/runtime
closure remain out of scope.
"""
from __future__ import annotations

import copy
from pathlib import Path
import re

from . import anomaly_v03 as v
from . import anomaly_v03_consumer_evidence as evidence
from . import anomaly_v03_preformal_owned_git as owned_git
from . import anomaly_v03_reader_evidence as observed
from . import _anomaly_v03_io as io
from . import _anomaly_v03_runtime as paths


ROOT = Path(__file__).resolve().parents[2]
FORMAT = 'anomaly-v03-preformal-owned-source-git-session-v1'
MAX_POLICY = 8 * 1024
MAX_MANIFEST = 256 * 1024
MAX_CALLS = 512
_NAME = re.compile(r'[a-z][a-z0-9-]{0,63}\Z')


def _name(value, label):
    v.require(type(value) is str and _NAME.fullmatch(value) is not None and
              value not in ('manifest', 'policy'), label)
    return value


def _policy(path, pin, revision, receipt_root, *, check_current=True):
    path = Path(path)
    evidence._pin(pin)
    v.require(path.is_absolute() and path.name == 'policy.json' and
              path.is_relative_to(ROOT / 'artifacts') and
              not path.is_relative_to(receipt_root) and
              not receipt_root.is_relative_to(path.parent),
              'separate externally pinned owned Git policy')
    raw = observed._file(path, MAX_POLICY)
    evidence._raw(raw, pin, 'owned source Git policy raw pin')
    policy = v.strict_json(raw)
    v.require(type(policy) is dict and policy.get('revision') == revision,
              'owned source Git policy revision')
    owned_git._policy(ROOT, policy, check_current=check_current)
    return policy


def _root(path):
    path = Path(path)
    v.require(path.is_absolute() and path.is_relative_to(ROOT / 'artifacts') and
              path.name not in ('', '.', '..'),
              'owned source Git receipt root under artifacts')
    paths.regular_path(path.parent, directory=True)
    paths.regular_path(path, directory=True, missing=True)
    return path


class OwnedSourceGitSession:
    """Run a sequence of explicit source Git calls and save one pinned index."""

    def __init__(self, *, policy_path, expected_policy_pin, revision,
                 receipt_root, phase):
        evidence._digest(revision, 40)
        self.phase = _name(phase, 'owned source Git phase')
        self.root = _root(receipt_root)
        v.require(not self.root.exists(), 'owned source Git root reused')
        self.policy_path = Path(policy_path)
        self.policy_pin = copy.deepcopy(expected_policy_pin)
        self.policy = _policy(self.policy_path, self.policy_pin, revision,
                              self.root)
        self.revision = revision
        self.root.mkdir()  # Exclusive root; neither calls nor manifest overwrite.
        self.calls = []
        self._ids = set()
        self._entered = False
        self._finished = False
        self._failed = False
        self._unreaped = None
        self.manifest_result = None

    def __enter__(self):
        v.require(not self._entered and not self._finished,
                  'owned source Git session entered once')
        self._entered = True
        return self

    def run(self, *, call_id, operation, source_path=None,
            expected_output_pin=None):
        """Return verified raw stdout; a failed call aborts the session."""
        try:
            v.require(self._entered and not self._finished and not self._failed,
                      'owned source Git session active')
            call_id = _name(call_id, 'owned source Git call id')
            v.require(call_id not in self._ids and len(self.calls) < MAX_CALLS,
                      'owned source Git unique bounded call id')
            owned_git._command(self.policy, operation, source_path,
                               expected_output_pin)
        except BaseException:
            # A caller may catch a rejected attempted call inside `with`.
            # Its earlier successful calls must not then finalize as verified.
            if self._entered and not self._finished:
                self._failed = True
            raise
        self._ids.add(call_id)
        row = {'index': len(self.calls), 'call_id': call_id,
               'operation': operation, 'source_path': source_path,
               'expected_output_pin': copy.deepcopy(expected_output_pin),
               'receipt_pin': None, 'call_status': None, 'reason': None,
               'error_type': None}
        self.calls.append(row)
        try:
            checked = owned_git.run_owned(
                root=ROOT, policy=self.policy, operation=operation,
                receipt_root=self.root / call_id,
                source_path=source_path,
                expected_output_pin=expected_output_pin)
            receipt = checked['receipt']
            row['receipt_pin'] = copy.deepcopy(checked['receipt_pin'])
            row['call_status'] = receipt['status']
            row['reason'] = receipt['reason']
            v.require(checked['receipt_root'] == str(self.root / call_id) and
                      receipt['operation'] == operation and
                      receipt['source_path'] == source_path and
                      receipt['expected_output_pin'] == expected_output_pin and
                      receipt['revision'] == self.revision and
                      receipt['formal_permission'] is False and
                      receipt['source_closure_complete'] is False and
                      receipt['runtime_closure_complete'] is False and
                      receipt['execution_authenticated'] is False,
                      'owned source Git direct receipt binding')
            v.require(receipt['status'] == 'verified',
                      'owned source Git call rejected: ' + str(receipt['reason']))
            output = checked['stdout']
            v.require(type(output) is bytes and
                      observed._pin(output) == receipt['stdout_pin'],
                      'owned source Git output binding')
            return output
        except BaseException as error:
            self._failed = True
            if isinstance(error, owned_git.UnreapedGit) and \
                    self._unreaped is None:
                self._unreaped = error
            row['error_type'] = type(error).__name__
            if row['receipt_pin'] is not None and \
                    row['call_status'] == 'verified':
                # A direct call may be valid while this adapter's returned
                # value/binding is not.  Keep that distinct from receipt.reason.
                row['reason'] = 'adapter_binding_failed'
            elif row['reason'] is None:
                row['reason'] = 'call_exception'
            raise

    def _finish(self, error):
        v.require(self._entered and not self._finished,
                  'owned source Git session finalized once')
        self._finished = True
        failed = error is not None or self._failed or not self.calls
        manifest = {'format': FORMAT, 'status': 'failed' if failed else 'verified',
                    'reason': ('session_error' if error is not None else
                               'call_failed' if self._failed else
                               'no_calls' if not self.calls else None),
                    'root': str(self.root), 'checkout_root': str(ROOT),
                    'phase': self.phase, 'revision': self.revision,
                    'policy_path': str(self.policy_path),
                    'policy_pin': copy.deepcopy(self.policy_pin),
                    'calls': copy.deepcopy(self.calls),
                    'call_count': len(self.calls),
                    'integration_pending': True,
                    'formal_permission': False,
                    'source_closure_complete': False,
                    'runtime_closure_complete': False,
                    'execution_authenticated': False,
                    'git_loaded_code_authenticated': False,
                    'git_descendants_authenticated': False}
        raw = io.json_bytes(manifest)
        v.require(len(raw) <= MAX_MANIFEST,
                  'owned source Git manifest byte limit')
        io._exclusive(self.root / 'manifest.json', raw)
        pin = observed._pin(raw)
        evidence._raw(observed._file(self.root / 'manifest.json', MAX_MANIFEST),
                      pin, 'saved owned source Git manifest raw pin')
        retained = verify_retained(
            self.root, pin, policy_path=self.policy_path,
            expected_policy_pin=self.policy_pin, revision=self.revision,
            phase=self.phase)
        v.require(retained['call_status'] == manifest['status'],
                  'saved owned source Git manifest readback')
        self.manifest_result = {
            'status': manifest['status'], 'reason': manifest['reason'],
            'receipt_root': str(self.root), 'manifest_pin': pin,
            'call_count': len(self.calls), 'formal_permission': False,
            'source_closure_complete': False,
            'runtime_closure_complete': False,
            'execution_authenticated': False,
            'integration_pending': True}
        return self.manifest_result

    def __exit__(self, error_type, error, traceback):
        primary = self._unreaped if self._unreaped is not None else error
        try:
            self._finish(primary)
        except BaseException as save_error:
            if primary is None:
                raise
            primary.source_git_manifest_error = save_error
        if self._unreaped is not None and error is not self._unreaped:
            if error is not None:
                self._unreaped.follow_on_error = error
            raise self._unreaped
        return False


def verify_retained(receipt_root, expected_manifest_pin, *, policy_path,
                    expected_policy_pin, revision, phase):
    """Reopen every saved pin without starting a new Git subprocess."""
    evidence._digest(revision, 40)
    _name(phase, 'retained owned source Git phase')
    target = _root(receipt_root)
    evidence._pin(expected_manifest_pin)
    raw = observed._file(target / 'manifest.json', MAX_MANIFEST)
    evidence._raw(raw, expected_manifest_pin,
                  'retained owned source Git manifest raw pin')
    manifest = v.strict_json(raw)
    v.require(type(manifest) is dict and set(manifest) == {
        'format', 'status', 'reason', 'root', 'checkout_root', 'phase',
        'revision', 'policy_path', 'policy_pin', 'calls', 'call_count',
        'integration_pending', 'formal_permission',
        'source_closure_complete', 'runtime_closure_complete',
        'execution_authenticated', 'git_loaded_code_authenticated',
        'git_descendants_authenticated'},
        'retained owned source Git manifest fields')
    v.require(manifest['format'] == FORMAT and
              manifest['root'] == str(target) and
              manifest['checkout_root'] == str(ROOT) and
              manifest['phase'] == phase and
              manifest['revision'] == revision and
              manifest['policy_path'] == str(policy_path) and
              manifest['policy_pin'] == expected_policy_pin and
              manifest['integration_pending'] is True and
              all(manifest[key] is False for key in (
                  'formal_permission', 'source_closure_complete',
                  'runtime_closure_complete', 'execution_authenticated',
                  'git_loaded_code_authenticated',
                  'git_descendants_authenticated')) and
              type(manifest['calls']) is list and
              type(manifest['call_count']) is int and
              manifest['call_count'] == len(manifest['calls']) <= MAX_CALLS,
              'retained owned source Git manifest scope')
    policy = _policy(policy_path, expected_policy_pin, revision, target,
                     check_current=False)
    seen = set()
    for index, row in enumerate(manifest['calls']):
        v.require(type(row) is dict and set(row) == {
            'index', 'call_id', 'operation', 'source_path',
            'expected_output_pin', 'receipt_pin', 'call_status',
            'reason', 'error_type'} and
            type(row['index']) is int and row['index'] == index,
            'retained owned source Git call row')
        call_id = _name(row['call_id'], 'retained owned source Git call id')
        v.require(call_id not in seen, 'retained owned source Git duplicate id')
        seen.add(call_id)
        owned_git._command(policy, row['operation'], row['source_path'],
                           row['expected_output_pin'])
        pin = row['receipt_pin']
        if pin is None:
            v.require(manifest['status'] == 'failed' and
                      row['call_status'] is None and
                      type(row['error_type']) is str and
                      row['reason'] == 'call_exception',
                      'retained owned source Git missing direct receipt')
            continue
        evidence._pin(pin)
        receipt_path = target / call_id / 'receipt.json'
        saved_receipt_raw = observed._file(receipt_path, owned_git.MAX_RECEIPT)
        evidence._raw(saved_receipt_raw, pin,
                      'retained owned source Git direct receipt raw pin')
        saved_receipt = v.strict_json(saved_receipt_raw)
        checked = owned_git.verify_retained(
            target / call_id, pin, root=ROOT, policy=policy)
        v.require(checked['call_status'] == row['call_status'] ==
                  saved_receipt['status'] and
                  checked['reason'] == saved_receipt['reason'] and
                  saved_receipt['operation'] == row['operation'] and
                  saved_receipt['source_path'] == row['source_path'] and
                  saved_receipt['expected_output_pin'] ==
                  row['expected_output_pin'] and
                  saved_receipt['revision'] == revision and
                  checked['formal_permission'] is False and
                  checked['integration_pending'] is True and
                  ((row['call_status'] == 'verified' and
                    ((row['reason'] is None and
                      row['error_type'] is None) or
                     (manifest['status'] == 'failed' and
                      row['reason'] == 'adapter_binding_failed' and
                      type(row['error_type']) is str))) or
                   (row['call_status'] == 'failed' and
                    row['reason'] == saved_receipt['reason'] and
                    type(row['error_type']) is str)),
                  'retained owned source Git direct call binding')
    if manifest['status'] == 'verified':
        v.require(manifest['reason'] is None and manifest['calls'] and
                  all(row['call_status'] == 'verified' and
                      row['receipt_pin'] is not None
                      for row in manifest['calls']),
                  'retained owned source Git success')
    else:
        v.require(manifest['status'] == 'failed' and
                  manifest['reason'] in
                  ('session_error', 'call_failed', 'no_calls'),
                  'retained owned source Git failure')
    return {'status': 'verified_retained',
            'call_status': manifest['status'],
            'manifest_pin': expected_manifest_pin,
            'call_count': manifest['call_count'],
            'calls': copy.deepcopy(manifest['calls']),
            'integration_pending': True, 'formal_permission': False,
            'source_closure_complete': False,
            'runtime_closure_complete': False,
            'execution_authenticated': False}
