"""S4-A pure attacks and owned-temp read-only capture; no native/seed campaign."""

from __future__ import annotations

import copy
import hashlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_acceptance as a
from banto_ai import _anomaly_v03_inventory as inv
from banto_ai import _anomaly_v03_runtime as rt
from banto_ai import anomaly_v03_runner as r
from banto_ai import anomaly_v03_materializer as m
from tests.test_anomaly_v03_runner import FakeBackend, GuardedMemory, fixture_checkout
from tests import test_anomaly_v03_provenance as source_fixture
from tools.evaluator import inspect_anomaly_v03 as cli

ROOT = Path(__file__).absolute().parents[1]
RAW = b"hand-written source\n"


def entry(path, raw=RAW):
    return {"path": path, "raw_sha256": hashlib.sha256(raw).hexdigest(), "byte_count": len(raw)}


def fixture():
    sources = [{"role": role, "state": "not_collected", "revision": None, "files": []} for role in a.ROLES]
    sources[0].update(state="collected", revision="a"*40, files=[entry(p) for p in sorted(a.REQUIRED_PRODUCER_PATHS)])
    sources[4].update(state="collected", revision="a"*40, files=[entry(a.WORKFLOW)])
    return {"receipt_version": "s4-a.2", "acceptance_status": "not_completed",
        "requirements": dict.fromkeys(a.REQUIREMENTS, "not_completed"),
        "stable": {"platform": {"system": "Linux", "release": "24.04", "version": "hand-kernel", "build": None,
            "ubr": None, "edition": "ubuntu", "architecture": "x86_64", "filesystem": "ext4", "local_fixed": True},
            "python": {"implementation": "CPython", "version": "3.12.8", "compiler": "hand-compiler", "gil_disabled": False,
                "source_tag": "hand-tag", "pointer_bits": 64, "executable": entry("python/python", b"hand executable"),
                "executable_native_path": "native/python", "loaded_python_dll": None,
                "basic_pin": "compatibility-only"},
            "cpu": {"architecture": "x86_64", "identity": "hand-cpu", "features": ["sse2"], "feature_scope": "linux-all-processors-intersection"},
            "startup": {"flags": [{"name": name, "value": 0} for name in a.FLAG_NAMES],
                "environment": [{"name": name, "present": False} for name in a.ENV_NAMES],
                "import_locations": ["source", "stdlib"], "user_site_enabled": False, "bytecode_writes_disabled": True},
            "stdlib": [entry("stdlib/random.py")],
            "loaded_native": [entry("native/libc.so"), entry("native/python", b"hand executable")], "loaded_extensions": [],
            "sources": sources, "scope": {"phase": "post-probe-import-observation", "closure_verified": False,
                "stdlib_policy": "regular-tree-excluding-site-packages", "native_method": "proc-self-maps", "limitations": list(a.LIMITATIONS)}},
        "observation": {"pid": 1, "observed_utc": "2026-09-07T00:00:00+00:00", "elapsed_seconds": 0.0, "free_bytes": 100,
            "peak_process_bytes": None, "system_commit_bytes": None, "token_ids": [],
            "native_files": [{"path": "native/"+name, "physical_path": "/hand/"+name, "device": 1,
                "inode": index+1, "nlink": 1, "trust_status": "not_accepted"} for index, name in enumerate(("libc.so", "python"))],
            "native_load_order": ["native/libc.so", "native/python"]}}


def check(value):
    return a.validate_receipt(value, expected_stable_sha256=v.canonical_sha256(value["stable"]))


