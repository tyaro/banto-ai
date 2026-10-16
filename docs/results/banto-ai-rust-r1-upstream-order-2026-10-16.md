# Rust R1 — 正規化・attentionの同一入力診断と7ケース再確認（2026-10-16）

[計画](../research/banto-ai-rust-implementation-plan-2026-10-16.md)に沿って実施。**attentionは同一入力の全28段階で固定許容差内。LayerNormに参照との一般的な演算順の相違を確認し、事前条件を通った修正を一度適用した。元の超過点は通過したが、別の中間値1点が超過し、R1全体は未合格のまま**。最終予測は全7ケースで通過。許容差を変えず、追加算術探索やR2学習へ進まない。

## 入力と演算を分離した診断

保存済みtrain-firstのPython/Rust双方の第2blockから、norm0/1/2の入力各120×64を再構成した。norm1はblock0＋temporal、norm2はさらにvariateを足す。attentionへは保存済みの正規化後入力を直接渡し、正規化差をattention単体の差と混同しない。固定weight/eps/causal mask/full-series maskを使用。

Python native LayerNorm6回とattention4moduleを診断用に実行。Python側の保存stageを全てbytes再現し、Rust側も従来の正規化・attention出力を全てbytes再現した。新しい全model forward/学習/target decodeは診断時0。以後の確認でだけ元の7ケースをRustで一度実行した。

| 同一入力の診断 | 結果 |
| --- | --- |
| norm6組/46,080要素、従来の除算 | 全て許容差内 |
| norm6組/46,080要素、逆標準偏差の乗算 | 全て許容差内 |
| attention4組×7段階 | 28/28通過、超過0 |
| attention段階 | q/k/v、masked logits、softmax、mixed、出力 |
| 時間maskの−∞ | 同じ位置で厳密一致 |

attentionでは重み射影・softmax等のfloat32差は残るが、同一入力での条件は通過した。attentionの式・backend・実装は変更していない。局所比較passを全モデル一致と読み替えない。

## 一般的な修正の根拠と固定条件

