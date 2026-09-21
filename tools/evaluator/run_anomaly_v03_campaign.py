"""Explicit preparation and chunk-count-bounded engineering continuation."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from banto_ai.anomaly_v03_campaign_launcher import main

if __name__ == "__main__":
    raise SystemExit(main())
