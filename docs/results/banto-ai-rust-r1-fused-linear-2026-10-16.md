# Rust R1 — pure-Rust fused linear候補は改善なしで不採用（2026-10-16）

**fused linearを公開backend extensionで実装し、独立人工8caseの通常/Autodiff forward、graph参加、13拒否条件を通過した。一方、保存済み154linearの465,696値は現行baselineと全bit一致し、参照との差が減らなかった。事前条件のSSE厳密減少を満たさず不採用とし、モデル全体の再実行は0。** model.rs/default/許容差は不変、R1は安定版の累積1点未達、R2未開始。

## 先に固定した方式と保護

[受入条件](../../examples/configs/rust-r1-fused-linear-admission-20261016.json)を維持し、実装・依存変更より前に `artifacts/rust-r1-fused-linear-declaration-20261016` へ元model/lib/Cargo.toml/Cargo.lock、既存rootsのclosure、独立人工fixtureを保存した。fixtureはPython Fractionで計算したexact integer/dyadic結果がfloat32で厳密表現できることを検査している。Rustの候補出力を見て期待値や計算順を変えていない。

候補は既存gemm0.19.0の同じfloat32/stride/orientation/Parallelism::Noneで、全出力を行broadcast biasへ初期化しread_dst=true・出力係数1・積係数1とした1方式。高水準APIは公開reshape/dispatchだけでgraphを保つ。新backend、Accelerate FFI、padding、f64 matmul、packing調整、scalar-dot代替、ケース/点別switchは0。

`fused-linear-extension` は非defaultで既存fma-extensionとoptional gemmを有効にする。gemmの直接依存はexact0.19.0/default-features=false。offline lock refreshは一度、Cargo.lockの差はbanto-ai root依存に既存gemm edgeが1本増えた箇所だけ。全package/version集合154と有効dependency feature集合は前後で同一、SIMD/rayon/vendor機能追加やdownloadはない。元のlock bytesも閉鎖保存した。

## 実装と安全性

[安全性の説明](../research/rust-fused-linear-safety-2026-10-16.md)とcode内SAFETYをGEMM前に保存した。rank/dtype/shape/device/autodiff/checkpointを検査し、m1..120/k1..128/n1..128に制限する。primitive側でも検査し、公開storage/layoutから非負strideとstart offsetを読み、全index/byte最大値をchecked arithmeticで証明してからpointerを作る。weightをcontiguousへ変換して別の算術候補にしない。

出力は独立した新規allocationで、全m×n値をbias初期化してからread_dstを許可する。immutable input同士の共有は読取りだけ、出力は他とaliasせず、連続strideは一意に書く。unsafeはこの検査後の公開gemm呼出し1箇所に隔離し、private bridge/表現変換は使わない。範囲・負stride・非有限はGEMM前に拒否し、overflowなど非有限出力も拒否する。

Autodiffは三parent guardをchild登録まで保持し、x/weightをstateへ残す。dx=dY@W.T、dW=x.T@dY、db=sum_rows(dY)のコードは既存backend演算でcompile済み。**今回確認したのはforwardとgraph参加で、backward・gradient・optimizerの数値正しさは未実行/未認定**。

## 人工確認

| 項目 | 結果 |
| --- | --- |
| ordinary / zero input / zero weight / mixed sign / broadcast / transposed weight / offset input / dyadic | 固定8case |
| plain・Autodiff | 各37値、合計74値の期待bits一致 |
| 親がxだけ/weightだけ/biasだけ | 各経路でgraph参加と期待bits一致 |
| rank4 wrapper・入力/weight/bias不変 | 確認 |
| shape・bias長・empty・dtype・context・m/k/n上限 | 8拒否 |
| input/weight/bias非有限、出力overflow、weight負stride | 5拒否 |
| backward呼出し | 0 |

拒否5件のkernel panicはcatchした意図的境界試験であり、stderrへ保持した。probe自体はexit0。compile失敗や科学的retryはなく、同じfixture1回の判定で完了した。

## 保存済み全154linearの局所比較

人工gate後、新候補だけをpatch7、attention projection84、output projection28、FF28、head7へ各1回適用した。入力は閉鎖済みPPの発行/時点を持つ既存値、比較先は同じ閉鎖済みPPとRP。旧baselineのkernelや55node全層再生を再実行していない。variate q/k/vは既存sourceと同じseries/time入替え、weight transposeのstrideも維持した。

