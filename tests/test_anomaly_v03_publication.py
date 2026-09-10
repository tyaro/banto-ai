"""Small dedicated-temp fixtures; no repo/formal artifact writes or ACL changes."""

from __future__ import annotations

import copy
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_materializer as m
from banto_ai import anomaly_v03_runner as runner
from banto_ai import _anomaly_v03_io as out
from banto_ai import _anomaly_v03_runtime as rt
from tests.test_anomaly_v03_runner import fixture_checkout
from tests.test_anomaly_v03_materializer import release_class_fields


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="banto-v03-s3-fixture-")
        self.parent = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def verify_hand(files):
        rt.require(files == {"facts.json": b'{"count":20}\n', "summary.md": b"20 planned incidents\n"}, "hand reconstruction failed")

    def stage(self, name="attempt"):
        store = out.FixturePublication(self.parent, name)
        store.write("facts.json", b'{"count":20}\n')
        store.write("summary.md", b"20 planned incidents\n")
        return store

    def test_atomic_marker_full_inventory_readback_and_fresh_consumer(self):
        with self.stage() as store:
            self.assertFalse((store.root/".complete").exists())
            receipt = store.publish(self.verify_hand, lambda: None)
        report = out.verify_fixture_publication(Path(receipt["output_path"]), expected_marker_sha256=receipt["marker_raw_sha256"], verify_semantics=self.verify_hand)
        self.assertEqual(report["payloads"], 2)
        self.assertTrue(report["fixture_verified"])
        self.assertEqual(report["native_acceptance"], "not_completed")

    def test_existing_unmarked_root_and_second_claim_cannot_overwrite(self):
        target = self.parent/"existing"; target.mkdir(); (target/"old.txt").write_bytes(b"keep")
        with self.assertRaises(FileExistsError): out.FixturePublication(self.parent, "existing")
        self.assertEqual((target/"old.txt").read_bytes(), b"keep")
        with self.stage() as first:
            with self.assertRaises(FileExistsError): out.FixturePublication(self.parent, "attempt")
            self.assertEqual(first.read("facts.json"), b'{"count":20}\n')

    def test_root_outside_temp_formal_names_and_traversal_rejected(self):
        root = Path(__file__).resolve().parents[1]
        with self.assertRaises(rt.IntegrityError): out.FixturePublication(root, "bad")
        for name in ("../escape", "a/b", "C:escape", "anomaly-multiseed-v03-holdout", "NUL", "/absolute"):
            with self.subTest(name=name), self.assertRaises(v.V03ValidationError): out.FixturePublication(self.parent, name)
        self.assertEqual(list(self.parent.iterdir()), [])

    def test_nested_exclusive_writes_and_unknown_reads_rejected(self):
        with out.FixturePublication(self.parent, "nested") as store:
            store.write("datasets/one/observations.jsonl", b'{"value":1}\n')
            self.assertEqual(len(store.verify()), 1)
            for name in ("../escape.json", "x/../../escape", "a/CON", "C:/escape", "a//b"):
                with self.subTest(name=name), self.assertRaises(v.V03ValidationError): store.write(name, b"{}\n")
            with self.assertRaises(rt.IntegrityError): store.write("datasets/one/observations.jsonl", b"{}\n")
            with self.assertRaises(rt.IntegrityError): store.read("absent.json")

    def test_payload_and_directory_inventory_tamper_before_marker_rejected(self):
        for kind in ("bytes", "extra-file", "empty-dir", "missing"):
            with self.stage(kind) as store:
                if kind == "bytes": (store.stage/"facts.json").write_bytes(b'{"count":19}\n')
                elif kind == "extra-file": (store.stage/"extra.json").write_bytes(b"{}\n")
                elif kind == "empty-dir": (store.stage/"empty").mkdir()
                else: (store.stage/"facts.json").unlink()
                with self.subTest(kind=kind), self.assertRaises(rt.IntegrityError): store.publish(self.verify_hand, lambda: None)
                self.assertFalse((store.root/".complete").exists())
                self.assertTrue(store.root.exists())

    def test_summary_plus_marker_rehash_still_fails_semantic_reconstruction(self):
        with self.stage() as store:
            receipt = store.publish(self.verify_hand, lambda: None)
        root = Path(receipt["output_path"])
        (root/"payload"/"facts.json").write_bytes(b'{"count":19}\n')
        (root/"payload"/"summary.md").write_bytes(b"19 planned incidents\n")
        marker = v.strict_json((root/".complete").read_bytes())
        marker["payload_inventory"] = out.inventory(out.read_tree(root/"payload"))
        marker["inventory_sha256"] = v.canonical_sha256(marker["payload_inventory"])
        raw = m.json_bytes(marker)
        (root/".complete").write_bytes(raw)  # changes the linked pending marker too
        with self.assertRaisesRegex(rt.IntegrityError, "external marker"):
            out.verify_fixture_publication(root, expected_marker_sha256=receipt["marker_raw_sha256"], verify_semantics=self.verify_hand)
        with self.assertRaisesRegex(rt.IntegrityError, "hand reconstruction"):
            out.verify_fixture_publication(root, expected_marker_sha256=m.sha(raw), verify_semantics=self.verify_hand)

    def test_completion_marker_race_is_nonoverwrite_and_retains_payload(self):
        with self.stage() as store:
            # Deliberately create a competing marker immediately before link.
            link = os.link
            def race(source, target, **kwargs):
                Path(target).write_bytes(b"competitor")
                return link(source, target, **kwargs)
            with patch.object(out.os, "link", side_effect=race), self.assertRaises(FileExistsError):
                store.publish(self.verify_hand, lambda: None)
            self.assertEqual((store.root/".complete").read_bytes(), b"competitor")
            self.assertTrue((store.root/"payload"/"facts.json").exists())
            self.assertFalse(store.committed)

    def test_payload_directory_race_never_replaces_competing_tree(self):
        with self.stage() as store:
            (store.root/"payload").mkdir()
            (store.root/"payload"/"competitor.txt").write_bytes(b"keep")
            with self.assertRaises(OSError): store.publish(self.verify_hand, lambda: None)
            self.assertEqual((store.root/"payload"/"competitor.txt").read_bytes(), b"keep")
            self.assertTrue((store.root/"stage"/"facts.json").exists())
            self.assertFalse((store.root/".complete").exists())

    def test_hash_row_count_canonical_and_duplicate_JSON_attacks(self):
        for raw in (b'{"x":1,"x":2}\n', b'{"x":NaN}\n', b'{"x":1}\r\n', b'{ "x": 1 }\n'):
            with self.assertRaises(v.V03ValidationError): out.payload_entry("rows.jsonl", raw)
        descriptor = out.payload_entry("rows.jsonl", b'{"x":1}\n{"x":2}\n')
        self.assertEqual(descriptor["row_count"], 2)
        self.assertEqual(descriptor["canonical_sha256"], v.canonical_sha256([{"x":1}, {"x":2}]))

    def test_hardlink_payload_and_reparse_ancestor_rejected(self):
        with self.stage() as store:
            os.link(store.stage/"facts.json", self.parent/"outside-link.json")
            with self.assertRaisesRegex(rt.IntegrityError, "multiply-linked"):
                store.publish(self.verify_hand, lambda: None)
        real = Path.lstat
        def lstat(path):
            value = real(path)
            if path == self.parent:
                return SimpleNamespace(st_mode=value.st_mode, st_file_attributes=0x400)
            return value
        with patch.object(Path, "lstat", new=lstat), self.assertRaisesRegex(rt.IntegrityError, "reparse"):
            out.FixturePublication(self.parent, "reparse")
        self.assertFalse((self.parent/"reparse").exists())

    def test_boundary_failure_and_partial_write_leave_inspectable_staging(self):
        with self.stage() as store:
            with self.assertRaisesRegex(rt.IntegrityError, "source changed"):
                store.publish(self.verify_hand, lambda: (_ for _ in ()).throw(rt.IntegrityError("source changed")))
            self.assertTrue((store.stage/"facts.json").exists())
            self.assertFalse((store.root/".complete").exists())
        with out.FixturePublication(self.parent, "partial") as store:
            def partial(path, raw):
                path.write_bytes(raw[:3])
                raise OSError("disk full")
            with patch.object(out, "_exclusive", side_effect=partial), self.assertRaises(OSError): store.write("partial.json", b'{"x":1}\n')
            self.assertEqual((store.stage/"partial.json").read_bytes(), b'{"x')
            self.assertFalse((store.root/".complete").exists())

    def test_mutation_during_semantic_replay_is_detected(self):
        with self.stage() as store:
            def change(files):
                self.verify_hand(files)
                (store.stage/"facts.json").write_bytes(b'{"count":21}\n')
            with self.assertRaises(rt.IntegrityError): store.publish(change, lambda: None)
            self.assertFalse((store.root/".complete").exists())

    def test_directory_binding_detects_changed_identity(self):
        with self.stage() as store:
            binding = store.bindings[-1]
            binding.identity = (binding.identity[0], binding.identity[1]+1)
            with self.assertRaisesRegex(rt.IntegrityError, "identity changed"): store.verify()

    def test_failed_directory_binding_releases_open_handle(self):
        closed, close = [], out.DirectoryBinding.close
        def release(binding):
            closed.append(binding)
            close(binding)
        with patch.object(out.DirectoryBinding, "check", side_effect=rt.IntegrityError("changed during bind")), \
                patch.object(out.DirectoryBinding, "close", new=release), self.assertRaises(rt.IntegrityError):
            out.DirectoryBinding(self.parent)
        self.assertEqual(len(closed), 1)
        self.assertIsNone(closed[0].fd)
        self.assertIsNone(closed[0].handle)

    def test_native_readonly_preparation_has_all_denied_rights_and_never_accepts(self):
        rights = out.native_acl_requirements()
        self.assertEqual(set(rights["file"]), {"write", "append", "write_ea", "write_attributes", "delete"})
        self.assertEqual(set(rights["directory"]), {"add_file", "add_subdirectory", "delete_child", "write_ea", "write_attributes", "delete"})
        requirements = rt.acceptance_requirements()
        self.assertEqual(requirements["windows_python"], ["3.14.0"])
        self.assertEqual(requirements["linux_python"], ["3.12", "3.14"])
        self.assertEqual(requirements["independent_token_access_check"], "not_accepted")
        with patch.object(out.os, "name", "posix"), self.assertRaises(rt.IntegrityError):
            out.windows_readonly_access_check(self.parent, 123)


