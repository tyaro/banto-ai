"""S4-A stdout-only inspection. No run, output, install or acceptance flags."""

from pathlib import Path
import sys

# Set before importing project modules: inspection must not create bytecode.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).absolute().parents[2]/"src"))

import argparse

from banto_ai import anomaly_v03 as v
from banto_ai._anomaly_v03_inventory import collect_receipt


class _RedactedArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's message can contain arbitrary option names and values.
        # Never print it, attach it to the exception, or emit usage on failure.
        raise ValueError("invalid inspection arguments")


def _full_revision(value):
    if len(value) != 40 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError("full revision required")
    return value


def main(argv=None):
    try:
        parser = _RedactedArgumentParser(description=__doc__, allow_abbrev=False)
        parser.add_argument("--root", type=Path, default=Path(__file__).absolute().parents[2])
        parser.add_argument("--expected-head", required=True, type=_full_revision)
        args = parser.parse_args(argv)
        result = collect_receipt(args.root, args.expected_head)
    except (Exception, KeyboardInterrupt):
        # Do not echo paths, environment, native errors or arbitrary exception text.
        print('{"acceptance_status":"not_completed","inspection_status":"failed","formal_permission":false}', file=sys.stderr)
        return 1
    print(v.canonical_json(result).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
