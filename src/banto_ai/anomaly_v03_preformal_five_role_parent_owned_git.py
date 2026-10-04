"""Opt-in owned Git for the five-role parent's selected source checks.

The seven pre-Job calls and the parent's 35 direct calls have separate pinned
manifests. Candidate profile sets are rejected because their loader uses bare
Git in the parent. The Job child and inner chain still use bare Git. Neither
Git's loaded code nor its descendants, the complete source/runtime closure,
or formal evaluation are authenticated here.
"""
from __future__ import annotations

import copy
from pathlib import Path

from . import anomaly_v03 as v
from . import anomaly_v03_consumer_evidence as evidence
from . import anomaly_v03_platform_five_role_fixture as chain
from . import anomaly_v03_preformal_five_role_job_owner as owner
from . import anomaly_v03_preformal_five_role_owned_source_anchor_v2 as preflight
from . import anomaly_v03_preformal_owned_source_git_session as source_git
from . import anomaly_v03_reader_evidence as observed
from . import _anomaly_v03_io as io


ROOT = Path(__file__).resolve().parents[2]
FORMAT = 'anomaly-v03-preformal-five-role-parent-owned-git-v1'
PREFLIGHT_PHASE = preflight.PHASE
PARENT_PHASE = 'parent-source-boundaries'
GIT_SCOPE = 'seven pre-Job and thirty-five parent direct Git calls only'
MAX_RECEIPT = 24 * 1024
_FIELDS = preflight._FIELDS | {
    'parent_git_root', 'parent_git_manifest_pin', 'parent_git_status',
    'parent_git_call_count', 'parent_v1_git_owned'}


def _pinned(path, pin, maximum):
    return preflight._pinned(path, pin, maximum)


def _capture(receipt, reader, prefix):
    if reader is not None and reader.manifest_result is not None:
        result = reader.manifest_result
        receipt[prefix + '_git_manifest_pin'] = result['manifest_pin']
        receipt[prefix + '_git_status'] = result['status']
        receipt[prefix + '_git_call_count'] = result['call_count']


def _expected_calls(source, prefix):
    expected = [(prefix + 'head', 'head', None, None),
                (prefix + 'status', 'status', None, None)]
    expected.extend((prefix + f'selected-source-{index}', 'source_blob',
                     name, source['orchestrator_selected'][name])
                    for index, name in enumerate(chain.SOURCES))
    expected.append((prefix + 'owner-source', 'source_blob', owner.SOURCE,
                     source['owner']))
    return expected


def _parent_calls(calls, source):
    v.require(type(calls) is list and len(calls) == 35,
              'exact parent owned Git call count')
    expected = []
    for index in range(4):
        expected.extend(_expected_calls(source, f'parent-source-{index}-'))
    expected.extend(_expected_calls(source, 'parent-verify-'))
    for index, (row, (call_id, operation, path, pin)) in enumerate(
            zip(calls, expected)):
        if pin is not None:
            evidence._pin(pin)
        v.require(type(row) is dict and row['index'] == index and
                  row['call_id'] == call_id and
                  row['operation'] == operation and
                  row['source_path'] == path and
                  row['expected_output_pin'] == pin and
                  row['call_status'] == 'verified' and
                  row['receipt_pin'] is not None and
                  row['reason'] is None and row['error_type'] is None,
                  'parent owned Git call order and receipt')


def _manifest(target, receipt, *, parent):
    prefix = 'parent' if parent else 'source'
    pin = receipt[prefix + '_git_manifest_pin']
    phase = PARENT_PHASE if parent else PREFLIGHT_PHASE
    root = target / ('parent-git' if parent else 'git')
    checked = source_git.verify_retained(
        root, pin, policy_path=receipt['git_policy_path'],
        expected_policy_pin=receipt['git_policy_pin'],
        revision=receipt['source_revision'], phase=phase)
    v.require(checked['call_status'] == receipt[prefix + '_git_status'] and
              checked['call_count'] == receipt[prefix + '_git_call_count'] and
              checked['formal_permission'] is False and
              checked['source_closure_complete'] is False and
              checked['runtime_closure_complete'] is False,
              'parent owned Git retained manifest scope')
    if not parent and checked['call_status'] == 'verified':
        preflight._source_calls(checked['calls'], receipt['source_pins'])
    if parent and receipt['status'] == 'verified':
        v.require(checked['call_status'] == 'verified',
                  'verified parent requires verified owned Git manifest')
        _parent_calls(checked['calls'], receipt['source_pins'])
    return checked


