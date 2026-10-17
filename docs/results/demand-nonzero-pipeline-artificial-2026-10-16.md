# 非ゼロ人工prefixから日次予測までの接続検証

2026-10-16 JST。[事前契約](../research/demand-nonzero-pipeline-artificial-contract-2026-10-16.md)・[Astra確認](../research/demand-nonzero-pipeline-artificial-astra-review-2026-10-16.md)・[決定表](../research/demand-nonzero-pipeline-artificial-decisions-2026-10-16.json)。

**人工prefix8件すべてでconsumer→solverの非ゼロ最適解を確認し、その証明書のβを使う日次予測240件と人工label scenario228件を独立照合した。実データでの学習、実problem内容decode、実2014採点、2015参照・再評価は0。**

前回のconsumer人工25件がすべてβ0だった限定に対し、今回は非ゼロconsumer解から日次bridgeまでを通した。nonzero_pipeline_artificial_ready=trueだけを更新し、fit_ready=false/can_launch_learning=false、heartbeat PAUSEDを維持する。

## 先に固定した人工prefixと解析解

既存10店のID（6,7,10,13,15,17,19,23,26,27）を人工行の識別に使い、数量は全て新規に生成した。固定2013暦21発行日を自Qに分け、全storeのpast56を14日block10/12/14/16、scale10、同休業mean28とした。完全ラベルは営業相当日のbaseline±1、休業相当日は0。正負×四季8primary・計420行出現（input context210を正負で共有しlabelは別）だけで、実データや旧保存consumer問題を使っていない。

old x0=[1,Fraction(binary64 .1),0]とtarget t=±1/10を区別した。Q1の初発行ではpast56に元日が含まれr_iが他行と異なり得るため、全row同zとは仮定せず、R1=Σw r_i、R2=Σw r_i²から

`β*=t R1 x0/(1+R2||x0||²)`

をexact oracleにした。全r_i>0、旧x/元E-I-w-v、label residualとunit、全Pがbaselineとlabelの間にあること、非ゼロ解・週変化係数0を確認した。新consumerのG/q/Cと既存solverのβがoracleと一致し、独立検証で全元hinge/非負・J尺度KKT/gap0を確認した。結果に合わせたlabel/λ/τ/期間の変更や追加探索はしていない。

| 人工state | βの概数（保存値はexact） | dual gap |
|---|---|---:|
| Q1_positive | 0.049597117, 0.0049597117, 0 | 0 |
| Q1_negative | -0.049597117, -0.0049597117, 0 | 0 |
| Q2_positive | 0.049698143, 0.0049698143, 0 | 0 |
| Q2_negative | -0.049698143, -0.0049698143, 0 | 0 |
| Q3_positive | 0.049698143, 0.0049698143, 0 | 0 |
| Q3_negative | -0.049698143, -0.0049698143, 0 | 0 |
| Q4_positive | 0.049698143, 0.0049698143, 0 | 0 |
| Q4_negative | -0.049698143, -0.0049698143, 0 | 0 |

これは共通方向のrank1 fixtureである。ridgeによる一意な非ゼロ最適点の接続検査であり、実学習開始のpool rank3・全削除rank条件や集中開示を緩和しない。四季の学習側平均under/overは同baseline以下だが、未来の実性能や非悪化を保証しない。

## 証明から日次予測への接続

新[connector](../../tools/demand_solved_artificial_bridge.py)はcallerの任意βを受けず、consumerのproblemにboundされたcertificateからだけβを取り出す。独立verifier callbackが証明を検査した後、同じ発行Q・cutoff・usable_fromを持つinput-only payloadを旧bridgeへ投影した。consumer input/compiled/problem/certificate/verification/issue-input/legacy-payloadの全pinを保存・独立突合した。

外側にはartificial_prefix_fit_performed=true、real_fit_performed=falseを記録した。nested legacy fit_performed=falseは『pure bridge component内ではfitしない』という局所flagで、上流の人工prefix solveを否定するものではない。旧consumer/solver/encoder/bridgeのsourceは変更していない。callbackの実装sourceと結果もpinする研究用接続であり、任意のcallbackを信頼できると主張しない。

8stateのprefix/state/solver journalを日次処理前にfreezeし、全240予測を人工issueラベル生成前にfreezeした。閉鎖時も各freeze pinが一致した。予測componentへ評価label・index・reader・path・全train sourceは渡さない。

人工issueは2014-01-01/03-26/04-02/07-02/12-17。uniform/weekday×10店×正負=200予測と、flat/missing/B0/open_zero×同5日×store6×正負=40予測、計240を実行した。01-01/12-25の同休業maskとunknown、営業0/Noneを維持し、03-26は4月のtargetへ跨いでもQ1係数を使った。全target日は2014内で、実2015情報を参照していない。

独立readerはcase名と実origin/store/profile/variantを対応させ、past56の固定生成式を再生成した。weekdayケースは正baselineが2種類以上であること、全Qの正負両方で非均一の日次配分が変化することを明示確認した。配列長・strict bool・finite非負・正scale・曜日別support・dot等長も確認し、zip省略や1==Trueで通さない。

