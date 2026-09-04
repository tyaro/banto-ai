"""Event-aware anomaly evaluation v0.1 entrypoint."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from banto_ai.anomaly_evaluation import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
