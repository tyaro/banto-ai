# rank3・週変化係数非ゼロの人工pipeline検証

2026-10-16 JST。[事前契約](../research/demand-rank3-pipeline-artificial-contract-2026-10-16.md)・[Astra確認](../research/demand-rank3-pipeline-artificial-astra-review-2026-10-16.md)・[決定表](../research/demand-rank3-pipeline-artificial-decisions-2026-10-16.json)。

**正負×四季の人工8prefixすべてで、罰則なし特徴量rank3と週変化係数を含む全3係数の非ゼロ最適解を確認した。その証明書のβによる日次予測640件と人工label380scenarioを独立照合した。実データ学習・実problem内容decode・実2014採点・2015参照再評価は0。**

rank_three_pipeline_artificial_ready=trueだけを更新する。fit_ready=false/can_launch_learning=false、heartbeat PAUSEDを維持する。人工のrank3は実データの支持・集中・頑健性・性能を保証しない。

## 起動前の人工設計と解析保証

FIT10の位置mod3でhistory A/B/Cを固定割当した。A=10/12/14/16を各14日、B=8/10/12/16を各14日、C=10/12/14を各14日と15/17を各7日。scale10・同休業mean28とし、旧xはA=[1,.1,0]、B=[1,.2,0]、C=[1,.2,.2]（小数はbinary64の値）。固定2013暦21発行日・全10店、正負labelは営業相当日baseline±1・休業0の完全非負。420行出現であり、input context210を正負で共有する。

r_i>0・z_i=r_i*old_x_iを維持し、旧featureの3方向、weighted featureの3行minorと罰則なしweighted Gramの行列式をexactに確認した。Gのridgeによる正定値性でrankを代用していない。Q1の元日除外によるr差・binary64丸めも残した。旧E/I・w=1/(10nE)/v=1/(10nI)、λ1/τ1/20/p32を変更していない。

各zの成分非負・各列の正support・||z||²<4と、一定target t=±1/10を確認した。Cramer oracleから正規方程式と

`||β||²+Σw(z_i·β−t/2)²=t²/4`

をexactに検査した。これにより正tなら全β成分が正、負tなら全負、かつ0とtの厳密な間にz_i·βが入る。全PはBとYの厳密な間で、元の季節平均under/over制約・非負を満たす。既存solverの解はoracleと一致し、独立J尺度KKT・full hinge/非負・dual gap0を確認した。週係数を得るためのlabel/λ/τ/期間の探索・再調整はない。

| 人工state | rank | β0, 水準β, 週変化βの概数 | gap |
|---|---:|---|---:|
| Q1_positive | 3 | 0.0487707528, 0.00775144816, 0.00292376354 | 0 |
| Q1_negative | 3 | -0.0487707528, -0.00775144816, -0.00292376354 | 0 |
| Q2_positive | 3 | 0.0489247359, 0.00777924964, 0.00292753093 | 0 |
| Q2_negative | 3 | -0.0489247359, -0.00777924964, -0.00292753093 | 0 |
| Q3_positive | 3 | 0.0489247359, 0.00777924964, 0.00292753093 | 0 |
| Q3_negative | 3 | -0.0489247359, -0.00777924964, -0.00292753093 | 0 |
| Q4_positive | 3 | 0.0489247359, 0.00777924964, 0.00292753093 | 0 |
| Q4_negative | 3 | -0.0489247359, -0.00777924964, -0.00292753093 | 0 |

正確なβ・minor/Gram/Gの行列式・恒等式・certificateは全stateへ保存した。行列式の数値そのものはexactで、上表のβ表示だけ概数である。rank3はこの人工入力群の代数的な性質で、実学習のrank/全削除/集中/開始AND条件を緩和しない。

全8解は非制約ridge解が既に元制約を満たし、certificateのactive一覧は空だった。制約が最適解を変えるconsumer→solver→日次の接続経路は今回未検証で、以前のsolver単体の境界人工例と区別する。

## 非ゼロ週変化項から日次数量まで

既存consumer/solver/encoder/connector/bridgeは変更せず、新規のfixture/driver/readerで接続を検証した。βは独立証明済みcertificateからだけ取得し、consumer input/compiled/problem/certificate/verification/issue-input/legacy payloadの全pinを照合した。外側synthetic fit true/real fit false、nested fit_performed=falseはpure bridge内でfitしない局所flagという区別も保持した。

8stateとsolver journalを予測前にfreeze、全640予測を評価label生成前にfreezeし、閉鎖時も5つのfreeze file pinsが一致した。人工issueは01-01/03-26/04-02/07-02/12-17の2014年5日。A/B/C×uniform/weekday×10店×正負の600件と、flat/missing/B0/open_zero×同5日×store6/historyA×正負の40件。03-26の4月targetにもQ1の係数を使い、全target日は2014内とした。

全予測で3項の総量寄与を保存し、`weekly_component=unit*z2*β2`と`raw_total_without_weekly=B+unit*(z0β0+z1β1)`の差がraw totalに一致することを確認した。これは同じ予測の代数分解で、β2を0へ差替えて予測し直したものではない。

