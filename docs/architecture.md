# banto-ai architecture and Banto Hub boundary

## Purpose

`banto-ai` owns research code, evaluation, model artifacts, and proposed contracts. `banto-industrial` and Banto Hub own operational data access, permissions, device identity, control integration, and production observability.

The initial architecture is deliberately one-way and reviewable:

```text
Banto Hub / historian
        |
        | approved export or read-only adapter
        v
banto-ai dataset adapter
        |
        +--> benchmark / training / evaluation
        |          |
        |          +--> model artifact
        |          +--> evaluation report
        |          +--> commissioning profile candidate
        v
shadow inference or reviewed handoff
        |
        v
Banto Hub operational consumers
        |
        v
PLC / control system (safety authority remains here)
```

## Responsibility split

| Concern | banto-ai | Banto Hub / control system |
| --- | --- | --- |
| Forecasting and anomaly research | Owns | Consumes approved outputs |
| Model training and evaluation | Owns | Does not train implicitly in production |
| Data export and access policy | Requests a contract | Owns identity, permissions, and retention |
| Equipment mode and recipe execution | Observes proposed metadata | Owns command execution and interlocks |
| Warning candidates | Proposes | Reviews, applies, or rejects |
| Emergency stop and hard limits | Never owns | Always owns |
| Promotion to production | Provides evidence | Owns approval and rollout |

## Integration stages

### Stage 1: offline export

An operator or scheduled process exports a bounded time window with a dataset manifest. The research code reads the export without needing a live connection.

Minimum metadata:

- `dataset_id` and provenance
- tag names and engineering units
- sampling interval and timezone
- equipment or line identifier, pseudonymized where required
- operating mode and recipe identifiers, if available
- quality flags, missing-value policy, and maintenance periods
- train/validation/test split definition

### Stage 2: read-only or shadow adapter

An adapter may request recent observations and return forecasts, residuals, anomaly scores, and confidence intervals. It must not write PLC values, thresholds, recipes, or interlock settings.

The adapter should expose an explicit model version and profile version on every response. If the model is unavailable, stale, out of distribution, or missing required tags, the consumer receives a clear degraded-state result rather than a silent fallback.

### Stage 3: reviewed handoff

A reviewed model artifact or commissioning profile can be promoted through Banto Hub's existing approval and deployment process. Promotion must include:

- evaluation report and baseline comparison
- training data provenance
- model and configuration hashes
- operating modes covered by the evidence
- known failure modes and rollback target
- reviewer and approval timestamp

## Proposed logical contracts

These are research contracts, not a finalized public API.

### Forecast request

```json
{
  "model_id": "timesfm3-baseline",
  "model_version": "<immutable-version>",
  "equipment_id": "<pseudonymous-id>",
  "as_of": "2026-01-01T00:00:00Z",
  "horizon": 60,
  "frequency": "1s",
  "signals": {
    "motor_current": ["..."],
    "motor_temperature": ["..."]
  },
  "mode": "shadow"
}
```

### Forecast response

```json
{
  "model_id": "timesfm3-baseline",
  "model_version": "<immutable-version>",
  "profile_version": "<optional-profile-version>",
  "status": "ok",
  "forecast": {"motor_current": ["..."]},
  "intervals": {"motor_current": {"p10": ["..."], "p50": ["..."], "p90": ["..."]}},
  "anomaly_score": 0.0,
  "quality": {"missing_ratio": 0.0, "out_of_distribution": false}
}
```

### Commissioning profile candidate

A candidate profile contains learned normal envelopes, calibration coefficients, covered recipe steps, data-quality evidence, and a validity period. It must identify which values are advisory and which values are protected from automatic promotion. The profile is not a control recipe and must not be written directly to a PLC.

## Data and artifact rules

- Raw customer data stays in the customer's approved storage boundary.
- Repository datasets are synthetic or public and include a license/provenance note.
- Exported data is immutable for an experiment run; transformations are recorded in the manifest.
- Artifacts are content-addressed or otherwise immutable after promotion.
- A model cannot be evaluated only on the data used to tune it.

## Open decisions

1. Which Banto Hub export format is stable enough for the first adapter: CSV bundle, Parquet, or a versioned API?
2. Which identity and authorization mechanism will the shadow adapter use?
3. Where will approved artifacts and commissioning profiles be stored and signed?
4. What latency, retention, and backfill guarantees are required for each use case?
