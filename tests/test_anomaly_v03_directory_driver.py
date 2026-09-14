"""Driver ordering and failure ownership without creating native objects."""
import copy
import ctypes as C
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests.fixtures import anomaly_v03_directory_driver as drv
from tests.fixtures import anomaly_v03_directory_acquisition as acq
from tests.fixtures import anomaly_v03_handle_owner as owned
from tests.test_anomaly_v03_directory_acquisition import setup, Function, failing


class Context:
    def __init__(self):
        self.api, self.backend, unused = setup()
        self.directory = None
        self.finished = self.resource = self.unknown = False

    def connect(self):
        self.api.hit("connect")

    def guard(self):
        self.api.hit("parent")

    def configure_directory(self, guard):
        self.directory = acq.DirectoryAcquisition(self.backend, guard=guard)
        self.api.hit("configure")

    def persist(self, observed):
        assert observed.pin.handle in self.api.live
        self.api.hit("persist")

    def resource_stop(self):
        return self.resource

    def child_requires_exit(self):
        return self.directory is not None and (self.directory._lease.close_state in ("unknown", "unavailable", "pending")
                or self.backend.snapshot()["worker_exit_required"])

    def finish(self):
        self.finished = True
        self.api.hit("ancestors_close")

    def requires_exit(self):
        return not self.finished or self.unknown

    def snapshot(self):
        return {"finished": self.finished}


