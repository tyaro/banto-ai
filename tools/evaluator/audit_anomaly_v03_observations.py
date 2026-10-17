"""Read-only connected audit of one explicitly selected saved dev/smoke chunk."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from banto_ai.anomaly_v03_observation_audit import main

if __name__ == '__main__':
    raise SystemExit(main())
