"""Opt-in invented slot-0 wall envelope through saved-row control binding.

The outer monotonic clock covers the existing wall chain, retained-byte reads,
and the pure journal-to-row bridge.  Its limit is cooperative.  This is one
invented six-row slice, not a producer campaign or a formal resource claim.
"""
from __future__ import annotations

import math
from pathlib import Path
import time

from . import _anomaly_v03_io as io
from . import _anomaly_v03_runtime as paths
from . import anomaly_v03 as v
from . import anomaly_v03_preformal_campaign_metadata as metadata
from . import anomaly_v03_preformal_campaign_saved_row_bridge as bridge
from . import anomaly_v03_preformal_campaign_store as store
from . import anomaly_v03_preformal_campaign_wall_envelope as wall
from . import anomaly_v03_preformal_saved_row_coverage as coverage


ROOT = Path(__file__).resolve().parents[2]
FORMAT = 'anomaly-v03-preformal-campaign-slot-wall-row-envelope-v1'
CLAIM_FORMAT = 'anomaly-v03-preformal-campaign-slot-wall-row-claim-v1'
SCOPE = 'invented-slot-0-six-saved-rows-single-invocation-cooperative-wall-only'
MAX_CONTROL = 32 * 1024
MAX_BRIDGE = 64 * 1024
RAW_NAMES = frozenset(coverage.RAW_LIMITS)
CLAIM_FIELDS = frozenset({
    'format', 'scope', 'campaign_root', 'control_root', 'plan_pin',
    'initial_checkpoint_pin', 'intention_pin', 'wall_seconds',
    'invented_only', 'formal_permission',
})
RECEIPT_FIELDS = frozenset({
    'format', 'scope', 'claim_pin', 'campaign_root', 'control_root',
    'wall_seconds', 'elapsed_seconds', 'last_stage', 'status', 'reason',
    'error_type', 'inner_wall_receipt_pin', 'bridge_result_pin',
    'saved_row_raw_pins', 'shared_slot_wall_observed',
    'hard_wall_quota_authenticated', 'full_end_to_end_budget_measured',
    'campaign_coherence_authenticated', 'campaign_evaluations_credited',
    'invented_only', 'actual_registered_observations_read',
    'formal_permission', 'retry_authorized',
})


class WallExpired(ValueError):
    """The outer cooperative clock expired at a stage boundary."""


def _raw(value, maximum=MAX_CONTROL):
    raw = v.canonical_json(value) + b'\n'
    v.require(len(raw) <= maximum, 'bounded wall row envelope raw')
    return raw


def _location(campaign_root, control_root):
    campaign = paths.regular_path(Path(campaign_root), directory=True)
    controls = paths.regular_path(Path(control_root), directory=True)
    prefix = 'anomaly-v03-preformal-campaign-'
    v.require(campaign.parent == ROOT / 'artifacts' and
              campaign.name.startswith(prefix) and
              len(campaign.name) == len(prefix) + 8 and
              controls == campaign.parent /
                  ('anomaly-v03-preformal-campaign-control-' +
                   campaign.name[-8:]),
              'dedicated matching campaign and control roots required')
    root = campaign.parent / (
        'anomaly-v03-preformal-campaign-wall-row-' + campaign.name[-8:])
    return campaign, controls, root


def _roots(campaign_root, control_root):
    campaign, controls, root = _location(campaign_root, control_root)
    paths.regular_path(root, directory=True, missing=True)
    v.require(not root.exists(), 'fresh wall row envelope root required')
    return campaign, controls, root


def _time(clock):
    current = clock()
    v.require(type(current) in (int, float) and math.isfinite(current) and
              current >= 0, 'finite nonnegative monotonic clock required')
    return current


def _remaining(clock, started, wall_seconds):
    elapsed = _time(clock) - started
    v.require(elapsed >= 0, 'monotonic clock moved backward')
    if elapsed >= wall_seconds:
        raise WallExpired('shared wall expired')
    return wall_seconds - elapsed


def _pinned(path, pin, maximum, remaining):
    remaining()
    raw = store._pinned(path, pin, maximum)
    remaining()
    return raw


