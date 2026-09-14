"""Pure ordering, mutation-response and native-shaped ABI faults."""
import ctypes as C
import hashlib
from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from banto_ai import _anomaly_v03_windows as win
from tests.fixtures import anomaly_v03_delete_matrix as dm
from tests.fixtures import anomaly_v03_directory_acquisition as acq
from tests.fixtures import anomaly_v03_handle_owner as owned
from tests.fixtures import anomaly_v03_prepublication as prep
from tests.fixtures import anomaly_v03_rename_adapter as rename
from tests.test_anomaly_v03_directory_acquisition import Function, FakeApi, BorrowedView, USER, failing
from tests.test_anomaly_v03_directory_driver import Context


class Backend:
    def __init__(self, directory, calls, hooks):
        self.directory, self.calls, self.hooks = directory, calls, hooks
        self.kind = "root" if directory else "file"
        self.handle = 301 if directory else 302
        self.live = self.called = self.returned = False
        self.descriptor = "not_started"
        self.access = acq.ROOT_ACCESS if directory else dm.FILE_ACCESS
        content_hash = None if directory else hashlib.sha256(b"").hexdigest()
        self.observed = prep.Observation(rename.ObjectPin(self.handle, 7, bytes([self.handle % 256]) * 16, directory, content_hash), b"policy")
        self.result, self.code, self.pending, self.initial_pending = 1, 0, False, False

    def hit(self, name):
        event = self.kind + "_" + name
        self.calls.append(event)
        if event in self.hooks:
            self.hooks[event]()

    def prepare(self):
        self.hit("prepare")
        self.descriptor = "owned"

    def create(self, cell):
        self.called = self.live = True
        self.hit("created")
        cell.handle = self.handle
        self.returned = True

    def granted_access(self, handle):
        self.hit("access")
        return self.access

    def inspect(self, handle, *, guard):
        self.hit("inspect")
        guard()
        return self.observed

    def standard(self, handle):
        self.hit("standard")
        return {"allocation": 0, "end": 0, "links": 1, "pending": self.initial_pending}

    def after(self, handle, original, *, guard):
        self.hit("after")
        guard()
        return {"allocation": 0, "end": 0, "links": 1, "pending": self.pending}

    def delete(self):
        self.hit("delete")
        if self.result == 1:
            self.pending = True
        self.hit("delete_return")
        return self.result

    def get_last_error(self):
        self.hit("error")
        return self.code

    def close_handle(self, handle):
        self.hit("close")
        self.live = False
        self.hit("closed")
        return 1

    def release(self):
        if self.called and not self.returned:
            self.descriptor = "retained_unknown"
            return
        if self.descriptor not in ("freed", "not_started"):
            self.descriptor = "free_unknown"
            self.hit("free")
            self.descriptor = "freed"

    def snapshot(self):
        self.hit("snapshot")
        return {"descriptor_state": self.descriptor,
                "worker_exit_required": self.called and not self.returned or self.descriptor == "free_unknown"}

    def requires_exit(self):
        self.hit("exit_state")
        return self.called and not self.returned or self.descriptor == "free_unknown"


def setup(index=0):
    calls, hooks = [], {}
    root, child = Backend(True, calls, hooks), Backend(False, calls, hooks)
    def guard():
        calls.append("guard")
        if "guard" in hooks:
            hooks["guard"]()
    case = dm.DeleteCase(dm.CASES[index], root, child, guard=guard)
    return case, root, child, calls, hooks


