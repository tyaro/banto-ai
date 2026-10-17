"""Read-only recheck of a pinned invented slot wall envelope and completion.

This verifies retained bytes and the limited completed chain.  It does not
authenticate a formal full-pipeline budget or permit a registered run.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from banto_ai import anomaly_v03_preformal_campaign_wall_envelope as wall  # noqa: E402


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
    parser.add_argument('--receipt-pin', type=_pin, required=True)
    args = parser.parse_args()
    result = wall.verify_completed(
        args.campaign_root, args.control_root,
        expected_receipt_pin=args.receipt_pin)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
