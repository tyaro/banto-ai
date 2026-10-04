"""Fail-closed owner for two invented campaign smoke slots.

This module never opens registered observations.  It accepts an externally
pinned, already-started metadata journal record before each CLI launch.  A
completed slot can be followed by the next slot; an unfinished or failed slot
is deliberately not restarted here.  A successful direct CLI exit and its
saved child evidence are local engineering observations, not S4 acceptance or
individual descendant exit-code authentication.
"""
from __future__ import annotations

import copy
from pathlib import Path
import re
import sys

from . import _anomaly_v03_io as io
from . import _anomaly_v03_runtime as paths
from . import anomaly_v03 as v
from . import anomaly_v03_platform_fixture as platform
from . import anomaly_v03_platform_fixture_runtime as runtime
from . import anomaly_v03_preformal_campaign_metadata as metadata
from . import anomaly_v03_preformal_campaign_child_context as child_context
from . import anomaly_v03_preformal_campaign_store as store
from . import anomaly_v03_preformal_owned_generated_attempt as generated
from . import anomaly_v03_preformal_owned_saved_attempt as copied
from . import anomaly_v03_preformal_saved_row_reread as reread
from . import anomaly_v03_preformal_job_tree_owner as job_owner
from . import anomaly_v03_reader_evidence as observed


ROOT = Path(__file__).resolve().parents[2]
REQUEST_FORMAT = 'anomaly-v03-preformal-two-slot-owned-cli-request-v1'
RECEIPT_FORMAT = 'anomaly-v03-preformal-two-slot-owned-cli-receipt-v1'
PHASES = ('run-budget', 'saved-reread')
LIMITS = {'wall_seconds': 900, 'private_bytes': 1024**3,
          'output_bytes': 1024**2}
MAX_REQUEST = 32 * 1024
MAX_RECEIPT = 32 * 1024
MAX_SAVED = 2 * 1024**2


def _same(actual, expected, label):
    v.require(v.canonical_json(actual) == v.canonical_json(expected), label)


def _source_state(plan_raw, plan_pin, record_raws, count, head):
    result = metadata.reduce_journal(
        plan_raw, record_raws, expected_plan_pin=plan_pin,
        expected_record_count=count, expected_head_sha256=head)
    plan = v.strict_json(plan_raw)
    v.require(result['declared_completed_chunks'] <= 2,
              'two-slot smoke cannot consume later campaign chunks')
    return plan, result


def next_started_record(plan_raw, plan_pin, record_raws, *,
                        expected_record_count, expected_head_sha256,
                        manifest_pin, prior_generation_receipt_pin=None,
                        prior_reread_receipt_pin=None):
    """Return a record to pin and append externally before a native launch.

    No source or process is inspected here.  The caller retains the returned
    bytes and a count/head checkpoint outside the journal before launch.
    """
    plan, state = _source_state(
        plan_raw, plan_pin, record_raws, expected_record_count,
        expected_head_sha256)
    index = state['next_chunk_index']
    v.require(index in (0, 1) and state['latest_unfinished_state'] is None and
              state['failed_attempt_count'] == 0,
              'only a clean next slot 0 or 1 may start')
    if index == 1:
        previous = v.strict_json(record_raws[-1])
        v.require(previous['state'] == 'completed' and len(record_raws) >= 2,
                  'previous slot completed record required')
        reproduced = completion_record(
            plan_raw, plan_pin, record_raws[:-1],
            expected_record_count=expected_record_count - 1,
            expected_head_sha256=previous['previous_sha256'],
            generation_receipt_pin=prior_generation_receipt_pin,
            reread_receipt_pin=prior_reread_receipt_pin)
        v.require(reproduced == record_raws[-1],
                  'previous completed declaration differs from owned receipts')
    else:
        v.require(prior_generation_receipt_pin is None and
                  prior_reread_receipt_pin is None,
                  'slot 0 has no prior owned receipts')
    metadata._pin(manifest_pin, 'prelaunch invented manifest')
    record = metadata.make_record(
        plan_pin, expected_head_sha256, expected_record_count + 1,
        index, 1, 'started', metadata.attempt_root(plan, index, 1),
        manifest_pin, source_revision=plan['source']['revision'],
        runtime_tuple_sha256=plan['runtime_candidate']['tuple_sha256'])
    raw = metadata.encode_record(record)
    metadata.reduce_journal(
        plan_raw, [*record_raws, raw], expected_plan_pin=plan_pin,
        expected_record_count=expected_record_count + 1,
        expected_head_sha256=metadata.pin(raw)['sha256'])
    return raw


def _started(plan_raw, plan_pin, record_raws, count, head):
    plan, state = _source_state(plan_raw, plan_pin, record_raws, count, head)
    v.require(state['latest_unfinished_state'] == 'started' and
              state['failed_attempt_count'] == 0 and record_raws,
              'externally pinned current started record required')
    current = v.strict_json(record_raws[-1])
    v.require(current['chunk_index'] in (0, 1) and current['attempt'] == 1 and
              current['chunk_index'] == state['next_chunk_index'],
              'only first attempts in the two-slot smoke are executable')
    return plan, current


