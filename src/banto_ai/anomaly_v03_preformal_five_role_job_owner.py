"""Job-owned entry for one invented five-role fixture attempt.

The older direct entry remains available, but its receipts are never Job-owned
evidence.  This owner authenticates only members of its private Windows Job;
it does not attest processes outside the Job, individual descendant exit
codes, in-memory code, or complete source/runtime closure.
"""
from __future__ import annotations

import copy
from contextlib import ExitStack
import os
from pathlib import Path
import secrets
import subprocess
import sys

from . import anomaly_v03 as v
from . import anomaly_v03_platform_five_role_fixture as chain
from . import anomaly_v03_platform_fixture_runtime as runtime
from . import anomaly_v03_preformal_job_tree_owner as job_owner
from . import anomaly_v03_preformal_role_profiles as profiles
from . import anomaly_v03_reader_evidence as observed
from . import _anomaly_v03_io as io


ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'src/banto_ai/anomaly_v03_preformal_five_role_job_owner.py'
FORMAT = 'anomaly-v03-preformal-five-role-job-owner-v1'
INVOCATION = 'anomaly-v03-preformal-five-role-job-invocation-v1'
OWNED_GIT_INVOCATION = 'anomaly-v03-preformal-five-role-job-invocation-v2'
OWNED_PRODUCER_INVOCATION = 'anomaly-v03-preformal-five-role-job-invocation-v3'
OWNED_ANALYSIS_INVOCATION = 'anomaly-v03-preformal-five-role-job-invocation-v4'
OWNED_AUDIT_INVOCATION = 'anomaly-v03-preformal-five-role-job-invocation-v5'
OWNED_INVOCATIONS = (OWNED_GIT_INVOCATION, OWNED_PRODUCER_INVOCATION,
                     OWNED_ANALYSIS_INVOCATION, OWNED_AUDIT_INVOCATION)
CHILD_GIT_PHASE = 'child-fixed-source-boundaries'
PRODUCER_GIT_PHASE = 'producer-source-and-dependencies'
ANALYSIS_GIT_PHASE = 'analysis-source-and-dependencies'
AUDIT_GIT_PHASE = 'audit-source-and-dependencies'
BOOTSTRAP = ('import sys;sys.path.insert(0,sys.argv.pop(1));'
             'from banto_ai.anomaly_v03_preformal_five_role_job_owner import child_main;'
             'raise SystemExit(child_main(sys.argv[1:]))')
LIMITS = {'wall_seconds': 300, 'private_bytes': 512 * 1024**2,
          'output_bytes': 1024**2}
MAX_INVOCATION = 16 * 1024
MAX_RECEIPT = 64 * 1024


def _same(actual, expected, label):
    chain.evidence._same(actual, expected, label)


def _pinned(path, pin, maximum):
    chain.evidence._pin(pin)
    raw = observed._file(path, maximum)
    chain.evidence._raw(raw, pin, str(path) + ' raw pin')
    return raw


def _source(revision, *, git_reader=None, git_call_prefix=''):
    """Check a clean HEAD and selected working raw, without claiming closure."""
    selected = chain._git_sources(revision, git_reader=git_reader,
                                  git_call_prefix=git_call_prefix)
    raw = observed._file(ROOT / SOURCE, 1024**2)
    committed = (subprocess.check_output(
        ['git', '-C', str(ROOT), 'show', revision + ':' + SOURCE],
        stderr=subprocess.DEVNULL, timeout=10)
        if git_reader is None else git_reader.run(
            call_id=git_call_prefix + 'owner-source', operation='source_blob',
            source_path=SOURCE, expected_output_pin=observed._pin(raw)))
    v.require(raw == committed, 'five-role Job owner source/Git bytes')
    return {'revision': revision, 'orchestrator_selected': selected,
            'owner': observed._pin(raw),
            'scope': 'clean-head-selected-working-raw-not-source-closure'}


