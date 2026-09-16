"""Single-writer development evaluation; original formal runner stays closed."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from banto_ai.anomaly_v03_engineering import main

if __name__ == "__main__":
    raise SystemExit(main())
