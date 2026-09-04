"""Toto 2.0 controlled 4-track acceptance analyzer entrypoint."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from banto_ai.toto2_acceptance import AcceptanceError, analyze_controlled_acceptance  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="analyze_controlled_acceptance.py", description="Toto 2.0 controlled 4-track acceptance analyzer")
    parser.add_argument("--config", required=True, help="analyzer config (repository-relative or absolute local path)")
    parser.add_argument("--root", default=str(ROOT), help="repository root")
    parser.add_argument("--recover-incomplete", action="store_true", help="quarantine an incomplete existing output before rerunning")
    args = parser.parse_args(argv)
    try:
        output = analyze_controlled_acceptance(args.config, Path(args.root), recover_incomplete=args.recover_incomplete)
    except (AcceptanceError, OSError, TypeError, ValueError, KeyError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"Toto 2.0 controlled acceptance: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