class DirectoryDriverTests(unittest.TestCase):
    def setUp(self):
        for target, attribute, value in ((acq.sys, "version_info", (3, 14, 0)),
                                         (acq.os, "name", "nt"), (acq, "Path", lambda value: value)):
            stub = patch.object(target, attribute, value)
            stub.start()
            self.addCleanup(stub.stop)

    def test_success_saves_before_same_handle_recheck_then_closes_child_before_ancestors(self):
        context = Context()
        driver = drv.AcquisitionDriver(context)
        driver.run()
        calls = context.api.calls
        self.assertEqual(calls.count("create"), 1)
        self.assertEqual(calls.count("observe"), 4)
        self.assertLess(calls.index("persist"), len(calls) - 1 - calls[::-1].index("observe"))
        self.assertEqual(calls[-3:], ["close", "free", "ancestors_close"])
        self.assertFalse(context.api.live)
        self.assertEqual(driver.exit_code(), 0)
        report = driver.snapshot()
        self.assertEqual(report["evidence"], "saved")
        self.assertTrue(report["same_handle_rechecked"])
        self.assertFalse(report["isolation_certified"])
        driver.finish()
        self.assertEqual(calls.count("ancestors_close"), 1)

    def test_connect_and_parent_failures_prevent_source_creation(self):
        for boundary in ("connect", "parent", "configure"):
            context = Context()
            driver = drv.AcquisitionDriver(context)
            error = ValueError(boundary)
            context.api.hooks[boundary] = failing(error)
            with self.assertRaises(ValueError) as caught:
                driver.run()
            self.assertIs(caught.exception, error)
            self.assertNotIn("create", context.api.calls)
            self.assertTrue(context.finished)

    def test_collision_retains_ancestors_until_exit_and_never_inspects_source(self):
        context = Context()
        context.api.value = None
        driver = drv.AcquisitionDriver(context)
        with patch.object(C, "get_last_error", return_value=183, create=True), self.assertRaises(owned.OwnershipError):
            driver.run()
        self.assertEqual(driver.exit_code(), 81)
        self.assertFalse(context.finished)
        self.assertNotIn("observe", context.api.calls)
        self.assertNotIn("persist", context.api.calls)
        self.assertEqual(driver.snapshot()["winerror"], 183)

    def test_creation_response_loss_requires_exit_and_disallows_allocated_report(self):
        context = Context()
        driver = drv.AcquisitionDriver(context)
        context.api.hooks["created"] = failing(MemoryError())
        with self.assertRaises(MemoryError):
            driver.run()
        self.assertEqual(driver.exit_code(), 80)
        self.assertEqual(context.api.live, {303})
        self.assertFalse(context.finished)
        self.assertNotIn("free", context.api.calls)
        with self.assertRaises(owned.OwnershipError):
            driver.snapshot()

    def test_close_or_free_response_loss_never_retries_or_releases_ancestors(self):
        for boundary in ("close", "free"):
            context = Context()
            driver = drv.AcquisitionDriver(context)
            error = OSError(boundary)
            context.api.hooks[boundary] = failing(error)
            for operation in (driver.run, driver.finish, driver.finish):
                with self.assertRaises(OSError) as caught:
                    operation()
                self.assertIs(caught.exception, error)
            self.assertEqual(driver.exit_code(), 81)
            self.assertEqual(context.api.calls.count(boundary), 1)
            self.assertFalse(context.finished)

    def test_evidence_failure_stops_recheck_and_preserves_primary_during_cleanup_resource_error(self):
        for secondary in (None, MemoryError()):
            context = Context()
            driver = drv.AcquisitionDriver(context)
            primary = ValueError("evidence")
            context.api.hooks["persist"] = failing(primary)
            if secondary is not None:
                context.api.hooks["close"] = failing(secondary)
            with self.assertRaises(ValueError) as caught:
                driver.run()
            self.assertIs(caught.exception, primary)
            self.assertEqual(context.api.calls.count("observe"), 2)
            self.assertEqual(driver._evidence, "pending")
            self.assertEqual(driver.exit_code(), 1 if secondary is None else 80)

    def test_directory_change_after_evidence_rejects_success(self):
        context = Context()
        context.api.hooks["persist"] = lambda: context.api.identity.update(file_id="02" * 16)
        driver = drv.AcquisitionDriver(context)
        with self.assertRaises(owned.OwnershipError) as caught:
            driver.run()
        self.assertEqual(caught.exception.reason, "driver_directory_changed")
        self.assertEqual(driver.snapshot()["evidence"], "saved")
        self.assertFalse(driver.snapshot()["same_handle_rechecked"])
        self.assertTrue(context.finished)

    def test_swallowed_reentry_at_every_callback_cannot_become_success(self):
        for boundary in ("connect", "configure", "parent", "descriptor", "create", "access", "observe", "security",
                         "persist", "close", "free", "ancestors_close"):
            for action in ("run", "finish"):
                context = Context()
                driver = drv.AcquisitionDriver(context)
                def reenter():
                    try:
                        getattr(driver, action)()
                    except owned.OwnershipError:
                        pass
                context.api.hooks[boundary] = reenter
                with self.subTest(boundary=boundary, action=action), self.assertRaises(owned.OwnershipError):
                    driver.run()
                self.assertNotEqual(driver.exit_code(), 0)
                self.assertLessEqual(context.api.calls.count("create"), 1)
                self.assertLessEqual(context.api.calls.count("close"), 1)

    def test_non_none_callback_responses_stop(self):
        for method in ("connect", "guard", "configure_directory", "persist", "finish"):
            context = Context()
            original = getattr(context, method)
            def wrong(*args):
                original(*args)
                return True
            setattr(context, method, wrong)
            driver = drv.AcquisitionDriver(context)
            with self.assertRaises(owned.OwnershipError):
                driver.run()
            self.assertNotEqual(driver.exit_code(), 0)

    def test_sink_unknown_close_is_not_reported_as_success(self):
        context = Context()
        context.unknown = True
        driver = drv.AcquisitionDriver(context)
        driver.run()
        self.assertEqual(driver.exit_code(), 81)

    def test_resource_stop_before_run_has_no_connection_or_source_io(self):
        context = Context()
        context.resource = True
        driver = drv.AcquisitionDriver(context)
        with self.assertRaises(MemoryError):
            driver.run()
        self.assertEqual(context.api.calls, ["ancestors_close"])
        self.assertEqual(driver.exit_code(), 80)

    def test_resource_stop_at_callback_boundaries_prevents_later_io(self):
        for boundary in ("connect", "configure", "parent", "security", "persist"):
            context = Context()
            context.api.hooks[boundary] = lambda: setattr(context, "resource", True)
            driver = drv.AcquisitionDriver(context)
            with self.assertRaises(MemoryError):
                driver.run()
            later = context.api.calls[context.api.calls.index(boundary) + 1:]
            self.assertTrue(all(event in ("close", "free", "ancestors_close") for event in later), later)
            self.assertEqual(driver.exit_code(), 80)

    def test_finished_driver_never_restarts(self):
        context = Context()
        driver = drv.AcquisitionDriver(context)
        driver.finish()
        self.assertEqual(driver.exit_code(), 1)
        self.assertEqual(driver.snapshot()["directory_acquisition"], "fail")
        with self.assertRaises(owned.OwnershipError):
            driver.run()
        self.assertNotIn("connect", context.api.calls)
        self.assertEqual(context.api.calls.count("ancestors_close"), 1)


