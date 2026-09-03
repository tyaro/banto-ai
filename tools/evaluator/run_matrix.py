"""baseline benchmark matrixのentrypoint。"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from banto_ai.matrix import MatrixError, run_matrix  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run_matrix.py")
    parser.add_argument("--config", required=True)
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    config = Path(args.config).expanduser()
    if not config.is_absolute():
        config = (root / config).resolve()
    try:
        output = run_matrix(config, root)
    except (MatrixError, KeyError, OSError, TypeError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"benchmark matrix: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
