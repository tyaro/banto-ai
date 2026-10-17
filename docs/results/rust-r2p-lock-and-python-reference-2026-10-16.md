# R2P: Cargo.lock最小案と人工Python参照

2026-10-16 JST。[復帰計画](../research/banto-ai-practical-training-return-plan-2026-10-16.md)と[固定R2P条件](../research/rust-r2p-synthetic-training-contract-2026-10-16.md)に沿って実施。隔離Cargo.lockの最小案と人工Python参照を保存済み。gemm直接edge1行削除のみ、lock662記録/version・有効154package/feature不変。loss7/clip4/AdamW6/小型8更新、独立照合107件すべて原許容差内。

## Cargo.lockの整合案

元workspaceのmanifest/source/lockを新しい隔離workspaceへ複写し、banto-aiのdependenciesからmanifestにない`gemm`直接edgeだけを削除した。既存gemm packageは他依存から使用されるため残す。元lock/manifestは変更していない。提案は[差分](../../artifacts/rust-r2p-reference-20261016-lock/Cargo.lock.diff)と[全lock](../../artifacts/rust-r2p-reference-20261016-lock/Cargo.lock.proposed)へ保存。

隔離側のnative Cargo1.95 `tree --locked --offline`はpackage/feature確認ともexit0。resolverによる追加更新・ダウンロード・compileなし。lockの全662 package記録/versionはこのroot edge以外同一。有効154package/versionとfeature集合を閉鎖済みfused-linear dependency baselineと照合し一致。未定義の旧研究feature3種を復活していない。feature照合は保存済みCargo feature tree集合によるもので、全研究targetのbuild成功を意味しない。

この工程では整合を検証した隔離案をPython参照生成の入口に使った。**元workspaceへはまだ適用していないため、Rust受入実行の前に提案を明示的に適用する必要がある。** 以前の元workspaceでのexit101は解消済みとは記載しない。

## 一度だけ生成した参照

Python3.14.8、固定Torch git `08187d9e0fba026dc8217405802ab5381dc88d90`、CPU float32、thread/interop各1、乱数draw0。固定fixtureのloss7・clip4・単独AdamW6と9parameterの連続8更新を一度だけ実行した。backward15、optimizer更新14、clip18、probe9。小型affineの更新であり、実データや全SmallForecasterの学習は行っていない。

| 保存・照合対象 | 結果 |
| --- | --- |
| loss・tieの勾配・batch/channel/horizonの縮約 | 有理数期待値と7case通過。全tieのloss0でも勾配非ゼロを保持 |
| global clip・zero/boundary・複数parameter | scalar期待値との4caseと全更新の照合通過 |
| AdamW・decay・epsilon・step4096のmoment | 6case通過、全parameter/m1/m2/counter保存 |
| 人工連続8更新 | 日次ではなく固定人工batchの小型学習。全更新のprediction/loss/gradient/clip/parameter/moment/counterとprobe0..8を保存 |
| 独立照合 | 107件すべて固定R0.1条件内。scalar数学計算はTorchのfloat32演算順を再現したという主張ではない |

[参照binary](../../artifacts/rust-r2p-reference-20261016-numeric/reference.f32)はfloat32 little-endian 4,608bytes/1,152値、[layout](../../artifacts/rust-r2p-reference-20261016-numeric/reference-layout.json)は427tensorの名前・shape・offset・長さ・SHA256・値を収録。binary全byteをlayoutと照合し、gap/overlap/重複なし。SHA256は`29ded0bc284c239326ddceb06e9ed7650f87789d7611a94291913824f9e70900`。layoutのoptimizer添字は各journalのordered_namesに対応する。Rust consumerはfixtureの初期値から開始し、この参照の中間stateを学習初期値へ流用しない。

[独立期待値](../../artifacts/rust-r2p-reference-20261016-publication/independent-expectations-layout.json)とfloat64数学値payloadも保存。これは閉鎖済み参照の保存値からのscalar検算で、Torch参照を再生成していない。nativeチェック107件の判定値も完全再現した。元有理数期待値、source/recipe/fixture/schedule pins、runtime版、stdio/exit/state/closureを保存した。NumPy未導入警告1件は保持し、NumPyを使わず数値bytesを保存した。

## 保護・資源・次工程

元R0.1許容差、41 source pinsと固定契約/fixture/protocol、元manifest/lock/model、既存失敗とclosed rootsは不変。libtorch_cpu SHAも既存pinと一致。最大観測（監視process込み）はphysical footprint 263,783,816B、RSS 315,244,544B、cache+target1,037,488,009Bで各2GiB/1.5GiB内。各parent900/child870秒とstdio/artifact/EvidenceStore枠を維持した。監視はsampleでありhard OS capではない。

次は保存した最小lock案を適用する工程と、固定条件内のfeature-gated小型loss/gradient/互換AdamW/checkpoint実装。既存推論modelを変更せず、小型Rustの連続8対4+復元4、入力拒否6/checkpoint拒否8/writer停止3を有限検証する。今回はそのRust実装・build・test・保存再開を行っていない。参照生成の成功だけでRust学習やfull modelの数値互換・保全性能の成功にしない。

ポインタ/once/TLS/PAC/vendor追跡は停止継続。R1残1点未達/正式R2実データ学習停止、CARE/MetroPT test凍結、需要2015停止・2014以前調整・同休業mean28比較・四季平均の過小量/過大量非増加・観測のみ/欠測0仮定分離を維持。保全・点検第一、学習を含むRust移植とbanto-ai→利用側の責務を維持する。AI crateはbanto-ai、依存方向はbanto-industrial/denroku-psi-demo→banto-ai。

Mac共通CPU上のPython参照とCargo metadata確認の結果である。Windows native/OS依存テストは未実行として分離。heartbeat PAUSED、外部送信・下流編集・Git push・製品採用0。証跡は`artifacts/rust-r2p-reference-20261016-evidence`、各phaseとpublicationの`-records`。元の固定契約文書の「未実行」は凍結時の状態として保護し、現在状態は本書と引継ぎを参照。
