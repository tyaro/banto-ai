"""Freeze one invented slot-0 completion from two saved owned receipts.

This is a metadata-only terminal boundary for the first invented chunk. It
reopens the generation and fresh saved-reread receipts before deriving the
completed declaration. The journal record is committed before its separate
count/head checkpoint. An interrupted or partial write is retained and is
never resumed here. No registered observation is read or credited.
"""
from __future__ import annotations

import copy
from pathlib import Path

from . import _anomaly_v03_io as io
from . import anomaly_v03 as v
from . import anomaly_v03_preformal_campaign_controller as controller
from . import anomaly_v03_preformal_campaign_metadata as metadata
from . import anomaly_v03_preformal_campaign_store as store


CHECKPOINT_FORMAT = 'anomaly-v03-preformal-campaign-completed-checkpoint-v1'
CHECKPOINT_NAME = 'checkpoint-000002.json'
RECORD_NAME = '000002.json'
MAX_CHECKPOINT = 4096


def _stage(campaign_root, control_root, *, allow_completion,
           expected_plan_pin, expected_initial_checkpoint_pin,
           expected_intention_pin, expected_prepare_receipt_pin,
           expected_started_record_pin, expected_next_checkpoint_pin,
           expected_run_pin_control_pin, expected_generation_receipt_pin,
           expected_reread_pin_control_pin):
    # Imported at use time so this module does not depend on request dispatch
    # while the saved-reread intent module is being initialized.
    from . import anomaly_v03_preformal_campaign_reread_intent_store as stage

    state = stage.verify_postrun_stage(
        campaign_root, control_root,
        expected_plan_pin=expected_plan_pin,
        expected_initial_checkpoint_pin=expected_initial_checkpoint_pin,
        expected_intention_pin=expected_intention_pin,
        expected_prepare_receipt_pin=expected_prepare_receipt_pin,
        expected_started_record_pin=expected_started_record_pin,
        expected_next_checkpoint_pin=expected_next_checkpoint_pin,
        expected_run_pin_control_pin=expected_run_pin_control_pin,
        expected_generation_receipt_pin=expected_generation_receipt_pin,
        expected_pin_control_pin=expected_reread_pin_control_pin,
        allow_completion=allow_completion)
    records = state['record_raws']
    checkpoint = state['checkpoint']
    v.require(type(records) is list and len(records) == 1 and
              metadata.pin(records[0]) == expected_started_record_pin and
              state['plan_pin'] == expected_plan_pin and
              checkpoint['record_count'] == 1 and
              checkpoint['head_sha256'] ==
              expected_started_record_pin['sha256'] and
              state['generation_receipt_pin'] ==
              expected_generation_receipt_pin and
              state['campaign_coherence_authenticated'] is False and
              state['formal_permission'] is False,
              'pinned count-1 post-reread stage required')
    return state


def _completed_raw(state, expected_generation_receipt_pin,
                   expected_reread_receipt_pin):
    metadata._pin(expected_reread_receipt_pin, 'external saved-reread receipt')
    plan = v.strict_json(state['plan_raw'])
    started = v.strict_json(state['record_raws'][0])
    reread_path = controller._control(plan, started, 'saved-reread') / 'receipt.json'
    reread_raw = store._pinned(reread_path, expected_reread_receipt_pin,
                               controller.MAX_RECEIPT)
    reread = v.strict_json(reread_raw)
    v.require(reread_raw == v.canonical_json(reread) + b'\n' and
              reread.get('status') == 'verified' and
              reread.get('phase') == 'saved-reread' and
              reread.get('actual_registered_observations_read') is False and
              reread.get('campaign_evaluations_credited') == 0 and
              reread.get('formal_permission') is False,
              'pinned closed saved-reread receipt required')
    raw = controller.completion_record(
        state['plan_raw'], state['plan_pin'], state['record_raws'],
        expected_record_count=1,
        expected_head_sha256=state['checkpoint']['head_sha256'],
        generation_receipt_pin=expected_generation_receipt_pin,
        reread_receipt_pin=expected_reread_receipt_pin)
    record_pin = metadata.pin(raw)
    result = metadata.reduce_journal(
        state['plan_raw'], [*state['record_raws'], raw],
        expected_plan_pin=state['plan_pin'], expected_record_count=2,
        expected_head_sha256=record_pin['sha256'])
    v.require(result['record_count'] == 2 and
              result['declared_completed_chunks'] == 1 and
              result['declared_completed_evaluations'] == 6 and
              result['completed_chunk_indices'] == [0] and
              result['missing_chunk_indices'] == list(range(1, 480)) and
              result['latest_unfinished_state'] is None and
              result['producer_campaign_anchor'] is None and
              result['campaign_coherence_authenticated'] is False and
              result['producer_execution_authenticated'] is False and
              result['launch_authorized'] is False and
              result['resume_authorized'] is False and
              result['campaign_evaluations_credited'] == 0 and
              result['formal_permission'] is False and
              result['clusters'] is None and result['diagnostics'] is None and
              result['slice_source'] is None,
              'closed one-chunk metadata completion only')
    v.require(store._pinned(reread_path, expected_reread_receipt_pin,
                             controller.MAX_RECEIPT) == reread_raw,
              'saved-reread receipt changed during completion derivation')
    return raw, record_pin, reread_raw, result


