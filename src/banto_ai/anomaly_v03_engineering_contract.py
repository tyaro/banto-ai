"""Adopted single-writer engineering policy. Metadata only; never runs science.

This separate scope does not satisfy or open the original S4 campaign gate.
Manifest validation checks declarations; saved-byte replay is still required.
"""
from __future__ import annotations

import math
import re
from collections import Counter

from . import _anomaly_v03_contract as c
from . import anomaly_v03 as v
from . import anomaly_v03_materializer as m
from ._anomaly_v03_runtime import require

POLICY_ID = "anomaly-v03-single-writer-v1"
PLAN_FORMAT = "anomaly-v03-engineering-plan-v1"
MANIFEST_FORMAT = "anomaly-v03-engineering-run-v1"
SCOPE = "engineering-dev"
OUTPUT_PARENT = "artifacts/anomaly-v03-engineering-dev"
STATES = ("not_started", "success", "inconclusive", "failed")
STAGES = ("source", "runtime", "materialization", "dataset_save", "evaluation", "replay", "publication", "resource")
REASONS = ("exception", "integrity", "time_limit", "memory_limit", "output_limit", "insufficient_resources", "worker_exit")


def limits():
    return {"wall_seconds": 900, "worker_private_bytes": 2 * 1024**3,
            "output_bytes": 1024**3, "minimum_free_ram_bytes": 4 * 1024**3,
            "minimum_free_disk_bytes": 20 * 1024**3}


def fixed_plan():
    """Fresh, ordered metadata; all three candidates on one registered dev pair."""
    identities = v.evaluation_inventory("dev")[:6]
    return {"format": PLAN_FORMAT, "policy_id": POLICY_ID, "scope": SCOPE,
            "science": {"science_revision": c.SCIENCE_REVISION, "post_audit_revision": c.STATUS_REVISION,
                        "registry_raw_sha256": v.REGISTRY_RAW_SHA256, "seed_list_sha256": c.SEED_HASH},
            "identities": identities, "limits": limits(),
            "planned_counts": {"seeds": 1, "layouts": 1, "datasets": 2, "evaluations": 6,
                               "observation_rows": 36000, "profiles": 288, "score_rows": 86400},
            "performance_status": "not_evaluated", "promotion_allowed": False,
            "formal_permission": False, "acceptance_status": "not_completed"}


def _exact(value, expected, message):
    require(v.canonical_json(value) == v.canonical_json(expected), message)


def _keys(value, names, message):
    require(type(value) is dict and set(value) == set(names.split()), message)


def _integer(value, minimum=0):
    return type(value) is int and value >= minimum


def _hash(value):
    return type(value) is str and re.fullmatch("[0-9a-f]{64}", value) is not None


def attempt_name(value):
    require(type(value) is str and re.fullmatch(r"[a-z][a-z0-9-]{0,63}", value), "invalid engineering attempt name")
    require(not value.startswith("anomaly-multiseed-v0"), "formal name is not an engineering attempt")
    return value


def validate_runtime(observed):
    """Validate a supplied observation, never fabricate the OS build from a pin."""
    expected = c.formal_runtime()
    require(type(observed) is dict and set(observed) == set(expected), "engineering runtime inventory")
    for key in ("os_build", "os_ubr"):
        require(_integer(observed[key], 22000 if key == "os_build" else 0), "invalid observed OS version")
        expected[key] = observed[key]
    _exact(observed, expected, "unsupported engineering runtime")


def validate_source(source):
    _keys(source, "revision sources", "engineering source descriptor")
    require(type(source["revision"]) is str and re.fullmatch("[0-9a-f]{40}", source["revision"]), "source revision")
    require(type(source["sources"]) is list and source["sources"], "empty source inventory")
    names = []
    for entry in source["sources"]:
        _keys(entry, "path raw_sha256 byte_count", "source entry inventory")
        names.append(v.safe_relative_path(entry["path"]))
        require(_hash(entry["raw_sha256"]) and _integer(entry["byte_count"]), "source entry hash/size")
    require(names == sorted(set(names)), "source order/uniqueness")


def file_record(path, raw):
    require(type(raw) is bytes, "file record requires bytes")
    return {"path": v.safe_relative_path(path), "bytes": len(raw), "sha256": m.sha(raw)}


def _file(value, path):
    _keys(value, "path bytes sha256", "saved file descriptor")
    require(value["path"] == path and _integer(value["bytes"]) and _hash(value["sha256"]), "saved file path/hash/size")


def new_manifest(name):
    plan = fixed_plan()
    return {"format": MANIFEST_FORMAT, "plan": plan, "attempt_id": attempt_name(name),
            "source": None, "runtime": None, "state": "planned", "failure": None,
            "datasets": [{"identity": plan["identities"][i], "files": None} for i in (0, 3)],
            "slots": [{"identity": identity, "status": "not_started", "input_hashes": None,
                       "evaluation": None} for identity in plan["identities"]],
            "coverage": dict.fromkeys(STATES, 0) | {"not_started": 6},
            "resources": {"measurement_end": "before_publication", "elapsed_seconds": 0.0,
                          "peak_worker_private_bytes": 0, "payload_bytes": 0}}


