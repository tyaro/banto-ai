"""Pure S1 v0.3 registry and ledger-contract validation.

All public validators consume decoded values or caller-supplied bytes. They never
open files, inspect the environment, resolve paths, generate observations, score,
match incidents, publish, or grant run permission. A result passing these checks
is only structurally consistent; S2/S3/S6 must independently recompute numerical
profiles, scores, episodes, matching, metrics and gates from captured observations.

The caller's trusted checkout pins this module plus REGISTRY_RAW_SHA256 below.
S1 commit identity is pinned OUTSIDE the JSON registry by the next savepoint.
Reading a hash from an untrusted registry and trusting it is never sufficient.
Runtime I/O must reject symlink/junction/any reparse-point traversal, validate
root containment, runtime/OS/source inventory and non-overwrite semantics before
generation or publication. safe_relative_path checks spelling only, not topology.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from typing import Any, Mapping

from . import _anomaly_v03_contract as c
from ._anomaly_v03_schema import common_defs, schemas
from .manifest import ManifestValidationError, validate

# Trusted external pins for these persisted S1 JSON bytes; no self-reference.
REGISTRY_RAW_SHA256 = "6b612def66bf577870489f5935c634c4d7cd1d4d49531ef0e674e226374bfec1"
REGISTRY_CANONICAL_SHA256 = "48caf57b3e45ed115cb757ef35638648f53b3294271ac1300688dd6928c1166b"
PLAN_SCIENCE_RAW_SHA256 = "8eef3a6dc094e9d48a321fe526e85c75e6876caf6023730c005381da4e762bc5"
PLAN_STATUS_RAW_SHA256 = "15e97cfa798618d6822664fc13e53a05279633dde1b0514fc52f6367d073e0c1"

__all__ = ["V03ValidationError", "strict_json", "canonical_json", "canonical_sha256",
           "safe_relative_path", "seed_registry", "bootstrap_indices", "validate_bundle",
           "validate_decoded_configs", "validate_result_contract", "validate_ledger_rows",
           "evaluation_inventory", "event_inventory", "validate_identity"]


class V03ValidationError(ValueError):
    """Strict S1 contract violation; never a performance result."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise V03ValidationError(message)


def json_value(value: Any) -> None:
    """Reject Python-only values and all nonfinite numbers before schema work."""
    if type(value) in (str, bool, int, type(None)):
        if type(value) is str:
            try:
                value.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise V03ValidationError("invalid Unicode scalar") from exc
        return
    if type(value) is float:
        require(math.isfinite(value), "nonfinite number")
    elif type(value) is list:
        for item in value:
            json_value(item)
    elif type(value) is dict:
        for key, item in value.items():
            require(type(key) is str, "JSON key is not a string")
            json_value(key)
            json_value(item)
    else:
        raise V03ValidationError("not a JSON value")


def strict_json(raw: bytes | str) -> Any:
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    def constant(_):
        raise V03ValidationError("nonfinite JSON constant")

    require(type(raw) in (str, bytes), "JSON input must be str or bytes")
    try:
        text = raw.decode("utf-8") if type(raw) is bytes else raw
        value = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
        json_value(value)
        return value
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise V03ValidationError("invalid strict UTF-8 JSON") from exc


def canonical_json(value: Any) -> bytes:
    json_value(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def safe_relative_path(value: Any) -> str:
    """Lexical-only path policy, deliberately without pathlib/os/I/O probes."""
    require(type(value) is str and bool(re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_./-]*", value)), "unsafe relative path")
    for part in value.split("/"):
        require(part not in ("", ".", "..") and not part.endswith((".", " ")), "path traversal or ambiguous component")
        require(part.split(".")[0].upper() not in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(10)), *(f"LPT{i}" for i in range(10))}, "reserved Windows path component")
    return value


def _paths(value: Any) -> None:
    if type(value) is dict:
        for key, item in value.items():
            if type(item) is str and (key == "path" or key.endswith(("_path", "_root"))):
                safe_relative_path(item)
            _paths(item)
    elif type(value) is list:
        for item in value:
            _paths(item)


def _shape(value: Any, schema: dict) -> None:
    json_value(value)
    try:
        validate(value, schema)
    except (ManifestValidationError, KeyError, TypeError, ValueError) as exc:
        raise V03ValidationError(f"schema violation: {exc}") from exc
    _paths(value)