def _inputs(join_root, join_pin, revision, candidate_path, candidate_pin):
    archive_path, archive_pin, bound_pin, lineage = chain._external_archive(
        join_root, join_pin)
    candidates = None
    profile_pins = None
    if candidate_path is not None:
        candidates = profiles.load_pinned_candidate_set(
            candidate_path, candidate_pin, revision=revision)
        profile_pins = {role: copy.deepcopy(candidates[role]['pin'])
                        for role in profiles.ROLES}
        _pinned(candidate_path, candidate_pin, profiles.MAX_RESULT)
        for role in profiles.ROLES:
            _pinned(candidates[role]['path'], candidates[role]['pin'],
                    profiles.MAX_PROFILE)
    return {'archive_path': str(archive_path), 'archive_pin': archive_pin,
            'bound_pin': bound_pin, 'join_lineage': lineage,
            'candidate_set_pin': copy.deepcopy(candidate_pin),
            'profile_pins': profile_pins}


def _invocation(path, expected_pin):
    raw = _pinned(path, expected_pin, MAX_INVOCATION)
    value = v.strict_json(raw)
    fields = ('format mode source_revision join_root '
                         'join_receipt_pin archive_pin bound_pin '
                         'candidate_set_path candidate_set_pin profile_pins '
                         'result_root invocation_id')
    if type(value) is dict and value.get('format') in OWNED_INVOCATIONS:
        fields += ' child_git_policy_path child_git_policy_pin'
    chain.evidence._keys(value, fields, 'five-role Job invocation')
    v.require(value['format'] in (INVOCATION, *OWNED_INVOCATIONS) and
              value['mode'] == 'fixture' and
              Path(value['result_root']) == Path(path).parent / 'five-role' and
              type(value['invocation_id']) is str and
              len(value['invocation_id']) == 64,
              'five-role Job invocation identity')
    if value['format'] in OWNED_INVOCATIONS:
        _child_policy(value, Path(path).parent, check_current=False)
    return value


def _child_policy(invocation, target, *, check_current=True):
    from . import anomaly_v03_preformal_owned_source_git_session as source_git
    policy_path = Path(invocation['child_git_policy_path'])
    v.require(invocation['candidate_set_path'] is None and
              invocation['candidate_set_pin'] is None and
              not policy_path.is_relative_to(Path(invocation['join_root'])),
              'owned child Git excludes candidate profiles and join policy')
    return source_git._policy(
        policy_path, invocation['child_git_policy_pin'],
        invocation['source_revision'], target / 'child-git',
        check_current=check_current)


def _boundary(path, pin, expected_source, expected_inputs, *,
              git_reader=None, git_call_prefix=''):
    invocation = _invocation(path, pin)
    if invocation['format'] in OWNED_INVOCATIONS:
        _child_policy(invocation, Path(path).parent)
    _same(_source(invocation['source_revision'], git_reader=git_reader,
                  git_call_prefix=git_call_prefix), expected_source,
          'five-role Job source changed')
    inputs = _inputs(invocation['join_root'], invocation['join_receipt_pin'],
                     invocation['source_revision'],
                     invocation['candidate_set_path'],
                     invocation['candidate_set_pin'])
    _same(inputs, expected_inputs, 'five-role Job inputs changed')
    v.require(not (Path(invocation['result_root']).is_relative_to(
        Path(invocation['join_root']))), 'output overlaps invented join')


