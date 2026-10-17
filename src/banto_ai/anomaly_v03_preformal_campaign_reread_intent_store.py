"""Pin and own one invented saved-row reread after a verified run-budget.

The generated attempt is retained.  A separate, fresh root fixes the
generation receipt and reread request before any reread process is started.
Partial publication is preserved and cannot be resumed here.
"""
from __future__ import annotations

import copy
import math
from pathlib import Path
import sys

from . import _anomaly_v03_io as io
from . import _anomaly_v03_runtime as paths
from . import anomaly_v03 as v
from . import anomaly_v03_preformal_campaign_controller as controller
from . import anomaly_v03_preformal_campaign_metadata as metadata
from . import anomaly_v03_preformal_campaign_preflight as preflight
from . import anomaly_v03_preformal_campaign_run_intent_store as run_intent
from . import anomaly_v03_preformal_campaign_store as store


ROOT = Path(__file__).resolve().parents[2]
PIN_FORMAT = 'anomaly-v03-preformal-campaign-saved-reread-request-pin-v1'
MAX_PIN_CONTROL = 4096
PIN_FILES = frozenset({'request-pin.json', 'request-pin.json.sha256'})
CONTROL_FILES = frozenset({'receipt.json', 'report.json', 'stderr.json',
                           'supervision.json'})


def _same(actual, expected, label):
    v.require(v.canonical_json(actual) == v.canonical_json(expected), label)


def _pinned(path, pin, maximum):
    return store._pinned(path, pin, maximum)


def _pin_root(plan):
    campaign = Path(plan['root'])
    artifacts = paths.regular_path(ROOT / 'artifacts', directory=True)
    code = plan['campaign_id'][:8]
    v.require(campaign == artifacts / ('anomaly-v03-preformal-campaign-' + code),
              'dedicated saved-reread campaign root')
    return artifacts / ('anomaly-v03-preformal-campaign-reread-intent-' + code)


def _inputs(expected_plan_pin, expected_initial_checkpoint_pin,
            expected_intention_pin, expected_prepare_receipt_pin,
            expected_started_record_pin, expected_next_checkpoint_pin,
            expected_run_pin_control_pin, expected_generation_receipt_pin):
    return {
        'expected_plan_pin': expected_plan_pin,
        'expected_initial_checkpoint_pin': expected_initial_checkpoint_pin,
        'expected_intention_pin': expected_intention_pin,
        'expected_prepare_receipt_pin': expected_prepare_receipt_pin,
        'expected_started_record_pin': expected_started_record_pin,
        'expected_next_checkpoint_pin': expected_next_checkpoint_pin,
        'expected_run_pin_control_pin': expected_run_pin_control_pin,
        'expected_generation_receipt_pin': expected_generation_receipt_pin,
    }


def _inventory(campaign, controls, *, has_request, after_reread,
               allow_completion):
    store._inventory(campaign, store.PLAN_FILES | {'intents', 'control'})
    store._inventory(controls, store.CONTROL_FILES |
                     ({'checkpoint-000001.json', 'checkpoint-000002.json'}
                      if allow_completion else {'checkpoint-000001.json'}))
    store._inventory(campaign / 'journal',
                     frozenset({'000001.json', '000002.json'} if
                               allow_completion else {'000001.json'}))
    store._inventory(campaign / 'pending', frozenset())
    store._inventory(campaign / 'intents',
                     frozenset({'0001-run-budget.json',
                                '0001-saved-reread.json'} if has_request else
                               {'0001-run-budget.json'}))
    store._inventory(campaign / 'control', frozenset({'000-1'}))
    store._inventory(campaign / 'control' / '000-1',
                     frozenset({'run-budget', 'saved-reread'} if after_reread
                               else {'run-budget'}))
    store._inventory(campaign / 'control' / '000-1' / 'run-budget',
                     CONTROL_FILES)
    if after_reread:
        store._inventory(campaign / 'control' / '000-1' / 'saved-reread',
                         CONTROL_FILES)


