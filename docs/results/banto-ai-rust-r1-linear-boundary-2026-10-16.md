# Rust R1 — patchのbias融合と行列積の差を分離（2026-10-16）

**両train batchでは、bias前の行列積はPython/Rustで全bit一致した。patch出力の差は、Pythonのbias込みaddmmとRustのmatmul後加算の違いとして分離できた。単独のbias加算は全7caseでbit一致した。一方、floor境界の人工3caseでは行列積自体に差が残る。** 今回は診断だけでモデルを変更せず、R1は安定版の累積1点未達、R2未開始を維持。

## ソース・版・実行境界

[事前の診断条件](../../examples/configs/rust-r1-linear-boundary-20261016.json)を保存してから演算を開始した。exact installed torch git `08187d9e0fba026dc8217405802ab5381dc88d90` の公式Linear/LinearAlgebra/CPUBlas/BlasKernelを取得・hash保存した。torch2.14.0、CPU capability DEFAULT、BLAS_INFO=accelerate、AT_BUILD_WITH_BLAS=1、MKL/MKLDNNなし。torch threads/interop各1とVECLIB_MAXIMUM_THREADS=1を記録し、その条件でも元のpatch全7anchorをbytes再現した。

[PyTorch Linear.cpp](https://github.com/pytorch/pytorch/blob/08187d9e0fba026dc8217405802ab5381dc88d90/aten/src/ATen/native/Linear.cpp)ではbias付き連続nD入力をflattenしてaddmmへ渡す。[LinearAlgebra.cpp](https://github.com/pytorch/pytorch/blob/08187d9e0fba026dc8217405802ab5381dc88d90/aten/src/ATen/native/LinearAlgebra.cpp)ではbiasを出力へcopyしbeta1でGEMMへ渡す。[CPUBlas.cpp](https://github.com/pytorch/pytorch/blob/08187d9e0fba026dc8217405802ab5381dc88d90/aten/src/ATen/native/CPUBlas.cpp)の今回の型/寸法/BLAS条件はsgemm_分岐に該当する。

libtorch_cpu handleで解決したsgemm_は `/System/Library/Frameworks/Accelerate.framework/Versions/A/Frameworks/vecLib.framework/Versions/A/libBLAS.dylib` の `SGEMM` を指した。これはbuild情報と解決symbolの確認であり、hot-pathをtraceした証明やAccelerate内部の積和順を確定したものではない。解決情報、実dylib SHA、入力/weightのshape・strideを保存した。

現行RustはFlexのgemm0.19.0で出力係数0の積を求め、その後biasを別加算する。Burn標準module::linearのFlex経路もmatmul→addのため、API名を置き換えるだけでは融合しない。registryの該当sourceを結果rootとEvidenceStoreへ保存した。

## 固定7caseの比較

閉鎖済みfixtureのPython経路normalized_contextとpatch weight/biasだけを使用した。全modelやlabelを開かず、Pythonでは各caseのnn.Linear・mm・別bias加算各1回、Rustでは同じoperandのmatmul・自前mmへのbias・保存Python mmへのbias各1回を実行した。元PP patch全7組、既存RP patch全7組、前回context修正候補のpatch全7組がbytes一致したため、再生経路の違いを今回の原因と混同しない。

| ケース群 | bias前matmulのbit差 | 同一mmへの単独bias加算 | Python fused/別加算のbit差 |
| --- | --- | --- | --- |
| train-first（6,144値） | 0 | 0 | 3,619 |
| train-last（6,144値） | 0 | 0 | 3,622 |
| zero・constant（各768値） | 各0 | 各0 | 各0 |
| floor-below/equal/above（各768値） | 各540 | 各0 | 各0 |
| 合計（16,128値） | 1,620 | 0 | 7,241 |

両train batchのpatch差は全てfused/別加算の項に一致し、最大絶対差は先頭4.76837158203125e-7、末尾2.384185791015625e-7。floor3caseはfused/別加算差0で、異なる行数/値域でのmatmul実装差が残る。単独加算の丸めを変更して直す根拠はない。

符号付きの出力差を、全16,128値で次のように分解し、float64差分上で残差0を確認した。

~~~text
Rust自前mm+加算 − Python fused Linear
 = (Rust自前mm+加算 − RustによるPython mm+加算)
 + (RustによるPython mm+加算 − Python mm+加算)
 + (Python mm+加算 − Python fused Linear)
~~~

第1項はmatmul差がbias後へ伝わった差、第2項は同一mmの局所加算差、第3項はPython内のfused/別加算差。SSEは順に1.895100742999034e-11、0、2.6417081699100754e-11、総差4.5368089129091095e-11。今回、非ゼロのケース群が分かれているが、一般に各項SSEを独立の寄与率として加算できるとは扱わない。生の出力/各項とケース別集計を保存した。

局所の全値は元R0許容差内だが、上流の相殺・伝播を含む全体gateの合格を意味しない。前回のblocks.1 index183がbias融合だけで解消するとの因果認定もしていない。

## 次の一般候補の受入条件

[fused linearの設計・有限受入条件](../../examples/configs/rust-r1-fused-linear-admission-20261016.json)を固定した。候補の実装/実行はまだ0。既存pure-Rust gemmで出力をbiasに初期化し、出力係数1・積係数1・read_dst=trueとする1方式を検討する。Mac専用Accelerate FFI、vendor backend、scalar積和順探索、padding、f64行列積、case別switchを追加しない。pure-Rustで同じ参照値を保証できるという意味ではない。

公開backend extensionによりgraphを保ち、rank2のshape/dtype/device-context/stride/boundsを検証する。gemmの公開unsafe pointer APIを呼ぶ必要がある場合は、専用primitive helper内だけに隔離し、入力storageのoffset/strideと全アクセス範囲、出力サイズ、alias不在をchecked arithmeticで証明する。private bridgeやunsafe型変換は使わず、安全性を示せなければkernel前に停止する。標準Burn linearへ単に置換する候補は起動しない。

既存gemmを直接参照する場合はoptional exact0.19.0/default-features=falseだけを追加し、既存package/version集合と有効featureを維持する。Cargo.lockのroot依存edge変更は実装前snapshotとoffline一回のrefreshを前提に検査し、registry/他依存versionは変更しない。今回のCargo.toml/Cargo.lockは不変。

実装時は固定8人工caseの独立期待値・graph/入力不変・拒否条件を先に保存して検証する。その後、閉鎖済みPP/RPを使い、新候補だけを全154linear（patch7、attention projection84、output projection28、FF28、head7）へ一度適用する。旧baseline/55node全層再生はしない。全finite/元許容差内、全体SSE厳密減少、各case合計SSE非増加が局所採用条件。

全局所gateを通った場合だけ、全linearと既知のcontext/LayerNorm補正を一律接続し、既存3テスト→元固定7case/389,214要素の全体比較を1回行う。全体未達ならmodel元bytesへ復元し、局所passだけでR1通過へ変えない。backwardは実装・compile・graph参加と数値確認を分け、R2設計前に実行/認定しない。

## 状態・保護・OS分離

model.rsはSHA `acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80` のまま。許容差・参照・weights・Cargo.lock/default不変、既存変更/失敗/closed roots保護。今回のRust診断exampleはcompile/run成功。モデルを変えていないため既存3テストの無目的な再実行やfull forwardは行わなかった。

この結果はMacの共通Flex診断とMac参照BLASの来歴確認である。Windows native/Windowsサービス/OS依存suiteは未実行であり、Macからの移植成立を認定しない。今回の候補にMac専用bindingを導入していない。

保全・点検支援第一、自作モデルの産業/需要での実用性、Rustでの学習・optimizer保存再開の目的を維持。CARE test/需要2015再評価・学習・下流編集・push・製品採用0。需要は2014以前だけ調整、同休業mean28、四季平均の過小/過大非増加、観測のみ/欠測0評価分離。heartbeat PAUSED。

親900/子870秒、各2GiB、build cache+target1.5GiBと旧artifact/EvidenceStore/stdio枠を維持。最大監視込みfootprint 288,410,672B、最大RSS系指標 386,383,872B、最終cache+target 1,025,959,491B。process group sampleの捕捉限界はありhard OS capではない。全source/stdio/exit/state/closure・文書前後はartifacts/rust-r1-linear-results-20261016-evidenceへ保存。
