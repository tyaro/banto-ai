"""Single-writer attempt lifecycle with durable transition intents.

This core takes owned producer/auditor callbacks; it provides no launch CLI or
budget freeze. It never overwrites an attempt or resumes a partial transition.
"""
from __future__ import annotations

import copy
from pathlib import Path

from . import anomaly_v03 as v
from . import anomaly_v03_checkpoints as checkpoints
from . import anomaly_v03_checkpoint_store as journal
from . import anomaly_v03_attempt_descriptor as descriptor
from . import anomaly_v03_attempt_files as files
from . import anomaly_v03_chunk_contract as chunk
from . import anomaly_v03_chunk_audit as audit
from . import _anomaly_v03_engineering_runtime as resources
from . import _anomaly_v03_io as storage
from . import _anomaly_v03_runtime as rt

INTENT_FORMAT = "anomaly-v03-controller-transition-v1"


class TransitionIncomplete(RuntimeError):
    """An intent exists; inspect/recover it before making any further mutation."""


def _directory(path):
    rt.regular_path(path, directory=True, missing=True)
    path.mkdir(exist_ok=True)


def _artifacts(root, layout):
    entries = {}
    for role in descriptor.ROLES:
        path = root / layout["files"][role]
        links = 2 if role == "marker" else 1
        rt.regular_path(path, links=links, missing=True)
        raw = files._read(path, files.CONTROL_LIMITS[role], links=links) if path.exists() else None
        entries[role] = None if raw is None else {"path": layout["files"][role], "bytes": len(raw), "sha256": storage.sha(raw)}
    return entries


