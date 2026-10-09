"""New OS eligibility and snapshot risks; fake native APIs only."""

import copy
import ctypes
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_acceptance as acceptance
from banto_ai import _anomaly_v03_contract as contract
from banto_ai import _anomaly_v03_inventory as inventory
from banto_ai import _anomaly_v03_runtime as runtime
from tests import test_anomaly_v03_acceptance as acceptance_tests

ROOT = Path(__file__).resolve().parents[1]
check = acceptance_tests.check


def host(**overrides):
    return {"major": 10, "minor": 0, "build": 26300, "ubr": 9457, "product_type": 1,
            "architecture": "AMD64", "edition": "Core", "release": "26H2", **overrides}


class FakeFunction:
    def __init__(self, callback):
        self.callback = callback
    def __call__(self, *args):
        return self.callback(*args)


class WindowsRuntimePolicyTests(unittest.TestCase):
    def receipt(self, **overrides):
        value = acceptance_tests.AcceptanceContractTests()._windows_fixture()
        platform = value["stable"]["platform"]
        platform.update({"build": 26300, "ubr": 9457, "edition": "Core", "release": "26H2", **overrides})
        platform["version"] = f"10.0.{platform['build']}.{platform['ubr']}"
        return value

    def test_supported_build_patch_and_edition_are_observed_without_exact_pin(self):
        for build, ubr, edition, release in ((22000, 0, "Core", "21H2"),
                                           (26200, 9169, "Professional", "25H2"),
                                           (26300, 9457, "Enterprise", "26H2")):
            with self.subTest(build=build):
                runtime.validate_windows_host(**host(build=build, ubr=ubr, edition=edition, release=release))
                result = check(self.receipt(build=build, ubr=ubr, edition=edition, release=release))
                self.assertFalse(result["formal_permission"])
                self.assertFalse(result["execution_authenticated"])

    def test_unsupported_platform_and_malformed_observation_are_rejected(self):
        for overrides in ({"build": 19045}, {"product_type": 3}, {"architecture": "ARM64"},
                          {"major": 11}, {"ubr": -1}, {"build": True}, {"ubr": 2**32}, {"release": ""}):
            with self.subTest(overrides=overrides), self.assertRaises(runtime.IntegrityError):
                runtime.validate_windows_host(**host(**overrides))

    def test_capability_check_does_not_call_job_acl_or_publication_functions(self):
        def forbidden(*args):
            self.fail("behavior API executed")
        libraries = {library: SimpleNamespace(**{name: forbidden for name in names})
                     for library, names in runtime.WINDOWS_REQUIRED_EXPORTS.items()}
        observed = runtime.windows_capabilities(libraries, runtime.FILE_PERSISTENT_ACLS)
        self.assertEqual(observed["api_exports"], list(runtime.WINDOWS_EXPORT_IDS))
        self.assertFalse(observed["behavior_verified"])
        libraries["kernel32"].AssignProcessToJobObject = None
        with self.assertRaisesRegex(runtime.IntegrityError, "API unavailable"):
            runtime.windows_capabilities(libraries, runtime.FILE_PERSISTENT_ACLS)
        with self.assertRaisesRegex(runtime.IntegrityError, "ACL support"):
            runtime.windows_capabilities({}, 0)

    def test_current_receipt_requires_ntfs_acl_capabilities_and_consistent_version(self):
        for attack in ("filesystem", "remote", "flags", "huge-flags", "exports", "behavior", "version", "missing"):
            value = self.receipt()
            platform = value["stable"]["platform"]
            capabilities = platform["native_capabilities"]
            if attack == "filesystem": platform["filesystem"] = "FAT32"
            elif attack == "remote": platform["local_fixed"] = False
            elif attack == "flags": capabilities["filesystem_flags"] = 0
            elif attack == "huge-flags": capabilities["filesystem_flags"] = 2**32+8
            elif attack == "exports": capabilities["api_exports"].pop()
            elif attack == "behavior": capabilities["behavior_verified"] = True
            elif attack == "version": platform["version"] = "10.0.26200.9168"
            else: platform["native_capabilities"] = None
            with self.subTest(attack=attack), self.assertRaises(v.V03ValidationError):
                check(value)

    def test_old_schema_bytes_and_old_os_pin_are_not_reinterpreted(self):
        for version, path in ((acceptance.LEGACY_RECEIPT_VERSION, acceptance.LEGACY_SCHEMA_PATH),
                              (acceptance.PREVIOUS_RECEIPT_VERSION, acceptance.PREVIOUS_SCHEMA_PATH)):
            saved = json.loads((ROOT/path).read_text(encoding="utf-8"))
            self.assertEqual(saved, acceptance.receipt_schema(version=version))
            value = self.receipt()
            value["receipt_version"] = version
            value["stable"]["platform"].pop("product_type")
            value["stable"]["platform"].pop("native_capabilities")
            value["stable"]["python"]["basic_pin"] = "matches-formal-basic-pin"
            if version == acceptance.LEGACY_RECEIPT_VERSION:
                value["requirements"] = dict.fromkeys(acceptance.LEGACY_REQUIREMENTS, "not_completed")
            for row in value["stable"]["sources"][0]["files"]:
                if row["path"] == acceptance.SCHEMA_PATH:
                    row["path"] = path
            value["stable"]["sources"][0]["files"].sort(key=lambda row: row["path"])
            with self.assertRaisesRegex(v.V03ValidationError, "unsupported Windows runtime"):
                check(value)
            value["stable"]["platform"].update(build=26200, ubr=9168, edition="Professional",
                                               release="25H2", version="10.0.26200.9168")
            self.assertFalse(check(value)["formal_permission"])

    def test_same_run_rejects_patch_change_even_when_both_environments_are_supported(self):
        observed = self.receipt()["stable"]["platform"]
        expected = v.canonical_json(observed)
        runtime.require_same_runtime(expected, observed)
        changed = copy.deepcopy(observed)
        changed["ubr"] += 1
        changed["version"] = f"10.0.{changed['build']}.{changed['ubr']}"
        with self.assertRaisesRegex(runtime.IntegrityError, "runtime changed during run"):
            runtime.require_same_runtime(expected, changed)
        with self.assertRaisesRegex(v.V03ValidationError, "external stable pin mismatch"):
            receipt = self.receipt()
            frozen = v.canonical_sha256(receipt["stable"])
            receipt["stable"]["platform"] = changed
            acceptance.validate_receipt(receipt, expected_stable_sha256=frozen)

    def probe(self, *, filesystem="NTFS", flags=8, build=26300, kernel_build=None,
              product_type=1, missing_export=False, drive_type=3, expected_snapshot=None):
        temp = tempfile.TemporaryDirectory(prefix="banto-os-policy-")
        self.addCleanup(temp.cleanup)
        parent = Path(temp.name)
        executable, dll = parent/"python.exe", parent/"python314.dll"
        executable.write_bytes(b"fake executing python")
        dll.write_bytes(b"fake loaded python DLL")
        functions = {}
        def unavailable(*args):
            self.fail("Job/ACL/publication behavior API executed")
        for library, names in runtime.WINDOWS_REQUIRED_EXPORTS.items():
            functions[library] = SimpleNamespace(**{name: FakeFunction(unavailable) for name in names})
        kernel = functions["kernel32"]
        kernel.GetVolumePathNameW = FakeFunction(lambda path, buffer, length: (setattr(buffer, "value", "C:\\"), 1)[1])
        kernel.GetDriveTypeW = FakeFunction(lambda path: drive_type)
        def volume(path, volume_name, size, serial, maximum, out_flags, out_name, length):
            out_flags._obj.value = flags
            out_name.value = filesystem
            return 1
        kernel.GetVolumeInformationW = FakeFunction(volume)
        if missing_export: kernel.AssignProcessToJobObject = None
        values = {"CurrentBuildNumber": str(build), "UBR": 9457, "EditionID": "Core", "DisplayVersion": "26H2"}
        class Key:
            def __enter__(self): return self
            def __exit__(self, *args): return None
        registry = SimpleNamespace(HKEY_LOCAL_MACHINE=1, OpenKey=lambda *a: Key(),
                                   QueryValueEx=lambda key, name: (values[name], 0))
        pin = {**contract.formal_runtime(), "python_exe_raw_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
               "python_dll_raw_sha256": hashlib.sha256(dll.read_bytes()).hexdigest()}
        fake_sys = SimpleNamespace(base_prefix=str(parent), executable=str(executable),
            _git=("CPython", "tags/v3.14.0", "ebf955d"),
            getwindowsversion=lambda: SimpleNamespace(major=10, minor=0,
                build=build if kernel_build is None else kernel_build, product_type=product_type))
        # Keep pathlib's host behavior intact while replacing only runtime's os view.
        with patch.object(runtime, "os", SimpleNamespace(name="nt")), patch.object(runtime, "sys", fake_sys), \
                patch.object(runtime.platform, "system", return_value="Windows"), \
                patch.object(runtime.platform, "machine", return_value="AMD64"), \
                patch.object(runtime.platform, "python_implementation", return_value="CPython"), \
                patch.object(runtime.platform, "python_version", return_value="3.14.0"), \
                patch.object(runtime.platform, "python_compiler", return_value="MSC v.1944 64 bit (AMD64)"), \
                patch.object(runtime.sysconfig, "get_config_var", return_value=0), \
                patch.dict(sys.modules, {"winreg": registry}), \
                patch.object(ctypes, "WinDLL", side_effect=lambda name, **kwargs: functions[name], create=True), \
                patch.object(contract, "formal_runtime", return_value=pin):
            return runtime.probe_runtime(parent, expected_snapshot=expected_snapshot)

    def test_probe_records_actual_os_and_capabilities_with_fake_api_returns(self):
        result = self.probe()
        self.assertEqual((result["os_build"], result["os_ubr"], result["os_edition"]), (26300, 9457, "Core"))
        self.assertFalse(result["runtime_policy"]["behavior_verified"])
        self.assertEqual(result["filesystem"], "local-NTFS")
        with self.assertRaisesRegex(runtime.IntegrityError, "runtime changed during run"):
            self.probe(expected_snapshot={**result, "os_ubr": 1})

    def test_probe_rejects_bad_volume_missing_api_and_inconsistent_host(self):
        for options in ({"filesystem": "FAT32"}, {"flags": 0}, {"missing_export": True},
                        {"drive_type": 4}, {"kernel_build": 26200}, {"product_type": 3}):
            with self.subTest(options=options), self.assertRaises(runtime.IntegrityError):
                self.probe(**options)

    def test_collector_forwards_actual_host_capability_snapshot(self):
        observed = self.probe()
        with patch.object(inventory, "os", SimpleNamespace(name="nt")), \
                patch.object(inventory, "sys", SimpleNamespace(dont_write_bytecode=True, version_info=(3,14,0), executable=__file__)), \
                patch.object(inventory.platform, "python_implementation", return_value="CPython"), \
                patch.object(inventory.sysconfig, "get_config_var", return_value=0), \
                patch.object(inventory.rt, "regular_path", side_effect=lambda value, **kwargs: value), \
                patch.object(inventory.rt, "probe_runtime", return_value=observed), \
                patch.object(inventory, "_windows_cpu", return_value=("stub CPU", ["sse2"])):
            result, _, _, basic = inventory.probe_host(ROOT)
        self.assertEqual((result["build"], result["ubr"], result["edition"]), (26300,9457,"Core"))
        self.assertEqual(result["native_capabilities"], observed["runtime_policy"])
        self.assertEqual(basic, "matches-python-basic-pin")

    def test_current_schema_and_closed_formal_gate(self):
        saved = json.loads((ROOT/acceptance.SCHEMA_PATH).read_text(encoding="utf-8"))
        self.assertEqual(saved, acceptance.receipt_schema())
        self.assertEqual(runtime.acceptance_requirements()["linux_python"], ["3.14"])
        with self.assertRaisesRegex(runtime.IntegrityError, "s4_acceptance_not_frozen"):
            runtime.require_campaign_acceptance()

    def test_discovery_exposes_only_local_case_class(self):
        suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
        for group in suite:
            for case in group:
                self.assertEqual(type(case).__module__, __name__)


if __name__ == "__main__":
    unittest.main()
