"""Replacement intent/snapshot evidence; pure faults plus one small native test."""

from contextlib import ExitStack
from copy import deepcopy
import ctypes
import json
import os
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from banto_ai import _anomaly_v03_windows as w
from tests.test_anomaly_v03_windows import parent_profile, restricted_profile, _prefix_inventory


class ReplacementModel:
    def __init__(self):
        self.root, self.nonce = Path("owned"), "1" * 32
        self.api, self.events, self.stopped = Mock(), [], False
        self.raw = bytearray()
        self.fault = lambda stage: None
        self.sd = {"owner": "DUMMY_PRIVATE_OWNER", "aces": ["DUMMY_PRIVATE_SD"]}
        self.source = self.snapshot_value("a" * 32, b"B1-control\n")
        self.state = {"control/data.bin": deepcopy(self.source)}
        self.ledger = {"control/data.bin": self.row(self.source)}
        self.trace = w._ReplaceTrace(self.nonce, self.sink)
        self.api.call.side_effect = lambda ok, reason: w._need(ok, reason)
        self.api.k.MoveFileExW.side_effect = lambda *args: self.move(False)
        self.api.k.MoveFileW.side_effect = lambda *args: self.move(True)

    def snapshot_value(self, identity, content):
        return {"identity": {"file_id": identity, "volume": 1, "directory": False, "links": 1, "attributes": 32},
                "security": deepcopy(self.sd), "content_hex": content.hex(), "bytes": len(content), "sha256": w._sha(content)}

    def row(self, snapshot):
        return {"identity": deepcopy(snapshot["identity"]), "sd": deepcopy(snapshot["security"]),
                "bytes": snapshot["bytes"], "sha256": snapshot["sha256"]}

    def event(self, stage):
        if self.stopped:
            raise AssertionError("IO after injected failure")
        self.events.append(stage)
        self.fault(stage)

    def sink(self, raw):
        stage = json.loads(raw)["stage"]
        self.event("write_" + stage)
        self.raw.extend(raw)
        self.event("flushed_" + stage)

    def snapshot(self, api, path):
        self.event("snapshot")
        return deepcopy(self.state[path.relative_to(self.root).as_posix()])

    def lstat(self, path):
        self.event("absence")
        if path.relative_to(self.root).as_posix() not in self.state:
            error = FileNotFoundError()
            error.winerror = 2
            raise error
        return object()

    def create(self, owned, name, content, mode):
        self.event("before_create")
        self.state[name] = self.snapshot_value("b" * 32, content)
        owned.ledger[name] = self.row(self.state[name])
        self.event("after_create")

    def move(self, restore):
        self.event("before_restore" if restore else "before_replace")
        source, target = ("control/replaced.bin", "control/data.bin") if restore else ("control/data.bin", "control/replaced.bin")
        self.state[target] = self.state.pop(source)
        self.event("after_restore" if restore else "after_replace")
        return True

    def patched(self):
        stack = ExitStack()
        stack.enter_context(patch.object(w, "_replace_snapshot", side_effect=self.snapshot))
        stack.enter_context(patch.object(w._Fixture, "file", lambda owned, *args: self.create(owned, *args)))
        stack.enter_context(patch.object(Path, "lstat", autospec=True, side_effect=self.lstat))
        stack.enter_context(patch.object(Path, "exists", side_effect=AssertionError))
        return stack

    def run(self):
        with self.patched():
            return w._replace_control(self.api, self.root, "user", self.ledger, self.trace)

    def validate(self, *, complete=False):
        return w._validate_replace_trace(bytes(self.raw), self.row(self.source), self.nonce, complete=complete)


