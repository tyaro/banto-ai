# 研究ロードマップ

## 最終的な目標

産業 AI が、予測・異常検知・試運転支援に有効であることを、再現可能な根拠として示します。同時に、可観測で、元に戻せて、安全重要な制御から分離されていることを満たします。

本書は研究テーマの長期的な順序を示します。候補モデルの比較は [`time-series-model-survey.md`](time-series-model-survey.md)、直近の作業、期間目安、暫定合格基準は [`research-implementation-plan.md`](research-implementation-plan.md) を参照してください。

公開産業データの選定と repository 外の取得境界は [`public-dataset-survey.md`](public-dataset-survey.md) と [`adr-0005-public-dataset-boundary.md`](adr-0005-public-dataset-boundary.md) を参照してください。第一候補は UCI MetroPT-3、次候補は UCI hydraulic systems、NASA C-MAPSS は公式 license 未指定のため採用見送りです。MetroPT-3のsource pin、標準化取込、Public-only quality gateは検証済みで、結果は[`docs/results/metropt3-import-2026-09-04.md`](results/metropt3-import-2026-09-04.md)に記録しています。

## フェーズ

| Phase | 焦点 | 2026-09-06の状態 | 完了時の根拠 |
| --- | --- | --- | --- |
| 0 | 研究基盤と契約 | complete | Python環境、データ方針、experiment／license manifest、共通interface、連携境界 |
| 1 | 合成データとbaseline | complete | 運転状態、fault、欠損、labelを持つgeneratorと、naive／古典baselineの再現性 |
| 2 | Forecast model benchmark | active / incomplete | TimesFM 3.0の評価済み結果を基準に、Chronos-2とTotoを同一契約へ追加し、Granite TTMは別sensitivity条件、自前／学習型baselineは別評価 |
| 3 | 異常とドリフト | active | 統計方式、forecast residual、TSPulse、Riverのevent単位比較 |
| 4 | 自前モデル研究 | not started | 点予測・分位点予測を備えた小型multivariate Transformerとablation |
| 5 | Commissioning auto-tuning | not started | レシピ駆動のprofile candidate、shadow評価、人手承認gate |
| 6 | Continual adaptation | not started | 本番mode固定、rollback、汚染testを含むfrozen model + profile適応 |
| 7 | Banto Hub pilot境界 | not started | read-only export／sidecarの試作と、制御を変更しないend-to-end demo |

## 推奨する優先順

1. package、dataset／run／license manifest、共通interfaceを確立する。
2. motor・conveyorに近い合成信号とnaive／統計baselineを作る。
3. Chronos-2、TimesFM 3.0、Toto 2.0 4m／22mを同じrunnerで測定し、Granite TTMはcontext=512／target-onlyの別sensitivity runnerで測定する。
4. 統計anomaly、forecast residual、TSPulseをevent単位で比較する。
5. benchmarkが安定してからmini-Transformerと対象データ学習型modelを実装する。
6. commissioning校正をofflineとshadow modeで検証する。
7. frozen base modelとversioned profileによる安全な適応を検証する。
8. 承認済み結果を利用できる最小限のBanto Hub read-only adapterを定義する。

## 2026-09-06時点の進捗

Toto 2.0 4Mは同じForecaster／MetroPT runnerへ実装接続し、固定HF revision、外部cache、offline／CPU／batch=1／`decode_block_size=None`でCPU smokeと実benchmarkを実行済みです。context=120はpatch_size=32に合わせて先頭8点の未観測paddingを内部追加します。6 models、3 targets、16 validation／16 test origins、4,320 predictionsの結果を[`docs/results/toto2-metropt3-evaluation-2026-09-04.md`](results/toto2-metropt3-evaluation-2026-09-04.md)に記録しました。22M、seed拡大、fault slice、実設備一般化は次工程です。

Toto 2.0 4Mの小規模matrixも、seed `[17, 42]` × horizon `[15, 30]` × context `[64, 120]`、2 equipment、各seed 480 samples／equipment、8/8 cells success／0 partial／0 failedで完走しました。正本とtarget別cell-macro metrics、exact origin、runtime、memory、padding境界は[`docs/results/toto2-matrix-2026-09-04.md`](results/toto2-matrix-2026-09-04.md)に記録しています。2 seed・少数origin・単一synthetic generatorの限定結果であり、次はseedを5以上、origin拡大、missing／stale／fault／regime slice、model-only resource、22M、公開／実設備一般化です。

