"""One invented 26H2 analysis -> audit -> writer -> reader trial.

The previously saved producer join is a pinned, pure fixture declaration.  It
is not an owned producer process.  This candidate therefore measures four
owned consumers only and cannot supply S4 acceptance or campaign credit.
"""
from __future__ import annotations

import copy
import os
from pathlib import Path
import subprocess
import sys
import time

from . import anomaly_v03_bound_fixture_pipeline as projection
from . import anomaly_v03_fixture_publication as publication
from . import anomaly_v03_platform_fixture as platform
from . import anomaly_v03_platform_fixture_runtime as runtime
from . import anomaly_v03_platform_numeric_fixture as numeric


analysis = projection.analysis
audit = projection.audit
v, io, evidence = analysis.v, analysis.io, analysis.evidence
observed = analysis.observed
ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'src/banto_ai/anomaly_v03_platform_four_role_fixture.py'
FORMAT = 'anomaly-v03-platform-four-role-fixture-v1'
JOIN_FORMAT = 'anomaly-v03-preformal-join-budget-v1'
JOIN_FILES = ('bound.json', 'invented-inputs.zip', *(f'projection/{name}' for name in analysis.INPUT_LIMITS))
OUTPUT_PARENT = ROOT / 'artifacts' / 'anomaly-v03-preformal-four-role-26h2'
INPUT_NAMES = ('fixture/input.json', 'fixture/slices.json', 'fixture/coverage.json', 'fixture/operation.json')
AUDIT_OUTPUT = 'primary-and-slices-audit.json'


def _pin_file(path, pin, maximum):
    evidence._pin(pin)
    return observed.consumer.pinned.read_pinned(Path(path), pin, maximum)


def _git_source(revision):
    evidence._digest(revision, 40)
    def git(*args):
        return subprocess.check_output(['git', '-C', str(ROOT), *args], stderr=subprocess.DEVNULL, timeout=10)
    v.require(git('rev-parse', 'HEAD').decode().strip() == revision, 'chain revision changed')
    v.require(not git('status', '--porcelain').strip(), 'chain candidate must be clean')
    raw = observed._file(ROOT / SOURCE, 1024**2)
    evidence._raw(raw, observed._pin(git('show', revision + ':' + SOURCE)), 'chain source/Git bytes')
    return observed._pin(raw)


def _join_projection(join_root, receipt_pin, revision):
    """Recheck all saved join bytes and project only its one invented draw."""
    join_root = Path(join_root)
    v.require(join_root.is_absolute() and join_root.parent == ROOT / 'artifacts' and
              join_root.name.startswith('anomaly-v03-preformal-join-budget-'), 'known local join root required')
    raw = _pin_file(join_root / 'receipt.json', receipt_pin, 32 * 1024)
    receipt = v.strict_json(raw)
    for key, want in {'format': JOIN_FORMAT, 'status': 'measured', 'resource_budget_passed': True,
                      'source_revision_scope': 'selected-working-raw-matches-head-blobs',
                      'joined_slices': 2880, 'projected_input_files': 4, 'new_evaluations': 0,
                      'real_producer_executed': False, 'owned_analysis_executed': False,
                      'owned_audit_executed': False, 'publication_executed': False,
                      'registered_data_read': False, 'formal_permission': False,
                      'promotion_allowed': False}.items():
        evidence._same(receipt[key], want, 'saved join ' + key)
    v.require(Path(receipt['root']) == join_root, 'saved join root')
    evidence._same(receipt['source_pins_before'], receipt['source_pins_after'], 'join selected source pins')
    saved = receipt['saved_file_pins']
    v.require(set(saved) == set(JOIN_FILES), 'join saved file inventory')
    evidence._same(receipt['bound_pin'], saved['bound.json'], 'join bound pin')
    bound = _pin_file(join_root / 'bound.json', saved['bound.json'], 8 * 1024**2)
    _pin_file(join_root / 'invented-inputs.zip', saved['invented-inputs.zip'], 12 * 1024**2)
    old_files = {}
    for name in INPUT_NAMES:
        key = 'projection/' + name
        evidence._same(saved[key], receipt['projected_input_pins'][name], 'join projected pin')
        old_files[name] = _pin_file(join_root / key, saved[key], analysis.INPUT_LIMITS[name])
    old_fixture = v.strict_json(old_files['fixture/input.json'])
    draws = old_fixture['draws']
    v.require(type(draws) is list and len(draws) == 1, 'one saved invented draw required')
    prepared = projection.prepare_inputs(bound, expected_mode='fixture',
        expected_pin=saved['bound.json'], expected_revision=revision, draws=draws)
    for name in INPUT_NAMES[:3]:
        v.require(prepared['files'][name] == old_files[name], 'reprojected invented input bytes')
    evidence._same(prepared['binding']['worker_input_pins'],
                   {name: observed._pin(raw) for name, raw in prepared['files'].items()}, 'projected input pins')
    lineage = {'join_root': str(join_root), 'join_receipt_pin': copy.deepcopy(receipt_pin),
               'join_revision': receipt['source_revision'],
               'bound_pin': saved['bound.json'], 'input_archive_pin': saved['invented-inputs.zip'],
               'saved_projection_pins': copy.deepcopy(receipt['projected_input_pins']),
               'current_projection_pins': copy.deepcopy(prepared['binding']['worker_input_pins']),
               'producer_join_scope': 'previous-pure-fixture-declarations-only'}
    return prepared['files'], lineage


