# 丸め差付き比例配分・floor到達の人工接続検証

2026-10-16 JST。[事前契約](../research/demand-roundfloor-pipeline-artificial-contract-2026-10-16.md)・[Astra確認](../research/demand-roundfloor-pipeline-artificial-astra-review-2026-10-16.md)・[決定表](../research/demand-roundfloor-pipeline-artificial-decisions-2026-10-16.json)。

**前回の制約付き非ゼロ8解を再利用し、新しいcompile/solver/学習を行わず、丸め差B≠Eを伴う比例配分160件とstrict negative rawPからfloorへ到達する80件を独立照合した。全400予測・152人工評価scenarioを保存した。実学習と2015参照再評価は停止を維持している。**

## 係数の再利用と入力

[前回active検証](demand-active-pipeline-artificial-2026-10-16.md)の四季正負8stateを、compiled problem/certificate/独立proof/input bindingsとともにそのまま再利用した。全8stateのrank3・全3係数非ゼロ・正dualの元hinge・KKT/gap0・非制約uからの解変化・Ju<Jc<J0を、旧人工prefixから独立2×2縮約/Cramer/元facet/全encoder数値state/元重みまで再確認した。新consumer compile=0、solver=0、prefix fit=falseであり、両関数の呼出を失敗させるcanaryもcount0だった。

外側artificial_prefix_fit_performed=trueは保存係数の過去の人工fit由来を表す。今回の新fitを意味せず、nested fit_performed=falseもpure bridge内でfitしない局所flagとして保持した。λ1/τ1/20/p32・元E/I/w-v・transforms/scale10・休業仮定・mean28・unknownを変更していない。

Rのpast56は.025/.05/.075/.125各14日、weekdayは各値+weekday/1024。Sは10/12/14/16各14日に、weekdayならweekday/1024も加えた後、全体を2^-20倍した。全ケースは発行前実績だけの人工入力で、結果を見た履歴/scale/係数の探索や再調整はない。Sのrは各profile自身の縮小前履歴と独立一致し、200件を確認した。weekday rがuniformと同じだとは主張しない。

5発行日2014-01-01/03-26/04-02/07-02/12-17×FIT10×正負×2profile×R/Sで400件。全targetは2014内、03-26の4月targetにもQ1を使用した。元日80件はpast14にChristmasがあり旧特徴unsupportedとなるcopy対照で、休日だけを理由に入力数量を0へ書き換えていない。

## 到達した日次分岐

| 固定ケース | 件数 | 独立に確認したこと |
|---|---:|---|
| R・丸め差付き比例配分 | 160 | 両sign・全Q・uniform80/weekday80、B≠E、P>0、delta≠0、exact日次=baseline*P/E・和P |
| S・負rawPのfloor | 80 | positive state・全Q、uniform40/weekday40、r>0/旧特徴有効、rawP<0、P=0、delta=-B、全日次/表示0 |
| S・正総量の対照 | 80 | negative stateでrawP=P>0、比例配分 |
| 元日のcopy対照 | 80 | unsupported、exact/display baselineコピー |

集計分岐は{"baseline_copy": 80, "changed_proportional": 240, "floor_zero": 80}。B=F(math.fsum(baseline))、E=ΣF(baseline)は分けたまま保持し、R全200件でB≠E（copy40件も含む）、うち160件をchanged比例配分まで通した。R/weekday例のB−Eは`1/18014398509481984`。誤ってBを分母にした日次数量・総和が正しいE配分と異なることもexactに検査した。非均一配分は全日次cross-productで照合し、canonical残差と表示丸め差も別保存した。

S/weekday例のrawPは約-0.0666595219、floor後P=0。clip前rawを保存し、strict負値からのfloor到達を確認した。rawP=0の境界そのもの、境界付近の連続性、学習時raw非負制約の将来への保証は今回検証していない。全過去学習行での可行性と、人工issueでrawPが負になってclipする事実を区別する。

