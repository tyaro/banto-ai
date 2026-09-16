"""Attempt metadata contract fixtures. No observed datasets or workers."""
import copy
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_attempt_descriptor as a
from banto_ai import anomaly_v03_checkpoints as p
from tests.test_anomaly_v03_checkpoints import JournalFixture, load_cli


def pins(f):
    return {"expected_plan_sha256": f.plan_hash, "expected_record_count": len(f.records), "expected_head_sha256": f.head}


def artifacts(f, *, audit_supervision=False):
    layout = a.describe_layout(f.plan, f.records, **pins(f))["layout"]
    record = f.records[-1]
    files = {}
    for role in a.ROLES:
        digest = ("f" * 64 if audit_supervision else None) if role == "audit_supervision" else record["evidence"][a.JOURNAL_EVIDENCE[role]]
        files[role] = {"path": layout["files"][role], "sha256": digest, "bytes": 123} if digest is not None else None
    return files


def complete_descriptor(f):
    observed = copy.deepcopy(f.context["runtime"])
    return a.new_descriptor(f.plan, f.records, artifacts(f, audit_supervision=True),
        audit_runtime={"before": observed, "after": copy.deepcopy(observed)}, **pins(f))


class DescriptorTests(unittest.TestCase):
    def setUp(self):
        self.f = JournalFixture()

    def validate(self, value, **overrides):
        return a.validate_descriptor(value, self.f.plan, self.f.records, **(pins(self.f) | overrides))

    def test_unstarted_journal_has_no_attempt_or_descriptor(self):
        with self.assertRaisesRegex(ValueError, "started journal"):
            a.describe_layout(self.f.plan, self.f.records, **pins(self.f))

    def test_running_and_marker_only_preserve_missing_evidence_and_never_grant_permission(self):
        self.f.add("running")
        value = a.new_descriptor(self.f.plan, self.f.records, artifacts(self.f), **pins(self.f))
        self.assertEqual(self.validate(value)["missing_for_verified_declaration"], list(a.ROLES))
        self.f.add("saved_pending_verification", evidence={"marker_sha256": "c" * 64,
            "supervision_sha256": None, "audit_sha256": None})
        value = a.new_descriptor(self.f.plan, self.f.records, artifacts(self.f), **pins(self.f))
        result = self.validate(value)
        self.assertEqual(result["artifact_roles_present"], ["marker"])
        for flag in ("artifact_bytes_verified", "filesystem_containment_verified", "execution_authorized",
                     "resume_authorized", "campaign_completed", "formal_permission", "independent_s6_complete"):
            self.assertIs(result[flag], False)
        self.assertEqual(result["campaign_evaluations_credited"], 0)

    def test_verified_and_inconclusive_need_all_evidence_and_preserve_outcomes(self):
        for inconclusive in (False, True):
            fixture = JournalFixture()
            fixture.complete(inconclusive=inconclusive)
            value = complete_descriptor(fixture)
            result = a.validate_descriptor(value, fixture.plan, fixture.records, **pins(fixture))
            self.assertEqual(result["missing_for_verified_declaration"], [])
            self.assertEqual(value["outcome"], fixture.records[-1]["outcome"])
            self.assertEqual(result["state"], "verified_inconclusive" if inconclusive else "verified_complete")
            for role in a.ROLES:
                bad = copy.deepcopy(value)
                bad["artifacts"][role] = None
                with self.assertRaises(ValueError):
                    a.validate_descriptor(bad, fixture.plan, fixture.records, **pins(fixture))

    def test_failure_before_marker_keeps_supervision_and_retry_cannot_reuse_old_artifact_paths(self):
        self.f.add("running")
        self.f.add("failed", reason="worker_exit", evidence={"marker_sha256": None,
            "supervision_sha256": "d" * 64, "audit_sha256": None})
        value = a.new_descriptor(self.f.plan, self.f.records, artifacts(self.f), **pins(self.f))
        self.assertEqual(self.validate(value)["artifact_roles_present"], ["producer_supervision"])
        self.f.complete(attempt=2)
        next_value = complete_descriptor(self.f)
        self.assertIn("attempt-0002", next_value["layout"]["result_root"])
        next_value["artifacts"]["producer_supervision"] = value["artifacts"]["producer_supervision"]
        with self.assertRaisesRegex(ValueError, "path/role"):
            self.validate(next_value)

    def test_failed_audit_without_report_can_retain_monitor_even_if_runtime_unavailable(self):
        self.f.add("running")
        self.f.add("failed", reason="worker_exit")
        files = artifacts(self.f, audit_supervision=True)
        value = a.new_descriptor(self.f.plan, self.f.records, files, **pins(self.f))
        self.assertEqual(self.validate(value)["artifact_roles_present"], ["audit_supervision"])

    def test_audit_runtime_may_differ_from_producer_but_change_within_audit_blocks(self):
        self.f.complete()
        value = complete_descriptor(self.f)
        for snapshot in ("before", "after"):
            value["audit_runtime"][snapshot]["os_ubr"] += 1
        self.assertEqual(self.validate(value)["state"], "verified_complete")
        value["audit_runtime"]["after"]["os_ubr"] += 1
        with self.assertRaises(ValueError):
            self.validate(value)
        self.f = JournalFixture()
        self.f.add("running")
        self.f.add("blocked_integrity", reason="runtime_changed")
        value = a.new_descriptor(self.f.plan, self.f.records, artifacts(self.f, audit_supervision=True),
            audit_runtime={"before": self.f.context["runtime"], "after": self.f.context["runtime"] | {"os_ubr": 9446}},
            **pins(self.f))
        self.assertEqual(self.validate(value)["state"], "blocked_integrity")

    def test_invalid_audit_runtime_types_and_incomplete_verified_runtime_rejected(self):
        self.f.complete()
        original = complete_descriptor(self.f)
        for change in (lambda x: x.update(audit_runtime=None), lambda x: x["audit_runtime"].update(after=None),
                       lambda x: x["audit_runtime"]["before"].update(os_ubr=True),
                       lambda x: x["audit_runtime"]["before"].update(python_version="3.12.0")):
            value = copy.deepcopy(original)
            change(value)
            with self.assertRaises(ValueError):
                self.validate(value)

    def test_record_context_identity_order_and_literal_flags_are_bound_exactly(self):
        self.f.complete(inconclusive=True)
        original = complete_descriptor(self.f)
        changes = [lambda x: x["record"].update(attempt=True), lambda x: x["record"].update(sequence=3.0),
            lambda x: x["context"]["source_bindings"].update(producer_revision="0" * 40),
            lambda x: x["context"]["runtime"].update(os_ubr=9999), lambda x: x["identities"].reverse(),
            lambda x: x["outcome"]["slots"][1].update(status="success"),
            lambda x: x.update(scope="historical-six-cell-trial-only"),
            lambda x: x.update(formal_permission=True), lambda x: x.update(resume_authorized=0),
            lambda x: x.update(independent_s6_complete=True), lambda x: x.update(extra="unbound")]
        for change in changes:
            value = copy.deepcopy(original)
            change(value)
            with self.assertRaises(ValueError):
                self.validate(value)

    def test_exact_paths_reject_escape_aliases_and_cross_role_reuse(self):
        self.f.complete()
        original = complete_descriptor(self.f)
        for bad in ("../escape/.complete", "C:/trial/.complete", "chunks/001/attempt-0001/result/.complete",
                    "chunks/000/attempt-0002/result/.complete", "chunks\\000\\attempt-0001\\result\\.complete",
                    "chunks/000/attempt-0001/result/../result/.complete", "chunks/000/attempt-0001/producer-control/supervision.json"):
            value = copy.deepcopy(original)
            value["artifacts"]["marker"]["path"] = bad
            with self.assertRaises(ValueError):
                self.validate(value)
        value = copy.deepcopy(original)
        value["layout"]["result_root"] = "outside"
        with self.assertRaises(ValueError):
            self.validate(value)

    def test_hash_size_role_inventory_and_unrecorded_evidence_rejected(self):
        self.f.complete()
        original = complete_descriptor(self.f)
        changes = [lambda f: f["marker"].update(sha256="0" * 64), lambda f: f["marker"].update(bytes=True),
            lambda f: f["marker"].update(bytes=0), lambda f: f["marker"].update(bytes=-1),
            lambda f: f["audit_supervision"].update(sha256="F" * 64), lambda f: f.pop("audit_report"),
            lambda f: f.update(extra=None), lambda f: f["audit_report"].update(extra=True)]
        for change in changes:
            value = copy.deepcopy(original)
            change(value["artifacts"])
            with self.assertRaises(ValueError):
                self.validate(value)
        self.f = JournalFixture()
        self.f.add("running")
        with self.assertRaises(ValueError):
            a.new_descriptor(self.f.plan, self.f.records, original["artifacts"], **pins(self.f))

    def test_external_snapshot_pins_prevent_stale_descriptor_and_truncated_or_forged_history(self):
        self.f.complete()
        value = complete_descriptor(self.f)
        for override in ({"expected_head_sha256": "0" * 64}, {"expected_record_count": 2},
                         {"expected_plan_sha256": "f" * 64}):
            with self.assertRaises(ValueError):
                self.validate(value, **override)
        self.f.add("running", chunk=1)
        with self.assertRaises(ValueError):
            self.validate(value)

    def test_paths_cover_dev_smoke_boundaries_and_last_chunk_without_generating_observations(self):
        for chunk in range(120):
            self.f.complete(chunk=chunk)
            if chunk in (0, 95, 96, 119):
                value = complete_descriptor(self.f)
                result = self.validate(value)
                self.assertEqual(result["chunk_index"], chunk)
                self.assertEqual(value["identities"], self.f.plan["chunks"][chunk]["identities"])
                self.assertTrue(value["layout"]["descriptor_path"].endswith(f"/{(chunk+1)*3:06d}.json"))


class CliTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="banto-attempt-descriptor-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.f = JournalFixture()
        self.f.complete()
        self.value = complete_descriptor(self.f)
        self.cli = load_cli()
        (self.root / "journal").mkdir()
        (self.root / "plan.json").write_bytes(v.canonical_json(self.f.plan))
        for index, record in enumerate(self.f.records, 1):
            (self.root / f"journal/{index:06d}.json").write_bytes(p.encode_record(record))
        self.raw = v.canonical_json(self.value) + b"\n"
        (self.root / "descriptor.json").write_bytes(self.raw)
        self.common = ["--plan", str(self.root / "plan.json"), "--plan-sha256", self.f.plan_hash,
            "--journal-dir", str(self.root / "journal"), "--record-count", "3", "--head-sha256", self.f.head]
        self.args = ["attempt-validate", *self.common, "--descriptor", str(self.root / "descriptor.json"),
                     "--descriptor-sha256", self.cli.storage.sha(self.raw)]

    def test_cli_layout_and_validation_read_only_with_no_attempt_tree(self):
        before = {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(self.cli.main(["attempt-layout", *self.common]), 0)
        self.assertEqual(v.strict_json(output.getvalue())["layout"], self.value["layout"])
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(self.cli.main(self.args), 0)
        report = v.strict_json(output.getvalue())
        self.assertEqual(report["status"], "attempt_descriptor_metadata_valid")
        self.assertFalse(report["artifact_bytes_verified"])
        self.assertFalse((self.root / "chunks").exists())
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_bad_external_descriptor_hash_and_oversize_input_return_exit_two(self):
        args = self.args[:-1] + ["0" * 64]
        with redirect_stderr(io.StringIO()) as error:
            self.assertEqual(self.cli.main(args), 2)
        self.assertIn("hash mismatch", error.getvalue())
        (self.root / "descriptor.json").write_bytes(b" " * (64 * 1024 + 1))
        with redirect_stderr(io.StringIO()) as error:
            self.assertEqual(self.cli.main(self.args), 2)
        self.assertIn("metadata file too large", error.getvalue())

    def test_journal_or_descriptor_change_during_validation_is_rejected(self):
        original = a.validate_descriptor
        for changed in ("journal/000003.json", "descriptor.json"):
            path = self.root / changed
            before = path.read_bytes()
            def mutate(*args, **kwargs):
                report = original(*args, **kwargs)
                path.write_bytes(before + b" ")
                return report
            with patch.object(a, "validate_descriptor", side_effect=mutate), redirect_stderr(io.StringIO()):
                self.assertEqual(self.cli.main(self.args), 2)
            path.write_bytes(before)


if __name__ == "__main__":
    unittest.main()