class ProducerReadbackTests(unittest.TestCase):
    """All-failed fake campaign uses the real inventory reader, never a PRNG."""
    @classmethod
    def setUpClass(cls):
        cls.addClassCleanup(release_class_fields, cls, "checkout", "runtime", "slots", "files", "result")
        cls.checkout, cls.runtime = fixture_checkout(), {"fixture": "hand-failure-only", "native_acceptance": "not_completed"}
        cls.slots = runner.planned_slots("smoke")
        cls.files = {"planned.json": m.json_bytes(runner.planned_metadata("smoke")), "runtime.json": m.json_bytes(cls.runtime)}
        for index, slot in enumerate(cls.slots):
            slot.update(status="failed", failure_stage="materialization", safe_reason="exception")
            cls.files[f"journal/{index:04d}-started.json"] = m.json_bytes(slot["identity"])
            cls.files[f"journal/{index:04d}-done.json"] = m.json_bytes(slot)
        cls.result = {"schema_version": "0.3", "result_type": "anomaly-multiseed-v03", "role": "smoke",
            "planned_counts": c_counts(), "evaluations": cls.slots, "coverage": runner._coverage(cls.slots),
            "status": runner._matrix_status(cls.slots, False), "provenance": runner._provenance(cls.checkout, out.inventory(cls.files))}
        cls.files["result.json"] = m.json_bytes(cls.result)
        cls.files["summary.md"] = runner.summary_bytes(cls.result)

    def test_full_failure_journal_is_not_engineering_success(self):
        with patch.object(m, "materialize_pair", side_effect=AssertionError("data generation")):
            report = runner._verify_producer_tree(self.files, self.checkout, self.runtime)
        self.assertEqual(report["coverage"]["failed"], 144)
        self.assertEqual(report["evaluations"], 144)
        self.assertEqual(report["performance_status"], "not_evaluated")

    def test_coordinated_count_ledger_status_summary_and_inventory_forgery(self):
        for attack in ("missing-slot", "duplicate-slot", "fake-success", "runtime", "journal", "extra-path"):
            files = dict(self.files); result = copy.deepcopy(self.result)
            if attack == "missing-slot": result["evaluations"].pop()
            elif attack == "duplicate-slot": result["evaluations"][1] = copy.deepcopy(result["evaluations"][0])
            elif attack == "fake-success":
                result["evaluations"][0].update(status="success", failure_stage=None, safe_reason=None,
                    input_hashes=dict.fromkeys(m.INPUT_FILES, "a"*64), evidence=[out.payload_entry("runtime.json", files["runtime.json"])])
            elif attack == "runtime": files["runtime.json"] = m.json_bytes({"accepted":True})
            elif attack == "journal": files["journal/0000-done.json"] = m.json_bytes({"status":"success"})
            else: files["extra.json"] = b"{}\n"
            result["coverage"] = runner._coverage(result["evaluations"])
            result["status"] = runner._matrix_status(result["evaluations"], False)
            result["provenance"] = runner._provenance(self.checkout, out.inventory({p:b for p,b in files.items() if p not in ("result.json", "summary.md")}))
            files["result.json"], files["summary.md"] = m.json_bytes(result), runner.summary_bytes(result)
            with self.subTest(attack=attack), self.assertRaises(v.V03ValidationError):
                runner._verify_producer_tree(files, self.checkout, self.runtime)


def c_counts():
    from banto_ai import _anomaly_v03_contract as c
    return c.counts("smoke")


if __name__ == "__main__":
    unittest.main()
