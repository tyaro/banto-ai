"""clean checkoutから実行するrepository safety guard。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from banto_ai.cli import main  # noqa: E402

raise SystemExit(main(["safety", "--root", str(ROOT)]))
