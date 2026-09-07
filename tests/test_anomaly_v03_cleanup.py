"""Pure contract tests; no native acceptance and no fixture creation."""

from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tests.fixtures.anomaly_v03_cleanup_model import CapturedObject, CleanupEvidenceError, CleanupJournal


def captured(name, *, directory=False, content=b"abc"):
    return CapturedObject(name, directory, ("identity:" + name).encode(),
                          b"DUMMY_PRIVATE_OLD_SD", b"DUMMY_PRIVATE_NEW_SD",
                          b"" if directory else content)


def journal():
    return CleanupJournal((captured("", directory=True), captured("control", directory=True),
                           captured("control/data.bin")), b"DUMMY_PRIVATE_OPERATIONS")


def remove(record, name):
    record.begin(name, "acl")
    record.confirmed()
    record.begin(name, "delete")
    record.confirmed()
    record.close_confirmed(name)
    record.begin(name, "absence")
    record.confirmed()


class CleanupEvidenceTests(unittest.TestCase):
    def test_snapshot_is_immutable_and_sensitive_evidence_is_not_in_repr_or_report(self):
        record = journal()
        objects, operations = record.private_snapshot
        self.assertEqual(operations, b"DUMMY_PRIVATE_OPERATIONS")
        self.assertEqual(objects[-1].content, b"abc")
        with self.assertRaises(FrozenInstanceError):
            objects[-1].content = b"changed"
        safe = repr(record) + repr(objects) + json.dumps(record.report())
        self.assertNotIn("DUMMY", safe)
        self.assertNotIn("identity:", safe)

    def test_complete_requires_confirmed_absence_of_every_object(self):
        record = journal()
        with self.assertRaises(CleanupEvidenceError):
            record.complete()
        for name in ("control/data.bin", "control", ""):
            remove(record, name)
        record.complete()
        report = record.report()
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["confirmed_absent_objects"], 3)
        self.assertEqual(report["confirmed_absent_bytes"], 3)
        self.assertEqual(report["retained_captured_objects_max"], 0)
        self.assertEqual(report["success_residue_count"], 0)
        self.assertFalse(report["native_accepted"])
        self.assertFalse(report["formal_permission"])

    def test_delete_success_and_close_success_alone_are_not_absence(self):
        record = journal()
        record.begin("control/data.bin", "acl")
        record.confirmed()
        record.begin("control/data.bin", "delete")
        record.confirmed()
        record.close_confirmed("control/data.bin")
        report = record.report()
        self.assertEqual(report["confirmed_absent_objects"], 0)
        self.assertEqual(report["unknown_objects"], 1)
        self.assertEqual(report["retained_captured_bytes_min"], 0)
        self.assertEqual(report["retained_captured_bytes_max"], 3)
        self.assertIsNone(report["success_residue_count"])

    def test_partial_cleanup_preserves_original_snapshot_and_exact_known_bounds(self):
        record = CleanupJournal((captured("", directory=True), captured("control", directory=True),
                                 captured("control/a.bin", content=b"12345"),
                                 captured("control/b.bin", content=b"1234567")), b"operations")
        before = record.private_snapshot
        digest = record.report()["snapshot_sha256"]
        remove(record, "control/a.bin")
        record.begin("control/b.bin", "acl")
        record.failed()
        report = record.report()
        self.assertEqual(record.private_snapshot, before)
        self.assertEqual(report["snapshot_sha256"], digest)
        self.assertEqual(report["captured_bytes"], 12)
        self.assertEqual(report["confirmed_absent_bytes"], 5)
        self.assertEqual(report["retained_captured_bytes_min"], 7)
        self.assertEqual(report["retained_captured_bytes_max"], 7)
        self.assertEqual(report["objects"][-1]["acl"], "unknown")
        self.assertEqual(report["status"], "failed")

    def test_failure_after_each_mutation_boundary_never_claims_unobserved_absence(self):
        for boundary in ("acl_pending", "acl_confirmed", "delete_pending", "delete_armed", "closed", "absence_pending"):
            with self.subTest(boundary=boundary):
                record = journal()
                record.begin("control/data.bin", "acl")
                if boundary != "acl_pending":
                    record.confirmed()
                if boundary not in ("acl_pending", "acl_confirmed"):
                    record.begin("control/data.bin", "delete")
                    if boundary != "delete_pending":
                        record.confirmed()
                    if boundary in ("closed", "absence_pending"):
                        record.close_confirmed("control/data.bin")
                    if boundary == "absence_pending":
                        record.begin("control/data.bin", "absence")
                record.failed()
                report = record.report()
                self.assertEqual(report["confirmed_absent_objects"], 0)
                self.assertIsNone(report["success_residue_count"])
                self.assertEqual(report["retained_captured_bytes_max"], 3)
                self.assertEqual(report["retained_captured_bytes_min"],
                                 3 if boundary.startswith("acl_") else 0)

    def test_resource_stop_latches_and_only_owned_close_can_continue(self):
        record = journal()
        record.begin("control/data.bin", "acl")
        record.confirmed()
        record.begin("control/data.bin", "delete")
        # Every filesystem entrypoint below must remain unused even by report().
        with patch("builtins.open", side_effect=AssertionError), \
             patch.object(Path, "exists", side_effect=AssertionError), \
             patch.object(Path, "stat", side_effect=AssertionError), \
             patch.object(Path, "iterdir", side_effect=AssertionError), \
             patch.object(Path, "read_bytes", side_effect=AssertionError):
            record.failed(resource_stop=True)
            record.close_failed("control/data.bin")
            record.close_confirmed("control/data.bin")
            record.failed(resource_stop=False)
            for action in (lambda: record.begin("control", "acl"), record.confirmed, record.complete):
                with self.assertRaises(CleanupEvidenceError):
                    action()
            report = record.report()
        self.assertTrue(report["resource_stop"])
        self.assertEqual(report["objects"][-1]["failed_operation"], "delete")
        self.assertEqual(report["objects"][-1]["close"], "confirmed")
        self.assertEqual(report["objects"][-1]["deletion"], "unknown")

    def test_close_failure_stops_attempt_without_losing_prior_evidence(self):
        record = journal()
        record.begin("control/data.bin", "acl")
        record.confirmed()
        record.begin("control/data.bin", "delete")
        record.confirmed()
        record.close_failed("control/data.bin")
        report = record.report()
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["objects"][-1]["failed_operation"], "close")
        self.assertEqual(report["objects"][-1]["deletion"], "armed")

    def test_parent_cannot_be_deleted_before_child_absence(self):
        record = journal()
        record.begin("control", "acl")
        record.confirmed()
        with self.assertRaises(CleanupEvidenceError):
            record.begin("control", "delete")
        remove(record, "control/data.bin")
        record.begin("control", "delete")

    def test_unknown_object_cannot_be_adopted(self):
        record = journal()
        before = record.report()
        for action in (lambda: record.begin("foreign", "acl"), lambda: record.close_confirmed("foreign")):
            with self.assertRaises(CleanupEvidenceError):
                action()
        self.assertEqual(record.report(), before)

    def test_bad_order_duplicate_confirmation_and_retry_rejected(self):
        record = journal()
        for action in (record.confirmed, lambda: record.begin("control/data.bin", "delete"),
                       lambda: record.begin("control/data.bin", "absence"),
                       lambda: record.begin("control/data.bin", "rename")):
            with self.assertRaises(CleanupEvidenceError):
                action()
        record.begin("control/data.bin", "acl")
        with self.assertRaises(CleanupEvidenceError):
            record.begin("control", "acl")
        record.confirmed()
        with self.assertRaises(CleanupEvidenceError):
            record.confirmed()
        record.failed()
        with self.assertRaises(CleanupEvidenceError):
            record.begin("control/data.bin", "acl")

    def test_close_cannot_precede_disposition_outcome_record(self):
        record = journal()
        record.begin("control/data.bin", "acl")
        record.confirmed()
        record.begin("control/data.bin", "delete")
        for action in (lambda: record.close_confirmed("control/data.bin"),
                       lambda: record.close_failed("control/data.bin")):
            with self.assertRaises(CleanupEvidenceError):
                action()
        record.failed()
        record.close_confirmed("control/data.bin")

    def test_identity_security_content_and_operation_changes_affect_snapshot_digest(self):
        objects, operations = journal().private_snapshot
        digest = CleanupJournal(objects, operations).report()["snapshot_sha256"]
        for change in ({"identity": b"other-id"}, {"security": b"other-sd"},
                       {"cleanup_security": b"other-target"}, {"content": b"xyz"}):
            changed = (*objects[:-1], replace(objects[-1], **change))
            self.assertNotEqual(CleanupJournal(changed, operations).report()["snapshot_sha256"], digest)
        self.assertNotEqual(CleanupJournal(objects, b"other-operation").report()["snapshot_sha256"], digest)
        self.assertEqual(CleanupJournal(tuple(reversed(objects)), operations).report()["snapshot_sha256"], digest)

    def test_bounded_strict_inputs_and_tree_shape(self):
        root = captured("", directory=True)
        for objects, operations in (((), b"op"), ([root], b"op"), ((root, root), b"op"),
                                    ((captured("file"),), b"op"),
                                    ((root, captured("missing/file")), b"op"),
                                    ((root, captured("parent"), captured("parent/file")), b"op"),
                                    ((root,), b""), ((root,), b"x" * (1024*1024+1)),
                                    ((root,) + tuple(captured(f"f{i}") for i in range(32)), b"op"),
                                    ((root,) + tuple(captured(f"f{i}", content=b"x"*(1024*1024))
                                                     for i in range(5)), b"op")):
            with self.assertRaises(CleanupEvidenceError):
                CleanupJournal(objects, operations)
        for change in ({"name": "../escape"}, {"name": "a/../escape"}, {"name": "C:/private"},
                       {"name": "a:stream"}, {"name": "a"*129}, {"directory": 1},
                       {"directory": True, "content": b"x"}, {"content": bytearray(b"x")},
                       {"content": b"x"*(1024*1024+1)}, {"identity": b""},
                       {"security": b"x"*(64*1024+1)}):
            with self.assertRaises(CleanupEvidenceError):
                replace(captured("valid"), **change)

    def test_failures_are_redacted(self):
        with self.assertRaises(CleanupEvidenceError) as caught:
            journal().begin("DUMMY_SECRET/path", "acl")
        self.assertEqual(str(caught.exception), "cleanup_evidence_contract")

    def test_completed_journal_cannot_be_reopened_or_reclassified(self):
        record = journal()
        for name in ("control/data.bin", "control", ""):
            remove(record, name)
        record.complete()
        for action in (lambda: record.begin("", "acl"), record.failed, record.complete,
                       lambda: record.close_failed("")):
            with self.assertRaises(CleanupEvidenceError):
                action()
