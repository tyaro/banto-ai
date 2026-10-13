"""One bounded exploratory pair; running this file explicitly starts training."""
import time
START = time.monotonic()
import argparse
from io import BytesIO
import hashlib
import json
import os
import sys
from pathlib import Path
import traceback

import torch

from check_model import process_memory
from data import load_fixed_day, TARGETS
from small_model import SmallForecaster, selection_score, training_loss


def choose_checkpoint(best, step, score, path):
    if not torch.isfinite(torch.tensor(score)) or step not in (32, 64, 96, 128):
        raise ValueError("invalid checkpoint candidate")
    candidate = {"step": step, "validation_score": score, "path": path}
    return candidate if best is None or (score, step) < (best["validation_score"], best["step"]) else best


class Files:
    """One writer to a fresh local output; no reopen or overwrite."""
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir()
        self.pins = {}

    def write(self, name, raw, failure=False):
        if (self.root/"root-closed.json").exists():
            raise ValueError("output root is closed")
        if Path(name).name != name or name in self.pins:
            raise ValueError("unsafe or reused output name")
        files = list(self.root.iterdir())
        if any(not p.is_file() or p.is_symlink() for p in files):
            raise ValueError("unexpected output entry")
        limit_files, limit_bytes = (32, 1024**3) if failure else (24, 768*1024**2)
        if len(files)+1 > limit_files or len(raw) > 32*1024**2 or sum(p.stat().st_size for p in files)+len(raw) > limit_bytes:
            raise RuntimeError("output checkpoint exceeded; failure reserve retained")
        with (self.root/name).open("xb") as stream:
            if stream.write(raw) != len(raw):
                raise OSError("short output write")
            stream.flush()
            os.fsync(stream.fileno())
        self.pins[name] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}

    def json(self, name, value, failure=False):
        self.write(name, json.dumps(value, sort_keys=True, allow_nan=False).encode(), failure)

    def state(self, name, model):
        buffer = BytesIO(); torch.save(model.state_dict(), buffer)
        self.write(name, buffer.getvalue())


def checkpoint():
    memory = process_memory()
    if max(memory["private_bytes"], memory["peak_pagefile_bytes"]) > 2*1024**3:
        raise RuntimeError("process memory checkpoint exceeded")
    if time.monotonic()-START > 870:
        raise RuntimeError("wall checkpoint exceeded; preserve within 900 seconds")
    return memory


def validate(model, prepared):
    scores = []
    with torch.no_grad():
        for origin in prepared.origins["validation"]:
            x, y = prepared.batch([origin], "validation")
            scores.append(selection_score(model(x), y, prepared.train_scale).item())
            checkpoint()
    return sum(scores)/len(scores)


def evaluate(model, prepared):
    actuals, predictions = [], []
    inference_start = time.monotonic()
    with torch.no_grad():
        for origin in prepared.origins["test"]:
            x, y = prepared.batch([origin], "test")
            predictions.append(model(x).quantiles); actuals.append(y)
            checkpoint()
    inference_seconds = time.monotonic()-inference_start
    prediction, actual = torch.cat(predictions), torch.cat(actuals)
    q = torch.tensor([.1, .5, .9])
    residual = actual[..., None]-prediction
    losses = torch.maximum(q*residual, (q-1)*residual)
    metrics = {}
    for v, (name, unit) in enumerate(TARGETS):
        error = (actual[:, v]-prediction[:, v, :, 1]).abs()
        metrics[name] = {"unit": unit, "mae": error.mean().item(),
            "pinball": losses[:, v].mean().item(), "wis": 2*losses[:, v].mean().item(),
            "coverage_80": ((actual[:, v]>=prediction[:, v, :, 0]) & (actual[:, v]<=prediction[:, v, :, 2])).float().mean().item(),
            "width_80": (prediction[:, v, :, 2]-prediction[:, v, :, 0]).mean().item(),
            "lead_mae": error.mean(dim=0).tolist()}
    return {"metrics": metrics, "predictions": prediction.tolist(), "actual": actual.tolist(),
            "inference_seconds": inference_seconds,
            "origins": prepared.origins["test"], "fixed_scale_pinball": (losses/prepared.train_scale[None, :, None, None]).mean().item()}


def baseline_metrics(prepared):
    results = {}
    for mode in ("last-value", "moving-average-15"):
        errors = []
        for origin in prepared.origins["test"]:
            x, y = prepared.batch([origin], "test")
            point = x[:, :, -1:] if mode == "last-value" else x[:, :, -15:].mean(-1, keepdim=True)
            errors.append((y-point).abs())
        error = torch.cat(errors)
        results[mode] = {name: {"unit": unit, "mae": error[:, v].mean().item(),
                         "lead_mae": error[:, v].mean(0).tolist()}
                         for v, (name, unit) in enumerate(TARGETS)}
    return results