def _stage(campaign_root, control_root, pins, *, has_request=False,
           after_reread=False, allow_completion=False,
           expected_pin_control_pin=None):
    """Reopen the count-1 chain after generation, without prelaunch readers."""
    campaign = paths.regular_path(Path(campaign_root), directory=True)
    controls = paths.regular_path(Path(control_root), directory=True)
    _inventory(campaign, controls, has_request=has_request,
               after_reread=after_reread, allow_completion=allow_completion)
    plan_raw = _pinned(campaign / 'plan.json', pins['expected_plan_pin'],
                       metadata.MAX_PLAN_BYTES)
    plan = v.strict_json(plan_raw)
    v.require(type(plan) is dict and plan_raw == metadata.encode_plan(plan),
              'canonical pinned saved-reread campaign plan')
    wanted_campaign, wanted_controls = store._roots(plan, controls)
    v.require(campaign == wanted_campaign and controls == wanted_controls,
              'saved-reread campaign/control roots changed')
    plan_pin = pins['expected_plan_pin']
    initial_pin = pins['expected_initial_checkpoint_pin']
    intention_pin = pins['expected_intention_pin']
    prepare_pin = pins['expected_prepare_receipt_pin']
    record_pin = pins['expected_started_record_pin']
    next_pin = pins['expected_next_checkpoint_pin']
    run_control_pin = pins['expected_run_pin_control_pin']
    generation_pin = pins['expected_generation_receipt_pin']
    anchor_raw = store._read(controls / 'anchor-pin.json', store.MAX_CONTROL)
    v.require(anchor_raw == store._lf(store._anchor(plan, plan_pin)),
              'external saved-reread anchor changed')
    initial_raw = _pinned(controls / 'checkpoint.json', initial_pin,
                          store.MAX_CONTROL)
    v.require(initial_raw == store._lf(store._checkpoint(plan_pin)),
              'initial saved-reread checkpoint changed')
    intention_raw = _pinned(controls / 'preflight-intention.json',
                            intention_pin, preflight.MAX_INTENTION)
    intention = v.strict_json(intention_raw)
    v.require(type(intention) is dict and
              intention.get('python_executable') == sys.executable and
              intention_raw == preflight.encode_intention(
                  preflight.make_intention(plan_raw, plan_pin, 0, 1,
                                           sys.executable)) and
              store._read(controls / 'preflight-intention-pin.json',
                          store.MAX_CONTROL) ==
              store._lf(store._intention_pin(plan_pin, intention_pin)),
              'fixed saved-reread prepare intention changed')
    owner_state = {
        'campaign_root': str(campaign), 'control_root': str(controls),
        'plan_raw': plan_raw, 'plan_pin': plan_pin,
        'checkpoint_pin': initial_pin, 'intention_raw': intention_raw,
        'intention_pin': intention_pin, 'intention': intention,
    }
    owner = store._prepared_owner(owner_state, prepare_pin,
                                  require_attempt_absent=False)
    record_raw = _pinned(campaign / 'journal' / '000001.json', record_pin,
                          metadata.MAX_RECORD_BYTES)
    v.require(record_raw == controller.next_started_record(
        plan_raw, plan_pin, [], expected_record_count=0,
        expected_head_sha256=plan_pin['sha256'],
        manifest_pin=owner['manifest_pin']),
        'started record differs from saved prepare manifest')
    journal = metadata.reduce_journal(
        plan_raw, [record_raw], expected_plan_pin=plan_pin,
        expected_record_count=1, expected_head_sha256=record_pin['sha256'])
    v.require(journal['latest_unfinished_state'] == 'started' and
              journal['declared_completed_chunks'] == 0 and
              journal['failed_attempt_count'] == 0 and
              journal['campaign_coherence_authenticated'] is False and
              journal['campaign_evaluations_credited'] == 0 and
              journal['formal_permission'] is False,
              'externally pinned started slot remains limited')
    next_raw = _pinned(controls / 'checkpoint-000001.json', next_pin,
                       store.MAX_CONTROL)
    checkpoint = v.strict_json(next_raw)
    v.require(next_raw == store._lf(store._started_checkpoint(
        plan_pin, initial_pin, intention_pin, prepare_pin, record_pin)) and
        checkpoint['record_count'] == 1 and
        checkpoint['head_sha256'] == record_pin['sha256'],
        'external count-1/head checkpoint changed')
    manifest_raw = owner['manifest_raw']
    manifest_pin = owner['manifest_pin']
    current = v.strict_json(record_raw)
    controller._manifest(plan, current, manifest_raw, manifest_pin)
    store._live_matches(plan)

    run_pin_root = (ROOT / 'artifacts' /
                    ('anomaly-v03-preformal-campaign-run-intent-' +
                     plan['campaign_id'][:8]))
    store._inventory(run_pin_root, run_intent.PIN_FILES)
    run_control_raw = _pinned(run_pin_root / 'request-pin.json',
                              run_control_pin, run_intent.MAX_PIN_CONTROL)
    run_sidecar = store._read(run_pin_root / 'request-pin.json.sha256', 128)
    v.require(run_sidecar == (run_control_pin['sha256'] + '\n').encode('ascii'),
              'external run-budget request pin sidecar changed')
    run_control = v.strict_json(run_control_raw)
    v.require(run_control_raw == v.canonical_json(run_control) + b'\n',
              'canonical external run-budget pin control')
    run_request_pin = run_control['request_pin']
    state_for_run_control = {
        'control_root': str(controls), 'plan_pin': plan_pin,
        'initial_checkpoint_pin': initial_pin, 'intention_pin': intention_pin,
        'prepare_receipt_pin': prepare_pin, 'manifest_pin': manifest_pin,
        'started_record_pin': record_pin, 'next_checkpoint_pin': next_pin,
        'checkpoint': checkpoint,
    }
    _same(run_control,
          run_intent._control(plan, state_for_run_control, run_request_pin),
          'external run-budget request control changed')
    run_request_path = campaign / 'intents' / '0001-run-budget.json'
    run_request_raw = _pinned(run_request_path, run_request_pin,
                              controller.MAX_REQUEST)
    run_request = v.strict_json(run_request_raw)
    v.require(run_request_raw == controller.encode_request(run_request),
              'canonical saved run-budget request')
    wanted_run = controller.fixed_request(
        plan_raw, plan_pin, [record_raw], expected_record_count=1,
        expected_head_sha256=checkpoint['head_sha256'],
        manifest_raw=manifest_raw, manifest_pin=manifest_pin,
        phase='run-budget', python_executable=sys.executable)
    _same(run_request, wanted_run, 'saved run-budget request changed')
    generation_raw = _pinned(
        campaign / 'control' / '000-1' / 'run-budget' / 'receipt.json',
        generation_pin, controller.MAX_RECEIPT)
    generation = controller._load_receipt(plan, current, 'run-budget',
                                           generation_pin)
    v.require(generation_raw == v.canonical_json(generation) + b'\n' and
              generation['status'] == 'verified' and
              generation['request_pin'] == run_request_pin and
              generation['formal_permission'] is False and
              generation['campaign_coherence_authenticated'] is False and
              generation['campaign_evaluations_credited'] == 0,
              'saved generation receipt/request binding')
    request = controller.fixed_request(
        plan_raw, plan_pin, [record_raw], expected_record_count=1,
        expected_head_sha256=checkpoint['head_sha256'],
        manifest_raw=manifest_raw, manifest_pin=manifest_pin,
        phase='saved-reread', python_executable=sys.executable,
        outer_result_pin=generation['inner']['outer_result_pin'],
        generation_receipt_pin=generation_pin)
    attempt = paths.regular_path(Path(request['attempt_root']),
                                 directory=True)
    reread = paths.regular_path(Path(request['reread_root']),
                                directory=True, missing=not after_reread)
    v.require(attempt.is_dir() and
              (reread.is_dir() if after_reread else not reread.exists()),
              'retained attempt and required reread output state')
    if after_reread:
        controller._verified_inputs_before_or_after(plan, request)
        _pinned(attempt / 'owned-generator' / 'result.json',
                request['outer_result_pin'], controller.MAX_SAVED)
    else:
        controller._verified_inputs(plan, request, current)
    request_raw = None
    request_pin = None
    pin_root = _pin_root(plan)
    if has_request:
        v.require(expected_pin_control_pin is not None,
                  'external saved-reread pin control required')
        store._inventory(pin_root, PIN_FILES)
        pin_control_raw = _pinned(pin_root / 'request-pin.json',
                                  expected_pin_control_pin, MAX_PIN_CONTROL)
        pin_sidecar = store._read(pin_root / 'request-pin.json.sha256', 128)
        v.require(pin_sidecar ==
                  (expected_pin_control_pin['sha256'] + '\n').encode('ascii'),
                  'saved-reread external pin sidecar changed')
        pin_control = v.strict_json(pin_control_raw)
        v.require(pin_control_raw == v.canonical_json(pin_control) + b'\n',
                  'canonical saved-reread external pin control')
        request_pin = pin_control['request_pin']
        request_raw = _pinned(campaign / 'intents' /
                              '0001-saved-reread.json', request_pin,
                              controller.MAX_REQUEST)
        v.require(request_raw == controller.encode_request(request),
                  'fixed saved-reread request raw changed')
        state_for_control = {
            'plan_pin': plan_pin, 'initial_checkpoint_pin': initial_pin,
            'intention_pin': intention_pin, 'prepare_receipt_pin': prepare_pin,
            'started_record_pin': record_pin, 'next_checkpoint_pin': next_pin,
            'run_pin_control_pin': run_control_pin,
            'run_request_pin': run_request_pin,
            'generation_receipt_pin': generation_pin,
            'manifest_pin': manifest_pin, 'checkpoint': checkpoint,
            'control_root': str(controls),
        }
        _same(pin_control, _control(plan, state_for_control, request_pin,
                                     request['outer_result_pin']),
              'saved-reread pin control context changed')
    _inventory(campaign, controls, has_request=has_request,
               after_reread=after_reread, allow_completion=allow_completion)
    for path, raw, maximum in (
        (campaign / 'plan.json', plan_raw, metadata.MAX_PLAN_BYTES),
        (campaign / 'journal' / '000001.json', record_raw,
         metadata.MAX_RECORD_BYTES),
        (controls / 'anchor-pin.json', anchor_raw, store.MAX_CONTROL),
        (controls / 'checkpoint.json', initial_raw, store.MAX_CONTROL),
        (controls / 'checkpoint-000001.json', next_raw, store.MAX_CONTROL),
        (controls / 'preflight-intention.json', intention_raw,
         preflight.MAX_INTENTION),
        (run_pin_root / 'request-pin.json', run_control_raw,
         run_intent.MAX_PIN_CONTROL),
        (run_request_path, run_request_raw, controller.MAX_REQUEST),
        (campaign / 'control' / '000-1' / 'run-budget' / 'receipt.json',
         generation_raw, controller.MAX_RECEIPT),
    ):
        v.require(store._read(path, maximum) == raw,
                  'saved-reread stage raw changed during verification')
    v.require(store._read(controls / 'preflight-intention-pin.json',
                          store.MAX_CONTROL) ==
              store._lf(store._intention_pin(plan_pin, intention_pin)) and
              store._read(run_pin_root / 'request-pin.json.sha256', 128) ==
              run_sidecar,
              'saved-reread external control sidecar changed')
    if has_request:
        v.require(_pinned(pin_root / 'request-pin.json',
                          expected_pin_control_pin, MAX_PIN_CONTROL) ==
                  pin_control_raw and
                  store._read(pin_root / 'request-pin.json.sha256', 128) ==
                  pin_sidecar and
                  _pinned(campaign / 'intents' / '0001-saved-reread.json',
                          request_pin, controller.MAX_REQUEST) == request_raw,
                  'saved-reread request/control changed during readback')
    return {
        'plan_raw': plan_raw, 'plan_pin': plan_pin,
        'record_raws': [record_raw], 'checkpoint': checkpoint,
        'manifest_raw': manifest_raw, 'manifest_pin': manifest_pin,
        'generation_receipt_pin': generation_pin,
        'run_request_pin': run_request_pin,
        'run_pin_control_pin': run_control_pin,
        'request': request, 'request_raw': request_raw,
        'request_pin': request_pin,
        'outer_result_pin': request['outer_result_pin'],
        'reread_root': request['reread_root'],
        'campaign_root': str(campaign), 'control_root': str(controls),
    }


