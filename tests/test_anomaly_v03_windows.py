"""B1 controls; Windows prerequisite failure is a FAILURE, never a native pass.

No TemporaryDirectory/rmtree, campaign, generated observations or repository
artifact mutation. Successful native controls clean only their exact ledger.
Failed cleanup retains private snapshots and partial state; it cannot retain files
already deleted. Public results omit raw security descriptors and content.
"""

from copy import deepcopy
from contextlib import ExitStack, nullcontext
import ast
import ctypes
import inspect
import json
import os
from pathlib import Path, PureWindowsPath
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from banto_ai import _anomaly_v03_windows as w
from banto_ai import _anomaly_v03_runtime as rt


def parent_profile():
    return {"user": ["S-1-5-21-1-2-3-1001", 0], "groups": [["S-1-5-32-544", 0x10]],
            "privileges": [["SeChangeNotifyPrivilege", 3], ["SeShutdownPrivilege", 0]],
            "restricted": [], "type": 1, "integrity": "S-1-16-8192", "elevated": 0,
            "elevation_type": 3, "session": 1, "has_restrictions": 1,
            "token_id": "1", "modified_id": "2", "authentication_id": "3"}


def restricted_profile():
    value = parent_profile()
    value.update(token_id="4", modified_id="5", restricted=[[w._COMPATIBILITY_SID, 7], [w._RC, 7]],
                 privileges=[["SeChangeNotifyPrivilege", 3]])
    return value


