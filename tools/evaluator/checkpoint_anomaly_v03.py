"""Inspect checkpoint metadata or verify historical preflight evidence; never resume."""
from pathlib import Path
import argparse
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_checkpoints as checkpoints
from banto_ai import anomaly_v03_checkpoint_store as store
from banto_ai import _anomaly_v03_runtime as rt
from banto_ai import _anomaly_v03_io as storage

load_journal = store.load_journal


def inspect(plan_path, journal_dir, plan_hash, count, head_hash):
    return load_journal(plan_path, journal_dir, plan_hash, count, head_hash)[2]


def preflight(args):
    from banto_ai import anomaly_v03_checkpoint_evidence as evidence
    from banto_ai import anomaly_v03_saved_audit as audit
    raw = audit._pin(args.reference, args.reference_sha256)
    reference = v.strict_json(raw)
    evidence.validate_reference(reference)
    pins = reference["journal"]
    inputs = (args.plan, args.journal_dir, pins["expected_plan_sha256"], pins["expected_record_count"], pins["expected_head_sha256"])
    plan, records, _ = load_journal(*inputs)
    result = evidence.verify_preflight(plan, records, reference, args.verifier_revision)
    # Re-read the journal/reference after the longer saved-ledger audit.
    load_journal(*inputs)
    rt.require(storage.read_regular(args.reference) == raw, "preflight reference changed during verification")
    result["reference_sha256"] = args.reference_sha256
    return result


def _pinned_json(path, digest, maximum, *, canonical=False):
    rt.require(type(digest) is str and len(digest) == 64, "external metadata file hash")
    raw = store.read_metadata(path, maximum)
    rt.require(storage.sha(raw) == digest, "external metadata file hash mismatch")
    value = v.strict_json(raw)
    if canonical:
        rt.require(raw == v.canonical_json(value) + b"\n", "record intent must be canonical JSON plus LF")
    return value


def write_metadata(args):
    if args.command == "store-init":
        plan = v.strict_json(store.read_metadata(args.plan, store.MAX_PLAN_BYTES))
        rt.require(v.canonical_sha256(plan) == args.plan_sha256, "external plan hash mismatch")
        return store.create_store(args.parent, args.name, plan)
    if args.command == "store-recover-init":
        return store.recover_initialization(args.root, args.plan_sha256)
    receipt = _pinned_json(args.receipt, args.receipt_sha256, 16 * 1024)
    if args.command == "store-inspect":
        return store.inspect_store(args.root, receipt)
    record = _pinned_json(args.record, args.record_sha256, store.MAX_RECORD_BYTES, canonical=True)
    if args.command == "store-append":
        return store.append_record(args.root, receipt, record)
    return store.recover_append(args.root, receipt, record)


def attempt_metadata(args):
    from banto_ai import anomaly_v03_attempt_descriptor as attempt
    pins = {"expected_plan_sha256": args.plan_sha256, "expected_record_count": args.record_count,
            "expected_head_sha256": args.head_sha256}
    inputs = (args.plan, args.journal_dir, args.plan_sha256, args.record_count, args.head_sha256)
    plan, records, _ = load_journal(*inputs)
    if args.command == "attempt-layout":
        return attempt.describe_layout(plan, records, **pins)
    descriptor = _pinned_json(args.descriptor, args.descriptor_sha256, 64 * 1024)
    report = attempt.validate_descriptor(descriptor, plan, records, **pins)
    load_journal(*inputs)
    _pinned_json(args.descriptor, args.descriptor_sha256, 64 * 1024)
    report["descriptor_raw_sha256"] = args.descriptor_sha256
    return report


