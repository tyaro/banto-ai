"""Read-only ledger audit of one externally selected registered dev/smoke chunk."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from banto_ai.anomaly_v03_chunk_audit import main

if __name__ == "__main__":
    raise SystemExit(main())