def _retain_inputs(target, files):
    v.require(set(files) == set(INPUT_NAMES), 'four projected files required')
    path = target / 'inputs'
    path.mkdir()
    records = {}
    for name in INPUT_NAMES:
        raw = files[name]
        v.require(type(raw) is bytes and 0 < len(raw) <= analysis.INPUT_LIMITS[name], 'projected input byte limit')
        destination = path / Path(name).name
        io._exclusive(destination, raw)
        pin = observed._pin(raw)
        _pin_file(destination, pin, analysis.INPUT_LIMITS[name])
        records[name] = {'path': str(destination), 'pin': pin, 'links': 1}
    return records


def _reference_document(files):
    """Retain a prior output pin; this uses the same fixture algorithm as the child."""
    fixture = v.strict_json(files['fixture/input.json'])
    source = v.strict_json(files['fixture/slices.json'])
    schema = v.schemas(v._expected_configs())[7]
    base = analysis.wrapper.document.build_fixture_document(fixture, schema)
    connected = analysis.wrapper.slices.attach_fixture_slices(
        base, fixture, analysis.wrapper._ordered_slice_input(source), schema)
    raw = v.canonical_json(connected)
    v.require(0 < len(raw) <= analysis.DOCUMENT_LIMIT, 'reference document byte limit')
    return raw


def _saved_result(target, result, role):
    v.require(Path(result['check_directory']) == target, role + ' check directory')
    raw = _pin_file(target / 'result.json', result['result_pin'], 64 * 1024)
    evidence._same(v.strict_json(raw), {key: value for key, value in result.items()
                                    if key not in ('check_directory', 'result_pin')}, role + ' retained result')
    return raw


def _role_identity(target, expected_role, expected_pin):
    raw = _pin_file(target / 'evidence.json', expected_pin, 64 * 1024)
    row = v.strict_json(raw)
    evidence._same(row['role'], expected_role, 'owned role')
    evidence._same(row['completion'], {'status': 'completed', 'exit_code': 0,
        'worker_exit_confirmed': True, 'observation_errors': []}, expected_role + ' completion')
    return {'pid': row['process']['pid'], 'start_token': row['process']['start_token'],
            'invocation_id': row['invocation_id'], 'evidence_pin': copy.deepcopy(expected_pin)}


def _record(path, raw):
    io._exclusive(path, raw)
    pin = observed._pin(raw)
    _pin_file(path, pin, max(len(raw), 1))
    return {'path': str(path), 'pin': pin, 'links': 1}


def _audit_request(target, records, a, revision, reference_pin):
    reference = {'result_pin': a['result_pin'], 'evidence_pin': a['evidence_pin'],
                 'source_revision': revision}
    operation = v.canonical_json(audit.operation_descriptor(revision, reference,
        operation=audit.SLICE_OPERATION))
    audit_input = target / 'inputs' / 'audit-operation.json'
    op_record = _record(audit_input, operation)
    inputs = {name: copy.deepcopy(records[name]) for name in INPUT_NAMES[:2]}
    inputs.update({'fixture/document.json': {'path': str(target / 'analysis' / 'payload' / 'document.json'),
                                              'pin': copy.deepcopy(reference_pin), 'links': 1},
                   'analysis/result.json': {'path': str(target / 'analysis' / 'result.json'),
                                            'pin': copy.deepcopy(a['result_pin']), 'links': 1},
                   'analysis/evidence.json': {'path': str(target / 'analysis' / 'evidence.json'),
                                              'pin': copy.deepcopy(a['evidence_pin']), 'links': 1},
                   'fixture/audit-operation.json': op_record})
    return {'format': audit.FORMAT, 'mode': 'fixture', 'role': 'audit',
            'operation': audit.SLICE_OPERATION, 'inputs': inputs, 'analysis_reference': reference}