class _SavedGitReader:
    """Replay only the pinned parent's verifier calls; launch nothing."""

    def __init__(self, root, calls):
        self.root = root
        self.calls = calls[-7:]
        self.index = 0

    def run(self, *, call_id, operation, source_path=None,
            expected_output_pin=None):
        v.require(self.index < len(self.calls), 'saved Git replay exhausted')
        row = self.calls[self.index]
        self.index += 1
        v.require(row['call_id'] == call_id and
                  row['operation'] == operation and
                  row['source_path'] == source_path and
                  row['expected_output_pin'] == expected_output_pin,
                  'saved Git replay call binding')
        path = self.root / call_id
        direct = v.strict_json(_pinned(
            path / 'receipt.json', row['receipt_pin'],
            source_git.owned_git.MAX_RECEIPT))
        pin = direct['stdout_pin']
        evidence._pin(pin)
        raw = observed._file(path / 'stdout.bin',
                             source_git.owned_git.MAX_OUTPUT[operation])
        evidence._raw(raw, pin, 'saved parent Git stdout')
        return raw

    def finish(self):
        v.require(self.index == len(self.calls),
                  'saved Git replay incomplete')


def _verify_owner_scope(root, pin, parent_root, calls):
    replay = _SavedGitReader(parent_root, calls)
    checked = owner.verify_retained(
        root, pin, git_reader=replay, git_call_prefix='parent-verify-')
    replay.finish()
    v.require(type(checked) is dict and
              checked.get('status') == 'verified_retained' and
              checked.get('receipt_pin') == pin and
              checked.get('formal_permission') is False and
              checked.get('source_closure_complete') is False and
              checked.get('runtime_closure_complete') is False,
              'retained parent owner closed scope')


def _save(target, receipt):
    raw = io.json_bytes(receipt)
    v.require(len(raw) <= MAX_RECEIPT, 'parent owned Git receipt bound')
    io._exclusive(target / 'receipt.json', raw)
    pin = observed._pin(raw)
    evidence._raw(_pinned(target / 'receipt.json', pin, MAX_RECEIPT), pin,
                  'saved parent owned Git receipt')
    return {**receipt, 'check_directory': str(target), 'receipt_pin': pin}