日次分岐は{"baseline_copy": 72, "changed_proportional": 168}。changedはexact比例配分で和P、copyはbaseline exact/displayをそのまま保持し、canonical Bと日次exact和の差を消さない。差のあるcaseは10件として保存した。全encoder数値stateも独立再構築した（記録max_bitsそのものは診断として除外）。floorは今回観測されていない。この固定fixtureで踏まない分岐へ追加stressや係数調整を行わず、floorの一般動作は旧人工bridge検証と分ける。

canonical B≠日次exact和の10件はすべてmissingのbaseline_copyだった。したがって非ゼロsolver解からその丸め差を伴う比例配分への接続も今回未検証で、以前の固定係数bridge試験と区別する。

## 評価labelの分離と負の例

全予測freeze後、store6の60予測へmatching_truth/baseline_truth/open_missing、休業を含む24予測へclosure_missing/closure_positiveも付けた計228scenarioを作った。matching_truthは営業相当日max(baseline±1,0)、休業0という固定人工規則。B0の負数量を避ける処理で、学習ラベルの補完や予測の調整ではない。

各scenarioの観測のみと休業相当Noneだけ0仮定を別に採点した。営業NoneはNone、営業0は観測、休業相当日の正値はそのまま。raw値・両mode actual・日次/数量/総量のloss/supportを全件独立再構築した。人工labelをtrainへ0補完したものではない。

baseline_truthで補正が変わるcaseでは、正補正は過大量、負補正は過小量を増やす反例48セル（case×mode）を保存した。これらを消さず、学習側under/over制約と未来の非悪化を分ける。今回のscenario atom検査は、既存全10店の実四季all/normal・元日ゲートやannual改善判定ではない。

## 検証・資源・保存

起動前Astraレビューで、Q1のr差、binary64 old xとexact targetの区別、局所fit flag、rank1/floor限定、case→input生成式・厳密型/長さ/支持を補強した。全8state/240予測/228labelの名前集合と行数、proof/各pin、解析式、日次・評価lossを照合し、実装側1380check、connector期待拒否12件を記録した。拒否は任意β/issue label/未来/別Q/cutoff/problem・certificate/state pin/input target/proof gap・status改変。期待拒否の入力と理由も保存した。

追加I/O canaryは保存240予測と別の1回で、同一の予測とproofが再現し、builtins.open/Path.open到達0。OS全sandboxや実timeout経路の新試験ではない。

| Mac実行 | 秒 | sampled physical footprint | peak RSS |
|---|---:|---:|---:|
| 人工pipeline | 10.841174 | 38,093,328B | 51,625,984B |
| 独立照合 | 6.319110 | 64,274,984B | 76,382,208B |

各親900/子870秒・sampled footprint/RSS各2GiBの既定内。実行最大366bit、独立最大366bit、形成する整数積/和/比較も8192bit内。solver/encoderのruntime max_bits値自体は独立同値再現の対象外の診断で、独立経路の上限検査と分けた。

artifact 17files/9,983,860B・最大3,056,804B。既定normal24files768MiB/total32files1GiB/single32MiB/failure8files256MiB、EvidenceStore16MiB512files/part256KiB/failure2MiB16files、stdout1MiB/stderr128KiBを拡張していない。全source/人工prefix/input/解析/問題/証明/solver全pivot-round/段階freeze/全日次・label atom/stdioexit/partialfailure/resourceclosureを保存した。

初版独立readerは8stateと23予測の検査後、open_zeroというvariantを含むcase名のsplitを誤りValueError exit1になった。全source/stdioexit/途中progress/failed closureを保持し、[補記](../research/demand-nonzero-pipeline-readback-amendment-2026-10-16.md)に沿ってfresh reader v2でsplit上限3だけを修正した。数学・問題・予測・label・条件は変更せず同じ保存済みrootだけを照合した。追加compile/solve/予測/label生成なし。旧変更/failed/closed roots/source・handoff/index全文を保持した。

Mac Python3.14.8共通の人工接続・独立検証pass、Mac資源観測pass。Windows固有/native・OS依存包括test suiteは未実行として分離する。

## 維持する研究条件と停止

調整2014年以前、自Q共有λ1、元E/I、四季all/normal・元日両modeの平均過小量/過大量・総量MSE非増加、annualMSE厳密改善、同休業mean28と観測のみ/休業相当欠測だけ0仮定の評価分離を維持する。実性能ゲートは今回未評価。人工rank1の成功で実rank/集中条件を緩和しない。

実fit/実problem内容decode/実予測/実2014採点/2015内容参照再評価0、fit_ready=false/can_launch_learning=false、heartbeat PAUSED、PSI採用なし。実適用は既存AND条件と人の新たな明示実学習再開が必要で、この人工検証から自動的に開始しない。

2016–17/予約31–54/販促/正式holdout/CARE/課金API/新データ取得/外部研究データ送信/commit-push/依存lock/Xcode変更なし。

証跡：[実行](../../artifacts/macos-demand-nonzero-pipeline-artificial-20261016-execution-records/root-closed.json)、[全state](../../artifacts/macos-demand-nonzero-pipeline-artificial-20261016/root-closed.json)、[初版独立failed](../../artifacts/macos-demand-nonzero-pipeline-artificial-20261016-readback-records/root-closed.json)、[独立v2](../../artifacts/macos-demand-nonzero-pipeline-artificial-20261016-readback-v2-records/root-closed.json)、[文書閉鎖](../../artifacts/macos-demand-nonzero-pipeline-artificial-20261016-doc-records/root-closed.json)。
