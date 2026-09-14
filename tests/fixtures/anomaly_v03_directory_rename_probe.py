"""Opt-in new-root directory sealing/relative rename smoke. Never commit marker."""
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
from tests.fixtures import anomaly_v03_directory_rename as move
from tests.fixtures import anomaly_v03_handle_owner as owned
from tests.fixtures import anomaly_v03_observed_evidence as bridge
from tests.fixtures import anomaly_v03_prepublication as prep
from tests.fixtures import anomaly_v03_publication_model as model
from tests.fixtures import anomaly_v03_reader_reacquisition as reopen
from tests.fixtures import anomaly_v03_sealed_files as seal
from tests.fixtures.anomaly_v03_private_sink import WindowsPrivateSink
from tests.fixtures.anomaly_v03_tracked_open import TrackedOpen

BASE = ROOT / "artifacts/directory-rename-2026-09-14"


def notice():
    try:
        os.write(1, b'{"directory_rename":"resource_stop","resource_stop":true}\n')
    except BaseException:
        pass


def main(*, compare_parent_policy=False):
    owned._need(type(compare_parent_policy) is bool, "probe_comparison_mode")
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--attempt", type=int, choices=(1, 2), required=True)
    args = parser.parse_args()
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if actual != args.expected_head or subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT):
        raise ValueError("probe_requires_exact_clean_head")
    base = ROOT / "artifacts/parent-policy-rename-2026-09-14" if compare_parent_policy else BASE
    parent_policy = "private" if compare_parent_policy and args.attempt == 1 else "frozen"
    attempt = base / f"attempt-{args.attempt}"
    attempt.mkdir()
    # A relative name resolved against CWD would stay within this new attempt
    # but fail the expected source-fixture/payload inventory and identity check.
    os.chdir(attempt)
    source, sink, group = move.WindowsDirectoryFixture(), WindowsPrivateSink(), bridge.AcquiredOwner()
    generation = operation = backend = None
    failure, resource_stop = None, False
    points, evidence, final_leases, final_observations = [], [], [], []
    raw_file = b'{"scope":"directory_rename_probe","count":1}\n'
    files = {"facts.json": raw_file}
    marker = model.marker_bytes(actual, files)  # Retained evidence only; no marker file.
    journal = model.PublicationJournal(hashlib.sha256(marker).hexdigest())
    started = time.monotonic()
    writer_access = None

    def failed(error):
        nonlocal failure, resource_stop
        if failure is None:
            failure = error
        resource_stop = resource_stop or owned._resource(error) or source._resource or sink._resource
        resource_stop = resource_stop or (backend is not None and backend.completion_unknown)
        if group.active:
            resource_stop = resource_stop or group.owner._resource_stop

    def budget():
        api, win = source._api, source._win
        memory, performance = win._Memory(), win._Performance()
        memory.cb, performance.cb = C.sizeof(memory), C.sizeof(performance)
        api.call(api.p.GetProcessMemoryInfo(api.k.GetCurrentProcess(), C.byref(memory), memory.cb), "probe_memory")
        api.call(api.p.GetPerformanceInfo(C.byref(performance), performance.cb), "probe_available_memory")
        point = {"elapsed_seconds": round(time.monotonic() - started, 3), "private_bytes": memory.private,
                 "working_bytes": memory.working, "peak_working_bytes": memory.peak_working,
                 "available_ram_bytes": performance.available * performance.page_size,
                 "free_disk_bytes": shutil.disk_usage(base).free}
        points.append(point)
        if point["elapsed_seconds"] > 40 or memory.private > 256*1024**2 or memory.working > 384*1024**2 \
                or point["available_ram_bytes"] < 2*1024**3 or point["free_disk_bytes"] < 2*1024**3:
            raise MemoryError("probe_resource_limit")

    def save(step, observations):
        record = prep.build_evidence(step, source_revision=actual, files=files, marker=marker, observations=observations)
        if len(record.raw) > 64*1024:
            raise MemoryError("probe_evidence_limit")
        sink.persist_evidence(step, record.raw, record.sha256)
        evidence.append(record)

    try:
        source.connect(attempt / "source-fixture")
        budget()
        root_lease = source._leases[-1]
        stage_path = source._root / "stage"
        # Both exact resolved targets must remain in this newly created root.
        owned._need(stage_path.resolve().parent == source._root.resolve()
                    and (source._root / "payload").resolve().parent == source._root.resolve(),
                    "directory_scope")
        with source._descriptor(True) as descriptor:
            security = source._win._SA(C.sizeof(source._win._SA), descriptor, False)
            source._api.call(source._api.k.CreateDirectoryW(str(stage_path), C.byref(security)), "stage_create")
        stage_lease = source._open(stage_path, directory=True)
        writer = source._open(stage_path / "facts.json", directory=False, create=True)
        buffer, written = C.create_string_buffer(raw_file), source._win.D()
        source._api.call(source._api.k.WriteFile(writer.handle, buffer, len(raw_file), C.byref(written), None), "fixture_write")
        owned._need(written.value == len(raw_file), "fixture_short_write")
        source._api.call(source._api.k.FlushFileBuffers(writer.handle), "fixture_flush")
        selected = (root_lease, stage_lease, writer)
        observations = tuple(bridge.inspect_native(cell, expected=value, private_user=source._user)
                             for cell, value in zip(selected, (None, None, raw_file)))
        group.adopt(leases=selected, journal=journal, observations=observations, parents=(None, 0, 1))
        backend = move.WindowsNtDirectoryBackend(source)
        writer_access = group.owner.borrowed((2,), lambda pins: backend.granted_access(pins[0].handle))
        owned._need(type(writer_access) is int and writer_access == reopen.WRITER_ACCESS, "writer_access")
        sink.connect(attempt / "private-evidence")
        budget()
        generation = seal.SealedFiles(move.WindowsStageFileBackend(source), group=group, root_index=1,
            plans=(reopen.ReadPlan(2, "facts.json", raw_file, observations[2]),), user=source._user, require_marker=False)
        operation = move.DirectoryRename(backend, group=group, previous=observations[:2], files=generation,
                                         parent_policy=parent_policy)
        journal.begin("prepare")
        record = prep.build_evidence("prepare", source_revision=actual, files=files, marker=marker, observations=observations)
        if len(record.raw) > 64*1024:
            raise MemoryError("probe_evidence_limit")
        barrier = prep.EvidenceBarrier(sink, owner=group.owner, protected=(0, 1))
        barrier.save_and_release(record, (2,))
        evidence.append(record)
        def file_sealed(pins):
            owned._need(pins.parent == observations[1].pin and pins.marker_index is None, "stage_seal_binding")
            save("seal_payload", observations[:2] + pins.observations)
        generation.seal_and_use(file_sealed)
        # Filename verify_final.json is the third local sink reservation,
        # recording sealed directories BEFORE rename, not model-phase success.
        operation.run(lambda directories, children: save("verify_final", directories + children))
        budget()
    except BaseException as error:
        failed(error)
    finally:
        if generation is not None:
            try:
                generation.finish(primary=failure)
            except BaseException as error:
                failed(error)
        if group.active:
            try:
                group.finish(primary=failure)
            except BaseException as error:
                failed(error)
        for cell in reversed(source._leases):
            if cell._custodian is group and group.active:
                continue
            try:
                cell.close()
            except BaseException as error:
                failed(error)
        try:
            sink.finish(primary=failure)
        except BaseException as error:
            failed(error)
    if resource_stop:
        notice()
        if backend is not None and backend.completion_unknown:
            os._exit(80)  # Retain pending request buffers until process death.
        return 80

    # Separate post-close reader verification only after successful operation
    # and confirmed teardown. An operation error skips all these native reads.
    if failure is None:
        try:
            owned._need(operation.snapshot()["rename"] == "confirmed"
                        and group.owner.snapshot()["all_closes_confirmed"]
                        and journal.snapshot()["teardown"] == "succeeded", "directory_teardown")
            owned._need({p.name for p in attempt.iterdir()} == {"source-fixture", "private-evidence"}
                        and {p.name for p in source._root.iterdir()} == {"payload"}
                        and {p.name for p in (source._root / "payload").iterdir()} == {"facts.json"}, "renamed_inventory")
            expected = tuple(operation._sealed) + tuple(generation._sealed)
            for path, before, contents in zip((source._root, source._root / "payload", source._root / "payload/facts.json"),
                                             expected, (None, None, raw_file)):
                cell = TrackedOpen(source._backend)
                final_leases.append(cell)
                def opener(receiver, path=path, before=before):
                    receiver.handle = source._api.k.CreateFileW(str(path), reopen.READER_ACCESS, 1, None, 3,
                        0x00200000 | (0x02000000 if before.pin.directory else 0), None)
                    if receiver.handle == C.c_void_p(-1).value:
                        raise owned.OwnershipError("final_reader_open", C.get_last_error())
                cell.acquire(opener, lambda h, path=path, before=before: source._file_view(h, path, before.pin.directory))
                mode = parent_policy if path == source._root else "frozen"
                after = bridge.inspect_native(cell, expected=contents, private_user=source._user, security_mode=mode)
                owned._need((after.pin.volume, after.pin.file_id, after.pin.directory, after.pin.content_sha256, after.descriptor)
                            == (before.pin.volume, before.pin.file_id, before.pin.directory, before.pin.content_sha256, before.descriptor),
                            "renamed_identity_or_content")
                final_observations.append(after)
                cell.close()
            owned._need({p.name for p in sink._root.iterdir()} == {"prepare.json", "seal_payload.json", "verify_final.json"},
                        "evidence_inventory")
            for record in evidence:
                owned._need((sink._root / (record.step + ".json")).read_bytes() == record.raw, "evidence_postclose_readback")
            budget()
        except BaseException as error:
            failed(error)
        finally:
            for cell in reversed(final_leases):
                try:
                    cell.close()
                except BaseException as error:
                    failed(error)
    if resource_stop:
        notice()
        return 80

    try:
        report = {"scope": "B2 held directory sealing and relative rename engineering smoke",
                  "utc": datetime.now(timezone.utc).isoformat(), "source_revision": actual, "attempt": args.attempt,
                  "parent_policy_comparison": compare_parent_policy, "parent_policy": parent_policy,
                  "directory_rename": "pass" if failure is None else "fail",
                  "error_type": None if failure is None else type(failure).__name__,
                  "error_reason": None if failure is None else getattr(failure, "reason", None),
                  "winerror": None if failure is None else getattr(failure, "winerror", getattr(failure, "error", None)),
                  "writer_access": writer_access, "source_bytes": len(raw_file), "marker_file_created": False,
                  "evidence": [{"step": r.step, "bytes": len(r.raw), "sha256": r.sha256} for r in evidence],
                  "source_handles": [cell.snapshot() for cell in source._leases],
                  "source_token": None if source._token is None else source._token.snapshot(), "sink": sink.snapshot(),
                  "generation": None if generation is None else generation.snapshot(),
                  "operation": None if operation is None else operation.snapshot(),
                  "native_rename": None if backend is None else backend.native_snapshot(),
                  "owner": group.owner.snapshot() if group.active else None,
                  "final_reader_handles": [cell.snapshot() for cell in final_leases],
                  "postclose_objects_matched": len(final_observations),
                  "journal": journal.snapshot(), "resources": points, "resource_stop": False,
                  "cwd_relation": "new attempt parent, distinct from held source-fixture root",
                  "native_publication_performed": False, "native_acceptance_completed": False,
                  "acceptance_status": "not_completed", "formal_permission": False, "execution_authenticated": False}
        raw = (json.dumps(report, ensure_ascii=True, indent=2) + "\n").encode("ascii")
        if len(raw) > 128*1024:
            raise MemoryError("report_budget")
        with (attempt / "probe-result.json").open("xb") as stream:
            stream.write(raw)
        print(json.dumps({"directory_rename": report["directory_rename"], "attempt": args.attempt,
                          "rename_state": None if operation is None else operation._rename,
                          "postclose_objects_matched": len(final_observations), "source_bytes": len(raw_file)}))
    except BaseException as error:
        if owned._resource(error):
            notice()
            return 80
        raise
    return 0 if failure is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
