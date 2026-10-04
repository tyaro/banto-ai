"""Freeze one invented slot-0 run-budget request outside its output roots.

The request is derived from an externally pinned started journal and a saved
prepare receipt. This module only stores and rereads launch metadata. It never
starts run-budget or authenticates a common producer campaign.
"""
from __future__ import annotations

import copy
from pathlib import Path
import re
import sys

from . import _anomaly_v03_io as io
from . import _anomaly_v03_runtime as paths
from . import anomaly_v03 as v
from . import anomaly_v03_preformal_campaign_controller as controller
from . import anomaly_v03_preformal_campaign_metadata as metadata
from . import anomaly_v03_preformal_campaign_store as store
from . import anomaly_v03_reader_evidence as observed


ROOT = Path(__file__).resolve().parents[2]
PIN_FORMAT = 'anomaly-v03-preformal-campaign-run-budget-request-pin-v1'
MAX_PIN_CONTROL = 4096
PIN_FILES = {'request-pin.json', 'request-pin.json.sha256'}


def _same(actual, expected, label):
    v.require(v.canonical_json(actual) == v.canonical_json(expected), label)


def _pinned(path, pin, maximum):
    metadata._pin(pin, 'external run-budget request')
    raw = observed._file(path, maximum)
    _same(metadata.pin(raw), pin, 'saved run-budget raw pin')
    return raw


def _pin_root(plan):
    campaign = Path(plan['root'])
    artifacts = paths.regular_path(ROOT / 'artifacts', directory=True)
    code = plan['campaign_id'][:8]
    v.require(campaign == artifacts /
              ('anomaly-v03-preformal-campaign-' + code),
              'local invented campaign request root')
    return artifacts / ('anomaly-v03-preformal-campaign-run-intent-' + code)


def _started(campaign_root, control_root, *, expected_plan_pin,
             expected_initial_checkpoint_pin, expected_intention_pin,
             expected_prepare_receipt_pin, expected_started_record_pin,
             expected_next_checkpoint_pin, expected_run_intent_pin=None):
    state = store.verify_started_store(
        campaign_root, control_root,
        expected_plan_pin=expected_plan_pin,
        expected_initial_checkpoint_pin=expected_initial_checkpoint_pin,
        expected_intention_pin=expected_intention_pin,
        expected_prepare_receipt_pin=expected_prepare_receipt_pin,
        expected_started_record_pin=expected_started_record_pin,
        expected_next_checkpoint_pin=expected_next_checkpoint_pin,
        expected_run_intent_pin=expected_run_intent_pin)
    checkpoint = state['checkpoint']
    record_raws = state['record_raws']
    v.require(type(record_raws) is list and len(record_raws) == 1 and
              metadata.pin(record_raws[0]) == expected_started_record_pin and
              checkpoint['record_count'] == 1 and
              checkpoint['head_sha256'] == expected_started_record_pin['sha256'] and
              state['plan_pin'] == expected_plan_pin and
              state['manifest_pin'] ==
              v.strict_json(record_raws[0])['manifest_pin'] and
              state['prepare_receipt_pin'] == expected_prepare_receipt_pin and
              state['campaign_coherence_authenticated'] is False and
              state['formal_permission'] is False,
              'externally pinned slot-0 started checkpoint required')
    store._live_matches(v.strict_json(state['plan_raw']))
    return state


def _prepared(state):
    plan = v.strict_json(state['plan_raw'])
    record = v.strict_json(state['record_raws'][0])
    receipt = v.strict_json(state['prepare_receipt_raw'])
    manifest = v.strict_json(state['manifest_raw'])
    v.require(record['state'] == 'started' and
              record['chunk_index'] == 0 and record['attempt'] == 1 and
              receipt['status'] == 'prepared' and receipt['reason'] is None and
              receipt['campaign_root'] == plan['root'] and
              receipt['control_root'] == state['control_root'] and
              receipt['anchor_pin'] == state['plan_pin'] and
              receipt['checkpoint_pin'] == state['initial_checkpoint_pin'] and
              receipt['intention_pin'] == state['intention_pin'] and
              receipt['manifest_pin'] == state['manifest_pin'] and
              receipt['direct_cli_exit_code'] == 0 and
              receipt['direct_cli_exit_confirmed'] is True and
              receipt['actual_registered_observations_read'] is False and
              receipt['campaign_evaluations_credited'] == 0 and
              receipt['formal_permission'] is False and
              receipt['campaign_coherence_authenticated'] is False and
              manifest['root'] == record['attempt_root'] and
              manifest['chunk_index'] == 0 and
              manifest['invented_only'] is True and
              manifest['actual_registered_observations_read'] is False and
              manifest['formal_permission'] is False,
              'saved invented prepare receipt/manifest slot binding')
    v.require(state['prepare_receipt_raw'] ==
              v.canonical_json(receipt) + b'\n' and
              metadata.pin(state['prepare_receipt_raw']) ==
              state['prepare_receipt_pin'] and
              state['manifest_raw'] == v.canonical_json(manifest) and
              metadata.pin(state['manifest_raw']) == state['manifest_pin'] and
              type(receipt['direct_cli_pid']) is int and
              receipt['direct_cli_pid'] > 0 and
              type(receipt['direct_cli_start_token']) is str and
              re.fullmatch(r'[0-9a-f]{64}',
                           receipt['direct_cli_start_token']) is not None and
              receipt['next_stage_authorized'] is False and
              receipt['retry_authorized'] is False,
              'raw pinned prepare ownership and closed next stage')
    return plan, record