def _manifest(plan, current, raw, expected_pin):
    metadata._pin(expected_pin, 'external manifest')
    v.require(type(raw) is bytes and 0 < len(raw) <= 256 * 1024 and
              metadata.pin(raw) == expected_pin and
              current['manifest_pin'] == expected_pin,
              'started record/external manifest raw pin mismatch')
    manifest = v.strict_json(raw)
    v.require(raw == v.canonical_json(manifest) and
              type(manifest) is dict and
              set(manifest) == set(generated_trial_manifest_fields()),
              'canonical invented external manifest required')
    v.require(manifest['format'] == 'anomaly-v03-preformal-owned-generated-external-pins-v1' and
              manifest['scope'] == 'invented-registered-format-owned-generator-only' and
              manifest['root'] == current['attempt_root'] and
              manifest['chunk_index'] == current['chunk_index'] and
              manifest['revision'] == plan['source']['revision'] and
              manifest['recipe_id'] == metadata.RECIPE and
              manifest['invented_only'] is True and
              manifest['actual_registered_observations_read'] is False and
              manifest['formal_permission'] is False,
              'manifest differs from frozen invented slot')
    metadata.require_generator_source_subset(
        plan['source'], manifest['source'], generated.SOURCE_FILES)
    v.require(type(manifest['output_pins']) is dict and
              set(manifest['output_pins']) == metadata._output_names(
                  current['chunk_index']) and
              manifest['output_file_count'] == 22 and
              manifest['output_bytes'] == sum(
                  row['bytes'] for row in manifest['output_pins'].values()),
              'manifest saved logical inventory')
    for row in manifest['output_pins'].values():
        metadata._pin(row, 'invented output pin')
    _same(manifest['output_pins']['saved/registry.json'],
          plan['registry_pin'], 'frozen registry manifest pin')
    return manifest


def generated_trial_manifest_fields():
    # Importing the command-line module would make this controller depend on
    # command dispatch.  Keep its exact file contract local and explicit.
    return ('format', 'scope', 'root', 'revision', 'chunk_index', 'recipe_id',
            'source', 'source_snapshots', 'source_snapshot_pins',
            'output_pins', 'output_file_count', 'output_bytes',
            'invented_only', 'actual_registered_observations_read',
            'formal_permission')


def _paths(plan, current):
    attempt = Path(current['attempt_root'])
    code = attempt.name.removeprefix(metadata.ATTEMPT_PREFIX)
    v.require(re.fullmatch(r'[a-z][0-9a-z]{2}1', code) is not None,
              'short first-attempt code')
    parent = ROOT / 'artifacts'
    v.require(attempt.parent == parent and Path(plan['root']).parent == parent,
              'dedicated local artifacts paths required')
    manifest = parent / ('anomaly-v03-preformal-generated-pinsets-' +
                         code) / 'pins.json'
    reread_root = parent / ('anomaly-v03-preformal-saved-row-reread-' + code)
    return attempt, manifest, reread_root


def _control(plan, current, phase):
    v.require(phase in PHASES, 'fixed owned phase')
    return (Path(plan['root']) / 'control' /
            f"{current['chunk_index']:03d}-{current['attempt']}" / phase)