| 判定 | 結果 |
| --- | --- |
| 比較 | 154組 / 465,696値 |
| 候補と現行RPのbytes一致 | 154 / 154組 |
| 元許容差の超過・非有限 | 0 |
| baseline SSE | 2.0614229837078294e-09 |
| candidate SSE | 2.0614229837078294e-09 |
| 各caseの合計SSE非増加 | 7 / 7 |
| 合計SSEの厳密減少 | **なし、不採用** |

- train-first: baseline=candidate SSE 8.0794938479687012e-10。
- train-last: baseline=candidate SSE 8.0311978489473029e-10。
- zero: baseline=candidate SSE 9.2671668254359029e-11。
- constant: baseline=candidate SSE 9.2671668254359029e-11。
- floor-below: baseline=candidate SSE 8.9794057317862572e-11。
- floor-equal: baseline=candidate SSE 8.760821009482422e-11。
- floor-above: baseline=candidate SSE 8.760821009482422e-11。

全154組が現行bytesと同じなので、train patchで見つけた7,241値のfused/別加算差も、人工floorのmatmul差も今回の方式では減っていない。局所の許容差内だけを採用理由にせず、事前の厳密改善条件を維持した。比較結果rootはcomplete/local_gate=false、commandは科学的負の結果を示すexit1として保存した。

## 改善しなかった理由と次工程

gemm-common0.19.0のreal microkernel sourceでは、積のaccumulatorをゼロで開始し、Kループを終えてからdestinationを組み込むepilogueを持つ。alpha_status1のscalar経路は `scalar_mul_add(beta, accumulated_product, old_destination)`、vector経路も同様。今回はbeta1なので、既に丸められた積へのbiasの最終加算となり得る。GEMMのdestinationへbiasを渡すAPIと、積の累積中にbiasを保持する計算順は同義ではない。

該当sourceの行番号/hash/原文を結果rootのgemm-epilogue-source.jsonへ保存した。今回の実行でどのmicrokernel命令を通ったかはtraceしておらず、これだけで全backend/寸法のbit同一性を証明したとはしない。固定154組が同一だった事実と、それを説明するsource上の順序を分けて報告する。

この候補のkernel/全体を反復せず、モデルhookを置かない。primitiveは非defaultの研究APIとして保持する。次は参照SGEMMのbias統合位置とサイズ依存経路を読取り監査する条件を固定する。実際にloadされたsymbolと対象範囲/byte上限を先に決め、一般方式を支持する根拠が得られるまで別の丸め順・bias-first scalar候補・vendor FFIを起動しない。単独加算の置換や、既読の失敗1点に合わせた調整も行わない。

## 現在の状態と資源・OS分離

model.rsは宣言前とbytes同一、SHA acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80。全体7case・既存baseline・学習/CARE test/需要2015再評価は0。今回の局所gateが不通過のため、全体接続後の既存3テスト工程へも進めていない。過去の既存3テストpassを今回の再実行とは扱わない。R1未達/R2停止、許容差・参照・weights/defaultは維持。

保全・点検支援第一、自作モデルの産業/需要での実用性、Rustでの学習/optimizer保存再開の目的を維持。需要は2014以前だけ調整、同休業mean28、四季平均の過小/過大非増加、観測のみ/欠測0分離。下流編集・Git push・製品採用0、heartbeat PAUSED。新primitiveはOS専用bindingを含まないが実行確認はMacのみ、Windows native/OS依存suiteは別途未実行。

全単位が親900/子870秒、physical footprint・peak RSS各2GiB、build cache+target1.5GiBと旧artifact/EvidenceStore/stdio枠内。最大監視込みfootprint 305,433,672B、最大RSS系 416,432,128B、最終cache+target 1,037,488,009B。process group sampleには短命process等の捕捉限界がありhard OS capではない。全source/stdio/exit/state/closure、独立fixture、依存前後、source説明、集計と文書前後をartifacts/rust-r1-fused-linear-results-20261016-evidenceへ保存し、旧成果/失敗/closed rootsを保持した。
