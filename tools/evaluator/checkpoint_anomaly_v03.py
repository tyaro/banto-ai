"""Emit/inspect campaign metadata only; never creates campaign output or starts work."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_checkpoints as checkpoints
from banto_ai import _anomaly_v03_runtime as rt
from banto_ai import _anomaly_v03_io as storage

MAX_PLAN_BYTES = 1024**2
MAX_RECORD_BYTES = 16 * 1024
MAX_JOURNAL_BYTES = 16 * 1024**2


def _read(path, maximum):
    path = rt.regular_path(path)
    v.require(path.stat().st_size <= maximum, "metadata file too large")
    raw = storage.read_regular(path)
    v.require(len(raw) <= maximum, "metadata file grew beyond limit")
    return raw


def inspect(plan_path, journal_dir, plan_hash, count, head_hash):
    v.require(type(count) is int and 0 <= count <= checkpoints.MAX_RECORDS, "journal record count limit")
    plan_raw = _read(plan_path, MAX_PLAN_BYTES)
    plan = v.strict_json(plan_raw)
    journal_dir = rt.regular_path(journal_dir, directory=True)
    expected = [f"{number:06d}.json" for number in range(1, count + 1)]
    v.require(sorted(p.name for p in journal_dir.iterdir()) == expected, "journal file inventory differs")
    records, pins, total = [], [], 0
    for name in expected:
        path = journal_dir / name
        raw = _read(path, MAX_RECORD_BYTES)
        total += len(raw)
        v.require(total <= MAX_JOURNAL_BYTES, "journal byte limit")
        record = v.strict_json(raw)
        v.require(raw == checkpoints.encode_record(record), "noncanonical or incomplete journal record")
        records.append(record)
        pins.append((path, hashlib.sha256(raw).digest()))
    report = checkpoints.reduce_journal(plan, records, expected_plan_sha256=plan_hash,
        expected_record_count=count, expected_head_sha256=head_hash)
    v.require(_read(plan_path, MAX_PLAN_BYTES) == plan_raw, "plan changed during inspection")
    v.require(sorted(p.name for p in journal_dir.iterdir()) == expected, "journal changed during inspection")
    for path, digest in pins:
        v.require(hashlib.sha256(_read(path, MAX_RECORD_BYTES)).digest() == digest, "journal changed during inspection")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan", help="Print the fixed metadata-only plan")
    plan.add_argument("--producer-revision", required=True)
    plan.add_argument("--consumer-revision", required=True)
    check = commands.add_parser("inspect", help="Read metadata; no saved payload verification or resume")
    check.add_argument("--plan", type=Path, required=True)
    check.add_argument("--plan-sha256", required=True, help="Externally retained canonical plan hash")
    check.add_argument("--journal-dir", type=Path, required=True)
    check.add_argument("--record-count", type=int, required=True)
    check.add_argument("--head-sha256", required=True, help="Externally retained last record raw hash, or empty plan hash")
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            report = checkpoints.fixed_plan(args.producer_revision, args.consumer_revision)
        else:
            report = inspect(args.plan, args.journal_dir, args.plan_sha256, args.record_count, args.head_sha256)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"status": "checkpoint_metadata_failed", "error_type": type(error).__name__,
                          "message": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
