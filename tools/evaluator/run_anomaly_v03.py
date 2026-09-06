"""Checkout entrypoint. S3 inspection is metadata-only; run awaits S4 acceptance."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/"src"))

from banto_ai.anomaly_v03_runner import main

if __name__ == "__main__":
    raise SystemExit(main())