class ReplacementTraceTests(unittest.TestCase):
    def test_success_preserves_consumed_destination_and_original_identity(self):
        model = ReplacementModel()
        trace = model.run()
        self.assertEqual(model.validate(complete=True)["status"], "complete")
        rows = [json.loads(line) for line in trace.raw().splitlines()]
        self.assertEqual(rows[0]["details"]["source"], model.source)
        self.assertEqual(bytes.fromhex(rows[1]["details"]["target"]["content_hex"]), b"B1-replace-destination\n")
        self.assertEqual(model.state, {"control/data.bin": model.source})
        self.assertEqual(set(model.ledger), {"control/data.bin"})
        self.assertLess(model.events.index("flushed_replace_pending"), model.events.index("before_replace"))
        self.assertLess(model.events.index("flushed_restore_pending"), model.events.index("before_restore"))
        self.assertNotIn("DUMMY", repr(trace) + json.dumps(model.validate()))

    def test_failure_after_each_mutation_keeps_intent_and_never_performs_repair(self):
        for stage, count in (("after_create", 1), ("after_replace", 3), ("after_restore", 5)):
            model = ReplacementModel()
            primary = w._Failure("mutation_api", 5)
            def fault(current):
                if current == stage:
                    model.stopped = True
                    raise primary
            model.fault = fault
            with self.subTest(stage=stage), self.assertRaises(w._Failure) as caught:
                model.run()
            self.assertIs(caught.exception, primary)
            self.assertIs(primary.private_replace_evidence, model.trace)
            self.assertEqual(model.validate()["confirmed_records"], count)
            self.assertEqual(model.validate()["status"], "incomplete")
            self.assertIn("control/replaced.bin", model.ledger)
            self.assertEqual(model.events[-1], stage)

    def test_resource_failure_does_not_serialize_or_write_in_handler(self):
        model = ReplacementModel()
        primary = MemoryError()
        def fault(stage):
            if stage == "after_replace":
                model.stopped = True
                raise primary
        model.fault = fault
        with patch.object(model.trace, "raw", side_effect=AssertionError), self.assertRaises(MemoryError) as caught:
            model.run()
        self.assertIs(caught.exception, primary)
        self.assertTrue(model.trace.failed)
        self.assertEqual(model.validate()["last_stage"], "replace_pending")
        self.assertNotIn("control/data.bin", model.state)

    def test_record_write_failure_prevents_the_next_operation(self):
        for stage, forbidden in (("write_create_pending", "before_create"),
                                 ("write_replace_pending", "before_replace"),
                                 ("write_restore_pending", "before_restore")):
            model = ReplacementModel()
            def fault(current):
                if current == stage:
                    model.stopped = True
                    raise OSError("DUMMY_PRIVATE_WRITE")
            model.fault = fault
            with self.subTest(stage=stage), self.assertRaises(OSError):
                model.run()
            self.assertNotIn(forbidden, model.events)
            self.assertIsNotNone(model.trace.pending_record)

    def test_full_intent_record_with_flush_failure_still_does_not_imply_operation_ran(self):
        model = ReplacementModel()
        def fault(stage):
            if stage == "flushed_replace_pending":
                model.stopped = True
                raise OSError("DUMMY_PRIVATE_FLUSH")
        model.fault = fault
        with self.assertRaises(OSError):
            model.run()
        self.assertEqual(model.validate()["last_stage"], "replace_pending")
        self.assertEqual(model.validate()["source_state"], "uncertain")
        self.assertEqual(model.validate()["original_destination_state"], "uncertain")
        self.assertEqual(set(model.state), {"control/data.bin", "control/replaced.bin"})
        self.assertNotIn("before_replace", model.events)

    def test_confirmed_prefix_distinguishes_consumed_target_from_uncertain_source_location(self):
        model = ReplacementModel()
        model.run()
        lines = bytes(model.raw).splitlines(keepends=True)
        for count, location, target in ((2, "at_original", "captured_present"), (3, "uncertain", "uncertain"),
                                        (4, "at_destination", "consumed"), (5, "uncertain", "consumed"),
                                        (6, "at_original", "consumed")):
            report = w._validate_replace_trace(b"".join(lines[:count]), model.row(model.source), model.nonce, complete=False)
            self.assertEqual((report["source_state"], report["original_destination_state"]), (location, target))

    def test_partial_line_is_unconfirmed_and_complete_records_are_strict(self):
        model = ReplacementModel()
        model.run()
        raw, source = bytes(model.raw), model.row(model.source)
        for cut in range(len(raw)-20, len(raw)):
            report = w._validate_replace_trace(raw[:cut], source, model.nonce, complete=False)
            self.assertEqual(report["confirmed_records"], 5)
            with self.assertRaises(w._Failure):
                w._validate_replace_trace(raw[:cut], source, model.nonce, complete=True)
        for bad in (raw + b"{}\n", raw.replace(b'"version":1', b'"version":true', 1),
                    raw.replace(model.nonce.encode(), b"2"*32, 1), b"{}\n", raw.replace(b'"sequence":1', b'"sequence":0', 1)):
            with self.assertRaises(w._Failure):
                w._validate_replace_trace(bad, source, model.nonce, complete=False)

    def test_source_target_bytes_and_hash_chain_tampering_are_rejected(self):
        model = ReplacementModel()
        model.run()
        rows = [json.loads(line) for line in bytes(model.raw).splitlines()]
        for mutation in ("source", "target", "chain", "duplicate_identity"):
            forged = deepcopy(rows)
            if mutation == "source":
                forged[0]["details"]["source"]["sha256"] = "0"*64
            elif mutation == "target":
                forged[1]["details"]["target"]["content_hex"] = "00"
            elif mutation == "duplicate_identity":
                forged[1]["details"]["target"]["identity"] = deepcopy(model.source["identity"])
            else:
                forged[-1]["previous_sha256"] = "0"*64
            # Even a recomputed chain cannot make inconsistent snapshots valid.
            lines, previous = [], "0"*64
            for row in forged:
                if mutation != "chain":
                    row["previous_sha256"] = previous
                line = w._canonical(row) + b"\n"
                previous = w._sha(line)
                lines.append(line)
            with self.subTest(mutation=mutation), self.assertRaises(w._Failure):
                w._validate_replace_trace(b"".join(lines), model.row(model.source), model.nonce, complete=True)

    def test_bounds_and_order_precede_sink_calls(self):
        sink = Mock()
        trace = w._ReplaceTrace("1"*32, sink)
        for stage, details in (("restored", {}), ("create_pending", {"source": "x"*w._REPLACE_TRACE_LIMIT})):
            with self.assertRaises(w._Failure):
                trace.emit(stage, details)
        sink.assert_not_called()
        trace.failed = True
        with self.assertRaises(w._Failure):
            trace.emit("create_pending", {})

    def test_capture_retains_raw_bytes_even_when_parser_or_close_fails(self):
        model = ReplacementModel()
        model.run()
        for failure in ("parse", "close"):
            raw = b"{}\n" if failure == "parse" else bytes(model.raw)
            api = Mock(security=Mock(return_value={}))
            fixture = w._Fixture(api, "user")
            fixture.root = Path("owned")
            fixture.ledger = {"control/data.bin": model.row(model.source),
                              w._REPLACE_TRACE_NAME: {"identity": {}, "sd": {}, "bytes": 0, "sha256": w._sha(b"")}}
            bound = Mock(identity={}, read=Mock(return_value=raw))
            if failure == "close":
                bound.close.side_effect = OSError("DUMMY_PRIVATE_CLOSE")
            result = w._ControlOutcome()
            with patch.object(w, "_Bound", return_value=bound), self.assertRaises(w._Failure):
                w._capture_replace_trace(api, fixture, result, model.nonce, complete=True)
            self.assertEqual(result.private_replace_evidence, raw)
            self.assertEqual(fixture.ledger[w._REPLACE_TRACE_NAME]["bytes"], 0)
            self.assertNotIn("DUMMY", json.dumps(result))

    def test_child_wrapper_has_distinct_resource_exit_without_running_native_child(self):
        class Flags:
            isolated = True
            def __getattr__(self, name):
                return getattr(original_flags, name)
        original_flags = sys.flags
        for error in (MemoryError(), w._Failure("memory_budget")):
            with patch.object(w, "_child_main", side_effect=error), patch.object(sys, "argv", ["fixture", "owned"]), \
                 patch.object(sys, "path", list(sys.path)), patch.object(sys, "flags", Flags()), self.assertRaises(SystemExit) as caught:
                runpy.run_path(str(w._CHILD), run_name="__main__")
            self.assertEqual(caught.exception.code, w._CHILD_RESOURCE_EXIT)

    def test_parent_skips_evidence_io_after_child_resource_exit_and_preserves_primary_capture_errors(self):
        for code, capture_error in ((w._CHILD_RESOURCE_EXIT, None), (1, None), (1, MemoryError())):
            api, fixture = Mock(), Mock()
            parent, child = parent_profile(), restricted_profile()
            api.profile.side_effect = [parent, child, child, {**child, "type": 2}]
            api.token.side_effect = [11, 33]
            api.restricted.return_value, api.impersonation.return_value = 22, 44
            api.resources.return_value = {"peak_pagefile_bytes": 1, "peak_working_bytes": 1,
                                          "system_commit_bytes": 1, "system_commit_limit_bytes": 2}
            api.call.side_effect = lambda ok, reason: w._need(ok, reason)
            api.k.WaitForSingleObject.return_value = 0
            api.k.CloseHandle.return_value = True
            def exit_code(process, pointer):
                ctypes.cast(pointer, ctypes.POINTER(w.D)).contents.value = code
                return True
            api.k.GetExitCodeProcess.side_effect = exit_code
            fixture.root, fixture.ledger = Path("owned")/(w._PREFIX+"0"*32), {}
            fixture.cleanup_attempted, fixture.cleanup_journal = False, None
            process = SimpleNamespace(process=1, thread=2, pid=99)
            with self.subTest(code=code, capture_error=type(capture_error)), patch.object(w, "_api", return_value=api), \
                 patch.object(w, "_runtime", return_value={}), patch.object(w, "_source_pin", return_value=[]), \
                 patch.object(w, "_Fixture", return_value=fixture), patch.object(w, "_start", return_value=process), \
                 patch.object(w, "_process_identity", return_value={"pid": 99}), patch.object(w, "_access_matrix", return_value={}), \
                 patch.object(w, "_capture_replace_trace", side_effect=capture_error) as capture, \
                 patch.object(Path, "exists", side_effect=AssertionError), patch.object(Path, "stat", side_effect=AssertionError), \
                 patch.object(Path, "read_bytes", side_effect=AssertionError), patch.object(Path, "iterdir", side_effect=AssertionError):
                result = w.run_control_harness()
            self.assertEqual(result["reason"], "child_resource_stop" if code == w._CHILD_RESOURCE_EXIT else "child_failed")
            self.assertEqual(capture.call_count, 0 if code == w._CHILD_RESOURCE_EXIT else 1)
            self.assertEqual(result["status"], "failed")
            fixture.cleanup.assert_not_called()
            if capture_error:
                self.assertTrue(result["teardown"]["resource_stop"])
                self.assertEqual(result["teardown"]["first_reason"], "replace_trace_capture")


