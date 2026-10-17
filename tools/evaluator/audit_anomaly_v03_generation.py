"""Verify frozen generation of one explicitly selected saved dev/smoke pair."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from banto_ai.anomaly_v03_generation_io import main

if __name__ == '__main__':
    raise SystemExit(main())
