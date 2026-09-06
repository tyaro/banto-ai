"""S3 paired materialization. No filesystem, campaign, or detector execution.

The registered seed is consumed once per pair, in the frozen generator order.
Only the final observation copy is rounded. The returned bytes must be saved
and read back by the runner before S2 sees them. Calling materialize_pair with a
registered seed constitutes data generation and belongs to S4/S5, not CI.
"""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from . import _anomaly_v03_contract as c
from . import anomaly_v03 as v
from .anomaly_v03_scoring import decode_saved_observations, quantize_observation
from .generator import _base_values, _unit, FINGERPRINT_FILE_NAMES, FINGERPRINT_CANONICALIZATION

SIGNALS = (*c.TARGETS, "load_proxy")
INPUT_FILES = {"observations": "observations.jsonl", "events": "event-ledger.jsonl",
               "quality_mask": "quality-mask.jsonl", "split": "split-manifest.json",
               "origins": "origins.json", "targets": "targets.json"}
DATASET_FILES = (*FINGERPRINT_FILE_NAMES, "event-ledger.jsonl", "quality-mask.jsonl",
                 "origins.json", "targets.json", "fingerprint.json")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value) -> bytes:
    return v.canonical_json(value) + b"\n"


def jsonl(rows) -> bytes:
    return b"".join(json_bytes(row) for row in rows)


def identity_for(identity: dict, stratum: str, candidate: str = c.CANDIDATES[0]) -> dict:
    v.validate_identity(identity)
    v.require(stratum in c.STRATA and candidate in c.CANDIDATES, "unknown stratum/candidate")
    dataset = identity["pair_id"] + "-" + stratum
    return {**identity, "stratum": stratum, "candidate_id": candidate,
            "dataset_id": dataset, "evaluation_id": dataset + "-" + candidate}


