"""Durable, read-only verifiable prelaunch boundary for an invented campaign.

One ordinary writer creates a fresh plan root and a separate external control
root.  This module never starts prepare, reads registered observations, or
authenticates a producer campaign.  Any incomplete root is retained and
rejected; there is no repair, cleanup, or resume path here.
"""
from __future__ import annotations

import copy
import re
import subprocess
import sys
from pathlib import Path

from . import _anomaly_v03_io as io
from . import _anomaly_v03_runtime as paths
from . import anomaly_v03 as v
from . import anomaly_v03_platform_fixture_runtime as runtime
from . import anomaly_v03_preformal_campaign_metadata as metadata
from . import anomaly_v03_preformal_campaign_preflight as preflight
from . import anomaly_v03_preformal_owned_generated_attempt as generated


ROOT = Path(__file__).resolve().parents[2]
ANCHOR_FORMAT = 'anomaly-v03-preformal-campaign-external-anchor-pin-v1'
CHECKPOINT_FORMAT = 'anomaly-v03-preformal-campaign-external-checkpoint-v1'
INTENTION_PIN_FORMAT = 'anomaly-v03-preformal-campaign-external-intention-pin-v1'
STARTED_CHECKPOINT_FORMAT = 'anomaly-v03-preformal-campaign-started-checkpoint-v1'
SOURCE_EXTRA = (
    'src/banto_ai/anomaly_v03_preformal_campaign_metadata.py',
    'src/banto_ai/anomaly_v03_preformal_campaign_preflight.py',
    'src/banto_ai/anomaly_v03_preformal_campaign_controller.py',
    'src/banto_ai/anomaly_v03_preformal_campaign_store.py',
    'src/banto_ai/anomaly_v03_preformal_campaign_prepare_owner.py',
    'src/banto_ai/anomaly_v03_preformal_campaign_run_intent_store.py',
    'src/banto_ai/anomaly_v03_preformal_campaign_run_budget_owner.py',
    'src/banto_ai/anomaly_v03_preformal_campaign_reread_intent_store.py',
    'src/banto_ai/anomaly_v03_preformal_campaign_completion_store.py',
    'tools/preformal_campaign_store_trial.py',
    'tools/preformal_campaign_prepare_owner.py',
    'tools/preformal_campaign_run_intent_store.py',
    'tools/preformal_campaign_run_budget_owner.py',
    'tools/preformal_campaign_reread_intent_store.py',
    'tools/preformal_campaign_completion_store.py',
)
CONTROL_FILES = frozenset({
    'anchor-pin.json', 'checkpoint.json', 'preflight-intention.json',
    'preflight-intention-pin.json',
})
PLAN_FILES = frozenset({'plan.json', 'journal', 'pending'})
MAX_CONTROL = 4096
OWNER_FILES = frozenset({
    'check.json', 'creation-observation.json', 'outcome.json',
    'prelaunch-claim.json', 'process-observation.json', 'receipt.json',
    'supervision.json', 'worker',
})
OWNER_RECEIPT_FIELDS = frozenset({
    'actual_registered_observations_read', 'anchor_pin',
    'campaign_coherence_authenticated', 'campaign_evaluations_credited',
    'campaign_root', 'check_pin', 'checkpoint_pin', 'control_root',
    'descendant_exit_confirmed', 'direct_cli_exit_code',
    'direct_cli_exit_confirmed', 'direct_cli_exit_reconciled_after_report',
    'direct_cli_pid', 'direct_cli_start_token', 'formal_permission',
    'format', 'intention_pin', 'invented_only', 'manifest_pin',
    'next_stage_authorized', 'outcome_pin', 'owner_root',
    'prelaunch_claim_pin', 'process_observation_pin', 'reason',
    'retry_authorized', 'scope', 'sidecar_pin', 'status', 'stderr_pin',
    'stdout_pin', 'supervision_pin',
})
BUDGET_CANDIDATE = {
    'scope': 'invented-480-chunk-campaign-candidate',
    'status': 'not_adopted',
    'enforcement': 'sampled-and-cooperative-not-hard-quota',
    'limits': {
        'wall_seconds': 100000,
        'parent_private_bytes': 1024**3,
        'directory_bytes': 256 * 1024**3,
        'directory_entries': 1000000,
        'directory_depth': 16,
        'minimum_commit_headroom_bytes': 16 * 1024**2,
        'minimum_free_ram_bytes': 1024**3,
        'minimum_free_disk_bytes': 4 * 1024**3,
    },
}


def _same(actual, wanted, label):
    v.require(v.canonical_json(actual) == v.canonical_json(wanted), label)


def _lf(value, maximum=MAX_CONTROL):
    raw = v.canonical_json(value) + b'\n'
    v.require(0 < len(raw) <= maximum, 'bounded canonical control raw')
    return raw


def _read(path, maximum):
    path = paths.regular_path(path)
    v.require(0 < path.stat().st_size <= maximum, 'bounded stored raw')
    raw = io.read_regular(path)
    v.require(0 < len(raw) <= maximum, 'bounded stored read')
    return raw


