# R2P工程4: SmallForecaster全体の人工学習接続

2026-10-17 JST。[固定条件](../research/rust-r2p-full-model-contract-2026-10-17.md)に沿い、SmallForecaster全体を学習graphへ接続し、lossと全59 parameter tensor（109,024値）の勾配を[Torch参照](../../crates/banto-ai/tests/fixtures/r2p-full/summary.json)とR0.1の許容差（変更なし）で照合した。

## 実装

- `SmallForecaster::forward`：推論と学習で共有するforward。context[B,3,128]から正規化・元単位の分位点とcontext center/scaleをtensorのまま返す。`predict`もこれを経由する。切り出しの前後で、固定の人工stateに対する推論の全trace（23件）と出力のbytesが一致することを確かめた。
- `SmallForecaster::from_named`：名前付きtensor（学習ではautodiff leaf）からmodelを作る。名前の集合と長さが`expected_shapes()`と違えば拒否する。
- `training::loss_and_gradients`：更新なしでlossと名前付き勾配を求める部分を`train_step`から切り出した。lossと勾配の非有限値、勾配の欠落はエラー。

## 検証（`tests/r2p_full_model.rs`、CIで毎回実行）

| 項目 | 結果 |
| --- | --- |
| 初期parameter：fixtureの式からRustで独立に実装し、参照の59個のSHA256と照合 | 全件一致、全値がfloat32で正確 |
| batch Aの正規化分位点・context center/scale | R0.1内 |
| batch Aのloss | R0.1内 |
| 全59 tensorの勾配（tensorごとの要素、全体の相対L2） | R0.1内 |
| global norm・clip係数・clip後の勾配（係数は1） | R0.1内 |
| batch B（初期parameter、更新なし）の正規化分位点・center/scale・loss | R0.1内 |
| 名前が欠けたtensor集合 | `from_named`が拒否 |

試験が誤りを検出できるか意図的な改変で確かめた。attentionの尺度を4.001にする、LayerNormのepsを変えるとforwardの照合で、1つのparameterをleafにしないと「勾配の欠落」で、pinballの|r|項をdetachして値を変えず勾配だけを変えると勾配の照合で、それぞれ失敗した。

## 変えていないもの・次工程

R0.1許容差、固定fixture、R1の残1点未達、正式R2実データ学習の停止。R2P（工程2〜4）の通過をR1や正式R2の合格へ読み替えない。全モデル1更新の比較はR0.1では成り立たないことが固定時に分かっており（固定条件の記録を参照）、正式R2へ進む前に比較方法を人が決め直す必要がある。
