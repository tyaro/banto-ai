"""Native chunk callbacks and a single new six-evaluation connection trial."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

from . import anomaly_v03 as v
from . import anomaly_v03_attempt_controller as lifecycle
from . import anomaly_v03_attempt_descriptor as descriptor
from . import anomaly_v03_checkpoints as checkpoints
from . import anomaly_v03_checkpoint_store as journal
from . import anomaly_v03_chunk_audit as audit
from . import anomaly_v03_chunk_contract as chunk
from . import anomaly_v03_chunk_producer as producer
from . import anomaly_v03_engineering as engine
from . import anomaly_v03_engineering_contract as policy
from . import anomaly_v03_materializer as materializer
from . import anomaly_v03_process_supervisor as processes
from . import _anomaly_v03_engineering_runtime as resources
from . import _anomaly_v03_io as storage
from . import _anomaly_v03_runtime as rt

PRODUCER_LIMITS = {"wall_seconds": 900, "private_bytes": 2 * 1024**3, "output_bytes": 1024**2}
AUDIT_LIMITS = {"wall_seconds": 600, "private_bytes": 1024**3, "output_bytes": 8 * 1024**2}
TRIAL_PARENT = "artifacts/anomaly-v03-chunk-trials"


def _path_budget(tree, plan, index, attempt):
    """Reject long native paths before generating data, without OS policy changes."""
    manifest = chunk.new_manifest(plan, index, attempt)
    names = ["planned.json", "context.json", "manifest.json"]
    names += ["evaluations/" + slot["identity"]["evaluation_id"] + ".json" for slot in manifest["slots"]]
    names += ["datasets/" + dataset["identity"]["dataset_id"] + "/" + name
              for dataset in manifest["datasets"] for name in materializer.DATASET_FILES]
    result = Path(tree).absolute() / f"chunks/{index:03d}/attempt-{attempt:04d}/result"
    # Include the longer final directory spelling, not only the staging path.
    longest = max(len(str(result / phase / name).encode("utf-16-le")) // 2
                  for phase in ("stage", "payload") for name in names)
    rt.require(longest < 248, "output path too long; use a shorter checkout or trial name")


def _worker(root, revision, tree, plan_path, plan_hash, index, attempt):
    started = time.monotonic()
    root = engine._root(root)
    plan_path, raw, plan = audit.read_plan(plan_path, plan_hash)
    selected = chunk.chunk_plan(plan, index, attempt)
    _path_budget(tree, plan, index, attempt)
    engine._same(revision, plan["source_bindings"]["producer_revision"], "worker revision selection")
    checkout = rt.capture_checkout(root, revision)
    tree = rt.regular_path(tree, directory=True)
    parent = rt.regular_path(tree / f"chunks/{index:03d}/attempt-{attempt:04d}", directory=True)
    observed = resources.probe_runtime(parent)
    resources.require_start_resources(parent)

    def boundary():
        checkout.recheck()
        rt.require(journal.read_metadata(plan_path, journal.MAX_PLAN_BYTES) == raw, "worker plan changed")
        engine._same(resources.probe_runtime(parent), observed, "worker runtime changed")

    boundary()
    with storage.LocalPublication(parent, "result") as owned:
        result = producer.execute_chunk(owned, checkout, observed, plan, index, attempt, started,
            boundary=boundary, sample_memory=resources.memory_bytes)
    verified = storage.verify_local_publication(parent / "result",
        expected_marker_sha256=result["receipt"]["marker_raw_sha256"],
        verify_semantics=lambda data: producer.verify_payloads(data, checkout, observed, plan, index, attempt))
    boundary()
    resources.check_budget(time.monotonic() - started, resources.memory_bytes()["peak_private_bytes"],
                           result["resources_at_publication"]["payload_bytes"] + engine.CONTROL_RESERVE)
    return {"status": "complete", "binding": selected["binding"], "receipt": result["receipt"],
        "verification": verified, "coverage": result["manifest"]["coverage"],
        "formal_permission": False, "campaign_evaluations_credited": 0}


class NativeCallbacks:
    """One producer process, then a separate ledger-auditor process; no descendants."""
    def __init__(self, session):
        self.session = session
        self.plan_path, self.plan_raw, plan = audit.read_plan(session.metadata_root / "plan.json",
                                                          session.pins["expected_plan_sha256"])
        engine._same(plan, session.plan, "native callback plan")
        # Fresh controller verification executes in this interpreter/checkout.
        engine._root(session.consumer_root)
        engine._same(session.verifier_revision, plan["source_bindings"]["consumer_revision"],
                     "native controller must use pinned consumer revision")
        self.producer = rt.capture_checkout(session.producer_root, plan["source_bindings"]["producer_revision"])
        self.consumer = rt.capture_checkout(session.consumer_root, plan["source_bindings"]["consumer_revision"])

    def boundary(self):
        self.producer.recheck()
        self.consumer.recheck()
        rt.require(journal.read_metadata(self.plan_path, journal.MAX_PLAN_BYTES) == self.plan_raw, "native plan changed")

    def _selection(self, context, status):
        self.session._load()
        row = self.session.records[-1]
        engine._same([row["status"], row["chunk_index"], row["attempt"]],
                     [status, context["chunk_index"], context["attempt"]], "native callback journal order")
        engine._same(context["plan"], self.session.plan, "native callback context plan")
        layout = descriptor._layout(row)
        _path_budget(self.session.root, self.session.plan, row["chunk_index"], row["attempt"])
        # descriptor_path changes with each record; all output paths stay fixed.
        engine._same({k: val for k, val in layout.items() if k != "descriptor_path"},
                     {k: val for k, val in context["layout"].items() if k != "descriptor_path"}, "native callback layout")
        self.boundary()
        return layout, row["chunk_index"], row["attempt"]

    def _save_monitor(self, argv, cwd, control, limits, *, producer_binding=None):
        report = None
        try:
            report = processes.supervise(argv, cwd, control, limits,
                stdout_name="stdout.jsonl" if producer_binding else "report.json", boundary=self.boundary)
        except processes.UnreapedWorker as error:
            # Keep ownership and the running journal. Do not declare a retriable failure.
            report = error.report
            try:
                self._write_monitor(control, report, producer_binding)
            except BaseException:
                pass  # A diagnostic write must not discard the original owner.
            raise
        primary = None
        if report["stop_reason"] == "interrupted":
            primary = KeyboardInterrupt("owned worker interrupted")
        elif report["stop_reason"] in ("time_limit", "memory_limit", "output_limit", "insufficient_resources"):
            primary = resources.ResourceStop(report["stop_reason"])
        elif report["stop_reason"] == "runtime_changed":
            primary = rt.IntegrityError("native worker runtime changed")
        elif report["status"] != "complete":
            primary = RuntimeError("owned worker did not complete")
        elif report["stderr"] != {"bytes": 0, "sha256": storage.sha(b"")}:
            primary = rt.IntegrityError("native worker stderr is not empty")
        try:
            self._write_monitor(control, report, producer_binding)
        except BaseException as secondary:
            if primary is not None:
                raise primary from secondary
            raise
        if primary is not None:
            raise primary
        return report

    @staticmethod
    def _write_monitor(control, report, binding):
        value = dict(report)
        if binding is not None:
            value.update(format=audit.SUPERVISION_FORMAT, policy_id=policy.POLICY_ID, scope=chunk.SCOPE,
                attempt_id="result", binding=binding, runtime=report["runtime_before"],
                resource_measurement_scope="whole_worker_including_replays_and_exit")
        storage._exclusive(control / "supervision.json", storage.json_bytes(value))

    def produce(self, context):
        layout, index, attempt = self._selection(context, "running")
        root = self.session.producer_root
        argv = [sys.executable, "-B", str(root / "tools/evaluator/run_anomaly_v03_chunk.py"), "_worker",
            "--root", str(root), "--expected-head", self.producer.revision, "--attempt-tree", str(self.session.root),
            "--plan", str(self.plan_path), "--plan-sha256", self.session.pins["expected_plan_sha256"],
            "--chunk-index", str(index), "--attempt", str(attempt)]
        binding = chunk.chunk_plan(self.session.plan, index, attempt)["binding"]
        return self._save_monitor(argv, root, self.session.root / layout["producer_control_root"],
                                  PRODUCER_LIMITS, producer_binding=binding)

    def inspect_audit(self, context):
        layout, index, attempt = self._selection(context, "saved_pending_verification")
        entries = lifecycle._artifacts(self.session.root, layout)
        argv = audit.invocation(self.session.consumer_root, self.session.root / layout["result_root"],
            entries["marker"]["sha256"], entries["producer_supervision"]["sha256"], self.session.producer_root,
            self.consumer.revision, self.plan_path, self.session.pins["expected_plan_sha256"], index, attempt)
        return self._save_monitor(argv, self.session.consumer_root, self.session.root / layout["audit_root"], AUDIT_LIMITS)

    def run_next(self, observed, *, retain=lambda result: None):
        """Never mark an unconfirmed live worker as a safely retriable failure."""
        self.boundary()
        context = self.session.start(observed)
        try:
            retain(context)
            self.produce(context)
            retain(self.session.producer_saved())
            self.inspect_audit(context)
            result = self.session.finish()
            retain(result)
            return result
        except (lifecycle.TransitionIncomplete, processes.UnreapedWorker):
            raise
        except (Exception, KeyboardInterrupt) as error:
            reason = "interrupted" if isinstance(error, KeyboardInterrupt) else "resource_limit" if isinstance(
                error, resources.ResourceStop) else "verification_failed" if isinstance(error, v.V03ValidationError) else "exception"
            self.session._preserve_stop(error, reason, integrity=reason == "verification_failed")
            raise


def trial(root, revision, name):
    """Fresh first chunk only; no existing campaign resume or full-run permission."""
    root, name = engine._root(root), policy.attempt_name(name)
    observed = resources.probe_runtime(root)
    before = resources.require_start_resources(root)
    checkout = rt.capture_checkout(root, revision)
    parent = root / TRIAL_PARENT
    target = parent / name
    plan = checkpoints.fixed_plan(revision, revision)
    _path_budget(target / "attempts", plan, 0, 1)
    rt.regular_path(parent, directory=True, missing=True)
    parent.mkdir(parents=True, exist_ok=True)
    target.mkdir()  # Existing or partially written trials are never reused.
    request = {"format": "anomaly-v03-chunk-connection-trial-v1", "chunk_index": 0, "attempt": 1,
        "maximum_chunks": 1, "plan_sha256": v.canonical_sha256(plan), "revision": revision,
        "producer_limits": PRODUCER_LIMITS, "audit_limits": AUDIT_LIMITS, "payload_limit_bytes": policy.limits()["output_bytes"],
        "runtime": observed, "campaign_evaluations_credited": 0, "formal_permission": False}
    storage._exclusive(target / "request.json", storage.json_bytes(request))
    receipt = journal.create_store(target, "metadata", plan)
    storage._exclusive(target / "initial-receipt.json", storage.json_bytes(receipt))
    tree = target / "attempts"
    tree.mkdir()
    retained = target / "receipts"
    retained.mkdir()
    session = lifecycle.Controller(target / "metadata", receipt, tree, root, root, revision)
    callbacks = NativeCallbacks(session)
    started = time.monotonic()

    def retain(value):
        sequence = value["receipt"]["journal"]["expected_record_count"]
        # Separate from both metadata and attempt trees; preserve exact successive receipts.
        storage._exclusive(retained / f"{sequence:06d}.json", storage.json_bytes(value))

    result = callbacks.run_next(observed, retain=retain)
    checkout.recheck()
    report = {"status": "connection_trial_verified", "request": request, "checkpoint": result,
        "elapsed_seconds": time.monotonic() - started, "controller_memory": resources.memory_bytes(),
        "free_before": before, "free_after": resources.free_resources(root),
        "verified_evaluations": 6, "campaign_evaluations_credited": 0, "formal_permission": False}
    storage._exclusive(target / "summary.json", storage.json_bytes(report))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="One new six-evaluation native connection trial")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("trial", "_worker"):
        command = commands.add_parser(name)
        command.add_argument("--root", type=Path, required=True)
        command.add_argument("--expected-head", required=True)
        if name == "trial":
            command.add_argument("--name", required=True)
        else:
            for key in ("attempt-tree", "plan"):
                command.add_argument("--" + key, type=Path, required=True)
            command.add_argument("--plan-sha256", required=True)
            command.add_argument("--chunk-index", type=int, required=True)
            command.add_argument("--attempt", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "trial":
            result = trial(args.root, args.expected_head, args.name)
        else:
            result = _worker(args.root, args.expected_head, args.attempt_tree, args.plan, args.plan_sha256,
                             args.chunk_index, args.attempt)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
        return 0
    except processes.UnreapedWorker as error:
        try:
            print(json.dumps({"status": "worker_exit_unconfirmed", "worker_pid": error.process.pid,
                              "message": "Retaining the original owner until exit is confirmed."}), file=sys.stderr, flush=True)
        except BaseException:
            pass  # Keep ownership even when diagnostic output cannot be written.
        # No new work or journal transition while the worker may still write.
        # Even an interrupt during reconciliation must not silently orphan it.
        while error.process.returncode is None:
            try:
                error.process.kill()
            except BaseException:
                pass
            try:
                error.process.wait(timeout=30)
            except BaseException:
                pass
        error.process._handle.Close()
        return 2
    except (OSError, ValueError, RuntimeError) as error:
        print(json.dumps({"status": "chunk_execution_failed", "error_type": type(error).__name__,
                          "message": str(error)}), file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
