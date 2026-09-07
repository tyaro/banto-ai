"""Fault tests for the actual cleanup adapter, using an in-memory Win32 model."""

from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from banto_ai import _anomaly_v03_windows as w
from tests.test_anomaly_v03_windows import parent_profile, restricted_profile


class MemoryTree:
    """Only owned-object semantics needed here; not native acceptance evidence."""
    def __init__(self):
        self.api = Mock()
        self.fixture = w._Fixture(self.api, "DUMMY_PRIVATE_USER")
        self.fixture.root = Path("owned")
        self.fixture.guards = [Mock(path=self.fixture.root, close=Mock(return_value=True))]
        self.objects, self.handles, self.events = {}, {}, []
        self.fault = lambda phase, name: None
        self.stop = False
        for number, name in enumerate(("", "control", "control/data.bin")):
            directory = number < 2
            sd = {"owner": "DUMMY_PRIVATE_USER", "group": "DUMMY_PRIVATE_GROUP", "protected": True,
                  "aces": w._dacl("DUMMY_PRIVATE_USER", "frozen", directory)[1],
                  "integrity": "S-1-16-8192", "mandatory_policy": 1}
            raw = b"" if directory else b"DUMMY_PRIVATE_CONTENT"
            identity = {"directory": directory, "file_id": str(number), "volume": 1}
            self.objects[name] = {"identity": identity, "sd": sd, "content": raw}
            self.fixture.ledger[name] = {"identity": deepcopy(identity), "sd": deepcopy(sd),
                                         "bytes": len(raw), "sha256": None if directory else w._sha(raw)}
        self.api.call.side_effect = lambda ok, reason: w._need(ok, reason)
        self.api.security.side_effect = lambda handle: deepcopy(self.objects[self.handles[handle].name]["sd"])
        self.api.k.SetFileInformationByHandle.side_effect = self.disposition

    def io(self, phase, name):
        if self.stop:
            raise AssertionError("filesystem operation after resource stop")
        self.events.append((phase, name))

    def bind(self, api, path, *, directory, **kwargs):
        name = path.relative_to(self.fixture.root).as_posix()
        name = "" if name == "." else name
        self.io("bind", name)
        row = self.objects[name]
        tree = self

        class Bound:
            def __init__(self):
                self.name, self.path, self.directory = name, path, directory
                self.identity = deepcopy(row["identity"])
                self.handle = len(tree.handles) + 1
                self.armed = False
                tree.handles[self.handle] = self

            def check(self):
                tree.io("check", name)
                return deepcopy(tree.objects[name]["identity"])

            def streams(self):
                tree.io("streams", name)

            def read(self):
                tree.io("read", name)
                return tree.objects[name]["content"]

            def freeze(self, sddl):
                tree.io("acl", name)
                tree.fault("before_acl", name)
                row["sd"]["aces"] = w._dacl("DUMMY_PRIVATE_USER", "private", directory)[1]
                tree.fault("after_acl", name)
                return deepcopy(row["sd"])

            def close(self, *, primary=None, teardown=None):
                def perform():
                    tree.events.append(("close", name))
                    tree.fault("close", name)
                    if self.armed:
                        tree.objects.pop(name)
                if self.handle is not None:
                    if not w._close_call(perform, "bound_handle_close", primary, teardown):
                        return False
                    self.handle = None
                return True

        return Bound()

    def disposition(self, handle, *args):
        bound = self.handles[handle]
        self.io("delete", bound.name)
        self.fault("before_delete", bound.name)
        bound.armed = True
        self.fault("after_delete", bound.name)
        return True

    def scan(self, path):
        name = path.relative_to(self.fixture.root).as_posix()
        name = "" if name == "." else name
        self.io("scan", name)
        entries = [SimpleNamespace(name=child.rpartition("/")[2]) for child in self.objects
                   if child and child.rpartition("/")[0] == name]
        return SimpleNamespaceContext(entries)

    def lstat(self, path):
        name = path.relative_to(self.fixture.root).as_posix()
        name = "" if name == "." else name
        self.io("absence", name)
        self.fault("absence", name)
        if name not in self.objects:
            error = FileNotFoundError()
            error.winerror = 2
            raise error
        return object()

    def patched(self):
        stack = ExitStack()
        stack.enter_context(patch.object(w, "_Bound", side_effect=self.bind))
        stack.enter_context(patch.object(w.os, "scandir", side_effect=self.scan))
        stack.enter_context(patch.object(Path, "lstat", autospec=True, side_effect=self.lstat))
        stack.enter_context(patch.object(Path, "exists", side_effect=AssertionError))
        return stack


