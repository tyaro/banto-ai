"""Suspended launch ownership tests: all process/debug calls are fake."""

import inspect
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from tests.fixtures.anomaly_v03_debug_launch import SuspendedDebugLaunch
from tests.fixtures.anomaly_v03_debug_stop import OwnedDebugStop
from tests.fixtures.anomaly_v03_debug_transport import DebugEventTransport, TransportError
from tests.fixtures import anomaly_v03_startup_preflight as preflight


class DebugLaunchTests(unittest.TestCase):
    def launcher(self):
        kernel = Mock()
        kernel.GetCurrentThreadId.return_value = 7
        kernel.GetProcessId.return_value = 17
        kernel.CloseHandle.return_value = True
        kernel.WaitForSingleObject.return_value = 0
        api = SimpleNamespace(k=kernel, a=Mock())
        def create(*args):
            output = args[-1].contents
            output.process, output.thread, output.pid, output.tid = 501, 502, 17, 19
            return True
        api.a.CreateProcessAsUserW.side_effect = create
        transport = DebugEventTransport(kernel=kernel, last_error=lambda: 5)
        stop = OwnedDebugStop(transport, clock=lambda: 0)
        fixture = SimpleNamespace(root=Path("C:/DUMMY PRIVATE/new-fixture"))
        with patch.dict("os.environ", {"SystemRoot": "C:\\Windows"}):
            launch = SuspendedDebugLaunch(api, 401, fixture, stop)
        return launch, api, kernel

    def test_exact_flags_fixed_child_environment_and_preallocated_ownership(self):
        launch, api, kernel = self.launcher()
        output, result = launch.process, launch.result
        self.assertIs(launch.stop.creation_owner, launch)
        api.a.CreateProcessAsUserW.assert_not_called()
        returned = launch.create()
        self.assertIs(returned, result)
        self.assertIs(launch.process, output)
        self.assertIs(returned.private_owner, launch)
        self.assertEqual(returned["status"], "suspended")
        self.assertEqual(launch.stop.handles, [501, 502])
        self.assertEqual(launch.stop.drain.pid, 17)
        args = api.a.CreateProcessAsUserW.call_args.args
        self.assertEqual(args[0], 401)
        self.assertEqual(args[1], sys.executable)
        self.assertEqual(args[2].value, subprocess.list2cmdline(
            [sys.executable, "-B", "-I", str(preflight.w._CHILD), str(launch.fixture.root)]))
        self.assertEqual(args[3:7], (None, None, False, 0x08000406))
        self.assertEqual(args[10].contents.pid, 17)
        self.assertEqual(args[9].contents.desktop, "")
        self.assertEqual(args[9].contents.flags, 0)
        self.assertEqual(args[7][:].rstrip("\0"), "SystemRoot=C:\\Windows\0TEMP="
                         + str(launch.fixture.root.parent) + "\0TMP=" + str(launch.fixture.root.parent))
        kernel.ResumeThread.assert_not_called()
        kernel.TerminateProcess.assert_not_called()
        self.assertFalse(result["native_accepted"])
        self.assertNotIn("DUMMY", json.dumps(result) + repr(launch))
        self.assertIn("tests/fixtures/anomaly_v03_debug_launch.py", preflight.SOURCES)

    def test_false_creation_retains_output_without_adoption_or_close(self):
        launch, api, kernel = self.launcher()
        api.a.CreateProcessAsUserW.side_effect = None
        api.a.CreateProcessAsUserW.return_value = False
        result = launch.create()
        self.assertEqual(result["creation_state"], "failed")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(launch.stop.handles, [None, None])
        kernel.CloseHandle.assert_not_called()
        kernel.TerminateProcess.assert_not_called()
        with self.assertRaises(TransportError):
            launch.create()
        api.a.CreateProcessAsUserW.assert_called_once()

    def test_uncertain_api_side_effect_and_post_return_interrupt_preserve_raw_output(self):
        source, first = inspect.getsourcelines(SuspendedDebugLaunch.create)
        confirmed = next(first + index for index, line in enumerate(source)
                         if line.strip() == 'self.creation_state = "created"')
        for phase in ("api", "post_return"):
            launch, api, kernel = self.launcher()
            original = MemoryError("DUMMY_PRIVATE")
            create = api.a.CreateProcessAsUserW.side_effect
            def interrupted(*args):
                create(*args)
                raise original
            def trace(frame, event, arg):
                if frame.f_code is SuspendedDebugLaunch.create.__code__ and event == "line" and frame.f_lineno == confirmed:
                    raise original
                return trace
            previous = sys.gettrace()
            try:
                if phase == "api":
                    api.a.CreateProcessAsUserW.side_effect = interrupted
                else:
                    sys.settrace(trace)
                result = launch.create()
            finally:
                sys.settrace(previous)
            self.assertIs(launch.primary, original)
            self.assertEqual(result["creation_state"], "uncertain")
            self.assertTrue(result["resource_stop"])
            self.assertEqual(result.private_owner.process.process, 501)
            self.assertEqual(launch.stop.handles, [None, None])
            kernel.CloseHandle.assert_not_called()
            kernel.TerminateProcess.assert_not_called()

    def test_bind_failure_recovers_confirmed_creation_for_owned_stop(self):
        launch, api, kernel = self.launcher()
        original = MemoryError()
        kernel.WaitForSingleObject.side_effect = [258, 0]
        kernel.TerminateProcess.return_value = kernel.ContinueDebugEvent.return_value = True
        def exit_event(pointer, timeout):
            pointer.contents.kind, pointer.contents.pid, pointer.contents.tid = 5, 17, 19
            return True
        kernel.WaitForDebugEventEx.side_effect = exit_event
        with patch.object(launch.transport, "bind", side_effect=original):
            result = launch.create()
        self.assertEqual(result["creation_state"], "created")
        self.assertFalse(result["ownership_transferred"])
        self.assertEqual(launch.process.process, 501)
        self.assertEqual(launch.stop_result["status"], "stopped")
        kernel.TerminateProcess.assert_called_once_with(501, 1)
        self.assertEqual(launch.stop.handles, [None, None])
        self.assertEqual(kernel.CloseHandle.call_count, 2)
        self.assertIs(launch.primary, original)
        self.assertEqual(launch.transport.state, "stopped")

    def test_partial_adoption_is_recovered_but_foreign_pid_is_not_terminated(self):
        for foreign in (False, True):
            launch, api, kernel = self.launcher()
            def partial(*args):
                launch.stop.handles[0] = args[0]
                raise MemoryError()
            if foreign:
                kernel.GetProcessId.return_value = 99
            with patch.object(launch.stop, "adopt", side_effect=partial):
                result = launch.create()
            self.assertEqual(result["status"], "failed")
            if foreign:
                self.assertEqual(launch.stop_result["status"], "unconfirmed")
                kernel.TerminateProcess.assert_not_called()
                kernel.CloseHandle.assert_not_called()
            else:
                self.assertEqual(launch.stop.handles, [None, None])
                self.assertEqual(kernel.CloseHandle.call_count, 2)

    def test_interruption_after_adoption_attempts_owned_stop_once(self):
        launch, api, kernel = self.launcher()
        adopt = launch.stop.adopt
        original = KeyboardInterrupt()
        def interrupted(*args):
            adopt(*args)
            raise original
        with patch.object(launch.stop, "adopt", side_effect=interrupted):
            result = launch.create()
        self.assertEqual(result["status"], "failed")
        self.assertIs(launch.primary, original)
        self.assertTrue(launch.stop.started)
        self.assertEqual(launch.stop.handles, [None, None])
        self.assertEqual([call.args[0] for call in kernel.CloseHandle.call_args_list], [502, 501])

    def test_first_line_after_confirmed_creation_can_stop_without_capture_call(self):
        launch, api, kernel = self.launcher()
        source, first = inspect.getsourcelines(SuspendedDebugLaunch.create)
        boundary = next(first + index for index, line in enumerate(source)
                        if line.strip().startswith("need(self.process.pid"))
        original = MemoryError()
        def trace(frame, event, arg):
            if frame.f_code is SuspendedDebugLaunch.create.__code__ and event == "line" and frame.f_lineno == boundary:
                raise original
            return trace
        previous = sys.gettrace()
        try:
            sys.settrace(trace)
            result = launch.create()
        finally:
            sys.settrace(previous)
        self.assertIs(launch.primary, original)
        self.assertIs(launch.stop.creation_owner, launch)
        self.assertEqual(result["creation_state"], "created")
        self.assertEqual(launch.stop_result["status"], "stopped")
        self.assertEqual(launch.stop.handles, [None, None])
        self.assertEqual(kernel.CloseHandle.call_count, 2)

    def test_report_faults_stop_owned_child_and_keep_private_result(self):
        for final in (False, True):
            launch, api, kernel = self.launcher()
            update = launch.result.update
            calls = 0
            original = MemoryError()
            def report(*args, **kwargs):
                nonlocal calls
                calls += 1
                if calls == (2 if final else 1):
                    raise original
                update(*args, **kwargs)
            with patch.object(launch.result, "update", side_effect=report):
                result = launch.create()
            self.assertEqual(result["status"], "report_failed" if final else "failed")
            self.assertTrue(result["resource_stop"])
            self.assertTrue(launch.stop.started)
            self.assertEqual(launch.stop.handles, [None, None])
            self.assertIs(result.private_owner, launch)
            self.assertEqual(kernel.CloseHandle.call_count, 2)

    def test_resource_or_thread_failure_before_create_cannot_launch(self):
        for fault in ("resource", "thread"):
            launch, api, kernel = self.launcher()
            if fault == "resource":
                launch.transport.resource_stop = True
            else:
                kernel.GetCurrentThreadId.side_effect = MemoryError()
            result = launch.create()
            self.assertTrue(result["resource_stop"])
            self.assertEqual(result["creation_state"], "not_started")
            api.a.CreateProcessAsUserW.assert_not_called()

    def test_owned_stop_resource_failure_propagates_to_launch_result(self):
        launch, api, kernel = self.launcher()
        adopt = launch.stop.adopt
        def interrupted(*args):
            adopt(*args)
            raise KeyboardInterrupt()
        kernel.CloseHandle.side_effect = [MemoryError(), True]
        with patch.object(launch.stop, "adopt", side_effect=interrupted):
            result = launch.create()
        self.assertTrue(result["resource_stop"])
        self.assertEqual(launch.stop.handles, [None, 502])
        self.assertEqual(result["status"], "failed")


if __name__ == "__main__":
    unittest.main()
