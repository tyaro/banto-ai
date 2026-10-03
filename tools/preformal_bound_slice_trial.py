"""Connect one retained invented 50,000-draw document to pinned slice counts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from banto_ai import anomaly_v03_preformal_bound_slice_bridge as mapping  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--document-root', required=True, type=Path)
    parser.add_argument('--document-result-bytes', required=True, type=int)
    parser.add_argument('--document-result-sha256', required=True)
    parser.add_argument('--slice-source-bytes', required=True, type=int)
    parser.add_argument('--slice-source-sha256', required=True)
    parser.add_argument('--trial-name', required=True)
    parser.add_argument('--revision', default=None)
    args = parser.parse_args(argv)
    revision = args.revision or subprocess.check_output(
        ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], stderr=subprocess.DEVNULL,
        timeout=10).decode().strip()
    result = mapping.run_saved_slices(
        document_root=args.document_root,
        expected_document_result_pin={'bytes': args.document_result_bytes,
                                      'sha256': args.document_result_sha256},
        expected_slice_source_pin={'bytes': args.slice_source_bytes,
                                   'sha256': args.slice_source_sha256},
        expected_revision=revision,
        trial_name=args.trial_name)
    print(json.dumps({'status': result['status'], 'receipt_root': result['receipt_root'],
                      'result_pin': result['result_pin'], 'slices_pin': result['slices_pin'],
                      'audit_pin': result['audit_pin'], 'formal_permission': False},
                     sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