@unittest.skipUnless(os.name == "nt", "Windows-only small same-parent trace test")
class NativeReplacementTraceTests(unittest.TestCase):
    def test_native_flush_capture_and_exact_cleanup(self):
        before = _prefix_inventory()
        self.assertEqual(len(w._source_pin()), 2)
        api, token, fixture, primary = w._api(), None, None, None
        teardown = w._Teardown()
        try:
            token = api.token(api.k.GetCurrentProcess())
            user = api.profile(token)["user"][0]
            fixture = w._Fixture(api, user)
            fixture.create()
            fixture.freeze()
            fixture.file(w._REPLACE_TRACE_NAME, b"", "control")
            initial = deepcopy(fixture.ledger["control/data.bin"])
            writer = w._Bound(api, fixture.path(w._REPLACE_TRACE_NAME), directory=False, access=0x20083, share=1)
            fixture.guards.append(writer)
            nonce = "3"*32
            trace = w._ReplaceTrace(nonce, writer.write)
            operations = w._operations(api, fixture.root, user, fixture.ledger, replace_trace=trace)
            self.assertEqual(operations, w._expected_operations())
            self.assertTrue(writer.close())
            fixture.guards.pop()
            result = w._ControlOutcome()
            w._capture_replace_trace(api, fixture, result, nonce, complete=True)
            self.assertEqual(result["replace_trace"]["confirmed_records"], 6)
            self.assertEqual(result.private_replace_evidence, trace.raw())
            self.assertTrue(fixture.ledger["control/data.bin"] == initial, "source pin changed")
            fixture.check()
            journal = fixture.cleanup(operations=w._canonical({"operations": operations, "replace_trace": result["replace_trace"]}))
            self.assertEqual(journal.report()["confirmed_absent_objects"], 7)
            self.assertTrue(any(item.name == w._REPLACE_TRACE_NAME and item.content == result.private_replace_evidence
                                for item in journal.private_snapshot[0]))
        except BaseException as error:
            primary = error
            raise
        finally:
            if fixture:
                teardown.attempt("fixture_close", lambda: fixture.close(teardown=teardown))
            if token:
                api.close(token, teardown=teardown)
            w._preserve_teardown(primary, teardown)
        self.assertEqual(before, _prefix_inventory())
