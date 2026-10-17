"""Opt-in B2 storage probe. Never part of unittest discovery or B1 controls."""
import argparse
import ctypes as C
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tests.fixtures.anomaly_v03_private_sink import WindowsPrivateSink
from tests.fixtures import anomaly_v03_handle_owner as owned

BASE = ROOT / "artifacts/private-sink-2026-09-14"


def _resource_notice():
    # Fixed minimal notification only; do not serialize snapshots or create a
    # normal report after a resource stop. The supervisor owns its own record.
    try:
        os.write(1, b'{"storage_smoke":"resource_stop","resource_stop":true}\n')
    except BaseException:
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--attempt", type=int, choices=(1, 2), required=True)
    args = parser.parse_args()
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if actual != args.expected_head or subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT):
        raise ValueError("probe_requires_exact_clean_head")
    root = BASE / f"attempt-{args.attempt}" / "private-evidence"
    if root.parent.exists():
        raise ValueError("probe_attempt_already_exists")
    root.parent.mkdir()  # Existing BASE is created by the recording workflow.
    started = time.monotonic()
    sink = WindowsPrivateSink()
    points, expected = [], {}
    report = {"scope": "B2 private-storage engineering smoke only", "source_revision": actual,
              "attempt": args.attempt, "utc": datetime.now(timezone.utc).isoformat(),
              "native_publication_performed": False, "native_acceptance_completed": False,
              "formal_permission": False, "execution_authenticated": False, "acceptance_status": "not_completed"}
    # The supervisor additionally enforces time/process memory once per second.
    def budget():
        from banto_ai import _anomaly_v03_windows as win
        api = sink._api
        memory, performance = win._Memory(), win._Performance()
        memory.cb, performance.cb = C.sizeof(memory), C.sizeof(performance)
        api.call(api.p.GetProcessMemoryInfo(api.k.GetCurrentProcess(), C.byref(memory), memory.cb), "probe_memory")
        api.call(api.p.GetPerformanceInfo(C.byref(performance), performance.cb), "probe_available_memory")
        point = {"elapsed_seconds": round(time.monotonic() - started, 3),
                 "private_bytes": memory.private, "working_bytes": memory.working,
                 "peak_working_bytes": memory.peak_working, "peak_commit_bytes": memory.peak_pagefile,
                 "available_ram_bytes": performance.available * performance.page_size,
                 "free_disk_bytes": shutil.disk_usage(BASE).free}
        points.append(point)
        if point["elapsed_seconds"] > 40 or memory.private > 256 * 1024**2 or memory.working > 384 * 1024**2 \
                or point["available_ram_bytes"] < 2 * 1024**3 or point["free_disk_bytes"] < 2 * 1024**3:
            raise MemoryError("probe_resource_limit")
    failure, resource_stop = None, False
    try:
        sink.connect(root)
        budget()
        for step in owned.RELEASE_STEPS:
            raw = (json.dumps({"scope": "synthetic_storage_probe", "step": step,
                               "acceptance_status": "not_completed", "formal_permission": False,
                               "execution_authenticated": False}, sort_keys=True) + "\n").encode("ascii")
            expected[step + ".json"] = raw
            if sum(map(len, expected.values())) > 16 * 1024:
                raise MemoryError("probe_payload_budget")
            sink.persist_evidence(step, raw, hashlib.sha256(raw).hexdigest())
            budget()
        sink.finish()
        budget()
        if {path.name for path in root.iterdir()} != set(expected):
            raise ValueError("probe_inventory")
        for name, raw in expected.items():
            if (root / name).read_bytes() != raw:
                raise ValueError("probe_closed_file_readback")
        snapshot = sink.snapshot()
        if any(row["close_state"] != "closed" for row in snapshot["handles"]) \
                or snapshot["token"]["close_state"] != "closed" or snapshot["stopped"] \
                or any(row["state"] != "saved" for row in snapshot["files"]):
            raise ValueError("probe_incomplete")
        report["storage_smoke"] = "pass"
    except BaseException as error:
        failure = error
        resource_stop = owned._resource(error) or sink._resource
        if not resource_stop:
            report.update(storage_smoke="fail", error_type=type(error).__name__,
                          error_reason=getattr(error, "reason", None), winerror=getattr(error, "winerror", getattr(error, "error", None)))
    finally:
        try:
            sink.finish(primary=failure)
        except BaseException as error:
            resource_stop = resource_stop or owned._resource(error) or sink._resource
            if failure is None:
                failure = error
                if not resource_stop:
                    report.update(storage_smoke="fail", error_type=type(error).__name__,
                                  error_reason=getattr(error, "reason", None))
    if resource_stop:
        _resource_notice()
        return 80
    try:
        report.update(sink=sink.snapshot(), resources=points, resource_stop=False)
        raw = (json.dumps(report, ensure_ascii=True, indent=2) + "\n").encode("ascii")
        if len(raw) > 128 * 1024:
            raise MemoryError("probe_report_budget")
        with (root.parent / "probe-result.json").open("xb") as stream:
            stream.write(raw)
        print(json.dumps({"storage_smoke": report["storage_smoke"], "attempt": args.attempt,
                          "files": len(expected), "payload_bytes": sum(map(len, expected.values())),
                          "handles": len(sink.snapshot()["handles"]),
                          "result": str((root.parent / "probe-result.json").relative_to(ROOT))}))
    except BaseException as error:
        if owned._resource(error):
            _resource_notice()
            return 80
        raise
    return 0 if failure is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
