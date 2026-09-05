"""D2-B publication boundary tests: synthetic receipts and temporary roots only."""

from __future__ import annotations

import io
import builtins
import inspect
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack, contextmanager, redirect_stderr, redirect_stdout
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from banto_ai import anomaly_failure_diagnostics as diagnostics
from banto_ai import anomaly_matrix_analysis as analysis, anomaly_matrix_runner as runner
from tests.test_anomaly_failure_diagnostics import ROOT, _complete_result_fixture, _write_traps


_WINDOWS_RACE_CHILD = r'''
import json, os, sys
from pathlib import Path
stage, final, replacement = map(Path, sys.argv[1:4])
blocked, succeeded = [], []
def attempt(label, action):
    try:
        action()
    except OSError:
        blocked.append(label)
    else:
        succeeded.append(label)
for name in ("result.json", "summary.md", ".complete", ".complete.pending"):
    path = stage / name
    attempt(name + ":overwrite", lambda: path.write_bytes(b"foreign overwrite"))
    attempt(name + ":replace", lambda: os.replace(replacement, path))
    attempt(name + ":unlink", lambda: path.unlink())
    attempt(name + ":rename", lambda: path.rename(stage / (name + ".stolen")))
    attempt(name + ":final-write", lambda: (final / name).write_bytes(b"early fixed-path write"))
attempt("extra-file", lambda: (stage / "unrelated.txt").write_bytes(b"extra"))
attempt("extra-directory", lambda: (stage / "unexpected-directory").mkdir())
fixed_was_absent = not final.exists()
if sys.argv[4] == "collide":
    final.mkdir()
    (final / "unrelated.txt").write_bytes(b"foreign winner")
    (final / ".complete").write_bytes(b"foreign marker")
print(json.dumps(dict(blocked=blocked, succeeded=succeeded, fixed_was_absent=fixed_was_absent)))
'''


class PublicationPlatformTests(unittest.TestCase):
    @contextmanager
    def non_windows(self, name="posix"):
        # Replace this module's platform bindings, not process-wide os.name.
        platform_os = SimpleNamespace(**vars(os))
        platform_os.name = name
        with patch.object(diagnostics, "os", platform_os), _write_traps():
            yield

    def test_non_windows_rename_factory_rejects_without_loading_a_native_primitive(self):
        import ctypes
        for name in ("posix", "java", "unsupported"):
            with self.subTest(os_name=name), self.non_windows(name), \
                 patch.object(ctypes, "CDLL", side_effect=AssertionError("no native fallback")) as load:
                with self.assertRaisesRegex(diagnostics.AnomalyFailureDiagnosticsError, "Windows-only"):
                    diagnostics._prepare_publication_rename()
            load.assert_not_called()

    def test_non_windows_publication_rejects_before_replay_path_inspection_or_claim(self):
        with self.non_windows(), ExitStack() as stack:
            forbidden = [stack.enter_context(patch.object(diagnostics, name, side_effect=AssertionError("must reject first")))
                         for name in ("_repository", "_safe_repo_path", "_replay_and_build_with_context", "_DiagnosticsOutputClaim", "_prepare_publication_rename")]
            with self.assertRaisesRegex(diagnostics.AnomalyFailureDiagnosticsError, "Windows-only"):
                diagnostics.run_and_publish_diagnostics(ROOT, replay_head="0" * 40)
        for entry in forbidden:
            entry.assert_not_called()

    def test_non_windows_private_staging_creation_rejects_without_mutation(self):
        with self.non_windows(), self.assertRaisesRegex(diagnostics.AnomalyFailureDiagnosticsError, "Windows-only"):
            diagnostics._create_private_staging_directory(ROOT / "artifacts" / (diagnostics._STAGING_PREFIX + "0" * 32), None)

    def test_non_windows_publication_guards_and_claim_reject_before_binding_paths(self):
        with self.non_windows(), patch.object(diagnostics, "_directory_identity", side_effect=AssertionError("no path binding")) as identity:
            for constructor in (diagnostics._OutputDirectoryGuard, diagnostics._DiagnosticsOutputClaim):
                with self.subTest(constructor=constructor.__name__), self.assertRaisesRegex(diagnostics.AnomalyFailureDiagnosticsError, "Windows-only"):
                    constructor(ROOT)
        identity.assert_not_called()

    def test_non_windows_cli_run_reports_platform_failure_without_publishing(self):
        with self.non_windows(), patch.object(diagnostics, "run_and_publish_diagnostics", side_effect=AssertionError("must reject before publisher")) as publish, \
             patch.object(diagnostics, "_repository", side_effect=AssertionError("no repository inspection")), redirect_stdout(io.StringIO()) as output:
            code = diagnostics.main(["--root", str(ROOT), "--run", "--replay-head", "0" * 40])
        self.assertEqual(code, 1)
        publish.assert_not_called()
        self.assertIn("Windows-only", output.getvalue())
        self.assertIn("--validate-only", output.getvalue())
        self.assertNotIn("published:", output.getvalue())

    def test_non_windows_validate_only_and_read_only_replay_do_not_enter_publication_gate(self):
        sentinel = object()
        with self.non_windows(), patch.object(diagnostics, "_require_windows_publication", side_effect=AssertionError("read-only is cross-platform")), \
             patch.object(diagnostics, "_replay_and_build_with_context", return_value=(sentinel, {}, b"")) as replay, redirect_stdout(io.StringIO()) as output:
            self.assertIs(diagnostics.replay_and_build_diagnostics_result(ROOT, replay_head="0" * 40), sentinel)
            self.assertEqual(diagnostics.main(["--root", str(ROOT), "--validate-only"]), 0)
        replay.assert_called_once_with(ROOT, replay_head="0" * 40)
        self.assertIn("filesystem_write: false", output.getvalue())


