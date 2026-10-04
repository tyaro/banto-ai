"""One live monotonic wall envelope for an invented slot-0 campaign chain.

This is a sampled, cooperative limit.  Each owned CLI gets the remaining wall
time at its entry; Python work before and after that Job is checked at stage
boundaries.  The receipt does not claim a hard quota or formal S4 closure.
"""
from __future__ import annotations

import math
from pathlib import Path
import time

from . import _anomaly_v03_io as io
from . import _anomaly_v03_runtime as paths
from . import anomaly_v03 as v
from . import anomaly_v03_preformal_campaign_completion_store as completion
from . import anomaly_v03_preformal_campaign_metadata as metadata
from . import anomaly_v03_preformal_campaign_prepare_owner as prepare
from . import anomaly_v03_preformal_campaign_reread_intent_store as reread
from . import anomaly_v03_preformal_campaign_run_budget_owner as run_owner
from . import anomaly_v03_preformal_campaign_run_intent_store as run_intent
from . import anomaly_v03_preformal_campaign_store as store


FORMAT = 'anomaly-v03-preformal-campaign-slot-wall-envelope-v1'
CLAIM_FORMAT = 'anomaly-v03-preformal-campaign-slot-wall-claim-v1'
MAX_CONTROL = 16 * 1024
SCOPE = 'invented-slot-0-single-invocation-cooperative-wall-only'
EVIDENCE_PINS = frozenset({
    'prepare_receipt_pin', 'started_record_pin', 'next_checkpoint_pin',
    'run_pin_control_pin', 'run_request_pin', 'generation_receipt_pin',
    'reread_pin_control_pin', 'reread_request_pin', 'reread_receipt_pin',
    'completed_record_pin', 'terminal_checkpoint_pin',
})
CLAIM_FIELDS = frozenset({
    'format', 'scope', 'campaign_root', 'control_root', 'anchor_pin',
    'initial_checkpoint_pin', 'intention_pin', 'source_revision',
    'wall_seconds', 'invented_only', 'formal_permission',
})
RECEIPT_FIELDS = frozenset({
    'format', 'scope', 'claim_pin', 'anchor_pin', 'campaign_root',
    'control_root', 'wall_seconds', 'elapsed_seconds', 'last_stage',
    'evidence_pins', 'status', 'reason', 'error_type', 'retry_authorized',
    'shared_slot_wall_observed', 'hard_wall_quota_authenticated',
    'full_end_to_end_budget_measured', 'campaign_coherence_authenticated',
    'campaign_evaluations_credited', 'invented_only',
    'actual_registered_observations_read', 'formal_permission',
})


class WallExpired(ValueError):
    """The shared slot wall elapsed before the next stage could finish."""


def _positive_seconds(value, label):
    v.require(type(value) in (int, float) and math.isfinite(value) and
              value > 0, 'finite positive ' + label + ' required')
    return value


def _clock_value(clock):
    value = clock()
    v.require(type(value) in (int, float) and math.isfinite(value) and
              value >= 0, 'finite nonnegative monotonic clock required')
    return value


def _raw(value):
    raw = v.canonical_json(value) + b'\n'
    v.require(len(raw) <= MAX_CONTROL, 'bounded wall envelope control')
    return raw


def _root(state):
    plan = v.strict_json(state['plan_raw'])
    campaign = Path(state['campaign_root'])
    root = campaign.parent / ('anomaly-v03-preformal-campaign-wall-' +
                              plan['campaign_id'][:8])
    paths.regular_path(root, directory=True, missing=True)
    v.require(not root.exists(), 'fresh slot wall envelope root required')
    return root


