"""Pure, fail-closed prepare receipts for an invented campaign attempt.

These receipts describe a proposed CLI call and its reported outcome.  They do
not observe the operating system, prove that the intention preceded launch, or
authorize the generator.  The owner must pin the raw intention externally
before starting prepare and retain process evidence separately.
"""
from __future__ import annotations

import copy
from pathlib import Path, PureWindowsPath

from . import anomaly_v03 as v
from . import anomaly_v03_consumer_evidence as evidence
from . import anomaly_v03_preformal_campaign_metadata as campaign
from . import anomaly_v03_preformal_owned_generated_attempt as generated
from . import anomaly_v03_preformal_owned_saved_attempt as copied


INTENTION_FORMAT = 'anomaly-v03-preformal-invented-prepare-intention-v1'
OUTCOME_FORMAT = 'anomaly-v03-preformal-invented-prepare-outcome-v1'
CHECK_FORMAT = 'anomaly-v03-preformal-invented-prepare-check-v1'
MAX_INTENTION = 4096
MAX_OUTCOME = 2048
MAX_MANIFEST = 256 * 1024
MANIFEST_FORMAT = 'anomaly-v03-preformal-owned-generated-external-pins-v1'
MANIFEST_FIELDS = {
    'format', 'scope', 'root', 'revision', 'chunk_index', 'recipe_id',
    'source', 'source_snapshots', 'source_snapshot_pins', 'output_pins',
    'output_file_count', 'output_bytes', 'invented_only',
    'actual_registered_observations_read', 'formal_permission',
}
INTENTION_FIELDS = {
    'format', 'scope', 'anchor_pin', 'chunk_index', 'attempt',
    'identity_sha256', 'attempt_root', 'manifest_path', 'sidecar_path',
    'python_executable', 'cwd', 'argv', 'expected_absent_paths',
    'source_revision', 'runtime_tuple_sha256', 'invented_only',
    'registered_seed_consumed', 'launch_authorized', 'formal_permission',
}
OUTCOME_FIELDS = {
    'format', 'scope', 'intention_pin', 'state', 'exit_code',
    'process_observation_pin', 'manifest_pin', 'sidecar_pin', 'reason',
    'invented_only', 'launch_authorized', 'formal_permission',
}
FAILURE_REASONS = {
    'precheck_rejected', 'prepare_launch_failed', 'prepare_exit',
    'prepare_timeout', 'prepare_interrupted', 'prepare_integrity',
    'prepare_owner_unreaped',
}


def _keys(value, expected, label):
    v.require(type(value) is dict and set(value) == expected,
              'exact ' + label + ' fields')


def _checked_plan(raw, expected_pin):
    campaign._pin(expected_pin, 'external campaign anchor')
    v.require(type(raw) is bytes and 0 < len(raw) <= campaign.MAX_PLAN_BYTES
              and campaign.pin(raw) == expected_pin,
              'external campaign anchor raw pin mismatch')
    plan = v.strict_json(raw)
    v.require(type(plan) is dict and raw == campaign.encode_plan(plan),
              'canonical campaign anchor required')
    return plan


def _python_path(value):
    v.require(type(value) is str and 0 < len(value) <= 512,
              'Python executable path')
    evidence._absolute(value)
    path = PureWindowsPath(value)
    v.require(path.is_absolute() and str(path) == value and
              path.suffix.casefold() == '.exe',
              'canonical absolute Windows Python executable required')
    return value


def paths(plan, chunk_index, attempt):
    """Return the deterministic new attempt and sibling pinset paths."""
    campaign.validate_plan(plan)
    root = campaign.attempt_root(plan, chunk_index, attempt)
    suffix = root.rsplit('-', 1)[1]
    artifacts = PureWindowsPath(plan['root']).parent
    manifest = str(artifacts / ('anomaly-v03-preformal-generated-pinsets-' +
                                suffix) / 'pins.json')
    return {'attempt_root': root, 'manifest_path': manifest,
            'sidecar_path': manifest + '.sha256'}


