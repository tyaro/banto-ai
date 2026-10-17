# R2P工程3: 人工学習の連続8更新と保存再開

2026-10-17 JST。[R2P固定条件](../research/rust-r2p-synthetic-training-contract-2026-10-16.md)の工程3として、[工程2の部品](rust-r2p-training-parts-2026-10-17.md)で人工affineモデル（weight[3,2]・bias[3]の9値）を学習し、checkpointの保存・別processでの再開を検証した。比較先は[Cloud参照](rust-r2p-cloud-reference-2026-10-17.md)、許容差はR0.1のまま。

## 実装

- `training::train_step`：毎更新でparameterから新しいautodiff leafを作り、forward→backward→名前で勾配回収→global clip→AdamW。更新間にgraphを持ち越さない。
- [`synthetic_checkpoint`](../../crates/banto-ai/src/synthetic_checkpoint.rs)：`banto.synthetic-training-checkpoint.v1`。新規directoryに`payload.f32`（little-endian float32のparameter・1次/2次moment・buffer）を書いてfsync、決定的な`manifest.json`（entryごとのshape/offset/hash、整数のglobal/parameter step、次位置、schedule・fixture・recipeの束縛、backend/thread、RNGなし）を書いてfsync、最後に`COMMIT`を排他作成してfsync。既存directoryは置き換えない。
- 復元はmarkerがmanifestのbytesを束縛すること、payloadのsize/hash、schema、schedule/fixture/recipe、entryの完全性と一意性、shape・範囲・entry hash、有限値、2次moment非負、整数step、step=次位置、bufferの一致をすべて確認してから状態を作る。不足時に0から始める代替はしない。

## 検証（`tests/r2p_synthetic.rs`、CIで毎回実行）

| 項目 | 結果 |
| --- | --- |
| A：連続8更新をTorch参照と各stepで照合（更新前予測・loss・clip前後の勾配・parameter・1次/2次moment・step・probe 0..8） | 全件R0.1内。step1はone-step/normalized-loss、step2〜8はeight-step条件 |
| B：別processで4更新しstep4をcommit、更新5の前の境界で取消 | step4・次位置4で停止、更新5なし。payloadはAのstep4とbyte一致 |
| C：さらに別processでBを復元し、更新5の前のprobe確認後に残り4更新 | step8のpayloadとprobe 4..8がAとbyte一致 |
| 不正checkpoint K0〜K7（切詰め、bit反転、moment欠落、名前重複、負の2次moment、step 4.5、schedule hash不一致、commit欠落） | 全件拒否。K2〜K6はhashとcommitを作り直した上で、意味の検査で拒否 |
| writer途中停止 F0〜F2（payload半分、payload fsync後、manifest fsync後） | commitなし、全件拒否 |
| 既存checkpointの保護 | 置き換え拒否、Bのファイルhash不変 |

Rustのtoy更新は計16（A8・B4・C4）、独立AdamW6と合わせ22で契約どおり。負のケースで追加の学習はしていない。

試験が誤りを検出できるか意図的な改変で確かめた。2次momentの非負検査を外すとK4、marker欠落時にmarkerを偽造するとK7、復元時にstepを0にするとCの再開がそれぞれ失敗した。

## 変えていないもの・次工程

R0.1許容差、固定fixture/protocol、R1の残1点未達、正式R2実データ学習の停止。R2Pの通過をR1や正式R2の合格へ読み替えない。次は工程4（SmallForecaster全体を人工データで学習graphへ接続する条件を、実装前に別fixtureとして固定する）。