def run_anchored(*, expected_mode, join_root, expected_join_receipt_pin,
                 expected_revision, receipt_parent, receipt_name,
                 git_policy_path, expected_git_policy_pin,
                 candidate_set_path=None, expected_candidate_set_pin=None):
    """Run preflight and the v1 parent with owned direct source Git calls."""
    v.require(type(expected_mode) is str and expected_mode == 'fixture',
              'only invented five-role mode')
    evidence._digest(expected_revision, 40)
    evidence._pin(expected_join_receipt_pin)
    evidence._pin(expected_git_policy_pin)
    v.require((candidate_set_path is None) ==
              (expected_candidate_set_pin is None), 'candidate path/pin pair')
    v.require(candidate_set_path is None,
              'candidate profiles use unowned parent Git; opt-in path closed')
    v.safe_relative_path(receipt_name)
    v.require('/' not in receipt_name and '\\' not in receipt_name and
              not receipt_name.casefold().startswith('anomaly-multiseed-v0'),
              'new parent owned Git attempt name')
    parent = Path(receipt_parent)
    v.require(parent.is_absolute() and parent.is_relative_to(ROOT / 'artifacts'),
              'parent owned Git under local artifacts')
    io.regular_path(parent, directory=True, missing=True)
    parent.mkdir(exist_ok=True)
    parent = io._local_parent(parent)
    target = io.regular_path(parent / receipt_name, directory=True,
                             missing=True)
    join_root = Path(join_root)
    v.require(join_root.is_absolute() and
              join_root.is_relative_to(ROOT / 'artifacts') and
              not target.is_relative_to(join_root) and
              not join_root.is_relative_to(target),
              'parent owned Git output/join separation')
    policy_path = Path(git_policy_path)
    v.require(policy_path.is_absolute() and
              policy_path.is_relative_to(ROOT / 'artifacts') and
              not policy_path.is_relative_to(join_root) and
              not policy_path.is_relative_to(target),
              'external parent owned Git policy separation')
    target.mkdir()
    inner_root = target / 'attempt'
    receipt = {
        'format': FORMAT, 'mode': 'fixture', 'status': 'failed',
        'reason': 'source_preflight_rejected', 'error_type': None,
        'root': str(target), 'source_revision': expected_revision,
        'join_root': str(join_root),
        'join_receipt_pin': copy.deepcopy(expected_join_receipt_pin),
        'candidate_set_path': (None if candidate_set_path is None else
                               str(candidate_set_path)),
        'candidate_set_pin': copy.deepcopy(expected_candidate_set_pin),
        'git_policy_path': str(policy_path),
        'git_policy_pin': copy.deepcopy(expected_git_policy_pin),
        'source_git_root': str(target / 'git'),
        'source_git_manifest_pin': None, 'source_git_status': None,
        'source_git_call_count': None, 'source_pins': None,
        'parent_git_root': str(target / 'parent-git'),
        'parent_git_manifest_pin': None, 'parent_git_status': None,
        'parent_git_call_count': None, 'parent_v1_git_owned': False,
        'owner_root': str(inner_root), 'owner_receipt_pin': None,
        'owner_status': None, 'git_scope': GIT_SCOPE,
        'inner_v1_git_owned': False, 'integration_pending': True,
        'invented_only': True, 'registered_data_read': False,
        'registered_saved_reader_used': False,
        'real_producer_executed': False, 'new_evaluations': 0,
        'formal_permission': False, 'source_closure_complete': False,
        'runtime_closure_complete': False,
        'execution_authenticated': False, 'next_stage_authorized': False,
        'retry_authorized': False}
    pre_reader = parent_reader = None
    critical = None
    try:
        try:
            with source_git.OwnedSourceGitSession(
                    policy_path=policy_path,
                    expected_policy_pin=expected_git_policy_pin,
                    revision=expected_revision, receipt_root=target / 'git',
                    phase=PREFLIGHT_PHASE) as pre_reader:
                source = owner._source(expected_revision, git_reader=pre_reader)
        finally:
            _capture(receipt, pre_reader, 'source')
        receipt['source_pins'] = copy.deepcopy(source)
        v.require(source['revision'] == expected_revision and
                  receipt['source_git_status'] == 'verified',
                  'owned source preflight verified')
        _manifest(target, receipt, parent=False)
        receipt['reason'] = 'owner_failed'
        try:
            with source_git.OwnedSourceGitSession(
                    policy_path=policy_path,
                    expected_policy_pin=expected_git_policy_pin,
                    revision=expected_revision,
                    receipt_root=target / 'parent-git',
                    phase=PARENT_PHASE) as parent_reader:
                inner = owner.run_owned(
                    expected_mode='fixture', join_root=join_root,
                    expected_join_receipt_pin=expected_join_receipt_pin,
                    expected_revision=expected_revision,
                    receipt_parent=target, receipt_name='attempt',
                    candidate_set_path=candidate_set_path,
                    expected_candidate_set_pin=expected_candidate_set_pin,
                    git_reader=parent_reader)
                receipt['owner_receipt_pin'] = copy.deepcopy(inner['receipt_pin'])
                receipt['owner_status'] = inner['status']
                v.require(inner['status'] in ('verified', 'failed') and
                          inner['check_directory'] == str(inner_root),
                          'owned parent five-role result binding')
                saved_owner = preflight._owner_receipt(
                    inner_root, inner['receipt_pin'])
                preflight._owner_binding(receipt, saved_owner, inner_root)
                if inner['status'] == 'verified':
                    checked = owner.verify_retained(
                        inner_root, inner['receipt_pin'],
                        git_reader=parent_reader,
                        git_call_prefix='parent-verify-')
                    v.require(checked['status'] == 'verified_retained' and
                              checked['receipt_pin'] == inner['receipt_pin'] and
                              checked['formal_permission'] is False and
                              checked['source_closure_complete'] is False and
                              checked['runtime_closure_complete'] is False,
                              'live owned parent retained verification')
        finally:
            _capture(receipt, parent_reader, 'parent')
        if receipt['owner_status'] == 'verified':
            v.require(receipt['parent_git_status'] == 'verified' and
                      receipt['parent_git_call_count'] == 35,
                      'owned parent source calls incomplete')
            _parent_calls(_manifest(target, receipt, parent=True)['calls'],
                          receipt['source_pins'])
            receipt.update(status='verified', reason=None,
                           parent_v1_git_owned=True)
    except (source_git.owned_git.UnreapedGit,
            owner.job_owner.UnreapedJob,
            owner.job_owner.UnclosedHandles) as error:
        receipt['reason'] = 'process_reconciliation_required'
        receipt['error_type'] = type(error).__name__
        critical = error
    except (ValueError, OSError, KeyError, TypeError) as error:
        receipt['error_type'] = type(error).__name__
        if receipt['reason'] == 'owner_failed':
            receipt['reason'] = 'owner_rejected'
    except BaseException as error:
        receipt['reason'] = 'unexpected_owned_source_failure'
        receipt['error_type'] = type(error).__name__
        critical = error
    try:
        saved = _save(target, receipt)
    except BaseException as save_error:
        if critical is None:
            raise
        critical.outer_receipt_error = save_error
        raise critical
    if critical is not None:
        raise critical
    return saved


