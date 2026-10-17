"""One saved dev/smoke dataset, one or two scorers, honest status and replay.

This is a local engineering evaluation. It does not launch the formal campaign,
generate observations, select a winner, or change its acceptance permissions.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_materializer as m
from banto_ai import anomaly_v03_runner as runner
from banto_ai import _anomaly_v03_contract as c
from banto_ai import _anomaly_v03_runtime as rt
from banto_ai import _anomaly_v03_engineering_runtime as resources

SOURCE_MODULES = (
    "manifest", "generator", "anomaly_v03", "_anomaly_v03_contract",
    "_anomaly_v03_schema", "_anomaly_v03_numeric", "anomaly_v03_scoring",
    "anomaly_v03_episodes", "anomaly_v03_materializer", "anomaly_v03_runner",
    "_anomaly_v03_runtime", "_anomaly_v03_io", "anomaly_v03_engineering_contract",
    "_anomaly_v03_engineering_runtime",
)
CONFIG_PATH = "examples/configs/anomaly-candidates-v0.3.json"
SOURCE_PATHS = tuple(sorted((*("src/banto_ai/" + n + ".py" for n in SOURCE_MODULES),
                             "tools/evaluator/run_representative_anomaly.py", CONFIG_PATH)))
FORMAT = "representative-anomaly-evaluation-v1"


def pin(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def read(path, maximum=16 * 1024**2):
    path = rt.regular_path(Path(path))
    rt.require(path.stat().st_size <= maximum, "input byte limit")
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    rt.require(len(raw) <= maximum, "input byte limit")
    return raw


def pinned_json(path, digest):
    rt.require(re.fullmatch("[0-9a-f]{64}", digest) is not None, "expected SHA256 required")
    raw = read(path, 512 * 1024)
    rt.require(pin(raw)["sha256"] == digest, "manifest SHA256 mismatch")
    return v.strict_json(raw)


def allowed_identity(identity):
    v.validate_identity(identity)
    rt.require(identity["role"] in ("dev", "smoke"), "holdout is not permitted")
    return identity


def load_input(manifest_path, digest, dataset_id):
    manifest_path = rt.regular_path(Path(manifest_path))
    manifest = pinned_json(manifest_path, digest)
    rt.require(manifest["state"] == "complete", "source dataset publication incomplete")
    selected = [d for d in manifest["datasets"] if d["identity"]["dataset_id"] == dataset_id]
    rt.require(len(selected) == 1, "dataset not uniquely present")
    record = selected[0]
    identity = allowed_identity(record["identity"])
    prefix = "datasets/" + dataset_id + "/"
    rt.require({p["path"] for p in record["files"]} == {prefix + n for n in m.DATASET_FILES},
               "dataset inventory mismatch")
    files = {}
    for p in record["files"]:
        raw = read(manifest_path.parent / p["path"])
        rt.require(pin(raw) == {"bytes": p["bytes"], "sha256": p["sha256"]}, "dataset pin mismatch")
        files[p["path"][len(prefix):]] = raw
    return identity, files, {"manifest_path": str(manifest_path), "manifest_sha256": digest}


def replay_input(path, digest):
    path = rt.regular_path(Path(path), directory=True)
    previous = pinned_json(path / "manifest.json", digest)
    rt.require(previous["format"] == FORMAT and previous["status"] == "complete", "run is not complete")
    identity = allowed_identity(previous["identity"])
    files = {}
    rt.require(set(previous["input_files"]) == set(m.DATASET_FILES), "replay input inventory mismatch")
    for name, expected in previous["input_files"].items():
        raw = read(path / "input" / name)
        rt.require(pin(raw) == expected, "replay input pin mismatch")
        files[name] = raw
    for cell in previous["cells"]:
        rt.require(cell["status"] == "success", "replay requires successful cells")
        rt.require(pin(read(path / cell["result_path"], 32 * 1024**2)) == cell["result_pin"],
                   "previous result pin mismatch")
    return identity, files, previous


def capture_source():
    calls, started = [], time.monotonic()

    def git(*args):
        remaining = 30 - (time.monotonic() - started)
        rt.require(remaining > 0, "Git time budget")
        p = subprocess.run(["git", "-c", "core.fsmonitor=false", "-C", str(ROOT), *args],
                           capture_output=True, timeout=remaining, check=False,
                           env={**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_NO_LAZY_FETCH": "1"})
        calls.append({"args": list(args), "exit_code": p.returncode,
                      "stdout": pin(p.stdout), "stderr": pin(p.stderr)})
        rt.require(len(p.stdout) <= 1024**2 and len(p.stderr) <= 131072 and p.returncode == 0,
                   "Git source capture failed")
        return p.stdout

    revision = git("rev-parse", "HEAD").decode().strip()
    rt.require(re.fullmatch("[0-9a-f]{40}", revision) is not None, "full code revision required")
    rt.require(not git("status", "--porcelain", "--untracked-files=no"), "tracked checkout dirty")
    entries, total = [], 0
    for name in SOURCE_PATHS:
        raw = read(ROOT / name, 131072)
        committed = git("show", revision + ":" + name)
        rt.require(raw == committed or raw.replace(b"\r\n", b"\n") == committed,
                   "calculator working/Git source mismatch: " + name)
        entries.append((name, raw))
        total += len(raw)
    rt.require(len(entries) <= 16 and total <= 512 * 1024, "source batch bound")
    return rt.Checkout(ROOT, revision, tuple(entries)), calls


def source_unchanged(checkout):
    rt.require(all(read(ROOT / n, 131072) == raw for n, raw in checkout.entries), "calculator source changed")


def numerical_pin(result):
    return pin(m.json_bytes({k: val for k, val in result.items() if k != "provenance"}))


def run(output, *, manifest_path=None, manifest_sha256=None, dataset_id=None,
        candidates=None, replay=None):
    output = Path(output).absolute()
    rt.require(output.is_relative_to(ROOT / "artifacts"), "output must be under repository artifacts")
    rt.regular_path(output.parent, directory=True)
    output.mkdir()  # Existing run IDs are never overwritten or retried.
    started = time.monotonic()
    record = {"format": FORMAT, "run_id": output.name, "status": "running", "cells": [],
              "formal_permission": False, "performance_status": "not_evaluated", "failure": None}
    byte_count, file_count, peak_sampled = 0, 0, 0

    def check():
        nonlocal peak_sampled
        peak_sampled = max(peak_sampled, resources.memory_bytes()["peak_private_bytes"])
        resources.check_budget(time.monotonic() - started, peak_sampled, byte_count)

    def write(name, raw):
        nonlocal byte_count, file_count
        check()
        rt.require(file_count < 32 and len(raw) <= 32 * 1024**2, "evaluation file bound")
        rt.require(byte_count + len(raw) + 1024**2 <= 1024**3, "evaluation output bound")
        path = output / name
        path.parent.mkdir(exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
        byte_count += len(raw)
        file_count += 1
        rt.require(read(path, 32 * 1024**2) == raw, "saved bytes differ")
        return pin(raw)

    try:
        write("started.json", m.json_bytes(record))
        if replay:
            identity, files, previous = replay_input(replay, manifest_sha256)
            candidates = [cell["candidate_id"] for cell in previous["cells"]]
            origin = {"replay_of": previous["run_id"], "manifest_sha256": manifest_sha256}
        else:
            identity, files, origin = load_input(manifest_path, manifest_sha256, dataset_id)
            previous = None
            candidates = candidates or list(c.CANDIDATES[:2])
        rt.require(1 <= len(candidates) <= 2 and len(set(candidates)) == len(candidates)
                   and all(x in c.CANDIDATES for x in candidates), "one or two distinct candidates required")
        record.update(identity=identity, origin=origin, input_files={n: pin(raw) for n, raw in files.items()},
                      cells=[{"candidate_id": x, "status": "not_started", "metrics": None} for x in candidates])
        checkout, calls = capture_source()
        record.update(code_revision=checkout.revision, calculator_sources=checkout.source_descriptor(),
                      runtime={"python": sys.version, "executable": sys.executable,
                               "system": platform.system(), "machine": platform.machine()},
                      resource_limits={"wall_seconds": 900, "private_bytes": 2 * 1024**3, "output_bytes": 1024**3},
                      resource_measurement="private bytes at checkpoints; blocking computation not interrupted")
        if previous:
            rt.require(record["calculator_sources"]["sources"] == previous["calculator_sources"]["sources"],
                       "replay calculator version differs")
        for name, raw in files.items():
            write("input/" + name, raw)
        config = {"candidate_config": v.strict_json(dict(checkout.entries)[CONFIG_PATH]),
                  "compiled_candidate_config": c.config_values(c.BOOTSTRAP_HASH, c.GOLDEN_DRAWS)[1],
                  "seed": identity["seed"], "layout": identity["layout"], "stratum": identity["stratum"],
                  "candidates": candidates}
        record["configuration_pin"] = write("configuration.json", m.json_bytes(config))
        write("source-snapshot.json", m.json_bytes({"git_calls": calls, "source_scope": "declared calculator and budget helpers",
              "files": {n: base64.b64encode(raw).decode("ascii") for n, raw in checkout.entries}}))
        write("planned.json", m.json_bytes(record))
        for index, cell in enumerate(record["cells"]):
            check()
            source_unchanged(checkout)
            cell["status"] = "running"
            write(f"cell-{index}-started.json", m.json_bytes(cell))
            evaluation_identity = m.identity_for(identity, identity["stratum"], cell["candidate_id"])
            result = runner.compute_evaluation(evaluation_identity, files, checkout)
            source_unchanged(checkout)
            check()
            rt.require(result["identity"] == evaluation_identity, "returned candidate/input differs")
            rt.require(result["input_hashes"] == {k: pin(files[n])["sha256"] for k, n in m.INPUT_FILES.items()},
                       "returned input hashes differ")
            cell.update(result_path=f"evaluation-{index}.json", numerical_pin=numerical_pin(result),
                        metrics=result["metrics"], row_counts=result["row_counts"])
            cell["result_pin"] = write(cell["result_path"], m.json_bytes(result))
            if previous:
                cell["replay_equal"] = cell["numerical_pin"] == previous["cells"][index]["numerical_pin"]
                rt.require(cell["replay_equal"], "recomputed scores/profiles/metrics differ")
            next_status = "success" if result["status"]["engineering_status"] == "pass" else "inconclusive"
            write(f"cell-{index}-done.json", m.json_bytes({**cell, "status": next_status}))
            cell["status"] = next_status
            print(json.dumps({"candidate": cell["candidate_id"], "status": cell["status"],
                              "score_rows": cell["row_counts"]["scores"]}), flush=True)
            del result
        record["status"] = "complete" if all(x["status"] == "success" for x in record["cells"]) else "inconclusive"
        record["successful_cells"] = sum(x["status"] == "success" for x in record["cells"])
    except BaseException as error:
        for cell in record["cells"]:
            if cell["status"] == "running":
                cell.update(status="failed", metrics=None)
        record.update(status="failed", failure={"type": type(error).__name__, "message": str(error)},
                      successful_cells=sum(x["status"] == "success" for x in record["cells"]))
        raise
    finally:
        record.update(elapsed_seconds=time.monotonic() - started, peak_sampled_private_bytes=peak_sampled)
        # Failure status must survive even when a resource checkpoint rejects.
        with (output / "manifest.json").open("xb") as stream:
            stream.write(m.json_bytes(record))
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--input-manifest", type=Path)
    mode.add_argument("--replay", type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--dataset-id")
    parser.add_argument("--candidate", action="append", choices=c.CANDIDATES)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run(args.output, manifest_path=args.input_manifest, manifest_sha256=args.manifest_sha256,
                     dataset_id=args.dataset_id, candidates=args.candidate, replay=args.replay)
    except Exception as error:
        print(json.dumps({"status": "failed", "type": type(error).__name__, "message": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps({"run_id": result["run_id"], "status": result["status"],
                      "manifest_pin": pin((args.output / "manifest.json").read_bytes())}), flush=True)
    return 0 if result["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
