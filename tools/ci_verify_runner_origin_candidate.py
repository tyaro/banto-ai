"""Read-only candidate provenance check for saved GitHub-hosted Ubuntu CI evidence.

The caller must supply a separately recorded SHA-256 of the pins file. This
checks consistency of retained API responses, raw job logs, tagged runner image
documents, and unittest journals. It does not obtain a VM image digest,
authenticate the GitHub API transport, or grant formal S4 acceptance.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import re
import stat
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import ci_compare_fixtures as ci_compare
from tools import ci_test_report as ci_report
from tools import ci_verify_regression_journals as regression

SCHEMA = "ci-runner-origin-candidate-pins-v1"
ROLES = (
    "run", "attempt_jobs", "release", "readme_metadata", "readme",
    "log_3.12", "log_3.14", "log_compare", "journal_3.12", "journal_3.14",
)
JOB_NAMES = {"3.12": "test (3.12)", "3.14": "test (3.14)",
             "compare": "compare-shared-fixtures"}
MAX_BYTES = {role: (ci_report.MAX_REPORT_BYTES if role.startswith("journal_") else
                    4 * 1024 * 1024 if role.startswith("log_") else
                    256 * 1024)
             for role in ROLES}
MAX_BYTES["readme"] = 512 * 1024
MAX_PINS_BYTES = 32 * 1024
HEX40 = re.compile(r"[a-f0-9]{40}\Z")
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
POSITIVE_ID = re.compile(r"[1-9][0-9]{0,19}\Z")
IMAGE_VERSION = re.compile(r"[0-9]{8}\.[0-9]+\.[0-9]+\Z")
TIMESTAMPED = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d+Z) (.*)$")


class CandidateEvidenceError(ValueError):
    """Saved evidence cannot support the candidate consistency claim."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise CandidateEvidenceError(code)


def strict_json(raw: bytes) -> dict:
    try:
        value = ci_compare.strict_json(raw)
    except ci_compare.EvidenceError as error:
        raise CandidateEvidenceError(str(error)) from error
    require(type(value) is dict, "json_object_required")
    return value


def timestamp(value: str) -> datetime:
    require(type(value) is str, "timestamp_type")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise CandidateEvidenceError("timestamp_format") from error
    require(result.tzinfo is not None and result.utcoffset() == timedelta(0), "timestamp_utc")
    return result.astimezone(timezone.utc)


def _positive_id(value: object, code: str) -> str:
    require(type(value) is str and POSITIVE_ID.fullmatch(value) is not None, code)
    return value


def _hex(value: object, pattern: re.Pattern, code: str) -> str:
    require(type(value) is str and pattern.fullmatch(value) is not None, code)
    return value


def _relative_file(root: Path, value: str) -> Path:
    require(type(value) is str and "\\" not in value and ":" not in value and "\x00" not in value,
            "evidence_path_format")
    part = PurePosixPath(value)
    require(not part.is_absolute() and part.parts and
            all(item not in (".", "..") for item in part.parts) and
            part.as_posix() == value, "evidence_path_escape")
    root_real = root.resolve(strict=True)
    path = root.joinpath(*part.parts).resolve(strict=True)
    require(path.is_relative_to(root_real), "evidence_path_escape")
    return path


def _read_bounded(path: Path, maximum: int) -> bytes:
    with path.open("rb") as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= maximum,
                "evidence_file_size")
        raw = stream.read(maximum + 1)
        require(len(raw) == info.st_size, "evidence_file_changed")
    return raw