class DeleteCaseTests(unittest.TestCase):
    def test_accepted_delete_checks_pending_then_closes_child_before_parent(self):
        case, root, child, calls, hooks = setup()
        case.run()
        report = case.snapshot()
        self.assertTrue(report["complete"])
        self.assertEqual(report["delete_result"], "accepted")
        self.assertTrue(report["after"]["pending"])
        self.assertLess(calls.index("file_after"), calls.index("file_close"))
        self.assertLess(calls.index("file_close"), calls.index("root_close"))
        self.assertEqual(calls.count("file_delete"), 1)
        self.assertFalse(root.live or child.live or case.requires_exit())
        self.assertFalse(report["retained_parent_capability_tested"])
        case.finish()
        self.assertEqual(calls.count("file_close"), 1)

    def test_known_denial_captures_error_before_guard_then_checks_retained_handle(self):
        for code in (5, 32):
            case, root, child, calls, hooks = setup(2)
            child.result, child.code = 0, code
            case.run()
            self.assertEqual(case.snapshot()["delete_result"], "denied")
            self.assertFalse(case.snapshot()["after"]["pending"])
            self.assertEqual(calls[calls.index("file_delete_return") + 1], "file_error")
            self.assertTrue(case.snapshot()["complete"])

    def test_positive_control_denial_cannot_be_complete(self):
        case, root, child, calls, hooks = setup()
        child.result, child.code = 0, 5
        with self.assertRaises(owned.OwnershipError) as caught:
            case.run()
        self.assertEqual(caught.exception.reason, "delete_positive_control_failed")
        self.assertFalse(case.snapshot()["complete"])
        self.assertFalse(root.live or child.live)

    def test_unclassified_reply_retains_inputs_and_both_handles_without_postreads(self):
        for value, code in ((0, 2), (0, 8), (0, True), (None, 0), (True, 0), (1.5, 0)):
            case, root, child, calls, hooks = setup()
            child.result, child.code = value, code
            with self.assertRaises(owned.OwnershipError):
                case.run()
            self.assertNotIn("file_after", calls)
            self.assertNotIn("file_close", calls)
            self.assertNotIn("root_close", calls)
            self.assertTrue(case.requires_exit() and root.live and child.live)
            self.assertEqual(case._resource, type(code) is int and code == 8)

    def test_delete_response_loss_records_unknown_and_never_retries(self):
        case, root, child, calls, hooks = setup()
        primary = MemoryError()
        hooks["file_delete_return"] = failing(primary)
        for method in (case.run, case.finish, case.finish):
            with self.assertRaises(MemoryError) as caught:
                method()
            self.assertIs(caught.exception, primary)
        self.assertTrue(child.pending)
        self.assertEqual(calls.count("file_delete"), 1)
        self.assertNotIn("file_after", calls)
        self.assertTrue(root.live and child.live and case.requires_exit())
        with self.assertRaises(owned.OwnershipError):
            case.snapshot()

    def test_file_acquisition_loss_retains_parent_and_stops_before_delete(self):
        case, root, child, calls, hooks = setup()
        hooks["file_created"] = failing(MemoryError())
        with self.assertRaises(MemoryError):
            case.run()
        self.assertNotIn("file_delete", calls)
        self.assertTrue(root.live and child.live and case.requires_exit())

    def test_inspection_access_or_initial_state_failure_never_deletes(self):
        for boundary in ("access", "initial_pending", "type"):
            case, root, child, calls, hooks = setup()
            if boundary == "access":
                child.access ^= 0x10000
            elif boundary == "initial_pending":
                child.initial_pending = True
            else:
                child.observed = replace(child.observed, pin=replace(child.observed.pin, directory=True, content_sha256=None))
            with self.assertRaises(owned.OwnershipError):
                case.run()
            self.assertNotIn("file_delete", calls)
            self.assertFalse(child.live or root.live)

    def test_known_response_pending_mismatch_or_postquery_failure_closes_known_handles(self):
        for boundary in ("mismatch", "query"):
            case, root, child, calls, hooks = setup()
            hooks["file_after"] = (lambda: setattr(child, "pending", False)) if boundary == "mismatch" else failing(ValueError("query"))
            with self.assertRaises((owned.OwnershipError, ValueError)):
                case.run()
            self.assertFalse(root.live or child.live)
            self.assertEqual(case._result, "accepted")
            self.assertFalse(case.snapshot()["complete"])

    def test_primary_failure_survives_later_close_resource_failure_and_keeps_parent(self):
        case, root, child, calls, hooks = setup()
        primary = ValueError("inspect")
        hooks["file_inspect"] = failing(primary)
        hooks["file_close"] = failing(MemoryError())
        with self.assertRaises(ValueError) as caught:
            case.run()
        self.assertIs(caught.exception, primary)
        self.assertTrue(case._resource and root.live and case.requires_exit())
        self.assertNotIn("root_close", calls)

    def test_child_close_or_free_uncertainty_keeps_parent_and_never_retries(self):
        for boundary in ("file_closed", "file_free"):
            case, root, child, calls, hooks = setup()
            error = OSError("close/free")
            hooks[boundary] = failing(error)
            for action in (case.run, case.finish):
                with self.assertRaises(OSError):
                    action()
            self.assertTrue(root.live and case.requires_exit())
            self.assertEqual(calls.count(boundary), 1)

    def test_swallowed_reentry_stops_at_all_callbacks(self):
        for boundary in ("guard", "root_prepare", "root_created", "file_prepare", "file_created", "file_inspect",
                         "file_standard", "file_delete", "file_after", "file_close", "root_close"):
            for action in ("run", "finish"):
                case, root, child, calls, hooks = setup()
                def reenter():
                    try:
                        getattr(case, action)()
                    except owned.OwnershipError:
                        pass
                hooks[boundary] = reenter
                with self.subTest(boundary=boundary, action=action), self.assertRaises(owned.OwnershipError):
                    case.run()
                self.assertFalse(case.snapshot()["complete"])
                self.assertLessEqual(calls.count("file_delete"), 1)

    def test_guard_notices_original_root_closed_by_callback_before_delete(self):
        case, root, child, calls, hooks = setup()
        hooks["file_standard"] = case.root.finish
        with self.assertRaises(owned.OwnershipError):
            case.run()
        self.assertNotIn("file_delete", calls)

    def test_finish_before_run_cannot_report_completion_or_create(self):
        case, root, child, calls, hooks = setup()
        case.finish()
        self.assertFalse(case.snapshot()["complete"])
        with self.assertRaises(owned.OwnershipError):
            case.run()
        self.assertNotIn("root_created", calls)

    def test_teardown_uses_no_reporting_snapshot_and_preserves_primary(self):
        case, root, child, calls, hooks = setup()
        primary = ValueError("inspect")
        hooks["file_inspect"] = failing(primary)
        hooks["file_snapshot"] = hooks["root_snapshot"] = failing(MemoryError())
        with self.assertRaises(ValueError) as caught:
            case.run()
        self.assertIs(caught.exception, primary)
        self.assertFalse(child.live or root.live or case.requires_exit())
        self.assertNotIn("file_snapshot", calls)
        self.assertNotIn("root_snapshot", calls)

    def test_lifetime_query_failure_latches_resource_and_retains_parent_without_retry(self):
        for boundary in ("file_exit_state", "root_exit_state"):
            case, root, child, calls, hooks = setup()
            primary = ValueError("inspect")
            hooks["file_inspect"] = failing(primary)
            hooks[boundary] = failing(MemoryError())
            for operation in (case.run, case.finish):
                with self.assertRaises(ValueError) as caught:
                    operation()
                self.assertIs(caught.exception, primary)
            self.assertTrue(case._resource and case.requires_exit())
            self.assertEqual(calls.count(boundary), 1)
            if boundary == "file_exit_state":
                self.assertTrue(root.live)
                self.assertNotIn("root_close", calls)

    def test_live_root_requires_exit_before_finish(self):
        case, root, child, calls, hooks = setup()
        case.root.acquire()
        self.assertTrue(case.requires_exit())
        case.finish()
        self.assertFalse(case.requires_exit())


