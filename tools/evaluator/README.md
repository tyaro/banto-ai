# benchmark runner

`tools/data-generator/generate.py`で合成データを作成し、`check_quality.py`で品質gateを通した後、次の順で評価します。

```text
python tools/data-generator/generate.py --config examples/configs/synthetic-motor-small.json --output artifacts/generated/synthetic-motor-small
python tools/data-generator/check_quality.py --dataset artifacts/generated/synthetic-motor-small
python tools/evaluator/run_benchmark.py --config examples/configs/benchmark-small.json
```

出力は新規ディレクトリへatomic作成され、`result.json`、`predictions.jsonl`、`summary.md`を含みます。既存出力は上書きしません。合成データの結果は実設備性能を示しません。fevは現段階では導入せず、自前runnerを安全性・再現性の基準にします。

公開実データのbaselineは、外部cacheから生成したMetroPT-3標準化artifactに対して実行できます。実データ本体はGit管理せず、先に公開データ専用importerとquality gateを完了してください。

```text
python tools/evaluator/run_benchmark.py --config examples/configs/benchmark-metropt3-baselines.json
```

この設定は2020-02-21の固定24時間窓、3 target、過去120分から15分先、known-future共変量なしで、5つの統計baselineを比較します。結果は公開実データの限定区間による研究評価であり、実設備一般の性能や製品適合性を示しません。

`runtime.model_state_bytes`は各baselineのmodel名・immutable parameters・空のlearned stateをcanonical JSONへUTF-8直列化したbyte数です。stateless baselineの決定的な保存量を表し、Python objectの実メモリ量や出力file sizeではありません。`output_size_bytes_excluding_result`は`predictions.jsonl`と`summary.md`の合計で、model stateとは別です。

AutoETSは未実装で、設定に指定できません。将来評価する場合はstatsforecast等を通常runtime／CIから分離した隔離環境で候補評価します。Holt linear trendはETSとは称しません。

chronological split、point／interval metric、residual anomaly metric、calibration check、report generation の共通 utility 用です。

単一の aggregate score が運用上の失敗を隠さないよう、metric は signal、horizon、operating mode、event type 別の slice を保持します。

## benchmark matrix

`tools/evaluator/run_matrix.py`は、既存の単一runをseed、horizon、context lengthの宣言順で反復します。baseline用matrix configでは、`benchmark_config_path`にTimesFMを含まないbase benchmarkを指定します。

```text
python tools/evaluator/run_matrix.py --config <baseline-matrix-config.json>
```

展開順は`seed → horizon → context_length`です。seedはgenerator configへmaterializeされ、datasetはseedごとに一度だけ生成・品質確認して、そのseedの全cellで再利用します。matrix configと全出力pathはrepository-relativeのforward slash表記かつ`artifacts/`配下に限定され、既存のdataset／benchmark／matrix出力は上書きしません。

base generator／benchmark configは読み込んだ同じraw bytesからSHA-256を取得し、matrix開始時のcode revisionとともに固定します。各completed cellのrevision一致と、publish直前のbase config／worktree不変性を検証し、差があれば正常なmatrix resultを確定しません。生成済みdataset／runは監査用に残し、runnerが削除するのは自身のtemporary matrix directoryだけです。dataset recordにはmanifestでdataset直下に解決した観測fileのSHA-256も残し、異seedで同一観測内容ならfail closedします。

`result.json`と日本語`summary.md`の主集計は、単位を分離した`by_model_target`をmodel×target×unit×horizon×contextごとにseed間要約したcell-macro summaryです。mean／min／max／sample stddevとcell／point countを記録します。raw predictionをまとめ直すpooled metricではなく、`aggregate`／`by_model`も優劣判定には使いません。matrix runnerは評価範囲拡大の基盤であり、Phase 2完了を示しません。

## event slices（post-hoc、Toto/TimesFM/Chronos共通）

matrix実行後の既存 `predictions.jsonl` と dataset `events.jsonl` を再推論なしで、予測timestamp・context window別に分類して再集計できます。成功／部分成功cellだけを対象にし、失敗cellは除外数と制約へ残します。分類は `[start,end)`、同時イベントは `target > covariate > other` の優先順位です。

