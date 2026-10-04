"""Bind seven owned pre-Job source Git calls to an invented five-role Job.

This opt-in v2 wrapper does not change the v1 Job owner.  Git calls made by
that owner, its child, and the inner chain remain outside this wrapper's owned
Git evidence.  No complete source/runtime closure or formal permission follows.
"""
from __future__ import annotations

import copy
from pathlib import Path

from . import anomaly_v03 as v
from . import anomaly_v03_consumer_evidence as evidence
from . import anomaly_v03_platform_five_role_fixture as chain
from . import anomaly_v03_preformal_five_role_job_owner as owner
from . import anomaly_v03_preformal_owned_source_git_session as source_git
from . import anomaly_v03_reader_evidence as observed
from . import _anomaly_v03_io as io


ROOT = Path(__file__).resolve().parents[2]
FORMAT = 'anomaly-v03-preformal-five-role-owned-source-anchor-v2'
PHASE = 'pre-job-selected-source'
GIT_SCOPE = 'seven direct pre-Job selected-source calls only'
MAX_RECEIPT = 24 * 1024
_FIELDS = {
    'format', 'mode', 'status', 'reason', 'error_type', 'root',
    'source_revision', 'join_root', 'join_receipt_pin',
    'candidate_set_path', 'candidate_set_pin', 'git_policy_path',
    'git_policy_pin', 'source_git_root', 'source_git_manifest_pin',
    'source_git_status', 'source_git_call_count', 'source_pins',
    'owner_root', 'owner_receipt_pin', 'owner_status', 'git_scope',
    'inner_v1_git_owned', 'integration_pending', 'invented_only',
    'registered_data_read', 'registered_saved_reader_used',
    'real_producer_executed', 'new_evaluations', 'formal_permission',
    'source_closure_complete', 'runtime_closure_complete',
    'execution_authenticated', 'next_stage_authorized', 'retry_authorized',
}


def _pinned(path, pin, maximum):
    evidence._pin(pin)
    raw = observed._file(path, maximum)
    evidence._raw(raw, pin, 'five-role owned-source anchor raw pin')
    return raw


def _source_calls(calls, source):
    """Check the selected seven-call inventory, not only its listed receipts."""
    v.require(type(source) is dict and set(source) == {
        'revision', 'orchestrator_selected', 'owner', 'scope'},
        'owned-source selected source fields')
    evidence._digest(source['revision'], 40)
    v.require(source['scope'] ==
              'clean-head-selected-working-raw-not-source-closure' and
              type(source['orchestrator_selected']) is dict and
              set(source['orchestrator_selected']) == set(chain.SOURCES),
              'owned-source selected source scope')
    expected = [('head', 'head', None, None),
                ('status', 'status', None, None)]
    expected.extend((f'selected-source-{index}', 'source_blob', name,
                     source['orchestrator_selected'][name])
                    for index, name in enumerate(chain.SOURCES))
    expected.append(('owner-source', 'source_blob', owner.SOURCE,
                     source['owner']))
    v.require(type(calls) is list and len(calls) == len(expected) == 7,
              'exact seven owned-source calls')
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
                  'owned-source call order and saved receipt')


def _source_manifest(target, receipt):
    checked = source_git.verify_retained(
        target / 'git', receipt['source_git_manifest_pin'],
        policy_path=receipt['git_policy_path'],
        expected_policy_pin=receipt['git_policy_pin'],
        revision=receipt['source_revision'], phase=PHASE)
    v.require(checked['call_status'] == receipt['source_git_status'] and
              checked['call_count'] == receipt['source_git_call_count'] and
              checked['formal_permission'] is False and
              checked['source_closure_complete'] is False and
              checked['runtime_closure_complete'] is False and
              checked['execution_authenticated'] is False,
              'retained owned-source manifest scope')
    if checked['call_status'] == 'verified':
        v.require(type(receipt['source_pins']) is dict and
                  receipt['source_pins'].get('revision') ==
                  receipt['source_revision'],
                  'retained owned-source revision')
        _source_calls(checked['calls'], receipt['source_pins'])
    return checked


def _owner_receipt(root, pin):
    return v.strict_json(_pinned(root / 'receipt.json', pin,
                                 owner.MAX_RECEIPT))