def _checkpoint(plan_pin, started_checkpoint_pin,
                generation_receipt_pin, reread_receipt_pin,
                run_pin_control_pin, reread_pin_control_pin, completed_pin):
    return {
        'format': CHECKPOINT_FORMAT,
        'anchor_pin': copy.deepcopy(plan_pin),
        'previous_checkpoint_pin': copy.deepcopy(started_checkpoint_pin),
        'generation_receipt_pin': copy.deepcopy(generation_receipt_pin),
        'saved_reread_receipt_pin': copy.deepcopy(reread_receipt_pin),
        'run_request_control_pin': copy.deepcopy(run_pin_control_pin),
        'reread_request_control_pin': copy.deepcopy(reread_pin_control_pin),
        'completed_record_pin': copy.deepcopy(completed_pin),
        'record_count': 2, 'head_sha256': completed_pin['sha256'],
        'invented_only': True,
        'actual_registered_observations_read': False,
        'campaign_coherence_authenticated': False,
        'launch_authorized': False, 'resume_authorized': False,
        'campaign_evaluations_credited': 0, 'formal_permission': False,
    }


def _inputs(expected_plan_pin, expected_initial_checkpoint_pin,
            expected_intention_pin, expected_prepare_receipt_pin,
            expected_started_record_pin, expected_next_checkpoint_pin,
            expected_run_pin_control_pin, expected_generation_receipt_pin,
            expected_reread_pin_control_pin):
    return {
        'expected_plan_pin': expected_plan_pin,
        'expected_initial_checkpoint_pin': expected_initial_checkpoint_pin,
        'expected_intention_pin': expected_intention_pin,
        'expected_prepare_receipt_pin': expected_prepare_receipt_pin,
        'expected_started_record_pin': expected_started_record_pin,
        'expected_next_checkpoint_pin': expected_next_checkpoint_pin,
        'expected_run_pin_control_pin': expected_run_pin_control_pin,
        'expected_generation_receipt_pin': expected_generation_receipt_pin,
        'expected_reread_pin_control_pin': expected_reread_pin_control_pin,
    }


def append_completed(campaign_root, control_root, *, expected_plan_pin,
                     expected_initial_checkpoint_pin, expected_intention_pin,
                     expected_prepare_receipt_pin, expected_started_record_pin,
                     expected_next_checkpoint_pin,
                     expected_run_pin_control_pin,
                     expected_generation_receipt_pin,
                     expected_reread_pin_control_pin,
                     expected_reread_receipt_pin):
    """Commit record 2, then the external checkpoint; never repair a gap."""
    inputs = _inputs(
        expected_plan_pin, expected_initial_checkpoint_pin,
        expected_intention_pin, expected_prepare_receipt_pin,
        expected_started_record_pin, expected_next_checkpoint_pin,
        expected_run_pin_control_pin, expected_generation_receipt_pin,
        expected_reread_pin_control_pin)
    state = _stage(campaign_root, control_root,
                   allow_completion=False, **inputs)
    record_raw, record_pin, _, _ = _completed_raw(
        state, expected_generation_receipt_pin, expected_reread_receipt_pin)
    checkpoint_raw = store._lf(_checkpoint(
        expected_plan_pin, expected_next_checkpoint_pin,
        expected_generation_receipt_pin, expected_reread_receipt_pin,
        expected_run_pin_control_pin, expected_reread_pin_control_pin,
        record_pin), MAX_CHECKPOINT)
    checkpoint_pin = metadata.pin(checkpoint_raw)
    campaign = Path(state['campaign_root'])
    controls = Path(state['control_root'])
    again = _stage(campaign, controls, allow_completion=False, **inputs)
    again_raw, again_pin, _, _ = _completed_raw(
        again, expected_generation_receipt_pin,
        expected_reread_receipt_pin)
    v.require(again_raw == record_raw and again_pin == record_pin and
              again['plan_raw'] == state['plan_raw'] and
              again['record_raws'] == state['record_raws'],
              'completion inputs changed before journal append')
    staged = campaign / 'pending' / RECORD_NAME
    committed = campaign / 'journal' / RECORD_NAME
    checkpoint_path = controls / CHECKPOINT_NAME
    v.require(not staged.exists() and not committed.exists() and
              not checkpoint_path.exists(),
              'fresh completion record/checkpoint required')
    io._exclusive(staged, record_raw)
    v.require(store._read(staged, metadata.MAX_RECORD_BYTES) == record_raw,
              'staged completion record changed')
    io._rename_no_replace(staged, committed)
    io._exclusive(checkpoint_path, checkpoint_raw)
    return verify_completed(
        campaign, controls, expected_completed_record_pin=record_pin,
        expected_terminal_checkpoint_pin=checkpoint_pin,
        expected_reread_receipt_pin=expected_reread_receipt_pin, **inputs)


