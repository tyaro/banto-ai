"""Own one pinned invented slot-0 run-budget CLI; print its saved receipt pin."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from banto_ai import anomaly_v03_preformal_campaign_run_budget_owner as owner  # noqa: E402


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
    parser.add_argument('--campaign-root', type=_path, required=True)
    parser.add_argument('--control-root', type=_path, required=True)
    parser.add_argument('--plan-pin', type=_pin, required=True)
    parser.add_argument('--initial-checkpoint-pin', type=_pin, required=True)
    parser.add_argument('--intention-pin', type=_pin, required=True)
    parser.add_argument('--prepare-receipt-pin', type=_pin, required=True)
    parser.add_argument('--started-record-pin', type=_pin, required=True)
    parser.add_argument('--next-checkpoint-pin', type=_pin, required=True)
    parser.add_argument('--pin-control-pin', type=_pin, required=True)
    args = parser.parse_args()
    receipt, receipt_pin = owner.execute_run_budget(
        args.campaign_root, args.control_root,
        expected_plan_pin=args.plan_pin,
        expected_initial_checkpoint_pin=args.initial_checkpoint_pin,
        expected_intention_pin=args.intention_pin,
        expected_prepare_receipt_pin=args.prepare_receipt_pin,
        expected_started_record_pin=args.started_record_pin,
        expected_next_checkpoint_pin=args.next_checkpoint_pin,
        expected_pin_control_pin=args.pin_control_pin)
    print(json.dumps({
        'status': receipt['status'],
        'reason': receipt.get('reason'),
        'receipt_pin': receipt_pin,
        'request_pin': receipt['request_pin'],
        'journal_count': receipt['journal_count'],
        'journal_head_sha256': receipt['journal_head_sha256'],
        'campaign_coherence_authenticated': False,
        'campaign_evaluations_credited': 0,
        'formal_permission': False,
    }, sort_keys=True))
    return 0 if receipt['status'] == 'verified' else 2


if __name__ == '__main__':
    raise SystemExit(main())
