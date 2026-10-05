"""Contiguous invented 26H2 producer -> analysis -> audit -> writer -> reader.

The first child joins a previously pinned invented archive.  Its fresh output
bytes, never the earlier pure-join output files, feed four more owned children.
This unadopted engineering candidate reads no registered observations and does
not supply S4 acceptance, S5/S6 permission, or campaign evaluations.
"""
from __future__ import annotations

import copy
from pathlib import Path
import subprocess
import sys
import time

from . import anomaly_v03_owned_producer_fixture as producer
from . import anomaly_v03_platform_four_role_fixture as four
from . import anomaly_v03_preformal_chain_budget as chain_budget
from . import anomaly_v03_preformal_role_profiles as role_profiles


v, io, evidence, observed = four.v, four.io, four.evidence, four.observed
ROOT = four.ROOT
FORMAT = 'anomaly-v03-platform-five-role-fixture-v1'
SOURCE = 'src/banto_ai/anomaly_v03_platform_five_role_fixture.py'
SOURCES = (SOURCE, four.SOURCE, 'src/banto_ai/anomaly_v03_owned_producer_fixture.py',
           'src/banto_ai/anomaly_v03_preformal_chain_budget.py')
OUTPUT_PARENT = ROOT / 'artifacts' / 'anomaly-v03-preformal-five-role-26h2'
JOIN_FORMAT = 'anomaly-v03-preformal-join-budget-v1'


def _git_sources(revision, *, git_reader=None, git_call_prefix=''):
    """Pin selected orchestrator sources; an owned reader remains partial."""
    evidence._digest(revision, 40)
    def git(*args):
        return subprocess.check_output(['git', '-C', str(ROOT), *args],
                                       stderr=subprocess.DEVNULL, timeout=10)
    head = (git('rev-parse', 'HEAD') if git_reader is None else
            git_reader.run(call_id=git_call_prefix + 'head', operation='head'))
    v.require(head.decode().strip() == revision,
              'five-role source revision changed')
    status = (git('status', '--porcelain') if git_reader is None else
              git_reader.run(call_id=git_call_prefix + 'status', operation='status'))
    v.require(not status.strip(),
              'five-role candidate must be clean')
    pins = {}
    for index, name in enumerate(SOURCES):
        raw = observed._file(ROOT / name, 1024**2)
        committed = (git('show', revision + ':' + name)
                     if git_reader is None else git_reader.run(
                         call_id=f'{git_call_prefix}selected-source-{index}',
                         operation='source_blob', source_path=name,
                         expected_output_pin=observed._pin(raw)))
        evidence._raw(raw, observed._pin(committed),
                      'five-role selected source/Git bytes')
        pins[name] = observed._pin(raw)
    return pins


