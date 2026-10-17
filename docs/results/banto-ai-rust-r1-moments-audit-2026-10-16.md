# Rust R1 — モーメント計算と丸め位置の照合（2026-10-16）

計画に沿って全7ケース・全7LayerNormの保存入力を照合した。**参照モーメントと参照順のaffineで全124,992出力をビット再現し、モーメント計算とaffineの結合順の違いを分離できた。4レーンWelford/FMAのソース再現は差を94.4974%減らしたが完全一致せず、モデル採用には進めていない**。元の累積1点未達、R1未合格・R2停止は維持する。

## 固定条件・来歴

[数量計算前の条件](../../examples/configs/rust-r1-moments-audit-20261016.json)とdeclaration rootを先に保存した。既存PP入力49組・1,953行/幅64のみ。native_layer_normは49回。既存のbalanced式、前回不採用のserial Flex式、インストール済みPyTorchヘッダーの4レーンWelford/FMAを再構成した。参照モーメントを二種類のaffine順に渡す比較も先に固定した。候補選択、full forward、model変更、学習は0。

インストール済みPyTorch2.14.0の `moments_utils.h` と `vec128_float_neon.h` をpinし、内容を証跡へ保存した。後者のfloat幅は4、fmaddはaarch64のvfmaq_f32を使う。前者は幅64では16回のレーン別更新、初期stackへの統合、4レーンのscalar AddMoments統合を行う。scalarの通常演算は各f32へ丸め、明示fmaddだけsystem fmafで一度丸めた。一つの読み方を固定しており、結果を見た後のFMA有無・lane幅・統合順の変更は0。

普通の乗算と加算はFMAと同じではないことを、(1+2^-23)×(1−2^-23)−1の人工例で確認した。FMAは−2^-46、分離演算は0になる。これだけでモデルの累積差全体の原因をFMAと断定しない。

保存PPとnative出力、保存RPとbalanced再構成、前回保存Flex候補とserial再構成は、それぞれ全49組がbytes一致した。この3系統のanchorを満たしたため、同じ入力に対する以下の成分比較を解釈する。参照や過去rootの更新はない。

## 平均・逆標準偏差の差

各方式の1,953行をnative_layer_normのmean/rstdと比較した。分散はnative APIから直接得られないため、rstdを逆算した値を「参照分散」とはしていない。各方式自身の分散は保存した。

| 方式 | mean不一致行 | rstd不一致行 | mean最大差 | rstd最大差 |
| --- | --- | --- | --- | --- |
| balanced | 1209 | 435 | 2.38418579e-07 | 2.38418579e-07 |
| serial | 1541 | 958 | 4.17232513e-07 | 3.57627869e-07 |
| source_ordered | 260 | 21 | 5.96046448e-08 | 1.1920929e-07 |

## 正規化・affine出力

reference affineは `((x−mean)×rstd)×gamma+beta`、Flex affineは `(x−mean)×(rstd×gamma)+beta`。各普通演算の後でf32へ丸める。nativeモーメントを共通にすると、結合順だけによる差を分離できる。

| 固定経路 | SSE | ビット不一致要素 | 元許容差の超過 |
| --- | --- | --- | --- |
| balanced_reference_affine | 5.55161517168e-10 | 56,578 | 0 |
| serial_flex_affine | 1.55678354613e-09 | 90,873 | 0 |
| source_ordered_reference_affine | 3.0548189263e-11 | 5,827 | 0 |
| native_moments_reference_affine | 0 | 0 | 0 |
| native_moments_flex_affine | 3.27042231083e-10 | 42,216 | 0 |

nativeモーメント＋reference affineは全要素一致、nativeモーメント＋Flex affineは42,216要素でビット差が生じた。モーメント差を含めないaffineの結合順でも差が生じることが確認できた。一方、全経路は局所の元許容差内であり、ビット差の個数をそのままR1超過や予測性能の差と呼ばない。

4レーン/FMAのソース再現はSSEが現行の約0.055026倍となった。ただしmean260行・rstd21行、出力5,827要素がビット一致しない。これを根拠に「参照の演算順を完全再現した」とはしない。compilerのscalar積和縮約やwheelの実行コードとヘッダーの対応は追加確認が必要であり、今回の結果だけでは残差の原因を特定できない。

## 判断と次工程

[次工程の受入条件](../research/rust-r1-moments-admission-2026-10-16.md)を保存した。ソース再構成のSSE減少は診断結果であり、model候補採用条件ではない。scalarの丸め順を複数試して合うものを選ぶことはしない。まず参照build/binaryの証拠を調べ、残差の由来を確定できるか判断する。

学習を含むRust移植には、hostへ値を取り出す今回の診断ループをforwardへ貼り付けられない。計算graphを保つFMAが必要。現在のpin済みBurn公開tensor/backend APIの調査では直接のFMAメソッドを見つけていない。f64乗算＋加算＋f32 castは二重丸めを含み得るため、IEEE f32 FMAの一般的代用品と認定しない。実装方式・forward oracle・将来のbackward条件を別途固定してから接続する。

元R1の7ケース/23anchor/許容差を維持し、これを通過するまでR2学習・保存再開へ進まない。保全・点検第一優先、産業/需要の自作モデル実用性とRust学習目的、需要2015停止・2014以前調整・同休業mean28・四季両側非増加・観測のみ/欠測0評価分離は不変。CARE test再評価・新依存/取得・下流変更・push・製品採用0。

## 資源と記録

| 実行 | 秒 | 監視込みfootprint / RSS |
| --- | --- | --- |
| rust-r1-moments-declaration-20261016-records | 2.106 | 37,078,024 / 61,767,680 B |
| rust-r1-moments-audit-20261016-records | 5.507 | 287,819,144 / 333,660,160 B |

全exit0、親900/子870秒・physical footprint/peak RSS各2GiB以内、cache+targetは967,097,375Bで1.5GiB以内。旧artifact/EvidenceStore/stdio枠を維持。Mac process groupのsample観測でありhard OS capではない。Windows native/OS依存suiteは未実行、heartbeat PAUSED維持。

実行rootは `artifacts/rust-r1-moments-declaration-20261016` と `rust-r1-moments-audit-20261016` および各records。全source/stdio/exit/state/closure・集計・文書前後を `artifacts/rust-r1-moments-results-20261016-evidence` へ保存。NumPy未導入の既存PyTorch警告はstderrへ保持し、インストールや依存変更は行っていない。
