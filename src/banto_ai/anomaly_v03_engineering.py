"""Fixed six-cell engineering trial, saved-input replay, no formal campaign gate."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from . import _anomaly_v03_io as storage
from . import _anomaly_v03_runtime as rt
from . import _anomaly_v03_engineering_runtime as resources
from . import anomaly_v03 as v
from . import anomaly_v03_engineering_contract as policy
from . import anomaly_v03_materializer as m
from . import anomaly_v03_runner as runner

CONTROL_RESERVE = 1024 * 1024


def _same(left, right, message):
    rt.require(v.canonical_json(left) == v.canonical_json(right), message)


def _read_dataset(read, identity):
    prefix = "datasets/" + identity["dataset_id"] + "/"
    return {name: read(prefix + name) for name in m.DATASET_FILES}


def _verify_payloads(files, checkout, observed):
    """Sequential producer replay from saved bytes; not independent S6 audit."""
    manifest = v.strict_json(files["manifest.json"])
    policy.validate_manifest(manifest)
    rt.require(manifest["state"] == "complete", "engineering trial incomplete")
    _same(manifest["source"], checkout.source_descriptor(), "engineering source changed")
    _same(manifest["runtime"], observed, "engineering runtime changed")
    rt.require(files["planned.json"] == m.json_bytes(policy.new_manifest(manifest["attempt_id"])), "initial plan changed")
    rt.require(files["context.json"] == m.json_bytes({"source": manifest["source"], "runtime": observed}), "context changed")
    allowed = {"manifest.json", "planned.json", "context.json"}
    pair = m.materialize_pair(manifest["plan"]["identities"][0])
    for record, generated in zip(manifest["datasets"], pair):
        saved = _read_dataset(files.__getitem__, record["identity"])
        rt.require(saved == generated.files(), "registered pair replay differs")
        for entry, name in zip(record["files"], m.DATASET_FILES):
            _same(entry, policy.file_record(entry["path"], saved[name]), "dataset snapshot differs")
            allowed.add(entry["path"])
    del pair, saved
    for index, slot in enumerate(manifest["slots"]):
        identity = slot["identity"]
        result_path = slot["evaluation"]["path"]
        raw = files[result_path]
        _same(slot["evaluation"], policy.file_record(result_path, raw), "evaluation bytes differ")
        result = v.strict_json(raw)
        saved = _read_dataset(files.__getitem__, identity)
        runner.verify_evaluation(result, identity, saved, checkout)
        status = "inconclusive" if any(p["status"] != "calibrated" for p in result["profiles"]) else "success"
        rt.require(slot["status"] == status, "slot calibration status differs")
        start, done = f"journal/{index:02d}-started.json", f"journal/{index:02d}-done.json"
        rt.require(files[start] == m.json_bytes(identity) and files[done] == m.json_bytes(slot), "slot journal differs")
        allowed.update((start, done, result_path))
        del result, saved, raw
    rt.require(set(files) == allowed, "engineering payload inventory differs")
    rt.require(sum(len(files[name]) for name in allowed - {"manifest.json"}) == manifest["resources"]["payload_bytes"], "payload byte accounting differs")
    return policy.validate_manifest(manifest)


def _execute(store, checkout, observed, name, started, *, boundary, sample_memory):
    """One owned store; seams permit small scheduler fixtures without generation."""
    manifest = policy.new_manifest(name)
    stage, current, written, peak = "source", None, 0, 0

    def check(extra=0):
        nonlocal peak
        peak = max(peak, sample_memory()["peak_private_bytes"])
        resources.check_budget(time.monotonic() - started, peak, written + extra + CONTROL_RESERVE)

    def write(path, raw):
        nonlocal written
        check(len(raw))
        store.write(path, raw)
        written += len(raw)

    def resource_record():
        return {"measurement_end": "before_publication", "elapsed_seconds": time.monotonic() - started,
                "peak_worker_private_bytes": peak, "payload_bytes": written}

    try:
        write("planned.json", m.json_bytes(manifest))
        manifest["source"], manifest["runtime"] = checkout.source_descriptor(), observed
        write("context.json", m.json_bytes({"source": manifest["source"], "runtime": observed}))
        stage = "materialization"
        check()
        pair = m.materialize_pair(manifest["plan"]["identities"][0])
        stage = "dataset_save"
        for record, dataset in zip(manifest["datasets"], pair):
            prefix = "datasets/" + record["identity"]["dataset_id"] + "/"
            entries = []
            for path, raw in dataset.entries:
                write(prefix + path, raw)
                rt.require(store.read(prefix + path) == raw, "dataset save readback differs")
                entries.append(policy.file_record(prefix + path, raw))
            record["files"] = entries
        del pair, dataset, raw
        # Both layers are saved before the first candidate starts.
        for index, slot in enumerate(manifest["slots"]):
            current = slot
            identity = slot["identity"]
            stage = "evaluation"
            boundary()
            check()
            saved = _read_dataset(store.read, identity)
            slot["input_hashes"] = {key: m.sha(saved[path]) for key, path in m.INPUT_FILES.items()}
            write(f"journal/{index:02d}-started.json", m.json_bytes(identity))
            result = runner.compute_evaluation(identity, saved, checkout)
            rt.require(_read_dataset(store.read, identity) == saved, "input changed during computation")
            path = "evaluations/" + identity["evaluation_id"] + ".json"
            raw = m.json_bytes(result)
            write(path, raw)
            slot["evaluation"] = policy.file_record(path, raw)
            slot["status"] = "inconclusive" if any(p["status"] != "calibrated" for p in result["profiles"]) else "success"
            write(f"journal/{index:02d}-done.json", m.json_bytes(slot))
            del saved, result, raw
            current = None
            print(json.dumps({"event": "evaluation_saved", "slot": index + 1, "status": slot["status"]}), flush=True)
        check()
        policy.refresh_coverage(manifest)
        manifest["state"], manifest["resources"] = "complete", resource_record()
        policy.validate_manifest(manifest)
        write("manifest.json", m.json_bytes(manifest))
        stage = "replay"

        def verify(files):
            _verify_payloads(files, checkout, observed)

        def publication_boundary():
            nonlocal stage
            stage = "publication"
            boundary()
            check()

        receipt = store.publish(verify, publication_boundary)
        return {"receipt": receipt, "manifest": manifest, "resources_at_publication": resource_record()}
    except Exception as error:
        # Only already-owned evidence is retained. No repair, resume or cleanup.
        if not store.commit_attempted:
            if current is not None and current["input_hashes"] is not None:
                current.update(status="failed", evaluation=None)
            manifest["state"] = "failed"
            manifest["failure"] = {"stage": "resource" if isinstance(error, resources.ResourceStop) else stage,
                "reason": error.reason if isinstance(error, resources.ResourceStop) else
                          "integrity" if isinstance(error, v.V03ValidationError) else "exception"}
            manifest["resources"] = resource_record()
            policy.refresh_coverage(manifest)
            try:
                store.preserve_failure(manifest)
            except Exception:
                pass  # Original failure wins; supervisor records nonzero exit.
        raise


def _root(root):
    root = rt.regular_path(root, directory=True)
    rt.require(root == Path(__file__).resolve().parents[2], "execute the entrypoint from the pinned checkout")
    return root


def _worker(root, revision, name, started):
    resources.check_budget(time.monotonic() - started, 0, 0)
    root = _root(root)
    parent = root / policy.OUTPUT_PARENT
    observed = resources.probe_runtime(parent)
    checkout = rt.capture_checkout(root, revision)
    resources.require_start_resources(parent)

    def boundary():
        checkout.recheck()
        _same(resources.probe_runtime(parent), observed, "runtime changed during attempt")

    with storage.LocalPublication(parent, policy.attempt_name(name)) as store:
        result = _execute(store, checkout, observed, name, started,
                          boundary=boundary, sample_memory=resources.memory_bytes)
    # Same producer, new read-only reader after every writer handle is closed.
    verified = storage.verify_local_publication(Path(result["receipt"]["output_path"]),
        expected_marker_sha256=result["receipt"]["marker_raw_sha256"],
        verify_semantics=lambda files: _verify_payloads(files, checkout, observed))
    boundary()
    resources.check_budget(time.monotonic() - started, resources.memory_bytes()["peak_private_bytes"],
                           result["resources_at_publication"]["payload_bytes"] + CONTROL_RESERVE)
    return {"receipt": result["receipt"], "verification": verified,
            "coverage": result["manifest"]["coverage"], "performance_status": "not_evaluated", "formal_permission": False}


def supervise(root, revision, name):
    root, name = _root(root), policy.attempt_name(name)
    parent = root / policy.OUTPUT_PARENT
    # Observe the existing checkout volume before creating the dedicated parent.
    observed = resources.probe_runtime(root)
    free_before = resources.require_start_resources(root)
    rt.require(rt._git(root, "rev-parse", "HEAD").decode().strip() == revision, "HEAD changed")
    rt.require(not rt._git(root, "status", "--porcelain", "--untracked-files=no"), "tracked source dirty")
    rt.regular_path(parent, directory=True, missing=True)
    parent.mkdir(parents=True, exist_ok=True)
    rt.require(not (parent / name).exists(), "attempt already exists")
    control = parent / (name + "-control")
    control.mkdir()  # retained even if worker never claims its output
    started, peak, reason = time.monotonic(), 0, None
    entrypoint = root / "tools/evaluator/run_anomaly_v03_engineering.py"
    argv = [sys.executable, "-B", str(entrypoint), "_worker", "--root", str(root),
            "--expected-head", revision, "--name", name, "--started", str(started)]
    process, errors, free_after = None, [], None

    def observation_error(stage, error):
        errors.append({"stage": stage, "error_type": type(error).__name__})

    try:
        with (control / "stdout.jsonl").open("xb") as stdout, (control / "stderr.json").open("xb") as stderr:
            process = subprocess.Popen(argv, cwd=root, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                creationflags=subprocess.CREATE_NO_WINDOW)
            while process.poll() is None:
                try:
                    peak = max(peak, resources.memory_bytes(process._handle)["peak_private_bytes"])
                    resources.check_budget(time.monotonic() - started, peak, 0)
                except resources.ResourceStop as error:
                    reason = error.reason
                    process.kill()
                    break
                time.sleep(0.25)
            process.wait(timeout=30)
            try:
                peak = max(peak, resources.memory_bytes(process._handle)["peak_private_bytes"])
            except Exception as error:
                observation_error("final_worker_memory", error)
    except Exception as error:
        observation_error("supervisor", error)
        if reason is None:
            reason = "supervision_error"
    finally:
        if process is not None and process.poll() is None:
            try:
                process.kill()
            except Exception as error:
                observation_error("worker_stop", error)
            try:
                process.wait(timeout=30)
            except Exception as error:
                observation_error("worker_reap", error)
    elapsed = time.monotonic() - started
    if reason is None:
        try:
            resources.check_budget(elapsed, peak, 0)
        except resources.ResourceStop as error:
            reason = error.reason
    try:
        free_after = resources.free_resources(root)
    except Exception as error:
        observation_error("free_resources_after", error)
    exit_code = process.returncode if process is not None else None
    result = {"policy_id": policy.POLICY_ID, "scope": policy.SCOPE, "attempt_id": name,
              "worker_pid": process.pid if process is not None else None, "exit_code": exit_code,
              "worker_exit_confirmed": exit_code is not None,
              "status": "complete" if exit_code == 0 and reason is None and not errors else "failed",
              "stop_reason": reason, "elapsed_seconds": elapsed, "peak_worker_private_bytes": peak,
              "resource_measurement_scope": "whole_worker_including_replays_and_exit",
              "observation_errors": errors, "runtime": observed, "free_before": free_before, "free_after": free_after,
              "worker_log": str(control / "stdout.jsonl"), "formal_permission": False,
              "performance_status": "not_evaluated"}
    storage._exclusive(control / "supervision.json", m.json_bytes(result))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Fixed six-cell single-writer engineering trial")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("plan", help="print fixed metadata without generating data")
    for command in ("run", "_worker"):
        sub = commands.add_parser(command, help="run the bounded trial" if command == "run" else argparse.SUPPRESS)
        sub.add_argument("--root", type=Path, required=True)
        sub.add_argument("--expected-head", required=True)
        sub.add_argument("--name", required=True)
        if command == "_worker":
            sub.add_argument("--started", type=float, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            result = policy.new_manifest("planned")
            policy.validate_manifest(result)
        elif args.command == "run":
            result = supervise(args.root, args.expected_head, args.name)
        else:
            result = _worker(args.root, args.expected_head, args.name, args.started)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
        return 0 if result.get("status") != "failed" else 2
    except (OSError, ValueError) as error:
        print(json.dumps({"status": "failed", "error_type": type(error).__name__, "message": str(error)}), file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
