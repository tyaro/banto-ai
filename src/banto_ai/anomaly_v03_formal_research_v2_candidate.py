"""Pure, unadopted S4-1 research-v2 wrapper candidate validation.

The caller supplies *trusted external* byte pins. This checks supplied bytes and
reported semantics only: it cannot authenticate processes, Git, runtime, NTFS,
the independent audit, numerical recomputation, or grant formal permission.
"""
from __future__ import annotations

import hashlib
import math
import re

from . import anomaly_v03 as science
from . import anomaly_v03_slices as slices
from . import _anomaly_v03_contract as frozen
from ._anomaly_v03_schema import schemas


FORMAT = "anomaly-v03-formal-research-wrapper-candidate-v2"
POLICY = "anomaly-v03-single-writer-research-v2"
ROOT = "artifacts/anomaly-v03-formal-research-v2"
PAYLOADS = ("execution.json", "coverage.json", "analysis.json",
            "diagnostics.json", "verification.json")
ROLES = ("producer", "analysis", "audit", "writer", "reader")
SERIES = ("incident-recall", "score-availability",
          "score-threshold-exceedance", "score-signal-onset")
SHA = re.compile(r"[0-9a-f]{64}\Z")
REVISION = re.compile(r"[0-9a-f]{40}\Z")
ATTEMPT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")
MAX_PAYLOAD = 16 * 1024 * 1024


def _need(ok, reason):
    if not ok:
        raise science.V03ValidationError("research-v2 candidate: " + reason)


def _fields(value, names, reason):
    _need(type(value) is dict and set(value) == set(names), reason + " fields")


def _same(actual, expected, reason):
    _need(science.canonical_json(actual) == science.canonical_json(expected), reason)


def _digest(value, reason):
    _need(type(value) is str and SHA.fullmatch(value) is not None, reason + " digest")


