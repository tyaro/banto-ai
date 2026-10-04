"""Append or verify one invented saved-reread completion declaration.

The two owned CLI receipts and prior external controls must already exist.
This command never launches a child or opens registered observations.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from banto_ai import anomaly_v03_preformal_campaign_completion_store as store  # noqa: E402


def _pin(value):
    match = re.fullmatch(r'([1-9][0-9]*):([0-9a-f]{64})', value)
    if match is None:
        raise argparse.ArgumentTypeError('expected positive bytes:sha256')
    return {'bytes': int(match.group(1)), 'sha256': match.group(2)}


def _path(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _summary(result):
    return {
        'status': result['status'],
        'campaign_root': result['campaign_root'],
        'control_root': result['control_root'],
        'plan_pin': result['plan_pin'],
        'started_record_pin': result['started_record_pin'],
        'completed_record_pin': result['completed_record_pin'],
        'terminal_checkpoint_pin': result['terminal_checkpoint_pin'],
        'record_count': result['checkpoint']['record_count'],
        'head_sha256': result['checkpoint']['head_sha256'],
        'generation_receipt_pin': result['generation_receipt_pin'],
        'reread_receipt_pin': result['reread_receipt_pin'],
        'declared_completed_chunks': result['declared_completed_chunks'],
        'declared_completed_evaluations': result['declared_completed_evaluations'],
        'missing_chunk_count': len(result['missing_chunk_indices']),
        'invented_only': True,
        'actual_registered_observations_read': False,
        'campaign_coherence_authenticated': False,
        'launch_authorized': False, 'resume_authorized': False,
        'campaign_evaluations_credited': 0, 'formal_permission': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('append', 'verify'):
        item = sub.add_parser(name)
        item.add_argument('--campaign-root', type=_path, required=True)
        item.add_argument('--control-root', type=_path, required=True)
        for flag in (
            'plan', 'initial-checkpoint', 'intention', 'prepare-receipt',
            'started-record', 'next-checkpoint', 'run-pin-control',
            'generation-receipt', 'reread-pin-control', 'reread-receipt',
        ):
            item.add_argument('--' + flag + '-pin', type=_pin, required=True)
        if name == 'verify':
            item.add_argument('--completed-record-pin', type=_pin,
                              required=True)
            item.add_argument('--terminal-checkpoint-pin', type=_pin,
                              required=True)
    args = parser.parse_args()
    inputs = {
        'expected_plan_pin': args.plan_pin,
        'expected_initial_checkpoint_pin': args.initial_checkpoint_pin,
        'expected_intention_pin': args.intention_pin,
        'expected_prepare_receipt_pin': args.prepare_receipt_pin,
        'expected_started_record_pin': args.started_record_pin,
        'expected_next_checkpoint_pin': args.next_checkpoint_pin,
        'expected_run_pin_control_pin': args.run_pin_control_pin,
        'expected_generation_receipt_pin': args.generation_receipt_pin,
        'expected_reread_pin_control_pin': args.reread_pin_control_pin,
        'expected_reread_receipt_pin': args.reread_receipt_pin,
    }
    if args.command == 'append':
        result = store.append_completed(args.campaign_root,
                                        args.control_root, **inputs)
    else:
        result = store.verify_completed(
            args.campaign_root, args.control_root,
            expected_completed_record_pin=args.completed_record_pin,
            expected_terminal_checkpoint_pin=args.terminal_checkpoint_pin,
            **inputs)
    print(json.dumps(_summary(result), sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
