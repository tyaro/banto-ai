# Mini Transformer

## 水準・相対変動とイベント別入力の別候補（2026-10-14）

[結果](../../docs/results/store-sales-small-model-inputs-2026-10-14.md)と[接続設計](../../docs/research/store-sales-small-model-input-pilot-design-2026-10-14.md)。tools/demand_input_features.pyでorigin-pastのみの2統計と暦12要素を組み立て、demand_data_inputs.py / demand_model_inputs.py / demand_train_inputs.pyへ接続。支持例不足はmetadataに保持。新7純粋入力＋3接続確認、一候補256stepは完了。旧sourceは変更せず、完成チェック/学習を反復しない。生データ・stateはlocalのみ。性能改善や実務採択とは別の経路確認で、今回は基準を置換しない。

## 需要用途の最新実装（2026-10-14）

[設計](../../docs/research/store-sales-small-model-design-2026-10-14.md)と[一回探索の結果](../../docs/results/store-sales-small-model-2026-10-14.md)。demand_data.py/demand_model.py/demand_train.pyは保存済み公開数量・mask・既知の暦から14日総量分位点と日次配分を出す。独立初期化110916parameter/一構成256step。新check_demand.pyの6機構確認と一回学習は完了、定期反復しない。学習開始は明示的な新outputを指定したdemand_train.py実行だけ。旧固定MetroPT実装は保持し、公式TimesFM重み・教師出力を使わない。今回は単純基準の置換根拠を得ていない。以下は先行工程の記録。

予測研究のための、小さく内部を検証しやすい多変量時系列 Transformer baseline です。

初期目標:

- aligned な多変量入力
- 明示的な operating-mode feature
- point forecast と quantile forecast
- 単純な training／ablation protocol
- 再現可能な CPU smoke test

この model は研究用 baseline であり、安全または制御コンポーネントではありません。

## 2026-10-13の設計

現在の初期仕様は [TimesFM構造を参考にした小型独自モデルの設計](../../docs/research/timesfm3-small-model-design-2026-10-13.md) を参照する。
3連続値target、context128/horizon32、幅64/2block、full対self-only系列attentionを独立初期化から比較する設計。公式学習・zero-shot性能の再現とはしない。最小実装と10件の構造確認は完了。学習・予測性能評価は未着手。

## optional実装

small_model.pyはCPU float32専用。check_model.pyはWindows current-process counterを使用する構造確認で、通常テストsuiteから独立。
確認環境CPython3.14.0/Torch2.14.0+cpu。requirements.txtはversion宣言でwheel hash全固定ではない。
新規未確認caseだけ、既存隔離Pythonからcheck_model.py --checks case名で実行する。完成10件を定期反復しない。
[原結果と次工程](../../docs/research/timesfm3-small-model-implementation-2026-10-13.md)。

## データ・trainer準備（2026-10-14）

data.pyは指定探索日だけをpin/時刻/quality/splitへ照合する。train.pyの実行は実データ学習を開始するため、一回の新output rootでだけ使用する。未更新の初期state、共通128×8 batch列、step別checkpoint/prefix、選択後testを保存する。
[9新確認・元失敗・資源・次の一回](../../docs/research/timesfm3-small-model-preparation-2026-10-14.md)。閉鎖outputへ再実行・追記しない。

## 一回探索完了（2026-10-14）

[研究結果](../../docs/research/timesfm3-small-model-pilot-2026-10-14.md)。両構成128step、validation選択後test各一度まで完了。単日探索でTimesFM3再現・同等性能・用途適合とはしない。閉鎖outputへ再実行しない。次の実用性研究の用途定義待ちで自走停止。
