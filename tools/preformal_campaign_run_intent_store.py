"""Create or verify a pinned invented run-budget request; never launch it."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from banto_ai import anomaly_v03_preformal_campaign_run_intent_store as store  # noqa: E402


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
    for command in ('create', 'verify'):
        item = sub.add_parser(command)
        item.add_argument('--campaign-root', type=_path, required=True)
        item.add_argument('--control-root', type=_path, required=True)
        item.add_argument('--plan-pin', type=_pin, required=True)
        item.add_argument('--initial-checkpoint-pin', type=_pin, required=True)
        item.add_argument('--intention-pin', type=_pin, required=True)
        item.add_argument('--prepare-receipt-pin', type=_pin, required=True)
        item.add_argument('--started-record-pin', type=_pin, required=True)
        item.add_argument('--next-checkpoint-pin', type=_pin, required=True)
        if command == 'verify':
            item.add_argument('--pin-control-pin', type=_pin, required=True)
    args = parser.parse_args()
    inputs = dict(
        expected_plan_pin=args.plan_pin,
        expected_initial_checkpoint_pin=args.initial_checkpoint_pin,
        expected_intention_pin=args.intention_pin,
        expected_prepare_receipt_pin=args.prepare_receipt_pin,
        expected_started_record_pin=args.started_record_pin,
        expected_next_checkpoint_pin=args.next_checkpoint_pin)
    value = (store.create_request(args.campaign_root, args.control_root,
                                  **inputs) if args.command == 'create'
             else store.verify_request(
                 args.campaign_root, args.control_root,
                 expected_pin_control_pin=args.pin_control_pin, **inputs))
    print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