def _load_receipt(plan, current, phase, expected_pin):
    metadata._pin(expected_pin, 'external owned CLI receipt')
    raw = _pinned(_control(plan, current, phase) / 'receipt.json',
                  expected_pin, MAX_RECEIPT)
    value = v.strict_json(raw)
    expected_count = (current['sequence'] if current['state'] == 'started'
                      else current['sequence'] - 1)
    expected_head = (metadata.pin(metadata.encode_record(current))['sha256']
                     if current['state'] == 'started' else
                     current['previous_sha256'])
    v.require(raw == v.canonical_json(value) + b'\n' and
              type(value) is dict and value.get('format') == RECEIPT_FORMAT and
              value.get('scope') == 'invented-two-slot-owned-cli-only' and
              value.get('phase') == phase and
              value.get('anchor_pin') == metadata.pin(
                  metadata.encode_plan(plan)) and
              value.get('journal_count') == expected_count and
              value.get('journal_head_sha256') == expected_head and
              value.get('chunk_index') == current['chunk_index'] and
              value.get('attempt') == current['attempt'] and
              value.get('attempt_root') == current['attempt_root'] and
              value.get('manifest_pin') == current['manifest_pin'] and
              value.get('status') == 'verified' and
              value.get('cli_exit_confirmed') is True and
              value.get('formal_permission') is False and
              value.get('campaign_coherence_authenticated') is False,
              'saved owned CLI receipt context')
    monitor_raw = _pinned(_control(plan, current, phase) /
                          'supervision.json',
                          value['cli_supervision_pin'], MAX_RECEIPT)
    monitor = v.strict_json(monitor_raw)
    stdout_raw = _pinned(_control(plan, current, phase) /
                         'report.json', value['cli_stdout_pin'],
                         LIMITS['output_bytes'])
    v.require(monitor['status'] == 'complete' and
              monitor['exit_code'] == value['cli_exit_code'] == 0 and
              monitor['worker_exit_confirmed'] is True and
              monitor['job']['format'] ==
              'anomaly-v03-preformal-owned-cli-job-v1' and
              monitor['job']['assignment_confirmed'] is True and
              monitor['job']['root_resumed'] is True and
              monitor['job']['all_assigned_processes_exit_confirmed'] is True and
              monitor['job']['accounting']['active_processes'] == 0 and
              monitor['job']['individual_descendant_exit_codes_authenticated'] is False and
              monitor['job']['whole_tree_resource_budget_measured'] is False and
              type(value['cli_process']) is dict and
              type(value['cli_process'].get('creation_time_100ns')) is int and
              value['cli_process']['creation_time_100ns'] > 0 and
              type(value['cli_process'].get('start_token')) is str and
              re.fullmatch(r'[0-9a-f]{64}',
                           value['cli_process']['start_token']) is not None and
              monitor['worker_pid'] == value['cli_process']['pid'] and
              monitor['output'] == metadata.pin(stdout_raw),
              'saved direct CLI supervisor binding')
    request_path = (Path(plan['root']) / 'intents' /
                    f"{value['journal_count']:04d}-{phase}.json")
    request_raw = _pinned(request_path, value['request_pin'], MAX_REQUEST)
    request = v.strict_json(request_raw)
    stderr_raw = _pinned(_control(plan, current, phase) /
                         'stderr.json', value['cli_stderr_pin'],
                         LIMITS['output_bytes'])
    v.require(request_raw == encode_request(request) and
              request['anchor_pin'] == value['anchor_pin'] and
              request['journal_count'] == expected_count and
              request['journal_head_sha256'] ==
              value['journal_head_sha256'] and
              request['chunk_index'] == current['chunk_index'] and
              request['attempt_root'] == current['attempt_root'] and
              request['manifest_pin'] == current['manifest_pin'] and
              request['phase'] == phase and
              monitor['argv'] == request['argv'] and
              monitor['limits'] == LIMITS and
              monitor['observation_errors'] == [] and
              monitor['stop_reason'] is None and
              monitor['runtime_before'] ==
              plan['runtime_candidate']['tuple'] and
              monitor['runtime_after'] ==
              plan['runtime_candidate']['tuple'] and
              monitor['output'] == value['cli_stdout_pin'] and
              monitor['stderr'] == value['cli_stderr_pin'] and
              stderr_raw == b'',
              'saved prelaunch invocation binding')
    inner = (_verify_generated(plan, request, value['cli_process']['pid'],
                               stdout_raw) if phase == 'run-budget' else
             _verify_reread(plan, request, value['cli_process']['pid'], stdout_raw))
    _same(value['inner'], inner, 'owned saved evidence receipt changed')
    return value


def _argv(phase, attempt, manifest, reread_root, manifest_pin,
          outer_result_pin, revision, python_executable, campaign_context):
    v.require(phase in PHASES, 'fixed native phase')
    v.require(type(python_executable) is str and
              Path(python_executable) == Path(sys.executable),
              'current Python executable required')
    if phase == 'run-budget':
        v.require(outer_result_pin is None, 'no prior result for generation')
        return [python_executable, '-B',
                str(ROOT / 'tools/preformal_owned_generated_trial.py'),
                'run-budget', '--root', str(attempt), '--manifest',
                str(manifest), '--manifest-sha256',
                manifest_pin['sha256'],
                *_campaign_argv(campaign_context)]
    metadata._pin(outer_result_pin, 'prior owned result')
    return [python_executable, '-B',
            str(ROOT / 'tools/preformal_saved_row_reread_trial.py'),
            '--source-root', str(attempt), '--output-root',
            str(reread_root), '--manifest-pin',
            f"{manifest_pin['bytes']}:{manifest_pin['sha256']}",
            '--outer-result-pin',
            f"{outer_result_pin['bytes']}:{outer_result_pin['sha256']}",
            '--revision', revision, *_campaign_argv(campaign_context)]


def _campaign_argv(context):
    return ['--campaign-plan-path', context['plan_path'],
            '--campaign-anchor-pin',
            f"{context['anchor_pin']['bytes']}:{context['anchor_pin']['sha256']}",
            '--campaign-chunk-index', str(context['chunk_index']),
            '--campaign-attempt', str(context['attempt'])]