def make_intention(plan_raw, expected_plan_pin, chunk_index, attempt,
                   python_executable):
    """Describe one exact prepare CLI invocation without launching it."""
    plan = _checked_plan(plan_raw, expected_plan_pin)
    _python_path(python_executable)
    names = paths(plan, chunk_index, attempt)
    cwd = str(PureWindowsPath(plan['root']).parent.parent)
    argv = [python_executable, '-B',
            'tools/preformal_owned_generated_trial.py', 'prepare',
            '--root', names['attempt_root'], '--manifest',
            names['manifest_path'], '--chunk-index', str(chunk_index)]
    return {
        'format': INTENTION_FORMAT, 'scope': campaign.SCOPE,
        'anchor_pin': copy.deepcopy(expected_plan_pin),
        'chunk_index': chunk_index, 'attempt': attempt,
        'identity_sha256': plan['chunks'][chunk_index]['identities_sha256'],
        **names, 'python_executable': python_executable, 'cwd': cwd,
        'argv': argv,
        'expected_absent_paths': [names['attempt_root'],
                                  names['manifest_path'],
                                  names['sidecar_path']],
        'source_revision': plan['source']['revision'],
        'runtime_tuple_sha256': plan['runtime_candidate']['tuple_sha256'],
        'invented_only': True, 'registered_seed_consumed': False,
        'launch_authorized': False, 'formal_permission': False,
    }


def encode_intention(intention):
    _keys(intention, INTENTION_FIELDS, 'prepare intention')
    raw = v.canonical_json(intention) + b'\n'
    v.require(len(raw) <= MAX_INTENTION, 'prepare intention byte bound')
    return raw


def make_outcome(intention_pin, state, *, exit_code=None,
                 process_observation_pin=None, manifest_pin=None,
                 sidecar_pin=None, reason=None):
    """Describe a prepare outcome, including failure before any manifest."""
    campaign._pin(intention_pin, 'external prepare intention')
    return {
        'format': OUTCOME_FORMAT, 'scope': campaign.SCOPE,
        'intention_pin': copy.deepcopy(intention_pin), 'state': state,
        'exit_code': exit_code,
        'process_observation_pin': copy.deepcopy(process_observation_pin),
        'manifest_pin': copy.deepcopy(manifest_pin),
        'sidecar_pin': copy.deepcopy(sidecar_pin), 'reason': reason,
        'invented_only': True, 'launch_authorized': False,
        'formal_permission': False,
    }


def encode_outcome(outcome):
    _keys(outcome, OUTCOME_FIELDS, 'prepare outcome')
    raw = v.canonical_json(outcome) + b'\n'
    v.require(len(raw) <= MAX_OUTCOME, 'prepare outcome byte bound')
    return raw


def _checked_raw(raw, expected_pin, maximum, label):
    campaign._pin(expected_pin, 'external ' + label)
    v.require(type(raw) is bytes and 0 < len(raw) <= maximum and
              campaign.pin(raw) == expected_pin,
              'external ' + label + ' raw pin mismatch')
    item = v.strict_json(raw)
    v.require(type(item) is dict and raw == v.canonical_json(item) + b'\n',
              'canonical LF ' + label + ' required')
    return item


def _manifest(raw, expected_pin, intention):
    campaign._pin(expected_pin, 'prepare manifest')
    v.require(type(raw) is bytes and 0 < len(raw) <= MAX_MANIFEST and
              campaign.pin(raw) == expected_pin,
              'prepare manifest raw pin mismatch')
    manifest = v.strict_json(raw)
    _keys(manifest, MANIFEST_FIELDS, 'prepare manifest')
    v.require(raw == v.canonical_json(manifest),
              'canonical prepare manifest required')
    v.require(manifest['format'] == MANIFEST_FORMAT and
              manifest['scope'] ==
              'invented-registered-format-owned-generator-only' and
              manifest['root'] == intention['attempt_root'] and
              manifest['chunk_index'] == intention['chunk_index'] and
              manifest['revision'] == intention['source_revision'] and
              manifest['recipe_id'] == campaign.RECIPE and
              manifest['invented_only'] is True and
              manifest['actual_registered_observations_read'] is False and
              manifest['formal_permission'] is False,
              'prepare manifest campaign slot/scope mismatch')
    pins = manifest['output_pins']
    v.require(type(pins) is dict and
              set(pins) == campaign._output_names(intention['chunk_index'])
              and manifest['output_file_count'] == len(pins) == 22,
              'prepare manifest exact 22 output names required')
    generated._validate_pins(
        generated._outputs(Path(intention['attempt_root']),
                           intention['chunk_index']), pins)
    v.require(manifest['output_bytes'] ==
              sum(item['bytes'] for item in pins.values()),
              'prepare manifest output bytes mismatch')
    snapshots = copied._decode_source_snapshots(manifest['source_snapshots'])
    revision = intention['source_revision']
    v.require(set(snapshots) == {revision} and
              set(snapshots[revision]) == set(generated.SNAPSHOT_FILES),
              'prepare manifest exact generator source snapshots required')
    snapshot_pins = {name: campaign.pin(raw)
                     for name, raw in sorted(snapshots[revision].items())}
    v.require(manifest['source_snapshot_pins'] == snapshot_pins,
              'prepare manifest source snapshot raw pins mismatch')
    return manifest


