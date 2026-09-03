# Commissioning learning design

## Objective

Turn a structured equipment trial into a reviewable commissioning profile: a description of learned normal behavior, calibration quality, and operating coverage. The profile is an advisory artifact, not a PLC program or a replacement for safety logic.

## Explicit operating modes

```text
Production
Commissioning
Maintenance
Manual
Test
Shadow
```

Learning and tuning are permitted only in `Commissioning` or an explicitly authorized offline replay. In `Production`, model parameters and learned profiles are locked. `Shadow` can score and report without changing control behavior.

## Recipe-driven flow

```text
Draft recipe
  -> operator review
  -> run step with data-quality checks
  -> identify valid normal windows
  -> estimate baseline/envelope/calibration
  -> shadow replay
  -> review candidate profile
  -> approve, reject, or rerun
  -> version and lock profile
```

An initial recipe may include:

1. stopped state for a defined duration
2. low speed / low load
3. nominal speed / nominal load
4. high speed or high load within safe limits
5. repeated normal production cycles
6. controlled restart or cooldown, if relevant

Each step needs entry conditions, duration or cycle count, expected mode, required tags, data-quality thresholds, and an operator abort path.

## Learnable values

Candidate values include:

- mean, variance, quantiles, and robust spread by mode
- forecast bias and calibration coefficients
- residual thresholds and persistence windows
- normal envelopes conditioned on speed, load, temperature, recipe, or runtime
- equipment-specific adapter parameters
- tag correlation and lag features

The candidate must retain the evidence behind each value: sample count, duration, covered regimes, rejected windows, and uncertainty.

## Protected values

The AI layer must never autonomously change:

- emergency stops and safety interlocks
- hard over-current, over-temperature, pressure, or motion limits
- machine guarding or permissive logic
- PLC program logic
- actuator commands or operating recipes

If a learned warning candidate is useful, it is exported for explicit review and policy-controlled promotion.

## Profile candidate schema

```yaml
profile_id: <immutable-id>
equipment_id: <pseudonymous-id>
source_recipe: <recipe-id>
source_run: <run-id>
mode_coverage: [stopped, low_speed, nominal, high_load]
learned:
  motor_current:
    envelope: {p10: <value>, p50: <value>, p90: <value>}
    forecast_bias: <value>
    sample_count: <integer>
quality:
  rejected_windows: <integer>
  missing_ratio: <value>
  out_of_distribution_ratio: <value>
validation:
  shadow_status: <pass|fail|inconclusive>
  false_alarm_rate: <value>
promotion:
  status: <candidate|approved|rejected|expired>
  approved_by: <identity-or-null>
```

## Safety and rollback gates

A profile candidate is not eligible for approval unless:

- every required recipe step has sufficient valid data;
- no maintenance or known fault window was learned as normal;
- the candidate is replayed against held-out data or shadow data;
- false alarms and missed events are reviewed by operating mode;
- the previous approved profile remains available as rollback;
- expiry and revalidation conditions are defined.

## Contamination defenses

- Require operator-confirmed step labels where possible.
- Exclude maintenance, alarm, and sensor-quality windows from baseline learning.
- Keep a holdout segment that cannot influence tuning.
- Use robust estimators and cap the influence of outliers.
- Require a minimum sample count and regime coverage.
- Never learn from a profile while it is being evaluated for promotion.