def _validated_pins(pins: dict) -> dict:
    require(set(pins) == {"schema", "repository", "run_id", "run_attempt", "head_sha",
                          "workflow_sha256", "job_ids", "image", "files"}, "pin_schema")
    require(pins["schema"] == SCHEMA, "pin_version")
    repository = pins["repository"]
    require(type(repository) is str and re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",
                                                   repository) is not None, "repository_pin")
    _positive_id(pins["run_id"], "run_id_pin")
    _positive_id(pins["run_attempt"], "run_attempt_pin")
    _hex(pins["head_sha"], HEX40, "head_pin")
    _hex(pins["workflow_sha256"], HEX64, "workflow_pin")
    job_ids = pins["job_ids"]
    require(type(job_ids) is dict and set(job_ids) == set(JOB_NAMES), "job_pin_inventory")
    for job_id in job_ids.values():
        _positive_id(job_id, "job_id_pin")
    require(len(set(job_ids.values())) == len(job_ids), "duplicate_job_pin")
    image = pins["image"]
    require(type(image) is dict and set(image) == {"name", "version", "tag",
                                                   "release_id", "release_target_commitish",
                                                   "readme_blob_sha"}, "image_pin_schema")
    require(image["name"] == "ubuntu-24.04" and type(image["version"]) is str and
            IMAGE_VERSION.fullmatch(image["version"]) is not None, "image_version_pin")
    require(image["tag"] == "ubuntu24/" + image["version"].rsplit(".", 1)[0],
            "image_tag_pin")
    _positive_id(image["release_id"], "release_id_pin")
    _hex(image["release_target_commitish"], HEX40, "release_commit_pin")
    _hex(image["readme_blob_sha"], HEX40, "readme_blob_pin")
    files = pins["files"]
    require(type(files) is dict and set(files) == set(ROLES), "file_pin_inventory")
    for role, file_pin in files.items():
        require(type(file_pin) is dict and set(file_pin) == {"path", "bytes", "sha256"},
                "file_pin_schema")
        require(type(file_pin["bytes"]) is int and 0 < file_pin["bytes"] <= MAX_BYTES[role],
                "file_pin_size")
        _hex(file_pin["sha256"], HEX64, "file_pin_sha256")
    require(len({file_pin["path"] for file_pin in files.values()}) == len(ROLES),
            "duplicate_file_path")
    return pins


def _read_inputs(root: Path, pins: dict) -> dict[str, bytes]:
    result = {}
    for role in ROLES:
        item = pins["files"][role]
        raw = _read_bounded(_relative_file(root, item["path"]), MAX_BYTES[role])
        require(len(raw) == item["bytes"] and hashlib.sha256(raw).hexdigest() == item["sha256"],
                "raw_pin_mismatch:" + role)
        result[role] = raw
    return result


def _run(run: dict, pins: dict) -> None:
    repository = pins["repository"]
    run_id = pins["run_id"]
    require(type(run.get("head_commit")) is dict and
            type(run.get("repository")) is dict and
            type(run.get("head_repository")) is dict, "run_nested_fields")
    require(type(run.get("id")) is int and str(run["id"]) == run_id and
            type(run.get("run_attempt")) is int and
            str(run["run_attempt"]) == pins["run_attempt"], "run_attempt_identity")
    require(run.get("head_sha") == pins["head_sha"] and
            run.get("head_commit", {}).get("id") == pins["head_sha"] and
            run.get("path") == ".github/workflows/ci.yml", "run_head_workflow")
    require(run.get("repository", {}).get("full_name") == repository and
            run.get("head_repository", {}).get("full_name") == repository,
            "run_repository")
    api = f"https://api.github.com/repos/{repository}/actions/runs/{run_id}"
    require(run.get("url") == api and run.get("jobs_url") == api + "/jobs" and
            run.get("html_url") == f"https://github.com/{repository}/actions/runs/{run_id}",
            "run_url")
    require(run.get("status") == "completed" and run.get("conclusion") == "success",
            "run_not_successful")
    require(timestamp(run.get("created_at")) <= timestamp(run.get("run_started_at")) <=
            timestamp(run.get("updated_at")), "run_time_order")


def _jobs(response: dict, run: dict, pins: dict) -> dict:
    jobs = response.get("jobs")
    require(type(jobs) is list and type(response.get("total_count")) is int and
            response["total_count"] == len(jobs) == 3, "attempt_job_inventory")
    by_name = {}
    for job in jobs:
        require(type(job) is dict and type(job.get("name")) is str and
                job["name"] not in by_name, "duplicate_or_invalid_job")
        by_name[job["name"]] = job
    require(set(by_name) == set(JOB_NAMES.values()), "attempt_job_names")
    result = {}
    for key, name in JOB_NAMES.items():
        job = by_name[name]
        job_id = pins["job_ids"][key]
        require(type(job.get("id")) is int and str(job["id"]) == job_id and
                type(job.get("run_id")) is int and str(job["run_id"]) == pins["run_id"] and
                type(job.get("run_attempt")) is int and
                str(job["run_attempt"]) == pins["run_attempt"], "job_attempt_identity:" + key)
        require(job.get("head_sha") == pins["head_sha"] and
                job.get("head_branch") == run.get("head_branch") and
                job.get("workflow_name") == run.get("name") and
                job.get("run_url") == run.get("url"), "job_run_source:" + key)
        api = f"https://api.github.com/repos/{pins['repository']}/actions/jobs/{job_id}"
        require(job.get("url") == api and
                job.get("check_run_url") ==
                f"https://api.github.com/repos/{pins['repository']}/check-runs/{job_id}" and
                job.get("html_url") == run["html_url"] + f"/job/{job_id}",
                "job_url:" + key)
        require(job.get("status") == "completed" and job.get("conclusion") == "success" and
                job.get("labels") == [pins["image"]["name"]] and
                job.get("runner_group_name") == "GitHub Actions" and
                type(job.get("runner_name")) is str and job["runner_name"].startswith("GitHub Actions "),
                "job_runner_or_status:" + key)
        require(timestamp(run["run_started_at"]) <= timestamp(job.get("created_at")) <=
                timestamp(job.get("started_at")) <= timestamp(job.get("completed_at")) <=
                timestamp(run["updated_at"]) + timedelta(seconds=5),
                "job_time_order:" + key)
        result[key] = job
    return result


