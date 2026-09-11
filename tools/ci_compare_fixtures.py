"""Compare bounded CI journals, never an authenticated S4 acceptance receipt."""

import hashlib
import json
import math
import re
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools import ci_shared_fixtures as shared
from tools import ci_test_report as ci

MINORS = ("3.12", "3.14")
MAX_LINE_BYTES = 4 * 1024 * 1024
REL_TOL = ABS_TOL = 1e-12


class EvidenceError(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise EvidenceError(code)


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result
    def number(value):
        result = float(value)
        require(math.isfinite(result), "nonfinite_json")
        return result
    def reject(value):
        raise EvidenceError("nonfinite_json")
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_float=number, parse_constant=reject)
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError) as error:
        if isinstance(error, EvidenceError): raise
        raise EvidenceError("invalid_json") from error


def read_report(path, minor, expected_source):
    planned, started, finished, fixtures, skips = [], set(), {}, {}, []
    first = last = active = None
    active_outcomes = set()
    total = payload_total = 0
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        info = __import__("os").fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= ci.MAX_REPORT_BYTES, "report_file_size")
        while line := stream.readline(MAX_LINE_BYTES + 1):
            total += len(line)
            require(total <= ci.MAX_REPORT_BYTES and len(line) <= MAX_LINE_BYTES and line.endswith(b"\n"), "report_byte_limit_or_partial_line")
            digest.update(line)
            row = strict_json(line)
            require(type(row) is dict and last is None, "record_after_finish_or_wrong_type")
            event = row.get("event")
            if first is None:
                require(event == "run_started" and row.get("report_version") == "ci-unittest.2", "report_version_or_start")
                require(row.get("source") == expected_source, "source_mismatch")
                require(row.get("acceptance_status") == "not_completed" and row.get("formal_permission") is False, "acceptance_claim")
                runtime = row.get("runtime", {})
                require((runtime.get("os"), runtime.get("os_version"), runtime.get("architecture")) == ("ubuntu", "24.04", "x86_64"), "runtime_mismatch")
                require(re.fullmatch(re.escape(minor) + r"\.\d+", runtime.get("python_version", "")) is not None, "python_mismatch")
                require(runtime.get("soabi") == "cpython-" + minor.replace(".", "") + "-x86_64-linux-gnu", "python_abi_mismatch")
                first = row
            elif event == "planned_test":
                name = row.get("test_id")
                require(not started and type(name) is str and name not in planned and len(planned) < 10000, "planned_test_inventory")
                planned.append(name)
            elif event == "test_started":
                name = row.get("test_id")
                require(active is None and name in planned and name not in started, "test_start_order")
                active = name
                active_outcomes = set()
                started.add(name)
            elif event == "outcome":
                require(active is not None and row.get("test_id") == active and row.get("status") in ("pass", "skip"), "test_not_successful")
                active_outcomes.add(row["status"])
                if row["status"] == "skip": skips.append(row)
            elif event == "test_finished":
                require(active is not None and row.get("test_id") == active and active_outcomes and row.get("outcomes") == sorted(active_outcomes), "test_finish_mismatch")
                finished[active] = row["outcomes"]
                active = None
            elif event == "shared_fixture":
                name = row.get("fixture_id")
                require(name in shared.EXPECTED and name not in fixtures, "fixture_inventory")
                owner, mode = shared.EXPECTED[name]
                require(active == row.get("test_id") == owner and row.get("comparison") == mode and row.get("fixture_version") == shared.VERSION, "fixture_owner_or_mode")
                require(type(row.get("payload_json")) is str and type(row.get("payload_bytes")) is int, "fixture_payload_type")
                raw = row["payload_json"].encode("utf-8")
                payload_total += len(raw)
                require(len(raw) <= shared.MAX_PAYLOAD_BYTES and payload_total <= shared.MAX_TOTAL_BYTES, "fixture_byte_limit")
                require(row["payload_bytes"] == len(raw) and row.get("payload_sha256") == hashlib.sha256(raw).hexdigest(), "fixture_digest")
                decoded = strict_json(raw)
                require(shared.canonical(decoded) == raw, "fixture_not_canonical")
                fixtures[name] = {"raw": raw, "value": decoded, "sha256": row["payload_sha256"]}
            elif event == "run_finished":
                require(active is None and row.get("acceptance_status") == "not_completed" and row.get("formal_permission") is False, "finish_or_acceptance_claim")
                require(all(row.get(key) is True for key in ("unittest_success", "source_unchanged", "shared_fixtures_complete")) and row.get("stopped") is False, "run_not_complete")
                for key in ("discovered", "tests_run", "failures", "errors", "skipped", "expected_failures", "unexpected_successes", "shared_fixtures"):
                    require(type(row.get(key)) is int and row[key] >= 0, "summary_count_type")
                require(all(row[key] == 0 for key in ("failures", "errors", "expected_failures", "unexpected_successes")), "run_failed")
                require(row["discovered"] == row["tests_run"] == len(planned) == len(started) == len(finished) > 0, "unexecuted_tests")
                require(row["skipped"] == len(skips) and row["shared_fixtures"] == len(fixtures) == len(shared.EXPECTED) and row.get("shared_fixture_version") == shared.VERSION, "summary_fixture_inventory")
                last = row
            else:
                raise EvidenceError("unexpected_event")
    require(first is not None and last is not None and fixtures.keys() == shared.EXPECTED.keys(), "incomplete_report")
    require(all(finished.get(owner) == ["pass"] for owner, _ in shared.EXPECTED.values()), "fixture_test_not_passed")
    return {"sha256": digest.hexdigest(), "bytes": total, "planned": planned, "finished": finished,
            "skips": skips, "fixtures": fixtures, "runtime": first["runtime"], "summary": last}


