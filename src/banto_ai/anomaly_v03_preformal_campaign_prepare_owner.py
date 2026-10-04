"""Own one invented campaign prepare CLI after its external intention is fixed.

This owns the prepare CLI Job tree. It does not run generation, read
registered observations, authenticate individual descendant exit codes,
or authorize a campaign.
The caller must supply the three pins retained by the separate campaign store.
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
from . import anomaly_v03_preformal_campaign_preflight as preflight
from . import anomaly_v03_preformal_campaign_store as store
from . import anomaly_v03_preformal_job_tree_owner as job_owner
from . import anomaly_v03_reader_evidence as observed


ROOT = Path(__file__).resolve().parents[2]
FORMAT = 'anomaly-v03-preformal-campaign-prepare-owner-v1'
CLAIM_FORMAT = 'anomaly-v03-preformal-campaign-prepare-owner-claim-v1'
OBSERVATION_FORMAT = 'anomaly-v03-preformal-campaign-prepare-process-observation-v1'
LIMITS = {'wall_seconds': 900, 'private_bytes': 1024**3,
          'output_bytes': 1024**2}
MAX_CONTROL = 32 * 1024
MAX_STDOUT = 1024**2


def _same(actual, expected, label):
    v.require(v.canonical_json(actual) == v.canonical_json(expected), label)


def _owner_root(plan):
    root = ROOT / 'artifacts' / (
        'anomaly-v03-preformal-campaign-prepare-' + plan['campaign_id'][:8])
    v.require(Path(plan['root']) == ROOT / 'artifacts' /
              ('anomaly-v03-preformal-campaign-' + plan['campaign_id'][:8]),
              'local invented campaign root required')
    paths.regular_path(root, directory=True, missing=True)
    v.require(not root.exists(), 'new prepare-owner root required')
    return root


def _pinned(path, pin, maximum, *, allow_empty=False):
    metadata._pin(pin, 'saved prepare-owner raw', positive=not allow_empty)
    raw = observed._file(path, maximum)
    _same(metadata.pin(raw), pin, 'saved prepare-owner raw pin')
    return raw


def _optional(path, maximum):
    paths.regular_path(path, missing=True)
    return observed._file(path, maximum) if path.exists() else None


def _save(root, name, raw, maximum=MAX_CONTROL):
    v.require(type(raw) is bytes and len(raw) <= maximum,
              'bounded prepare-owner ' + name)
    path = root / name
    io._exclusive(path, raw)
    v.require(observed._file(path, maximum) == raw,
              'retained prepare-owner ' + name)
    return metadata.pin(raw)


def _store(campaign_root, control_root, plan_pin, checkpoint_pin,
           intention_pin, *, absent):
    state = store.verify_store(
        campaign_root, control_root, expected_plan_pin=plan_pin,
        expected_checkpoint_pin=checkpoint_pin,
        expected_intention_pin=intention_pin,
        require_absent_targets=absent)
    v.require(state['status'] == 'preflight_intention_fixed' and
              state['checkpoint']['record_count'] == 0 and
              state['checkpoint']['head_sha256'] == plan_pin['sha256'] and
              state['intention']['chunk_index'] == 0 and
              state['intention']['attempt'] == 1 and
              state['intention']['python_executable'] == sys.executable and
              state['invented_only'] is True and
              state['formal_permission'] is False,
              'fixed invented slot-0 prepare store required')
    return state


def _targets_absent(intention):
    for name in intention['expected_absent_paths']:
        path = paths.regular_path(Path(name), missing=True)
        v.require(not path.exists(), 'prepare target already exists')
    pinset_root = Path(intention['manifest_path']).parent
    paths.regular_path(pinset_root, directory=True, missing=True)
    v.require(not pinset_root.exists(), 'new generated pinset root required')


def _stdout_claim(stdout_raw, intention, manifest, manifest_raw):
    value = v.strict_json(stdout_raw)
    v.require(type(value) is dict and set(value) == {
        'status', 'manifest', 'manifest_sha256', 'sha256_sidecar',
        'root', 'revision', 'output_file_count', 'output_bytes',
        'invented_only', 'formal_permission'} and
        value['status'] == 'prepared' and
        value['manifest'] == intention['manifest_path'] and
        value['manifest_sha256'] == metadata.pin(manifest_raw)['sha256'] and
        value['sha256_sidecar'] == intention['sidecar_path'] and
        value['root'] == intention['attempt_root'] and
        value['revision'] == intention['source_revision'] and
        value['output_file_count'] == manifest['output_file_count'] == 22 and
        value['output_bytes'] == manifest['output_bytes'] and
        value['invented_only'] is True and
        value['formal_permission'] is False,
        'owned prepare stdout/manifest binding')


def _completed_cli(report, launch, intention, plan, stdout_raw,
                   stderr_raw, manifest_raw, sidecar_raw):
    v.require(report['status'] == 'complete' and
              report['exit_code'] == 0 and
              report['worker_exit_confirmed'] is True and
              report['worker_pid'] == launch.get('pid') and
              type(launch.get('creation_time_100ns')) is int and
              launch['creation_time_100ns'] > 0 and
              re.fullmatch(r'[0-9a-f]{64}',
                           launch.get('start_token', '')) is not None and
              report['argv'] == intention['argv'] and
              report['limits'] == LIMITS and
              report['runtime_before'] == plan['runtime_candidate']['tuple'] and
              report['runtime_after'] == plan['runtime_candidate']['tuple'] and
              report['observation_errors'] == [] and
              report['stop_reason'] is None and
              report['job']['format'] ==
              'anomaly-v03-preformal-owned-cli-job-v1' and
              report['job']['assignment_confirmed'] is True and
              report['job']['root_resumed'] is True and
              report['job']['all_assigned_processes_exit_confirmed'] is True and
              report['job']['accounting']['active_processes'] == 0 and
              report['job']['individual_descendant_exit_codes_authenticated'] is False and
              report['job']['whole_tree_resource_budget_measured'] is False and
              stdout_raw is not None and stderr_raw == b'' and
              manifest_raw is not None and sidecar_raw is not None,
              'owned prepare CLI and bounded output required')


def _observation(root, claim_pin, launch, report, report_pin, reconciled):
    value = {
        'format': OBSERVATION_FORMAT,
        'scope': 'invented-direct-prepare-cli-only',
        'prelaunch_claim_pin': copy.deepcopy(claim_pin),
        'creation_observation': copy.deepcopy(launch) if launch else None,
        'creation_observation_pin': None,
        'supervision_pin': copy.deepcopy(report_pin),
        'direct_cli_exit_confirmed_in_report': (
            report.get('worker_exit_confirmed') is True if report else False),
        'direct_cli_exit_reconciled_after_report': reconciled,
        'direct_cli_exit_code': report.get('exit_code') if report else None,
        'descendant_exit_confirmed': False,
        'invented_only': True,
        'formal_permission': False,
    }
    if launch:
        launch_raw = _pinned(root / 'creation-observation.json',
                             metadata.pin(v.canonical_json(launch) + b'\n'),
                             MAX_CONTROL)
        v.require(launch_raw == v.canonical_json(launch) + b'\n',
                  'saved direct CLI creation observation')
        value['creation_observation_pin'] = metadata.pin(launch_raw)
    return _save(root, 'process-observation.json',
                 v.canonical_json(value) + b'\n')


def _finish(root, state, claim_pin, launch, report, reconciled,
            reason, *, manifest_raw=None, sidecar_raw=None):
    report_pin = (_save(root, 'supervision.json', v.canonical_json(report))
                  if report is not None else None)
    observation_pin = _observation(root, claim_pin, launch, report,
                                   report_pin, reconciled)
    manifest_pin = metadata.pin(manifest_raw) if manifest_raw is not None else None
    sidecar_pin = metadata.pin(sidecar_raw) if sidecar_raw is not None else None
    exit_code = report.get('exit_code') if report else None
    def checked_outcome(failure_reason):
        outcome = preflight.make_outcome(
            state['intention_pin'],
            'prepared' if failure_reason is None else 'failed',
            exit_code=exit_code, process_observation_pin=observation_pin,
            manifest_pin=manifest_pin, sidecar_pin=sidecar_pin,
            reason=failure_reason)
        raw = preflight.encode_outcome(outcome)
        check = preflight.check_preflight(
            state['plan_raw'], state['plan_pin'],
            state['intention_raw'], state['intention_pin'],
            raw, metadata.pin(raw), manifest_raw=manifest_raw,
            sidecar_raw=sidecar_raw)
        return outcome, raw, check

    try:
        outcome, outcome_raw, check = checked_outcome(reason)
    except (ValueError, KeyError, TypeError):
        if reason is not None:
            raise
        reason = 'prepare_integrity'
        outcome, outcome_raw, check = checked_outcome(reason)
    success = reason is None
    v.require(check['state'] == outcome['state'] and
              check['formal_permission'] is False and
              check['campaign_evaluations_credited'] == 0 and
              check['prepare_process_authenticated'] is False,
              'closed prepare preflight check')
    saved_outcome_pin = _save(root, 'outcome.json', outcome_raw,
                              preflight.MAX_OUTCOME)
    check_pin = _save(root, 'check.json', v.canonical_json(check) + b'\n')
    value = {
        'format': FORMAT, 'scope': 'invented-direct-prepare-cli-only',
        'status': 'prepared' if success else 'failed', 'reason': reason,
        'campaign_root': state['campaign_root'],
        'control_root': state['control_root'],
        'owner_root': str(root),
        'anchor_pin': copy.deepcopy(state['plan_pin']),
        'checkpoint_pin': copy.deepcopy(state['checkpoint_pin']),
        'intention_pin': copy.deepcopy(state['intention_pin']),
        'prelaunch_claim_pin': copy.deepcopy(claim_pin),
        'process_observation_pin': observation_pin,
        'supervision_pin': report_pin,
        'stdout_pin': report.get('output') if report else None,
        'stderr_pin': report.get('stderr') if report else None,
        'manifest_pin': manifest_pin, 'sidecar_pin': sidecar_pin,
        'outcome_pin': saved_outcome_pin, 'check_pin': check_pin,
        'direct_cli_pid': launch.get('pid') if launch else None,
        'direct_cli_start_token': launch.get('start_token') if launch else None,
        'direct_cli_exit_code': exit_code,
        'direct_cli_exit_confirmed': (
            report.get('worker_exit_confirmed') is True if report else False),
        'direct_cli_exit_reconciled_after_report': reconciled,
        'descendant_exit_confirmed': False,
        'retry_authorized': False, 'next_stage_authorized': False,
        'invented_only': True,
        'actual_registered_observations_read': False,
        'campaign_coherence_authenticated': False,
        'campaign_evaluations_credited': 0,
        'formal_permission': False,
    }
    receipt_raw = v.canonical_json(value) + b'\n'
    receipt_pin = _save(root, 'receipt.json', receipt_raw)
    return value, receipt_pin


def execute(campaign_root, control_root, *, expected_plan_pin,
            expected_checkpoint_pin, expected_intention_pin):
    """Run fixed prepare once; every returned failure prohibits a later stage."""
    state = _store(campaign_root, control_root, expected_plan_pin,
                   expected_checkpoint_pin, expected_intention_pin,
                   absent=True)
    plan = v.strict_json(state['plan_raw'])
    root = _owner_root(plan)
    root.mkdir()
    intention = state['intention']
    claim = {
        'format': CLAIM_FORMAT, 'scope': 'invented-direct-prepare-cli-only',
        'anchor_pin': copy.deepcopy(state['plan_pin']),
        'checkpoint_pin': copy.deepcopy(state['checkpoint_pin']),
        'intention_pin': copy.deepcopy(state['intention_pin']),
        'campaign_root': state['campaign_root'],
        'control_root': state['control_root'],
        'owner_root': str(root),
        'argv': intention['argv'], 'cwd': intention['cwd'],
        'limits': dict(LIMITS), 'targets_absent_at_claim': True,
        'invented_only': True, 'formal_permission': False,
    }
    claim_pin = _save(root, 'prelaunch-claim.json',
                      v.canonical_json(claim) + b'\n')
    launch = {}
    report = None
    reconciled = False
    reason = None
    manifest_raw = sidecar_raw = None
    try:
        _store(campaign_root, control_root, expected_plan_pin,
               expected_checkpoint_pin, expected_intention_pin,
               absent=True)
        _targets_absent(intention)
    except (ValueError, OSError, KeyError, TypeError) as error:
        reason = 'precheck_rejected'

    if reason is None:
        first_boundary = True

        def boundary():
            nonlocal first_boundary
            _pinned(root / 'prelaunch-claim.json', claim_pin, MAX_CONTROL)
            _store(campaign_root, control_root, expected_plan_pin,
                   expected_checkpoint_pin, expected_intention_pin,
                   absent=first_boundary)
            if first_boundary:
                _targets_absent(intention)
                first_boundary = False

        def on_started(process):
            launch.update(observed.creation_observation(
                process.pid, process._handle))
            _save(root, 'creation-observation.json',
                  v.canonical_json(launch) + b'\n')

        try:
            with platform._platform_scope():
                report = job_owner.supervise_cli(
                    intention['argv'], ROOT, root / 'worker', LIMITS,
                    stdout_name='report.json',
                    runtime_probe=lambda: runtime.probe_runtime(ROOT),
                    boundary=boundary, on_started=on_started)
        except KeyboardInterrupt:
            reason = 'prepare_interrupted'
        except (ValueError, OSError, KeyError, TypeError) as error:
            reason = 'prepare_launch_failed'

    if report is not None:
        if reason is None and (report.get('status') != 'complete' or
                               report.get('exit_code') != 0):
            reason = ('prepare_integrity' if report.get('exit_code') == 0 else
                      'prepare_timeout' if report.get('stop_reason') ==
                      'time_limit' else 'prepare_interrupted'
                      if report.get('stop_reason') == 'interrupted'
                      else 'prepare_exit')
        try:
            if report.get('output') is not None:
                stdout_raw = _pinned(root / 'worker/report.json',
                                     report['output'], MAX_STDOUT)
            else:
                stdout_raw = None
            if report.get('stderr') is not None:
                stderr_raw = _pinned(root / 'worker/stderr.json',
                                     report['stderr'], MAX_STDOUT,
                                     allow_empty=True)
            else:
                stderr_raw = None
            manifest_raw = _optional(Path(intention['manifest_path']),
                                     preflight.MAX_MANIFEST)
            sidecar_raw = _optional(Path(intention['sidecar_path']), 128)
            if reason is None:
                _completed_cli(report, launch, intention, plan, stdout_raw,
                               stderr_raw, manifest_raw, sidecar_raw)
                manifest = v.strict_json(manifest_raw)
                _stdout_claim(stdout_raw, intention, manifest, manifest_raw)
                v.require(not Path(intention['attempt_root']).exists(),
                          'prepare must not create generation attempt root')
                pinset_root = Path(intention['manifest_path']).parent
                v.require(set(item.name for item in pinset_root.iterdir()) ==
                          {'pins.json', 'pins.json.sha256'},
                          'prepare exact external pinset inventory')
                _store(campaign_root, control_root, expected_plan_pin,
                       expected_checkpoint_pin, expected_intention_pin,
                       absent=False)
                v.require(observed._file(
                    Path(intention['manifest_path']),
                    preflight.MAX_MANIFEST) == manifest_raw and
                    observed._file(Path(intention['sidecar_path']), 128) ==
                    sidecar_raw,
                    'postcheck external prepare manifest/sidecar changed')
        except (ValueError, OSError, KeyError, TypeError, IndexError):
            if reason is None:
                reason = 'prepare_integrity'
    if reason is None and report is None:
        reason = 'prepare_launch_failed'
    return _finish(root, state, claim_pin, launch, report, reconciled,
                   reason, manifest_raw=manifest_raw,
                   sidecar_raw=sidecar_raw)
