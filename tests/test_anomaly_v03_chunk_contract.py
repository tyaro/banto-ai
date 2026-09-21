"""Small chunk envelopes; numerical/schema mocks are explicit, no observations."""
import copy
import unittest
from unittest.mock import patch

from banto_ai import _anomaly_v03_contract as c
from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_checkpoints as checkpoints
from banto_ai import anomaly_v03_chunk_contract as chunk
from banto_ai import anomaly_v03_engineering_contract as legacy
from banto_ai import anomaly_v03_materializer as m
from banto_ai import anomaly_v03_saved_audit as reader
from tests.test_anomaly_v03_engineering import fixture_context, fixture_pair
from tests.test_anomaly_v03_saved_audit import envelope as legacy_envelope


def envelope(campaign, index, attempt=1):
    manifest = chunk.new_manifest(campaign, index, attempt)
    producer, manifest["runtime"] = fixture_context()
    manifest.update(source=producer.source_descriptor(), state="complete")
    files = {"planned.json": m.json_bytes(chunk.new_manifest(campaign, index, attempt)),
             "context.json": m.json_bytes({"source": manifest["source"], "runtime": manifest["runtime"]})}
    for row, dataset in zip(manifest["datasets"], fixture_pair(manifest["plan"]["identities"][0])):
        row["files"] = []
        for name, raw in dataset.entries:
            path = "datasets/" + row["identity"]["dataset_id"] + "/" + name
            files[path] = raw
            row["files"].append(legacy.file_record(path, raw))
    for i, slot in enumerate(manifest["slots"]):
        inputs = fixture_pair(slot["identity"])[c.STRATA.index(slot["identity"]["stratum"])].files()
        slot.update(status="success", input_hashes={key: m.sha(inputs[name]) for key, name in m.INPUT_FILES.items()})
        value = {"identity": slot["identity"], "input_hashes": slot["input_hashes"],
                 "events": v.event_inventory(slot["identity"]), "profiles": [{"status": "calibrated"}],
                 "provenance": {"producer_source": manifest["source"]}}
        path = "evaluations/" + slot["identity"]["evaluation_id"] + ".json"
        files[path] = m.json_bytes(value)
        slot["evaluation"] = legacy.file_record(path, files[path])
        files[f"journal/{i:02d}-started.json"] = m.json_bytes(slot["identity"])
        files[f"journal/{i:02d}-done.json"] = m.json_bytes(slot)
    manifest["resources"]["payload_bytes"] = sum(map(len, files.values()))
    legacy.refresh_coverage(manifest)
    files["manifest.json"] = m.json_bytes(manifest)
    return files, producer


