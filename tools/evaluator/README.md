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

### v0.3 S1: config/schema/pure validator

[v0.3凍結計画](../../docs/anomaly-multiseed-evaluation-plan-v0.3.md)のS0は監査合格済みです。
現在のS1は実装候補・独立監査待ちで、S2以降は未着手です。
[公開module](../../src/banto_ai/anomaly_v03.py)は標準ライブラリのみで、渡された値またはbytesを検査します。
package rootへの副作用のある自動importは追加せず、`from banto_ai import anomaly_v03`で利用します。

| 登録情報 | config | config schema |
| --- | --- | --- |
| 正常生成・overlay・split | [generator](../../examples/configs/synthetic-anomaly-v0.3.json) | [generator schema](../../schemas/synthetic-anomaly-config-v0.3.schema.json) |
| 3候補・calibration・support | [candidates](../../examples/configs/anomaly-candidates-v0.3.json) | [candidates schema](../../schemas/anomaly-candidates-config-v0.3.schema.json) |
| seed・件数・pairing | [matrix](../../examples/configs/anomaly-multiseed-v0.3.json) | [matrix schema](../../schemas/anomaly-multiseed-matrix-config-v0.3.schema.json) |
| bootstrap・gate・選択 | [analysis](../../examples/configs/anomaly-multiseed-analysis-v0.3.json) | [analysis schema](../../schemas/anomaly-multiseed-analysis-config-v0.3.schema.json) |
| provenance・相互hash | [freeze registry](../../examples/configs/anomaly-v03-freeze-registry.json) | [registry schema](../../schemas/anomaly-v03-freeze-registry.schema.json) |

結果台帳は[evaluator](../../schemas/anomaly-evaluation-result-v0.3.schema.json)、
[matrix](../../schemas/anomaly-multiseed-matrix-result-v0.3.schema.json)、
[analysis](../../schemas/anomaly-multiseed-analysis-result-v0.3.schema.json)、
[audit](../../schemas/anomaly-multiseed-audit-result-v0.3.schema.json)の4 schemaへ分けています。
各objectは再帰的にclosedです。候補IDは計画の`c0-diff-control`／`c1-phase-level`／
`c2-phase-conditional`を使用します。`overall`は集計tableにのみあり、dataset stratumは2値です。

`validate_bundle(snapshots, science_plan_raw=..., status_plan_raw=...)`へ5 config＋9 schemaの
path→raw bytesの完全なmappingを渡します。科学仕様snapshotはcommit
`4b02201f95e8ffa3a243be716872d95815a554bd`、監査後snapshotは
`0b40e7295cfa20f32889005ceca2d29d29ca340c`から取得したplan bytesです。
registry内の13 pinを照合する前に、信頼済みS1 checkoutのmoduleに置いた外部raw/canonical hashで
registry自体を検証します。registryは自分自身をpinしません。次savepointの呼出し側が、レビュー済みS1の
full commitとmoduleの`REGISTRY_RAW_SHA256`を外部provenanceとしてpinし、trusted sourceを使ってください。
未検証registryから読んだhashをそのまま信頼根拠にする使い方は禁止です。
hashテストは、浅いCI checkoutでも過去commitに依存せず実行できるよう、検証用の圧縮plan snapshotを
testsのfixtureに保存しています。復元したbytesは上記2 revisionのplan raw hashと照合します。

`validate_decoded_configs`はI/Oなしで登録値とcross-config整合性を検査します。
`evaluation_inventory`／`event_inventory`は設計台帳だけを返し、観測値を生成しません。
`validate_result_contract`はshape、ID、件数、時刻、split、claimed support／参照、pairing、statusを検査します。
返値は常に`run_status=not_run`、`engineering_status=not_evaluated`、
`performance_status=not_evaluated`、`result_trusted=false`で、入力のrun状態は`reported_run_status`へ分離します。
数値profile／score、episodeの完全列挙、matching候補列の完全性、CI／gateの再計算はS2〜S6の責務です。
M1〜M9／Q1〜Q5は今回ID・shape・enumだけを登録し、scorer挙動は未実装です。

seed registryはdev 8／smoke 2／holdout 40、bootstrapは40 clusters×50,000 replicatesです。
`bootstrap_indices()`は全2,000,000 accepted indicesだけを純粋計算し、datasetや性能指標を作りません。
1 byte連結SHA-256は`e375bf3feacb2f04bf5e1d40b141c1cfc5f69fa5437ea2704e323fd7523b22e5`。
replicate 0／1／24,999／49,999の40 index goldenをanalysis configとregistryに保存しています。

