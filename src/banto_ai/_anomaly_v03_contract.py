"""Frozen S1 declarations. No observations, scores, I/O, or run execution.

Builders return fresh JSON values; callers cannot mutate the registered contract.
The persisted JSON documents, not builder output alone, are verified by the registry.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy

VERSION = "0.3"
SCIENCE_REVISION = "4b02201f95e8ffa3a243be716872d95815a554bd"
STATUS_REVISION = "0b40e7295cfa20f32889005ceca2d29d29ca340c"
BASE_REVISION = "026aa77fe96afd954957acb2fc7d0df9ee3cc938"
PLAN_PATH = "docs/anomaly-multiseed-evaluation-plan-v0.3.md"
ROLES = ("dev", "smoke", "holdout")
ROLE_COUNTS = (8, 2, 40)
CANDIDATES = ("c0-diff-control", "c1-phase-level", "c2-phase-conditional")
STRATA = ("core", "quality-stress")
EQUIPMENT = ("motor-01", "conveyor-01")
TARGETS = ("motor_current", "motor_temperature", "conveyor_speed", "vibration_feature")
FULL_TARGETS = tuple(f"{e}.{t}" for e in EQUIPMENT for t in TARGETS)
MODES = ("stopped", "startup", "low_speed", "nominal", "high_load", "cooldown")
RECIPES = ("stop", "start", "low", "run", "load", "cooldown")
CLASSES = ("machine", "sensor", "data_quality", "ignored")
OLD_SEEDS = (11, 17, 23, 29, 37, 42, 53, 67, 79, 97)
SEED_ALGORITHM = "anomaly-v03-seed-registry-sha256-v1"
SEED_HASH = "fa072f5299132fc22cce471c94ca189ddfc0f3acd27c2c5201bc31a2a9287505"
BOOTSTRAP_ALGORITHM = "sha256-counter-rejection-v1"
BOOTSTRAP_SEED = 2026090603
BOOTSTRAP_REPLICATES = 50000
BOOTSTRAP_HASH = "e375bf3feacb2f04bf5e1d40b141c1cfc5f69fa5437ea2704e323fd7523b22e5"
GOLDEN_DRAWS = [{"replicate":0,"indices":[28,5,25,0,34,30,1,38,29,36,18,5,29,16,4,13,25,10,5,29,12,21,25,20,31,29,10,25,31,7,4,4,13,23,6,14,20,35,9,30]},{"replicate":1,"indices":[26,3,36,29,12,21,36,7,37,11,8,30,31,23,20,28,36,30,33,9,27,36,24,6,39,27,10,15,19,20,0,7,27,38,3,5,10,5,1,2]},{"replicate":24999,"indices":[34,16,4,17,28,18,5,11,32,0,1,7,25,12,8,37,33,24,9,33,16,22,15,18,8,1,34,18,27,32,1,13,2,37,30,18,28,22,36,23]},{"replicate":49999,"indices":[29,24,39,17,23,20,38,7,20,13,11,10,26,4,30,34,34,9,19,31,39,21,37,9,29,10,16,26,0,1,13,20,35,4,39,4,35,7,31,34]}]
CLUSTERS = 40
START_MS = 1767225600000
CANONICALIZATION = "utf-8-json-sort-keys-compact-no-trailing-newline-v1"
CONFIG_NAMES = (
    "synthetic-anomaly-v0.3.json", "anomaly-candidates-v0.3.json",
    "anomaly-multiseed-v0.3.json", "anomaly-multiseed-analysis-v0.3.json",
    "anomaly-v03-freeze-registry.json",
)
CONFIG_PATHS = tuple("examples/configs/" + n for n in CONFIG_NAMES)
SCHEMA_NAMES = (
    "synthetic-anomaly-config-v0.3.schema.json",
    "anomaly-candidates-config-v0.3.schema.json",
    "anomaly-multiseed-matrix-config-v0.3.schema.json",
    "anomaly-multiseed-analysis-config-v0.3.schema.json",
    "anomaly-v03-freeze-registry.schema.json",
    "anomaly-evaluation-result-v0.3.schema.json",
    "anomaly-multiseed-matrix-result-v0.3.schema.json",
    "anomaly-multiseed-analysis-result-v0.3.schema.json",
    "anomaly-multiseed-audit-result-v0.3.schema.json",
)
SCHEMA_PATHS = tuple("schemas/" + n for n in SCHEMA_NAMES)
OUTPUT_ROOTS = tuple("artifacts/anomaly-multiseed-v03-" + r for r in (*ROLES, "analysis", "audit"))
REASONS = (
    "current_target_quality", "current_nonfinite", "no_previous_or_gap",
    "previous_target_quality_or_nonfinite", "mode_recipe_or_phase",
    "peer_quality_or_nonfinite", "profile_inconclusive", "nonfinite_score",
)
MATCH_REASONS = ("not_processed", "causal_detected", "no_candidate_in_window",
                 "first_candidate_no_target_onset", "first_candidate_noncausal_support")
QUALITY = ("ok", "missing", "stale", "invalid")
SLOT_STATUS = ("success", "partial", "inconclusive", "failed", "not_started")


def seed_registry() -> dict:
    used = set(OLD_SEEDS)
    entries = []
    lists = {}
    for role, count in zip(ROLES, ROLE_COUNTS):
        seeds, counters = [], []
        for index in range(count):
            counter = 0
            while True:
                key = f"banto-ai/anomaly-v03/seeds/{role}/{index}/{counter}"
                value = int.from_bytes(hashlib.sha256(key.encode("ascii")).digest()[:8], "big") & (2**63 - 1)
                if value >= 1000000 and value not in used:
                    break
                counter += 1
            used.add(value)
            seeds.append(value)
            counters.append(counter)
        lists[role] = seeds
        entries.append({"role": role, "seeds": seeds, "counters": counters})
    raw = json.dumps(lists, sort_keys=True, separators=(",", ":")).encode("ascii")
    assert hashlib.sha256(raw).hexdigest() == SEED_HASH
    return {"algorithm_id": SEED_ALGORITHM, "role_order": list(ROLES),
            "excluded_seeds": list(OLD_SEEDS), "entries": entries,
            "seed_list_canonical_sha256": SEED_HASH}


def bootstrap_indices() -> bytes:
    """Exactly 2,000,000 accepted indices; deterministic pure arithmetic only."""
    limit = (2**256 // CLUSTERS) * CLUSTERS
    result = bytearray()
    for replicate in range(BOOTSTRAP_REPLICATES):
        for position in range(CLUSTERS):
            counter = 0
            while True:
                key = f"{BOOTSTRAP_ALGORITHM}:{BOOTSTRAP_SEED}:{replicate}:{position}:{counter}"
                value = int.from_bytes(hashlib.sha256(key.encode("ascii")).digest(), "big")
                if value < limit:
                    result.append(value % CLUSTERS)
                    break
                counter += 1
    return bytes(result)


def counts(role: str) -> dict:
    if type(role) is not str or role not in ROLES:
        raise ValueError("unknown role")
    seeds = ROLE_COUNTS[ROLES.index(role)]
    datasets = seeds * 12 * 2
    return {"seeds": seeds, "layouts": 12, "datasets": datasets,
            "evaluations": datasets * 3, "observation_rows": datasets * 9000 * 2,
            "score_rows": datasets * 3 * 14400, "event_rows": datasets * 40,
            "enabled_events": seeds * 12 * 70, "positive_incidents": datasets * 20,
            "profiles": datasets * 3 * 48, "clean_equipment_seconds": datasets * 3365,
            "target_origins_per_stratum": seeds * 12 * 1800}


def formal_runtime() -> dict:
    return {"os": "Windows 11 Pro", "release": "25H2", "architecture": "AMD64",
            "os_major": 10, "os_minor": 0, "os_build": 26200, "os_ubr": 9168,
            "filesystem": "local-NTFS", "implementation": "CPython", "python_version": "3.14.0",
            "pointer_bits": 64, "gil_disabled": False, "compiler": "MSC v.1944",
            "source_tag": "v3.14.0:ebf955d",
            "python_exe_raw_sha256": "467014615a5255aca450ae88100dd2caf887da87657f00e3c2171ec44a685aec",
            "python_dll_raw_sha256": "f1722bd369d79fecbc85f3ed2790c30c330b9413fd74332f95b086e60dfacc2a"}


def config_values(bootstrap_hash: str, golden_draws: list) -> list[dict]:
    generator = {
        "schema_version": VERSION, "config_type": "synthetic-anomaly-v03", "generator_id": "synthetic-anomaly-v03",
        "generator_version": "0.3.0", "base_revision": BASE_REVISION,
        "base_source_path": "src/banto_ai/generator.py", "base_function": "_base_values",
        "equipment": list(EQUIPMENT), "targets": list(TARGETS), "numeric_signals": [*TARGETS, "load_proxy"],
        "start_timestamp": "2026-01-01T00:00:00Z", "start_timestamp_ms": START_MS,
        "sampling_interval_ms": 1000, "sample_count": 9000, "cycles": 50, "mode_samples": 30,
        "modes": list(MODES), "recipes": list(RECIPES),
        "splits": {"warmup": [0, 1800], "fit": [1800, 5400], "calibration": [5400, 7200], "test": [7200, 9000]},
        "initial_temperature": 24.0, "random_stream": "single-random.Random(seed)-equipment-signal-order",
        "latent_state": "unrounded-normal-temperature", "overlay_order": ["machine", "sensor", "ignored", "data_quality"],
        "quantization": {"algorithm": "python-builtin-round-float", "digits": 6, "stage": "after-all-overlays",
                         "null": "preserve", "signed_zero": "preserve", "input": "verified-saved-observations-only",
                         "jsonl": "utf8-sorted-compact-ensure_ascii_false-allow_nan_false-LF"},
        "layout": {"count": 12, "order": "equipment-major-mode-minor", "slots": [0, 7, 14, 21],
                   "test_cycles": 10, "base_sample": 7200, "cycle_samples": 180,
                   "event_duration": 3, "grace": 3, "window": "half-open",
                   "quality_overlap_cycle": 9, "quality_overlap_sensor_offset": 1},
        "events": [
            {"class": "machine", "type": "jam_or_slip", "magnitude": 0.55, "class_index": 0,
             "target_by_equipment": ["motor_current", "conveyor_speed"]},
            {"class": "sensor", "type": "spike", "magnitude": 8.0, "class_index": 1,
             "target_by_equipment": ["motor_temperature", "motor_temperature"]},
            {"class": "data_quality", "type": "dropout", "magnitude": 0.0, "class_index": 2,
             "target_by_equipment": ["motor_temperature", "motor_temperature"]},
            {"class": "ignored", "type": "stuck_value", "magnitude": 0.0, "class_index": 3,
             "target_by_equipment": ["load_proxy", "load_proxy"]}],
        "strata": list(STRATA), "core_quality_enabled": False, "stress_quality_enabled": True,
        "pairing": "same-normal-stream-fault-ledger-except-quality-coordinates",
    }
    candidates = {
        "schema_version": VERSION, "config_type": "anomaly-candidates-v03", "analyzer_id": "event-aware-anomaly-v03",
        "candidates": [{"candidate_id": c, "fit": fit, "residual": residual, "threshold": threshold}
                       for c, fit, residual, threshold in zip(CANDIDATES,
                           ("no-op", "phase-median", "phase-median-shrinkage-covariance"),
                           ("x_i(t)-x_i(t-1)", "x_i(t)-mu_i,m(u)", "(Omega*(r(t)-v))_i/sqrt(Omega_ii)"), (4.0, 6.0, 6.0))],
        "profile_version": VERSION, "profile_identity": ["candidate", "role", "seed", "layout", "stratum", "equipment", "full_target", "mode", "recipe_family", "profile_version"],
        "features": ["same-equipment-current-and-past-target-values", "quality", "timestamp", "observed-mode", "recipe-family", "locked-normal-profile"],
        "forbidden_features": ["GT", "layout", "seed", "cycle", "absolute-test-position", "future", "other-equipment", "load_proxy"],
        "targets": list(FULL_TARGETS), "phase_range": [0, 29], "phase_zero_available": False,
        "history_samples": 1, "threshold_operator": ">", "persistence": 2,
        "resets": ["mode", "recipe", "gap", "quality", "profile"], "c2_requires_complete_current_and_previous": True,
        "calibration": {"center": "median", "scale": "1.4826*MAD", "mad_factor": 1.4826, "planned_points": 290,
                        "minimum_points": 250, "zero_or_nonfinite_scale": "inconclusive", "fallback": "forbidden", "test_update": False},
        "phase_fit": {"phases": 30, "points_each": 20, "median": "middle-two-arithmetic-mean-even"},
        "c2": {"fit_phases": [1, 29], "complete_vectors": 580, "covariance_denominator": 579,
               "standardization": "r_i=(e_i-median(e_i))/(1.4826*MAD(e_i))", "mean": "arithmetic",
               "shrinkage": 0.25, "covariance": "0.75*S+0.25*diag(S)", "precision": "inverse(Sigma)",
               "sum": "math.fsum", "solver": "Cholesky", "target_order": list(TARGETS), "jitter": False},
        "episode": {"onset": "second-exceedance", "support_size": 2, "interval": "onset-to-last-exceedance-plus-one-second",
                    "merge": "transitive-overlap-or-adjacency", "merge_scope": ["dataset", "equipment", "mode", "visit"],
                    "source_sort": ["onset", "full_target", "episode_id"], "label_input": False},
        "matching_policy": "first-equipment-onset-no-retry-v1", "failure_retry": False,
        "exclusion_priority": list(REASONS), "fixtures": {"matching": [f"M{i}" for i in range(1, 10)], "quantization": [f"Q{i}" for i in range(1, 6)]},
    }
    matrix = {
        "schema_version": VERSION, "config_type": "anomaly-multiseed-v03", "matrix_id": "anomaly-multiseed-v03",
        "plan_id": "anomaly-multiseed-plan-v03", "generator_config_path": CONFIG_PATHS[0], "candidates_config_path": CONFIG_PATHS[1],
        "seed_registry": seed_registry(), "candidate_order": list(CANDIDATES), "stratum_order": list(STRATA),
        "roles": list(ROLES), "counts": [{"role": r, **counts(r)} for r in ROLES],
        "output_roots": [{"role": r, "path": p} for r, p in zip(ROLES, OUTPUT_ROOTS)],
        "inventory_order": ["registered-seed", "layout-index", "stratum", "candidate"],
        "pair_id_format": "anomaly-v03-{role}-seed-{seed}-layout-{layout:02d}",
        "cell_id_format": "{pair_id}-{stratum}", "evaluation_id_format": "{cell_id}-{candidate_id}",
        "event_id_format": "{pair_id}-cycle-{cycle:02d}-{event_class}",
        "planned": {"events_per_dataset": 40, "positives_per_dataset": 20, "profiles_per_evaluation": 48,
                    "scores_per_evaluation": 14400, "origins_per_target": 1800, "clean_seconds_per_dataset": 3365,
                    "stress_structurally_unavailable_sensor_incidents": 480, "stress_sensor_recall_ceiling": 0.9,
                    "core_available_per_target_stratum": 835200, "stress_motor_temperature_available": 825960,
                    "stress_conveyor_temperature_available": 826320},
        "paired_inputs": ["observations", "events", "quality_mask", "split", "origins", "targets"],
        "validation_status": "not_run", "run_status": "not_run", "performance_status": "not_evaluated",
        "safety": {"input": "synthetic-only", "network": False, "customer_data": False, "control_write": False,
                   "hub_write": False, "nonoverwrite": True, "reparse_traversal": "forbidden-runtime-io-check-required"},
    }
    gate_rows = []
    for stratum, sensor, avail in zip((*STRATA, "overall"), ((0.90, 0.85), (0.85, 0.80), (0.875, 0.825)), (0.960, 0.950, 0.955)):
        gate_rows.append({"stratum": stratum, "machine_recall": [0.85, 0.80], "sensor_recall": list(sensor),
                          "precision": [0.85, 0.80], "clean_rate": [1.0, 1.5], "each_target_availability": [avail, avail]})
    analysis = {
        "schema_version": VERSION, "config_type": "anomaly-multiseed-analysis-v03", "analysis_id": "anomaly-multiseed-analysis-v03",
        "audit_id": "anomaly-multiseed-audit-v03", "matrix_id": "anomaly-multiseed-v03", "matrix_config_path": CONFIG_PATHS[2],
        "input_root": OUTPUT_ROOTS[2], "output_root": OUTPUT_ROOTS[3], "audit_root": OUTPUT_ROOTS[4],
        "bootstrap": {"algorithm_id": BOOTSTRAP_ALGORITHM, "seed": BOOTSTRAP_SEED, "clusters": CLUSTERS,
                      "replicates": BOOTSTRAP_REPLICATES, "accepted_indices": 2000000, "indices_raw_sha256": bootstrap_hash,
                      "golden_draws": deepcopy(golden_draws), "sampling": "paired-seed-clusters-with-replacement",
                      "aggregation": "ratio-of-sums", "interval": [0.025, 0.975], "quantile": "type-7",
                      "zero_denominator": "inconclusive-no-drop-no-redraw"},
        "absolute_gates": gate_rows,
        "paired_noninferiority": {"machine_recall": [0.0, -0.02], "sensor_recall": [0.0, -0.02],
                                 "clean_rate": [0.0, 0.25], "false_alert_burden": [0.0, 1.0], "each_target_availability": [-0.0125, -0.0125]},
        "multiple_testing": {"candidate_alpha": 0.025, "candidate_correction": "Bonferroni-two",
                             "within_candidate": "intersection-union-all-gates-strata-targets"},
        "selection_order": list(CANDIDATES[1:]), "fallback": "no-promotion", "control_promotable": False,
        "units": {"clean_rate": "alerts-per-8-equipment-hours", "false_alert_burden": "false-equipment-episodes-per-100-planned-positive-incidents"},
        "slices": {"incident": ["class", "equipment", "mode", "class-equipment-mode", "test-cycle", "event-start-phase"],
                   "phase": ["0", "1", "2", "3", "4..6", "7..13", "14..20", "21..29"],
                   "event_offsets": [-2, -1, 0, 1, 2, 3, 4, 5], "context": ["raw-event", "grace", "clean"],
                   "diagnostics": ["full-target", "signal-mode", "quality-current", "quality-previous", "fault-quality-overlap", "profile-status"],
                   "class_precision": "not-applicable", "delay": "detected-only", "event_offset_partition": False},
        "validation_status": "not_run", "run_status": "not_run", "performance_status": "not_evaluated",
    }
    return [generator, candidates, matrix, analysis]