def bind_retained(campaign_root, control_root, *, expected_plan_pin,
                  expected_started_record_pin, expected_completed_record_pin,
                  expected_started_checkpoint_pin,
                  expected_terminal_checkpoint_pin,
                  expected_generation_receipt_pin,
                  expected_reread_receipt_pin, remaining=lambda: 1):
    """Reopen one completed journal and ten externally journal-pinned raws.

    The plan/checkpoint/owner pins come from the just-completed wall receipt;
    row pins must match its completed record.  No saved payload is reopened.
    """
    campaign = Path(campaign_root)
    controls = Path(control_root)
    plan_raw = _pinned(campaign / 'plan.json', expected_plan_pin,
                       metadata.MAX_PLAN_BYTES, remaining)
    records = [
        _pinned(campaign / 'journal' / f'{index:06d}.json', pin,
                metadata.MAX_RECORD_BYTES, remaining)
        for index, pin in ((1, expected_started_record_pin),
                           (2, expected_completed_record_pin))
    ]
    started_raw = _pinned(controls / 'checkpoint-000001.json',
                          expected_started_checkpoint_pin,
                          bridge.MAX_CHECKPOINT, remaining)
    terminal_raw = _pinned(controls / 'checkpoint-000002.json',
                           expected_terminal_checkpoint_pin,
                           bridge.MAX_CHECKPOINT, remaining)
    control = campaign / 'control' / '000-1'
    generation_raw = _pinned(control / 'run-budget' / 'receipt.json',
                             expected_generation_receipt_pin,
                             bridge.MAX_OWNER_RECEIPT, remaining)
    reread_raw = _pinned(control / 'saved-reread' / 'receipt.json',
                         expected_reread_receipt_pin,
                         bridge.MAX_OWNER_RECEIPT, remaining)
    plan = v.strict_json(plan_raw)
    completed = v.strict_json(records[1])
    attempt = Path(metadata.attempt_root(plan, 0, 1))
    v.require(completed['attempt_root'] == str(attempt) and
              attempt.parent == ROOT / 'artifacts',
              'journal latest slot-0 attempt root required')
    code = attempt.name.removeprefix(metadata.ATTEMPT_PREFIX)
    reread = attempt.parent / ('anomaly-v03-preformal-saved-row-reread-' + code)
    manifest = attempt.parent / (
        'anomaly-v03-preformal-generated-pinsets-' + code) / 'pins.json'
    evidence = completed['evidence_pins']
    pins = {name: evidence[evidence_name]
            for name, evidence_name in bridge.ENTRY_PINS.items()}
    pins['manifest'] = completed['manifest_pin']
    paths_by_name = {
        'result': reread / 'result.json',
        'rows': reread / 'rows.json',
        'budget': reread / 'resource-budget.json',
        'supervision': reread / 'owned-reader/supervision.json',
        'stdout': reread / 'owned-reader/worker/report.json',
        'manifest': manifest,
        'receipt': attempt / 'saved/receipt.json',
        'report': attempt / 'saved/report.json',
        'savepoint': attempt / 'saved/savepoint.json',
        'outer': attempt / 'owned-generator/result.json',
    }
    v.require(set(paths_by_name) == RAW_NAMES and
              set(pins) == RAW_NAMES, 'exact ten saved-row raw inputs')
    entry = {'expected_pins': pins}
    for name in sorted(RAW_NAMES):
        entry[name + '_raw'] = _pinned(
            paths_by_name[name], pins[name], coverage.RAW_LIMITS[name],
            remaining)
    remaining()
    result = bridge.bind_completed_saved_rows(
        plan_raw, records, started_raw, terminal_raw, entry,
        generation_receipt_raw=generation_raw,
        saved_reread_receipt_raw=reread_raw,
        expected_plan_pin=expected_plan_pin,
        expected_started_checkpoint_pin=expected_started_checkpoint_pin,
        expected_terminal_checkpoint_pin=expected_terminal_checkpoint_pin)
    remaining()
    v.require(result['status'] == 'partial_saved_row_journal_link_only' and
              result['verified_chunks'] == 1 and
              result['verified_evaluations'] == 6 and
              result['campaign_evaluations_credited'] == 0 and
              result['formal_permission'] is False,
              'limited invented saved-row bridge required')
    for name in sorted(RAW_NAMES):
        _pinned(paths_by_name[name], pins[name], coverage.RAW_LIMITS[name],
                remaining)
    for path, pin, maximum in (
        (campaign / 'plan.json', expected_plan_pin,
         metadata.MAX_PLAN_BYTES),
        (campaign / 'journal/000001.json', expected_started_record_pin,
         metadata.MAX_RECORD_BYTES),
        (campaign / 'journal/000002.json', expected_completed_record_pin,
         metadata.MAX_RECORD_BYTES),
        (controls / 'checkpoint-000001.json', expected_started_checkpoint_pin,
         bridge.MAX_CHECKPOINT),
        (controls / 'checkpoint-000002.json', expected_terminal_checkpoint_pin,
         bridge.MAX_CHECKPOINT),
        (control / 'run-budget/receipt.json', expected_generation_receipt_pin,
         bridge.MAX_OWNER_RECEIPT),
        (control / 'saved-reread/receipt.json', expected_reread_receipt_pin,
         bridge.MAX_OWNER_RECEIPT),
    ):
        _pinned(path, pin, maximum, remaining)
    return result, pins