def execute(campaign_root, control_root, *, expected_plan_pin,
            expected_initial_checkpoint_pin, expected_intention_pin,
            wall_seconds, clock=time.monotonic):
    """Run one pinned invented slot through completion under one live clock.

    A failure retains prior stage artifacts and a terminal envelope receipt.
    There is no restart or reuse of the same envelope root.
    """
    wall_seconds = _positive_seconds(wall_seconds, 'slot wall seconds')
    started = _clock_value(clock)
    state = store.verify_store(
        campaign_root, control_root,
        expected_plan_pin=expected_plan_pin,
        expected_checkpoint_pin=expected_initial_checkpoint_pin,
        expected_intention_pin=expected_intention_pin)
    plan = v.strict_json(state['plan_raw'])
    v.require(wall_seconds <= plan['budget_candidate']['limits']['wall_seconds'],
              'slot wall exceeds unadopted campaign candidate')
    root = _root(state)
    root.mkdir()
    claim = {
        'format': CLAIM_FORMAT,
        'scope': SCOPE,
        'campaign_root': state['campaign_root'],
        'control_root': state['control_root'],
        'anchor_pin': expected_plan_pin,
        'initial_checkpoint_pin': expected_initial_checkpoint_pin,
        'intention_pin': expected_intention_pin,
        'source_revision': plan['source']['revision'],
        'wall_seconds': wall_seconds,
        'invented_only': True, 'formal_permission': False,
    }
    claim_raw = _raw(claim)
    io._exclusive(root / 'claim.json', claim_raw)
    claim_pin = metadata.pin(claim_raw)
    evidence = {}
    stage = 'prelaunch'
    reason = None
    error_type = None
    completed = False

    def remaining():
        elapsed = _clock_value(clock) - started
        v.require(elapsed >= 0, 'monotonic clock moved backward')
        if elapsed >= wall_seconds:
            raise WallExpired('shared slot wall expired')
        return wall_seconds - elapsed

    def step(name, action, capture):
        nonlocal stage
        stage = name
        available = remaining()
        result = action(available)
        capture(result)
        remaining()  # Include Python verification and stage transition time.
        return result

    def require_status(value, wanted, label):
        v.require(value['status'] == wanted, label + ' did not complete')

    try:
        def capture_prepare(result):
            value, pin = result
            metadata._pin(pin, 'wall prepare receipt')
            evidence['prepare_receipt_pin'] = pin
            require_status(value, 'prepared', 'owned prepare')

        prepared, prepare_pin = step(
            'prepare',
            lambda available: prepare.execute(
                campaign_root, control_root,
                expected_plan_pin=expected_plan_pin,
                expected_checkpoint_pin=expected_initial_checkpoint_pin,
                expected_intention_pin=expected_intention_pin,
                remaining_wall_seconds=available),
            capture_prepare)

        shared = {
            'expected_plan_pin': expected_plan_pin,
            'expected_initial_checkpoint_pin': expected_initial_checkpoint_pin,
            'expected_intention_pin': expected_intention_pin,
            'expected_prepare_receipt_pin': prepare_pin,
        }

        def capture_started(value):
            require_status(value, 'started_record_fixed', 'started journal')
            evidence['started_record_pin'] = value['started_record_pin']
            evidence['next_checkpoint_pin'] = value['next_checkpoint_pin']

        started_state = step(
            'started',
            lambda _: store.append_started(campaign_root, control_root,
                                           **shared),
            capture_started)
        shared.update(
            expected_started_record_pin=started_state['started_record_pin'],
            expected_next_checkpoint_pin=started_state['next_checkpoint_pin'])

        def capture_run_intent(value):
            require_status(value, 'run_budget_request_pinned', 'run intent')
            evidence['run_pin_control_pin'] = value['pin_control_pin']
            evidence['run_request_pin'] = value['request_pin']

        run_request = step(
            'run-intent',
            lambda _: run_intent.create_request(campaign_root, control_root,
                                                **shared),
            capture_run_intent)

        def capture_generation(result):
            value, pin = result
            metadata._pin(pin, 'wall generation receipt')
            evidence['generation_receipt_pin'] = pin
            require_status(value, 'verified', 'owned generation')

        generation, generation_pin = step(
            'run-budget',
            lambda available: run_owner.execute_run_budget(
                campaign_root, control_root,
                expected_pin_control_pin=run_request['pin_control_pin'],
                remaining_wall_seconds=available, **shared),
            capture_generation)
        shared.update(
            expected_run_pin_control_pin=run_request['pin_control_pin'],
            expected_generation_receipt_pin=generation_pin)

        def capture_reread_intent(value):
            require_status(value, 'saved_reread_request_pinned',
                           'saved reread intent')
            evidence['reread_pin_control_pin'] = value['pin_control_pin']
            evidence['reread_request_pin'] = value['request_pin']

        reread_request = step(
            'reread-intent',
            lambda _: reread.create_request(campaign_root, control_root,
                                            **shared),
            capture_reread_intent)

        def capture_reread(result):
            value, pin = result
            metadata._pin(pin, 'wall reread receipt')
            evidence['reread_receipt_pin'] = pin
            require_status(value, 'verified', 'owned saved reread')

        reread_result, reread_pin = step(
            'saved-reread',
            lambda available: reread.execute_request(
                campaign_root, control_root,
                expected_pin_control_pin=reread_request['pin_control_pin'],
                remaining_wall_seconds=available, **shared),
            capture_reread)

        def capture_completed(value):
            v.require(value['declared_completed_chunks'] == 1 and
                      value['declared_completed_evaluations'] == 6 and
                      value['campaign_evaluations_credited'] == 0 and
                      value['formal_permission'] is False,
                      'limited invented completion required')
            evidence['completed_record_pin'] = value['completed_record_pin']
            evidence['terminal_checkpoint_pin'] = value[
                'terminal_checkpoint_pin']

        step(
            'completed',
            lambda _: completion.append_completed(
                campaign_root, control_root,
                expected_reread_pin_control_pin=
                    reread_request['pin_control_pin'],
                expected_reread_receipt_pin=reread_pin, **shared),
            capture_completed)
        completed = True
    except WallExpired:
        reason = 'shared_wall_expired'
        error_type = 'WallExpired'
    except (Exception, KeyboardInterrupt) as error:
        reason = 'stage_failed'
        error_type = type(error).__name__

    elapsed = _clock_value(clock) - started
    v.require(elapsed >= 0, 'monotonic clock moved backward at receipt')
    if completed and reason is None and elapsed >= wall_seconds:
        reason = 'shared_wall_expired'
        error_type = 'WallExpired'
    status = 'verified' if completed and reason is None else 'failed'
    value = {
        'format': FORMAT,
        'scope': SCOPE,
        'claim_pin': claim_pin,
        'anchor_pin': expected_plan_pin,
        'campaign_root': state['campaign_root'],
        'control_root': state['control_root'],
        'wall_seconds': wall_seconds,
        'elapsed_seconds': elapsed,
        'last_stage': stage,
        'evidence_pins': evidence,
        'status': status, 'reason': reason, 'error_type': error_type,
        'retry_authorized': False,
        'shared_slot_wall_observed': True,
        'hard_wall_quota_authenticated': False,
        'full_end_to_end_budget_measured': False,
        'campaign_coherence_authenticated': False,
        'campaign_evaluations_credited': 0,
        'invented_only': True,
        'actual_registered_observations_read': False,
        'formal_permission': False,
    }
    raw = _raw(value)
    io._exclusive(root / 'receipt.json', raw)
    v.require((root / 'claim.json').read_bytes() == claim_raw and
              (root / 'receipt.json').read_bytes() == raw,
              'retained slot wall envelope raw changed')
    return value, metadata.pin(raw)


