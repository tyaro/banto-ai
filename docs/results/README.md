# 実測・監査・実行報告

[文書の入口](../README.md) · [最新の引継ぎ](../current-handoff.md)

各報告は実施時点の記録です。数値、失敗、実行範囲、原artifactのidentityはその報告の条件に従って読みます。現在状態は引継ぎを参照してください。

## Rustクレートの移植

- [CARE Farm B・Cの1回限りholdout：結果（2026-10-18）](care-holdout-bc-2026-10-18.md) — 不合格。自作モデルの検知は72時間76%・24時間76%で基準を満たしたが、誤警報がasset・30日あたり9.45件（上限1.0）で、31 assetのうち7 assetしか上限内に入らなかった。
- [CARE保全の実用性評価：自作モデルと基盤モデル3種の比較（2026-10-18）](care-maintenance-practical-2026-10-18.md) — 基盤モデルは1step予測が正確だが、同じ残差警報では12件中0〜1件しか検知せず誤警報も少ない。自作モデルは3件（24時間前は2件）。開発材料での評価で合否なし。
- [正式R2：CARE fold0の学習移植（2026-10-17）](rust-r2-formal-2026-10-17.md) — 1回だけ実行し全ケース合格。1更新・8更新・成熟state import・floorのtieがR0.1/R0.2内、保存再開はbytes一致。
- [正式R2の入口確認（2026-10-17）](rust-r2-entry-check-2026-10-17.md) — Cloud環境でR1最終出力・同一入力局所比較385件ともに超過0、数値以外の条件も確認。中間値は3要素超過（診断）。
- [R2P工程4: SmallForecaster全体の人工学習接続（2026-10-17）](rust-r2p-full-model-2026-10-17.md)
- [R2P工程3: 人工学習の連続8更新と保存再開（2026-10-17）](rust-r2p-resume-2026-10-17.md)
- [R2P工程2: Rustの学習部品（2026-10-17）](rust-r2p-training-parts-2026-10-17.md)
- [R2P: Cloud環境でのTorch参照の再生成（2026-10-17）](rust-r2p-cloud-reference-2026-10-17.md)
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

- [rawP厳密ゼロ境界と両側：人工接続検証](demand-zero-boundary-artificial-2026-10-16.md)
- [自Qの重み付き制約solver：人工検証完了](demand-weighted-solver-artificial-2026-10-16.md)
- [丸め差付き比例配分・floor到達の人工接続検証](demand-roundfloor-pipeline-artificial-2026-10-16.md)
- [rank3・週係数非ゼロ解のrawP厳密ゼロ境界と両側](demand-rank3-zero-boundary-artificial-2026-10-16.md)
- [rank3・週変化係数非ゼロの人工pipeline検証](demand-rank3-pipeline-artificial-2026-10-16.md)
- [非ゼロ人工prefixから日次予測までの接続検証](demand-nonzero-pipeline-artificial-2026-10-16.md)
- [制約が非ゼロ解を変える人工pipeline検証](demand-active-pipeline-artificial-2026-10-16.md)
- [実学習prefixの接続条件固定・時点来歴metadata監査](demand-weighted-prefix-preflight-2026-10-15.md)
- [実2013数量prefixのpin・完全性・問題生成とβ0確認](demand-weighted-numeric-prefix-2026-10-15.md)
- [非ゼロ係数から日次予測への接続：人工検証完了](demand-weighted-daily-bridge-2026-10-15.md)
- [学習consumerの問題生成・β0 baseline再現：人工検証完了](demand-weighted-consumer-artificial-2026-10-15.md)
- [Q4集中・自店学習信号0の分析と、学習開始条件](demand-weight-learning-entry-2026-10-15.md)
- [Astraレビューに基づく総量保存・四季別日次配分の評価](demand-total-preserving-2026-10-15.md)
- [総量過小非増加を課した元日前後数量の検証](demand-shortfall-quantity-2026-10-15.md)
- [四季平均の両側制約付き総量補正・改善支持なし](demand-seasonal-risk-2026-10-15.md)
- [休業ゼロ・営業中の販売ゼロ・欠測の分離と固定2015評価](demand-sales-state-2026-10-15.md)
- [過去からの休業相当推定・観測評価と欠測0仮定の評価](demand-recurring-closure-2026-10-15.md)
- [順序付き重みの数値仕様固定・人工統合確認](demand-ordered-weight-numeric-2026-10-15.md)
- [固定重みの発行前入力接続・集中とrankの監査](demand-ordered-weight-input-audit-2026-10-15.md)
- [店舗特性×短期持続性：順序付き重みの第一案を保存](demand-ordered-persistence-design-2026-10-15.md)
- [Macでの需要入力・profile・模型の新規生成](demand-macos-rebuild-2026-10-15.md)
- [入力・ラベル分離と仮定に基づく時点契約の検証完了](demand-input-boundary-2026-10-15.md)
- [既存10店の2015年評価 — 小幅改善、暫定条件未達](demand-existing-stores-2015-2026-10-15.md)
- [保存260予測の2014採点完了：年間は改善、Q1条件違反で不適格](demand-bounded-scoring-2014-2026-10-15.md)
- [店舗分離による終了点選択・一軌跡比較（2026-10-14）](demand-group-selection-2026-10-14.md)
- [学習量の時系列分離診断・256以降改善（2026-10-14）](demand-training-adequacy-2026-10-14.md)
- [統計8入力あり/なしの同条件学習比較（2026-10-14）](demand-statistical-feature-pair-2026-10-14.md)
- [σ/EMAの追加学習入力・6確認（2026-10-14）](demand-statistical-features-2026-10-14.md)
- [σ/EMA/等重み併用・条件未達（2026-10-14）](demand-statistical-overlay-2026-10-14.md)
- [当日/前後の小型模型比較・自走停止（2026-10-14）](demand-calendar-model-pair-2026-10-14.md)
- [名目暦60の入力確認・fit支持（2026-10-14）](demand-public-calendar-input-2026-10-14.md)
- [休暇区間と営業予定の分離・新6確認（2026-10-14）](demand-event-interval-input-2026-10-14.md)
- [営業状態と休日の前後入力・新6確認（2026-10-14）](demand-holiday-event-input-2026-10-14.md)
- [8週間の自己履歴入力と新5確認（2026-10-14）](store-sales-weekly-history-input-2026-10-14.md)
- [独立mean出力の実装・一回評価（2026-10-14）](store-sales-mean-pilot-2026-10-14.md)
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