class ParentSecurityTests(unittest.TestCase):
    def setUp(self):
        self.context = drv.WindowsAcquisitionContext(Path.cwd() / "fake-unused", "a" * 40)
        self.buffer = C.create_string_buffer(b"x" * 32)
        self.freed = []
        def query(handle, kind, mask, *outputs):
            self.assertEqual((handle, kind, mask), (707, 1, 0x17))
            self.assertEqual(outputs[:-1], (None,) * 4)
            outputs[-1]._obj.value = C.addressof(self.buffer)
            return 0
        def control(pointer, flags, revision):
            flags._obj.value = 0x8000  # Self-relative, inherited ACLs allowed.
            return 1
        def free(pointer):
            self.freed.append(pointer.value)
            return None
        def call(ok, reason):
            owned._need(ok, reason)
        self.api = SimpleNamespace(a=SimpleNamespace(GetSecurityInfo=Function(query),
            GetSecurityDescriptorControl=Function(control), GetSecurityDescriptorLength=Function(lambda pointer: 32)),
            k=SimpleNamespace(LocalFree=Function(free)), call=call)
        self.context.sink._api = self.api

    def test_complete_self_relative_sd_is_bounded_and_freed_once_per_observation(self):
        for _ in range(2):
            self.assertEqual(self.context._parent_security(707), b"x" * 32)
        self.assertEqual(self.freed, [C.addressof(self.buffer)] * 2)
        self.assertEqual(self.context._parent_sd_state, "freed")
        self.assertEqual(self.api.a.GetSecurityDescriptorLength.argtypes, [C.c_void_p])

    def test_query_error_and_response_loss_never_free_unknown_output_or_retry(self):
        for mode in ("error", "null", "lost"):
            self.setUp()
            original = self.api.a.GetSecurityInfo.operation
            calls = []
            def query(*args):
                calls.append(1)
                if mode == "null":
                    return 0
                original(*args)
                if mode == "lost":
                    raise MemoryError()
                return 5
            self.api.a.GetSecurityInfo.operation = query
            for _ in range(2):
                with self.assertRaises((MemoryError, owned.OwnershipError)):
                    self.context._parent_security(707)
            self.assertEqual(calls, [1])
            self.assertFalse(self.freed)
            self.assertTrue(self.context.child_requires_exit())

    def test_invalid_length_or_absolute_sd_does_not_read_and_frees_known_buffer(self):
        for size in (0, 19, 8193, True):
            self.setUp()
            self.api.a.GetSecurityDescriptorLength.operation = lambda pointer: size
            with patch.object(C, "string_at") as read, self.assertRaises(owned.OwnershipError):
                self.context._parent_security(707)
            read.assert_not_called()
            self.assertEqual(len(self.freed), 1)
        self.setUp()
        self.api.a.GetSecurityDescriptorControl.operation = lambda *args: 1
        with patch.object(C, "string_at") as read, self.assertRaises(owned.OwnershipError):
            self.context._parent_security(707)
        read.assert_not_called()
        self.assertEqual(len(self.freed), 1)

    def test_copy_error_remains_primary_when_free_has_resource_failure(self):
        error = ValueError("copy")
        self.api.k.LocalFree.operation = lambda pointer: failing(MemoryError())()
        with patch.object(C, "string_at", side_effect=error), self.assertRaises(ValueError) as caught:
            self.context._parent_security(707)
        self.assertIs(caught.exception, error)
        self.assertTrue(self.context.resource_stop())
        self.assertTrue(self.context.child_requires_exit())
        self.assertEqual(self.context._parent_sd_state, "free_unknown")

    def test_parent_identity_and_descriptor_changes_stop_guard(self):
        identity = {"volume": 7, "file_id": "01" * 16, "directory": True}
        view = SimpleNamespace(identity=identity, observe=lambda: copy.deepcopy(identity))
        lease = SimpleNamespace(state="ready", close_state="not_started", _error=None, _custodian=None,
                                observed=view, handle=707)
        initial = self.context._observe_parent(lease)
        self.context._ancestors, self.context._before = (lease,), (initial,)
        self.context._connected = True
        self.context.budget = lambda: None
        self.context.guard()
        self.buffer[0] = b"y"
        with self.assertRaises(owned.OwnershipError):
            self.context.guard()
        self.buffer[0] = b"x"
        view.observe = lambda: {**identity, "file_id": "02" * 16}
        with self.assertRaises(owned.OwnershipError):
            self.context.guard()

    def test_connect_requires_the_exact_source_ancestor_chain(self):
        self.context.budget = lambda: None
        def connect(root):
            self.context.sink._leases = [SimpleNamespace(observed=SimpleNamespace(path=Path.cwd())), object()]
        self.context.sink.connect = connect
        with self.assertRaises(owned.OwnershipError) as caught:
            self.context.connect()
        self.assertEqual(caught.exception.reason, "driver_parent_chain")


if __name__ == "__main__":
    unittest.main()