def _read_empty_allowed(path, maximum):
    path = paths.regular_path(path)
    v.require(path.stat().st_size <= maximum, 'bounded stored raw')
    raw = io.read_regular(path)
    v.require(len(raw) <= maximum, 'bounded stored read')
    return raw


def _pinned(path, pin, maximum):
    metadata._pin(pin, 'external saved control')
    raw = _read(path, maximum)
    v.require(metadata.pin(raw) == pin, 'external raw pin mismatch')
    return raw


def _inventory(root, expected):
    root = paths.regular_path(root, directory=True)
    v.require({entry.name for entry in root.iterdir()} == expected,
              'prelaunch store exact inventory required')
    return root


def _roots(plan, control_root):
    metadata.validate_plan(plan)
    campaign = paths.regular_path(Path(plan['root']), directory=True, missing=True)
    controls = paths.regular_path(Path(control_root), directory=True, missing=True)
    artifacts = paths.regular_path(ROOT / 'artifacts', directory=True)
    code = plan['campaign_id'][:8]
    v.require(campaign.parent == artifacts and
              campaign.name == 'anomaly-v03-preformal-campaign-' + code and
              controls.parent == artifacts and
              controls.name == 'anomaly-v03-preformal-campaign-control-' + code and
              campaign != controls,
              'matching separate dedicated campaign/control roots required')
    return campaign, controls


def _targets_absent(intention):
    for name in intention['expected_absent_paths']:
        target = paths.regular_path(Path(name), missing=True)
        v.require(not target.exists(), 'preflight target already exists: ' + name)
    pinset_root = Path(intention['manifest_path']).parent
    paths.regular_path(pinset_root, directory=True, missing=True)
    v.require(not pinset_root.exists(), 'preflight pinset root already exists')


def _campaign_namespace_absent(plan):
    """Refuse a path code that overlaps any already retained attempt."""
    artifacts = paths.regular_path(ROOT / 'artifacts', directory=True)
    for index in range(480):
        for attempt in range(1, metadata.MAX_ATTEMPTS + 1):
            generated_root = Path(metadata.attempt_root(plan, index, attempt))
            suffix = generated_root.name.removeprefix(metadata.ATTEMPT_PREFIX)
            pinset_root = artifacts / ('anomaly-v03-preformal-generated-pinsets-' + suffix)
            for target in (generated_root, pinset_root):
                paths.regular_path(target, directory=True, missing=True)
                v.require(not target.exists(),
                          'campaign path code overlaps retained attempt/pinset')


def _anchor(plan, plan_pin):
    return {
        'format': ANCHOR_FORMAT, 'campaign_id': plan['campaign_id'],
        'campaign_root': plan['root'], 'plan_pin': copy.deepcopy(plan_pin),
        'invented_only': True, 'formal_permission': False,
    }


def _checkpoint(plan_pin):
    return {
        'format': CHECKPOINT_FORMAT, 'anchor_pin': copy.deepcopy(plan_pin),
        'record_count': 0, 'head_sha256': plan_pin['sha256'],
        'launch_authorized': False, 'resume_authorized': False,
        'formal_permission': False,
    }


def _started_checkpoint(plan_pin, initial_checkpoint_pin,
                        intention_pin, prepare_receipt_pin, record_pin):
    return {
        'format': STARTED_CHECKPOINT_FORMAT,
        'anchor_pin': copy.deepcopy(plan_pin),
        'previous_checkpoint_pin': copy.deepcopy(initial_checkpoint_pin),
        'preflight_intention_pin': copy.deepcopy(intention_pin),
        'prepare_receipt_pin': copy.deepcopy(prepare_receipt_pin),
        'started_record_pin': copy.deepcopy(record_pin),
        'record_count': 1, 'head_sha256': record_pin['sha256'],
        'launch_authorized': False, 'resume_authorized': False,
        'formal_permission': False, 'campaign_evaluations_credited': 0,
    }


def _intention_pin(plan_pin, pin):
    return {
        'format': INTENTION_PIN_FORMAT, 'anchor_pin': copy.deepcopy(plan_pin),
        'chunk_index': 0, 'attempt': 1, 'intention_pin': copy.deepcopy(pin),
        'launch_authorized': False, 'formal_permission': False,
    }


def _revision():
    raw = subprocess.check_output(
        ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'],
        stderr=subprocess.DEVNULL, timeout=10)
    revision = raw.decode('ascii').strip()
    v.require(re.fullmatch(r'[0-9a-f]{40}', revision) is not None,
              'full clean HEAD required')
    return revision


