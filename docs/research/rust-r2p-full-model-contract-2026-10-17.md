# R2P工程4: SmallForecaster全体の人工学習接続の固定条件

2026-10-17 JST。[復帰計画](banto-ai-practical-training-return-plan-2026-10-16.md)の工程4（全モデルの人工接続）を、Rust実装の前に固定する。工程2・3（[学習部品](../results/rust-r2p-training-parts-2026-10-17.md)、[保存再開](../results/rust-r2p-resume-2026-10-17.md)）は通過済み。機械可読の条件は[fixture](../../examples/configs/rust-r2p-full-model-fixtures-20261017.json)を正とする。

## 目的と範囲

SmallForecaster全体（C128/H32/V3/D64/L2、full series attention）を学習graphへ接続し、固定した人工の状態・入力・正解で、lossと全59 parameter tensor（109,024値）の勾配がTorchと原許容差で一致することを確かめる。実データ、CAREの重み・label、正式R2、R1の合格判定は含まない。R1の残1点未達は残る。

## 固定した入力

- 初期parameter：名前と要素番号だけで決まる式（整数÷2のべき乗）。乱数を使わず、PythonとRustでbit単位で同じ値になる。Rustは式から作り、参照に保存したtensorごとのSHA256と照合する。
- buffer：scale_floor=[0.5, 0.25, 0.125]、time_maskは下三角、series_maskは全true（variate attentionにmaskなし）。positionはsmall_model.pyのfloat32 sin/cos表を参照に保存し、Rustはそれを読む（入力であり、比較対象の出力ではない）。
- batch A・B：context[2,3,128]、正解[2,3,32]。channel 2は標準偏差1/32でscale_floorが効く。

## 比較

| 対象 | 許容差（R0.1、変更なし） |
| --- | --- |
| batch A・Bの正規化分位点[2,3,32,3]、context center/scale | normalized_activation |
| batch A・Bのloss（正規化label、B×C×H×3平均のpinball） | normalized_loss |
| clip前後の勾配（tensorごと） | gradient の要素ごとatol/rtol |
| clip前後の勾配（59 tensor全体） | gradient の global相対L2（参照0なら候補L2の規則） |
| global norm・clip係数 | gradient |

この固定入力では勾配のglobal normが約0.958で1未満のため、clip係数はちょうど1になり、clip後の勾配はclip前と同じになる。全モデルでの比較はnormの値と「max_norm未満では勾配を変えない」ことの確認で、norm>max_normで縮める分岐は工程2（C2・C3・O3）で検証済み。

勾配の相対L2は、R0.1の定義どおり全勾配をまとめて評価する。attentionのkey biasは、softmaxが全keyへの共通shiftに不変なため勾配が理論上0になり、tensor単位の相対L2は丸め誤差同士の比になって意味を持たない。

## 固定前に除外したもの

当初は1回のAdamW更新後のparameter・momentとbatch Bのforwardも比較する案だったが、参照生成時のfloat64独立検算で除外した。AdamWはsqrt(v)+epsで割るため、|勾配|がeps程度以下の要素では更新量が丸め誤差に左右される。[確認スクリプト](../../tools/r2p_full_model_adamw_probe.py)で再現でき、parameter・moment 177 tensorのうち5件がfloat32とfloat64で1更新の許容差を超え、最大差は1.1e−5（atol 1e−6）。大きいのは|勾配|がeps程度の要素（blocks.1.temporal.v.weight、1.05e−8対1.22e−8）と、float64の勾配がpinballのtieでちょうど0になるhead.biasの要素（float32では2.3e−10）。上のkey biasは勾配が理論上0で、差は2e−6以下。いずれも実装の誤りではなく、全モデル1更新の比較がこの許容差では数値的に成り立たないことを示す。復帰計画は工程4をlossと全parameter勾配の確認と定めており、AdamW自体は工程2・3で検証済みのため、比較をforward・loss・勾配・clipに限った。

この性質は、計画上の正式R2（CARE fold0の1更新・8更新をR0.1で比較）にも同じく当てはまる見込みが高い。正式R2へ進む前に、比較方法（例：更新量の比較を勾配が十分大きい要素に限る、別の基準を定める）を人の判断で決め直す必要がある。本工程ではR0.1を変更しない。

## 参照と停止条件

[生成器](../../tools/r2p_full_model_reference.py)はfloat32のTorch結果を同じ手順のfloat64計算と上表の許容差で照合し、全130件が通った場合だけ`crates/banto-ai/tests/fixtures/r2p-full/`へ保存する（Linux x86_64、Python 3.14.6、torch 2.14.1+cpu）。Rust実装は次の工程で行い、推論と同じforwardのcode pathをtensorのままlossへ渡す。hostで計算した参照値をgraphへ注入しない。不一致は記録して止め、fixture・許容差を結果に合わせて変えない。
