"""Independent in-memory handle/name tables; no Windows DLL or disk mutation."""
from dataclasses import replace
import hashlib
import unittest
from unittest.mock import patch

from tests.fixtures import anomaly_v03_publication_model as model
from tests.fixtures import anomaly_v03_rename_adapter as adapter


MARKER = model.marker_bytes("a" * 40, {"a.json": b"{}\n", "dir/b.bin": b"toy"})
DIGEST = hashlib.sha256(MARKER).hexdigest()
PARENT = adapter.ObjectPin(0x101, 7, b"P" * 16, True)
LEAVES = {"rename_payload": ("stage", "payload"), "commit_marker": ("marker-pending.json", ".complete")}


def source_pin(step):
    return adapter.ObjectPin(0x202, 7, b"S" * 16, step == "rename_payload",
                             None if step == "rename_payload" else DIGEST)


def journal_for(step):
    journal = model.PublicationJournal(DIGEST)
    for preceding in model.STEPS[:model.STEPS.index(step)]:
        journal.begin(preceding)
        journal.succeed(preceding)
    return journal


class TableBackend:
    """Separate simulator, decoding bytes without the adapter's packing helper.

    It deliberately omits Windows sharing/DACL/ancestor/stream semantics.
    Passing these tests establishes only the injected backend protocol.
    """

    def __init__(self, step):
        self.step, self.source = step, source_pin(step)
        self.handles = {PARENT.handle: PARENT.file_id, self.source.handle: self.source.file_id}
        self.objects = {
            PARENT.file_id: {"volume": 7, "directory": True, "raw": None},
            self.source.file_id: {"volume": 7, "directory": self.source.directory,
                                 "raw": None if self.source.directory else MARKER},
        }
        self.names = {(PARENT.file_id, LEAVES[step][0]): self.source.file_id}
        self.calls, self.hooks = [], {}
        self.error = 0
        self.forced_result = None

    def enter(self, name):
        self.calls.append(name)
        if name in self.hooks:
            self.hooks[name]()

    def check_pin(self, pin):
        if self.handles.get(pin.handle) != pin.file_id:
            raise ValueError("identity_changed")
        obj = self.objects[pin.file_id]
        if obj["volume"] != pin.volume or obj["directory"] is not pin.directory:
            raise ValueError("object_changed")
        if not pin.directory and hashlib.sha256(obj["raw"]).hexdigest() != pin.content_sha256:
            raise ValueError("bytes_changed")

    def recheck_parent(self, pin):
        self.enter("parent")
        self.check_pin(pin)

    def recheck_source(self, pin, parent, leaf):
        self.enter("source")
        self.check_pin(pin)
        if self.names.get((parent.file_id, leaf)) != pin.file_id:
            raise ValueError("name_changed")

    def set_file_information_by_handle(self, handle, info_class, raw):
        self.enter("api")
        # Independent offset decoder and fixed wire expectations.
        assert info_class == 3 and raw[:8] == b"\0" * 8
        parent_handle = int.from_bytes(raw[8:16], "little")
        count = int.from_bytes(raw[16:20], "little")
        assert count % 2 == 0 and len(raw) == 22 + count and raw[-2:] == b"\0\0"
        leaf = raw[20:20 + count].decode("utf-16-le")
        assert leaf == LEAVES[self.step][1]
        if self.forced_result is not None:
            return self.forced_result
        parent_id, object_id = self.handles[parent_handle], self.handles[handle]
        target = (parent_id, leaf)
        if target in self.names:
            self.error = 183
            return 0
        # Object identity comes from the held source handle, not the old leaf.
        previous = [key for key, value in self.names.items() if value == object_id]
        assert len(previous) == 1
        del self.names[previous[0]]
        self.names[target] = object_id
        if "after_effect" in self.hooks:
            self.hooks["after_effect"]()
        return 1

    def get_last_error(self):
        self.enter("error")
        return self.error


def setup(step="commit_marker"):
    backend = TableBackend(step)
    operation = adapter.BoundRename(backend, step=step, parent=PARENT, source=backend.source)
    return backend, operation, journal_for(step)


def raising(error):
    def fail():
        raise error
    return fail