def _selected_source(revision):
    source = generated._source(revision)
    rows = list(source['selected_files'])
    existing = {row['path'] for row in rows}
    for name in SOURCE_EXTRA:
        if name in existing:
            continue
        working = _read(ROOT / name, 1024**2)
        committed = subprocess.check_output(
            ['git', '-C', str(ROOT), 'show', revision + ':' + name],
            stderr=subprocess.DEVNULL, timeout=10)
        v.require(working == committed, 'selected campaign source changed: ' + name)
        rows.append({'path': name, 'pin': metadata.pin(working)})
    v.require(len(rows) <= 64, 'selected campaign source count')
    return {'revision': revision,
            'selected_files': sorted(rows, key=lambda row: row['path']),
            'scope': 'selected-working-git-raw-only-not-source-closure'}


def _registry_pin():
    raw = _read(ROOT / 'examples/configs/anomaly-v03-freeze-registry.json',
                metadata.FROZEN_REGISTRY_BYTES)
    pin = metadata.pin(raw)
    v.require(pin == {'bytes': metadata.FROZEN_REGISTRY_BYTES,
                      'sha256': v.REGISTRY_RAW_SHA256},
              'frozen registry raw pin changed')
    return pin


def _runtime_candidate():
    value = runtime.probe_runtime(ROOT / 'artifacts')
    return {'candidate_id': 'win26h2-v1', 'tuple': value,
            'tuple_sha256': v.canonical_sha256(value),
            'status': 'not_adopted'}


def capture_current_plan(campaign_id, path_code):
    """Freeze selected clean HEAD, actual candidate runtime and registry."""
    revision = _revision()
    source = _selected_source(revision)
    artifacts = paths.regular_path(ROOT / 'artifacts', directory=True)
    root = artifacts / ('anomaly-v03-preformal-campaign-' + campaign_id[:8])
    plan = metadata.fixed_plan(
        campaign_id, str(root), path_code, _registry_pin(), source,
        _runtime_candidate(), BUDGET_CANDIDATE)
    _live_matches(plan)
    return plan


def _live_matches(plan):
    v.require(_revision() == plan['source']['revision'],
              'current HEAD differs from frozen plan')
    _same(_selected_source(plan['source']['revision']), plan['source'],
          'selected clean source differs from frozen plan')
    _same(_registry_pin(), plan['registry_pin'], 'registry changed')
    _same(_runtime_candidate(), plan['runtime_candidate'],
          'runtime candidate changed')
    _same(plan['budget_candidate'], BUDGET_CANDIDATE,
          'store budget candidate changed')


def create_store(plan, control_root, python_executable):
    """Write once, then re-read.  Partial writes stay visible and unusable."""
    campaign, controls = _roots(plan, control_root)
    v.require(not campaign.exists() and not controls.exists(),
              'fresh campaign and external control roots required')
    _live_matches(plan)
    v.require(python_executable == sys.executable,
              'current Python executable required')
    plan_raw = metadata.encode_plan(plan)
    plan_pin = metadata.pin(plan_raw)
    intention = preflight.make_intention(
        plan_raw, plan_pin, 0, 1, python_executable)
    intention_raw = preflight.encode_intention(intention)
    intention_pin = metadata.pin(intention_raw)
    checkpoint_raw = _lf(_checkpoint(plan_pin))
    checkpoint_pin = metadata.pin(checkpoint_raw)
    _campaign_namespace_absent(plan)
    _targets_absent(intention)

    campaign.mkdir()  # O_EXCL semantics for the root; never reuse partial roots.
    (campaign / 'journal').mkdir()
    (campaign / 'pending').mkdir()
    io._exclusive(campaign / 'pending' / 'plan.json', plan_raw)
    io._rename_no_replace(campaign / 'pending' / 'plan.json',
                          campaign / 'plan.json')
    controls.mkdir()
    io._exclusive(controls / 'anchor-pin.json', _lf(_anchor(plan, plan_pin)))
    io._exclusive(controls / 'checkpoint.json', checkpoint_raw)
    io._exclusive(controls / 'preflight-intention.json', intention_raw)
    io._exclusive(controls / 'preflight-intention-pin.json',
                  _lf(_intention_pin(plan_pin, intention_pin)))
    return verify_store(campaign, controls, expected_plan_pin=plan_pin,
                        expected_checkpoint_pin=checkpoint_pin,
                        expected_intention_pin=intention_pin)


