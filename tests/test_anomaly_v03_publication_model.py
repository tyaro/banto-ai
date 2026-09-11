"""Pure B2 protocol attacks; no native operation or campaign run."""

import hashlib
import json
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import _anomaly_v03_runtime as runtime
from tests.fixtures import anomaly_v03_publication_model as model

REVISION = "a" * 40
FILES = {"facts.json": b'{"count":20}\n', "summary.md": b"20 planned incidents\n"}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def journal():
    return model.PublicationJournal(digest(model.marker_bytes(REVISION, FILES)))


def through(j, steps):
    for step in steps:
        j.begin(step)
        j.succeed(step)


class MarkerModelTests(unittest.TestCase):
    def verify(self, raw, files=None, *, pin=None, revision=REVISION):
        return model.verify_marker(raw, expected_marker_sha256=pin or digest(raw),
                                   source_revision=revision, files=FILES if files is None else files)

    def test_hand_inventory_and_external_pin_without_acceptance(self):
        raw = model.marker_bytes(REVISION, FILES)
        row = json.loads(raw)
        self.assertEqual(row["payload_inventory"], [
            {"path": "facts.json", "byte_count": 13, "raw_sha256": digest(b'{"count":20}\n')},
            {"path": "summary.md", "byte_count": 21, "raw_sha256": digest(b"20 planned incidents\n")},
        ])
        self.assertNotIn("marker_sha256", row)
        self.assertEqual(row["inventory_sha256"], digest(v.canonical_json(row["payload_inventory"])))
        result = self.verify(raw)
        self.assertTrue(result["marker_verified"])
        self.assertEqual(result["semantic_verification"], "not_performed")
        self.assertEqual(result["acceptance_status"], "not_completed")
        self.assertIs(result["formal_permission"], False)
        self.assertIs(result["execution_authenticated"], False)
        self.assertEqual(raw, model.marker_bytes(REVISION, dict(reversed(list(FILES.items())))))

    def test_fresh_payload_missing_extra_changed_and_source_rejected(self):
        raw = model.marker_bytes(REVISION, FILES)
        for files in ({"facts.json": FILES["facts.json"]}, {**FILES, "extra.txt": b"extra\n"},
                      {**FILES, "summary.md": b"19 planned incidents\n"}):
            with self.subTest(files=list(files)), self.assertRaises(model.ModelError):
                self.verify(raw, files)
        with self.assertRaises(model.ModelError):
            self.verify(raw, revision="b" * 40)

    def test_coordinated_marker_rehash_cannot_replace_external_pin(self):
        original = model.marker_bytes(REVISION, FILES)
        changed = {"facts.json": b'{"count":19}\n', "summary.md": b"19 planned incidents\n"}
        forged = model.marker_bytes(REVISION, changed)
        with self.assertRaises(model.ModelError):
            self.verify(forged, changed, pin=digest(original))
        # Replacing trusted inputs AND their pin requires semantic verification.
        result = self.verify(forged, changed)
        self.assertEqual(result["semantic_verification"], "not_performed")
        self.assertIs(result["formal_permission"], False)

    def test_rehashed_wrong_shape_format_and_acceptance_claim_rejected(self):
        raw = model.marker_bytes(REVISION, FILES)
        changed = json.loads(raw)
        changed["formal_permission"] = True
        self_ref = json.loads(raw)
        self_ref["payload_inventory"].append({"path": ".complete", "byte_count": len(raw), "raw_sha256": digest(raw)})
        cases = [raw[:-1], raw.replace(b"\n", b"\r\n"), b" " + raw, b"{}\n", b"[]\n",
                 b'{"x":1,"x":2}\n', b'{"x":NaN}\n', b'{"x":1e999}\n',
                 v.canonical_json(changed) + b"\n", v.canonical_json(self_ref) + b"\n"]
        for value in cases:
            with self.subTest(raw=value[:35]), self.assertRaises(model.ModelError):
                self.verify(value)

    def test_unsafe_paths_and_file_directory_aliases_rejected(self):
        for name in ("../escape", "/absolute", "C:/path", "C:stream", "a\\b", "a//b", "a/../b",
                     "a/NUL.txt", "a/b.", "a/b ", ".complete", "x" * 129, "a/\ud800"):
            with self.subTest(name=repr(name)), self.assertRaises(model.ModelError):
                model.marker_bytes(REVISION, {name: b"x"})
        for files in ({"Facts.json": b"x", "facts.json": b"y"},
                      {"a": b"x", "a/b": b"y"}, {"A": b"x", "a/b": b"y"},
                      {"A/x": b"x", "a/y": b"y"}, {"a/B/x": b"x", "a/b/y": b"y"}):
            with self.subTest(files=files), self.assertRaises(model.ModelError):
                model.marker_bytes(REVISION, files)
        model.marker_bytes(REVISION, {"A/x": b"x", "A/y": b"y"})

    def test_input_types_and_limits_before_hashing(self):
        bad = [{}, {str(i): b"" for i in range(9)}, {"x": b"x" * (model.MAX_FILE_BYTES + 1)},
               {str(i): b"x" * model.MAX_FILE_BYTES for i in range(5)}, {1: b"x"}, {"x": bytearray(b"x")},
               {"x": "text"}, list(FILES.items())]
        with patch.object(model.hashlib, "sha256", side_effect=AssertionError("must reject before hashing")):
            for value in bad:
                with self.subTest(type=type(value).__name__), self.assertRaises(model.ModelError):
                    model.marker_bytes(REVISION, value)
        model.marker_bytes(REVISION, {str(i): b"x" * model.MAX_FILE_BYTES for i in range(4)})
        model.marker_bytes(REVISION, {str(i): b"" for i in range(8)})
        with patch.object(model, "marker_bytes", side_effect=AssertionError("must reject before reconstruction")):
            for raw, pin in ((b"", "a" * 64), (b"x" * (model.MAX_MARKER_BYTES + 1), "a" * 64),
                             (bytearray(b"x"), "a" * 64), (b"x", True), (b"x", "A" * 64)):
                with self.assertRaises(model.ModelError):
                    model.verify_marker(raw, expected_marker_sha256=pin, source_revision=REVISION, files=FILES)

    def test_digest_types_and_resource_error_are_not_suppressed(self):
        for value in (True, 1, None, "A" * 40, "a" * 39):
            with self.assertRaises(model.ModelError):
                model.marker_bytes(value, FILES)
        for value in (True, 1, None, "A" * 64, "a" * 63):
            with self.assertRaises(model.ModelError):
                model.PublicationJournal(value)
        with patch.object(model.hashlib, "sha256", side_effect=MemoryError), self.assertRaises(MemoryError):
            model.marker_bytes(REVISION, FILES)


