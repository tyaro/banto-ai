"""Owned, bounded numerical fixture worker; never a registered-data consumer.

The caller retains all four input pins and a known fixture document pin before
launch. The child computes at most eight supplied draws. Parent-side checks do
not recompute inference and do not establish independent numerical agreement.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

from . import anomaly_v03_wrapper_fixture as wrapper
from . import anomaly_v03_reader_evidence as observed
from . import _anomaly_v03_reader_dependencies as dependencies
from . import _anomaly_v03_fixture_budget as budgets

v = observed.v
io = observed.io
evidence = observed.evidence
supervisor = observed.supervisor
ROOT = Path(__file__).resolve().parents[2]
FORMAT = 'anomaly-v03-fixture-numerical-request-v1'
INVOCATION = 'anomaly-v03-fixture-numerical-invocation-v1'
OPERATION = wrapper.OPERATION
INPUT_LIMITS = {'fixture/input.json': 1024**2, 'fixture/slices.json': 8*1024**2,
                'fixture/coverage.json': 128*1024, 'fixture/operation.json': 4096}
TOTAL_INPUT_LIMIT = 10*1024**2
DOCUMENT_LIMIT = 4*1024**2
WRAPPER_LIMIT = 8*1024**2
MAX_DRAWS = 8
LIMITS = {'wall_seconds': 60, 'private_bytes': 256*1024**2, 'output_bytes': 1024**2}
EXTRA_SOURCES = tuple('src/banto_ai/'+name+'.py' for name in (
    'anomaly_v03_fixture_worker', 'anomaly_v03_wrapper_fixture', 'anomaly_v03_document_fixture',
    'anomaly_v03_slice_fixture', 'anomaly_v03_analysis_adapter', 'anomaly_v03_inference_audit',
    'anomaly_v03_analysis_inputs', 'anomaly_v03_descriptive_report', 'anomaly_v03_slices',
    'anomaly_v03_consumer_input', '_anomaly_v03_reader_dependencies','_anomaly_v03_fixture_budget'))
SOURCE_FILES = tuple(sorted((*observed.SOURCE_FILES, *EXTRA_SOURCES)))
BOOTSTRAP = ('import sys;sys.path.insert(0,sys.argv.pop(1));'
             'from banto_ai.anomaly_v03_fixture_worker import worker_main;'
             'raise SystemExit(worker_main(sys.argv[1:]))')


def _request(value):
    evidence._keys(value, 'format mode role operation inputs expected_document_pin', 'fixture worker request fields')
    v.require(value['format'] == FORMAT and value['mode'] == 'fixture'
              and value['role'] == 'analysis' and value['operation'] == OPERATION,
              'non-fixture role/mode/operation is closed')
    evidence._keys(value['inputs'], ' '.join(INPUT_LIMITS), 'four fixture worker inputs')
    total = 0
    for name, row in value['inputs'].items():
        evidence._keys(row, 'path pin links', 'fixture input record fields')
        evidence._absolute(row['path'])
        evidence._same(row['links'], 1, 'single-link fixture inputs')
        evidence._pin(row['pin'])
        v.require(0 < row['pin']['bytes'] <= INPUT_LIMITS[name], 'fixture input file limit')
        total += row['pin']['bytes']
    v.require(total <= TOTAL_INPUT_LIMIT, 'fixture total input limit')
    evidence._pin(value['expected_document_pin'])
    v.require(0 < value['expected_document_pin']['bytes'] <= DOCUMENT_LIMIT, 'fixture expected output limit')


def _load(request, revision):
    _request(request)
    raw = observed._inputs(request['inputs'])
    decoded = {name: v.strict_json(value) for name, value in raw.items()}
    v.require(all(v.canonical_json(decoded[name]) == value for name, value in raw.items()),
              'canonical fixture input bytes required')
    evidence._same(decoded['fixture/operation.json'], wrapper.operation_descriptor(revision),
                   'retained fixture operation/revision')
    fixture = decoded['fixture/input.json']
    wrapper.document._input(fixture)
    v.require(len(fixture['draws']) <= MAX_DRAWS, 'at most eight fixture draws')
    wrapper.document.I._fixture_clusters(fixture['clusters'])
    wrapper.document.adapter._diagnostics(fixture['clusters'], fixture['diagnostics'])
    coverage = wrapper._coverage(decoded['fixture/coverage.json'], fixture)
    v.require(coverage['complete'], 'fixture worker requires complete declared coverage')
    source = decoded['fixture/slices.json']
    evidence._keys(source, 'format invented_only clusters', 'fixture slice fields')
    evidence._same(source['format'], wrapper.slices.INPUT_FORMAT, 'fixture slice identity')
    evidence._same(source['invented_only'], True, 'invented slices only')
    v.require(type(source['clusters']) is list and len(source['clusters']) == 40, 'forty fixture slice clusters')
    for row, identifier in zip(source['clusters'], wrapper.document.IDS):
        evidence._keys(row, 'cluster_id candidates', 'fixture slice cluster fields')
        evidence._same(row['cluster_id'], identifier, 'fixture slice cluster identity/order')
    return raw, decoded


def _working_source(revision):
    rows = []
    for name in SOURCE_FILES:
        raw = observed._file(ROOT/name, 1024**2)
        rows.append({'path': name, 'byte_count': len(raw), 'raw_sha256': observed._pin(raw)['sha256']})
    return {'revision': revision, 'sources': rows}


def _git_sources(revision):
    _, snapshots, git = observed._git_sources(revision)
    v.require(not git('status', '--porcelain').strip(), 'fixture candidate must be clean')
    for name in EXTRA_SOURCES:
        raw = git('show', revision+':'+name)
        v.require(len(raw) <= 1024**2 and raw == observed._file(ROOT/name, 1024**2),
                  'fixture source differs from Git')
        snapshots[revision][name] = raw
    return _working_source(revision), snapshots, git


def worker_main(argv):
    try:
        v.require(len(argv) == 3, 'fixture worker arguments')
        invocation = Path(argv[0])
        pin = {'bytes': int(argv[1]), 'sha256': argv[2]}
        raw_bundle = observed.consumer.pinned.read_pinned(invocation, pin, 64*1024)
        bundle = v.strict_json(raw_bundle)
        evidence._keys(bundle, 'format invocation_id source request' +
                       (' dependency_profile_pin' if 'dependency_profile_pin' in bundle else ''),
                       'fixture invocation fields')
        evidence._same(bundle['format'], INVOCATION, 'fixture invocation identity')
        evidence._digest(bundle['invocation_id']);evidence._source(bundle['source'])
        revision = bundle['source']['revision']
        request = bundle['request'];_request(request)
        source_before = _working_source(revision)
        evidence._same(source_before, bundle['source'], 'fixture child source differs')
        process = observed.creation_observation(os.getpid())
        runtime_before = observed._observed_runtime()
        inputs, decoded = _load(request, revision)
        profile = None
        if 'dependency_profile_pin' in bundle:
            raw_profile = observed._file(invocation.parent/'dependency-profile.json',
                                         dependencies.PROFILE_MAX)
            profile = dependencies.load_five_role_profile(
                raw_profile, bundle['dependency_profile_pin'], role='analysis',
                root=ROOT, revision=revision)
        deps_before = dependencies.collect(ROOT)
        if profile is not None:
            dependencies.match_five_role_profile(profile, deps_before,
                                                 runtime_before, phase='before')
        fixture, source = decoded['fixture/input.json'], decoded['fixture/slices.json']
        schema = v.schemas(v._expected_configs())[7]
        base = wrapper.document.build_fixture_document(fixture, schema)
        connected = wrapper.slices.attach_fixture_slices(base, fixture, wrapper._ordered_slice_input(source), schema)
        output = v.canonical_json(connected)
        v.require(len(output) <= DOCUMENT_LIMIT, 'fixture computed document limit')
        evidence._raw(output, request['expected_document_pin'], 'fixture computed output differs from retained pin')
        target = invocation.parent/'payload';target.mkdir()
        io._exclusive(target/'document.json', output)
        evidence._raw(observed._file(target/'document.json', DOCUMENT_LIMIT), request['expected_document_pin'],
                      'fixture output readback differs')
        deps_after = dependencies.collect(ROOT)
        runtime_after = observed._observed_runtime();source_after = _working_source(revision)
        if profile is not None:
            dependencies.match_five_role_profile(profile, deps_after,
                                                 runtime_after, phase='after')
        evidence._same({n: observed._pin(b) for n, b in observed._inputs(request['inputs']).items()},
                       {n: observed._pin(b) for n, b in inputs.items()}, 'fixture inputs changed during computation')
        evidence._raw(observed._file(invocation, 64*1024), pin, 'fixture invocation changed')
        value = {'format': evidence.FORMAT, 'mode': 'fixture', 'role': 'analysis',
            'invocation_id': bundle['invocation_id'], 'source_before': source_before, 'source_after': source_after,
            'process': {'pid': os.getpid(), 'parent_pid': os.getppid(), 'start_token': process['start_token'],
                        'argv': list(sys.orig_argv), 'cwd': str(Path.cwd())},
            'runtime_before': runtime_before, 'runtime_after': runtime_after,
            'inputs': {n: observed._pin(b) for n, b in inputs.items()},
            'outputs': {'fixture/document.json': observed._pin(output)},
            'completion': {'status': 'completed', 'exit_code': 0, 'worker_exit_confirmed': True, 'observation_errors': []}}
        print(json.dumps({'evidence': value, 'creation_observation': process,
            'dependencies_before': deps_before, 'dependencies_after': deps_after,
            'computation': {'fixture_only': True, 'clusters': 40, 'replicates': len(fixture['draws'])}}, sort_keys=True))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({'status': 'fixture_computation_rejected', 'error_type': type(error).__name__,
                         'detail': str(error), 'formal_permission': False}, sort_keys=True))
        return 2


def calculate_with_evidence(request, *, expected_revision, receipt_parent, receipt_name,
                            budget_limits=None, resource_budget=None,
                            dependency_profile_raw=None,
                            expected_dependency_profile_pin=None):
    """Compute a bounded known fixture, retain owned-child evidence and map five payloads.

    Input and expected document pins originate with the caller, before launch.
    Invocation bytes are separately bound to the original launch and checked on
    both sides; the evidence's numerical input inventory stays exactly four files.
    No registered observations, formal bootstrap, publication or independent audit.
    """
    _request(request);evidence._digest(expected_revision, 40)
    v.require((dependency_profile_raw is None) ==
              (expected_dependency_profile_pin is None),
              'analysis profile raw/pin pair')
    profile = None
    if dependency_profile_raw is not None:
        profile = dependencies.load_five_role_profile(
            dependency_profile_raw, expected_dependency_profile_pin,
            role='analysis', root=ROOT, revision=expected_revision)
    budget_limits = budgets.limits(budget_limits)
    request = copy.deepcopy(request)
    parent = io._local_parent(Path(receipt_parent));v.safe_relative_path(receipt_name)
    v.require('/' not in receipt_name and not receipt_name.casefold().startswith('anomaly-multiseed-v0'),
              'fixture attempt name')
    target = io.regular_path(parent/receipt_name, directory=True, missing=True)
    v.require(not any(observed.reader._overlap(target, p) for p in
        (ROOT/'src', *(Path(row['path']).parent for row in request['inputs'].values()))),
        'fixture receipt overlaps inputs/source')
    target.mkdir()
    if profile is not None:
        io._exclusive(target/'dependency-profile.json', dependency_profile_raw)
    budget = budgets.FixtureBudget(target,budget_limits,upstream=resource_budget)
    result = {**wrapper.CLOSED, 'format': 'anomaly-v03-fixture-worker-check-v1', 'status': 'failed',
        'role': 'analysis', 'mode': 'fixture', 'operation': OPERATION, 'fixture_inference_performed': False,
        'profile_required': profile is not None, 'before_work_profile_enforcement': False,
        'worker_exit_confirmed': False, 'worker_pid': None, 'new_evaluations': 0}
    try:
        budget.start()
        source, source_bytes, git = _git_sources(expected_revision)
        observed._save(target/'source-tool.json', git.tool_record)
        budget.checkpoint()
        runtime, runtime_bytes = observed._expected_runtime()
        raw_inputs, decoded = _load(request, expected_revision)
        budget.checkpoint()
        bundle = {'format': INVOCATION, 'invocation_id': secrets.token_hex(32), 'source': source, 'request': request}
        if profile is not None:
            bundle['dependency_profile_pin'] = copy.deepcopy(expected_dependency_profile_pin)
        bundle_raw = io.json_bytes(bundle);bundle_pin = observed._pin(bundle_raw)
        bundle_path = target/'invocation.json';io._exclusive(bundle_path, bundle_raw)
        expected = {'invocation_id': bundle['invocation_id'], 'source': source, 'runtime': runtime,
            'inputs': {n: observed._pin(b) for n, b in raw_inputs.items()},
            'outputs': {'fixture/document.json': request['expected_document_pin']}}
        argv = [sys.executable, '-I', '-S', '-B', '-c', BOOTSTRAP, str(ROOT/'src'), str(bundle_path),
                str(bundle_pin['bytes']), bundle_pin['sha256']]
        launch = {}
        def boundary():
            budget.checkpoint()
            v.require(git('rev-parse', 'HEAD').decode().strip() == expected_revision, 'fixture revision changed')
            evidence._same(_working_source(expected_revision), source, 'fixture source changed')
            evidence._same({n: observed._pin(b) for n, b in observed._inputs(request['inputs']).items()},
                           expected['inputs'], 'parent fixture inputs changed')
            evidence._raw(observed._file(bundle_path, 64*1024), bundle_pin, 'fixture invocation changed')
            current, _ = observed._expected_runtime()
            evidence._same(current, runtime, 'fixture runtime expectation changed')
            if profile is not None:
                evidence._raw(observed._file(target/'dependency-profile.json',
                                             dependencies.PROFILE_MAX),
                              expected_dependency_profile_pin,
                              'analysis profile changed')
        def started(process):
            launch.update(observed.creation_observation(process.pid, process._handle))
            expected['process'] = {'pid': process.pid, 'parent_pid': os.getpid(), 'start_token': launch['start_token'],
                                   'argv': list(argv), 'cwd': str(ROOT)}
            observed._save(target/'launch.json', launch);observed._save(target/'expected.json', expected)
        monitor = supervisor.supervise(argv, ROOT, target/'worker', LIMITS, boundary=boundary, on_started=started, resource_probe=budget.probe)
        observed._save(target/'supervision.json', monitor)
        result.update(worker_exit_confirmed=monitor['worker_exit_confirmed'], worker_pid=monitor['worker_pid'],
                      reason=monitor['stop_reason'] or 'worker_failed')
        if monitor['status'] == 'complete':
            budget.checkpoint()
            v.require(monitor['worker_exit_confirmed'] and monitor['exit_code'] == 0 and not monitor['observation_errors'],
                      'fixture owned worker completion')
            v.require(monitor['worker_pid'] == expected['process']['pid'], 'fixture owned PID changed')
            reply = v.strict_json(observed.consumer.pinned.read_pinned(target/'worker/report.json', monitor['output'], LIMITS['output_bytes']))
            evidence._keys(reply, 'evidence creation_observation dependencies_before dependencies_after computation', 'fixture envelope')
            evidence._same(reply['creation_observation'], launch, 'fixture child/owned creation differs')
            for name, value in (('launch.json', launch), ('expected.json', expected)):
                evidence._raw(observed._file(target/name, 64*1024), observed._pin(io.json_bytes(value)), 'fixture retained expectation changed')
            evidence._same(reply['computation'], {'fixture_only': True, 'clusters': 40,
                'replicates': len(decoded['fixture/input.json']['draws'])}, 'fixture computation dimensions')
            payload = io.regular_path(target/'payload', directory=True)
            v.require({p.name for p in payload.iterdir()} == {'document.json'}, 'fixture output inventory')
            output = observed._file(payload/'document.json', DOCUMENT_LIMIT)
            evidence._raw(output, request['expected_document_pin'], 'fixture output differs from retained expectation')
            record = io.json_bytes(reply['evidence']);record_pin = observed._pin(record)
            binding = evidence.validate_execution_evidence(record, expected_mode='fixture', expected_role='analysis',
                expected_pin=record_pin, expected=expected, source_snapshots=source_bytes,
                runtime_snapshots=runtime_bytes, input_snapshots=raw_inputs, output_snapshots={'fixture/document.json': output})
            supplement = dependencies.verify_pair(reply['dependencies_before'], reply['dependencies_after'],
                root=ROOT, revision=expected_revision, git=git, required_sources=SOURCE_FILES)
            if profile is not None:
                for phase in ('before', 'after'):
                    dependencies.match_five_role_profile(
                        profile, reply['dependencies_' + phase],
                        reply['evidence']['runtime_' + phase], phase=phase)
                boundary()
            budget.checkpoint()
            draft = {'format': wrapper.FORMAT, 'mode': 'fixture', 'invented_only': True,
                'fixture_input': decoded['fixture/input.json'], 'slice_input': decoded['fixture/slices.json'],
                'coverage': decoded['fixture/coverage.json'], 'document': v.strict_json(output)}
            mapped = wrapper.assemble_fixture_wrapper(draft, v.schemas(v._expected_configs())[7],
                expected_mode='fixture', expected_revision=expected_revision, expected_input_pins=expected['inputs'],
                analysis_record=record, expected_analysis={'evidence_pin': record_pin, 'invocation': expected},
                source_snapshots=source_bytes, runtime_snapshots=runtime_bytes)
            files = {n: v.canonical_json(value) for n, value in mapped['payloads'].items()}
            v.require(sum(map(len, files.values())) <= WRAPPER_LIMIT, 'fixture wrapper byte limit')
            budget.checkpoint()
            (target/'wrapper').mkdir()
            for name, raw in files.items():
                budget.checkpoint()
                io._exclusive(target/'wrapper'/name, raw)
                evidence._raw(observed._file(target/'wrapper'/name, WRAPPER_LIMIT), mapped['payload_pins'][name], 'fixture wrapper readback')
            io._exclusive(target/'evidence.json', record);observed._save(target/'binding.json', binding)
            observed._save(target/'dependencies.json', {'before': reply['dependencies_before'], 'after': reply['dependencies_after']})
            observed._save(target/'dependency-crosscheck.json', supplement)
            observed._save(target/'wrapper-descriptor.json', {k: value for k, value in mapped.items() if k != 'payloads'})
            result.update(status='verified', reason=None, fixture_inference_performed=True,
                computation=reply['computation'], evidence_pin=record_pin, invocation_pin=bundle_pin,
                binding_pin=observed._pin(io.json_bytes(binding)), stdout_pin=monitor['output'],
                document_pin=request['expected_document_pin'], wrapper_payload_pins=mapped['payload_pins'],
                selected_source_files=len(SOURCE_FILES), runtime_files=2, authenticated_input_files=4,
                dependency_observation=supplement, parent_and_child_creation_matched=True)
            if profile is not None:
                result['dependency_profile_pin'] = copy.deepcopy(expected_dependency_profile_pin)
                result['before_work_profile_enforcement'] = True
    except supervisor.UnreapedWorker as error:
        try:
            observed._save(target/'supervision.json', error.report)
            observed._save(target/'result.json', {**result, 'reason': 'worker_exit_unconfirmed'})
        finally:
            raise error
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        result.update(reason='fixture_evidence_rejected', error_type=type(error).__name__, detail=str(error))
    finally:
        budgets.finish(budget,target,result,owner_error=sys.exception())
    budgets.save_result(target,result)
    return {**result, 'check_directory': str(target), 'result_pin': observed._pin(io.json_bytes(result))}