class RenameAdapterTests(unittest.TestCase):
    def assert_stopped(self, journal, *, resource=False, commit="unknown"):
        state = journal.snapshot()
        self.assertEqual(state["model_status"], "stopped")
        self.assertEqual(state["resource_stop"], resource)
        self.assertEqual(state["commit_observation"], commit)
        for key in ("retry_permitted", "cleanup_permitted", "formal_permission", "execution_authenticated"):
            self.assertIs(state[key], False)
        self.assertEqual(state["acceptance_status"], "not_completed")

    def test_fixed_win64_wire_layout(self):
        for step, count, total in (("rename_payload", 14, 36), ("commit_marker", 18, 40)):
            with self.subTest(step=step):
                raw = adapter.rename_request(0x0102030405060708, step)
                self.assertEqual(raw[:8], b"\0" * 8)
                self.assertEqual(raw[8:16], bytes((8, 7, 6, 5, 4, 3, 2, 1)))
                self.assertEqual(raw[16:20], bytes((count, 0, 0, 0)))
                self.assertEqual(raw[20:-2].decode("utf-16-le"), LEAVES[step][1])
                self.assertEqual(raw[-2:], b"\0\0")
                self.assertEqual(len(raw), total)

    def test_invalid_binding_has_no_backend_calls(self):
        invalid_handles = (True, False, 0, -1, 1 << 64, (1 << 64) - 1, (1 << 64) - 16, "257")
        for value in invalid_handles:
            with self.subTest(handle=value), self.assertRaises(adapter.AdapterError):
                adapter.rename_request(value, "commit_marker")
        for step in ("../payload", "prepare", "", None, True):
            with self.subTest(step=step), self.assertRaises(adapter.AdapterError):
                adapter.rename_request(PARENT.handle, step)
        backend = TableBackend("commit_marker")
        invalid_sources = [
            replace(backend.source, handle=True), replace(backend.source, handle=PARENT.handle),
            replace(backend.source, file_id=PARENT.file_id), replace(backend.source, file_id=b"\0" * 16),
            replace(backend.source, file_id=bytearray(b"S" * 16)), replace(backend.source, file_id=b"x"),
            replace(backend.source, volume=8), replace(backend.source, volume=True),
            replace(backend.source, directory=True), replace(backend.source, directory=0),
            replace(backend.source, content_sha256=None), replace(backend.source, content_sha256="A" * 64),
        ]
        for source in invalid_sources:
            with self.subTest(source=source), self.assertRaises(adapter.AdapterError):
                adapter.BoundRename(backend, step="commit_marker", parent=PARENT, source=source)
        for parent in (None, replace(PARENT, directory=False, content_sha256=DIGEST),
                       replace(PARENT, content_sha256=DIGEST), replace(PARENT, volume=0)):
            with self.subTest(parent=parent), self.assertRaises(adapter.AdapterError):
                adapter.BoundRename(backend, step="commit_marker", parent=parent, source=backend.source)
        self.assertEqual(backend.calls, [])

    def test_both_successes_preserve_identity_and_borrowed_handles(self):
        for step in LEAVES:
            with self.subTest(step=step):
                backend, operation, journal = setup(step)
                handles_before = backend.handles.copy()
                operation.run(journal)
                self.assertEqual(backend.names, {(PARENT.file_id, LEAVES[step][1]): backend.source.file_id})
                self.assertEqual(backend.handles, handles_before)
                self.assertEqual(backend.calls, ["parent", "source", "api"])
                state = journal.snapshot()
                self.assertEqual(state["steps"][model.STEPS.index(step)]["state"], "succeeded")
                self.assertEqual(state["commit_observation"], "confirmed" if step == "commit_marker" else "not_started")
                if step == "commit_marker":
                    self.assertEqual(backend.objects[backend.source.file_id]["raw"], MARKER)
                    self.assertEqual(state["model_status"], "awaiting_teardown")
                    journal.finish_teardown(success=True)
                    self.assertEqual(journal.snapshot()["model_status"], "complete")
                self.assertIs(state["formal_permission"], False)

    def test_competing_destination_is_never_replaced(self):
        for step in LEAVES:
            with self.subTest(step=step):
                backend, operation, journal = setup(step)
                target = (PARENT.file_id, LEAVES[step][1])
                backend.hooks["api"] = lambda: backend.names.update({target: b"X" * 16})
                with self.assertRaises(adapter.AdapterError) as caught:
                    operation.run(journal)
                self.assertEqual(caught.exception.winerror, 183)
                self.assertEqual(backend.names[target], b"X" * 16)
                self.assertEqual(backend.names[(PARENT.file_id, LEAVES[step][0])], backend.source.file_id)
                self.assertEqual(backend.calls, ["parent", "source", "api", "error"])
                self.assert_stopped(journal, commit="unknown" if step == "commit_marker" else "not_started")
                with self.assertRaises(adapter.AdapterError):
                    operation.run(journal)
                self.assertEqual(backend.calls, ["parent", "source", "api", "error"])

    def test_source_handle_selects_original_object_after_name_race(self):
        backend, operation, journal = setup()
        old = (PARENT.file_id, "marker-pending.json")
        def swap_name():
            backend.names[(PARENT.file_id, "relocated")] = backend.names[old]
            backend.names[old] = b"X" * 16
        backend.hooks["api"] = swap_name
        operation.run(journal)
        self.assertEqual(backend.names[old], b"X" * 16)
        self.assertEqual(backend.names[(PARENT.file_id, ".complete")], backend.source.file_id)
        self.assertNotIn((PARENT.file_id, "relocated"), backend.names)

    def test_identity_kind_volume_name_and_bytes_drift_stop_before_api(self):
        for drift in ("parent_handle", "source_handle", "source_kind", "source_volume", "name", "bytes"):
            with self.subTest(drift=drift):
                backend, operation, journal = setup()
                if drift == "parent_handle":
                    backend.handles[PARENT.handle] = b"X" * 16
                elif drift == "source_handle":
                    backend.handles[backend.source.handle] = b"X" * 16
                elif drift == "source_kind":
                    backend.objects[backend.source.file_id]["directory"] = True
                elif drift == "source_volume":
                    backend.objects[backend.source.file_id]["volume"] = 8
                elif drift == "name":
                    backend.names[(PARENT.file_id, "marker-pending.json")] = b"X" * 16
                else:
                    backend.objects[backend.source.file_id]["raw"] = b"changed"
                with self.assertRaises(ValueError):
                    operation.run(journal)
                self.assertNotIn("api", backend.calls)
                self.assert_stopped(journal)

    def test_marker_digest_mismatch_stops_before_checks(self):
        backend, operation, journal = setup()
        journal = model.PublicationJournal("b" * 64)
        for step in model.STEPS[:-1]:
            journal.begin(step)
            journal.succeed(step)
        with self.assertRaises(adapter.AdapterError) as caught:
            operation.run(journal)
        self.assertEqual(caught.exception.reason, "marker_pin_mismatch")
        self.assertEqual(backend.calls, [])
        self.assert_stopped(journal)

    def test_bad_check_return_does_not_reach_api(self):
        for method in ("recheck_parent", "recheck_source"):
            for result in (True, False, 0, "ok"):
                with self.subTest(method=method, result=result):
                    backend, operation, journal = setup()
                    with patch.object(backend, method, return_value=result):
                        with self.assertRaises(adapter.AdapterError):
                            operation.run(journal)
                    self.assertNotIn("api", backend.calls)
                    self.assert_stopped(journal)

    def test_journal_protocol_and_single_use(self):
        for kind in ("wrong_type", "out_of_order", "stopped"):
            with self.subTest(kind=kind):
                backend, operation, journal = setup()
                if kind == "wrong_type":
                    journal = object()
                elif kind == "out_of_order":
                    journal = model.PublicationJournal(DIGEST)
                else:
                    journal.stop()
                with self.assertRaises((adapter.AdapterError, model.ModelError)):
                    operation.run(journal)
                self.assertEqual(backend.calls, [])
        backend, operation, journal = setup()
        operation.run(journal)
        fresh = journal_for("commit_marker")
        with self.assertRaises(adapter.AdapterError):
            operation.run(fresh)
        self.assert_stopped(fresh, commit="not_started")
        self.assertEqual(backend.calls, ["parent", "source", "api"])

    def test_swallowed_stop_or_reentrant_attempt_blocks_next_backend_call(self):
        for boundary in ("parent", "source"):
            for kind in ("stop", "reenter"):
                with self.subTest(boundary=boundary, kind=kind):
                    backend, operation, journal = setup()
                    def interrupt():
                        if kind == "stop":
                            journal.stop(resource=True)
                        else:
                            try:
                                operation.run(journal)
                            except adapter.AdapterError:
                                pass
                    backend.hooks[boundary] = interrupt
                    with self.assertRaises(adapter.AdapterError):
                        operation.run(journal)
                    self.assertEqual(backend.calls, ["parent"] if boundary == "parent" else ["parent", "source"])
                    self.assert_stopped(journal, resource=kind == "stop")

    def test_raw_bool_and_error_shapes_fail_closed(self):
        for result in (True, False, "1", 1 << 31, -(1 << 31) - 1):
            with self.subTest(result=result):
                backend, operation, journal = setup()
                backend.forced_result = result
                with self.assertRaises(adapter.AdapterError):
                    operation.run(journal)
                self.assertEqual(backend.calls, ["parent", "source", "api"])
                self.assert_stopped(journal)
        for error in (0, True, "5", -1, 1 << 32):
            with self.subTest(error=error):
                backend, operation, journal = setup()
                backend.forced_result, backend.error = 0, error
                with self.assertRaises(adapter.AdapterError):
                    operation.run(journal)
                self.assertEqual(backend.calls, ["parent", "source", "api", "error"])
                self.assert_stopped(journal)
        backend, operation, journal = setup()
        backend.forced_result = -1  # Raw signed Win32 BOOL: every nonzero value succeeds.
        operation.run(journal)
        self.assertEqual(journal.snapshot()["commit_observation"], "confirmed")

    def test_native_resource_error_codes_and_ordinary_denials(self):
        for code in (8, 14, 39, 112, 1450, 1451, 1452, 1453, 1454, 1455, 1816, 5, 183):
            with self.subTest(code=code):
                backend, operation, journal = setup()
                backend.forced_result, backend.error = 0, code
                with self.assertRaises(adapter.AdapterError) as caught:
                    operation.run(journal)
                self.assertEqual(caught.exception.winerror, code)
                self.assert_stopped(journal, resource=code not in (5, 183))
                self.assertEqual(backend.calls, ["parent", "source", "api", "error"])

    def test_resource_causes_context_groups_and_cycles(self):
        disk = OSError("simulated")
        disk.winerror = 112
        cause, context = RuntimeError("outer"), RuntimeError("outer")
        cause.__cause__, context.__context__ = disk, adapter.BudgetStop()
        cycle = ValueError("cycle")
        cycle.__cause__ = cycle
        errors = [(MemoryError(), True), (disk, True), (cause, True), (context, True),
                  (ExceptionGroup("group", [ValueError(), disk]), True), (cycle, False),
                  (OSError("ordinary"), False)]
        for error, resource in errors:
            with self.subTest(error=type(error).__name__, resource=resource):
                backend, operation, journal = setup()
                backend.hooks["source"] = raising(error)
                with self.assertRaises(type(error)) as caught:
                    operation.run(journal)
                self.assertIs(caught.exception, error)
                self.assert_stopped(journal, resource=resource)
                self.assertEqual(backend.calls, ["parent", "source"])

    def test_resource_graph_budget_is_conservative(self):
        chain = ValueError()
        for _ in range(65):
            outer = ValueError()
            outer.__cause__, chain = chain, outer
        for error in (chain, ExceptionGroup("wide", [ValueError() for _ in range(65)])):
            backend, operation, journal = setup()
            backend.hooks["parent"] = raising(error)
            with self.assertRaises(type(error)):
                operation.run(journal)
            self.assert_stopped(journal, resource=True)
            self.assertEqual(backend.calls, ["parent"])

    def test_every_backend_exception_stops_without_followup(self):
        for boundary in ("parent", "source", "api", "error"):
            for error in (ValueError("private/path"), MemoryError(), KeyboardInterrupt()):
                with self.subTest(boundary=boundary, error=type(error).__name__):
                    backend, operation, journal = setup()
                    backend.hooks[boundary] = raising(error)
                    if boundary == "error":
                        backend.forced_result, backend.error = 0, 5
                    with self.assertRaises(type(error)) as caught:
                        operation.run(journal)
                    self.assertIs(caught.exception, error)
                    expected = ["parent", "source", "api", "error"]
                    self.assertEqual(backend.calls, expected[:expected.index(boundary) + 1])
                    self.assert_stopped(journal, resource=isinstance(error, MemoryError))
                    self.assertNotIn("private/path", str(journal.snapshot()))

    def test_lost_acknowledgement_remains_unknown_without_readback_or_retry(self):
        backend, operation, journal = setup()
        backend.hooks["after_effect"] = raising(MemoryError())
        with self.assertRaises(MemoryError):
            operation.run(journal)
        self.assertEqual(backend.names[(PARENT.file_id, ".complete")], backend.source.file_id)
        self.assert_stopped(journal, resource=True)
        self.assertEqual(backend.calls, ["parent", "source", "api"])
        with self.assertRaises(adapter.AdapterError):
            operation.run(journal)
        self.assertEqual(backend.calls, ["parent", "source", "api"])

    def test_journal_acknowledgement_failure_before_and_after_update(self):
        original = model.PublicationJournal.succeed
        for after in (False, True):
            with self.subTest(after=after):
                backend, operation, journal = setup()
                def fail_ack(current, step):
                    if after:
                        original(current, step)
                    raise MemoryError()
                with patch.object(model.PublicationJournal, "succeed", fail_ack):
                    with self.assertRaises(MemoryError):
                        operation.run(journal)
                self.assert_stopped(journal, resource=True, commit="confirmed" if after else "unknown")
                self.assertEqual(backend.names[(PARENT.file_id, ".complete")], backend.source.file_id)
                self.assertEqual(backend.calls, ["parent", "source", "api"])

    def test_teardown_failure_preserves_commit_and_first_failure(self):
        backend, operation, journal = setup()
        operation.run(journal)
        journal.finish_teardown(success=False)
        journal.stop(resource=True)
        self.assert_stopped(journal, resource=True, commit="confirmed")
        self.assertEqual(journal.snapshot()["failure_reason"], "teardown_error")
        self.assertEqual(backend.calls, ["parent", "source", "api"])


if __name__ == "__main__":
    unittest.main()