def _request(state):
    plan, record = _prepared(state)
    request = controller.fixed_request(
        state['plan_raw'], state['plan_pin'], state['record_raws'],
        expected_record_count=1,
        expected_head_sha256=state['checkpoint']['head_sha256'],
        manifest_raw=state['manifest_raw'],
        manifest_pin=state['manifest_pin'], phase='run-budget',
        python_executable=sys.executable)
    v.require(request['anchor_pin'] == state['plan_pin'] and
              request['journal_count'] == 1 and
              request['journal_head_sha256'] ==
              state['checkpoint']['head_sha256'] and
              request['chunk_index'] == 0 and request['attempt'] == 1 and
              request['attempt_root'] == record['attempt_root'] and
              request['manifest_pin'] == state['manifest_pin'] and
              request['generation_receipt_pin'] is None and
              request['outer_result_pin'] is None and
              request['invented_only'] is True and
              request['actual_registered_observations_read'] is False and
              request['campaign_evaluations_credited'] == 0 and
              request['formal_permission'] is False,
              'fixed slot-0 invented run-budget request')
    attempt = paths.regular_path(Path(request['attempt_root']),
                                 directory=True, missing=True)
    reread = paths.regular_path(Path(request['reread_root']),
                                directory=True, missing=True)
    v.require(not attempt.exists() and not reread.exists(),
              'run-budget needs new attempt and reread roots')
    return plan, request


def _control(plan, state, request_pin):
    campaign = Path(plan['root'])
    control = {
        'format': PIN_FORMAT, 'scope': 'invented-slot-0-run-budget-request-only',
        'campaign_root': str(campaign),
        'control_root': state['control_root'],
        'request_path': str(campaign / 'intents' / '0001-run-budget.json'),
        'anchor_pin': copy.deepcopy(state['plan_pin']),
        'initial_checkpoint_pin': copy.deepcopy(
            state['initial_checkpoint_pin']),
        'intention_pin': copy.deepcopy(state['intention_pin']),
        'prepare_receipt_pin': copy.deepcopy(state['prepare_receipt_pin']),
        'manifest_pin': copy.deepcopy(state['manifest_pin']),
        'started_record_pin': copy.deepcopy(state['started_record_pin']),
        'next_checkpoint_pin': copy.deepcopy(state['next_checkpoint_pin']),
        'journal_count': 1,
        'journal_head_sha256': state['checkpoint']['head_sha256'],
        'request_pin': copy.deepcopy(request_pin),
        'native_run_started': False, 'invented_only': True,
        'actual_registered_observations_read': False,
        'campaign_coherence_authenticated': False,
        'campaign_evaluations_credited': 0,
        'launch_authorized': False, 'resume_authorized': False,
        'formal_permission': False,
    }
    return control


def create_request(campaign_root, control_root, *, expected_plan_pin,
                   expected_initial_checkpoint_pin, expected_intention_pin,
                   expected_prepare_receipt_pin, expected_started_record_pin,
                   expected_next_checkpoint_pin):
    """Save an exact request and its separate pin; partial roots stay blocked."""
    inputs = dict(
        expected_plan_pin=expected_plan_pin,
        expected_initial_checkpoint_pin=expected_initial_checkpoint_pin,
        expected_intention_pin=expected_intention_pin,
        expected_prepare_receipt_pin=expected_prepare_receipt_pin,
        expected_started_record_pin=expected_started_record_pin,
        expected_next_checkpoint_pin=expected_next_checkpoint_pin)
    state = _started(campaign_root, control_root, **inputs)
    plan, request = _request(state)
    pin_root = _pin_root(plan)
    paths.regular_path(pin_root, directory=True, missing=True)
    v.require(not pin_root.exists(), 'new external run-budget pin root required')
    request_path = Path(plan['root']) / 'intents' / '0001-run-budget.json'
    pending = Path(plan['root']) / 'pending' / '0001-run-budget.json'
    paths.regular_path(request_path, missing=True)
    paths.regular_path(pending, missing=True)
    v.require(not request_path.exists() and not pending.exists(),
              'new run-budget request path required')
    # Recheck source/runtime and all external heads at the last write boundary.
    state = _started(campaign_root, control_root, **inputs)
    fresh_plan, fresh_request = _request(state)
    _same(fresh_plan, plan, 'campaign plan changed before request save')
    _same(fresh_request, request, 'run-budget request changed before save')
    request_raw = controller.encode_request(request)
    request_pin = metadata.pin(request_raw)
    pin_root.mkdir()  # Claim a separate root before any request is published.
    io._exclusive(pending, request_raw)
    io._rename_no_replace(pending, request_path)
    _pinned(request_path, request_pin, controller.MAX_REQUEST)
    state = _started(campaign_root, control_root,
                     **inputs, expected_run_intent_pin=request_pin)
    value = _control(plan, state, request_pin)
    control_raw = v.canonical_json(value) + b'\n'
    v.require(len(control_raw) <= MAX_PIN_CONTROL,
              'bounded external run-budget pin control')
    io._exclusive(pin_root / 'request-pin.json', control_raw)
    control_pin = metadata.pin(control_raw)
    io._exclusive(pin_root / 'request-pin.json.sha256',
                  (control_pin['sha256'] + '\n').encode('ascii'))
    return verify_request(campaign_root, control_root,
                          expected_pin_control_pin=control_pin, **inputs)