def verify_store(campaign_root, control_root, *, expected_plan_pin,
                 expected_checkpoint_pin, expected_intention_pin,
                 require_absent_targets=True):
    """Read strict inventory and external pins; this never authorizes launch."""
    campaign = _inventory(campaign_root, PLAN_FILES)
    controls = _inventory(control_root, CONTROL_FILES)
    _inventory(campaign / 'journal', frozenset())
    _inventory(campaign / 'pending', frozenset())
    plan_raw = _pinned(campaign / 'plan.json', expected_plan_pin,
                       metadata.MAX_PLAN_BYTES)
    plan = v.strict_json(plan_raw)
    v.require(type(plan) is dict and plan_raw == metadata.encode_plan(plan),
              'canonical pinned campaign plan required')
    wanted_campaign, wanted_controls = _roots(plan, controls)
    v.require(campaign == wanted_campaign and controls == wanted_controls,
              'stored plan/control roots changed')
    anchor_raw = _read(controls / 'anchor-pin.json', MAX_CONTROL)
    v.require(anchor_raw == _lf(_anchor(plan, expected_plan_pin)),
              'external anchor pin control changed')
    checkpoint_raw = _pinned(controls / 'checkpoint.json',
                             expected_checkpoint_pin, MAX_CONTROL)
    checkpoint = v.strict_json(checkpoint_raw)
    v.require(checkpoint_raw == _lf(_checkpoint(expected_plan_pin)),
              'external count/head checkpoint changed')
    intention_raw = _pinned(controls / 'preflight-intention.json',
                            expected_intention_pin, preflight.MAX_INTENTION)
    intention = v.strict_json(intention_raw)
    v.require(type(intention) is dict and
              intention.get('python_executable') == sys.executable and
              intention_raw == preflight.encode_intention(intention) and
              intention_raw == preflight.encode_intention(
                  preflight.make_intention(plan_raw, expected_plan_pin,
                                           0, 1, sys.executable)),
              'fixed slot-0 preflight intention changed')
    intention_pin_raw = _read(controls / 'preflight-intention-pin.json',
                              MAX_CONTROL)
    v.require(intention_pin_raw == _lf(_intention_pin(
                  expected_plan_pin, expected_intention_pin)),
              'external intention pin control changed')
    state = metadata.reduce_journal(
        plan_raw, [], expected_plan_pin=expected_plan_pin,
        expected_record_count=checkpoint['record_count'],
        expected_head_sha256=checkpoint['head_sha256'])
    v.require(state['declared_completed_chunks'] == 0 and
              state['campaign_coherence_authenticated'] is False and
              state['launch_authorized'] is False and
              state['resume_authorized'] is False and
              state['formal_permission'] is False,
              'empty prelaunch metadata boundary')
    if require_absent_targets:
        _targets_absent(intention)
    _live_matches(plan)
    # Detect changes during inspection, including extra files or pending traces.
    _inventory(campaign, PLAN_FILES)
    _inventory(controls, CONTROL_FILES)
    _inventory(campaign / 'journal', frozenset())
    _inventory(campaign / 'pending', frozenset())
    for name, raw, limit in (
        ('plan.json', plan_raw, metadata.MAX_PLAN_BYTES),
        ('anchor-pin.json', anchor_raw, MAX_CONTROL),
        ('checkpoint.json', checkpoint_raw, MAX_CONTROL),
        ('preflight-intention.json', intention_raw, preflight.MAX_INTENTION),
        ('preflight-intention-pin.json', intention_pin_raw, MAX_CONTROL),
    ):
        parent = campaign if name == 'plan.json' else controls
        v.require(_read(parent / name, limit) == raw,
                  'prelaunch control changed during inspection')
    return {
        'status': 'preflight_intention_fixed',
        'campaign_root': str(campaign), 'control_root': str(controls),
        'plan_raw': plan_raw, 'plan_pin': copy.deepcopy(expected_plan_pin),
        'checkpoint_raw': checkpoint_raw,
        'checkpoint_pin': copy.deepcopy(expected_checkpoint_pin),
        'checkpoint': checkpoint,
        'intention_raw': intention_raw,
        'intention_pin': copy.deepcopy(expected_intention_pin),
        'intention': intention,
        'invented_only': True, 'actual_registered_observations_read': False,
        'campaign_coherence_authenticated': False,
        'launch_authorized': False, 'resume_authorized': False,
        'formal_permission': False, 'campaign_evaluations_credited': 0,
    }