class AcceptanceContractTests(unittest.TestCase):
    def test_persisted_schema_matches_closed_builder(self):
        schema = v.strict_json((ROOT/a.SCHEMA_PATH).read_bytes())
        self.assertEqual(schema, a.receipt_schema())
        def walk(node):
            if isinstance(node, dict):
                if node.get("type") == "object":
                    self.assertIs(node["additionalProperties"], False)
                    self.assertEqual(set(node["required"]), set(node["properties"]))
                for value in node.values(): walk(value)
            elif isinstance(node, list):
                for value in node: walk(value)
        walk(schema)

    def test_pure_no_IO_and_no_permission_even_with_external_pin(self):
        value = fixture()
        digest = v.canonical_sha256(value["stable"])
        with ExitStack() as traps:
            for name in ("builtins.open", "pathlib.Path.open", "os.stat", "os.getenv", "socket.socket", "subprocess.run"):
                traps.enter_context(patch(name, side_effect=AssertionError("unexpected I/O")))
            report = a.validate_receipt(value, expected_stable_sha256=digest)
        self.assertEqual(report["acceptance_status"], "not_completed")
        self.assertFalse(report["formal_permission"])
        self.assertFalse(report["execution_authenticated"])
        with self.assertRaisesRegex(rt.IntegrityError, "s4_acceptance_not_frozen"):
            rt.require_campaign_acceptance()

    def test_all_acceptance_self_claims_rejected(self):
        for key in ("acceptance_status", *a.REQUIREMENTS):
            value = fixture()
            if key == "acceptance_status": value[key] = "accepted"
            else: value["requirements"][key] = "complete"
            with self.subTest(key=key), self.assertRaises(v.V03ValidationError): check(value)

    def test_previous_receipt_revision_and_removed_requirement_are_not_reinterpreted(self):
        for previous_version, previous_requirement in ((True, False), (False, True), (True, True)):
            value = fixture()
            if previous_version:
                value["receipt_version"] = "s4-a.1"
            if previous_requirement:
                value["requirements"]["windows-3.12"] = "not_completed"
            with self.subTest(version=previous_version, requirement=previous_requirement), \
                    self.assertRaisesRegex(v.V03ValidationError, "engineering schema violation"):
                check(value)

    def test_both_linux_minors_remain_compatibility_only_and_unaccepted(self):
        for version in ("3.12.8", "3.14.0"):
            value = fixture()
            value["stable"]["python"]["version"] = version
            with self.subTest(version=version):
                report = check(value)
                self.assertEqual(report["acceptance_status"], "not_completed")
                self.assertFalse(report["formal_permission"])

    def test_external_pin_required_no_self_pin_or_circular_envelope(self):
        value = fixture()
        for digest in (None, "a"*40, "a"*64+"\n", "0"*64):
            with self.subTest(pin=digest), self.assertRaises(v.V03ValidationError):
                a.validate_receipt(value, expected_stable_sha256=digest)
        for owner in (value, value["stable"]):
            for key in ("raw_sha256", "equivalence_sha256", "self_pin"):
                owner[key] = "a"*64
                with self.subTest(key=key), self.assertRaises(v.V03ValidationError): check(value)
                del owner[key]

    def test_volatile_changes_do_not_change_equivalence(self):
        value = fixture(); digest = v.canonical_sha256(value["stable"])
        value["observation"].update(pid=200, free_bytes=999, elapsed_seconds=22.0, peak_process_bytes=1000)
        a.validate_receipt(value, expected_stable_sha256=digest)
        value["stable"]["stdlib"][0]["byte_count"] += 1
        with self.assertRaisesRegex(v.V03ValidationError, "external stable pin"):
            a.validate_receipt(value, expected_stable_sha256=digest)

    def test_path_missing_extra_duplicate_case_and_order_attacks(self):
        for attack in ("traversal", "absolute", "unc", "alias", "dot", "namespace", "duplicate", "case", "order", "missing", "extra-field"):
            value = fixture(); rows = value["stable"]["stdlib"]
            if attack in ("traversal", "absolute", "unc", "alias", "dot"):
                rows[0]["path"] = {"traversal":"stdlib/../x", "absolute":"C:/x", "unc":"//host/x", "alias":"stdlib/CON", "dot":".github/workflows/evil.yml"}[attack]
            elif attack == "namespace": rows[0]["path"] = a.WORKFLOW
            elif attack == "duplicate": rows.append(copy.deepcopy(rows[0]))
            elif attack == "case": rows.insert(0, entry("STDLIB/random.py"))
            elif attack == "order": rows.insert(0, entry("stdlib/z.py"))
            elif attack == "missing": value["stable"]["sources"][0]["files"].pop()
            else: rows[0]["permissions"] = "read-only"
            with self.subTest(attack=attack), self.assertRaises(v.V03ValidationError): check(value)

    def test_source_snapshot_full_revision_bytes_hash_inventory(self):
        value = fixture()
        snapshots = {s["role"]: {"revision": s["revision"], "files": {row["path"]: RAW for row in s["files"]}}
                     for s in value["stable"]["sources"] if s["state"] == "collected"}
        digest = v.canonical_sha256(value["stable"])
        self.assertTrue(a.validate_receipt(value, expected_stable_sha256=digest, source_snapshots=snapshots)["source_bytes_checked"])
        for attack in ("bytes", "missing", "extra", "revision", "role"):
            bad = copy.deepcopy(snapshots); source = bad["producer"]
            name = next(iter(source["files"]))
            if attack == "bytes": source["files"][name] += b"x"
            elif attack == "missing": del source["files"][name]
            elif attack == "extra": source["files"]["src/extra.py"] = RAW
            elif attack == "revision": source["revision"] = "b"*40
            else: del bad["workflow"]
            with self.subTest(attack=attack), self.assertRaises(v.V03ValidationError):
                a.validate_receipt(value, expected_stable_sha256=digest, source_snapshots=bad)

    def test_scope_sources_extensions_and_runtime_cross_fields(self):
        for attack in ("closure", "limitation", "workflow", "revision", "uncollected", "extension", "order", "minor", "version", "arch", "fs", "fstype", "cpu", "env"):
            value = fixture(); stable = value["stable"]
            if attack == "closure": stable["scope"]["closure_verified"] = True
            elif attack == "limitation": stable["scope"]["limitations"].pop()
            elif attack == "workflow": stable["sources"][-1]["files"] = []
            elif attack == "revision": stable["sources"][-1]["revision"] = "b"*40
            elif attack == "uncollected": stable["sources"][1]["revision"] = "a"*40
            elif attack == "extension": stable["loaded_extensions"] = [entry("native/absent.so")]
            elif attack == "order": value["observation"]["native_load_order"] *= 2
            elif attack == "minor": stable["python"]["version"] = "3.11.9"
            elif attack == "version": stable["python"]["version"] = "3.12.bogus"
            elif attack == "arch": stable["platform"]["architecture"] = "ARM64"
            elif attack == "fs": stable["platform"]["local_fixed"] = False
            elif attack == "fstype": stable["platform"]["filesystem"] = "overlay"
            elif attack == "cpu": stable["cpu"]["features"] *= 2
            else: stable["startup"]["environment"][0]["value"] = "sensitive-value"
            with self.subTest(attack=attack), self.assertRaises(v.V03ValidationError): check(value)

    def test_numeric_bool_nonfinite_and_trailing_hash_rejected(self):
        for field, val in (("byte_count", True), ("byte_count", -1), ("raw_sha256", "a"*64+"\n")):
            value = fixture(); value["stable"]["stdlib"][0][field] = val
            with self.assertRaises(v.V03ValidationError): check(value)
        value = fixture(); value["observation"]["elapsed_seconds"] = float("nan")
        with self.assertRaises(v.V03ValidationError): check(value)

    def _windows_fixture(self):
        from banto_ai import _anomaly_v03_contract as c
        value = fixture(); stable = value["stable"]; pin = c.formal_runtime()
        stable["platform"].update(system="Windows", release="25H2", version="10.0.26200.9168", build=26200,
            ubr=9168, edition="Professional", architecture="AMD64", filesystem="NTFS")
        stable["cpu"].update(architecture="AMD64", feature_scope="win32-processor-feature-api")
        stable["scope"]["native_method"] = "EnumProcessModulesEx"
        stable["python"].update(version="3.14.0", compiler="MSC v.1944 64 bit (AMD64)", source_tag="v3.14.0:ebf955d",
            executable_native_path="native/python.exe", loaded_python_dll="native/python314.dll", basic_pin="matches-formal-basic-pin")
        stable["python"]["executable"]["path"] = "python/python.exe"
        stable["python"]["executable"]["raw_sha256"] = pin["python_exe_raw_sha256"]
        stable["loaded_native"] = [{**stable["python"]["executable"], "path": "native/python.exe"},
            {**entry("native/python314.dll"), "raw_sha256": pin["python_dll_raw_sha256"]}]
        value["observation"]["native_load_order"] = ["native/python.exe", "native/python314.dll"]
        for row, name in zip(value["observation"]["native_files"], ("python.exe", "python314.dll"), strict=True):
            row.update(path="native/"+name, physical_path="C:/hand/"+name)
        return value

    def test_windows_formal_basic_match_remains_unaccepted(self):
        value = self._windows_fixture()
        self.assertFalse(check(value)["formal_permission"])
        for field, val in (("version", "3.14.1"), ("source_tag", "other"), ("gil_disabled", True)):
            bad = copy.deepcopy(value); bad["stable"]["python"][field] = val
            with self.assertRaises(v.V03ValidationError): check(bad)

    def test_windows_312_compatibility_receipt_is_no_longer_supported(self):
        value = self._windows_fixture()
        value["stable"]["python"].update(version="3.12.10", basic_pin="compatibility-only")
        with self.assertRaisesRegex(v.V03ValidationError, "formal basic pin mismatch"):
            check(value)

    def test_executable_native_reference_is_required_unique_and_byte_equal(self):
        for system, make in (("Linux", fixture), ("Windows", self._windows_fixture)):
            self.assertFalse(check(make())["formal_permission"])
            for attack in ("missing-field", "missing-image", "unknown", "unsafe", "namespace", "hash", "size", "duplicate", "case-alias"):
                value = make(); stable = value["stable"]; py = stable["python"]
                ref = py["executable_native_path"]
                row = next(row for row in stable["loaded_native"] if row["path"] == ref)
                if attack == "missing-field": del py["executable_native_path"]
                elif attack == "missing-image": stable["loaded_native"].remove(row)
                elif attack == "unknown": py["executable_native_path"] = "native/absent"
                elif attack == "unsafe": py["executable_native_path"] = "native/../python"
                elif attack == "namespace": py["executable_native_path"] = "python/python"
                elif attack == "hash": row["raw_sha256"] = "0"*64
                elif attack == "size": row["byte_count"] += 1
                else:
                    duplicate = copy.deepcopy(row)
                    if attack == "case-alias": duplicate["path"] = ref.upper()
                    stable["loaded_native"].append(duplicate)
                    stable["loaded_native"].sort(key=lambda item:item["path"])
                with self.subTest(system=system, attack=attack), self.assertRaises(v.V03ValidationError): check(value)

    def test_executable_reference_is_bound_by_external_equivalence_pin(self):
        value = fixture()
        value["stable"]["loaded_native"].append(entry("native/python-copy", b"hand executable"))
        value["observation"]["native_load_order"].append("native/python-copy")
        value["observation"]["native_files"].append({"path":"native/python-copy", "physical_path":"/hand/python-copy",
            "device":1, "inode":3, "nlink":1, "trust_status":"not_accepted"})
        digest = v.canonical_sha256(value["stable"])
        a.validate_receipt(value, expected_stable_sha256=digest)
        value["stable"]["python"]["executable_native_path"] = "native/python-copy"
        self.assertFalse(check(value)["formal_permission"])
        with self.assertRaisesRegex(v.V03ValidationError, "external stable pin"):
            a.validate_receipt(value, expected_stable_sha256=digest)


class ReadOnlyCollectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="banto-v03-s4a-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.file = self.root/"runtime.py"
        self.file.write_bytes(RAW)

    def test_hash_is_chunk_bounded_no_write_and_detects_read_mutation(self):
        with patch.object(inv, "CHUNK_SIZE", 2), patch.object(Path, "write_bytes", side_effect=AssertionError("write")):
            self.assertEqual(inv.hash_file(self.file, "stdlib/runtime.py"), entry("stdlib/runtime.py"))
        real = inv._stamp
        calls = []
        def changed(meta):
            calls.append(1)
            stamp = real(meta)
            return (*stamp[:-1], stamp[-1]+1) if len(calls) == 3 else stamp
        with patch.object(inv, "_stamp", side_effect=changed), self.assertRaisesRegex(rt.IntegrityError, "during hash"):
            inv.hash_file(self.file, "stdlib/runtime.py")

    def test_symlink_reparse_hardlink_metadata_rejected(self):
        metadata = self.file.lstat()
        for attack in ("reparse", "hardlink", "symlink"):
            def lstat(path):
                if path != self.file: return original(path)
                return SimpleNamespace(st_mode=metadata.st_mode if attack != "symlink" else 0o120777,
                    st_nlink=2 if attack == "hardlink" else 1, st_file_attributes=0x400 if attack == "reparse" else 0)
            original = Path.lstat
            with patch.object(Path, "lstat", new=lstat), self.subTest(attack=attack), self.assertRaises(rt.IntegrityError):
                inv.hash_file(self.file, "stdlib/runtime.py")

    def test_environment_only_allowlist_names_and_presence(self):
        with patch.dict(os.environ, {"PYTHONPATH":"sensitive-value", "UNLISTED_PRIVATE":"hidden-value"}, clear=True):
            value = inv._startup(self.root)
        text = v.canonical_json(value).decode()
        self.assertNotIn("sensitive-value", text)
        self.assertNotIn("hidden-value", text)
        self.assertNotIn("UNLISTED_PRIVATE", text)
        self.assertTrue(next(r for r in value["environment"] if r["name"] == "PYTHONPATH")["present"])

    def test_native_hardlink_observation_does_not_relax_source(self):
        original_lstat, original_fstat = Path.lstat, os.fstat
        def hardlink(meta):
            values = {key: getattr(meta, key) for key in dir(meta) if key.startswith("st_")}
            return SimpleNamespace(**{**values, "st_nlink": 2})
        def lstat(path):
            meta = original_lstat(path)
            return hardlink(meta) if path == self.file else meta
        with patch.object(Path, "lstat", new=lstat), patch.object(os, "fstat", side_effect=lambda fd:hardlink(original_fstat(fd))), \
                patch.object(inv, "_native_local"), patch.object(inv, "CHUNK_SIZE", 2):
            row, observed = inv.hash_native(self.file, "native/runtime.py")
            self.assertEqual(row, entry("native/runtime.py"))
            self.assertEqual(observed["nlink"], 2)
            self.assertEqual(observed["trust_status"], "not_accepted")
            self.assertEqual(observed["inode"], self.file.lstat().st_ino)
            with self.assertRaises(rt.IntegrityError): inv.hash_file(self.file, "stdlib/runtime.py")

    def test_native_identity_nlink_and_metadata_changes_fail_closed(self):
        stamp = inv._native_stamp
        for call_index in (2, 3, 4):
            for field in range(6):
                # ctime is deliberately compared within each API on Windows.
                if call_index == 2 and field == 4: continue
                calls = []
                def changed(meta):
                    values = list(stamp(meta)); calls.append(1)
                    if len(calls) == call_index: values[field] += 1
                    return tuple(values)
                with self.subTest(call=call_index, field=field), patch.object(inv, "_native_stamp", side_effect=changed), \
                        patch.object(inv, "_native_local"), self.assertRaises(rt.IntegrityError):
                    inv.hash_native(self.file, "native/runtime.py")
        with patch.object(inv, "_native_local", side_effect=rt.IntegrityError("nonlocal")), \
                patch.object(Path, "open", side_effect=AssertionError("must not open nonlocal file")), self.assertRaises(rt.IntegrityError):
            inv.hash_native(self.file, "native/runtime.py")

    def test_native_symlink_reparse_and_path_aliases_rejected(self):
        original = Path.lstat
        metadata = original(self.file)
        for attack in ("symlink", "reparse"):
            def lstat(path):
                if path != self.file: return original(path)
                values = {key: getattr(metadata, key) for key in dir(metadata) if key.startswith("st_")}
                values.update(st_mode=0o120777 if attack == "symlink" else metadata.st_mode,
                              st_file_attributes=0x400 if attack == "reparse" else 0)
                return SimpleNamespace(**values)
            with patch.object(Path, "lstat", new=lstat), self.subTest(attack=attack), self.assertRaises(rt.IntegrityError):
                inv.hash_native(self.file, "native/runtime.py")
        for name in ("native/../runtime.py", "stdlib/runtime.py", "native/other.py"):
            with self.subTest(name=name), self.assertRaises(v.V03ValidationError): inv.hash_native(self.file, name)

    def test_unsupported_before_source_or_inventory_and_no_write(self):
        with patch.object(inv.platform, "python_implementation", return_value="PyPy"), \
                patch.object(inv, "capture_sources", side_effect=AssertionError("source")), \
                patch.object(Path, "mkdir", side_effect=AssertionError("write")), self.assertRaises(rt.IntegrityError):
            inv.collect_receipt(self.root, "a"*40)

    def test_windows_other_python_versions_rejected_before_path_or_native_probe(self):
        for version in ((3, 12, 10), (3, 14, 1)):
            with self.subTest(version=version), \
                    patch.object(inv, "os", SimpleNamespace(name="nt")), \
                    patch.object(inv, "sys", SimpleNamespace(dont_write_bytecode=True, version_info=version)), \
                    patch.object(rt, "regular_path", side_effect=AssertionError("path inspection")), \
                    patch.object(inv, "capture_sources", side_effect=AssertionError("source")), \
                    patch.object(inv, "native_paths", side_effect=AssertionError("native inventory")), \
                    self.assertRaisesRegex(rt.IntegrityError, "unsupported_runtime"):
                inv.collect_receipt(self.root, "a"*40)

    def _capture(self, attack=None):
        hand = fixture()["stable"]
        source_rows = sorted(hand["sources"][0]["files"]+hand["sources"][-1]["files"], key=lambda r:r["path"])
        native = [("native/runtime.py", self.file)]
        actual_hash = inv.hash_file
        calls = []
        def hash_row(path, name):
            row = actual_hash(path, name); calls.append(name)
            if attack == "bytes" and len(calls) > 3: row["raw_sha256"] = "0"*64
            return row
        with ExitStack() as stack:
            for name, value in (("probe_host", (hand["platform"], hand["cpu"], self.file, "compatibility-only")),
                                ("capture_sources", source_rows), ("stdlib_paths", [("stdlib/runtime.py", self.file)]),
                                ("extension_paths", set()), ("_startup", hand["startup"])):
                stack.enter_context(patch.object(inv, name, return_value=value))
            stack.enter_context(patch.object(inv, "native_paths", side_effect=[native, []] if attack == "native" else None, return_value=native))
            stack.enter_context(patch.object(inv, "hash_file", side_effect=hash_row))
            stack.enter_context(patch.object(inv.platform, "python_version", return_value="3.12.8"))
            stack.enter_context(patch.object(Path, "write_bytes", side_effect=AssertionError("collector writes")))
            return inv.collect_receipt(self.root, "a"*40)

    def test_collector_double_readback_and_not_complete(self):
        result = self._capture()
        self.assertEqual(result["receipt"]["acceptance_status"], "not_completed")
        self.assertEqual(result["receipt"]["stable"]["python"]["executable_native_path"], "native/runtime.py")
        self.assertEqual(result["pin_origin"], "self-observation-not-trusted-external-pin")
        self.assertEqual([p.name for p in self.root.iterdir()], ["runtime.py"])
        for attack in ("bytes", "native"):
            with self.subTest(attack=attack), self.assertRaises(rt.IntegrityError): self._capture(attack)

    def test_cli_stdout_only_and_redacted_errors(self):
        with patch.object(cli, "collect_receipt", return_value={"hand":"inspection"}), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cli.main(["--expected-head", "a"*40]), 0)
        self.assertEqual(v.strict_json(output.getvalue()), {"hand":"inspection"})
        with patch.object(cli, "collect_receipt", side_effect=RuntimeError("dummy-sensitive-value")), \
                redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()) as output:
            self.assertEqual(cli.main(["--expected-head", "a"*40]), 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(output.getvalue(), '{"acceptance_status":"not_completed","inspection_status":"failed","formal_permission":false}\n')

    def test_cli_argument_failures_are_fixed_json_without_reflection(self):
        dummy = "dummy-sensitive-value"
        cases = ([], ["--root", dummy], ["--expected-head"], ["--expected-head", dummy],
            ["--expected-head", "a"*40, "--root"], ["--expected-head", "a"*40, "--dummy-sensitive-option", dummy],
            ["--expected-head", "a"*40, "--output="+dummy], ["--expected-h", "a"*40])
        expected = '{"acceptance_status":"not_completed","inspection_status":"failed","formal_permission":false}\n'
        for args in cases:
            with self.subTest(args=args), patch.object(cli, "collect_receipt") as collect, \
                    redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()) as stderr:
                self.assertEqual(cli.main(args), 1)
            collect.assert_not_called()
            self.assertEqual(stdout.getvalue(), "")
            self.assertEqual(stderr.getvalue(), expected)
        with patch.object(cli, "_full_revision", side_effect=RuntimeError(dummy)), \
                redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(cli.main(["--expected-head", dummy]), 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), expected)
        # Also verify the real entrypoint propagates the nonzero status, without
        # calling collection, creating artifacts, or echoing the dummy value.
        process = subprocess.run([sys.executable, "-B", str(ROOT/"tools/evaluator/inspect_anomaly_v03.py"),
            "--expected-head", "a"*40, "--output", dummy], capture_output=True, text=True, check=False)
        self.assertEqual(process.returncode, 1)
        self.assertEqual(process.stdout, "")
        self.assertEqual(process.stderr, expected)

    def test_cli_help_remains_normal_and_does_not_collect(self):
        with patch.object(cli, "collect_receipt") as collect, redirect_stdout(io.StringIO()) as stdout, \
                redirect_stderr(io.StringIO()) as stderr, self.assertRaises(SystemExit) as exit_info:
            cli.main(["--help"])
        self.assertEqual(exit_info.exception.code, 0)
        self.assertIn("--expected-head", stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")
        collect.assert_not_called()


class SourceCollectorTests(unittest.TestCase):
    def setUp(self):
        old = source_fixture.ProvenanceTests()
        old.setUp()
        self.addCleanup(old.tearDown)
        self.old = old
        for name in (*a.OWN_SOURCES, a.WORKFLOW):
            raw = (ROOT/name).read_bytes()
            old.files[name] = raw
            path = old.root/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        old.blobs = {hashlib.sha1(raw).hexdigest(): raw for raw in old.files.values()}
        old.tree = b"".join(f"100644 blob {hashlib.sha1(raw).hexdigest()}\t{name}\0".encode() for name, raw in old.files.items())

    def test_source_actual_bytes_and_workflow_included(self):
        with patch.object(rt, "_git", side_effect=self.old.git):
            rows = inv.capture_sources(self.old.root, "a"*40)
        self.assertEqual({r["path"] for r in rows}, set(self.old.files))
        self.assertIn(a.WORKFLOW, {r["path"] for r in rows})

    def test_workflow_untracked_missing_change_shallow_fail_closed(self):
        tree = self.old.tree
        for attack in ("untracked", "missing", "change", "shallow"):
            self.old.tree, self.old.extra = tree, b""
            path = self.old.root/a.WORKFLOW
            path.write_bytes(self.old.files[a.WORKFLOW])
            if attack == "untracked": self.old.extra = b".github/workflows/injected.yml\0"
            elif attack == "missing": self.old.tree = b"\0".join(row for row in tree.split(b"\0") if a.WORKFLOW.encode() not in row)
            elif attack == "change": path.write_bytes(b"forged workflow\n")
            def git(root, *args):
                if attack == "shallow" and args[0] == "show": raise rt.IntegrityError("Git provenance unavailable")
                return self.old.git(root, *args)
            with patch.object(rt, "_git", side_effect=git), self.subTest(attack=attack), self.assertRaises(rt.IntegrityError):
                inv.capture_sources(self.old.root, "a"*40)


class ResourceFailureTests(unittest.TestCase):
    def test_wrapped_memoryerror_graph_stops_future_slots(self):
        def fail(*_):
            try: raise MemoryError("hand resource failure")
            except MemoryError as cause: raise r.CellFailure("scoring") from cause
        backend = FakeBackend(fail)
        slots, stopped = r._drive("smoke", backend, lambda: None)
        self.assertTrue(stopped)
        self.assertEqual(len(slots), 144)
        self.assertEqual(r._coverage(slots)["not_started"], 143)
        self.assertEqual(backend.dones, [])
        self.assertTrue(r._has_global_cause(ExceptionGroup("resource", [MemoryError()])))

    def test_production_candidate_wrap_keeps_memoryerror_global_no_poststop_IO(self):
        # Bypass only materialization and saved-input validation with explicit
        # hand bytes. Execute the real candidate exception wrapper and driver.
        identity = v.evaluation_inventory("smoke")[0]
        files = {name: b"{}\n" for name in m.DATASET_FILES}
        store = GuardedMemory()
        for name, raw in files.items():
            path = "datasets/"+identity["dataset_id"]+"/"+name
            store.files[path] = raw
            store.expected[path] = r.payload_entry(path, raw)
        backend = r._DiskBackend(store, fixture_checkout())
        backend.pair_id, backend.pair = identity["pair_id"], [SimpleNamespace(files=lambda: files)]*2
        def exhaust(*_):
            store.unsafe = True
            raise MemoryError("hand failure at real candidate boundary")
        with patch.object(r, "_DiskBackend", return_value=backend), \
                patch.object(m, "validate_dataset", return_value=dict.fromkeys(m.INPUT_FILES, "a"*64)), \
                patch.object(r, "_execute_candidate", side_effect=exhaust) as candidate, \
                patch.object(m, "normal_stream", side_effect=AssertionError("registered generation")):
            result = r._run_prepared("smoke", store, fixture_checkout(), {"hand":True}, lambda: None)
        self.assertIsNone(result["publication"])
        self.assertEqual(candidate.call_count, 1)
        self.assertEqual(result["result"]["coverage"]["not_started"], 143)
        self.assertEqual(len(result["result"]["evaluations"]), 144)
        self.assertEqual(store.after_stop_IO_attempts, [])
        self.assertEqual(result["result"]["status"], r._status("failed", "fail"))


if __name__ == "__main__":
    unittest.main()