pathの検査は字句上のrelative pathだけです。symlink／junction／全reparse pointは禁止し、
将来のI/O境界で全祖先の実体、root包含、OS/runtime、nonoverwriteを確認する必要があります。
pure validatorはfilesystem/network/environmentに触れず、これらの実機確認を代行したとは報告しません。
新5 output rootsの作成、ACL、materializer／runner実行、dev／smoke／formal campaignはS1にありません。

```text
python -B -m unittest tests.test_anomaly_v03 -v
```

このS1 savepointのローカル検査対象はWindowsのCPython 3.14.0です。Python 3.12はローカルに
存在せず未実行であり、Linux／Windows両minorの正式な受入完了としては扱いません。

### v0.1 / v0.2の既存validator

Savepoint Aでは、実験前に固定した10 seed × 12 event-layoutのmatrix configだけを、matrix schema／base generator config／base generator schemaのcanonical SHA-256 pin、mode境界、expanded accounting window、event class partition、slot balance、detector／bootstrap parameter、安全なoutput pathについて検証します。summaryにはcanonicalization identifier、canonical／raw digestの意味、4つの入力schema/configのprovenance、`run_status=not_run`、`performance_status=not_evaluated`を残します。validatorはfilesystemへ書き込まず、dataset、result、bootstrap集計、性能達成を生成・主張しません。

```text
python tools/evaluator/validate_anomaly_matrix.py --root . --config examples/configs/anomaly-multiseed-v0.1.json
python tools/evaluator/validate_anomaly_matrix.py --root . --config examples/configs/anomaly-multiseed-v0.1.json --format text
```

正本schemaは [`schemas/anomaly-multiseed-matrix-config.schema.json`](../../schemas/anomaly-multiseed-matrix-config.schema.json)、固定configは [`examples/configs/anomaly-multiseed-v0.1.json`](../../examples/configs/anomaly-multiseed-v0.1.json)、preregistration本文は [`docs/anomaly-multiseed-evaluation-plan.md`](../../docs/anomaly-multiseed-evaluation-plan.md) です。Savepoint B runnerのresult schemaは [`schemas/anomaly-multiseed-matrix-result.schema.json`](../../schemas/anomaly-multiseed-matrix-result.schema.json) です。

summary integrity fix後の次versionとして固定した [`v0.2 preregistration`](../../docs/anomaly-multiseed-evaluation-plan-v0.2.md) に基づく formal replay を完了した。v0.2 validatorは [`schemas/anomaly-multiseed-matrix-config-v0.2.schema.json`](../../schemas/anomaly-multiseed-matrix-config-v0.2.schema.json) と [`examples/configs/anomaly-multiseed-v0.2.json`](../../examples/configs/anomaly-multiseed-v0.2.json) を使い、matrix id `anomaly-multiseed-v02`、output root `artifacts/anomaly-multiseed-v02`、v0.2 result schema [`schemas/anomaly-multiseed-matrix-result-v0.2.schema.json`](../../schemas/anomaly-multiseed-matrix-result-v0.2.schema.json) を選択する。120/120 cells success、engineering gate `pass`、analysis performance gate `fail` で、baselineは昇格しない。v0.1のREJECT artifactは変更していない。結果は[`v0.2 evaluation`](../../docs/results/anomaly-multiseed-v02-evaluation-2026-09-05.md)に記録する。

standalone analysisの固定configは [`examples/configs/anomaly-multiseed-analysis-v0.2.json`](../../examples/configs/anomaly-multiseed-analysis-v0.2.json)、strict result schemaは [`schemas/anomaly-multiseed-analysis-result-v0.2.schema.json`](../../schemas/anomaly-multiseed-analysis-result-v0.2.schema.json) である。analysisはmatrix artifactへwriteせず、seed-cluster ratio-of-sums、stable SHA-256 bootstrap、95% percentile CI、promotion gateを実行する。configだけを検査する場合は `--validate-only` を使う。

### exploratory failure diagnostics D2-A / D2-B

