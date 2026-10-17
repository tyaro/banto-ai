# 正式R2の入口確認（2026-10-17）

[R0.2](../research/rust-r0.2-comparison-amendment-2026-10-17.md)の入口条件を、正式R2を実行するCloud環境（x86_64 Linux、Rust 1.95.0、Burn 0.22 Flex CPU、Torch 2.14.1+cpu、1 thread）で確認した。**数値の条件（最終出力・同一入力局所比較385件）と数値以外のR1条件はすべて満たした。** 累積中間値はR0.2どおり診断として記録した。R0.1の許容差は変えていない。学習・CARE test/truthの読み込みはない。

## 入力

MacからCAREの保存物を受け取り、R0.1に記録した5参照（成熟state・layout・fold0 batch参照・profile・schedule）のbyte数とsha256、8つのartifactの閉包記録（`root-closed.json`）の全ファイルを照合し、すべて一致した。CARE数値入力の閉包hashは学習コードに固定された値と一致した。fold0のbatchをCloudで組み立て直すと、step 0と4095がMacのbatch参照とbytes一致した。保存物は公開リポジトリに入れず、gitignore済みの`artifacts/`に置く。

## 方法

[`tools/r2_entry_r1_check.py`](../../tools/r2_entry_r1_check.py)が、MacでのR1手順をそのまま1回で行う。

1. Torch参照：保存weightで7case（保存train batchの先頭・末尾、zero・constant・floor3種）のforwardと23の名前付きtrace。7caseの入力はMacのR1と同じbytesであることを確認する。
2. Rust：`predict`例（crateの推論traceそのもの）。
3. 元のR1比較：23 traceの全389,214要素をR0.1で比べる。最終出力（正規化・元単位の分位点）は別に集計する。
4. Torchの55節点の関数的再生。フックで取ったtraceとbytes一致を確認する。
5. Rust：[`r1_layer_audit`例](../../crates/banto-ai/examples/r1_layer_audit.rs)（保存tagの`diagnose_layers.rs`を戻したもの）。自前経路はcrateのtraceと161 anchorすべてbytes一致し、同一入力の各演算を評価する。
6. 385比較：局所差（同じ入力でのRust−Torch）、累積差、伝播差の符号付き分解。

## 結果

| 判定 | 結果 |
| --- | --- |
| 最終出力（7case、12,096要素） | **超過0**（許容差比 最大0.47） |
| 同一入力局所比較（385件、953,694要素） | **超過0**（許容差比 最大0.35、blocks.1.ff.1） |
| 符号付き分解の残差 | 0 |
| 累積中間値（診断） | 389,214要素中3要素超過：train-last/blocks.1（index 3983・3984・4343、許容差比 最大1.10） |

累積中間値の超過は、Macの1点（index 3450）と同じtrain-last/blocks.1の残差和で、位置だけが変わった。局所差は0で、上流から引き継いだ差である。節点単位の診断では、train-lastのblocks.1.temporal.mixed・blocks.1.residual1・blocks.1.ff.2にも1要素ずつ累積差の超過がある（元のR1判定の対象外の節点）。

MacとCloudの差（診断）：Torchの節点値は385節点中31節点がbytes一致、最大差1.5e−5。Rustの自前経路は73節点がbytes一致、最大差1.1e−5。どちらも同じ桁の丸め差で、局所比較・最終出力の判定には影響しない。

## 数値以外のR1条件

| 項目 | 確認 |
| --- | --- |
| 分離build・CPU compile | CIの新しいrunnerでworkspaceを毎回build/test。Cloudで`cargo build --release --locked`（`predict`・`r1_layer_audit`）成功 |
| backend・lock | Burn =0.22.0（std/optim/flex）、Cargo.lockを`--locked`で使用 |
| 依存ライセンス一覧 | `cargo metadata`でbanto-aiから到達する564 package。MIT/Apache-2.0系が大半。ほかにUnicode-3.0、BSD-2/3-Clause、ISC、Zlib、BSL-1.0、CC0-1.0、CDLA-Permissive-2.0（webpki-roots）、MPL-2.0（buildid・colored・option-ext、ファイル単位のcopyleft）。license欄が空のcfg_blockはLICENSEファイルがApache-2.0 |
| 非有限・mask・分位点順序 | crateのunit test（欠測・非有限の入力拒否、時間maskで過去出力が未来queryに影響しない）と推論時の非有限・順序違反の拒否、`neutral_integrity`（破損・NaN・非因果mask・余分byteのweightを拒否）がすべて通過 |

## 保存物

`artifacts/r2-entry-r1-20261017/`（gitignore、公開しない）。閉包hash：reference `4a679811…`、rust-predict `825296f6…`、layer-fixture `b4a14795…`、rust-layer `f4cb5f4d…`。summary.json `f58bea09…`。

次は[正式R2の固定条件](../research/rust-r2-formal-contract-2026-10-17.md)に沿い、実行前のfixtureを固定してから正式R2を1回だけ行う。