def child_main(argv=None):
    """Run the existing direct chain inside the owner's already assigned Job."""
    argv = sys.argv[1:] if argv is None else argv
    v.require(len(argv) == 3, 'five-role Job child arguments')
    path = Path(argv[0])
    pin = {'bytes': int(argv[1]), 'sha256': argv[2]}
    invocation = _invocation(path, pin)
    v.require(path.name == 'invocation.json' and path.is_absolute() and
              path.parent.is_relative_to(ROOT / 'artifacts'),
              'five-role Job invocation path')
    if invocation['format'] in OWNED_INVOCATIONS:
        from . import anomaly_v03_preformal_owned_source_git_session as source_git
        with ExitStack() as stack:
            reader = stack.enter_context(source_git.OwnedSourceGitSession(
                policy_path=Path(invocation['child_git_policy_path']),
                expected_policy_pin=invocation['child_git_policy_pin'],
                revision=invocation['source_revision'],
                receipt_root=path.parent / 'child-git',
                phase=CHILD_GIT_PHASE))
            producer_reader = None
            if invocation['format'] in (OWNED_PRODUCER_INVOCATION, OWNED_ANALYSIS_INVOCATION,
                                        OWNED_AUDIT_INVOCATION):
                producer_reader = stack.enter_context(source_git.OwnedSourceGitSession(
                    policy_path=Path(invocation['child_git_policy_path']),
                    expected_policy_pin=invocation['child_git_policy_pin'],
                    revision=invocation['source_revision'],
                    receipt_root=path.parent / 'producer-git',
                    phase=PRODUCER_GIT_PHASE))
            options = ({} if producer_reader is None else
                       {'producer_git_reader': producer_reader})
            analysis_reader = None
            if invocation['format'] in (OWNED_ANALYSIS_INVOCATION, OWNED_AUDIT_INVOCATION):
                analysis_reader = stack.enter_context(source_git.OwnedSourceGitSession(
                    policy_path=Path(invocation['child_git_policy_path']),
                    expected_policy_pin=invocation['child_git_policy_pin'],
                    revision=invocation['source_revision'],
                    receipt_root=path.parent / 'analysis-git',
                    phase=ANALYSIS_GIT_PHASE))
                options['analysis_git_reader'] = analysis_reader
            audit_reader = None
            if invocation['format'] == OWNED_AUDIT_INVOCATION:
                audit_reader = stack.enter_context(source_git.OwnedSourceGitSession(
                    policy_path=Path(invocation['child_git_policy_path']),
                    expected_policy_pin=invocation['child_git_policy_pin'],
                    revision=invocation['source_revision'],
                    receipt_root=path.parent / 'audit-git',
                    phase=AUDIT_GIT_PHASE))
                options['audit_git_reader'] = audit_reader
            value = _run_child(path, pin, invocation, git_reader=reader, **options)
        v.require(reader.manifest_result['status'] == 'verified' and
                  reader.manifest_result['call_count'] == 26,
                  'owned child fixed Git calls incomplete')
        if producer_reader is not None:
            v.require(producer_reader.manifest_result['status'] == 'verified',
                      'owned producer Git calls incomplete')
        if analysis_reader is not None:
            v.require(analysis_reader.manifest_result['status'] == 'verified',
                      'owned analysis Git calls incomplete')
        if audit_reader is not None:
            v.require(audit_reader.manifest_result['status'] == 'verified',
                      'owned audit Git calls incomplete')
    else:
        value = _run_child(path, pin, invocation)
    print(io.json_bytes({'status': value['status'],
                         'result_pin': value['result_pin'],
                         'check_directory': value['check_directory']}).decode(),
          end='')
    return 0 if value['status'] == 'verified' else 2


def _run_child(path, pin, invocation, *, git_reader=None, producer_git_reader=None,
               analysis_git_reader=None, audit_git_reader=None):
    source = _source(
        invocation['source_revision'], git_reader=git_reader,
        git_call_prefix='' if git_reader is None else 'child-source-')
    inputs = _inputs(invocation['join_root'], invocation['join_receipt_pin'],
                     invocation['source_revision'],
                     invocation['candidate_set_path'],
                     invocation['candidate_set_pin'])
    _same(inputs['archive_pin'], invocation['archive_pin'], 'child archive pin')
    _same(inputs['bound_pin'], invocation['bound_pin'], 'child bound pin')
    _same(inputs['profile_pins'], invocation['profile_pins'], 'child profile pins')
    value = chain.run_chain(
        expected_mode='fixture', join_root=invocation['join_root'],
        expected_join_receipt_pin=invocation['join_receipt_pin'],
        expected_revision=invocation['source_revision'],
        receipt_parent=path.parent, receipt_name='five-role',
        candidate_set_path=invocation['candidate_set_path'],
        expected_candidate_set_pin=invocation['candidate_set_pin'],
        git_reader=git_reader, producer_git_reader=producer_git_reader,
        analysis_git_reader=analysis_git_reader, audit_git_reader=audit_git_reader)
    _boundary(path, pin, source, inputs, git_reader=git_reader,
              git_call_prefix='' if git_reader is None else 'child-boundary-')
    return value


