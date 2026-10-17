# 正式R2：CARE fold0の学習移植（2026-10-17）

[固定条件](../research/rust-r2-formal-contract-2026-10-17.md)に沿って正式R2を1回だけ実行した。**全ケースが合格した。** 1更新・8更新・成熟state import・floorのtieの全比較がR0.1の許容差内（parameterはR0.2の規則）で、保存再開はbytes一致した。許容差・fixture・参照は実行後に変えていない。

## 実行

- commit 7efe839（clean tree）から[`tools/r2_formal.py`](../../tools/r2_formal.py)を1回起動した。Rust側は[`r2_formal`例](../../crates/banto-ai/examples/r2_formal.rs)。
- 環境：x86_64 Linux、Rust 1.95.0、Burn 0.22 Flex CPU、Torch 2.14.1+cpu、1 thread。
- 本実行の前に、実行ツールをFableがレビューした。誤って合格になる問題はなかった。指摘（親processの資源記録、失敗要素の全件記録、参照固定前のbuild、失敗時の記録と再実行の照合、4更新後checkpointの照合など）はすべて直した。
- 実行したbinaryは、同じcrateのsourceから実行の前にbuild済みだった（7efe839で変えたのは実行ツールのPythonだけ）。そのため実行時のbuildは何もせずに終わった（記録0.4秒）。binaryのhashは記録してあり、作り直しても同じhashになることをレビューで確認した。
- 人工入力モード（`--synthetic`）で、全体の流れ、失敗の記録、再実行時の照合、比較の検出力（値を変えると不合格になること）を確認した。この確認では実データを使っていない。
- 入力：固定7件のhashとR0.1の5参照が一致した。step 0・4095のbatchはMacのbatch参照とbytes一致した。学習recipeは固定した学習契約と一致した。
- Torch参照はfloat64確認（全ケースのloss・勾配・norm・係数）を通過してから固定した（閉包hash `551306ed…`）。Rustの実行はその後に行った。

## 結果

| 判定 | 結果 |
| --- | --- |
| loss（全11回） | 超過0。許容差比 最大0.015（floorのtie。更新を伴う10回では最大0.0094） |
| clip前・clip後の勾配（全59 tensor、全11回） | 超過0。要素の許容差比 最大0.0011、全体の相対L2 最大7.6e−7（上限2e−4） |
| global norm・clip係数 | 超過0。許容差比 最大0.002。normは0.31〜0.98で、係数はすべて1 |
| parameter（10回の更新後） | 超過0。許容差比 最大0.027 |
| 判定から外したparameter要素 | 1回目の後0.28%、8回目の後0.65%（停止条件10%）。key biasの4 tensor（各64要素）は勾配が理論上0のため常に外れる。残りは各層に散らばる少数 |
| 1次・2次moment（全要素、10回の更新後） | 超過0。許容差比 最大0.017 |
| 更新後のforward（記録のみ） | 最大差1.9e−6 |
| floorのtie（std＝floor） | loss・勾配とも超過0 |
| 保存再開 | 4更新後のcheckpoint（parameter・moment 177 tensor、step 4）が連続8更新の4回目とbytes一致した。別processで復元した5〜8回目の全記録・step 8も一致した |

成熟state import（step 4096のmomentで1更新）は、新しいoptimizerの1更新と同じparameter・batchで、parameterの許容差比が0.027から0.0063に下がった。成熟したmomentでは更新量が勾配の丸め差に左右されにくいことと合う。

資源：Rustの各processは0.4秒以下・ピーク43MB以下。Torch側の親processはbuildを除いて4.7秒・651MB（上限900秒・2GiB）。

## 範囲と次

- これで、R2の範囲（loss・backward・clip・AdamW、保存再開、成熟stateのimport）のCARE fold0上での移植が確認できた。
- R1は累積中間値の1点（Cloudでは3要素）が未達のままで、R0.2により診断として記録している。R1を合格とは扱わない。
- validation選択・校正・CARE testの評価・追加学習・別foldは行っていない。
- R0.2のとおり、これ以外の実データ学習は停止のまま。
- R3（有限の移植比較）とbanto接続は別の実行仕様を固定してから行う。並行して、保全の実用性評価の契約（必要な先行時間、許容する誤警報、event集計）を固定し、TimesFM・Chronos・Totoと比較する。

## 保存物

`artifacts/r2-formal-20261017/`（gitignore、公開しない）。
- 閉包記録 `e44f5e39…`
- summary.json `d722aa8a…`、comparisons.json `0d26f809…`、sources.json `c1d7f9ef…`
- fixture `4e58b614…`（inputs.jsonのhash）
- 実行したbinaryのhash `12de1e57…`