class PureWindowsControls(unittest.TestCase):
    def test_restricted_control_launch_is_detached_suspended_and_noninheriting(self):
        api = Mock()
        fixture = SimpleNamespace(root=Path("C:/DUMMY PRIVATE/new-fixture"))
        def create(*args):
            process = args[-1]._obj
            process.process, process.thread, process.pid, process.tid = 501, 502, 17, 19
            return True
        api.a.CreateProcessAsUserW.side_effect = create
        api.call.side_effect = lambda ok, reason: w._need(ok, reason)
        with patch.dict(os.environ, {"SystemRoot": "C:\\Windows"}):
            process = w._start(api, 401, fixture)
        api.a.CreateProcessAsUserW.assert_called_once()
        args = api.a.CreateProcessAsUserW.call_args.args
        self.assertEqual(args[0:2], (401, sys.executable))
        self.assertEqual(args[2].value, w.subprocess.list2cmdline(
            [sys.executable, "-B", "-I", str(w._CHILD), str(fixture.root)]))
        self.assertEqual(args[3:7], (None, None, False, 0x40C))
        self.assertEqual(args[7][:].rstrip("\0"), "SystemRoot=C:\\Windows\0TEMP="
                         + str(fixture.root.parent) + "\0TMP=" + str(fixture.root.parent))
        self.assertEqual(args[8], str(fixture.root))
        self.assertNotIn(args[8], [str(fixture.root / mode) for mode in w._expected_operations()])
        startup = args[9]._obj
        self.assertEqual(startup.desktop, "")
        self.assertEqual(startup.flags, 0)
        self.assertEqual((startup.stdin, startup.stdout, startup.stderr), (None, None, None))
        self.assertEqual((process.process, process.thread, process.pid, process.tid), (501, 502, 17, 19))
        api.k.ResumeThread.assert_not_called()
        api.k.TerminateProcess.assert_not_called()
        api.k.CloseHandle.assert_not_called()

    def runtime_case(self, *, ubr=9445, build="26200", architecture=(0, 0x8664), hashes=None,
                     compiler="MSC v.1944 64 bit (AMD64)", git=("CPython", "tags/v3.14.0", "ebf955d"), free_threaded=0):
        import platform
        import sysconfig
        values = {"CurrentBuildNumber": build, "UBR": ubr, "EditionID": "Professional", "DisplayVersion": "25H2"}
        registry = SimpleNamespace(HKEY_LOCAL_MACHINE=0, OpenKey=lambda *args: nullcontext(1),
                                   QueryValueEx=lambda key, name: (values[name], 0))
        with ExitStack() as stack:
            stack.enter_context(patch.dict(sys.modules, {"winreg": registry}))
            stack.enter_context(patch.object(w, "os", SimpleNamespace(name="nt")))
            stack.enter_context(patch.object(w, "sys", SimpleNamespace(
                version_info=(3, 14, 0), _git=git,
                executable=sys.executable, base_prefix=sys.base_prefix)))
            stack.enter_context(patch.object(platform, "machine", side_effect=AssertionError("must not use WMI/environment")))
            stack.enter_context(patch.object(platform, "python_compiler", return_value=compiler))
            stack.enter_context(patch.object(sysconfig, "get_config_var", return_value=free_threaded))
            stack.enter_context(patch.object(w, "_api", return_value=Mock(architecture=Mock(return_value=architecture))))
            stack.enter_context(patch.object(w, "_read_source", side_effect=hashes or [(w._EXE_SHA,), (w._DLL_SHA,)]))
            return w._runtime()

    def test_windows_update_revision_is_recorded_instead_of_fixed(self):
        recorded = [self.runtime_case(ubr=value) for value in (9168, 9445, 9446)]
        self.assertEqual([row["build"] for row in recorded],
                         ["10.0.26200.9168", "10.0.26200.9445", "10.0.26200.9446"])
        self.assertNotEqual(recorded[1], recorded[2])  # End-of-run drift comparison remains meaningful.

    def test_windows_revision_type_and_release_boundary_remain_checked(self):
        for kwargs in ({"ubr": -1}, {"ubr": True}, {"ubr": "9445"}, {"ubr": 2**32},
                       {"build": "26100"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(w._Failure) as caught:
                self.runtime_case(**kwargs)
            self.assertEqual(caught.exception.reason, "runtime_pin")

    def test_windows_update_does_not_relax_python_binary_hashes(self):
        with self.assertRaises(w._Failure) as caught:
            self.runtime_case(hashes=[("wrong",)])
        self.assertEqual(caught.exception.reason, "runtime_hash")

    def test_runtime_uses_native_architecture_when_wmi_and_cpu_environment_are_absent(self):
        import platform
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(platform, "_wmi_query", side_effect=OSError("simulated unavailable"), create=True):
            if sys.platform == "win32":
                self.assertEqual(platform._get_machine_win32(), "")
            self.assertEqual(self.runtime_case()["python"], "3.14.0")

    def test_runtime_rejects_other_architectures_despite_spoofed_cpu_environment(self):
        for architecture in ((0, 0xaa64), (0x8664, 0xaa64), (0x14c, 0x8664), (0, 0), (0x8664, 0x8664)):
            with self.subTest(architecture=architecture), \
                 patch.dict(os.environ, {"PROCESSOR_ARCHITECTURE": "AMD64", "PROCESSOR_ARCHITEW6432": "AMD64"}), \
                 self.assertRaises(w._Failure) as caught:
                self.runtime_case(architecture=architecture)
            self.assertEqual(caught.exception.reason, "runtime_architecture")

    def test_runtime_python_metadata_remains_pinned(self):
        for changes in ({"compiler": "unknown"}, {"git": ("CPython", "other", "build")}, {"free_threaded": 1}):
            with self.subTest(changes=changes), self.assertRaises(w._Failure) as caught:
                self.runtime_case(**changes)
            self.assertEqual(caught.exception.reason, "runtime_python_metadata")

    def test_native_architecture_query_has_fixed_signature_and_borrowed_handle(self):
        kernel = Mock()
        with patch.object(w.os, "name", "nt"), patch.object(w.C, "WinDLL", return_value=kernel, create=True):
            api = w._Win()
        self.assertIs(kernel.IsWow64Process2.restype, w.B)
        self.assertEqual(kernel.IsWow64Process2.argtypes,
                         [w.H, ctypes.POINTER(ctypes.c_uint16), ctypes.POINTER(ctypes.c_uint16)])
        kernel.GetCurrentProcess.return_value = -1
        def query(process, process_machine, native_machine):
            self.assertEqual(process, -1)
            self.assertIs(type(process_machine._obj), ctypes.c_uint16)
            self.assertIs(type(native_machine._obj), ctypes.c_uint16)
            process_machine._obj.value, native_machine._obj.value = 0, 0x8664
            return 1
        kernel.IsWow64Process2.side_effect = query
        self.assertEqual(api.architecture(), (0, 0x8664))
        kernel.IsWow64Process2.assert_called_once()
        kernel.GetCurrentProcess.assert_called_once_with()
        kernel.CloseHandle.assert_not_called()
        kernel.OpenProcess.assert_not_called()

    def test_native_architecture_failure_never_accepts_outputs_or_falls_back(self):
        kernel = Mock()
        with patch.object(w.os, "name", "nt"), patch.object(w.C, "WinDLL", return_value=kernel, create=True):
            api = w._Win()
        def fail(process, process_machine, native_machine):
            process_machine._obj.value, native_machine._obj.value = 0, 0x8664
            return 0
        kernel.IsWow64Process2.side_effect = fail
        with patch.object(w.C, "get_last_error", return_value=5, create=True), self.assertRaises(w._Failure) as caught:
            api.architecture()
        self.assertEqual((caught.exception.reason, caught.exception.error), ("runtime_machine_query", 5))
        kernel.IsWow64Process2.assert_called_once()
        kernel.CloseHandle.assert_not_called()
        del kernel.IsWow64Process2
        with patch.object(w.os, "name", "nt"), patch.object(w.C, "WinDLL", return_value=kernel, create=True), \
             self.assertRaises(w._Failure) as caught:
            w._Win()
        self.assertEqual(caught.exception.reason, "runtime_machine_api_unavailable")

    def test_stream_enumeration_success_empty_directory_and_single_findclose_failure(self):
        for directory, close_ok in ((False, True), (True, True), (False, False)):
            api = Mock()
            api.call.side_effect = lambda ok, reason: w._need(ok, reason)
            api.close.return_value = True
            api.k.FindNextStreamW.return_value = False
            api.k.FindClose.return_value = close_ok
            bound = object.__new__(w._Bound)
            bound.api, bound.path, bound.handle, bound.directory = api, Path("owned"), 77, directory
            bound.check = Mock()
            def first(path, level, pointer, flags):
                ctypes.cast(pointer, ctypes.POINTER(w._StreamInfo)).contents.name = "::$DATA"
                return ctypes.c_void_p(-1).value if directory else 88
            api.k.FindFirstStreamW.side_effect = first
            with self.subTest(directory=directory, close_ok=close_ok), \
                 patch.object(w.C, "get_last_error", return_value=38, create=True):
                if close_ok:
                    with w._Closing(bound.close):
                        bound.streams()
                    self.assertEqual(bound.check.call_count, 2)
                else:
                    with self.assertRaises(w._Failure) as caught, w._Closing(bound.close):
                        bound.streams()
                    self.assertEqual(caught.exception.reason, "owned_teardown_failed")
                    self.assertEqual(caught.exception.teardown.report()["reasons"], ["stream_close"])
                    self.assertEqual(bound.check.call_count, 1)
            if directory:
                api.k.FindClose.assert_not_called()
            else:
                api.k.FindClose.assert_called_once_with(88)
            api.k.CloseHandle.assert_not_called()  # Enumeration handle is not CloseHandle-owned.
            api.close.assert_called_once_with(77)
            self.assertIsNone(bound.handle)

    def test_stream_resource_failure_survives_findclose_and_outer_bound_close_without_fs_io(self):
        for stage in ("name", "next", "resource_reason"):
            primary = w._Failure("memory_budget") if stage == "resource_reason" else MemoryError()
            stream_api, api = Mock(), Mock()
            stream_api.call.side_effect = lambda ok, reason: w._need(ok, reason)
            stream_api.k.FindFirstStreamW.return_value = 88
            stream_api.k.FindClose.return_value = False
            stream_api.close.side_effect = OSError("DUMMY_SECRET")
            if stage != "name":
                stream_api.k.FindNextStreamW.side_effect = primary
            class Item:
                @property
                def name(self):
                    if stage == "name":
                        raise primary
                    return "::$DATA"
            bound = object.__new__(w._Bound)
            bound.api, bound.path, bound.handle, bound.directory = stream_api, Path("owned"), 77, False
            bound.check = Mock()
            fixture = Mock(root=Path("owned")/(w._PREFIX+"0"*32), ledger={"known": {"bytes": 11}})
            def create():
                with w._Closing(bound.close):
                    bound.streams()
            fixture.create.side_effect = create
            api.profile.return_value = parent_profile()
            api.token.return_value, api.restricted.return_value = 11, 22
            api.k.CloseHandle.return_value = True
            api.call.side_effect = lambda ok, reason: w._need(ok, reason)
            with self.subTest(stage=stage), patch.object(w, "_StreamInfo", Item), \
                 patch.object(w.C, "byref", side_effect=lambda value: value), \
                 patch.object(w, "_api", return_value=api), patch.object(w, "_runtime", return_value={}), \
                 patch.object(w, "_source_pin", return_value=[]), patch.object(w, "_Fixture", return_value=fixture), \
                 patch.object(Path, "exists", side_effect=AssertionError), patch.object(Path, "stat", side_effect=AssertionError), \
                 patch.object(Path, "read_bytes", side_effect=AssertionError), patch.object(Path, "iterdir", side_effect=AssertionError), \
                 patch.object(w, "_temporary_path", side_effect=AssertionError):
                result = w.run_control_harness()
            self.assertEqual(result["reason"], "memory_budget" if stage == "resource_reason" else "resource_failure")
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["retained_existence"], "unverified")
            self.assertEqual(result["teardown"]["reasons"], ["stream_close", "bound_handle_close"])
            self.assertEqual(result["teardown"]["failure_count"], 2)
            self.assertTrue(result["teardown"]["resource_stop"])
            self.assertNotIn("DUMMY", json.dumps(result))
            stream_api.k.FindClose.assert_called_once_with(88)
            stream_api.k.CloseHandle.assert_not_called()
            stream_api.close.assert_called_once_with(77)
            self.assertEqual(bound.handle, 77)
            self.assertEqual(bound.check.call_count, 1)
            self.assertEqual(api.k.CloseHandle.call_count, 2)
            fixture.close.assert_called_once()

    def test_stream_primary_failure_and_findfirst_failure_do_not_skip_outer_close(self):
        for first_fails in (False, True):
            primary = MemoryError() if first_fails else w._Failure("stream_next", 5)
            api = Mock()
            api.call.side_effect = lambda ok, reason: w._need(ok, reason)
            api.k.FindFirstStreamW.side_effect = primary if first_fails else None
            api.k.FindFirstStreamW.return_value = 88
            api.k.FindNextStreamW.side_effect = primary
            api.k.FindClose.return_value = False
            api.close.side_effect = OSError("DUMMY_SECRET")
            bound = object.__new__(w._Bound)
            bound.api, bound.path, bound.handle, bound.directory = api, Path("owned"), 77, False
            bound.check = Mock()
            with self.subTest(first_fails=first_fails), self.assertRaises(type(primary)) as caught, w._Closing(bound.close):
                bound.streams()
            self.assertIs(caught.exception, primary)
            self.assertEqual(primary.teardown.count, 1 if first_fails else 2)
            if first_fails:
                api.k.FindClose.assert_not_called()  # No enumeration handle was returned.
            else:
                api.k.FindClose.assert_called_once_with(88)
            api.close.assert_called_once_with(77)
            self.assertEqual(bound.check.call_count, 1)

    def test_bound_handle_identity_survives_close_failure_until_success(self):
        bound = object.__new__(w._Bound)
        bound.handle, bound.api = 77, Mock()
        bound.api.close.side_effect = [w._Failure("handle_close"), None]
        with self.assertRaises(w._Failure):
            bound.close()
        self.assertEqual(bound.handle, 77)
        bound.close()
        self.assertIsNone(bound.handle)
        self.assertEqual(bound.api.close.call_count, 2)
        self.assertTrue(all(call.args == (77,) for call in bound.api.close.call_args_list))

    def test_bound_close_preserves_explicit_local_memory_error(self):
        bound = object.__new__(w._Bound)
        bound.handle, bound.api = 77, Mock()
        bound.api.close.side_effect = OSError("DUMMY_SECRET")
        primary = MemoryError()
        with self.assertRaises(MemoryError) as caught:
            try:
                raise primary
            except MemoryError as local:
                bound.close(primary=local)
                raise
        self.assertIs(caught.exception, primary)
        self.assertEqual(bound.handle, 77)
        self.assertEqual(primary.teardown.report()["reasons"], ["bound_handle_close"])
        self.assertNotIn("DUMMY", json.dumps(primary.teardown.report()))

    def test_fixture_close_attempts_every_guard_and_retains_unconfirmed_ones(self):
        fixture = w._Fixture(Mock(), "user")
        guards = [Mock() for _ in range(4)]
        guards[1].close.side_effect = OSError("DUMMY_SECRET")
        guards[3].close.side_effect = w._Failure("handle_close")
        fixture.guards = guards.copy()
        with self.assertRaises(w._Failure) as caught:
            fixture.close()
        self.assertEqual(caught.exception.reason, "owned_teardown_failed")
        self.assertEqual(fixture.guards, [guards[1], guards[3]])
        for guard in guards:
            guard.close.assert_called_once_with()
        self.assertEqual(fixture.teardown.count, 2)
        self.assertEqual(fixture.teardown.report()["first_reason"], "fixture_guard_close")

    def test_owned_teardown_checks_wait_terminate_and_all_close_results(self):
        for initial, final, terminate, close in ((258, 258, False, False), (0xffffffff, 0xffffffff, False, False),
                                                 (0, 0, True, False), (0, 0, True, True)):
            api, process, fixture = Mock(), SimpleNamespace(process=1), Mock()
            api.call.side_effect = lambda ok, reason: w._need(ok, reason)
            api.k.WaitForSingleObject.side_effect = [initial, final]
            api.k.TerminateProcess.return_value = terminate
            api.k.CloseHandle.return_value = close
            teardown = w._Teardown()
            with self.subTest(initial=initial, final=final, close=close), \
                 patch.object(Path, "exists", side_effect=AssertionError), patch.object(w, "_Bound", side_effect=AssertionError):
                w._owned_teardown(api, process, (2, 3, 4, 5, 6, 1), fixture, teardown)
            self.assertEqual(api.k.CloseHandle.call_count, 6)
            fixture.close.assert_called_once()
            if initial != 0:
                api.k.TerminateProcess.assert_called_once_with(1, 1)
                self.assertEqual(api.k.WaitForSingleObject.call_count, 2)
            else:
                api.k.TerminateProcess.assert_not_called()
            pending = {**w._result_status(), "status": "native_control_pass"}
            result = w._finish_outcome(pending, None, teardown)
            if initial == 0 and close:
                self.assertEqual(result["status"], "native_control_pass")
                self.assertNotIn("teardown", result)
            else:
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["reason"], "owned_teardown_failed")
                self.assertGreater(result["teardown"]["failure_count"], 0)
            self.assertFalse(result["native_accepted"])

    def test_process_api_exceptions_do_not_skip_remaining_teardown(self):
        api, fixture, teardown = Mock(), Mock(), w._Teardown()
        api.k.WaitForSingleObject.side_effect = MemoryError()
        api.k.TerminateProcess.side_effect = OSError("DUMMY_SECRET")
        api.k.CloseHandle.side_effect = [OSError("DUMMY_SECRET"), True, True]
        api.call.side_effect = lambda ok, reason: w._need(ok, reason)
        w._owned_teardown(api, SimpleNamespace(process=1), (2, 3, 1), fixture, teardown)
        self.assertEqual(api.k.WaitForSingleObject.call_count, 2)
        self.assertEqual(api.k.CloseHandle.call_count, 3)
        fixture.close.assert_called_once()
        result = w._finish_outcome({"status": "native_control_pass"}, None, teardown)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["teardown"]["resource_stop"])
        self.assertIsNone(result["retained_exists"])

    def test_harness_pending_success_is_decided_after_all_owned_teardown(self):
        for failure in (None, "handle", "memory", "bound_os", "bound_memory"):
            api, fixture = Mock(), Mock()
            parent, child = parent_profile(), restricted_profile()
            api.profile.side_effect = [parent, child, child, {**child, "type": 2}, child, parent]
            api.token.side_effect = [11, 33]
            api.restricted.return_value, api.impersonation.return_value = 22, 44
            api.resources.return_value = {"peak_pagefile_bytes": 1, "peak_working_bytes": 1,
                                          "system_commit_bytes": 1, "system_commit_limit_bytes": 2}
            api.call.side_effect = lambda ok, reason: w._need(ok, reason)
            api.k.WaitForSingleObject.return_value = 0
            api.k.CloseHandle.return_value = failure != "handle"
            fixture.root, fixture.ledger = Path("owned")/(w._PREFIX+"0"*32), {}
            if failure == "memory":
                fixture.close.side_effect = MemoryError()
            guard = None
            if failure in ("bound_os", "bound_memory"):
                fixture = w._Fixture(api, "user")
                fixture.root = Path("owned")/(w._PREFIX+"0"*32)
                for name in ("create", "freeze", "file", "record", "check", "cleanup"):
                    setattr(fixture, name, Mock())
                guard = object.__new__(w._Bound)
                guard.api, guard.handle = Mock(), 77
                guard.api.close.side_effect = OSError("DUMMY_SECRET") if failure == "bound_os" else MemoryError()
                fixture.guards = [guard]
                fixture.close = Mock(wraps=fixture.close)  # Real Fixture and Bound close.
            process = SimpleNamespace(process=1, thread=2, pid=99)
            report = Mock(read=Mock(return_value=b"{}"))
            with self.subTest(failure=failure), patch.object(w, "_api", return_value=api), \
                 patch.object(w, "_runtime", return_value={}), patch.object(w, "_source_pin", return_value=[]), \
                 patch.object(w, "_Fixture", return_value=fixture), patch.object(w, "_start", return_value=process), \
                 patch.object(w, "_process_identity", return_value={"pid": 99}), patch.object(w, "_access_matrix", return_value={}), \
                 patch.object(w, "_capture_replace_trace"), \
                 patch.object(w, "_Bound", return_value=report), patch.object(w, "_verify_report"), \
                 patch.object(Path, "exists", side_effect=AssertionError), patch.object(Path, "stat", side_effect=AssertionError), \
                 patch.object(Path, "iterdir", side_effect=AssertionError), patch.object(Path, "read_bytes", side_effect=AssertionError):
                try:
                    raise ValueError("unrelated outer exception")
                except ValueError as ambient:
                    result = w.run_control_harness()
                    self.assertFalse(hasattr(ambient, "teardown"))
            fixture.cleanup.assert_called_once()
            fixture.close.assert_called_once()
            self.assertEqual(api.k.CloseHandle.call_count, 6)
            self.assertEqual(result["status"], "failed" if failure else "native_control_pass")
            self.assertFalse(result["native_accepted"])
            if failure:
                self.assertEqual(result["reason"], "owned_teardown_failed")
                self.assertNotIn("success_residue_count", result)
                if guard is not None:
                    self.assertEqual(guard.handle, 77)
                    self.assertEqual(fixture.guards, [guard])
                    self.assertIs(fixture.close.call_args.kwargs["teardown"], fixture.teardown)
                    self.assertEqual(result["teardown"]["failure_count"], 1)
            else:
                self.assertNotIn("teardown", result)

    def test_collectorless_closes_raise_inside_unrelated_outer_except(self):
        for failure in (OSError("DUMMY_SECRET"), MemoryError()):
            api = object.__new__(w._Win)
            api.k = Mock()
            api.k.CloseHandle.side_effect = failure
            bound = object.__new__(w._Bound)
            bound.api, bound.handle = api, 77
            fixture = w._Fixture(api, "user")
            fixture.guards = [bound]
            for close in (lambda: api.close(77), bound.close, fixture.close):
                try:
                    raise ValueError("unrelated outer exception")
                except ValueError as ambient:
                    with self.assertRaises(w._Failure):
                        close()
                    self.assertFalse(hasattr(ambient, "teardown"))
                self.assertEqual(bound.handle, 77)
            self.assertEqual(fixture.guards, [bound])

    def test_bound_constructor_preserves_its_local_primary_not_outer_exception(self):
        api, primary = Mock(), MemoryError()
        api.k.CreateFileW.return_value = 77
        api.close.side_effect = OSError("DUMMY_SECRET")
        with patch.object(w, "_lexical"), patch.object(w._Bound, "observe", side_effect=primary):
            try:
                raise ValueError("unrelated outer exception")
            except ValueError as ambient:
                with self.assertRaises(MemoryError) as caught:
                    w._Bound(api, Path("owned"), directory=False)
                self.assertIs(caught.exception, primary)
                self.assertFalse(hasattr(ambient, "teardown"))
        self.assertEqual(primary.teardown.count, 1)

    def test_cleanup_root_guard_is_not_popped_when_close_is_unconfirmed(self):
        api = Mock()
        fixture = w._Fixture(api, "user")
        fixture.root = Path("owned")
        fixture.check = Mock()
        identity = {"directory": True}
        fixture.ledger = {"": {"identity": identity, "sd": {}, "bytes": 0}}
        guard = object.__new__(w._Bound)
        guard.path, guard.api, guard.handle = fixture.root, Mock(), 77
        guard.api.close.side_effect = OSError("DUMMY_SECRET")
        fixture.guards = [guard]
        restore = Mock(identity=identity, directory=True)
        restore.freeze.return_value = {}
        journal = w.CleanupJournal((w.CapturedObject("", True, b"{}", b"{}", b"{}", b""),), b"{}")
        fixture.cleanup_journal = journal
        fixture.capture_cleanup = Mock(return_value=journal)
        fixture._cleanup_verify = Mock()
        with patch.object(w, "_Bound", return_value=restore), patch.object(w, "_verify_sd"), \
             patch.object(Path, "exists", side_effect=AssertionError), patch.object(Path, "iterdir", side_effect=AssertionError):
            try:
                raise ValueError("unrelated outer exception")
            except ValueError as ambient:
                with self.assertRaises(w._Failure):
                    fixture.cleanup()
                self.assertFalse(hasattr(ambient, "teardown"))
        self.assertEqual(fixture.guards, [guard])
        self.assertEqual(guard.handle, 77)
        api.k.SetFileInformationByHandle.assert_not_called()

    def test_child_teardown_attempts_all_guards_and_tokens_with_explicit_primary(self):
        for primary in (None, MemoryError()):
            api, guards, teardown = Mock(), [Mock(), Mock(), Mock()], w._Teardown()
            guards[-1].close.side_effect = OSError("DUMMY_SECRET")
            api.close.side_effect = [OSError("DUMMY_SECRET"), None]
            try:
                raise ValueError("unrelated outer exception")
            except ValueError as ambient:
                if primary is None:
                    with self.assertRaises(w._Failure) as caught:
                        w._child_teardown(api, guards, (11, 22), primary, teardown)
                    self.assertEqual(caught.exception.reason, "owned_teardown_failed")
                else:
                    w._child_teardown(api, guards, (11, 22), primary, teardown)
                    self.assertIs(primary.teardown, teardown)
                self.assertFalse(hasattr(ambient, "teardown"))
            self.assertEqual(teardown.count, 2)
            for guard in guards:
                guard.close.assert_called_once_with()
            self.assertEqual([call.args for call in api.close.call_args_list], [(11,), (22,)])

    def test_child_main_preserves_local_memory_error_and_closes_every_guard(self):
        api, primary, guards = Mock(), MemoryError(), []
        api.token.return_value = 11
        api.close.side_effect = OSError("DUMMY_SECRET")
        request = Mock()
        request.read.side_effect = primary
        request.close.side_effect = OSError("DUMMY_SECRET")
        root = Path("owned")/(w._PREFIX+"0"*32)
        def bind(api, path, **kwargs):
            if kwargs["directory"]:
                guard = Mock()
                guard.close.side_effect = OSError("DUMMY_SECRET")
                guards.append(guard)
                return guard
            return request
        with patch.object(w, "_api", return_value=api), patch.object(w, "_runtime"), \
             patch.object(w, "_temporary_path", return_value=root.parent), patch.object(w, "_Bound", side_effect=bind), \
             patch.object(Path, "exists", side_effect=AssertionError), patch.object(Path, "stat", side_effect=AssertionError), \
             patch.object(Path, "read_bytes", side_effect=AssertionError), patch.object(Path, "iterdir", side_effect=AssertionError):
            try:
                raise ValueError("unrelated outer exception")
            except ValueError as ambient:
                with self.assertRaises(MemoryError) as caught:
                    w._child_main(root)
                self.assertIs(caught.exception, primary)
                self.assertFalse(hasattr(ambient, "teardown"))
        self.assertEqual(primary.teardown.count, len(guards)+2)
        api.close.assert_called_once_with(11)
        request.close.assert_called_once_with()
        for guard in guards:
            guard.close.assert_called_once_with()

    def test_no_ambient_exception_dependency_in_close_implementation(self):
        self.assertNotIn("sys.exception", w._SOURCE.read_text(encoding="utf-8"))

    def test_all_primary_resource_reasons_survive_source_guard_failures(self):
        for reason in w._RESOURCE_REASONS:
            api, file, guard = Mock(), Mock(handle=9), Mock()
            api.call.side_effect = lambda ok, reason: w._need(ok, reason)
            primary = w._Failure(reason)
            file.read.side_effect = primary
            file.close.side_effect = OSError("DUMMY_SECRET")
            guard.close.side_effect = OSError("DUMMY_SECRET")
            with self.subTest(reason=reason), \
                 patch.object(w, "_Bound", side_effect=lambda api, path, **kw: guard if kw["directory"] else file), \
                 self.assertRaises(w._Failure) as caught:
                w._source_bytes(api, Path("source.py"))
            self.assertIs(caught.exception, primary)
            self.assertEqual(primary.reason, reason)
            self.assertTrue(primary.teardown.resource_stop)
            self.assertEqual(primary.teardown.count, 2)
            file.close.assert_called_once_with()
            guard.close.assert_called_once_with()

    def test_streaming_source_memory_error_preserved_after_guard_close_errors(self):
        api, file, guard = Mock(), Mock(handle=9), Mock()
        primary = MemoryError()
        api.k.ReadFile.side_effect = primary
        file.close.side_effect = OSError("DUMMY_SECRET")
        guard.close.side_effect = OSError("DUMMY_SECRET")
        with patch.object(w, "_Bound", side_effect=lambda api, path, **kw: guard if kw["directory"] else file), \
             self.assertRaises(MemoryError) as caught:
            w._read_source(api, Path("source.py"))
        self.assertIs(caught.exception, primary)
        self.assertEqual(primary.teardown.count, 2)
        api.k.ReadFile.assert_called_once()
        file.check.assert_not_called()
        file.close.assert_called_once_with()
        guard.close.assert_called_once_with()

    def test_compound_resource_failure_preserved_across_all_teardown_layers(self):
        for overflow in (False, True):
            api, process = Mock(), Mock()
            api.profile.return_value = parent_profile()
            api.token.return_value, api.restricted.return_value = 11, 22
            api.call.side_effect = lambda ok, reason: w._need(ok, reason)
            api.k.CloseHandle.return_value = False
            process.poll.return_value = None
            process.stdout.fileno.return_value = 7
            process.kill.side_effect = OSError("DUMMY_SECRET")
            process.wait.side_effect = OSError("DUMMY_SECRET")
            process.stdout.close.side_effect = OSError("DUMMY_SECRET")
            primary = MemoryError()
            process.stdout.read.side_effect = primary
            def peek(handle, unused, size, read, available, left):
                ctypes.cast(available, ctypes.POINTER(w.D)).contents.value = w._LIMIT+1 if overflow else 1
                return True
            api.k.PeekNamedPipe.side_effect = peek
            file, guard = Mock(handle=9), Mock()
            file.close.side_effect = OSError("DUMMY_SECRET")
            guard.close.side_effect = OSError("DUMMY_SECRET")
            file.read.side_effect = lambda: w._index_bytes(api, w._SOURCE, {})
            fixture = w._Fixture(api, "user")
            fixture.root = Path("owned")/(w._PREFIX+"0"*32)
            fixture.ledger = {"known": {"bytes": 11}}
            fixture.guards = [Mock(), Mock()]
            fixture_guards = fixture.guards.copy()
            for item in fixture_guards:
                item.close.side_effect = OSError("DUMMY_SECRET")
            fixture.create = lambda: w._source_bytes(api, Path("source.py"))
            with self.subTest(overflow=overflow), \
                 patch.dict(sys.modules, {"msvcrt": SimpleNamespace(get_osfhandle=lambda _: 7)}), \
                 patch.object(w.subprocess, "Popen", return_value=process), \
                 patch.object(w, "_api", return_value=api), patch.object(w, "_runtime", return_value={}), \
                 patch.object(w, "_source_pin", return_value=[]), patch.object(w, "_Fixture", return_value=fixture), \
                 patch.object(w, "_Bound", side_effect=lambda api, path, **kw: guard if kw["directory"] else file), \
                 patch.object(Path, "exists", side_effect=AssertionError), patch.object(Path, "stat", side_effect=AssertionError), \
                 patch.object(Path, "iterdir", side_effect=AssertionError), patch.object(Path, "read_bytes", side_effect=AssertionError), \
                 patch.object(w, "_temporary_path", side_effect=AssertionError):
                report = w.run_control_harness()
            self.assertEqual(report["reason"], "source_index_size" if overflow else "resource_failure")
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["retained_existence"], "unverified")
            self.assertEqual(report["teardown"]["failure_count"], 9)
            self.assertEqual(len(report["teardown"]["reasons"]), 8)
            self.assertEqual(report["teardown"]["omitted_count"], 1)
            self.assertEqual(report["teardown"]["first_reason"], "index_process_kill")
            self.assertNotIn("DUMMY", json.dumps(report))
            self.assertEqual(api.k.CloseHandle.call_count, 2)
            for item in (file, guard, *fixture_guards):
                item.close.assert_called_once_with()
            process.kill.assert_called_once()
            process.wait.assert_called_once()
            process.stdout.close.assert_called_once()
            self.assertEqual(fixture.guards, fixture_guards)

    def test_no_primary_source_or_index_close_failure_cannot_return_success(self):
        api, file, guard = Mock(), Mock(handle=9), Mock()
        api.call.side_effect = lambda ok, reason: w._need(ok, reason)
        file.read.return_value = b""
        file.close.side_effect = OSError("DUMMY_SECRET")
        guard.close.side_effect = OSError("DUMMY_SECRET")
        with patch.object(w, "_Bound", side_effect=lambda api, path, **kw: guard if kw["directory"] else file), \
             self.assertRaises(w._Failure) as caught:
            w._source_bytes(api, Path("source.py"))
        self.assertEqual(caught.exception.reason, "owned_teardown_failed")
        self.assertEqual(caught.exception.teardown.count, 2)
        process = Mock()
        process.poll.return_value, process.wait.return_value = 0, 0
        process.stdout.close.side_effect = OSError("DUMMY_SECRET")
        def peek(handle, unused, size, read, available, left):
            ctypes.cast(available, ctypes.POINTER(w.D)).contents.value = 0
            return True
        api.k.PeekNamedPipe.side_effect = peek
        with patch.dict(sys.modules, {"msvcrt": SimpleNamespace(get_osfhandle=lambda _: 7)}), \
             patch.object(w.subprocess, "Popen", return_value=process), self.assertRaises(w._Failure) as caught:
            w._index_bytes(api, w._SOURCE, {})
        self.assertEqual(caught.exception.reason, "owned_teardown_failed")
        self.assertEqual(caught.exception.teardown.report()["reasons"], ["index_pipe_close"])

    def test_temp_path_counts_utf16_units_and_rejects_unpaired_surrogates(self):
        for value in ("C:\\candidate-\U0001f600\\", "C:\\candidate-\ud800\\", "C:\\candidate-\udfff\\"):
            def query(size, buffer):
                buffer.value = value
                return len(value.encode("utf-16-le", errors="surrogatepass")) // 2
            api = SimpleNamespace(k=SimpleNamespace(GetTempPath2W=query))
            with self.subTest(value=ascii(value)), patch.object(w, "Path", PureWindowsPath):
                if "\U0001f600" in value:
                    self.assertEqual(w._temporary_path(api), PureWindowsPath(value))
                else:
                    with self.assertRaises(w._Failure) as caught:
                        w._temporary_path(api)
                    self.assertEqual(caught.exception.reason, "temp_path_result")

    def test_replace_control_requires_existing_owned_destination_and_restores_source(self):
        for fail in (False, True, "no_op"):
            root, raw = Path("owned"), b"B1-control\n"
            original = {"file_id": "source", "directory": False, "volume": 1}
            ledger = {"control/data.bin": {"identity": original, "sd": {}, "sha256": w._sha(raw), "bytes": len(raw)}}
            initial = deepcopy(ledger)
            state = {"control/data.bin": (original, raw)}
            def create(owned, name, data, mode):
                self.assertNotIn(name, state)
                self.assertIs(owned.ledger, ledger)
                state[name] = ({"file_id": "destination", "directory": False, "volume": 1}, data)
                ledger[name] = {"identity": state[name][0], "sd": {}, "sha256": w._sha(data), "bytes": len(data)}
            def bind(api, path, **kwargs):
                identity, data = state[path.relative_to(root).as_posix()]
                return Mock(identity=identity, read=Mock(return_value=data))
            def replace(source, target, flags):
                self.assertEqual(flags, 1)
                self.assertIn("control/replaced.bin", ledger)
                self.assertIn("control/replaced.bin", state)
                self.assertNotEqual(state["control/replaced.bin"], state["control/data.bin"])
                if fail == "no_op":
                    return True  # Claimed success without replacing must fail readback.
                if fail:
                    return False
                state["control/replaced.bin"] = state.pop("control/data.bin")
                return True
            def restore(source, target):
                state["control/data.bin"] = state.pop("control/replaced.bin")
                return True
            api = Mock()
            api.security.return_value = {}
            api.call.side_effect = lambda ok, reason: w._need(ok, reason)
            api.k.MoveFileExW.side_effect = replace
            api.k.MoveFileW.side_effect = restore
            def lstat(path):
                if path.relative_to(root).as_posix() not in state:
                    error = FileNotFoundError()
                    error.winerror = 2
                    raise error
                return object()
            with self.subTest(fail=fail), patch.object(w._Fixture, "file", create), \
                 patch.object(w, "_Bound", side_effect=bind), \
                 patch.object(Path, "lstat", autospec=True, side_effect=lstat):
                if fail:
                    with self.assertRaises(w._Failure):
                        w._replace_control(api, root, "user", ledger)
                else:
                    w._replace_control(api, root, "user", ledger)
            api.k.MoveFileExW.assert_called_once()
            if fail:
                api.k.MoveFileW.assert_not_called()
                self.assertEqual(set(state), {"control/data.bin", "control/replaced.bin"})
                self.assertIn("control/replaced.bin", ledger)
            else:
                self.assertEqual(ledger, initial)
                self.assertEqual(state, {"control/data.bin": (original, raw)})
            api.k.DeleteFileW.assert_not_called()
            api.k.RemoveDirectoryW.assert_not_called()

    def test_source_size_limit_precedes_content_read(self):
        for size in (w._LIMIT, w._LIMIT+1, 1 << 32):
            api, bound = Mock(), Mock(handle=1)
            bound.read.return_value = b"x"  # A mismatched short read must also fail.
            def info(handle, pointer):
                obj = ctypes.cast(pointer, ctypes.POINTER(w._FileInfo)).contents
                obj.size_high, obj.size_low = size >> 32, size & 0xffffffff
                return True
            api.k.GetFileInformationByHandle.side_effect = info
            api.call.side_effect = lambda ok, reason: w._need(ok, reason)
            with self.subTest(size=size), \
                 patch.object(w, "_Bound", side_effect=lambda api, path, **kw: Mock() if kw["directory"] else bound), \
                 self.assertRaises(w._Failure):
                w._source_bytes(api, Path("source.py"))
            if size > w._LIMIT:
                bound.read.assert_not_called()
            else:
                bound.read.assert_called_once()
            bound.close.assert_called_once()

    def test_index_pipe_bounded_output_timeout_and_memory_failure(self):
        for case in ("ok", "overflow", "cumulative", "timeout", "memory"):
            api, process = Mock(), Mock()
            process.stdout.fileno.return_value = 7
            process.poll.return_value = None if case != "ok" else 0
            process.wait.return_value = 0
            process.stdout.read.side_effect = MemoryError() if case == "memory" else [b"raw"]
            amounts = iter([w._LIMIT+1] if case == "overflow" else [3, 2] if case == "cumulative" else [3, 0])
            def peek(handle, unused, size, read, available, left):
                ctypes.cast(available, ctypes.POINTER(w.D)).contents.value = next(amounts)
                return True
            api.k.PeekNamedPipe.side_effect = peek
            clock = [0, 11] if case == "timeout" else [0, 0, 0, 0]
            with self.subTest(case=case), patch.dict(sys.modules, {"msvcrt": SimpleNamespace(get_osfhandle=lambda _: 7)}), \
                 patch.object(w.subprocess, "Popen", return_value=process) as popen, \
                 patch.object(w, "_LIMIT", 4), \
                 patch.object(w.time, "monotonic", side_effect=clock):
                if case == "ok":
                    self.assertEqual(w._index_bytes(api, w._SOURCE, {}), b"raw")
                else:
                    with self.assertRaises(MemoryError if case == "memory" else w._Failure):
                        w._index_bytes(api, w._SOURCE, {})
            options = popen.call_args.kwargs
            self.assertEqual(options["stderr"], w.subprocess.DEVNULL)
            self.assertEqual(options["bufsize"], 0)
            process.stdout.close.assert_called_once()
            if case in ("overflow", "timeout"):
                process.stdout.read.assert_not_called()
            if case == "cumulative":
                process.stdout.read.assert_called_once_with(3)
            if case != "ok":
                process.kill.assert_called_once()
            else:
                process.stdout.read.assert_called_once_with(3)

    def test_resource_stop_has_no_source_temp_or_artifact_io(self):
        for failure in (MemoryError(), w._Failure("memory_budget"), w._Failure("source_size"),
                        w._Failure("source_index_size"), w._Failure("file_size")):
            api = Mock()
            api.profile.return_value = parent_profile()
            fixture = Mock(root=Path("owned")/(w._PREFIX+"0"*32), ledger={"known": {"bytes": 11}})
            fixture.create.side_effect = failure
            with self.subTest(failure=type(failure).__name__), patch.object(w, "_api", return_value=api), \
                 patch.object(w, "_runtime", return_value={}) as runtime, patch.object(w, "_source_pin", return_value=[]) as source, \
                 patch.object(w, "_Fixture", return_value=fixture), \
                 patch.object(Path, "exists", side_effect=AssertionError), patch.object(Path, "stat", side_effect=AssertionError), \
                 patch.object(Path, "iterdir", side_effect=AssertionError), patch.object(Path, "read_bytes", side_effect=AssertionError), \
                 patch.object(w, "_temporary_path", side_effect=AssertionError), patch.object(w, "_Bound", side_effect=AssertionError):
                report = w.run_control_harness()
            self.assertEqual(report["status"], "failed")
            self.assertIsNone(report["retained_exists"])
            self.assertEqual(report["retained_existence"], "unverified")
            self.assertEqual(report["known_bytes"], 11)
            runtime.assert_called_once()
            source.assert_called_once()
            fixture.check.assert_not_called()
            fixture.cleanup.assert_not_called()
            fixture.close.assert_called_once()

    def test_source_pin_retains_raw_index_equality_and_stops_on_resource_failure(self):
        for failure in (None, MemoryError(), w._Failure("source_size")):
            with self.subTest(failure=type(failure).__name__), patch.object(w, "_api", return_value=Mock()), \
                 patch.object(w, "_source_bytes", return_value=b"raw", side_effect=failure) as read, \
                 patch.object(w, "_index_bytes", return_value=b"raw") as index, \
                 patch.object(Path, "read_bytes", side_effect=AssertionError), \
                 patch.object(w.subprocess, "run", side_effect=AssertionError):
                if failure:
                    with self.assertRaises(type(failure)):
                        w._source_pin()
                    self.assertEqual(read.call_count, 1)
                    index.assert_not_called()
                else:
                    self.assertEqual(len(w._source_pin()), 2)
                    self.assertEqual(index.call_count, 2)
        with patch.object(w, "_api", return_value=Mock()), patch.object(w, "_source_bytes", return_value=b"raw"), \
             patch.object(w, "_index_bytes", return_value=b"different"), self.assertRaises(w._Failure) as caught:
            w._source_pin()
        self.assertEqual(caught.exception.reason, "source_index_bytes")

    def test_memory_error_during_source_read_or_index_never_rereads(self):
        api, bound = Mock(), Mock(handle=1)
        bound.read.side_effect = MemoryError()
        api.call.side_effect = lambda ok, reason: w._need(ok, reason)
        with patch.object(w, "_Bound", side_effect=lambda api, path, **kw: Mock() if kw["directory"] else bound), \
             self.assertRaises(MemoryError):
            w._source_bytes(api, Path("source.py"))
        bound.read.assert_called_once()
        bound.check.assert_not_called()
        bound.close.assert_called_once()
        with patch.object(w, "_api", return_value=Mock()), patch.object(w, "_source_bytes", return_value=b"raw") as read, \
             patch.object(w, "_index_bytes", side_effect=MemoryError()) as index, self.assertRaises(MemoryError):
            w._source_pin()
        read.assert_called_once()
        index.assert_called_once()

    def test_temp_path_api_has_fixed_wide_signature_and_no_fallback(self):
        kernel = Mock()
        with patch.object(w.os, "name", "nt"), patch.object(w.C, "WinDLL", return_value=kernel, create=True):
            w._Win()
        self.assertIs(kernel.GetTempPath2W.restype, w.D)
        self.assertEqual(kernel.GetTempPath2W.argtypes, [w.D, ctypes.POINTER(ctypes.c_wchar)])
        kernel.GetTempPath2W.assert_not_called()
        del kernel.GetTempPath2W
        with patch.object(w.os, "name", "nt"), patch.object(w.C, "WinDLL", return_value=kernel, create=True), \
             self.assertRaises(w._Failure) as caught:
            w._Win()
        self.assertEqual(caught.exception.reason, "temp_path_api_unavailable")

    def test_temp_path_ignores_python_temp_cache_and_never_probes_candidates(self):
        # Poison a cold/warm Python temp module without importing or using it.
        # Every environment value is synthetic; no outside object is created.
        for cache in (None, r"C:\foreign-cache"):
            poison = SimpleNamespace(tempdir=cache, gettempdir=Mock(side_effect=AssertionError),
                                     _get_default_tempdir=Mock(side_effect=AssertionError))
            def query(size, buffer):
                self.assertEqual(size, 32768)
                buffer.value = "C:\\candidate\\"
                return len(buffer.value)
            api = SimpleNamespace(k=SimpleNamespace(GetTempPath2W=Mock(side_effect=query)))
            with self.subTest(cache=cache), patch.dict(sys.modules, {"tempfile": poison}), \
                 patch.dict(os.environ, {"TMP": r"\\foreign\share", "TEMP": r"C:\foreign:stream",
                                         "TMPDIR": r"C:\foreign-repository"}), \
                 patch.object(w, "Path", PureWindowsPath), \
                 patch.object(os, "open", side_effect=AssertionError), \
                 patch.object(os, "unlink", side_effect=AssertionError), \
                 patch.object(w, "_Bound", side_effect=AssertionError):
                self.assertEqual(w._temporary_path(api), PureWindowsPath(r"C:\candidate"))
            api.k.GetTempPath2W.assert_called_once()
            poison.gettempdir.assert_not_called()
            poison._get_default_tempdir.assert_not_called()
            self.assertEqual(poison.tempdir, cache)

    def test_bad_temp_api_results_reject_before_any_object_operation(self):
        cases = [(0, ""), (32768, ""), (32769, ""), (4, "C:\\"), (3, "abc"),
                 (None, "\\\\server\\share\\"), (None, "relative\\"),
                 (None, "C:\\foreign:stream\\"), (None, "C:\\foreign.\\"),
                 (None, "C:\\a\\..\\foreign\\")]
        for size, value in cases:
            def query(capacity, buffer):
                buffer.value = value
                return len(value) if size is None else size
            api = Mock()
            api.k.GetTempPath2W.side_effect = query
            fixture = w._Fixture(api, "user")
            with self.subTest(size=size, value=value), patch.object(w, "Path", PureWindowsPath), \
                 patch.object(w, "_Bound", side_effect=AssertionError) as bound, \
                 patch.object(fixture, "directory", side_effect=AssertionError) as create, \
                 self.assertRaises(w._Failure):
                fixture.create()
            bound.assert_not_called()
            create.assert_not_called()
            self.assertIsNone(fixture.root)
            self.assertEqual(fixture.ledger, {})
            self.assertEqual(len(api.mock_calls), 1)  # Path query only; no native mutation.

    def test_temp_ancestry_faults_cannot_create_delete_or_change_acl(self):
        temporary = PureWindowsPath(r"C:\candidate\leaf")
        for failed_index in range(3):
            for reason in ("object_reparse_or_type", "volume_not_local_ntfs", "mapped_drive", "object_path_changed"):
                api = Mock()
                fixture = w._Fixture(api, "user")
                opened = []
                def bind(api, path, *, directory):
                    self.assertTrue(directory)
                    if len(opened) == failed_index:
                        raise w._Failure(reason)
                    guard = Mock(path=path)
                    opened.append(guard)
                    return guard
                with self.subTest(index=failed_index, reason=reason), \
                     patch.object(w, "_temporary_path", return_value=temporary), \
                     patch.object(w, "_Bound", side_effect=bind), \
                     patch.object(fixture, "directory", side_effect=AssertionError) as create, \
                     patch.object(os, "open", side_effect=AssertionError), \
                     patch.object(os, "unlink", side_effect=AssertionError), self.assertRaises(w._Failure):
                    fixture.create()
                self.assertIsNone(fixture.root)
                self.assertEqual(fixture.ledger, {})
                create.assert_not_called()
                self.assertEqual(api.mock_calls, [])
                fixture.close()
                for guard in opened:
                    guard.close.assert_called_once_with()

    def test_repository_and_formal_temp_candidates_reject_before_root_creation(self):
        for suffix in ("", "artifacts/anomaly-multiseed-v03-holdout", "artifacts/anomaly-multiseed-v03-audit"):
            temporary = w._ROOT / suffix
            api, fixture = Mock(), None
            fixture = w._Fixture(api, "user")
            # Synthetic metadata only, including absent formal roots; no mkdir/unlink.
            with self.subTest(suffix=suffix), patch.object(w, "_temporary_path", return_value=temporary), \
                 patch.object(w, "_Bound", return_value=Mock()), \
                 patch.object(Path, "exists", autospec=True, side_effect=lambda p: p == w._ROOT/".git"), \
                 patch.object(fixture, "directory", side_effect=AssertionError) as create, \
                 patch.object(os, "open", side_effect=AssertionError), \
                 patch.object(os, "unlink", side_effect=AssertionError), self.assertRaises(w._Failure) as caught:
                fixture.create()
            self.assertEqual(caught.exception.reason, "temp_in_repository")
            self.assertIsNone(fixture.root)
            self.assertEqual(fixture.ledger, {})
            create.assert_not_called()
            self.assertEqual(api.mock_calls, [])
            fixture.close()

    def test_child_uses_same_temp_query_and_scope_rejects_before_objects(self):
        api = Mock()
        def query(size, buffer):
            buffer.value = "C:\\candidate\\"
            return len(buffer.value)
        api.k.GetTempPath2W.side_effect = query
        with patch.object(w, "_api", return_value=api), patch.object(w, "_runtime"), \
             patch.object(w, "Path", PureWindowsPath), patch.object(w, "_Bound", side_effect=AssertionError), \
             self.assertRaises(w._Failure) as caught:
            w._child_main(PureWindowsPath(r"C:\foreign")/(w._PREFIX+"0"*32))
        self.assertEqual(caught.exception.reason, "child_scope")
        self.assertEqual(len(api.mock_calls), 1)

    def test_prefix_inventory_uses_same_side_effect_free_query(self):
        api, temporary = Mock(), Mock()
        temporary.iterdir.return_value = [SimpleNamespace(name="foreign"), SimpleNamespace(name=w._PREFIX+"known")]
        with patch.object(w, "_api", return_value=api), patch.object(w, "_temporary_path", return_value=temporary) as query:
            self.assertEqual(_prefix_inventory(), [w._PREFIX+"known"])
        query.assert_called_once_with(api)
        self.assertEqual(api.mock_calls, [])

    def test_no_temp_module_dependency_in_implementation_child_or_helpers(self):
        for path in (w._SOURCE, w._CHILD, Path(__file__)):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertNotIn("tempfile", [item.name.split(".")[0] for item in node.names])
                if isinstance(node, ast.ImportFrom):
                    self.assertNotEqual((node.module or "").split(".")[0], "tempfile")
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    self.assertNotEqual(node.func.attr, "gettempdir")

    def test_non_windows_rejects_before_loading_or_creating(self):
        with patch.object(w.os, "name", "posix"), patch.object(w, "_Win", side_effect=AssertionError), \
             patch.object(w, "_runtime", side_effect=AssertionError), patch.object(w, "_Fixture", side_effect=AssertionError):
            value = w.run_control_harness()
        self.assertEqual(value["reason"], "unsupported_platform")
        self.assertFalse(value["formal_permission"])

    def test_public_api_has_no_path_token_acl_or_override_parameters(self):
        self.assertEqual(str(inspect.signature(w.run_control_harness)), "()")
        self.assertEqual(w.__all__, ["run_control_harness"])
        with self.assertRaises(TypeError):
            w.run_control_harness("forbidden")

    def test_campaign_gate_unchanged(self):
        with self.assertRaisesRegex(rt.IntegrityError, "s4_acceptance_not_frozen"):
            rt.require_campaign_acceptance()
        result = w._result_status()
        for key in ("formal_permission", "native_accepted", "s4_accepted"):
            self.assertIs(result[key], False)
        self.assertEqual(result["windows_3_12"], "not_run/runtime_unavailable")

    def test_owner_and_admin_are_explicit_non_goals(self):
        self.assertTrue({"owner-admin", "write-dac-write-owner", "privileged-writer", "worm", "power-loss", "sandbox", "publication"} <= set(w._NON_GOALS))

    def test_parent_expected_limited_uac_is_not_elevated_or_rc_token(self):
        w._validate_parent(parent_profile())
        for change in ({"elevated": 1}, {"integrity": "S-1-16-12288"}, {"restricted": [[w._RC, 7]]},
                       {"elevation_type": 2}, {"groups": [["S-1-5-32-544", 4]]}, {"type": 2}):
            with self.subTest(change=change), self.assertRaises(w._Failure):
                w._validate_parent({**parent_profile(), **change})

    def test_restricted_fixed_policy_and_same_account_logon(self):
        w._validate_restricted(parent_profile(), restricted_profile())
        self.assertEqual(w._shape(restricted_profile())["authentication_id"], "3")
        for change in ({"token_id": "1"}, {"user": ["wrong", 0]}, {"session": 2},
                       {"authentication_id": "other"}, {"restricted": []}, {"elevated": 1},
                       {"privileges": [["SeDebugPrivilege", 2]]}, {"groups": [["S-1-5-32-544", 4]]}):
            with self.subTest(change=change), self.assertRaises(w._Failure):
                w._validate_restricted(parent_profile(), {**restricted_profile(), **change})

    def test_compatibility_restrictions_reject_missing_extra_duplicate_and_bad_attributes(self):
        parent, child = parent_profile(), restricted_profile()
        expected = [[w._COMPATIBILITY_SID, 7], [w._RC, 7]]
        self.assertEqual(w._RESTRICTING_SIDS, (w._RC, "S-1-1-0"))
        for restricted in (expected[:1], expected[1:], list(reversed(expected)),
                           expected + [expected[1]], expected + [["S-1-5-11", 7]],
                           [["S-1-15-2-2", 7], [w._RC, 7]],
                           [["S-1-15-2-1", 7], [w._RC, 7]],
                           [[w._RC, 7], ["S-1-5-18", 7]],
                           [[w._COMPATIBILITY_SID, 7], [w._RC, 0]],
                           [[w._COMPATIBILITY_SID, 4], [w._RC, 7]]):
            with self.subTest(restricted=restricted), self.assertRaises(w._Failure) as caught:
                w._validate_restricted(parent, {**child, "restricted": restricted})
            self.assertEqual(caught.exception.reason, "restricted_sids")

    def test_native_profile_buffer_order_matches_compatibility_validation(self):
        # Run the real profile parser on owned fake buffers, including its SID sort.
        api = Mock()
        identifiers = {501: parent_profile()["user"][0], 502: "S-1-16-8192",
                       503: "S-1-5-32-544", 504: w._RC, 505: w._COMPATIBILITY_SID}
        api.sid.side_effect = identifiers.__getitem__
        def groups(rows):
            raw = ctypes.create_string_buffer(w._Groups.rows.offset + len(rows) * ctypes.sizeof(w._SidAttr))
            w.D.from_buffer(raw).value = len(rows)
            for target, (sid, attributes) in zip(
                    (w._SidAttr * len(rows)).from_buffer(raw, w._Groups.rows.offset), rows):
                target.sid, target.attributes = sid, attributes
            return raw
        def sid(pointer):
            raw = ctypes.create_string_buffer(ctypes.sizeof(w._SidAttr))
            w._SidAttr.from_buffer(raw).sid = pointer
            return raw
        stats = ctypes.create_string_buffer(ctypes.sizeof(w._Statistics))
        values = w._Statistics.from_buffer(stats)
        values.token.low, values.modified.low, values.authentication.low = 4, 5, 3
        buffers = {1: sid(501), 25: sid(502), 2: groups([(503, 0x10)]),
                   3: ctypes.create_string_buffer(w._Privileges.rows.offset), 10: stats}
        buffers.update({key: ctypes.create_string_buffer(value.to_bytes(4, "little"), 4)
                        for key, value in ((8, 1), (20, 0), (18, 3), (12, 1), (21, 1))})
        api.query.side_effect = lambda token, kind: buffers[kind]
        for native_order in ([(504, 7), (505, 7)], [(505, 7), (504, 7)]):
            buffers[11] = groups(native_order)
            profile = w._Win.profile(api, 401)
            self.assertEqual(profile["restricted"], [[w._COMPATIBILITY_SID, 7], [w._RC, 7]])
            parent = {**parent_profile(), "authentication_id": profile["authentication_id"]}
            w._validate_restricted(parent, profile)
        buffers[11] = groups([(504, 7), (504, 7)])
        with self.assertRaises(w._Failure) as caught:
            w._Win.profile(api, 401)
        self.assertEqual(caught.exception.reason, "token_duplicate_sid")

    def compatibility_api(self, *, fail_compatibility_sid=False):
        api = Mock()
        api.call.side_effect = lambda ok, reason: w._need(ok, reason)
        api.profile.return_value = restricted_profile()
        ids = {"S-1-5-32-544": 701, w._RC: 702, w._COMPATIBILITY_SID: 703}
        def sid(value, pointer):
            if fail_compatibility_sid and value == w._COMPATIBILITY_SID:
                return False
            pointer._obj.value = ids[value]
            return True
        def create(parent, flags, disable_count, disable, delete_count, delete, count, restrict, output):
            self.assertEqual((parent, flags, disable_count, delete_count, delete, count),
                             (401, 9, 1, 0, None, 2))
            self.assertEqual([(row.sid, row.attributes) for row in disable], [(701, 0)])
            self.assertEqual([(row.sid, row.attributes) for row in restrict], [(702, 0), (703, 0)])
            output._obj.value = 402
            return True
        api.a.ConvertStringSidToSidW.side_effect = sid
        api.a.CreateRestrictedToken.side_effect = create
        return api

    def test_core_creates_fixed_compatibility_token_and_releases_all_sid_allocations(self):
        api = self.compatibility_api()
        self.assertEqual(w._Win.restricted(api, 401, parent_profile()), 402)
        api.a.CreateRestrictedToken.assert_called_once()
        self.assertEqual([call.args[0].value for call in api.k.LocalFree.call_args_list], [701, 702, 703])
        api.close.assert_not_called()

    def test_core_compatibility_sid_failure_never_creates_partial_token(self):
        api = self.compatibility_api(fail_compatibility_sid=True)
        with self.assertRaises(w._Failure):
            w._Win.restricted(api, 401, parent_profile())
        api.a.CreateRestrictedToken.assert_not_called()
        self.assertEqual([call.args[0].value for call in api.k.LocalFree.call_args_list], [701, 702])
        api.close.assert_not_called()

    def test_duplicate_token_luid_is_not_assumed_equal(self):
        a, b = restricted_profile(), restricted_profile()
        b.update(token_id="other", modified_id="other", type=2)
        self.assertEqual(w._shape(a), w._shape(b))
        b["groups"] = []
        self.assertNotEqual(w._shape(a), w._shape(b))

    def test_accesscheck_api_failure_is_not_a_denial(self):
        denial = dict(api_success=True, mask=2, access_status=False, granted=0, privileges_used=0)
        w._check_access(denial, 2, False)
        for change in ({"api_success": False}, {"granted": 2}, {"access_status": True}, {"mask": 4}, {"privileges_used": 1}):
            with self.subTest(change=change), self.assertRaises(w._Failure):
                w._check_access({**denial, **change}, 2, False)

    def test_positive_accesscheck_is_required(self):
        with self.assertRaises(w._Failure):
            w._check_access(dict(api_success=True, mask=2, access_status=False, granted=0, privileges_used=0), 2, True)

    def test_positive_operation_exception_stops_before_any_following_operation(self):
        errors = [OSError("DUMMY_PRIVATE"), w._Failure("object_open", 0),
                  w._Failure("mutation_api", 0), w._Failure("object_open", 5)]
        explicit_zero = OSError("DUMMY_PRIVATE")
        explicit_zero.winerror = 0
        errors.append(explicit_zero)
        for error in errors:
            api = Mock()
            api.k.CreateFileW.return_value = 7
            with self.subTest(error=type(error), reason=getattr(error, "reason", None)), \
                 patch.object(w, "_Bound", side_effect=error) as bound, self.assertRaises(BaseException) as caught:
                w._operations(api, Path("owned"), "user", {})
            self.assertIs(caught.exception, error)
            bound.assert_called_once()
            api.k.SetFileTime.assert_not_called()
            api.k.MoveFileW.assert_not_called()

    def test_right_open_failure_stops_before_mutation_even_without_last_error(self):
        for error in (0, 5):
            api = Mock()
            api.k.CreateFileW.return_value = ctypes.c_void_p(-1).value
            with self.subTest(error=error), patch.object(w.C, "get_last_error", return_value=error), \
                 patch.object(w, "_Bound") as bound, self.assertRaises(w._Failure):
                w._operations(api, Path("owned"), "user", {})
            api.k.CreateFileW.assert_called_once()
            api.close.assert_not_called()
            bound.assert_not_called()

    def test_each_positive_right_open_retains_its_case_and_native_error(self):
        root = Path("owned")
        cases = [("file_right_open", key, mask, root / "control/data.bin") for key, mask in w._FILE_RIGHTS.items()]
        cases += [("directory_right_open", key, mask, root / "control") for key, mask in w._DIR_RIGHTS.items()]
        for index, (category, key, mask, path) in enumerate(cases):
            api = Mock()
            def opening(name, requested, *args):
                return ctypes.c_void_p(-1).value if (name, requested) == (str(path), mask) else 7
            api.k.CreateFileW.side_effect = opening
            with self.subTest(category=category, key=key), \
                 patch.object(w.C, "get_last_error", return_value=32), \
                 patch.object(w, "_Bound") as bound, self.assertRaises(w._Failure) as caught:
                w._operations(api, root, "user", {})
            self.assertEqual((caught.exception.reason, caught.exception.error), ("operation_unexpected", 32))
            self.assertEqual(w._child_failure_diagnostic(w._child_failure_exit(caught.exception)),
                             {"phase": "child_call", "reason": "operation_unexpected",
                              "operation_case": f"control.{category}.{key}", "winerror": 32})
            self.assertEqual(api.k.CreateFileW.call_count, index + 1)
            self.assertEqual(api.close.call_count, index)
            bound.assert_not_called()
            api.k.MoveFileW.assert_not_called()

    def test_resource_failure_of_right_open_reaches_child_stop_code(self):
        for error in w._CHILD_RESOURCE_ERRORS:
            api = Mock()
            api.k.CreateFileW.return_value = ctypes.c_void_p(-1).value
            with self.subTest(error=error), patch.object(w.C, "get_last_error", return_value=error), \
                 patch.object(w, "_Bound") as bound, self.assertRaises(w._Failure) as caught:
                w._operations(api, Path("owned"), "user", {})
            self.assertEqual(caught.exception.error, error)
            self.assertEqual(w._child_failure_exit(caught.exception), 80)
            self.assertFalse(hasattr(caught.exception, "operation_case"))
            api.k.CreateFileW.assert_called_once()
            api.close.assert_not_called()
            bound.assert_not_called()

    def test_dacl_masks_and_no_inheritable_aces(self):
        for directory, mask in ((False, 0x10116), (True, 0x10156)):
            sddl, rows = w._dacl("S-1-5-21-1", "frozen", directory)
            self.assertTrue(sddl.startswith("D:P(D;;"))
            self.assertEqual(rows[0], [1, 0, mask, "S-1-1-0"])
            self.assertTrue(all(row[1] == 0 for row in rows))
            value = dict(protected=True, owner="S-1-5-21-1", group="group", aces=rows)
            w._verify_sd(value, "S-1-5-21-1", "frozen", directory)
            for field, changed in (("protected", False), ("owner", "other"), ("group", ""), ("aces", [])):
                with self.subTest(field=field), self.assertRaises(w._Failure):
                    w._verify_sd({**value, field: changed}, "S-1-5-21-1", "frozen", directory)

    def test_paths_reject_unc_ads_relative_and_aliases(self):
        for value in (r"\\server\share\x", r"C:\x:stream", "x", r"C:\x\..\y", "C:\\x.\\y", "C:\\x \\y"):
            with self.subTest(value=value), self.assertRaises(w._Failure):
                w._lexical(PureWindowsPath(value))
        w._lexical(PureWindowsPath(r"C:\temp\owned"))

    def test_fixture_name_escape(self):
        fixture = w._Fixture(None, "user")
        fixture.root = Path("/test-owned")
        for name in ("../x", "a/../../x", "/absolute", "C:\\x", "a:stream", "a/./x", "A"):
            with self.subTest(name=name), self.assertRaises(w._Failure):
                fixture.path(name)

    def test_ipc_bounded_canonical_no_duplicates_or_numbers(self):
        self.assertEqual(w._json(w._canonical({"x": 1})), {"x": 1})
        for raw in (b"x"*(w._LIMIT+1), b'{"x":1,"x":2}', b'{"x":NaN}', b'{ "x":1}', b'[] trailing'):
            with self.assertRaises(w._Failure):
                w._json(raw)

    def test_ipc_replay_pid_profile_and_source_spoof_fail(self):
        identity, profile, access, source = {"pid": 11}, restricted_profile(), {}, []
        report = dict(version="b1.2", nonce="nonce", request_sha256="digest", identity=identity, profile=profile,
                      source=source, access=access, operations=w._expected_operations(), no_impersonation=True,
                      isolated=True, no_bytecode=True, inherited_handles=False)
        w._verify_report(report, identity, "nonce", "digest", profile, access, source)
        for change in ({"version": "b1.1"}, {"nonce": "replay"}, {"request_sha256": "wrong"}, {"identity": {"pid": 12}},
                       {"profile": {}}, {"source": ["spoof"]}, {"access": {"wrong": 0}},
                       {"inherited_handles": True}, {"operations": {}}, {"new_key": 1}):
            with self.subTest(change=change), self.assertRaises(w._Failure):
                w._verify_report({**report, **change}, identity, "nonce", "digest", profile, access, source)

    def test_failure_redaction_including_dummy_secret_and_memoryerror(self):
        for error in (OSError("DUMMY_SECRET_TOKEN=C:\\private\\argv"), MemoryError("DUMMY_SECRET")):
            with patch.object(w, "_api", side_effect=error):
                result = w.run_control_harness()
            raw = json.dumps(result)
            self.assertNotIn("DUMMY", raw)
            self.assertNotIn("private", raw)
            self.assertNotIn("traceback", raw)
            self.assertEqual(result["status"], "failed")

    def test_failed_fixture_cleanup_cannot_start_when_check_fails(self):
        fixture = w._Fixture(Mock(), "user")
        fixture.check = Mock(side_effect=w._Failure("unknown_fixture_object"))
        with patch.object(w, "_Bound", side_effect=AssertionError), self.assertRaises(w._Failure):
            fixture.cleanup()
        fixture.api.assert_not_called()

    def test_no_recursive_cleanup_or_publication_primitives(self):
        source = w._SOURCE.read_text(encoding="utf-8")
        for text in ("shutil.rmtree(", "TemporaryDirectory(", "CreateProcessWithLogon", "SetNamedSecurityInfo", "os.link("):
            self.assertNotIn(text, source)
        self.assertNotIn("anomaly-multiseed-v03-holdout", source)

    def test_abi_sizes_are_win64_and_not_host_c_long(self):
        self.assertEqual(ctypes.sizeof(w.D), 4)
        self.assertEqual(ctypes.sizeof(w._FileInfo), 52)
        if ctypes.sizeof(w.H) == 8:
            self.assertEqual(ctypes.sizeof(w._Startup), 104)
            self.assertEqual(ctypes.sizeof(w._Process), 24)

    def test_native_identity_reparse_hardlink_network_and_handle_faults(self):
        # Fake values exercise rejection only; never counted as native evidence.
        settings = dict(attributes=32, links=1, filesystem="NTFS", drive=3,
                        device=r"\Device\HarddiskVolume3", file_id=1, inherit=0, info_ok=True)
        bound = object.__new__(w._Bound)
        bound.path, bound.directory, bound.handle = PureWindowsPath(r"C:\temp\data.bin"), False, 7
        def info(handle, pointer):
            obj = ctypes.cast(pointer, ctypes.POINTER(w._FileInfo)).contents
            obj.attributes, obj.links = settings["attributes"], settings["links"]
            return settings["info_ok"]
        def file_id(handle, kind, pointer, size):
            obj = ctypes.cast(pointer, ctypes.POINTER(w._FileId)).contents
            obj.volume, obj.identifier[0] = 3, settings["file_id"]
            return True
        def final(handle, buffer, length, flags):
            buffer.value = "\\\\?\\"+str(bound.path)
            return len(buffer.value)
        def volume(handle, unused, zero, serial, maximum, flags, buffer, size):
            buffer.value = settings["filesystem"]
            return True
        def device(drive, buffer, length):
            buffer.value = settings["device"]
            return len(buffer.value)
        def inherit(handle, pointer):
            ctypes.cast(pointer, ctypes.POINTER(w.D)).contents.value = settings["inherit"]
            return True
        bound.api = SimpleNamespace(call=lambda ok, reason: w._need(ok, reason), k=SimpleNamespace(
            GetFileInformationByHandle=info, GetFileInformationByHandleEx=file_id, GetFinalPathNameByHandleW=final,
            GetVolumeInformationByHandleW=volume, GetDriveTypeW=lambda _: settings["drive"],
            QueryDosDeviceW=device, GetHandleInformation=inherit))
        self.assertEqual(bound.observe()["volume"], 3)
        for key, bad in (("attributes", 0x400), ("attributes", 16), ("attributes", 33), ("links", 2),
                         ("filesystem", "FAT32"), ("drive", 4), ("device", r"\??\D:\mapped"),
                         ("file_id", 0), ("inherit", 1), ("info_ok", False)):
            original = settings[key]
            settings[key] = bad
            with self.subTest(key=key, bad=bad), self.assertRaises(w._Failure):
                bound.observe()
            settings[key] = original

    def test_source_and_unsupported_runtime_failure_precedes_fixture(self):
        fake = Mock()
        for target in ("_runtime", "_source_pin"):
            with patch.object(w, "_api", return_value=fake), patch.object(w, "_runtime", return_value={}), \
                 patch.object(w, "_source_pin", return_value=[]), patch.object(w, target, side_effect=w._Failure("preflight_failed")), \
                 patch.object(w, "_Fixture", side_effect=AssertionError):
                report = w.run_control_harness()
            self.assertEqual(report["reason"], "preflight_failed")
            self.assertIsNone(report["retained_basename"])

    def test_failure_class_never_echoes_underlying_error(self):
        error = w._Failure("child_failed", child_exit_code=0xc0000142)
        self.assertEqual(str(error), "s4_b1_control_failed")
        self.assertEqual(error.error, 0)
        self.assertEqual(error.child_exit_code, 0xc0000142)


