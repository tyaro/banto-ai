"""Run a bounded invented saved-reader reread and six-row projection.

The source is an existing invented registered-format g02 root. Its saved
payload bytes are external inputs to this trial's new output-root budget.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from banto_ai import anomaly_v03_preformal_saved_row_reread as reread  # noqa: E402


def _pin(value: str) -> dict:
    match = re.fullmatch(r'([1-9][0-9]*):([0-9a-f]{64})', value)
    if match is None:
        raise argparse.ArgumentTypeError('expected bytes:sha256')
    return {'bytes': int(match.group(1)), 'sha256': match.group(2)}


def _path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', required=True)
    parser.add_argument('--output-root', required=True)
    parser.add_argument('--manifest-pin', type=_pin, required=True)
    parser.add_argument('--outer-result-pin', type=_pin, required=True)
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    if re.fullmatch(r'[0-9a-f]{40}', args.revision) is None:
        parser.error('full clean source revision required')
    result = reread.run_reread(
        _path(args.source_root), _path(args.output_root),
        expected_manifest_pin=args.manifest_pin,
        expected_outer_result_pin=args.outer_result_pin,
        expected_revision=args.revision)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result['status'] == 'verified' else 2


if __name__ == '__main__':
    raise SystemExit(main())
