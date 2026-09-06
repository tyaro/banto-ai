"""S3 fake inventory attacks and full hand-series S2 integration, no campaigns."""

from __future__ import annotations

import copy
import io
import tempfile
import unittest
import weakref
from collections.abc import Sequence
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from banto_ai import _anomaly_v03_contract as c
from banto_ai import _anomaly_v03_runtime as rt
from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_materializer as m
from banto_ai import anomaly_v03_runner as r
from banto_ai._anomaly_v03_io import payload_entry
from tests.test_anomaly_v03_materializer import hand_pair, release_class_fields
from tests.test_anomaly_v03_scoring import identity

ROOT = Path(__file__).resolve().parents[1]


def fixture_checkout():
    # Explicitly invented source; never passed as accepted formal provenance.
    return rt.Checkout(Path("fixture"), "a"*40, (("src/fixture.py", b"# fixture source\n"),))


class MemoryStore:
    def __init__(self):
        self.expected, self.files = {}, {}

    def write(self, name, raw):
        if name in self.files:
            raise rt.IntegrityError("nonoverwrite")
        self.expected[name], self.files[name] = payload_entry(name, raw), raw

    def read(self, name):
        raw = self.files[name]
        rt.require(payload_entry(name, raw) == self.expected[name], "input changed")
        return raw


class FakeBackend:
    """Metadata scheduler fixture. No generated observations or result publication."""
    def __init__(self, mutation=None):
        self.mutation, self.calls, self.starts, self.dones = mutation, [], [], []

    def begin(self, planned):
        self.plan = planned

    def started(self, index, ident):
        self.starts.append((index, ident))

    def finished(self, index, slot):
        self.dones.append((index, slot))

    def failure_evidence(self, identity):
        return {}

    def evaluate(self, index, ident):
        self.calls.append(ident)
        row = {"identity": ident, "status": "success", "failure_stage": None, "safe_reason": None,
               "input_hashes": dict.fromkeys(m.INPUT_FILES, "a"*64),
               "evidence": [{"path": "fixture/evaluation.json", "raw_sha256": "b"*64, "canonical_sha256": "c"*64, "row_count": 1}]}
        if self.mutation:
            self.mutation(index, row)
        return row