def verify_request(campaign_root, control_root, *, expected_plan_pin,
                   expected_initial_checkpoint_pin, expected_intention_pin,
                   expected_prepare_receipt_pin, expected_started_record_pin,
                   expected_next_checkpoint_pin,
                   expected_pin_control_pin):
    """Reread the separate pin and saved request; return closed metadata."""
    inputs = dict(
        expected_plan_pin=expected_plan_pin,
        expected_initial_checkpoint_pin=expected_initial_checkpoint_pin,
        expected_intention_pin=expected_intention_pin,
        expected_prepare_receipt_pin=expected_prepare_receipt_pin,
        expected_started_record_pin=expected_started_record_pin,
        expected_next_checkpoint_pin=expected_next_checkpoint_pin)
    campaign_root = paths.regular_path(Path(campaign_root), directory=True)
    plan_raw = _pinned(campaign_root / 'plan.json', expected_plan_pin,
                       metadata.MAX_PLAN_BYTES)
    plan = v.strict_json(plan_raw)
    v.require(type(plan) is dict and
              plan_raw == metadata.encode_plan(plan),
              'canonical pinned run-budget campaign plan')
    pin_root = _pin_root(plan)
    paths.regular_path(pin_root, directory=True)
    v.require({path.name for path in pin_root.iterdir()} == PIN_FILES,
              'exact external run-budget pin inventory')
    control_raw = _pinned(pin_root / 'request-pin.json',
                          expected_pin_control_pin, MAX_PIN_CONTROL)
    sidecar = observed._file(pin_root / 'request-pin.json.sha256', 128)
    v.require(sidecar == (expected_pin_control_pin['sha256'] + '\n').encode('ascii'),
              'external run-budget pin sidecar')
    control = v.strict_json(control_raw)
    v.require(type(control) is dict and
              control_raw == v.canonical_json(control) + b'\n' and
              control['format'] == PIN_FORMAT and
              control['request_path'] == str(Path(plan['root']) / 'intents' /
                                             '0001-run-budget.json'),
              'canonical external run-budget pin control')
    request_pin = control['request_pin']
    metadata._pin(request_pin, 'external run-budget request pin')
    state = _started(campaign_root, control_root, **inputs,
                     expected_run_intent_pin=request_pin)
    fresh_plan, request = _request(state)
    _same(fresh_plan, plan, 'run-budget plan after save')
    expected_raw = controller.encode_request(request)
    v.require(metadata.pin(expected_raw) == request_pin and
              _pinned(Path(control['request_path']), request_pin,
                      controller.MAX_REQUEST) == expected_raw,
              'exact saved run-budget request changed')
    _same(control, _control(plan, state, request_pin),
          'external run-budget pin context changed')
    v.require({path.name for path in pin_root.iterdir()} == PIN_FILES and
              _pinned(pin_root / 'request-pin.json',
                      expected_pin_control_pin, MAX_PIN_CONTROL) == control_raw and
              observed._file(pin_root / 'request-pin.json.sha256', 128) ==
              sidecar and
              _pinned(Path(control['request_path']), request_pin,
                      controller.MAX_REQUEST) == expected_raw,
              'run-budget request/control changed during readback')
    return {
        'status': 'run_budget_request_pinned',
        'campaign_root': plan['root'], 'control_root': state['control_root'],
        'request_path': control['request_path'],
        'request_pin': request_pin,
        'pin_control_path': str(pin_root / 'request-pin.json'),
        'pin_control_pin': expected_pin_control_pin,
        'record_count': 1,
        'journal_head_sha256': state['checkpoint']['head_sha256'],
        'native_run_started': False,
        'invented_only': True,
        'actual_registered_observations_read': False,
        'campaign_coherence_authenticated': False,
        'campaign_evaluations_credited': 0,
        'launch_authorized': False, 'resume_authorized': False,
        'formal_permission': False,
    }
