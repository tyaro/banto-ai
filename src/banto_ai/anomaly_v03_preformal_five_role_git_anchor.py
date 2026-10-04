"""Versioned direct-Git preflight around the existing invented five-role Job.

Only the two Git calls before the Job are owned here.  The existing five-role
implementation, its later Git calls, and all source/runtime closure flags keep
their previous boundaries.
"""
from __future__ import annotations

import copy
from pathlib import Path

from . import anomaly_v03 as v
from . import anomaly_v03_consumer_evidence as evidence
from . import anomaly_v03_preformal_five_role_job_owner as owner
from . import anomaly_v03_preformal_owned_git as owned_git
from . import anomaly_v03_reader_evidence as observed
from . import _anomaly_v03_io as io


ROOT = Path(__file__).resolve().parents[2]
FORMAT = 'anomaly-v03-preformal-five-role-git-anchor-v1'
MAX_POLICY = 8 * 1024
MAX_RECEIPT = 16 * 1024


def _pinned(path, pin, maximum):
    evidence._pin(pin)
    raw = observed._file(path, maximum)
    evidence._raw(raw, pin, 'five-role Git anchor raw pin')
    return raw


def _policy(path, pin, revision, target, join_root):
    path = Path(path)
    v.require(path.is_absolute() and path.is_relative_to(ROOT / 'artifacts') and
              path.name == 'policy.json' and
              not path.is_relative_to(target) and
              not path.is_relative_to(Path(join_root)),
              'separate externally pinned Git policy')
    policy = v.strict_json(_pinned(path, pin, MAX_POLICY))
    v.require(type(policy) is dict and policy.get('revision') == revision,
              'Git policy revision binding')
    return policy


def _save(target, receipt):
    raw = io.json_bytes(receipt)
    v.require(len(raw) <= MAX_RECEIPT, 'five-role Git anchor receipt size')
    io._exclusive(target / 'receipt.json', raw)
    pin = observed._pin(raw)
    evidence._raw(_pinned(target / 'receipt.json', pin, MAX_RECEIPT), pin,
                  'saved five-role Git anchor receipt')
    return {**receipt, 'check_directory': str(target), 'receipt_pin': pin}


def _owner_receipt(root, pin):
    return v.strict_json(_pinned(root / 'receipt.json', pin, owner.MAX_RECEIPT))


def _verify_owner_scope(root, pin):
    # The v1 owner verifier reads retained evidence but also launches Git for
    # its clean-HEAD/source checks.  It never reruns the five-role Job.
    checked = owner.verify_retained(root, pin)
    v.require(type(checked) is dict and
              checked.get('status') == 'verified_retained' and
              checked.get('receipt_pin') == pin and
              checked.get('formal_permission') is False and
              checked.get('source_closure_complete') is False and
              checked.get('runtime_closure_complete') is False,
              'retained inner owner scope')


