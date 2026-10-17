# TimesFM構造を参考にした小型独自モデルの設計
策定日: 2026-10-13 JST
状態: 設計候補を固定。実装・PyTorch import・学習・モデル評価は未実施。

## 設計の要約

研究仮説は、**他の信号の過去情報へattention経路を開くと、一信号だけから予測する同規模構成より局所的な予測が改善するか**。
最初はMetroPT-3の既存24時間を候補に、3連続値target・60秒間隔・過去128分から次32分を予測する。
これは独立初期化した対象データ学習型モデルの機構研究であり、TimesFM 3の公式学習・重み・汎用zero-shot性能の再現とはしない。
現場の行動と必要時間幅は未確定なので、32分は構造の小規模確認用の設定であり、運用要件ではない。

| 項目 | 初期仕様 |
| --- | --- |
| 入力 | [B,3,128]。tp3、oil_temperature、motor_currentの過去実績のみ |
| 出力 | [B,3,32,3]。p10/p50/p90、各信号の原単位 |
| patch / token | 32点。過去4token＋予測用learned token1 |
| network | 幅64・4heads・2block・FFN幅128、float32、CPU |
| block | pre-LayerNorm→時間causal attention＋residual→pre-LN→系列attention＋residual→pre-LN→FFN＋residual |
| 比較 | 系列attentionをfull対diagonal self-onlyに切替。他の構造・初期state・window列を共通化 |
| 学習 | 独自pinball loss、AdamW、batch8、最大128step、dropout0 |
| 終了 | 工程未成立／局所的追加価値未確認／探索的改善ありを分ける |
| 次のunit | optional環境を固定し、forward・mask・lossの最小実装と未確認の情報境界だけを確認する。学習はまだ開始しない |

## 1. 公開情報との対応と利用条件

Google公式sourceの取得commitは **e51928e27119cb17bebc005be2696b75e0a9e688**。
LICENSEおよびtorchのmodel/configs/dense/transformer/normalization/util/cpm_revin_refineの8fileを、新しい閉鎖root
`artifacts/representative-timesfm-small-design-20261013-source-records`へraw保存した。
各fileのbyte数・SHA-256・URLはsource-pins記録にある。取得sourceは実行・importしていない。
公式モデルsourceは推論用と明記され、今回も公式trainerの公開を確認した証拠にはしない。

| 公開構造 | 本設計での採用 | 独自に変える部分 |
| --- | --- | --- |
| patch入力 | 32点patch | 32→64の単純linear。公式入力residual blockをコピーしない |
| 時間・系列attention | 時間causalと同位置系列attentionを順に適用 | 2block/幅64、標準scaled-dot-product、LayerNorm |
| horizon mask | 未来実績を含まない予測token | horizon32のtoken1個。公式CPM学習recipeの再現とはしない |
| 正規化 | 各系列のcontextから平均・scaleを作る | context-only、固定floor。CPM iterative RevIN/running stats/detrendingを再現しない |
| 分位点 | 複数分位点を出す | 3分位点、順序付きhead、独自pinball loss |
| 学習 | 独立初期化・独立データ | optimizer、sampling、学習量を独自に固定する |