def _release_and_readme(raw: dict[str, bytes], pins: dict, run: dict) -> dict:
    image = pins["image"]
    release = strict_json(raw["release"])
    metadata = strict_json(raw["readme_metadata"])
    tag = image["tag"]
    release_html = "https://github.com/actions/runner-images/releases/tag/" + tag
    require(type(release.get("id")) is int and str(release["id"]) == image["release_id"] and
            release.get("tag_name") == tag and release.get("html_url") == release_html and
            release.get("url") ==
            "https://api.github.com/repos/actions/runner-images/releases/" + image["release_id"] and
            release.get("target_commitish") == image["release_target_commitish"] and
            release.get("draft") is False and release.get("prerelease") is False,
            "release_identity")
    require(timestamp(release.get("published_at")) <= timestamp(run["run_started_at"]),
            "release_after_run")
    require(type(release.get("body")) is str and
            len(re.findall(r"^- Image Version: " + re.escape(image["version"]) + r"\s*$",
                           release["body"], re.MULTILINE)) == 1, "release_image_version")
    readme_path = "images/ubuntu/Ubuntu2404-Readme.md"
    readme_html = "https://github.com/actions/runner-images/blob/" + tag + "/" + readme_path
    require(metadata.get("type") == "file" and metadata.get("name") == "Ubuntu2404-Readme.md" and
            metadata.get("path") == readme_path and metadata.get("html_url") == readme_html and
            metadata.get("url") == "https://api.github.com/repos/actions/runner-images/contents/" +
            readme_path + "?ref=" + tag and
            metadata.get("download_url") == "https://raw.githubusercontent.com/actions/runner-images/" +
            tag + "/" + readme_path and metadata.get("sha") == image["readme_blob_sha"] and
            metadata.get("git_url") == "https://api.github.com/repos/actions/runner-images/git/blobs/" +
            image["readme_blob_sha"] and metadata.get("encoding") == "base64" and
            type(metadata.get("size")) is int and metadata["size"] == len(raw["readme"]),
            "readme_metadata_identity")
    try:
        content = metadata["content"]
        require(type(content) is str and
                re.fullmatch(r"[A-Za-z0-9+/=\n]+", content) is not None,
                "readme_metadata_base64")
        decoded = base64.b64decode(content.replace("\n", ""), validate=True)
    except (KeyError, TypeError, ValueError, binascii.Error) as error:
        raise CandidateEvidenceError("readme_metadata_base64") from error
    require(decoded == raw["readme"], "readme_metadata_content")
    blob = b"blob " + str(len(decoded)).encode("ascii") + b"\0" + decoded
    require(hashlib.sha1(blob).hexdigest() == image["readme_blob_sha"], "readme_git_blob")
    try:
        readme = raw["readme"].decode("utf-8")
    except UnicodeError as error:
        raise CandidateEvidenceError("readme_utf8") from error
    kernels = re.findall(r"^- Kernel Version: ([^\r\n]+)$", readme, re.MULTILINE)
    require(len(re.findall(r"^- Image Version: " + re.escape(image["version"]) + r"\s*$",
                           readme, re.MULTILINE)) == 1 and
            "- OS Version: 24.04.5 LTS" in readme and len(kernels) == 1,
            "readme_image_version")
    return {"release_html": release_html, "log_release_html": release_html.replace("/ubuntu24/", "/ubuntu24%2F"),
            "readme_html": readme_html, "kernel": kernels[0]}