def _job_complete(report, argv, launch):
    job = report['job']
    v.require(report['format'] == 'anomaly-v03-owned-process-monitor-v1' and
              report['limits'] == LIMITS and
              report['formal_permission'] is False and
              report['performance_status'] == 'not_evaluated' and
              len(argv) == 10 and argv[:7] ==
              [sys.executable, '-I', '-S', '-B', '-c', BOOTSTRAP,
               str(ROOT / 'src')] and
              report['status'] == 'complete' and report['exit_code'] == 0 and
              report['worker_exit_confirmed'] is True and
              report['worker_pid'] == launch['pid'] and
              report['argv'] == argv and
              report['stop_reason'] is None and
              not report['observation_errors'] and
              report['runtime_before'] == report['runtime_after'] and
              report['output'] is not None and
              report['stderr'] is not None and report['stderr']['bytes'] == 0 and
              job['format'] == 'anomaly-v03-preformal-owned-cli-job-v1' and
              job['assignment_confirmed'] is True and
              job['root_resumed'] is True and
              job['accounting']['active_processes'] == 0 and
              job['accounting']['total_processes'] >= 6 and
              job['all_assigned_processes_exit_confirmed'] is True and
              job['individual_descendant_exit_codes_authenticated'] is False and
              job['whole_tree_resource_budget_measured'] is False and
              job_owner.valid_job_memory(job['memory']),
              'five-role CLI or Job did not complete')


