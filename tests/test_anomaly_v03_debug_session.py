"""Session integration uses fake Win32 and preflight, never a native child."""

from contextlib import ExitStack
import inspect
import json
import sys
import unittest
from unittest.mock import Mock, patch

from tests import test_anomaly_v03_debug_launch as fixtures
from tests.fixtures.anomaly_v03_debug_observer import DebugObserver
from tests.fixtures import anomaly_v03_debug_session as s


class DebugSessionTests(unittest.TestCase):
    def session(self, stack):
        launch, api, kernel = fixtures.DebugLaunchTests().launcher()
        launch.fixture.ledger = []
        api.token = Mock(return_value=701)
        api.impersonation = Mock(return_value=702)
        def token(*args):
            args[-1].contents.value = 701
            return True
        def duplicate_token(*args):
            args[-1].contents.value = 702
            return True
        api.a.OpenProcessToken.side_effect = token
        api.a.DuplicateTokenEx.side_effect = duplicate_token
        actual, duplicate = {"type": 1, "shape": "same"}, {"type": 2, "shape": "same"}
        api.profile = Mock(side_effect=lambda handle: actual if handle == 701 else duplicate)
        kernel.ResumeThread.return_value = 1
        kernel.ContinueDebugEvent.return_value = True
        events = iter((3, 5))
        def wait(pointer, timeout):
            raw = pointer.contents
            raw.kind, raw.pid, raw.tid = next(events), 17, 19
            return True
        kernel.WaitForDebugEventEx.side_effect = wait
        preflight = Mock(started=False, resource_stop=False, primary=None, secondary=None)
        preflight.run.return_value = {"status": "verified"}
        observer = DebugObserver(launch.stop, sample_memory=lambda: 0, clock=lambda: 0)
        identity = stack.enter_context(patch.object(s.w, "_process_identity", return_value={"pid": 17}))
        validate = stack.enter_context(patch.object(s.w, "_validate_restricted"))
        stack.enter_context(patch.object(s.w, "_shape", side_effect=lambda profile: profile["shape"]))
        access = stack.enter_context(patch.object(s.w, "_access_matrix", return_value={"checked": True}))
        session = s.DebugSession(preflight, launch, observer, {}, actual)
        return session, api, kernel, identity, validate, access

    def test_preflight_create_validate_resume_observe_and_owned_token_close(self):
        with ExitStack() as stack:
            session, api, kernel, identity, validate, access = self.session(stack)
            result = session.run()
            self.assertEqual(result["status"], "observed")
            self.assertEqual(result["resume_state"], "resumed")
            self.assertEqual(session.tokens, [None, None])
            self.assertEqual([call.args[0] for call in kernel.CloseHandle.call_args_list], [502, 501, 702, 701])
            kernel.ResumeThread.assert_called_once_with(502)
            validate.assert_called_once()
            access.assert_called_once()
            self.assertIs(result.private_owner, session)
            self.assertFalse(result["native_accepted"])
            self.assertFalse(result["formal_permission"])
            self.assertNotIn("DUMMY", json.dumps(result) + repr(session))
            with self.assertRaises(s.TransportError):
                session.run()

    def test_preflight_failure_never_creates_and_preserves_original(self):
        with ExitStack() as stack:
            session, api, kernel, identity, validate, access = self.session(stack)
            original = MemoryError()
            session.preflight.primary = original
            session.preflight.resource_stop = True
            session.preflight.run.return_value = {"status": "failed"}
            result = session.run()
            self.assertIs(session.primary, original)
            self.assertTrue(result["resource_stop"])
            api.a.CreateProcessAsUserW.assert_not_called()
            kernel.ResumeThread.assert_not_called()

    def test_validation_failures_never_resume_and_keep_acquired_token_slots(self):
        for phase in ("identity", "actual", "duplicate", "access"):
            with ExitStack() as stack, self.subTest(phase=phase):
                session, api, kernel, identity, validate, access = self.session(stack)
                original = MemoryError()
                target = {"identity": identity, "actual": validate, "duplicate": api.a.DuplicateTokenEx,
                          "access": access}[phase]
                target.side_effect = original
                result = session.run()
                self.assertIs(session.primary, original)
                self.assertTrue(result["resource_stop"])
                kernel.ResumeThread.assert_not_called()
                self.assertTrue(session.stop.started)
                self.assertEqual(session.tokens, [None, None])
                self.assertEqual(session.transport.state, "stopped")

    def test_resume_failure_or_unexpected_count_never_retries(self):
        for outcome in (0, 2, 0xFFFFFFFF, MemoryError()):
            with ExitStack() as stack, self.subTest(outcome=type(outcome).__name__):
                session, api, kernel, identity, validate, access = self.session(stack)
                if isinstance(outcome, BaseException):
                    kernel.ResumeThread.side_effect = outcome
                else:
                    kernel.ResumeThread.return_value = outcome
                result = session.run()
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["resume_state"], "uncertain")
                kernel.ResumeThread.assert_called_once()
                self.assertFalse(session.observer.started)
                self.assertTrue(session.stop.started)

    def test_shared_deadline_expires_during_validation_before_resume(self):
        with ExitStack() as stack:
            session, api, kernel, identity, validate, access = self.session(stack)
            now = 0
            session.observer.clock = lambda: now
            def expired(*args):
                nonlocal now
                now = 30
                return {"checked": True}
            access.side_effect = expired
            result = session.run()
            self.assertEqual(result["status"], "failed")
            self.assertEqual(session.primary.reason, "observation_deadline")
            kernel.ResumeThread.assert_not_called()

    def test_token_close_interrupt_keeps_handle_and_closes_other_once(self):
        with ExitStack() as stack:
            session, api, kernel, identity, validate, access = self.session(stack)
            def close(handle):
                if handle == 702:
                    raise KeyboardInterrupt()
                return True
            kernel.CloseHandle.side_effect = close
            result = session.run()
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["token_teardown"], "failed")
            self.assertEqual(session.tokens, [None, 702])
            self.assertEqual(session.token_close_state, ["closed", "uncertain"])
            session._close_tokens()
            self.assertEqual(kernel.CloseHandle.call_count, 4)

    def test_observer_failure_and_report_oom_keep_private_owners(self):
        for phase in ("observer", "report"):
            with ExitStack() as stack, self.subTest(phase=phase):
                session, api, kernel, identity, validate, access = self.session(stack)
                original = MemoryError("DUMMY_PRIVATE")
                if phase == "observer":
                    stack.enter_context(patch.object(session.observer, "run", side_effect=original))
                else:
                    stack.enter_context(patch.object(session.result, "update", side_effect=original))
                result = session.run()
                self.assertTrue(result["resource_stop"])
                self.assertIs(result.private_owner.launch, session.launch)
                self.assertIs(result.private_owner.stop, session.stop)
                self.assertIn(original, (session.primary, session.secondary))
                self.assertEqual(session.tokens, [None, None])
                self.assertTrue(session.stop.started)

    def test_token_output_interruption_retains_buffer_without_false_teardown_pass(self):
        for index in (0, 1):
            with ExitStack() as stack, self.subTest(index=index):
                session, api, kernel, identity, validate, access = self.session(stack)
                function = api.a.OpenProcessToken if index == 0 else api.a.DuplicateTokenEx
                original_call = function.side_effect
                original = MemoryError()
                def interrupted(*args):
                    original_call(*args)
                    raise original
                function.side_effect = interrupted
                result = session.run()
                self.assertIs(session.primary, original)
                self.assertEqual(session.token_buffers[index].value, 701 + index)
                self.assertEqual(session.token_acquire_state[index], "uncertain")
                self.assertEqual(result["token_teardown"], "failed")
                self.assertNotIn(701 + index, [call.args[0] for call in kernel.CloseHandle.call_args_list])
                kernel.ResumeThread.assert_not_called()

    def test_confirmed_token_is_recovered_if_slot_assignment_is_interrupted(self):
        source, first = inspect.getsourcelines(s.DebugSession._acquire_token)
        boundary = next(first + index for index, line in enumerate(source)
                        if line.strip() == "self.tokens[index] = self.token_buffers[index].value")
        for target in (0, 1):
            with ExitStack() as stack, self.subTest(index=target):
                session, api, kernel, identity, validate, access = self.session(stack)
                original = MemoryError()
                def trace(frame, event, arg):
                    if (frame.f_code is s.DebugSession._acquire_token.__code__ and event == "line"
                            and frame.f_lineno == boundary and frame.f_locals["index"] == target):
                        raise original
                    return trace
                previous = sys.gettrace()
                try:
                    sys.settrace(trace)
                    result = session.run()
                finally:
                    sys.settrace(previous)
                self.assertIs(session.primary, original)
                self.assertEqual(result["token_teardown"], "pass")
                self.assertIn(701 + target, [call.args[0] for call in kernel.CloseHandle.call_args_list])
                self.assertEqual(session.tokens, [None, None])


if __name__ == "__main__":
    unittest.main()