```powershell
py -3.14 tools/evaluator/analyze_event_slices.py `
  --matrix-result artifacts/benchmarks/example-matrix/result.json `
  --output artifacts/evaluator/example-event-slices `
  --root .
```

出力は新規ディレクトリの `result.json`（schema 0.1）と `summary.md` です。`macro_summary` はseedをpoolせず、cell metricのmean/min/max/sample stddevを持ち、target logical keyとunitを分離します。各cellの `event_coverage` に、予測timestampで1点以上覆われたevent IDと未cover event IDを記録します。`event_provenance` はpriority分類bucketに属したprediction rowと重なった全event IDのoverlap provenanceであり、priorityで選ばれたeventだけの一覧ではありません。`overlaps_test_split` は半開区間 `[start,end)` で判定し、`forecast_point_count` は予測row数なのでmodel／targetごとに同じイベントが重複カウントされ得ます。未coverイベントは評価済みとは解釈しません。

この機能は研究・探索専用で、既存成功予測へのpost-hocラベル付与です。missing/stale予測の頑健性や異常検知性能は測定しません。

## event-aware anomaly multi-seed preregistration validator

Savepoint Aでは、実験前に固定した10 seed × 12 event-layoutのmatrix configだけを、matrix schema／base generator config／base generator schemaのcanonical SHA-256 pin、mode境界、expanded accounting window、event class partition、slot balance、detector／bootstrap parameter、安全なoutput pathについて検証します。summaryにはcanonicalization identifier、canonical／raw digestの意味、4つの入力schema/configのprovenance、`run_status=not_run`、`performance_status=not_evaluated`を残します。validatorはfilesystemへ書き込まず、dataset、result、bootstrap集計、性能達成を生成・主張しません。

```text
python tools/evaluator/validate_anomaly_matrix.py --root . --config examples/configs/anomaly-multiseed-v0.1.json
python tools/evaluator/validate_anomaly_matrix.py --root . --config examples/configs/anomaly-multiseed-v0.1.json --format text
```

正本schemaは [`schemas/anomaly-multiseed-matrix-config.schema.json`](../../schemas/anomaly-multiseed-matrix-config.schema.json)、固定configは [`examples/configs/anomaly-multiseed-v0.1.json`](../../examples/configs/anomaly-multiseed-v0.1.json)、preregistration本文は [`docs/anomaly-multiseed-evaluation-plan.md`](../../docs/anomaly-multiseed-evaluation-plan.md) です。Savepoint B runnerのresult schemaは [`schemas/anomaly-multiseed-matrix-result.schema.json`](../../schemas/anomaly-multiseed-matrix-result.schema.json) です。

summary integrity fix後の次versionは [`v0.2 preregistration`](../../docs/anomaly-multiseed-evaluation-plan-v0.2.md) に固定する。v0.2 validatorは [`schemas/anomaly-multiseed-matrix-config-v0.2.schema.json`](../../schemas/anomaly-multiseed-matrix-config-v0.2.schema.json) と [`examples/configs/anomaly-multiseed-v0.2.json`](../../examples/configs/anomaly-multiseed-v0.2.json) を使い、matrix id `anomaly-multiseed-v02`、output root `artifacts/anomaly-multiseed-v02`、v0.2 result schema [`schemas/anomaly-multiseed-matrix-result-v0.2.schema.json`](../../schemas/anomaly-multiseed-matrix-result-v0.2.schema.json) を選択する。v0.1のREJECT artifactは変更せず、v0.2 formal runは未実施である。

standalone analysisの固定configは [`examples/configs/anomaly-multiseed-analysis-v0.2.json`](../../examples/configs/anomaly-multiseed-analysis-v0.2.json)、strict result schemaは [`schemas/anomaly-multiseed-analysis-result-v0.2.schema.json`](../../schemas/anomaly-multiseed-analysis-result-v0.2.schema.json) である。analysisはmatrix artifactへwriteせず、seed-cluster ratio-of-sums、stable SHA-256 bootstrap、95% percentile CI、promotion gateを実行する。configだけを検査する場合は `--validate-only` を使う。

```text
python tools/evaluator/validate_anomaly_matrix.py --root . --config examples/configs/anomaly-multiseed-v0.2.json
python tools/evaluator/run_anomaly_matrix.py --root . --config examples/configs/anomaly-multiseed-v0.2.json
python tools/evaluator/analyze_anomaly_matrix.py --root . --validate-only
python tools/evaluator/analyze_anomaly_matrix.py --root .
```

## event-aware anomaly multi-seed matrix runner

generator configのschema後semantic（version、equipment、regime、event、disabled event、quality-changing overlap）はgeneratorとqualityが共有するI/Oなしvalidatorで検査します。

Savepoint Bのrunnerは固定configをseed-major × layout_index昇順で120 cellへ展開します。production CLIにseed／layout／limit overrideはなく、Savepoint A validator、入力snapshot、clean git revision、event inventory、dataset／evaluation provenanceを必須境界として検証します。artifactは`artifacts/anomaly-multiseed-v01/{configs/generator,configs/evaluator,datasets,evaluations}`へ分離し、aggregateはroot直下の`result.json`、`summary.md`、`.complete`をatomic・non-overwriteで配置します。evaluatorの`pass`はcell `success`へ正規化し、`partial`／`inconclusive`／通常cell failureはinventoryへ残して継続しますが、120 cellを処理したpublished runでnon-successがあればengineering gateは`fail`です。failure cellのstage/error/reasonは安定値で、検証済みconfig・dataset・evaluation outputは各境界で再検証します。result schemaはshape、enum、path、digestを担当し、incident／profile／score／availability／statusの算術的・cross-field整合性はrunnerのruntime verifierが担当します。さらに各cellのevaluation検証では、初期snapshotからcapturedしたmanifest／generator config／observations／events／split／summary／fingerprintとcaptured hash inventoryからquality gateを同じpure実装で再計算し、evaluator provenanceのquality gate（status／counts／checks）とexact比較します。同じcaptured inputsと固定generator／evaluator configからevaluator semantics（`profiles`／`scores`／`alert_episodes`／`alert_episode_accounting`／`incidents`／`clean_false_alert_episodes`／`metrics`／`exclusions`／`status`／`row_counts`／`limitations`）を純粋再計算し、canonical JSONでexpected payloadとexact比較します。検証計算量・時間は各cellあたり概ね評価1回分を追加し、replay contextはcell完了時に破棄してpublication／runtime snapshotへ保持しません。global provenance／schema／path／revision failureはsuccess aggregateをpublishしません。未完了rootは既定で拒否し、明示的な`--recover-incomplete`時だけquarantineします。

```text
python tools/evaluator/run_anomaly_matrix.py --root . --config examples/configs/anomaly-multiseed-v0.1.json
python tools/evaluator/run_anomaly_matrix.py --root . --config examples/configs/anomaly-multiseed-v0.1.json --recover-incomplete
```

Savepoint B実装の確認時点では実120-cell run、bootstrap、performance判定を実行していないため、`run_status=not_run`、`performance_status=not_evaluated`です。customer data、checkpoint／weights、control write、Banto Hub writeはありません。

## event-aware anomaly evaluation

forecast benchmarkとは別に、専用synthetic eventを対象としたcausal one-step residual評価を実行できます。validation-onlyのrobust profile、quality／gap／mode／previous-event reset、persistence、event単位matching、5-way alert partition、available score exposure、clean equipment-hour false-alertを記録します。

```text
python tools/data-generator/generate.py --root . --config examples/configs/synthetic-anomaly-evaluation-v0.1.json
python tools/evaluator/evaluate_anomalies.py --root . --config examples/configs/anomaly-evaluation-v0.1.json
# markerless／invalidなincomplete outputを退避して再実行する場合だけ追加
python tools/evaluator/evaluate_anomalies.py --root . --config examples/configs/anomaly-evaluation-v0.1.json --recover-incomplete
```

詳細なboundary、precisionのsignal-level／equipment-level区別、strict provenance、atomic publish、解釈上の制約は [`docs/anomaly-evaluation-contract.md`](../../docs/anomaly-evaluation-contract.md) を参照してください。