def _prefix_inventory():
    return sorted(p.name for p in w._temporary_path(w._api()).iterdir() if p.name.startswith(w._PREFIX))


@unittest.skipUnless(os.name == "nt", "Windows-only native control; NOT acceptance on Linux")
class NativeWindowsControls(unittest.TestCase):
    def test_held_identity_protected_acl_and_success_cleanup(self):
        before = _prefix_inventory()
        self.assertEqual(len(w._source_pin()), 2)  # Bounded, read-only index equality.
        api = w._api()
        token = api.token(api.k.GetCurrentProcess())
        fixture = None
        try:
            user = api.profile(token)["user"][0]
            fixture = w._Fixture(api, user)
            fixture.create()
            fixture.freeze()
            fixture.check()
            self.assertEqual(len(fixture.ledger), 6)
            self.assertTrue(all(x["sd"]["protected"] for x in fixture.ledger.values()))
            before_operations = deepcopy(fixture.ledger)
            # Same-parent native operation controls are useful but NOT evidence
            # for the separate restricted-child requirement below.
            operations = w._operations(api, fixture.root, user, fixture.ledger)
            self.assertEqual(operations, w._expected_operations())
            self.assertTrue(fixture.ledger == before_operations, "owned ledger changed")
            fixture.check()
            journal = fixture.cleanup(operations=w._canonical(operations))
            self.assertEqual(journal.report()["status"], "completed")
            self.assertEqual(journal.report()["confirmed_absent_objects"], 6)
            self.assertEqual(len(journal.private_snapshot[0]), 6)
            self.assertTrue(fixture.ledger == before_operations, "cleanup changed original ledger")
            self.assertTrue(all(bound is None for bound in fixture.cleanup_handles))
        finally:
            api.close(token)
            if fixture:
                fixture.close()
        self.assertEqual(before, _prefix_inventory())

    def test_real_restricted_child_control_required_not_mocked_or_skipped(self):
        before = _prefix_inventory()
        result = w.run_control_harness()
        # This assertion FAILS on missing privilege, DLL init failure or timeout.
        # Failure evidence remains, never relabeled as successful native testing.
        self.assertEqual(result["status"], "native_control_pass", result)
        self.assertEqual(result["success_residue_count"], 0)
        self.assertFalse(result["native_accepted"])
        self.assertEqual(before, _prefix_inventory())
        self.assertLess(result["resources"]["combined_peak_private_bytes"], w._MEMORY_LIMIT)


if __name__ == "__main__":
    unittest.main()
