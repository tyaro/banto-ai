"""Ordinary single-writer storage in small, independently owned temp directories."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from banto_ai import _anomaly_v03_io as out
from banto_ai import _anomaly_v03_runtime as rt
from banto_ai import anomaly_v03_materializer as m


FILES = {"result.json": b'{"count":2}\n', "summary.md": b"2 saved records\n"}


def verify_result(files):
    rt.require(dict(files) == FILES, "result content mismatch")


class LocalPublicationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="banto-local-result-tests-")
        self.addCleanup(temporary.cleanup)
        self.parent = Path(temporary.name)

    def stage(self, name="attempt"):
        store = out.LocalPublication(self.parent, name)
        self.addCleanup(store.close)
        for path, raw in FILES.items():
            store.write(path, raw)
        return store

    def assert_stopped(self, store):
        self.assertTrue(store.failed)
        with patch.object(store, "check", side_effect=AssertionError("IO after stop")):
            for operation in (lambda: store.write("later.json", b"{}\n"), lambda: store.read("result.json"),
                              store.verify, lambda: store.publish(verify_result, lambda: None)):
                with self.assertRaisesRegex(rt.IntegrityError, "stopped"):
                    operation()

    def test_local_roundtrip_uses_distinct_format_and_no_fixture_parent_gate(self):
        with patch.object(out, "_fixture_parent", side_effect=AssertionError("temp-only gate")):
            receipt = out.publish_local_result(self.parent, "ordinary", FILES, verify_semantics=verify_result)
        root = Path(receipt["output_path"])
        report = out.verify_local_publication(root, expected_marker_sha256=receipt["marker_raw_sha256"], verify_semantics=verify_result)
        self.assertEqual(report, {"payloads": 2, "local_verified": True, "native_acceptance": "not_completed"})
        self.assertEqual(out.v.strict_json((root/".complete").read_bytes())["marker_type"], "anomaly-v03-local-complete")
        with self.assertRaisesRegex(rt.IntegrityError, "completion inventory"):
            out.verify_fixture_publication(root, expected_marker_sha256=receipt["marker_raw_sha256"], verify_semantics=verify_result)
        with self.assertRaisesRegex(rt.IntegrityError, "s4_acceptance_not_frozen"):
            rt.require_campaign_acceptance()

    def test_existing_and_incomplete_results_are_never_reclaimed(self):
        first = self.stage()
        with self.assertRaises(FileExistsError):
            out.LocalPublication(self.parent, "attempt")
        first.close()
        with self.assertRaises(FileExistsError):
            out.publish_local_result(self.parent, "attempt", FILES, verify_semantics=verify_result)
        self.assertEqual((first.stage/"result.json").read_bytes(), FILES["result.json"])
        self.assertFalse((first.root/".complete").exists())

    def test_write_failure_before_creation_cannot_be_ignored_and_published(self):
        store = self.stage()
        with patch.object(out, "_exclusive", side_effect=OSError("disk full before open")):
            with self.assertRaises(OSError):
                store.write("additional.json", b"{}\n")
        # Even when no partial file exists, losing the attempted output stops this run.
        self.assert_stopped(store)
        self.assertFalse((store.root/".complete").exists())

    def test_short_write_and_flush_failure_stop_without_completion_marker(self):
        for failure in ("partial", "flush"):
            with self.subTest(failure=failure):
                store = self.stage(failure)
                def partial(path, raw):
                    with path.open("xb") as stream:
                        stream.write(raw[:3])
                    raise OSError("partial write")
                target = patch.object(out, "_exclusive", side_effect=partial) if failure == "partial" else patch.object(out.os, "fsync", side_effect=OSError("flush failed"))
                with target, self.assertRaises(OSError):
                    store.write("additional.json", b'{"x":1}\n')
                self.assert_stopped(store)
                self.assertFalse((store.root/".complete").exists())

    def test_validation_rename_and_marker_failures_cannot_retry_publication(self):
        for failure in ("validation", "rename", "marker"):
            with self.subTest(failure=failure):
                store = self.stage(failure)
                verifier = verify_result
                if failure == "validation":
                    def verifier(_):
                        raise ValueError("wrong totals")
                    target = patch.object(out, "_rename_no_replace", wraps=out._rename_no_replace)
                elif failure == "rename":
                    target = patch.object(out, "_rename_no_replace", side_effect=OSError("rename failed"))
                else:
                    target = patch.object(out.os, "link", side_effect=OSError("marker failed"))
                with target, self.assertRaises((ValueError, OSError)):
                    store.publish(verifier, lambda: None)
                self.assert_stopped(store)
                self.assertFalse((store.root/".complete").exists())

    def test_closed_writer_cannot_read_write_verify_or_publish(self):
        store = self.stage()
        store.close()
        store.close()
        with patch.object(store, "check", side_effect=AssertionError("IO after close")):
            for operation in (lambda: store.write("later.json", b"{}\n"), lambda: store.read("result.json"),
                              store.verify, lambda: store.publish(verify_result, lambda: None), store.__enter__):
                with self.assertRaises(rt.IntegrityError):
                    operation()
        self.assertFalse((store.root/".complete").exists())

    def test_callback_cannot_hide_a_nested_storage_failure_before_commit(self):
        store = self.stage()
        calls = []
        def boundary():
            calls.append(None)
            if len(calls) == 2:
                try:
                    store.read("missing.json")
                except rt.IntegrityError:
                    pass
        with self.assertRaisesRegex(rt.IntegrityError, "stopped"):
            store.publish(verify_result, boundary)
        self.assertEqual(len(calls), 2)
        self.assert_stopped(store)
        self.assertFalse((store.root/".complete").exists())
        self.assertFalse(store.commit_attempted)

    def test_completed_result_cannot_be_republished_or_extended(self):
        store = self.stage()
        receipt = store.publish(verify_result, lambda: None)
        with patch.object(out, "_exclusive", side_effect=AssertionError("write after commit")):
            with self.assertRaises(rt.IntegrityError):
                store.publish(verify_result, lambda: None)
            with self.assertRaises(rt.IntegrityError):
                store.write("later.json", b"{}\n")
        self.assertTrue(store.committed)
        store.close()
        self.assertTrue(out.verify_local_publication(store.root, expected_marker_sha256=receipt["marker_raw_sha256"], verify_semantics=verify_result)["local_verified"])

    def test_process_exit_mid_save_leaves_incomplete_output_and_refuses_restart(self):
        script = """import os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from banto_ai._anomaly_v03_io import LocalPublication