def _owner_binding(receipt, saved, root):
    v.require(type(saved) is dict and
              saved.get('format') == owner.FORMAT and
              saved.get('mode') == 'fixture' and
              saved.get('status') == receipt['owner_status'] and
              saved.get('status') in ('verified', 'failed') and
              saved.get('formal_permission') is False and
              saved.get('source_revision') == receipt['source_revision'] and
              saved.get('join_root') == receipt['join_root'] and
              saved.get('join_receipt_pin') == receipt['join_receipt_pin'] and
              saved.get('candidate_set_pin') == receipt['candidate_set_pin'],
              'retained v1 five-role owner binding')
    invocation_pin = saved.get('invocation_pin')
    if invocation_pin is not None:
        invocation = v.strict_json(_pinned(
            root / 'invocation.json', invocation_pin, owner.MAX_INVOCATION))
        v.require(invocation.get('source_revision') ==
                  receipt['source_revision'] and
                  invocation.get('join_root') == receipt['join_root'] and
                  invocation.get('join_receipt_pin') ==
                  receipt['join_receipt_pin'] and
                  invocation.get('candidate_set_path') ==
                  receipt['candidate_set_path'] and
                  invocation.get('candidate_set_pin') ==
                  receipt['candidate_set_pin'],
                  'retained v1 invocation/outer input binding')
    else:
        v.require(receipt['owner_status'] != 'verified',
                  'verified v1 owner invocation required')
    if receipt['owner_status'] == 'verified':
        v.require(saved.get('source_pins') == receipt['source_pins'],
                  'v1 owner source differs from owned preflight')


def _verify_owner_scope(root, pin):
    # The v1 verifier relaunches read-only bare Git for its source checks.
    checked = owner.verify_retained(root, pin)
    v.require(type(checked) is dict and
              checked.get('status') == 'verified_retained' and
              checked.get('receipt_pin') == pin and
              checked.get('formal_permission') is False and
              checked.get('source_closure_complete') is False and
              checked.get('runtime_closure_complete') is False,
              'retained v1 owner closed scope')


def _save(target, receipt):
    raw = io.json_bytes(receipt)
    v.require(len(raw) <= MAX_RECEIPT, 'owned-source anchor receipt bound')
    io._exclusive(target / 'receipt.json', raw)
    pin = observed._pin(raw)
    evidence._raw(_pinned(target / 'receipt.json', pin, MAX_RECEIPT), pin,
                  'saved owned-source anchor receipt')
    return {**receipt, 'check_directory': str(target), 'receipt_pin': pin}


