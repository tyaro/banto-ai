# Commissioning learning の設計

## 目的

構造化された設備試運転を、レビュー可能な commissioning profile に変換します。profile には、学習した正常挙動、校正品質、カバーした運転範囲を記録します。profile は助言用 artifact であり、PLC program や安全ロジックの代替ではありません。

## 明示的な運転モード

```text
Production
Commissioning
Maintenance
Manual
Test
Shadow
```

学習・tuning を許可するのは `Commissioning` または明示的に認可された offline replay だけです。`Production` では model parameter と学習済み profile を lock します。`Shadow` では制御動作を変更せず、score と report だけを行えます。

## レシピ駆動の流れ

```text
Draft recipe
  -> operator review
  -> data-quality check 付きで step 実行
  -> 有効な normal window を抽出
  -> baseline / envelope / calibration を推定
  -> shadow replay
  -> candidate profile をレビュー
  -> approve、reject、または rerun
  -> profile を versioning して lock
```

初期レシピには、次の step を含められます。

1. 一定時間の停止状態
2. low speed／low load
3. nominal speed／nominal load
4. 安全範囲内での high speed または high load
5. 通常生産 cycle の繰り返し
6. 必要に応じた controlled restart または cooldown

各 step に、開始条件、時間または cycle 数、期待する mode、必要な tag、data-quality threshold、operator abort path を定義します。

## 学習してよい値

候補となる値は次のとおりです。

- mode ごとの mean、variance、quantile、robust spread
- forecast bias と calibration coefficient
- residual threshold と persistence window
- speed、load、temperature、recipe、runtime を条件とする normal envelope
- 設備固有の adapter parameter
- tag 間の相関と lag feature

candidate には各値の根拠として、sample 数、時間、カバーした regime、除外 window、不確実性を残します。

## 保護する値

AI レイヤーは次を自律的に変更してはいけません。

- emergency stop と safety interlock
- hard な over-current、over-temperature、pressure、motion limit
- machine guarding と permissive logic
- PLC program logic
- actuator command と operating recipe

学習した warning candidate が有用な場合も、明示的なレビューと policy 管理された昇格を経て export します。

## Profile candidate の schema

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

## Safety と rollback の gate

次を満たさない profile candidate は承認対象にしません。

- すべての必須 recipe step に十分な有効データがある。
- maintenance または既知の fault window を normal として学習していない。
- held-out data または shadow data に対して candidate を replay している。
- 誤警報と見逃しを運転 mode ごとにレビューしている。
- 直前の approved profile を rollback 用に保持している。
- expiry と再検証条件を定義している。

## 汚染対策

- 可能な限り operator が step label を確認する。
- maintenance、alarm、sensor-quality window を baseline 学習から除外する。
- tuning に影響しない holdout segment を確保する。
- robust estimator を使い、outlier の影響を制限する。
- 最低 sample 数と regime coverage を要求する。
- promotion 評価中の profile から学習しない。
