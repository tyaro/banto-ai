"""clean checkoutから実行できるbenchmark entrypoint。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from banto_ai.benchmark import BenchmarkError, run_benchmark  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run_benchmark.py")
    parser.add_argument("--config", required=True)
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    config = Path(args.config)
    if not config.is_absolute():
        config = (root / config).resolve()
    try:
        output = run_benchmark(config, root)
    except (BenchmarkError, ValueError, OSError, KeyError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"benchmark: PASS ({output})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