def _control(plan, state, request_pin, outer_result_pin):
    return {
        'format': PIN_FORMAT, 'scope': 'invented-slot-0-saved-reread-request-only',
        'campaign_root': plan['root'], 'control_root': state['control_root'],
        'request_path': str(Path(plan['root']) / 'intents' /
                            '0001-saved-reread.json'),
        'anchor_pin': copy.deepcopy(state['plan_pin']),
        'initial_checkpoint_pin': copy.deepcopy(state['initial_checkpoint_pin']),
        'intention_pin': copy.deepcopy(state['intention_pin']),
        'prepare_receipt_pin': copy.deepcopy(state['prepare_receipt_pin']),
        'manifest_pin': copy.deepcopy(state['manifest_pin']),
        'started_record_pin': copy.deepcopy(state['started_record_pin']),
        'next_checkpoint_pin': copy.deepcopy(state['next_checkpoint_pin']),
        'run_pin_control_pin': copy.deepcopy(state['run_pin_control_pin']),
        'run_request_pin': copy.deepcopy(state['run_request_pin']),
        'generation_receipt_pin': copy.deepcopy(
            state['generation_receipt_pin']),
        'outer_result_pin': copy.deepcopy(outer_result_pin),
        'journal_count': 1,
        'journal_head_sha256': state['checkpoint']['head_sha256'],
        'request_pin': copy.deepcopy(request_pin),
        'native_reread_started': False, 'invented_only': True,
        'actual_registered_observations_read': False,
        'campaign_coherence_authenticated': False,
        'campaign_evaluations_credited': 0,
        'launch_authorized': False, 'resume_authorized': False,
        'formal_permission': False,
    }