@contextmanager
def _only_output_mutations(output: Path):
    """Trap filesystem mutations outside the exact temporary claimed output tree."""
    events = []
    writable_descriptors = set()
    originals = {name: getattr(os, name) for name in ("open", "mkdir", "unlink", "rmdir", "link", "rename", "replace")}

    def contained(path, descriptor=None, parent_operation=False):
        if descriptor is not None:
            metadata = os.fstat(descriptor)
            directory = output.parent if parent_operation and str(path) == output.name else output
            expected = directory.stat()
            if (metadata.st_dev, metadata.st_ino) != (expected.st_dev, expected.st_ino) or Path(path).name != str(path):
                raise AssertionError("mutation used an unowned directory descriptor")
            return
        candidate = Path(path).absolute()
        if candidate != output and output not in candidate.parents:
            raise AssertionError(f"mutation escaped the claimed output: {candidate}")

    def open_guard(path, flags, *args, **kwargs):
        mutating = flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
        if mutating:
            contained(path, kwargs.get("dir_fd"))
            events.append(("write", Path(path).name, flags))
        descriptor = originals["open"](path, flags, *args, **kwargs)
        writable_descriptors.discard(descriptor)
        if mutating:
            writable_descriptors.add(descriptor)
        return descriptor

    def stream_guard(original):
        def call(path, mode="r", *args, **kwargs):
            if any(flag in mode for flag in "wax+"):
                if isinstance(path, int):
                    if path not in writable_descriptors:
                        raise AssertionError("write stream used an unowned descriptor")
                else:
                    contained(path)
            return original(path, mode, *args, **kwargs)
        return call

    def mutation_guard(name):
        def call(path, *args, **kwargs):
            contained(path, kwargs.get("dir_fd", kwargs.get("src_dir_fd")), name in {"mkdir", "rmdir"})
            if name in {"link", "rename", "replace"}:
                contained(args[0], kwargs.get("dst_dir_fd"))
            events.append((name, Path(path).name))
            return originals[name](path, *args, **kwargs)
        return call

    with ExitStack() as stack:
        stack.enter_context(patch.object(builtins, "open", stream_guard(builtins.open)))
        stack.enter_context(patch.object(io, "open", stream_guard(io.open)))
        stack.enter_context(patch.object(os, "open", side_effect=open_guard))
        for name in originals.keys() - {"open"}:
            stack.enter_context(patch.object(os, name, side_effect=mutation_guard(name)))
        import socket
        stack.enter_context(patch.object(socket, "create_connection", side_effect=AssertionError("network is forbidden")))
        yield events
        if any(event[0] in {"unlink", "rmdir", "link", "replace"} for event in events):
            raise AssertionError("publisher must never delete, hardlink, or replace output")


