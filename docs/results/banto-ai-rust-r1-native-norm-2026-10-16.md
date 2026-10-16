# Rust R1 — 標準LayerNorm候補は不採用（2026-10-16）

[実装計画](../research/banto-ai-rust-implementation-plan-2026-10-16.md)に沿い、全入力・全LayerNormへ共通に適用できる候補を一つ検証した。**Burn標準LayerNormは同一入力の二乗誤差が全7ケースで増えたため不採用。モデル本体は変更せず、R1は元の累積1点未達のまま**。許容差・weights・参照・Cargo.lock・依存featureを変更していない。

## 先に固定した仮説と判断条件

[固定条件](../../examples/configs/rust-r1-native-norm-20261016.json)とdeclaration rootを候補kernel実行前に保存した。候補は `burn::tensor::module::layer_norm`、epsilon=1e-5、既存Flex CPU/stdのみ。2blockの各3normとfinal_normの全7moduleへ一律に適用する方式であり、特定の店舗・発行日・失敗点を判断材料にしない。

算術上の根拠は、[PyTorchのRowwiseMoments](https://github.com/pytorch/pytorch/blob/v2.14.0/aten/src/ATen/native/cpu/moments_utils.h)と、pin済みBurn0.22.0の標準kernelがWelford方式のモーメント計算を使うこと。既存のbalanced二段階計算から標準operatorへ寄せることで、将来の学習経路と演算境界を共通化できる可能性も検討した。ただし参照はvectorized Welfordとcascade merge、Flexはscalar Welfordで、後者はinv_stdとgammaの積を先に求める。演算順が違うため、安定な方式であることから参照に近いと保証はしない。backwardの正しさは今回は未検証。

固定7ケースの保存済みPython経路入力を各moduleへ与え、候補49回・現行式49回を一度だけ実行した。現行式は保存済みRP出力49組とのbytes一致を必要条件とした。候補は全要素finite・元の2e-6+2e-5×abs(reference)以内、全体SSEの厳密減少、各ケースの全module合計SSE非増加を要求した。通過時だけ一般修正と元7ケースのfull確認を一度許可し、非通過時はモデル変更なしで停止する条件だった。

## 結果

| 項目 | 結果 |
| --- | --- |
| ケース / module / 比較 | 7 / 7 / 49 |
| 比較要素数（各方式） | 124,992 |
| 現行式の保存RPとのbytes一致 | 49 / 49 |
| 候補の許容差超過 | 0 |
| 現行式SSE | 5.55161517168e-10 |
| 候補SSE | 1.55678354613e-09 |
| 候補 / 現行SSE | 2.804199倍 |
| ケース別SSE非増加 | 0 / 7 |
| 採用条件 | 不通過 |

| ケース | 現行式SSE | 候補SSE | 候補/現行 |
| --- | --- | --- | --- |
| train-first | 1.9925003e-10 | 6.2471063e-10 | 3.1353 |
| train-last | 2.1699232e-10 | 5.5989012e-10 | 2.5802 |
| zero | 1.7478922e-11 | 7.5134257e-11 | 4.2986 |
| constant | 1.7478922e-11 | 7.5134257e-11 | 4.2986 |
| floor-below | 3.9378005e-11 | 8.8531759e-11 | 2.2483 |
| floor-equal | 3.2291659e-11 | 6.6691263e-11 | 2.0653 |
| floor-above | 3.2291659e-11 | 6.6691263e-11 | 2.0653 |

SSEは同じ正規化出力の要素別差の平方和である。batch数の異なるケースを単純平均せず全要素集計とケース別を併記した。zeroとconstantなどで値が等しくても独立の追加標本とは数えない。許容差内という結果だけで、より誤差が大きい候補を採用しない。

## 採否・今後の境界

候補は不採用として保存した。モデル本体・標準forwardは実行も変更もしておらず、元の中間値1点が直ったか悪化したかは未評価。既存の最終予測通過・中間値1点未達というR1判定を保持し、R2のRust学習へ進まない。標準operatorが参照に近いという仮説は今回の有限入力では支持されなかった。これをWelford方式一般の劣位や保全性能の悪化に読み替えない。

同一条件のretryや二つ目の候補探索は行わない。次の有益な工程は、参照と現行式のモーメント計算・float32丸め位置のソース上の差を整理し、学習へ接続できる一つの共通方式を選べるか判断する設計レビューである。方式・有限比較・全体採否条件が定まるまでは新kernel/full forwardを起動しない。未達1点への係数調整、参照再生成、許容差緩和は行わない。

保全・点検支援第一優先、TimesFMを参考にした自作モデルの産業/需要実用性、学習を含むRust移植の目的を維持。CARE test/需要2015再評価・実学習・下流repo変更・新依存/取得・Git push・製品採用は0。需要調整2014以前、同休業mean28比較、四季の過小/過大非増加、観測のみ/欠測0評価分離も不変。

## 資源と保存

| 実行 | 秒 | 監視込みfootprint / RSS |
| --- | --- | --- |
| rust-r1-native-norm-format-20261016 | 2.064 | 25,265,280 / 58,408,960 B |
| rust-r1-native-norm-declaration-20261016-records | 1.696 | 36,209,672 / 60,899,328 B |
| rust-r1-native-norm-kernel-20261016-records | 6.683 | 279,465,008 / 403,030,016 B |
| rust-r1-native-norm-comparison-20261016-records | 1.718 | 53,298,184 / 78,020,608 B |

全exit0。親900/子870秒、physical footprintとpeak RSS各2GiB、build cache+target1.5GiB、旧artifact/EvidenceStore/stdio上限を維持。最終cache+targetは967,097,375B。process group観測でcompiler/linkerを含むが、sample間の短命childを完全捕捉するhard OS capではない。Mac CPUでの候補診断のみ、Windows native/OS依存suiteは未実行、heartbeat PAUSED維持。

主要rootは `artifacts/rust-r1-native-norm-declaration-20261016`、`rust-r1-native-norm-kernel-20261016`、`rust-r1-native-norm-comparison-20261016` と各records。全source/stdio/exit/source pin/state/closureと集計・文書前後を `artifacts/rust-r1-native-norm-results-20261016-evidence` に保存。旧closed rootsと失敗を保持した。