Phase 2の基盤として、chronological rolling-origin runnerへmodel registry注入境界、equipment／model単位のinstance再利用、origin単位のmulti-target request、past-only／known-future covariate境界、model別quantile policy、共通origin選択とprovenance記録を追加しました。result schema `0.2`にはmodel-target別およびmodel-equipment-target別metricsを追加し、unit一致を検証してから設備横断集約します。結果にはmodel別metrics、model別latency、OS process peakの測定源も記録します。TimesFM 3専用entrypointは、既存のlicense manifest、固定checkpoint revision、artifact hash、専用外部cache、offline環境を検証してから実行します。実行用sampleは[`examples/configs/benchmark-timesfm3-small.json`](../examples/configs/benchmark-timesfm3-small.json)です。

2026-09-04に、LastValueとの小規模なTimesFM 3 rolling-origin実測と、統計baselineを含むtarget別比較を追加しました。`synthetic-motor-small`、seed 42、2 equipment、各2 validation／test origin、context 12、horizon 3の限定条件です。target別比較の詳細は[`docs/results/timesfm3-baselines-comparison-2026-09-04.md`](results/timesfm3-baselines-comparison-2026-09-04.md)、旧composite結果の経緯は[`docs/results/timesfm3-rolling-benchmark-2026-09-04.md`](results/timesfm3-rolling-benchmark-2026-09-04.md)に記録しています。past-onlyではTimesFM 3が温度MAEで最良でしたが、電流ではmoving-average等に劣りました。known-loadは計画値をorigin時点で取得できるsynthetic oracle-styleの別scenarioであり、実績先読みや本番効果を示しません。

次の評価範囲拡大に向け、seedをgeneratorへ反映してdatasetを再生成し、horizon／context lengthとのmatrixを安全に反復する基盤を追加しました。datasetはseedごとに一度生成・品質確認し、観測file hashでseed差の実体を確認します。base config raw bytesと開始code revisionを固定し、cell／publish時の不変性も検証します。主集計は単位別のseed間cell-macro summaryです。

この基盤で2 seeds×2 horizons×2 context lengthsの実TimesFM matrixを完走し、8 cells success／0 failureを[`docs/results/timesfm3-matrix-2026-09-04.md`](results/timesfm3-matrix-2026-09-04.md)へ記録しました。TimesFM 3は温度の4条件でMAE最良、電流では4条件とも6モデル中4位でした。ただし2 seeds、少数origin、単一generatorの結果で、coverage／WISも暫定です。seedを最低5以上、origin／条件追加、欠損・fault・regime別、モデル単独resource測定、他候補との同一契約比較、実設備でのplanned-load契約検証が残っています。重みはresearch-only／non-commercialであり、製品・顧客PoC・PLC／Banto Hub write経路へ昇格させず、Phase 2も未完了です。

TimesFM 3.0の限定matrix評価後、Chronos-2へ比較軸を移しました。`chronos-forecasting==2.3.1`、固定checkpoint revision／実計算SHA-256、repository外cache、offline読み込み、native quantile（pointはp50）を契約として、公式API direct CPU smokeとBanto adapter／tool smokeを完了しました。さらに、60 samples×2 equipment、context 12、horizon 3、各equipment validation／test各2 originsの初期rolling benchmarkを完走しました。

past-only 6 modelsではChronos-2のaggregate MAEは`0.20672198138554906`、WISは`0.1952207659517925`でした。origin時点で確定済みの計画値を模したknown-future 7 modelsでは、MAE `0.1691488806622826`、WIS `0.15937026919725228`で1位となり、past-onlyから改善しました。ただし電流MAEはmoving-average、温度MAEはHolt linearが優位で、aggregateはAとdegCを混合する比較値です。小標本・単一seed・合成データで、runはdirty worktreeを記録しているため、製品性能や一般性能を示しません。詳細は[`docs/results/chronos2-initial-evaluation-2026-09-04.md`](results/chronos2-initial-evaluation-2026-09-04.md)に記録しています。

Chronos-2のseed `[17, 42]`×horizon `[1, 3]`×context `[6, 12]`の実model matrixは、固定clean HEAD `3f57c8500f2a746dd0fce1d02bb9eba566d47748`から8/8 cells success／0 failureとなりました。currentは4条件すべてmoving-averageがMAE首位で、Chronos-2はMAE 3位または4位でした。temperatureはWIS 4条件すべてChronos-2が1位で、MAEはcontext 6の2条件で1位でした。context 12が常に改善しないことも確認しました。詳細は[`docs/results/chronos2-matrix-2026-09-04.md`](results/chronos2-matrix-2026-09-04.md)に記録しています。

