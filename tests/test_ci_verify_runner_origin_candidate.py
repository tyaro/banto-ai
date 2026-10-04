"""Synthetic, retained-byte tests for the candidate Ubuntu origin checker."""

from __future__ import annotations

import base64
import copy
import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from tests.test_ci_shared_fixtures import journal as fixture_journal
from tools import ci_verify_runner_origin_candidate as verifier
from tools import ci_verify_regression_journals as regression


def encoded(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def add_passing_case(rows: list[dict], test_id: str) -> None:
    planned_end = next(i for i, row in enumerate(rows) if row["event"] == "test_started")
    rows.insert(planned_end, {"event": "planned_test", "test_id": test_id})
    rows[-1:-1] = [
        {"event": "test_started", "test_id": test_id},
        {"event": "outcome", "test_id": test_id, "status": "pass"},
        {"event": "test_finished", "test_id": test_id, "outcomes": ["pass"]},
    ]
    rows[-1]["discovered"] += 1
    rows[-1]["tests_run"] += 1


def fixture(root: Path) -> dict:
    repo = "tyaro/banto-ai"
    run_id = "37230362806"
    head = "a" * 40
    version = "20260927.320.1"
    tag = "ubuntu24/20260927.320"
    run_url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}"
    run_html = f"https://github.com/{repo}/actions/runs/{run_id}"
    release_html = "https://github.com/actions/runner-images/releases/tag/" + tag
    readme_path = "images/ubuntu/Ubuntu2404-Readme.md"
    readme_html = "https://github.com/actions/runner-images/blob/" + tag + "/" + readme_path
    readme = (b"# Ubuntu 24.04\n- OS Version: 24.04.5 LTS\n"
              b"- Kernel Version: 6.17.0-1022-azure\n- Image Version: 20260927.320.1\n")
    blob = hashlib.sha1(b"blob " + str(len(readme)).encode() + b"\0" + readme).hexdigest()
    run = {
        "id": int(run_id), "run_attempt": 1, "head_sha": head, "head_commit": {"id": head},
        "path": ".github/workflows/ci.yml", "repository": {"full_name": repo},
        "head_repository": {"full_name": repo}, "url": run_url, "jobs_url": run_url + "/jobs",
        "html_url": run_html, "status": "completed", "conclusion": "success",
        "created_at": "2026-10-04T00:00:00Z", "run_started_at": "2026-10-04T00:00:00Z",
        "updated_at": "2026-10-04T00:05:00Z", "head_branch": "codex/example", "name": "Phase 1 CI",
    }
    jobs = []
    raw = {"run": encoded(run), "readme": readme}
    for key, job_id, created, started, finished in (
        ("3.12", "111518564307", "00:00:01", "00:00:02", "00:02:00"),
        ("3.14", "111518564200", "00:00:02", "00:00:03", "00:02:01"),
        ("compare", "111525197943", "00:02:02", "00:02:03", "00:04:00"),
    ):
        name = verifier.JOB_NAMES[key]
        job = {
            "id": int(job_id), "run_id": int(run_id), "run_attempt": 1, "name": name,
            "head_sha": head, "head_branch": run["head_branch"], "workflow_name": run["name"],
            "run_url": run_url, "url": f"https://api.github.com/repos/{repo}/actions/jobs/{job_id}",
            "check_run_url": f"https://api.github.com/repos/{repo}/check-runs/{job_id}",
            "html_url": run_html + f"/job/{job_id}", "status": "completed", "conclusion": "success",
            "labels": ["ubuntu-24.04"], "runner_group_name": "GitHub Actions",
            "runner_name": "GitHub Actions " + job_id,
            "created_at": "2026-10-04T" + created + "Z",
            "started_at": "2026-10-04T" + started + "Z",
            "completed_at": "2026-10-04T" + finished + "Z",
        }
        jobs.append(job)
        start = "2026-10-04T" + started + ".1000000Z"
        end = "2026-10-04T" + finished + ".0000000Z"
        payloads = [
            "##[group]Operating System", "Ubuntu", "24.04.5", "LTS", "##[endgroup]",
            "##[group]Runner Image", "Image: ubuntu-24.04", "Version: " + version,
            "Included Software: " + readme_html,
            "Image Release: " + release_html.replace("/ubuntu24/", "/ubuntu24%2F"),
            "##[endgroup]", "Complete job name: " + name,
            "  repository: " + repo,
            "[command]/usr/bin/git -c protocol.version=2 fetch +" + head +
            ":refs/remotes/origin/codex/example", head,
        ] + ["setup line " + str(i) for i in range(20)]
        log = "\n".join(start + " " + line for line in payloads) + "\n" + end + " Cleanup\n"
        raw["log_" + key] = log.encode("utf-8")
    raw["attempt_jobs"] = encoded({"total_count": 3, "jobs": jobs})
    raw["release"] = encoded({
        "id": 398506734, "tag_name": tag, "html_url": release_html,
        "url": "https://api.github.com/repos/actions/runner-images/releases/398506734",
        "target_commitish": "b" * 40, "draft": False, "prerelease": False,
        "published_at": "2026-09-28T18:18:10Z",
        "body": "# Ubuntu 24.04\n- Image Version: " + version + "\n",
    })
    raw["readme_metadata"] = encoded({
        "type": "file", "name": "Ubuntu2404-Readme.md", "path": readme_path,
        "html_url": readme_html,
        "url": "https://api.github.com/repos/actions/runner-images/contents/" +
        readme_path + "?ref=" + tag,
        "download_url": "https://raw.githubusercontent.com/actions/runner-images/" +
        tag + "/" + readme_path,
        "sha": blob, "git_url": "https://api.github.com/repos/actions/runner-images/git/blobs/" + blob,
        "encoding": "base64", "size": len(readme), "content": base64.b64encode(readme).decode("ascii"),
    })
    source = {"revision": head, "workflow_sha256": "c" * 64,
              "github_run_id": run_id, "github_run_attempt": "1"}
    for minor in ("3.12", "3.14"):
        rows = fixture_journal(minor)
        rows[0]["source"] = source
        rows[0]["started_utc"] = "2026-10-04T00:00:0" + ("3" if minor == "3.12" else "4") + "Z"
        rows[0]["runtime"]["kernel"] = "6.17.0-1022-azure"
        rows[0]["runtime"]["runner_image_version"] = version
        existing = {row["test_id"] for row in rows if row["event"] == "planned_test"}
        for test_id in sorted(regression.REQUIRED_TEST_IDS - existing):
            add_passing_case(rows, test_id)
        raw["journal_" + minor] = b"".join(encoded(row) for row in rows)
    pins = {
        "schema": verifier.SCHEMA, "repository": repo, "run_id": run_id, "run_attempt": "1",
        "head_sha": head, "workflow_sha256": "c" * 64,
        "job_ids": {"3.12": "111518564307", "3.14": "111518564200",
                    "compare": "111525197943"},
        "image": {"name": "ubuntu-24.04", "version": version, "tag": tag,
                  "release_id": "398506734", "release_target_commitish": "b" * 40,
                  "readme_blob_sha": blob},
        "files": {},
    }
    for role, content in raw.items():
        path = role.replace(".", "_") + ".raw"
        (root / path).write_bytes(content)
        pins["files"][role] = {"path": path, "bytes": len(content),
                               "sha256": hashlib.sha256(content).hexdigest()}
    return pins


class RunnerOriginCandidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pins = fixture(self.root)

    def repin(self, role: str, value: dict | bytes) -> None:
        content = value if type(value) is bytes else encoded(value)
        path = self.root / self.pins["files"][role]["path"]
        path.write_bytes(content)
        self.pins["files"][role]["bytes"] = len(content)
        self.pins["files"][role]["sha256"] = hashlib.sha256(content).hexdigest()

    def value(self, role: str) -> dict:
        return json.loads((self.root / self.pins["files"][role]["path"]).read_bytes())

    def rejected(self, code: str) -> None:
        with self.assertRaisesRegex(verifier.CandidateEvidenceError, code):
            verifier.verify_evidence(self.root, self.pins)

    def test_candidate_consistency_retains_preformal_scope(self) -> None:
        result = verifier.verify_evidence(self.root, self.pins)
        self.assertEqual(result["status"], "consistent_candidate")
        self.assertEqual(result["runner_image_digest_status"], "not_collected")
        self.assertEqual(result["acceptance_status"], "not_completed")
        self.assertIs(result["formal_permission"], False)
        self.assertEqual(result["full_journal_verification_status"], "passed")
        self.assertEqual(result["required_tests_per_minor"], len(regression.REQUIRED_TEST_IDS))
        self.assertEqual(set(result["job_ids"]), {"3.12", "3.14", "compare"})

    def test_raw_tamper_is_rejected_before_semantics(self) -> None:
        path = self.root / self.pins["files"]["log_compare"]["path"]
        path.write_bytes(path.read_bytes() + b"x")
        self.rejected("raw_pin_mismatch:log_compare")

    def test_changed_attempt_even_with_repin_is_rejected(self) -> None:
        run = self.value("run")
        run["run_attempt"] = 2
        self.repin("run", run)
        self.rejected("run_attempt_identity")

    def test_wrong_job_id_and_attempt_even_with_repin_are_rejected(self) -> None:
        response = self.value("attempt_jobs")
        response["jobs"][0]["id"] += 1
        self.repin("attempt_jobs", response)
        self.rejected("job_attempt_identity:3.12")
        response["jobs"][0]["id"] -= 1
        response["jobs"][0]["run_attempt"] = 2
        self.repin("attempt_jobs", response)
        self.rejected("job_attempt_identity:3.12")

    def test_missing_or_duplicate_job_is_rejected(self) -> None:
        response = self.value("attempt_jobs")
        response["jobs"][2] = copy.deepcopy(response["jobs"][1])
        self.repin("attempt_jobs", response)
        self.rejected("duplicate_or_invalid_job")

    def test_retagged_release_and_changed_readme_rejected(self) -> None:
        release = self.value("release")
        release["tag_name"] = "ubuntu24/other"
        self.repin("release", release)
        self.rejected("release_identity")
        release["tag_name"] = self.pins["image"]["tag"]
        self.repin("release", release)
        metadata = self.value("readme_metadata")
        metadata["content"] = base64.b64encode(b"changed").decode()
        self.repin("readme_metadata", metadata)
        self.rejected("readme_metadata_content")

    def test_replaced_comparison_log_and_image_header_rejected(self) -> None:
        other = (self.root / self.pins["files"]["log_3.12"]["path"]).read_bytes()
        self.repin("log_compare", other)
        self.rejected("job_log_window:compare")
        original = fixture(self.root)
        self.pins = original
        content = (self.root / self.pins["files"]["log_3.12"]["path"]).read_bytes()
        self.repin("log_3.12", content.replace(b"Version: 20260927.320.1",
                                              b"Version: 20260927.320.2"))
        self.rejected("job_log_image:3.12")

    def test_repinning_middle_image_line_with_future_timestamp_is_rejected(self) -> None:
        path = self.root / self.pins["files"]["log_3.12"]["path"]
        raw = path.read_bytes()
        old = b"2026-10-04T00:00:02.1000000Z Version: 20260927.320.1"
        self.assertEqual(raw.count(old), 1)
        self.repin("log_3.12", raw.replace(old,
                    b"2099-01-01T00:00:02.1000000Z Version: 20260927.320.1"))
        self.rejected("job_log_timestamp_window:3.12")

    def test_repinning_middle_image_line_with_backward_timestamp_is_rejected(self) -> None:
        path = self.root / self.pins["files"]["log_3.12"]["path"]
        raw = path.read_bytes()
        old = b"2026-10-04T00:00:02.1000000Z Version: 20260927.320.1"
        self.assertEqual(raw.count(old), 1)
        self.repin("log_3.12", raw.replace(old,
                    b"2026-10-04T00:00:02.0500000Z Version: 20260927.320.1"))
        self.rejected("job_log_timestamp_order:3.12")

    def test_journal_source_and_digest_claim_rejected(self) -> None:
        path = self.root / self.pins["files"]["journal_3.14"]["path"]
        rows = [json.loads(x) for x in path.read_bytes().splitlines()]
        rows[0]["source"]["github_run_attempt"] = "2"
        self.repin("journal_3.14", b"".join(encoded(row) for row in rows))
        self.rejected("journal_source:3.14")
        rows[0]["source"]["github_run_attempt"] = "1"
        rows[0]["runtime"]["runner_image_digest_status"] = "collected"
        self.repin("journal_3.14", b"".join(encoded(row) for row in rows))
        self.rejected("journal_runtime:3.14")

    def test_repinning_middle_required_failure_cannot_pass(self) -> None:
        path = self.root / self.pins["files"]["journal_3.14"]["path"]
        rows = [json.loads(x) for x in path.read_bytes().splitlines()]
        required = next(test_id for test_id in regression.REQUIRED_TEST_IDS if
                        any(row.get("test_id") == test_id and row.get("event") == "outcome"
                            for row in rows))
        outcome = next(row for row in rows if row.get("event") == "outcome" and
                       row.get("test_id") == required)
        outcome["status"] = "skip"
        outcome["reason"] = "forged skip"
        outcome["subtest"] = False
        finished = next(row for row in rows if row.get("event") == "test_finished" and
                        row.get("test_id") == required)
        finished["outcomes"] = ["skip"]
        self.repin("journal_3.14", b"".join(encoded(row) for row in rows))
        self.rejected("full_journal_verification:")

    def test_repinning_middle_forged_fail_is_cli_rejected(self) -> None:
        path = self.root / self.pins["files"]["journal_3.14"]["path"]
        rows = [json.loads(x) for x in path.read_bytes().splitlines()]
        middle = next(row for row in rows[1:-1] if row.get("event") == "outcome")
        middle["status"] = "fail"
        self.repin("journal_3.14", b"".join(encoded(row) for row in rows))
        pins_path = self.root / "pins.json"
        raw_pins = encoded(self.pins)
        pins_path.write_bytes(raw_pins)
        with redirect_stdout(io.StringIO()) as output:
            code = verifier.main(["--evidence-root", str(self.root),
                                  "--pins", str(pins_path),
                                  "--pins-sha256", hashlib.sha256(raw_pins).hexdigest()])
        self.assertEqual(code, 1)
        self.assertIn('"status": "rejected"', output.getvalue())
        self.assertIn("full_journal_verification:test_not_successful", output.getvalue())

    def test_journal_changed_between_raw_pin_and_full_parse_is_rejected(self) -> None:
        full_verify = verifier.regression.verify

        def changed_before_full(paths, *args):
            path = paths["3.12"]
            before = path.read_bytes()
            self.assertIn(b'"elapsed_seconds":0.0', before)
            path.write_bytes(before.replace(b'"elapsed_seconds":0.0',
                                            b'"elapsed_seconds":1.0', 1))
            return full_verify(paths, *args)

        with patch.object(verifier.regression, "verify", side_effect=changed_before_full):
            self.rejected("full_journal_pin_mismatch:3.12")

    def test_path_escape_and_external_pin_hash_rejected(self) -> None:
        self.pins["files"]["run"]["path"] = "../run.json"
        self.rejected("evidence_path_escape")
        self.pins = fixture(self.root)
        pins_path = self.root / "pins.json"
        pins_path.write_bytes(encoded(self.pins))
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(verifier.main(["--evidence-root", str(self.root), "--pins", str(pins_path),
                                            "--pins-sha256", "0" * 64]), 1)
        self.assertIn('"status": "rejected"', output.getvalue())

    def test_cli_succeeds_only_with_external_pins_hash(self) -> None:
        pins_path = self.root / "pins.json"
        raw = encoded(self.pins)
        pins_path.write_bytes(raw)
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(verifier.main(["--evidence-root", str(self.root), "--pins", str(pins_path),
                                            "--pins-sha256", hashlib.sha256(raw).hexdigest()]), 0)
        self.assertIn('"status":"consistent_candidate"', output.getvalue())


if __name__ == "__main__":
    unittest.main()
