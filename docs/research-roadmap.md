# Research roadmap

## North-star outcome

Provide reproducible evidence that industrial AI can forecast, detect abnormal behavior, and support commissioning while remaining observable, reversible, and separate from safety-critical control.

## Phases

| Phase | Focus | Exit evidence |
| --- | --- | --- |
| 0 | Research hygiene and contracts | Repository scaffold, data policy, experiment manifest, artifact naming, integration boundary |
| 1 | TimesFM-3 benchmark | Reproducible runner, naive/classical baselines, metrics by signal and operating mode |
| 2 | Synthetic industrial data | Parameterized generator with regimes, faults, missingness, and labels; seed-reproducible datasets |
| 3 | Owned baselines | Mini multivariate Transformer with point and quantile forecasts; ablation report |
| 4 | Anomaly and drift | Residual/envelope detectors, false-alarm analysis, data-quality and out-of-distribution handling |
| 5 | Continual learning | Safe adaptation experiments with frozen production mode, rollback, and contamination tests |
| 6 | Commissioning auto-tuning | Recipe-driven profile candidate, shadow evaluation, human approval gate |
| 7 | Banto Hub pilot boundary | Read-only export/adapter prototype and an end-to-end non-control demo |

## Priority order

The recommended first sequence is:

1. Establish a benchmark and data manifest.
2. Generate synthetic motor and conveyor signals.
3. Measure TimesFM-3, seasonal-naive, and a simple statistical baseline.
4. Implement the mini-Transformer only after the benchmark is stable.
5. Add residual anomaly scoring and mode-aware normal envelopes.
6. Test commissioning calibration offline and in shadow mode.
7. Define the smallest Banto Hub adapter that can consume approved results.

## Experiment requirements

Every experiment should record:

- objective and hypothesis
- dataset identifier, provenance, and license
- time split and leakage controls
- sampling, resampling, and missing-value policy
- feature and context window configuration
- random seeds and software/model versions
- baseline and primary metrics
- results by operating mode and fault/regime
- compute environment and runtime, when relevant
- limitations, failed runs, and next decision

## Decision gates

### Gate A: data validity

Do not compare models until timestamps, units, missingness, and split boundaries are validated. Synthetic data must have a documented generator seed and known ground truth.

### Gate B: baseline value

A more complex model proceeds only if it improves the agreed metric or provides a meaningful operational advantage such as calibrated intervals, earlier detection, or lower compute cost.

### Gate C: operational safety

No online or commissioning experiment proceeds without explicit mode, rollback behavior, stale-data behavior, and a statement of what the AI cannot control.

### Gate D: handoff readiness

An artifact is eligible for Banto Hub shadow use only after reproducibility, versioning, data-quality, and failure-mode checks pass. Shadow success never grants control authority automatically.

## Success metrics to refine

- Forecast: MAE, RMSE, sMAPE where meaningful, WIS/coverage for intervals, and horizon-wise degradation.
- Anomaly: precision/recall by incident, false alarms per operating hour, detection lead time, and alert persistence.
- Adaptation: recovery after regime change, performance under contamination, rollback correctness, and stability while frozen.
- Commissioning: profile coverage, calibration error, rejected/ambiguous steps, operator review time, and shadow false-alarm rate.
- System: p95 inference latency, resource use, missing-data tolerance, and reproducibility across runs.