このmatrixは2 seed、単一の合成generator、2 equipment、各equipment validation／test各2 origins、CPUのみの小標本であり、一般性能や実設備性能を示しません。matrix固有の次はorigin拡大、missing／stale／regime／fault slice、context探索、モデル単独resource測定です。公開データについてはMetroPT-3のsource pin、標準化取込、Public-only quality gateに加え、Chronos-2、TimesFM 3.0、5 baselineの限定rolling benchmarkを完了しました。package・code・weightsはApache-2.0ですが、追加gateが完了するまでChronos-2は`commercial-evaluation`に留め、`product-candidate`へ昇格しません。TimesFM 3.0は重み条件によりresearch-onlyの比較基準として残します。

2026-09-04に、固定24時間・1設備・3 targetのMetroPT-3公開実データで、統計baseline 5モデルのrolling-origin benchmarkを完走しました。context 120分、horizon 15分、validation／test各16 origins、past-only covariate 11、known-future 0、validation residual by leadの契約です。test prediction 3,600件、quality gate PASS、dataset fingerprint `e6210e4e48e05c025fc8895ddeddf0c53a49dc53fd1c2f49e8c3272a3c7b37b0`で、詳細は[`docs/results/metropt3-baseline-evaluation-2026-09-04.md`](results/metropt3-baseline-evaluation-2026-09-04.md)に記録しました。

同じ契約でChronos-2 nativeとpoint-calibratedの2 scenario、TimesFM 3.0のnative scenarioも実施しました。Chronos nativeは公式分位点の交差を補正せずpartialとして失敗証跡を維持し、point-calibratedは公式point-only予測＋validation residual by leadでsuccess、TimesFM 3.0はcrossingなしのsuccessとなりました。Chronos-2のtarget別metrics、hash、runtime、限界は[`docs/results/chronos2-metropt3-evaluation-2026-09-04.md`](results/chronos2-metropt3-evaluation-2026-09-04.md)、TimesFM 3.0は[`docs/results/timesfm3-metropt3-evaluation-2026-09-04.md`](results/timesfm3-metropt3-evaluation-2026-09-04.md)に記録しています。これは限定区間のforecast研究評価で、実設備一般の性能、製品適合性、異常検知性能を示しません。Phase 2全体は未完了です。

Toto 2.0 4Mの既存matrix予測に対するevent slice post-hoc解析を完了しました。8/8 cells analyzed、excluded 0、8,640 predictionsで、forecast target eventとして実際に評価されたのは`conveyor-01.motor_temperature`のoverheatだけです。`motor-01-slip-test`の`motor_current` faultは全cellでforecast未coverのため、anomaly detectionやmissing／stale robustnessの結果ではありません。正本hashとToto target-eventの限定metricは[`docs/results/toto2-event-slices-2026-09-04.md`](results/toto2-event-slices-2026-09-04.md)に記録し、Totoは`commercial-evaluation`、Phase 2未完了を維持します。次gateはseed最低5、origin／event位置／設備／mode拡大、専用fault／missing／stale scenario、event単位不確実性です。

Toto 2.0 controlled 4-track acceptance analyzerのsource、固定config/schema、fake artifact unittestを追加し、2026-09-05にformal controlled runを完了しました。4 matrix各20/20 success、acceptance `pass`、80/80 cells、1,920/1,920 groups、1,440/1,440 paired deltas、availability delta 0を確認しています。詳細は[`docs/results/toto2-controlled-evaluation-2026-09-05.md`](results/toto2-controlled-evaluation-2026-09-05.md)に記録しています。analyzerはcontrolから各degradedへの同一model/group paired deltaだけを出し、cross-model rankingを禁止します。synthetic／4M／CPUの契約受入であり、実設備性能やmodel採用判断は追加していません。

次のsavepointとして、forecast benchmarkから分離したevent-aware anomaly evaluation v0.1を追加しました。validation-only robust residual profile、quality／gap／mode reset、persistence、machine／sensor faultのincident matching、data-quality／ignored除外、clean equipment-hour false-alert集計、strict provenanceとatomic publishを専用synthetic scenarioで固定しています。single-seed契約検証であり、Toto性能、lead time、実設備性能、制御writeは示しません。v0.2固定計画 [`anomaly-multiseed-evaluation-plan-v0.2.md`](anomaly-multiseed-evaluation-plan-v0.2.md) に従う正式multi-seed replayとstandalone analysisは完了しましたが、performance gateはfailであり、実設備性能やモデル昇格は示しません。詳細は[`anomaly-multiseed-v02-evaluation-2026-09-05.md`](results/anomaly-multiseed-v02-evaluation-2026-09-05.md)を参照してください。

### Phase 3: multi-seed anomaly replay result