class PublicationJournalTests(unittest.TestCase):
    def assert_closed(self, result):
        self.assertEqual(result["acceptance_status"], "not_completed")
        for key in ("retry_permitted", "cleanup_permitted", "formal_permission", "execution_authenticated"):
            self.assertIs(result[key], False)

    def test_complete_requires_ordered_commit_and_successful_teardown(self):
        j = journal()
        self.assertEqual(j.snapshot()["model_status"], "not_started")
        through(j, ("prepare", "verify_prepared", "seal_payload", "rename_payload", "verify_final"))
        self.assertEqual(j.snapshot()["commit_observation"], "not_started")
        j.begin("commit_marker")
        self.assertEqual(j.snapshot()["commit_observation"], "unknown")
        j.succeed("commit_marker")
        self.assertEqual(j.snapshot()["model_status"], "awaiting_teardown")
        j.finish_teardown(success=True)
        result = j.snapshot()
        self.assertEqual(result["model_status"], "complete")
        self.assertEqual(result["commit_observation"], "confirmed")
        self.assertEqual([r["state"] for r in result["steps"]], ["succeeded"] * 6)
        self.assert_closed(result)

    def test_fault_at_each_operation_retains_prior_and_future_slots(self):
        expected = ("unknown", "failed", "unknown", "unknown", "failed", "unknown")
        for index, step in enumerate(model.STEPS):
            for resource in (False, True):
                with self.subTest(step=step, resource=resource):
                    j = journal()
                    through(j, model.STEPS[:index])
                    j.begin(step)
                    j.fail(resource=resource)
                    j.finish_teardown(success=True)
                    result = j.snapshot()
                    self.assertEqual([r["state"] for r in result["steps"]],
                                     ["succeeded"] * index + [expected[index]] + ["not_started"] * (5 - index))
                    self.assertEqual(result["model_status"], "stopped")
                    self.assertIs(result["resource_stop"], resource)
                    self.assertEqual(result["commit_observation"], "unknown" if index == 5 else "not_started")
                    self.assert_closed(result)
                    with self.assertRaises(model.ModelError): j.succeed(step)
                    with self.assertRaises(model.ModelError): j.begin(step)
                    self.assertEqual(j.snapshot()["steps"], result["steps"])

    def test_swallowed_protocol_errors_cannot_resume_or_report_complete(self):
        actions = (lambda j: j.begin("commit_marker"), lambda j: j.succeed("prepare"),
                   lambda j: j.finish_teardown(success=True), lambda j: j.fail(),
                   lambda j: j.begin(True), lambda j: j.stop(resource=1))
        for action in actions:
            j = journal()
            with self.assertRaises(model.ModelError): action(j)
            with self.assertRaises(model.ModelError): j.begin("prepare")
            j.finish_teardown(success=True)
            self.assertEqual(j.snapshot()["model_status"], "stopped")
            self.assertEqual(j.snapshot()["failure_reason"], "protocol_error")
            self.assert_closed(j.snapshot())

    def test_double_start_wrong_success_and_early_teardown_preserve_uncertainty(self):
        actions = (lambda j: j.begin("prepare"), lambda j: j.succeed("verify_prepared"),
                   lambda j: j.finish_teardown(success=True), lambda j: j.fail(resource=1))
        for action in actions:
            j = journal()
            j.begin("prepare")
            with self.assertRaises(model.ModelError): action(j)
            self.assertEqual(j.snapshot()["steps"][0]["state"], "unknown")
            self.assertEqual(j.snapshot()["model_status"], "stopped")

    def test_commit_response_loss_never_becomes_absent_or_confirmed(self):
        j = journal()
        through(j, model.STEPS[:-1])
        j.begin("commit_marker")
        j.fail()
        with self.assertRaises(model.ModelError): j.succeed("commit_marker")
        j.finish_teardown(success=False)
        self.assertEqual(j.snapshot()["commit_observation"], "unknown")
        self.assertEqual(j.snapshot()["failure_reason"], "operation_error")
        self.assertEqual(j.snapshot()["teardown"], "failed")

    def test_commit_success_survives_teardown_failure_and_late_resource_stop(self):
        for resource in (False, True):
            j = journal()
            through(j, model.STEPS)
            if resource: j.stop(resource=True)
            j.finish_teardown(success=False)
            result = j.snapshot()
            self.assertEqual(result["commit_observation"], "confirmed")
            self.assertEqual(result["model_status"], "stopped")
            self.assertEqual(result["failure_reason"], "resource_stop" if resource else "teardown_error")
            self.assert_closed(result)

    def test_between_step_resource_stop_preserves_first_cause_and_no_retry(self):
        j = journal()
        through(j, ("prepare",))
        j.stop()
        j.stop(resource=True)
        j.stop()
        self.assertEqual(j.snapshot()["failure_reason"], "operation_error")
        self.assertIs(j.snapshot()["resource_stop"], True)
        self.assertEqual([r["state"] for r in j.snapshot()["steps"]], ["succeeded"] + ["not_started"] * 5)
        j.finish_teardown(success=True)
        with self.assertRaises(model.ModelError): j.begin("verify_prepared")

    def test_snapshot_is_detached_and_completed_attempt_cannot_be_reused(self):
        j = journal()
        result = j.snapshot()
        result["steps"][0]["state"] = "succeeded"
        result["steps"].clear()
        result["formal_permission"] = True
        self.assertEqual(len(j.snapshot()["steps"]), 6)
        through(j, model.STEPS)
        j.finish_teardown(success=True)
        for action in (lambda: j.begin("prepare"), lambda: j.succeed("commit_marker"),
                       lambda: j.finish_teardown(success=True)):
            with self.assertRaises(model.ModelError): action()
        self.assertEqual(j.snapshot()["model_status"], "stopped")
        self.assertEqual(j.snapshot()["commit_observation"], "confirmed")
        self.assert_closed(j.snapshot())

    def test_bool_teardown_is_required_and_no_operation_is_performed(self):
        j = journal()
        with patch("builtins.open", side_effect=AssertionError("unexpected I/O")), \
             patch("os.mkdir", side_effect=AssertionError("unexpected mutation")), \
             patch("subprocess.Popen", side_effect=AssertionError("unexpected child")):
            raw = model.marker_bytes(REVISION, FILES)
            model.verify_marker(raw, expected_marker_sha256=digest(raw), source_revision=REVISION, files=FILES)
            through(j, model.STEPS)
            with self.assertRaises(model.ModelError): j.finish_teardown(success=1)
            self.assertEqual(j.snapshot()["model_status"], "stopped")
        with self.assertRaisesRegex(runtime.IntegrityError, "s4_acceptance_not_frozen"):
            runtime.require_campaign_acceptance()
