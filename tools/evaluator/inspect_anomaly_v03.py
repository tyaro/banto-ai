"""S4-A stdout-only inspection. No run, output, install or acceptance flags."""

from pathlib import Path
import sys

# Set before importing project modules: inspection must not create bytecode.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).absolute().parents[2]/"src"))

from banto_ai import anomaly_v03 as v
from banto_ai._anomaly_v03_inventory import collect_receipt


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).absolute().parents[2])
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args(argv)
    try:
        result = collect_receipt(args.root, args.expected_head)
    except (Exception, KeyboardInterrupt):
        # Do not echo paths, environment, native errors or arbitrary exception text.
        print('{"acceptance_status":"not_completed","inspection_status":"failed","formal_permission":false}', file=sys.stderr)
        return 1
    print(v.canonical_json(result).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