def numeric_equal(left, right):
    if type(left) is not type(right): return False
    if type(left) is float:
        return math.isfinite(left) and math.isfinite(right) and math.isclose(left, right, rel_tol=REL_TOL, abs_tol=ABS_TOL)
    if type(left) is list:
        return len(left) == len(right) and all(numeric_equal(a, b) for a, b in zip(left, right))
    if type(left) is dict:
        return left.keys() == right.keys() and all(numeric_equal(left[key], right[key]) for key in left)
    return left == right


def compare_reports(paths, expected_source):
    require(set(paths) == set(MINORS), "required_python_matrix")
    reports = {minor: read_report(paths[minor], minor, expected_source) for minor in MINORS}
    left, right = (reports[minor] for minor in MINORS)
    require(left["planned"] == right["planned"] and left["finished"] == right["finished"] and left["skips"] == right["skips"], "test_inventory_or_outcomes_differ")
    compared = []
    for name, (owner, mode) in shared.EXPECTED.items():
        a, b = left["fixtures"][name], right["fixtures"][name]
        matched = a["raw"] == b["raw"] if mode == "exact" else numeric_equal(a["value"], b["value"])
        require(matched, "shared_fixture_mismatch")
        compared.append({"fixture_id": name, "test_id": owner, "comparison": mode,
                         "payload_sha256": {"3.12": a["sha256"], "3.14": b["sha256"]}})
    return {"comparison_version": shared.VERSION, "comparison_status": "matched", "source": expected_source,
            "fixtures": compared, "numeric_tolerance": {"rel_tol": REL_TOL, "abs_tol": ABS_TOL},
            "reports": {minor: {key: report[key] for key in ("sha256", "bytes", "runtime", "summary")} for minor, report in reports.items()},
            "acceptance_status": "not_completed", "formal_permission": False, "execution_authenticated": False,
            "scope": "selected existing hand fixtures on Linux 3.12 and 3.14; Windows and full S4 acceptance remain incomplete"}


def main():
    source = ci.source_identity(ROOT)
    base = ROOT / "artifacts/ci-fixtures"
    try:
        report = compare_reports({minor: base / ("python" + minor) / "unittest.jsonl" for minor in MINORS}, source)
        require(ci.source_identity(ROOT) == source, "comparison_source_changed")
    except (EvidenceError, OSError, ValueError, KeyError, TypeError, RecursionError) as error:
        report = {"comparison_version": shared.VERSION, "comparison_status": "failed", "source": source,
                  "reason": str(error) if isinstance(error, EvidenceError) else "invalid_report",
                  "acceptance_status": "not_completed", "formal_permission": False, "execution_authenticated": False}
    base.mkdir(parents=True, exist_ok=True)
    with (base / "comparison.json").open("xb") as output:
        output.write(shared.canonical(report) + b"\n")
    print("shared fixture comparison: " + report["comparison_status"])
    return 0 if report["comparison_status"] == "matched" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ci.subprocess.SubprocessError):
        print("CI fixture comparison could not complete", file=sys.stderr)
        raise SystemExit(2)