def _publication_request(target, a, b, revision, reference_pin):
    analysis_ref = {'result_pin': a['result_pin'], 'evidence_pin': a['evidence_pin'],
                    'source_revision': revision}
    audit_ref = {'result_pin': b['result_pin'], 'evidence_pin': b['evidence_pin'],
                 'source_revision': revision}
    locations = {
        'analysis/result.json': (target / 'analysis' / 'result.json', a['result_pin']),
        'analysis/evidence.json': (target / 'analysis' / 'evidence.json', a['evidence_pin']),
        'analysis/binding.json': (target / 'analysis' / 'binding.json', a['binding_pin']),
        'analysis/document.json': (target / 'analysis' / 'payload' / 'document.json', reference_pin),
        'audit/result.json': (target / 'audit' / 'result.json', b['result_pin']),
        'audit/evidence.json': (target / 'audit' / 'evidence.json', b['evidence_pin']),
        'audit/verdict.json': (target / 'audit' / 'payload' / AUDIT_OUTPUT, b['audit_pin']),
    }
    locations.update({'wrapper/' + name: (target / 'analysis' / 'wrapper' / name,
                                          a['wrapper_payload_pins'][name]) for name in publication.PAYLOADS})
    v.require(set(locations) == set(publication.INPUTS), 'publication input inventory')
    rows = {}
    for name, (path, pin) in locations.items():
        maximum = 4 * 1024**2 if name.startswith('wrapper/') or name == 'analysis/document.json' else 64 * 1024
        _pin_file(path, pin, maximum)
        rows[name] = {'path': str(path), 'pin': copy.deepcopy(pin), 'links': 1}
    return {'format': publication.FORMAT, 'mode': 'fixture', 'inputs': rows,
            'analysis_reference': analysis_ref, 'audit_reference': audit_ref}


def _budget_checkpoint(budget, phase):
    if budget is not None:
        if hasattr(budget, 'record_role'):
            budget.checkpoint(phase)
        else:
            budget.checkpoint()


def _budget_role(budget, role, row):
    if budget is not None and hasattr(budget, 'record_role'):
        budget.record_role(role, row['status'], result_pin=row['result_pin'],
                           worker_pid=row.get('worker_pid'),
                           exit_confirmed=row.get('worker_exit_confirmed'))


