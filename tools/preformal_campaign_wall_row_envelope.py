"""Run or verify an opt-in invented slot-0 wall plus six saved-row bridge.

This is one cooperative wall and one partial chunk.  No formal permission,
registered observation, 40-seed aggregate, or full resource claim is made.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from banto_ai import anomaly_v03_preformal_campaign_wall_row_envelope as envelope  # noqa: E402


def _pin(value):
    match = re.fullmatch(r'([1-9][0-9]*):([0-9a-f]{64})', value)
    if match is None:
        raise argparse.ArgumentTypeError('expected bytes:sha256')
    return {'bytes': int(match.group(1)), 'sha256': match.group(2)}


def _seconds(value):
    try:
        number = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError('expected finite positive seconds') from error
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError('expected finite positive seconds')
    return number


def _path(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('run', 'verify'):
        part = sub.add_parser(name)
        part.add_argument('--campaign-root', type=_path, required=True)
        part.add_argument('--control-root', type=_path, required=True)
        if name == 'run':
            part.add_argument('--plan-pin', type=_pin, required=True)
            part.add_argument('--initial-checkpoint-pin', type=_pin,
                              required=True)
            part.add_argument('--intention-pin', type=_pin, required=True)
            part.add_argument('--wall-seconds', type=_seconds, required=True)
        else:
            part.add_argument('--receipt-pin', type=_pin, required=True)
    args = parser.parse_args()
    if args.command == 'run':
        value, pin = envelope.execute(
            args.campaign_root, args.control_root,
            expected_plan_pin=args.plan_pin,
            expected_initial_checkpoint_pin=args.initial_checkpoint_pin,
            expected_intention_pin=args.intention_pin,
            wall_seconds=args.wall_seconds)
        print(json.dumps({
            'status': value['status'], 'reason': value['reason'],
            'last_stage': value['last_stage'],
            'elapsed_seconds': value['elapsed_seconds'],
            'receipt_pin': pin,
            'bridge_result_pin': value['bridge_result_pin'],
            'verified_evaluations': 6 if value['status'] == 'verified' else 0,
            'full_end_to_end_budget_measured': False,
            'formal_permission': False,
        }, sort_keys=True))
        return 0 if value['status'] == 'verified' else 2
    value = envelope.verify_retained(
        args.campaign_root, args.control_root,
        expected_receipt_pin=args.receipt_pin)
    print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
