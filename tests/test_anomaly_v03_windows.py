"""B1 controls; Windows prerequisite failure is a FAILURE, never a native pass.

No TemporaryDirectory/rmtree, campaign, generated observations or repository
artifact mutation. Successful native controls clean only their exact ledger.
Failed native controls print a safe basename/size and retain all evidence.
"""

from copy import deepcopy
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
    value.update(token_id="4", modified_id="5", restricted=[[w._RC, 7]],
                 privileges=[["SeChangeNotifyPrivilege", 3]])
    return value


class PureWindowsControls(unittest.TestCase):
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
            original = {"file_id": "source"}
            ledger = {"control/data.bin": {"identity": original, "sha256": w._sha(raw), "bytes": len(raw)}}
            initial = deepcopy(ledger)
            state = {"control/data.bin": (original, raw)}
            def create(owned, name, data, mode):
                self.assertNotIn(name, state)
                self.assertIs(owned.ledger, ledger)
                state[name] = ({"file_id": "destination"}, data)
                ledger[name] = {"identity": state[name][0], "sha256": w._sha(data), "bytes": len(data)}
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
            api.call.side_effect = lambda ok, reason: w._need(ok, reason)
            api.k.MoveFileExW.side_effect = replace
            api.k.MoveFileW.side_effect = restore
            with self.subTest(fail=fail), patch.object(w._Fixture, "file", create), \
                 patch.object(w, "_Bound", side_effect=bind), \
                 patch.object(Path, "exists", autospec=True, side_effect=lambda p: p.relative_to(root).as_posix() in state):
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
        report = dict(version="b1.1", nonce="nonce", request_sha256="digest", identity=identity, profile=profile,
                      source=source, access=access, operations=w._expected_operations(), no_impersonation=True,
                      isolated=True, no_bytecode=True, inherited_handles=False)
        w._verify_report(report, identity, "nonce", "digest", profile, access, source)
        for change in ({"nonce": "replay"}, {"request_sha256": "wrong"}, {"identity": {"pid": 12}},
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
            self.assertEqual(w._operations(api, fixture.root, user, fixture.ledger), w._expected_operations())
            self.assertEqual(fixture.ledger, before_operations)
            fixture.check()
            fixture.cleanup()
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