[PyTorch v2.14 CPU LayerNorm](https://github.com/pytorch/pytorch/blob/v2.14.0/aten/src/ATen/native/cpu/layer_norm_kernel.cpp)は行ごとに `1/sqrt(var+eps)` を計算し、中心化した値へ掛ける。Rustは中心化値をsqrtで要素ごとに割っていた。数学的には同値でもfloat32の丸め順序が異なる。参照sourceと同一入力診断を根拠に、候補を**逆数乗算の一つだけ**に固定した。

候補の採用条件は実行前phase.jsonに保存した「全6入力で元の中間値許容差内、かつ全6入力合計の参照との二乗誤差が減る」。失敗indexの値では選ばない。従来SSE 2.2910479491599104e-10、候補SSE 1.769485064963066e-10で、合計22.765%減り条件を通過した。一部入力では最大誤差が増えており、全要素が改善するという意味ではない。

修正前に別declarationへsource/理由/再確認条件/停止条件を保存。coreの全LayerNorm（final_normを含む）で `centered / sqrt` を `centered * reciprocal(sqrt)` へ変更した。balanced float32 mean/variance、eps、weight、モデル構成、context正規化、attention、R0の許容差は不変。参照値の置換、特定店/発行日/indexだけの処理、float64モデル化は行わない。

## 3テストと固定7ケース

Rustの入力0/欠測・shape、因果query、neutral破損拒否の3テストは全pass。診断exampleを含むall-targetsもbuildされた。保存済みPython参照を再生成せず、train先頭/末尾batch＋zero/constant/floor下/境界/上の7ケースを一度比較した。

| 項目 | 結果 |
| --- | --- |
| case / named tensor | 7 / 161 |
| 比較要素 | 389,214 |
| 超過 | **1**（新しい点） |
| 元単位の最終分位点 | 全6,048要素pass |
| 正規化後の最終分位点 | 全6,048要素pass |
| 元単位最大error/limit | 0.011307481 |
| 正規化後最大error/limit | 0.704768984 |
| finite / 分位点順序 | 全case成立 |
| R1全体 | **fail** |

元のtrain-first/block1 index4359は条件内になった。新たにtrain-last/block1 index3450＝[batch3,series1,token3,dim58]（0始まり）が超過。両点の修正前後はpoint-before-after.jsonへ保存し、元の1点だけを再確認して合格としなかった。

| 点 | 修正前絶対差 | 修正後絶対差 | 固定限界 |
| --- | --- | --- | --- |
| train-first index4359 | 2.29477882385e-06 | 1.01327896118e-06 | 2.11238396168e-06 |
| train-last index3450 | 2.38418579102e-06 | 2.74181365967e-06 | 2.56762218475e-06 |

新しい点のPython値0.0283811092376709、Rust値0.028383851051330566、差2.741813660e-6>限界2.567622185e-6。原因はまだ同一入力で分離していない。前の点と同じ原因だと断定しない。局所SSEの改善が全層の最大誤差条件を保証しない負の結果として保持する。一般的な修正根拠がある今回のsourceを保存し、最後の1点だけに合わせる再変更や旧版への成績選択rollbackは行わない。

## 実行・失敗・保存

初回診断exampleはgeneric shape配列のSerialize未対応でcompile exit101、局所演算0。shapeをVecへ変える記録形式だけの修正後、fresh command rootでbuild/実行した。初回比較器をcompile成功確認前に起動し、未生成closureの読取りでexit1になった。両失敗とsource/stdio/exit/closureを保持し、成功したkernel後のfresh比較器だけを判定に使用。数値候補の試し直しではない。

| 主実行 | 秒 | 監視込みfootprint B | 監視込みRSS B | exit |
| --- | --- | --- | --- | --- |
| rust-r1-upstream-kernel2-20261016-records | 4.161 | 294,587,464 | 388,907,008 | 0 |
| rust-r1-tests4-20261016 | 10.367 | 284,986,488 | 430,899,200 | 0 |
| rust-r1-predict3-20261016-records | 6.992 | 285,215,816 | 404,701,184 | 0 |

全単位が親900/子870秒、physical footprintとpeak RSS各2GiB内。Python診断のchild peak RSS 305,037,312B。Rust wrapperは同process groupのCargo/compiler/linkerを監視し、sampling間隔と短命childの捕捉限界を記録。hard OS capではない。build cache+targetの上限1.5GiBは維持し、最終regular file合計941,516,286B。旧artifact/EvidenceStore/stdio上限も維持。

主要rootはartifacts/rust-r1-upstream-comparison2-20261016、rust-r1-tests4-20261016、rust-r1-burn-predictions3-20261016、rust-r1-compare3-20261016。新しい全体比較rootは有効な負の結果でcomplete、command rootはexit1/failedのまま。旧closed roots/失敗/参照は保持。全source/stdio/exit/state/closureと文書前後はartifacts/rust-r1-upstream-results-20261016-evidenceへ保存し、全part/SHAを読戻す。

Mac共通CPUのテストと局所診断はpass、元のR1全体gateは未達。Windows native/OS依存suite、製品toolchain1.98.1、下流lockなし解決は未実行/未解決のまま。R2学習、CARE test/需要2015再評価、製品repo編集、push、本番採用は0。

## 次工程の境界

同一入力でのnorm/attention診断と一つの事前固定した一般修正、元7ケースでの確認までを完了し閉鎖した。新しい1点へ同様の局所修正を次々選ぶ探索はしない。次に進める診断は、両train batchと人工入力を含めた全層について、単体丸め誤差と上流累積差を共通の指標で分ける有限設計を先に固定するものとする。特定の1点だけを改善する追加candidateや全体forward反復を許可条件にしない。R1 gateの許容差は維持し、未達の間R2は開始しない。

保全・点検第一、学習を含むRust/bantoの目的、AI本体banto-ai/利用側banto-industrialとdenroku-psi-demoを維持。需要2015停止・調整2014以前・同休業mean28・四季両側非増加・観測のみ/欠測0評価分離、heartbeat PAUSEDは不変。
