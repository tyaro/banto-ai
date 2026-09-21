"""Small actual files; numerical and source capture fixtures are explicit mocks."""
import copy
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_attempt_descriptor as d
from banto_ai import anomaly_v03_attempt_files as a
from banto_ai import anomaly_v03_checkpoints as p
from banto_ai import _anomaly_v03_io as storage
from banto_ai import anomaly_v03_materializer as materializer
from tests.test_anomaly_v03_checkpoints import JournalFixture, load_cli
from tests.test_anomaly_v03_attempt_descriptor import pins
from tests.test_anomaly_v03_checkpoint_evidence import fixture


class AttemptFixture:
    def __init__(self, root, state="verified_complete"):
        self.root = root
        self.f = JournalFixture()
        self.data = fixture(root)
        self.f.records = self.data["records"]
        self.layout = d.describe_layout(self.f.plan, self.f.records, **pins(self.f))["layout"]
        self.result = root / self.layout["result_root"]
        self.result.parent.mkdir(parents=True)
        self.data["manifest"]["attempt_id"] = "result"
        self.data["supervision"]["attempt_id"] = "result"
        if state in ("saved_pending_verification", "verified_complete"):
            # This small manifest publication verifies storage. Numerical results
            # are mocked only in audit binding tests, never called real evaluations.
            storage.publish_local_result(self.result.parent, "result",
                {"manifest.json": storage.json_bytes(self.data["manifest"])}, verify_semantics=lambda files: None)
            marker_raw = storage.read_regular(self.result / ".complete", links=2)
            self.f.records[1]["evidence"]["marker_sha256"] = storage.sha(marker_raw)
            self.f.records[2]["evidence"]["marker_sha256"] = storage.sha(marker_raw)
        if state == "running":
            self.f.records = self.f.records[:1]
        elif state == "saved_pending_verification":
            self.f.records = self.f.records[:2]
        elif state == "failed":
            self.f.records = self.f.records[:1]
            self.f.add("failed", reason="worker_exit", evidence={"marker_sha256": None,
                "supervision_sha256": storage.sha(storage.json_bytes({"status": "failed"})), "audit_sha256": None})
            self.write_role("producer_supervision", {"status": "failed"})
        else:
            self.write_role("producer_supervision", self.data["supervision"])
            stored = self.data["stored_audit"]
            stored["input"] = {"root": str(self.result),
                "marker_sha256": self.f.records[-1]["evidence"]["marker_sha256"],
                "supervision_sha256": storage.sha(self.role_path("producer_supervision").read_bytes())}
            stored["storage_verification"] = {"payloads": 1, "local_verified": True, "native_acceptance": "not_completed"}
            stored["resources"]["input_payload_bytes"] = (self.result / "payload/manifest.json").stat().st_size
            self.write_role("audit_report", stored)
            monitor = self.data["monitor"]
            monitor["output"] = {"bytes": self.role_path("audit_report").stat().st_size,
                                  "sha256": storage.sha(self.role_path("audit_report").read_bytes())}
            args = monitor["argv"]
            args[args.index("--input-root") + 1] = str(self.result)
            args[args.index("--marker-sha256") + 1] = stored["input"]["marker_sha256"]
            args[args.index("--supervision-sha256") + 1] = stored["input"]["supervision_sha256"]
            args.extend(("--supervision-path", str(self.role_path("producer_supervision"))))
            self.write_role("audit_supervision", monitor)
            self.data["fresh_audit"] = copy.deepcopy(stored)
            self.data["fresh_audit"]["consumer_source"]["revision"] = "f" * 40
        self.save_descriptor()

    def role_path(self, role):
        return self.root / self.layout["files"][role]

    def write_role(self, role, value):
        path = self.role_path(role)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(storage.json_bytes(value))

    def save_descriptor(self):
        record = self.f.records[-1]
        entries = {}
        for role in d.ROLES:
            path = self.role_path(role)
            raw = path.read_bytes() if path.exists() else None
            entries[role] = None if raw is None else {"path": self.layout["files"][role], "bytes": len(raw), "sha256": storage.sha(raw)}
            if role in d.JOURNAL_EVIDENCE:
                record["evidence"][d.JOURNAL_EVIDENCE[role]] = entries[role]["sha256"] if raw is not None else None
        self.f.rechain()
        observed = self.data["stored_audit"]["consumer_runtime"]
        self.value = d.new_descriptor(self.f.plan, self.f.records, entries,
            audit_runtime={"before": observed, "after": copy.deepcopy(observed)} if record["status"] in p.VERIFIED else None,
            **pins(self.f))
        self.path = self.root / self.value["layout"]["descriptor_path"]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(storage.json_bytes(self.value))
        self.digest = storage.sha(self.path.read_bytes())

    def inspect(self):
        return a.inspect_attempt(self.root, self.f.plan, self.f.records, self.digest, **pins(self.f))

    def audit(self):
        return a.audit_attempt(self.root, self.f.plan, self.f.records, self.digest,
            self.root / "producer", self.root / "consumer", "f" * 40, **pins(self.f))


class AttemptFilesTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="banto-attempt-files-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.enterContext(patch.object(materializer, "materialize_pair", side_effect=AssertionError("generation forbidden")))

    def test_running_pending_failed_and_complete_storage_keep_scope_explicit(self):
        for state in ("running", "saved_pending_verification", "failed", "verified_complete"):
            f = AttemptFixture(self.root / state, state)
            before = {x: x.read_bytes() for x in f.root.rglob("*") if x.is_file()}
            with patch.object(a.audit, "audit_saved", side_effect=AssertionError("no numerical work")):
                result = f.inspect()
            self.assertEqual(result["state"], state)
            self.assertIs(result["artifact_bytes_verified"], True)
            self.assertEqual(result["payload_inventory_verified"], state in ("saved_pending_verification", "verified_complete"))
            for flag in ("evidence_body_bindings_verified", "saved_ledgers_revalidated", "source_checkouts_verified",
                         "resume_authorized", "campaign_completed", "independent_s6_complete", "formal_permission"):
                self.assertIs(result[flag], False)
            self.assertEqual(result["campaign_evaluations_credited"], 0)
            self.assertEqual(before, {x: x.read_bytes() for x in f.root.rglob("*") if x.is_file()})

    def test_missing_wrong_location_or_wrong_external_descriptor_pin_rejected(self):
        f = AttemptFixture(self.root)
        with self.assertRaisesRegex(ValueError, "descriptor hash mismatch"):
            a.inspect_attempt(f.root, f.f.plan, f.f.records, "0" * 64, **pins(f.f))
        f.path.rename(f.path.parent / "different.json")
        with self.assertRaises(ValueError):
            f.inspect()

    def test_changed_control_hash_and_declared_size_rejected(self):
        f = AttemptFixture(self.root)
        path = f.role_path("audit_report")
        original = path.read_bytes()
        path.write_bytes(original + b" ")
        with self.assertRaisesRegex(ValueError, "bytes/hash"):
            f.inspect()
        path.write_bytes(original)
        f.value["artifacts"]["audit_report"]["bytes"] += 1
        f.path.write_bytes(storage.json_bytes(f.value))
        f.digest = storage.sha(f.path.read_bytes())
        with self.assertRaisesRegex(ValueError, "bytes/hash"):
            f.inspect()

    def test_undeclared_missing_or_multiply_linked_controls_rejected(self):
        f = AttemptFixture(self.root, "running")
        f.write_role("audit_supervision", {})
        with self.assertRaisesRegex(ValueError, "undeclared"):
            f.inspect()
        f.role_path("audit_supervision").unlink()
        os.link(f.path, self.root / "descriptor-alias.json")
        with self.assertRaisesRegex(ValueError, "multiply-linked"):
            f.inspect()

    def test_reparse_ancestor_is_rejected_before_read(self):
        f = AttemptFixture(self.root)
        original = Path.lstat
        target = f.root / "chunks"
        def reparse(path, *args, **kwargs):
            meta = original(path, *args, **kwargs)
            if path == target:
                return type("Metadata", (), {"st_mode": meta.st_mode, "st_file_attributes": 0x400})()
            return meta
        with patch.object(Path, "lstat", reparse), self.assertRaisesRegex(ValueError, "reparse"):
            f.inspect()

    def test_byte_file_and_payload_count_limits(self):
        f = AttemptFixture(self.root)
        with patch.object(a, "MAX_DESCRIPTOR_BYTES", 1), self.assertRaisesRegex(ValueError, "byte limit"):
            f.inspect()
        with patch.dict(a.CONTROL_LIMITS, audit_report=1), self.assertRaisesRegex(ValueError, "byte limit"):
            f.inspect()
        with patch.object(a.audit, "MAX_FILE_BYTES", 1), self.assertRaisesRegex(ValueError, "payload byte limit"):
            f.inspect()
        with patch.object(a, "MAX_PAYLOAD_FILES", 0), self.assertRaisesRegex(ValueError, "file count"):
            f.inspect()

    def test_forged_payload_extra_file_or_wrong_marker_object_rejected(self):
        for mutation in ("payload", "extra", "marker"):
            f = AttemptFixture(self.root / mutation)
            if mutation == "payload":
                (f.result / "payload/manifest.json").write_bytes(b"{}\n")
            elif mutation == "extra":
                (f.result / "payload/extra.json").write_bytes(b"{}\n")
            else:
                (f.result / "marker-pending.json").unlink()
            with self.assertRaises(ValueError):
                f.inspect()

    def test_control_change_or_new_unrecorded_control_during_read_is_rejected(self):
        f = AttemptFixture(self.root, "saved_pending_verification")
        original = storage.verify_local_publication
        def mutate(*args, **kwargs):
            value = original(*args, **kwargs)
            f.write_role("audit_supervision", {})
            return value
        with patch.object(storage, "verify_local_publication", side_effect=mutate), self.assertRaisesRegex(ValueError, "undeclared"):
            f.inspect()

    def install_audit_mocks(self, f):
        historical = Mock()
        historical.source_descriptor.return_value = f.data["historical_consumer_source"]
        self.enterContext(patch.object(a.rt, "capture_checkout", return_value=historical))
        fresh = self.enterContext(patch.object(a.audit, "audit_saved", return_value=f.data["fresh_audit"]))
        return historical, fresh

    def test_completed_body_binding_calls_existing_reader_and_keeps_no_campaign_credit(self):
        f = AttemptFixture(self.root)
        historical, fresh = self.install_audit_mocks(f)
        result = f.audit()
        self.assertTrue(result["evidence_body_bindings_verified"])
        self.assertTrue(result["saved_ledgers_revalidated"])
        self.assertEqual(result["evaluations_checked"], 6)
        self.assertEqual(result["campaign_evaluations_credited"], 0)
        self.assertFalse(result["resume_authorized"])
        fresh.assert_called_once()
        self.assertEqual(fresh.call_args.kwargs["supervision_path"], f.role_path("producer_supervision"))
        historical.recheck.assert_called_once()

    def test_rehashed_wrong_monitor_invocation_failure_or_wrong_body_is_rejected(self):
        mutations = [lambda f: f.data["monitor"].update(exit_code=True),
            lambda f: f.data["monitor"]["argv"].__setitem__(-1, str(self.root / "wrong.json")),
            lambda f: f.data["monitor"]["output"].update(bytes=0),
            lambda f: f.data["supervision"].update(attempt_id="other")]
        for i, change in enumerate(mutations):
            f = AttemptFixture(self.root / str(i))
            self.install_audit_mocks(f)
            change(f)
            f.write_role("audit_supervision", f.data["monitor"])
            f.write_role("producer_supervision", f.data["supervision"])
            f.save_descriptor()
            with self.assertRaises(ValueError):
                f.audit()

    def test_fresh_numeric_disagreement_and_audit_runtime_mismatch_rejected(self):
        f = AttemptFixture(self.root)
        _, fresh = self.install_audit_mocks(f)
        fresh.return_value = copy.deepcopy(f.data["fresh_audit"])
        fresh.return_value["evaluations"][0]["metrics"]["fixture"] = -1
        with self.assertRaisesRegex(ValueError, "stored/fresh"):
            f.audit()
        fresh.return_value = f.data["fresh_audit"]
        f.value["audit_runtime"]["before"]["os_ubr"] += 1
        f.value["audit_runtime"]["after"]["os_ubr"] += 1
        f.path.write_bytes(storage.json_bytes(f.value))
        f.digest = storage.sha(f.path.read_bytes())
        with self.assertRaisesRegex(ValueError, "runtime differs"):
            f.audit()

    def test_reader_failure_or_payload_change_during_audit_rejected(self):
        f = AttemptFixture(self.root)
        _, fresh = self.install_audit_mocks(f)
        fresh.side_effect = ValueError("source or numeric failure")
        with self.assertRaisesRegex(ValueError, "source or numeric"):
            f.audit()
        def mutate(*args, **kwargs):
            f.role_path("audit_report").write_bytes(b"{}\n")
            return f.data["fresh_audit"]
        fresh.side_effect = mutate
        with self.assertRaises(ValueError):
            f.audit()

    def test_nonfirst_chunk_or_unverified_declaration_never_launches_audit(self):
        f = AttemptFixture(self.root, "running")
        with patch.object(a.audit, "audit_saved") as fresh:
            with self.assertRaisesRegex(ValueError, "verified first"):
                f.audit()
            f.f = JournalFixture()
            f.f.complete()
            f.f.complete(chunk=1)
            with self.assertRaisesRegex(ValueError, "verified first"):
                f.audit()
            fresh.assert_not_called()

    def test_payload_change_after_audit_body_binding_is_rejected(self):
        f = AttemptFixture(self.root)
        historical, _ = self.install_audit_mocks(f)
        path = f.result / "payload/manifest.json"
        original = path.read_bytes()
        # Same byte count defeats a size-only final check.
        historical.recheck.side_effect = lambda: path.write_bytes(original.replace(b'"result"', b'"resulx"'))
        with self.assertRaisesRegex(ValueError, "inventory/hash"):
            f.audit()

    def test_saved_audit_explicit_fixed_control_and_legacy_default_both_work(self):
        f = AttemptFixture(self.root)
        legacy = f.result.parent / "result-control/supervision.json"
        legacy.parent.mkdir()
        legacy.write_bytes(f.role_path("producer_supervision").read_bytes())
        producer, consumer = Mock(), Mock()
        producer.source_descriptor.return_value = f.data["manifest"]["source"]
        consumer.source_descriptor.return_value = f.data["fresh_audit"]["consumer_source"]
        with patch.object(a.audit.rt, "capture_checkout", side_effect=[producer, consumer, producer, consumer]), \
                patch.object(a.audit.resources, "require_start_resources", return_value={}), \
                patch.object(a.audit.resources, "probe_runtime", return_value=f.data["manifest"]["runtime"]), \
                patch.object(a.audit.resources, "free_resources", return_value={}), \
                patch.object(a.audit.resources, "memory_bytes", return_value={"peak_private_bytes": 1000}), \
                patch.object(a.audit, "audit_payloads", return_value=(f.data["manifest"], f.data["stored_audit"]["evaluations"])):
            for path in (None, f.role_path("producer_supervision")):
                report = a.audit.audit_saved(f.result, f.value["artifacts"]["marker"]["sha256"],
                    f.value["artifacts"]["producer_supervision"]["sha256"], self.root / "producer", "a" * 40,
                    "f" * 40, supervision_path=path)
                self.assertEqual(report["status"], "ledger_checks_passed")
                self.assertEqual(report["input"]["root"], str(f.result))
        with patch.object(a.audit.rt, "capture_checkout") as capture, self.assertRaisesRegex(ValueError, "path differs"):
            a.audit.audit_saved(f.result, "c" * 64, "d" * 64, self.root, "a" * 40, "f" * 40,
                                supervision_path=self.root / "other.json")
        capture.assert_not_called()

    def test_cli_external_journal_pins_and_postread_journal_check(self):
        f = AttemptFixture(self.root)
        journal = self.root / "journal"
        journal.mkdir()
        (self.root / "plan.json").write_bytes(storage.json_bytes(f.f.plan))
        for i, row in enumerate(f.f.records, 1):
            (journal / f"{i:06d}.json").write_bytes(p.encode_record(row))
        cli = load_cli()
        args = ["attempt-files", "--root", str(f.root), "--descriptor-sha256", f.digest,
            "--plan", str(self.root / "plan.json"), "--journal-dir", str(journal),
            "--plan-sha256", f.f.plan_hash, "--head-sha256", f.f.head, "--record-count", "3"]
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli.main(args), 0)
        self.assertTrue(v.strict_json(out.getvalue())["payload_inventory_verified"])
        original = a.inspect_attempt
        def mutate(*args, **kwargs):
            report = original(*args, **kwargs)
            (journal / "000003.json").write_bytes(b"{}\n")
            return report
        with patch.object(a, "inspect_attempt", side_effect=mutate), redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(args), 2)


if __name__ == "__main__":
    unittest.main()