class Controller:
    def __init__(self, metadata_root, receipt, attempt_root, producer_root, consumer_root, verifier_revision,
                 *, descriptor_pins=None):
        self.metadata_root = rt.regular_path(Path(metadata_root), directory=True)
        self.root = rt.regular_path(Path(attempt_root), directory=True)
        rt.require(self.root != self.metadata_root and self.root not in self.metadata_root.parents
            and self.metadata_root not in self.root.parents, "metadata and attempt roots must be separate")
        self.receipt = copy.deepcopy(receipt)
        self.descriptor_pins = copy.deepcopy(descriptor_pins if descriptor_pins is not None else {})
        self.producer_root, self.consumer_root = Path(producer_root).absolute(), Path(consumer_root).absolute()
        self.verifier_revision = verifier_revision
        self.verified_in_session = set()
        self.last_stop = None
        self._load()

    def _load(self):
        pins = journal.validate_receipt(self.metadata_root, self.receipt)
        _, self.plan, self.records, self.state = journal._load(self.metadata_root, pins)
        self.pins = pins
        expected = {str(row["sequence"]) for row in self.records if row["status"] in checkpoints.VERIFIED}
        rt.require(type(self.descriptor_pins) is dict and set(self.descriptor_pins) == expected,
                   "externally retained verified descriptor pins required")
        for digest in self.descriptor_pins.values():
            checkpoints._hex(digest, 64, "external verified descriptor hash")

    def _verify(self, records, pins, digest):
        return audit.audit_chunk_attempt(self.root, self.plan, records, digest, self.producer_root,
            self.consumer_root, self.verifier_revision, self.metadata_root / "plan.json", **pins)

    def _revalidate_completed(self):
        for offset, record in enumerate(self.records):
            if record["status"] not in checkpoints.VERIFIED:
                continue
            digest = checkpoints.record_hash(record)
            if digest in self.verified_in_session:
                continue
            pins = {**self.pins, "expected_record_count": offset + 1, "expected_head_sha256": digest}
            self._verify(self.records[:offset + 1], pins, self.descriptor_pins[str(offset + 1)])
            self.verified_in_session.add(digest)

    def _transition(self, record, entries, *, audit_runtime=None, verify=False):
        self._load()
        raw, next_pins = journal._intent(self.plan, self.records, record, self.pins)
        records = self.records + [record]
        value = descriptor.new_descriptor(self.plan, records, entries, audit_runtime=audit_runtime, **next_pins)
        descriptor_raw = storage.json_bytes(value)
        digest = storage.sha(descriptor_raw)
        intent = {"format": INTENT_FORMAT, "attempt_root": str(self.root), "previous_receipt": self.receipt,
            "previous_descriptor_pins": self.descriptor_pins, "record": record,
            "descriptor_path": value["layout"]["descriptor_path"], "descriptor_sha256": digest}
        control = self.root / "controller"
        _directory(control)
        step = control / f"{record['sequence']:06d}"
        step.mkdir()  # Even an incomplete old transition is never reused.
        intent_raw = storage.json_bytes(intent)
        rt.require(len(intent_raw) <= 32 * 1024, "controller intent byte limit")
        storage._exclusive(step / "intent.json", intent_raw)
        try:
            target = self.root / value["layout"]["descriptor_path"]
            _directory(target.parent)
            storage._exclusive(target, descriptor_raw)
            if verify:
                self._verify(records, next_pins, digest)
            else:
                files.inspect_attempt(self.root, self.plan, records, digest, **next_pins)
            receipt = journal.append_record(self.metadata_root, self.receipt, record)
            descriptor_pins = {**self.descriptor_pins}
            if verify:
                descriptor_pins[str(record["sequence"])] = digest
            result = {"receipt": receipt, "descriptor_sha256": digest,
                "intent_path": str(step / "intent.json"), "intent_sha256": storage.sha(intent_raw),
                "descriptor_pins": descriptor_pins, "execution_authorized": False, "campaign_evaluations_credited": 0}
            storage._exclusive(step / "receipt.json", storage.json_bytes(result))
        except BaseException as error:
            # Do not guess whether journal rename committed. Both intent and any
            # saved bytes remain for exact, read-only reconciliation.
            raise TransitionIncomplete(str(step / "intent.json")) from error
        self.receipt = receipt
        self.descriptor_pins = descriptor_pins
        self._load()
        if verify:
            self.verified_in_session.add(checkpoints.record_hash(record))
        return copy.deepcopy(result)

    def _record(self, status, context, index, attempt, entries, *, outcome=None, reason=None):
        evidence = {key: entries[role]["sha256"] if entries[role] else None for role, key in descriptor.JOURNAL_EVIDENCE.items()}
        return checkpoints.make_record(self.pins["expected_plan_sha256"], self.pins["expected_head_sha256"],
            len(self.records) + 1, index, attempt, status, context, evidence=evidence, outcome=outcome, reason=reason)

    def start(self, observed):
        rt.require(not self.last_stop or "failure_recording_error" not in self.last_stop,
                   "failure recording requires reconciliation")
        self._load()
        index = self.state["next_unverified_chunk"]
        rt.require(index is not None, "all chunks already declared complete")
        last = self.records[-1] if self.records else None
        rt.require(last is None or last["status"] in (*checkpoints.VERIFIED, "failed", "interrupted"),
                   "unfinished or integrity-blocked attempt requires reconciliation")
        checkpoints._runtime(observed)
        self._revalidate_completed()
        attempt = last["attempt"] + 1 if last and last["chunk_index"] == index else 1
        chunk.chunk_plan(self.plan, index, attempt)
        entries = dict.fromkeys(descriptor.ROLES)
        context = {"source_bindings": self.plan["source_bindings"], "runtime": observed}
        record = self._record("running", context, index, attempt, entries)
        layout = descriptor._layout(record)
        # Check the transition slot before allocating an attempt on a lost commit.
        step = self.root / "controller" / f"{record['sequence']:06d}"
        rt.regular_path(step, directory=True, missing=True)
        rt.require(not step.exists(), "controller transition intent already exists")
        _directory(self.root / "chunks")
        _directory(self.root / "chunks" / f"{index:03d}")
        (self.root / layout["attempt_root"]).mkdir()
        result = self._transition(record, entries)
        return {**result, "chunk_index": index, "attempt": attempt, "layout": layout,
            "plan_path": str(self.metadata_root / "plan.json"), "plan": copy.deepcopy(self.plan)}

    def producer_saved(self):
        self._load()
        record = self.records[-1]
        rt.require(record["status"] == "running", "producer save requires running attempt")
        layout = descriptor._layout(record)
        entries = _artifacts(self.root, layout)
        rt.require(entries["marker"] and entries["producer_supervision"] and not entries["audit_report"]
                   and not entries["audit_supervision"], "producer save evidence order")
        supervision, manifest = self._producer_evidence(record, layout)
        return self._transition(self._record("saved_pending_verification", record["context"], record["chunk_index"],
            record["attempt"], entries), entries)

    def _producer_evidence(self, record, layout):
        supervision = v.strict_json(files._read(self.root / layout["files"]["producer_supervision"], 1024**2))
        manifest = v.strict_json(files._read(self.root / layout["payload_root"] / "manifest.json", 1024**2))
        index, attempt = record["chunk_index"], record["attempt"]
        audit.validate_supervision(supervision, self.plan, index, attempt)
        chunk.validate_manifest(manifest, self.plan, index, attempt)
        rt.require(manifest["state"] == "complete", "producer result incomplete")
        descriptor._same(manifest["runtime"], record["context"]["runtime"], "controller producer runtime mismatch")
        descriptor._same(supervision["runtime"], manifest["runtime"], "controller supervision runtime mismatch")
        return supervision, manifest

    def finish(self):
        self._load()
        record = self.records[-1]
        rt.require(record["status"] == "saved_pending_verification", "audit completion requires saved attempt")
        layout = descriptor._layout(record)
        entries = _artifacts(self.root, layout)
        rt.require(all(entries.values()), "audit completion needs all evidence")
        supervision, manifest = self._producer_evidence(record, layout)
        monitor = v.strict_json(files._read(self.root / layout["files"]["audit_supervision"], 1024**2))
        status = "verified_inconclusive" if manifest["coverage"]["inconclusive"] else "verified_complete"
        outcome = {"slots": [{"evaluation_id": slot["identity"]["evaluation_id"], "status": slot["status"]}
                              for slot in manifest["slots"]], "worker_exit_confirmed": True,
            "runtime_after": supervision["runtime_after"], "audit_scope": "stored_score_ledgers_only"}
        next_record = self._record(status, record["context"], record["chunk_index"], record["attempt"], entries, outcome=outcome)
        return self._transition(next_record, entries,
            audit_runtime={"before": monitor["runtime_before"], "after": monitor["runtime_after"]}, verify=True)

    def fail(self, reason="exception", *, integrity=False):
        self._load()
        record = self.records[-1]
        rt.require(record["status"] in ("running", "saved_pending_verification"), "failure requires active attempt")
        layout = descriptor._layout(record)
        entries = _artifacts(self.root, layout)
        status = "blocked_integrity" if integrity or reason in checkpoints.INTEGRITY_REASONS else "interrupted" if reason == "interrupted" else "failed"
        runtime = None
        if entries["producer_supervision"]:
            producer = v.strict_json(files._read(self.root / layout["files"]["producer_supervision"], 1024**2))
            if producer.get("runtime_after") is not None and producer.get("runtime") != producer["runtime_after"]:
                status, reason = "blocked_integrity", "runtime_changed"
        if entries["audit_supervision"]:
            monitor = v.strict_json(files._read(self.root / layout["files"]["audit_supervision"], 1024**2))
            if monitor.get("runtime_before") is not None:
                runtime = {"before": monitor["runtime_before"], "after": monitor.get("runtime_after")}
                if runtime["after"] is not None and runtime["before"] != runtime["after"]:
                    status, reason = "blocked_integrity", "runtime_changed"
        return self._transition(self._record(status, record["context"], record["chunk_index"], record["attempt"], entries,
            reason=reason), entries, audit_runtime=runtime)

    def run_next(self, observed, *, produce, inspect_audit):
        """One synchronous owned producer then auditor; callbacks must reap workers."""
        context = self.start(observed)
        try:
            produce(context)
            self.producer_saved()
            inspect_audit(context)
            return self.finish()
        except TransitionIncomplete:
            raise
        except KeyboardInterrupt as error:
            self._preserve_stop(error, "interrupted")
            raise
        except resources.ResourceStop as error:
            self._preserve_stop(error, "resource_limit")
            raise
        except v.V03ValidationError as error:
            self._preserve_stop(error, "verification_failed", integrity=True)
            raise
        except Exception as error:
            self._preserve_stop(error, "exception")
            raise

    def _preserve_stop(self, primary, reason, *, integrity=False):
        try:
            self._try_preserve_stop(primary, reason, integrity=integrity)
        except BaseException:
            # Even allocation or add_note failures during diagnosis must return
            # to the original exception handler, which re-raises the first stop.
            pass

    def _try_preserve_stop(self, primary, reason, *, integrity=False):
        self.last_stop = {"primary_error_type": type(primary).__name__, "reason": reason,
            "resource_reason": getattr(primary, "reason", None), "failure_recorded": False}
        try:
            self.fail(reason, integrity=integrity)
            self.last_stop["failure_recorded"] = True
        except BaseException as secondary:
            self.last_stop.update(failure_recording_error=type(secondary).__name__,
                transition_incomplete=isinstance(secondary, TransitionIncomplete))
            if isinstance(secondary, TransitionIncomplete):
                self.last_stop["intent_path"] = str(secondary)
            primary.add_note("Controller failure recording failed: " + type(secondary).__name__ + "; reconciliation required")
            # Best effort in the already committed step. Never mask the original
            # stop if this additional evidence cannot be written either.
            try:
                step = self.root / "controller" / f"{self.pins['expected_record_count']:06d}"
                rt.regular_path(step, directory=True)
                storage._exclusive(step / "failure-recording.json", storage.json_bytes(self.last_stop))
            except BaseException:
                primary.add_note("Secondary stop evidence could not be saved; Controller.last_stop retains its classification")


