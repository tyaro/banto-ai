"""MetroPT-3 public source pinning entrypoint."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from banto_ai.public_source import main  # noqa: E402


raise SystemExit(main())