def _prepared_owner(state, expected_prepare_receipt_pin, *,
                    require_attempt_absent=True):
    """Reopen the successful direct prepare evidence before journal mutation."""
    # Late import avoids a store/owner import cycle. The owner never runs here.
    from . import anomaly_v03_preformal_campaign_prepare_owner as owner

    plan = v.strict_json(state['plan_raw'])
    intention = state['intention']
    root = ROOT / 'artifacts' / (
        'anomaly-v03-preformal-campaign-prepare-' + plan['campaign_id'][:8])
    _inventory(root, OWNER_FILES)
    _inventory(root / 'worker', frozenset({'report.json', 'stderr.json'}))
    _inventory(Path(intention['manifest_path']).parent,
               frozenset({'pins.json', 'pins.json.sha256'}))
    if require_attempt_absent:
        v.require(not Path(intention['attempt_root']).exists(),
                  'attempt root appeared during prepare inspection')
    receipt_raw = _pinned(root / 'receipt.json', expected_prepare_receipt_pin,
                          owner.MAX_CONTROL)
    receipt = v.strict_json(receipt_raw)
    v.require(type(receipt) is dict and
              set(receipt) == OWNER_RECEIPT_FIELDS and
              receipt_raw == _lf(receipt, owner.MAX_CONTROL),
              'exact canonical owned prepare receipt required')
    _same({key: receipt[key] for key in (
        'campaign_root', 'control_root', 'owner_root', 'anchor_pin',
        'checkpoint_pin', 'intention_pin')}, {
        'campaign_root': state['campaign_root'],
        'control_root': state['control_root'], 'owner_root': str(root),
        'anchor_pin': state['plan_pin'],
        'checkpoint_pin': state['checkpoint_pin'],
        'intention_pin': state['intention_pin'],
    }, 'prepare receipt campaign/control/initial pins')
    v.require(receipt['format'] == owner.FORMAT and
              receipt['scope'] == 'invented-direct-prepare-cli-only' and
              receipt['status'] == 'prepared' and receipt['reason'] is None and
              receipt['direct_cli_exit_code'] == 0 and
              receipt['direct_cli_exit_confirmed'] is True and
              receipt['direct_cli_exit_reconciled_after_report'] is False and
              receipt['descendant_exit_confirmed'] is False and
              receipt['retry_authorized'] is False and
              receipt['next_stage_authorized'] is False and
              receipt['invented_only'] is True and
              receipt['actual_registered_observations_read'] is False and
              receipt['campaign_coherence_authenticated'] is False and
              receipt['campaign_evaluations_credited'] == 0 and
              receipt['formal_permission'] is False,
              'successful limited direct prepare receipt required')

    claim_raw = _pinned(root / 'prelaunch-claim.json',
                        receipt['prelaunch_claim_pin'], owner.MAX_CONTROL)
    claim = v.strict_json(claim_raw)
    v.require(claim_raw == _lf(claim, owner.MAX_CONTROL) and
              type(claim) is dict and set(claim) == {
                  'format', 'scope', 'anchor_pin', 'checkpoint_pin',
                  'intention_pin', 'campaign_root', 'control_root',
                  'owner_root', 'argv', 'cwd', 'limits',
                  'targets_absent_at_claim', 'invented_only',
                  'formal_permission'} and
              claim['format'] == owner.CLAIM_FORMAT and
              claim['scope'] == 'invented-direct-prepare-cli-only' and
              claim['anchor_pin'] == state['plan_pin'] and
              claim['checkpoint_pin'] == state['checkpoint_pin'] and
              claim['intention_pin'] == state['intention_pin'] and
              claim['campaign_root'] == state['campaign_root'] and
              claim['control_root'] == state['control_root'] and
              claim['owner_root'] == str(root) and
              claim['argv'] == intention['argv'] and
              claim['cwd'] == intention['cwd'] and
              claim['limits'] == owner.LIMITS and
              claim['targets_absent_at_claim'] is True and
              claim['invented_only'] is True and
              claim['formal_permission'] is False,
              'pinned direct prepare prelaunch claim mismatch')

    observation_raw = _pinned(root / 'process-observation.json',
                               receipt['process_observation_pin'],
                               owner.MAX_CONTROL)
    observation = v.strict_json(observation_raw)
    v.require(observation_raw == _lf(observation, owner.MAX_CONTROL) and
              type(observation) is dict and set(observation) == {
                  'format', 'scope', 'prelaunch_claim_pin',
                  'creation_observation', 'creation_observation_pin',
                  'supervision_pin', 'direct_cli_exit_confirmed_in_report',
                  'direct_cli_exit_reconciled_after_report',
                  'direct_cli_exit_code', 'descendant_exit_confirmed',
                  'invented_only', 'formal_permission'} and
              observation['format'] == owner.OBSERVATION_FORMAT and
              observation['scope'] == 'invented-direct-prepare-cli-only' and
              observation['prelaunch_claim_pin'] == receipt['prelaunch_claim_pin'] and
              observation['supervision_pin'] == receipt['supervision_pin'] and
              observation['direct_cli_exit_confirmed_in_report'] is True and
              observation['direct_cli_exit_reconciled_after_report'] is False and
              observation['direct_cli_exit_code'] == 0 and
              observation['descendant_exit_confirmed'] is False and
              observation['invented_only'] is True and
              observation['formal_permission'] is False,
              'saved direct prepare process observation mismatch')
    creation_raw = _pinned(root / 'creation-observation.json',
                            observation['creation_observation_pin'],
                            owner.MAX_CONTROL)
    creation = v.strict_json(creation_raw)
    v.require(creation_raw == _lf(creation, owner.MAX_CONTROL) and
              creation == observation['creation_observation'] and
              creation['pid'] == receipt['direct_cli_pid'] and
              creation['start_token'] == receipt['direct_cli_start_token'],
              'saved direct prepare creation observation mismatch')

    supervision_raw = _pinned(root / 'supervision.json',
                               receipt['supervision_pin'], owner.MAX_CONTROL)
    report = v.strict_json(supervision_raw)
    v.require(supervision_raw == v.canonical_json(report),
              'canonical direct prepare supervisor report required')
    stdout_raw = _pinned(root / 'worker' / 'report.json',
                          receipt['stdout_pin'], owner.MAX_STDOUT)
    metadata._pin(receipt['stderr_pin'], 'owned prepare stderr', positive=False)
    stderr_raw = _read_empty_allowed(root / 'worker' / 'stderr.json',
                                      owner.MAX_STDOUT)
    v.require(metadata.pin(stderr_raw) == receipt['stderr_pin'] and
              report['output'] == receipt['stdout_pin'] and
              report['stderr'] == receipt['stderr_pin'],
              'owned direct prepare stdout/stderr pins')
    manifest_raw = _pinned(Path(intention['manifest_path']),
                            receipt['manifest_pin'], preflight.MAX_MANIFEST)
    sidecar_raw = _pinned(Path(intention['sidecar_path']),
                           receipt['sidecar_pin'], 128)
    _inventory(Path(intention['manifest_path']).parent,
               frozenset({'pins.json', 'pins.json.sha256'}))
    if require_attempt_absent:
        v.require(not Path(intention['attempt_root']).exists(),
                  'prepare created attempt output before started record')
    owner._completed_cli(report, creation, intention, plan, stdout_raw,
                         stderr_raw, manifest_raw, sidecar_raw)
    manifest = v.strict_json(manifest_raw)
    owner._stdout_claim(stdout_raw, intention, manifest, manifest_raw)

    outcome_raw = _pinned(root / 'outcome.json', receipt['outcome_pin'],
                          preflight.MAX_OUTCOME)
    outcome = v.strict_json(outcome_raw)
    v.require(outcome_raw == preflight.encode_outcome(outcome) and
              outcome['state'] == 'prepared' and
              outcome['process_observation_pin'] ==
              receipt['process_observation_pin'] and
              outcome['manifest_pin'] == receipt['manifest_pin'] and
              outcome['sidecar_pin'] == receipt['sidecar_pin'],
              'owned prepare outcome pin binding')
    check = preflight.check_preflight(
        state['plan_raw'], state['plan_pin'],
        state['intention_raw'], state['intention_pin'],
        outcome_raw, receipt['outcome_pin'],
        manifest_raw=manifest_raw, sidecar_raw=sidecar_raw)
    check_raw = _pinned(root / 'check.json', receipt['check_pin'],
                        owner.MAX_CONTROL)
    v.require(check_raw == _lf(check, owner.MAX_CONTROL) and
              check['state'] == 'prepared' and
              check['campaign_evaluations_credited'] == 0 and
              check['formal_permission'] is False,
              'saved prepare preflight check mismatch')

    # Detect changed raw and directory contents before returning the manifest.
    _inventory(root, OWNER_FILES)
    _inventory(root / 'worker', frozenset({'report.json', 'stderr.json'}))
    _inventory(Path(intention['manifest_path']).parent,
               frozenset({'pins.json', 'pins.json.sha256'}))
    if require_attempt_absent:
        v.require(not Path(intention['attempt_root']).exists(),
                  'attempt root appeared during prepare inspection')
    for path, raw, maximum in (
        (root / 'receipt.json', receipt_raw, owner.MAX_CONTROL),
        (root / 'prelaunch-claim.json', claim_raw, owner.MAX_CONTROL),
        (root / 'process-observation.json', observation_raw, owner.MAX_CONTROL),
        (root / 'creation-observation.json', creation_raw, owner.MAX_CONTROL),
        (root / 'supervision.json', supervision_raw, owner.MAX_CONTROL),
        (root / 'worker' / 'report.json', stdout_raw, owner.MAX_STDOUT),
        (root / 'outcome.json', outcome_raw, preflight.MAX_OUTCOME),
        (root / 'check.json', check_raw, owner.MAX_CONTROL),
        (Path(intention['manifest_path']), manifest_raw, preflight.MAX_MANIFEST),
        (Path(intention['sidecar_path']), sidecar_raw, 128),
    ):
        v.require(_read(path, maximum) == raw,
                  'owned prepare raw changed during inspection')
    v.require(_read_empty_allowed(root / 'worker' / 'stderr.json',
                                   owner.MAX_STDOUT) == stderr_raw,
              'owned prepare stderr changed during inspection')
    return {
        'prepare_receipt_raw': receipt_raw,
        'prepare_receipt_pin': copy.deepcopy(expected_prepare_receipt_pin),
        'prepare_receipt': receipt,
        'manifest_raw': manifest_raw,
        'manifest_pin': copy.deepcopy(receipt['manifest_pin']),
    }