def execute(campaign_root, control_root, *, expected_plan_pin,
            expected_initial_checkpoint_pin, expected_intention_pin,
            wall_seconds, clock=time.monotonic):
    """Run the existing slot envelope and bridge under one outer clock."""
    wall._positive_seconds(wall_seconds, 'outer wall seconds')
    started = _time(clock)
    campaign, controls, root = _roots(campaign_root, control_root)
    claim = {
        'format': CLAIM_FORMAT, 'scope': SCOPE,
        'campaign_root': str(campaign), 'control_root': str(controls),
        'plan_pin': expected_plan_pin,
        'initial_checkpoint_pin': expected_initial_checkpoint_pin,
        'intention_pin': expected_intention_pin,
        'wall_seconds': wall_seconds,
        'invented_only': True, 'formal_permission': False,
    }
    claim_raw = _raw(claim)
    root.mkdir()
    io._exclusive(root / 'claim.json', claim_raw)
    claim_pin = metadata.pin(claim_raw)
    inner_pin = None
    bridge_pin = None
    source_pins = {}
    stage = 'wall-chain'
    reason = None
    error_type = None
    try:
        inner, inner_pin = wall.execute(
            campaign, controls, expected_plan_pin=expected_plan_pin,
            expected_initial_checkpoint_pin=expected_initial_checkpoint_pin,
            expected_intention_pin=expected_intention_pin,
            wall_seconds=_remaining(clock, started, wall_seconds),
            clock=clock)
        v.require(inner['status'] == 'verified', 'inner wall chain failed')
        _remaining(clock, started, wall_seconds)
        stage = 'saved-row-bridge'
        evidence = inner['evidence_pins']
        result, source_pins = bind_retained(
            campaign, controls, expected_plan_pin=expected_plan_pin,
            expected_started_record_pin=evidence['started_record_pin'],
            expected_completed_record_pin=evidence['completed_record_pin'],
            expected_started_checkpoint_pin=evidence['next_checkpoint_pin'],
            expected_terminal_checkpoint_pin=evidence['terminal_checkpoint_pin'],
            expected_generation_receipt_pin=evidence['generation_receipt_pin'],
            expected_reread_receipt_pin=evidence['reread_receipt_pin'],
            remaining=lambda: _remaining(clock, started, wall_seconds))
        raw = _raw(result, MAX_BRIDGE)
        _remaining(clock, started, wall_seconds)
        io._exclusive(root / 'bridge-result.json', raw)
        bridge_pin = metadata.pin(raw)
        _remaining(clock, started, wall_seconds)
        stage = 'completed'
    except WallExpired:
        reason, error_type = 'shared_wall_expired', 'WallExpired'
    except (Exception, KeyboardInterrupt) as error:
        reason, error_type = ('stage_failed', type(error).__name__)
    elapsed = _time(clock) - started
    v.require(elapsed >= 0, 'monotonic clock moved backward at receipt')
    if reason is None and elapsed >= wall_seconds:
        reason, error_type = 'shared_wall_expired', 'WallExpired'
    receipt = {
        'format': FORMAT, 'scope': SCOPE, 'claim_pin': claim_pin,
        'campaign_root': str(campaign), 'control_root': str(controls),
        'wall_seconds': wall_seconds, 'elapsed_seconds': elapsed,
        'last_stage': stage, 'status': 'verified' if reason is None else 'failed',
        'reason': reason, 'error_type': error_type,
        'inner_wall_receipt_pin': inner_pin, 'bridge_result_pin': bridge_pin,
        'saved_row_raw_pins': source_pins,
        'shared_slot_wall_observed': True,
        'hard_wall_quota_authenticated': False,
        'full_end_to_end_budget_measured': False,
        'campaign_coherence_authenticated': False,
        'campaign_evaluations_credited': 0,
        'invented_only': True,
        'actual_registered_observations_read': False,
        'formal_permission': False, 'retry_authorized': False,
    }
    receipt_raw = _raw(receipt)
    io._exclusive(root / 'receipt.json', receipt_raw)
    v.require((root / 'claim.json').read_bytes() == claim_raw and
              (root / 'receipt.json').read_bytes() == receipt_raw,
              'wall row receipt changed after write')
    return receipt, metadata.pin(receipt_raw)


