"""Check a closed diagnostic record without executing or replaying its work."""
import argparse
import json
from pathlib import Path

from verification_records import verify_record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args(argv)
    try:
        record = verify_record(args.root)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"record_integrity": "failed", "type": type(error).__name__, "message": str(error)}))
        return 1
    print(json.dumps({"record_integrity": "passed", "recorded_status": record["status"],
                      "operations": {k: v["status"] for k, v in record["operations"].items()},
                      "formal_permission": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
