"""B1 controls; Windows prerequisite failure is a FAILURE, never a native pass.

No TemporaryDirectory/rmtree, campaign, generated observations or repository
artifact mutation. Successful native controls clean only their exact ledger.
Failed native controls print a safe basename/size and retain all evidence.
"""

from copy import deepcopy
import ctypes
import inspect
import json
import os
from pathlib import Path, PureWindowsPath
import tempfile
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
    return sorted(p.name for p in Path(tempfile.gettempdir()).iterdir() if p.name.startswith(w._PREFIX))


@unittest.skipUnless(os.name == "nt", "Windows-only native control; NOT acceptance on Linux")
class NativeWindowsControls(unittest.TestCase):
    def test_held_identity_protected_acl_and_success_cleanup(self):
        before = _prefix_inventory()
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
            # Same-parent native operation controls are useful but NOT evidence
            # for the separate restricted-child requirement below.
            self.assertEqual(w._operations(api, fixture.root, user, fixture.ledger), w._expected_operations())
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
