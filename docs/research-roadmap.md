# 研究ロードマップ

## 最終的な目標

産業 AI が、予測・異常検知・試運転支援に有効であることを、再現可能な根拠として示します。同時に、可観測で、元に戻せて、安全重要な制御から分離されていることを満たします。

本書は研究テーマの長期的な順序を示します。候補モデルの比較は [`time-series-model-survey.md`](time-series-model-survey.md)、直近の作業、期間目安、暫定合格基準は [`research-implementation-plan.md`](research-implementation-plan.md) を参照してください。

## フェーズ

| Phase | 焦点 | 完了時の根拠 |
| --- | --- | --- |
| 0 | 研究基盤と契約 | Python環境、データ方針、experiment／license manifest、共通interface、連携境界 |
| 1 | 合成データとbaseline | 運転状態、fault、欠損、labelを持つgeneratorと、naive／古典baselineの再現性 |
| 2 | Forecast model benchmark | Chronos-2、TimesFM 3.0、Toto、Granite TTM、自前／学習型baselineの同条件比較 |
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

Phase 2の基盤として、chronological rolling-origin runnerへmodel registry注入境界、equipment／model単位のinstance再利用、origin単位のmulti-target request、past-only／known-future covariate境界、model別quantile policy、共通origin選択とprovenance記録を追加しました。結果にはmodel別metrics、model別latency、OS process peakの測定源も記録します。TimesFM 3専用entrypointは、既存のlicense manifest、固定checkpoint revision、artifact hash、専用外部cache、offline環境を検証してから実行します。実行用sampleは[`examples/configs/benchmark-timesfm3-small.json`](../examples/configs/benchmark-timesfm3-small.json)です。

2026-09-04に、LastValueとの小規模なTimesFM 3 rolling-origin実測を追加しました。`synthetic-motor-small`、seed 42、2 equipment、各2 validation／test origin、context 12、horizon 3の限定条件では、TimesFM 3がMAE、RMSE、MASE、WISでLastValueを上回りました。これはAとdegCの異なる単位を持つ2 targetを同数point-weightで混合した固定構成のcomposite値による結果です。一方、native p10-p90 coverageは70.833%でnominal 80%未達、interval widthはbaselineの4.519074倍でした。詳細は[`docs/results/timesfm3-rolling-benchmark-2026-09-04.md`](results/timesfm3-rolling-benchmark-2026-09-04.md)に記録しています。

この時点でTimesFM 3の広範な精度比較や採否は判断していません。実測は単一generator、少数origin、短いcontext／horizon、LastValueのみの比較です。統計baseline全種、複数origin／horizon／context／seed、target別・equipment-target別集計、欠損・fault・regime別、公開データ、native quantile calibration、他候補との同条件比較が残っています。重みのlicenseはresearch-only／non-commercialのままであり、製品・顧客PoC・PLC／Banto Hub write経路へ昇格させません。

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