正式 v0.2 artifact の post-hoc exploratory failure diagnostics は [`docs/anomaly-multiseed-failure-diagnostics-plan-v0.1.md`](../../docs/anomaly-multiseed-failure-diagnostics-plan-v0.1.md)、[`examples/configs/anomaly-multiseed-failure-diagnostics-v0.1.json`](../../examples/configs/anomaly-multiseed-failure-diagnostics-v0.1.json)、[`schemas/anomaly-multiseed-failure-diagnostics-config-v0.1.schema.json`](../../schemas/anomaly-multiseed-failure-diagnostics-config-v0.1.schema.json)、[`schemas/anomaly-multiseed-failure-diagnostics-result-v0.1.schema.json`](../../schemas/anomaly-multiseed-failure-diagnostics-result-v0.1.schema.json) に固定する。D2-Aの `replay_and_build_diagnostics_result` はread-onlyで、最終再検査後に `VerifiedDiagnosticsResult` を返す。D2-Bの `run_and_publish_diagnostics(root, replay_head=...)` は内部でfresh replayし、この型だけをprivate stagingから固定outputへatomic no-replace directory renameで公開する。古いsealed resultを渡すAPI、output／schema／renderer override、recoverはない。任意Mappingやdraftのsemantic check成功をlive replayの証明として扱わない。input/formal artifact、customer data、network、control／Banto Hub writeは行わない。result shapeはexploratory_only=true、promotion_eligible=false、performance_status=not_evaluatedのまま。D2-Bの正式artifact診断run/build/publishはまだ実施していない。

```text
python -B tools/evaluator/diagnose_anomaly_matrix.py --root . --config examples/configs/anomaly-multiseed-failure-diagnostics-v0.1.json --validate-only
```

以下はWindows専用・未実行のrun例。非Windowsの `--run` はreplay／path検査／staging作成前にWindows-onlyエラーで拒否する。D2-A read-only replayと `--validate-only` はcross-platformのまま。`<reviewed-full-lowercase-head>`を、レビュー承認済みclean checkoutの40桁lowercase SHAに置き換える。`--validate-only`との同時指定は不可。既存outputはmarkerlessでも拒否し、自動cleanup/recoverの対象にはしない。

```text
python -B tools/evaluator/diagnose_anomaly_matrix.py --root . --run --replay-head <reviewed-full-lowercase-head>
```

Windows-onlyの公開先は `artifacts/anomaly-multiseed-v02-diagnostics-v01` のみ。準備中は固定公開先を作らず、同じ親の `.anomaly-multiseed-v02-diagnostics-v01.staging-<UUID4 lowerhex>` に3 filesをexclusive create＋flush/fsyncで準備する。private DACL付きでstagingを作り、全fileをpinした状態で通常のwrite／delete／add-childをDACLで拒否する。全再検証・receipt計算・子handle解放を済ませ、保持したdirectory handleから `SetFileInformationByHandle(FileRenameInfo, ReplaceIfExists=FALSE)` でdirectory全体をrenameする操作を最終commitとする。以降は検証・削除・権限復旧を行わない。staging内の `.complete` は準備済みを示すだけで公開成功ではない。consumerは固定公開先のexact 3-file setとstrict marker／raw hashesを検証する。失敗stagingも成功outputも自動cleanup／recoverせず、残置物は次回runで拒否する。read-onlyのため手動撤去にはownerによる権限復旧が必要。guardはrepository／artifacts／stagingに限定し、無関係なsibling作業を妨げない。意図的なpermission再変更や特権操作に対するsandbox保証はない。旧Linuxの名前ベースrename経路は削除済み。chmodだけでは親directory経由のsource-name swapを防げず、将来のLinux publisherには検証したsource identityにcommitを結び付ける別設計が必要である。詳細はplanのD2-B境界を参照。

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

Savepoint B実装に基づくv0.2の実120-cell runとstandalone analysis、bootstrap、performance判定は完了した。matrixは`run_status=complete`、status `pass`、engineering `pass`、`performance_status=not_evaluated`、analysisはengineering `pass`、performance／overall `fail` である。5つのpromotion gateはすべてfailしたため、baselineを昇格しない。customer data、checkpoint／weights、control write、Banto Hub writeはない。詳細は[`v0.2 evaluation`](../../docs/results/anomaly-multiseed-v02-evaluation-2026-09-05.md)を参照。

## event-aware anomaly evaluation

forecast benchmarkとは別に、専用synthetic eventを対象としたcausal one-step residual評価を実行できます。validation-onlyのrobust profile、quality／gap／mode／previous-event reset、persistence、event単位matching、5-way alert partition、available score exposure、clean equipment-hour false-alertを記録します。

```text
python tools/data-generator/generate.py --root . --config examples/configs/synthetic-anomaly-evaluation-v0.1.json
python tools/evaluator/evaluate_anomalies.py --root . --config examples/configs/anomaly-evaluation-v0.1.json
# markerless／invalidなincomplete outputを退避して再実行する場合だけ追加
python tools/evaluator/evaluate_anomalies.py --root . --config examples/configs/anomaly-evaluation-v0.1.json --recover-incomplete
```

詳細なboundary、precisionのsignal-level／equipment-level区別、strict provenance、atomic publish、解釈上の制約は [`docs/anomaly-evaluation-contract.md`](../../docs/anomaly-evaluation-contract.md) を参照してください。
