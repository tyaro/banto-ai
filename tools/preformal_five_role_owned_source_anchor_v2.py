"""Run or recheck seven owned pre-Job Git calls around an invented five-role Job."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from banto_ai import anomaly_v03_preformal_five_role_owned_source_anchor_v2 as anchor  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    run = commands.add_parser('run')
    run.add_argument('--join-root', type=Path, required=True)
    run.add_argument('--join-receipt-bytes', type=int, required=True)
    run.add_argument('--join-receipt-sha256', required=True)
    run.add_argument('--revision', required=True)
    run.add_argument('--git-policy-path', type=Path, required=True)
    run.add_argument('--git-policy-bytes', type=int, required=True)
    run.add_argument('--git-policy-sha256', required=True)
    run.add_argument('--receipt-parent', type=Path, required=True)
    run.add_argument('--receipt-name', required=True)
    run.add_argument('--candidate-set-path', type=Path)
    run.add_argument('--candidate-set-bytes', type=int)
    run.add_argument('--candidate-set-sha256')
    verify = commands.add_parser('verify')
    verify.add_argument('--result-root', type=Path, required=True)
    verify.add_argument('--receipt-bytes', type=int, required=True)
    verify.add_argument('--receipt-sha256', required=True)
    args = parser.parse_args(argv)
    if args.command == 'run':
        if (args.candidate_set_path is None) != \
                (args.candidate_set_bytes is None) or \
                (args.candidate_set_path is None) != \
                (args.candidate_set_sha256 is None):
            parser.error('candidate set path, bytes, sha256 must be supplied together')
        candidate_pin = (None if args.candidate_set_path is None else
                         {'bytes': args.candidate_set_bytes,
                          'sha256': args.candidate_set_sha256})
        result = anchor.run_anchored(
            expected_mode='fixture', join_root=args.join_root,
            expected_join_receipt_pin={
                'bytes': args.join_receipt_bytes,
                'sha256': args.join_receipt_sha256},
            expected_revision=args.revision,
            receipt_parent=args.receipt_parent,
            receipt_name=args.receipt_name,
            git_policy_path=args.git_policy_path,
            expected_git_policy_pin={
                'bytes': args.git_policy_bytes,
                'sha256': args.git_policy_sha256},
            candidate_set_path=args.candidate_set_path,
            expected_candidate_set_pin=candidate_pin)
        output = {'status': result['status'],
                  'reason': result['reason'],
                  'check_directory': result['check_directory'],
                  'receipt_pin': result['receipt_pin'],
                  'formal_permission': False}
        code = 0 if result['status'] == 'verified' else 2
    else:
        output = anchor.verify_retained(
            args.result_root,
            {'bytes': args.receipt_bytes,
             'sha256': args.receipt_sha256})
        code = 0
    print(json.dumps(output, sort_keys=True, separators=(',', ':')))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