@unittest.skipUnless(os.name == "nt", "D2-B publication is Windows-only; non-Windows rejection is tested separately")
class DiagnosticsPublisherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = _complete_result_fixture()
        cls.source_rows, _ = runner._snapshot_inputs(ROOT, ROOT / diagnostics.EXPECTED_MATRIX_CONFIG_PATH)
        cls.template_paths = {item["path"] for key, item in cls.source_rows.items() if not key.startswith("_")}
        cls.template_paths.update((diagnostics.CONFIG_PATH, diagnostics.SCHEMA_PATH, diagnostics.RESULT_SCHEMA_PATH,
                                   analysis.ANALYSIS_CONFIG_PATH, analysis.ANALYSIS_SCHEMA_PATH,
                                   "tools/evaluator/render_anomaly_failure_diagnostics.py"))
        cls.templates = {path: (ROOT / path).read_bytes() for path in cls.template_paths}
        config, config_source, config_schema, result_schema = diagnostics._load_config(diagnostics.CONFIG_PATH, ROOT)
        provenance = cls.fixture["provenance"]
        compatibility = deepcopy(provenance["revision_compatibility"])
        compatibility["current_d2_diagnostics"]["renderer_raw_sha256"] = diagnostics._sha256_bytes(cls.templates["tools/evaluator/render_anomaly_failure_diagnostics.py"])
        compatibility["replay_revision"] = deepcopy(provenance["replay_code_revision"])
        verified = {"diagnostics_config": config, "diagnostics_config_source": config_source,
                    "diagnostics_schema_source": config_schema, "diagnostics_result_schema_source": result_schema,
                    "input_artifact": provenance["input_artifact"], "input_snapshot": provenance["input_snapshot"],
                    "revision_compatibility": compatibility, "replay_revision": compatibility["replay_revision"]}
        # Issue the fixture through the real shared builder/type boundary. The
        # initial formal replay and final filesystem audit are explicit stubs.
        with patch.object(diagnostics, "_verify_input_replay", return_value=verified), \
             patch.object(diagnostics, "_build_ledgers_from_verified_replay", return_value=cls.fixture["ledger"]), \
             patch.object(diagnostics, "_recheck_verified_replay_boundary"), _write_traps():
            cls.sealed, _, cls.payload = diagnostics._replay_and_build_with_context(ROOT, replay_head="0" * 40)
        cls.compatibility = compatibility

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="d2b-publisher-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for relative, raw in self.templates.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        self.input = self.root / diagnostics.EXPECTED_INPUT_ROOT
        self.input.mkdir(parents=True)
        (self.input / "synthetic-input.txt").write_bytes(b"synthetic artifact, never formal data\n")
        self.formal_analysis = self.root / "artifacts/anomaly-multiseed-v02-analysis"
        self.formal_analysis.mkdir()
        (self.formal_analysis / "sentinel.txt").write_bytes(b"protected analysis\n")
        self.output = self.root / diagnostics.EXPECTED_OUTPUT_ROOT
        self.stage = self.output.parent / (diagnostics._STAGING_PREFIX + "0" * 32)
        self.addCleanup(self.restore_private_fixture_permissions)
        config, config_source, config_schema, result_schema = diagnostics._load_config(diagnostics.CONFIG_PATH, self.root)
        _, analysis_source, analysis_schema = analysis._load_analysis_inputs(analysis.ANALYSIS_CONFIG_PATH, self.root)
        sources, values = runner._snapshot_inputs(self.root, self.root / diagnostics.EXPECTED_MATRIX_CONFIG_PATH)
        provenance = self.sealed["provenance"]
        self.context = {"diagnostics_config": config, "diagnostics_config_source": config_source,
                        "diagnostics_schema_source": config_schema, "diagnostics_result_schema_source": result_schema,
                        "analysis_source": analysis_source, "analysis_schema_source": analysis_schema,
                        "sources": sources, "values": values, "input_capture": diagnostics._capture_tree_bytes(self.input, "synthetic fixture"),
                        "input_artifact": provenance["input_artifact"], "input_snapshot": provenance["input_snapshot"],
                        "revision_compatibility": deepcopy(self.compatibility), "replay_revision": deepcopy(self.compatibility["replay_revision"])}
        self.before = self.protected_snapshot()

    def protected_snapshot(self):
        return {path.relative_to(self.root).as_posix(): path.read_bytes() for path in self.root.rglob("*")
                if path.is_file() and self.output not in path.parents and not any(parent.name.startswith(diagnostics._STAGING_PREFIX) for parent in path.parents)}

    def restore_private_fixture_permissions(self):
        """Explicit test teardown only; publisher NEVER restores ACLs or deletes."""
        folders = [self.output, *self.output.parent.glob(diagnostics._STAGING_PREFIX + "*")]
        for folder in folders:
            if not folder.is_dir():
                continue
            self.assertEqual(folder.parent, self.root / "artifacts")
            if os.name == "nt":
                import ctypes
                guard = diagnostics._OutputDirectoryGuard(folder)
                kernel = guard.kernel
                guard.close()
                for path in [folder, *folder.iterdir()]:
                    handle = kernel.CreateFileW(str(path), 0x60000, 7, None, 3, 0x02200000, None)
                    if handle == ctypes.c_void_p(-1).value:
                        raise ctypes.WinError(ctypes.get_last_error())
                    try:
                        inheritance = "OICI" if path.is_dir() else ""
                        diagnostics._set_windows_dacl(handle, f"D:P(A;{inheritance};FA;;;OW)(A;{inheritance};FA;;;SY)(A;{inheritance};FA;;;BA)")
                    finally:
                        kernel.CloseHandle(handle)
            else:
                folder.chmod(0o700)
                for path in folder.iterdir():
                    path.chmod(0o700 if path.is_dir() else 0o600)

    @contextmanager
    def runtime(self, **overrides):
        with ExitStack() as stack:
            stack.enter_context(patch.object(diagnostics.uuid, "uuid4", return_value=SimpleNamespace(hex="0" * 32)))
            replay = stack.enter_context(patch.object(diagnostics, "_replay_and_build_with_context", return_value=(self.sealed, self.context, self.payload)))
            stack.enter_context(patch.object(diagnostics, "_validate_revision_compatibility", return_value=self.compatibility))
            for name, replacement in overrides.items():
                stack.enter_context(patch.object(diagnostics, name, replacement))
            yield replay

    def run_publisher(self):
        return diagnostics.run_and_publish_diagnostics(self.root, replay_head="0" * 40)

    def assert_partial(self):
        self.assertTrue(self.stage.is_dir())
        self.assertFalse(self.output.exists())
        self.assertEqual(self.before, self.protected_snapshot())

    def reset_partial_fixture(self):
        """Test-only teardown between fault cases, outside publisher/mutation traps."""
        self.assert_partial()
        self.restore_private_fixture_permissions()
        for path in self.stage.iterdir():
            self.assertTrue(path.is_file())
            path.unlink()
        self.stage.rmdir()

    def test_success_publishes_three_files_together_and_protected_roots_are_unchanged(self):
        original_recheck = diagnostics._recheck_verified_replay_boundary
        original_rename = diagnostics._prepare_publication_rename()
        observations = []

        def boundary(context, repository):
            observations.append((set(path.name for path in self.stage.iterdir()), context is self.context))
            original_recheck(context, repository)

        def commit(source, target, directory_fd):
            self.assertFalse(self.output.exists())
            original_rename(source, target, directory_fd)
            mutations.append(("native_commit", diagnostics._STAGED_MARKER))

        with self.runtime(_recheck_verified_replay_boundary=boundary) as replay, \
             patch.object(diagnostics, "_prepare_publication_rename", return_value=commit), _only_output_mutations(self.stage) as mutations:
            receipt = self.run_publisher()
        replay.assert_called_once_with(self.root, replay_head="0" * 40)
        self.assertEqual(observations, [({"result.json", "summary.md", diagnostics._STAGED_MARKER}, True)])
        self.assertEqual([item[1] for item in mutations if item[0] == "write"], ["result.json", "summary.md", diagnostics._STAGED_MARKER])
        self.assertTrue(all(item[2] & os.O_EXCL and item[2] & os.O_CREAT for item in mutations if item[0] == "write"))
        self.assertEqual(mutations[-1], ("native_commit", diagnostics._STAGED_MARKER))
        self.assertFalse(self.stage.exists())
        self.assertEqual({path.name for path in self.output.iterdir()}, {"result.json", "summary.md", ".complete"})
        self.assertEqual((self.output / "result.json").read_bytes(), self.payload)
        marker_raw = (self.output / ".complete").read_bytes()
        marker = json.loads(marker_raw)
        self.assertEqual(marker, {"schema_version": diagnostics.SCHEMA_VERSION, "marker_type": diagnostics.DIAGNOSTICS_COMPLETION_MARKER_TYPE,
                                  "result_sha256": diagnostics._sha256_bytes(self.payload),
                                  "summary_sha256": diagnostics._sha256_bytes((self.output / "summary.md").read_bytes())})
        self.assertEqual(marker_raw, diagnostics._canonical_json(marker))
        self.assertEqual(receipt["completion_marker_sha256"], diagnostics._sha256_bytes(marker_raw))
        self.assertEqual(receipt["output_path"], str(self.output))
        self.assertNotIn(b"\r", (self.output / "summary.md").read_bytes())
        self.assertEqual(self.before, self.protected_snapshot())

    def test_no_public_stale_result_or_override_publication_route(self):
        self.assertEqual(set(inspect.signature(diagnostics.run_and_publish_diagnostics).parameters), {"root", "replay_head"})
        for extra in ({"result": self.sealed}, {"result": self.fixture}, {"schema": {}}, {"output_root": "elsewhere"}, {"renderer": lambda _: b"fake"}, {"recover": True}):
            with self.subTest(extra=tuple(extra)), self.assertRaises(TypeError):
                diagnostics.run_and_publish_diagnostics(self.root, replay_head="0" * 40, **extra)
        self.assertFalse(any(name.startswith("publish") and not name.startswith("_") for name in vars(diagnostics)))
        for value in (self.fixture, {"status": "draft"}):
            with self.runtime() as replay:
                replay.return_value = (value, self.context, self.payload)
                with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError): self.run_publisher()
            self.assertFalse(self.stage.exists())

    def test_read_only_api_does_not_enter_publisher(self):
        with self.runtime(), patch.object(diagnostics, "run_and_publish_diagnostics", side_effect=AssertionError("publish forbidden")), _write_traps():
            result = diagnostics.replay_and_build_diagnostics_result(self.root, replay_head="0" * 40)
        self.assertIs(result, self.sealed)
        self.assertFalse(self.stage.exists())

    def test_existing_directory_and_markerless_output_are_never_adopted(self):
        self.output.mkdir()
        (self.output / "existing.txt").write_bytes(b"do not overwrite")
        with self.runtime() as replay, _write_traps(), self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
            self.run_publisher()
        replay.assert_not_called()
        self.assertEqual((self.output / "existing.txt").read_bytes(), b"do not overwrite")

    def test_existing_output_file_is_never_adopted(self):
        self.output.write_bytes(b"existing file")
        with self.runtime(), _write_traps(), self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError): self.run_publisher()
        self.assertEqual(self.output.read_bytes(), b"existing file")

    def test_existing_staging_residue_is_rejected_even_with_a_prepared_marker(self):
        self.stage.mkdir()
        (self.stage / ".complete").write_bytes(b"prepared is not published")
        with self.runtime() as replay, _write_traps(), self.assertRaisesRegex(diagnostics.AnomalyFailureDiagnosticsError, "staging residue"):
            self.run_publisher()
        replay.assert_not_called()
        self.assert_partial()
        self.assertEqual((self.stage / ".complete").read_bytes(), b"prepared is not published")

    def test_staging_names_are_unique_and_not_the_fixed_destination(self):
        claims = [diagnostics._DiagnosticsOutputClaim(self.root) for _ in range(2)]
        self.assertNotEqual(claims[0].path, claims[1].path)
        for claim in claims:
            self.assertEqual(claim.destination, self.output)
            self.assertEqual(claim.path.parent, self.output.parent)
            self.assertRegex(claim.path.name, "^" + diagnostics._STAGING_PREFIX.replace(".", r"\.") + "[0-9a-f]{32}$")
            self.assertFalse(claim.path.exists())

    def test_existing_reparse_or_junction_target_is_rejected(self):
        original = diagnostics._is_reparse_point
        with self.runtime(), patch.object(diagnostics, "_is_reparse_point", side_effect=lambda path: path == self.output or original(path)), _write_traps():
            with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError): self.run_publisher()
        self.assertFalse(self.stage.exists())

    def test_parent_reparse_is_rejected_before_replay(self):
        original = diagnostics._is_reparse_point
        with self.runtime() as replay, patch.object(diagnostics, "_is_reparse_point", side_effect=lambda path: path == self.stage.parent or original(path)), _write_traps():
            with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError): self.run_publisher()
        replay.assert_not_called()

    def test_exclusive_claim_race_does_not_clean_the_winners_directory(self):
        original_mkdir = diagnostics._create_private_staging_directory

        def race(path, descriptor):
            if path == self.stage:
                original_mkdir(path, descriptor)
                (path / "winner.txt").write_bytes(b"racing owner")
            return original_mkdir(path, descriptor)

        with self.runtime(), patch.object(diagnostics, "_create_private_staging_directory", race), _only_output_mutations(self.stage):
            with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError): self.run_publisher()
        self.assertEqual((self.stage / "winner.txt").read_bytes(), b"racing owner")

    def test_successful_mkdir_then_swap_preserves_winner_without_cleanup(self):
        original_mkdir, original_rmdir = diagnostics._create_private_staging_directory, os.rmdir
        original_open = builtins.open

        def swap(path, descriptor):
            original_mkdir(path, descriptor)
            if path == self.stage:
                # Another actor's operations, before mkdir returns to the claim.
                original_rmdir(path if descriptor is None else path.name, **({"dir_fd": descriptor} if descriptor is not None else {}))
                original_mkdir(path, descriptor)
                with original_open(self.stage / "winner.txt", "wb") as handle:
                    handle.write(b"winner after successful mkdir")

        with self.runtime(), patch.object(diagnostics, "_create_private_staging_directory", side_effect=swap), _only_output_mutations(self.stage) as mutations:
            with self.assertRaisesRegex(diagnostics.AnomalyFailureDiagnosticsError, "retained for inspection"):
                self.run_publisher()
        self.assertEqual({path.name for path in self.stage.iterdir()}, {"winner.txt"})
        self.assertEqual((self.stage / "winner.txt").read_bytes(), b"winner after successful mkdir")
        self.assertFalse(any(row[0] in {"unlink", "rmdir"} for row in mutations))
        self.assert_partial()

    def test_final_directory_collision_never_overwrites_foreign_marker_or_files(self):
        original_rename = diagnostics._prepare_publication_rename()
        observed = []

        def race(source, target, directory_fd):
            self.output.mkdir()
            (self.output / ".complete").write_bytes(b"racing marker")
            (self.output / "unrelated.txt").write_bytes(b"racing owner")
            try:
                return original_rename(source, target, directory_fd)
            finally:
                observed.append((self.output / ".complete").read_bytes())

        with self.runtime(), patch.object(diagnostics, "_prepare_publication_rename", return_value=race):
            with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError): self.run_publisher()
        self.assertEqual(observed, [b"racing marker"])
        self.assertEqual((self.output / ".complete").read_bytes(), b"racing marker")
        self.assertEqual((self.output / "unrelated.txt").read_bytes(), b"racing owner")
        self.assertEqual({path.name for path in self.stage.iterdir()}, {"result.json", "summary.md", ".complete"})
        self.assertEqual(self.before, self.protected_snapshot())

    def test_final_empty_directory_collision_is_also_never_replaced(self):
        original, identity = diagnostics._prepare_publication_rename(), []
        def race(source, target, descriptor):
            self.output.mkdir()
            identity.append(diagnostics._directory_identity(self.output))
            return original(source, target, descriptor)
        with self.runtime(), patch.object(diagnostics, "_prepare_publication_rename", return_value=race):
            with self.assertRaisesRegex(diagnostics.AnomalyFailureDiagnosticsError, "staging retained for inspection"):
                self.run_publisher()
        self.assertEqual(diagnostics._directory_identity(self.output), identity[0])
        self.assertEqual(list(self.output.iterdir()), [])
        self.assertEqual({path.name for path in self.stage.iterdir()}, {"result.json", "summary.md", ".complete"})
        self.assertEqual(self.before, self.protected_snapshot())

    def test_result_file_create_race_never_overwrites_racing_bytes(self):
        original = diagnostics._DiagnosticsOutputClaim.write_exclusive
        observed = []
        def race(claim, name, raw):
            if name == "result.json":
                (self.stage / name).write_bytes(b"racing result")
            try:
                return original(claim, name, raw)
            finally:
                if name == "result.json": observed.append((self.stage / name).read_bytes())
        with self.runtime(), patch.object(diagnostics._DiagnosticsOutputClaim, "write_exclusive", race), _only_output_mutations(self.stage):
            with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError): self.run_publisher()
        self.assertEqual(observed, [b"racing result"])
        self.assertEqual((self.stage / "result.json").read_bytes(), b"racing result")
        self.assert_partial()

    def test_missing_atomic_rename_primitive_fails_before_claim(self):
        with self.runtime() as replay, patch.object(diagnostics, "_prepare_publication_rename", side_effect=OSError("no no-replace rename support")), _write_traps():
            with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError): self.run_publisher()
        replay.assert_not_called()
        self.assertFalse(self.stage.exists())

    def test_marker_rename_filesystem_failure_retains_pending_output(self):
        def unavailable(*args):
            raise OSError("filesystem does not support no-replace rename")
        with self.runtime(), patch.object(diagnostics, "_prepare_publication_rename", return_value=unavailable), _only_output_mutations(self.stage):
            with self.assertRaisesRegex(diagnostics.AnomalyFailureDiagnosticsError, "retained for inspection"):
                self.run_publisher()
        self.assert_partial()
        self.assertTrue((self.stage / diagnostics._STAGED_MARKER).is_file())

    def test_windows_directory_guard_prevents_rename_while_owned(self):
        if os.name != "nt": self.skipTest("Windows native sharing guard")
        self.stage.mkdir()
        guard = diagnostics._OutputDirectoryGuard(self.stage)
        try:
            with self.assertRaises(OSError): self.stage.rename(self.root / "replacement")
            guard.check()
        finally:
            guard.close()
        self.assertTrue(self.stage.is_dir())

    def test_windows_atomic_directory_rename_keeps_frozen_files_and_held_directory(self):
        if os.name != "nt": self.skipTest("Windows native pin during atomic rename")
        original_rename, checked = diagnostics._prepare_publication_rename(), []
        def rename(source, target, directory_fd):
            with self.assertRaises(OSError): (self.stage / "result.json").unlink()
            with self.assertRaises(OSError): self.stage.rename(self.root / "moved-output")
            checked.append(True)
            return original_rename(source, target, directory_fd)
        with self.runtime(), patch.object(diagnostics, "_prepare_publication_rename", return_value=rename):
            receipt = self.run_publisher()
        self.assertEqual(checked, [True])
        self.assertEqual(receipt["status"], "published")
        self.assertEqual(self.before, self.protected_snapshot())

    def test_windows_parent_summary_overwrite_probe_fails_before_marker(self):
        if os.name != "nt": self.skipTest("Windows final-boundary overwrite regression")
        original_install, captured = diagnostics._DiagnosticsOutputClaim.install_output, []
        def overwrite(claim, rename):
            captured.append(claim.read_owned("summary.md"))
            (claim.path / "summary.md").write_bytes(b"tampered immediately before install_output")
            return original_install(claim, rename)
        with self.runtime(), patch.object(diagnostics._DiagnosticsOutputClaim, "install_output", overwrite), _only_output_mutations(self.stage):
            with self.assertRaisesRegex(diagnostics.AnomalyFailureDiagnosticsError, "retained for inspection"):
                self.run_publisher()
        self.assertEqual(len(captured), 1)
        self.assertEqual((self.stage / "summary.md").read_bytes(), captured[0])
        self.assert_partial()

    def test_windows_all_files_stay_immutable_at_install_and_native_commit_callbacks(self):
        if os.name != "nt": self.skipTest("Windows native immutable publication pins")
        import msvcrt
        names = ("result.json", "summary.md", diagnostics._STAGED_MARKER)
        replacements = {}
        for index, name in enumerate(names):
            replacements[name] = self.root / f"competing-replacement-{index}.txt"
            replacements[name].write_bytes(b"foreign replacement: " + name.encode())
        protected = self.protected_snapshot()
        original_install = diagnostics._DiagnosticsOutputClaim.install_output
        original_rename = diagnostics._prepare_publication_rename()
        active, attempts = [], []

        def attack(claim, boundary):
            self.assertFalse(claim.pinned_descriptors)
            for name in names:
                target = claim.path / name
                expected = claim.read_owned(name)
                actions = {
                    "overwrite": lambda: target.write_bytes(b"foreign overwrite"),
                    "truncate": lambda: os.truncate(target, 0),
                    "unlink": lambda: target.unlink(),
                    "rename": lambda: target.rename(claim.path / (name + ".stolen")),
                    "replace": lambda: os.replace(replacements[name], target),
                }
                for label, action in actions.items():
                    with self.subTest(boundary=boundary, name=name, action=label), self.assertRaises(OSError):
                        action()
                    attempts.append((boundary, name, label))
                self.assertEqual(claim.read_owned(name), expected)
            self.assertEqual({path.name for path in claim.path.iterdir()}, set(names))

        def install(claim, rename):
            active.append(claim)
            attack(claim, "install_output")
            return original_install(claim, rename)

        def native_commit(source, target, directory_fd):
            claim = active[0]
            self.assertEqual(source, claim.directory.handle)
            self.assertEqual(target, self.output)
            self.assertIsNone(directory_fd)
            attack(claim, "native_commit")
            return original_rename(source, target, directory_fd)

        # These deliberate adversary attempts include an external source path;
        # ordinary publisher mutation confinement is tested separately.
        with self.runtime(), patch.object(diagnostics._DiagnosticsOutputClaim, "install_output", install), \
             patch.object(diagnostics, "_prepare_publication_rename", return_value=native_commit):
            receipt = self.run_publisher()
        self.assertEqual(len(attempts), 30)
        self.assertEqual(receipt["status"], "published")
        self.assertEqual({path.name for path in self.output.iterdir()}, {"result.json", "summary.md", ".complete"})
        marker_raw = (self.output / ".complete").read_bytes()
        marker = json.loads(marker_raw)
        for name in ("result.json", "summary.md"):
            field = "result_sha256" if name == "result.json" else "summary_sha256"
            self.assertEqual(marker[field], diagnostics._sha256_bytes((self.output / name).read_bytes()))
            self.assertEqual(receipt[field], marker[field])
        self.assertEqual(receipt["completion_marker_sha256"], diagnostics._sha256_bytes(marker_raw))
        self.assertEqual(protected, self.protected_snapshot())

    def test_windows_preexisting_writer_on_each_file_prevents_commit(self):
        if os.name != "nt": self.skipTest("Windows incompatible preexisting writer sharing")
        original = diagnostics._DiagnosticsOutputClaim.prepare_publication_commit
        for name in ("result.json", "summary.md", diagnostics._STAGED_MARKER):
            def writer(claim):
                with (claim.path / name).open("r+b"):
                    return original(claim)
            with self.subTest(name=name), self.runtime(), \
                 patch.object(diagnostics._DiagnosticsOutputClaim, "prepare_publication_commit", writer), \
                 patch.object(diagnostics._DiagnosticsOutputClaim, "install_output") as install, _only_output_mutations(self.stage):
                with self.assertRaisesRegex(diagnostics.AnomalyFailureDiagnosticsError, "retained for inspection"):
                    self.run_publisher()
            install.assert_not_called()
            self.reset_partial_fixture()

    def test_windows_separate_process_cannot_change_frozen_inventory_at_native_commit(self):
        self._assert_windows_child_race(collide=False)

    def test_windows_separate_process_final_path_collision_fails_without_overwrite(self):
        self._assert_windows_child_race(collide=True)

    def _assert_windows_child_race(self, *, collide):
        if os.name != "nt": self.skipTest("real Windows child-process precommit race")
        replacement = self.root / "foreign-child-replacement.txt"
        replacement.write_bytes(b"foreign replacement must survive")
        protected = self.protected_snapshot()
        original, reports = diagnostics._prepare_publication_rename(), []
        def commit(source, target, descriptor):
            self.assertFalse(self.output.exists())
            child = subprocess.run([sys.executable, "-B", "-c", _WINDOWS_RACE_CHILD, str(self.stage), str(self.output), str(replacement),
                                    "collide" if collide else "observe"], capture_output=True, text=True, timeout=15, check=True)
            report = json.loads(child.stdout)
            self.assertTrue(report["fixed_was_absent"])
            self.assertEqual(report["succeeded"], [])
            self.assertEqual(len(report["blocked"]), 22)
            reports.append(report)
            return original(source, target, descriptor)
        with self.runtime(), patch.object(diagnostics, "_prepare_publication_rename", return_value=commit):
            if collide:
                with self.assertRaisesRegex(diagnostics.AnomalyFailureDiagnosticsError, "staging retained for inspection"):
                    self.run_publisher()
            else:
                receipt = self.run_publisher()
                self.assertEqual(receipt["status"], "published")
        self.assertEqual(len(reports), 1)
        self.assertEqual(protected, self.protected_snapshot())
        if collide:
            self.assertEqual((self.output / "unrelated.txt").read_bytes(), b"foreign winner")
            self.assertEqual((self.output / ".complete").read_bytes(), b"foreign marker")
            self.assertEqual({path.name for path in self.stage.iterdir()}, {"result.json", "summary.md", ".complete"})
        else:
            self.assertFalse(self.stage.exists())
            self.assertEqual({path.name for path in self.output.iterdir()}, {"result.json", "summary.md", ".complete"})
            marker_raw = (self.output / ".complete").read_bytes()
            marker = json.loads(marker_raw)
            self.assertEqual(marker_raw, diagnostics._canonical_json(marker))
            self.assertEqual(marker["result_sha256"], diagnostics._sha256_bytes((self.output / "result.json").read_bytes()))
            self.assertEqual(marker["summary_sha256"], diagnostics._sha256_bytes((self.output / "summary.md").read_bytes()))
            self.assertEqual(receipt["completion_marker_sha256"], diagnostics._sha256_bytes(marker_raw))

    def test_windows_freeze_permissions_touch_only_four_held_staging_objects(self):
        if os.name != "nt": self.skipTest("Windows held-object DACL scope")
        import msvcrt
        original_prepare = diagnostics._DiagnosticsOutputClaim.prepare_publication_commit
        original_set, active, changed = diagnostics._set_windows_dacl, [], []
        def prepare(claim):
            active.append(claim)
            return original_prepare(claim)
        def set_dacl(handle, sddl):
            claim = active[0]
            allowed = {claim.directory.handle, *(msvcrt.get_osfhandle(fd) for fd in claim.pinned_descriptors.values())}
            self.assertIn(handle, allowed)
            changed.append((handle, sddl))
            return original_set(handle, sddl)
        with self.runtime(), patch.object(diagnostics._DiagnosticsOutputClaim, "prepare_publication_commit", prepare), \
             patch.object(diagnostics, "_set_windows_dacl", side_effect=set_dacl), _only_output_mutations(self.stage):
            self.run_publisher()
        self.assertEqual(len(changed), 4)
        self.assertEqual(len({handle for handle, _ in changed}), 4)
        self.assertEqual(self.before, self.protected_snapshot())

    def test_windows_permission_freeze_failure_is_before_commit_and_retains_staging(self):
        if os.name != "nt": self.skipTest("Windows DACL fail-closed")
        with self.runtime(), patch.object(diagnostics, "_set_windows_dacl", side_effect=OSError("cannot freeze permissions")), \
             patch.object(diagnostics._DiagnosticsOutputClaim, "install_output") as install, _only_output_mutations(self.stage):
            with self.assertRaisesRegex(diagnostics.AnomalyFailureDiagnosticsError, "staging retained for inspection"):
                self.run_publisher()
        install.assert_not_called()
        self.assert_partial()

    def test_windows_extra_child_just_before_freeze_is_retained_with_its_access(self):
        if os.name != "nt": self.skipTest("Windows no inherited-ACL propagation to racing child")
        original_prepare = diagnostics._DiagnosticsOutputClaim.prepare_publication_commit
        original_set, active, injected = diagnostics._set_windows_dacl, [], []
        def prepare(claim):
            active.append(claim)
            return original_prepare(claim)
        def set_dacl(handle, sddl):
            if handle == active[0].directory.handle:
                # The initial private directory has no inheritable ACEs. Freezing
                # its DACL must not strip access from this unowned racing subtree.
                directory = self.stage / "unexpected-directory"
                directory.mkdir()
                (directory / "foreign.txt").write_bytes(b"foreign subtree bytes")
                injected.append(directory)
            return original_set(handle, sddl)
        with self.runtime(), patch.object(diagnostics._DiagnosticsOutputClaim, "prepare_publication_commit", prepare), \
             patch.object(diagnostics, "_set_windows_dacl", side_effect=set_dacl), _only_output_mutations(self.stage):
            with self.assertRaisesRegex(diagnostics.AnomalyFailureDiagnosticsError, "staging retained for inspection"):
                self.run_publisher()
        self.assertEqual(len(injected), 1)
        self.assert_partial()
        foreign = injected[0] / "foreign.txt"
        self.assertEqual(foreign.read_bytes(), b"foreign subtree bytes")
        with foreign.open("r+b") as handle:
            self.assertEqual(handle.read(), b"foreign subtree bytes")

    def test_child_handle_release_failure_precedes_commit(self):
        original = diagnostics._DiagnosticsOutputClaim.release_child_handles
        def fail(claim):
            original(claim)
            raise OSError("synthetic child close failure")
        with self.runtime(), patch.object(diagnostics._DiagnosticsOutputClaim, "release_child_handles", fail), \
             patch.object(diagnostics._DiagnosticsOutputClaim, "install_output") as install, _only_output_mutations(self.stage):
            with self.assertRaisesRegex(diagnostics.AnomalyFailureDiagnosticsError, "staging retained for inspection"):
                self.run_publisher()
        install.assert_not_called()
        self.assert_partial()

    def test_windows_external_reader_blocking_directory_rename_fails_closed(self):
        if os.name != "nt": self.skipTest("Windows directory rename with open child")
        original = diagnostics._prepare_publication_rename()
        def commit(source, target, descriptor):
            with (self.stage / "result.json").open("rb"):
                return original(source, target, descriptor)
        with self.runtime(), patch.object(diagnostics, "_prepare_publication_rename", return_value=commit), _only_output_mutations(self.stage):
            with self.assertRaisesRegex(diagnostics.AnomalyFailureDiagnosticsError, "staging retained for inspection"):
                self.run_publisher()
        self.assert_partial()

    def test_windows_claim_guards_are_scoped_and_allow_unrelated_sibling_work(self):
        if os.name != "nt": self.skipTest("Windows native ancestry sharing guards")
        inside = self.root / "unrelated-project"
        inside.mkdir()
        claim = diagnostics._DiagnosticsOutputClaim(self.root)
        with tempfile.TemporaryDirectory(prefix="d2b-outside-sibling-") as external:
            outside = Path(external)
            self.assertEqual(outside.parent, self.root.parent)
            try:
                claim.claim()
                self.assertEqual([guard.path for guard in claim.guards], [self.root, self.stage.parent])
                for sibling in (inside, outside):
                    moved = sibling.rename(sibling.with_name(sibling.name + "-renamed"))
                    try:
                        (moved / "work.txt").write_bytes(b"unrelated work remains possible")
                        self.assertEqual((moved / "work.txt").read_bytes(), b"unrelated work remains possible")
                    finally:
                        moved.rename(sibling)
                for guarded in (self.root, self.stage.parent, claim.path):
                    with self.assertRaises(OSError): guarded.rename(guarded.with_name(guarded.name + "-moved"))
                    with self.assertRaises(OSError): guarded.rmdir()
                claim.check()
            finally:
                claim.close()

    def test_pre_marker_artifact_drift_is_detected_and_partial_output_is_retained(self):
        original_capture = diagnostics._capture_tree_bytes

        def changed(path, label):
            capture = original_capture(path, label)
            if path == self.input:
                capture["bytes"]["synthetic-input.txt"] += b"observed drift"
            return capture

        with self.runtime(), patch.object(diagnostics, "_capture_tree_bytes", side_effect=changed), _only_output_mutations(self.stage):
            with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError): self.run_publisher()
        self.assert_partial()
        self.assertEqual(self.before, self.protected_snapshot())

    def test_pre_marker_config_and_schema_drift_use_real_final_recheck(self):
        original = diagnostics._strict_object
        for source_key in ("diagnostics_config_source", "diagnostics_schema_source", "diagnostics_result_schema_source", "analysis_source", "analysis_schema_source"):
            changed_path = self.root / self.context[source_key]["path"]

            def drift(path, label):
                value, raw, raw_sha, canonical_sha = original(path, label)
                return value, raw + (b" " if path == changed_path else b""), raw_sha, canonical_sha

            with self.subTest(source=source_key), self.runtime(), patch.object(diagnostics, "_strict_object", side_effect=drift), _only_output_mutations(self.stage):
                with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError): self.run_publisher()
            self.reset_partial_fixture()
        self.assertEqual(self.before, self.protected_snapshot())

    def test_pre_marker_matrix_source_and_revision_drift_fail_closed(self):
        original = diagnostics.anomaly_matrix._load_object_snapshot

        def drift(path, label):
            value, raw, raw_sha, canonical_sha = original(path, label)
            return value, raw + (b" " if path == self.root / diagnostics.EXPECTED_MATRIX_CONFIG_PATH else b""), raw_sha, canonical_sha

        with self.runtime(), patch.object(diagnostics.anomaly_matrix, "_load_object_snapshot", side_effect=drift), _only_output_mutations(self.stage):
            with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError): self.run_publisher()
        self.reset_partial_fixture()
        changed = deepcopy(self.compatibility)
        changed["replay_revision"]["head"] = "f" * 40
        with self.runtime(), patch.object(diagnostics, "_validate_revision_compatibility", return_value=changed), _only_output_mutations(self.stage):
            with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError): self.run_publisher()
        self.assert_partial()

    def test_write_and_fsync_failures_never_leave_completed_output(self):
        original = diagnostics._DiagnosticsOutputClaim.write_exclusive
        for name in ("result.json", "summary.md", diagnostics._STAGED_MARKER):
            def fail(claim, file_name, raw):
                if file_name == name: raise OSError("synthetic write failure")
                return original(claim, file_name, raw)
            with self.subTest(name=name), self.runtime(), patch.object(diagnostics._DiagnosticsOutputClaim, "write_exclusive", fail), _only_output_mutations(self.stage):
                with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError): self.run_publisher()
            self.reset_partial_fixture()
        for failure_call in (1, 2, 3):
            real_fsync, calls = os.fsync, []
            def fsync(descriptor):
                calls.append(descriptor)
                if len(calls) == failure_call: raise OSError("synthetic fsync failure")
                return real_fsync(descriptor)
            with self.subTest(fsync=failure_call), self.runtime(), patch.object(os, "fsync", side_effect=fsync), _only_output_mutations(self.stage):
                with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError): self.run_publisher()
            self.reset_partial_fixture()
        self.assertEqual(self.before, self.protected_snapshot())

    def test_renderer_failure_precedes_any_output_claim(self):
        with self.runtime(_render_verified_summary=lambda *args: (_ for _ in ()).throw(RuntimeError("renderer failed"))), _write_traps():
            with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError): self.run_publisher()
        self.assertFalse(self.stage.exists())

    def test_each_staged_file_readback_mismatch_retains_markerless_output(self):
        original = diagnostics._DiagnosticsOutputClaim.read_owned
        for changed_name in ("result.json", "summary.md", diagnostics._STAGED_MARKER):
            def mismatch(claim, name):
                raw = original(claim, name)
                if name == changed_name:
                    return raw + b"changed"
                return raw
            with self.subTest(name=changed_name), self.runtime(), patch.object(diagnostics._DiagnosticsOutputClaim, "read_owned", mismatch), _only_output_mutations(self.stage):
                with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError): self.run_publisher()
            self.reset_partial_fixture()

    def test_extra_file_race_is_rejected_without_deleting_any_files(self):
        original = diagnostics._DiagnosticsOutputClaim.verify_files
        injected = []
        def extra(claim, expected):
            if not injected:
                (self.stage / "extra.txt").write_bytes(b"unexpected extra file")
                injected.append(True)
            return original(claim, expected)
        with self.runtime(), patch.object(diagnostics._DiagnosticsOutputClaim, "verify_files", extra), _only_output_mutations(self.stage):
            with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError): self.run_publisher()
        self.assert_partial()
        self.assertEqual((self.stage / "extra.txt").read_bytes(), b"unexpected extra file")

    def test_unexpected_directory_is_retained_without_recursion(self):
        original = diagnostics._DiagnosticsOutputClaim.verify_files
        injected = []
        def extra(claim, expected):
            if not injected:
                directory = self.stage / "unexpected-directory"
                directory.mkdir()
                (directory / "do-not-delete.txt").write_bytes(b"foreign subtree")
                injected.append(True)
            return original(claim, expected)
        with self.runtime(), patch.object(diagnostics._DiagnosticsOutputClaim, "verify_files", extra), _only_output_mutations(self.stage):
            with self.assertRaisesRegex(diagnostics.AnomalyFailureDiagnosticsError, "retained for inspection"): self.run_publisher()
        self.assertEqual((self.stage / "unexpected-directory/do-not-delete.txt").read_bytes(), b"foreign subtree")
        self.assertFalse(self.output.exists())
        self.assertEqual(self.before, self.protected_snapshot())

    def test_output_file_reparse_status_is_fail_closed(self):
        original_stat = os.stat
        def reparse(path, *args, **kwargs):
            metadata = original_stat(path, *args, **kwargs)
            if (Path(path) == self.stage / "result.json" or path == "result.json") and kwargs.get("follow_symlinks") is False:
                return SimpleNamespace(st_dev=metadata.st_dev, st_ino=metadata.st_ino, st_mode=stat.S_IFREG, st_file_attributes=0x400)
            return metadata
        with self.runtime(), patch.object(os, "stat", side_effect=reparse), _only_output_mutations(self.stage):
            with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError): self.run_publisher()
        self.assertFalse(self.output.exists())
        self.assertEqual(self.before, self.protected_snapshot())

    def test_payload_drift_from_original_draft_is_rejected(self):
        with self.runtime() as replay, _write_traps():
            replay.return_value = (self.sealed, self.context, self.payload + b" ")
            with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError): self.run_publisher()
        self.assertFalse(self.stage.exists())

    def test_payload_is_recompared_immediately_before_marker(self):
        original, calls = diagnostics._sealed_payload_bytes, []
        def drift(result, captured):
            calls.append(self.output.exists())
            return original(result, captured + b" " if len(calls) == 2 else captured)
        with self.runtime(_sealed_payload_bytes=drift), _only_output_mutations(self.stage):
            with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError): self.run_publisher()
        self.assertEqual(calls, [False, False])
        self.assert_partial()

    def test_failure_never_attempts_deletion_even_after_identity_or_reparse_change(self):
        real_identity = diagnostics._directory_identity
        real_reparse = diagnostics._is_reparse_point
        for kind in ("identity", "reparse"):
            state = {"changed": False}
            def identity(path):
                value = real_identity(path)
                return (value[0], value[1] + 1) if state["changed"] and path == self.stage and kind == "identity" else value
            def reparse(path):
                return True if state["changed"] and path == self.stage and kind == "reparse" else real_reparse(path)
            def fail_boundary(*args):
                state["changed"] = True
                raise diagnostics.AnomalyFailureDiagnosticsError("boundary drift")
            with self.subTest(kind=kind), self.runtime(_recheck_verified_replay_boundary=fail_boundary), \
                 patch.object(diagnostics, "_directory_identity", side_effect=identity), \
                 patch.object(diagnostics, "_is_reparse_point", side_effect=reparse), _only_output_mutations(self.stage) as mutations:
                with self.assertRaisesRegex(diagnostics.AnomalyFailureDiagnosticsError, "retained for inspection"): self.run_publisher()
            self.assertTrue(self.stage.is_dir())
            self.assertFalse(self.output.exists())
            self.assertFalse(any(row[0] in {"unlink", "rmdir"} for row in mutations))
            self.reset_partial_fixture()
        self.assertEqual(self.before, self.protected_snapshot())

    def test_directory_rename_is_final_commit_with_no_post_commit_checks_reads_or_hashes(self):
        committed = []
        original_rename = diagnostics._prepare_publication_rename()
        def commit(source, target, directory_fd):
            original_rename(source, target, directory_fd)
            committed.append(True)
        def before_only(original):
            def call(*args, **kwargs):
                self.assertFalse(committed, "fallible work after successful marker commit")
                return original(*args, **kwargs)
            return call
        with ExitStack() as stack:
            stack.enter_context(self.runtime())
            stack.enter_context(patch.object(diagnostics, "_prepare_publication_rename", return_value=commit))
            for name in ("_recheck_verified_replay_boundary", "_sealed_payload_bytes", "_strict_bytes", "_sha256_bytes", "_set_windows_dacl"):
                stack.enter_context(patch.object(diagnostics, name, before_only(getattr(diagnostics, name))))
            for name in ("check", "verify_files", "read_owned", "write_exclusive"):
                stack.enter_context(patch.object(diagnostics._DiagnosticsOutputClaim, name, before_only(getattr(diagnostics._DiagnosticsOutputClaim, name))))
            for name in ("open", "stat", "lstat", "scandir", "fsync", "read", "lseek", "unlink", "rmdir", "chmod"):
                stack.enter_context(patch.object(os, name, before_only(getattr(os, name))))
            receipt = self.run_publisher()
        self.assertEqual(committed, [True])
        self.assertEqual(receipt["status"], "published")
        self.assertEqual({path.name for path in self.output.iterdir()}, {"result.json", "summary.md", ".complete"})

    def test_handle_close_error_cannot_turn_a_committed_publish_into_failure(self):
        original_close = diagnostics._OutputDirectoryGuard.close
        def close(guard):
            original_close(guard)
            if (self.output / ".complete").exists():
                raise OSError("synthetic close failure after actual release")
        with self.runtime(), patch.object(diagnostics._OutputDirectoryGuard, "close", close), _only_output_mutations(self.stage):
            receipt = self.run_publisher()
        self.assertEqual(receipt["status"], "published")
        self.assertTrue((self.output / ".complete").is_file())

    def test_cli_modes_head_requirement_and_no_overrides(self):
        invalid = ([], ["--run"], ["--run", "--replay-head", "A" * 40], ["--run", "--replay-head", "0" * 39],
                   ["--validate-only", "--run"], ["--validate-only", "--replay-head", "0" * 40],
                   ["--run", "--replay-head", "0" * 40, "--output", "elsewhere"],
                   ["--run", "--replay-head", "0" * 40, "--config", "other.json"])
        with patch.object(diagnostics, "run_and_publish_diagnostics", side_effect=AssertionError("must not run")):
            for args in invalid:
                with self.subTest(args=args), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    self.assertEqual(diagnostics.main(args), 2)

    def test_cli_validate_only_zero_writes_and_run_success_receipt(self):
        with patch.object(diagnostics, "run_and_publish_diagnostics", side_effect=AssertionError("no publisher")), \
             patch.object(diagnostics, "_replay_and_build_with_context", side_effect=AssertionError("no replay")), \
             redirect_stdout(io.StringIO()) as output, _write_traps():
            self.assertEqual(diagnostics.main(["--root", str(self.root), "--validate-only"]), 0)
        self.assertIn("run_status: not_run", output.getvalue())
        self.assertIn("filesystem_write: false", output.getvalue())
        receipt = {"status": "published", "output_path": str(self.output), "result_sha256": "1" * 64, "summary_sha256": "2" * 64, "completion_marker_sha256": "3" * 64}
        with patch.object(diagnostics, "run_and_publish_diagnostics", return_value=receipt) as run, redirect_stdout(io.StringIO()) as output:
            self.assertEqual(diagnostics.main(["--root", str(self.root), "--run", "--replay-head", "0" * 40]), 0)
        run.assert_called_once_with(self.root, replay_head="0" * 40)
        self.assertIn("published: " + str(self.output), output.getvalue())
        for field in ("result_sha256", "summary_sha256", "completion_marker_sha256"):
            self.assertIn(field + ": " + receipt[field], output.getvalue())
        with patch.object(diagnostics, "run_and_publish_diagnostics", side_effect=diagnostics.AnomalyFailureDiagnosticsError("not published")), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(diagnostics.main(["--run", "--replay-head", "0" * 40]), 1)
        self.assertNotIn("published:", output.getvalue())
        self.assertNotIn("Traceback", output.getvalue())


if __name__ == "__main__":
    unittest.main()