def fixed_request(plan_raw, plan_pin, record_raws, *, expected_record_count,
                  expected_head_sha256, manifest_raw, manifest_pin,
                  phase, python_executable, outer_result_pin=None,
                  generation_receipt_pin=None):
    """Build an exact launch request; pin it outside output roots first."""
    plan, current = _started(plan_raw, plan_pin, record_raws,
                             expected_record_count, expected_head_sha256)
    _manifest(plan, current, manifest_raw, manifest_pin)
    attempt, manifest_path, reread_root = _paths(plan, current)
    if phase == 'saved-reread':
        prior = _load_receipt(plan, current, 'run-budget',
                              generation_receipt_pin)
        _same(outer_result_pin, prior['inner']['outer_result_pin'],
              'reread must use preceding owned generation result')
    else:
        v.require(phase == 'run-budget' and
                  generation_receipt_pin is None,
                  'generation has no prior owned receipt')
    campaign_context = {
        'plan_path': str(Path(plan['root']) / 'plan.json'),
        'anchor_pin': copy.deepcopy(plan_pin),
        'chunk_index': current['chunk_index'], 'attempt': current['attempt'],
    }
    return {
        'format': REQUEST_FORMAT, 'scope': 'invented-two-slot-owned-cli-only',
        'phase': phase, 'anchor_pin': copy.deepcopy(plan_pin),
        'journal_count': expected_record_count,
        'journal_head_sha256': expected_head_sha256,
        'chunk_index': current['chunk_index'], 'attempt': 1,
        'attempt_root': str(attempt), 'manifest_path': str(manifest_path),
        'manifest_pin': copy.deepcopy(manifest_pin),
        'reread_root': str(reread_root),
        'outer_result_pin': copy.deepcopy(outer_result_pin),
        'generation_receipt_pin': copy.deepcopy(generation_receipt_pin),
        'source_revision': plan['source']['revision'],
        'runtime_tuple_sha256': plan['runtime_candidate']['tuple_sha256'],
        'cwd': str(ROOT), 'argv': _argv(
            phase, attempt, manifest_path, reread_root, manifest_pin,
            outer_result_pin, plan['source']['revision'], python_executable,
            campaign_context),
        'invented_only': True,
        'actual_registered_observations_read': False,
        'formal_permission': False, 'campaign_evaluations_credited': 0,
    }


def encode_request(request):
    raw = v.canonical_json(request) + b'\n'
    v.require(len(raw) <= MAX_REQUEST, 'owned CLI request byte bound')
    return raw


def _read(path, maximum=MAX_SAVED):
    return observed._file(path, maximum)


def _pinned(path, expected, maximum=MAX_SAVED):
    raw = _read(path, maximum)
    _same(metadata.pin(raw), expected, 'saved raw pin ' + str(path))
    return raw


def _verified_inputs(plan, request, current):
    store._live_matches(plan)
    attempt = Path(request['attempt_root'])
    manifest = Path(request['manifest_path'])
    expected = request['manifest_pin']
    raw = _pinned(manifest, expected, generated.MAX_INVOCATION)
    v.require(_read(manifest.with_name('pins.json.sha256'), 128) ==
              (expected['sha256'] + '\n').encode('ascii'),
              'external manifest SHA sidecar changed')
    manifest_context = {'manifest_pin': expected,
                        'attempt_root': str(attempt),
                        'chunk_index': request['chunk_index']}
    value = _manifest(plan, manifest_context, raw, expected)
    snapshots = copied._decode_source_snapshots(value['source_snapshots'])
    generated._validated_snapshots(snapshots, plan['source']['revision'])
    _same(value['source_snapshot_pins'], {
        name: metadata.pin(content)
        for name, content in snapshots[plan['source']['revision']].items()},
        'external manifest source snapshot raw pins')
    source = generated._source(plan['source']['revision'])
    metadata.require_generator_source_subset(
        plan['source'], source, generated.SOURCE_FILES)
    actual_runtime = runtime.probe_runtime(ROOT)
    _same(actual_runtime, plan['runtime_candidate']['tuple'],
          'selected runtime changed')
    generated._validate_pins(generated._outputs(attempt,
                              request['chunk_index']), value['output_pins'])
    if request['phase'] == 'run-budget':
        v.require(not attempt.exists(), 'new attempt root required')
    else:
        v.require(attempt.is_dir() and
                  not Path(request['reread_root']).exists(),
                  'saved reread requires retained source and new output root')
        _load_receipt(plan, current, 'run-budget',
                      request['generation_receipt_pin'])
        _pinned(attempt / 'owned-generator/result.json',
                request['outer_result_pin'])


def _inner_role(root, role, cli_pid, expected_pid, expected_token,
                campaign_context, attempt_root, revision,
                invocation_format, reply_format):
    directory = root / ('owned-' + role)
    invocation_raw = _read(directory / 'invocation.json')
    invocation = v.strict_json(invocation_raw)
    monitor_raw = _read(directory / 'supervision.json')
    monitor = v.strict_json(monitor_raw)
    stdout_raw = _read(directory / 'worker/report.json')
    reply = v.strict_json(stdout_raw)
    v.require(monitor['status'] == 'complete' and
              monitor['exit_code'] == 0 and
              monitor['worker_exit_confirmed'] is True and
              monitor['worker_pid'] == expected_pid and
              monitor['output'] == metadata.pin(stdout_raw) and
              invocation.get('format') == invocation_format and
              reply.get('format') == reply_format and
              type(invocation.get('invocation_id')) is str and
              re.fullmatch(r'[0-9a-f]{64}',
                           invocation['invocation_id']) is not None and
              reply.get('invocation_id') == invocation['invocation_id'] and
              reply['process'] == {'pid': expected_pid,
                                   'parent_pid': cli_pid,
                                   'start_token': expected_token} and
              invocation.get('campaign_context') == campaign_context and
              reply.get('campaign_context') == campaign_context,
              'saved inner ' + role + ' process binding')
    child_context.verify_context(
        invocation['campaign_context'], attempt_root=attempt_root,
        revision=revision)
    return metadata.pin(monitor_raw), metadata.pin(stdout_raw)


