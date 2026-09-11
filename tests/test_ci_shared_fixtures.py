"""Synthetic evidence attacks; no repository discovery, fixture generation or native APIs."""

import copy
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import ci_compare_fixtures as compare
from tools import ci_shared_fixtures as shared
from tools import ci_test_report as ci

SOURCE = {"revision": "a" * 40, "workflow_sha256": "b" * 64, "github_run_id": "12", "github_run_attempt": "1"}


def payload(row, value):
    raw = shared.canonical(value)
    row.update(payload_json=raw.decode(), payload_bytes=len(raw), payload_sha256=hashlib.sha256(raw).hexdigest())


def journal(minor):
    owners = sorted({owner for owner, _ in shared.EXPECTED.values()})
    rows = [{"event": "run_started", "report_version": "ci-unittest.2", "source": dict(SOURCE),
             "runtime": {"os": "ubuntu", "os_version": "24.04", "architecture": "x86_64",
                         "python_version": minor + ".7", "soabi": "cpython-" + minor.replace(".", "") + "-x86_64-linux-gnu"},
             "acceptance_status": "not_completed", "formal_permission": False}]
    rows.extend({"event": "planned_test", "test_id": owner} for owner in owners)
    for owner in owners:
        rows.append({"event": "test_started", "test_id": owner})
        for name, (test_id, mode) in shared.EXPECTED.items():
            if test_id != owner: continue
            row = {"event": "shared_fixture", "fixture_id": name, "test_id": owner,
                   "comparison": mode, "fixture_version": shared.VERSION}
            payload(row, {"value": 1.0, "integer": 2486912926863618161, "flag": False, "null": None})
            rows.append(row)
        rows.append({"event": "outcome", "test_id": owner, "status": "pass"})
        rows.append({"event": "test_finished", "test_id": owner, "outcomes": ["pass"], "elapsed_seconds": 0.0})
    rows.append({"event": "run_finished", "discovered": len(owners), "tests_run": len(owners), "failures": 0, "errors": 0,
                 "skipped": 0, "expected_failures": 0, "unexpected_successes": 0, "stopped": False,
                 "unittest_success": True, "source_unchanged": True, "shared_fixture_version": shared.VERSION,
                 "shared_fixtures": len(shared.EXPECTED), "shared_fixtures_complete": True,
                 "acceptance_status": "not_completed", "formal_permission": False})
    return rows


