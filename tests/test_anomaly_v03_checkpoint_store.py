"""Small single-writer crash-boundary fixtures; no campaign/data generation."""
import copy
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_checkpoint_store as store
from banto_ai import anomaly_v03_checkpoints as p
from banto_ai import anomaly_v03_materializer as materializer
from tests.test_anomaly_v03_checkpoints import JournalFixture, load_cli


class StoreTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="banto-checkpoint-store-")
        self.addCleanup(temp.cleanup)
        self.parent = Path(temp.name)
        self.f = JournalFixture()
        self.root = self.parent / "metadata"
        self.receipt = store.create_store(self.parent, self.root.name, self.f.plan)
        self.enterContext(patch.object(materializer, "materialize_pair", side_effect=AssertionError("generation forbidden")))

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def append(self, record):
        self.receipt = store.append_record(self.root, self.receipt, record)
        return self.receipt

    def test_initialization_returns_empty_external_pins_and_recovers_lost_receipt(self):
        self.assertEqual(store.recover_initialization(self.root, self.f.plan_hash), self.receipt)
        self.assertEqual(self.snapshot(), {"plan.json": v.canonical_json(self.f.plan) + b"\n"})
        report = store.inspect_store(self.root, self.receipt)
        self.assertEqual(report["coverage"]["not_started"], 120)
        self.assertFalse(report["resume_authorized"])
        self.assertFalse(self.receipt["execution_authorized"])
        self.assertFalse(self.receipt["campaign_completed"])

    def test_existing_root_never_reinitialized_or_overwritten(self):
        before = self.snapshot()
        for plan in (self.f.plan, p.fixed_plan("c" * 40, "d" * 40)):
            with self.assertRaises(FileExistsError):
                store.create_store(self.parent, self.root.name, plan)
        self.assertEqual(before, self.snapshot())

    def test_append_reopens_with_external_receipt_and_preserves_old_bytes(self):
        first = self.f.add("running")
        old_receipt = copy.deepcopy(self.receipt)
        self.append(first)
        prefix = self.snapshot()
        report = store.inspect_store(self.root, copy.deepcopy(self.receipt))
        self.assertEqual(report["next_action"], "reconcile_interrupted_attempt")
        self.append(self.f.add("interrupted", reason="interrupted"))
        self.append(self.f.add("running", attempt=2))
        for name, raw in prefix.items():
            self.assertEqual((self.root / name).read_bytes(), raw)
        self.assertEqual(store.inspect_store(self.root, self.receipt)["attempt_count"], 2)
        with self.assertRaises(ValueError):
            store.append_record(self.root, old_receipt, first)
        with self.assertRaises(ValueError):
            store.recover_initialization(self.root, self.f.plan_hash)

    def test_invalid_next_state_does_not_create_pending_or_journal_bytes(self):
        record = self.f.add("running", chunk=1)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "chunk order"):
            self.append(record)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(list((self.root / "pending").iterdir()), [])

    def test_marker_and_verified_declarations_never_grant_campaign_permission(self):
        self.f.complete(inconclusive=True)
        for record in self.f.records:
            self.append(record)
        report = store.inspect_store(self.root, self.receipt)
        self.assertEqual(report["coverage"]["verified_inconclusive"], 1)
        self.assertEqual(report["next_action"], "revalidate_saved_evidence")
        self.assertFalse(report["evidence_revalidated"])
        self.assertFalse(self.receipt["resume_authorized"])

    def test_failed_write_leaves_partial_pending_and_preserves_committed_prefix(self):
        self.append(self.f.add("running"))
        before = self.snapshot()
        record = self.f.add("interrupted", reason="interrupted")
        def partial(path, raw):
            with path.open("xb") as stream:
                stream.write(raw[:20])
            raise OSError("simulated write interruption")
        with patch.object(store.storage, "_exclusive", side_effect=partial), self.assertRaises(OSError):
            self.append(record)
        self.assertEqual((self.root / "pending/000002.json").read_bytes(), p.encode_record(record)[:20])
        for name, raw in before.items():
            self.assertEqual((self.root / name).read_bytes(), raw)
        for operation in (lambda: store.inspect_store(self.root, self.receipt),
                          lambda: store.append_record(self.root, self.receipt, record),
                          lambda: store.recover_append(self.root, self.receipt, record)):
            with self.assertRaisesRegex(ValueError, "pending metadata"):
                operation()
        self.assertTrue((self.root / "pending/000002.json").is_file())

    def test_failure_before_rename_retains_staged_record_without_publishing(self):
        record = self.f.add("running")
        with patch.object(store.storage, "_rename_no_replace", side_effect=OSError("interrupted before commit")):
            with self.assertRaises(OSError):
                self.append(record)
        self.assertEqual((self.root / "pending/000001.json").read_bytes(), p.encode_record(record))
        self.assertEqual(list((self.root / "journal").iterdir()), [])
        with self.assertRaises(ValueError):
            store.recover_append(self.root, self.receipt, record)

    def test_flush_failure_is_not_acknowledged_and_does_not_delete_pending(self):
        record = self.f.add("running")
        with patch.object(store.storage.os, "fsync", side_effect=OSError("flush failed")):
            with self.assertRaises(OSError):
                self.append(record)
        self.assertTrue((self.root / "pending/000001.json").exists())
        self.assertEqual(list((self.root / "journal").iterdir()), [])

    def test_lost_receipt_after_commit_recovers_read_only_from_exact_intent(self):
        record = self.f.add("running")
        previous = copy.deepcopy(self.receipt)
        original, calls = store._load, 0
        def interrupted(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise OSError("receipt delivery interrupted after rename")
            return original(*args, **kwargs)
        with patch.object(store, "_load", side_effect=interrupted):
            with self.assertRaises(OSError):
                self.append(record)
        before = self.snapshot()
        recovered = store.recover_append(self.root, previous, record)
        self.assertEqual(recovered["journal"]["expected_record_count"], 1)
        self.assertEqual(recovered["journal"]["expected_head_sha256"], p.record_hash(record))
        self.assertEqual(before, self.snapshot())
        with self.assertRaises(ValueError):
            store.append_record(self.root, previous, record)
        self.assertEqual(recovered, store.recover_append(self.root, previous, record))

    def test_recovery_rejects_different_intent_wrong_old_head_and_extra_tail(self):
        first = self.f.add("running")
        previous = copy.deepcopy(self.receipt)
        self.append(first)
        other = copy.deepcopy(first)
        other["context"]["runtime"]["os_ubr"] += 1
        with self.assertRaises(ValueError):
            store.recover_append(self.root, previous, other)
        wrong = copy.deepcopy(previous)
        wrong["journal"]["expected_head_sha256"] = "f" * 64
        with self.assertRaises(ValueError):
            store.recover_append(self.root, wrong, first)
        self.append(self.f.add("interrupted", reason="interrupted"))
        with self.assertRaises(ValueError):
            store.recover_append(self.root, previous, first)

    def test_receipt_cannot_be_reused_for_other_root_or_permission_flags(self):
        other = self.parent / "other"
        store.create_store(self.parent, other.name, self.f.plan)
        record = self.f.add("running")
        with self.assertRaises(ValueError):
            store.append_record(other, self.receipt, record)
        for field in ("execution_authorized", "resume_authorized", "campaign_completed", "formal_permission"):
            receipt = copy.deepcopy(self.receipt)
            receipt[field] = True
            with self.assertRaises(ValueError):
                store.append_record(self.root, receipt, record)
        self.assertEqual(list((self.root / "journal").iterdir()), [])

    def test_changed_prefix_and_unexpected_files_are_preserved_and_rejected(self):
        self.append(self.f.add("running"))
        path = self.root / "journal/000001.json"
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaises(ValueError):
            store.inspect_store(self.root, self.receipt)
        extra = self.root / "leftover.json"
        extra.write_bytes(b"{}")
        with self.assertRaisesRegex(ValueError, "layout"):
            store.inspect_store(self.root, self.receipt)
        self.assertTrue(extra.exists())

    def test_initialization_crash_leaves_root_closed_to_reuse_or_recovery(self):
        root = self.parent / "incomplete"
        with patch.object(store.storage, "_rename_no_replace", side_effect=OSError("init interrupted")):
            with self.assertRaises(OSError):
                store.create_store(self.parent, root.name, self.f.plan)
        self.assertTrue((root / "pending/plan.json").is_file())
        with self.assertRaises(ValueError):
            store.recover_initialization(root, self.f.plan_hash)
        with self.assertRaises(FileExistsError):
            store.create_store(self.parent, root.name, self.f.plan)

    def test_size_and_count_limits_refuse_before_creating_pending(self):
        record = self.f.add("running")
        for module, field, limit in ((store, "MAX_RECORD_BYTES", 1), (store, "MAX_JOURNAL_BYTES", 1),
                                      (p, "MAX_RECORDS", 0)):
            with patch.object(module, field, limit), self.assertRaises(ValueError):
                self.append(record)
            self.assertEqual(list((self.root / "pending").iterdir()), [])
        with patch.object(store, "MAX_PLAN_BYTES", 1), self.assertRaises(ValueError):
            store.create_store(self.parent, "oversize", self.f.plan)
        self.assertFalse((self.parent / "oversize").exists())

    def test_cli_append_and_read_only_recovery_use_external_hashes(self):
        cli = load_cli()
        record = self.f.add("running")
        receipt_path, record_path = self.parent / "receipt.json", self.parent / "intent.json"
        receipt_raw, record_raw = v.canonical_json(self.receipt) + b"\n", p.encode_record(record)
        receipt_path.write_bytes(receipt_raw)
        record_path.write_bytes(record_raw)
        options = ["--root", str(self.root), "--receipt", str(receipt_path), "--receipt-sha256", store.storage.sha(receipt_raw),
                   "--record", str(record_path), "--record-sha256", store.storage.sha(record_raw)]
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cli.main(["store-append", *options]), 0)
        acknowledged = v.strict_json(output.getvalue())
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cli.main(["store-recover-append", *options]), 0)
        self.assertEqual(acknowledged, v.strict_json(output.getvalue()))
        with redirect_stderr(io.StringIO()) as error:
            self.assertEqual(cli.main(["store-append", *options]), 2)
        self.assertIn("inventory", error.getvalue())
        record_path.write_bytes(record_raw + b" ")
        with redirect_stderr(io.StringIO()) as error:
            self.assertEqual(cli.main(["store-recover-append", *options]), 2)
        self.assertIn("hash mismatch", error.getvalue())

    def test_cli_init_inspect_and_recover_init(self):
        cli = load_cli()
        path = self.parent / "plan-input.json"
        path.write_bytes(v.canonical_json(self.f.plan))
        root = self.parent / "cli-store"
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cli.main(["store-init", "--parent", str(self.parent), "--name", root.name,
                "--plan", str(path), "--plan-sha256", self.f.plan_hash]), 0)
        receipt = v.strict_json(output.getvalue())
        path = self.parent / "cli-receipt.json"
        raw = v.canonical_json(receipt)
        path.write_bytes(raw)
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cli.main(["store-inspect", "--root", str(root), "--receipt", str(path),
                "--receipt-sha256", store.storage.sha(raw)]), 0)
        self.assertEqual(v.strict_json(output.getvalue())["record_count"], 0)
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cli.main(["store-recover-init", "--root", str(root), "--plan-sha256", self.f.plan_hash]), 0)
        self.assertEqual(v.strict_json(output.getvalue()), receipt)


if __name__ == "__main__":
    unittest.main()