def seed_registry() -> dict:
    return c.seed_registry()


def bootstrap_indices() -> bytes:
    result = c.bootstrap_indices()
    require(hashlib.sha256(result).hexdigest() == c.BOOTSTRAP_HASH, "bootstrap golden digest mismatch")
    for draw in c.GOLDEN_DRAWS:
        start = draw["replicate"] * 40
        require(list(result[start:start+40]) == draw["indices"], "bootstrap golden draw mismatch")
    return result


def _expected_configs() -> list[dict]:
    return c.config_values(c.BOOTSTRAP_HASH, c.GOLDEN_DRAWS)


def validate_decoded_configs(configs: Mapping[str, Any]) -> dict:
    """Exact frozen semantic values, independent of raw byte/hash validation."""
    require(type(configs) is dict and set(configs) == set(c.CONFIG_PATHS[:4]), "config inventory mismatch")
    expected = _expected_configs()
    for path, value, schema in zip(c.CONFIG_PATHS[:4], expected, schemas(expected)[:4]):
        _shape(configs[path], schema)
        # Canonical equality preserves bool/int and integer/float distinctions.
        require(canonical_json(configs[path]) == canonical_json(value), f"frozen config disagreement: {path}")
    return _validation_report()


def _validation_report() -> dict:
    return {"validation_status": "configuration_valid", "run_status": "not_run",
            "engineering_status": "not_evaluated", "performance_status": "not_evaluated",
            "runtime_io_status": "not_checked", "s2_semantics_status": "not_implemented"}


def validate_bundle(snapshots: Mapping[str, bytes], *, science_plan_raw: bytes, status_plan_raw: bytes) -> dict:
    """Verify a complete captured bundle using trusted external registry pins.

    snapshots must contain exactly 5 configs + 9 schemas. The two plan snapshots
    come from the two pinned commits, not from a mutable unverified plan path.
    This function cannot attest which Git commit the caller read; that is an I/O
    boundary obligation. It attests that all supplied bytes match the trusted pins.
    """
    require(type(snapshots) is dict and set(snapshots) == set((*c.CONFIG_PATHS, *c.SCHEMA_PATHS)), "snapshot inventory mismatch")
    require(all(type(raw) is bytes for raw in snapshots.values()), "snapshot must be bytes")
    require(type(science_plan_raw) is bytes and type(status_plan_raw) is bytes, "plan snapshot must be bytes")
    registry_raw = snapshots[c.CONFIG_PATHS[4]]
    require(hashlib.sha256(registry_raw).hexdigest() == REGISTRY_RAW_SHA256, "external registry raw pin mismatch")
    registry = strict_json(registry_raw)
    require(canonical_sha256(registry) == REGISTRY_CANONICAL_SHA256, "external registry canonical pin mismatch")
    values = {path: strict_json(raw) for path, raw in snapshots.items()}
    expected = _expected_configs()
    expected_schemas = schemas(expected)
    for path, schema in zip(c.SCHEMA_PATHS, expected_schemas):
        require(canonical_json(values[path]) == canonical_json(schema), f"schema contract changed: {path}")
    _shape(registry, expected_schemas[4])
    require(registry["plan"]["science_raw_sha256"] == PLAN_SCIENCE_RAW_SHA256 == hashlib.sha256(science_plan_raw).hexdigest(), "science plan pin mismatch")
    require(registry["plan"]["status_raw_sha256"] == PLAN_STATUS_RAW_SHA256 == hashlib.sha256(status_plan_raw).hexdigest(), "status plan pin mismatch")
    pins = registry["pins"]
    require([p["path"] for p in pins] == [*c.CONFIG_PATHS[:4], *c.SCHEMA_PATHS], "pin order/inventory mismatch")
    for pin in pins:
        raw = snapshots[pin["path"]]
        require(hashlib.sha256(raw).hexdigest() == pin["raw_sha256"], "raw hash mismatch: " + pin["path"])
        require(canonical_sha256(values[pin["path"]]) == pin["canonical_sha256"], "canonical hash mismatch: " + pin["path"])
    validate_decoded_configs({p: values[p] for p in c.CONFIG_PATHS[:4]})
    require(canonical_json(registry["seed_registry"]) == canonical_json(seed_registry()), "registry seed disagreement")
    require(canonical_json(registry["bootstrap"]) == canonical_json(expected[3]["bootstrap"]), "registry bootstrap disagreement")
    require(canonical_json(registry["runtime"]) == canonical_json(c.formal_runtime()), "registry runtime disagreement")
    return {**_validation_report(), "counts": c.counts("holdout"), "seed_list_canonical_sha256": c.SEED_HASH,
            "bootstrap_indices_raw_sha256": c.BOOTSTRAP_HASH, "registry_raw_sha256": REGISTRY_RAW_SHA256}


