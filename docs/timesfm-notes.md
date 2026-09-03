# TimesFM-3 evaluation notes

## Scope

This document defines an evaluation protocol. It does not assume a particular package layout, checkpoint URL, hardware target, or feature set until the exact implementation under test is pinned in an experiment manifest.

The first question is practical: does TimesFM-3 provide useful forecasts on industrial-like signals, compared with simple baselines, across multiple horizons and operating regimes?

## Evaluation matrix

| Dimension | Initial values |
| --- | --- |
| Signals | motor current, motor temperature, vibration proxy, conveyor speed, load proxy |
| Regimes | stopped, low speed, nominal speed, high load, startup, cooldown |
| Horizons | short, medium, and long relative to the sampling interval |
| Tasks | point forecasting first; probabilistic/quantile output when supported or via a calibrated wrapper |
| Context | recent history with a documented window; optional known covariates as a separate ablation |
| Baselines | last value, seasonal-naive, moving average, and a small learned baseline |
| Splits | chronological train/validation/test; regime and fault periods kept explicit |

## Protocol

1. Freeze the exact model release, checkpoint, tokenizer/preprocessing behavior if applicable, and runtime environment.
2. Normalize only with statistics available to the training portion of each split.
3. Resample signals explicitly; never hide irregular timestamps in a model call.
4. Evaluate each signal and horizon separately before aggregating.
5. Report results by operating regime, missing-data condition, and forecast horizon.
6. Compare against baselines on the identical windows.
7. Repeat with fixed seeds where the runtime permits and record hardware/runtime.
8. Store predictions and metrics outside Git unless they are generated from repository-safe synthetic data.

## Metrics

For point forecasts, start with MAE and RMSE. Use sMAPE only where zero-heavy signals do not make it misleading. For intervals, report empirical coverage and interval width, plus a proper interval score such as weighted interval score when the implementation supports it.

For industrial use, the report must include operational slices, not only one global score:

- startup and shutdown transitions
- steady-state nominal operation
- high-load operation
- missing or delayed observations
- regime changes
- fault-like synthetic events

## Questions to answer

- Does the model outperform a seasonal-naive baseline at the target horizons?
- Does performance transfer between equipment instances or require calibration?
- How sensitive is it to sampling rate, missing values, and mode changes?
- Are forecast intervals calibrated enough to support a normal envelope?
- Does the model degrade gracefully when the requested context is incomplete?
- What is the minimum useful runtime footprint for a Banto Hub shadow service?

## Reproducibility record

Each run should have a small manifest containing:

```yaml
run_id: <timestamp-or-uuid>
model:
  name: timesfm3
  release: <pinned-release>
  checkpoint: <immutable-reference>
data:
  dataset_id: <synthetic-or-public-id>
  split: <manifest-reference>
preprocessing:
  frequency: <duration>
  context_length: <integer>
  missing_policy: <description>
evaluation:
  horizons: [<integer>]
  metrics: [mae, rmse]
runtime:
  device: <cpu-or-accelerator>
  seed: <integer>
```

## Current non-goals

- Choosing a production checkpoint before the benchmark exists.
- Treating a zero-shot result as a commissioning profile.
- Writing thresholds, recipes, or control parameters from model output.
- Using customer data in public experiments.
