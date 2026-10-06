"""Run one pinned historical writer timing trial, never generation or draws."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from banto_ai import anomaly_v03_saved_writer_profile as profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', required=True)
    parser.add_argument('--request-bytes', required=True, type=int)
    parser.add_argument('--request-sha256', required=True)
    parser.add_argument('--worker-revision', required=True)
    parser.add_argument('--receipt-name', required=True)
    args = parser.parse_args()
    result = profile.run(source_root=args.source_root,
        expected_request_pin={'bytes': args.request_bytes, 'sha256': args.request_sha256},
        expected_worker_revision=args.worker_revision, receipt_name=args.receipt_name)
    print(json.dumps({key: result[key] for key in ('status', 'reason', 'result_pin',
        'numerical_source_revision', 'worker_source_revision', 'worker_exit_confirmed',
        'formal_permission', 'full_end_to_end_budget_measured')}, sort_keys=True), flush=True)
    return 0 if result['status'] == 'verified' else 2


if __name__ == '__main__':
    raise SystemExit(main())
