"""Read-only Git/source boundary fixtures; no formal runtime acceptance claim."""

from __future__ import annotations

import base64
import hashlib
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

from banto_ai import _anomaly_v03_contract as c
from banto_ai import _anomaly_v03_runtime as rt
from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_materializer as m
from banto_ai import anomaly_v03_runner as r
from banto_ai import _anomaly_v03_io as out
from tests.test_anomaly_v03_runner import fixture_checkout

ROOT = Path(__file__).resolve().parents[1]


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="banto-v03-source-fixture-")
        self.root = Path(self.temporary.name)
        paths = [*c.CONFIG_PATHS, *c.SCHEMA_PATHS, c.PLAN_PATH, "src/banto_ai/generator.py",
                 *("src/banto_ai/"+name+".py" for name in ("anomaly_v03", "_anomaly_v03_contract", "_anomaly_v03_schema",
                   "_anomaly_v03_numeric", "anomaly_v03_scoring", "anomaly_v03_episodes", "anomaly_v03_materializer",
                   "anomaly_v03_runner", "_anomaly_v03_runtime", "_anomaly_v03_io")), "tools/evaluator/run_anomaly_v03.py"]
        self.files = {name: (ROOT/name).read_bytes() for name in paths}
        for name, raw in self.files.items():
            path = self.root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        self.blobs = {hashlib.sha1(raw).hexdigest():raw for raw in self.files.values()}
        self.tree = b"".join(f"100644 blob {hashlib.sha1(raw).hexdigest()}\t{name}\0".encode() for name, raw in self.files.items())
        self.plan = v.strict_json((ROOT/"tests/fixtures/anomaly-v03-plan-snapshots.json").read_bytes())
        self.head, self.dirty, self.extra = b"a"*40+b"\n", b"", b""

    def tearDown(self):
        self.temporary.cleanup()

    def git(self, root, *args):
        self.assertEqual(root, self.root)
        if args == ("rev-parse", "HEAD"): return self.head
        if args[0] == "status": return self.dirty
        if args[0] == "ls-files": return self.extra
        if args[0] == "ls-tree": return self.tree
        if args[0] == "cat-file": return self.blobs[args[2]]
        if args == ("show", c.BASE_REVISION+":src/banto_ai/generator.py"): return self.files["src/banto_ai/generator.py"]
        if args[0] == "show":
            key = "science_zlib_base85" if args[1].startswith(c.SCIENCE_REVISION) else "status_zlib_base85"
            return zlib.decompress(base64.b85decode(self.plan[key]))
        raise AssertionError(args)

    def test_complete_captured_source_and_plan_bytes_bound_to_revision(self):
        with patch.object(rt, "_git", side_effect=self.git):
            captured = rt.capture_checkout(self.root, "a"*40)
            captured.recheck()
        self.assertEqual(captured.snapshots(), {"a"*40:self.files})
        self.assertEqual({x["path"] for x in captured.source_descriptor()["sources"]}, set(self.files))

    def test_wrong_head_dirty_and_untracked_source_are_global(self):
        for attack in ("head", "dirty", "extra"):
            self.head, self.dirty, self.extra = b"a"*40+b"\n", b"", b""
            if attack == "head": self.head = b"b"*40+b"\n"
            elif attack == "dirty": self.dirty = b" M src/changed.py\n"
            else: self.extra = b"src/injected.py\0"
            with patch.object(rt, "_git", side_effect=self.git), self.subTest(attack=attack), self.assertRaises(rt.IntegrityError):
                rt.capture_checkout(self.root, "a"*40)

    def test_byte_only_CRLF_difference_not_silently_normalized(self):
        path = self.root/c.CONFIG_PATHS[0]
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        with patch.object(rt, "_git", side_effect=self.git), self.assertRaisesRegex(rt.IntegrityError, "working bytes"):
            rt.capture_checkout(self.root, "a"*40)

    def test_missing_required_S3_source_and_git_link_rejected(self):
        original = self.tree
        for attack in ("missing", "link"):
            if attack == "missing":
                self.tree = b"\0".join(x for x in original.split(b"\0") if b"anomaly_v03_runner.py" not in x)
            else: self.tree = original.replace(b"100644 blob", b"120000 blob", 1)
            with patch.object(rt, "_git", side_effect=self.git), self.subTest(attack=attack), self.assertRaises(rt.IntegrityError):
                rt.capture_checkout(self.root, "a"*40)

    def test_boundary_rechecks_source_bytes_not_just_git_status(self):
        with patch.object(rt, "_git", side_effect=self.git):
            captured = rt.capture_checkout(self.root, "a"*40)
            (self.root/"src/banto_ai/anomaly_v03_runner.py").write_bytes(b"# replaced despite clean fake status\n")
            with self.assertRaisesRegex(rt.IntegrityError, "working source bytes changed"):
                captured.recheck()

    def test_formal_pin_guard_rejects_wrong_python_before_filesystem_probe(self):
        with patch.object(rt.platform, "python_version", return_value="3.12.13"), \
                patch.object(rt, "regular_path", side_effect=AssertionError("filesystem accessed")), \
                self.assertRaisesRegex(rt.IntegrityError, "unsupported_runtime"):
            rt.probe_runtime(self.root)


class PreparedEngineTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="banto-v03-engine-fixture-")
        self.parent = Path(self.temporary.name)
        self.checkout, self.runtime = fixture_checkout(), {"fixture": "fake-materializer-failure", "native_acceptance": "not_completed"}

    def tearDown(self):
        self.temporary.cleanup()

    def test_materializer_failure_is_global_and_retains_full_failure_ledger(self):
        with out.FixturePublication(self.parent, "all-failed") as store, \
                patch.object(m, "materialize_pair", side_effect=OSError("deliberate fixture failure")) as materialize:
            run = r._run_prepared("smoke", store, self.checkout, self.runtime, lambda: None)
        self.assertEqual(materialize.call_count, 1)
        self.assertEqual(run["result"]["coverage"], dict(success=0, partial=0, inconclusive=0, failed=1, not_started=143))
        self.assertEqual(run["result"]["status"], r._status("failed", "fail"))
        self.assertIsNone(run["publication"])
        self.assertTrue((store.stage/"result.json").exists())
        self.assertFalse((store.root/".complete").exists())

    def test_global_integrity_failure_retains_all_planned_slots_no_marker(self):
        with out.FixturePublication(self.parent, "global") as store, \
                patch.object(m, "materialize_pair", side_effect=rt.IntegrityError("paired input changed")):
            run = r._run_prepared("holdout", store, self.checkout, self.runtime, lambda: None)
            self.assertIsNone(run["publication"])
            self.assertEqual(run["result"]["coverage"]["not_started"], 2879)
            self.assertEqual(len(run["result"]["evaluations"]), 2880)
            self.assertTrue((store.stage/"result.json").exists())
            self.assertFalse((store.root/".complete").exists())

    def test_publication_failure_has_complete_ledger_in_exception_and_owned_evidence(self):
        def scoring_failure(*_):
            raise r.CellFailure("scoring")
        with out.FixturePublication(self.parent, "publish-failed") as store, \
                patch.object(r._DiskBackend, "evaluate", side_effect=scoring_failure), \
                patch.object(out, "_rename_no_replace", side_effect=OSError("fixture rename failure")):
            with self.assertRaises(r.RunAborted) as error:
                r._run_prepared("smoke", store, self.checkout, self.runtime, lambda: None)
            self.assertEqual(error.exception.result["status"], r._status("failed", "fail"))
            self.assertEqual(len(error.exception.result["evaluations"]), 144)
            self.assertEqual(v.strict_json((store.root/"failure.json").read_bytes())["result"], error.exception.result)
            self.assertFalse((store.root/".complete").exists())


if __name__ == "__main__":
    unittest.main()