def append_started(campaign_root, control_root, *, expected_plan_pin,
                   expected_initial_checkpoint_pin, expected_intention_pin,
                   expected_prepare_receipt_pin):
    """Commit a single prepared slot-0 started declaration and new checkpoint.

    The journal rename precedes the external checkpoint write. A crash in
    either gap leaves a partial inventory and no operation here can recover or
    launch from it. The initial checkpoint is never changed.
    """
    from . import anomaly_v03_preformal_campaign_controller as controller

    state = verify_store(
        campaign_root, control_root,
        expected_plan_pin=expected_plan_pin,
        expected_checkpoint_pin=expected_initial_checkpoint_pin,
        expected_intention_pin=expected_intention_pin,
        require_absent_targets=False)
    owner = _prepared_owner(state, expected_prepare_receipt_pin)
    record_raw = controller.next_started_record(
        state['plan_raw'], state['plan_pin'], [],
        expected_record_count=0,
        expected_head_sha256=state['checkpoint']['head_sha256'],
        manifest_pin=owner['manifest_pin'])
    record_pin = metadata.pin(record_raw)
    report = metadata.reduce_journal(
        state['plan_raw'], [record_raw], expected_plan_pin=expected_plan_pin,
        expected_record_count=1,
        expected_head_sha256=record_pin['sha256'])
    v.require(report['latest_unfinished_state'] == 'started' and
              report['declared_completed_chunks'] == 0 and
              report['campaign_coherence_authenticated'] is False and
              report['launch_authorized'] is False and
              report['resume_authorized'] is False and
              report['campaign_evaluations_credited'] == 0 and
              report['formal_permission'] is False,
              'closed slot-0 started declaration required')
    checkpoint_raw = _lf(_started_checkpoint(
        expected_plan_pin, expected_initial_checkpoint_pin,
        expected_intention_pin, expected_prepare_receipt_pin,
        record_pin))
    next_checkpoint_pin = metadata.pin(checkpoint_raw)
    campaign = Path(state['campaign_root'])
    controls = Path(state['control_root'])
    (campaign / 'intents').mkdir()
    staged = campaign / 'pending' / '000001.json'
    committed = campaign / 'journal' / '000001.json'
    io._exclusive(staged, record_raw)
    v.require(_read(staged, metadata.MAX_RECORD_BYTES) == record_raw,
              'staged started record changed')
    io._rename_no_replace(staged, committed)
    io._exclusive(controls / 'checkpoint-000001.json', checkpoint_raw)
    return verify_started_store(
        campaign, controls,
        expected_plan_pin=expected_plan_pin,
        expected_initial_checkpoint_pin=expected_initial_checkpoint_pin,
        expected_intention_pin=expected_intention_pin,
        expected_prepare_receipt_pin=expected_prepare_receipt_pin,
        expected_started_record_pin=record_pin,
        expected_next_checkpoint_pin=next_checkpoint_pin)


