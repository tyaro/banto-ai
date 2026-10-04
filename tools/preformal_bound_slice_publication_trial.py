"""Publish one retained invented slice draft after pinned postcheck verification."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from banto_ai import anomaly_v03_preformal_bound_slice_publication as publication  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--slice-root', required=True, type=Path)
    parser.add_argument('--slice-result-bytes', required=True, type=int)
    parser.add_argument('--slice-result-sha256', required=True)
    parser.add_argument('--postcheck-root', required=True, type=Path)
    parser.add_argument('--postcheck-bytes', required=True, type=int)
    parser.add_argument('--postcheck-sha256', required=True)
    parser.add_argument('--trial-name', required=True)
    parser.add_argument('--revision', default=None)
    args = parser.parse_args(argv)
    revision = args.revision or subprocess.check_output(
        ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'],
        stderr=subprocess.DEVNULL, timeout=10).decode().strip()
    result = publication.run_saved_publication(
        slice_root=args.slice_root,
        expected_slice_result_pin={'bytes': args.slice_result_bytes,
                                   'sha256': args.slice_result_sha256},
        postcheck_root=args.postcheck_root,
        expected_postcheck_pin={'bytes': args.postcheck_bytes,
                                'sha256': args.postcheck_sha256},
        expected_revision=revision,
        trial_name=args.trial_name)
    print(json.dumps({'status': result['status'],
                      'receipt_root': result['receipt_root'],
                      'result_pin': result['result_pin'],
                      'source_payload_pins': result['source_payload_pins'],
                      'payload_pins': result['payload_pins'],
                      'marker_raw_sha256': result.get('marker_raw_sha256'),
                      'resource_budget_passed': result['resource_budget_passed'],
                      'formal_permission': False}, sort_keys=True))
    return 0 if result['status'] == 'verified' else 2


if __name__ == '__main__':
    raise SystemExit(main())
