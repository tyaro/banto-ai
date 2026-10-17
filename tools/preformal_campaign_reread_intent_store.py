"""Pin, verify, or own the invented slot-0 saved-row reread request."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from banto_ai import anomaly_v03_preformal_campaign_reread_intent_store as store  # noqa: E402


def _pin(value):
    match = re.fullmatch(r'([1-9][0-9]*):([0-9a-f]{64})', value)
    if match is None:
        raise argparse.ArgumentTypeError('expected bytes:sha256')
    return {'bytes': int(match.group(1)), 'sha256': match.group(2)}


def _path(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('create', 'verify', 'execute', 'verify-postrun'):
        item = sub.add_parser(command)
        item.add_argument('--campaign-root', type=_path, required=True)
        item.add_argument('--control-root', type=_path, required=True)
        item.add_argument('--plan-pin', type=_pin, required=True)
        item.add_argument('--initial-checkpoint-pin', type=_pin, required=True)
        item.add_argument('--intention-pin', type=_pin, required=True)
        item.add_argument('--prepare-receipt-pin', type=_pin, required=True)
        item.add_argument('--started-record-pin', type=_pin, required=True)
        item.add_argument('--next-checkpoint-pin', type=_pin, required=True)
        item.add_argument('--run-pin-control-pin', type=_pin, required=True)
        item.add_argument('--generation-receipt-pin', type=_pin, required=True)
        if command != 'create':
            item.add_argument('--pin-control-pin', type=_pin, required=True)
        if command == 'verify-postrun':
            item.add_argument('--allow-completion', action='store_true')
    args = parser.parse_args()
    inputs = dict(
        expected_plan_pin=args.plan_pin,
        expected_initial_checkpoint_pin=args.initial_checkpoint_pin,
        expected_intention_pin=args.intention_pin,
        expected_prepare_receipt_pin=args.prepare_receipt_pin,
        expected_started_record_pin=args.started_record_pin,
        expected_next_checkpoint_pin=args.next_checkpoint_pin,
        expected_run_pin_control_pin=args.run_pin_control_pin,
        expected_generation_receipt_pin=args.generation_receipt_pin)
    if args.command == 'create':
        result = store.create_request(args.campaign_root, args.control_root,
                                      **inputs)
    elif args.command == 'verify':
        result = store.verify_request(
            args.campaign_root, args.control_root,
            expected_pin_control_pin=args.pin_control_pin, **inputs)
    elif args.command == 'execute':
        receipt, receipt_pin = store.execute_request(
            args.campaign_root, args.control_root,
            expected_pin_control_pin=args.pin_control_pin, **inputs)
        result = {'status': receipt['status'], 'phase': receipt['phase'],
                  'receipt_pin': receipt_pin,
                  'formal_permission': receipt['formal_permission'],
                  'campaign_evaluations_credited':
                      receipt['campaign_evaluations_credited']}
    else:
        state = store.verify_postrun_stage(
            args.campaign_root, args.control_root,
            expected_pin_control_pin=args.pin_control_pin,
            allow_completion=args.allow_completion, **inputs)
        result = {
            'status': state['status'],
            'campaign_root': state['campaign_root'],
            'control_root': state['control_root'],
            'request_pin': state['request_pin'],
            'generation_receipt_pin': state['generation_receipt_pin'],
            'journal_head_sha256': state['checkpoint']['head_sha256'],
            'formal_permission': state['formal_permission'],
            'campaign_evaluations_credited':
                state['campaign_evaluations_credited'],
        }
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] != 'failed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