def refresh_coverage(manifest):
    counts = Counter(slot["status"] for slot in manifest["slots"])
    manifest["coverage"] = {state: counts[state] for state in STATES}


def validate_manifest(value):
    """Structural/accounting checks only, never proof of execution or trust."""
    _keys(value, "format plan attempt_id source runtime state failure datasets slots coverage resources", "manifest fields")
    require(value["format"] == MANIFEST_FORMAT, "engineering manifest format")
    plan = fixed_plan()
    _exact(value["plan"], plan, "fixed engineering plan changed")
    attempt_name(value["attempt_id"])
    state = value["state"]
    require(type(state) is str and state in ("planned", "failed", "complete"), "manifest state")
    require((value["source"] is None) == (value["runtime"] is None), "partial source/runtime context")
    if value["source"] is not None:
        validate_source(value["source"])
        validate_runtime(value["runtime"])
    datasets, slots = value["datasets"], value["slots"]
    require(type(datasets) is list and len(datasets) == 2 and type(slots) is list and len(slots) == 6, "fixed dataset/slot count")
    dataset_hashes = {}
    known_bytes = 0
    for row, index in zip(datasets, (0, 3)):
        _keys(row, "identity files", "dataset fields")
        ident = plan["identities"][index]
        _exact(row["identity"], ident, "dataset identity/order")
        entries = row["files"]
        if entries is None:
            continue
        require(type(entries) is list and len(entries) == len(m.DATASET_FILES), "dataset files count")
        for entry, name in zip(entries, m.DATASET_FILES):
            _file(entry, "datasets/" + ident["dataset_id"] + "/" + name)
            known_bytes += entry["bytes"]
        hashes = {name: entry["sha256"] for name, entry in zip(m.DATASET_FILES, entries)}
        dataset_hashes[ident["dataset_id"]] = {key: hashes[name] for key, name in m.INPUT_FILES.items()}
    ended = False
    failure_count = 0
    for row, ident in zip(slots, plan["identities"]):
        _keys(row, "identity status input_hashes evaluation", "slot fields")
        _exact(row["identity"], ident, "slot identity/order")
        status = row["status"]
        require(type(status) is str and status in STATES, "slot status")
        if status == "not_started":
            ended = True
            require(row["input_hashes"] is None and row["evaluation"] is None, "not_started has results")
            continue
        require(not ended, "nonsequential slot execution")
        require(len(dataset_hashes) == 2 and value["source"] is not None, "evaluation before saved pair/context")
        _exact(row["input_hashes"], dataset_hashes[ident["dataset_id"]], "paired candidate input hashes")
        if status == "failed":
            failure_count += 1
            ended = True
            require(row["evaluation"] is None, "failed slot claims verified evaluation")
        else:
            _file(row["evaluation"], "evaluations/" + ident["evaluation_id"] + ".json")
            known_bytes += row["evaluation"]["bytes"]
    counts = Counter(row["status"] for row in slots)
    _exact(value["coverage"], {s: counts[s] for s in STATES}, "coverage counts")
    resource = value["resources"]
    _keys(resource, "measurement_end elapsed_seconds peak_worker_private_bytes payload_bytes", "resource fields")
    require(resource["measurement_end"] == "before_publication", "resource measurement scope")
    require(type(resource["elapsed_seconds"]) in (int, float) and math.isfinite(resource["elapsed_seconds"])
            and resource["elapsed_seconds"] >= 0, "elapsed time")
    require(_integer(resource["peak_worker_private_bytes"]) and _integer(resource["payload_bytes"])
            and resource["payload_bytes"] >= known_bytes, "resource byte accounting")
    if state == "planned":
        _exact(value, new_manifest(value["attempt_id"]), "planned manifest contains execution")
    elif state == "complete":
        require(value["failure"] is None and counts["success"] + counts["inconclusive"] == 6, "incomplete claimed completion")
        require(resource["elapsed_seconds"] <= limits()["wall_seconds"]
                and resource["peak_worker_private_bytes"] <= limits()["worker_private_bytes"]
                and resource["payload_bytes"] <= limits()["output_bytes"], "completed beyond resource limit")
    else:
        _keys(value["failure"], "stage reason", "failed manifest needs reason")
        require(value["failure"]["stage"] in STAGES and value["failure"]["reason"] in REASONS, "failure classification")
        require(failure_count <= 1, "multiple stopped slots")
    return {"validation_status": "engineering_manifest_contract_valid", "result_trusted": False,
            "scope": SCOPE, "state": state, "coverage": dict(value["coverage"]),
            "performance_status": "not_evaluated", "formal_permission": False}
