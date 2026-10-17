# Rust R1 — 初期contextのbit一致、全体候補は1点未達（2026-10-16）

**初期contextの平均・標準偏差・尺度・正規化入力の差を説明し、Rustの通常/自動微分forwardで参照と全bit一致した。ただし既知のLayerNorm修正と合わせた全体候補は389,214要素中1点が元の許容差を超え、不採用としてmodel.rsを元bytesへ戻した。** R1未合格・R2未開始。最終予測だけの通過で中間値条件を変更しない。

## ソースで特定した違い

インストール済みtorchのgit版 `08187d9e0fba026dc8217405802ab5381dc88d90` と同じ公式ソースを取得し、URL・bytes・hashを固定した。タグ名だけで版を推測しない。各ソースはartifacts/rust-r1-context-source-20261016へ保存した。

- CPU meanはfloat32のsum_out後に128で除算する。[ReduceOps.cpp](https://github.com/pytorch/pytorch/blob/08187d9e0fba026dc8217405802ab5381dc88d90/aten/src/ATen/native/ReduceOps.cpp)。
- 連続幅128、NEON4laneでは4ベクトル×各8回の逐次加算を行い、ベクトル4本・lane4個を順に統合する。[SumKernel.cpp](https://github.com/pytorch/pytorch/blob/08187d9e0fba026dc8217405802ab5381dc88d90/aten/src/ATen/native/cpu/SumKernel.cpp)。サイズ8はcascadeの最小level16より小さい。既存Rustの隣接pair treeとは加算順が異なる。
- std_cpuはmeanとは独立にWelfordData<double>を使う。[ReduceOpsKernel.cpp](https://github.com/pytorch/pytorch/blob/08187d9e0fba026dc8217405802ab5381dc88d90/aten/src/ATen/native/cpu/ReduceOpsKernel.cpp)、インストール済みReduce.h/SharedReduceOps.h。各128値行は単一threadの逐次処理で、float64で人口分散とsqrtを計算してからfloat32へ戻す。現行Rustは丸めたfloat32 meanからcentered varianceを計算していた。

これはLayerNormのfloat32/vector Welfordとは別の契約である。今回のfloat64は参照stdが実際に使う型を表現するもので、f32 FMAをf64で代用するものではない。WelfordのC++積和のバイナリ縮約は今回調査しておらず、非縮約のsource表現が固定入力のf32結果を再現した事実までを報告する。

## 事前固定した局所検証

[診断条件](../../examples/configs/rust-r1-context-audit-20261016.json)を閉鎖保存後、既存train先頭/末尾batchとzero/constant/floor前後3caseだけを使った。補助のnative context pipelineを各case1回実行し、元のmean/scale/normalized anchor21組のbytes一致を確認した。元の参照rootは再生成していない。標準偏差のfloor前値だけ補助保存し、全体model forwardやlabel/target読取りは0。

| 確認 | 結果 |
| --- | --- |
| scalarで現行Rustを再現 | 元21anchorのbytes一致 |
| ソース順のmean/raw std/scale | 各63値、全bit一致 |
| ソース順のnormalized context | 8,064値、全bit一致 |
| Rust baseline / plain候補 / Autodiff候補 | 全84比較のbytes一致 |
| Autodiff graph参加・入力不変 | 4出力×7case=28箇所、入力不変 |
| backward・gradient・学習 | 未実行、正しさ未認定 |

Rustの `context::reference_context` は公開tensorのslice/reshape/cast/通常演算だけで表現した。float64 Welfordを含めてgraphを保ち、host読戻し・値の注入・unsafe/private bridgeを使わない。読み出しは診断exampleの出力境界だけ。zeroやfloorを理由に入力を欠測へ変えない。

## 全体の有限候補と採否

[モデル接続条件](../../examples/configs/rust-r1-context-model-20261016.json)をRust実装前に固定した。今回の一般候補は、独立に根拠を得た初期contextと既存のbinary順LayerNormを一律に合わせる1方式だけ。LayerNormだけの過去の不採用候補を再試行したものではなく、当時不変だった上流入力を今回初めて修正した。contextだけの追加full候補や結果に応じた混合は行わなかった。

局所gate後、既存3テストpass、固定7caseの全体forwardを1回実行した。元の23anchor/389,214要素の比較は次の1点が未達。

| 項目 | 値 |
| --- | --- |
| case / tensor / index | train-last / blocks.1 / 183 |
| Python | 0.004164397716522217 |
| Rust候補 | 0.0041619837284088135 |
| 絶対差 | 2.4139881134033203e-6 |
| 元の許容差 | 2.0832879543304442e-6 |
| 合計 | 1 / 389,214要素 |

正規化後/元単位の最終分位点は各6,048値が元許容差内、全caseで有限・分位点順序を維持。しかし全体の元gateは不通過で、候補を採用しない。結果rootはcomplete/parity=false、比較command exit1という科学的負の結果であり、保存失敗ではない。

model.rsはSHA `acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80` へbytes復元した。現在の安定版は旧train-last index3450の累積1点未達で、今回の候補index183と区別する。`reference-normalization` は非defaultでcontext API/診断を公開するだけであり、featureを有効にしても復元後のSmallForecasterの処理は切り替わらない。FMAも研究APIのまま。Cargo.lockと有効package154件の集合は不変、Flex SIMD/rayonを追加せず、依存download0。

## 次の工程

保存済みの今回のtracesでは、context3anchor×7caseはPythonと全bit一致した。その直後のpatchでは両train batchにbit差が残り、初期正規化だけでは消えない差がある。patchはlinearのmatmulとbiasを含む境界であり、この保存結果だけでmatmul・bias・layoutのどれかへ単独帰属しない。prefix35組の候補/旧版のbits・SSEを同結果rootのprefix-comparisons.jsonへ保存した。

次はpatchのlinear境界を出発点に、参照CPU/Flexのmatmul・biasとlayoutのソースを確認し、一般的に直せる差があるか判断する。閉鎖済み55node診断の局所差も再利用し、全層再生や同じmodel候補のfull比較を反復しない。同一operandの有限比較・採否条件が固定できるまでは新kernel/full forwardを起動しない。index183へ合わせる分岐・許容差緩和・参照再生成は禁止。R1通過前にR2学習へ進めない。

保全・点検支援を第一優先とし、自作モデルの産業/需要での実用性、学習とoptimizer保存再開を含むRust移植の目的は維持。CARE test/需要2015再評価、実学習、下流repo変更、push、製品採用0。需要は2014以前調整、同休業mean28、四季過小/過大非増加、観測のみ/欠測0評価分離を維持。heartbeat PAUSED。Windows native/OS依存suiteは今回も未実行でMac共通CPU確認と分ける。

## 資源と保存

親900秒/子870秒、physical footprint・peak RSS各2GiB、build cache+target1.5GiBと旧artifact/EvidenceStore/stdio枠を維持。全単位で上限内、監視込み最大footprint 304,090,232B、RSS系最大 424,476,672B、最終cache+target 1,017,201,968B。process group sampleは短命process等の捕捉限界がありhard OS capではない。全source/stdio/exit/state/closureと文書前後をartifacts/rust-r1-context-results-20261016-evidenceへ保存し、旧roots・失敗・既存変更を保持した。

保存補足: 最終読取りcallerの相対pathエラーと、既存層別診断の抽出に存在しないfamily名linearを指定した空抽出を検出して保持した。前者は絶対path、後者は既存patch/attention_projection/attention_output_projection/ff_linear/headの154nodeを抽出する形へ修正し、artifacts/rust-r1-context-final-integrity2-20261016/prior-linear-diagnosis.jsonへ保存。元のclosed空抽出/失敗rootsを変更せず、数値計算・候補・採否は変更0。補足前後は同名-evidenceへ保存した。