def validate_identity(value: dict) -> None:
    defs = common_defs()
    _shape(value, {**defs["identity"], "$defs": defs})
    role = value["role"]
    seeds = c.seed_registry()["entries"][c.ROLES.index(role)]["seeds"]
    require(value["seed"] in seeds, "seed not registered for role")
    pair = f'anomaly-v03-{role}-seed-{value["seed"]}-layout-{value["layout"]:02d}'
    require(value["pair_id"] == pair, "pair ID mismatch")
    require(value["dataset_id"] == pair + "-" + value["stratum"], "dataset ID mismatch")
    require(value["evaluation_id"] == value["dataset_id"] + "-" + value["candidate_id"], "evaluation ID mismatch")


def evaluation_inventory(role: str) -> list[dict]:
    """S1 planned metadata only. Never materializes observations or output roots."""
    require(type(role) is str and role in c.ROLES, "unknown role")
    rows = []
    for seed in c.seed_registry()["entries"][c.ROLES.index(role)]["seeds"]:
        for layout in range(12):
            pair = f"anomaly-v03-{role}-seed-{seed}-layout-{layout:02d}"
            for stratum in c.STRATA:
                dataset = pair + "-" + stratum
                for candidate in c.CANDIDATES:
                    rows.append({"role": role, "seed": seed, "layout": layout, "stratum": stratum,
                                 "candidate_id": candidate, "pair_id": pair, "dataset_id": dataset,
                                 "evaluation_id": dataset + "-" + candidate})
    return rows


def event_inventory(identity: dict) -> list[dict]:
    """40 planned event rows including disabled core quality; no data generation."""
    validate_identity(identity)
    layout = identity["layout"]
    ei, mi = divmod(layout, 6)
    result = []
    events = _expected_configs()[0]["events"]
    for cycle in range(10):
        base = 7200 + 180 * cycle + 30 * mi
        for ci, definition in enumerate(events):
            start = base + (0, 7, 14, 21)[(layout + ci) % 4]
            if ci == 2 and cycle == 9:
                start = base + (0, 7, 14, 21)[(layout+1) % 4] + 1
            result.append({"dataset_id": identity["dataset_id"], "event_id": f'{identity["pair_id"]}-cycle-{cycle:02d}-{c.CLASSES[ci]}',
                           "cycle": cycle, "event_class": c.CLASSES[ci], "equipment": c.EQUIPMENT[ei],
                           "full_target": c.EQUIPMENT[ei] + "." + definition["target_by_equipment"][ei],
                           "mode": c.MODES[mi], "recipe": c.RECIPES[mi], "event_type": definition["type"],
                           "start_sample": start, "end_sample": start+3, "window_end_sample": start+6,
                           "start_ms": c.START_MS+start*1000, "end_ms": c.START_MS+(start+3)*1000,
                           "window_end_ms": c.START_MS+(start+6)*1000, "magnitude": definition["magnitude"],
                           "enabled": ci != 2 or identity["stratum"] == "quality-stress"})
    return result


def _unique(rows: list, key: str) -> dict:
    values = {row[key]: row for row in rows}
    require(len(values) == len(rows), "duplicate " + key)
    return values


def _coordinate(row: dict, identity: dict) -> None:
    require(row.get("dataset_id", identity["dataset_id"]) == identity["dataset_id"], "cross-dataset row")
    require(row.get("candidate_id", identity["candidate_id"]) == identity["candidate_id"], "cross-candidate row")
    if "full_target" in row:
        require(row["full_target"].startswith(row["equipment"] + "."), "equipment/target disagreement")
    require(c.RECIPES[c.MODES.index(row["mode"])] == row["recipe"], "mode/recipe disagreement")