def _run_roles(target, files, revision, result, *, resource_budget=None,
               role_profiles=None, analysis_git_reader=None, audit_git_reader=None):
    v.require(role_profiles is None or
              (type(role_profiles) is dict and
               set(role_profiles) == {'analysis', 'audit', 'writer', 'reader'}),
              'four-role profile inventory')
    def current_profile(role):
        if role_profiles is None:
            return None
        row = role_profiles[role]
        raw = observed._file(row['path'], numeric.analysis.dependencies.PROFILE_MAX)
        evidence._raw(raw, row['pin'], role + ' external profile changed')
        v.require(raw == row['raw'], role + ' retained profile changed')
        return {key: row[key] for key in ('path', 'pin', 'raw')}
    _budget_checkpoint(resource_budget, 'analysis')
    records = _retain_inputs(target, files)
    result['input_pins'] = {name: row['pin'] for name, row in records.items()}
    reference = _reference_document(files)
    reference_path = target / 'reference'
    reference_path.mkdir()
    reference_pin = _record(reference_path / 'document.json', reference)['pin']
    result['reference_document_pin'] = reference_pin
    result['reference_scope'] = 'same-fixture-algorithm-output-pin-before-child; independent audit follows'
    _budget_checkpoint(resource_budget, 'analysis')
    request = {'format': analysis.FORMAT, 'mode': 'fixture', 'role': 'analysis',
               'operation': analysis.OPERATION, 'inputs': records,
               'expected_document_pin': reference_pin}
    analysis._request(request)
    result['stage'] = 'analysis'
    analysis_profile = current_profile('analysis')
    a = numeric.calculate_fixture(request, expected_revision=revision, receipt_parent=target,
                                  receipt_name='analysis', resource_budget=resource_budget,
                                  dependency_profile_raw=(None if analysis_profile is None else
                                                          analysis_profile['raw']),
                                  expected_dependency_profile_pin=(None if analysis_profile is None else
                                                                   analysis_profile['pin']),
                                  **({} if analysis_git_reader is None else
                                     {'git_reader': analysis_git_reader}))
    _saved_result(target / 'analysis', a, 'analysis')
    _budget_role(resource_budget, 'analysis', a)
    result['analysis'] = {'status': a['status'], 'result_pin': a['result_pin'],
                          'evidence_pin': a.get('evidence_pin')}
    v.require(a['status'] == 'verified' and a['resource_budget_passed'] and
              a['worker_exit_confirmed'] and a['fixture_inference_performed'], 'owned analysis failed')
    result['identities'] = {'analysis': _role_identity(target / 'analysis', 'analysis', a['evidence_pin'])}
    _budget_checkpoint(resource_budget, 'audit')
    audit_request = _audit_request(target, records, a, revision, reference_pin)
    audit._request(audit_request)
    result['stage'] = 'audit'
    audit_profile = current_profile('audit')
    b = numeric.audit_fixture(audit_request, expected_revision=revision, receipt_parent=target,
                              receipt_name='audit', resource_budget=resource_budget,
                              dependency_profile_raw=(None if audit_profile is None else
                                                      audit_profile['raw']),
                              expected_dependency_profile_pin=(None if audit_profile is None else
                                                               audit_profile['pin']),
                              **({} if audit_git_reader is None else
                                 {'git_reader': audit_git_reader}))
    _saved_result(target / 'audit', b, 'audit')
    _budget_role(resource_budget, 'audit', b)
    result['audit'] = {'status': b['status'], 'result_pin': b['result_pin'],
                       'evidence_pin': b.get('evidence_pin'), 'verdict_pin': b.get('audit_pin')}
    v.require(b['status'] == 'verified' and b['resource_budget_passed'] and
              b['worker_exit_confirmed'] and b['fixture_numerical_audit_performed'] and
              b['fixture_slice_audit_performed'], 'owned audit failed')
    result['identities']['audit'] = _role_identity(target / 'audit', 'audit', b['evidence_pin'])
    _budget_checkpoint(resource_budget, 'writer')
    publication_request = _publication_request(target, a, b, revision, reference_pin)
    publication._request(publication_request)
    result['preflight_runtime'] = runtime.probe_runtime(ROOT)
    result['stage'] = 'writer_then_reader'
    publication_profiles = (None if role_profiles is None else
                            {role: current_profile(role) for role in ('writer', 'reader')})
    with platform._platform_scope():
        p = publication.publish_with_evidence(publication_request, expected_revision=revision,
            receipt_parent=target, receipt_name='publication',
            resource_budget=resource_budget,
            dependency_profiles=publication_profiles)
    _saved_result(target / 'publication', p, 'publication')
    result['publication'] = {'status': p['status'], 'result_pin': p['result_pin'],
                             'binding_pin': p.get('publication_binding_pin'),
                             'publication_status': p['publication_status'],
                             'reader_status': p['reader_status']}
    v.require(p['status'] == 'verified' and p['resource_budget_passed'] and
              p['publication_status'] == 'completed' and p['reader_status'] == 'completed',
              'owned writer or reader failed')
    result['postflight_runtime'] = runtime.probe_runtime(ROOT)
    evidence._same(result['postflight_runtime'], result['preflight_runtime'], 'four-role runtime changed')
    for role in ('writer', 'reader'):
        row = p[role]
        v.require(row['worker_exit_confirmed'], role + ' exit unconfirmed')
        result['identities'][role] = _role_identity(target / 'publication' / role,
            role, row['evidence_pin'])
        evidence._same(row['worker_pid'], result['identities'][role]['pid'], role + ' process identity')
    identities = list(result['identities'].values())
    v.require(len({(r['pid'], r['start_token']) for r in identities}) == 4,
              'four distinct owned process identities required')
    v.require(len({r['invocation_id'] for r in identities}) == 4,
              'four distinct invocations required')
    for name, row in records.items():
        _pin_file(row['path'], row['pin'], analysis.INPUT_LIMITS[name])
    _pin_file(reference_path / 'document.json', reference_pin, analysis.DOCUMENT_LIMIT)
    _budget_checkpoint(resource_budget, 'postflight')


