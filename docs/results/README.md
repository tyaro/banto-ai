# 実測・監査・実行報告

[文書の入口](../README.md) · [最新の引継ぎ](../current-handoff.md)

各報告は実施時点の記録です。数値、失敗、実行範囲、原artifactのidentityはその報告の条件に従って読みます。現在状態は引継ぎを参照してください。

## Rustクレートの移植

- [研究ブランチの整理とmain取り込み](research-consolidation-2026-10-17.md) — 停止済みsourceの保存、lock整合、現在の確認結果。

- [R2P lock最小整合案と人工Python参照](rust-r2p-lock-and-python-reference-2026-10-16.md) — 隔離案通過、107照合pass、元lock未適用/Rust学習未実行。

- [Rust R2P棚卸しと仕様固定](rust-r2p-inventory-and-specification-2026-10-16.md) — readonly依存確認と人工条件、学習は未実行。

- [実用性とRust学習への計画改訂結果](banto-ai-rust-practical-training-replan-2026-10-16.md) — 保存成果だけを整理、許容差不変・学習未実行。












- [Rust R1全55箇所・7ケースの局所/累積差診断](banto-ai-rust-r1-all-layer-audit-2026-10-16.md) — 局所超過0、上流累積1点未達、モデル変更0。




- Rust R1のビルド容量上限停止 — Xcode確認通過。R1 CPU buildがcache+target合計768MiB上限で停止、テスト/数値比較未確認。


## 産業設備の保全と点検支援

- [CARE保存予測の未検知分析とRust R0（2026-10-16）](care-saved-diagnostics-rust-r0-2026-10-16.md) — 元結果固定、未検知8+1の内訳とbanto-industrial接続契約。

- [CARE5fold実学習とイベント評価（2026-10-16）](care-macos-learning-evaluation-2026-10-16.md) — 固定比較4条件通過、検知3/12・未検知9件とnative可用性差を保存。
- [CARE train尺度とbaseline profile・全学習schedule固定（2026-10-16）](care-training-preparation-2026-10-16.md) — 5fold支持pass、全抽出列独立照合。
- [CARE数値入力と実consumerの支持確認（2026-10-16）](care-numeric-consumer-2026-10-16.md) — 固定22file/3信号とquality mask、全支持床pass。

## 独自モデルの需要用途

