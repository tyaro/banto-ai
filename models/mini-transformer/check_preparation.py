"""New data/trainer boundary checks; no dataset learning or repeated model checks."""
import hashlib
import argparse
import json
import random
import sys
import time
import traceback
from pathlib import Path
from datetime import datetime, timedelta, timezone

import torch

from check_model import process_memory
from data import BOUNDS, TARGETS, candidate_origins, load_fixed_day, prepare, rows_to_tensors
from small_model import SmallForecaster
from train import choose_checkpoint, Files, evaluate, baseline_metrics
from small_model import Forecast


def fixture():
    values = torch.arange(1440, dtype=torch.float32)[None].repeat(3, 1)
    return values, torch.ones_like(values, dtype=torch.bool)


def window_boundaries():
    values, valid = fixture(); data = prepare(values, valid)
    assert data.origins["train"] == list(range(128, 833))
    assert data.origins["validation"] == list(range(864, 1152, 32))
    assert data.origins["test"] == list(range(1152, 1440, 32))
    x, y = data.batch([832], "train")
    assert x[0, 0].tolist() == list(range(704, 832))
    assert y[0, 0].tolist() == list(range(832, 864))
    x, y = data.batch([864], "validation")
    assert x[0, 0, 0].item() == 736 and y[0, 0, -1].item() == 895
    for split, wrong in (("train", 833), ("validation", 1152), ("test", 1440)):
        try: data.batch([wrong], split)
        except ValueError: pass
        else: raise AssertionError("split-crossing label admitted")


def train_only_scale():
    values, valid = fixture(); data = prepare(values, valid)
    changed = values.clone(); changed[:, 864:] *= 10000
    other = prepare(changed, valid)
    torch.testing.assert_close(data.train_scale, other.train_scale)
    torch.testing.assert_close(data.scale_floor, other.scale_floor)
    expected_std = ((864**2-1)/12)**.5
    torch.testing.assert_close(data.train_scale, torch.full((3,), expected_std))
    torch.testing.assert_close(data.scale_floor, torch.full((3,), .01*expected_std))


def quality_and_nonfinite_exclusion():
    values, valid = fixture(); valid[1, 864] = False
    data = prepare(values, valid)
    assert len(data.origins["train"]) == 705 and len(data.origins["test"]) == 9
    assert [item["origin"] for item in data.excluded["validation"]] == [864, 896, 928, 960, 992]
    try: data.batch([864], "validation")
    except ValueError: pass
    else: raise AssertionError("bad window admitted")
    values, valid = fixture(); values[0, 720] = float("nan")
    data = prepare(values, valid)
    assert 688 in data.origins["train"] and 689 not in data.origins["train"]
    assert len(data.excluded["train"]) == 144
    assert torch.isnan(data.values[0, 720]) and torch.isfinite(data.train_scale).all()


def row_mapping_and_cadence():
    start = datetime(2020, 2, 21, 0, 1, tzinfo=timezone.utc)
    rows = [{"timestamp": (start+timedelta(minutes=i)).isoformat().replace("+00:00", "Z"),
        "equipment_id": "metropt3-apu-01", "signals": {name: {"unit": unit, "value": i+v*10000}
        for v, (name, unit) in enumerate(TARGETS)}, "quality": {name: "ok" for name, _ in TARGETS}}
        for i in range(1440)]
    values, valid = rows_to_tensors(rows)
    assert values[:, 5].tolist() == [5, 10005, 20005] and valid.all()
    rows[23]["timestamp"] = rows[22]["timestamp"]
    try: rows_to_tensors(rows)
    except ValueError: pass
    else: raise AssertionError("duplicate time admitted")
    rows[23]["timestamp"] = (start+timedelta(minutes=23)).isoformat().replace("+00:00", "Z")
    rows[0]["signals"]["tp3"]["unit"] = "A"
    try: rows_to_tensors(rows)
    except ValueError: pass
    else: raise AssertionError("wrong unit admitted")


def common_schedule():
    values, valid = fixture(); data = prepare(values, valid)
    state = random.getstate()
    first, second = data.schedule(), data.schedule()
    assert first == second and random.getstate() == state
    assert len(first) == 128 and all(len(batch) == 8 for batch in first)
    assert all(o in data.origins["train"] for batch in first for o in batch)


def selection_and_optimizer_configuration():
    best = choose_checkpoint(None, 64, 2., "64.pt")
    assert choose_checkpoint(best, 32, 2., "32.pt")["step"] == 32
    assert choose_checkpoint(best, 96, 3., "96.pt") == best
    try: choose_checkpoint(best, 128, float("nan"), "bad.pt")
    except ValueError: pass
    else: raise AssertionError("nonfinite selection admitted")
    model = SmallForecaster(torch.full((3,), .001))
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, betas=(.9, .999), eps=1e-8,
        weight_decay=.01, foreach=False, fused=False)
    assert optimizer.defaults["lr"] == 3e-4 and not optimizer.state
    assert optimizer.defaults["foreach"] is False and optimizer.defaults["fused"] is False