def _external_archive(join_root, expected_receipt_pin):
    """Authenticate the earlier fixture archive without using its outputs."""
    join_root = Path(join_root)
    v.require(join_root.is_absolute() and join_root.parent == ROOT / 'artifacts' and
              join_root.name.startswith('anomaly-v03-preformal-join-budget-'),
              'saved invented join root required')
    raw = four._pin_file(join_root / 'receipt.json', expected_receipt_pin, 32 * 1024)
    receipt = v.strict_json(raw)
    for key, want in {'format': JOIN_FORMAT, 'status': 'measured',
                      'resource_budget_passed': True,
                      'source_revision_scope': 'selected-working-raw-matches-head-blobs',
                      'new_evaluations': 0, 'real_producer_executed': False,
                      'owned_analysis_executed': False, 'owned_audit_executed': False,
                      'publication_executed': False, 'registered_data_read': False,
                      'formal_permission': False, 'promotion_allowed': False}.items():
        evidence._same(receipt[key], want, 'saved invented archive receipt ' + key)
    v.require(Path(receipt['root']) == join_root, 'saved invented archive root')
    evidence._same(receipt['source_pins_before'], receipt['source_pins_after'],
                   'saved invented archive source pins')
    saved = receipt['saved_file_pins']
    evidence._same(saved['invented-inputs.zip'], receipt['input_archive']['compressed_pin'],
                   'saved invented archive pin')
    evidence._same(saved['bound.json'], receipt['bound_pin'], 'saved expected bound pin')
    evidence._same(receipt['input_archive']['files'], 12004, 'invented archive entry count')
    evidence._same(receipt['invented_inputs']['primary_snapshot_files'], 9122,
                   'invented primary snapshot count')
    evidence._same(receipt['invented_inputs']['slice_snapshot_files'], 2880,
                   'invented slice snapshot count')
    archive_path = join_root / 'invented-inputs.zip'
    four._pin_file(archive_path, saved['invented-inputs.zip'], producer.ARCHIVE_MAX)
    return archive_path, copy.deepcopy(saved['invented-inputs.zip']), \
        copy.deepcopy(saved['bound.json']), {
            'join_root': str(join_root), 'join_receipt_pin': copy.deepcopy(expected_receipt_pin),
            'join_revision': receipt['source_revision'],
            'archive_pin': copy.deepcopy(saved['invented-inputs.zip']),
            'expected_bound_pin': copy.deepcopy(saved['bound.json']),
            'input_scope': 'previous-retained-invented-archive-only',
            'prior_bound_or_projection_used_as_child_input': False}


def _producer_identity(target, result):
    """Bind the owned producer PID and start token to its saved invocation."""
    raw = four._pin_file(target / 'invocation.json', result['invocation_pin'], 16 * 1024)
    invocation = v.strict_json(raw)
    evidence._same(invocation['format'], producer.INVOCATION, 'producer invocation format')
    evidence._same(invocation['source_revision'], result['source_revision'],
                   'producer invocation revision')
    report = v.strict_json(four._pin_file(target / 'worker' / 'report.json',
                                        result['stdout_pin'], producer.LIMITS['output_bytes']))
    evidence._same(report['invocation_id'], invocation['invocation_id'],
                   'producer invocation identity')
    evidence._same(report['process']['pid'], result['worker_pid'], 'producer owned PID')
    evidence._same(report['process']['start_token'], result['child_start_token'],
                   'producer owned start token')
    return {'pid': result['worker_pid'], 'start_token': result['child_start_token'],
            'invocation_id': invocation['invocation_id'],
            'result_pin': copy.deepcopy(result['result_pin']),
            'stdout_pin': copy.deepcopy(result['stdout_pin'])}


def _fresh_projection(target, result, revision):
    """Read only the output of this attempt's owned producer child."""
    output = target / 'producer' / 'output'
    v.require(Path(result['projection_root']) == output / 'projection',
              'fresh producer projection root')
    v.require(Path(result['bound_path']) == output / 'bound.json',
              'fresh producer bound path')
    four._pin_file(result['bound_path'], result['bound_pin'], 8 * 1024**2)
    v.require(set(result['projection_pins']) == set(four.INPUT_NAMES),
              'fresh producer projection inventory')
    files = {}
    for name in four.INPUT_NAMES:
        files[name] = four._pin_file(output / 'projection' / name,
                                    result['projection_pins'][name],
                                    four.analysis.INPUT_LIMITS[name])
    evidence._same(v.strict_json(files['fixture/operation.json']),
                   four.analysis.wrapper.operation_descriptor(revision),
                   'fresh producer operation revision')
    fixture = v.strict_json(files['fixture/input.json'])
    v.require(type(fixture['draws']) is list and len(fixture['draws']) == 1,
              'one fresh invented draw')
    return files


def _check_five_identities(result):
    identities = result['identities']
    v.require(set(identities) == {'producer', 'analysis', 'audit', 'writer', 'reader'},
              'five owned role inventory')
    rows = list(identities.values())
    v.require(len({(r['pid'], r['start_token']) for r in rows}) == 5,
              'five distinct owned process identities')
    v.require(len({r['invocation_id'] for r in rows}) == 5,
              'five distinct owned invocations')


