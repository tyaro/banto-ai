"""Opt-in single attempt; caller must first pin a clean revision and supervisor."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from tests.fixtures.anomaly_v03_delete_matrix import DeleteDriver, DeleteContext
from tests.fixtures import anomaly_v03_handle_owner as owned

BASE = ROOT / "artifacts/delete-matrix-2026-09-14"


def _notice():
    try:
        os.write(1, b'{"delete_matrix":"resource_stop","resource_stop":true}\n')
    except BaseException:
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--attempt", type=int, choices=(1,), required=True)
    args = parser.parse_args()
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    owned._need(re.fullmatch("[a-f0-9]{40}", args.expected_head) is not None and actual == args.expected_head
                and not subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT), "probe_requires_exact_clean_head")
    attempt = BASE / "attempt-1"
    context = DeleteContext(attempt, actual)
    driver = DeleteDriver(context)
    attempt.mkdir()  # Exclusive; no source exists check, open or fallback.
    try:
        driver.run()
    except BaseException:
        pass  # The driver latches the first error and completes bounded teardown.
    if driver._resource:
        _notice()
        return 80
    try:
        report = {"source_revision": actual, "attempt": 1, **driver.snapshot()}
        raw = (json.dumps(report, sort_keys=True, ensure_ascii=True) + "\n").encode("ascii")
        if len(raw) > 128 * 1024:
            raise MemoryError("driver_report_budget")
        # Only stdout after teardown/failure. Supervisor owns its redirect file.
        owned._need(os.write(1, raw) == len(raw), "driver_short_report")
    except BaseException as error:
        if owned._resource(error):
            _notice()
            return 80
        return 1
    return driver.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
