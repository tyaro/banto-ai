# Rust R1 — CPUテスト通過、数値比較は中間値1点で未達（2026-10-16）

[実装計画](../research/banto-ai-rust-implementation-plan-2026-10-16.md)に沿ってR1a/R1bを実行。**CPU buildと3テストは通過。最終予測は7ケースとも許容差内だが、中間値1点が超過しR1全体は未合格**。R2学習へ進まない。保全・点検支援を第一優先とし、banto-ai内で学習・推論・保存再開をRust化する目的は維持する。

## 容量変更と既存成果の保護

人の「容量上限を必要な範囲で見直して…」の指示を受け、[ビルド専用予算](../../examples/configs/rust-r1-build-budget-20261016-r1.json)を実行前に保存。前回の479,959,378B依存cache＋326,020,247B未完targetを維持し、残りの依存・テスト/exampleリンクと一時出力のため、合計上限を768MiBから**1.5GiB**へ変更した。最終regular file合計は921,252,730B（約878.6MiB）。この上限分を事前確保したわけではない。

親900秒/子870秒、メモリ各2GiB、jobs1/CPU threads1、通常artifact24file/768MiB・単一32MiB、EvidenceStore16MiB/512file/part256KiBと失敗reserve等は据え置いた。旧source/失敗/closed rootsを保持し、cacheの手動削除・移動、新依存取得、push、下流repo変更なし。offline/locked/native Rust1.95.0で実行。Cargo.lockのSHAは既存inventoryと一致。

## ビルドとテスト

`cargo test -p banto-ai --locked --offline --all-targets --features reference-tests -- --test-threads=1` を実行し、修正後も3テスト成功。

| テスト | 確認内容 |
| --- | --- |
| input | 観測0を保持、非有限/欠測・batch/shape不正を拒否 |
| temporal_query | 将来queryの変更が過去token出力へ影響しない |
| neutral_integrity | 固定参照を読込み、不正hash/shape/重複/offset overflow/NaN/noncausal mask/末尾byteを拒否 |

predict exampleもbuild・link後に実行。crateはprepared finite contextだけを受け、実タグのquality/時刻や利用可能時刻の検査は将来adapter/consumerの責務として残る。loaderはpinned CARE neutral参照用で、製品package/optimizer再開は未実装。TensorData::to_vecのdeprecated警告が1種あり、エラーではない。

## 固定した7ケースの比較

既存fold0 modelとtrain先頭/末尾各B8、人工zero/constant/floor-below/equal/aboveを使用。Python参照は再生成せず、test/validation/calibration/truthは開かない。新Rust forwardは修正前後7ずつ、計14ケース。モデル学習・性能再評価は0。

| 判定 | 修正前 | ペア加算への修正後 |
| --- | --- | --- |
| case / named tensor比較 | 7 / 161 | 7 / 161 |
| 全要素 | 389,214 | 389,214 |
| 許容差超過 | 114 | **1** |
| 正規化後の最終分位点 | 1点超過 | 全6,048要素pass |
| 元単位の最終分位点 | 全6,048要素pass | 全6,048要素pass |
| 全体gate | fail | **fail** |

元単位出力の最大error/許容限界比は0.011307481、正規化後出力は0.585107130。全出力finite・分位点順序成立。R0の中間値条件 `abs(diff)<=2e-6+2e-5*abs(ref)` と元単位条件は変更していない。合格した最終出力だけを根拠に中間値gateを外さない。q50/context_centerを需要平均として使わない。

## 数値修正の根拠と残差

初回はtrain2caseのblock0出力から超過し、人工5caseは通過。保存値だけの診断で、Flex scalar sumの逐次float32加算によるcontext標準偏差の誤差を確認した。独立した高精度momentをfloat32へ丸めた値に対するscale絶対誤差の総和は、Python参照0、旧Rust7.691141e-5、ペア加算3.352761e-8。これは丸め誤差の一因を支持するが、残り全ての差の単独原因という証明ではない。

原因・修正仮説・停止条件を先に保存し、context128とLayerNorm64のmean/varianceをbalanced pairwise float32加算へ変更した。重み・dtype・分散の式・eps・モデル構成・許容差は不変、Burn tensor操作のままでhost処理へ迂回せず、将来のgradient経路を残した。ただしbackward一致はR2で未検証。

残る超過はtrain-firstの `blocks.1` shape[8,3,5,64]、flatten index4359＝[batch4,series1,token3,dim7]（0始まり）。

| 値 | 数値 |
| --- | --- |
| Python | -0.0056191980838775635 |
| Rust | -0.005616903305053711 |
| 絶対差 | 2.294778823852539e-06 |
| 固定許容限界 | 2.112383961677551e-06 |
| 差/限界 | 1.086345506 |

このcaseで最初に条件を超えるのは第2blockの出力段階。先行する保存済みLayerNorm/attention/GELU出力は条件内だが、途中の差が累積し得る。線形演算・残差加算のどちらが決定的かは現時点では未分離であり、特定backendの不具合や物理的意味を断定しない。事前宣言どおり、残差に合わせる追加算術探索や許容差拡大は行わず終了した。

## 資源・OS・保存

| 実行単位 | 秒 | 監視込みfootprint最大B | 監視込みRSS最大B | exit |
| --- | --- | --- | --- | --- |
| rust-r1-tests2-20261016 | 123.618 | 744,835,400 | 692,011,008 | 0 |
| rust-r1-predict-20261016-records | 6.758 | 283,495,472 | 398,442,496 | 0 |
| rust-r1-tests3-20261016 | 8.586 | 288,345,208 | 432,537,600 | 0 |
| rust-r1-predict2-20261016-records | 6.029 | 284,724,344 | 374,161,408 | 0 |

全単位で子870秒と各2GiB内。Rust wrapperはCargo/compiler/linker/build-scriptの同process groupを監視し、測定間隔とshort-lived childの捕捉限界を保存。samplingでありhard OS capではない。Mac共通CPU build/テストpass、R1bの全体一致fail。Windows native・OS依存包括suiteと製品側toolchain1.98.1は未実行。下流のlockなし解決に残るyanked任意依存の問題も未解決で、配布成立とはしない。

主要保存先は artifacts/rust-r1-tests3-20261016、rust-r1-burn-predictions2-20261016、rust-r1-compare2-20261016。修正前のcompareは有効な負の結果としてcomplete、対応するcommand記録はexit1/failedを保つ。旧容量超過もfailedのまま。全source/stdio/exit/state/closure、文書前後、全比較と残差、元参照のpinは artifacts/rust-r1-results-20261016-evidence に保存。

次の工程は**R1bの残差1点の演算切り分け**。先に固定する診断は保存済み第2block入力/重みを用い、共通入力でff.2線形出力と残差和を別々に比較し、上流誤差の伝播と演算自身の丸めを区別するものとする。変更理由が得られるまで新しいfull forward/再試行・学習へ進まない。R1a済みをもってR2/CARE再学習/製品利用へ移らない。

保全第一・学習を含むRust移植、AI本体banto-ai/利用側banto-industrialとdenroku-psi-demoの責務を維持。需要2015停止・調整2014以前・同休業mean28・四季両側非増加・観測のみ/欠測0評価分離、heartbeat PAUSEDも不変。