class SharedFixtureTests(unittest.TestCase):
    def test_disabled_capture_does_not_evaluate_payload_and_nested_context_restores(self):
        with patch.object(shared, "_current", shared.ContextVar("isolated", default=None)):
            shared.record("unknown", "unknown", lambda: self.fail("inactive factory ran"))
            rows = []
            name, (owner, _) = next(iter(shared.EXPECTED.items()))
            with shared.capture(lambda event, **fields: rows.append((event, fields))) as outer:
                with shared.capture(lambda *args, **kwargs: None) as inner:
                    shared.record(name, owner, lambda: [1])
                self.assertEqual(inner.seen, {name})
                self.assertEqual(outer.seen, set())
                shared.record(name, owner, lambda: [2])
            self.assertIsNone(shared._current.get())
            self.assertEqual(json.loads(rows[0][1]["payload_json"]), [2])

    def test_capture_requires_full_inventory_and_latches_swallowed_errors(self):
        rows = []
        with shared.capture(lambda event, **fields: rows.append(fields)) as cap:
            self.assertFalse(cap.complete())
            for name, (owner, _) in shared.EXPECTED.items(): shared.record(name, owner, lambda: {"x": -0.0})
            self.assertTrue(cap.complete())
            name, (owner, _) = next(iter(shared.EXPECTED.items()))
            with self.assertRaises(ValueError): shared.record(name, owner, lambda: self.fail("duplicate factory ran"))
            self.assertFalse(cap.complete())
        self.assertEqual(len(rows), 29)
        self.assertEqual(sum(mode == "numeric" for _, mode in shared.EXPECTED.values()), 6)

    def test_bad_owner_unknown_id_invalid_payload_and_byte_limits_poison_capture(self):
        name, (owner, _) = next(iter(shared.EXPECTED.items()))
        for bad_name, bad_owner, value in (("unknown", owner, {}), (name, "wrong", {}), (name, owner, float("nan")),
                                            (name, owner, (1, 2)), (name, owner, {1: "bad"})):
            with self.subTest(name=bad_name, owner=bad_owner), shared.capture(lambda *args, **kwargs: None) as cap:
                with self.assertRaises(ValueError): shared.record(bad_name, bad_owner, lambda: value)
                self.assertTrue(cap.failed)
        for bound in ("MAX_PAYLOAD_BYTES", "MAX_TOTAL_BYTES"):
            with self.subTest(bound=bound), patch.object(shared, bound, 1), shared.capture(lambda *args, **kwargs: self.fail("oversize emitted")) as cap:
                with self.assertRaises(ValueError): shared.record(name, owner, lambda: [1])
                self.assertEqual(cap.seen, set())
                self.assertFalse(cap.complete())

    def test_emit_or_factory_failure_is_not_a_completed_record(self):
        name, (owner, _) = next(iter(shared.EXPECTED.items()))
        def fail(*args, **kwargs): raise OSError("synthetic")
        for writer, factory in ((fail, lambda: [1]), (lambda *a, **k: None, fail)):
            with shared.capture(writer) as cap:
                with self.assertRaises(OSError): shared.record(name, owner, factory)
                self.assertEqual(cap.seen, set())
                self.assertTrue(cap.failed)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="banto-shared-evidence-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def pair(self, rows=None):
        rows = rows or {minor: journal(minor) for minor in compare.MINORS}
        paths = {}
        for minor in compare.MINORS:
            path = self.root / (minor + ".jsonl")
            path.write_bytes(b"".join(shared.canonical(row) + b"\n" for row in rows[minor]))
            paths[minor] = path
        return paths

    def test_equal_pair_is_explicitly_unaccepted_and_keeps_source_digests(self):
        result = compare.compare_reports(self.pair(), SOURCE)
        self.assertEqual(result["comparison_status"], "matched")
        self.assertEqual(len(result["fixtures"]), 29)
        self.assertEqual(result["acceptance_status"], "not_completed")
        self.assertFalse(result["formal_permission"])
        self.assertFalse(result["execution_authenticated"])
        self.assertEqual(result["source"], SOURCE)

    def test_numeric_tolerance_only_applies_to_declared_float_values(self):
        for name, value, accepted in (("profile-values-C0", 1.0 + 1e-13, True), ("profile-values-C0", 1.001, False),
                                      ("Q1", 1.0 + 1e-13, False), ("profile-values-C0", 1, False), ("profile-values-C0", True, False)):
            rows = {minor: journal(minor) for minor in compare.MINORS}
            row = next(r for r in rows["3.14"] if r.get("fixture_id") == name)
            changed = json.loads(row["payload_json"]); changed["value"] = value; payload(row, changed)
            with self.subTest(name=name, value=value):
                if accepted: compare.compare_reports(self.pair(rows), SOURCE)
                else:
                    with self.assertRaises(compare.EvidenceError): compare.compare_reports(self.pair(rows), SOURCE)
        self.assertFalse(compare.numeric_equal({"count": 10**18}, {"count": 10**18+1}))
        self.assertFalse(compare.numeric_equal({"x": [1.0]}, {"y": [1.0]}))

    def test_exact_signed_zero_payload_bytes_are_distinct(self):
        rows = {minor: journal(minor) for minor in compare.MINORS}
        for minor, value in (("3.12", -0.0), ("3.14", 0.0)):
            row = next(r for r in rows[minor] if r.get("fixture_id") == "Q5")
            payload(row, {"value": value})
        with self.assertRaisesRegex(compare.EvidenceError, "shared_fixture_mismatch"):
            compare.compare_reports(self.pair(rows), SOURCE)

    def test_wrong_source_runtime_summary_and_acceptance_claims_are_rejected(self):
        attacks = [(0, "source", {**SOURCE, key: "wrong"}) for key in SOURCE]
        attacks += [(0, "report_version", "ci-unittest.1"), (0, "formal_permission", True),
                    (0, "runtime", {"os": "windows"}), (-1, "shared_fixtures_complete", False),
                    (-1, "shared_fixtures", 28), (-1, "tests_run", True), (-1, "discovered", 99),
                    (-1, "unittest_success", False), (-1, "source_unchanged", False), (-1, "stopped", True),
                    (-1, "failures", 1), (-1, "skipped", 1), (-1, "acceptance_status", "completed")]
        for index, key, value in attacks:
            rows = {minor: journal(minor) for minor in compare.MINORS}
            rows["3.14"][index][key] = value
            with self.subTest(index=index, key=key), self.assertRaises(compare.EvidenceError):
                compare.compare_reports(self.pair(rows), SOURCE)

    def test_missing_duplicate_wrong_owner_or_tampered_fixture_is_rejected(self):
        for attack in ("missing", "duplicate", "owner", "mode", "hash", "size", "version", "noncanonical", "nonfinite", "unknown"):
            rows = {minor: journal(minor) for minor in compare.MINORS}
            journal_rows = rows["3.14"]
            index = next(i for i, r in enumerate(journal_rows) if r.get("fixture_id") == "Q1")
            row = journal_rows[index]
            if attack == "missing": journal_rows.pop(index)
            elif attack == "duplicate": journal_rows.insert(index, copy.deepcopy(row))
            elif attack == "owner": row["test_id"] = "wrong"
            elif attack == "mode": row["comparison"] = "numeric"
            elif attack == "hash": row["payload_sha256"] = "f" * 64
            elif attack == "size": row["payload_bytes"] = True
            elif attack == "version": row["fixture_version"] = "old"
            elif attack == "unknown": row["fixture_id"] = "unknown"
            else:
                raw = (" " + row["payload_json"]) if attack == "noncanonical" else '{"x":NaN}'
                row.update(payload_json=raw, payload_bytes=len(raw), payload_sha256=hashlib.sha256(raw.encode()).hexdigest())
            with self.subTest(attack=attack), self.assertRaises(compare.EvidenceError): compare.compare_reports(self.pair(rows), SOURCE)

    def test_partial_extra_reordered_and_skipped_owner_records_are_rejected(self):
        for attack in ("partial", "after_finish", "reordered", "owner_skip", "no_start"):
            rows = {minor: journal(minor) for minor in compare.MINORS}
            right = rows["3.14"]
            if attack == "partial": right.pop()
            elif attack == "after_finish": right.append(dict(right[-1]))
            elif attack == "reordered": right[1], right[2] = right[2], right[1]
            elif attack == "no_start": right.pop(next(i for i, r in enumerate(right) if r["event"] == "test_started"))
            else:
                next(r for r in right if r["event"] == "outcome")["status"] = "skip"
                next(r for r in right if r["event"] == "test_finished")["outcomes"] = ["skip"]
                right[-1]["skipped"] = 1
            with self.subTest(attack=attack), self.assertRaises(compare.EvidenceError): compare.compare_reports(self.pair(rows), SOURCE)

    def test_strict_json_and_file_bounds_reject_truncation_duplicates_and_overflow(self):
        paths = self.pair()
        original = paths["3.14"].read_bytes()
        for raw in (original[:-1], original.replace(b'"report_version":', b'"source":{},"report_version":', 1), b'{"x":1e999}\n'):
            paths["3.14"].write_bytes(raw)
            with self.assertRaises(compare.EvidenceError): compare.compare_reports(paths, SOURCE)
        paths["3.14"].write_bytes(original)
        with patch.object(compare, "MAX_LINE_BYTES", 10), self.assertRaises(compare.EvidenceError): compare.compare_reports(paths, SOURCE)
        with patch.object(ci, "MAX_REPORT_BYTES", 10), self.assertRaises(compare.EvidenceError): compare.compare_reports(paths, SOURCE)

    def test_ci_main_fails_when_passing_suite_does_not_emit_required_fixtures(self):
        class Sample(unittest.TestCase):
            def test_ok(self): pass
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(Sample)
        with patch.object(ci, "ROOT", self.root), patch.object(ci, "runtime_metadata", return_value={"fixture": True}), \
                patch.object(ci, "source_identity", return_value=SOURCE), patch.object(unittest.TestLoader, "discover", return_value=suite), \
                patch.object(ci.sys, "stderr", io.StringIO()):
            self.assertEqual(ci.main(), 1)
        last = json.loads((self.root / ci.REPORT).read_bytes().splitlines()[-1])
        self.assertTrue(last["unittest_success"])
        self.assertFalse(last["shared_fixtures_complete"])

    def test_comparison_cli_saves_failure_on_source_drift_and_never_overwrites(self):
        for minor, path in self.pair().items():
            dest = self.root / "artifacts/ci-fixtures" / ("python" + minor) / "unittest.jsonl"
            dest.parent.mkdir(parents=True)
            dest.write_bytes(path.read_bytes())
        with patch.object(compare, "ROOT", self.root), patch.object(ci, "source_identity", side_effect=[SOURCE, {**SOURCE, "revision": "c" * 40}]), patch.object(compare.sys, "stdout", io.StringIO()):
            self.assertEqual(compare.main(), 1)
        path = self.root / "artifacts/ci-fixtures/comparison.json"
        raw = path.read_bytes()
        self.assertEqual(json.loads(raw)["reason"], "comparison_source_changed")
        with patch.object(compare, "ROOT", self.root), patch.object(ci, "source_identity", return_value=SOURCE), self.assertRaises(FileExistsError): compare.main()
        self.assertEqual(path.read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()
