"""Real small journal/publication IO; source/runtime/science mocks are explicit."""
import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_attempt_controller as controller
from banto_ai import anomaly_v03_chunk_audit as audit
from banto_ai import anomaly_v03_chunk_contract as chunk
from banto_ai import anomaly_v03_engineering_contract as policy
from banto_ai import anomaly_v03_checkpoint_store as journal
from banto_ai import anomaly_v03_checkpoints as checkpoints
from banto_ai import _anomaly_v03_io as storage
from banto_ai import _anomaly_v03_engineering_runtime as resources
from tests import test_anomaly_v03_chunk_audit as audit_fixtures
from tests.test_anomaly_v03_chunk_contract import envelope
from tests.test_anomaly_v03_engineering import fixture_context


class ControllerTests(unittest.TestCase):
    def setUp(self):
        audit_fixtures.ChunkAuditTests.setUp(self)
        self.metadata = self.root / "metadata"
        self.tree = self.root / "attempts"
        self.tree.mkdir()
        self.plan = checkpoints.fixed_plan("a" * 40, "b" * 40)
        self.receipt = journal.create_store(self.root, "metadata", self.plan)
        self.observed = fixture_context()[1]
        self.session = self.open(self.receipt)

    def open(self, receipt, descriptor_pins=None):
        return controller.Controller(self.metadata, receipt, self.tree, self.root / "producer",
            self.root / "consumer", "f" * 40, descriptor_pins=descriptor_pins)

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        storage._exclusive(path, storage.json_bytes(value))

    def produce(self, context):
        layout = context["layout"]
        result = self.tree / layout["result_root"]
        files, _ = envelope(context["plan"], context["chunk_index"], context["attempt"])
        storage.publish_local_result(result.parent, "result", files, verify_semantics=lambda files: None)
        supervision = {"format": audit.SUPERVISION_FORMAT, "policy_id": policy.POLICY_ID, "scope": chunk.SCOPE,
            "attempt_id": "result", "binding": chunk.chunk_plan(self.plan, context["chunk_index"], context["attempt"])["binding"],
            "status": "complete", "exit_code": 0, "worker_exit_confirmed": True, "stop_reason": None,
            "observation_errors": [], "formal_permission": False, "performance_status": "not_evaluated",
            "resource_measurement_scope": "whole_worker_including_replays_and_exit", "elapsed_seconds": 1.0,
            "peak_worker_private_bytes": 1000, "runtime": self.observed, "runtime_after": copy.deepcopy(self.observed)}
        self.write(self.tree / layout["files"]["producer_supervision"], supervision)

    def inspect_audit(self, context):
        layout = context["layout"]
        result = self.tree / layout["result_root"]
        marker = storage.sha(storage.read_regular(result / ".complete", links=2))
        supervision = storage.sha(storage.read_regular(self.tree / layout["files"]["producer_supervision"]))
        plan_hash = v.canonical_sha256(self.plan)
        report = audit.audit_saved_chunk(result, marker, supervision, self.root / "producer", "b" * 40,
            Path(context["plan_path"]), plan_hash, context["chunk_index"], context["attempt"])
        report_path = self.tree / layout["files"]["audit_report"]
        self.write(report_path, report)
        raw = report_path.read_bytes()
        monitor = {"status": "complete", "exit_code": 0, "worker_exit_confirmed": True, "stop_reason": None,
            "observation_errors": [], "formal_permission": False, "output": {"bytes": len(raw), "sha256": storage.sha(raw)},
            "stderr": {"bytes": 0, "sha256": storage.sha(b"")}, "elapsed_seconds": 1.0, "peak_worker_private_bytes": 1000,
            "limits": {"wall_seconds": 600, "private_bytes": 1024**3, "output_bytes": 8 * 1024**2},
            "runtime_before": report["consumer_runtime"], "runtime_after": copy.deepcopy(report["consumer_runtime"]),
            "argv": audit.invocation(self.root / "consumer", result, marker, supervision, self.root / "producer",
                "b" * 40, Path(context["plan_path"]), plan_hash, context["chunk_index"], context["attempt"])}
        self.write(self.tree / layout["files"]["audit_supervision"], monitor)

    def run_one(self):
        return self.session.run_next(self.observed, produce=self.produce, inspect_audit=self.inspect_audit)

    def test_two_chunks_run_in_order_keep_receipts_and_do_not_repeat_verified_prefix(self):
        with patch.object(self.session, "_verify", wraps=self.session._verify) as verify:
            first = self.run_one()
            before = {p: p.read_bytes() for p in (self.tree / "chunks/000").rglob("*") if p.is_file()}
            second = self.run_one()
        self.assertEqual(verify.call_count, 2)
        self.assertEqual([r["status"] for r in self.session.records],
            ["running", "saved_pending_verification", "verified_complete"] * 2)
        self.assertEqual(second["receipt"]["journal"]["expected_record_count"], 6)
        self.assertEqual(set(second["descriptor_pins"]), {"3", "6"})
        self.assertEqual(before, {p: p.read_bytes() for p in (self.tree / "chunks/000").rglob("*") if p.is_file()})
        self.assertFalse(first["execution_authorized"])
        self.assertEqual(second["campaign_evaluations_credited"], 0)

    def test_restart_requires_external_descriptor_pins_and_revalidates_once(self):
        result = self.run_one()
        with self.assertRaisesRegex(ValueError, "descriptor pins"):
            self.open(result["receipt"])
        restored = self.open(result["receipt"], result["descriptor_pins"])
        with patch.object(restored, "_verify", wraps=restored._verify) as verify:
            restored.start(self.observed)
        self.assertEqual(verify.call_count, 1)
        self.assertEqual(restored.records[-1]["chunk_index"], 1)

    def test_failure_after_publication_is_retained_and_retries_new_attempt(self):
        def fail(context):
            self.produce(context)
            raise RuntimeError("producer failed after save")
        with self.assertRaisesRegex(RuntimeError, "producer failed"):
            self.session.run_next(self.observed, produce=fail, inspect_audit=self.inspect_audit)
        self.assertEqual(self.session.records[-1]["status"], "failed")
        first = self.tree / "chunks/000/attempt-0001"
        before = {p: p.read_bytes() for p in first.rglob("*") if p.is_file()}
        self.run_one()
        self.assertEqual(self.session.records[-1]["attempt"], 2)
        self.assertEqual(before, {p: p.read_bytes() for p in first.rglob("*") if p.is_file()})

    def test_worker_resource_failure_preserves_empty_failure_record(self):
        def stop(context):
            raise resources.ResourceStop("memory_limit")
        with self.assertRaises(resources.ResourceStop):
            self.session.run_next(self.observed, produce=stop, inspect_audit=self.inspect_audit)
        self.assertEqual(self.session.records[-1]["reason"], "resource_limit")
        self.assertEqual(self.session.state["failed_attempt_count"], 1)

    def test_runtime_change_blocks_further_start(self):
        context = self.session.start(self.observed)
        self.produce(context)
        path = self.tree / context["layout"]["files"]["producer_supervision"]
        value = v.strict_json(path.read_bytes())
        value["runtime_after"]["os_ubr"] += 1
        path.write_bytes(storage.json_bytes(value))
        self.session.fail()
        self.assertEqual((self.session.records[-1]["status"], self.session.records[-1]["reason"]),
                         ("blocked_integrity", "runtime_changed"))
        with self.assertRaisesRegex(ValueError, "integrity-blocked"):
            self.session.start(self.observed)

    def test_audit_exception_retains_saved_pending_and_partial_audit_evidence(self):
        def fail(context):
            self.write(self.tree / context["layout"]["files"]["audit_supervision"], {"status": "failed"})
            raise RuntimeError("audit exit")
        with self.assertRaisesRegex(RuntimeError, "audit exit"):
            self.session.run_next(self.observed, produce=self.produce, inspect_audit=fail)
        self.assertEqual([r["status"] for r in self.session.records], ["running", "saved_pending_verification", "failed"])
        self.assertIsNotNone(self.session.records[-1]["evidence"]["marker_sha256"])

    def test_rejected_final_verification_keeps_intent_and_never_commits_completion(self):
        with patch.object(self.session, "_verify", side_effect=ValueError("mismatch")), self.assertRaises(controller.TransitionIncomplete):
            self.run_one()
        self.assertEqual(self.session.records[-1]["status"], "saved_pending_verification")
        self.assertTrue((self.tree / "controller/000003/intent.json").is_file())
        self.assertFalse((self.metadata / "journal/000003.json").exists())
        with self.assertRaisesRegex(ValueError, "reconciliation"):
            self.session.start(self.observed)
        path = self.tree / "controller/000003/intent.json"
        with self.assertRaises(ValueError):
            controller.recover_committed_transition(self.metadata, self.tree, path, storage.sha(path.read_bytes()))

    def test_lost_receipt_recovery_is_read_only_and_does_not_repeat_append(self):
        append = journal.append_record
        def lost(*args):
            append(*args)
            raise OSError("lost receipt")
        with patch.object(journal, "append_record", side_effect=lost), self.assertRaises(controller.TransitionIncomplete):
            self.session.start(self.observed)
        path = self.tree / "controller/000001/intent.json"
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        recovered = controller.recover_committed_transition(self.metadata, self.tree, path, storage.sha(path.read_bytes()))
        self.assertEqual(recovered["receipt"]["journal"]["expected_record_count"], 1)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})
        restored = self.open(recovered["receipt"], recovered["descriptor_pins"])
        restored.fail("interrupted")
        restored.start(self.observed)
        self.assertEqual(restored.records[-1]["attempt"], 2)

    def test_bad_external_pins_and_overlapping_roots_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "separate"):
            controller.Controller(self.metadata, self.receipt, self.metadata, self.root, self.root, "f" * 40)
        context = self.session.start(self.observed)
        path = Path(context["intent_path"])
        with self.assertRaisesRegex(ValueError, "intent hash"):
            controller.recover_committed_transition(self.metadata, self.tree, path, "0" * 64)

    def test_partial_control_does_not_mask_original_resource_stop(self):
        def stop(context):
            path = self.tree / context["layout"]["files"]["producer_supervision"]
            path.parent.mkdir()
            path.write_bytes(b'{')
            raise resources.ResourceStop("memory_limit")
        with self.assertRaises(resources.ResourceStop) as caught:
            self.session.run_next(self.observed, produce=stop, inspect_audit=self.inspect_audit)
        self.assertEqual(caught.exception.reason, "memory_limit")
        self.assertEqual(self.session.last_stop["reason"], "resource_limit")
        self.assertEqual(self.session.last_stop["failure_recording_error"], "V03ValidationError")
        self.assertTrue((self.tree / "controller/000001/failure-recording.json").is_file())
        with self.assertRaisesRegex(ValueError, "reconciliation"):
            self.session.start(self.observed)

    def test_failure_journal_write_does_not_mask_primary_exception(self):
        append = journal.append_record
        def fail_append(root, receipt, record):
            if record["status"] == "failed":
                raise OSError("injected journal failure")
            return append(root, receipt, record)
        def stop(context):
            raise RuntimeError("original callback failure")
        with patch.object(journal, "append_record", side_effect=fail_append), self.assertRaisesRegex(RuntimeError, "original callback failure"):
            self.session.run_next(self.observed, produce=stop, inspect_audit=self.inspect_audit)
        self.assertTrue(self.session.last_stop["transition_incomplete"])
        self.assertIn("000002", self.session.last_stop["intent_path"])

    def test_diagnostic_allocation_failure_still_preserves_primary_stop(self):
        class Stop(resources.ResourceStop):
            def add_note(self, note):
                raise MemoryError("injected annotation failure")
        def stop(context):
            raise Stop("memory_limit")
        with patch.object(self.session, "fail", side_effect=OSError("secondary write failure")), self.assertRaises(Stop) as caught:
            self.session.run_next(self.observed, produce=stop, inspect_audit=self.inspect_audit)
        self.assertEqual(caught.exception.reason, "memory_limit")


if __name__ == "__main__":
    unittest.main()