def normal_stream(seed: int):
    """Frozen normal physics, equipment-major, one PRNG; no rounding/overlays."""
    v.require(type(seed) is int and 0 <= seed < 2**63, "seed must be an exact integer")
    rng = random.Random(seed)
    for ei, equipment in enumerate(c.EQUIPMENT):
        temperature = 24.0
        for sample in range(9000):
            values, temperature = _base_values(("motor", "conveyor")[ei],
                                               c.MODES[(sample % 180)//30], temperature, rng)
            # temperature is the unrounded NORMAL return, not output_values.
            yield equipment, sample, values


def overlay_sample(normal: dict, equipment: str, sample: int, events: list, stuck: dict) -> tuple[dict, dict]:
    """Machine -> sensor -> ignored -> quality, then one final quantization.

    This primitive also supports hand fixtures; the enclosing pair materializer
    validates the exact registered event inventory before invoking it.
    """
    v.require(type(normal) is dict and set(normal) == set(SIGNALS), "normal signal inventory")
    v.require(all(type(x) in (int, float) for x in normal.values()), "normal values must be numeric")
    v.require(all(math.isfinite(x) for x in normal.values()), "normal values must be finite before masking")
    values, quality = dict(normal), dict.fromkeys(SIGNALS, "ok")
    for kind in ("machine", "sensor", "ignored", "data_quality"):
        for event in events:
            if (event["event_class"] != kind or not event["enabled"] or event["equipment"] != equipment
                    or not event["start_sample"] <= sample < event["end_sample"]):
                continue
            target = event["full_target"].split(".", 1)[1]
            magnitude = event["magnitude"]
            if kind == "machine":
                values[target] = max(0.0, values[target] * max(0.0, 1.0-magnitude))
                values["load_proxy"] = min(100.0, values["load_proxy"]+abs(magnitude)*35.0)
                values["vibration_feature"] += abs(magnitude)*2.0
            elif kind == "sensor":
                values[target] += magnitude
            elif kind == "ignored":
                key = (event["event_id"], target)
                if key not in stuck:
                    stuck[key] = values[target]  # preserve unrounded capture and signed zero
                values[target] = stuck[key]
            else:
                values[target], quality[target] = None, "missing"
    return {name: quantize_observation(values[name]) for name in SIGNALS}, quality


@dataclass(frozen=True)
class DatasetBytes:
    identity_json: bytes
    entries: tuple[tuple[str, bytes], ...]

    def __post_init__(self):
        identity = v.strict_json(self.identity_json)
        v.validate_identity(identity)
        v.require(identity["candidate_id"] == c.CANDIDATES[0] and self.identity_json == v.canonical_json(identity), "dataset identity must be canonical C0 coordinate")
        v.require(type(self.entries) is tuple and tuple(x[0] for x in self.entries) == DATASET_FILES
                  and all(type(x) is tuple and len(x) == 2 and type(x[1]) is bytes for x in self.entries), "immutable dataset file inventory")

    def files(self) -> dict[str, bytes]:
        return dict(self.entries)

    def input_hashes(self) -> dict:
        files = self.files()
        return {key: sha(files[name]) for key, name in INPUT_FILES.items()}


def _dataset(identity, observations, masks, events) -> DatasetBytes:
    config = c.config_values(c.BOOTSTRAP_HASH, c.GOLDEN_DRAWS)[0]
    dataset_identity = {k: identity[k] for k in ("role", "seed", "layout", "stratum", "pair_id", "dataset_id")}
    files = {
        "generator-config.json": json_bytes({"generator": config, "identity": dataset_identity, "events": events}),
        "observations.jsonl": b"".join(observations),
        "events.jsonl": jsonl(e for e in events if e["enabled"]),
        "event-ledger.jsonl": jsonl(events),
        "quality-mask.jsonl": b"".join(masks),
        "split-manifest.json": json_bytes(config["splits"]),
        "origins.json": json_bytes(list(range(7200, 9000))),
        "targets.json": json_bytes(list(c.FULL_TARGETS)),
        "dataset-manifest.json": json_bytes({"schema_version": "0.3", "generator_id": "synthetic-anomaly-v03",
            "generator_version": "0.3.0", "identity": dataset_identity, "provenance": "synthetic",
            "equipment": list(c.EQUIPMENT), "signals": list(SIGNALS), "sample_count_per_equipment": 9000,
            "observation_record_count": 18000, "planned_event_count": 40,
            "enabled_event_count": sum(e["enabled"] for e in events), "input_files": INPUT_FILES}),
    }
    hashes = {name: sha(files[name]) for name in FINGERPRINT_FILE_NAMES}
    fingerprint_input = "".join(f"{name}\n{digest}\n" for name, digest in sorted(hashes.items())).encode("utf-8")
    files["fingerprint.json"] = json_bytes({"algorithm": "sha256", "canonicalization": FINGERPRINT_CANONICALIZATION,
                                          "files": hashes, "dataset_fingerprint": sha(fingerprint_input)})
    return DatasetBytes(v.canonical_json(identity), tuple((name, files[name]) for name in DATASET_FILES))


def _build_pair(identity: dict, normal) -> tuple[DatasetBytes, DatasetBytes]:
    """Internal hand-series seam for CI; no seed substitution in public API."""
    identities = [identity_for(identity, layer) for layer in c.STRATA]
    events = [v.event_inventory(i) for i in identities]
    observed, masks, stuck = [[], []], [[], []], [{}, {}]
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    count = 0
    for equipment, sample, values in normal:
        v.require(type(sample) is int and count < 18000 and
                  (equipment, sample) == (c.EQUIPMENT[count//9000], count % 9000), "normal stream coordinate/count")
        timestamp = (start+timedelta(seconds=sample)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        equipment_type = ("motor", "conveyor")[count//9000]
        for si in range(2):
            output, quality = overlay_sample(values, equipment, sample, events[si], stuck[si])
            row = {"timestamp": timestamp, "equipment_id": equipment, "equipment_type": equipment_type,
                   "operating_mode": c.MODES[(sample % 180)//30], "recipe_step": c.RECIPES[(sample % 180)//30],
                   "signals": {t: {"unit": _unit(equipment_type, t), "value": output[t]} for t in SIGNALS}, "quality": quality}
            observed[si].append(json_bytes(row))
            masks[si].append(json_bytes({"equipment_id": equipment, "sample": sample, "quality": quality}))
        count += 1
    v.require(count == 18000, "incomplete normal stream")
    return tuple(_dataset(i, observed[si], masks[si], events[si]) for si, i in enumerate(identities))


def materialize_pair(identity: dict) -> tuple[DatasetBytes, DatasetBytes]:
    """Generate a whole registered pair once; S4/S5 call only, never CI."""
    v.validate_identity(identity)
    return _build_pair(identity, normal_stream(identity["seed"]))


def validate_dataset(identity: dict, files: dict[str, bytes]) -> dict:
    """Strict saved coverage/metadata validation, without normal-physics replay.

    The runner separately byte-compares a pair with freshly materialized output;
    this structural function by itself is not a producer or consumer audit.
    """
    ident = identity_for(identity, identity["stratum"])
    v.require(type(files) is dict and set(files) == set(DATASET_FILES), "dataset file inventory")
    v.require(all(type(x) is bytes for x in files.values()), "dataset files must be bytes")
    raw = files["observations.jsonl"]
    decoded = decode_saved_observations(raw, expected_sha256=sha(raw))
    v.require(len(decoded) == 18000, "observation count")
    rows, masks = [], []
    quality_events = [e for e in v.event_inventory(ident) if e["event_class"] == "data_quality" and e["enabled"]]
    for index, (obs, line) in enumerate(zip(decoded, raw.splitlines(keepends=True))):
        equipment, sample = c.EQUIPMENT[index//9000], index % 9000
        v.require((obs.equipment, obs.timestamp_ms, obs.mode, obs.recipe) ==
                  (equipment, c.START_MS+sample*1000, c.MODES[(sample % 180)//30], c.RECIPES[(sample % 180)//30]),
                  "observation coordinate/mode/recipe mismatch")
        row = v.strict_json(line)
        quality = dict.fromkeys(SIGNALS, "ok")
        if any(e["equipment"] == equipment and e["start_sample"] <= sample < e["end_sample"] for e in quality_events):
            quality["motor_temperature"] = "missing"
        v.require(row["quality"] == quality, "quality mask mismatch")
        for target in SIGNALS:
            cell = row["signals"][target]
            v.require(cell["unit"] == _unit(("motor", "conveyor")[index//9000], target), "signal unit mismatch")
            v.require((cell["value"] is None) == (quality[target] == "missing"), "unplanned null or missing non-null")
        rows.append(line)
        masks.append(json_bytes({"equipment_id": equipment, "sample": sample, "quality": quality}))
    expected = _dataset(ident, rows, masks, v.event_inventory(ident)).files()
    v.require(files == expected, "dataset metadata/events/fingerprint mismatch")
    return {key: sha(files[name]) for key, name in INPUT_FILES.items()}


def validate_pair(core: DatasetBytes, stress: DatasetBytes) -> None:
    """Full pairing including every non-quality numeric coordinate and ledger."""
    identities = [v.strict_json(x.identity_json) for x in (core, stress)]
    v.require(identities[1] == identity_for(identities[0], "quality-stress") and identities[0]["stratum"] == "core", "pair identity/order")
    files = [x.files() for x in (core, stress)]
    for ident, captured in zip(identities, files):
        validate_dataset(ident, captured)
    for a, b in zip(files[0]["observations.jsonl"].splitlines(), files[1]["observations.jsonl"].splitlines()):
        left, right = v.strict_json(a), v.strict_json(b)
        if right["quality"]["motor_temperature"] == "missing":
            left["quality"]["motor_temperature"] = "missing"
            left["signals"]["motor_temperature"]["value"] = None
        v.require(v.canonical_json(left) == v.canonical_json(right), "paired non-quality observation mismatch")