def recover_committed_transition(metadata_root, attempt_root, intent_path, intent_sha256):
    """Read-only recovery after journal commit; never publish an uncommitted intent."""
    root = rt.regular_path(Path(attempt_root), directory=True)
    raw = journal.read_metadata(Path(intent_path), 32 * 1024)
    rt.require(storage.sha(raw) == intent_sha256, "external controller intent hash mismatch")
    value = v.strict_json(raw)
    descriptor._same(value["format"], INTENT_FORMAT, "controller intent format")
    descriptor._same(value["attempt_root"], str(root), "controller intent root")
    record = value["record"]
    expected = root / "controller" / f"{record['sequence']:06d}" / "intent.json"
    rt.require(Path(intent_path).absolute() == expected, "controller intent location")
    receipt = journal.recover_append(Path(metadata_root), value["previous_receipt"], record)
    _, plan, records, _ = journal._load(Path(metadata_root), receipt["journal"])
    layout = descriptor.describe_layout(plan, records, **receipt["journal"])["layout"]
    descriptor._same(value["descriptor_path"], layout["descriptor_path"], "controller descriptor location")
    files.inspect_attempt(root, plan, records, value["descriptor_sha256"], **receipt["journal"])
    rt.require(journal.read_metadata(Path(intent_path), 32 * 1024) == raw, "controller intent changed")
    descriptor_pins = copy.deepcopy(value["previous_descriptor_pins"])
    prior = {str(row["sequence"]) for row in records[:-1] if row["status"] in checkpoints.VERIFIED}
    rt.require(type(descriptor_pins) is dict and set(descriptor_pins) == prior, "controller retained descriptor inventory")
    for digest in descriptor_pins.values():
        checkpoints._hex(digest, 64, "controller retained descriptor hash")
    if record["status"] in checkpoints.VERIFIED:
        descriptor_pins[str(record["sequence"])] = value["descriptor_sha256"]
    return {"receipt": receipt, "descriptor_sha256": value["descriptor_sha256"], "intent_path": str(expected),
        "intent_sha256": intent_sha256, "descriptor_pins": descriptor_pins,
        "execution_authorized": False, "campaign_evaluations_credited": 0}
