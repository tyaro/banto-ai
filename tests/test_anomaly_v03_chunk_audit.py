"""Actual small files and IO; source/runtime/schema/numerical mocks are explicit."""
import copy
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_chunk_audit as a
from banto_ai import anomaly_v03_chunk_contract as chunk
from banto_ai import anomaly_v03_engineering_contract as policy
from banto_ai import anomaly_v03_saved_audit as saved
from banto_ai import anomaly_v03_attempt_files as attempts
from banto_ai import anomaly_v03_attempt_descriptor as descriptor
from banto_ai import anomaly_v03_materializer as m
from banto_ai import _anomaly_v03_io as storage
from tests.test_anomaly_v03_checkpoints import JournalFixture, load_cli
from tests.test_anomaly_v03_attempt_descriptor import pins
from tests.test_anomaly_v03_engineering import fixture_context
from tests.test_anomaly_v03_chunk_contract import envelope


class ChunkFixture:
    def __init__(self, root, index=1, attempt=1, inconclusive=False):
        self.root, self.index, self.attempt = root, index, attempt
        root.mkdir(parents=True)
        self.f = JournalFixture()
        for prior in range(index):
            self.f.complete(chunk=prior)
        if attempt == 2:
            self.f.add("running", chunk=index)
            self.f.add("failed", chunk=index, reason="worker_exit")
        self.f.complete(chunk=index, attempt=attempt, inconclusive=inconclusive)
        self.layout = descriptor.describe_layout(self.f.plan, self.f.records, **pins(self.f))["layout"]
        self.plan_path = root / "plan.json"
        self.plan_path.write_bytes(m.json_bytes(self.f.plan))
        self.result = root / self.layout["result_root"]
        self.result.parent.mkdir(parents=True)
        files, _ = envelope(self.f.plan, index, attempt)
        manifest = v.strict_json(files["manifest.json"])
        if inconclusive:
            slot = manifest["slots"][1]
            path = slot["evaluation"]["path"]
            evaluation = v.strict_json(files[path])
            evaluation["profiles"][0]["status"] = "inconclusive"
            files[path] = m.json_bytes(evaluation)
            slot.update(status="inconclusive", evaluation=policy.file_record(path, files[path]))
            files["journal/01-done.json"] = m.json_bytes(slot)
            policy.refresh_coverage(manifest)
            manifest["resources"]["payload_bytes"] = sum(len(raw) for name, raw in files.items() if name != "manifest.json")
            files["manifest.json"] = m.json_bytes(manifest)
        storage.publish_local_result(self.result.parent, "result", files, verify_semantics=lambda files: None)
        self.marker_hash = storage.sha(storage.read_regular(self.result / ".complete", links=2))
        self.supervision = {"format": a.SUPERVISION_FORMAT, "policy_id": policy.POLICY_ID, "scope": chunk.SCOPE,
            "attempt_id": "result", "binding": chunk.chunk_plan(self.f.plan, index, attempt)["binding"],
            "status": "complete", "exit_code": 0, "worker_exit_confirmed": True, "stop_reason": None,
            "observation_errors": [], "formal_permission": False, "performance_status": "not_evaluated",
            "resource_measurement_scope": "whole_worker_including_replays_and_exit", "elapsed_seconds": 1.0,
            "peak_worker_private_bytes": 1000, "runtime": manifest["runtime"], "runtime_after": copy.deepcopy(manifest["runtime"])}
        self.write_role("producer_supervision", self.supervision)
        self.stored = self.saved_audit("b" * 40)
        self.write_role("audit_report", self.stored)
        self.monitor = {"status": "complete", "exit_code": 0, "worker_exit_confirmed": True, "stop_reason": None,
            "observation_errors": [], "formal_permission": False,
            "output": policy.file_record("unused", self.role_path("audit_report").read_bytes()),
            "stderr": {"bytes": 0, "sha256": storage.sha(b"")}, "elapsed_seconds": 1.0, "peak_worker_private_bytes": 1000,
            "limits": {"wall_seconds": 600, "private_bytes": 1024**3, "output_bytes": 8 * 1024**2},
            "runtime_before": self.stored["consumer_runtime"], "runtime_after": copy.deepcopy(self.stored["consumer_runtime"]),
            "argv": a.invocation(root / "consumer", self.result, self.marker_hash, self.supervision_hash,
                root / "producer", "b" * 40, self.plan_path, self.f.plan_hash, index, attempt)}
        del self.monitor["output"]["path"]
        self.write_role("audit_supervision", self.monitor)
        self.save_descriptor()

    def role_path(self, role):
        return self.root / self.layout["files"][role]

    def write_role(self, role, value):
        path = self.role_path(role)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(m.json_bytes(value))

    @property
    def supervision_hash(self):
        return storage.sha(self.role_path("producer_supervision").read_bytes())

    def saved_audit(self, revision="f" * 40):
        return a.audit_saved_chunk(self.result, self.marker_hash, self.supervision_hash, self.root / "producer",
            revision, self.plan_path, self.f.plan_hash, self.index, self.attempt)

    def save_descriptor(self):
        entries = {}
        for role in descriptor.ROLES:
            raw = self.role_path(role).read_bytes()
            entries[role] = policy.file_record(self.layout["files"][role], raw)
            if role in descriptor.JOURNAL_EVIDENCE:
                self.f.records[-1]["evidence"][descriptor.JOURNAL_EVIDENCE[role]] = storage.sha(raw)
        self.f.records[-2]["evidence"]["marker_sha256"] = self.marker_hash
        self.f.rechain()
        self.value = descriptor.new_descriptor(self.f.plan, self.f.records, entries,
            audit_runtime={"before": self.stored["consumer_runtime"], "after": copy.deepcopy(self.stored["consumer_runtime"])}, **pins(self.f))
        path = self.root / self.value["layout"]["descriptor_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(m.json_bytes(self.value))
        self.digest = storage.sha(path.read_bytes())

    def audit(self):
        return a.audit_chunk_attempt(self.root, self.f.plan, self.f.records, self.digest, self.root / "producer",
            self.root / "consumer", "f" * 40, self.plan_path, **pins(self.f))

    def cli_args(self):
        journal = self.root / "journal"
        journal.mkdir()
        for i, record in enumerate(self.f.records, 1):
            (journal / f"{i:06d}.json").write_bytes(a.checkpoints.encode_record(record))
        return ["attempt-chunk-audit", "--root", str(self.root), "--descriptor-sha256", self.digest,
            "--producer-root", str(self.root / "producer"), "--consumer-root", str(self.root / "consumer"),
            "--verifier-revision", "f" * 40, "--plan", str(self.plan_path), "--plan-sha256", self.f.plan_hash,
            "--journal-dir", str(journal), "--record-count", str(len(self.f.records)), "--head-sha256", self.f.head]


class ChunkAuditTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="banto-chunk-audit-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        producer, runtime = fixture_context()
        self.checkouts = []
        def capture(path, revision):
            checkout = Mock()
            checkout.source_descriptor.return_value = producer.source_descriptor() | {"revision": revision}
            checkout.snapshots.return_value = producer.snapshots()
            self.checkouts.append(checkout)
            return checkout
        self.capture = self.enterContext(patch.object(a.rt, "capture_checkout", side_effect=capture))
        self.runtime = self.enterContext(patch.object(saved.resources, "probe_runtime", return_value=runtime | {"os_ubr": 9457}))
        for name in ("require_start_resources", "free_resources"):
            self.enterContext(patch.object(saved.resources, name, return_value={"fixture": True}))
        self.enterContext(patch.object(saved.resources, "memory_bytes", return_value={"peak_private_bytes": 1000}))
        self.enterContext(patch.object(v, "validate_result_contract", return_value={"fixture": True}))
        self.numeric = self.enterContext(patch.object(saved.audit, "audit_evaluation", return_value={
            "status": "ledger_checks_passed", "score_derivation_verified": False, "independent_s6_complete": False,
            "performance_status": "not_evaluated", "metrics": {"fixture": 0}}))
        self.enterContext(patch.object(m, "materialize_pair", side_effect=AssertionError("generation forbidden")))

    def test_dev_smoke_boundaries_and_retry_bind_real_files_without_generation(self):
        for index in (0, 95, 96, 119):
            f = ChunkFixture(self.root / str(index), index, attempt=2 if index == 96 else 1)
            before = {p: p.read_bytes() for p in f.root.rglob("*") if p.is_file()}
            result = f.audit()
            self.assertEqual(result["status"], "attempt_chunk_ledgers_verified")
            self.assertEqual(result["binding"]["chunk_index"], index)
            self.assertEqual(result["evaluations_checked"], 6)
            self.assertEqual(result["historical_consumer_revision"], "b" * 40)
            self.assertEqual(result["verifier_revision"], "f" * 40)
            self.assertNotEqual(result["historical_producer_runtime"], result["verifier_runtime"])
            self.assertFalse(result["execution_authorized"] or result["budgets_frozen"] or result["independent_s6_complete"])
            self.assertEqual(result["campaign_evaluations_credited"], 0)
            self.assertEqual(before, {p: p.read_bytes() for p in f.root.rglob("*") if p.is_file()})
        self.assertEqual(self.numeric.call_count, 48)
        self.assertTrue(all(c.recheck.call_count == 1 for c in self.checkouts))

    def test_inconclusive_outcome_is_preserved(self):
        f = ChunkFixture(self.root / "case", inconclusive=True)
        self.assertEqual(f.audit()["state"], "verified_inconclusive")
        self.assertEqual(f.stored["evaluations"][1]["status"], "ledger_checks_passed")

    def test_old_api_still_rejects_new_format_and_old_nonfirst_chunks(self):
        f = ChunkFixture(self.root / "case", 0)
        with self.assertRaises(ValueError):
            attempts.audit_attempt(f.root, f.f.plan, f.f.records, f.digest, f.root / "producer", f.root / "consumer", "f" * 40, **pins(f.f))
        with self.assertRaises(ValueError):
            saved.audit_saved(f.result, f.marker_hash, f.supervision_hash, f.root / "producer", "a" * 40,
                "f" * 40, supervision_path=f.role_path("producer_supervision"))

    def test_unverified_declaration_never_enters_payload_audit(self):
        f = ChunkFixture(self.root / "case", 0)
        f.f.records.pop()
        with patch.object(a, "audit_saved_chunk") as run, self.assertRaisesRegex(ValueError, "verified declaration"):
            f.audit()
        run.assert_not_called()

    def test_external_plan_pin_and_selection_rejected_before_numerical_work(self):
        f = ChunkFixture(self.root / "case", 1)
        self.numeric.reset_mock()
        for index, attempt, digest in ((0, 1, f.f.plan_hash), (1, 2, f.f.plan_hash), (1, 1, "0" * 64)):
            with self.assertRaises(ValueError):
                a.audit_saved_chunk(f.result, f.marker_hash, f.supervision_hash, f.root / "producer", "f" * 40,
                    f.plan_path, digest, index, attempt)
        self.numeric.assert_not_called()

    def test_standalone_payload_file_limit_rejected_before_source_capture(self):
        f = ChunkFixture(self.root / "case")
        self.capture.reset_mock()
        self.numeric.reset_mock()
        with patch.object(attempts, "MAX_PAYLOAD_FILES", 1), self.assertRaisesRegex(ValueError, "file count limit"):
            f.saved_audit()
        self.capture.assert_not_called()
        self.numeric.assert_not_called()

    def test_rehashed_monitor_selection_failures_runtime_and_limits_rejected(self):
        f = ChunkFixture(self.root / "case")
        original = copy.deepcopy(f.monitor)
        mutations = [lambda x: x.update(exit_code=True), lambda x: x.update(worker_exit_confirmed=False),
            lambda x: x.update(elapsed_seconds=601), lambda x: x["output"].update(bytes=0),
            lambda x: x["argv"].__setitem__(-1, "2"), lambda x: x["argv"].__setitem__(-3, "0"),
            lambda x: x["runtime_after"].update(os_ubr=9999)]
        for mutate in mutations:
            f.monitor = copy.deepcopy(original)
            mutate(f.monitor)
            f.write_role("audit_supervision", f.monitor)
            f.save_descriptor()
            with self.assertRaises(ValueError):
                f.audit()

    def test_rehashed_producer_scope_selection_and_runtime_failures_rejected(self):
        f = ChunkFixture(self.root / "case")
        original = copy.deepcopy(f.supervision)
        self.numeric.reset_mock()
        for mutate in (lambda x: x["binding"].update(attempt=2), lambda x: x.update(scope=policy.SCOPE),
                       lambda x: x["runtime_after"].update(os_ubr=9999), lambda x: x.update(exit_code=False),
                       lambda x: x.update(resource_measurement_scope="before_publication")):
            f.supervision = copy.deepcopy(original)
            mutate(f.supervision)
            f.write_role("producer_supervision", f.supervision)
            f.save_descriptor()
            with self.assertRaises(ValueError):
                f.audit()
        self.numeric.assert_not_called()

    def test_stored_results_and_input_binding_disagree_despite_updated_file_hash(self):
        f = ChunkFixture(self.root / "case")
        original, monitor = copy.deepcopy(f.stored), copy.deepcopy(f.monitor)
        for mutate in (lambda x: x["evaluations"][0]["metrics"].update(fixture=999),
                       lambda x: x["input"]["binding"].update(chunk_index=0),
                       lambda x: x["consumer_source"].update(revision="f" * 40),
                       lambda x: x.update(execution_authorized=True)):
            f.stored, f.monitor = copy.deepcopy(original), copy.deepcopy(monitor)
            mutate(f.stored)
            f.write_role("audit_report", f.stored)
            raw = f.role_path("audit_report").read_bytes()
            f.monitor["output"] = {"bytes": len(raw), "sha256": storage.sha(raw)}
            f.write_role("audit_supervision", f.monitor)
            f.save_descriptor()
            with self.assertRaises(ValueError):
                f.audit()

    def test_numeric_and_clean_source_failures_propagate(self):
        f = ChunkFixture(self.root / "case")
        self.numeric.side_effect = ValueError("numeric disagreement")
        with self.assertRaisesRegex(ValueError, "numeric disagreement"):
            f.audit()
        self.numeric.side_effect = None
        self.capture.side_effect = ValueError("unclean source")
        with self.assertRaisesRegex(ValueError, "unclean source"):
            f.audit()

    def test_plan_runtime_and_control_changes_during_saved_read_are_rejected(self):
        f = ChunkFixture(self.root / "case")
        original = f.plan_path.read_bytes()
        def change(value):
            f.plan_path.write_bytes(original + b" ")
            return {"status": "ledger_checks_passed"}
        self.numeric.side_effect = change
        with self.assertRaisesRegex(ValueError, "plan changed"):
            f.saved_audit()
        f.plan_path.write_bytes(original)
        self.numeric.side_effect = None
        observed = self.runtime.return_value
        self.runtime.side_effect = [observed, observed | {"os_ubr": 9458}]
        with self.assertRaisesRegex(ValueError, "audit runtime changed"):
            f.saved_audit()
        self.runtime.side_effect = None
        def change_control(value):
            f.role_path("producer_supervision").write_bytes(b"{}\n")
            return {"status": "ledger_checks_passed"}
        self.numeric.side_effect = change_control
        with self.assertRaisesRegex(ValueError, "supervision changed"):
            f.saved_audit()

    def test_payload_and_descriptor_rechecked_after_body_binding(self):
        f = ChunkFixture(self.root / "case")
        original = a.evidence._bind_checked_trial
        def change(*args, **kwargs):
            report = original(*args, **kwargs)
            path = f.result / "payload/planned.json"
            path.write_bytes(path.read_bytes().replace(b'"result"', b'"resulx"'))
            return report
        with patch.object(a.evidence, "_bind_checked_trial", side_effect=change), self.assertRaisesRegex(ValueError, "inventory/hash"):
            f.audit()

    def test_both_clis_route_real_small_files_and_recheck_journal(self):
        f = ChunkFixture(self.root / "case")
        saved_args = f.monitor["argv"][3:]
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(a.main(saved_args), 0)
        self.assertEqual(v.strict_json(out.getvalue())["input"]["binding"]["chunk_index"], 1)
        cli = load_cli()
        args = f.cli_args()
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli.main(args), 0)
        self.assertEqual(v.strict_json(out.getvalue())["status"], "attempt_chunk_ledgers_verified")
        original = a.audit_chunk_attempt
        def change(*args, **kwargs):
            report = original(*args, **kwargs)
            (f.root / "journal/000006.json").write_bytes(b"{}\n")
            return report
        with patch.object(a, "audit_chunk_attempt", side_effect=change), redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(args), 2)


if __name__ == "__main__":
    unittest.main()