class InventoryEngineTests(unittest.TestCase):
    def test_count_oracle_complete_960_datasets_2880_slots_no_generation(self):
        fake = FakeBackend()
        with patch.object(m, "normal_stream", side_effect=AssertionError("generation forbidden")):
            slots, stopped = r._drive("holdout", fake, lambda: None)
        self.assertFalse(stopped)
        self.assertEqual(fake.calls, v.evaluation_inventory("holdout"))
        self.assertEqual(len({s["identity"]["dataset_id"] for s in slots}), 960)
        self.assertEqual(len(slots), 2880)
        self.assertEqual(len(fake.dones), 2880)
        self.assertEqual(r._coverage(slots), dict(success=2880, partial=0, inconclusive=0, failed=0, not_started=0))
        expected = {"observations": 960*18000, "scores": 2880*14400, "profiles": 2880*48, "events": 960*40}
        self.assertEqual(expected, dict(observations=17280000, scores=41472000, profiles=138240, events=38400))

    def test_dev_smoke_metadata_sizes_and_inventory_order(self):
        for role, expected in (("dev", 576), ("smoke", 144)):
            slots, stopped = r._drive(role, FakeBackend(), lambda: None)
            self.assertFalse(stopped)
            self.assertEqual(len(slots), expected)
            self.assertEqual([x["identity"]["candidate_id"] for x in slots[:3]], list(c.CANDIDATES))
            self.assertEqual([x["identity"]["stratum"] for x in slots[:6]], ["core"]*3+["quality-stress"]*3)

    def test_normal_failure_preserves_full_ledger_and_continues(self):
        def mutate(index, row):
            if index == 2:
                raise r.CellFailure("profile", evidence=row["evidence"], input_hashes=row["input_hashes"])
            if index == 5:
                raise RuntimeError("secret exception text must not escape")
        fake = FakeBackend(mutate)
        slots, stopped = r._drive("smoke", fake, lambda: None)
        self.assertFalse(stopped)
        self.assertEqual(len(slots), 144)
        self.assertEqual((slots[2]["status"], slots[5]["status"], slots[6]["status"]), ("partial", "failed", "success"))
        self.assertNotIn("secret", v.canonical_json(slots).decode())
        self.assertEqual(r._matrix_status(slots, stopped), r._status("complete", "fail"))

    def test_global_failure_stops_and_preserves_future_not_started(self):
        def mutate(index, row):
            if index == 4:
                raise rt.IntegrityError("input changed")
        fake = FakeBackend(mutate)
        slots, stopped = r._drive("holdout", fake, lambda: None)
        self.assertTrue(stopped)
        self.assertEqual(len(fake.calls), 5)
        self.assertEqual(len(slots), 2880)
        self.assertEqual(r._coverage(slots), dict(success=4, partial=0, inconclusive=0, failed=1, not_started=2875))
        self.assertEqual(slots[4]["failure_stage"], "integrity")
        self.assertTrue(all(s["input_hashes"] is None and not s["evidence"] for s in slots[5:]))

    def test_inventory_identity_missing_counts_partial_fake_success_attacks(self):
        for attack in ("identity", "partial", "hash-only", "extra", "bool-row-count", "paired-hash"):
            def mutate(index, row):
                if index != 1: return
                if attack == "identity": row["identity"]["layout"] += 1
                elif attack == "partial": row["status"] = "partial"
                elif attack == "hash-only": row["evidence"] = []
                elif attack == "extra": row["extra"] = True
                elif attack == "bool-row-count": row["evidence"][0]["row_count"] = True
                else: row["input_hashes"]["observations"] = "d"*64
            slots, stopped = r._drive("smoke", FakeBackend(mutate), lambda: None)
            with self.subTest(attack=attack):
                self.assertTrue(stopped)
                self.assertEqual(r._coverage(slots)["not_started"], 142)

    def test_defined_inconclusive_not_success_or_software_failure(self):
        def mutate(index, row):
            if index == 0:
                row.update(status="inconclusive", failure_stage="profile", safe_reason="profile_inconclusive")
        slots, stopped = r._drive("smoke", FakeBackend(mutate), lambda: None)
        self.assertFalse(stopped)
        self.assertEqual(r._matrix_status(slots, stopped), r._status("complete", "inconclusive"))

    def test_interrupted_run_never_reclassifies_future_as_misses(self):
        def mutate(index, row):
            if index == 0: raise KeyboardInterrupt()
        slots, stopped = r._drive("smoke", FakeBackend(mutate), lambda: None)
        self.assertTrue(stopped)
        self.assertEqual(slots[0]["safe_reason"], "incomplete")
        self.assertEqual(r._coverage(slots)["not_started"], 143)

    def test_start_and_final_boundary_failure_are_not_success(self):
        for failing_call in (1, 2, 4):
            calls = []
            def boundary():
                calls.append(1)
                if len(calls) == failing_call: raise rt.IntegrityError("source/runtime/root changed")
            slots, stopped = r._drive("smoke", FakeBackend(), boundary)
            self.assertTrue(stopped)
            self.assertEqual(r._matrix_status(slots, stopped), r._status("failed", "fail"))

    def test_journal_failure_stops_later_slots_and_initial_failure_keeps_plan(self):
        fake = FakeBackend()
        with patch.object(fake, "finished", side_effect=OSError("disk full")):
            slots, stopped = r._drive("smoke", fake, lambda: None)
        self.assertTrue(stopped)
        self.assertEqual(slots[0]["failure_stage"], "publication")
        self.assertEqual(r._coverage(slots)["not_started"], 143)
        with patch.object(fake, "begin", side_effect=OSError("disk full")):
            slots, stopped = r._drive("holdout", fake, lambda: None)
        self.assertTrue(stopped)
        self.assertEqual(r._coverage(slots)["not_started"], 2880)

    def test_validate_only_is_read_only_and_not_run(self):
        with patch.object(m, "normal_stream", side_effect=AssertionError("generation")), patch.object(r, "_run_prepared", side_effect=AssertionError("run")):
            report = r.validate_only(ROOT)
        self.assertEqual(report["planned_slots"], 2880)
        self.assertEqual(report["run_status"], "not_run")
        self.assertFalse(report["output_created"])

    def test_run_unsupported_before_claim_generation_and_acceptance_gate(self):
        with patch.object(rt.os, "name", "posix"), patch.object(m, "materialize_pair", side_effect=AssertionError("generation")):
            with self.assertRaisesRegex(rt.IntegrityError, "unsupported_runtime"):
                r.run_campaign(ROOT, "holdout", expected_head="a"*40)
        with patch.object(rt, "probe_runtime", return_value=c.formal_runtime()):
            with self.assertRaisesRegex(rt.IntegrityError, "s4_acceptance_not_frozen"):
                r.run_campaign(ROOT, "holdout", expected_head="a"*40)

    def test_cli_validate_only_and_no_override_flags(self):
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(r.main(["--validate-only", "--root", str(ROOT)]), 0)
        self.assertEqual(v.strict_json(output.getvalue())["planned_slots"], 2880)
        self.assertTrue(all(not (ROOT/path).exists() for path in c.OUTPUT_ROOTS))


class SavedEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addClassCleanup(release_class_fields, cls, "checkout", "pair", "saved", "results")
        temporary = tempfile.TemporaryDirectory(prefix="banto-v03-result-fixture-")
        cls.addClassCleanup(temporary.cleanup)
        cls.checkout = fixture_checkout()
        cls.pair = hand_pair()
        cls.saved = cls.pair[0].files()
        # Three independently fit profiles on exactly the same hand-saved bytes.
        # Preserve every result byte, but do not retain three decoded ledgers
        # while S2 constructs and canonical-compares the next full ledger.
        paths = []
        with patch.object(m, "normal_stream", side_effect=AssertionError("registered generation")):
            for candidate in range(3):
                result = r.compute_evaluation(identity(candidate), cls.saved, cls.checkout)
                path = Path(temporary.name)/f"candidate-{candidate}.json"
                path.write_bytes(m.json_bytes(result))
                paths.append(path)
                del result
        cls.results = SavedResultFiles(paths)

    def test_three_candidates_share_saved_bytes_hashes_and_fixed_rows(self):
        hashes = self.pair[0].input_hashes()
        for candidate, result in enumerate(self.results):
            self.assertEqual(result["input_hashes"], hashes)
            self.assertEqual([result["row_counts"][k] for k in ("events", "profiles", "scores", "incidents")], [40, 48, 14400, 20])
            self.assertEqual(result["status"]["performance_status"], "not_evaluated")
            self.assertEqual(result["identity"], identity(candidate))

    def test_saved_replay_rejects_hash_only_coordinated_numeric_ledger_forgery(self):
        forged = copy.deepcopy(self.results[0])
        point = next(s for s in forged["scores"] if s["available"] and not s["threshold_exceeded"])
        point["residual"] += 0.001
        # S1 syntax/ledger consistency alone accepts this forged mathematical value.
        v.validate_result_contract(forged, source_snapshots=self.checkout.snapshots())
        with self.assertRaisesRegex(rt.IntegrityError, "replay mismatch"):
            r.verify_evaluation(forged, identity(), self.saved, self.checkout)

    def test_partial_cannot_claim_success_by_adjusting_row_count_or_hashes(self):
        forged = copy.deepcopy(self.results[0])
        forged["scores"].pop(); forged["row_counts"]["scores"] -= 1
        with self.assertRaises(v.V03ValidationError):
            r.verify_evaluation(forged, identity(), self.saved, self.checkout)

    def test_disk_backend_rereads_same_saved_capture_and_rejects_input_mutation(self):
        store = MemoryStore()
        backend = r._DiskBackend(store, self.checkout)
        first = self.results[0]
        with patch.object(m, "materialize_pair", return_value=self.pair) as materialize, \
                patch.object(r, "_execute_candidate", new=lambda *_: first), \
                patch.object(r, "compute_evaluation", new=lambda *_: first):
            self.addCleanup(materialize.reset_mock, return_value=True, side_effect=True)
            completed = backend.evaluate(0, identity())
            self.assertEqual(completed["status"], "success")
            self.assertEqual(materialize.call_count, 1)
            name = "datasets/"+identity()["dataset_id"]+"/observations.jsonl"
            store.files[name] += b"{}\n"
            with self.assertRaises(rt.IntegrityError): backend.evaluate(1, identity(1))

    def test_fake_candidate_cannot_return_another_candidates_result(self):
        with self.assertRaisesRegex(rt.IntegrityError, "identity changed"):
            r.verify_evaluation(self.results[1], identity(), self.saved, self.checkout)


class SavedResultFiles(Sequence):
    """Fresh full JSON per access; class state holds paths, never a ledger cache."""
    def __init__(self, paths):
        self.paths = tuple(paths)

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, index):
        return v.strict_json(self.paths[index].read_bytes())


class SavedFixtureLifetimeTests(unittest.TestCase):
    def test_file_results_are_fresh_complete_and_never_cached(self):
        with tempfile.TemporaryDirectory(prefix="banto-v03-lifetime-fixture-") as name:
            paths = [Path(name)/f"{i}.json" for i in range(3)]
            expected = [{"candidate": i, "rows": [1, 2, 3]} for i in range(3)]
            for path, value in zip(paths, expected):
                path.write_bytes(m.json_bytes(value))
            files = SavedResultFiles(paths)
            self.assertEqual(list(files), expected)
            self.assertEqual(vars(files), {"paths": tuple(paths)})
            changed = files[0]
            changed["rows"].pop()
            self.assertEqual(files[0], expected[0])

    def test_failed_setup_releases_class_objects_without_GC(self):
        references = []
        class Payload:
            pass
        class Owner(unittest.TestCase):
            @classmethod
            def setUpClass(cls):
                cls.addClassCleanup(release_class_fields, cls, "payload")
                cls.payload = Payload()
                references.append(weakref.ref(cls.payload))
                raise RuntimeError("deliberate setup failure")
            def runTest(self):
                raise AssertionError("failed setup must not run a test")
        output = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.TestSuite([Owner()]))
        self.assertEqual(len(output.errors), 1)
        self.assertFalse("payload" in Owner.__dict__)
        self.assertIsNone(references[0]())


if __name__ == "__main__":
    unittest.main()
