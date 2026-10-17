# 正式R2の固定条件（CARE fold0）

2026-10-17 JST。[R0.2](rust-r0.2-comparison-amendment-2026-10-17.md)で1回だけ実行できる正式R2を、Torch参照とRustの実行より前に固定する。機械可読の条件は[R2契約](../../examples/configs/rust-r2-formal-20261017.json)を正とする。許容差はR0.1のまま、更新の比較はR0.2の規則に従う。

## 入口

[入口確認](../results/rust-r2-entry-check-2026-10-17.md)で、この環境のR1最終出力（超過0/12,096）と同一入力局所比較385件（超過0）、数値以外のR1条件を確認した。累積中間値は3/389,214要素超過（train-last/blocks.1）で、診断として記録している。

## 入力

- 保存state：fold0で選択されたstep4096のstate（59 trainable tensorとbuffer、AdamWのstepとmoment）。中立binaryから読む。
- batch：fold0のtrain-prefixから、固定scheduleのstepで決まる8例（context [8,3,128]、正解 [8,3,32]）。Macで保存したbatch参照（step 0・4095）とbytes一致することを毎回確認する。
- 保存物の場所：CARE由来のデータと学習済みstateは公開リポジトリに入れず、gitignore済みの`artifacts/`に置く。リポジトリにはhashと集計だけを残す。

## ケース

| ケース | 内容 |
| --- | --- |
| 1更新 | 保存parameter＋新しいAdamW（step 0、moment 0）、batch step 0で1更新 |
| 8更新 | 保存parameter＋新しいAdamW、batch step 0〜7で8更新 |
| 成熟state import | 保存parameter＋保存AdamW（step 4096とmoment）、batch step 0で1更新 |
| floorのtie | 人工データ。保存parameter、R1のfloor-equal入力（母標準偏差がscale_floorとちょうど等しい）、交互符号の人工正解。lossと勾配だけ（更新なし） |
| 保存再開 | Rustのみ。連続8更新と、4更新→checkpoint→別processで復元→4更新で、parameter・moment・counter・出力（次batchのforward）がbytes一致 |

**開始weight。** 1更新と8更新は、選択された保存parameterに新しいAdamWを付けて始める。理由は次の3つ。
- R0.1の参照が固定しているのは選択stateだけで、初期weightは`initial.pt`にしかない。使うなら新しい参照を足すことになる。
- 1更新と成熟state importが同じparameter・同じbatchになり、違いがoptimizerの状態だけになる。
- 実行前の測定で、step 0と4095のbatchでK·eps未満として除外される要素は0.28%で、10%の停止条件から遠い。

実装計画は「保存weightからfresh optimizer」「同じ初期weight」と書いており、初期weightと選択weightのどちらかは明記していない。`initial.pt`を中立形式に変換して使う案もある（計画がR3で行う方法）が、上の理由で採らない。

**成熟state importのbatch。** 4096 stepのscheduleはstep 4096で尽きる。`FrozenPreparation`はstep 4096以上を拒否し、保存stateのsampler位置は32768である。そのため、scheduleの最初のbatch（step 0）を実行前に固定した。

## 微分できない境界

| 境界 | 確認 |
| --- | --- |
| pinballのtie | R2PのL1・L4（人工、通過）。実batchのstep 0・4095にちょうどのtieはなかった |
| context尺度のmaximum（std＝floor） | floorのtieケース。尺度は入力とscale_floor（buffer）だけで決まるので、tieでの劣勾配の選び方はparameterの勾配を変えない。R0.1の`nondifferentiable_boundary`どおり数値でも確かめる |
| clip係数＜1 | 実batchのglobal normは約0.43〜0.73で係数は1。normがmax_normを超えて縮める分岐はR2PのC2・C3・O3で確認済みで、実データでは確認しない |

## 比較（R0.2）

| 対象 | 方法 |
| --- | --- |
| loss | 毎更新。1回目はnormalized_loss、2回目以降はeight_step_loss。floorのtieはnormalized_loss |
| 勾配 | 毎更新とfloorのtie、全59 tensor。clip前・clip後、global norm、clip係数（分母のeps 1e−6）をR0.1のgradient規則で |
| parameter | 毎更新の後。1回目はone_step_parameter、8更新の2〜8回目はeight_step_parameter。参照のclip後|勾配|≥1e−7をその実行の各更新で満たす要素だけを判定し、除外を記録 |
| moment | 毎更新の後、全要素 |
| forward | 毎更新の後に記録のみ。次の更新のlossとして判定 |
| 保存再開 | bytes一致 |

## 実行の単位と停止

- 正式R2は、実行ツールの1回の起動で次の順に行う。
  1. Torch参照とそのfloat64確認を行い、hashを付けて固定する。
  2. Rustで1更新・8更新・成熟state import・floorのtieを比べる。
  3. 別processで保存再開を確認する。
- buildは実行前に`cargo build --release --locked`で行い、時間制限の外とする（所要時間は記録する）。
- 数値の比較結果ではない失敗（crash・I/O・ファイル欠落・時間切れ）に限り、実行ツールだけを直して全体を実行し直せる。fixture・許容差・recipe・参照は変えない。その場合も、固定した参照と、すでに数値結果を出したケースの結果がbytes一致で再現しなければ止める。
- 数値の超過は記録して正式R2を止める。その後にfixture・許容差・参照を変えない。
- float64確認の不一致は数値の失敗として扱い、Rustを実行せずに止める。設定を変えて参照を作り直すことはしない。
- どこかの比較更新で除外が10%を超えたら、採否の前に原因を調べる。
- 資源上限（各process）：親900秒、子870秒、2GiB、jobs 1。

## 参照と記録

- Torch参照はこの環境（float32、1 thread、deterministic）で作る。元の学習はmacOSの2 threadだったため作り直す。同じ手順のfloat64計算と、lossと勾配がR0.1内で一致した場合だけ採用する。parameterとmomentは、AdamWが|勾配|がeps程度の要素で丸めを増幅するため、この確認では記録だけにする。
- 記録するもの：
  - git commit、`crates/banto-ai/src/*.rs`・実行ツール・参照生成器・small_model.py・Cargo.lockのsha256、rustcとtorchのversion
  - 比べる更新ごとに、除外したparameter要素の割合（109,024要素に対して）・tensor名・位置
  - 超過したすべての要素の値
  - 各processの時間とメモリ、buildの所要時間
- validation選択・校正・CARE testの予測/評価・追加学習・別fold・R3は行わない。
