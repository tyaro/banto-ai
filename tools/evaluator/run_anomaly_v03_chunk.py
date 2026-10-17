"""Run one new six-evaluation connection trial from a pinned clean checkout."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from banto_ai.anomaly_v03_chunk_execution import main

if __name__ == "__main__":
    raise SystemExit(main())
