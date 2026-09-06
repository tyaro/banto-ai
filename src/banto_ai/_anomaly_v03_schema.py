"""Closed JSON Schema declarations for the frozen v0.3 S1 contracts."""

from __future__ import annotations

from . import _anomaly_v03_contract as c


def obj(properties: dict) -> dict:
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def array(items: dict, minimum: int = 0, maximum: int | None = None) -> dict:
    result = {"type": "array", "items": items, "minItems": minimum}
    if maximum is not None:
        result["maxItems"] = maximum
    return result


def enum(values) -> dict:
    return {"type": "string", "enum": list(values)}


def ref(name: str) -> dict:
    return {"$ref": "#/$defs/" + name}


def nullable(value: dict) -> dict:
    return {"anyOf": [value, {"type": "null"}]}


def fixed(value) -> dict:
    """Shape plus literal values; ordered equality is also checked semantically."""
    if type(value) is dict:
        return obj({k: fixed(v) for k, v in value.items()})
    if type(value) is list:
        choices = []
        for v in value:
            schema = fixed(v)
            if schema not in choices:
                choices.append(schema)
        return {**array({"anyOf": choices} if choices else {"type": "null"}, len(value), len(value)), "const": value}
    kind = {str: "string", int: "integer", float: "number", bool: "boolean", type(None): "null"}[type(value)]
    return {"type": kind, "const": value}


def document(name: str, body: dict, defs: dict | None = None) -> dict:
    value = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://banto-ai.local/schemas/" + name,
             "title": name, "description": "v0.3 shape only; pure semantic validation is not run execution or performance acceptance.", **body}
    if defs:
        value["$defs"] = defs
    return value