def verify_started_store(campaign_root, control_root, *, expected_plan_pin,
                         expected_initial_checkpoint_pin,
                         expected_intention_pin, expected_prepare_receipt_pin,
                         expected_started_record_pin,
                         expected_next_checkpoint_pin,
                         expected_run_intent_pin=None):
    """Read the exact count-1 prelaunch boundary; never inspect a run result."""
    from . import anomaly_v03_preformal_campaign_controller as controller

    campaign = _inventory(campaign_root, PLAN_FILES | {'intents'})
    controls = _inventory(control_root,
                          CONTROL_FILES | {'checkpoint-000001.json'})
    _inventory(campaign / 'journal', frozenset({'000001.json'}))
    _inventory(campaign / 'pending', frozenset())
    intent_names = (frozenset() if expected_run_intent_pin is None else
                    frozenset({'0001-run-budget.json'}))
    _inventory(campaign / 'intents', intent_names)
    plan_raw = _pinned(campaign / 'plan.json', expected_plan_pin,
                       metadata.MAX_PLAN_BYTES)
    plan = v.strict_json(plan_raw)
    v.require(type(plan) is dict and plan_raw == metadata.encode_plan(plan),
              'canonical pinned campaign plan required')
    wanted_campaign, wanted_controls = _roots(plan, controls)
    v.require(campaign == wanted_campaign and controls == wanted_controls,
              'started plan/control roots changed')
    anchor_raw = _read(controls / 'anchor-pin.json', MAX_CONTROL)
    v.require(anchor_raw == _lf(_anchor(plan, expected_plan_pin)),
              'external anchor control changed')
    initial_checkpoint_raw = _pinned(
        controls / 'checkpoint.json', expected_initial_checkpoint_pin,
        MAX_CONTROL)
    v.require(initial_checkpoint_raw == _lf(_checkpoint(expected_plan_pin)),
              'initial count/head checkpoint changed')
    intention_raw = _pinned(controls / 'preflight-intention.json',
                            expected_intention_pin, preflight.MAX_INTENTION)
    intention = v.strict_json(intention_raw)
    v.require(type(intention) is dict and
              intention.get('python_executable') == sys.executable and
              intention_raw == preflight.encode_intention(
                  preflight.make_intention(plan_raw, expected_plan_pin,
                                           0, 1, sys.executable)) and
              _read(controls / 'preflight-intention-pin.json', MAX_CONTROL) ==
              _lf(_intention_pin(expected_plan_pin, expected_intention_pin)),
              'initial fixed intention changed')
    state = {
        'campaign_root': str(campaign), 'control_root': str(controls),
        'plan_raw': plan_raw, 'plan_pin': expected_plan_pin,
        'checkpoint_pin': expected_initial_checkpoint_pin,
        'intention_raw': intention_raw, 'intention_pin': expected_intention_pin,
        'intention': intention,
    }
    owner = _prepared_owner(state, expected_prepare_receipt_pin)
    record_raw = _pinned(campaign / 'journal' / '000001.json',
                          expected_started_record_pin,
                          metadata.MAX_RECORD_BYTES)
    v.require(record_raw == controller.next_started_record(
        plan_raw, expected_plan_pin, [], expected_record_count=0,
        expected_head_sha256=expected_plan_pin['sha256'],
        manifest_pin=owner['manifest_pin']),
        'journal started record differs from prepared manifest')
    journal_state = metadata.reduce_journal(
        plan_raw, [record_raw], expected_plan_pin=expected_plan_pin,
        expected_record_count=1,
        expected_head_sha256=expected_started_record_pin['sha256'])
    v.require(journal_state['latest_unfinished_state'] == 'started' and
              journal_state['declared_completed_chunks'] == 0 and
              journal_state['campaign_coherence_authenticated'] is False and
              journal_state['launch_authorized'] is False and
              journal_state['resume_authorized'] is False and
              journal_state['campaign_evaluations_credited'] == 0 and
              journal_state['formal_permission'] is False,
              'started journal remains unauthenticated')
    next_checkpoint_raw = _pinned(
        controls / 'checkpoint-000001.json', expected_next_checkpoint_pin,
        MAX_CONTROL)
    checkpoint = v.strict_json(next_checkpoint_raw)
    v.require(next_checkpoint_raw == _lf(_started_checkpoint(
        expected_plan_pin, expected_initial_checkpoint_pin,
        expected_intention_pin, expected_prepare_receipt_pin,
        expected_started_record_pin)),
        'new immutable count/head checkpoint changed')
    run_intent_raw = None
    if expected_run_intent_pin is not None:
        run_intent_raw = _pinned(
            campaign / 'intents' / '0001-run-budget.json',
            expected_run_intent_pin, controller.MAX_REQUEST)
        request = v.strict_json(run_intent_raw)
        v.require(run_intent_raw == controller.encode_request(request),
                  'canonical fixed run-budget request required')
    _live_matches(plan)
    # Recheck every mutable metadata path and exact inventories after the
    # owner/manifest inspection. Any pending or extra file blocks launch.
    _inventory(campaign, PLAN_FILES | {'intents'})
    _inventory(controls, CONTROL_FILES | {'checkpoint-000001.json'})
    _inventory(campaign / 'journal', frozenset({'000001.json'}))
    _inventory(campaign / 'pending', frozenset())
    _inventory(campaign / 'intents', intent_names)
    for path, raw, maximum in (
        (campaign / 'plan.json', plan_raw, metadata.MAX_PLAN_BYTES),
        (campaign / 'journal' / '000001.json', record_raw,
         metadata.MAX_RECORD_BYTES),
        (controls / 'anchor-pin.json', anchor_raw, MAX_CONTROL),
        (controls / 'checkpoint.json', initial_checkpoint_raw, MAX_CONTROL),
        (controls / 'checkpoint-000001.json', next_checkpoint_raw, MAX_CONTROL),
        (controls / 'preflight-intention.json', intention_raw,
         preflight.MAX_INTENTION),
        (controls / 'preflight-intention-pin.json',
         _lf(_intention_pin(expected_plan_pin, expected_intention_pin)),
         MAX_CONTROL),
    ):
        v.require(_read(path, maximum) == raw,
                  'started store raw changed during inspection')
    if run_intent_raw is not None:
        v.require(_read(campaign / 'intents' / '0001-run-budget.json',
                        controller.MAX_REQUEST) == run_intent_raw,
                  'run-budget request changed during inspection')
    return {
        'status': 'started_record_fixed',
        'campaign_root': str(campaign), 'control_root': str(controls),
        'plan_raw': plan_raw, 'plan_pin': copy.deepcopy(expected_plan_pin),
        'record_raws': [record_raw],
        'started_record_pin': copy.deepcopy(expected_started_record_pin),
        'initial_checkpoint_pin': copy.deepcopy(expected_initial_checkpoint_pin),
        'intention_pin': copy.deepcopy(expected_intention_pin),
        'prepare_receipt_raw': owner['prepare_receipt_raw'],
        'prepare_receipt_pin': copy.deepcopy(expected_prepare_receipt_pin),
        'manifest_raw': owner['manifest_raw'],
        'manifest_pin': owner['manifest_pin'],
        'checkpoint_raw': next_checkpoint_raw,
        'checkpoint': checkpoint,
        'next_checkpoint_pin': copy.deepcopy(expected_next_checkpoint_pin),
        'run_intent_raw': run_intent_raw,
        'run_intent_pin': copy.deepcopy(expected_run_intent_pin),
        'invented_only': True, 'actual_registered_observations_read': False,
        'campaign_coherence_authenticated': False,
        'launch_authorized': False, 'resume_authorized': False,
        'formal_permission': False, 'campaign_evaluations_credited': 0,
    }