def verify_completed(campaign_root, control_root, *, expected_plan_pin,
                     expected_initial_checkpoint_pin, expected_intention_pin,
                     expected_prepare_receipt_pin, expected_started_record_pin,
                     expected_next_checkpoint_pin,
                     expected_run_pin_control_pin,
                     expected_generation_receipt_pin,
                     expected_reread_pin_control_pin,
                     expected_reread_receipt_pin,
                     expected_completed_record_pin,
                     expected_terminal_checkpoint_pin):
    """Reread both receipts and exact terminal count/head without a launch."""
    inputs = _inputs(
        expected_plan_pin, expected_initial_checkpoint_pin,
        expected_intention_pin, expected_prepare_receipt_pin,
        expected_started_record_pin, expected_next_checkpoint_pin,
        expected_run_pin_control_pin, expected_generation_receipt_pin,
        expected_reread_pin_control_pin)
    state = _stage(campaign_root, control_root,
                   allow_completion=True, **inputs)
    expected_raw, expected_pin, reread_raw, journal_state = _completed_raw(
        state, expected_generation_receipt_pin, expected_reread_receipt_pin)
    v.require(expected_pin == expected_completed_record_pin,
              'externally pinned completion record differs')
    campaign = Path(state['campaign_root'])
    controls = Path(state['control_root'])
    actual_raw = store._pinned(campaign / 'journal' / RECORD_NAME,
                                expected_completed_record_pin,
                                metadata.MAX_RECORD_BYTES)
    v.require(actual_raw == expected_raw,
              'saved completion record differs from owned receipts')
    checkpoint_raw = store._pinned(
        controls / CHECKPOINT_NAME, expected_terminal_checkpoint_pin,
        MAX_CHECKPOINT)
    checkpoint = v.strict_json(checkpoint_raw)
    v.require(checkpoint_raw == store._lf(_checkpoint(
        expected_plan_pin, expected_next_checkpoint_pin,
        expected_generation_receipt_pin, expected_reread_receipt_pin,
        expected_run_pin_control_pin, expected_reread_pin_control_pin,
        expected_completed_record_pin), MAX_CHECKPOINT),
        'external terminal checkpoint changed')
    v.require(journal_state['head_sha256'] == checkpoint['head_sha256'] and
              journal_state['record_count'] == checkpoint['record_count'] == 2,
              'terminal journal/checkpoint count or head differs')
    # Recheck the entire terminal layout after receipt derivation, including
    # pending traces and unexpected owner/intention files.
    from . import anomaly_v03_preformal_campaign_reread_intent_store as stage
    stage._inventory(campaign, controls, has_request=True,
                     after_reread=True, allow_completion=True)
    plan = v.strict_json(state['plan_raw'])
    started = v.strict_json(state['record_raws'][0])
    generation_path = (controller._control(plan, started, 'run-budget') /
                       'receipt.json')
    reread_path = (controller._control(plan, started, 'saved-reread') /
                   'receipt.json')
    v.require(store._read(campaign / 'journal' / RECORD_NAME,
                           metadata.MAX_RECORD_BYTES) == actual_raw and
              store._read(controls / CHECKPOINT_NAME,
                          MAX_CHECKPOINT) == checkpoint_raw and
              metadata.pin(store._read(generation_path,
                                       controller.MAX_RECEIPT)) ==
              expected_generation_receipt_pin and
              store._pinned(reread_path, expected_reread_receipt_pin,
                            controller.MAX_RECEIPT) == reread_raw,
              'terminal record/checkpoint/receipt changed during inspection')
    return {
        'status': journal_state['status'],
        'campaign_root': str(campaign), 'control_root': str(controls),
        'plan_pin': copy.deepcopy(expected_plan_pin),
        'started_record_pin': copy.deepcopy(expected_started_record_pin),
        'completed_record_pin': copy.deepcopy(expected_completed_record_pin),
        'terminal_checkpoint_pin': copy.deepcopy(expected_terminal_checkpoint_pin),
        'checkpoint': checkpoint,
        'generation_receipt_pin': copy.deepcopy(expected_generation_receipt_pin),
        'reread_receipt_pin': copy.deepcopy(expected_reread_receipt_pin),
        'reread_receipt_raw': reread_raw,
        'record_raws': [*state['record_raws'], actual_raw],
        'declared_completed_chunks': 1,
        'declared_completed_evaluations': 6,
        'missing_chunk_indices': list(range(1, 480)),
        'invented_only': True,
        'actual_registered_observations_read': False,
        'campaign_coherence_authenticated': False,
        'producer_execution_authenticated': False,
        'launch_authorized': False, 'resume_authorized': False,
        'campaign_evaluations_credited': 0,
        'formal_permission': False,
    }