def common_defs() -> dict:
    integer = {"type": "integer", "minimum": 0}
    number = {"type": "number"}
    identifier = {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_.-]*$", "minLength": 1}
    digest = {"type": "string", "pattern": "^[a-f0-9]{64}$"}
    quality = enum(c.QUALITY)
    counts = obj({k: integer for k in c.counts("holdout")})
    hashes = obj({k: digest for k in ("observations", "events", "quality_mask", "split", "origins", "targets")})
    status = obj({"run_status": enum(("not_run", "in_progress", "complete", "failed")),
                  "engineering_status": enum(("not_evaluated", "pass", "fail", "inconclusive")),
                  "performance_status": enum(("not_evaluated", "pass", "fail", "inconclusive"))})
    identity = obj({"role": enum(c.ROLES), "seed": {"type": "integer", "minimum": 1000000, "maximum": 2**63-1},
                    "layout": {"type": "integer", "minimum": 0, "maximum": 11}, "stratum": enum(c.STRATA),
                    "candidate_id": enum(c.CANDIDATES), "pair_id": identifier, "dataset_id": identifier, "evaluation_id": identifier})
    dependency = obj({"full_target": enum(c.FULL_TARGETS), "sample": integer, "timestamp_ms": integer,
                      "quality": quality, "value": nullable(number)})
    event = obj({"dataset_id": identifier, "event_id": identifier, "cycle": {"type": "integer", "minimum": 0, "maximum": 9},
                 "event_class": enum(c.CLASSES), "equipment": enum(c.EQUIPMENT), "full_target": enum((*c.FULL_TARGETS, *(e+".load_proxy" for e in c.EQUIPMENT))),
                 "mode": enum(c.MODES), "recipe": enum(c.RECIPES), "event_type": enum(("jam_or_slip", "spike", "dropout", "stuck_value")),
                 "start_sample": integer, "end_sample": integer, "window_end_sample": integer,
                 "start_ms": integer, "end_ms": integer, "window_end_ms": integer,
                 "magnitude": number, "enabled": {"type": "boolean"}})
    profile = obj({"profile_id": identifier, "identity": ref("identity"), "profile_version": {"const": "0.3", "type": "string"},
                   "equipment": enum(c.EQUIPMENT), "full_target": enum(c.FULL_TARGETS), "mode": enum(c.MODES), "recipe": enum(c.RECIPES),
                   "status": enum(("not_fitted", "calibrated", "inconclusive")),
                   "fit_samples": array(integer), "calibration_samples": array(integer, 0, 290),
                   "planned_calibration_points": {"type": "integer", "const": 290}, "minimum_calibration_points": {"type": "integer", "const": 250},
                   "phase_medians": nullable(array(number, 30, 30)), "center": nullable(number), "scale": nullable(number),
                   "c2_state": nullable(obj({"centers": array(number, 4, 4), "scales": array(number, 4, 4),
                                             "mean": array(number, 4, 4), "covariance": array(array(number, 4, 4), 4, 4),
                                             "precision": array(array(number, 4, 4), 4, 4)})),
                   "reason": nullable(enum(("insufficient_points", "zero_scale", "nonfinite", "cholesky_failure", "not_fitted")))})
    score = obj({"score_id": identifier, "dataset_id": identifier, "candidate_id": enum(c.CANDIDATES),
                 "sample": integer, "timestamp_ms": integer, "phase": nullable({"type": "integer", "minimum": 0, "maximum": 29}),
                 "equipment": enum(c.EQUIPMENT), "full_target": enum(c.FULL_TARGETS), "mode": enum(c.MODES), "recipe": enum(c.RECIPES),
                 "profile_id": identifier, "dependencies": array(dependency, 0, 8), "residual": nullable(number), "score": nullable(number),
                 "available": {"type": "boolean"}, "exclusion_reason": nullable(enum(c.REASONS)),
                 "exclusion_tags": array(enum(c.REASONS), 0, 8), "threshold_exceeded": {"type": "boolean"}, "streak": integer,
                 "source_episode_id": nullable(identifier)})
    source_episode = obj({"episode_id": identifier, "dataset_id": identifier, "candidate_id": enum(c.CANDIDATES),
                  "equipment": enum(c.EQUIPMENT), "full_target": enum(c.FULL_TARGETS), "mode": enum(c.MODES), "recipe": enum(c.RECIPES),
                  "visit_start_sample": integer, "profile_id": identifier, "onset_ms": integer, "end_ms": integer,
                  "support_score_ids": array(identifier, 2, 2)})
    equipment_episode = obj({"episode_id": identifier, "dataset_id": identifier, "candidate_id": enum(c.CANDIDATES),
                             "equipment": enum(c.EQUIPMENT), "mode": enum(c.MODES), "recipe": enum(c.RECIPES), "visit_start_sample": integer,
                             "onset_ms": integer, "end_ms": integer, "source_episode_ids": array(identifier, 1),
                             "matched_event_id": nullable(identifier), "context_tags": array(enum(("raw-event", "grace", "clean", "quality", "ignored", "pre-event")))})
    incident = obj({"dataset_id": identifier, "event_id": identifier, "status": enum(("not_processed", "processed", "engineering_failure")),
                    "candidate_count": integer, "candidate_episode_ids": array(identifier), "selected_candidate_episode_id": nullable(identifier),
                    "selected_source_episode_id": nullable(identifier), "support_score_ids": array(identifier, 0, 2),
                    "reason": enum(c.MATCH_REASONS), "matched_episode_id": nullable(identifier),
                    "causal_detected": nullable({"type": "boolean"}), "delay_seconds": nullable(number),
                    "secondary_canonical_detected": nullable({"type": "boolean"})})
    metric = obj({"numerator": integer, "denominator": integer, "value": nullable(number),
                  "ci_status": enum(("not_evaluated", "complete", "inconclusive", "not_applicable")),
                  "ci_lower": nullable(number), "ci_upper": nullable(number), "null_replicates": integer})
    delay = obj({"count": integer, **{k: nullable(number) for k in ("median", "mean", "min", "max")},
                 "conditioned_on": {"type": "string", "const": "causal-detected-only"},
                 "undetected_fill": {"type": "string", "const": "forbidden"},
                 "unit": {"type": "string", "const": "seconds"}})
    source = obj({"revision": {"type": "string", "pattern": "^[a-f0-9]{40}$"},
                  "sources": array(obj({"path": ref("relative_path"), "raw_sha256": digest, "byte_count": integer}), 1)})
    metrics = obj({"machine_recall": ref("metric"), "sensor_recall": ref("metric"), "precision": ref("metric"),
                   "clean_rate": ref("metric"), "false_alert_burden": ref("metric"),
                   "availability": array(obj({"full_target": enum(c.FULL_TARGETS), "metric": ref("metric")}), 8, 8),
                   "scheduled_clean_seconds": integer, "effective_clean_seconds": integer,
                   "effective_clean_rate": nullable(number), "delay_summary": ref("delay_summary")})
    slice_row = obj({"candidate_id": enum(c.CANDIDATES), "stratum": enum((*c.STRATA, "overall")),
                     "dimension": enum(("class", "equipment", "mode", "class-equipment-mode", "test-cycle", "event-start-phase",
                                        "phase", "event-offset", "context", "full-target", "signal-mode", "quality-current", "quality-previous", "fault-quality-overlap", "profile-status")),
                     "key": identifier, "metric": ref("metric"), "planned_count": integer, "actual_count": integer,
                     "delay_summary": nullable(ref("delay_summary"))})
    payload = obj({"path": ref("relative_path"), "raw_sha256": digest, "canonical_sha256": digest, "row_count": integer})
    slot = obj({"identity": ref("identity"), "status": enum(c.SLOT_STATUS),
                "failure_stage": nullable(enum(("validation", "materialization", "profile", "scoring", "ledger", "publication", "integrity", "unsupported_runtime"))),
                "safe_reason": nullable(enum(("contract_violation", "input_changed", "incomplete", "profile_inconclusive", "unsupported_runtime", "exception"))),
                "input_hashes": nullable(ref("input_hashes")), "evidence": array(ref("payload"))})
    return {"identifier": identifier, "digest": digest, "integer": integer,
            "relative_path": {"type": "string", "pattern": r"^[A-Za-z0-9_-][A-Za-z0-9_./-]*$", "minLength": 1},
            "status": status, "identity": identity, "counts": counts, "input_hashes": hashes,
            "event": event, "profile": profile, "score": score, "source_episode": source_episode,
            "equipment_episode": equipment_episode, "incident": incident, "metric": metric,
            "metrics": metrics, "slice": slice_row, "payload": payload, "slot": slot,
            "delay_summary": delay, "source_descriptor": source}