def create_request(campaign_root, control_root, *, expected_plan_pin,
                   expected_initial_checkpoint_pin, expected_intention_pin,
                   expected_prepare_receipt_pin, expected_started_record_pin,
                   expected_next_checkpoint_pin, expected_run_pin_control_pin,
                   expected_generation_receipt_pin):
    """Publish one exact reread request with a separate external pin."""
    pins = _inputs(expected_plan_pin, expected_initial_checkpoint_pin,
                   expected_intention_pin, expected_prepare_receipt_pin,
                   expected_started_record_pin, expected_next_checkpoint_pin,
                   expected_run_pin_control_pin,
                   expected_generation_receipt_pin)
    state = _stage(campaign_root, control_root, pins)
    plan = v.strict_json(state['plan_raw'])
    pin_root = _pin_root(plan)
    paths.regular_path(pin_root, directory=True, missing=True)
    request_path = Path(plan['root']) / 'intents' / '0001-saved-reread.json'
    pending = Path(plan['root']) / 'pending' / '0001-saved-reread.json'
    control = Path(plan['root']) / 'control' / '000-1' / 'saved-reread'
    for path in (request_path, pending):
        paths.regular_path(path, missing=True)
    paths.regular_path(control, directory=True, missing=True)
    v.require(not pin_root.exists() and not request_path.exists() and
              not pending.exists() and not control.exists(),
              'new saved-reread pin/request/control roots required')
    # The last prepublication read includes the clean source and output state.
    again = _stage(campaign_root, control_root, pins)
    _same(again['request'], state['request'],
          'saved-reread request changed before publication')
    request_raw = controller.encode_request(state['request'])
    request_pin = metadata.pin(request_raw)
    pin_root.mkdir()  # Claim before publishing; any interruption stays blocked.
    io._exclusive(pending, request_raw)
    io._rename_no_replace(pending, request_path)
    _pinned(request_path, request_pin, controller.MAX_REQUEST)
    control_state = {
        'plan_pin': expected_plan_pin,
        'initial_checkpoint_pin': expected_initial_checkpoint_pin,
        'intention_pin': expected_intention_pin,
        'prepare_receipt_pin': expected_prepare_receipt_pin,
        'started_record_pin': expected_started_record_pin,
        'next_checkpoint_pin': expected_next_checkpoint_pin,
        'run_pin_control_pin': expected_run_pin_control_pin,
        'run_request_pin': state['run_request_pin'],
        'generation_receipt_pin': expected_generation_receipt_pin,
        'manifest_pin': state['manifest_pin'],
        'checkpoint': state['checkpoint'],
        'control_root': str(control_root),
    }
    pin_control_raw = v.canonical_json(_control(
        plan, control_state, request_pin, state['outer_result_pin'])) + b'\n'
    v.require(len(pin_control_raw) <= MAX_PIN_CONTROL,
              'bounded saved-reread external pin control')
    io._exclusive(pin_root / 'request-pin.json', pin_control_raw)
    pin_control_pin = metadata.pin(pin_control_raw)
    io._exclusive(pin_root / 'request-pin.json.sha256',
                  (pin_control_pin['sha256'] + '\n').encode('ascii'))
    return verify_request(campaign_root, control_root,
                          expected_pin_control_pin=pin_control_pin, **pins)