def _log(raw: bytes, job: dict, head: str, repository: str, image: dict,
         urls: dict, code: str) -> None:
    try:
        # PowerShell's redirected gh output may carry a UTF-8 BOM.
        lines = raw.decode("utf-8-sig").splitlines()
    except UnicodeError as error:
        raise CandidateEvidenceError("job_log_utf8:" + code) from error
    require(30 <= len(lines) <= 100000 and raw.endswith(b"\n"), "job_log_lines:" + code)
    first = TIMESTAMPED.fullmatch(lines[0])
    last = TIMESTAMPED.fullmatch(lines[-1])
    earliest = timestamp(job["started_at"]) - timedelta(seconds=2)
    latest = timestamp(job["completed_at"]) + timedelta(seconds=2)
    require(first is not None and last is not None and
            earliest <= timestamp(first[1]) <= timestamp(last[1]) <= latest,
            "job_log_window:" + code)
    payloads = []
    previous_time = None
    for line in lines:
        match = TIMESTAMPED.fullmatch(line)
        # Tool stdout can include continuation lines without the GitHub prefix.
        # Identity-bearing header/check-out lines must still be prefixed.
        if match is not None:
            current_time = timestamp(match[1])
            require(earliest <= current_time <= latest,
                    "job_log_timestamp_window:" + code)
            require(previous_time is None or previous_time <= current_time,
                    "job_log_timestamp_order:" + code)
            previous_time = current_time
            payloads.append(match[2])
        else:
            require(len(line) <= 65536 and payloads, "job_log_continuation:" + code)
    require(payloads.count("Complete job name: " + job["name"]) == 1 and
            payloads.count("  repository: " + repository) >= 1 and
            head in payloads and
            any("+" + head + ":refs/remotes/origin/" in line for line in payloads),
            "job_log_checkout:" + code)
    def group(name: str) -> list[str]:
        start = "##[group]" + name
        require(payloads.count(start) == 1, "job_log_group:" + code)
        at = payloads.index(start)
        try:
            end = payloads.index("##[endgroup]", at + 1)
        except ValueError as error:
            raise CandidateEvidenceError("job_log_group_end:" + code) from error
        return payloads[at + 1:end]
    require(group("Operating System") == ["Ubuntu", "24.04.5", "LTS"],
            "job_log_os:" + code)
    require(group("Runner Image") == [
        "Image: " + image["name"],
        "Version: " + image["version"],
        "Included Software: " + urls["readme_html"],
        "Image Release: " + urls["log_release_html"],
    ], "job_log_image:" + code)


def _journal(raw: bytes, minor: str, pins: dict, image: dict, job: dict,
             kernel: str) -> dict:
    require(raw.endswith(b"\n"), "journal_partial:" + minor)
    lines = raw.splitlines()
    require(2 <= len(lines) <= 100000 and
            all(len(line) <= ci_compare.MAX_LINE_BYTES for line in lines),
            "journal_lines:" + minor)
    first, last = strict_json(lines[0]), strict_json(lines[-1])
    source = {"revision": pins["head_sha"], "workflow_sha256": pins["workflow_sha256"],
              "github_run_id": pins["run_id"], "github_run_attempt": pins["run_attempt"]}
    require(first.get("event") == "run_started" and first.get("report_version") == "ci-unittest.3" and
            first.get("source") == source and first.get("acceptance_status") == "not_completed" and
            first.get("formal_permission") is False, "journal_source:" + minor)
    require(timestamp(job["started_at"]) - timedelta(seconds=2) <=
            timestamp(first.get("started_utc")) <= timestamp(job["completed_at"]) + timedelta(seconds=2),
            "journal_job_window:" + minor)
    runtime = first.get("runtime")
    require(type(runtime) is dict and runtime.get("os") == "ubuntu" and
            runtime.get("os_version") == "24.04" and runtime.get("architecture") == "x86_64" and
            runtime.get("kernel") == kernel and
            type(runtime.get("python_version")) is str and
            re.fullmatch(re.escape(minor) + r"\.\d+", runtime["python_version"]) is not None and
            runtime.get("runner_image_os") == "ubuntu24" and
            runtime.get("runner_image_version") == image["version"] and
            runtime.get("runner_image_digest") is None and
            runtime.get("runner_image_digest_status") == "not_collected",
            "journal_runtime:" + minor)
    require(last.get("event") == "run_finished" and last.get("unittest_success") is True and
            last.get("source_unchanged") is True and
            last.get("shared_fixtures_complete") is True and last.get("stopped") is False and
            last.get("acceptance_status") == "not_completed" and last.get("formal_permission") is False and
            all(type(last.get(key)) is int and last[key] == 0 for key in
                ("failures", "errors", "expected_failures", "unexpected_successes")) and
            type(last.get("discovered")) is int and last["discovered"] > 0 and
            last.get("tests_run") == last["discovered"], "journal_finish:" + minor)
    return {"python_version": runtime["python_version"], "tests_run": last["tests_run"],
            "skipped": last.get("skipped")}


