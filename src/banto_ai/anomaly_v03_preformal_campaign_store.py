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
SOURCE_EXTRA = (
    'src/banto_ai/anomaly_v03_preformal_campaign_metadata.py',
    'src/banto_ai/anomaly_v03_preformal_campaign_preflight.py',
    'src/banto_ai/anomaly_v03_preformal_campaign_controller.py',
    'src/banto_ai/anomaly_v03_preformal_campaign_store.py',
    'src/banto_ai/anomaly_v03_preformal_campaign_prepare_owner.py',
    'tools/preformal_campaign_store_trial.py',
    'tools/preformal_campaign_prepare_owner.py',
)
CONTROL_FILES = frozenset({
    'anchor-pin.json', 'checkpoint.json', 'preflight-intention.json',
    'preflight-intention-pin.json',
})
PLAN_FILES = frozenset({'plan.json', 'journal', 'pending'})
MAX_CONTROL = 4096
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