def _save(target, result, started):
    result['wall_seconds'] = time.monotonic() - started
    raw = io.json_bytes(result)
    v.require(len(raw) <= 64 * 1024, 'five-role receipt byte limit')
    path = target / 'result.json'
    io._exclusive(path, raw)
    four._pin_file(path, observed._pin(raw), 64 * 1024)
    return {**result, 'check_directory': str(target), 'result_pin': observed._pin(raw)}


def run_chain(*, expected_mode, join_root, expected_join_receipt_pin,
              expected_revision, receipt_name, receipt_parent=OUTPUT_PARENT,
              budget_limits=None, candidate_set_path=None,
              expected_candidate_set_pin=None, git_reader=None,
              producer_git_reader=None, analysis_git_reader=None, audit_git_reader=None):
    """One new attempt with five owned children and pinned stage succession."""
    v.require(type(expected_mode) is str and expected_mode == 'fixture',
              'only invented five-role fixture is open')
    evidence._pin(expected_join_receipt_pin)
    evidence._digest(expected_revision, 40)
    v.safe_relative_path(receipt_name)
    v.require('/' not in receipt_name and '\\' not in receipt_name and
              not receipt_name.casefold().startswith('anomaly-multiseed-v0'),
              'new five-role receipt name')
    parent = Path(receipt_parent)
    io.regular_path(parent, directory=True, missing=True)
    parent.mkdir(exist_ok=True)
    parent = io._local_parent(parent)
    v.require(parent.is_relative_to(ROOT / 'artifacts'),
              'five-role parent must be under local artifacts')
    target = io.regular_path(parent / receipt_name, directory=True, missing=True)
    v.require(not observed.reader._overlap(target, Path(join_root)),
              'five-role output/input overlap')
    target.mkdir()
    started = time.monotonic()
    result = {**four.publication.CLOSED, 'format': FORMAT, 'mode': 'fixture',
              'status': 'failed', 'scope': 'invented-26h2-five-owned-role-trial',
              'platform_contract_status': 'proposal-not-accepted',
              'numeric_policy_id': four.numeric.POLICY_ID,
              'publication_policy_id': four.platform.POLICY_ID,
              'source_revision': expected_revision,
              'source_scope': 'selected-orchestrator-files-plus-per-role-source-records',
              'source_closure_complete': False, 'runtime_closure_complete': False,
              'combined_resource_budget_measured': False,
              'combined_resource_budget_passed': None,
              'resource_budget_scope': 'one sampled outer root plus shared cooperative child stop',
              'registered_data_read': False, 'registered_saved_reader_used': False,
              'real_producer_executed': False, 'owned_producer_join_executed': False,
              'independent_s6_complete': False, 'formal_permission': False,
              'promotion_allowed': False, 'new_evaluations': 0,
              'stage': 'preflight', 'identities': {},
              'profile_required': (candidate_set_path is not None or
                                   expected_candidate_set_pin is not None),
              'before_work_profile_enforcement': False}
    budget = None
    critical = None
    try:
        budget = chain_budget.PreformalChainBudget(
            target, budget_limits,
            publication_roots=(target / 'publication' / 'published',)).start()
        budget.checkpoint('preflight')
        v.require((candidate_set_path is None) ==
                  (expected_candidate_set_pin is None),
                  'external candidate set path/pin pair')
        candidates = None
        if candidate_set_path is not None:
            candidates = role_profiles.load_pinned_candidate_set(
                candidate_set_path, expected_candidate_set_pin,
                revision=expected_revision)
            result['candidate_profile_set_pin'] = copy.deepcopy(expected_candidate_set_pin)
        result['selected_source_pins'] = _git_sources(
            expected_revision, git_reader=git_reader,
            git_call_prefix='' if git_reader is None else 'child-chain-source-0-')
        archive_path, archive_pin, bound_pin, lineage = _external_archive(
            join_root, expected_join_receipt_pin)
        result['archive_lineage'] = lineage
        result['stage'] = 'producer'
        budget.checkpoint('producer')
        producer_profile = None
        if candidates is not None:
            producer_profile = candidates['producer']
            evidence._raw(observed._file(producer_profile['path'],
                                         role_profiles.MAX_PROFILE),
                          producer_profile['pin'], 'external producer profile changed')
        p = producer.join_with_evidence(archive_path, archive_pin,
            expected_revision=expected_revision, receipt_parent=target,
            receipt_name='producer', expected_bound_pin=bound_pin,
            resource_budget=budget,
            dependency_profile_raw=(None if producer_profile is None else
                                    producer_profile['raw']),
            expected_dependency_profile_pin=(None if producer_profile is None else
                                             producer_profile['pin']),
            git_reader=producer_git_reader)
        four._saved_result(target / 'producer', p, 'producer')
        result['producer'] = {'status': p['status'], 'result_pin': p['result_pin'],
                              'bound_pin': p.get('bound_pin'),
                              'stdout_pin': p.get('stdout_pin')}
        budget.record_role('producer', p['status'], result_pin=p['result_pin'],
                           worker_pid=p.get('worker_pid'),
                           exit_confirmed=p['worker_exit_confirmed'])
        v.require(p['status'] == 'verified' and p['worker_exit_confirmed'] and
                  p['owned_producer_join_executed'] and not p['real_producer_executed'],
                  'owned producer join failed')
        if producer_profile is not None:
            evidence._same(p['dependency_profile_pin'], producer_profile['pin'],
                           'producer profile result pin')
            v.require(p['before_work_profile_enforcement'] is True,
                      'producer before-work profile check')
        result['owned_producer_join_executed'] = True
        producer_identity = _producer_identity(target / 'producer', p)
        result['identities']['producer'] = producer_identity
        files = _fresh_projection(target, p, expected_revision)
        result['stage'] = 'analysis'
        budget.checkpoint('analysis')
        try:
            four._run_roles(target, files, expected_revision, result,
                            resource_budget=budget,
                            role_profiles=(None if candidates is None else
                                           {role: candidates[role] for role in
                                            ('analysis', 'audit', 'writer', 'reader')}),
                            **({} if analysis_git_reader is None else
                               {'analysis_git_reader': analysis_git_reader}),
                            **({} if audit_git_reader is None else
                               {'audit_git_reader': audit_git_reader}))
        finally:
            # The reusable four-role helper initializes its own identity map.
            result['identities'] = {'producer': producer_identity, **result['identities']}
        result['stage'] = 'postflight'
        budget.checkpoint('postflight')
        evidence._same(_git_sources(
            expected_revision, git_reader=git_reader,
            git_call_prefix='' if git_reader is None else 'child-chain-source-1-'),
                       result['selected_source_pins'],
                       'five-role selected source changed')
        four._pin_file(archive_path, archive_pin, producer.ARCHIVE_MAX)
        for name in four.INPUT_NAMES:
            four._pin_file(target / 'producer' / 'output' / 'projection' / name,
                           p['projection_pins'][name], four.analysis.INPUT_LIMITS[name])
        _check_five_identities(result)
        if candidates is not None:
            for role in role_profiles.ROLES:
                evidence._raw(observed._file(candidates[role]['path'],
                                             role_profiles.MAX_PROFILE),
                              candidates[role]['pin'],
                              role + ' external profile changed at postflight')
            evidence._raw(observed._file(candidate_set_path,
                                         role_profiles.MAX_RESULT),
                          expected_candidate_set_pin,
                          'external candidate set changed at postflight')
            for role in ('analysis', 'audit'):
                saved_role = v.strict_json(four._pin_file(
                    target / role / 'result.json', result[role]['result_pin'],
                    64 * 1024))
                evidence._same(saved_role['dependency_profile_pin'],
                               candidates[role]['pin'], role + ' profile result pin')
                v.require(saved_role['before_work_profile_enforcement'] is True,
                          role + ' before-work profile check')
            publication_result = v.strict_json(four._pin_file(
                target / 'publication' / 'result.json',
                result['publication']['result_pin'], 64 * 1024))
            for role in ('writer', 'reader'):
                saved_role = v.strict_json(four._pin_file(
                    target / 'publication' / role / 'result.json',
                    observed._pin(io.json_bytes(publication_result[role])),
                    64 * 1024))
                evidence._same(saved_role, publication_result[role],
                               role + ' embedded/saved result')
                evidence._same(saved_role['dependency_profile_pin'],
                               candidates[role]['pin'], role + ' profile result pin')
                v.require(saved_role['before_work_profile_enforcement'] is True,
                          role + ' before-work profile check')
            result['before_work_profile_enforcement'] = True
        result['status'] = 'verified'
        result['stage'] = 'complete'
    except four.analysis.supervisor.UnreapedWorker as error:
        result.update(status='failed', reason='owned_worker_exit_unconfirmed',
                      error_type=type(error).__name__)
        critical = error
    except four.analysis.budgets.UnclosedMonitor as error:
        result.update(status='failed', reason='resource_monitor_exit_unconfirmed',
                      error_type=type(error).__name__)
        critical = error
    except chain_budget.resources.ResourceStop as error:
        result.update(status='failed', reason=error.reason,
                      error_type=type(error).__name__)
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        result.update(status='failed', reason='five_role_fixture_rejected',
                      error_type=type(error).__name__, detail=str(error))
    except BaseException as error:
        result.update(status='failed', reason='unexpected_five_role_exception',
                      error_type=type(error).__name__, detail=str(error))
        critical = error
    finally:
        if budget is not None and budget._thread is not None:
            try:
                report = budget.close()
                raw = io.json_bytes(report)
                v.require(len(raw) <= 64 * 1024, 'outer budget receipt byte limit')
                record = four._record(target / 'resource-budget.json', raw)
                result['resource_budget_pin'] = record['pin']
                result['combined_resource_budget_measured'] = True
                result['outer_monitor_passed'] = report['passed']
                result['combined_resource_budget_passed'] = (
                    report['passed'] and report['caller_reported_all_five_exits'] and
                    result['status'] == 'verified')
                result['five_role_budget_closure_passed'] = result['combined_resource_budget_passed']
                if not report['passed'] or (result['status'] == 'verified' and
                                            not report['caller_reported_all_five_exits']):
                    result.update(status='failed', reason=report['stop_reason'] or
                                  'five_owned_exits_not_all_reported')
            except BaseException as error:
                result.update(status='failed', reason='outer_budget_close_or_save_failed',
                              budget_error_type=type(error).__name__)
                if critical is None:
                    critical = error
        saved = None
        try:
            saved = _save(target, result, started)
        except BaseException as save_error:
            if critical is None:
                critical = save_error
            else:
                critical.outer_receipt_error = save_error
    if critical is not None:
        raise critical
    return saved


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) not in (3, 6):
        raise SystemExit('usage: RECEIPT_NAME SAVED_JOIN_ROOT SAVED_JOIN_RECEIPT_SHA256 '
                         '[EXTERNAL_CANDIDATE_SET_PATH BYTES SHA256]')
    name, join_root, digest = argv[:3]
    pin = observed._pin(observed._file(Path(join_root) / 'receipt.json', 32 * 1024))
    v.require(pin['sha256'] == digest, 'caller join receipt digest')
    revision = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'],
        text=True, timeout=10).strip()
    value = run_chain(expected_mode='fixture', join_root=join_root,
        expected_join_receipt_pin=pin, expected_revision=revision, receipt_name=name,
        candidate_set_path=(None if len(argv) == 3 else argv[3]),
        expected_candidate_set_pin=(None if len(argv) == 3 else
                                    {'bytes': int(argv[4]), 'sha256': argv[5]}))
    print(io.json_bytes({'status': value['status'], 'stage': value['stage'],
                         'result_pin': value['result_pin'], 'check_directory': value['check_directory']}).decode())
    return 0 if value['status'] == 'verified' else 2


if __name__ == '__main__':
    raise SystemExit(main())