def verify_request(campaign_root, control_root, *, expected_plan_pin,
                   expected_initial_checkpoint_pin, expected_intention_pin,
                   expected_prepare_receipt_pin, expected_started_record_pin,
                   expected_next_checkpoint_pin, expected_run_pin_control_pin,
                   expected_generation_receipt_pin,
                   expected_pin_control_pin):
    """Reread all external controls; only an absent reread root is launchable."""
    pins = _inputs(expected_plan_pin, expected_initial_checkpoint_pin,
                   expected_intention_pin, expected_prepare_receipt_pin,
                   expected_started_record_pin, expected_next_checkpoint_pin,
                   expected_run_pin_control_pin,
                   expected_generation_receipt_pin)
    state = _stage(campaign_root, control_root, pins, has_request=True,
                   expected_pin_control_pin=expected_pin_control_pin)
    return {
        'status': 'saved_reread_request_pinned',
        'campaign_root': state['campaign_root'],
        'control_root': state['control_root'],
        'request_path': str(Path(state['campaign_root']) / 'intents' /
                            '0001-saved-reread.json'),
        'request_pin': state['request_pin'],
        'pin_control_path': str(_pin_root(v.strict_json(state['plan_raw'])) /
                                'request-pin.json'),
        'pin_control_pin': expected_pin_control_pin,
        'generation_receipt_pin': expected_generation_receipt_pin,
        'outer_result_pin': state['outer_result_pin'],
        'record_count': 1,
        'journal_head_sha256': state['checkpoint']['head_sha256'],
        'native_reread_started': False,
        'invented_only': True,
        'actual_registered_observations_read': False,
        'campaign_coherence_authenticated': False,
        'campaign_evaluations_credited': 0,
        'launch_authorized': False, 'resume_authorized': False,
        'formal_permission': False,
    }


