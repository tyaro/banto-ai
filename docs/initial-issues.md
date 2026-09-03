# Initial issue proposals

These are the first five issues to create when a remote GitHub repository is available. They are documented locally because this scaffold has no configured remote and should not create external issues implicitly.

## 1. Establish a reproducible TimesFM-3 benchmark runner

**Goal:** Run TimesFM-3 and simple baselines over a versioned dataset manifest and emit comparable metrics.

**Acceptance criteria:**

- A single command accepts a run manifest and produces a machine-readable result.
- The exact model release/checkpoint and preprocessing are recorded.
- Results are reported by signal, horizon, and operating regime.
- The runner includes last-value and seasonal-naive baselines.
- A smoke test runs on a tiny synthetic fixture without customer data.

**Non-goals:** Production serving, PLC connectivity, or model promotion.

## 2. Build a seed-reproducible synthetic industrial data generator

**Goal:** Generate multivariate motor/conveyor-like signals with regimes, faults, missingness, and known event labels.

**Acceptance criteria:**

- A seed fully determines the generated dataset.
- Units, sampling rate, and generator parameters are recorded.
- Startup, steady state, load changes, and at least three fault-like patterns exist.
- Ground-truth event intervals are exported separately from observations.
- The dataset can be regenerated without committing generated data.

**Non-goals:** Claiming synthetic signals represent any customer's equipment.

## 3. Implement a mini multivariate quantile Transformer baseline

**Goal:** Create an inspectable baseline for point and interval forecasting.

**Acceptance criteria:**

- Inputs support multiple aligned signals and explicit mode/context features.
- Outputs include p10, p50, and p90 or an equivalent documented interval representation.
- Training uses chronological splits and reports calibration metrics.
- An ablation compares univariate, multivariate, and mode-aware inputs.
- Model size, runtime, and failure behavior are recorded.

**Non-goals:** Beating a foundation model before the evaluation harness is stable.

## 4. Design commissioning profile calibration and shadow evaluation

**Goal:** Convert a commissioning recipe into a versioned profile candidate without changing control behavior.

**Acceptance criteria:**

- Recipe steps have explicit entry, exit, data-quality, and abort conditions.
- Baselines/envelopes are learned only from eligible windows.
- A held-out or shadow replay evaluates false alarms and coverage.
- Candidate profiles include provenance, uncertainty, expiry, and rollback metadata.
- Production mode locks learning and does not write PLC settings.

**Non-goals:** Autonomous threshold or PID writes.

## 5. Define the Banto Hub read-only adapter contract

**Goal:** Specify the smallest versioned interface for observations, forecasts, quality, and shadow results.

**Acceptance criteria:**

- Request/response examples cover model version, profile version, status, and quality.
- Missing, stale, and out-of-distribution behavior is explicit.
- The contract states identity, authorization, retention, and audit expectations.
- No endpoint writes PLC values, recipes, interlocks, or safety limits.
- A local contract test can run without a live Banto Hub.

**Non-goals:** Deploying a production service or selecting a final transport protocol.