def _pin(raw):
    return {"byte_count": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _check_pin(value, reason):
    _fields(value, ("byte_count", "sha256"), reason)
    _need(type(value["byte_count"]) is int and value["byte_count"] > 0,
          reason + " byte count")
    _digest(value["sha256"], reason)


def _source_role(value, revision, reason):
    _fields(value, ("revision", "sources", "runtime"), reason)
    _need(value["revision"] == revision, reason + " revision")
    for kind in ("sources", "runtime"):
        rows = value[kind]
        _need(type(rows) is list and bool(rows), reason + " " + kind + " inventory")
        paths = []
        for row in rows:
            _fields(row, ("path", "raw_sha256", "byte_count"), reason + " " + kind)
            science.safe_relative_path(row["path"])
            _digest(row["raw_sha256"], reason + " " + kind)
            _need(type(row["byte_count"]) is int and row["byte_count"] > 0,
                  reason + " " + kind + " byte count")
            paths.append(row["path"])
        _need(len(paths) == len(set(paths)), reason + " duplicate " + kind)


def _role_snapshots(snapshots, expected):
    """Bind declared role files to supplied bytes; no checkout/loader attestation."""
    _fields(snapshots, ROLES, "supplied role snapshot")
    shared_bytes = {}
    for role in ROLES:
        _fields(snapshots[role], ("sources", "runtime"), role + " snapshot")
        for kind in ("sources", "runtime"):
            entries = expected["role_pins"][role][kind]
            supplied = snapshots[role][kind]
            _fields(supplied, [entry["path"] for entry in entries],
                    role + " " + kind + " snapshot")
            for entry in entries:
                raw = supplied[entry["path"]]
                _need(type(raw) is bytes and len(raw) == entry["byte_count"] and
                      hashlib.sha256(raw).hexdigest() == entry["raw_sha256"],
                      role + " " + kind + " raw bytes")
                # On this proposed Windows runtime, case variants name the same
                # logical file. A role-local pin is insufficient when another
                # role declares that file under the same full revision.
                identity = (expected["role_pins"][role]["revision"],
                            entry["path"].casefold())
                previous = shared_bytes.setdefault(identity, raw)
                _need(previous == raw, "cross-role revision/path byte conflict")


def _expected_boundary(expected):
    _fields(expected, ("attempt_id", "revision", "plan_raw_sha256",
                       "registry_raw_sha256", "role_pins", "input_pins",
                       "receipt_pins", "payload_pins", "marker_pin"), "external expectation")
    _need(type(expected["attempt_id"]) is str and ATTEMPT.fullmatch(expected["attempt_id"])
          is not None and ".." not in expected["attempt_id"], "attempt ID")
    _need(type(expected["revision"]) is str and REVISION.fullmatch(expected["revision"])
          is not None, "full clean revision")
    for name in ("plan_raw_sha256", "registry_raw_sha256"):
        _digest(expected[name], name)
    _need(expected["registry_raw_sha256"] == science.REGISTRY_RAW_SHA256,
          "frozen registry raw pin")
    _fields(expected["role_pins"], ROLES, "role pin")
    for role in ROLES:
        _source_role(expected["role_pins"][role], expected["revision"], role)
    _need(type(expected["input_pins"]) is dict and bool(expected["input_pins"]),
          "external input inventory")
    for path, pin in expected["input_pins"].items():
        science.safe_relative_path(path)
        _check_pin(pin, "external input")
    _fields(expected["receipt_pins"], ("audit", "writer", "reader"), "outer receipt pin")
    for pin in expected["receipt_pins"].values():
        _check_pin(pin, "outer receipt")
    _fields(expected["payload_pins"], PAYLOADS, "external payload pin")
    for pin in expected["payload_pins"].values():
        _check_pin(pin, "external payload")
    _check_pin(expected["marker_pin"], "external marker")


def _decode(raw, reason, limit):
    _need(type(raw) is bytes and 0 < len(raw) <= limit, reason + " byte bound")
    value = science.strict_json(raw)
    _need(raw == science.canonical_json(value), reason + " canonical bytes")
    return value


def _header(value, attempt, reason):
    _need(value["format"] == FORMAT and value["attempt_id"] == attempt,
          reason + " identity")


def _execution(value, expected, identities):
    _fields(value, ("format", "policy_id", "attempt_id", "root",
                    "plan_raw_sha256", "registry_raw_sha256", "planned_identities",
                    "roles", "external_inputs", "stages"), "execution")
    _header(value, expected["attempt_id"], "execution")
    _need(value["policy_id"] == POLICY and value["root"] == ROOT, "policy/root")
    for key in ("plan_raw_sha256", "registry_raw_sha256"):
        _need(value[key] == expected[key], "execution " + key)
    _same(value["planned_identities"], identities, "all planned identities/order")
    _same(value["roles"], expected["role_pins"], "role source/runtime pins")
    _same(value["external_inputs"], expected["input_pins"], "external input pins")
    _fields(value["stages"], ROLES, "stage")
    for role in ROLES:
        row = value["stages"][role]
        _fields(row, ("status", "failure"), role + " stage")
        _need(row == {"status": "success", "failure": None}, role + " incomplete")


def _coverage(value, attempt, identities):
    _fields(value, ("format", "attempt_id", "planned", "chunks", "evaluations"),
            "coverage")
    _header(value, attempt, "coverage")
    _same(value["planned"], {"chunks": 480, "datasets": 960, "evaluations": 2880},
          "coverage planned counts")
    chunks = []
    for row in identities[::6]:
        chunks.append({"pair_id": row["pair_id"], "seed": row["seed"],
                       "layout": row["layout"], "latest_attempt": attempt,
                       "status": "success"})
    _same(value["chunks"], chunks, "480 chunk identity/latest-attempt coverage")
    _same(value["evaluations"],
          [{"identity": row, "latest_attempt": attempt, "status": "success",
            "failure": None} for row in identities],
          "2880 evaluation identity/latest-attempt coverage")


def _slice_keys(dimensions, candidate, stratum):
    return [(candidate, stratum, dimension, key)
            for dimension, keys in dimensions.items() for key in keys]


def _rows(rows, expected_keys, reason, schema):
    _need(type(rows) is list and len(rows) == len(expected_keys), reason + " row count")
    science._shape(rows, schema)
    science._reported_slices(rows, uncomputed_ci=True)
    keys = [(r["candidate_id"], r["stratum"], r["dimension"], r["key"])
            for r in rows]
    _need(keys == expected_keys, reason + " row identity/order")
    for row in rows:
        metric = row["metric"]
        _need(row["actual_count"] == metric["numerator"], reason + " actual numerator")
        _need(metric["denominator"] <= row["planned_count"], reason + " denominator")
        _need(metric["ci_status"] == ("not_evaluated" if metric["denominator"] else
                                     "not_applicable"), reason + " auxiliary CI")
        if row["dimension"] in slices.INCIDENT_KEYS:
            _need(metric["denominator"] == row["planned_count"] and
                  row["delay_summary"] is not None, reason + " incident meaning")
        else:
            _need(row["delay_summary"] is None, reason + " score delay meaning")
            if row["dimension"] != "event-offset":
                _need(metric["denominator"] == row["planned_count"],
                      reason + " exclusive score reference meaning")


def _incident_marginal(rows):
    count = sum(row["delay_summary"]["count"] for row in rows)
    return (sum(row["planned_count"] for row in rows),
            sum(row["actual_count"] for row in rows), count,
            math.fsum(row["delay_summary"]["mean"] * row["delay_summary"]["count"]
                      for row in rows if row["delay_summary"]["count"]),
            min((row["delay_summary"]["min"] for row in rows
                 if row["delay_summary"]["count"]), default=None),
            max((row["delay_summary"]["max"] for row in rows
                 if row["delay_summary"]["count"]), default=None))


def _overall_cells(series):
    """Every overall cell must be the same key's two-stratum raw count sum."""
    for name, rows in series.items():
        by_key = {(r["candidate_id"], r["stratum"], r["dimension"], r["key"]): r
                  for r in rows}
        for candidate in frozen.CANDIDATES:
            dimensions = (slices.INCIDENT_KEYS if name == SERIES[0]
                          else slices.SCORE_KEYS)
            for dimension, keys in dimensions.items():
                for key in keys:
                    core, stress, overall = [by_key[candidate, layer, dimension, key]
                                             for layer in (*frozen.STRATA, "overall")]
                    for field in ("planned_count", "actual_count"):
                        _need(overall[field] == core[field] + stress[field],
                              "per-key overall " + name + " " + field)
                    _need(overall["metric"]["denominator"] ==
                          core["metric"]["denominator"] +
                          stress["metric"]["denominator"],
                          "per-key overall " + name + " denominator")
                    if name == SERIES[0]:
                        summaries = [r["delay_summary"] for r in (core, stress, overall)]
                        left, right, pooled = summaries
                        _need(pooled["count"] == left["count"] + right["count"],
                              "per-key overall incident delay count")
                        weighted = math.fsum(s["mean"] * s["count"] for s in
                                             (left, right) if s["count"])
                        extrema = [s for s in (left, right) if s["count"]]
                        _need((pooled["mean"] is None if not extrema else
                               math.isclose(pooled["mean"] * pooled["count"],
                                            weighted, rel_tol=1e-12,
                                            abs_tol=1e-7)) and
                              pooled["min"] == min((s["min"] for s in extrema),
                                                    default=None) and
                              pooled["max"] == max((s["max"] for s in extrema),
                                                    default=None),
                              "per-key overall incident delay moments")


def _diagnostics(value, analysis, attempt):
    _fields(value, ("format", "attempt_id", "series"), "diagnostics")
    _header(value, attempt, "diagnostics")
    _fields(value["series"], SERIES, "diagnostic series")
    table_keys = [(candidate, stratum) for candidate in frozen.CANDIDATES
                  for stratum in (*frozen.STRATA, "overall")]
    incident = [key for candidate, stratum in table_keys
                for key in _slice_keys(slices.INCIDENT_KEYS, candidate, stratum)]
    score = [key for candidate, stratum in table_keys
             for key in _slice_keys(slices.SCORE_KEYS, candidate, stratum)]
    _need(len(incident) == 432 and len(score) == 801, "frozen slice dimensions")
    schema = schemas(science._expected_configs())[7]
    row_schema = {**schema["properties"]["slices"], "$defs": schema["$defs"]}
    for name in SERIES:
        _rows(value["series"][name], incident if name == SERIES[0] else score,
              name, row_schema)
    main = [*value["series"][SERIES[0]], *value["series"][SERIES[1]]]
    _need(len(main) == 1233, "main slice row count")
    _same(analysis["slices"], main, "analysis.slices/sidecar mapping")
    available = value["series"][SERIES[1]]
    threshold = value["series"][SERIES[2]]
    onset = value["series"][SERIES[3]]
    for a, t, o in zip(available, threshold, onset):
        _need(a["metric"]["denominator"] == t["metric"]["denominator"] ==
              o["metric"]["denominator"] and
              a["planned_count"] == t["planned_count"] == o["planned_count"] and
              o["actual_count"] <= t["actual_count"] <= a["actual_count"],
              "score family denominator/numerator relation")
    _overall_cells(value["series"])
    incident_index = {(r["candidate_id"], r["stratum"], r["dimension"], r["key"]): r
                      for r in value["series"][SERIES[0]]}
    score_index = {(r["candidate_id"], r["stratum"], r["dimension"], r["key"]): r
                   for r in available}
    for table in analysis["candidate_tables"]:
        candidate, stratum = table["candidate_id"], table["stratum"]
        metrics = table["metrics"]
        incident_rows = [r for r in value["series"][SERIES[0]]
                         if (r["candidate_id"], r["stratum"]) == (candidate, stratum)]
        incident_baseline = _incident_marginal(
            [r for r in incident_rows if r["dimension"] == "class"])
        primary_delay = metrics["delay_summary"]
        _need(primary_delay["count"] == incident_baseline[2] and
              primary_delay["min"] == incident_baseline[4] and
              primary_delay["max"] == incident_baseline[5] and
              ((primary_delay["mean"] is None and incident_baseline[2] == 0) or
               (incident_baseline[2] > 0 and
                math.isclose(primary_delay["mean"],
                             incident_baseline[3] / incident_baseline[2],
                             rel_tol=1e-12, abs_tol=1e-9))),
              "incident sidecar/primary pooled delay")
        for dimension in slices.INCIDENT_KEYS:
            marginal = _incident_marginal(
                [r for r in incident_rows if r["dimension"] == dimension])
            _need(marginal[:3] == incident_baseline[:3] and
                  math.isclose(marginal[3], incident_baseline[3],
                               rel_tol=1e-12, abs_tol=1e-7) and
                  marginal[4:] == incident_baseline[4:],
                  "incident dimension count/delay marginal")
        for class_name, metric_name in (("machine", "machine_recall"),
                                        ("sensor", "sensor_recall")):
            row = incident_index[candidate, stratum, "class", class_name]
            metric = metrics[metric_name]
            _need((row["actual_count"], row["planned_count"]) ==
                  (metric["numerator"], metric["denominator"]),
                  "incident class/primary recall binding")
        for target in metrics["availability"]:
            row = score_index[candidate, stratum, "full-target", target["full_target"]]
            metric = target["metric"]
            _need((row["actual_count"], row["metric"]["denominator"]) ==
                  (metric["numerator"], metric["denominator"]),
                  "score target/primary availability binding")
        for name in SERIES[1:]:
            score_rows = [r for r in value["series"][name]
                          if (r["candidate_id"], r["stratum"]) ==
                          (candidate, stratum)]
            baseline = [r for r in score_rows if r["dimension"] == "full-target"]
            totals = (sum(r["planned_count"] for r in baseline),
                      sum(r["metric"]["denominator"] for r in baseline),
                      sum(r["actual_count"] for r in baseline))
            for dimension in slices.SCORE_KEYS:
                rows = [r for r in score_rows if r["dimension"] == dimension]
                if dimension == "event-offset":
                    # These are event references, not an exclusive partition.
                    # Their target/out-of-test exclusions require raw detail.
                    expected_refs = 40 * (960 if stratum == "overall" else 480)
                    _need(all(r["planned_count"] == expected_refs for r in rows),
                          "event-offset planned references")
                    continue
                marginal = (sum(r["planned_count"] for r in rows),
                            sum(r["metric"]["denominator"] for r in rows),
                            sum(r["actual_count"] for r in rows))
                _need(marginal == totals, "exclusive score dimension marginal")
    _need(sum(len(rows) for rows in value["series"].values()) == 2835,
          "four-series sidecar row count")


def _verification(value, expected):
    _fields(value, ("format", "attempt_id", "reader", "receipt_pins",
                    "payload_pins", "semantic_checks", "unverified"), "verification")
    _header(value, expected["attempt_id"], "verification")
    _same(value["reader"], {"separate_process": True, "exit_code": 0, "reaped": True},
          "declared reader lifecycle")
    _same(value["receipt_pins"], expected["receipt_pins"], "outer receipt reference")
    _fields(value["payload_pins"], PAYLOADS[:-1], "verification payload pin")
    _same(value["payload_pins"],
          {name: expected["payload_pins"][name] for name in PAYLOADS[:-1]},
          "verification payload references")
    _same(value["semantic_checks"],
          {"science_contract": "pass", "slice_inventory": "pass",
           "coverage": "pass", "saved_raw": "pass", "independent_audit": "pass"},
          "declared semantic checks")
    _need(type(value["unverified"]) is list and
          all(type(item) is str and item for item in value["unverified"]) and
          len(value["unverified"]) == len(set(value["unverified"])),
          "unverified scope list")


def validate_candidate_bundle(payload_raw, marker_raw, *, expected, role_snapshots):
    """Validate a proposed complete bundle; always return formal_permission=False.

    Passing means only that these caller-supplied bytes agree with caller-supplied
    external pins and the reported contract. It is not an acceptance gate.
    """
    _expected_boundary(expected)
    _role_snapshots(role_snapshots, expected)
    _fields(payload_raw, PAYLOADS, "payload byte inventory")
    decoded = {}
    for name in PAYLOADS:
        raw = payload_raw[name]
        decoded[name] = _decode(raw, name, MAX_PAYLOAD)
        _same(_pin(raw), expected["payload_pins"][name], name + " external raw pin")
    marker = _decode(marker_raw, "marker", 64 * 1024)
    _same(_pin(marker_raw), expected["marker_pin"], "external marker raw pin")
    _fields(marker, ("format", "attempt_id", "payloads"), "marker")
    _header(marker, expected["attempt_id"], "marker")
    _same(marker["payloads"],
          [{"path": name, **expected["payload_pins"][name]} for name in PAYLOADS],
          "marker complete payload inventory")
    identities = science.evaluation_inventory("holdout")
    _need(len(identities) == 2880, "frozen identity count")
    execution = decoded["execution.json"]
    coverage = decoded["coverage.json"]
    analysis = decoded["analysis.json"]
    _execution(execution, expected, identities)
    _coverage(coverage, expected["attempt_id"], identities)
    source_bytes = {}
    for role in ("producer", "analysis"):
        source_bytes.update(role_snapshots[role]["sources"])
    science.validate_result_contract(
        analysis, source_snapshots={expected["revision"]: source_bytes})
    _need(analysis["status"]["run_status"] == "complete", "complete analysis")
    _need(analysis["provenance"]["producer_revision"] == expected["revision"],
          "analysis producer revision")
    for field, role in (("producer_source", "producer"),
                        ("analysis_consumer", "analysis")):
        descriptor = (analysis["provenance"][field] if field == "producer_source"
                      else analysis[field])
        _same(descriptor,
              {"revision": expected["revision"],
               "sources": expected["role_pins"][role]["sources"]},
              "analysis " + field + " source")
    _diagnostics(decoded["diagnostics.json"], analysis, expected["attempt_id"])
    _verification(decoded["verification.json"], expected)
    return {"status": "candidate_supplied_bytes_consistent",
            "payload_count": 5, "planned_chunks": 480,
            "planned_evaluations": 2880, "main_slice_rows": 1233,
            "diagnostic_rows": 2835, "formal_permission": False,
            "S4_ACCEPTED": False, "campaign_evaluations_credited": 0,
            "external_pin_authentication": "caller_responsibility",
            "process_source_runtime_audit_authentication": "not_performed",
            "independent_numerical_recomputation": "not_performed",
            "event_offset_exclusion_ledger": "not_supplied",
            "quality_current_previous_dependency_ledger": "not_supplied",
            "primary_delay_median_from_slice_rows": "not_derivable"}