def _inner(target, report, launch, invocation):
    """Reopen the five saved role results and evidence after Job empty."""
    inner = target / 'five-role'
    raw = _pinned(target / 'job' / 'report.json', report['output'],
                  LIMITS['output_bytes'])
    child = v.strict_json(raw)
    chain.evidence._keys(child, 'status result_pin check_directory',
                         'five-role Job child response')
    v.require(child['status'] == 'verified' and
              child['check_directory'] == str(inner),
              'five-role Job child result')
    top = v.strict_json(_pinned(inner / 'result.json', child['result_pin'],
                                MAX_RECEIPT))
    for key, expected in chain.four.publication.CLOSED.items():
        _same(top[key], expected, 'five-role top closed scope ' + key)
    v.require(top['format'] == chain.FORMAT and top['status'] == 'verified' and
              top['scope'] == 'invented-26h2-five-owned-role-trial' and
              top['platform_contract_status'] == 'proposal-not-accepted' and
              top['stage'] == 'complete' and
              top['source_revision'] == invocation['source_revision'] and
              top['combined_resource_budget_measured'] is True and
              top['combined_resource_budget_passed'] is True and
              top['five_role_budget_closure_passed'] is True and
              top['resource_budget_scope'] ==
              'one sampled outer root plus shared cooperative child stop' and
              top['owned_producer_join_executed'] is True and
              top['source_closure_complete'] is False and
              top['runtime_closure_complete'] is False and
              top['formal_permission'] is False and
              top['registered_data_read'] is False and
              top['real_producer_executed'] is False and
              top['registered_saved_reader_used'] is False and
              type(top['new_evaluations']) is int and
              top['new_evaluations'] == 0 and
              top['profile_required'] is
              (invocation['candidate_set_pin'] is not None) and
              top['before_work_profile_enforcement'] is
              (invocation['candidate_set_pin'] is not None),
              'five-role saved top scope/completion')
    chain._check_five_identities(top)
    if invocation['candidate_set_pin'] is not None:
        _same(top['candidate_profile_set_pin'],
              invocation['candidate_set_pin'], 'five-role candidate set binding')
    else:
        v.require('candidate_profile_set_pin' not in top,
                  'unrequested five-role profile binding')
    budget = v.strict_json(_pinned(inner / 'resource-budget.json',
                                   top['resource_budget_pin'], MAX_RECEIPT))
    v.require(budget['format'] == chain.chain_budget.FORMAT and
              budget['scope'] == 'invented-preformal-five-role-engineering-fixture' and
              budget['root'] == str(inner) and
              budget['limits'] == chain.chain_budget.DEFAULTS and
              budget['publication_roots'] ==
              [str(inner / 'publication' / 'published')] and
              budget['sampler_exit_confirmed'] is True and
              budget['stop_reason'] is None and
              budget['observation_error'] is None and
              budget['formal_permission'] is False and
              budget['registered_data_read'] is False and
              budget['independent_s6_complete'] is False and
              budget['formal_50000_draw_budget_measured'] is False and
              budget['passed'] is True and
              budget['caller_reported_all_five_exits'] is True and
              type(budget['caller_reported_roles']) is dict and
              set(budget['caller_reported_roles']) == set(profiles.ROLES),
              'five-role saved shared budget')
    publication = v.strict_json(_pinned(
        inner / 'publication' / 'result.json',
        top['publication']['result_pin'], MAX_RECEIPT))
    v.require(top['publication']['status'] == 'verified' and
              publication['status'] == 'verified' and
              top['publication']['publication_status'] ==
              publication['publication_status'] and
              top['publication']['reader_status'] ==
              publication['reader_status'] and
              publication['publication_status'] == 'completed' and
              publication['reader_status'] == 'completed',
              'five-role saved publication result')
    role_paths = profiles.ROLE_PATHS
    for role in profiles.ROLES:
        role_root = inner / role_paths[role]
        if role in ('producer', 'analysis', 'audit'):
            role_pin = top[role]['result_pin']
            row = v.strict_json(_pinned(role_root / 'result.json', role_pin,
                                        MAX_RECEIPT))
        else:
            row = publication[role]
            role_pin = observed._pin(io.json_bytes(row))
            v.require(_pinned(role_root / 'result.json',
                              role_pin, MAX_RECEIPT)
                      == io.json_bytes(row),
                      role + ' saved publication result')
        v.require(row['status'] == 'verified' and
                  row['worker_exit_confirmed'] is True and
                  row['worker_pid'] == top['identities'][role]['pid'],
                  role + ' saved result/identity')
        if role in ('producer', 'analysis', 'audit'):
            v.require(top[role]['status'] == row['status'],
                      role + ' saved top/result status')
        budget_role = budget['caller_reported_roles'][role]
        v.require(type(budget_role) is dict and
                  budget_role['status'] == 'verified' and
                  budget_role['worker_exit_confirmed'] is True and
                  budget_role['worker_pid'] == row['worker_pid'] and
                  budget_role['result_pin'] == role_pin,
                  role + ' saved budget/result binding')
        if invocation['candidate_set_pin'] is not None:
            _same(row['dependency_profile_pin'],
                  invocation['profile_pins'][role], role + ' profile pin')
            v.require(row['before_work_profile_enforcement'] is True,
                      role + ' profile before work')
        if role == 'producer':
            identity = chain._producer_identity(role_root, {
                **row, 'result_pin': top['producer']['result_pin']})
            worker = v.strict_json(_pinned(role_root / 'worker' / 'report.json',
                                           row['stdout_pin'], LIMITS['output_bytes']))
            parent_pid = worker['process']['parent_pid']
        else:
            identity = chain.four._role_identity(
                role_root, role, top['identities'][role]['evidence_pin'])
            evidence = v.strict_json(_pinned(
                role_root / 'evidence.json', identity['evidence_pin'],
                MAX_RECEIPT))
            parent_pid = evidence['process']['parent_pid']
        _same(identity, top['identities'][role], role + ' saved identity')
        v.require(parent_pid == launch['pid'], role + ' outer CLI parent PID')
    return {'inner_result_pin': child['result_pin'],
            'identities': copy.deepcopy(top['identities']),
            'resource_budget_pin': copy.deepcopy(top['resource_budget_pin'])}


def _receipt(target, value):
    raw = io.json_bytes(value)
    v.require(len(raw) <= MAX_RECEIPT, 'five-role Job receipt byte limit')
    io._exclusive(target / 'receipt.json', raw)
    v.require(_pinned(target / 'receipt.json', observed._pin(raw),
                      MAX_RECEIPT) == raw,
              'five-role Job saved receipt')
    return {**value, 'check_directory': str(target),
            'receipt_pin': observed._pin(raw)}


def _job_exception_summary(error):
    """Retain bounded, handle-free facts; native handles stay on the exception."""
    report = error.report if type(error.report) is dict else {}
    summary = {'error_type': type(error).__name__}
    for key in ('status', 'phase', 'stop_reason', 'root_pid',
                'root_exit_code', 'formal_permission'):
        value = report.get(key)
        if value is None or type(value) in (bool, int) or \
                (type(value) is str and len(value) <= 80):
            summary[key] = value
    accounting = report.get('job_accounting')
    if accounting is None and type(report.get('job')) is dict:
        accounting = report['job'].get('accounting')
    if type(accounting) is dict and set(accounting) == {
            'total_processes', 'active_processes',
            'limit_terminated_processes'} and all(
                type(number) is int and number >= 0
                for number in accounting.values()):
        summary['job_accounting'] = dict(accounting)
    return summary