def _verify_generated(plan, request, cli_pid, stdout_raw):
    root = Path(request['attempt_root'])
    printed = v.strict_json(stdout_raw)
    budget_raw = _read(root / 'budgeted-result.json')
    budget = v.strict_json(budget_raw)
    v.require(printed == {**budget, 'result_pin': metadata.pin(budget_raw)} and
              budget['status'] == 'verified' and
              budget['root'] == str(root) and
              budget['external_manifest_pin'] == request['manifest_pin'] and
              budget['source_revision'] == request['source_revision'] and
              budget['shared_budget_passed'] is True and
              budget['both_owned_exits_reported'] is True and
              budget['saved_role_evidence_bound'] is True and
              budget['resource_budget_pin'] ==
              _pinned_pin(root / 'resource-budget.json') and
              budget['formal_permission'] is False,
              'retained generated budget/result binding')
    outer_raw = _pinned(root / 'owned-generator/result.json',
                        budget['inner_result_pin'])
    outer = v.strict_json(outer_raw)
    manifest = v.strict_json(_pinned(Path(request['manifest_path']),
                                     request['manifest_pin']))
    pins = manifest['output_pins']
    v.require(outer['status'] == 'verified' and
              outer['generated_output_pins'] == pins and
              outer['owned_fixture_generator_exit_confirmed'] is True and
              outer['owned_fixture_reader_exit_confirmed'] is True and
              budget['generator_pid'] ==
              outer['owned_fixture_generator_pid'] and
              budget['reader_pid'] == outer['owned_fixture_reader_pid'] and
              budget['generator_start_token'] ==
              outer['owned_fixture_generator_start_token'] and
              budget['reader_start_token'] ==
              outer['owned_fixture_reader_start_token'] and
              outer['formal_permission'] is False,
              'owned generator and initial reader result')
    names = generated._outputs(root, request['chunk_index'])
    for logical, relative in names.items():
        _pinned(root / relative, pins[logical], copied._maximum(logical))
    evidence = {
        'outer_result': metadata.pin(outer_raw),
        'two_role_budget_result': metadata.pin(budget_raw),
        'two_role_budget_receipt': _pinned_pin(root / 'resource-budget.json'),
    }
    budget_receipt = v.strict_json(_pinned(
        root / 'resource-budget.json', budget['resource_budget_pin']))
    campaign_context = child_context.from_parts(
        Path(plan['root']) / 'plan.json', request['anchor_pin'],
        request['chunk_index'], request['attempt'], attempt_root=root,
        revision=request['source_revision'])
    for role, prefix in (('generator', 'generator'),
                         ('reader', 'initial_saved_reader')):
        token = outer['owned_fixture_' + role + '_start_token']
        pid = outer['owned_fixture_' + role + '_pid']
        supervision, output = _inner_role(
            root, role, cli_pid, pid, token, campaign_context, root,
            request['source_revision'],
            (generated.CAMPAIGN_INVOCATION if role == 'generator' else
             copied.CAMPAIGN_READER_INVOCATION),
            (generated.CAMPAIGN_FORMAT if role == 'generator' else
             copied.CAMPAIGN_READER_FORMAT))
        invocation = _pinned_pin(
            root / ('owned-' + role) / 'invocation.json')
        _same(invocation, outer[role + '_invocation_pin'],
              'saved ' + role + ' invocation pin')
        _same(output, outer[role + '_stdout_pin'],
              'saved ' + role + ' stdout pin')
        _same(supervision,
              budget_receipt['caller_reported_roles'][role]['result_pin'],
              'saved ' + role + ' budget monitor pin')
        evidence[prefix + '_invocation'] = invocation
        evidence[prefix + '_supervision'] = supervision
        evidence[prefix + '_stdout'] = output
    for label in ('receipt', 'report', 'savepoint', 'registry'):
        evidence['saved_' + label] = pins['saved/' + label + '.json']
    return {'evidence_pins': evidence, 'saved_output_pins': pins,
            'outer_result_pin': metadata.pin(outer_raw),
            'result_pin': metadata.pin(budget_raw)}


def _pinned_pin(path):
    return metadata.pin(_read(path))