def schemas(configs: list[dict]) -> list[dict]:
    config_schemas = [document(name, fixed(value)) for name, value in zip(c.SCHEMA_NAMES, configs)]
    defs = common_defs()
    digest = ref("digest")
    registry = obj({"schema_version": {"type": "string", "const": c.VERSION}, "registry_id": {"type": "string", "const": "anomaly-v03-freeze-registry"},
                    "science_revision": {"type": "string", "const": c.SCIENCE_REVISION},
                    "post_audit_revision": {"type": "string", "const": c.STATUS_REVISION},
                    "plan": obj({"path": {"type": "string", "const": c.PLAN_PATH}, "science_raw_sha256": digest, "status_raw_sha256": digest}),
                    "canonicalization": {"type": "string", "const": c.CANONICALIZATION},
                    "seed_registry": fixed(c.seed_registry()), "bootstrap": fixed(configs[3]["bootstrap"]),
                    "runtime": fixed(c.formal_runtime()),
                    "pins": array(obj({"path": enum((*c.CONFIG_PATHS[:4], *c.SCHEMA_PATHS)), "raw_sha256": digest, "canonical_sha256": digest}), 13, 13),
                    "external_pin": {"type": "string", "const": "trusted-commit-and-registry-raw-sha256-outside-registry"},
                    "validation_status": {"type": "string", "const": "not_run"}, "run_status": {"type": "string", "const": "not_run"},
                    "performance_status": {"type": "string", "const": "not_evaluated"}})
    config_schemas.append(document(c.SCHEMA_NAMES[4], registry, {"digest": defs["digest"]}))
    shared = {"schema_version": {"type": "string", "const": c.VERSION}, "status": ref("status"),
              "provenance": obj({"science_revision": {"type": "string", "const": c.SCIENCE_REVISION},
                                 "post_audit_revision": {"type": "string", "const": c.STATUS_REVISION},
                                 "producer_revision": {"type": "string", "pattern": "^[a-f0-9]{40}$"},
                                 "producer_source": ref("source_descriptor"),
                                 "registry_raw_sha256": digest, "inventory": array(ref("payload"), 1)})}
    evaluator = obj({**shared, "result_type": {"type": "string", "const": "event-aware-anomaly-v03"},
                     "identity": ref("identity"), "input_hashes": ref("input_hashes"),
                     "splits": fixed(configs[0]["splits"]), "events": array(ref("event"), 40, 40),
                     "profiles": array(ref("profile"), 0, 48), "scores": array(ref("score"), 0, 14400),
                     "source_episodes": array(ref("source_episode")), "equipment_episodes": array(ref("equipment_episode")),
                     "incidents": array(ref("incident"), 20, 20), "metrics": nullable(ref("metrics")),
                     "row_counts": obj({k: ref("integer") for k in ("events", "profiles", "scores", "source_episodes", "equipment_episodes", "incidents")}),
                     "slices": array(ref("slice"))})
    matrix = obj({**shared, "result_type": {"type": "string", "const": "anomaly-multiseed-v03"},
                  "role": enum(c.ROLES), "planned_counts": ref("counts"), "evaluations": array(ref("slot")),
                  "coverage": obj({k: ref("integer") for k in c.SLOT_STATUS})})
    gate = obj({"name": enum(("machine_recall", "sensor_recall", "precision", "clean_rate", "false_alert_burden", "availability")),
                "comparison": enum(("absolute", "paired-control")), "full_target": nullable(enum(c.FULL_TARGETS)),
                "point": nullable({"type": "number"}), "lower": nullable({"type": "number"}), "upper": nullable({"type": "number"}),
                "ci_status": enum(("not_evaluated", "complete", "inconclusive")), "null_replicates": ref("integer"),
                "status": enum(("not_evaluated", "pass", "fail", "inconclusive", "not_applicable"))})
    analysis = obj({**shared, "result_type": {"type": "string", "const": "anomaly-multiseed-analysis-v03"},
                    "analysis_consumer": ref("source_descriptor"),
                    "bootstrap": fixed(configs[3]["bootstrap"]),
                    "candidate_tables": array(obj({"candidate_id": enum(c.CANDIDATES), "stratum": enum((*c.STRATA, "overall")),
                                                   "profile_status": enum(("not_evaluated", "calibrated", "inconclusive")),
                                                   "metrics": nullable(ref("metrics")), "gates": array(gate), "qualified": {"type": "boolean"}}), 9, 9),
                    "slices": array(ref("slice")), "selected_candidate": nullable(enum(c.CANDIDATES[1:])),
                    "decision": enum(("not_evaluated", "qualified", "no_promotion", "inconclusive"))})
    audit = obj({**shared, "result_type": {"type": "string", "const": "anomaly-multiseed-audit-v03"},
                 "consumer_revision": {"type": "string", "pattern": "^[a-f0-9]{40}$"},
                 "input_analysis": ref("source_descriptor"), "audit_consumer": ref("source_descriptor"),
                 "checks": array(obj({"name": enum(("inventory", "raw-observations", "profiles", "scores", "support", "matching", "denominators", "bootstrap", "gates", "selection", "native-publication")),
                                      "status": enum(("not_evaluated", "pass", "fail", "inconclusive")), "evidence": array(ref("payload"))}), 11, 11),
                 "result_trusted": {"type": "boolean"}, "limitations": array(enum(("owner-can-change-acl", "privileged-writer", "no-power-loss-guarantee", "synthetic-only")), 4, 4)})
    for name, body in zip(c.SCHEMA_NAMES[5:], (evaluator, matrix, analysis, audit)):
        needed = set()
        def collect(node):
            if isinstance(node, dict):
                if "$ref" in node:
                    key = node["$ref"].split("/")[-1]
                    if key not in needed:
                        needed.add(key)
                        collect(defs[key])
                for value in node.values():
                    collect(value)
            elif isinstance(node, list):
                for value in node:
                    collect(value)
        collect(body)
        config_schemas.append(document(name, body, {k: defs[k] for k in sorted(needed)}))
    return config_schemas