def attempt_files(args):
    from banto_ai import anomaly_v03_attempt_files as attempt
    pins = {"expected_plan_sha256": args.plan_sha256, "expected_record_count": args.record_count,
            "expected_head_sha256": args.head_sha256}
    inputs = (args.plan, args.journal_dir, args.plan_sha256, args.record_count, args.head_sha256)
    plan, records, _ = load_journal(*inputs)
    if args.command == "attempt-files":
        report = attempt.inspect_attempt(args.root, plan, records, args.descriptor_sha256, **pins)
    elif args.command == "attempt-chunk-audit":
        from banto_ai import anomaly_v03_chunk_audit as chunk_audit
        report = chunk_audit.audit_chunk_attempt(args.root, plan, records, args.descriptor_sha256,
            args.producer_root, args.consumer_root, args.verifier_revision, args.plan, **pins)
    else:
        report = attempt.audit_attempt(args.root, plan, records, args.descriptor_sha256,
            args.producer_root, args.consumer_root, args.verifier_revision, **pins)
    load_journal(*inputs)
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
    verify = commands.add_parser("preflight-trial", help="Bind one reference journal to an existing six-cell trial; no campaign credit")
    verify.add_argument("--plan", type=Path, required=True)
    verify.add_argument("--journal-dir", type=Path, required=True)
    verify.add_argument("--reference", type=Path, required=True)
    verify.add_argument("--reference-sha256", required=True)
    verify.add_argument("--verifier-revision", required=True)
    initialize = commands.add_parser("store-init", help="Create a new metadata-only store; refuses every existing root")
    initialize.add_argument("--parent", type=Path, required=True)
    initialize.add_argument("--name", required=True)
    initialize.add_argument("--plan", type=Path, required=True)
    initialize.add_argument("--plan-sha256", required=True)
    recover = commands.add_parser("store-recover-init", help="Read an empty committed store after a lost initial receipt")
    recover.add_argument("--root", type=Path, required=True)
    recover.add_argument("--plan-sha256", required=True)
    for name in ("store-inspect", "store-append", "store-recover-append"):
        command = commands.add_parser(name, help="Metadata only; requires externally retained receipt and intent pins")
        command.add_argument("--root", type=Path, required=True)
        command.add_argument("--receipt", type=Path, required=True)
        command.add_argument("--receipt-sha256", required=True)
        if name != "store-inspect":
            command.add_argument("--record", type=Path, required=True)
            command.add_argument("--record-sha256", required=True)
    for name in ("attempt-layout", "attempt-validate", "attempt-files", "attempt-audit", "attempt-chunk-audit"):
        command = commands.add_parser(name, help="Inspect attempt files or audit saved ledgers; never resume")
        command.add_argument("--plan", type=Path, required=True)
        command.add_argument("--plan-sha256", required=True)
        command.add_argument("--journal-dir", type=Path, required=True)
        command.add_argument("--record-count", type=int, required=True)
        command.add_argument("--head-sha256", required=True)
        if name == "attempt-validate":
            command.add_argument("--descriptor", type=Path, required=True)
        if name != "attempt-layout":
            command.add_argument("--descriptor-sha256", required=True)
        if name in ("attempt-files", "attempt-audit", "attempt-chunk-audit"):
            command.add_argument("--root", type=Path, required=True, help="Attempt tree root, separate from metadata-only store")
        if name in ("attempt-audit", "attempt-chunk-audit"):
            command.add_argument("--producer-root", type=Path, required=True)
            command.add_argument("--consumer-root", type=Path, required=True, help="Historical audit checkout")
            command.add_argument("--verifier-revision", required=True, help="This clean verifier checkout's full revision")
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            report = checkpoints.fixed_plan(args.producer_revision, args.consumer_revision)
        elif args.command == "inspect":
            report = inspect(args.plan, args.journal_dir, args.plan_sha256, args.record_count, args.head_sha256)
        elif args.command == "preflight-trial":
            report = preflight(args)
        elif args.command in ("attempt-layout", "attempt-validate"):
            report = attempt_metadata(args)
        elif args.command in ("attempt-files", "attempt-audit", "attempt-chunk-audit"):
            report = attempt_files(args)
        else:
            report = write_metadata(args)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"status": "checkpoint_metadata_failed", "error_type": type(error).__name__,
                          "message": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