def _verify_reread(plan, request, cli_pid, stdout_raw):
    root = Path(request['reread_root'])
    printed = v.strict_json(stdout_raw)
    raw = _read(root / 'result.json')
    result = v.strict_json(raw)
    v.require(printed == {**result, 'result_pin': metadata.pin(raw)} and
              result['status'] == 'verified' and
              result['source_root'] == request['attempt_root'] and
              result['output_root'] == str(root) and
              result['manifest_pin'] == request['manifest_pin'] and
              result['old_outer_result_pin'] == request['outer_result_pin'] and
              result['chunk_index'] == request['chunk_index'] and
              result['child_exit_confirmed'] is True and
              result['budget_passed'] is True and
              result['external_saved_payloads_reopened_in_child'] is True and
              result['fresh_saved_payload_bytes_rechecked_this_run'] is True and
              result['resource_budget_pin'] ==
              _pinned_pin(root / 'resource-budget.json') and
              result['formal_permission'] is False,
              'retained fresh saved reread binding')
    rows_raw = _pinned(root / 'rows.json', result['row_projection_pin'])
    rows = v.strict_json(rows_raw)
    v.require(rows['status'] == 'fixture_rows_bound_partial' and
              rows['chunk_index'] == request['chunk_index'] and
              rows['verified_evaluations'] == 6 and
              rows['latest_attempt'] == 1 and
              rows['actual_registered_observations_read'] is False and
              rows['formal_permission'] is False,
              'six invented saved rows from latest attempt')
    campaign_context = child_context.from_parts(
        Path(plan['root']) / 'plan.json', request['anchor_pin'],
        request['chunk_index'], request['attempt'],
        attempt_root=request['attempt_root'],
        revision=request['source_revision'])
    supervision, output = _inner_role(
        root, 'reader', cli_pid, result['child_pid'],
        result['child_start_token'], campaign_context,
        request['attempt_root'], request['source_revision'],
        reread.CAMPAIGN_INVOCATION_FORMAT,
        reread.CAMPAIGN_CHILD_FORMAT)
    invocation = _pinned_pin(root / 'owned-reader/invocation.json')
    _same(invocation, result['invocation_pin'],
          'fresh saved reader invocation pin')
    _same(supervision, result['reader_supervision_pin'],
          'fresh saved reader supervision pin')
    _same(output, result['child_stdout_pin'],
          'fresh saved reader stdout pin')
    evidence = {
        'fresh_reread_result': metadata.pin(raw),
        'fresh_reread_supervision': supervision,
        'fresh_reread_stdout': output,
        'fresh_reread_budget_receipt': _pinned_pin(
            root / 'resource-budget.json'),
        'fresh_reread_rows': metadata.pin(rows_raw),
        'rows': metadata.pin(rows_raw),
    }
    return {'evidence_pins': evidence,
            'outer_result_pin': request['outer_result_pin'],
        'fresh_reread_invocation_pin': invocation,
            'result_pin': metadata.pin(raw)}


def _failed_receipt(control, request, request_pin, plan_pin, report, launch,
                    reason, error_type=None, reconciled=False):
    """Persist a bounded stop observation; it never permits retry/next slot."""
    paths.regular_path(control, directory=True, missing=True)
    control.mkdir(parents=True, exist_ok=True)
    report_raw = v.canonical_json(report) if report is not None else None
    if report_raw is not None:
        v.require(len(report_raw) <= MAX_RECEIPT,
                  'failed CLI supervisor byte bound')
        io._exclusive(control / 'supervision.json', report_raw)
    value = {
        'format': RECEIPT_FORMAT, 'scope': 'invented-two-slot-owned-cli-only',
        'phase': request['phase'], 'request_pin': request_pin,
        'anchor_pin': plan_pin,
        'journal_count': request['journal_count'],
        'journal_head_sha256': request['journal_head_sha256'],
        'chunk_index': request['chunk_index'], 'attempt': 1,
        'attempt_root': request['attempt_root'],
        'manifest_pin': request['manifest_pin'],
        'cli_process': copy.deepcopy(launch),
        'cli_exit_code': report.get('exit_code') if report else None,
        'cli_exit_confirmed_in_report': (
            report.get('worker_exit_confirmed') is True if report else False),
        'cli_exit_reconciled_after_report': reconciled,
        'cli_supervision_pin': (metadata.pin(report_raw)
                                if report_raw is not None else None),
        'cli_stdout_pin': report.get('output') if report else None,
        'cli_stderr_pin': report.get('stderr') if report else None,
        'reason': reason, 'error_type': error_type,
        'status': 'failed', 'retry_authorized': False,
        'descendant_exit_confirmed': False,
        'invented_only': True,
        'actual_registered_observations_read': False,
        'campaign_evaluations_credited': 0,
        'formal_permission': False, 'campaign_coherence_authenticated': False,
        'full_end_to_end_budget_measured': False,
    }
    raw = v.canonical_json(value) + b'\n'
    v.require(len(raw) <= MAX_RECEIPT, 'failed owned CLI receipt byte bound')
    io._exclusive(control / 'receipt.json', raw)
    _pinned(control / 'receipt.json', metadata.pin(raw), MAX_RECEIPT)
    return value, metadata.pin(raw)


