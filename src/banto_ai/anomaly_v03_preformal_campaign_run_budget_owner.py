"""Enter one invented run-budget CLI from its saved external request pin.

The campaign store and run-intent store must already be complete. This owner
reopens both immediately before handing their saved raw bytes to the existing
single-CLI controller. A verified CLI is still not a coherent or formal
campaign, and a failed receipt does not permit a retry.
"""
from __future__ import annotations

from pathlib import Path

from . import anomaly_v03 as v
from . import anomaly_v03_preformal_campaign_controller as controller
from . import anomaly_v03_preformal_campaign_metadata as metadata
from . import anomaly_v03_preformal_campaign_run_intent_store as intent
from . import anomaly_v03_preformal_campaign_store as store
from . import anomaly_v03_reader_evidence as observed


def _inputs(*, expected_plan_pin, expected_initial_checkpoint_pin,
            expected_intention_pin, expected_prepare_receipt_pin,
            expected_started_record_pin, expected_next_checkpoint_pin):
    return dict(
        expected_plan_pin=expected_plan_pin,
        expected_initial_checkpoint_pin=expected_initial_checkpoint_pin,
        expected_intention_pin=expected_intention_pin,
        expected_prepare_receipt_pin=expected_prepare_receipt_pin,
        expected_started_record_pin=expected_started_record_pin,
        expected_next_checkpoint_pin=expected_next_checkpoint_pin)


def execute_run_budget(campaign_root, control_root, *, expected_plan_pin,
                       expected_initial_checkpoint_pin, expected_intention_pin,
                       expected_prepare_receipt_pin,
                       expected_started_record_pin,
                       expected_next_checkpoint_pin,
                       expected_pin_control_pin):
    """Return the retained CLI receipt and its raw pin, including on failure.

    Any prelaunch mismatch raises before the native CLI is called. Once the
    controller starts, its saved receipt is the only accepted result. No
    second attempt is made here.
    """
    inputs = _inputs(
        expected_plan_pin=expected_plan_pin,
        expected_initial_checkpoint_pin=expected_initial_checkpoint_pin,
        expected_intention_pin=expected_intention_pin,
        expected_prepare_receipt_pin=expected_prepare_receipt_pin,
        expected_started_record_pin=expected_started_record_pin,
        expected_next_checkpoint_pin=expected_next_checkpoint_pin)
    verified = intent.verify_request(
        campaign_root, control_root,
        expected_pin_control_pin=expected_pin_control_pin, **inputs)
    state = store.verify_started_store(
        campaign_root, control_root,
        expected_run_intent_pin=verified['request_pin'], **inputs)
    v.require(state['status'] == 'started_record_fixed' and
              state['plan_pin'] == expected_plan_pin and
              state['started_record_pin'] == expected_started_record_pin and
              state['next_checkpoint_pin'] == expected_next_checkpoint_pin and
              state['checkpoint']['record_count'] == 1 and
              state['checkpoint']['head_sha256'] ==
              expected_started_record_pin['sha256'] and
              state['run_intent_pin'] == verified['request_pin'] and
              state['run_intent_raw'] is not None and
              metadata.pin(state['run_intent_raw']) ==
              verified['request_pin'] and
              state['campaign_coherence_authenticated'] is False and
              state['formal_permission'] is False,
              'saved pinned slot-0 run-budget launch inputs required')
    plan = v.strict_json(state['plan_raw'])
    records = state['record_raws']
    v.require(type(records) is list and len(records) == 1 and
              metadata.pin(records[0]) == expected_started_record_pin and
              v.strict_json(records[0])['state'] == 'started' and
              v.strict_json(records[0])['chunk_index'] == 0 and
              v.strict_json(records[0])['attempt'] == 1,
              'one saved slot-0 started record required')
    # Reopen the external request pin-control and all of its upstream raw
    # immediately before the controller's own last pre-spawn checks.
    latest = intent.verify_request(
        campaign_root, control_root,
        expected_pin_control_pin=expected_pin_control_pin, **inputs)
    v.require(latest == verified and
              latest['request_pin'] == metadata.pin(state['run_intent_raw']) and
              latest['record_count'] == 1 and
              latest['journal_head_sha256'] ==
              expected_started_record_pin['sha256'] and
              latest['native_run_started'] is False and
              latest['campaign_coherence_authenticated'] is False and
              latest['formal_permission'] is False,
              'external run-budget pin-control changed before CLI entry')
    request_path = Path(latest['request_path'])
    v.require(request_path == Path(plan['root']) / 'intents' /
              '0001-run-budget.json',
              'fixed saved run-budget request path required')
    value, returned_pin = controller.execute_owned(
        request_path, latest['request_pin'], state['plan_raw'],
        expected_plan_pin, records, expected_record_count=1,
        expected_head_sha256=expected_started_record_pin['sha256'])
    metadata._pin(returned_pin, 'owned run-budget receipt')
    receipt_path = controller._control(
        plan, v.strict_json(records[0]), 'run-budget') / 'receipt.json'
    receipt_raw = observed._file(receipt_path, controller.MAX_RECEIPT)
    receipt = v.strict_json(receipt_raw)
    v.require(metadata.pin(receipt_raw) == returned_pin and
              receipt_raw == v.canonical_json(receipt) + b'\n' and
              receipt == value and
              receipt['format'] == controller.RECEIPT_FORMAT and
              receipt['scope'] == 'invented-two-slot-owned-cli-only' and
              receipt['phase'] == 'run-budget' and
              receipt['request_pin'] == latest['request_pin'] and
              receipt['anchor_pin'] == expected_plan_pin and
              receipt['journal_count'] == 1 and
              receipt['journal_head_sha256'] ==
              expected_started_record_pin['sha256'] and
              receipt['chunk_index'] == 0 and
              receipt['attempt'] == 1 and
              receipt['status'] in ('verified', 'failed') and
              receipt['invented_only'] is True and
              receipt['actual_registered_observations_read'] is False and
              receipt['campaign_evaluations_credited'] == 0 and
              receipt['campaign_coherence_authenticated'] is False and
              receipt['full_end_to_end_budget_measured'] is False and
              receipt['formal_permission'] is False,
              'retained limited run-budget receipt changed')
    if receipt['status'] == 'verified':
        v.require(controller._load_receipt(
            plan, v.strict_json(records[0]), 'run-budget', returned_pin) ==
            receipt, 'saved verified run-budget evidence changed')
    else:
        v.require(receipt['retry_authorized'] is False and
                  receipt['descendant_exit_confirmed'] is False and
                  type(receipt['reason']) is str,
                  'failed run-budget receipt must remain terminal')
    return receipt, returned_pin
