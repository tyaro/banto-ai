"""Small journal metadata fixtures only; never run observations/scoring."""
from __future__ import annotations

import copy
import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from banto_ai import _anomaly_v03_contract as c
from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_checkpoints as p
from banto_ai import anomaly_v03_materializer as materializer


def load_cli():
    spec = importlib.util.spec_from_file_location("checkpoint_cli", Path(__file__).resolve().parents[1]
                                               / "tools/evaluator/checkpoint_anomaly_v03.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class JournalFixture:
    def __init__(self):
        self.plan = p.fixed_plan("a" * 40, "b" * 40)
        self.plan_hash = v.canonical_sha256(self.plan)
        self.records = []
        self.context = {"source_bindings": self.plan["source_bindings"],
                        "runtime": c.formal_runtime() | {"os_ubr": 9445}}

    @property
    def head(self):
        return p.record_hash(self.records[-1]) if self.records else self.plan_hash

    def add(self, status, *, chunk=0, attempt=1, evidence=None, outcome=None, reason=None):
        record = p.make_record(self.plan_hash, self.head, len(self.records) + 1, chunk, attempt,
                               status, self.context, evidence=evidence, outcome=outcome, reason=reason)
        self.records.append(record)
        return record

    def reduce(self, **overrides):
        args = {"expected_plan_sha256": self.plan_hash, "expected_record_count": len(self.records),
                "expected_head_sha256": self.head} | overrides
        return p.reduce_journal(self.plan, self.records, **args)

    def complete(self, chunk=0, attempt=1, inconclusive=False):
        self.add("running", chunk=chunk, attempt=attempt)
        pins = {"marker_sha256": "c" * 64, "supervision_sha256": None, "audit_sha256": None}
        self.add("saved_pending_verification", chunk=chunk, attempt=attempt, evidence=pins)
        pins.update(supervision_sha256="d" * 64, audit_sha256="e" * 64)
        outcome = {"worker_exit_confirmed": True, "runtime_after": self.context["runtime"],
            "audit_scope": "stored_score_ledgers_only",
            "slots": [{"evaluation_id": identity["evaluation_id"],
                       "status": "inconclusive" if inconclusive and i == 1 else "success"}
                      for i, identity in enumerate(self.plan["chunks"][chunk]["identities"])]}
        self.add("verified_inconclusive" if inconclusive else "verified_complete", chunk=chunk,
                 attempt=attempt, evidence=pins, outcome=outcome)

    def rechain(self):
        previous = self.plan_hash
        for sequence, record in enumerate(self.records, 1):
            record.update(previous_sha256=previous, sequence=sequence)
            previous = p.record_hash(record)


class PlanTests(unittest.TestCase):
    def test_all_registered_cells_in_fixed_order_without_generation(self):
        with patch.object(materializer, "normal_stream", side_effect=AssertionError("no generation")):
            plan = p.fixed_plan("a" * 40, "b" * 40)
            p.validate_plan(plan)
        identities = [identity for chunk in plan["chunks"] for identity in chunk["identities"]]
        self.assertEqual(identities, v.evaluation_inventory("dev") + v.evaluation_inventory("smoke"))
        self.assertEqual(len({x["evaluation_id"] for x in identities}), 720)
        self.assertEqual(len(plan["chunks"]), 120)
        self.assertEqual(plan["chunks"][95]["role"], "dev")
        self.assertEqual(plan["chunks"][96]["role"], "smoke")
        for chunk in plan["chunks"]:
            self.assertEqual(len({(x["seed"], x["layout"]) for x in chunk["identities"]}), 1)
            self.assertEqual(len({x["dataset_id"] for x in chunk["identities"]}), 2)
        self.assertFalse(plan["execution_authorized"])
        self.assertEqual(plan["budgets"]["status"], "not_frozen")

    def test_plan_mutations_including_typed_literals_and_rehashed_order_rejected(self):
        mutations = [lambda x: x["chunks"].reverse(), lambda x: x["chunks"][0]["identities"].pop(),
            lambda x: x["chunks"][0]["identities"][0].update(role="holdout"),
            lambda x: x["planned_counts"].update(chunks=120.0),
            lambda x: x.update(execution_authorized=0), lambda x: x.update(formal_permission=True),
            lambda x: x["budgets"].update(campaign={"wall_seconds": 100}),
            lambda x: x["source_bindings"].update(producer_revision="bad")]
        for mutate in mutations:
            value = p.fixed_plan("a" * 40, "b" * 40)
            mutate(value)
            value["chunks_sha256"] = v.canonical_sha256(value["chunks"])
            with self.assertRaises(ValueError):
                p.validate_plan(value)

    def test_plan_copies_are_independent_and_bindings_need_complete_revision(self):
        first = p.fixed_plan("a" * 40, "b" * 40)
        first["chunks"][0]["identities"].clear()
        self.assertEqual(len(p.fixed_plan("a" * 40, "b" * 40)["chunks"][0]["identities"]), 6)
        for bad in ("abc1234", "A" * 40, True, None):
            with self.assertRaises(ValueError):
                p.fixed_plan(bad, "b" * 40)


class ReducerTests(unittest.TestCase):
    def setUp(self):
        self.f = JournalFixture()

    def test_empty_and_abruptly_ended_running_journal_never_resume(self):
        report = self.f.reduce()
        self.assertEqual(report["coverage"]["not_started"], 120)
        self.assertFalse(report["resume_authorized"])
        self.f.add("running")
        self.assertEqual(self.f.reduce()["next_action"], "reconcile_interrupted_attempt")
        self.f.add("running", attempt=2)
        with self.assertRaises(ValueError):
            self.f.reduce()

    def test_marker_only_stays_pending_and_cannot_skip_next_chunk(self):
        self.f.add("running")
        self.f.add("saved_pending_verification", evidence={"marker_sha256": "c" * 64,
            "supervision_sha256": None, "audit_sha256": None})
        report = self.f.reduce()
        self.assertEqual(report["coverage"]["saved_pending_verification"], 1)
        self.assertEqual(report["next_action"], "verify_saved_attempt")
        self.f.add("running", chunk=1)
        with self.assertRaises(ValueError):
            self.f.reduce()

    def test_failed_and_interrupted_attempts_are_retained_with_new_roots(self):
        self.f.add("running")
        self.f.add("failed", reason="worker_exit")
        self.f.add("running", attempt=2)
        self.f.add("interrupted", attempt=2, reason="interrupted")
        self.assertEqual(self.f.reduce()["next_action"], "new_attempt_required")
        self.f.complete(attempt=3, inconclusive=True)
        report = self.f.reduce()
        self.assertEqual(report["failed_attempt_count"], 2)
        self.assertEqual(report["attempt_count"], 3)
        self.assertEqual(report["coverage"]["verified_inconclusive"], 1)
        self.assertEqual(len({a["attempt_root"] for a in report["chunks"][0]["attempts"]}), 3)
        self.assertEqual(report["next_action"], "revalidate_saved_evidence")
        self.assertFalse(report["evidence_revalidated"])
        self.assertFalse(report["campaign_completed"])

    def test_skipped_attempt_and_reused_root_are_rejected(self):
        self.f.add("running")
        self.f.add("failed", reason="exception")
        self.f.add("running", attempt=3)
        with self.assertRaises(ValueError):
            self.f.reduce()
        self.f.records[-1]["attempt"] = 2
        self.f.records[-1]["attempt_root"] = "chunks/000/attempt-0001"
        with self.assertRaises(ValueError):
            self.f.reduce()

    def test_integrity_failure_is_terminal_and_cannot_be_disguised_as_retry(self):
        self.f.add("running")
        self.f.add("blocked_integrity", reason="hash_mismatch")
        self.assertEqual(self.f.reduce()["next_action"], "investigate_integrity_failure")
        self.f.add("running", attempt=2)
        with self.assertRaises(ValueError):
            self.f.reduce()
        self.f.records.pop()
        self.f.records[-1]["status"] = "failed"
        with self.assertRaises(ValueError):
            self.f.reduce()

    def test_prepublication_failure_keeps_supervision_pin_without_marker(self):
        for status, reason in (("failed", "resource_limit"), ("failed", "worker_exit"),
                               ("interrupted", "interrupted"), ("blocked_integrity", "runtime_changed")):
            with self.subTest(status=status, reason=reason):
                fixture = JournalFixture()
                fixture.add("running")
                pins = {"marker_sha256": None, "supervision_sha256": "d" * 64, "audit_sha256": None}
                fixture.add(status, reason=reason, evidence=pins)
                report = fixture.reduce()
                self.assertEqual(report["chunks"][0]["attempts"][0]["evidence"], pins)
                if status != "blocked_integrity":
                    fixture.complete(attempt=2)
                    report = fixture.reduce()
                    self.assertEqual(report["chunks"][0]["attempts"][0]["evidence"], pins)
                    self.assertEqual(report["failed_attempt_count"], 1)

    def test_external_plan_head_and_count_detect_tampering_and_tail_loss(self):
        self.f.complete()
        head, count = self.f.head, len(self.f.records)
        for overrides in ({"expected_plan_sha256": "f" * 64}, {"expected_head_sha256": "f" * 64},
                          {"expected_record_count": True}, {"expected_record_count": 2}):
            with self.assertRaises(ValueError):
                self.f.reduce(**overrides)
        self.f.records.pop()
        with self.assertRaises(ValueError):
            self.f.reduce(expected_record_count=count, expected_head_sha256=head)
        self.f.records.clear()
        with self.assertRaises(ValueError):
            self.f.reduce(expected_record_count=0, expected_head_sha256=head)

    def test_reordered_deleted_and_duplicated_records_rejected(self):
        self.f.complete()
        records = copy.deepcopy(self.f.records)
        for indices in ([1, 0, 2], [0, 2], [0, 1, 1, 2]):
            self.f.records = [copy.deepcopy(records[i]) for i in indices]
            self.f.rechain()
            with self.assertRaises(ValueError):
                self.f.reduce()

    def test_next_chunk_must_be_fixed_and_completed_chunk_cannot_be_retried(self):
        self.f.complete()
        self.f.add("running", chunk=2)
        with self.assertRaises(ValueError):
            self.f.reduce()
        self.f.records.pop()
        self.f.add("running", attempt=2)
        with self.assertRaises(ValueError):
            self.f.reduce()

    def test_verification_requires_all_pins_worker_exit_runtime_and_six_outcomes(self):
        self.f.complete()
        original = copy.deepcopy(self.f.records)
        mutations = [lambda x: x["evidence"].update(audit_sha256=None),
            lambda x: x["evidence"].update(supervision_sha256=None),
            lambda x: x["evidence"].update(marker_sha256="f" * 64),
            lambda x: x["outcome"].update(worker_exit_confirmed=1),
            lambda x: x["outcome"]["runtime_after"].update(os_ubr=9446),
            lambda x: x["outcome"]["slots"].pop(), lambda x: x["outcome"]["slots"].reverse(),
            lambda x: x["outcome"]["slots"][0].update(status="inconclusive"),
            lambda x: x["outcome"].update(audit_scope="full_s6"),
            lambda x: x.update(chunk_index=False)]
        for mutate in mutations:
            self.f.records = copy.deepcopy(original)
            mutate(self.f.records[-1])
            with self.assertRaises(ValueError):
                self.f.reduce()

    def test_source_changes_and_runtime_changes_within_attempt_are_rejected(self):
        self.f.complete()
        original = copy.deepcopy(self.f.records)
        for mutate in (lambda x: x["context"]["source_bindings"].update(producer_revision="f" * 40),
                       lambda x: x["context"]["runtime"].update(os_ubr=9446),
                       lambda x: x["context"]["runtime"].update(python_version="3.12.0")):
            self.f.records = copy.deepcopy(original)
            mutate(self.f.records[1])
            self.f.rechain()
            with self.assertRaises(ValueError):
                self.f.reduce()

    def test_windows_update_between_chunks_is_recorded_without_acceptance_promotion(self):
        self.f.complete()
        self.f.context["runtime"]["os_ubr"] = 9446
        self.f.complete(chunk=1)
        report = self.f.reduce()
        self.assertEqual(report["next_unverified_chunk"], 2)
        self.assertEqual(self.f.records[0]["context"]["runtime"]["os_ubr"], 9445)
        self.assertEqual(self.f.records[3]["context"]["runtime"]["os_ubr"], 9446)
        self.assertFalse(report["formal_permission"])

    def test_all_120_declared_chunks_still_require_evidence_revalidation(self):
        for chunk in range(120):
            self.f.complete(chunk=chunk, inconclusive=chunk == 119)
        report = self.f.reduce()
        self.assertTrue(report["declared_coverage_complete"])
        self.assertIsNone(report["next_unverified_chunk"])
        self.assertEqual(report["coverage"]["verified_complete"], 119)
        self.assertEqual(report["coverage"]["verified_inconclusive"], 1)
        self.assertFalse(report["resume_authorized"])
        self.assertFalse(report["campaign_completed"])
        self.assertFalse(report["independent_s6_complete"])
        self.assertEqual(report["performance_status"], "not_evaluated")


class ReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cli = load_cli()

    def setUp(self):
        self.f = JournalFixture()
        self.f.complete()
        temp = tempfile.TemporaryDirectory(prefix="banto-checkpoint-metadata-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.plan_path = self.root / "plan.json"
        self.journal = self.root / "journal"
        self.journal.mkdir()
        self.plan_path.write_bytes(v.canonical_json(self.f.plan) + b"\n")
        for number, record in enumerate(self.f.records, 1):
            (self.journal / f"{number:06d}.json").write_bytes(p.encode_record(record))

    def inspect(self):
        return self.cli.inspect(self.plan_path, self.journal, self.f.plan_hash, len(self.f.records), self.f.head)

    def test_real_read_only_reader_preserves_all_metadata_bytes(self):
        before = {str(path): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        report = self.inspect()
        self.assertEqual(report, self.f.reduce())
        after = {str(path): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(before, after)

    def test_missing_tail_extra_file_and_noncanonical_or_partial_record_fail_closed(self):
        path = self.journal / "000003.json"
        raw = path.read_bytes()
        path.unlink()
        with self.assertRaises(ValueError):
            self.inspect()
        for invalid in (raw[:-1], raw[:20], b" " + raw, b'{"a":1,"a":2}\n'):
            path.write_bytes(invalid)
            with self.assertRaises(ValueError):
                self.inspect()
        path.write_bytes(raw)
        (self.journal / "leftover.tmp").write_text("partial", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.inspect()

    def test_metadata_size_caps_and_negative_count(self):
        with patch.object(self.cli, "MAX_PLAN_BYTES", 10), self.assertRaises(ValueError):
            self.inspect()
        with patch.object(self.cli, "MAX_RECORD_BYTES", 10), self.assertRaises(ValueError):
            self.inspect()
        with patch.object(self.cli, "MAX_JOURNAL_BYTES", 10), self.assertRaises(ValueError):
            self.inspect()
        with self.assertRaises(ValueError):
            self.cli.inspect(self.plan_path, self.journal, self.f.plan_hash, -1, self.f.head)

    def test_change_between_initial_read_and_final_recheck_is_rejected(self):
        original = self.cli._read
        calls = 0
        def changing_read(path, maximum):
            nonlocal calls
            raw = original(path, maximum)
            calls += 1
            if calls == 4:
                with (self.journal / "000001.json").open("ab") as stream:
                    stream.write(b" ")
            return raw
        with patch.object(self.cli, "_read", side_effect=changing_read):
            with self.assertRaisesRegex(ValueError, "journal changed during inspection"):
                self.inspect()

    def test_cli_emits_plan_and_read_report_and_failure_exit_two(self):
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(self.cli.main(["plan", "--producer-revision", "a" * 40,
                                           "--consumer-revision", "b" * 40]), 0)
        self.assertEqual(v.strict_json(output.getvalue()), self.f.plan)
        args = ["inspect", "--plan", str(self.plan_path), "--plan-sha256", self.f.plan_hash,
                "--journal-dir", str(self.journal), "--record-count", "3", "--head-sha256", self.f.head]
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(self.cli.main(args), 0)
        self.assertEqual(v.strict_json(output.getvalue())["status"], "journal_metadata_valid")
        args[-1] = "f" * 64
        with redirect_stderr(io.StringIO()) as error:
            self.assertEqual(self.cli.main(args), 2)
        self.assertEqual(v.strict_json(error.getvalue())["status"], "checkpoint_metadata_failed")


if __name__ == "__main__":
    unittest.main()