週寄与が非ゼロだった予測は168件、うちweekday/Cの非均一配分は80件。全Q・両signで確認した。Cの支持された入力では、日次についても`daily_j−baseline_j*without/E=baseline_j*weekly_component/E`がexactに一致した。したがって週係数が非ゼロという確認だけでなく、週項が総量と日次数量へ伝わったことを検証している。

日次分岐は{"baseline_copy": 152, "changed_proportional": 488}。同休業mask/unknown、営業0/None、旧None/B0/r0、baseline exact/display copyとchanged exact比例配分を保持した。canonical Bと日次exact和が異なる10件のうち、changedは0件。floor到達はFalse。到達しなかった分岐へ追加fixtureを探索せず、今回未検証の接続は以前の固定係数bridge検査と分けて扱う。

週寄与168件はpersistent160件とopen_zero8件。canonical B≠Eの10件は全baseline copyで、比例配分488件はすべてB=Eだった。非ゼロ週係数からcanonical差を伴う比例配分への接続も今回未検証である。

## 人工評価・反例と独立検証

全予測freeze後、store6の100予測へmatching_truth/baseline_truth/open_missing、休業を含む40予測へclosure_missing/closure_positiveを追加し、380scenarioを観測のみ/休業相当Noneだけ0仮定の2modeで別に照合した。営業Noneを0へ補完せず、営業0/休業正値を保持した。matching_truthのmax(baseline±1,0)はB0 stressの負数量を避ける固定人工規則で、学習label補完ではない。

baselineが真値のとき補正によるunder/over悪化112セル（case×mode）を保存した。学習側の季節平均制約から将来の非悪化を保証しない。この380scenarioは人工atom検査で、実10店の四季all/normal・元日ゲートやannual改善判定ではない。

独立readerはconsumer/solver/encoder/connector/bridgeをimportせず、元人工prefixから旧x/r/z/full encoder数値state・分母/重み、別determinant実装のCramer/Gram/minor/恒等式、全certificateを再構築した。起動前Astra指摘により、再構築したstate.r_stored→weighted r→z/problemと全ledgerの接続も明示一致させた。case名→origin/store/profile/history/variant→past56生成式、全8/640/380の名前集合と長さ・strict bool・finite非負/正scale/曜日supportも確認した。日次/週分解/全loss-supportが一致し、full state 154,060比較・daily 16,000比較を記録した。

実装2918check・期待拒否16件。任意β/未来label/別Q/各pin/proof等12件に加え、rank1へのcollapse、週列0、週項drop、二重rの4canaryを保存した。4canaryは内部のrank/代数分解検査へ直接不正値を渡したもので、追加学習/予測ではない。C/weekdayによるI/O canary追加1件は保存640件と別に数えた。

## 資源・保存・停止

| Mac実行 | 秒 | sampled physical footprint | peak RSS |
|---|---:|---:|---:|
| 人工rank3 pipeline | 26.746691 | 60,506,640B | 69,566,464B |
| 独立照合 | 14.768375 | 122,798,680B | 129,499,136B |

各親900/子870秒・sampled footprint/RSS各2GiB、形成する整数積/和/比較8192bit・既存solver有限上限を維持。実行最大842bit、独立最大842bit。runtime max_bits値自体の別経路同値再現は主張せず、独立経路の上限検査と区別した。

artifact 17files/24,802,019B・最大11,776,114B。normal24files768MiB/total32files1GiB/single32MiB/failure8files256MiB、EvidenceStore16MiB512files/part256KiB/failure2MiB16files、stdout1MiB/stderr128KiBを拡張していない。全source/人工入力/rank/oracle/問題/証明/solver全pivot-round/週分解/日次/label atom/stdioexit/段階freeze/partialfailure/resourceclosureを保存した。今回各一巡complete、予期しないfailedなし。過去の失敗/source/closed roots/変更と旧handoff/index全文を保持した。

Mac Python3.14.8共通の人工接続・独立照合pass、Mac資源観測pass。Windows固有/native・OS依存包括test suiteは未実行として分離する。I/O canaryは指定関数の到達検査でOS sandboxではなく、実timeout経路の新試験も行っていない。

調整2014以前、自Q共有λ1・元E/I、四季all/normal・元日両modeの平均過小量/過大量と総量MSE非増加、annualMSE厳密改善、同休業mean28・評価mode分離を維持。実四季性能ゲートは今回未評価。実fit/実problem内容decode/実予測/実2014採点/2015内容参照再評価0、fit_ready=false/can_launch_learning=false/heartbeat PAUSED、PSI採用なし。

実適用には既存AND条件と人の新たな明示的実学習再開が必要で、この人工検証から自動起動しない。2016–17/予約31–54/販促/正式holdout/CARE/課金API/新取得/外部研究データ送信/commit-push/依存lock/Xcode変更なし。

証跡：[実行](../../artifacts/macos-demand-rank3-pipeline-artificial-20261016-execution-records/root-closed.json)、[全state](../../artifacts/macos-demand-rank3-pipeline-artificial-20261016/root-closed.json)、[独立](../../artifacts/macos-demand-rank3-pipeline-artificial-20261016-readback-records/root-closed.json)、[文書閉鎖](../../artifacts/macos-demand-rank3-pipeline-artificial-20261016-doc-records/root-closed.json)。
