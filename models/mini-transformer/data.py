"""Fixed exploratory MetroPT day, context/label boundaries and common schedule."""
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import random

import torch


TARGETS = (("tp3", "bar"), ("oil_temperature", "ºC"), ("motor_current", "A"))
FINGERPRINT = "e6210e4e48e05c025fc8895ddeddf0c53a49dc53fd1c2f49e8c3272a3c7b37b0"
OBSERVATIONS = "d74b53979a051270f045265ccce3a582f3164500f8c7d3a8cf6940ce9a1a5077"
BOUNDS = {"train": (0, 864), "validation": (864, 1152), "test": (1152, 1440)}


def candidate_origins(split):
    start, end = BOUNDS[split]
    return list(range(max(128, start), end-32+1, 1 if split == "train" else 32))


@dataclass(frozen=True)
class Prepared:
    values: torch.Tensor
    valid: torch.Tensor
    origins: dict
    excluded: dict
    train_scale: torch.Tensor
    scale_floor: torch.Tensor

    def batch(self, origins, split):
        if not 1 <= len(origins) <= 8 or any(o not in self.origins[split] for o in origins):
            raise ValueError("invalid or excluded origin for split")
        x = torch.stack([self.values[:, o-128:o] for o in origins])
        y = torch.stack([self.values[:, o:o+32] for o in origins])
        return x, y

    def schedule(self):
        if not self.origins["train"]:
            raise ValueError("no training origins")
        rng = random.Random(20261014)
        return [[rng.choice(self.origins["train"]) for _ in range(8)] for _ in range(128)]

    def description(self):
        return {"target_order": [name for name, _ in TARGETS], "origins": self.origins,
                "excluded": self.excluded, "train_scale": self.train_scale.tolist(),
                "scale_floor": self.scale_floor.tolist(), "schedule": self.schedule(),
                "test_status": "previously evaluated public day; exploratory only"}


def prepare(values, valid):
    if values.shape != (3, 1440) or values.dtype != torch.float32 or values.device.type != "cpu":
        raise ValueError("values: CPU float32 [3,1440] required")
    if valid.shape != values.shape or valid.dtype != torch.bool or valid.device.type != "cpu":
        raise ValueError("valid: CPU bool [3,1440] required")
    values = values.detach().clone()
    valid = valid.clone() & torch.isfinite(values)
    scales = []
    for v in range(3):
        prefix = values[v, :864][valid[v, :864]]
        if prefix.numel() < 2:
            raise ValueError("insufficient valid training prefix")
        scales.append(prefix.std(correction=0))
    std = torch.stack(scales)
    train_scale = std.clamp_min(1e-5)
    floor = (0.01*std).clamp_min(1e-5)
    origins, excluded = {}, {}
    for split in BOUNDS:
        origins[split], excluded[split] = [], []
        for origin in candidate_origins(split):
            bad = (~valid[:, origin-128:origin+32]).nonzero()
            if len(bad):
                first = bad[0].tolist()
                excluded[split].append({"origin": origin, "bad_cells": len(bad),
                    "first_bad_target": TARGETS[first[0]][0],
                    "first_bad_index": origin-128+first[1]})
            else:
                origins[split].append(origin)
    return Prepared(values, valid, origins, excluded, train_scale, floor)


def rows_to_tensors(rows):
    if len(rows) != 1440:
        raise ValueError("expected 1440 minute rows")
    values, valid, previous = [], [], None
    for row in rows:
        timestamp = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
        if timestamp.utcoffset() is None or timestamp.utcoffset().total_seconds() != 0:
            raise ValueError("expected UTC-formatted research ordering")
        if previous is None and row["timestamp"] != "2020-02-21T00:01:00Z":
            raise ValueError("unexpected first bin-end timestamp")
        if previous is not None and (timestamp-previous).total_seconds() != 60:
            raise ValueError("non-contiguous minute rows")
        previous = timestamp
        if row["equipment_id"] != "metropt3-apu-01":
            raise ValueError("unexpected equipment identity")
        v, good = [], []
        for name, unit in TARGETS:
            signal = row["signals"][name]
            if signal["unit"] != unit:
                raise ValueError("unexpected target unit/order mapping")
            value = signal["value"]
            finite = type(value) in (int, float) and math.isfinite(value)
            v.append(float(value) if finite else float("nan"))
            good.append(finite and row["quality"].get(name) == "ok")
        values.append(v); valid.append(good)
    return torch.tensor(values, dtype=torch.float32).T, torch.tensor(valid, dtype=torch.bool).T


def load_fixed_day(directory):
    directory = Path(directory)
    if directory.name != "metropt3-public-2020-02-21":
        raise ValueError("only the specified exploratory day is admitted")
    fingerprint = json.loads((directory/"fingerprint.json").read_bytes())
    if fingerprint["dataset_fingerprint"] != FINGERPRINT:
        raise ValueError("dataset fingerprint mismatch")
    raw_files, pins = {}, {}
    for name, digest in fingerprint["files"].items():
        if Path(name).name != name:
            raise ValueError("fingerprint path must be a filename")
        raw = (directory/name).read_bytes()
        observed = hashlib.sha256(raw).hexdigest()
        if observed != digest:
            raise ValueError("input file digest mismatch: "+name)
        raw_files[name] = raw
        pins[name] = {"bytes": len(raw), "sha256": observed}
    if pins["observations.jsonl"]["sha256"] != OBSERVATIONS:
        raise ValueError("fixed observations pin mismatch")
    manifest = json.loads(raw_files["dataset-manifest.json"])
    if manifest["sample_count"] != 1440 or manifest["sampling_interval_ms"] != 60000:
        raise ValueError("unexpected cadence/count")
    split = json.loads(raw_files["split-manifest.json"])
    rows = [json.loads(line) for line in raw_files["observations.jsonl"].splitlines()]
    declared = split["strategies"]
    if len(declared) != 1 or declared[0]["strategy"] != "chronological":
        raise ValueError("unexpected split strategy")
    for item, (name, (start, end)) in zip(declared[0]["splits"], BOUNDS.items(), strict=True):
        if item["split_id"] != name or item["record_count"] != end-start:
            raise ValueError("unexpected chronological split")
        first = datetime.fromisoformat(rows[start]["timestamp"].replace("Z", "+00:00"))
        end_time = first.timestamp()+(end-start)*60
        if datetime.fromisoformat(item["start_timestamp"].replace("Z", "+00:00")) != first:
            raise ValueError("split start mismatch")
        if datetime.fromisoformat(item["end_timestamp"].replace("Z", "+00:00")).timestamp() != end_time:
            raise ValueError("split end mismatch")
    values, valid = rows_to_tensors(rows)
    prepared = prepare(values, valid)
    if any(not prepared.origins[name] for name in BOUNDS):
        raise ValueError("no usable origins in a required split")
    return prepared, pins