def execute_owned(request_path, expected_request_pin, plan_raw, plan_pin,
                  record_raws, *, expected_record_count,
                  expected_head_sha256):
    """Execute exactly one pinned CLI, retaining its direct owner observation.

    Successful return has a saved receipt in a fresh metadata control root.
    On an abnormal exit, the caller must stop; this function never retries.
    """
    plan, current = _started(plan_raw, plan_pin, record_raws,
                             expected_record_count, expected_head_sha256)
    request_path = paths.regular_path(Path(request_path))
    request_raw = _pinned(request_path, expected_request_pin, MAX_REQUEST)
    request = v.strict_json(request_raw)
    v.require(request_raw == encode_request(request),
              'canonical LF prelaunch request required')
    manifest_raw = _pinned(Path(request['manifest_path']),
                           request['manifest_pin'], generated.MAX_INVOCATION)
    wanted = fixed_request(
        plan_raw, plan_pin, record_raws,
        expected_record_count=expected_record_count,
        expected_head_sha256=expected_head_sha256,
        manifest_raw=manifest_raw, manifest_pin=request['manifest_pin'],
        phase=request['phase'], python_executable=sys.executable,
        outer_result_pin=request['outer_result_pin'],
        generation_receipt_pin=request['generation_receipt_pin'])
    _same(request, wanted, 'fixed two-slot owned CLI request')
    v.require(request['anchor_pin'] == plan_pin and
              request['chunk_index'] == current['chunk_index'],
              'prelaunch request anchor/slot')
    v.require(request_path.parent == Path(plan['root']) / 'intents' and
              request_path.name ==
              f"{expected_record_count:04d}-{request['phase']}.json",
              'dedicated prelaunch intention location')
    control = _control(plan, current, request['phase'])
    paths.regular_path(control, directory=True, missing=True)
    v.require(not control.exists(), 'new owned CLI control root required')
    control.parent.mkdir(parents=True, exist_ok=True)
    launch = {}
    try:
        _verified_inputs(plan, request, current)
    except (ValueError, OSError, KeyError, TypeError, IndexError) as error:
        return _failed_receipt(
            control, request, expected_request_pin, plan_pin, None, launch,
            'integrity', type(error).__name__)

    def boundary():
        _pinned(request_path, expected_request_pin, MAX_REQUEST)
        _verified_inputs_before_or_after(plan, request)

    def on_started(process):
        launch.update(observed.creation_observation(
            process.pid, process._handle))

    try:
        with platform._platform_scope():
            report = job_owner.supervise_cli(
                request['argv'], ROOT, control, LIMITS,
                stdout_name='report.json',
                runtime_probe=lambda: runtime.probe_runtime(ROOT),
                boundary=boundary, on_started=on_started)
    except (ValueError, OSError, TypeError) as error:
        return _failed_receipt(
            control, request, expected_request_pin, plan_pin, None,
            launch, 'verification_failed', type(error).__name__)
    if not (report['status'] == 'complete' and report['exit_code'] == 0 and
            report['worker_exit_confirmed'] is True and
            report['job']['format'] ==
            'anomaly-v03-preformal-owned-cli-job-v1' and
            report['job']['assignment_confirmed'] is True and
            report['job']['root_resumed'] is True and
            report['job']['all_assigned_processes_exit_confirmed'] is True and
            report['job']['accounting']['active_processes'] == 0 and
            report['job']['individual_descendant_exit_codes_authenticated'] is False and
            report['job']['whole_tree_resource_budget_measured'] is False and
            report['worker_pid'] == launch.get('pid') and
            type(launch.get('start_token')) is str and
            not report['observation_errors'] and
            report['stderr'] is not None and
            report['stderr']['bytes'] == 0):
        return _failed_receipt(
            control, request, expected_request_pin, plan_pin, report, launch,
            'resource_limit' if report.get('stop_reason') in
            ('time_limit', 'memory_limit', 'output_limit') else 'worker_exit')
    try:
        stdout_raw = _pinned(control / 'report.json', report['output'],
                             LIMITS['output_bytes'])
        inner = (_verify_generated(plan, request, launch['pid'], stdout_raw)
                 if request['phase'] == 'run-budget' else
                 _verify_reread(plan, request, launch['pid'], stdout_raw))
    except (ValueError, OSError, KeyError, TypeError, IndexError) as error:
        return _failed_receipt(
            control, request, expected_request_pin, plan_pin, report, launch,
            'verification_failed', type(error).__name__)
    value = {
        'format': RECEIPT_FORMAT, 'scope': 'invented-two-slot-owned-cli-only',
        'phase': request['phase'], 'request_pin': expected_request_pin,
        'anchor_pin': plan_pin,
        'journal_count': expected_record_count,
        'journal_head_sha256': expected_head_sha256,
        'chunk_index': request['chunk_index'], 'attempt': 1,
        'attempt_root': request['attempt_root'],
        'manifest_pin': request['manifest_pin'],
        'cli_process': launch, 'cli_exit_code': report['exit_code'],
        'cli_exit_confirmed': True, 'cli_stdout_pin': report['output'],
        'cli_stderr_pin': report['stderr'],
        'cli_supervision_pin': metadata.pin(v.canonical_json(report)),
        'inner': inner, 'status': 'verified', 'invented_only': True,
        'actual_registered_observations_read': False,
        'campaign_evaluations_credited': 0,
        'formal_permission': False, 'campaign_coherence_authenticated': False,
        'full_end_to_end_budget_measured': False,
    }
    monitor_raw = v.canonical_json(report)
    io._exclusive(control / 'supervision.json', monitor_raw)
    raw = v.canonical_json(value) + b'\n'
    v.require(len(raw) <= MAX_RECEIPT, 'owned CLI receipt byte bound')
    io._exclusive(control / 'receipt.json', raw)
    _pinned(control / 'receipt.json', metadata.pin(raw), MAX_RECEIPT)
    return value, metadata.pin(raw)