def run_anchored(*, expected_mode, join_root, expected_join_receipt_pin,
                 expected_revision, receipt_parent, receipt_name,
                 git_policy_path, expected_git_policy_pin,
                 candidate_set_path=None, expected_candidate_set_pin=None):
    """Run exact owned source preflight, then the unchanged v1 five-role Job."""
    v.require(type(expected_mode) is str and expected_mode == 'fixture',
              'only invented five-role mode')
    evidence._digest(expected_revision, 40)
    evidence._pin(expected_join_receipt_pin)
    evidence._pin(expected_git_policy_pin)
    v.require((candidate_set_path is None) ==
              (expected_candidate_set_pin is None), 'candidate path/pin pair')
    if expected_candidate_set_pin is not None:
        evidence._pin(expected_candidate_set_pin)
    v.safe_relative_path(receipt_name)
    v.require('/' not in receipt_name and '\\' not in receipt_name and
              not receipt_name.casefold().startswith('anomaly-multiseed-v0'),
              'new owned-source attempt name')
    parent = Path(receipt_parent)
    v.require(parent.is_absolute() and parent.is_relative_to(ROOT / 'artifacts'),
              'owned-source parent under local artifacts')
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
              'owned-source output/join separation')
    policy_path = Path(git_policy_path)
    v.require(policy_path.is_absolute() and
              policy_path.is_relative_to(ROOT / 'artifacts') and
              not policy_path.is_relative_to(join_root) and
              not policy_path.is_relative_to(target),
              'external owned-source policy separation')
    target.mkdir()  # Exclusive attempt root; a failed attempt is never reused.
    git_root = target / 'git'
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
        'source_git_root': str(git_root), 'source_git_manifest_pin': None,
        'source_git_status': None, 'source_git_call_count': None,
        'source_pins': None, 'owner_root': str(inner_root),
        'owner_receipt_pin': None, 'owner_status': None,
        'git_scope': GIT_SCOPE, 'inner_v1_git_owned': False,
        'integration_pending': True, 'invented_only': True,
        'registered_data_read': False, 'registered_saved_reader_used': False,
        'real_producer_executed': False, 'new_evaluations': 0,
        'formal_permission': False, 'source_closure_complete': False,
        'runtime_closure_complete': False,
        'execution_authenticated': False, 'next_stage_authorized': False,
        'retry_authorized': False,
    }
    reader = None
    critical = None
    try:
        try:
            with source_git.OwnedSourceGitSession(
                    policy_path=policy_path,
                    expected_policy_pin=expected_git_policy_pin,
                    revision=expected_revision, receipt_root=git_root,
                    phase=PHASE) as reader:
                source = owner._source(expected_revision, git_reader=reader)
        finally:
            if reader is not None and reader.manifest_result is not None:
                manifest = reader.manifest_result
                receipt['source_git_manifest_pin'] = manifest['manifest_pin']
                receipt['source_git_status'] = manifest['status']
                receipt['source_git_call_count'] = manifest['call_count']
        receipt['source_pins'] = copy.deepcopy(source)
        v.require(source['revision'] == expected_revision and
                  receipt['source_git_status'] == 'verified',
                  'owned-source preflight verified')
        _source_manifest(target, receipt)
        receipt['reason'] = 'owner_failed'
        inner = owner.run_owned(
            expected_mode='fixture', join_root=join_root,
            expected_join_receipt_pin=expected_join_receipt_pin,
            expected_revision=expected_revision, receipt_parent=target,
            receipt_name='attempt', candidate_set_path=candidate_set_path,
            expected_candidate_set_pin=expected_candidate_set_pin)
        receipt['owner_receipt_pin'] = copy.deepcopy(inner['receipt_pin'])
        receipt['owner_status'] = inner['status']
        v.require(inner['status'] in ('verified', 'failed'),
                  'v1 owner result status')
        v.require(inner['check_directory'] == str(inner_root),
                  'owned v1 five-role result root')
        saved_owner = _owner_receipt(inner_root, inner['receipt_pin'])
        _owner_binding(receipt, saved_owner, inner_root)
        if inner['status'] == 'verified':
            _verify_owner_scope(inner_root, inner['receipt_pin'])
            receipt.update(status='verified', reason=None)
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
    """Reopen saved pins; v1 owner verification still uses bare read-only Git."""
    target = Path(result_root)
    v.require(target.is_absolute() and
              target.is_relative_to(ROOT / 'artifacts'),
              'known local owned-source anchor root')
    receipt = v.strict_json(_pinned(target / 'receipt.json',
                                    expected_receipt_pin, MAX_RECEIPT))
    v.require(type(receipt) is dict and set(receipt) == _FIELDS and
              receipt['format'] == FORMAT and receipt['mode'] == 'fixture' and
              receipt['root'] == str(target) and
              receipt['source_git_root'] == str(target / 'git') and
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
              'retained owned-source anchor closed scope')
    evidence._digest(receipt['source_revision'], 40)
    evidence._pin(receipt['join_receipt_pin'])
    evidence._pin(receipt['git_policy_pin'])
    v.require((receipt['candidate_set_path'] is None) ==
              (receipt['candidate_set_pin'] is None),
              'retained candidate path/pin pair')
    if receipt['candidate_set_pin'] is not None:
        evidence._pin(receipt['candidate_set_pin'])
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
              'retained external policy/join separation')
    # The policy can be checked even if the first Git call never started.
    source_git._policy(policy_path, receipt['git_policy_pin'],
                       receipt['source_revision'], target / 'git',
                       check_current=False)
    pin = receipt['source_git_manifest_pin']
    if pin is None:
        v.require(receipt['source_git_status'] is None and
                  receipt['source_git_call_count'] is None and
                  receipt['source_pins'] is None,
                  'absent owned-source session fields')
    else:
        evidence._pin(pin)
        _source_manifest(target, receipt)
    owner_pin = receipt['owner_receipt_pin']
    if owner_pin is None:
        v.require(receipt['owner_status'] is None,
                  'absent owner status')
    else:
        evidence._pin(owner_pin)
        v.require(receipt['source_git_status'] == 'verified',
                  'owner requires verified owned-source preflight')
        saved_owner = _owner_receipt(target / 'attempt', owner_pin)
        _owner_binding(receipt, saved_owner, target / 'attempt')
    if receipt['reason'] == 'source_preflight_rejected':
        v.require(owner_pin is None and receipt['owner_status'] is None,
                  'source rejection cannot have an owner result')
    if receipt['reason'] == 'owner_failed':
        v.require(receipt['source_git_status'] == 'verified' and
                  owner_pin is not None and
                  receipt['owner_status'] == 'failed',
                  'failed owner requires a retained verified preflight')
    if receipt['status'] == 'verified':
        v.require(receipt['reason'] is None and
                  receipt['error_type'] is None and
                  receipt['source_git_status'] == 'verified' and
                  receipt['source_git_call_count'] == 7 and
                  receipt['owner_status'] == 'verified' and
                  owner_pin is not None,
                  'retained owned-source anchor success prerequisites')
        _verify_owner_scope(target / 'attempt', owner_pin)
    else:
        v.require(receipt['status'] == 'failed' and
                  receipt['reason'] in (
                      'source_preflight_rejected', 'owner_failed',
                      'owner_rejected', 'process_reconciliation_required',
                      'unexpected_owned_source_failure'),
                  'retained owned-source anchor failure')
    return {'status': 'verified_retained',
            'call_status': receipt['status'],
            'reason': receipt['reason'],
            'source_git_call_count': receipt['source_git_call_count'],
            'receipt_pin': expected_receipt_pin,
            'integration_pending': True, 'formal_permission': False,
            'source_closure_complete': False,
            'runtime_closure_complete': False,
            'execution_authenticated': False}
