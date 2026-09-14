"""Pre-publication release/evidence faults using toy bytes and handle tables."""
import base64
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.fixtures import anomaly_v03_handle_owner as owned
from tests.fixtures import anomaly_v03_publication_model as model
from tests.fixtures import anomaly_v03_prepublication as prep
from tests import test_anomaly_v03_handle_owner as owner_tests

FILES = {"facts.json": b'{"count":2}\n', "nested/summary.txt": b"toy\n"}
MARKER = model.marker_bytes("a" * 40, FILES)
DIGEST = hashlib.sha256(MARKER).hexdigest()


class Sink:
    def __init__(self, calls):
        self.calls, self.records = calls, {}
        self.before = self.after = None
        self.result = None

    def persist_evidence(self, step, raw, digest):
        self.calls.append(("save", step))
        if self.before:
            self.before()
        if step in self.records:
            raise FileExistsError("previous_record")
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("bad_digest")
        self.records[step] = raw
        if self.after:
            self.after()
        return self.result


def setup(step="prepare"):
    journal = model.PublicationJournal(DIGEST)
    for preceding in model.STEPS[:model.STEPS.index(step)]:
        journal.begin(preceding)
        journal.succeed(preceding)
    journal.begin(step)
    entries = owner_tests.slots()
    entries = entries[:3] + (replace(entries[3], pin=replace(entries[3].pin, content_sha256=DIGEST)),)
    backend = owner_tests.ClosingTable(row.pin.handle for row in entries)
    owner = owned.HandleOwner(backend, journal=journal, slots=entries)
    sink = Sink(backend.calls)
    gate = prep.EvidenceBarrier(sink, owner=owner, protected=(0, 1, 3))
    observations = tuple(prep.Observation(row.pin, b"toy-descriptor") for row in entries)
    record = prep.build_evidence(step, source_revision="a" * 40, files=FILES,
                                 marker=MARKER, observations=observations)
    return backend, owner, journal, sink, gate, record