- [店舗分離による終了点選択・一軌跡比較（2026-10-14）](demand-group-selection-2026-10-14.md)
- [保存済み予測の補正誤差分解（2026-10-14）](demand-correction-decomposition-2026-10-14.md)
- [内部選択済み模型の未学習店舗評価・基準未達（2026-10-14）](demand-selected-series-evaluation-2026-10-14.md)
- [学習量の時系列分離診断・256以降改善（2026-10-14）](demand-training-adequacy-2026-10-14.md)
- [統計8入力の2016時間順検証・9of15/停止（2026-10-14）](demand-statistical-feature-validation-2026-10-14.md)
- [統計8入力あり/なしの同条件学習比較（2026-10-14）](demand-statistical-feature-pair-2026-10-14.md)
- [σ/EMAの追加学習入力・6確認（2026-10-14）](demand-statistical-features-2026-10-14.md)
- [σ/EMA/等重み併用・条件未達（2026-10-14）](demand-statistical-overlay-2026-10-14.md)
- [当日/前後の小型模型比較・自走停止（2026-10-14）](demand-calendar-model-pair-2026-10-14.md)
- [名目暦60の入力確認・fit支持（2026-10-14）](demand-public-calendar-input-2026-10-14.md)
- [営業日水準と確定休業0・新6確認（2026-10-14）](demand-operating-sales-2026-10-14.md)
- [休暇区間と営業予定の分離・新6確認（2026-10-14）](demand-event-interval-input-2026-10-14.md)
- [営業状態と休日の前後入力・新6確認（2026-10-14）](demand-holiday-event-input-2026-10-14.md)
- [8週補正の保存誤差分解・入力支持監査（2026-10-14）](store-sales-weekly-correction-diagnosis-2026-10-14.md)
- [数量支持15店の8週回帰・全18店評価（2026-10-14）](store-sales-weekly-ridge-cohort-2026-10-14.md)
- [8週共有回帰の学習前支持・停止（2026-10-14）](store-sales-weekly-ridge-readiness-2026-10-14.md)
- [8週間の自己履歴入力と新5確認（2026-10-14）](store-sales-weekly-history-input-2026-10-14.md)
- [完了した過去誤差による時点別総量区間（2026-10-14）](store-sales-sequential-interval-2026-10-14.md)
- [自身の過去総量区間・期間診断（2026-10-14）](store-sales-own-history-interval-2026-10-14.md)
- [共有総量区間と一尺度案の結果・失敗保全（2026-10-14）](store-sales-shared-interval-results-2026-10-14.md)
- [新6店舗への共有数量残差の一回検証（2026-10-14）](store-sales-shared-residual-2026-10-14.md)
- [共有学習の店舗選定・数量支持（2026-10-14）](store-sales-shared-series-support-2026-10-14.md)
- [過去販促の支持・残差記述と一回2016検証（2026-10-14）](store-sales-past-promotion-2026-10-14.md)
- [独立mean出力の実装・一回評価（2026-10-14）](store-sales-mean-pilot-2026-10-14.md)
- [平均・中央値・意思決定分位点と学習目的の整理（2026-10-14）](store-sales-quantity-objectives-2026-10-14.md)
- [水準・相対変動とイベント別入力の確認・一回接続（2026-10-14）](store-sales-small-model-inputs-2026-10-14.md)
- [学習支持例・連続ゼロ・入力情報の診断（2026-10-14）](store-sales-training-diagnosis-2026-10-14.md)
- [小型モデルの需要設計・一回探索（2026-10-14）](store-sales-small-model-2026-10-14.md)

## 検証記録の保存改善

- [検証記録の容量・自動分割・失敗保存の改善（2026-10-12）](verification-recording-policy-2026-10-12.md)

## モデル・baseline評価（14件）

- [Chronos-2 初期評価結果（2026-09-04）](chronos2-initial-evaluation-2026-09-04.md)
- [Chronos-2 8条件matrix初期評価](chronos2-matrix-2026-09-04.md)
- [Chronos-2 MetroPT-3公開実データ評価結果（2026-09-04）](chronos2-metropt3-evaluation-2026-09-04.md)
- [MetroPT-3 統計baseline評価結果（2026-09-04）](metropt3-baseline-evaluation-2026-09-04.md)
- [MetroPT-3 取込・品質ゲート結果（2026-09-04）](metropt3-import-2026-09-04.md)
- [TimesFM 3.0／統計baseline比較結果](timesfm3-baselines-comparison-2026-09-04.md)
- [TimesFM 3 CPU smoke結果（2026-09-04）](timesfm3-cpu-smoke-2026-09-04.md)
- [TimesFM 3.0 小規模matrix実測結果](timesfm3-matrix-2026-09-04.md)
- [TimesFM 3.0 MetroPT-3公開実データ評価結果（2026-09-04）](timesfm3-metropt3-evaluation-2026-09-04.md)
- [TimesFM 3 rolling-origin benchmark 実測結果（2026-09-04）](timesfm3-rolling-benchmark-2026-09-04.md)
- [Toto 2.0 4M controlled evaluation 実測報告](toto2-controlled-evaluation-2026-09-05.md)
- [Toto 2.0 4M event slice post-hoc解析](toto2-event-slices-2026-09-04.md)
- [Toto 2.0 4M 小規模matrix実測結果](toto2-matrix-2026-09-04.md)
- [Toto 2.0 4M MetroPT-3公開実データ評価結果（2026-09-04）](toto2-metropt3-evaluation-2026-09-04.md)