構造確認の一次根拠:
[model.py](https://github.com/google-research/timesfm/blob/e51928e27119cb17bebc005be2696b75e0a9e688/src/timesfm3/torch/model.py)、
[transformer.py](https://github.com/google-research/timesfm/blob/e51928e27119cb17bebc005be2696b75e0a9e688/src/timesfm3/torch/transformer.py)。
Apache-2.0の明示は[固定LICENSE](https://github.com/google-research/timesfm/blob/e51928e27119cb17bebc005be2696b75e0a9e688/LICENSE)と保存source headerで確認。
使用するfile・notice・依存libraryの条件を実装時に対応付ける。独自学習だけで権利適合を保証しない。
既存重み・教師出力・fine-tuningは今回の経路に含めない。重み条件は[先行調査](timesfm3-utility-and-reproduction-2026-10-13.md)を参照する。

## 2. tensor・正規化・未来情報の境界

origin oのcontextは[o-128,o)、labelは[o,o+32)。label tensorはforwardの引数にしない。

1. 各window/系列のcontextだけで平均muとpopulation標準偏差を計算する。
2. scaleはmax(context std, floor_v)。floor_v=max(1e-5 native units,0.01×train-only std_v)とし、train prefixだけから作って固定する。
3. contextを(x-mu)/scaleへ変換し、32点ずつ4patchにする。
4. shared linear32→64でembedding。別のlearned horizon tokenを末尾へ加える。
5. 非学習のsinusoidal位置表現を加え、[B,3,5,64]とする。系列ID embeddingは使わない。
6. 2block→final LayerNorm→horizon tokenのshared linear64→96→[B,3,32,3]。
7. 分位点を同じmu/scaleで原単位へ戻す。

floorの標準偏差もvalidation/testから更新しない。全信号共通scaleは使わない。
maskから先にfutureをゼロ化しただけで漏洩なしとは判定しない。平均・scale・補助特徴量・embedding・attentionまで入力境界を確認する。

時間maskはquery位置qからkey位置kへ k<=qだけ許す。過去tokenはhorizon tokenを見ない。
系列maskは同じpatch位置でfullまたはself-onlyを使う。horizon位置の他系列も実績ではなく、過去から計算した表現だけ。
内部仕様のmaskはtrue=参照可能とする。利用APIのbool maskの意味が逆の場合は明示変換する。
品質不良・nonfinite・欠測を含む必要windowは両構成で同じように除外し、件数と理由を保存する。補間せず、欠測耐性を今回の成果に含めない。

LayerNormはaffineあり・eps=1e-5、attentionは4heads/head幅16、QKのscaleは1/sqrt(16)、projectionにbiasあり。
FFNは64→128→64、GELU、各sublayerにresidual。dropoutは0。位置表現はsin/cos、base10000、position0..4、learned parameterなし。

分位点headのraw(a,b,c)を p50=a、p10=a-softplus(b)、p90=a+softplus(c)へ変換する。
これは独自のparameterizationであり、出力後のsort/clipではない。nonfiniteを補正して成功へしない。順序成立は校正済みという意味ではない。

## 3. 一つの機構比較

fullとself-onlyの2構成だけを比較する。self-onlyでも系列attentionのprojection・LayerNorm・演算形状を残し、maskだけを対角にする。
両者は同じ109,024 parameterを持ち、同じ初期stateから開始する。
これは系列間経路の開閉の比較であり、系列attention sublayerを除いた純粋temporal-onlyモデルとは呼ばない。

self-onlyではsoftmaxが単一keyになりQ/Kの学習への寄与が退化する。登録parameter数の一致を、学習に有効な自由度や勾配の一致とみなさない。
full版の改善からあらゆる多変量モデルの優位性を主張しない。両者の演算形状を揃えるため、この比較からself-onlyの計算節約効果を判定しない。

PyTorch seed20261013で一つの初期stateを作り、両構成へ同じstateを渡す。
linear weightsはXavier uniform/bias0、LN weight1/bias0、horizon tokenはnormal std0.02とする。
batch列は別の固定sampler seed20261014から作り、両者に同じorigin列を渡す。これらは新規設計のseedであり、既存anomaly dev seedとは別物。

## 4. データ候補とsplit

候補は既存の`metropt3-public-2020-02-21`。今回読み取ったのは6つのmetadata fileと観測fileの名前・サイズのみ。
観測本文の読取り、再変換、新dataset生成、登録holdout読取りはしていない。

既存manifestのmetadataは60秒間隔、1440点、chronological train864/validation288/test288。
dataset fingerprintはe6210e4e48e05c025fc8895ddeddf0c53a49dc53fd1c2f49e8c3272a3c7b37b0。
保存fingerprintのobservations SHA-256宣言はd74b53979a051270f045265ccce3a582f3164500f8c7d3a8cf6940ce9a1a5077。
今回その本文hashを再計算していない。将来の読取り時には原manifest対応と品質を確認してから使う。

入力順はtp3(bar)、oil_temperature(ºC)、motor_current(A)。互いの過去を利用し、binary系列や既知将来共変量は初回に追加しない。
sourceのtimezoneは未指定であり、既存transformの研究用UTC仮定を継承する。modeはunknownのまま。
CC BY 4.0と帰属は[既存source manifest](../../datasets/manifests/metropt3-source.json)にある。
故障報告がない区間を正常確認済みとみなさない。[UCI公式説明](https://archive.ics.uci.edu/dataset/791/metropt%2B3%2Bdataset)

| 区分 | originの候補（0始まりsample index） | label境界 |
| --- | --- | --- |
| train | 128..832、stride1、品質除外前705window | 全labelが[0,864)内 |
| validation | 864+32k、k=0..8、品質除外前9origin | 全labelが[864,1152)内 |
| exploratory test | 1152+32k、k=0..8、品質除外前9origin | 全labelが[1152,1440)内 |

validation/testの過去contextが直前splitへ跨ぐことは許す。予測labelがsplitを跨ぐことは許さない。
32点幅の評価labelは重ならないが、contextは重なり、同日・同設備なので独立した運転試行とは数えない。
705train windowから学習回数を増やしても独立データが増えたとはしない。
この24h testは既に先行研究で評価済みである。新たな未使用holdoutや正式確認試験と呼ばず、探索用に限定する。

既存TimesFM評価はcontext120/horizon15・11past covariatesで、今回のcontext128/horizon32・3seriesと異なる。数値を同条件比較に流用しない。
新しい設定でのlast-valueとmoving-average(window15)を安価な点予測基準として設計する。完成済みbenchmarkの再実行はしない。
運用適合性を判断する段階では、別の承認済み日・運転・設備で確認する必要がある。

## 5. 独自学習recipeと評価

- AdamW: lr3e-4、betas(0.9,0.999)、eps1e-8、weight decay0.01、foreach=false/fused=false。schedulerなし。
- gradient clipping: global norm1.0。nonfinite loss/gradientは工程失敗として保存。
- float32、CPU、batch8、data-loader worker0、最大128step/variant、dropout0。
- 有効train originsからreplacement sampling。固定seedのsamplerで128×8=1024提示の共通列を先に作って保存する。epoch数や独立例数と称さない。
- context正規化空間でpinball loss。u=y-qτ、rhoτ(u)=max(τu,(τ-1)u)。B×3target×32lead×3quantileの等重み平均。
- labelはcontextと同じmu/scaleで正規化するが、loss計算側だけが受け取る。mask/token/正規化へ戻さない。

validationはstep32/64/96/128の同じ4時点。checkpoint選択指標は原単位へ逆変換したpinballを固定train-only scale T_v=max(train std_v,1e-5 native units)で割り、origin/target/lead/quantileを等重み平均する。
学習lossのwindowごとのcontext scaleと、checkpoint選択の固定T_vは別にする。

各variantが4候補から個別に最小validation値を選ぶ。同値なら早いstepを選ぶ。結果は同じ探索予算で選んだモデル同士の比較であり、選ばれたstepが同一とは限らない。
testは両方の選択後に一回だけ評価する。testを見てrecipe・checkpointを選び直さない。

出力はtarget別p50 MAE、pinball/WIS、p10–p90 coverage/width、lead別誤差、利用可能origin数、学習・推論時間、OS private peak、選択step。
MAEのA/bar/ºCを平均しない。集約する場合は上記固定T_vで正規化した式を使う。coverageの点数を独立試行数とみなさない。
安価な点baselineとのMAE比較と、2学習構成の確率予測比較を区別する。単一seed・単一日の僅差から勝者・採択・有意差を出さない。

## 6. 資源の机上見積りと有限予算

parameterの計数は独自設計の式によるもので、実装の実測ではない。

| 部分 | parameter数 |
| --- | ---: |
| shared patch linear32→64（biasあり） | 2,112 |
| learned horizon token | 64 |
| 1block: attention2組＋FFN＋LN3組 | 50,240 |
| 2block | 100,480 |
| final LN | 128 |
| shared head64→96（biasあり） | 6,240 |
| 合計（各構成） | 109,024 |

float32のweights/gradient/Adam moments2組のpayload計は1構成1,744,384B、2構成3,488,768B。
入力[B8,V3,C128]は12,288B、1hidden tensor[B8,V3,N5,D64]は30,720B。
1blockのattention-score tensorは時間9,600B、系列5,760B。
全中間tensor・autograd保存・checkpoint copy・optimizer transient・Python/PyTorch runtime・allocator・他writerを含むpeakではない。
机上の小ささを2GiB容量合格の証明へしない。実装時に実parameter数と測定源を対応させる。

将来の小研究全体は既存900秒/OS private2GiB上限内。構成を順に完走させるのでなく同stepをpairで進め、共通128stepを完了できなければ比較はincompleteで閉じる。
設計上は準備/品質120秒、pair学習660秒、validation/test90秒、失敗保全30秒を配分候補とする。何stepを実行できるかは未測定。
checkpointの最大単体32MiB、output合計1GiB、files32を維持。normal24file以内＋failure8fileを計画枠とし、checkpointはstep/variant別の未使用pathへ一回保存する。保存前のbytes/entries確認が必要。
診断EvidenceStoreは既存16MiB/512entry/256KiB part/失敗予備2MiB・16entryを維持する。
checkpoint監視をOS強制停止・全writer coupled capacity/native所有権の証明とみなさない。

## 7. 実装確認と研究の出口

次のunitは学習を開始せず、最小forward/lossと以下の未確認事項だけを小さく確認する。

- loss側future labelを変更しても、同じcontextのforward出力・正規化が変わらない。
- self-onlyでは別系列contextの変更が対象出力へ伝わらない。full経路は固定した小さな例で伝達を確認する。
- 系列の並べ替えと出力の対応、horizon形状、分位点順序、逆正規化、有限なgradientを確認する。
- 実装parameter数と上記の計数、maskのAPI意味を対応させる。

これは新しい構造の情報境界確認であり、完成済みC0/C1/C2テスト・評価・CIを反復するものではない。
optional PyTorch依存はcoreへ持ち込まない。モデル重みの自動取得、追加worker、既存native readerの起動はしない。

Astraは独立して設計を批評し、3target/context-only正規化、同じbatch列、fixed train scaleによる選択、checkpoint選択単位の明記を提案した。self-only対照への変更は親が採用した設計判断であり、最終批評で大きな矛盾なし・計数整合の確認を受けた。

将来の学習結果は次のように閉じる。

1. nonfinite/情報境界違反/予算内共通step未完了: 工程不成立。仮説の否定にしない。
2. fullに追加価値が見えない: この設定で未確認。無制限のgridへ進まない。
3. 探索的改善: targetごとの利点と代償を示す。次は別の承認済み運転区間で確認する。

formal gate=s4_acceptance_not_frozen、formal_permission=false、credit0、登録holdout未読、正式受入未完了、native reader禁止を維持する。
元の144cell・失敗・閉鎖rootは保全する。今回新モデル・学習・テスト・CIは未実施。研究の進捗と正式受入を別に記録する。

## 最小実装の保存（2026-10-13）

上記の次unitは [実装記録](timesfm3-small-model-implementation-2026-10-13.md) で10新確認を一度完了。学習は未開始。次はdataset adapterとtrainerの学習前準備。設計時の次unit記述は履歴として保持する。
