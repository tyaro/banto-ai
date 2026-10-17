"""Budget accounting and continuation at closed single-writer boundaries.

Run budgets are cooperative admission/stop limits, not process-tree hard limits.
An unclosed invocation requires reconciliation; its time is never reset on retry.
"""
from __future__ import annotations

import copy
import math
import os
from pathlib import Path
import stat
import time

from . import anomaly_v03 as v
from . import anomaly_v03_attempt_controller as lifecycle
from . import anomaly_v03_checkpoints as checkpoints
from . import anomaly_v03_checkpoint_store as journal
from . import anomaly_v03_chunk_execution as native
from . import anomaly_v03_engineering_contract as policy
from . import _anomaly_v03_engineering_runtime as resources
from . import _anomaly_v03_io as storage
from . import _anomaly_v03_runtime as rt

FORMAT = "anomaly-v03-budgeted-continuation-v1"
STATE_FORMAT = "anomaly-v03-closed-invocation-v1"
MAX_STATE_BYTES = 64 * 1024
MAX_INVOCATIONS = 4096
MAX_OUTPUT_ENTRIES = 200000


def budget():
    return {"wall_seconds": 48 * 3600, "output_bytes": 32 * 1024**3,
        "controller_private_bytes": 2 * 1024**3, "chunk_admission_seconds": 2460,
        "chunk_output_reserve_bytes": 1024**3 + 32 * 1024**2,
        "control_reserve_bytes": 1024**2, "producer": dict(native.PRODUCER_LIMITS),
        "audit": dict(native.AUDIT_LIMITS), "minimum_free_ram_bytes": 4 * 1024**3,
        "minimum_free_disk_bytes": 20 * 1024**3,
        "enforcement": "invocation-and-chunk-boundaries; owned workers have separate hard limits"}


def request(plan, observed):
    checkpoints.validate_plan(plan)
    policy.validate_runtime(observed)
    return {"format": FORMAT, "scope": "engineering-dev-smoke-continuation",
        "plan_sha256": v.canonical_sha256(plan), "source_bindings": copy.deepcopy(plan["source_bindings"]),
        "limits": budget(), "initial_runtime": copy.deepcopy(observed), "maximum_chunks": 120,
        "runtime_inventory_scope": "existing-basic-runtime-pins", "full_runtime_inventory_complete": False,
        "formal_permission": False, "independent_s6_complete": False, "campaign_evaluations_credited": 0}


def _same(a, b, reason):
    rt.require(v.canonical_json(a) == v.canonical_json(b), reason)


def _number(value, reason):
    rt.require(type(value) in (int, float) and math.isfinite(value) and value >= 0, reason)


def output_bytes(root):
    """Bounded metadata walk of this owned output root, counting hardlink aliases."""
    root = rt.regular_path(root, directory=True)
    count, total = 0, 0
    maximum = budget()["output_bytes"]

    def walk(folder, depth):
        nonlocal count, total
        rt.require(depth <= 16, "run output depth limit")
        with os.scandir(folder) as entries:
            for entry in entries:
                count += 1
                rt.require(count <= MAX_OUTPUT_ENTRIES, "run output inventory limit")
                info = entry.stat(follow_symlinks=False)
                rt.require(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
                           "run output contains reparse path")
                if stat.S_ISDIR(info.st_mode):
                    walk(Path(entry.path), depth + 1)
                else:
                    rt.require(stat.S_ISREG(info.st_mode), "nonregular run output")
                    total += info.st_size
                    if total > maximum:
                        raise resources.ResourceStop("output_limit")
    walk(root, 0)
    return total


def _write(path, value):
    raw = storage.json_bytes(value)
    rt.require(len(raw) <= MAX_STATE_BYTES, "run state byte limit")
    storage._exclusive(path, raw)
    return {"path": str(path), "sha256": storage.sha(raw)}


def _state(sequence, request_hash, checkpoint, elapsed, status, previous=None, stop_reason=None):
    return {"format": STATE_FORMAT, "sequence": sequence, "request_sha256": request_hash,
        "checkpoint": copy.deepcopy(checkpoint), "elapsed_seconds_total": elapsed,
        "status": status, "stop_reason": stop_reason, "previous_state_sha256": previous, "formal_permission": False}


def prepare(parent, name, plan, observed):
    """Create only new metadata and explicit limits; no computation or native freeze."""
    proposal = request(plan, observed)
    parent = rt.regular_path(parent, directory=True)
    root = parent / policy.attempt_name(name)
    # All identities must fit, including longer seed spellings later in the plan.
    for index in range(120):
        native._path_budget(root / "attempts", plan, index, 1)
    root.mkdir()
    request_pin = _write(root / "request.json", proposal)
    receipt = journal.create_store(root, "metadata", plan)
    (root / "attempts").mkdir()
    (root / "control").mkdir()
    initial = root / "control/000000"
    initial.mkdir()
    state = _state(0, request_pin["sha256"], {"receipt": receipt, "descriptor_pins": {}}, 0, "ready")
    state_pin = _write(initial / "closed.json", state)
    return {"root": str(root), "request": request_pin, "state": state_pin,
        "status": "continuation_metadata_prepared", "execution_started": False, "formal_permission": False}