def verify_completed(campaign_root, control_root, *, expected_receipt_pin):
    """Reopen a successful wall receipt and the existing saved completion.

    The caller supplies the receipt's raw pin.  This is read-only and does not
    authenticate a formal budget, independently attest the elapsed clock, or
    launch any child.
    """
    metadata._pin(expected_receipt_pin, 'external slot wall receipt')
    campaign = paths.regular_path(Path(campaign_root), directory=True)
    controls = paths.regular_path(Path(control_root), directory=True)
    v.require(campaign.name.startswith('anomaly-v03-preformal-campaign-') and
              len(campaign.name) == len('anomaly-v03-preformal-campaign-') + 8,
              'dedicated slot wall campaign root required')
    suffix = campaign.name[-8:]
    root = paths.regular_path(
        campaign.parent / ('anomaly-v03-preformal-campaign-wall-' + suffix),
        directory=True)
    v.require({path.name for path in root.iterdir()} ==
              {'claim.json', 'receipt.json'},
              'exact slot wall envelope inventory required')
    receipt_raw = store._pinned(root / 'receipt.json',
                                expected_receipt_pin, MAX_CONTROL)
    receipt = v.strict_json(receipt_raw)
    v.require(type(receipt) is dict and set(receipt) == RECEIPT_FIELDS and
              receipt_raw == _raw(receipt),
              'canonical pinned slot wall receipt required')
    metadata._pin(receipt['claim_pin'], 'slot wall claim')
    claim_raw = store._pinned(root / 'claim.json',
                              receipt['claim_pin'], MAX_CONTROL)
    claim = v.strict_json(claim_raw)
    v.require(type(claim) is dict and set(claim) == CLAIM_FIELDS and
              claim_raw == _raw(claim),
              'canonical pinned slot wall claim required')
    _positive_seconds(claim['wall_seconds'], 'saved slot wall seconds')
    v.require(type(receipt['elapsed_seconds']) in (int, float) and
              math.isfinite(receipt['elapsed_seconds']) and
              0 <= receipt['elapsed_seconds'] < claim['wall_seconds'],
              'successful slot wall elapsed seconds out of range')
    v.require(claim['format'] == CLAIM_FORMAT and claim['scope'] == SCOPE and
              claim['campaign_root'] == str(campaign) and
              claim['control_root'] == str(controls) and
              claim['invented_only'] is True and
              claim['formal_permission'] is False and
              receipt['format'] == FORMAT and receipt['scope'] == SCOPE and
              receipt['anchor_pin'] == claim['anchor_pin'] and
              receipt['campaign_root'] == claim['campaign_root'] and
              receipt['control_root'] == claim['control_root'] and
              receipt['wall_seconds'] == claim['wall_seconds'] and
              receipt['last_stage'] == 'completed' and
              receipt['status'] == 'verified' and
              receipt['reason'] is None and receipt['error_type'] is None and
              receipt['retry_authorized'] is False and
              receipt['shared_slot_wall_observed'] is True and
              receipt['hard_wall_quota_authenticated'] is False and
              receipt['full_end_to_end_budget_measured'] is False and
              receipt['campaign_coherence_authenticated'] is False and
              receipt['campaign_evaluations_credited'] == 0 and
              receipt['invented_only'] is True and
              receipt['actual_registered_observations_read'] is False and
              receipt['formal_permission'] is False,
              'limited successful slot wall claim/receipt binding')
    for name in ('anchor_pin', 'initial_checkpoint_pin', 'intention_pin'):
        metadata._pin(claim[name], 'saved wall ' + name)
    evidence = receipt['evidence_pins']
    v.require(type(evidence) is dict and set(evidence) == EVIDENCE_PINS,
              'exact completed wall evidence pin inventory required')
    for name in EVIDENCE_PINS:
        metadata._pin(evidence[name], 'saved wall ' + name)
    plan_raw = store._pinned(campaign / 'plan.json', claim['anchor_pin'],
                             metadata.MAX_PLAN_BYTES)
    plan = v.strict_json(plan_raw)
    v.require(plan_raw == metadata.encode_plan(plan) and
              plan['root'] == str(campaign) and
              plan['campaign_id'][:8] == suffix and
              plan['source']['revision'] == claim['source_revision'] and
              claim['wall_seconds'] <=
                  plan['budget_candidate']['limits']['wall_seconds'],
              'saved slot wall plan/source/budget changed')
    from . import anomaly_v03_preformal_campaign_controller as controller
    for name, path in (
            ('run_request_pin', campaign / 'intents' /
             '0001-run-budget.json'),
            ('reread_request_pin', campaign / 'intents' /
             '0001-saved-reread.json')):
        store._pinned(path, evidence[name], controller.MAX_REQUEST)
    saved = completion.verify_completed(
        campaign, controls,
        expected_plan_pin=claim['anchor_pin'],
        expected_initial_checkpoint_pin=claim['initial_checkpoint_pin'],
        expected_intention_pin=claim['intention_pin'],
        expected_prepare_receipt_pin=evidence['prepare_receipt_pin'],
        expected_started_record_pin=evidence['started_record_pin'],
        expected_next_checkpoint_pin=evidence['next_checkpoint_pin'],
        expected_run_pin_control_pin=evidence['run_pin_control_pin'],
        expected_generation_receipt_pin=evidence['generation_receipt_pin'],
        expected_reread_pin_control_pin=evidence['reread_pin_control_pin'],
        expected_reread_receipt_pin=evidence['reread_receipt_pin'],
        expected_completed_record_pin=evidence['completed_record_pin'],
        expected_terminal_checkpoint_pin=evidence['terminal_checkpoint_pin'])
    v.require(saved['status'] == 'partial_declarations_unverified' and
              saved['declared_completed_chunks'] == 1 and
              saved['declared_completed_evaluations'] == 6 and
              saved['campaign_evaluations_credited'] == 0 and
              saved['formal_permission'] is False and
              saved['completed_record_pin'] ==
                  evidence['completed_record_pin'] and
              saved['terminal_checkpoint_pin'] ==
                  evidence['terminal_checkpoint_pin'],
              'saved completed chain differs from slot wall receipt')
    v.require(store._pinned(root / 'claim.json', receipt['claim_pin'],
                            MAX_CONTROL) == claim_raw and
              store._pinned(root / 'receipt.json', expected_receipt_pin,
                            MAX_CONTROL) == receipt_raw,
              'slot wall envelope changed during readback')
    return {
        'status': 'verified_retained',
        'scope': SCOPE,
        'receipt_pin': expected_receipt_pin,
        'claim_pin': receipt['claim_pin'],
        'elapsed_seconds': receipt['elapsed_seconds'],
        'wall_seconds': claim['wall_seconds'],
        'completed_record_pin': evidence['completed_record_pin'],
        'terminal_checkpoint_pin': evidence['terminal_checkpoint_pin'],
        'full_end_to_end_budget_measured': False,
        'formal_permission': False,
    }