def check_preflight(plan_raw, expected_plan_pin, intention_raw,
                    expected_intention_pin, outcome_raw,
                    expected_outcome_pin, *, manifest_raw=None,
                    sidecar_raw=None):
    """Check raw declarations; always return an unauthenticated boundary."""
    _checked_plan(plan_raw, expected_plan_pin)
    intention = _checked_raw(intention_raw, expected_intention_pin,
                             MAX_INTENTION, 'prepare intention')
    _keys(intention, INTENTION_FIELDS, 'prepare intention')
    wanted = make_intention(plan_raw, expected_plan_pin,
                            intention['chunk_index'], intention['attempt'],
                            intention['python_executable'])
    v.require(intention == wanted,
              'prepare intention changed from fixed campaign slot')
    outcome = _checked_raw(outcome_raw, expected_outcome_pin,
                           MAX_OUTCOME, 'prepare outcome')
    _keys(outcome, OUTCOME_FIELDS, 'prepare outcome')
    v.require(outcome['format'] == OUTCOME_FORMAT and
              outcome['scope'] == campaign.SCOPE and
              outcome['intention_pin'] == expected_intention_pin and
              outcome['invented_only'] is True and
              outcome['launch_authorized'] is False and
              outcome['formal_permission'] is False,
              'prepare outcome scope/intention mismatch')
    for name in ('process_observation_pin', 'manifest_pin', 'sidecar_pin'):
        item = outcome[name]
        if item is not None:
            campaign._pin(item, 'prepare ' + name)
    v.require(type(outcome['exit_code']) is int or
              outcome['exit_code'] is None, 'prepare exit code')
    v.require(outcome['exit_code'] is None or
              outcome['process_observation_pin'] is not None,
              'prepare exit code needs a process observation pin')
    state = outcome['state']
    v.require(state in ('prepared', 'failed'), 'prepare state')
    if state == 'prepared':
        v.require(outcome['exit_code'] == 0 and
                  outcome['process_observation_pin'] is not None and
                  outcome['manifest_pin'] is not None and
                  outcome['sidecar_pin'] is not None and
                  outcome['reason'] is None,
                  'prepare success evidence declaration incomplete')
        manifest = _manifest(manifest_raw, outcome['manifest_pin'], intention)
        campaign.require_generator_source_subset(
            _checked_plan(plan_raw, expected_plan_pin)['source'],
            manifest['source'], generated.SOURCE_FILES)
        expected_sidecar = (outcome['manifest_pin']['sha256'] + '\n').encode('ascii')
        v.require(sidecar_raw == expected_sidecar and
                  campaign.pin(sidecar_raw) == outcome['sidecar_pin'],
                  'prepare sidecar raw mismatch')
    else:
        v.require(type(outcome['reason']) is str and
                  outcome['reason'] in FAILURE_REASONS and
                  (outcome['exit_code'] != 0 or
                   (outcome['reason'] == 'prepare_integrity' and
                    outcome['process_observation_pin'] is not None)),
                  'prepare failure classification/exit mismatch')
        if outcome['manifest_pin'] is None:
            v.require(manifest_raw is None, 'unexpected failed manifest raw')
        else:
            v.require(type(manifest_raw) is bytes and
                      campaign.pin(manifest_raw) == outcome['manifest_pin'],
                      'partial failed manifest raw pin mismatch')
        if outcome['sidecar_pin'] is None:
            v.require(sidecar_raw is None, 'unexpected failed sidecar raw')
        else:
            v.require(type(sidecar_raw) is bytes and
                      campaign.pin(sidecar_raw) == outcome['sidecar_pin'],
                      'partial failed sidecar raw pin mismatch')
    return {
        'format': CHECK_FORMAT, 'scope': campaign.SCOPE,
        'state': state, 'chunk_index': intention['chunk_index'],
        'attempt': intention['attempt'],
        'anchor_pin': copy.deepcopy(expected_plan_pin),
        'intention_pin': copy.deepcopy(expected_intention_pin),
        'outcome_pin': copy.deepcopy(expected_outcome_pin),
        'manifest_pin': copy.deepcopy(outcome['manifest_pin']),
        'prepare_process_authenticated': False,
        'prelaunch_temporality_authenticated': False,
        'actual_registered_observations_read': False,
        'launch_authorized': False, 'resume_authorized': False,
        'formal_permission': False, 'campaign_evaluations_credited': 0,
    }