def verify_retained(result_root, expected_receipt_pin):
    """Reopen owned Git and owner bytes without launching Git or a worker."""
    target = Path(result_root)
    v.require(target.is_absolute() and target.is_relative_to(ROOT / 'artifacts'),
              'known parent owned Git root')
    receipt = v.strict_json(_pinned(target / 'receipt.json',
                                    expected_receipt_pin, MAX_RECEIPT))
    v.require(type(receipt) is dict and set(receipt) == _FIELDS and
              receipt['format'] == FORMAT and receipt['mode'] == 'fixture' and
              receipt['root'] == str(target) and
              receipt['source_git_root'] == str(target / 'git') and
              receipt['parent_git_root'] == str(target / 'parent-git') and
              receipt['owner_root'] == str(target / 'attempt') and
              receipt['git_scope'] == GIT_SCOPE and
              receipt['inner_v1_git_owned'] is False and
              receipt['integration_pending'] is True and
              receipt['invented_only'] is True and
              all(receipt[key] is False for key in (
                  'registered_data_read', 'registered_saved_reader_used',
                  'real_producer_executed', 'formal_permission',
                  'source_closure_complete', 'runtime_closure_complete',
                  'execution_authenticated', 'next_stage_authorized',
                  'retry_authorized')) and
              type(receipt['new_evaluations']) is int and
              receipt['new_evaluations'] == 0,
              'retained parent owned Git closed scope')
    evidence._digest(receipt['source_revision'], 40)
    evidence._pin(receipt['join_receipt_pin'])
    evidence._pin(receipt['git_policy_pin'])
    v.require((receipt['candidate_set_path'] is None) ==
              (receipt['candidate_set_pin'] is None),
              'retained candidate path/pin pair')
    v.require(receipt['candidate_set_path'] is None,
              'retained parent owned Git excludes candidate profiles')
    policy_path = Path(receipt['git_policy_path'])
    join_root = Path(receipt['join_root'])
    v.require(policy_path.is_absolute() and
              policy_path.is_relative_to(ROOT / 'artifacts') and
              not policy_path.is_relative_to(target) and
              not policy_path.is_relative_to(join_root) and
              join_root.is_absolute() and
              join_root.is_relative_to(ROOT / 'artifacts') and
              not join_root.is_relative_to(target) and
              not target.is_relative_to(join_root),
              'retained policy/join separation')
    source_git._policy(policy_path, receipt['git_policy_pin'],
                       receipt['source_revision'], target / 'git',
                       check_current=False)
    for prefix, parent in (('source', False), ('parent', True)):
        pin = receipt[prefix + '_git_manifest_pin']
        if pin is None:
            v.require(receipt[prefix + '_git_status'] is None and
                      receipt[prefix + '_git_call_count'] is None,
                      'absent owned Git manifest fields')
        else:
            evidence._pin(pin)
            _manifest(target, receipt, parent=parent)
    owner_pin = receipt['owner_receipt_pin']
    if owner_pin is None:
        v.require(receipt['owner_status'] is None,
                  'absent owner status')
    else:
        evidence._pin(owner_pin)
        v.require(receipt['source_git_status'] == 'verified' and
                  receipt['parent_git_manifest_pin'] is not None,
                  'owner requires both owned Git phases')
        saved_owner = preflight._owner_receipt(target / 'attempt', owner_pin)
        preflight._owner_binding(receipt, saved_owner, target / 'attempt')
    if receipt['status'] == 'verified':
        v.require(receipt['reason'] is None and
                  receipt['error_type'] is None and
                  receipt['parent_v1_git_owned'] is True and
                  receipt['source_git_status'] == 'verified' and
                  receipt['source_git_call_count'] == 7 and
                  receipt['parent_git_status'] == 'verified' and
                  receipt['parent_git_call_count'] == 35 and
                  receipt['owner_status'] == 'verified' and
                  owner_pin is not None,
                  'retained parent owned Git success prerequisites')
        checked = _manifest(target, receipt, parent=True)
        _verify_owner_scope(target / 'attempt', owner_pin,
                            target / 'parent-git', checked['calls'])
    else:
        v.require(receipt['status'] == 'failed' and
                  receipt['parent_v1_git_owned'] is False and
                  receipt['reason'] in (
                      'source_preflight_rejected', 'owner_failed',
                      'owner_rejected', 'process_reconciliation_required',
                      'unexpected_owned_source_failure'),
                  'retained parent owned Git failure')
        if receipt['reason'] == 'source_preflight_rejected':
            v.require(owner_pin is None and
                      receipt['parent_git_manifest_pin'] is None,
                      'preflight rejection before parent')
    return {'status': 'verified_retained',
            'call_status': receipt['status'], 'reason': receipt['reason'],
            'source_git_call_count': receipt['source_git_call_count'],
            'parent_git_call_count': receipt['parent_git_call_count'],
            'receipt_pin': expected_receipt_pin,
            'formal_permission': False, 'source_closure_complete': False,
            'runtime_closure_complete': False,
            'execution_authenticated': False}