def validate_ledger_rows(identity: dict, *, events: list, profiles: list, scores: list,
                         source_episodes: list, equipment_episodes: list, incidents: list) -> None:
    """Validate claimed row identity/time/split/support relations, not detector math.

    In particular this does not compute residuals, form episodes, enumerate
    matching candidates or establish that supplied numerical scores are correct.
    """
    validate_identity(identity)
    defs = common_defs()
    ledgers = {"event": events, "profile": profiles, "score": scores, "source_episode": source_episodes,
               "equipment_episode": equipment_episodes, "incident": incidents}
    for name, rows in ledgers.items():
        require(type(rows) is list, "ledger must be array")
        for row in rows:
            _shape(row, {**defs[name], "$defs": defs})
    require(canonical_json(events) == canonical_json(event_inventory(identity)), "event layout/overlap/time/stratum inventory mismatch")
    event_map = _unique(events, "event_id")
    profile_map = _unique(profiles, "profile_id")
    score_map = _unique(scores, "score_id")
    source_map = _unique(source_episodes, "episode_id")
    episode_map = _unique(equipment_episodes, "episode_id")
    _unique(incidents, "event_id")
    profile_keys, score_keys = set(), set()
    previous_sample = {}
    for row in profiles:
        _coordinate(row, identity)
        require(canonical_json(row["identity"]) == canonical_json(identity), "profile identity disagreement")
        key = (row["full_target"], row["mode"])
        require(key not in profile_keys, "duplicate profile coordinate")
        profile_keys.add(key)
        for field, lo, hi in (("fit_samples", 1800, 5400), ("calibration_samples", 5400, 7200)):
            samples = row[field]
            require(samples == sorted(set(samples)) and all(lo <= s < hi for s in samples), "profile split violation")
            require(all(c.MODES[(s % 180)//30] == row["mode"] for s in samples), "profile sample mode mismatch")
        if row["status"] == "calibrated":
            require(row["reason"] is None and row["center"] is not None and row["scale"] is not None and row["scale"] > 0, "invalid calibrated profile")
            require(250 <= len(row["calibration_samples"]) <= 290, "calibration point count")
            require(all(s % 30 > 0 for s in row["calibration_samples"]), "calibration includes mode entry")
        else:
            require(row["reason"] is not None, "missing profile reason")
        if identity["candidate_id"] == c.CANDIDATES[0]:
            require(not row["fit_samples"] and row["phase_medians"] is None and row["c2_state"] is None, "C0 fit is no-op")
        elif row["status"] == "calibrated":
            mode_index = c.MODES.index(row["mode"])
            expected_fit = [1800+cycle*180+mode_index*30+phase for cycle in range(20) for phase in range(30)]
            require(row["fit_samples"] == expected_fit and row["phase_medians"] is not None, "phase fit inventory incomplete")
            if identity["candidate_id"] == c.CANDIDATES[1]:
                require(row["c2_state"] is None, "C1 contains C2 state")
            else:
                state = row["c2_state"]
                require(state is not None and all(q > 0 for q in state["scales"]), "C2 scale/state missing")
                require(all(state[name][i][i] > 0 for name in ("covariance", "precision") for i in range(4)), "C2 nonpositive diagonal")
    for row in scores:
        _coordinate(row, identity)
        sample = row["sample"]
        require(7200 <= sample < 9000 and row["timestamp_ms"] == c.START_MS + sample*1000, "score timestamp/test split mismatch")
        require(row["mode"] == c.MODES[(sample % 180)//30], "score mode mismatch")
        require(row["phase"] is None or row["phase"] == sample % 30, "score phase mismatch")
        key = (row["full_target"], sample)
        require(key not in score_keys, "duplicate score coordinate")
        score_keys.add(key)
        require(sample > previous_sample.get(row["full_target"], -1), "reversed score time")
        previous_sample[row["full_target"]] = sample
        require(row["profile_id"] in profile_map, "unknown score profile")
        profile = profile_map[row["profile_id"]]
        require((row["full_target"], row["mode"]) == (profile["full_target"], profile["mode"]), "score/profile coordinate mismatch")
        tags = row["exclusion_tags"]
        require(len(tags) == len(set(tags)), "duplicate exclusion tag")
        if row["available"]:
            require(row["score"] is not None and row["score"] >= 0 and row["residual"] is not None and row["phase"] not in (None, 0), "invalid available score")
            require(row["exclusion_reason"] is None and not tags and profile["status"] == "calibrated", "availability/profile/reason disagreement")
            threshold = 4.0 if identity["candidate_id"] == c.CANDIDATES[0] else 6.0
            require(row["threshold_exceeded"] == (row["score"] > threshold), "reported threshold comparison mismatch")
            require((row["streak"] > 0) == row["threshold_exceeded"], "reported streak/exceedance mismatch")
            require(row["threshold_exceeded"] or row["source_episode_id"] is None, "low score contains episode")
        else:
            require(row["score"] is None and not row["threshold_exceeded"] and row["streak"] == 0 and row["source_episode_id"] is None, "unavailable score pretends to exceed")
            require(bool(tags) and row["exclusion_reason"] == next(r for r in c.REASONS if r in tags), "exclusion priority mismatch")
        deps = row["dependencies"]
        dep_keys = {(d["full_target"], d["sample"]) for d in deps}
        require(len(deps) == len(dep_keys), "duplicate score dependency")
        for dep in deps:
            require(dep["full_target"].startswith(row["equipment"] + "."), "other-equipment dependency")
            require(dep["sample"] in (sample-1, sample) and dep["timestamp_ms"] == c.START_MS+dep["sample"]*1000, "future or invalid support time")
        if row["available"]:
            targets = [row["equipment"] + "." + t for t in c.TARGETS] if identity["candidate_id"] == c.CANDIDATES[2] else [row["full_target"]]
            require(dep_keys == {(t, s) for t in targets for s in (sample-1, sample)}, "dependency allowlist mismatch")
            require(all(d["quality"] == "ok" and d["value"] is not None for d in deps), "available dependency quality")
        if row["source_episode_id"] is not None:
            require(row["source_episode_id"] in source_map, "unknown source episode")
    for row in source_episodes:
        _coordinate(row, identity)
        require(row["onset_ms"] < row["end_ms"] and (row["end_ms"] - c.START_MS) % 1000 == 0, "invalid source interval")
        ids = row["support_score_ids"]
        require(len(set(ids)) == 2 and all(i in score_map for i in ids), "unknown/duplicate support")
        support = [score_map[i] for i in ids]
        require([s["timestamp_ms"] for s in support] == [row["onset_ms"]-1000, row["onset_ms"]], "support-to-onset mismatch")
        require(all(s["available"] and s["threshold_exceeded"] and all(s[k] == row[k] for k in ("full_target", "mode", "recipe", "profile_id")) for s in support), "invalid source support")
        require(support[-1]["sample"]//30*30 == row["visit_start_sample"], "source visit mismatch")
        require([s["streak"] for s in support] == [1, 2], "source onset is not second exceedance")
        require(row["end_ms"] <= c.START_MS+(row["visit_start_sample"]+30)*1000, "source interval crosses visit")
    used_sources = []
    for row in equipment_episodes:
        _coordinate(row, identity)
        ids = row["source_episode_ids"]
        require(len(ids) == len(set(ids)) and all(i in source_map for i in ids), "unknown/duplicate merge source")
        used_sources.extend(ids)
        sources = [source_map[i] for i in ids]
        require(all(all(s[k] == row[k] for k in ("equipment", "mode", "recipe", "visit_start_sample")) for s in sources), "cross-mode/visit merge")
        require(row["onset_ms"] == min(s["onset_ms"] for s in sources) and row["end_ms"] == max(s["end_ms"] for s in sources), "merge interval mismatch")
        ordered = sorted(sources, key=lambda s: (s["onset_ms"], s["full_target"], s["episode_id"]))
        require(ids == [s["episode_id"] for s in ordered], "merge source order mismatch")
        covered_end = ordered[0]["end_ms"]
        for source in ordered[1:]:
            require(source["onset_ms"] <= covered_end, "disconnected merge sources")
            covered_end = max(covered_end, source["end_ms"])
    require(sorted(used_sources) == sorted(source_map), "merge source partition mismatch")
    claims = set()
    for row in incidents:
        require(row["dataset_id"] == identity["dataset_id"] and row["event_id"] in event_map, "unknown incident event")
        require(event_map[row["event_id"]]["event_class"] in ("machine", "sensor"), "nonpositive incident")
        ids = row["candidate_episode_ids"]
        require(row["candidate_count"] == len(ids) and len(ids) == len(set(ids)) and all(i in episode_map for i in ids), "candidate inventory mismatch")
        require(ids == sorted(ids, key=lambda i: (episode_map[i]["onset_ms"], i)), "candidate order mismatch")
        selected = row["selected_candidate_episode_id"]
        require(selected == (ids[0] if ids else None), "selected candidate is not first (retry)")
        if selected is not None:
            require(selected not in claims, "episode claimed twice")
            claims.add(selected)
        if row["selected_source_episode_id"] is not None:
            source_id = row["selected_source_episode_id"]
            require(source_id in source_map and selected is not None and source_id in episode_map[selected]["source_episode_ids"], "unknown selected source")
            require(row["support_score_ids"] == source_map[source_id]["support_score_ids"], "claimed support IDs mismatch")
        else:
            require(not row["support_score_ids"], "support without source")
        if row["status"] != "processed":
            require(row["causal_detected"] is None and row["matched_episode_id"] is None and row["delay_seconds"] is None and row["reason"] == "not_processed", "unprocessed incident filled as miss")
            require(not ids and row["selected_source_episode_id"] is None, "unprocessed incident contains selection")
        elif row["causal_detected"]:
            require(row["reason"] == "causal_detected" and selected is not None and row["matched_episode_id"] == selected, "detection identity mismatch")
            require(row["delay_seconds"] is not None and 1 <= row["delay_seconds"] < 6, "invalid detection delay")
            event = event_map[row["event_id"]]
            require(row["selected_source_episode_id"] is not None, "detected without source support")
            source = source_map[row["selected_source_episode_id"]]
            require(source["full_target"] == event["full_target"] and source["onset_ms"] == episode_map[selected]["onset_ms"], "detected target/onset mismatch")
            require(all(event["start_ms"] <= score_map[i]["timestamp_ms"] < event["window_end_ms"] for i in row["support_score_ids"]), "noncausal detection support")
            require(row["delay_seconds"] == (source["onset_ms"]-event["start_ms"])/1000, "reported delay mismatch")
        else:
            require(row["causal_detected"] is False and row["matched_episode_id"] is None and row["delay_seconds"] is None and row["reason"] not in ("not_processed", "causal_detected"), "invalid miss/null status")
            require((row["reason"] == "no_candidate_in_window") == (selected is None), "miss reason/selection mismatch")
    matched = {r["matched_episode_id"]: r["event_id"] for r in incidents if r["matched_episode_id"] is not None}
    require(all(row["matched_event_id"] == matched.get(row["episode_id"]) for row in equipment_episodes), "event/episode match backlink mismatch")


def validate_result_contract(value: dict) -> dict:
    """Shape + declared-ledger consistency only; never return a run success."""
    types = ("event-aware-anomaly-v03", "anomaly-multiseed-v03", "anomaly-multiseed-analysis-v03", "anomaly-multiseed-audit-v03")
    require(type(value) is dict and value.get("result_type") in types, "unknown result identity")
    schema = schemas(_expected_configs())[5+types.index(value["result_type"])]
    _shape(value, schema)
    require(value["provenance"]["registry_raw_sha256"] == REGISTRY_RAW_SHA256, "result registry pin mismatch")
    _unique(value["provenance"]["inventory"], "path")
    status = value["status"]
    if status["run_status"] != "complete":
        require(status["engineering_status"] != "pass" and status["performance_status"] == "not_evaluated", "unfinished run claims acceptance")
    if status["engineering_status"] != "pass":
        require(status["performance_status"] != "pass", "performance without engineering acceptance")
    kind = value["result_type"]
    if kind in types[:2]:
        require(status["performance_status"] == "not_evaluated", "producer must not decide performance")
    if kind == types[0]:
        ledgers = ("events", "profiles", "scores", "source_episodes", "equipment_episodes", "incidents")
        validate_ledger_rows(value["identity"], **{k: value[k] for k in ledgers})
        require(value["row_counts"] == {k: len(value[k]) for k in ledgers}, "row counts mismatch")
        require({r["event_id"] for r in value["incidents"]} == {e["event_id"] for e in value["events"] if e["event_class"] in ("machine", "sensor")}, "positive inventory incomplete")
        if status["run_status"] == "complete":
            require(len(value["scores"]) == 14400 and len(value["profiles"]) == 48, "incomplete planned rows")
            require(all(i["status"] == "processed" for i in value["incidents"]), "unprocessed incident in complete result")
        if status["run_status"] == "not_run":
            require(not value["scores"] and not value["profiles"] and value["metrics"] is None, "not_run contains computed data")
    elif kind == types[1]:
        require(value["planned_counts"] == c.counts(value["role"]), "planned count mismatch")
        expected = evaluation_inventory(value["role"])
        require(canonical_json([s["identity"] for s in value["evaluations"]]) == canonical_json(expected), "evaluation inventory/order/pairing mismatch")
        tally = Counter(s["status"] for s in value["evaluations"])
        require(value["coverage"] == {s: tally[s] for s in c.SLOT_STATUS}, "slot coverage mismatch")
        paired = {}
        for slot in value["evaluations"]:
            state = slot["status"]
            if state in ("success", "not_started"):
                require(slot["failure_stage"] is None and slot["safe_reason"] is None, "slot failure state mismatch")
            else:
                require(slot["failure_stage"] is not None and slot["safe_reason"] is not None, "failure reason missing")
            if state == "not_started":
                require(slot["input_hashes"] is None and not slot["evidence"], "not_started contains evidence")
            if state == "success":
                require(slot["input_hashes"] is not None and bool(slot["evidence"]), "success missing input/evidence")
            if slot["input_hashes"] is not None:
                key = slot["identity"]["dataset_id"]
                raw = canonical_json(slot["input_hashes"])
                require(key not in paired or paired[key] == raw, "candidate paired input hash mismatch")
                paired[key] = raw
        if status["engineering_status"] == "pass":
            require(tally["partial"] + tally["failed"] + tally["not_started"] == 0, "incomplete engineering coverage")
        if status["run_status"] == "not_run":
            require(tally["not_started"] == len(expected), "not_run has started slots")
    elif kind == types[2]:
        require([(t["candidate_id"], t["stratum"]) for t in value["candidate_tables"]] == [(a,b) for a in c.CANDIDATES for b in (*c.STRATA, "overall")], "candidate table inventory mismatch")
        if status["run_status"] == "not_run":
            require(value["decision"] == "not_evaluated" and all(t["metrics"] is None and not t["gates"] for t in value["candidate_tables"]), "not_run analysis contains computed results")
        if status["run_status"] == "complete":
            require(all(t["metrics"] is not None for t in value["candidate_tables"]), "complete analysis missing metrics")
        if status["performance_status"] != "pass":
            require(value["selected_candidate"] is None and not any(t["qualified"] for t in value["candidate_tables"]), "selection without acceptance")
        if value["decision"] == "not_evaluated":
            require(status["performance_status"] == "not_evaluated", "decision/status mismatch")
        require((value["selected_candidate"] is not None) == (value["decision"] == "qualified"), "decision/selection mismatch")
        require(not any(t["qualified"] for t in value["candidate_tables"] if t["candidate_id"] == c.CANDIDATES[0]), "control cannot qualify")
    else:
        require(len({r["name"] for r in value["checks"]}) == 11, "audit check inventory mismatch")
        require(len(set(value["limitations"])) == 4, "audit limitation inventory mismatch")
        if status["run_status"] == "not_run":
            require(all(r["status"] == "not_evaluated" and not r["evidence"] for r in value["checks"]), "not_run audit contains completed checks")
        if value["result_trusted"]:
            require(status["engineering_status"] == "pass" and all(r["status"] == "pass" and r["evidence"] for r in value["checks"]), "audit acceptance lacks complete evidence")
    return {**_validation_report(), "validation_status": "result_contract_valid", "reported_run_status": status["run_status"],
            "result_trusted": False, "independent_recomputation": "required-not-performed"}
