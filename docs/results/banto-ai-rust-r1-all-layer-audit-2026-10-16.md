# Rust R1 — 全55箇所・7ケースの局所差と累積差の診断（2026-10-16）

[実装計画](../research/banto-ai-rust-implementation-plan-2026-10-16.md)に沿い、[診断条件](../../examples/configs/rust-r1-all-layer-audit-20261016.json)を数量計算前に固定して実行した。**同一入力での局所的な実装差は全385比較で固定許容差内。上流の差を引き継いだ結果は、従来と同じtrain-last/block1の1点が超過した**。1点向けの修正や算術候補選択は行わず、core/weight/許容差は不変。診断は完了、R1全体は未合格のまま。

## 固定条件と分解の意味

対象は両train batch＋人工zero/constant/floor-below/equal/aboveの固定7ケース、各55箇所。context平均/尺度/正規化、patch/tokens、2blockの全LayerNorm、時間・系列attentionのq/k/v線形射影/logits/softmax/mixing/出力、3残差和、FF線形/GELU/線形、final_norm/head、分位点組立と元単位復元を含む。LayerNormやstd/floor等は一つのkernel境界であり、その内部の全CPU命令を個別に分けたものではない。

各箇所で、Pythonの自経路入力にPythonを適用したPP、Rustの自経路入力にRustを適用したRR、Pythonの入力を同じ形・bytesでRustへ渡したRPを保存した。q/k/vは同じtranspose配置を再構成する。

| 分解 | 定義 |
| --- | --- |
| 同一入力の局所差 | RP − PP |
| 上流から伝わる差 | RR − RP |
| 合計差 | RR − PP |

局所差にはfloat32の丸め、数学関数の近似、kernel実装差やlayoutの影響が含まれ得る。「純粋な丸め誤差だけ」と証明した解析的上限ではない。上流差も微分/Jacobian近似ではなく、同じRust演算を実際の2種類の入力で評価した差である。符号付き分解を保存float32からfloat64で集計し、全有限要素で**合計＝局所＋上流が厳密成立**した。絶対誤差の和には相殺があるため、各L1を足せば合計L1になるとはしない。

R0の中間値条件2e-6＋2e-5×abs(PP)、元単位quantile条件1e-4×T32＋2e-5×abs(PP−context_center)は変更していない。追加したprimitive内部比較は診断指標であり、元のR1 gateへ新条件を加えたり、既存条件を外したりしていない。

## 再現・来歴の条件

既存の23 named outputs×7ケース＝161箇所について、Python・Rustの自経路再生がそれぞれ保存済み成果とbytes一致したことを確認してから分解を解釈した。参照Pythonの保存7ケースと現行Rust predictions3を変更せず、モデル・profile・信号順・入力を同じhashで固定した。

初回の診断用Python再生は、plain tensorの関数呼出しと既定grad modeを用い、zero/blocks.0.variateの厳密再現条件に失敗した。そのrootと全記録をfailedのまま保持。診断だけを元のSmallForecaster nn module/Parameterとno_gradにそろえ、fresh rootで全161箇所を再現した。複数の実行条件を一緒にそろえたため、そのうち一つだけが原因とは断定しない。失敗した再生を元のモデル誤差に混ぜず、数値候補や許容差の変更も行っていない。

成功経路はPython参照診断再生7回、Rust診断再生7回と385箇所の独立した同一入力評価。これは新しいモデル候補のfull確認ではなく、保存値を再現する有限診断である。初回失敗で実行した途中の再生も記録に残る。学習/backward/optimizer、target/CARE test/truth、需要2015の再評価は0。

## 全ケースの結果

| 項目 | 結果 |
| --- | --- |
| ケース / 箇所 / 比較 | 7 / 55 / 385 |
| 診断要素 | 953,694 |
| 有限要素の分解確認 | 948,654、分解残差0 |
| −∞ causal mask | 5,040値で厳密一致、NaN/予期しない∞なし |
| 同一入力局所差の超過 | **0要素 / 0箇所** |
| 累積差の超過 | **1要素 / 1箇所** |
| 元のR1比較対象 | 389,214要素中1超過、従来結果と一致 |
| Python / Rustの保存出力anchor | 各161箇所でbytes一致 |
| モデル修正・候補探索 | 0 |

| ケース | 局所差の超過 | 累積差の超過 |
| --- | --- | --- |
| train-first | 0 | 0 |
| train-last | 0 | 1 |
| zero | 0 | 0 |
| constant | 0 | 0 |
| floor-below | 0 | 0 |
| floor-equal | 0 | 0 |
| floor-above | 0 | 0 |

## 演算群別の最大絶対差

