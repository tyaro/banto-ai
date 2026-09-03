"""clean checkoutから実行するPhase 0 smoke test。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from banto_ai.cli import main  # noqa: E402

raise SystemExit(main(["smoke", "--root", str(ROOT)]))
