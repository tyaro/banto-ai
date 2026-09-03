"""clean checkoutからsynthetic datasetの品質検査を起動する薄いentrypoint。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from banto_ai.cli import main  # noqa: E402

raise SystemExit(main(["check-quality", "--root", str(ROOT), *sys.argv[1:]]))
