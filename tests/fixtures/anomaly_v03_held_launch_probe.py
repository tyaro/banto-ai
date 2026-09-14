"""Opt-in dedicated worker. Run only via the pinned external supervisor."""
import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from tests.fixtures.anomaly_v03_held_launch import launch

BASE = ROOT / "artifacts/held-launch-2026-09-14"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--input-sha256", required=True)
    parser.add_argument("--attempt", type=int, choices=(1,), required=True)
    args = parser.parse_args()
    return launch(ROOT, BASE, args.expected_head, args.input_sha256, os.write)


if __name__ == "__main__":
    raise SystemExit(main())
