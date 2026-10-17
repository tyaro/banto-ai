# Rust人工学習の棚卸しと検証条件の固定

2026-10-16 JST。[人工R2P契約](../research/rust-r2p-synthetic-training-contract-2026-10-16.md)、[機械仕様](../../examples/configs/rust-r2p-synthetic-protocol-20261016.json)、[人工入力と期待値](../../examples/configs/rust-r2p-synthetic-fixtures-20261016.json)を固定した。現実装の棚卸しと数式の検算を完了し、学習実装・数値参照生成・Rust学習/保存再開の実行はまだ行っていない。

## 現在の不足と入口条件

推論Tensor経路と名前付きstateはあるが、学習leaf登録、loss、named gradient、互換AdamW、完全な再開checkpointは未実装。source由来schemaは62tensor、学習対象59/109,024値、buffer3/348値。現parameter_count()は定数なので実列挙の試験結果とは区別した。neutral readerはAdamW項目を検査しても返さず、moment完全性/step/schedule/writer/復元を備えていない。

Cargo tree --locked --offlineはexit101でlock更新が必要。manifestにないgemmのroot edgeがlockに残る。Burnのinstalled optim featureはautodiffを有効にするため、それだけのための依存追加は不要と静的には読めるが、実効feature graphは確認できていない。Cargo/lockを編集せず、先に最小整合案を隔離copyで作る条件とした。

初版inventoryのfeature抽出regexに余分な閉じ括弧があり、空リストを出していた。閉鎖済みlib.rs snapshotから独立に再抽出し、未定義cfg featureはfma-extension/fused-linear-extension/reference-normalizationの3つと訂正した。初版root/sourceを変更せず、本rootのcorrected-dependency-inventory.jsonを正とする。Cargoの再実行はせず、実データ/ポインタも読んでいない。

## 固定した有限検証

loss7、global clip4、AdamW1更新6、小型affine1問題を固定。小型問題は人工parameter9値、乱数なし、固定8batch。Rustは連続8、取消保存4、別process復元4の3軌道で、独立AdamW込みの更新数上限22。取消はstep4の確定保存後/step5前を使い、別の学習軌道を増やさない。入力拒否6、checkpoint不正8、writer途中停止3地点も固定し、全変異をJSONへ列挙した。

7つのlossとgradientをFractionによる独立した有理数計算で検算し、L0〜L4の保存gradientと全loss期待値に一致した。これはfloat32のTorch参照や実学習ではない。次の参照生成でinstalled Torchとの一致を要求し、参照bytesを閉鎖してからRust受入を実行する。数学的式だけでPyTorchの丸め順を再現したとはしない。

loss/gradient/1更新/第1第2moment/8更新は元R0.1の条件を参照。小型問題のstep1とsteps2..8の割当ても事前固定した。同じRustの連続と復元はparameter/m/v/counter/schedule/probe bytes一致。既存の数値条件を緩めず、R1未達や正式R2停止を解除しない。

次はmanifest/lockの最小整合案と、固定した人工データの一度のPython参照生成。実データ/CARE weights・全SmallForecasterの人工学習接続はこのv1に含めない。全モデル接続は部品通過後の別条件とする。

## 保護と確認

ポインタ追跡は停止継続。source/manifest/lock/元R0.1/installed Burn/Torch sourceのhashを棚卸し前後と文書保存後に照合し、変更していない。今回の依存確認はbuild/testではなくreadonly metadata probe。Rust学習・forward/backward/optimizer更新・CARE/MetroPT test/需要2015再評価・新取得・下流編集・Git push・製品採用0。heartbeat PAUSED、保全第一、需要の2014以前/同休業mean28/四季両側非増加/観測欠測0分離を維持。

親900/子870秒、physical footprint/peakRSS各2GiB、cache+target1.5GiB、元artifact/EvidenceStore/stdio枠を維持。Mac共通CPUの仕様とWindows native/OS依存試験は分離し、後者は未実行。全source/metadata command/stdio/exit/state/closure、訂正、解析的期待値、条件pinsと文書前後はartifacts/rust-r2p-inventory-20261016と同-records、artifacts/rust-r2p-specification-20261016と同-evidenceへ保存。publication自身のstdio/exit/stateは同-records。