10 seed × 12 event-layout、120 cellsのstdlib-only offline replayを、実装前に固定したschema/configとengineering／performanceの二段gateで実施しました。canonical JSON identity（UTF-8、sort keys、compact separators、末尾改行なし）によるschema/config pinとraw-byte監査値、expanded accounting windowのmode/test内収容、seed-cluster block bootstrap、8個の完全修飾target signal availability、stopped／cooldown faultのsynthetic stress testとしての位置付けを含むseed、layout、detector parameter、指標、promotion閾値、安全境界は v0.2固定計画 [`anomaly-multiseed-evaluation-plan-v0.2.md`](anomaly-multiseed-evaluation-plan-v0.2.md) に記録しています。matrix／analysis artifact とも engineering gate は `pass`、performance gate は matrix `not_evaluated`、analysis `fail` で、5つの promotion gate はすべて fail しました。v0.1の正式120-cell artifactは生成後監査でsummary integrity bypassが見つかったためREJECT evidenceとして保全し、詳細を[`anomaly-multiseed-v01-integrity-audit-2026-09-05.md`](results/anomaly-multiseed-v01-integrity-audit-2026-09-05.md)に記録しています。v0.2の結果と判断は[`anomaly-multiseed-v02-evaluation-2026-09-05.md`](results/anomaly-multiseed-v02-evaluation-2026-09-05.md)を参照してください。baselineは昇格せず、v0.3 preregistrationでphase／recipe-step／time-since-mode-entry／conditional-level／longer clean calibration／multivariate residual、machine fault sensitivity、false-alert reduction、data-quality dropoutとavailability gate handlingを別途検討します。TimesFM3 residual／scoringは別の後続候補です。

v0.2 failure diagnosticsは、固定計画に従うD2-Bを正式公開し、Astra/maxによる
独立read-only監査とresult文書まで完了しました。`engineering_status=pass`、
`performance_status=not_evaluated`、`exploratory_only=true`、
`promotion_eligible=false`です。canonical detectionを保持した因果的supportは0/240で、
v0.3の仮説材料にのみ使います。計画は
[`anomaly-multiseed-failure-diagnostics-plan-v0.1.md`](anomaly-multiseed-failure-diagnostics-plan-v0.1.md)、
正式な結果と監査境界は
[`anomaly-multiseed-v02-failure-diagnostics-2026-09-06.md`](results/anomaly-multiseed-v02-failure-diagnostics-2026-09-06.md)
を参照してください。計画内の古い「未実施」はfreeze時点の記録であり、遡及変更しません。

