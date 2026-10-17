"""Read-only independent ledger checks; does not run or modify a campaign."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from banto_ai.anomaly_v03_saved_audit import main

if __name__ == "__main__":
    raise SystemExit(main())
