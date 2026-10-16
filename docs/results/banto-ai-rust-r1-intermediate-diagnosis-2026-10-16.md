# Rust R1 — 残る1点の演算差の切り分け（2026-10-16）

[計画](../research/banto-ai-rust-implementation-plan-2026-10-16.md)に沿い、残るtrain-first/block1の1点を共通入力で診断した。**この点のff.2線形演算は共通入力ならRust/Pythonで一致し、残差加算も同じ結果だった。超過は上流2経路の誤差が相殺の大きい和へ集まった結果**。局所演算の違いと上流伝播を分離できたが、元のR1全体は1点未達のまま。許容差は変更しない。

## 固定入力と実施範囲

保存済みPython参照とbalanced Rustのtrain-first全120行を使い、block0出力＋block1 temporal＋variateからFF前残差を再構成した。ff.1出力[8,3,5,128]、固定ff.2 weight[64,128]/bias[64]を取り出し、Python入力とRust入力それぞれを両backendへ同じbytesで渡した。Python側の保存block1再構成はbytes一致。Rust側も実際のFlex線形＋残差和で保存block1全7,680要素にbytes一致し、診断経路が対象経路を再現することを確認。

全model forward0、学習/backward/optimizer0、label/CARE test/需要2015の参照0。PyTorchとFlexは各2回の局所linearだけ。新しい予測やPython参照の再生成は行っていない。model.rsを含むcore sourceとCargo.lockは前回テスト成功時と同じ。追加した [diagnose_ff実行例](../../crates/banto-ai/examples/diagnose_ff.rs) はlocked/offline CPU build・実行済み。coreに変更がないため、既存3テストの無目的な再実行はしていない。

## 共通入力での比較

| 比較 | 要素数 | 最大絶対差 | 超過数 |
| --- | --- | --- | --- |
| Python保存FF入力→各backendのff.2 | 7,680 | 1.430511475e-6 | 0 |
| Rust保存FF入力→各backendのff.2 | 7,680 | 9.536743164e-7 | 0 |
| 同一の残差/線形出力を足す | 各7,680 | 0 | 0 |

線形出力自身にも従来の中間値許容差2e-6＋2e-5×abs(reference)を適用。両共通入力で全要素pass。全linearがbytes一致という意味ではないが、問題のindex4359では両入力ともff.2出力もbytes一致した。独立高精度dotは診断だけに用い、モデルのdtype/演算を高精度値へ置換していない。

## 残る1点の誤差分解

対象は[batch4,series1,token3,dim7]、0始まり。

| 枝 | Python | Rust | Rust−Python |
| --- | --- | --- | --- |
| FF前の残差 | 0.3676687479019165 | 0.36767011880874634 | 1.3709068298339844e-06 |
| ff.2（各自のFF入力） | -0.37328794598579407 | -0.37328702211380005 | 9.238719940185547e-07 |
| 出力の和 | -0.0056191980838775635 | -0.005616903305053711 | 2.294778823852539e-06 |

符号付き誤差の内訳は、上流残差1.370906830e-6＋上流FF入力が伝わった差9.238719940e-7＋この点の同一入力backend差0＋加算丸めの差0＝2.294778824e-6。固定限界2.112383962e-6を超える。約0.368と−0.373の和が約−0.00562となり、枝に比べて出力が小さいため、この出力に対する限界が厳しくなる。枝の大きさの和/出力絶対値は約131.86倍。閾値変更の根拠にはしない。

FF前残差をさらにblock0/temporal/variateへ分解した数値をupstream-residual-breakdown.jsonへ保存した。現在の結果から「ff.2のバグ」「残差加算のバグ」や「ある1つの上流演算だけが原因」とは断定しない。上流のfloat32演算順・累積差をどこまで参照へ合わせられるかが残る課題である。

## 失敗・資源・保存

診断集計の初回はRust JSONのfloat32最短表現をPython float64のままbytes等価比較し、再構成一致assertが失敗した。読戻しをfloat32へ戻して比較するよう修正し、同じ保存済み出力だけをfresh診断rootで集計し直した。最初の失敗と全stdio/source/exit/closureは保持。モデル/局所kernelの再実行は0。この不具合は元のbinary方式R1比較器にはない。

PyTorch診断は7.294秒・child peak RSS304,250,880B。Rust build/局所演算は5.351秒、監視込みphysical footprint286,624,768B/RSS397,443,072B、子peak RSS4,161,536Bを別々に保存。RSSの定義とsampling値を混同せず、各2GiB・子870/親900秒以内。build cache観測929,981,148Bで1.5GiB内。samplingの短命process捕捉限界を維持する。旧artifact24file/768MiB・単一32MiB、EvidenceStore16MiB等の保存枠も不変。

主要rootはartifacts/rust-r1-ff-fixture-20261016、rust-r1-ff-kernel-20261016、rust-r1-ff-diagnosis2-20261016。失敗はrust-r1-ff-diagnosis-20261016とそのrecordsへ保存。全source/stdio/exit/state/closure、文書前後と旧成果pinはartifacts/rust-r1-ff-results-20261016-evidence。全part/SHAを読戻して閉鎖する。

Mac共通CPUの局所演算比較はpass、元の固定7ケース全体一致は未達のまま。以前の最終予測7case/各6,048要素passを変更せず、R1完了/製品採用とはしない。Windows native/OS依存suite、下流toolchain1.98.1、lockなし解決は未検証。banto-industrial/denroku編集、新取得/外部送信/pushなし。

## 次工程

次は**上流の同一入力での演算順の差**を有限に切り分ける。保存値から第2blockのnorm/attention/FF入力を共通化し、参照と実装の一般的な演算順の相違があるか確認する。特定indexだけの補正、値の置換、許容差拡大、同じfull forwardの反復は行わない。修正根拠が得られた場合にだけ、事前宣言した一般的な修正を行い、元の7ケース全部で確認する。R1未達の間はR2へ進まない。

保全・点検支援第一、学習を含むRustとbanto統合の目的、AI本体banto-ai/利用側責務は維持。需要2015停止・調整2014以前・同休業mean28・四季両側非増加・観測のみ/欠測0評価分離、heartbeat PAUSEDも維持する。