def _read_state(path, expected_hash, request_hash, sequence):
    raw = journal.read_metadata(path, MAX_STATE_BYTES)
    rt.require(storage.sha(raw) == expected_hash, "external closed-state hash mismatch")
    value = v.strict_json(raw)
    rt.require(set(value) == set(_state(0, "", {}, 0, "")), "closed-state fields")
    _same([value["format"], value["request_sha256"], value["sequence"], value["formal_permission"]],
          [STATE_FORMAT, request_hash, sequence, False], "closed-state binding")
    _number(value["elapsed_seconds_total"], "closed-state elapsed time")
    rt.require(value["status"] in ("ready", "yielded", "stopped", "completed", "failed", "reconciliation_required"),
               "closed-state status")
    rt.require(value["stop_reason"] in (None, "time_budget", "output_budget", "stop_requested", "exception"),
               "closed-state stop reason")
    rt.require(type(value["checkpoint"]) is dict and set(value["checkpoint"]) == {"receipt", "descriptor_pins"},
               "closed-state checkpoint fields")
    return value


class Run:
    def __init__(self, root, request_hash, state_path, state_hash, producer_root, consumer_root, verifier_revision,
                 *, clock=time.monotonic, measure=output_bytes, sample_memory=resources.memory_bytes):
        self.root = rt.regular_path(Path(root), directory=True)
        self.clock, self.measure, self.sample_memory = clock, measure, sample_memory
        self.request_hash, self.last_closed = request_hash, None
        raw = journal.read_metadata(self.root / "request.json", MAX_STATE_BYTES)
        rt.require(storage.sha(raw) == request_hash, "external run request hash mismatch")
        self.proposal = v.strict_json(raw)
        state_path = Path(state_path).absolute()
        rt.require(state_path.name == "closed.json" and state_path.parent.parent == self.root / "control",
                   "fixed closed-state location required")
        rt.require(state_path.parent.name.isascii() and state_path.parent.name.isdigit(), "closed-state sequence")
        self.sequence = int(state_path.parent.name)
        rt.require(0 <= self.sequence < MAX_INVOCATIONS and state_path.parent.name == f"{self.sequence:06d}",
                   "closed-state sequence limit")
        _same(sorted(p.name for p in (self.root / "control").iterdir()),
              [f"{i:06d}" for i in range(self.sequence + 1)], "unclosed or unexpected invocation requires reconciliation")
        self.closed = _read_state(state_path, state_hash, request_hash, self.sequence)
        current = self.closed
        for number in range(self.sequence - 1, -1, -1):
            previous = _read_state(self.root / f"control/{number:06d}/closed.json", current["previous_state_sha256"],
                                   request_hash, number)
            rt.require(previous["elapsed_seconds_total"] <= current["elapsed_seconds_total"], "run budget time rolled back")
            current = previous
        _same([current["previous_state_sha256"], current["elapsed_seconds_total"], current["status"]],
              [None, 0, "ready"], "initial closed-state budget")
        self.state_hash = state_hash
        checkpoint = self.closed["checkpoint"]
        self.session = lifecycle.Controller(self.root / "metadata", checkpoint["receipt"], self.root / "attempts",
            producer_root, consumer_root, verifier_revision, descriptor_pins=checkpoint["descriptor_pins"])
        _same(self.proposal, request(self.session.plan, self.proposal["initial_runtime"]), "run request or limits changed")
        rt.require(self.closed["status"] != "reconciliation_required", "run requires reconciliation")
        rt.require(not self.session.records or self.session.records[-1]["status"] in (*checkpoints.VERIFIED, "failed", "interrupted"),
                   "active or blocked attempt requires reconciliation")
        self._request_raw = raw

    def run(self, observed, *, max_chunks=120, callbacks_factory=native.NativeCallbacks):
        """Run sequential chunks; return a new externally retained closed-state pin.

        Native runtime/source validation remains in the callbacks. A stop request
        at control/<invocation>/stop.request is honored between whole chunks.
        """
        started = self.clock()
        rt.require(type(max_chunks) is int and 1 <= max_chunks <= 120, "invocation chunk count")
        rt.require(self.sequence + 1 < MAX_INVOCATIONS, "invocation count limit")
        # Re-open from the original external pins to reject stale objects/reuse.
        check = Run(self.root, self.request_hash, self.root / f"control/{self.sequence:06d}/closed.json", self.state_hash,
            self.session.producer_root, self.session.consumer_root, self.session.verifier_revision,
            clock=self.clock, measure=self.measure, sample_memory=self.sample_memory)
        self.session = check.session
        policy.validate_runtime(observed)
        limits = self.proposal["limits"]
        directory = self.root / f"control/{self.sequence + 1:06d}"
        directory.mkdir()
        _write(directory / "started.json", {"previous_state_sha256": self.state_hash,
            "request_sha256": self.request_hash, "max_chunks": max_chunks, "runtime": observed})
        (directory / "receipts").mkdir()
        count, status, primary, stop_reason = 0, "yielded", None, None

        def checkpoint():
            return {"receipt": self.session.receipt, "descriptor_pins": self.session.descriptor_pins}

        def retain(value):
            # The start context includes the entire plan; keep only recovery pins.
            slim = {key: value[key] for key in ("receipt", "descriptor_pins", "intent_path", "intent_sha256", "descriptor_sha256")}
            number = value["receipt"]["journal"]["expected_record_count"]
            _write(directory / f"receipts/{number:06d}.json", slim)

        def elapsed_seconds():
            elapsed = self.clock() - started
            _number(elapsed, "invocation clock moved backwards")
            return elapsed

        def measured_size():
            size = self.measure(self.root)
            rt.require(type(size) is int and size >= 0, "run output measurement")
            return size

        def memory_check():
            private = self.sample_memory()["private_bytes"]
            rt.require(type(private) is int and private >= 0, "run memory measurement")
            if private > limits["controller_private_bytes"]:
                raise resources.ResourceStop("memory_limit")

        def unchanged_request():
            rt.require(journal.read_metadata(self.root / "request.json", MAX_STATE_BYTES) == self._request_raw, "run request changed")

        def admission():
            nonlocal stop_reason
            unchanged_request()
            if self.closed["elapsed_seconds_total"] + elapsed_seconds() + limits["chunk_admission_seconds"] > limits["wall_seconds"]:
                stop_reason = "time_budget"
                return False
            if measured_size() + limits["chunk_output_reserve_bytes"] > limits["output_bytes"]:
                stop_reason = "output_budget"
                return False
            memory_check()
            resources.require_start_resources(self.root)
            return True

        try:
            if not admission():
                status = "stopped"
            else:
                callbacks = callbacks_factory(self.session)
                while count < max_chunks and self.session.state["next_unverified_chunk"] is not None:
                    stop = directory / "stop.request"
                    rt.regular_path(stop, missing=True)
                    if stop.exists():
                        status, stop_reason = "stopped", "stop_requested"
                        break
                    if not admission():
                        status = "stopped"
                        break
                    before = self.session.state["next_unverified_chunk"]
                    callbacks.run_next(observed, retain=retain)
                    expected = before + 1 if before < 119 else None
                    rt.require(self.session.state["next_unverified_chunk"] == expected
                               and self.session.records[-1]["status"] in checkpoints.VERIFIED,
                               "callback did not verify exactly one chunk")
                    count += 1
                    unchanged_request()
                    memory_check()
                    if self.closed["elapsed_seconds_total"] + elapsed_seconds() >= limits["wall_seconds"]:
                        status, stop_reason = "stopped", "time_budget"
                        break
                if self.session.state["next_unverified_chunk"] is None and status != "stopped":
                    status = "completed"
        except BaseException as error:
            primary, status, stop_reason = error, "failed", "exception"
        # Never close an invocation if worker ownership or a transition is unresolved.
        unsafe = isinstance(primary, (native.processes.UnreapedWorker, lifecycle.TransitionIncomplete))
        if self.session.records and self.session.records[-1]["status"] not in (*checkpoints.VERIFIED, "failed", "interrupted"):
            unsafe = True
        if self.session.last_stop and "failure_recording_error" in self.session.last_stop:
            unsafe = True
        if unsafe:
            # In particular, do not walk logs/output while an unreaped worker can
            # still write. The original exception retains the process owner.
            if primary is not None:
                raise primary
            raise lifecycle.TransitionIncomplete("unclosed invocation requires reconciliation")
        try:
            unchanged_request()
            size = measured_size()
            rt.require(size + limits["control_reserve_bytes"] <= limits["output_bytes"], "run output budget exceeded")
            elapsed = elapsed_seconds()
            if primary is None and self.closed["elapsed_seconds_total"] + elapsed >= limits["wall_seconds"]:
                status, stop_reason = "stopped", "time_budget"
            final = _state(self.sequence + 1, self.request_hash, checkpoint(),
                           self.closed["elapsed_seconds_total"] + elapsed, status, self.state_hash, stop_reason)
            self.last_closed = _write(directory / "closed.json", final)
        except BaseException:
            if primary is not None:
                raise primary
            raise
        if primary is not None:
            raise primary
        return {"state": self.last_closed, "status": status, "stop_reason": stop_reason, "chunks_verified_in_invocation": count,
            "next_unverified_chunk": self.session.state["next_unverified_chunk"],
            "elapsed_seconds_total": final["elapsed_seconds_total"], "output_bytes_before_closed_state": size,
            "formal_permission": False, "campaign_evaluations_credited": 0}