def failed_record(plan_raw, plan_pin, record_raws, *,
                  expected_record_count, expected_head_sha256,
                  failed_receipt_pin, phase):
    """Declare a terminal failed attempt from its saved stop receipt."""
    plan, current = _started(plan_raw, plan_pin, record_raws,
                             expected_record_count, expected_head_sha256)
    v.require(phase in PHASES, 'failed phase')
    metadata._pin(failed_receipt_pin, 'external failed receipt')
    raw = _pinned(_control(plan, current, phase) / 'receipt.json',
                  failed_receipt_pin, MAX_RECEIPT)
    receipt = v.strict_json(raw)
    v.require(raw == v.canonical_json(receipt) + b'\n' and
              receipt['format'] == RECEIPT_FORMAT and
              receipt['status'] == 'failed' and
              receipt['phase'] == phase and
              receipt['anchor_pin'] == plan_pin and
              receipt['journal_count'] == expected_record_count and
              receipt['journal_head_sha256'] == expected_head_sha256 and
              receipt['chunk_index'] == current['chunk_index'] and
              receipt['attempt_root'] == current['attempt_root'] and
              receipt['manifest_pin'] == current['manifest_pin'] and
              receipt['retry_authorized'] is False and
              receipt['descendant_exit_confirmed'] is False and
              receipt['formal_permission'] is False and
              receipt['reason'] in ('worker_exit', 'resource_limit',
                                    'verification_failed', 'integrity'),
              'terminal owned failure receipt')
    record = metadata.make_record(
        plan_pin, expected_head_sha256, expected_record_count + 1,
        current['chunk_index'], current['attempt'], 'failed',
        current['attempt_root'], current['manifest_pin'],
        source_revision=plan['source']['revision'],
        runtime_tuple_sha256=plan['runtime_candidate']['tuple_sha256'],
        reason=receipt['reason'])
    result = metadata.encode_record(record)
    metadata.reduce_journal(
        plan_raw, [*record_raws, result], expected_plan_pin=plan_pin,
        expected_record_count=expected_record_count + 1,
        expected_head_sha256=metadata.pin(result)['sha256'])
    return result


def _verified_inputs_before_or_after(plan, request):
    # An output root is expected to change after launch, so do not rerun the
    # new-root preflight check in the supervisor's postflight boundary.
    _pinned(Path(request['manifest_path']), request['manifest_pin'],
            generated.MAX_INVOCATION)
    store._live_matches(plan)
    metadata.require_generator_source_subset(
        plan['source'], generated._source(plan['source']['revision']),
        generated.SOURCE_FILES)
    _same(runtime.probe_runtime(ROOT), plan['runtime_candidate']['tuple'],
          'owned CLI runtime changed')


def completion_record(plan_raw, plan_pin, record_raws, *,
                      expected_record_count, expected_head_sha256,
                      generation_receipt_pin, reread_receipt_pin):
    """Make a declaration from two pinned owned receipts, for external append."""
    plan, current = _started(plan_raw, plan_pin, record_raws,
                             expected_record_count, expected_head_sha256)
    generation_receipt = _load_receipt(
        plan, current, 'run-budget', generation_receipt_pin)
    reread_receipt = _load_receipt(
        plan, current, 'saved-reread', reread_receipt_pin)
    for receipt, phase in ((generation_receipt, 'run-budget'),
                           (reread_receipt, 'saved-reread')):
        v.require(type(receipt) is dict and
                  receipt['format'] == RECEIPT_FORMAT and
                  receipt['status'] == 'verified' and
                  receipt['phase'] == phase and
                  receipt['anchor_pin'] == plan_pin and
                  receipt['journal_head_sha256'] == expected_head_sha256 and
                  receipt['journal_count'] == expected_record_count and
                  receipt['chunk_index'] == current['chunk_index'] and
                  receipt['attempt_root'] == current['attempt_root'] and
                  receipt['manifest_pin'] == current['manifest_pin'] and
                  receipt['cli_exit_confirmed'] is True and
                  receipt['formal_permission'] is False,
                  'verified owned receipt context')
    _same(reread_receipt['inner']['evidence_pins']['rows'],
          reread_receipt['inner']['evidence_pins']['fresh_reread_rows'],
          'fresh saved row pin')
    _same(reread_receipt['inner']['result_pin'],
          reread_receipt['inner']['evidence_pins']['fresh_reread_result'],
          'reread result pin')
    _same(generation_receipt['inner']['outer_result_pin'],
          reread_receipt['inner']['outer_result_pin'],
          'generation to reread result pin')
    evidence = {**generation_receipt['inner']['evidence_pins'],
                **reread_receipt['inner']['evidence_pins']}
    record = metadata.make_record(
        plan_pin, expected_head_sha256, expected_record_count + 1,
        current['chunk_index'], 1, 'completed', current['attempt_root'],
        current['manifest_pin'], source_revision=plan['source']['revision'],
        runtime_tuple_sha256=plan['runtime_candidate']['tuple_sha256'],
        evidence_pins=evidence,
        saved_output_pins=generation_receipt['inner']['saved_output_pins'])
    raw = metadata.encode_record(record)
    metadata.reduce_journal(
        plan_raw, [*record_raws, raw], expected_plan_pin=plan_pin,
        expected_record_count=expected_record_count + 1,
        expected_head_sha256=metadata.pin(raw)['sha256'])
    return raw