v0.3は実装前S0計画候補をcommit
`41decf9b6f8d6c876715729516354bf6da49422c`に作成しましたが、このcandidate stackは
main未統合です。初稿へのAstra/max監査はP0/P1 0件・P2 3件で、その3件を
文書同期commit `e92c83df03b2f798d60246e14411d249a0b76202`の上の監査対象
`4b02201f95e8ffa3a243be716872d95815a554bd`で修正しました。
最初のequipment episodeを固定する再探索なしmatchingと境界fixture、event/quality適用後の
6桁丸めと保存済みfit/calibration/test入力、Linux 3.12/3.14共通試験とWindows native受入を
明記しました。正式runtimeはWindows 11 Pro 25H2 build `10.0.26200.9168`／CPython `3.14.0`です。
独立再監査はP0〜P3 0件で合格し、`SCIENCE_READY=yes`、`FREEZE_READY=yes`、
`DOCS_READY=yes`、`IMPLEMENTATION_READY=yes`、`STACK_READY=yes`としてS0をfrozen・adoptedにしました。
S0監査記録commit `0b40e7295cfa20f32889005ceca2d29d29ca340c`の上で、5 config、9 schema、
pure semantic validator、全seed・bootstrap goldenの固定とadversarial testsをS1として追加しました。
S1初回監査（`0368769acf12a0279c84f30c6435e853208386e9`）はP2=6／P3=1件でした。
修正commit `d6ca0f9ee85172caae3b658bdb105287f8e43141`への独立再監査はP0〜P3 0件で合格し、
S1は完了し、candidate stackはmain統合済みです。S2ではpure scoring、episode、causal matching、固定分母を実装し、独立監査はP0〜P3 0件でした。S2監査結果は
[`anomaly-multiseed-v0.3-s2-audit-2026-09-06.md`](results/anomaly-multiseed-v0.3-s2-audit-2026-09-06.md)に記録しています。S2はformal run、性能評価、promotionを意味せず、Linux正式受入やWindows native／DACL／AccessCheck受入も未実施です。
その後、S3 deterministic runnerを実装し、固定inventory、paired materialization、完全ledger、安全停止、provenance、non-overwrite publisherを独立監査しました。実装commit群は`bdd59c5`、`2a01146`、`bb42d37`、`dc52266`、監査P0〜P3は0件、`S3_READY=yes`、`INTEGRATION_READY=yes`です。S4-A engineering inspection/resource guardも`8befc5bb`と`e61d14c4`でmainへ統合し、初回P2/P3修正後の再監査P0〜P3は0件、`S4_A_READY=yes`となりました。CI [run 34057314195](https://github.com/tyaro/banto-ai/actions/runs/34057314195)はPython 3.12/3.14の全工程greenでした。S4-Aは本番試験前の車検機能であり、正式試験はまだ開始していません。受入は`not_completed`のまま、次はS4-B native publisher/DACL/restricted-token/race harnessです。正式output rootとformal dev/smoke/holdout実行権限はS4受入まで閉鎖します。
S0の監査根拠は
[`anomaly-multiseed-v0.3-plan-audit-2026-09-06.md`](results/anomaly-multiseed-v0.3-plan-audit-2026-09-06.md)、
S1の初回指摘・修正・監査境界は
[`anomaly-multiseed-v0.3-s1-audit-2026-09-06.md`](results/anomaly-multiseed-v0.3-s1-audit-2026-09-06.md)、
候補本文は[`anomaly-multiseed-evaluation-plan-v0.3.md`](anomaly-multiseed-evaluation-plan-v0.3.md)、
最新の文書状態と正本の読み方は[文書索引](README.md)を参照してください。

## 実験の必須記録

すべての実験に、次を記録します。

- 目的と仮説
- dataset identifier、出所、license
- 時系列 split と leakage 対策
- サンプリング、resampling、欠損値方針
- feature と context window の設定
- random seed と software／model version
- ベースラインと主要指標
- 運転モード・fault／regime ごとの結果
- 必要に応じて計算環境と実行時間
- 制約、失敗した実行、次の判断

## 判断ゲート

### Gate A: データの妥当性

timestamp、単位、欠損、split 境界を検証するまでモデルを比較しません。合成データには generator の seed と既知の ground truth を記録します。

### Gate B: ベースラインに対する価値

複雑なモデルへ進むのは、合意した指標が改善するか、校正済み interval、早期検知、計算コストなどの運用上の明確な利点がある場合だけにします。

### Gate C: 運用安全性

online または commissioning 実験へ進む前に、mode、rollback、stale data の挙動と、AI が制御できない範囲を明示します。

### Gate D: handoff 準備

再現性、versioning、データ品質、失敗モードの確認に合格した artifact だけを Banto Hub の shadow 利用候補にします。shadow の成功だけで制御権限を自動付与してはいけません。

## 追って具体化する成功指標

- Forecast: MAE、RMSE、妥当な場合の sMAPE、interval の WIS／coverage、horizon 別の劣化。
- Anomaly: incident 別 precision／recall、運転時間あたりの誤警報、検知リードタイム、alert の持続性。
- Adaptation: regime 変更後の回復、汚染下の性能、rollback の正しさ、固定中の安定性。
- Commissioning: profile coverage、校正誤差、却下・判定不能な step、オペレーターのレビュー時間、shadow 誤警報率。
- System: p95 inference latency、リソース使用量、欠損耐性、実行間の再現性。
v0.2のstandalone seed-cluster analysisは [`anomaly-multiseed-evaluation-plan-v0.2.md`](anomaly-multiseed-evaluation-plan-v0.2.md) の固定config、stable SHA-256 bootstrap、ratio-of-sums、slice別CI、strict read-only artifact verifierを使って完了しました。engineering gateは`pass`、performance gateとoverall statusは`fail`であり、formal run、analysis、bootstrap、promotion判定の詳細は[`anomaly-multiseed-v02-evaluation-2026-09-05.md`](results/anomaly-multiseed-v02-evaluation-2026-09-05.md)に記録しています。

## 2026-09-24: v0.3開発・動作確認720評価と比較

単一writerの運用経路で、dev 8 seeds/576評価とsmoke 2 seeds/144評価、計120区間/720評価の実行・保存照合が完了しました。最後の区間の失敗attemptは保持し、再試行成功分だけを集計しています。[完走記録](results/anomaly-multiseed-v0.3-final-chunk-retry-2026-09-24.md)。

保存監査に基づく記述的な比較では、C1（運転段階別の正常値）は機械異常91.67%、センサー異常95.00%、警報正解率95.73%。C2は機械89.92%、センサー95.00%、警報正解率94.83%でした。停止中のコンベヤー、C2の停止中モーター、欠損とセンサー異常が重なる条件が次の切り分け対象です。[比較表と残項目](results/anomaly-multiseed-v0.3-dev-smoke-comparison-2026-09-24.md)、[上司向け説明](results/banto-ai-anomaly-briefing-2026-09-24.md)。

全scoreの再生成なしで既存120監査reportを利用しました。これは合成dev/smokeの記述統計であり、holdout、bootstrap信頼区間、正式gate、完全S6、方式の正式選択・昇格は未実施です。Phase 3はactiveのまま、独立score検算・正式実行条件の整理と、別方式や公開/実設備への一般化が残ります。Phase 2のforecast比較の残項目は今回の試験では解消しません。凍結済み科学計画と登録済み3候補を維持し、保留した専用principal試験は再開していません。

## 2026-09-24: 全720保存評価の独立profile・score・ledger検算

続いて、全120区間/720評価の保存観測から正常profile・残差・scoreを別実装で復元し、警報・異常との照合・集計まで一致を確認しました。正常profile 34,560件、score 10,368,000行が対象です。前回の比較表の全720件ともidentity・attempt・件数・指標が一致しました。[検算結果と対応範囲](results/anomaly-multiseed-v0.3-full-connected-audit-2026-09-24.md)に保存しています。

検算済みの6評価を全対象入力hash一致後に再利用し、残り714評価を順次検算しました。6新規区間ごとに中間保存し、約19分56秒、process peak private約188MiBで完了しています。追加のproducer・登録seed生成・holdoutは起動していません。

保存観測→profile/score→ledgerの独立検算は全720件で完了しました。正常生成・overlay・丸め工程、bootstrap/信頼区間、正式gate/holdout、runtime/運用受入は残ります。Phase 3はactive、Phase 2のforecast比較の残件も維持します。C1/C2の既存の記述統計は変わらず、正式採択や実設備の性能保証には進めていません。

### 2026-09-24：正常生成から保存観測までの検算完了

全120区間・240データセットについて、正常生成式、異常の重ね方、欠損処理、丸めから復元した4,320,000観測行が保存bytesと完全に一致しました。前回の全720評価のprofile/score/ledger検算とも入力hashで接続しました。[詳細](results/anomaly-multiseed-v0.3-independent-generation-audit-2026-09-24.md)。保存済みseedをメモリ内で再構成する検算で、新規データセットやholdoutは作成していません。

次はbootstrap/信頼区間/候補比較の独立実装と手計算fixtureを検証します。正式計画の40 holdout seedを現dev/smoke 10 seedで代用せず、正式gateや採択判定は進めません。Phase 3 active、Phase 2 forecast比較・runtime/単一writer受入の残件も維持します。

### 2026-09-24：信頼区間・候補比較の計算部分を検証

独立した計算部分を実装し、手計算21試験と固定200万個のbootstrap抽出番号照合を通過しました。件数の合算、候補間の共通抽出、分母0の扱い、全層・全信号の判定とC1優先選択を確認しています。[検証結果](results/anomaly-multiseed-v0.3-independent-inference-math-2026-09-24.md)。

実データの信頼区間は未算出です。次は監査済み結果のseed単位集計を認証する入口を実装します。dev/smokeを正式40holdoutの代わりに使わず、正式採択・完全S6・Phase 2/3全体は未完了を維持します。

### 2026-09-24：監査済み結果のseed単位集計を完了

検算済み720評価を保存点のhashで認証し、開発用8 seedと動作確認用2 seedを分けて集計しました。各seedの12区間・両条件・3候補を確認し、seed別90表と用途別18表、候補差12表が過去の記述集計と一致しました。警報0件の適合率46評価もnullとして保持しています。関連33試験通過、処理約1.3秒、最大メモリ約39MiB。[結果](results/anomaly-multiseed-v0.3-independent-seed-aggregation-2026-09-24.md)。

次は独立analysis出力とschemaの接続を手例で確認します。正式40 holdoutの解析を現10 seedに代用せず、実信頼区間・正式gate・完全S6・Phase 2/3全体は未完了を維持します。

### 2026-09-24：解析結果表の出力形式への接続

独立した計算結果を所定の9表へ変換し、候補比較・分母0・判定不能の扱いを7手例で確認しました。関連59試験通過。検出遅延の中央値は元の値を結合して計算し、区間別中央値の平均を避けています。[結果](results/anomaly-multiseed-v0.3-analysis-table-adapter-2026-09-24.md)。

検証したのは表の形式と手例の整合性で、正式な解析文書全体や実データの信頼区間はまだ完成していません。次は保存済み実データの検出遅延と条件別内訳の独立集計です。正式holdout/gate・完全S6・Phase 2/3全体の残件を維持します。

### 2026-09-25：保存結果の遅延と条件別の集計を完了

720評価から、検出までの時間と設備・運転段階・信号品質などの条件別件数を集計しました。約1,037万判定行と14,400異常事例を確認し、用途別・seed別の全108表が既存の検出件数等と一致しました。見逃しを遅延0秒にせず、開発用と動作確認用を分けています。関連32試験通過、最大メモリ約145MiB。[結果と集計の定義](results/anomaly-multiseed-v0.3-independent-slice-audit-2026-09-25.md)。

次はcounts・遅延・条件別表を認証済みの解析入力にまとめ、正式報告に不足する証拠を整理します。今回も追加評価や実CIは行っていません。正式holdout・性能判定・runtime受入が残るため、Phase 2/3全体の完了ではありません。

### 2026-09-25：検算済み集計を解析入力へ統合

720評価の件数・遅延・条件別内訳・診断を用途別にまとめ、108表の対応と48組の加算を確認しました。大きな元評価ファイルを読まず、集計約5.5MBから約3.2秒で作成。39試験通過、最大メモリ約53MiB。[統合結果と正式判定の残件](results/anomaly-multiseed-v0.3-analysis-inputs-2026-09-25.md)。

正式schemaの必須10項目について、用意できた情報と不足する証拠を整理しました。次は用途別の記述結果表と診断表への出力です。正式holdout・信頼区間・性能判定・source/runtime受入・完全S6は未完了で、Phase 2/3全体の完了にはしません。

### 2026-09-25：用途別の結果表・全条件別診断表を出力

検算済み720評価から、開発用と動作確認用を分けた18結果表・5,670診断行を作りました。検出率、利用可能率、閾値超過率、警報開始率を区別し、元入力との全セル照合と所定の表形式の検査を通過。27試験通過、閲覧用の要約と展開式HTMLを保存しました。[結果](results/anomaly-multiseed-v0.3-descriptive-report-2026-09-25.md)。

次は既存のsource/runtime・単一writer受入記録とconsumer実装を対応づけ、freeze前の残件を確定します。今回も正式holdout・信頼区間・性能判定を実施しておらず、Phase 2/3全体は未完了です。

### 2026-09-25：正式評価前の残件を整理

[受入証拠と接続状況](results/anomaly-multiseed-v0.3-acceptance-gap-review-2026-09-25.md)を確認しました。既存の保存・独立検算を再利用し、freeze前の作業を「運用契約、解析側の接続、版と実行環境の固定、保存経路の接続、容量・時間の計画」の5まとまりに整理しました。試験数やPhase 2/3全体の残件数ではありません。

11保存点と3小型記録のhashを確認し、720評価を再計算していません。依存ファイル1本の改行差、本流での別作業、Windows更新後の状態を記録しました。次は単一writer方針で解析側の入出力と公開手順の契約案を具体化します。正式評価・性能判定は未実施です。


### 2026-09-25：解析側の入力・検証・保存手順を具体化

[契約案](anomaly-v03-consumer-io-proposal.md)で、入力の認証から独立検算、保存、別readerと独立監査までの手順を定めました。既存10モジュールを再利用する箇所と、追加で確認する接続12群を対応づけています。12群を新たに試験したわけではなく、評価データや正式評価は実行していません。[確認記録](results/anomaly-multiseed-v0.3-consumer-io-contract-2026-09-25.md)。

次は評価データを読まず、入力の種類・完全性・失敗状態を検査する部分の実装です。正式運用契約と診断表の対応は提案段階で、5作業群全体やPhase 2/3の完了にはしません。


### 2026-09-25：解析に渡す入力宣言の検査を実装

[入力検査](anomaly-v03-consumer-input.md)を実装し、22試験が通過しました。対象の欠落・順序違い、候補間/再試行間の入力hash不一致、失敗履歴の不整合を拒否し、途中停止と計算上の判定不能を分けて保持します。評価データは読まず、正式評価の起動にも接続していません。[結果](results/anomaly-multiseed-v0.3-consumer-input-validator-2026-09-25.md)。

次は保存済みの完了記録から、この検査へ渡す入力宣言への変換です。検査成功は実データの認証や実行許可を意味せず、正式受入・Phase 2/3全体は未完了です。

### 2026-09-25：保存済み完了記録と入力検査を接続

[checkpoint adapter](anomaly-v03-consumer-checkpoints.md)を実装し、新規15＋既存22の37試験が通過しました。保存済みの管理記録でも全120区間・720評価との対応を確認し、最後の再試行前の失敗を残したまま最終attemptを選択します。観測やスコアの再計算はありません。[結果](results/anomaly-multiseed-v0.3-consumer-checkpoint-adapter-2026-09-25.md)。

区間別の公開印と全体の終了は別に認証する必要があり、そのreader結合を次に進めます。正式評価・運用契約採択・Phase 2/3全体は未完了です。

### 2026-09-25：公開完了の印と終了記録を接続

[公開metadata reader](anomaly-v03-consumer-publication.md)を実装し、14新規試験が通過しました。全120区間の公開印・結果目録・worker終了記録を照合し、720評価の管理参照を確認しています。観測/スコアは再計算していません。[結果](results/anomaly-multiseed-v0.3-consumer-publication-reader-2026-09-25.md)。

次は既存の独立監査済み集計入力とのhash対応を固定します。全payloadの再認証、controllerプロセス自体の終了認証、正式受入・Phase 2/3全体の完了とは区別します。

### 2026-09-25：監査済み集計入力と公開記録を結合

[結合API](anomaly-v03-consumer-analysis-binding.md)を実装し、14新規試験が通過しました。全120区間・720評価の公開記録と集計入力が同じ最終attempt・input/evaluation hashを参照することを確認し、失敗履歴と判定不能46指標を維持しています。旧数値検証を再利用し、観測/scoreを再計算していません。[結果](results/anomaly-multiseed-v0.3-consumer-analysis-binding-2026-09-25.md)。

次はengineering consumerの入力選択・記述結果までの入口を接続します。全payloadの新規認証、正式運用契約採択、source/runtime freeze、Phase 2/3全体は未完了です。

### 2026-09-25：engineering consumerの入力から結果保存までを接続

[API/CLI](anomaly-v03-engineering-consumer.md)を実装し、16新規試験が通過しました。7保存fileを認証し、全120区間720評価の記述結果18表・234主指標・5,670診断行を新規保存・読み戻し確認しました。旧数値検証を再利用し、集計や観測/scoreを再計算していません。[結果](results/anomaly-multiseed-v0.3-engineering-consumer-entry-2026-09-25.md)。

次は契約案T01〜T12への対応と残件・容量時間予算を整理します。正式運用契約採択、source/runtime freeze、正式gate/holdout、S4/S6、Phase2/3全体は未完了です。

### 2026-09-25：consumer残件と容量・時間の見積りを更新

[T01〜T12の対応表](results/anomaly-multiseed-v0.3-consumer-coverage-budget-2026-09-25.md)を保存しました。engineering接続5群、旧検証再利用3群、計算部品まで1群、受入・外側状態・別reader/auditの接続残り3群です。新試験や720評価の再計算は行っていません。

正式2,880評価への単純外挿は約59.91GiB/活動178.17時間。240時間/96GiB＋空き32GiBを仮の予算枠として整理しましたが、正式推論/最終独立auditの予算は未確定で、設定へ適用していません。次は通常権限の別process readerと外側receipt（T11/T12）を接続します。正式契約採択・freeze・正式gate/holdout・S4/S6・Phase2/3全体は未完了です。

### 2026-09-25：保存結果を別processで確認し、外側に結果を記録

[engineering reader](anomaly-v03-consumer-reader.md)を実装し、13接続試験と実公開物の読取りが通過しました。元の保存点に対応する4payloadを別processで照合し、終了を確認。応答消失・不一致の記録は外側に保存し、元の結果と完了印を変更しません。[結果](results/anomaly-multiseed-v0.3-consumer-separate-reader-2026-09-25.md)。

T11/T12のengineering部分が接続できました。次は40-cluster入力・固定推論/full documentのadapterを架空入力で準備します。独立数値audit、正式契約採択、source/runtime freeze、正式gate/holdout、S4/S6、Phase2/3全体は未完了です。


### v0.3追記: 架空40clusterの推論・文書接続（2026-09-25）

[文書adapter](anomaly-v03-document-fixture.md)で40個の架空clusterから9表180gateを組み立て、正式文書の10項目へ対応づけました。12新規試験が通過し、候補差の信頼区間を手計算とも照合しています。[結果](results/anomaly-multiseed-v0.3-consumer-document-fixture-2026-09-25.md)。

不足するstatus・provenance・consumer source・正式bootstrap・slicesの5欄はnullの草稿です。実データや正式採択の結果ではありません。次は架空診断からslice行を接続します。正式契約、source/runtime freeze、正式gate/holdout、独立S6、Phase2/3全体は引き続き未完了です。


### v0.3追記: 架空診断の文書接続（2026-09-25）

[slice接続adapter](anomaly-v03-slice-fixture.md)で、異常検出率・信号利用可能率の本文1233行と、4系列の補助表2835行を配置しました。13新規試験が通過し、cluster単位と全体の件数・遅延、結合表と周辺表、試験内外の参照数を確認しています。[結果](results/anomaly-multiseed-v0.3-consumer-slice-fixture-2026-09-25.md)。

正式実行前の練習用データによる接続です。文書の残る4欄は実行状態・producer証拠・consumer source・正式bootstrapで、正式受入や実行の完了ではありません。次は最新consumerのsource/runtime固定対象と判断資料を整理します。Phase2/3全体は未完了です。
