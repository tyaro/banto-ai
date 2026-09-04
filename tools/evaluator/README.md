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

正本schemaは [`schemas/anomaly-multiseed-matrix-config.schema.json`](../../schemas/anomaly-multiseed-matrix-config.schema.json)、固定configは [`examples/configs/anomaly-multiseed-v0.1.json`](../../examples/configs/anomaly-multiseed-v0.1.json)、preregistration本文は [`docs/anomaly-multiseed-evaluation-plan.md`](../../docs/anomaly-multiseed-evaluation-plan.md) です。Savepoint B以降のrunner、120-cell実行、bootstrap集計は未実装です。

## event-aware anomaly evaluation

forecast benchmarkとは別に、専用synthetic eventを対象としたcausal one-step residual評価を実行できます。validation-onlyのrobust profile、quality／gap／mode／previous-event reset、persistence、event単位matching、5-way alert partition、available score exposure、clean equipment-hour false-alertを記録します。

```text
python tools/data-generator/generate.py --root . --config examples/configs/synthetic-anomaly-evaluation-v0.1.json
python tools/evaluator/evaluate_anomalies.py --root . --config examples/configs/anomaly-evaluation-v0.1.json
# markerless／invalidなincomplete outputを退避して再実行する場合だけ追加
python tools/evaluator/evaluate_anomalies.py --root . --config examples/configs/anomaly-evaluation-v0.1.json --recover-incomplete
```

詳細なboundary、precisionのsignal-level／equipment-level区別、strict provenance、atomic publish、解釈上の制約は [`docs/anomaly-evaluation-contract.md`](../../docs/anomaly-evaluation-contract.md) を参照してください。
