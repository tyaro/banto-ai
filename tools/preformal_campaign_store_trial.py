"""Freeze or verify one invented campaign metadata boundary.

``create`` saves only metadata and the slot-0 prepare intention.  It does not
invoke prepare, consume registered observations, or authorize a formal run.
Retain the printed raw pins outside both roots for later read-only checks.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import secrets
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from banto_ai import anomaly_v03_preformal_campaign_store as store  # noqa: E402


def _pin_arg(value):
    match = re.fullmatch(r'([1-9][0-9]*):([0-9a-f]{64})', value)
    if match is None:
        raise argparse.ArgumentTypeError('expected positive bytes:sha256')
    return {'bytes': int(match.group(1)), 'sha256': match.group(2)}


def _root_arg(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _summary(result):
    return {
        'status': result['status'],
        'campaign_root': result['campaign_root'],
        'control_root': result['control_root'],
        'plan_pin': result['plan_pin'],
        'checkpoint_pin': result['checkpoint_pin'],
        'intention_pin': result['intention_pin'],
        'record_count': result['checkpoint']['record_count'],
        'head_sha256': result['checkpoint']['head_sha256'],
        'chunk_index': result['intention']['chunk_index'],
        'attempt': result['intention']['attempt'],
        'expected_absent_paths': result['intention']['expected_absent_paths'],
        'invented_only': True,
        'actual_registered_observations_read': False,
        'campaign_coherence_authenticated': False,
        'launch_authorized': False,
        'resume_authorized': False,
        'formal_permission': False,
        'campaign_evaluations_credited': 0,
    }


def _started_summary(result):
    return {
        'status': result['status'],
        'campaign_root': result['campaign_root'],
        'control_root': result['control_root'],
        'plan_pin': result['plan_pin'],
        'initial_checkpoint_pin': result['initial_checkpoint_pin'],
        'intention_pin': result['intention_pin'],
        'prepare_receipt_pin': result['prepare_receipt_pin'],
        'manifest_pin': result['manifest_pin'],
        'started_record_pin': result['started_record_pin'],
        'next_checkpoint_pin': result['next_checkpoint_pin'],
        'record_count': result['checkpoint']['record_count'],
        'head_sha256': result['checkpoint']['head_sha256'],
        'run_intent_pin': result['run_intent_pin'],
        'invented_only': True,
        'actual_registered_observations_read': False,
        'campaign_coherence_authenticated': False,
        'launch_authorized': False,
        'resume_authorized': False,
        'formal_permission': False,
        'campaign_evaluations_credited': 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    create = sub.add_parser('create')
    create.add_argument('--path-code', required=True,
                        help='one lowercase letter for short attempt roots')
    create.add_argument('--campaign-id',
                        help='optional 64 lowercase hex ID; default is fresh random')
    verify = sub.add_parser('verify')
    verify.add_argument('--campaign-root', type=_root_arg, required=True)
    verify.add_argument('--control-root', type=_root_arg, required=True)
    verify.add_argument('--plan-pin', type=_pin_arg, required=True)
    verify.add_argument('--checkpoint-pin', type=_pin_arg, required=True)
    verify.add_argument('--intention-pin', type=_pin_arg, required=True)
    started = sub.add_parser('append-started')
    started.add_argument('--campaign-root', type=_root_arg, required=True)
    started.add_argument('--control-root', type=_root_arg, required=True)
    started.add_argument('--plan-pin', type=_pin_arg, required=True)
    started.add_argument('--initial-checkpoint-pin', type=_pin_arg,
                         required=True)
    started.add_argument('--intention-pin', type=_pin_arg, required=True)
    started.add_argument('--prepare-receipt-pin', type=_pin_arg,
                         required=True)
    inspect = sub.add_parser('verify-started')
    inspect.add_argument('--campaign-root', type=_root_arg, required=True)
    inspect.add_argument('--control-root', type=_root_arg, required=True)
    inspect.add_argument('--plan-pin', type=_pin_arg, required=True)
    inspect.add_argument('--initial-checkpoint-pin', type=_pin_arg,
                         required=True)
    inspect.add_argument('--intention-pin', type=_pin_arg, required=True)
    inspect.add_argument('--prepare-receipt-pin', type=_pin_arg,
                         required=True)
    inspect.add_argument('--started-record-pin', type=_pin_arg, required=True)
    inspect.add_argument('--next-checkpoint-pin', type=_pin_arg, required=True)
    inspect.add_argument('--run-intent-pin', type=_pin_arg)
    args = parser.parse_args()
    if args.command == 'create':
        campaign_id = args.campaign_id or secrets.token_hex(32)
        plan = store.capture_current_plan(campaign_id, args.path_code)
        control_root = ROOT / 'artifacts' / (
            'anomaly-v03-preformal-campaign-control-' + campaign_id[:8])
        result = store.create_store(plan, control_root, sys.executable)
        print(json.dumps(_summary(result), sort_keys=True))
        return 0
    if args.command == 'verify':
        result = store.verify_store(
            args.campaign_root, args.control_root,
            expected_plan_pin=args.plan_pin,
            expected_checkpoint_pin=args.checkpoint_pin,
            expected_intention_pin=args.intention_pin)
        print(json.dumps(_summary(result), sort_keys=True))
        return 0
    shared = {
        'expected_plan_pin': args.plan_pin,
        'expected_initial_checkpoint_pin': args.initial_checkpoint_pin,
        'expected_intention_pin': args.intention_pin,
        'expected_prepare_receipt_pin': args.prepare_receipt_pin,
    }
    if args.command == 'append-started':
        result = store.append_started(args.campaign_root, args.control_root,
                                      **shared)
    else:
        result = store.verify_started_store(
            args.campaign_root, args.control_root,
            expected_started_record_pin=args.started_record_pin,
            expected_next_checkpoint_pin=args.next_checkpoint_pin,
            expected_run_intent_pin=args.run_intent_pin, **shared)
    print(json.dumps(_started_summary(result), sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
