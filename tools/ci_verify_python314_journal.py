"""Verify one saved Python 3.14 Ubuntu journal; never grant S4 acceptance."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import ci_compare_fixtures as comparison
from tools import ci_shared_fixtures as shared
from tools import ci_verify_regression_journals as legacy

REQUIRED_TEST_IDS = (legacy.REQUIRED_TEST_IDS - {
    "tests.test_anomaly_v03_acceptance.AcceptanceContractTests.test_both_linux_minors_remain_compatibility_only_and_unaccepted",
}) | {
    "tests.test_anomaly_v03_acceptance.AcceptanceContractTests.test_python314_scope_requires_one_minor_and_rejects_old_requirements",
}


def verify(path: Path, expected_head: str, expected_workflow_sha256: str,
           expected_run_id: str, expected_run_attempt: str) -> dict:
    source = {"revision": expected_head, "workflow_sha256": expected_workflow_sha256,
              "github_run_id": expected_run_id, "github_run_attempt": expected_run_attempt}
    comparison.source_identity(source)
    report = comparison.read_report(path, "3.14", source)
    comparison.require(REQUIRED_TEST_IDS <= set(report["planned"]), "required_test_missing")
    finished = report["finished"]
    comparison.require(all(finished.get(test_id) == ["pass"] for test_id in REQUIRED_TEST_IDS),
                       "required_test_not_passed")
    windows_skips, optional_skips = [], []
    for skip in report["skips"]:
        test_id = skip.get("test_id")
        policy = legacy._allowed_skip(test_id) if type(test_id) is str else None
        comparison.require(policy is not None and skip.get("reason") == policy[1]
                           and skip.get("subtest") is False and finished.get(test_id) == ["skip"],
                           "unexpected_linux_skip")
        (windows_skips if policy[0] == "windows_native" else optional_skips).append(test_id)
    return {"verification_version": "ci-python314-journal.1", "verification_status": "passed",
            "source": source, "python_minor": "3.14",
            "raw_pin": {"bytes": report["bytes"], "sha256": report["sha256"]},
            "runtime": report["runtime"], "summary": report["summary"],
            "required_tests_passed": len(REQUIRED_TEST_IDS),
            "windows_native_skips": sorted(windows_skips), "non_s4_optional_skips": sorted(optional_skips),
            "shared_fixture_inventory_status": "complete",
            "fixtures": [{"fixture_id": name, "test_id": owner,
                          "payload_sha256": report["fixtures"][name]["sha256"]}
                         for name, (owner, _) in shared.EXPECTED.items()],
            "cross_python_comparison_performed": False,
            "runner_image_digest_status": "not_collected", "execution_authenticated": False,
            "acceptance_status": "not_completed", "formal_permission": False,
            "scope": "one saved Python 3.14 Ubuntu journal; Windows and full S4 acceptance remain incomplete"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python314", required=True, type=Path)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--expected-workflow-sha256", required=True)
    parser.add_argument("--expected-run-id", required=True)
    parser.add_argument("--expected-run-attempt", required=True)
    args = parser.parse_args(argv)
    try:
        result = verify(args.python314, args.expected_head, args.expected_workflow_sha256,
                        args.expected_run_id, args.expected_run_attempt)
    except (comparison.EvidenceError, OSError, ValueError, TypeError, KeyError, RecursionError) as error:
        reason = str(error) if isinstance(error, comparison.EvidenceError) else "invalid_journal"
        print("Python 3.14 journal failed: " + reason, file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