class NativeBindingTests(unittest.TestCase):
    def setUp(self):
        for target, attribute, value in ((acq.sys, "version_info", (3, 14, 0)),
                                         (acq.os, "name", "nt"), (acq, "Path", lambda value: value)):
            stub = patch.object(target, attribute, value)
            stub.start()
            self.addCleanup(stub.stop)
        self.api = FakeApi()
        self.descriptors, self.arguments = [], []
        self.api.descriptor = lambda sddl: self.descriptors.append(sddl) or C.c_void_p(808)
        self.api.k.CreateFileW = Function(lambda *args: self.arguments.append(args) or 303)
        self.api.k.DeleteFileW = Function(lambda pointer: self.arguments.append(pointer.value) or 1)
        self.surface = SimpleNamespace(_SA=win._SA, D=win.D, _Bound=BorrowedView, _FileId=win._FileId)
        self.api.call = lambda ok, reason: owned._need(ok, reason)

    def test_file_binding_is_exclusive_empty_creation_without_delete_access_or_sd_mutation(self):
        backend = dm.FileBackend(self.surface, self.api, path=r"C:\fresh\empty.bin", user=USER, deny=True, share=3)
        backend.prepare()
        self.assertEqual(self.descriptors, [dm.policy(USER, directory=False, deny=True)[0]])
        self.assertEqual(backend._arguments[:3], (r"C:\fresh\empty.bin", 0x120081, 3))
        self.assertEqual(backend._arguments[4:], (1, 0x00200000, None))
        self.assertEqual(backend._arguments[3]._obj.inherit, 0)
        self.assertEqual(backend.delete(), 1)
        self.assertEqual(self.arguments, [r"C:\fresh\empty.bin"])
        backend.release()
        self.assertEqual(self.api.calls.count("free"), 1)

    def test_root_policy_changes_only_delete_child_bit_and_verifies_exact_acl(self):
        backend = dm.PolicyBackend(self.surface, self.api, path=r"C:\fresh\root", user=USER, deny=True)
        backend.prepare()
        self.assertEqual(self.descriptors, [dm.policy(USER, directory=True, deny=True)[0]])
        self.assertEqual(backend._arguments[1:4], (acq.ROOT_ACCESS, 1, 1))
        sd = {"protected": True, "owner": USER, "group": USER, "aces": dm.policy(USER, directory=True, deny=True)[1]}
        backend._verify_policy(sd)
        sd["aces"] = sd["aces"][1:]
        with self.assertRaises(owned.OwnershipError):
            backend._verify_policy(sd)
        backend.release()

    def test_standard_info_abi_and_bounds_are_checked(self):
        backend = dm.FileBackend(self.surface, self.api, path=r"C:\fresh\empty.bin", user=USER, deny=True, share=7)
        self.assertEqual((C.sizeof(dm._Standard), dm._Standard.pending.offset, dm._Standard.directory.offset), (24, 20, 21))
        def query(handle, kind, pointer, size):
            self.assertEqual((handle, kind, size), (303, 1, 24))
            pointer._obj.links, pointer._obj.pending = 1, 1
            return 1
        self.api.k.GetFileInformationByHandleEx = query
        self.assertTrue(backend.standard(303)["pending"])
        for field, value in (("end", 1), ("allocation", 4096), ("links", 2), ("pending", 2), ("directory", 1)):
            def invalid(handle, kind, pointer, size):
                query(handle, kind, pointer, size)
                setattr(pointer._obj, field, value)
                return 1
            self.api.k.GetFileInformationByHandleEx = invalid
            with self.assertRaises(owned.OwnershipError):
                backend.standard(303)

    def test_file_pin_requires_same_handle_zero_length_evidence(self):
        backend = dm.FileBackend(self.surface, self.api, path=r"C:\fresh\empty.bin", user=USER, deny=True, share=7)
        self.api.identity["directory"] = False
        self.api.sd["aces"] = dm.policy(USER, directory=False, deny=True)[1]
        def query(handle, kind, pointer, size):
            self.assertEqual((handle, kind, size), (303, 1, 24))
            pointer._obj.links = 1
            self.api.hit("standard")
            return 1
        self.api.k.GetFileInformationByHandleEx = query
        observation = backend.inspect(303, guard=lambda: None)
        self.assertFalse(observation.pin.directory)
        self.assertEqual(observation.pin.content_sha256, hashlib.sha256(b"").hexdigest())
        self.assertEqual(self.api.calls.count("standard"), 1)
        def nonempty(handle, kind, pointer, size):
            query(handle, kind, pointer, size)
            pointer._obj.end = 1
            return 1
        self.api.k.GetFileInformationByHandleEx = nonempty
        with self.assertRaises(owned.OwnershipError):
            backend.inspect(303, guard=lambda: None)