| 演算群 | 局所差最大 | 上流差最大 | 合計差最大 |
| --- | --- | --- | --- |
| context_normalization | 2.9802322e-08 | 4.7683716e-07 | 4.7683716e-07 |
| patch | 4.7683716e-07 | 7.1525574e-07 | 7.1525574e-07 |
| tokens | 0 | 7.1525574e-07 | 7.1525574e-07 |
| layer_norm | 7.1525574e-07 | 1.7881393e-06 | 1.7881393e-06 |
| attention_projection | 7.1525574e-07 | 2.1457672e-06 | 2.1457672e-06 |
| attention_logits | 4.7683716e-07 | 5.2452087e-06 | 5.2452087e-06 |
| attention_softmax | 1.1920929e-07 | 7.1525574e-07 | 7.1525574e-07 |
| attention_mixing | 0 | 3.8146973e-06 | 3.8146973e-06 |
| attention_output_projection | 9.5367432e-07 | 3.3378601e-06 | 3.8146973e-06 |
| residual_sum | 0 | 6.1988831e-06 | 6.1988831e-06 |
| ff_linear | 1.4305115e-06 | 4.0531158e-06 | 4.2915344e-06 |
| gelu | 4.7683716e-07 | 1.9073486e-06 | 2.1457672e-06 |
| head | 7.1525574e-07 | 2.1457672e-06 | 2.3841858e-06 |
| normalized_quantiles | 0 | 2.8610229e-06 | 2.8610229e-06 |
| quantiles | 0 | 7.6293945e-06 | 7.6293945e-06 |

単位・尺度の違う行の絶対値を単純な優劣の順位にしない。RMS・ULP距離・固定限界比・L1・要素数と先頭失敗例はnode-comparisons.json、全case/演算群は別JSONに保存した。ULPは0近傍で大きくなり得る診断値で、採否基準の置換には使わない。

residual_sumの同一入力差は全42比較で0、attention mixingと分位点組立/復元も今回の同一入力では0だった。他の層の小さな実装差が存在し、上流を通るうちに大きくなる局面がある。有限集合での結果であり、一般の入力すべてに対する誤差上限保証ではない。

## 残る1点と結論

train-last/blocks.1 index3450＝[3,1,3,58]、PP=0.0283811092376709、RR=0.028383851051330566。今回RP=PPで局所差0、合計差2.741813660e-6は全て上流入力の差として分解され、固定限界2.567622185e-6を超える。したがって、この残差加算だけを直す根拠は得られなかった。

元の最終正規化/元単位出力は各6,048要素が許容差内、元R1の中間値1点未達は不変。局所差が全て条件内でも、全体の中間値gateを保証しないことを7ケース全層で確認した。局所passだけでR1合格へ変更せず、R2学習にも進まない。q50/context_centerを需要平均へ読み替えない。

## 資源と保存

| 実行 | 秒 | 測定メモリ |
| --- | --- | --- |
| rust-r1-layer-fixture-20261016-records | 2.868 | child peak RSS 308,969,472B |
| rust-r1-layer-fixture2-20261016-records | 2.662 | child peak RSS 326,467,584B |
| rust-r1-layer-format-20261016 | 1.993 | 監視込みfootprint 26,870,912B / 同時RSS 62,554,112B |
| rust-r1-layer-kernel-20261016-records | 5.337 | 監視込みfootprint 287,886,384B / 同時RSS 409,698,304B |
| rust-r1-layer-comparison-20261016-records | 2.290 | child peak RSS 49,954,816B |

全実行は親900/子870秒、physical footprintとpeak RSS各2GiB以内。RustはCargo/compiler/linkerの同process groupを監視し、最大sampling間隔/短命childの捕捉限界も保存。hard OS capではない。build cache+targetは最終958,632,885Bで1.5GiB以内。artifact24file/768MiB・単一32MiB、EvidenceStore16MiB/512file/part256KiB等も維持した。

主要rootはartifacts/rust-r1-layer-fixture2-20261016、rust-r1-layer-kernel-20261016、rust-r1-layer-comparison-20261016。最初の失敗はrust-r1-layer-fixture-20261016とrecordsへ保持。数値payloadは各closed artifactで保管し、全hashを読戻し確認。EvidenceStoreへは全source/stdio/exit/state/closure、payload manifest/hash、全診断集計と文書前後をartifacts/rust-r1-layer-results-20261016-evidenceへ保存する。

Mac共通CPUの診断は完了、元R1 gateは未達。Windows native/OS依存suite、製品toolchain1.98.1、lockなし配布は別の未確認項目。core source/Cargo.lockと旧成果不変、新依存/取得/外部送信/製品repo変更/push/本番採用なし。保全第一・学習を含むRust/banto目的、需要2015停止/調整2014以前/同休業mean28/四季両側非増加/観測と欠測0評価分離、heartbeat PAUSEDを維持。

## 今後の境界

今回固定した全層診断は完了し、同じ再生や1点狙いの修正を反復しない。現行の局所誤差が固定許容差内という事実だけでは、追加の一般修正を選ぶ根拠にならない。今後実装方式を比較する場合は、全ケース・全層へ一律適用する方式、その算術上の根拠、有限な比較数、全体gateを含む採否/停止条件を先に定める。現在その追加方式は選んでおらず、この診断をR1通過やRust学習開始の許可に読み替えない。