def run_anchored(*, expected_mode, join_root, expected_join_receipt_pin,
                 expected_revision, receipt_parent, receipt_name,
                 git_policy_path, expected_git_policy_pin,
                 candidate_set_path=None, expected_candidate_set_pin=None):
    """Retain two owned preflight Git calls, then enter the unchanged Job owner."""
    v.require(expected_mode == 'fixture' and type(expected_mode) is str,
              'only invented five-role mode')
    evidence._digest(expected_revision, 40)
    evidence._pin(expected_join_receipt_pin)
    evidence._pin(expected_git_policy_pin)
    v.require((candidate_set_path is None) ==
              (expected_candidate_set_pin is None),
              'candidate path/pin pair')
    if expected_candidate_set_pin is not None:
        evidence._pin(expected_candidate_set_pin)
    v.safe_relative_path(receipt_name)
    v.require('/' not in receipt_name and '\\' not in receipt_name and
              not receipt_name.casefold().startswith('anomaly-multiseed-v0'),
              'new Git anchor attempt name')
    parent = Path(receipt_parent)
    v.require(parent.is_absolute() and parent.is_relative_to(ROOT / 'artifacts'),
              'Git anchor parent under local artifacts')
    io.regular_path(parent, directory=True, missing=True)
    parent.mkdir(exist_ok=True)
    parent = io._local_parent(parent)
    target = io.regular_path(parent / receipt_name, directory=True,
                             missing=True)
    v.require(not target.is_relative_to(Path(join_root)) and
              not Path(join_root).is_relative_to(target),
              'Git anchor output/join overlap')
    target.mkdir()  # Exclusive attempt root; reuse fails before any Git call.
    inner_root = target / 'attempt'
    receipt = {'format': FORMAT, 'mode': 'fixture', 'status': 'failed',
               'reason': 'preflight_rejected', 'source_revision': expected_revision,
               'root': str(target), 'join_root': str(join_root),
               'join_receipt_pin': copy.deepcopy(expected_join_receipt_pin),
               'git_policy_path': str(git_policy_path),
               'git_policy_pin': copy.deepcopy(expected_git_policy_pin),
               'git_head_receipt_pin': None, 'git_head_status': None,
               'git_status_receipt_pin': None, 'git_status_status': None,
               'owner_root': str(inner_root), 'owner_receipt_pin': None,
               'owner_status': None,
               'candidate_set_path': (None if candidate_set_path is None else
                                      str(candidate_set_path)),
               'candidate_set_pin': copy.deepcopy(expected_candidate_set_pin),
               'git_scope': 'two direct pre-Job HEAD/status calls only',
               'integration_pending': True,
               'registered_data_read': False,
               'registered_saved_reader_used': False,
               'real_producer_executed': False,
               'new_evaluations': 0,
               'formal_permission': False,
               'source_closure_complete': False,
               'runtime_closure_complete': False,
               'execution_authenticated': False,
               'next_stage_authorized': False,
               'retry_authorized': False}
    critical = None
    policy = None
    try:
        policy = _policy(git_policy_path, expected_git_policy_pin,
                         expected_revision, target, join_root)
        git_root = target / 'git'
        git_root.mkdir()
        for operation, field in (('head', 'git_head'),
                                 ('status', 'git_status')):
            checked = owned_git.run_owned(
                root=ROOT, policy=policy, operation=operation,
                receipt_root=git_root / operation)
            receipt[field + '_receipt_pin'] = checked['receipt_pin']
            receipt[field + '_status'] = checked['receipt']['status']
            if checked['receipt']['status'] != 'verified':
                receipt['reason'] = operation + '_rejected'
                break
        else:
            receipt['reason'] = 'owner_failed'
            inner = owner.run_owned(
                expected_mode='fixture', join_root=join_root,
                expected_join_receipt_pin=expected_join_receipt_pin,
                expected_revision=expected_revision,
                receipt_parent=target, receipt_name='attempt',
                candidate_set_path=candidate_set_path,
                expected_candidate_set_pin=expected_candidate_set_pin)
            receipt['owner_receipt_pin'] = inner['receipt_pin']
            receipt['owner_status'] = inner['status']
            v.require(inner['check_directory'] == str(inner_root),
                      'owned five-role result root')
            saved_owner = _owner_receipt(inner_root, inner['receipt_pin'])
            v.require(saved_owner['status'] == inner['status'] and
                      saved_owner['formal_permission'] is False and
                      saved_owner['source_revision'] == expected_revision and
                      saved_owner['join_root'] == str(join_root) and
                      saved_owner['join_receipt_pin'] ==
                      expected_join_receipt_pin and
                      saved_owner['candidate_set_pin'] ==
                      expected_candidate_set_pin,
                      'owned five-role saved result')
            if inner['status'] == 'verified':
                _verify_owner_scope(inner_root, inner['receipt_pin'])
                receipt.update(status='verified', reason=None)
        _pinned(git_policy_path, expected_git_policy_pin, MAX_POLICY)
    except (owned_git.UnreapedGit, owner.job_owner.UnreapedJob,
            owner.job_owner.UnclosedHandles) as error:
        receipt['reason'] = 'process_reconciliation_required'
        receipt['error_type'] = type(error).__name__
        critical = error
    except (ValueError, OSError, KeyError, TypeError) as error:
        receipt['reason'] = 'git_anchor_rejected'
        receipt['error_type'] = type(error).__name__
    except BaseException as error:
        receipt['reason'] = 'unexpected_git_anchor_failure'
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
    """Reopen pins without a Job or owned preflight rerun.

    On success the existing v1 owner verifier also starts read-only Git
    subprocesses for its clean-HEAD and selected-source checks.
    """
    target = Path(result_root)
    v.require(target.is_absolute() and target.is_relative_to(ROOT / 'artifacts'),
              'known local Git anchor root')
    receipt = v.strict_json(_pinned(target / 'receipt.json',
                                    expected_receipt_pin, MAX_RECEIPT))
    v.require(receipt['format'] == FORMAT and receipt['mode'] == 'fixture' and
              receipt['root'] == str(target) and
              receipt['owner_root'] == str(target / 'attempt') and
              receipt['git_scope'] == 'two direct pre-Job HEAD/status calls only' and
              receipt['integration_pending'] is True and
              all(receipt[key] is False for key in (
                  'registered_data_read', 'registered_saved_reader_used',
                  'real_producer_executed', 'formal_permission',
                  'source_closure_complete', 'runtime_closure_complete',
                  'execution_authenticated', 'next_stage_authorized',
                  'retry_authorized')) and
              type(receipt['new_evaluations']) is int and
              receipt['new_evaluations'] == 0,
              'retained Git anchor closed scope')
    evidence._digest(receipt['source_revision'], 40)
    evidence._pin(receipt['join_receipt_pin'])
    policy = _policy(receipt['git_policy_path'], receipt['git_policy_pin'],
                     receipt['source_revision'], target, receipt['join_root'])
    for operation, field in (('head', 'git_head'), ('status', 'git_status')):
        pin = receipt[field + '_receipt_pin']
        status = receipt[field + '_status']
        if pin is None:
            v.require(status is None, field + ' absent status')
            continue
        evidence._pin(pin)
        result = owned_git.verify_retained(
            target / 'git' / operation, pin, root=ROOT, policy=policy)
        v.require(result['call_status'] == status and
                  result['formal_permission'] is False and
                  result['integration_pending'] is True,
                  field + ' retained result')
    if receipt['owner_receipt_pin'] is not None:
        evidence._pin(receipt['owner_receipt_pin'])
        saved_owner = _owner_receipt(target / 'attempt',
                                     receipt['owner_receipt_pin'])
        v.require(saved_owner['status'] == receipt['owner_status'] and
                  saved_owner['formal_permission'] is False and
                  saved_owner['source_revision'] ==
                  receipt['source_revision'] and
                  saved_owner['join_root'] == receipt['join_root'] and
                  saved_owner['join_receipt_pin'] ==
                  receipt['join_receipt_pin'] and
                  saved_owner['candidate_set_pin'] ==
                  receipt['candidate_set_pin'],
                  'retained inner owner receipt')
    else:
        v.require(receipt['owner_status'] is None,
                  'missing inner owner pin/status pair')
    if receipt['status'] == 'verified':
        v.require(receipt['reason'] is None and
                  receipt['git_head_status'] ==
                  receipt['git_status_status'] ==
                  receipt['owner_status'] == 'verified' and
                  receipt['owner_receipt_pin'] is not None,
                  'retained Git anchor success prerequisites')
        _verify_owner_scope(target / 'attempt', receipt['owner_receipt_pin'])
    else:
        v.require(receipt['status'] == 'failed' and
                  type(receipt['reason']) is str,
                  'retained Git anchor failure')
    return {'status': 'verified_retained',
            'call_status': receipt['status'],
            'formal_permission': False,
            'integration_pending': True,
            'receipt_pin': expected_receipt_pin}