class ChunkContractTests(unittest.TestCase):
    def setUp(self):
        self.campaign = checkpoints.fixed_plan("a" * 40, "b" * 40)
        self.enterContext(patch.object(m, "materialize_pair", side_effect=AssertionError("generation forbidden")))

    def test_all_registered_chunks_select_exactly_six_without_mutating_campaign(self):
        before = copy.deepcopy(self.campaign)
        identities = []
        roles = []
        for index in range(120):
            plan = chunk.chunk_plan(self.campaign, index, 1)
            self.assertEqual(plan["identities"], self.campaign["chunks"][index]["identities"])
            self.assertEqual(len(plan["identities"]), 6)
            self.assertFalse(plan["execution_authorized"] or plan["budgets_frozen"] or plan["formal_permission"])
            self.assertEqual(plan["limits_status"], "provisional_validation_caps")
            identities.extend(plan["identities"])
            roles.append(plan["binding"]["role"])
        self.assertEqual(identities, v.evaluation_inventory("dev") + v.evaluation_inventory("smoke"))
        self.assertEqual(roles, ["dev"] * 96 + ["smoke"] * 24)
        plan["identities"][0]["seed"] = -1
        plan["runtime_policy"].clear()
        self.assertEqual(self.campaign, before)

    def test_planned_and_complete_manifests_at_dev_smoke_boundaries_and_retry(self):
        for index in (0, 95, 96, 119):
            with self.subTest(index=index):
                report = chunk.validate_manifest(chunk.new_manifest(self.campaign, index, 2), self.campaign, index, 2)
                self.assertEqual(report["state"], "planned")
                files, _ = envelope(self.campaign, index, 2)
                report = chunk.validate_manifest(v.strict_json(files["manifest.json"]), self.campaign, index, 2)
                self.assertEqual(report["coverage"]["success"], 6)
                self.assertEqual(report["campaign_evaluations_credited"], 0)
                self.assertFalse(report["result_trusted"] or report["execution_authorized"])

    def test_invalid_selection_and_changed_campaign_rejected(self):
        for index in (True, 1.0, -1, 120):
            with self.subTest(index=index), self.assertRaises(ValueError):
                chunk.new_manifest(self.campaign, index, 1)
        for attempt in (True, 1.0, 0, checkpoints.MAX_RECORDS + 1):
            with self.subTest(attempt=attempt), self.assertRaises(ValueError):
                chunk.new_manifest(self.campaign, 0, attempt)
        for mutate in (lambda p: p["chunks"].reverse(),
                       lambda p: p["chunks"][0].update(role="holdout"),
                       lambda p: p["chunks"][0]["identities"][0].update(seed=-1)):
            campaign = copy.deepcopy(self.campaign)
            mutate(campaign)
            with self.assertRaises(ValueError):
                chunk.new_manifest(campaign, 0, 1)

    def test_external_chunk_attempt_and_campaign_pins_are_required(self):
        value = chunk.new_manifest(self.campaign, 96, 2)
        for index, attempt, campaign in ((95, 2, self.campaign), (96, 1, self.campaign),
                (96, 2, checkpoints.fixed_plan("a" * 40, "c" * 40))):
            with self.subTest(index=index, attempt=attempt), self.assertRaises(ValueError):
                chunk.validate_manifest(value, campaign, index, attempt)

    def test_old_and_new_formats_cannot_be_relabelled_even_for_chunk_zero(self):
        old = legacy.new_manifest("result")
        new = chunk.new_manifest(self.campaign, 0, 1)
        with self.assertRaises(ValueError):
            legacy.validate_manifest(new)
        with self.assertRaises(ValueError):
            chunk.validate_manifest(old, self.campaign, 0, 1)
        new["format"] = legacy.MANIFEST_FORMAT
        with self.assertRaises(ValueError):
            legacy.validate_manifest(new)
        self.assertEqual(legacy.validate_manifest(old)["state"], "planned")

    def test_completed_context_plan_order_input_and_budget_tampering_rejected(self):
        files, _ = envelope(self.campaign, 119)
        original = v.strict_json(files["manifest.json"])
        mutations = [lambda x: x["source"].update(revision="c" * 40),
            lambda x: x["runtime"].update(python_version="3.12.0"),
            lambda x: x.update(attempt_id="other"),
            lambda x: x["plan"].update(scope="holdout"),
            lambda x: x["plan"].update(budgets_frozen=True),
            lambda x: x["slots"].reverse(),
            lambda x: x["slots"][1]["input_hashes"].update(observations="0" * 64),
            lambda x: x["datasets"][0]["files"][0].update(path="datasets/other/file.json"),
            lambda x: x["coverage"].update(success=5),
            lambda x: x["resources"].update(elapsed_seconds=901)]
        for mutate in mutations:
            value = copy.deepcopy(original)
            mutate(value)
            with self.assertRaises(ValueError):
                chunk.validate_manifest(value, self.campaign, 119, 1)
        original["runtime"]["os_ubr"] = 9457
        self.assertEqual(chunk.validate_manifest(original, self.campaign, 119, 1)["state"], "complete")

    def test_inconclusive_and_failed_prefix_are_retained(self):
        files, _ = envelope(self.campaign, 96)
        value = v.strict_json(files["manifest.json"])
        value["slots"][1]["status"] = "inconclusive"
        legacy.refresh_coverage(value)
        self.assertEqual(chunk.validate_manifest(value, self.campaign, 96, 1)["coverage"]["inconclusive"], 1)
        value.update(state="failed", failure={"stage": "evaluation", "reason": "exception"})
        value["slots"][2].update(status="failed", evaluation=None)
        for slot in value["slots"][3:]:
            slot.update(status="not_started", input_hashes=None, evaluation=None)
        legacy.refresh_coverage(value)
        report = chunk.validate_manifest(value, self.campaign, 96, 1)
        self.assertEqual(report["coverage"], {"success": 1, "inconclusive": 1, "failed": 1, "not_started": 3})
        value["state"] = "complete"
        with self.assertRaises(ValueError):
            chunk.validate_manifest(value, self.campaign, 96, 1)