def output_closed_and_no_overwrite():
    root = Path(__file__).resolve().parents[2]/"artifacts/representative-small-model-output-fixture-20261014"
    # Keep this fixture as evidence. An existing fixture is never reopened.
    files = Files(root)
    files.json("record.json", {"value": 1})
    try: files.json("record.json", {"value": 2})
    except ValueError: pass
    else: raise AssertionError("output overwritten")
    files.json("root-closed.json", {"status": "fixture", "files": files.pins})
    try: files.json("late.json", {})
    except ValueError: pass
    else: raise AssertionError("closed output appended")


def metrics_hand_example():
    class Data:
        origins = {"test": [1152]}
        train_scale = torch.tensor([1., 2., 4.])
        def batch(self, origins, split):
            return torch.full((1, 3, 128), 4.), torch.full((1, 3, 32), 3.)
    class Fixed:
        def __call__(self, context):
            output = torch.tensor([0., 1., 2.]).expand(1, 3, 32, 3)
            return Forecast(output, output, torch.zeros(1, 3, 1), torch.ones(1, 3, 1))
    result = evaluate(Fixed(), Data())
    for metric in result["metrics"].values():
        assert abs(metric["mae"]-2.) < 1e-6
        assert abs(metric["pinball"]-11/15) < 1e-6
        assert abs(metric["wis"]-22/15) < 1e-6
        assert metric["coverage_80"] == 0 and metric["width_80"] == 2
        assert metric["lead_mae"] == [2.]*32
    assert abs(result["fixed_scale_pinball"]-(11/15)*(1+.5+.25)/3) < 1e-6
    for baseline in baseline_metrics(Data()).values():
        assert all(metric["mae"] == 1. for metric in baseline.values())


def first_error_survives_preservation_failure():
    from contextlib import redirect_stderr
    from io import StringIO
    from unittest.mock import patch
    import train
    original = RuntimeError("fixture-original-input-failure")
    root = Path(__file__).resolve().parents[2]/"artifacts/representative-small-model-first-error-fixture-20261014"
    writer = Files(root)
    real_json = writer.json
    def fail_preservation(name, value, failure=False):
        if name == "failure.json":
            raise OSError("fixture-preservation-failure")
        return real_json(name, value, failure)
    stderr = StringIO()
    with patch("train.Files", return_value=writer), patch("train.load_fixed_day", side_effect=original), \
         patch("train.torch.set_num_interop_threads"), patch.object(writer, "json", side_effect=fail_preservation), \
         redirect_stderr(stderr):
        try: train.run("fixture-input", root)
        except RuntimeError as caught: assert caught is original
        else: raise AssertionError("original exception replaced or swallowed")
    evidence = json.loads(stderr.getvalue())
    assert evidence["original_error"]["message"] == "fixture-original-input-failure"
    assert evidence["preservation_error"]["message"] == "fixture-preservation-failure"
    assert not (root/"summary.json").exists()
    writer.json("fixture-errors.json", evidence)
    writer.json("root-closed.json", {"status": "fixture-original-error-preserved", "files": writer.pins})


def main():
    all_checks = (window_boundaries, train_only_scale, quality_and_nonfinite_exclusion,
        row_mapping_and_cadence, common_schedule, selection_and_optimizer_configuration,
        output_closed_and_no_overwrite, metrics_hand_example, first_error_survives_preservation_failure)
    lookup = {check.__name__: check for check in all_checks}
    parser = argparse.ArgumentParser()
    parser.add_argument("--checks", default=",".join(lookup))
    args = parser.parse_args()
    names = args.checks.split(",")
    if len(names) != len(set(names)) or any(name not in lookup for name in names):
        parser.error("unknown or duplicate check")
    torch.set_num_threads(2); torch.set_num_interop_threads(1)
    start = time.monotonic(); failures = 0
    checks = [lookup[name] for name in names]
    for check in checks:
        try:
            check(); print(json.dumps({"check": check.__name__, "status": "passed"}), flush=True)
        except Exception as error:
            failures += 1
            print(json.dumps({"check": check.__name__, "status": "failed", "type": type(error).__name__, "message": str(error)}), flush=True)
            traceback.print_exc()
        memory = process_memory()
        if max(memory["private_bytes"], memory["peak_pagefile_bytes"]) > 2*1024**3:
            raise RuntimeError("memory checkpoint exceeded")
    prepared, pins = None, None
    if names == list(lookup):
        prepared, pins = load_fixed_day(Path(__file__).resolve().parents[2]/"artifacts/public-datasets/metropt3-public-2020-02-21")
    result = {"checks": len(checks), "passed": len(checks)-failures, "failed": failures,
              "elapsed_seconds": time.monotonic()-start, "memory": process_memory(),
              "input_pins": pins, "prepared": prepared.description() if prepared else None, "optimizer_steps": 0,
              "model_training": False, "data_status": "exploratory public day"}
    print(json.dumps(result), flush=True)
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