def run_owned(*, expected_mode, join_root, expected_join_receipt_pin,
              expected_revision, receipt_parent, receipt_name,
              candidate_set_path=None, expected_candidate_set_pin=None,
              git_reader=None, child_git_policy_path=None,
              expected_child_git_policy_pin=None, own_producer_git=False,
              own_analysis_git=False, own_audit_git=False):
    """Launch one invented five-role parent CLI in a new private Windows Job."""
    v.require(expected_mode == 'fixture' and type(expected_mode) is str,
              'only invented five-role mode is open')
    v.require(type(own_producer_git) is bool and
              (not own_producer_git or child_git_policy_path is not None),
              'owned producer Git requires owned child policy')
    v.require(type(own_analysis_git) is bool and
              (not own_analysis_git or (own_producer_git and child_git_policy_path is not None)),
              'owned analysis Git requires producer and child policy')
    v.require(type(own_audit_git) is bool and
              (not own_audit_git or (own_analysis_git and own_producer_git and
                                     child_git_policy_path is not None)),
              'owned audit Git requires analysis, producer and child policy')
    chain.evidence._digest(expected_revision, 40)
    chain.evidence._pin(expected_join_receipt_pin)
    v.require((candidate_set_path is None) ==
              (expected_candidate_set_pin is None),
              'candidate set path/pin pair')
    if expected_candidate_set_pin is not None:
        chain.evidence._pin(expected_candidate_set_pin)
    v.require((child_git_policy_path is None) ==
              (expected_child_git_policy_pin is None),
              'owned child Git policy path/pin pair')
    if child_git_policy_path is not None:
        chain.evidence._pin(expected_child_git_policy_pin)
        v.require(candidate_set_path is None,
                  'owned child Git excludes candidate profiles')
    v.safe_relative_path(receipt_name)
    v.require('/' not in receipt_name and '\\' not in receipt_name and
              receipt_name not in ('five-role', 'job'), 'new owner receipt name')
    parent = Path(receipt_parent)
    v.require(parent.is_absolute() and
              parent.is_relative_to(ROOT / 'artifacts'),
              'owner parent under local artifacts')
    io.regular_path(parent, directory=True, missing=True)
    parent.mkdir(exist_ok=True)
    parent = io._local_parent(parent)
    target = io.regular_path(parent / receipt_name, directory=True,
                             missing=True)
    v.require(not target.is_relative_to(Path(join_root)) and
              not Path(join_root).is_relative_to(target),
              'owner result/input overlap')
    target.mkdir()
    value = {**chain.four.publication.CLOSED,
             'format': FORMAT, 'mode': 'fixture', 'status': 'failed',
             'reason': 'preflight_rejected', 'source_revision': expected_revision,
             'join_root': str(join_root),
             'join_receipt_pin': copy.deepcopy(expected_join_receipt_pin),
             'candidate_set_pin': copy.deepcopy(expected_candidate_set_pin),
             'profile_required': candidate_set_path is not None,
             'invented_only': True, 'registered_data_read': False,
             'registered_saved_reader_used': False,
             'new_evaluations': 0,
             'real_producer_executed': False, 'formal_permission': False,
             'source_closure_complete': False,
             'runtime_closure_complete': False,
             'execution_authenticated': False,
             'job_outside_processes_authenticated': False,
             'individual_descendant_exit_codes_authenticated': False,
             'all_job_processes_exit_confirmed': False,
             'retry_authorized': False, 'next_stage_authorized': False}
    critical = None
    report = None
    launch = {}
    source_read_index = 0

    def source_prefix():
        nonlocal source_read_index
        if git_reader is None:
            return ''
        prefix = f'parent-source-{source_read_index}-'
        source_read_index += 1
        return prefix

    try:
        source = _source(expected_revision, git_reader=git_reader,
                         git_call_prefix=source_prefix())
        inputs = _inputs(join_root, expected_join_receipt_pin,
                         expected_revision, candidate_set_path,
                         expected_candidate_set_pin)
        value['source_pins'] = source
        value['input_binding'] = inputs
        invocation = {'format': INVOCATION, 'mode': 'fixture',
                      'source_revision': expected_revision,
                      'join_root': str(join_root),
                      'join_receipt_pin': copy.deepcopy(expected_join_receipt_pin),
                      'archive_pin': inputs['archive_pin'],
                      'bound_pin': inputs['bound_pin'],
                      'candidate_set_path': (None if candidate_set_path is None
                                             else str(candidate_set_path)),
                      'candidate_set_pin': copy.deepcopy(expected_candidate_set_pin),
                      'profile_pins': inputs['profile_pins'],
                      'result_root': str(target / 'five-role'),
                      'invocation_id': secrets.token_hex(32)}
        if child_git_policy_path is not None:
            invocation.update(
                format=(OWNED_AUDIT_INVOCATION if own_audit_git else
                        OWNED_ANALYSIS_INVOCATION if own_analysis_git else
                        OWNED_PRODUCER_INVOCATION if own_producer_git else
                        OWNED_GIT_INVOCATION),
                child_git_policy_path=str(child_git_policy_path),
                child_git_policy_pin=copy.deepcopy(expected_child_git_policy_pin))
        invocation_raw = v.canonical_json(invocation)
        v.require(len(invocation_raw) <= MAX_INVOCATION,
                  'five-role Job invocation byte limit')
        invocation_path = target / 'invocation.json'
        io._exclusive(invocation_path, invocation_raw)
        invocation_pin = observed._pin(invocation_raw)
        _same(_invocation(invocation_path, invocation_pin), invocation,
              'saved five-role Job invocation')
        argv = [sys.executable, '-I', '-S', '-B', '-c', BOOTSTRAP,
                str(ROOT / 'src'), str(invocation_path),
                str(invocation_pin['bytes']), invocation_pin['sha256']]
        value.update(invocation_pin=invocation_pin, argv=argv, cwd=str(ROOT))
        def boundary():
            _boundary(invocation_path, invocation_pin, source, inputs,
                      git_reader=git_reader,
                      git_call_prefix=source_prefix())

        def on_started(process):
            launch.update(observed.creation_observation(
                process.pid, process._handle))
            io._exclusive(target / 'launch.json', io.json_bytes(launch))

        value['reason'] = 'job_failed'
        with chain.four.platform._platform_scope():
            report = job_owner.supervise_cli(
                argv, ROOT, target / 'job', LIMITS,
                runtime_probe=lambda: runtime.probe_runtime(ROOT),
                boundary=boundary, on_started=on_started)
        report_raw = io.json_bytes(report)
        io._exclusive(target / 'supervision.json', report_raw)
        value['job_supervision_pin'] = observed._pin(report_raw)
        value['launch'] = launch
        _job_complete(report, argv, launch)
        value['reason'] = 'inner_result_rejected'
        verified = _inner(target, report, launch, invocation)
        boundary()
        value.update(status='verified', reason=None,
                     all_job_processes_exit_confirmed=True,
                     job_accounting=copy.deepcopy(report['job']['accounting']),
                     job_memory=copy.deepcopy(report['job']['memory']),
                     **verified)
    except (job_owner.UnreapedJob, job_owner.UnclosedHandles) as error:
        value['reason'] = 'job_reconciliation_required'
        value['error_type'] = type(error).__name__
        value['job_exception_report'] = _job_exception_summary(error)
        value['launch'] = copy.deepcopy(launch)
        value['launch_pin'] = None
        if launch:
            try:
                launch_raw = io.json_bytes(launch)
                launch_pin = observed._pin(launch_raw)
                v.require(_pinned(target / 'launch.json', launch_pin,
                                  MAX_RECEIPT) == launch_raw,
                          'unreaped Job saved launch changed')
                value['launch_pin'] = launch_pin
            except BaseException as capture_error:
                value['launch_capture_error_type'] = type(capture_error).__name__
        critical = error
    except BaseException as error:
        value['error_type'] = type(error).__name__
        if report is not None:
            value['job_accounting'] = copy.deepcopy(
                report.get('job', {}).get('accounting'))
            value['all_job_processes_exit_confirmed'] = bool(
                report.get('job', {}).get('all_assigned_processes_exit_confirmed'))
        if not isinstance(error, (ValueError, OSError, KeyError, TypeError,
                                  subprocess.SubprocessError)):
            critical = error
    try:
        saved = _receipt(target, value)
    except BaseException as save_error:
        if critical is None:
            raise
        critical.outer_receipt_error = save_error
        raise critical
    if critical is not None:
        raise critical
    return saved


