"""Opt-in observed prepare evidence smoke; no rename, sealing or publication."""
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
from tests.fixtures import anomaly_v03_observed_evidence as bridge
from tests.fixtures import anomaly_v03_handle_owner as owned
from tests.fixtures import anomaly_v03_prepublication as prep
from tests.fixtures import anomaly_v03_publication_model as model
from tests.fixtures.anomaly_v03_private_sink import WindowsPrivateSink

BASE = ROOT / "artifacts/observed-evidence-2026-09-14"


def _notice():
    try:
        os.write(1, b'{"observed_prepare":"resource_stop","resource_stop":true}\n')
    except BaseException:
        pass


def main(*, scenario=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--attempt", type=int, choices=(1, 2), required=True)
    args = parser.parse_args()
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if actual != args.expected_head or subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT):
        raise ValueError("probe_requires_exact_clean_head")
    probe_base = BASE if scenario is None else scenario.base
    attempt = probe_base / f"attempt-{args.attempt}"
    attempt.mkdir()  # Exclusive new attempt. Existing BASE only.
    source, sink, group = WindowsPrivateSink(), WindowsPrivateSink(), bridge.AcquiredOwner()
    failure, resource_stop = None, False
    points, record = [], None
    files = {"facts.json": b'{"scope":"observed_prepare_probe","count":2}\n'}
    marker = model.marker_bytes(actual, files)
    journal = model.PublicationJournal(hashlib.sha256(marker).hexdigest())
    started = time.monotonic()

    def failed(error):
        nonlocal failure, resource_stop
        if failure is None:
            failure = error
        resource_stop = resource_stop or owned._resource(error) or source._resource or sink._resource
        if group.active:
            resource_stop = resource_stop or group.owner._resource_stop

    def budget():
        from banto_ai import _anomaly_v03_windows as win
        api = source._api
        memory, performance = win._Memory(), win._Performance()
        memory.cb, performance.cb = C.sizeof(memory), C.sizeof(performance)
        api.call(api.p.GetProcessMemoryInfo(api.k.GetCurrentProcess(), C.byref(memory), memory.cb), "probe_memory")
        api.call(api.p.GetPerformanceInfo(C.byref(performance), performance.cb), "probe_available_memory")
        point = {"elapsed_seconds": round(time.monotonic() - started, 3),
                 "private_bytes": memory.private, "working_bytes": memory.working,
                 "peak_working_bytes": memory.peak_working, "peak_commit_bytes": memory.peak_pagefile,
                 "available_ram_bytes": performance.available * performance.page_size,
                 "free_disk_bytes": shutil.disk_usage(probe_base).free}
        points.append(point)
        if point["elapsed_seconds"] > 40 or memory.private > 256 * 1024**2 or memory.working > 384 * 1024**2 \
                or point["available_ram_bytes"] < 2 * 1024**3 or point["free_disk_bytes"] < 2 * 1024**3:
            raise MemoryError("probe_resource_limit")

    try:
        source.connect(attempt / "source-fixture")
        budget()
        root_lease = source._leases[-1]
        selected = [root_lease]
        # This fixture retains the original writers until the prepare barrier.
        # Optional scenarios run only after the prepare barrier releases writers.
        for name, raw in (("facts.json", files["facts.json"]), ("marker-pending.json", marker)):
            if len(raw) > 4096:
                raise MemoryError("source_fixture_budget")
            buffer, written = C.create_string_buffer(raw), source._win.D()
            lease = source._open(source._root / name, directory=False, create=True)
            selected.append(lease)
            source._win._verify_sd(source._api.security(lease.handle), source._user, "private", False)
            source._api.call(source._api.k.WriteFile(lease.handle, buffer, len(raw), C.byref(written), None), "fixture_write")
            owned._need(written.value == len(raw), "fixture_short_write")
            source._api.call(source._api.k.FlushFileBuffers(lease.handle), "fixture_flush")
            owned._need(lease.observed.read() == raw, "fixture_readback")
        observations = tuple(bridge.inspect_native(lease, expected=raw, private_user=source._user)
                             for lease, raw in zip(selected, (None, files["facts.json"], marker)))
        group.adopt(leases=tuple(selected), journal=journal, observations=observations, parents=(None, 0, 0))
        sink.connect(attempt / "private-evidence")
        budget()
        journal.begin("prepare")
        record = bridge.capture_record(group, "prepare", source_revision=actual, files=files, marker=marker,
                                       bindings=((1, "facts.json"), (2, None)), private_indices=(0, 1, 2), user=source._user)
        if len(record.raw) > 64 * 1024:
            raise MemoryError("evidence_probe_budget")
        if scenario is not None:
            scenario.before_release(source, group, record)
        barrier = prep.EvidenceBarrier(sink, owner=group.owner, protected=(0,))
        barrier.save_and_release(record, (1, 2))
        owned._need(barrier.snapshot()["steps"][0]["state"] == "released", "barrier_not_released")
        if scenario is not None:
            scenario.after_release()
        budget()
    except BaseException as error:
        failed(error)
    finally:
        # Only terminal ownership release after failure/resource stop.
        if scenario is not None:
            try:
                scenario.finish(primary=failure)
            except BaseException as error:
                failed(error)
        if group.active:
            try:
                group.finish(primary=failure)
            except BaseException as error:
                failed(error)
        # Ancestors remain under their original source owner; adopted cells
        # must only close through the group, even if its close is unknown.
        for lease in reversed(source._leases):
            if lease._custodian is group and group.active:
                continue
            try:
                lease.close()
            except BaseException as error:
                failed(error)
        try:
            sink.finish(primary=failure)
        except BaseException as error:
            failed(error)
    if resource_stop:
        _notice()
        return 80

    try:
        if failure is None:
            budget()
            owned._need(group.owner.snapshot()["all_closes_confirmed"]
                        and all(lease.close_state == "closed" for lease in source._leases + sink._leases)
                        and source._token.close_state == sink._token.close_state == "closed", "probe_unclosed")
            owned._need(journal.snapshot()["commit_observation"] == "not_started"
                        and journal.snapshot()["teardown"] == "succeeded", "probe_publication_state")
            expected_source = {"facts.json": files["facts.json"], "marker-pending.json": marker}
            owned._need({p.name for p in source._root.iterdir()} == set(expected_source), "source_inventory")
            for name, raw in expected_source.items():
                owned._need((source._root / name).read_bytes() == raw, "source_postclose_readback")
            owned._need({p.name for p in sink._root.iterdir()} == {"prepare.json"}
                        and (sink._root / "prepare.json").read_bytes() == record.raw, "evidence_postclose_readback")
            if scenario is not None:
                scenario.validate_terminal()
    except BaseException as error:
        failed(error)
    if resource_stop:
        _notice()
        return 80
    try:
        result = {"scope": "B2 observed prepare evidence engineering smoke", "utc": datetime.now(timezone.utc).isoformat(),
                  "source_revision": actual, "attempt": args.attempt, "observed_prepare": "pass" if failure is None else "fail",
                  "error_type": None if failure is None else type(failure).__name__,
                  "error_reason": None if failure is None else getattr(failure, "reason", None),
                  "winerror": None if failure is None else getattr(failure, "winerror", getattr(failure, "error", None)),
                  "evidence_bytes": None if record is None else len(record.raw),
                  "evidence_sha256": None if record is None else record.sha256,
                  "source_bytes": sum(map(len, files.values())) + len(marker),
                  "source_handles": [lease.snapshot() for lease in source._leases],
                  "source_token": None if source._token is None else source._token.snapshot(),
                  "owner": None if not group.active else group.owner.snapshot(),
                  "sink": sink.snapshot(), "journal": journal.snapshot(), "resources": points,
                  "scenario": None if scenario is None else scenario.snapshot(),
                  "resource_stop": False, "native_publication_performed": False, "native_acceptance_completed": False,
                  "acceptance_status": "not_completed", "formal_permission": False, "execution_authenticated": False}
        raw = (json.dumps(result, ensure_ascii=True, indent=2) + "\n").encode("ascii")
        if len(raw) > 128 * 1024:
            raise MemoryError("probe_report_budget")
        with (attempt / "probe-result.json").open("xb") as stream:
            stream.write(raw)
        print(json.dumps({"observed_prepare": result["observed_prepare"], "attempt": args.attempt,
                          "evidence_bytes": result["evidence_bytes"], "source_bytes": result["source_bytes"],
                          "source_handles": len(source._leases), "sink_handles": len(sink._leases)}))
    except BaseException as error:
        if owned._resource(error):
            _notice()
            return 80
        raise
    return 0 if failure is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
