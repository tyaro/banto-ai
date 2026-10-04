"""Own fixed invented campaign prepare after a separately pinned store exists.

Example::

    python -B tools/preformal_campaign_prepare_owner.py \
      --campaign-root artifacts/anomaly-v03-preformal-campaign-12345678 \
      --control-root artifacts/anomaly-v03-preformal-campaign-control-12345678 \
      --plan-pin BYTES:SHA256 --checkpoint-pin BYTES:SHA256 \
      --intention-pin BYTES:SHA256

Only the direct prepare CLI is owned. A failed result stops the next stage.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from banto_ai import anomaly_v03_preformal_campaign_prepare_owner as owner  # noqa: E402


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
    parser.add_argument('--campaign-root', required=True)
    parser.add_argument('--control-root', required=True)
    parser.add_argument('--plan-pin', type=_pin, required=True)
    parser.add_argument('--checkpoint-pin', type=_pin, required=True)
    parser.add_argument('--intention-pin', type=_pin, required=True)
    args = parser.parse_args()
    value, receipt_pin = owner.execute(
        _path(args.campaign_root), _path(args.control_root),
        expected_plan_pin=args.plan_pin,
        expected_checkpoint_pin=args.checkpoint_pin,
        expected_intention_pin=args.intention_pin)
    print(json.dumps({'status': value['status'], 'reason': value['reason'],
                      'owner_root': value['owner_root'],
                      'receipt_pin': receipt_pin,
                      'next_stage_authorized': False,
                      'formal_permission': False}, sort_keys=True))
    return 0 if value['status'] == 'prepared' else 2


if __name__ == '__main__':
    raise SystemExit(main())