def run_chain(*, expected_mode, join_root, expected_join_receipt_pin,
              expected_revision, receipt_name, receipt_parent=OUTPUT_PARENT):
    """Measure one preformal four-child chain from a pinned pure invented join."""
    v.require(expected_mode == 'fixture' and type(expected_mode) is str,
              'only invented fixture chain is open')
    evidence._pin(expected_join_receipt_pin)
    evidence._digest(expected_revision, 40)
    v.safe_relative_path(receipt_name)
    v.require('/' not in receipt_name and not receipt_name.casefold().startswith('anomaly-multiseed-v0'),
              'chain receipt name')
    parent = Path(receipt_parent)
    io.regular_path(parent, directory=True, missing=True)
    parent.mkdir(exist_ok=True)
    parent = io._local_parent(parent)
    v.require(not observed.reader._overlap(parent, ROOT / 'src'), 'chain/source overlap')
    target = io.regular_path(parent / receipt_name, directory=True, missing=True)
    v.require(not observed.reader._overlap(target, Path(join_root)), 'chain/join overlap')
    target.mkdir()
    started = time.monotonic()
    result = {**publication.CLOSED, 'format': FORMAT, 'mode': 'fixture', 'status': 'failed',
              'scope': 'invented-26h2-four-owned-consumer-trial',
              'numeric_policy_id': numeric.POLICY_ID,
              'publication_policy_id': platform.POLICY_ID,
              'platform_contract_status': 'proposal-not-accepted',
              'source_revision': expected_revision, 'chain_source_scope': 'selected-file-Git-byte-pin',
              'source_closure_complete': False, 'runtime_closure_complete': False,
              'registered_data_read': False, 'registered_saved_reader_used': False,
              'real_producer_executed': False, 'owned_producer_executed': False,
              'combined_resource_budget_measured': False,
              'combined_resource_budget_passed': None,
              'resource_budget_scope': 'per-role-budgets-only; total wall is elapsed without continuous outer monitor',
              'independent_s6_complete': False, 'formal_permission': False,
              'promotion_allowed': False, 'new_evaluations': 0,
              'stage': 'preflight', 'identities': {}}
    try:
        result['chain_source_pin'] = _git_source(expected_revision)
        files, lineage = _join_projection(join_root, expected_join_receipt_pin, expected_revision)
        result['join_lineage'] = lineage
        _run_roles(target, files, expected_revision, result)
        result['stage'] = 'postflight'
        evidence._same(_git_source(expected_revision), result['chain_source_pin'], 'chain source changed')
        _join_projection(join_root, expected_join_receipt_pin, expected_revision)
        result['status'] = 'verified'
        result['stage'] = 'complete'
    except analysis.supervisor.UnreapedWorker as error:
        result.update(status='failed', reason='owned_worker_exit_unconfirmed',
                      error_type=type(error).__name__)
        _save(target, result, started)
        raise
    except analysis.budgets.UnclosedMonitor as error:
        result.update(status='failed', reason='resource_monitor_exit_unconfirmed',
                      error_type=type(error).__name__)
        _save(target, result, started)
        raise
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        result.update(status='failed', reason='four_role_fixture_rejected',
                      error_type=type(error).__name__, detail=str(error))
    return _save(target, result, started)


def _save(target, result, started):
    result['wall_seconds'] = time.monotonic() - started
    raw = io.json_bytes(result)
    v.require(len(raw) <= 64 * 1024, 'chain receipt byte limit')
    path = target / 'result.json'
    io._exclusive(path, raw)
    _pin_file(path, observed._pin(raw), 64 * 1024)
    return {**result, 'check_directory': str(target), 'result_pin': observed._pin(raw)}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 3:
        raise SystemExit('usage: RECEIPT_NAME SAVED_JOIN_ROOT SAVED_JOIN_RECEIPT_SHA256')
    name, join_root, digest = argv
    receipt = Path(join_root) / 'receipt.json'
    pin = observed._pin(observed._file(receipt, 32 * 1024))
    v.require(pin['sha256'] == digest, 'caller join receipt digest')
    revision = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'],
        text=True, timeout=10).strip()
    value = run_chain(expected_mode='fixture', join_root=join_root,
        expected_join_receipt_pin=pin, expected_revision=revision, receipt_name=name)
    print(io.json_bytes({'status': value['status'], 'stage': value['stage'],
                         'result_pin': value['result_pin'], 'check_directory': value['check_directory']}).decode())
    return 0 if value['status'] == 'verified' else 2


if __name__ == '__main__':
    raise SystemExit(main())