def execute_request(campaign_root, control_root, *, expected_plan_pin,
                    expected_initial_checkpoint_pin, expected_intention_pin,
                    expected_prepare_receipt_pin, expected_started_record_pin,
                    expected_next_checkpoint_pin, expected_run_pin_control_pin,
                    expected_generation_receipt_pin,
                    expected_pin_control_pin,
                    remaining_wall_seconds=None):
    """Own exactly one pinned native reread; never retry a failed attempt."""
    if remaining_wall_seconds is not None:
        v.require(type(remaining_wall_seconds) in (int, float) and
                  math.isfinite(remaining_wall_seconds) and
                  remaining_wall_seconds > 0,
                  'finite positive saved-reread remaining wall seconds required')
    inputs = _inputs(expected_plan_pin, expected_initial_checkpoint_pin,
                     expected_intention_pin, expected_prepare_receipt_pin,
                     expected_started_record_pin, expected_next_checkpoint_pin,
                     expected_run_pin_control_pin,
                     expected_generation_receipt_pin)
    verified = verify_request(campaign_root, control_root,
                              expected_pin_control_pin=expected_pin_control_pin,
                              **inputs)
    state = _stage(campaign_root, control_root, inputs, has_request=True,
                   expected_pin_control_pin=expected_pin_control_pin)
    v.require(verified['request_pin'] == state['request_pin'] and
              verified['journal_head_sha256'] ==
              state['checkpoint']['head_sha256'],
              'saved-reread launch boundary changed')
    wall_option = ({} if remaining_wall_seconds is None else
                   {'remaining_wall_seconds': remaining_wall_seconds})
    return controller.execute_owned(
        verified['request_path'], verified['request_pin'],
        state['plan_raw'], state['plan_pin'], state['record_raws'],
        expected_record_count=1,
        expected_head_sha256=state['checkpoint']['head_sha256'],
        **wall_option)


def verify_postrun_stage(campaign_root, control_root, *, expected_plan_pin,
                         expected_initial_checkpoint_pin,
                         expected_intention_pin,
                         expected_prepare_receipt_pin,
                         expected_started_record_pin,
                         expected_next_checkpoint_pin,
                         expected_run_pin_control_pin,
                         expected_generation_receipt_pin,
                         expected_pin_control_pin,
                         allow_completion=False):
    """Reopen the preceding chain after reread; completion is still unproved."""
    pins = _inputs(expected_plan_pin, expected_initial_checkpoint_pin,
                   expected_intention_pin, expected_prepare_receipt_pin,
                   expected_started_record_pin, expected_next_checkpoint_pin,
                   expected_run_pin_control_pin,
                   expected_generation_receipt_pin)
    state = _stage(campaign_root, control_root, pins, has_request=True,
                   after_reread=True, allow_completion=allow_completion,
                   expected_pin_control_pin=expected_pin_control_pin)
    return {**state, 'status': 'saved_reread_postrun_stage_reopened',
            'pin_control_pin': expected_pin_control_pin,
            'campaign_coherence_authenticated': False,
            'campaign_evaluations_credited': 0,
            'formal_permission': False}
