# 研究ロードマップ

## 最終的な目標

産業 AI が、予測・異常検知・試運転支援に有効であることを、再現可能な根拠として示します。同時に、可観測で、元に戻せて、安全重要な制御から分離されていることを満たします。

本書は研究テーマの長期的な順序を示します。候補モデルの比較は [`time-series-model-survey.md`](time-series-model-survey.md)、直近の作業、期間目安、暫定合格基準は [`research-implementation-plan.md`](research-implementation-plan.md) を参照してください。

## フェーズ

| Phase | 焦点 | 完了時の根拠 |
| --- | --- | --- |
| 0 | 研究基盤と契約 | Python環境、データ方針、experiment／license manifest、共通interface、連携境界 |
| 1 | 合成データとbaseline | 運転状態、fault、欠損、labelを持つgeneratorと、naive／古典baselineの再現性 |
| 2 | Forecast model benchmark | TimesFM 3.0の評価済み結果を基準に、Chronos-2を商用候補として追加し、Toto、Granite TTM、自前／学習型baselineを同条件比較 |
| 3 | 異常とドリフト | 統計方式、forecast residual、TSPulse、Riverのevent単位比較 |
| 4 | 自前モデル研究 | 点予測・分位点予測を備えた小型multivariate Transformerとablation |
| 5 | Commissioning auto-tuning | レシピ駆動のprofile candidate、shadow評価、人手承認gate |
| 6 | Continual adaptation | 本番mode固定、rollback、汚染testを含むfrozen model + profile適応 |
| 7 | Banto Hub pilot境界 | read-only export／sidecarの試作と、制御を変更しないend-to-end demo |

## 推奨する優先順

1. package、dataset／run／license manifest、共通interfaceを確立する。
2. motor・conveyorに近い合成信号とnaive／統計baselineを作る。
3. Chronos-2、TimesFM 3.0、Toto 2.0 4m／22m、Granite TTMを同じrunnerで測定する。
4. 統計anomaly、forecast residual、TSPulseをevent単位で比較する。
5. benchmarkが安定してからmini-Transformerと対象データ学習型modelを実装する。
6. commissioning校正をofflineとshadow modeで検証する。
7. frozen base modelとversioned profileによる安全な適応を検証する。
8. 承認済み結果を利用できる最小限のBanto Hub read-only adapterを定義する。

## 2026-09-04時点の進捗

Phase 2の基盤として、chronological rolling-origin runnerへmodel registry注入境界、equipment／model単位のinstance再利用、origin単位のmulti-target request、past-only／known-future covariate境界、model別quantile policy、共通origin選択とprovenance記録を追加しました。result schema `0.2`にはmodel-target別およびmodel-equipment-target別metricsを追加し、unit一致を検証してから設備横断集約します。結果にはmodel別metrics、model別latency、OS process peakの測定源も記録します。TimesFM 3専用entrypointは、既存のlicense manifest、固定checkpoint revision、artifact hash、専用外部cache、offline環境を検証してから実行します。実行用sampleは[`examples/configs/benchmark-timesfm3-small.json`](../examples/configs/benchmark-timesfm3-small.json)です。

2026-09-04に、LastValueとの小規模なTimesFM 3 rolling-origin実測と、統計baselineを含むtarget別比較を追加しました。`synthetic-motor-small`、seed 42、2 equipment、各2 validation／test origin、context 12、horizon 3の限定条件です。target別比較の詳細は[`docs/results/timesfm3-baselines-comparison-2026-09-04.md`](results/timesfm3-baselines-comparison-2026-09-04.md)、旧composite結果の経緯は[`docs/results/timesfm3-rolling-benchmark-2026-09-04.md`](results/timesfm3-rolling-benchmark-2026-09-04.md)に記録しています。past-onlyではTimesFM 3が温度MAEで最良でしたが、電流ではmoving-average等に劣りました。known-loadは計画値をorigin時点で取得できるsynthetic oracle-styleの別scenarioであり、実績先読みや本番効果を示しません。

次の評価範囲拡大に向け、seedをgeneratorへ反映してdatasetを再生成し、horizon／context lengthとのmatrixを安全に反復する基盤を追加しました。datasetはseedごとに一度生成・品質確認し、観測file hashでseed差の実体を確認します。base config raw bytesと開始code revisionを固定し、cell／publish時の不変性も検証します。主集計は単位別のseed間cell-macro summaryです。

この基盤で2 seeds×2 horizons×2 context lengthsの実TimesFM matrixを完走し、8 cells success／0 failureを[`docs/results/timesfm3-matrix-2026-09-04.md`](results/timesfm3-matrix-2026-09-04.md)へ記録しました。TimesFM 3は温度の4条件でMAE最良、電流では4条件とも6モデル中4位でした。ただし2 seeds、少数origin、単一generatorの結果で、coverage／WISも暫定です。seedを最低5以上、origin／条件追加、欠損・fault・regime別、モデル単独resource測定、他候補との同一契約比較、実設備でのplanned-load契約検証が残っています。重みはresearch-only／non-commercialであり、製品・顧客PoC・PLC／Banto Hub write経路へ昇格させず、Phase 2も未完了です。

TimesFM 3.0の限定matrix評価後、Chronos-2へ比較軸を移しました。`chronos-forecasting==2.3.1`、固定checkpoint revision／実計算SHA-256、repository外cache、offline読み込み、native quantile（pointはp50）を契約として、公式API direct CPU smokeとBanto adapter／tool smokeを完了しました。さらに、60 samples×2 equipment、context 12、horizon 3、各equipment validation／test各2 originsの初期rolling benchmarkを完走しました。

past-only 6 modelsではChronos-2のaggregate MAEは`0.20672198138554906`、WISは`0.1952207659517925`でした。origin時点で確定済みの計画値を模したknown-future 7 modelsでは、MAE `0.1691488806622826`、WIS `0.15937026919725228`で1位となり、past-onlyから改善しました。ただし電流MAEはmoving-average、温度MAEはHolt linearが優位で、aggregateはAとdegCを混合する比較値です。小標本・単一seed・合成データで、runはdirty worktreeを記録しているため、製品性能や一般性能を示しません。詳細は[`docs/results/chronos2-initial-evaluation-2026-09-04.md`](results/chronos2-initial-evaluation-2026-09-04.md)に記録しています。

次はChronos-2のseed×horizon×context matrix、origin拡大、missing／stale／regime／fault slice、clean savepoint再実行、model単独resource測定です。package・code・weightsはApache-2.0ですが、追加gateが完了するまで`commercial-evaluation`に留め、`product-candidate`へ昇格しません。TimesFM 3.0は重み条件によりresearch-onlyの比較基準として残します。

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