def rehash(record, transform):
    data = json.loads(record.raw)
    transform(data)
    raw = (json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
    return replace(record, raw=raw, sha256=hashlib.sha256(raw).hexdigest())


class EarlyReleaseTests(unittest.TestCase):
    def test_partial_release_keeps_journal_pending_and_terminal_close_skips_it(self):
        backend, owner, journal, *_ = setup()
        owner.release_before_publish("prepare", (2,))
        self.assertEqual(backend.calls, [("close", 303)])
        self.assertEqual(journal.snapshot()["steps"][0]["state"], "pending")
        self.assertEqual(journal.snapshot()["teardown"], "not_started")
        journal.stop()
        owner.finish()
        self.assertEqual(backend.calls, [("close", h) for h in (303, 404, 202, 101)])
        self.assertTrue(owner.snapshot()["all_closes_confirmed"])

    def test_parent_release_requires_all_live_children_and_releases_in_reverse_order(self):
        backend, owner, journal, *_ = setup("seal_payload")
        with self.assertRaises(owned.OwnershipError):
            owner.release_before_publish("seal_payload", (1,))
        self.assertEqual(backend.calls, [])
        with self.assertRaises(owned.OwnershipError):
            owner.finish()
        self.assertEqual(backend.live, {})
        backend, owner, journal, *_ = setup("seal_payload")
        owner.release_before_publish("seal_payload", (1, 2))
        self.assertEqual(backend.calls, [("close", 303), ("close", 202)])
        journal.stop()
        owner.finish()
        self.assertEqual(backend.calls[-2:], [("close", 404), ("close", 101)])

    def test_failed_early_close_is_never_retried_and_remaining_handles_are_released(self):
        backend, owner, journal, *_ = setup("seal_payload")
        backend.hooks[303] = owner_tests.raising(MemoryError())
        with self.assertRaises(MemoryError) as caught:
            owner.release_before_publish("seal_payload", (1, 2))
        self.assertEqual(backend.calls, [("close", 303), ("close", 202)])
        with self.assertRaises(MemoryError) as finished:
            owner.finish()
        self.assertIs(finished.exception, caught.exception)
        self.assertEqual(backend.calls, [("close", h) for h in (303, 202, 404, 101)])
        self.assertEqual(backend.live, {303: "original"})
        self.assertEqual(journal.snapshot()["teardown"], "failed")
        self.assertTrue(journal.snapshot()["resource_stop"])

    def test_selection_and_phase_errors_stop_before_close(self):
        selections = [(), [2], (True,), (-1,), (32,), (2, 2)]
        for selection in selections:
            with self.subTest(selection=selection):
                backend, owner, journal, *_ = setup()
                with self.assertRaises(owned.OwnershipError):
                    owner.release_before_publish("prepare", selection)
                self.assertEqual(backend.calls, [])
                self.assertEqual(journal.snapshot()["model_status"], "stopped")
        for step in ("rename_payload", "commit_marker", "verify_prepared", "seal_payload", None):
            with self.subTest(step=step):
                backend, owner, journal, *_ = setup()
                with self.assertRaises(owned.OwnershipError):
                    owner.release_before_publish(step, (2,))
                self.assertEqual(backend.calls, [])

    def test_phase_cannot_release_twice_and_closed_handle_cannot_be_borrowed(self):
        for action in ("repeat", "borrow"):
            with self.subTest(action=action):
                backend, owner, journal, *_ = setup()
                owner.release_before_publish("prepare", (2,))
                with self.assertRaises(owned.OwnershipError):
                    if action == "repeat":
                        owner.release_before_publish("prepare", (3,))
                    else:
                        owner.borrowed((2,), lambda pins: self.fail("closed handle escaped"))
                self.assertEqual(backend.calls, [("close", 303)])
                self.assertEqual(journal.snapshot()["model_status"], "stopped")

    def test_swallowed_finish_release_or_nested_borrow_is_blocked_during_borrow(self):
        for action in ("finish", "release", "borrow"):
            with self.subTest(action=action):
                backend, owner, journal, *_ = setup()
                def operation(pins):
                    self.assertEqual(pins[0].handle, 303)
                    try:
                        if action == "finish":
                            owner.finish()
                        elif action == "release":
                            owner.release_before_publish("prepare", (2,))
                        else:
                            owner.borrowed((3,), lambda other: None)
                    except owned.OwnershipError:
                        pass
                with self.assertRaises(owned.OwnershipError):
                    owner.borrowed((2,), operation)
                self.assertEqual(backend.calls, [])
                with self.assertRaises(owned.OwnershipError):
                    owner.finish()
                self.assertEqual(backend.live, {})

    def test_swallowed_reentry_during_release_does_not_double_close(self):
        backend, owner, journal, *_ = setup()
        def reenter():
            try:
                owner.finish()
            except owned.OwnershipError:
                pass
        backend.hooks[303] = reenter
        with self.assertRaises(owned.OwnershipError):
            owner.release_before_publish("prepare", (2,))
        with self.assertRaises(owned.OwnershipError):
            owner.finish()
        self.assertEqual(backend.calls, [("close", h) for h in (303, 404, 202, 101)])

    def test_borrowed_success_and_exception_preserve_the_callback_result_or_error(self):
        backend, owner, journal, *_ = setup()
        self.assertEqual(owner.borrowed((1, 2), lambda pins: tuple(pin.handle for pin in pins)), (202, 303))
        primary = RuntimeError("wrapped-primary")
        with self.assertRaises(RuntimeError) as caught:
            owner.borrowed((2,), lambda pins: owner_tests.raising(primary)())
        self.assertIs(caught.exception, primary)

    def test_explicit_primary_at_finish_wins_over_earlier_release_failure(self):
        backend, owner, journal, *_ = setup()
        backend.hooks[303] = owner_tests.raising(MemoryError())
        with self.assertRaises(MemoryError):
            owner.release_before_publish("prepare", (2,))
        primary = ValueError("caller-primary")
        with self.assertRaises(ValueError) as caught:
            owner.finish(primary=primary)
        self.assertIs(caught.exception, primary)
        self.assertTrue(journal.snapshot()["resource_stop"])


class EvidenceBarrierTests(unittest.TestCase):
    def test_saved_record_roundtrips_exact_marker_payload_and_bounded_descriptors(self):
        backend, owner, journal, sink, gate, record = setup()
        gate.save_and_release(record, (2,))
        data = json.loads(sink.records["prepare"])
        self.assertEqual(base64.b64decode(data["marker_b64"]), MARKER)
        self.assertEqual({row["path"]: base64.b64decode(row["bytes_b64"]) for row in data["files"]}, FILES)
        self.assertEqual(data["observations"][0]["descriptor_b64"], base64.b64encode(b"toy-descriptor").decode())
        self.assertIs(data["formal_permission"], False)
        self.assertIs(data["native_observations_authenticated"], False)
        self.assertNotIn('"handle"', record.raw.decode())
        self.assertEqual(backend.calls, [("save", "prepare"), ("close", 303)])
        self.assertEqual(gate.snapshot()["steps"][0]["state"], "released")
        self.assertEqual(journal.snapshot()["teardown"], "not_started")

    def test_each_permitted_pending_phase_has_its_own_evidence_name(self):
        for step in owned.RELEASE_STEPS:
            with self.subTest(step=step):
                backend, owner, journal, sink, gate, record = setup(step)
                gate.save_and_release(record, (2,))
                self.assertEqual(set(sink.records), {step})
                self.assertEqual(backend.calls, [("save", step), ("close", 303)])

    def test_record_inputs_and_limits_fail_before_sink(self):
        backend, owner, journal, sink, gate, record = setup()
        observation = prep.Observation(owner._slots[0].pin, b"x")
        for observations in ((), [observation], (observation,) * 33,
                             (replace(observation, descriptor=b""),),
                             (replace(observation, descriptor=b"x" * 2049),),
                             (observation, observation)):
            with self.subTest(observations=type(observations).__name__), self.assertRaises(ValueError):
                prep.build_evidence("prepare", source_revision="a" * 40, files=FILES, marker=MARKER, observations=observations)
        for files in ({"../bad": b"x"}, {"a": b"x" * (64 * 1024 + 1)}):
            with self.assertRaises(ValueError):
                prep.build_evidence("prepare", source_revision="a" * 40, files=files, marker=MARKER, observations=(observation,))
        self.assertEqual(backend.calls, [])

    def test_maximum_toy_payload_and_descriptors_fit_record_cap(self):
        files = {f"p{index}.bin": bytes([index]) * (64 * 1024) for index in range(4)}
        observations = tuple(prep.Observation(
            replace(owner_tests.slots()[0].pin, handle=1000 + index, file_id=(index + 1).to_bytes(16, "little")),
            b"s" * 2048) for index in range(32))
        record = prep.build_evidence("prepare", source_revision="a" * 40, files=files,
                                     marker=model.marker_bytes("a" * 40, files), observations=observations)
        self.assertLessEqual(len(record.raw), 512 * 1024)
        self.assertGreater(len(record.raw), 400 * 1024)

    def test_rehashed_tampering_and_marker_or_owner_substitution_are_rejected(self):
        edits = [
            lambda data: data.update(formal_permission=True),
            lambda data: data.update(step="verify_final"),
            lambda data: data.update(extra="field"),
            lambda data: data["files"].append(data["files"][0]),
            lambda data: data["files"][0].update(bytes_b64=base64.b64encode(b"changed").decode()),
            lambda data: data["observations"][0].update(volume=8),
            lambda data: data["observations"][0].update(file_id="11" * 16),
            lambda data: data["observations"][0].update(content_sha256="c" * 64),
            lambda data: data["observations"].pop(),
        ]
        for edit in edits:
            with self.subTest(edit=edits.index(edit)):
                backend, owner, journal, sink, gate, record = setup()
                with self.assertRaises(ValueError):
                    gate.save_and_release(rehash(record, edit), (2,))
                self.assertEqual(backend.calls, [])
                self.assertTrue(gate.snapshot()["stopped"])
        backend, owner, journal, sink, gate, record = setup()
        changed = prep.build_evidence("prepare", source_revision="b" * 40, files=FILES,
            marker=model.marker_bytes("b" * 40, FILES),
            observations=tuple(prep.Observation(row.pin, b"x") for row in owner._slots))
        with self.assertRaises(ValueError):
            gate.save_and_release(changed, (2,))
        self.assertEqual(backend.calls, [])

    def test_protected_handle_wrong_phase_and_budget_are_rejected_before_save(self):
        for kind in ("protected", "phase", "record_cap", "attempt_cap"):
            with self.subTest(kind=kind):
                backend, owner, journal, sink, gate, record = setup()
                indices = (3,) if kind == "protected" else (2,)
                if kind == "phase":
                    record = replace(record, step="seal_payload")
                if kind == "record_cap":
                    record = replace(record, raw=b"x" * (512 * 1024 + 1))
                context = patch.object(prep, "MAX_ATTEMPT_BYTES", len(record.raw) - 1) if kind == "attempt_cap" else patch.object(prep, "MAX_ATTEMPT_BYTES", prep.MAX_ATTEMPT_BYTES)
                with context, self.assertRaises(ValueError):
                    gate.save_and_release(record, indices)
                self.assertEqual(backend.calls, [])

    def test_sink_failure_and_lost_save_reply_keep_handles_owned_until_terminal_release(self):
        for after in (False, True):
            with self.subTest(after=after):
                backend, owner, journal, sink, gate, record = setup()
                error = MemoryError()
                if after:
                    sink.after = owner_tests.raising(error)
                else:
                    sink.before = owner_tests.raising(error)
                with self.assertRaises(MemoryError) as caught:
                    gate.save_and_release(record, (2,))
                self.assertIs(caught.exception, error)
                self.assertEqual(backend.calls, [("save", "prepare")])
                self.assertEqual(gate.snapshot()["steps"][0]["state"], "unknown")
                self.assertEqual(gate.snapshot()["reserved_bytes"], len(record.raw))
                self.assertEqual("prepare" in sink.records, after)
                with self.assertRaises(ValueError):
                    gate.save_and_release(record, (2,))
                self.assertEqual(backend.calls, [("save", "prepare")])
                with self.assertRaises(MemoryError):
                    owner.finish()
                self.assertEqual(backend.live, {})

    def test_bad_acknowledgement_existing_record_and_swallowed_reentry_do_not_release(self):
        for kind in ("bad_ack", "existing", "gate_reentry", "owner_finish"):
            with self.subTest(kind=kind):
                backend, owner, journal, sink, gate, record = setup()
                if kind == "bad_ack":
                    sink.result = True
                elif kind == "existing":
                    sink.records["prepare"] = b"old"
                else:
                    def reenter():
                        try:
                            gate.save_and_release(record, (2,)) if kind == "gate_reentry" else owner.finish()
                        except ValueError:
                            pass
                    sink.before = reenter
                with self.assertRaises(ValueError if kind != "existing" else FileExistsError):
                    gate.save_and_release(record, (2,))
                self.assertEqual(backend.calls, [("save", "prepare")])
                self.assertEqual(len(backend.live), 4)
                if kind == "existing":
                    self.assertEqual(sink.records["prepare"], b"old")

    def test_close_failure_keeps_saved_bytes_and_blocks_all_later_operations(self):
        backend, owner, journal, sink, gate, record = setup()
        backend.hooks[303] = owner_tests.raising(MemoryError())
        with self.assertRaises(MemoryError):
            gate.save_and_release(record, (2,))
        self.assertEqual(sink.records["prepare"], record.raw)
        self.assertEqual(gate.snapshot()["steps"][0]["state"], "saved")
        with self.assertRaises(ValueError):
            owner.borrowed((1, 3), lambda pins: self.fail("publication resumed"))
        with self.assertRaises(MemoryError):
            owner.finish()
        self.assertEqual(backend.calls, [("save", "prepare")] + [("close", h) for h in (303, 404, 202, 101)])
        self.assertFalse(journal.snapshot()["formal_permission"])

    def test_one_owner_and_barrier_run_all_phases_through_both_rename_operations(self):
        from tests import test_anomaly_v03_rename_adapter as rename_tests
        from tests.fixtures import anomaly_v03_rename_adapter as rename
        backend = rename_tests.TableBackend("commit_marker")
        parent = rename_tests.PARENT
        marker = replace(backend.source, content_sha256=DIGEST)
        stage = rename.ObjectPin(707, parent.volume, b"D" * 16, True)
        children = tuple(rename.ObjectPin(800 + index, parent.volume, bytes([index + 1]) * 16,
                                         False, hashlib.sha256(b"toy").hexdigest()) for index in range(3))
        entries = (owned.OwnedSlot(parent, None), owned.OwnedSlot(stage, 0),
                   *(owned.OwnedSlot(pin, 1) for pin in children), owned.OwnedSlot(marker, 0))
        backend.objects[marker.file_id]["raw"] = MARKER
        backend.handles[stage.handle] = stage.file_id
        backend.objects[stage.file_id] = {"volume": parent.volume, "directory": True, "raw": None}
        backend.names[(parent.file_id, "stage")] = stage.file_id
        backend.handles.update({pin.handle: pin.file_id for pin in children})
        close_calls = []
        def close_handle(handle):
            close_calls.append(handle)
            del backend.handles[handle]
            return 1
        backend.close_handle = close_handle
        journal = model.PublicationJournal(DIGEST)
        owner = owned.HandleOwner(backend, journal=journal, slots=entries)
        sink = Sink(backend.calls)
        gate = prep.EvidenceBarrier(sink, owner=owner, protected=(0, 1, 5))
        observations = tuple(prep.Observation(row.pin, b"toy-descriptor") for row in entries)
        groups = dict(zip(owned.RELEASE_STEPS, (2, 3, 4)))
        for step in model.STEPS:
            if step in ("rename_payload", "commit_marker"):
                backend.step = step
                index = 1 if step == "rename_payload" else 5
                operation = rename.BoundRename(backend, step=step, parent=parent, source=entries[index].pin)
                owner.borrowed((0, index), lambda pins: operation.run(journal))
            else:
                journal.begin(step)
                if step in groups:
                    record = prep.build_evidence(step, source_revision="a" * 40, files=FILES,
                                                 marker=MARKER, observations=observations)
                    gate.save_and_release(record, (groups[step],))
                journal.succeed(step)
        self.assertEqual(journal.snapshot()["model_status"], "awaiting_teardown")
        owner.finish()
        self.assertEqual(journal.snapshot()["model_status"], "complete")
        self.assertEqual(backend.handles, {})
        self.assertEqual(close_calls, [pin.handle for pin in children] + [marker.handle, stage.handle, parent.handle])
        self.assertEqual(backend.names[(parent.file_id, "payload")], stage.file_id)
        self.assertEqual(backend.names[(parent.file_id, ".complete")], marker.file_id)
        self.assertEqual(set(sink.records), set(owned.RELEASE_STEPS))
        self.assertEqual([row["state"] for row in gate.snapshot()["steps"]], ["released"] * 3)
        self.assertEqual(gate.snapshot()["reserved_bytes"], sum(map(len, sink.records.values())))
        self.assertFalse(journal.snapshot()["formal_permission"])

    def test_exclusive_local_sink_retains_evidence_after_handles_are_released(self):
        # A real tiny temporary-file roundtrip, not a native private-DACL sink.
        backend, owner, journal, sink, gate, record = setup()
        with tempfile.TemporaryDirectory(prefix="banto-b2-evidence-") as directory:
            target = Path(directory) / "prepare.json"
            def persist(step, raw, digest):
                with target.open("xb") as stream:
                    stream.write(raw)
                self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), digest)
            sink.persist_evidence = persist
            gate.save_and_release(record, (2,))
            self.assertEqual(target.read_bytes(), record.raw)
            with self.assertRaises(FileExistsError):
                persist("prepare", record.raw, record.sha256)
            self.assertEqual(target.read_bytes(), record.raw)
            journal.stop()
            owner.finish()
            self.assertEqual(target.read_bytes(), record.raw)


if __name__ == "__main__":
    unittest.main()
