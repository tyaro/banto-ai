# Mini Transformer

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
3連続値target、context128/horizon32、幅64/2block、full対self-only系列attentionを独立初期化から比較する設計。公式学習・zero-shot性能の再現とはしない。実装・学習はまだ未着手。
