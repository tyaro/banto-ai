"""Execute the fixed child wrapper with injected failures; no native API calls."""

import builtins
from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from banto_ai import _anomaly_v03_windows as w


class ChildDiagnostics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = compile(w._CHILD.read_text(encoding="utf-8"), str(w._CHILD), "exec")

    def invoke(self, error=None, *, bootstrap=False, isolated=True, actual_main=False):
        original_import = builtins.__import__
        fake_sys = SimpleNamespace(path=list(sys.path), argv=[str(w._CHILD), "C:/DUMMY_PRIVATE"],
                                   flags=SimpleNamespace(isolated=isolated), dont_write_bytecode=False)
        def importing(name, *args, **kwargs):
            if name == "sys":
                return fake_sys
            if bootstrap and name == "banto_ai._anomaly_v03_windows":
                raise error
            return original_import(name, *args, **kwargs)
        entry = Mock(side_effect=error, return_value=0)
        target = "_runtime" if actual_main else "_child_main"
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(w, target, entry), patch.object(w, "_api") as native, \
             patch("builtins.__import__", side_effect=importing), \
             patch.object(Path, "open") as opening, \
             redirect_stdout(stdout), redirect_stderr(stderr), self.assertRaises(SystemExit) as caught:
            exec(self.script, {"__name__": "__main__", "__file__": str(w._CHILD)})
        opening.assert_not_called()
        self.assertEqual((stdout.getvalue(), stderr.getvalue()), ("", ""))
        self.assertTrue(fake_sys.dont_write_bytecode)
        if not actual_main:
            native.assert_not_called()
        return caught.exception.code, entry

    def test_success_and_pre_call_validation(self):
        code, entry = self.invoke()
        self.assertEqual(code, 0)
        entry.assert_called_once_with(Path("C:/DUMMY_PRIVATE"))
        code, entry = self.invoke(isolated=False)
        self.assertEqual(w._child_failure_diagnostic(code),
                         {"phase": "bootstrap", "exception_class": "ValueError"})
        entry.assert_not_called()

    def test_real_child_entry_runtime_failure_reports_safe_reason_and_error(self):
        code, entry = self.invoke(w._Failure("runtime_pin", 5), actual_main=True)
        entry.assert_called_once_with()
        self.assertEqual(w._child_failure_diagnostic(code),
                         {"phase": "child_call", "reason": "runtime_pin", "winerror": 5})

    def test_recorded_runtime_pin_exit_keeps_its_original_reason_id(self):
        self.assertEqual(w._child_failure_diagnostic(278331392),
                         {"phase": "child_call", "reason": "runtime_pin", "winerror": 0})
        self.assertEqual(self.invoke(w._Failure("runtime_pin"))[0], 278331392)

    def test_bootstrap_and_child_exceptions_are_distinct_and_redacted(self):
        for kind in (*w._CHILD_EXCEPTION_TYPES, Exception):
            for bootstrap in (False, True):
                with self.subTest(kind=kind, bootstrap=bootstrap):
                    code, entry = self.invoke(kind("DUMMY_PRIVATE path/token"), bootstrap=bootstrap)
                    expected = kind.__name__ if kind is not Exception else "unknown_exception"
                    self.assertEqual(w._child_failure_diagnostic(code),
                                     {"phase": "bootstrap" if bootstrap else "child_call", "exception_class": expected})
                    self.assertNotIn("DUMMY_PRIVATE", repr(w._child_failure_diagnostic(code)))
                    self.assertEqual(entry.call_count, 0 if bootstrap else 1)

    def test_memory_and_resource_teardown_override_other_failures(self):
        failures = [MemoryError(), *(w._Failure(reason) for reason in w._RESOURCE_REASONS),
                    *(w._Failure("token_query", error) for error in w._CHILD_RESOURCE_ERRORS)]
        secondary = w._Failure("runtime_pin", 5)
        secondary.teardown = w._Teardown()
        secondary.teardown.record("source_guard_close", MemoryError())
        failures.append(secondary)
        for failure in failures:
            with self.subTest(kind=type(failure), reason=getattr(failure, "reason", None)):
                self.assertEqual(self.invoke(failure)[0], 80)
        self.assertEqual(self.invoke(MemoryError(), bootstrap=True)[0], 80)

    def test_reason_ids_are_unique_and_do_not_alias_native_or_resource_exits(self):
        self.assertLessEqual(len(w._CHILD_FAILURE_REASONS), 255)
        self.assertEqual(len(set(w._CHILD_FAILURE_REASONS)), len(w._CHILD_FAILURE_REASONS))
        codes = set()
        for reason in w._CHILD_FAILURE_REASONS:
            if reason in w._RESOURCE_REASONS:
                continue
            code, _ = self.invoke(w._Failure(reason, 5))
            self.assertNotIn(code, codes)
            self.assertLess(code, 2**31)
            codes.add(code)
            self.assertEqual(w._child_failure_diagnostic(code),
                             {"phase": "child_call", "reason": reason, "winerror": 5})
        for index, reason in enumerate(w._CHILD_LEGACY_REASONS):
            self.assertEqual(self.invoke(w._Failure(reason))[0], 32 + index)

    def test_os_resource_errors_stop_before_bootstrap_or_child_classification(self):
        for kind in (OSError, PermissionError):
            for number in w._CHILD_RESOURCE_ERRORS:
                failure = kind("DUMMY_PRIVATE")
                failure.winerror = number
                self.assertEqual(w._child_failure_exit(failure), 80)
                for bootstrap in (False, True):
                    with self.subTest(kind=kind, winerror=number, bootstrap=bootstrap):
                        self.assertEqual(self.invoke(failure, bootstrap=bootstrap)[0], 80)

    def test_unknown_reason_and_unrepresentable_error_are_not_echoed_or_truncated(self):
        for failure, reason in ((w._Failure("DUMMY_PRIVATE"), "unknown_failure"),
                                (w._Failure("token_query", -1), "unrepresentable_winerror"),
                                (w._Failure("token_query", 65536), "unrepresentable_winerror")):
            self.assertEqual(w._child_failure_diagnostic(self.invoke(failure)[0]),
                             {"phase": "child_call", "reason": reason})
        foreign = Exception("DUMMY_PRIVATE")
        foreign.reason = "child_scope"
        self.assertEqual(self.invoke(foreign)[0], 171)
        valid = w._child_failure_exit(w._Failure("token_query", 5))
        for code in (None, True, 0, 1, 80, 120, 0xc0000142, 0x10000005, 0x10ff0005,
                     valid + 2**32, valid - 2**32):
            self.assertIsNone(w._child_failure_diagnostic(code))


if __name__ == "__main__":
    unittest.main()
