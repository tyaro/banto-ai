"""Explicit engineering preparation/continuation; no automatic full-run launch."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import anomaly_v03_budgeted_run as runs
from . import anomaly_v03_chunk_execution as native
from . import anomaly_v03_checkpoints as checkpoints
from . import anomaly_v03_checkpoint_store as journal
from . import anomaly_v03_engineering as engine
from . import anomaly_v03_engineering_contract as policy
from . import anomaly_v03_engineering_inventory as snapshot
from . import anomaly_v03_process_supervisor as processes
from . import _anomaly_v03_engineering_runtime as resources
from . import _anomaly_v03_inventory as inventory
from . import _anomaly_v03_io as storage
from . import _anomaly_v03_runtime as rt

PARENT = "artifacts/v03-runs"
FORMAT = "anomaly-v03-engineering-launch-preparation-v1"
INSPECTION_LIMITS = {"wall_seconds": 300, "private_bytes": 512 * 1024**2, "output_bytes": snapshot.MAX_BYTES}


def inspect(root, revision, control):
    """One owned, bounded observation process; result/monitor files are exclusive."""
    command = [sys.executable, "-B", str(root / "tools/evaluator/run_anomaly_v03_campaign.py"),
               "_inventory", "--root", str(root), "--expected-head", revision]
    # If this raises UnreapedWorker, do no further IO before returning its owner.
    report = processes.supervise(command, root, control, INSPECTION_LIMITS,
                                 boundary=lambda: inventory._clean(root, revision))
    primary = None
    if report["stop_reason"] is not None:
        primary = resources.ResourceStop(report["stop_reason"])
    elif not (report["status"] == "complete" and report["exit_code"] == 0 and report["worker_exit_confirmed"]
              and not report["observation_errors"] and report["stderr"]["bytes"] == 0):
        primary = RuntimeError("runtime inspection did not complete")
    try:
        monitor = runs._write(control / "supervision.json", report)
    except BaseException as error:
        if primary is not None:
            raise primary from error
        raise
    if primary is not None:
        raise primary
    raw = journal.read_metadata(control / "report.json", snapshot.MAX_BYTES)
    engine._same({"bytes": len(raw), "sha256": storage.sha(raw)}, report["output"], "inspection output changed")
    value = snapshot.validate(native.v.strict_json(raw), root, revision)
    rt.require(type(value["pid"]) is int and value["pid"] == report["worker_pid"], "inspection process binding")
    engine._same(value["runtime"], report["runtime_before"], "inspection runtime differs from supervisor")
    engine._same(report["runtime_after"], report["runtime_before"], "inspection runtime changed")
    inventory._clean(root, revision)
    return value, {"report": {"path": str(control / "report.json"), "sha256": storage.sha(raw)}, "monitor": monitor}


def location(root, revision, name):
    root = engine._root(Path(root))
    inventory._clean(root, revision)
    return root, root / PARENT / policy.attempt_name(name)


def prepare(root, revision, name):
    root, target = location(root, revision, name)
    plan = checkpoints.fixed_plan(revision, revision)
    # Reject long paths before allocating the preparation or running inspection.
    for index in range(120):
        native._path_budget(target / "run/attempts", plan, index, 1)
    rt.regular_path(target.parent, directory=True, missing=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.mkdir()
    value, inspection = inspect(root, revision, target / "inspection")
    prepared = runs.prepare(target, "run", plan, value["runtime"])
    result = {"format": FORMAT, "source_root": str(root), "revision": revision, "name": name,
              "budgeted": prepared, "inspection": inspection, "formal_permission": False}
    pin = runs._write(target / "prepared.json", result)
    return {"status": "engineering_run_prepared", "prepared": pin, "state": prepared["state"],
        "limits": runs.budget(), "runtime_snapshot_recorded": True, "full_runtime_inventory_complete": False,
        "execution_started": False, "formal_permission": False}


def open_run(root, revision, name, prepared_hash, state_path, state_hash):
    root, target = location(root, revision, name)
    raw = journal.read_metadata(target / "prepared.json", runs.MAX_STATE_BYTES)
    rt.require(storage.sha(raw) == prepared_hash, "external preparation hash mismatch")
    value = native.v.strict_json(raw)
    rt.require(type(value) is dict and set(value) == {"format", "source_root", "revision", "name", "budgeted",
                                                    "inspection", "formal_permission"}, "preparation fields")
    engine._same([value["format"], value["source_root"], value["revision"], value["name"], value["formal_permission"]],
                 [FORMAT, str(root), revision, name, False], "preparation binding")
    engine._same(value["budgeted"]["root"], str(target / "run"), "prepared run location")
    for role, filename, maximum in (("report", "report.json", snapshot.MAX_BYTES), ("monitor", "supervision.json", runs.MAX_STATE_BYTES)):
        pin = value["inspection"][role]
        path = target / "inspection" / filename
        engine._same(pin["path"], str(path), "prepared inspection location")
        rt.require(storage.sha(journal.read_metadata(path, maximum)) == pin["sha256"], "prepared inspection changed")
    session = runs.Run(target / "run", value["budgeted"]["request"]["sha256"], state_path, state_hash, root, root, revision)
    engine._same(session.session.plan, checkpoints.fixed_plan(revision, revision), "prepared source selection")
    return root, session


def continue_run(root, revision, session, count):
    observed = resources.probe_runtime(root)

    def callbacks(controller):
        directory = session.root / f"control/{session.sequence + 1:06d}"
        # Observation is inside Run.run's activity accounting and before data work.
        value, pin = inspect(root, revision, directory / "inspection")
        engine._same(value["runtime"], observed, "runtime changed before continuation")
        runs._write(directory / "inspection-pin.json", pin)
        return native.NativeCallbacks(controller)

    return session.run(observed, max_chunks=count, callbacks_factory=callbacks)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prepare or explicitly continue an engineering dev/smoke run")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "continue", "_inventory"):
        command = commands.add_parser(name)
        command.add_argument("--root", type=Path, required=True)
        command.add_argument("--expected-head", required=True)
        if name != "_inventory":
            command.add_argument("--name", required=True)
        if name == "continue":
            command.add_argument("--prepared-sha256", required=True)
            command.add_argument("--state-path", type=Path, required=True)
            command.add_argument("--state-sha256", required=True)
            command.add_argument("--max-chunks", type=int, choices=range(1, 121), required=True)
    args, session = parser.parse_args(argv), None
    try:
        if args.command == "_inventory":
            result = snapshot.collect(args.root, args.expected_head)
        elif args.command == "prepare":
            result = prepare(args.root, args.expected_head, args.name)
        else:
            root, session = open_run(args.root, args.expected_head, args.name, args.prepared_sha256,
                                     args.state_path, args.state_sha256)
            result = continue_run(root, args.expected_head, session, args.max_chunks)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
        return 0
    except processes.UnreapedWorker as error:
        try:
            print(json.dumps({"status": "worker_exit_unconfirmed", "worker_pid": error.process.pid}), file=sys.stderr, flush=True)
        except BaseException:
            pass
        processes.retain_until_exit(error)
        return 2
    except (Exception, KeyboardInterrupt) as error:
        print(json.dumps({"status": "engineering_run_stopped", "error_type": type(error).__name__, "message": str(error),
            "state": session.last_closed if session is not None else None, "formal_permission": False}), file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