def verify_evidence(evidence_root: Path, pins: dict) -> dict:
    """Verify retained bytes against external pins and compare their identities."""
    _validated_pins(pins)
    raw = _read_inputs(evidence_root, pins)
    run = strict_json(raw["run"])
    _run(run, pins)
    jobs = _jobs(strict_json(raw["attempt_jobs"]), run, pins)
    urls = _release_and_readme(raw, pins, run)
    for key in JOB_NAMES:
        role = "log_" + key
        _log(raw[role], jobs[key], pins["head_sha"], pins["repository"],
             pins["image"], urls, key)
    journals = {minor: _journal(raw["journal_" + minor], minor, pins, pins["image"],
                                jobs[minor], urls["kernel"])
                for minor in ("3.12", "3.14")}
    require(journals["3.12"]["tests_run"] == journals["3.14"]["tests_run"] and
            journals["3.12"]["skipped"] == journals["3.14"]["skipped"],
            "journal_matrix_counts")
    journal_paths = {minor: _relative_file(evidence_root,
                                           pins["files"]["journal_" + minor]["path"])
                     for minor in ("3.12", "3.14")}
    try:
        full_journals = regression.verify(journal_paths, pins["head_sha"],
                                          pins["workflow_sha256"], pins["run_id"],
                                          pins["run_attempt"])
    except (ci_compare.EvidenceError, OSError, ValueError, TypeError, KeyError,
            RecursionError) as error:
        raise CandidateEvidenceError("full_journal_verification:" +
                                     (str(error) if isinstance(error, ci_compare.EvidenceError)
                                      else "invalid_journal")) from error
    require(full_journals["verification_status"] == "passed" and
            full_journals["shared_fixture_comparison"] == "matched", "full_journal_status")
    for minor in ("3.12", "3.14"):
        require(full_journals["jobs"][minor]["journal_sha256"] ==
                pins["files"]["journal_" + minor]["sha256"] and
                full_journals["jobs"][minor]["runner_image_version"] ==
                pins["image"]["version"], "full_journal_pin_mismatch:" + minor)
    return {"schema": "ci-runner-origin-candidate-result-v1", "status": "consistent_candidate",
            "repository": pins["repository"], "run_id": pins["run_id"],
            "run_attempt": pins["run_attempt"], "head_sha": pins["head_sha"],
            "workflow_sha256": pins["workflow_sha256"], "job_ids": pins["job_ids"],
            "image": pins["image"], "raw_pins": pins["files"], "journals": journals,
            "full_journal_verification_status": "passed",
            "required_tests_per_minor": len(regression.REQUIRED_TEST_IDS),
            "runner_image_digest_status": "not_collected", "acceptance_status": "not_completed",
            "formal_permission": False,
            "scope": "saved run/attempt job API, three logs, tagged release/README, and full two-journal regression; candidate provenance only"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", required=True, type=Path)
    parser.add_argument("--pins", required=True, type=Path)
    parser.add_argument("--pins-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        _hex(args.pins_sha256, HEX64, "external_pins_sha256")
        raw_pins = _read_bounded(args.pins, MAX_PINS_BYTES)
        require(hashlib.sha256(raw_pins).hexdigest() == args.pins_sha256,
                "external_pins_mismatch")
        result = verify_evidence(args.evidence_root, strict_json(raw_pins))
    except (CandidateEvidenceError, OSError, UnicodeError, TypeError, KeyError, RecursionError) as error:
        print(json.dumps({"schema": "ci-runner-origin-candidate-result-v1", "status": "rejected",
                          "reason": str(error) if isinstance(error, CandidateEvidenceError) else
                          "invalid_or_unreadable_evidence", "runner_image_digest_status": "not_collected",
                          "acceptance_status": "not_completed", "formal_permission": False},
                         sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