def verify_retained(result_root, expected_receipt_pin, *, git_reader=None,
                    git_call_prefix=''):
    """Read saved Job and five-role bytes; never re-launch a worker."""
    root = Path(result_root)
    v.require(root.is_absolute() and root.is_relative_to(ROOT / 'artifacts'),
              'known local owner result root')
    receipt = v.strict_json(_pinned(root / 'receipt.json',
                                    expected_receipt_pin, MAX_RECEIPT))
    for key, expected in chain.four.publication.CLOSED.items():
        _same(receipt[key], expected, 'retained owner closed scope ' + key)
    v.require(receipt['format'] == FORMAT and receipt['mode'] == 'fixture' and
              receipt['status'] == 'verified' and receipt['reason'] is None and
              receipt['formal_permission'] is False and
              receipt['source_closure_complete'] is False and
              receipt['runtime_closure_complete'] is False and
              receipt['execution_authenticated'] is False and
              receipt['retry_authorized'] is False and
              receipt['next_stage_authorized'] is False and
              receipt['job_outside_processes_authenticated'] is False and
              receipt['individual_descendant_exit_codes_authenticated'] is False and
              receipt['registered_saved_reader_used'] is False and
              type(receipt['new_evaluations']) is int and
              receipt['new_evaluations'] == 0,
              'retained five-role Job receipt scope')
    invocation_path = root / 'invocation.json'
    invocation = _invocation(invocation_path, receipt['invocation_pin'])
    v.require(invocation['result_root'] == str(root / 'five-role') and
              invocation['source_revision'] == receipt['source_revision'] and
              invocation['join_root'] == receipt['join_root'] and
              invocation['join_receipt_pin'] == receipt['join_receipt_pin'] and
              invocation['candidate_set_pin'] == receipt['candidate_set_pin'] and
              receipt['profile_required'] is
              (invocation['candidate_set_path'] is not None),
              'retained five-role Job invocation binding')
    source = _source(invocation['source_revision'], git_reader=git_reader,
                     git_call_prefix=git_call_prefix)
    inputs = _inputs(invocation['join_root'], invocation['join_receipt_pin'],
                     invocation['source_revision'],
                     invocation['candidate_set_path'],
                     invocation['candidate_set_pin'])
    _same(source, receipt['source_pins'], 'retained owner source')
    _same(inputs, receipt['input_binding'], 'retained owner inputs')
    launch = v.strict_json(_pinned(root / 'launch.json',
                                   observed._pin(io.json_bytes(receipt['launch'])),
                                   MAX_RECEIPT))
    _same(launch, receipt['launch'], 'retained owner launch')
    report = v.strict_json(_pinned(root / 'supervision.json',
                                   receipt['job_supervision_pin'], MAX_RECEIPT))
    _job_complete(report, receipt['argv'], launch)
    _same(receipt['cwd'], str(ROOT), 'retained owner CWD')
    expected_argv = [sys.executable, '-I', '-S', '-B', '-c', BOOTSTRAP,
                     str(ROOT / 'src'), str(invocation_path),
                     str(receipt['invocation_pin']['bytes']),
                     receipt['invocation_pin']['sha256']]
    _same(receipt['argv'], expected_argv, 'retained owner argv')
    verified = _inner(root, report, launch, invocation)
    for key, item in verified.items():
        _same(receipt[key], item, 'retained owner ' + key)
    _same(receipt['job_accounting'], report['job']['accounting'],
          'retained owner Job accounting')
    _same(receipt['job_memory'], report['job']['memory'],
          'retained owner Job memory')
    v.require(receipt['all_job_processes_exit_confirmed'] is True,
              'retained owner Job exit')
    return {'status': 'verified_retained', 'receipt_pin': expected_receipt_pin,
            'inner_result_pin': verified['inner_result_pin'],
            'formal_permission': False, 'source_closure_complete': False,
            'runtime_closure_complete': False}