def run(dataset, output):
    files = Files(output)
    journal, best = [], {"full": None, "self-only": None}
    training_seconds = {"full": 0., "self-only": 0.}
    validation_seconds = {"full": 0., "self-only": 0.}
    try:
        for name in ("train.py", "data.py", "small_model.py", "check_model.py"):
            files.write("source-"+name, Path(__file__).with_name(name).read_bytes())
        torch.set_num_threads(2); torch.set_num_interop_threads(1)
        torch.use_deterministic_algorithms(True)
        checkpoint()
        prepared, pins = load_fixed_day(dataset)
        schedule = prepared.schedule()
        files.json("input.json", {"pins": pins, **prepared.description()})
        torch.manual_seed(20261013)
        full = SmallForecaster(prepared.scale_floor, series_attention="full")
        control = SmallForecaster(prepared.scale_floor, series_attention="self-only")
        control.load_state_dict(full.state_dict())
        files.state("initial.pt", full)
        models = {"full": full, "self-only": control}
        optimizers = {name: torch.optim.AdamW(model.parameters(), lr=3e-4, betas=(.9, .999),
            eps=1e-8, weight_decay=.01, foreach=False, fused=False) for name, model in models.items()}
        checkpoint()
        for step, origins in enumerate(schedule, 1):
            x, y = prepared.batch(origins, "train")
            for name, model in models.items():
                step_start = time.monotonic()
                optimizer = optimizers[name]
                optimizer.zero_grad(set_to_none=True)
                loss = training_loss(model(x), y)
                if not torch.isfinite(loss):
                    raise RuntimeError("nonfinite training loss")
                loss.backward()
                norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
                optimizer.step()
                training_seconds[name] += time.monotonic()-step_start
                journal.append({"step": step, "variant": name, "loss": loss.item(), "preclip_norm": norm.item()})
                checkpoint()
            if step in (32, 64, 96, 128):
                for name, model in models.items():
                    validation_start = time.monotonic()
                    score = validate(model, prepared)
                    validation_seconds[name] += time.monotonic()-validation_start
                    path = name+"-step"+str(step)+".pt"
                    files.state(path, model)
                    best[name] = choose_checkpoint(best[name], step, score, path)
                    journal.append({"step": step, "variant": name, "validation": score})
                files.json("prefix-step"+str(step)+".json", {"common_steps": step,
                    "journal": journal, "best": best})
                print(json.dumps({"common_steps": step, "best": best}), flush=True)
        # Test is opened for scoring only after both independent selections are complete.
        metrics = {}
        for name, model in models.items():
            selected_path = best[name]["path"]
            raw = (files.root/selected_path).read_bytes()
            if hashlib.sha256(raw).hexdigest() != files.pins[selected_path]["sha256"]:
                raise ValueError("selected checkpoint digest mismatch")
            state = torch.load(BytesIO(raw), map_location="cpu", weights_only=True)
            model.load_state_dict(state)
            result = evaluate(model, prepared)
            metrics[name] = {"selected": best[name], "targets": result["metrics"],
                "training_seconds": training_seconds[name], "validation_seconds": validation_seconds[name],
                "test_inference_seconds": result["inference_seconds"],
                "fixed_scale_pinball": result["fixed_scale_pinball"]}
            files.json(name+"-exploratory-test.json", result)
        files.json("journal.json", journal)
        result = {"status": "candidate-complete", "common_steps": 128, "variants": metrics,
                  "point_baselines": baseline_metrics(prepared), "torch": torch.__version__,
                  "elapsed_seconds": time.monotonic()-START, "memory": checkpoint(),
                  "formal_permission": False, "test_status": "previously evaluated public day, exploratory",
                  "official_timesfm_training_reproduction": False}
        files.json("summary.json", result)
        files.json("root-closed.json", {"status": "complete", "files": files.pins})
    except BaseException as error:
        # Preserve the first error and completed common prefix; never retry this root.
        original = {"type": type(error).__name__, "message": str(error),
                    "traceback": traceback.format_exc(), "journal": journal, "best": best}
        try:
            files.json("failure.json", original, failure=True)
            files.json("root-closed.json", {"status": "incomplete", "files": files.pins}, failure=True)
        except BaseException as preservation_error:
            print(json.dumps({"original_error": original,
                "preservation_error": {"type": type(preservation_error).__name__,
                                       "message": str(preservation_error)}}), file=sys.stderr, flush=True)
        raise
    # A stdout failure after successful closure must never append to that root.
    print(json.dumps(dict(result, status="complete")), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    run(args.dataset, args.output)