class ChunkPayloadTests(unittest.TestCase):
    def setUp(self):
        self.campaign = checkpoints.fixed_plan("a" * 40, "b" * 40)
        self.schema = self.enterContext(patch.object(v, "validate_result_contract", return_value={"fixture": True}))
        self.numeric = self.enterContext(patch.object(reader.audit, "audit_evaluation", return_value={"status": "fixture"}))
        self.enterContext(patch.object(m, "materialize_pair", side_effect=AssertionError("generation forbidden")))

    def test_six_saved_ledgers_in_order_for_each_boundary_without_generation(self):
        for index in (0, 95, 96, 119):
            files, producer = envelope(self.campaign, index, 2)
            before = copy.deepcopy(files)
            manifest, reports = chunk.audit_chunk_payloads(files, producer, self.campaign, index, 2)
            self.assertEqual([r["identity"] for r in reports], self.campaign["chunks"][index]["identities"])
            self.assertEqual(manifest["state"], "complete")
            self.assertEqual(files, before)
        self.assertEqual((self.schema.call_count, self.numeric.call_count), (24, 24))

    def test_legacy_reader_and_new_reader_reject_other_format(self):
        files, producer = envelope(self.campaign, 0)
        with self.assertRaises(ValueError):
            reader.audit_payloads(files, producer)
        files, producer = legacy_envelope()
        with self.assertRaises(ValueError):
            chunk.audit_chunk_payloads(files, producer, self.campaign, 0, 1)
        self.numeric.assert_not_called()

    def test_external_selection_and_noncomplete_rejected_before_numeric_work(self):
        files, producer = envelope(self.campaign, 96)
        with self.assertRaises(ValueError):
            chunk.audit_chunk_payloads(files, producer, self.campaign, 95, 1)
        manifest = v.strict_json(files["manifest.json"])
        manifest.update(state="failed", failure={"stage": "publication", "reason": "exception"})
        files["manifest.json"] = m.json_bytes(manifest)
        with self.assertRaisesRegex(ValueError, "only completed"):
            chunk.audit_chunk_payloads(files, producer, self.campaign, 96, 1)
        self.numeric.assert_not_called()

    def test_saved_bytes_and_context_or_journals_cannot_be_substituted(self):
        for which in ("dataset", "evaluation", "planned.json", "context.json", "journal/00-started.json",
                      "journal/00-done.json", "unexpected.json"):
            files, producer = envelope(self.campaign, 119)
            manifest = v.strict_json(files["manifest.json"])
            path = (manifest["datasets"][0]["files"][0]["path"] if which == "dataset" else
                    manifest["slots"][0]["evaluation"]["path"] if which == "evaluation" else which)
            files[path] = b'{}\n'
            with self.subTest(which=which), self.assertRaises(ValueError):
                chunk.audit_chunk_payloads(files, producer, self.campaign, 119, 1)

    def test_evaluation_semantics_bound_even_if_file_hash_updated(self):
        for field, replacement in (("identity", self.campaign["chunks"][95]["identities"][0]),
                                   ("events", []), ("input_hashes", {}),
                                   ("provenance", {"producer_source": {}})):
            files, producer = envelope(self.campaign, 96)
            manifest = v.strict_json(files["manifest.json"])
            slot = manifest["slots"][0]
            path = slot["evaluation"]["path"]
            evaluation = v.strict_json(files[path])
            evaluation[field] = replacement
            files[path] = m.json_bytes(evaluation)
            slot["evaluation"] = legacy.file_record(path, files[path])
            files["journal/00-done.json"] = m.json_bytes(slot)
            manifest["resources"]["payload_bytes"] = sum(len(raw) for name, raw in files.items() if name != "manifest.json")
            files["manifest.json"] = m.json_bytes(manifest)
            with self.subTest(field=field), self.assertRaises(ValueError):
                chunk.audit_chunk_payloads(files, producer, self.campaign, 96, 1)
        self.numeric.assert_not_called()

    def test_inconclusive_profile_remains_inconclusive(self):
        files, producer = envelope(self.campaign, 96)
        manifest = v.strict_json(files["manifest.json"])
        slot = manifest["slots"][1]
        path = slot["evaluation"]["path"]
        value = v.strict_json(files[path])
        value["profiles"][0]["status"] = "inconclusive"
        files[path] = m.json_bytes(value)
        slot.update(status="inconclusive", evaluation=legacy.file_record(path, files[path]))
        files["journal/01-done.json"] = m.json_bytes(slot)
        legacy.refresh_coverage(manifest)
        manifest["resources"]["payload_bytes"] = sum(len(raw) for name, raw in files.items() if name != "manifest.json")
        files["manifest.json"] = m.json_bytes(manifest)
        result, _ = chunk.audit_chunk_payloads(files, producer, self.campaign, 96, 1)
        self.assertEqual(result["coverage"]["inconclusive"], 1)

    def test_numerical_failure_stops_remaining_slots(self):
        files, producer = envelope(self.campaign, 119)
        self.numeric.side_effect = ValueError("bad matching")
        with self.assertRaisesRegex(ValueError, "bad matching"):
            chunk.audit_chunk_payloads(files, producer, self.campaign, 119, 1)
        self.assertEqual(self.numeric.call_count, 1)


if __name__ == "__main__":
    unittest.main()
