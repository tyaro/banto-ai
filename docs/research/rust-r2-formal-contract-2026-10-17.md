# 正式R2の固定条件（CARE fold0）

2026-10-17 JST。[R0.2](rust-r0.2-comparison-amendment-2026-10-17.md)で1回だけ実行できる正式R2を、Torch参照とRustの実行より前に固定する。機械可読の条件は[R2契約](../../examples/configs/rust-r2-formal-20261017.json)を正とする。許容差はR0.1のまま、更新の比較はR0.2の規則に従う。

## 入口

[入口確認](../results/rust-r2-entry-check-2026-10-17.md)で、この環境のR1最終出力（超過0/12,096）と同一入力局所比較385件（超過0）、数値以外のR1条件を確認した。累積中間値は3/389,214要素超過（train-last/blocks.1）で、診断として記録している。

## 入力

- 保存state：fold0で選択されたstep4096のstate（59 trainable tensorとbuffer、AdamWのstepとmoment）。中立binaryから読み、pickleは使わない。
- batch：fold0のtrain-prefixから、固定scheduleのstepで決まる8例（context [8,3,128]、正解 [8,3,32]）。Macで保存したbatch参照（step 0・4095）とbytes一致することを毎回確認する。
- 保存物の場所：CARE由来のデータと学習済みstateは公開リポジトリに入れず、gitignore済みの`artifacts/`に置く。リポジトリにはhashと集計だけを残す。

## ケース

| ケース | 内容 |
| --- | --- |
| 1更新 | 保存parameter＋新しいAdamW（step 0、moment 0）、batch step 0で1更新 |
| 8更新 | 保存parameter＋新しいAdamW、batch step 0〜7で8更新 |
| 保存再開 | Rustのみ。連続8更新と、4更新→checkpoint→別processで復元→4更新のbytes一致 |
| 成熟state import | 保存parameter＋保存AdamW（step 4096とmoment）、batch step 0で1更新 |

実装計画の「保存weightからfresh optimizer」は、選択された保存weightと解釈した。初期weightは`initial.pt`（pickle）にしかなく、R0.1の`untrusted_pickle_required: false`に反するため使わない。成熟state importのbatchは、4096 stepのscheduleがstep 4096で尽きているため、scheduleの最初のbatch（step 0）を実行前に固定した。

## 比較（R0.2）

| 対象 | 方法 |
| --- | --- |
| loss | 毎更新。1回目はnormalized_loss、2回目以降はeight_step_loss |
| 勾配 | 毎更新、全59 tensor。clip前・clip後、global norm、clip係数をR0.1のgradient規則で |
| parameter | 8更新の1回目後と8回目後、1更新の後、成熟importの後。参照のclip後|勾配|≥1e−7をその実行の各更新で満たす要素だけを判定し、除外を記録 |
| moment | 比べる更新の後、全要素 |
| forward | 記録のみ。次の更新のlossとして判定 |
| 保存再開 | bytes一致 |

## 参照・記録・停止

- Torch参照はこの環境（float32、1 thread、deterministic）でRust実行より前に生成し、hashを記録する。同じ手順のfloat64計算とlossと勾配がR0.1内で一致した場合だけ参照として採用する。元の学習はmacOSの2 threadだったため、参照は作り直す。
- 比べる更新ごとに、除外したparameter要素の割合（109,024要素に対して）・tensor名・位置、超過した全要素の値、各processの時間とメモリを記録する。
- どこかの更新で除外が10%を超えたら、採否の前に原因を調べる。
- 数値の不一致は記録して正式R2を止める。Rustの数値結果が出た後に、fixture・許容差・参照を変えない。数値比較の前の失敗（build・I/O・ファイル欠落）に限り、修正して実行し直せる。
- 資源上限：親900秒、子870秒、各process 2GiB、jobs 1。
- validation選択・校正・CARE testの予測/評価・追加学習・別fold・R3は行わない。
