# banto-ai

Industrial AI research for forecasting, anomaly detection, adaptive commissioning, and predictive analytics within the Banto ecosystem.

This repository is intentionally separate from `banto-industrial`. It is a research workspace for experiments, evaluation protocols, model prototypes, and integration contracts. Production control behavior remains owned by Banto Hub and the PLC/control system.

## Research tracks

| Track | First question |
| --- | --- |
| TimesFM-3 evaluation | How does a foundation time-series model perform on industrial-like signals under a reproducible benchmark? |
| Mini time-series Transformer | What is the smallest useful multivariate forecasting baseline we can own and inspect? |
| Multivariate and quantile forecasting | Can the model produce calibrated ranges, not only point forecasts? |
| Anomaly detection | Can forecast residuals and learned normal envelopes detect drift early with acceptable false alarms? |
| Continual learning | How can a model adapt without allowing bad data to redefine normal operation? |
| Commissioning auto-tuning | Can a structured commissioning recipe produce a safe, reviewable equipment profile? |
| Synthetic industrial data | Can we create realistic, labeled signals before customer data is available? |
| Banto Hub integration | What read-only, shadow, and approved handoff boundaries are required for deployment? |

## Initial principles

- Customer data is never committed to this repository. Use synthetic or explicitly redistributable public data only.
- Research outputs are advisory until reviewed and explicitly promoted.
- PLC safety logic, interlocks, emergency stops, and hard protection limits remain authoritative outside the AI layer.
- Production adaptation is disabled by default. Commissioning and shadow modes are explicit states.
- Every result should record data provenance, configuration, code revision, metrics, and known limitations.

## Repository map

```text
docs/
  architecture.md              Banto Hub boundary and artifact flow
  research-roadmap.md          staged research plan and exit criteria
  timesfm-notes.md             TimesFM-3 evaluation protocol
  commissioning-learning.md   commissioning, calibration, and promotion design
  initial-issues.md             first five proposed GitHub issues
experiments/
  timesfm3/                    foundation-model benchmark work
  synthetic-data/              reproducible industrial-like data generation
  online-learning/             adaptation and drift experiments
models/
  mini-transformer/            small inspectable forecasting baseline
  industrial-tsfm/             industrial-specific model experiments
datasets/                      data policy and local dataset layout
tools/
  data-generator/              dataset generation utilities
  evaluator/                   common metrics and experiment reports
```

## Working agreement

1. Keep private or customer data outside the repository and reference it by a local dataset identifier.
2. Add a small experiment manifest before adding a new benchmark result.
3. Compare against a simple baseline before claiming an improvement.
4. Save model artifacts with their configuration and evaluation report.
5. Do not connect an experiment directly to a PLC or write control parameters automatically.

## What comes next

The first implementation milestone is a reproducible TimesFM-3 benchmark on synthetic industrial data, with naive and classical baselines. The roadmap and proposed issues are in [`docs/research-roadmap.md`](docs/research-roadmap.md) and [`docs/initial-issues.md`](docs/initial-issues.md).

## Status

Research scaffold; no production deployment path is included yet.