class SimpleNamespaceContext:
    def __init__(self, entries):
        self.entries = entries

    def __enter__(self):
        return iter(self.entries)

    def __exit__(self, *args):
        return False


class CleanupAdapterTests(unittest.TestCase):
    def test_teardown_report_failure_cannot_leave_success_or_replace_child_exit(self):
        for primary in (None, w._Failure("child_failed", child_exit_code=0xC0000142)):
            collector = w._Teardown()
            collector.record("owned_handle_close")
            outcome = ({"status": "native_control_pass", "success_residue_count": 0} if primary is None else
                       {"status": "failed", "reason": "child_failed", "winerror": 0, "child_exit_code": 0xC0000142})
            with self.subTest(primary=primary), patch.object(collector, "report", side_effect=MemoryError()):
                result = w._finish_outcome(outcome, primary, collector)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["reason"], "owned_teardown_failed" if primary is None else "child_failed")
            self.assertNotIn("success_residue_count", result)
            self.assertTrue(collector.resource_stop)
            if primary is not None:
                self.assertEqual(result["child_exit_code"], 0xC0000142)

    def test_teardown_report_failure_preserves_primary_and_private_journal_in_harness(self):
        tree = MemoryTree()
        with tree.patched():
            journal = tree.fixture.capture_cleanup(b"DUMMY_PRIVATE_CONTROL")
        for report_error in (MemoryError("DUMMY_REPORT"), ValueError("DUMMY_REPORT")):
            api = Mock()
            api.profile.return_value = parent_profile()
            fixture = Mock(root=Path("owned"), ledger={})
            fixture.cleanup_journal, fixture.cleanup_attempted = journal, True
            primary = w._Failure("freeze_set", 5)
            # Inject the existing captured journal at the harness failure boundary;
            # process/native creation is forbidden in this pure result-path test.
            fixture.create.side_effect = primary
            api.k.CloseHandle.return_value = False
            api.call.side_effect = lambda ok, reason: w._need(ok, reason)
            with self.subTest(error=type(report_error)), patch.object(w, "_api", return_value=api), \
                 patch.object(w, "_runtime", return_value={}), patch.object(w, "_source_pin", return_value=[]), \
                 patch.object(w, "_Fixture", return_value=fixture), \
                 patch.object(w._Teardown, "report", side_effect=report_error) as render, \
                 patch.object(journal, "report", return_value={}) as detail, \
                 patch.object(w, "_start", side_effect=AssertionError("native child")), \
                 patch.object(w, "_Bound", side_effect=AssertionError("filesystem read")):
                result = w.run_control_harness()
            self.assertEqual((result["status"], result["reason"], result["winerror"]), ("failed", "freeze_set", 5))
            self.assertEqual(result["teardown_status"], "failed")
            self.assertEqual(result["teardown_report_status"], "failed")
            self.assertIs(result.private_evidence, journal)
            self.assertTrue(result.private_teardown_evidence.count)
            self.assertEqual(result.private_teardown_evidence.resource_stop, isinstance(report_error, MemoryError))
            self.assertNotIn("success_residue_count", result)
            self.assertNotIn("DUMMY", json.dumps(result) + repr(result))
            render.assert_called_once()
            self.assertEqual(detail.call_count, 0 if isinstance(report_error, MemoryError) else 1)
            fixture.close.assert_called_once()

    def test_harness_retains_primary_and_snapshot_on_cleanup_or_report_failure_without_post_failure_io(self):
        for resource, report_error, completed in ((False, None, False), (True, None, False),
                (False, MemoryError("DUMMY_REPORT_OOM"), False),
                (False, ValueError("DUMMY_REPORT_ERROR"), False),
                (False, MemoryError("DUMMY_REPORT_OOM"), True),
                (False, ValueError("DUMMY_REPORT_ERROR"), True)):
            api, fixture = Mock(), Mock()
            parent, child = parent_profile(), restricted_profile()
            api.profile.side_effect = [parent, child, child, {**child, "type": 2}, child, parent]
            api.token.side_effect = [11, 33]
            api.restricted.return_value, api.impersonation.return_value = 22, 44
            api.resources.return_value = {"peak_pagefile_bytes": 1, "peak_working_bytes": 1,
                                          "system_commit_bytes": 1, "system_commit_limit_bytes": 2}
            api.call.side_effect = lambda ok, reason: w._need(ok, reason)
            api.k.WaitForSingleObject.return_value = 0
            api.k.CloseHandle.return_value = True
            fixture.root, fixture.ledger = Path("owned") / (w._PREFIX + "0" * 32), {}
            fixture.cleanup_attempted = False
            fixture.cleanup_journal = None
            def cleanup(*, operations):
                fixture.cleanup_attempted = True
                fixture.cleanup_journal = w.CleanupJournal((w.CapturedObject(
                    "", True, b"{}", b"DUMMY_OLD_SD", b"DUMMY_NEW_SD", b""),), operations)
                fixture.cleanup_journal.begin("", "acl")
                if completed:
                    journal = fixture.cleanup_journal
                    journal.confirmed()
                    journal.begin("", "delete")
                    journal.confirmed()
                    journal.close_confirmed("")
                    journal.begin("", "absence")
                    journal.confirmed()
                    journal.complete()
                    journal.report = Mock(side_effect=report_error)
                    return journal
                fixture.cleanup_journal.failed(resource_stop=resource)
                if resource:
                    fixture.cleanup_journal.report = Mock(side_effect=AssertionError("report allocation after OOM"))
                    raise MemoryError()
                if report_error is not None:
                    fixture.cleanup_journal.report = Mock(side_effect=report_error)
                raise w._Failure("freeze_set", 5)
            fixture.cleanup.side_effect = cleanup
            process = SimpleNamespace(process=1, thread=2, pid=99)
            report = Mock(read=Mock(return_value=b"{}"))
            with self.subTest(resource=resource, report_error=type(report_error), completed=completed), patch.object(w, "_api", return_value=api), \
                 patch.object(w, "_runtime", return_value={}), patch.object(w, "_source_pin", return_value=[]), \
                 patch.object(w, "_Fixture", return_value=fixture), patch.object(w, "_start", return_value=process), \
                 patch.object(w, "_process_identity", return_value={"pid": 99}), patch.object(w, "_access_matrix", return_value={}), \
                 patch.object(w, "_capture_replace_trace"), \
                 patch.object(w, "_Bound", return_value=report), patch.object(w, "_verify_report"), \
                 patch.object(Path, "exists", side_effect=AssertionError), patch.object(Path, "stat", side_effect=AssertionError), \
                 patch.object(Path, "iterdir", side_effect=AssertionError), patch.object(Path, "read_bytes", side_effect=AssertionError):
                result = w.run_control_harness()
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["control_status"], "pass")
            self.assertEqual(result["cleanup_status"], "completed" if completed else "failed")
            self.assertEqual(result["teardown_status"], "pass")
            self.assertIs(result.private_evidence, fixture.cleanup_journal)
            self.assertEqual(result.private_evidence.private_snapshot[1], result.private_control_evidence)
            self.assertEqual(json.loads(result.private_control_evidence)["parent_profile"], parent)
            self.assertNotIn(parent["user"][0], json.dumps(result))
            self.assertNotIn("DUMMY", json.dumps(result))
            if not completed:
                self.assertEqual(result["retained_existence"], "unverified")
            expected = ("resource_failure" if isinstance(report_error, MemoryError) else "cleanup_report_failed") if completed \
                else "resource_failure" if resource else "freeze_set"
            self.assertEqual(result["reason"], expected)
            self.assertEqual(result["winerror"], 0 if resource or completed else 5)
            self.assertNotIn("success_residue_count", result)
            self.assertEqual("cleanup" in result, not resource and report_error is None)
            if report_error is not None:
                fixture.cleanup_journal.report.assert_called_once()
                self.assertEqual(result["cleanup_report_status"], "failed")
                self.assertEqual(result["cleanup_report_resource_stop"], isinstance(report_error, MemoryError))
            if resource:
                fixture.cleanup_journal.report.assert_not_called()
            self.assertEqual(api.k.CloseHandle.call_count, 6)
            fixture.close.assert_called_once()

    def test_success_captures_every_original_byte_before_mutation_and_keeps_ledger(self):
        tree = MemoryTree()
        before = deepcopy(tree.fixture.ledger)
        def check_snapshot(phase, name):
            if phase == "before_acl":
                objects, operations = tree.fixture.cleanup_journal.private_snapshot
                self.assertEqual(len(objects), 3)
                self.assertEqual(operations, b"DUMMY_PRIVATE_CONTROL")
                self.assertEqual(objects[-1].content, b"DUMMY_PRIVATE_CONTENT")
                self.assertEqual(json.loads(objects[-1].security), before["control/data.bin"]["sd"])
        tree.fault = check_snapshot
        with tree.patched():
            journal = tree.fixture.cleanup(operations=b"DUMMY_PRIVATE_CONTROL")
        self.assertEqual(tree.objects, {})
        self.assertEqual(tree.fixture.ledger, before)
        self.assertEqual(journal.report()["status"], "completed")
        self.assertTrue(all(bound.handle is None for bound in tree.handles.values()))
        self.assertNotIn("DUMMY", json.dumps(journal.report()))

    def test_partial_delete_failures_keep_deleted_and_uncertain_objects_distinct(self):
        for target, expected_absent in (("control/data.bin", 0), ("control", 1), ("", 2)):
            tree = MemoryTree()
            def fail(phase, name):
                if phase == "after_delete" and name == target:
                    raise w._Failure("cleanup_disposition")
            tree.fault = fail
            with self.subTest(target=target), tree.patched(), self.assertRaises(w._Failure):
                tree.fixture.cleanup()
            report = tree.fixture.cleanup_journal.report()
            self.assertEqual(report["confirmed_absent_objects"], expected_absent)
            self.assertEqual(report["unknown_objects"], 1)
            self.assertEqual(report["status"], "failed")
            self.assertIsNone(report["success_residue_count"])
            self.assertEqual(len(tree.fixture.cleanup_journal.private_snapshot[0]), 3)
            # Disposition may have succeeded despite the error; close deleted it.
            self.assertNotIn(target, tree.objects)

    def test_acl_failure_after_side_effect_preserves_old_and_target_sd(self):
        tree = MemoryTree()
        def fail(phase, name):
            if phase == "after_acl":
                raise w._Failure("freeze_set")
        tree.fault = fail
        with tree.patched(), self.assertRaises(w._Failure):
            tree.fixture.cleanup()
        report = tree.fixture.cleanup_journal.report()
        self.assertEqual(report["objects"][-1]["acl"], "unknown")
        self.assertEqual(report["retained_captured_bytes_min"], len(b"DUMMY_PRIVATE_CONTENT"))
        item = tree.fixture.cleanup_journal.private_snapshot[0][-1]
        self.assertNotEqual(item.security, item.cleanup_security)
        self.assertEqual(json.loads(item.cleanup_security), tree.objects[item.name]["sd"])

    def test_capture_unknown_object_and_content_mismatch_precede_all_mutations(self):
        for kind in ("foreign", "content"):
            tree = MemoryTree()
            if kind == "foreign":
                tree.objects["control/foreign.bin"] = {}
            else:
                tree.objects["control/data.bin"]["content"] = b"changed"
            with self.subTest(kind=kind), tree.patched(), self.assertRaises(w._Failure):
                tree.fixture.cleanup()
            self.assertIsNone(tree.fixture.cleanup_journal)
            self.assertFalse(any(phase in ("acl", "delete") for phase, _ in tree.events))
            self.assertTrue(all(bound.handle is None for bound in tree.handles.values()))

    def test_identity_or_sd_changed_after_capture_is_never_mutated(self):
        for kind in ("identity", "sd"):
            tree = MemoryTree()
            original = tree.fixture.capture_cleanup
            def capture(operations):
                result = original(operations)
                tree.objects["control/data.bin"][kind]["file_id" if kind == "identity" else "owner"] = "foreign"
                return result
            tree.fixture.capture_cleanup = capture
            with self.subTest(kind=kind), tree.patched(), self.assertRaises(w._Failure):
                tree.fixture.cleanup()
            self.assertFalse(any(phase in ("acl", "delete") for phase, _ in tree.events))

    def test_close_failure_retains_handle_then_attempts_remaining_owned_teardown(self):
        tree = MemoryTree()
        failed_once = False
        def fail(phase, name):
            nonlocal failed_once
            if phase == "close" and name == "control/data.bin" and not failed_once:
                journal = tree.fixture.cleanup_journal
                if journal is not None and journal._progress[name].deletion == "armed":
                    failed_once = True
                    raise OSError("DUMMY_PRIVATE_FAILURE")
        tree.fault = fail
        with tree.patched():
            with self.assertRaises(w._Failure):
                tree.fixture.cleanup()
            self.assertEqual(sum(bound is not None for bound in tree.fixture.cleanup_handles), 1)
            last = len(tree.events)
            tree.fixture.close()
            self.assertTrue(all(phase == "close" for phase, _ in tree.events[last:]))
        self.assertTrue(all(bound is None for bound in tree.fixture.cleanup_handles))
        self.assertEqual(tree.fixture.cleanup_journal.report()["unknown_objects"], 1)
        self.assertEqual(tree.fixture.cleanup_journal.report()["status"], "failed")

    def test_resource_failure_at_acl_or_delete_is_primary_and_no_filesystem_io_follows(self):
        for operation in ("after_acl", "after_delete"):
            tree = MemoryTree()
            primary = MemoryError("DUMMY_PRIVATE_FAILURE")
            def fail(phase, name):
                if phase == operation:
                    tree.stop = True
                    raise primary
                if phase == "close" and tree.stop:
                    raise OSError("DUMMY_PRIVATE_SECONDARY")
            tree.fault = fail
            with self.subTest(operation=operation), tree.patched():
                with self.assertRaises(MemoryError) as caught:
                    tree.fixture.cleanup()
                self.assertIs(caught.exception, primary)
                self.assertTrue(primary.teardown.count)
                original_diagnostics = primary.teardown.report()
                teardown = w._Teardown()
                tree.fixture.close(teardown=teardown)
                self.assertTrue(teardown.count)
                self.assertEqual(primary.teardown.report(), original_diagnostics)
            self.assertTrue(tree.fixture.cleanup_journal.report()["resource_stop"])
            self.assertFalse(any(phase == "absence" for phase, _ in tree.events))

    def test_absence_permission_error_or_missing_parent_never_means_success(self):
        for error in (PermissionError("DUMMY_PRIVATE"), FileNotFoundError()):
            error.winerror = 5 if isinstance(error, PermissionError) else 3
            tree = MemoryTree()
            def fail(phase, name):
                if phase == "absence":
                    raise error
            tree.fault = fail
            with self.subTest(error=type(error)), tree.patched(), self.assertRaises((PermissionError, w._Failure)):
                tree.fixture.cleanup()
            report = tree.fixture.cleanup_journal.report()
            self.assertEqual(report["confirmed_absent_objects"], 0)
            self.assertEqual(report["unknown_objects"], 1)

    def test_second_cleanup_attempt_is_rejected_without_any_io(self):
        tree = MemoryTree()
        with tree.patched():
            tree.fixture.cleanup()
            count = len(tree.events)
            with self.assertRaises(w._Failure):
                tree.fixture.cleanup()
            self.assertEqual(len(tree.events), count)

    def test_result_mapping_does_not_serialize_private_snapshot(self):
        tree = MemoryTree()
        result = w._ControlOutcome()
        with tree.patched():
            result.private_evidence = tree.fixture.cleanup(operations=b"DUMMY_PRIVATE_CONTROL")
        result.private_control_evidence = b"DUMMY_PRIVATE_CONTROL"
        result.update(cleanup=result.private_evidence.report())
        self.assertNotIn("DUMMY", json.dumps(result) + repr(result))
        self.assertEqual(result.private_evidence.private_snapshot[1], result.private_control_evidence)
