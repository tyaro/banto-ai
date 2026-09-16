"""Small evidence-binding fixtures; real numerical auditing has separate tests."""
import copy
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_checkpoints as checkpoints
from banto_ai import anomaly_v03_checkpoint_evidence as e
from banto_ai import anomaly_v03_materializer as materializer
from tests.test_anomaly_v03_checkpoints import JournalFixture, load_cli
from tests.test_anomaly_v03_engineering import complete_fixture, fixture_context


def fixture(root):
    journal = JournalFixture()
    journal.complete()
    manifest = complete_fixture()
    producer, runtime = fixture_context()
    consumer = producer.source_descriptor() | {"revision": "b" * 40}
    paths = {"trial_root": str(root / "attempt"), "producer_root": str(root / "producer"),
             "consumer_root": str(root / "consumer"), "audit_path": str(root / "audit.json"),
             "audit_monitor_path": str(root / "monitor.json")}
    stored = {"format": "anomaly-v03-independent-ledger-audit-v1", "scope": "saved-engineering-six-cell-ledgers",
        "status": "ledger_checks_passed", "producer_source": producer.source_descriptor(), "consumer_source": consumer,
        "consumer_runtime": runtime, "storage_verification": {"payloads": 41, "local_verified": True},
        "input": {"root": paths["trial_root"], "marker_sha256": "c" * 64, "supervision_sha256": "d" * 64},
        "evaluations": [{"identity": s["identity"], "status": "ledger_checks_passed", "score_derivation_verified": False,
            "independent_s6_complete": False, "performance_status": "not_evaluated", "metrics": {"fixture": i}}
                        for i, s in enumerate(manifest["slots"])],
        "checked": ["fixture"], "shared_checks": ["fixture"], "not_checked_independently": ["score_derivation"],
        "independent_s6_complete": False, "performance_status": "not_evaluated", "formal_permission": False,
        "resources": {"input_payload_bytes": 1000}}
    supervision = {"status": "complete", "exit_code": 0, "worker_exit_confirmed": True, "stop_reason": None,
        "observation_errors": [], "formal_permission": False, "performance_status": "not_evaluated",
        "attempt_id": "attempt", "policy_id": e.policy.POLICY_ID, "scope": e.policy.SCOPE, "runtime": runtime,
        "resource_measurement_scope": "whole_worker_including_replays_and_exit", "elapsed_seconds": 1.0,
        "peak_worker_private_bytes": 1000}
    supervision_raw = v.canonical_json(supervision)
    stored["input"]["supervision_sha256"] = e.storage.sha(supervision_raw)
    raw = v.canonical_json(stored)
    journal.records[-1]["evidence"].update(audit_sha256=e.storage.sha(raw),
        supervision_sha256=e.storage.sha(supervision_raw))
    monitor = {"status": "complete", "exit_code": 0, "worker_exit_confirmed": True, "stop_reason": None,
        "observation_errors": [], "formal_permission": False, "output": {"bytes": len(raw), "sha256": e.storage.sha(raw)},
        "stderr": {"bytes": 0, "sha256": e.storage.sha(b"")}, "elapsed_seconds": 1.0, "peak_worker_private_bytes": 1000,
        "limits": {"wall_seconds": 600, "private_bytes": 1024**3, "output_bytes": 8 * 1024**2},
        "argv": [sys.executable, "-B", str(root / "consumer/tools/evaluator/audit_anomaly_v03_saved.py"),
            "--input-root", paths["trial_root"], "--marker-sha256", "c" * 64,
            "--supervision-sha256", stored["input"]["supervision_sha256"], "--producer-root", paths["producer_root"],
            "--producer-revision", "a" * 40, "--consumer-revision", "b" * 40]}
    ref = {"format": e.REFERENCE_FORMAT, "purpose": e.PURPOSE, **paths,
        "audit_monitor_sha256": e.storage.sha(v.canonical_json(monitor)),
        "journal": {"expected_plan_sha256": journal.plan_hash, "expected_record_count": 3,
                    "expected_head_sha256": journal.head}}
    fresh = copy.deepcopy(stored)
    fresh["consumer_source"]["revision"] = "f" * 40
    return {"plan": journal.plan, "records": journal.records, "reference": ref, "manifest": manifest,
        "supervision": supervision, "stored_audit": stored, "fresh_audit": fresh, "monitor": monitor,
        "audit_raw": raw, "historical_consumer_source": copy.deepcopy(consumer)}


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.data = fixture(Path.cwd() / "fixture-only")
        self.enterContext(patch.object(materializer, "materialize_pair", side_effect=AssertionError("generation forbidden")))

    def test_success_is_preflight_only_and_keeps_both_consumers_distinct(self):
        before = copy.deepcopy(self.data)
        result = e.bind_evidence(**self.data)
        self.assertEqual(result["status"], "preflight_evidence_verified")
        self.assertEqual(result["evaluations_checked"], 6)
        self.assertEqual(result["historical_consumer_revision"], "b" * 40)
        self.assertEqual(result["verifier_revision"], "f" * 40)
        self.assertEqual(result["campaign_evaluations_credited"], 0)
        for flag in ("campaign_attempt_roots_verified", "resume_authorized", "campaign_completed",
                     "formal_permission", "score_derivation_verified", "independent_s6_complete"):
            self.assertIs(result[flag], False)
        self.assertEqual(self.data, before)

    def test_runtime_update_for_later_verifier_is_recorded_without_rewriting_trial(self):
        self.data["fresh_audit"]["consumer_runtime"]["os_ubr"] += 1
        result = e.bind_evidence(**self.data)
        self.assertNotEqual(result["verifier_runtime"], result["historical_producer_runtime"])
        self.data["records"][-1]["outcome"]["runtime_after"]["os_ubr"] += 1
        with self.assertRaises(ValueError):
            e.bind_evidence(**self.data)

    def test_journal_outcome_source_identity_and_trial_mismatch_stop_binding(self):
        changes = [lambda d: d["reference"].update(purpose="campaign-resume"),
            lambda d: d["reference"].update(trial_root="relative"),
            lambda d: d["reference"]["journal"].update(expected_record_count=True),
            lambda d: d["reference"]["journal"].update(expected_head_sha256="0" * 64),
            lambda d: d["manifest"].update(attempt_id="other"),
            lambda d: d["manifest"]["slots"][0].update(status="inconclusive"),
            lambda d: d["historical_consumer_source"].update(revision="f" * 40),
            lambda d: d["stored_audit"]["producer_source"].update(revision="b" * 40),
            lambda d: d["stored_audit"]["input"].update(root=str(Path.cwd() / "different")),
            lambda d: d["stored_audit"]["input"].update(marker_sha256="0" * 64)]
        for change in changes:
            with self.subTest(change=change):
                data = copy.deepcopy(self.data)
                change(data)
                with self.assertRaises(ValueError):
                    e.bind_evidence(**data)

    def test_failed_or_wrong_monitor_and_exceeded_limits_rejected(self):
        changes = [lambda m: m.update(exit_code=False), lambda m: m.update(worker_exit_confirmed=1),
            lambda m: m.update(status="failed"), lambda m: m.update(stop_reason="resource_limit"),
            lambda m: m.update(observation_errors=["failure"]),
            lambda m: m["output"].update(sha256="0" * 64), lambda m: m["output"].update(bytes=0),
            lambda m: m["argv"].__setitem__(-1, "f" * 40), lambda m: m["limits"].update(wall_seconds=601),
            lambda m: m.update(elapsed_seconds=601), lambda m: m.update(elapsed_seconds=float("nan")),
            lambda m: m.update(peak_worker_private_bytes=True)]
        for change in changes:
            data = copy.deepcopy(self.data)
            change(data["monitor"])
            with self.assertRaises(ValueError):
                e.bind_evidence(**data)

    def test_supervision_failure_wrong_runtime_or_fake_whole_worker_scope_rejected(self):
        changes = [lambda m: m.update(exit_code=True), lambda m: m.update(worker_exit_confirmed=False),
            lambda m: m.update(observation_errors={}), lambda m: m.update(attempt_id="other"),
            lambda m: m.update(resource_measurement_scope="before_publication"),
            lambda m: m["runtime"].update(os_ubr=9999), lambda m: m.update(elapsed_seconds=901)]
        for change in changes:
            data = copy.deepcopy(self.data)
            change(data["supervision"])
            with self.assertRaises(ValueError):
                e.bind_evidence(**data)

    def test_changed_saved_audit_conclusions_and_missing_or_reordered_cells_rejected(self):
        changes = [lambda a: a["evaluations"].pop(), lambda a: a["evaluations"].reverse(),
            lambda a: a["evaluations"][0]["metrics"].update(fixture=99),
            lambda a: a["evaluations"][0].update(score_derivation_verified=True),
            lambda a: a.update(independent_s6_complete=True), lambda a: a.update(formal_permission=True),
            lambda a: a["resources"].update(input_payload_bytes=999),
            lambda a: a["consumer_source"]["sources"][0].update(raw_sha256="f" * 64)]
        for change in changes:
            data = copy.deepcopy(self.data)
            change(data["stored_audit"])
            with self.assertRaises(ValueError):
                e.bind_evidence(**data)


class ReaderTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="banto-preflight-evidence-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.data = fixture(self.root)
        self.reference = self.data["reference"]
        for key in ("trial_root", "producer_root", "consumer_root"):
            Path(self.reference[key]).mkdir()
        (self.root / "attempt/payload").mkdir()
        (self.root / "attempt-control").mkdir()
        self.manifest_path = self.root / "attempt/payload/manifest.json"
        self.manifest_path.write_bytes(v.canonical_json(self.data["manifest"]))
        (self.root / "attempt-control/supervision.json").write_bytes(v.canonical_json(self.data["supervision"]))
        Path(self.reference["audit_path"]).write_bytes(self.data["audit_raw"])
        Path(self.reference["audit_monitor_path"]).write_bytes(v.canonical_json(self.data["monitor"]))
        producer, _ = fixture_context()
        consumer = e.rt.Checkout(Path(self.reference["consumer_root"]), "b" * 40, producer.entries)
        self.capture = self.enterContext(patch.object(e.rt, "capture_checkout", return_value=consumer))
        self.recheck = self.enterContext(patch.object(e.rt.Checkout, "recheck"))
        self.fresh = self.enterContext(patch.object(e.audit, "audit_saved", return_value=self.data["fresh_audit"]))
        self.enterContext(patch.object(materializer, "materialize_pair", side_effect=AssertionError("generation forbidden")))

    def verify(self):
        return e.verify_preflight(self.data["plan"], self.data["records"], self.reference, "f" * 40)

    def test_reader_pins_then_invokes_saved_audit_once_without_changing_inputs(self):
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        result = self.verify()
        self.assertEqual(result["evaluations_checked"], 6)
        self.fresh.assert_called_once()
        self.assertEqual(self.fresh.call_args.args[-1], "f" * 40)
        self.recheck.assert_called_once()
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_wrong_saved_report_or_monitor_pin_stops_before_long_audit(self):
        for key in ("audit_path", "audit_monitor_path"):
            path = Path(self.reference[key])
            raw = path.read_bytes()
            path.write_bytes(raw + b" ")
            with self.assertRaisesRegex(ValueError, "external hash mismatch"):
                self.verify()
            self.fresh.assert_not_called()
            path.write_bytes(raw)

    def test_numerical_audit_failure_does_not_return_success(self):
        self.fresh.side_effect = ValueError("saved score mismatch")
        with self.assertRaisesRegex(ValueError, "saved score mismatch"):
            self.verify()

    def test_evidence_change_during_long_audit_is_rejected(self):
        def change(*args):
            self.manifest_path.write_bytes(self.manifest_path.read_bytes() + b" ")
            return self.data["fresh_audit"]
        self.fresh.side_effect = change
        with self.assertRaisesRegex(ValueError, "evidence changed during verification"):
            self.verify()

    def cli_args(self):
        (self.root / "plan.json").write_bytes(v.canonical_json(self.data["plan"]))
        journal = self.root / "journal"
        journal.mkdir()
        for i, record in enumerate(self.data["records"], 1):
            (journal / f"{i:06d}.json").write_bytes(checkpoints.encode_record(record))
        raw = v.canonical_json(self.reference)
        (self.root / "reference.json").write_bytes(raw)
        return ["preflight-trial", "--plan", str(self.root / "plan.json"), "--journal-dir", str(journal),
            "--reference", str(self.root / "reference.json"), "--reference-sha256", e.storage.sha(raw),
            "--verifier-revision", "f" * 40]

    def test_cli_binds_reference_and_returns_zero_credit(self):
        cli = load_cli()
        args = self.cli_args()
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cli.main(args), 0)
        result = v.strict_json(output.getvalue())
        self.assertTrue(result["preflight_evidence_revalidated"])
        self.assertEqual(result["campaign_evaluations_credited"], 0)

    def test_cli_rechecks_journal_after_long_audit(self):
        cli = load_cli()
        args = self.cli_args()
        def change(*unused):
            (self.root / "journal/000003.json").unlink()
            return self.data["fresh_audit"]
        self.fresh.side_effect = change
        with redirect_stderr(io.StringIO()) as error:
            self.assertEqual(cli.main(args), 2)
        self.assertIn("journal file inventory differs", error.getvalue())


if __name__ == "__main__":
    unittest.main()