既存connector/bridge/consumer/solver/encoderは無変更。certificate由来betaだけを同Q/利用可能cutoffのinput-only bridgeへ渡し、全bindingを確認した。新予測前のreuse/state/source pins、予測後かつlabel前の400件freezeを照合した。rawの週3成分と制約差unit*z·(beta-u)を保存し、raw-unconstrained_rawと一致させた。floor後の日次にはraw差の線形式を適用しない。今回の入力は週特徴0であり、週係数非ゼロ自体は保存stateの性質として再確認した。

## 人工評価・改変拒否・限定

予測freeze後、store6の40予測×3labelと休業あり16予測×2labelで152scenarioを生成し、観測のみ/休業相当Noneだけ0仮定を別々に照合した。営業NoneはNone、営業0・休業正値を保持した。matching_truthは営業相当日max(baseline±1,0)の固定人工stress規則であり、モデル性能の意味ではない。

baseline真値で補正がunder/overを悪化させる64セル（case×mode）も保存した。人工stressの152scenarioは実10店四季ゲートではなく、未来の非悪化/性能改善/PSI採用の認定にはならない。

元12接続改変、保存uへのcert beta差替え、誤B分母・未clip floorの直接canary2の計15拒否を確認した。2直接canaryは内部整合検査であり、新たなfit/forecastではない。I/O canary追加1件は400保存予測と別に数え、指定経路のopen各0・出力一致を確認した（OS sandboxではない）。

独立readerはconsumer/solver/encoder/connector/bridgeをimportせず、旧人工prefixからの8state再証明、新inputの生成式/名前集合/長さ/strict bool/有限非負/正scale/mean28支持、full encoder/r-z、全日次/floor/残差/表示、152label全atomを照合した。full state比較120,700、daily比較10,000、実装check5,198。runtime max_bits値自体の同値再現は主張しない。

## 資源・保存・停止

| Mac実行 | 秒 | sampled physical footprint | peak RSS |
|---|---:|---:|---:|
| 再利用係数→日次人工検証 | 15.208307 | 47,579,688B | 60,260,352B |
| 独立照合 | 12.102172 | 89,997,864B | 112,558,080B |

各親900/子870秒・Mac footprint/RSS各2GiB、整数形成/比較8192bit・元有限上限を維持。新日次実行最大924bit、独立（旧証明再確認を含む）最大924bit。artifact 17files/14,727,372B、最大7,937,250B。normal24files768MiB/total32files1GiB/single32MiB/failure8files256MiB、EvidenceStore16MiB512files/part256KiB/failure2MiB16files、stdout1MiB/stderr128KiBは不変。

全source/reusedstate/pins/input/raw/floor/配分/日次/label/stdioexit/phasefreeze/state/partialfailure/resourceclosureを保存。旧変更/source/failed/closed rootsと旧handoff/index全文を保持した。

Mac Python3.14.8共通人工接続/独立照合・Mac資源観測pass。Windows固有/native・OS依存包括suiteは未実行として分離。実timeout経路の新試験なし。

調整2014以前、自Q共有λ1、四季all/normal・元日両modeの平均under/over・総量MSE非増加、annualMSE厳密改善、同休業mean28/元支持/観測と欠測0仮定の分離を維持。実四季性能ゲートは今回未評価。実problem/quantity/labels内容decode・実fit/solve/予測/2014採点/2015参照再評価0、fit_ready=false/can_launch_learning=false・heartbeat PAUSED・採用なし。実開始AND条件を緩和せず、明示停止解除なしに実学習を起動しない。

2016–17/予約31–54/販促/正式holdout/CARE/課金API/新取得/外部研究データ送信/commit-push/依存lock/Xcode変更なし。

証跡：[実行](../../artifacts/macos-demand-roundfloor-pipeline-artificial-20261016-execution-records/root-closed.json)、[全予測](../../artifacts/macos-demand-roundfloor-pipeline-artificial-20261016/root-closed.json)、[独立](../../artifacts/macos-demand-roundfloor-pipeline-artificial-20261016-readback-records/root-closed.json)、[文書閉鎖](../../artifacts/macos-demand-roundfloor-pipeline-artificial-20261016-doc-records/root-closed.json)。