class MatrixDriverTests(unittest.TestCase):
    def setup_context(self):
        context = Context()
        context.peers = None
        context.persist = lambda: context.api.hit("persist")
        self.cases = [setup(i) for i in range(4)]
        for case, root, child, calls, hooks in self.cases[2:]:
            child.result, child.code = 0, 32 if case.plan.child_share == 3 else 5
        def configure(guard):
            matrix = dm.DeleteMatrix.__new__(dm.DeleteMatrix)
            matrix._context, matrix._external_guard = context, guard
            matrix._started = matrix._busy = matrix._done = matrix._complete = matrix._resource = False
            matrix._error = None
            matrix.cases = tuple(row[0] for row in self.cases)
            for case in matrix.cases:
                case._external_guard = matrix._guard
            context.peers = matrix
        context.configure_cases = configure
        resource = context.resource_stop
        context.resource_stop = lambda: resource() or context.peers is not None and context.peers._resource
        return context

    def test_complete_matrix_closes_all_cases_before_evidence_and_context(self):
        context = self.setup_context()
        runner = dm.DeleteDriver(context)
        runner.run()
        self.assertEqual(runner.exit_code(), 0)
        self.assertTrue(context.peers.snapshot()["matrix_complete"])
        self.assertEqual(context.api.calls[-2:], ["parent", "ancestors_close"])
        self.assertTrue(all(not root.live and not child.live for case, root, child, calls, hooks in self.cases))

    def test_unknown_case_retains_context_and_prevents_later_cases_or_evidence(self):
        context = self.setup_context()
        self.cases[0][4]["file_delete_return"] = failing(OSError("lost"))
        runner = dm.DeleteDriver(context)
        with self.assertRaises(OSError):
            runner.run()
        self.assertEqual(runner.exit_code(), 81)
        self.assertFalse(context.finished)
        self.assertNotIn("persist", context.api.calls)
        self.assertTrue(all(not root.called and not child.called for case, root, child, calls, hooks in self.cases[1:]))

    def test_preexisting_resource_stop_prevents_connection(self):
        context = self.setup_context()
        context.resource = True
        runner = dm.DeleteDriver(context)
        with self.assertRaises(MemoryError):
            runner.run()
        self.assertEqual(context.api.calls, ["ancestors_close"])
        self.assertEqual(runner.exit_code(), 80)

    def test_lifetime_query_resource_failure_keeps_primary_and_ancestors(self):
        context = self.setup_context()
        primary = ValueError("inspect")
        self.cases[0][4]["file_inspect"] = failing(primary)
        self.cases[0][4]["file_exit_state"] = failing(MemoryError())
        runner = dm.DeleteDriver(context)
        with self.assertRaises(ValueError) as caught:
            runner.run()
        self.assertIs(caught.exception, primary)
        self.assertEqual(runner.exit_code(), 80)
        self.assertFalse(context.finished)
        self.assertTrue(self.cases[0][1].live)
        self.assertNotIn("ancestors_close", context.api.calls)


if __name__ == "__main__":
    unittest.main()