store = LocalPublication(Path(sys.argv[2]), 'interrupted')
store.write('result.json', b'{"count":2}\\n')
os._exit(23)
"""
        result = subprocess.run([sys.executable, "-c", script, str(Path(__file__).resolve().parents[1]/"src"), str(self.parent)],
                                capture_output=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 23, result.stderr.decode(errors="replace"))
        root = self.parent/"interrupted"
        self.assertEqual((root/"stage"/"result.json").read_bytes(), FILES["result.json"])
        self.assertFalse((root/".complete").exists())
        with self.assertRaises(rt.IntegrityError):
            out.verify_local_publication(root, expected_marker_sha256="0"*64, verify_semantics=verify_result)
        with self.assertRaises(FileExistsError):
            out.LocalPublication(self.parent, "interrupted")

    def test_lost_commit_reply_stops_writer_but_does_not_retract_a_valid_marker(self):
        store = self.stage()
        link, saved = os.link, {}
        def lost_reply(source, target, **kwargs):
            saved["pin"] = m.sha(Path(source).read_bytes())
            link(source, target, **kwargs)
            raise OSError("reply lost after link")
        with patch.object(out.os, "link", side_effect=lost_reply), self.assertRaises(OSError):
            store.publish(verify_result, lambda: None)
        self.assert_stopped(store)
        self.assertFalse(store.committed)  # Writer did not receive confirmation.
        self.assertTrue(store.commit_attempted)
        with self.assertRaisesRegex(rt.IntegrityError, "commit attempt"):
            store.preserve_failure({"reason": "unknown commit"})
        self.assertFalse((store.root/"failure.json").exists())
        store.close()
        self.assertTrue(out.verify_local_publication(store.root, expected_marker_sha256=saved["pin"], verify_semantics=verify_result)["local_verified"])

    def test_formal_names_empty_inputs_and_invalid_paths_are_rejected(self):
        for name in ("../escape", "a/b", "NUL", "ANOMALY-MULTISEED-V03-HOLDOUT"):
            with self.subTest(name=name), self.assertRaises(out.v.V03ValidationError):
                out.LocalPublication(self.parent, name)
        reserved = self.parent/"Anomaly-Multiseed-v03-holdout"
        reserved.mkdir()
        with self.assertRaisesRegex(rt.IntegrityError, "formal root"):
            out.LocalPublication(reserved, "child")
        with self.assertRaises(rt.IntegrityError):
            out.publish_local_result(self.parent, "empty", {}, verify_semantics=verify_result)
        self.assertFalse((self.parent/"empty").exists())

    def test_failure_record_prevents_later_success(self):
        store = self.stage()
        store.preserve_failure({"reason": "calculation failed"})
        self.assert_stopped(store)
        self.assertTrue((store.root/"failure.json").exists())
        self.assertFalse((store.root/".complete").exists())


if __name__ == "__main__":
    unittest.main()