def verify_retained(campaign_root, control_root, *, expected_receipt_pin):
    """Read-only verification of a successful invented wall-row receipt."""
    metadata._pin(expected_receipt_pin, 'external wall row receipt')
    campaign, controls, root = _location(campaign_root, control_root)
    paths.regular_path(root, directory=True)
    v.require({path.name for path in root.iterdir()} ==
              {'claim.json', 'bridge-result.json', 'receipt.json'},
              'exact completed wall row inventory required')
    receipt_raw = store._pinned(root / 'receipt.json',
                                expected_receipt_pin, MAX_CONTROL)
    receipt = v.strict_json(receipt_raw)
    v.require(type(receipt) is dict and set(receipt) == RECEIPT_FIELDS and
              receipt_raw == _raw(receipt),
              'canonical pinned wall row receipt')
    claim_raw = store._pinned(root / 'claim.json',
                              receipt['claim_pin'], MAX_CONTROL)
    claim = v.strict_json(claim_raw)
    v.require(type(claim) is dict and set(claim) == CLAIM_FIELDS and
              claim_raw == _raw(claim),
              'canonical pinned wall row claim')
    wall._positive_seconds(claim['wall_seconds'], 'saved outer wall seconds')
    v.require(claim['format'] == CLAIM_FORMAT and claim['scope'] == SCOPE and
              claim['campaign_root'] == str(campaign) and
              claim['control_root'] == str(controls) and
              claim['invented_only'] is True and
              claim['formal_permission'] is False and
              receipt['format'] == FORMAT and receipt['scope'] == SCOPE and
              receipt['campaign_root'] == str(campaign) and
              receipt['control_root'] == str(controls) and
              receipt['wall_seconds'] == claim['wall_seconds'] and
              type(receipt['elapsed_seconds']) in (int, float) and
              math.isfinite(receipt['elapsed_seconds']) and
              0 <= receipt['elapsed_seconds'] < claim['wall_seconds'] and
              receipt['last_stage'] == 'completed' and
              receipt['status'] == 'verified' and
              receipt['reason'] is None and
              receipt['error_type'] is None and
              receipt['shared_slot_wall_observed'] is True and
              receipt['hard_wall_quota_authenticated'] is False and
              receipt['full_end_to_end_budget_measured'] is False and
              receipt['campaign_coherence_authenticated'] is False and
              receipt['campaign_evaluations_credited'] == 0 and
              receipt['invented_only'] is True and
              receipt['actual_registered_observations_read'] is False and
              receipt['formal_permission'] is False and
              receipt['retry_authorized'] is False,
              'limited successful wall row claim/receipt required')
    metadata._pin(receipt['inner_wall_receipt_pin'], 'saved inner wall receipt')
    metadata._pin(receipt['bridge_result_pin'], 'saved bridge result')
    bridge_raw = store._pinned(root / 'bridge-result.json',
                               receipt['bridge_result_pin'], MAX_BRIDGE)
    bridge_value = v.strict_json(bridge_raw)
    v.require(bridge_raw == _raw(bridge_value, MAX_BRIDGE),
              'canonical pinned bridge result')
    inner = wall.verify_completed(
        campaign, controls,
        expected_receipt_pin=receipt['inner_wall_receipt_pin'])
    v.require(inner['status'] == 'verified_retained' and
              inner['receipt_pin'] == receipt['inner_wall_receipt_pin'] and
              type(inner['elapsed_seconds']) in (int, float) and
              inner['elapsed_seconds'] <= receipt['elapsed_seconds'] and
              inner['completed_record_pin'] ==
                  bridge_value['completed_record_pin'] and
              inner['terminal_checkpoint_pin'] ==
                  bridge_value['terminal_checkpoint_pin'],
              'inner wall completion differs from bridge')
    inner_root = campaign.parent / (
        'anomaly-v03-preformal-campaign-wall-' + campaign.name[-8:])
    inner_raw = store._pinned(
        inner_root / 'receipt.json',
        receipt['inner_wall_receipt_pin'], wall.MAX_CONTROL)
    inner_claim = v.strict_json(store._pinned(
        inner_root / 'claim.json', inner['claim_pin'], wall.MAX_CONTROL))
    v.require(inner_claim['anchor_pin'] == claim['plan_pin'] and
              inner_claim['initial_checkpoint_pin'] ==
                  claim['initial_checkpoint_pin'] and
              inner_claim['intention_pin'] == claim['intention_pin'] and
              inner_claim['campaign_root'] == claim['campaign_root'] and
              inner_claim['control_root'] == claim['control_root'] and
              inner_claim['wall_seconds'] <= claim['wall_seconds'],
              'inner wall inputs differ from outer claim')
    evidence = v.strict_json(inner_raw)['evidence_pins']
    result, pins = bind_retained(
        campaign, controls, expected_plan_pin=claim['plan_pin'],
        expected_started_record_pin=evidence['started_record_pin'],
        expected_completed_record_pin=evidence['completed_record_pin'],
        expected_started_checkpoint_pin=evidence['next_checkpoint_pin'],
        expected_terminal_checkpoint_pin=evidence['terminal_checkpoint_pin'],
        expected_generation_receipt_pin=evidence['generation_receipt_pin'],
        expected_reread_receipt_pin=evidence['reread_receipt_pin'])
    v.require(result == bridge_value and
              pins == receipt['saved_row_raw_pins'],
              'saved row result/pins differ from completed wall')
    v.require(store._pinned(root / 'claim.json', receipt['claim_pin'],
                            MAX_CONTROL) == claim_raw and
              store._pinned(root / 'bridge-result.json',
                            receipt['bridge_result_pin'],
                            MAX_BRIDGE) == bridge_raw and
              store._pinned(root / 'receipt.json', expected_receipt_pin,
                            MAX_CONTROL) == receipt_raw,
              'wall row envelope changed during readback')
    return {
        'status': 'verified_retained', 'scope': SCOPE,
        'receipt_pin': expected_receipt_pin,
        'inner_wall_receipt_pin': receipt['inner_wall_receipt_pin'],
        'bridge_result_pin': receipt['bridge_result_pin'],
        'verified_chunks': 1, 'verified_evaluations': 6,
        'elapsed_seconds': receipt['elapsed_seconds'],
        'wall_seconds': receipt['wall_seconds'],
        'full_end_to_end_budget_measured': False,
        'campaign_evaluations_credited': 0, 'formal_permission': False,
    }
