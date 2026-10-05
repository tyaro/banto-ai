"""Opt-in owned Git for the five-role parent's selected source checks.

The seven pre-Job calls and the parent's 35 direct calls have separate pinned
manifests. An explicit v2 opt-in also owns the child's 26 fixed source calls;
v3 includes the producer parent's source and observed project dependency Git.
v4 also includes direct Git in the numeric fixture analysis parent.
v5 adds the numeric fixture audit parent's direct Git.
v6 includes the publication prelude and writer parent's direct Git.
Candidate profile sets are rejected because their loader uses bare Git in the
parent. Reader Git in the inner chain remains unowned. Neither
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
from . import anomaly_v03_preformal_producer_git_binding as producer_binding
from . import anomaly_v03_preformal_analysis_git as analysis_binding
from . import anomaly_v03_preformal_writer_git as writer_binding
from . import anomaly_v03_reader_evidence as observed
from . import _anomaly_v03_io as io


ROOT = Path(__file__).resolve().parents[2]
FORMAT = 'anomaly-v03-preformal-five-role-parent-owned-git-v1'
CHILD_FORMAT = 'anomaly-v03-preformal-five-role-parent-owned-git-v2'
PRODUCER_FORMAT = 'anomaly-v03-preformal-five-role-parent-owned-git-v3'
ANALYSIS_FORMAT = 'anomaly-v03-preformal-five-role-parent-owned-git-v4'
AUDIT_FORMAT = 'anomaly-v03-preformal-five-role-parent-owned-git-v5'
WRITER_FORMAT = 'anomaly-v03-preformal-five-role-parent-owned-git-v6'
PREFLIGHT_PHASE = preflight.PHASE
PARENT_PHASE = 'parent-source-boundaries'
GIT_SCOPE = 'seven pre-Job and thirty-five parent direct Git calls only'
CHILD_GIT_SCOPE = ('seven pre-Job, thirty-five parent and '
                   'twenty-six child fixed source Git calls only')
PRODUCER_GIT_SCOPE = CHILD_GIT_SCOPE + '; producer direct source/dependency Git included'
ANALYSIS_GIT_SCOPE = PRODUCER_GIT_SCOPE + '; analysis direct source/dependency Git included'
AUDIT_GIT_SCOPE = ANALYSIS_GIT_SCOPE + '; audit direct source/dependency Git included'
WRITER_GIT_SCOPE = AUDIT_GIT_SCOPE + '; publication prelude and writer direct Git included'
MAX_RECEIPT = 24 * 1024
_FIELDS = preflight._FIELDS | {
    'parent_git_root', 'parent_git_manifest_pin', 'parent_git_status',
    'parent_git_call_count', 'parent_v1_git_owned'}
_CHILD_FIELDS = {'child_git_root', 'child_git_manifest_pin',
                 'child_git_status', 'child_git_call_count',
                 'child_fixed_git_owned'}
_PRODUCER_FIELDS = {'producer_git_root', 'producer_git_manifest_pin',
                    'producer_git_status', 'producer_git_call_count',
                    'producer_v1_git_owned'}
_ANALYSIS_FIELDS = {'analysis_git_root', 'analysis_git_manifest_pin',
                    'analysis_git_status', 'analysis_git_call_count',
                    'analysis_v1_git_owned'}
_AUDIT_FIELDS = {'audit_git_root', 'audit_git_manifest_pin',
                 'audit_git_status', 'audit_git_call_count', 'audit_v1_git_owned'}
_WRITER_FIELDS = {'writer_git_root', 'writer_git_manifest_pin',
                  'writer_git_status', 'writer_git_call_count', 'writer_v1_git_owned'}


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


def _child_calls(calls, source):
    expected = _expected_calls(source, 'child-source-')
    for index in range(2):
        expected.extend(_expected_calls(
            source, f'child-chain-source-{index}-')[:-1])
    expected.extend(_expected_calls(source, 'child-boundary-'))
    v.require(type(calls) is list and len(calls) == len(expected) == 26,
              'exact child fixed source Git call count')
    for index, (row, (call_id, operation, path, pin)) in enumerate(
            zip(calls, expected)):
        v.require(type(row) is dict and row['index'] == index and
                  row['call_id'] == call_id and
                  row['operation'] == operation and
                  row['source_path'] == path and
                  row['expected_output_pin'] == pin and
                  row['call_status'] == 'verified' and
                  row['receipt_pin'] is not None and
                  row['reason'] is None and row['error_type'] is None,
                  'child fixed source Git call order and receipt')


def _child_binding(target, receipt, saved_owner):
    invocation = owner._invocation(
        target / 'attempt' / 'invocation.json', saved_owner['invocation_pin'])
    expected = (owner.OWNED_WRITER_INVOCATION if receipt['format'] == WRITER_FORMAT else
                owner.OWNED_AUDIT_INVOCATION if receipt['format'] == AUDIT_FORMAT else
                owner.OWNED_ANALYSIS_INVOCATION if receipt['format'] == ANALYSIS_FORMAT else
                owner.OWNED_PRODUCER_INVOCATION if
                receipt['format'] == PRODUCER_FORMAT else owner.OWNED_GIT_INVOCATION)
    v.require(invocation['format'] == expected and
              invocation['child_git_policy_path'] == receipt['git_policy_path'] and
              invocation['child_git_policy_pin'] == receipt['git_policy_pin'],
              'owned child invocation to outer policy binding')


def _child_manifest(target, receipt):
    checked = source_git.verify_retained(
        target / 'attempt' / 'child-git', receipt['child_git_manifest_pin'],
        policy_path=receipt['git_policy_path'],
        expected_policy_pin=receipt['git_policy_pin'],
        revision=receipt['source_revision'], phase=owner.CHILD_GIT_PHASE)
    v.require(checked['call_status'] == receipt['child_git_status'] and
              checked['call_count'] == receipt['child_git_call_count'] and
              checked['formal_permission'] is False and
              checked['source_closure_complete'] is False and
              checked['runtime_closure_complete'] is False,
              'owned child retained Git manifest scope')
    if checked['call_status'] == 'verified':
        _child_calls(checked['calls'], receipt['source_pins'])
    return checked


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
                 candidate_set_path=None, expected_candidate_set_pin=None,
                 own_child_git=False, own_producer_git=False, own_analysis_git=False,
                 own_audit_git=False, own_writer_git=False):
    """Own parent source Git, optionally including fixed child source calls."""
    v.require(type(expected_mode) is str and expected_mode == 'fixture',
              'only invented five-role mode')
    v.require(type(own_child_git) is bool, 'owned child Git opt-in boolean')
    v.require(type(own_producer_git) is bool, 'owned producer Git opt-in boolean')
    v.require(type(own_analysis_git) is bool, 'owned analysis Git opt-in boolean')
    v.require(type(own_audit_git) is bool, 'owned audit Git opt-in boolean')
    v.require(type(own_writer_git) is bool, 'owned writer Git opt-in boolean')
    own_audit_git = own_audit_git or own_writer_git
    own_analysis_git = own_analysis_git or own_audit_git
    own_producer_git = own_producer_git or own_analysis_git
    own_child_git = own_child_git or own_producer_git
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
    if own_child_git:
        receipt.update(
            format=CHILD_FORMAT, git_scope=CHILD_GIT_SCOPE,
            child_git_root=str(inner_root / 'child-git'),
            child_git_manifest_pin=None, child_git_status=None,
            child_git_call_count=None, child_fixed_git_owned=False)
    if own_producer_git:
        receipt.update(
            format=PRODUCER_FORMAT, git_scope=PRODUCER_GIT_SCOPE,
            producer_git_root=str(inner_root / 'producer-git'),
            producer_git_manifest_pin=None, producer_git_status=None,
            producer_git_call_count=None, producer_v1_git_owned=False)
    if own_analysis_git:
        receipt.update(
            format=ANALYSIS_FORMAT, git_scope=ANALYSIS_GIT_SCOPE,
            analysis_git_root=str(inner_root / 'analysis-git'),
            analysis_git_manifest_pin=None, analysis_git_status=None,
            analysis_git_call_count=None, analysis_v1_git_owned=False)
    if own_audit_git:
        receipt.update(
            format=AUDIT_FORMAT, git_scope=AUDIT_GIT_SCOPE,
            audit_git_root=str(inner_root / 'audit-git'),
            audit_git_manifest_pin=None, audit_git_status=None,
            audit_git_call_count=None, audit_v1_git_owned=False)
    if own_writer_git:
        receipt.update(
            format=WRITER_FORMAT, git_scope=WRITER_GIT_SCOPE,
            writer_git_root=str(inner_root / 'writer-git'),
            writer_git_manifest_pin=None, writer_git_status=None,
            writer_git_call_count=None, writer_v1_git_owned=False)
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
                    git_reader=parent_reader,
                    **({'child_git_policy_path': policy_path,
                        'expected_child_git_policy_pin': expected_git_policy_pin}
                       if own_child_git else {}),
                    **({'own_producer_git': True} if own_producer_git else {}),
                    **({'own_analysis_git': True} if own_analysis_git else {}),
                    **({'own_audit_git': True} if own_audit_git else {}),
                    **({'own_writer_git': True} if own_writer_git else {}))
                receipt['owner_receipt_pin'] = copy.deepcopy(inner['receipt_pin'])
                receipt['owner_status'] = inner['status']
                v.require(inner['status'] in ('verified', 'failed') and
                          inner['check_directory'] == str(inner_root),
                          'owned parent five-role result binding')
                saved_owner = preflight._owner_receipt(
                    inner_root, inner['receipt_pin'])
                preflight._owner_binding(receipt, saved_owner, inner_root)
                if own_child_git and 'invocation_pin' in saved_owner:
                    _child_binding(target, receipt, saved_owner)
                    manifest_path = inner_root / 'child-git' / 'manifest.json'
                    if manifest_path.exists():
                        raw = observed._file(manifest_path, source_git.MAX_MANIFEST)
                        manifest = v.strict_json(raw)
                        receipt.update(
                            child_git_manifest_pin=observed._pin(raw),
                            child_git_status=manifest['status'],
                            child_git_call_count=manifest['call_count'])
                        _child_manifest(target, receipt)
                    if own_producer_git:
                        manifest_path = inner_root / 'producer-git' / 'manifest.json'
                        if manifest_path.exists():
                            raw = observed._file(manifest_path, source_git.MAX_MANIFEST)
                            manifest = v.strict_json(raw)
                            receipt.update(
                                producer_git_manifest_pin=observed._pin(raw),
                                producer_git_status=manifest['status'],
                                producer_git_call_count=manifest['call_count'])
                            producer_binding.verify_manifest(
                                target, receipt, saved_owner, phase=owner.PRODUCER_GIT_PHASE)
                    if own_analysis_git:
                        manifest_path = inner_root / 'analysis-git' / 'manifest.json'
                        if manifest_path.exists():
                            raw = observed._file(manifest_path, source_git.MAX_MANIFEST)
                            manifest = v.strict_json(raw)
                            receipt.update(
                                analysis_git_manifest_pin=observed._pin(raw),
                                analysis_git_status=manifest['status'],
                                analysis_git_call_count=manifest['call_count'])
                            analysis_binding.verify_manifest(
                                target, receipt, saved_owner, phase=owner.ANALYSIS_GIT_PHASE)
                    if own_audit_git:
                        manifest_path = inner_root / 'audit-git' / 'manifest.json'
                        if manifest_path.exists():
                            raw = observed._file(manifest_path, source_git.MAX_MANIFEST)
                            manifest = v.strict_json(raw)
                            receipt.update(
                                audit_git_manifest_pin=observed._pin(raw),
                                audit_git_status=manifest['status'],
                                audit_git_call_count=manifest['call_count'])
                            analysis_binding.verify_manifest(
                                target, receipt, saved_owner, phase=owner.AUDIT_GIT_PHASE,
                                role='audit')
                    if own_writer_git:
                        manifest_path = inner_root / 'writer-git' / 'manifest.json'
                        if manifest_path.exists():
                            raw = observed._file(manifest_path, source_git.MAX_MANIFEST)
                            manifest = v.strict_json(raw)
                            receipt.update(
                                writer_git_manifest_pin=observed._pin(raw),
                                writer_git_status=manifest['status'],
                                writer_git_call_count=manifest['call_count'])
                            writer_binding.verify_manifest(
                                target, receipt, saved_owner, phase=owner.WRITER_GIT_PHASE)
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
            if own_child_git:
                v.require(receipt['child_git_status'] == 'verified' and
                          receipt['child_git_call_count'] == 26,
                          'owned child fixed Git manifest required')
            if own_producer_git:
                v.require(receipt['producer_git_status'] == 'verified' and
                          receipt['producer_git_manifest_pin'] is not None,
                          'owned producer Git manifest required')
            if own_analysis_git:
                v.require(receipt['analysis_git_status'] == 'verified' and
                          receipt['analysis_git_manifest_pin'] is not None,
                          'owned analysis Git manifest required')
            if own_audit_git:
                v.require(receipt['audit_git_status'] == 'verified' and
                          receipt['audit_git_manifest_pin'] is not None,
                          'owned audit Git manifest required')
            if own_writer_git:
                v.require(receipt['writer_git_status'] == 'verified' and
                          receipt['writer_git_manifest_pin'] is not None,
                          'owned writer Git manifest required')
            receipt.update(status='verified', reason=None,
                           parent_v1_git_owned=True)
            if own_child_git:
                receipt['child_fixed_git_owned'] = True
            if own_producer_git:
                receipt['producer_v1_git_owned'] = True
            if own_analysis_git:
                receipt['analysis_v1_git_owned'] = True
            if own_audit_git:
                receipt['audit_v1_git_owned'] = True
            if own_writer_git:
                receipt['writer_v1_git_owned'] = True
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
    own_writer_git = type(receipt) is dict and receipt.get('format') == WRITER_FORMAT
    own_audit_git = type(receipt) is dict and receipt.get('format') in (AUDIT_FORMAT, WRITER_FORMAT)
    own_analysis_git = type(receipt) is dict and receipt.get('format') in (ANALYSIS_FORMAT, AUDIT_FORMAT, WRITER_FORMAT)
    own_producer_git = type(receipt) is dict and receipt.get('format') in (PRODUCER_FORMAT, ANALYSIS_FORMAT, AUDIT_FORMAT, WRITER_FORMAT)
    own_child_git = type(receipt) is dict and receipt.get('format') in (CHILD_FORMAT, PRODUCER_FORMAT, ANALYSIS_FORMAT, AUDIT_FORMAT, WRITER_FORMAT)
    fields = _FIELDS | _CHILD_FIELDS if own_child_git else _FIELDS
    if own_producer_git:
        fields |= _PRODUCER_FIELDS
    if own_analysis_git:
        fields |= _ANALYSIS_FIELDS
    if own_audit_git:
        fields |= _AUDIT_FIELDS
    if own_writer_git:
        fields |= _WRITER_FIELDS
    scope = (WRITER_GIT_SCOPE if own_writer_git else
             AUDIT_GIT_SCOPE if own_audit_git else
             ANALYSIS_GIT_SCOPE if own_analysis_git else
             PRODUCER_GIT_SCOPE if own_producer_git else
             CHILD_GIT_SCOPE if own_child_git else GIT_SCOPE)
    v.require(type(receipt) is dict and set(receipt) == fields and
              receipt['format'] in (FORMAT, CHILD_FORMAT, PRODUCER_FORMAT, ANALYSIS_FORMAT, AUDIT_FORMAT, WRITER_FORMAT) and
              receipt['mode'] == 'fixture' and
              receipt['root'] == str(target) and
              receipt['source_git_root'] == str(target / 'git') and
              receipt['parent_git_root'] == str(target / 'parent-git') and
              receipt['owner_root'] == str(target / 'attempt') and
              receipt['git_scope'] == scope and
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
        if own_child_git and 'invocation_pin' in saved_owner:
            _child_binding(target, receipt, saved_owner)
    if own_child_git:
        v.require(receipt['child_git_root'] ==
                  str(target / 'attempt' / 'child-git') and
                  type(receipt['child_fixed_git_owned']) is bool and
                  receipt['child_fixed_git_owned'] ==
                  (receipt['status'] == 'verified'),
                  'retained owned child Git scope')
        child_pin = receipt['child_git_manifest_pin']
        if child_pin is None:
            v.require(receipt['child_git_status'] is None and
                      receipt['child_git_call_count'] is None and
                      receipt['status'] != 'verified',
                      'absent child Git manifest fields')
        else:
            v.require(owner_pin is not None,
                      'child Git manifest requires bound owner invocation')
            evidence._pin(child_pin)
            _child_manifest(target, receipt)
        if receipt['status'] == 'verified':
            v.require(receipt['child_git_status'] == 'verified' and
                      receipt['child_git_call_count'] == 26,
                      'retained child fixed source Git prerequisites')
    if own_producer_git:
        v.require(receipt['producer_git_root'] ==
                  str(target / 'attempt' / 'producer-git') and
                  type(receipt['producer_v1_git_owned']) is bool and
                  receipt['producer_v1_git_owned'] == (receipt['status'] == 'verified'),
                  'retained producer owned Git scope')
        producer_pin = receipt['producer_git_manifest_pin']
        if producer_pin is None:
            v.require(receipt['producer_git_status'] is None and
                      receipt['producer_git_call_count'] is None and
                      receipt['status'] != 'verified',
                      'absent producer Git manifest fields')
        else:
            v.require(owner_pin is not None and 'invocation_pin' in saved_owner,
                      'producer Git manifest requires bound owner invocation')
            producer_binding.verify_manifest(
                target, receipt, saved_owner, phase=owner.PRODUCER_GIT_PHASE)
    if own_analysis_git:
        v.require(receipt['analysis_git_root'] == str(target / 'attempt' / 'analysis-git') and
                  type(receipt['analysis_v1_git_owned']) is bool and
                  receipt['analysis_v1_git_owned'] == (receipt['status'] == 'verified'),
                  'retained analysis owned Git scope')
        if receipt['analysis_git_manifest_pin'] is None:
            v.require(receipt['analysis_git_status'] is None and
                      receipt['analysis_git_call_count'] is None and receipt['status'] != 'verified',
                      'absent analysis Git manifest fields')
        else:
            v.require(owner_pin is not None and 'invocation_pin' in saved_owner,
                      'analysis Git manifest requires bound owner invocation')
            analysis_binding.verify_manifest(
                target, receipt, saved_owner, phase=owner.ANALYSIS_GIT_PHASE)
    if own_audit_git:
        v.require(receipt['audit_git_root'] == str(target / 'attempt' / 'audit-git') and
                  type(receipt['audit_v1_git_owned']) is bool and
                  receipt['audit_v1_git_owned'] == (receipt['status'] == 'verified'),
                  'retained audit owned Git scope')
        if receipt['audit_git_manifest_pin'] is None:
            v.require(receipt['audit_git_status'] is None and
                      receipt['audit_git_call_count'] is None and receipt['status'] != 'verified',
                      'absent audit Git manifest fields')
        else:
            v.require(owner_pin is not None and 'invocation_pin' in saved_owner,
                      'audit Git manifest requires bound owner invocation')
            analysis_binding.verify_manifest(
                target, receipt, saved_owner, phase=owner.AUDIT_GIT_PHASE, role='audit')
    if own_writer_git:
        v.require(receipt['writer_git_root'] == str(target/'attempt/writer-git') and
                  type(receipt['writer_v1_git_owned']) is bool and
                  receipt['writer_v1_git_owned'] == (receipt['status'] == 'verified'),
                  'retained writer owned Git scope')
        if receipt['writer_git_manifest_pin'] is None:
            v.require(receipt['writer_git_status'] is None and
                      receipt['writer_git_call_count'] is None and receipt['status'] != 'verified',
                      'absent writer Git manifest fields')
        else:
            v.require(owner_pin is not None and 'invocation_pin' in saved_owner,
                      'writer Git manifest requires bound owner invocation')
            writer_binding.verify_manifest(
                target, receipt, saved_owner, phase=owner.WRITER_GIT_PHASE)
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
            'execution_authenticated': False,
            **({'child_git_call_count': receipt['child_git_call_count'],
                'child_fixed_git_owned': receipt['child_fixed_git_owned']}
               if own_child_git else {}),
            **({'producer_git_call_count': receipt['producer_git_call_count'],
                'producer_v1_git_owned': receipt['producer_v1_git_owned']}
               if own_producer_git else {}),
            **({'analysis_git_call_count': receipt['analysis_git_call_count'],
                'analysis_v1_git_owned': receipt['analysis_v1_git_owned']}
               if own_analysis_git else {}),
            **({'audit_git_call_count': receipt['audit_git_call_count'],
                'audit_v1_git_owned': receipt['audit_v1_git_owned']}
               if own_audit_git else {}),
            **({'writer_git_call_count': receipt['writer_git_call_count'],
                'writer_v1_git_owned': receipt['writer_v1_git_owned']}
               if own_writer_git else {})}
