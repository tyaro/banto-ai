"""Small IO-envelope checks, separate from independent numerical fixtures."""
import copy
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_saved_audit as reader
from banto_ai import anomaly_v03_engineering_contract as p
from banto_ai import anomaly_v03_materializer as m
from tests.test_anomaly_v03_engineering import complete_fixture, fixture_context, fixture_pair


def envelope():
    manifest = complete_fixture()
    producer, _ = fixture_context()
    files = {"planned.json": m.json_bytes(p.new_manifest("attempt")),
             "context.json": m.json_bytes({"source": manifest["source"], "runtime": manifest["runtime"]})}
    for row, dataset in zip(manifest["datasets"], fixture_pair(manifest["plan"]["identities"][0])):
        for entry, (_, raw) in zip(row["files"], dataset.entries):
            files[entry["path"]] = raw
    for i, slot in enumerate(manifest["slots"]):
        value = {"identity": slot["identity"], "input_hashes": slot["input_hashes"],
                 "events": v.event_inventory(slot["identity"]), "profiles": [{"status": "calibrated"}],
                 "provenance": {"producer_source": manifest["source"]}}
        path = slot["evaluation"]["path"]
        files[path] = m.json_bytes(value)
        slot["evaluation"] = p.file_record(path, files[path])
        files[f"journal/{i:02d}-started.json"] = m.json_bytes(slot["identity"])
        files[f"journal/{i:02d}-done.json"] = m.json_bytes(slot)
    manifest["resources"]["payload_bytes"] = sum(map(len, files.values()))
    files["manifest.json"] = m.json_bytes(manifest)
    return files, producer


class SavedAuditTests(unittest.TestCase):
    def setUp(self):
        self.schema = self.enterContext(patch.object(v, "validate_result_contract", return_value={"fixture": True}))
        self.numeric = self.enterContext(patch.object(reader.audit, "audit_evaluation", return_value={"status": "fixture"}))
        self.enterContext(patch.object(m, "materialize_pair", side_effect=AssertionError("generation forbidden")))

    def test_six_saved_slots_are_passed_in_order_without_generation(self):
        files, producer = envelope()
        before = copy.deepcopy(files)
        manifest, results = reader.audit_payloads(files, producer)
        self.assertEqual([r["identity"] for r in results], p.fixed_plan()["identities"])
        self.assertEqual((self.schema.call_count, self.numeric.call_count), (6, 6))
        self.assertEqual(files, before)
        self.assertEqual(manifest["state"], "complete")

    def test_changed_dataset_hash_stops_before_numerical_checks(self):
        files, producer = envelope()
        manifest = v.strict_json(files["manifest.json"])
        files[manifest["datasets"][0]["files"][0]["path"]] = b'{"changed":true}\n'
        with self.assertRaisesRegex(ValueError, "dataset hash"):
            reader.audit_payloads(files, producer)
        self.numeric.assert_not_called()

    def test_changed_evaluation_bytes_stops_before_numerical_checks(self):
        files, producer = envelope()
        name = v.strict_json(files["manifest.json"])["slots"][0]["evaluation"]["path"]
        files[name] = b'{}\n'
        with self.assertRaisesRegex(ValueError, "evaluation hash"):
            reader.audit_payloads(files, producer)
        self.numeric.assert_not_called()

    def test_numerical_failure_stops_remaining_slots(self):
        files, producer = envelope()
        self.numeric.side_effect = ValueError("bad matching")
        with self.assertRaisesRegex(ValueError, "bad matching"):
            reader.audit_payloads(files, producer)
        self.assertEqual(self.numeric.call_count, 1)

    def test_journal_and_extra_payload_are_rejected(self):
        for which in ("journal", "extra"):
            files, producer = envelope()
            files["journal/00-done.json" if which == "journal" else "unexpected.json"] = b'{}\n'
            with self.subTest(which=which), self.assertRaises(ValueError):
                reader.audit_payloads(files, producer)

    def test_invalid_completion_or_source_rejected_before_any_numerical_work(self):
        for which in ("state", "source"):
            files, producer = envelope()
            manifest = v.strict_json(files["manifest.json"])
            if which == "state":
                manifest.update(state="failed", failure={"stage": "publication", "reason": "exception"})
            else:
                manifest["source"]["revision"] = "b" * 40
            files["manifest.json"] = m.json_bytes(manifest)
            with self.subTest(which=which), self.assertRaises(ValueError):
                reader.audit_payloads(files, producer)
        self.numeric.assert_not_called()


if __name__ == "__main__":
    unittest.main()
