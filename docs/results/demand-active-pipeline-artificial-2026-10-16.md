# 制約が非ゼロ解を変える人工pipeline検証

2026-10-16 JST。[事前契約](../research/demand-active-pipeline-artificial-contract-2026-10-16.md)・[Astra確認](../research/demand-active-pipeline-artificial-astra-review-2026-10-16.md)・[決定表](../research/demand-active-pipeline-artificial-decisions-2026-10-16.json)。

**四季×正負の人工8prefixすべてで、非制約ridge解が元の過小・過大量制約を厳密に違反し、制約によって異なる非ゼロ最適解になることを確認した。全8解はrank3・週変化係数も非ゼロ、正dualのactive hingeと独立KKT/gap0を持つ。consumer→solver→日次640件の接続を独立照合した。**

実データ学習・実problem/実ラベル内容decode・実2014採点・2015参照再評価は0。active_constraint_pipeline_artificial_ready=trueだけを今回の接続状態として追加し、fit_ready=false/can_launch_learning=false・heartbeat PAUSEDを維持する。実性能や将来非悪化の認定ではない。

## 人工prefixと制約が解を変えた証拠

前回のA/B/C past56、FIT位置mod3、固定2013暦21日、自Q、scale10・同休業mean28を保持した。A=10/12/14/16各14日、B=8/10/12/16各14日、C=10/12/14各14日+15/17各7日。人工学習labelをAだけbaselineそのまま、B/Cを営業相当日baseline±1・休業0へ固定した。target A=0、B/C=±1/10。420行出現・input context210の正負共有。実店舗を分類する設計ではない。探索や結果に合わせたlabel/λ/期間変更はない。

旧x=[1,.1,0]/[1,.2,0]/[1,.2,.2]はbinary64の値を厳密に保持。r>0・z=r*oldx、Q1元日除外によるr差、元E/I/w-v・λ1・τ1/20・p32を保持した。3行minorと罰則なしGram行列式>0でrank3を確認し、ridgeの正定値性をrankの代用にしなかった。

s=±1、n=s*[1,binary64(.1),0]、u=G^-1rhs、v=G^-1n、a=(n·u)/(n·v)、beta=u-a*vをchecked Cramerで構成。n·u>0・a>0、n·beta=0を確認した。非制約uは正ケースでover、負ケースでunderを元baselineより増やす。制約解はAのP=B、B/CのPがBとYの厳密な間となり、全P非負・元full hinge両側非増加を満たした。

solve前に全Aを選ぶ元hinge facet・正dual・J尺度stationarityと`J(u)<J(beta)<J(0)`、`J(beta)-J(u)=a²*(n·v)>0`をpresolve-witnessesへ永続保存した。実際のsolverを各1回呼び、同じbeta、正dualのactive hinge、独立full hinge/非負/KKT/gap0を確認した。active数は[1, 1, 1, 1, 1, 1, 1, 1]。これにより、制約を加えても解が同じだった前回との差を明示できる。

| 人工state | 非制約βの概数 | 制約付きβの概数 | gap |
|---|---|---|---:|
| Q1_positive | 0.0278225136, 0.00654381628, 0.00394734444 | -0.000491157922, 0.00491157922, 0.00533081793 | 0 |
| Q1_negative | -0.0278225136, -0.00654381628, -0.00394734444 | 0.000491157922, -0.00491157922, -0.00533081793 | 0 |
| Q2_positive | 0.0278905151, 0.00660845291, 0.00400242307 | -0.00050280376, 0.0050280376, 0.00545338031 | 0 |
| Q2_negative | -0.0278905151, -0.00660845291, -0.00400242307 | 0.00050280376, -0.0050280376, -0.00545338031 | 0 |
| Q3_positive | 0.0278905151, 0.00660845291, 0.00400242307 | -0.00050280376, 0.0050280376, 0.00545338031 | 0 |
| Q3_negative | -0.0278905151, -0.00660845291, -0.00400242307 | 0.00050280376, -0.0050280376, -0.00545338031 | 0 |
| Q4_positive | 0.0278905151, 0.00660845291, 0.00400242307 | -0.00050280376, 0.0050280376, 0.00545338031 | 0 |
| Q4_negative | -0.0278905151, -0.00660845291, -0.00400242307 | 0.00050280376, -0.0050280376, -0.00545338031 | 0 |

正確なbeta・Gram/minor・facet/dual・目的値・制約差は各stateに保存し、上表だけ概数とした。独立readerはA平面上の2×2縮約を解く別経路でbetaを求め、producerの3×3射影と一致させた。さらに別determinant、元facetと目的関数の残差和表示、全certificateから保存証拠を再構築した。実のrank/集中/全削除/開始AND条件は緩和していない。

## 日次予測までの接続

既存consumer/solver/encoder/connector/bridgeは無変更。独立証明済みcertificateのbetaだけをinput-only旧bridgeへ渡し、consumer input/compiled/problem/cert/proof/issue/legacy pinsを全確認した。外側synthetic fit=true/real fit=false、nested fit_performed=falseはpure bridge内でfitしない局所flagとして保持した。

8state・prefix・solver journal・presolve witnessesを日次前にfreezeし、全640予測を評価label生成前にfreezeした。人工発行日は2014-01-01/03-26/04-02/07-02/12-17。A/B/C×uniform/weekday×10店×正負の600件と、flat/missing/B0/open_zero×同5日×store6/historyA×正負の40件。03-26は4月targetまでQ1を使い、全targetが2014内である。

各予測で`unconstrained_raw=B+unit*z·u`、`constraint_shift=unit*z·(beta-u)`を保存し、raw総量との差と一致させた。制約の効果が非ゼロの488件、日次まで差を独立照合できた488件を全Q・両signで確認した。内訳は比例配分が変わる368件とbaseline copyへ戻る120件。これは同じ入力に対する代数式の比較で、uをconnectorへ差し替えた追加予測ではない。日次差の式はB=E・両raw非負の適格入力で`candidate_j-baseline_j*unconstrained_raw/E=baseline_j*constraint_shift/E`。

週変化項の分解も保持し、非ゼロ寄与168件（persistent160+open_zero8）、非均一weekday/Cの80件を全Q・両signで日次まで確認した。日次分岐は{"baseline_copy": 272, "changed_proportional": 368}。floor到達False、B≠Eの10件のうちchanged0件。未到達経路を今回の検証済みに含めない。

同休業mask/unknown、営業0/None、旧None/B0/r0、canonical Bとexact和E、copy/比例配分を保持。任意beta・issue label/未来・別Q/cutoff・problem/cert/state/target/proof等の元12改変、rank1/週列0/drop週/二重rの4直接canary、新たなunconstrained beta差替えの計17拒否。独立readerでも差替えpayloadが保存uと一致し通常betaと違うことを確認した。I/O canary追加1件は640件に含めず、指定関数経路でopen各0・出力一致を確認した。

## 人工評価と限界

予測freeze後に380scenarioを生成し、観測のみと休業相当Noneだけ0仮定を別々に照合した。営業NoneはNone、営業0・休業正値は保持する。matching_truthは人工stress label名であり、A群の学習labelと異なり全営業相当日max(baseline±1,0)とする。学習labelの補完や「予測が真値に一致する」との主張ではない。

baselineが真値なら補正でunder/overが悪化する88セル（case×mode）も保存した。学習側の制約は将来の非悪化を保証しない。380scenarioは人工atom確認であり、実10店の四季all/normal・元日両mode性能ゲートやannual改善の実施ではない。

独立readerはconsumer/solver/encoder/connector/bridgeをimportせず、全raw人工history→full encoder/r→z/problem/ledgerを再構築し、元分母/重み・名前集合/長さ/strict bool・有限非負/正scale/曜日support・証明・日次・週/制約寄与・両mode lossを照合した。full state比較154,060、daily比較16,000、実装check10,495。Astraの起動前指摘による新canary入力の独立照合も反映し、最終確認を保存した。

## 資源・保存・停止

| Mac実行 | 秒 | sampled physical footprint | peak RSS |
|---|---:|---:|---:|
| 人工active pipeline | 28.030997 | 60,490,256B | 70,402,048B |
| 独立照合 | 15.268773 | 117,490,264B | 128,385,024B |

各親900/子870秒、Mac footprint/RSS各2GiB、整数形成/比較8192bitと既存solver有限上限を維持。実行最大995bit・独立最大829bit、runtime max_bits値自体の別経路同値再現は主張しない。artifact 18files/23,225,803B・最大10,977,686B。normal24files768MiB/total32files1GiB/single32MiB/failure8files256MiB、EvidenceStore16MiB512files/part256KiB/failure2MiB16files、stdout1MiB/stderr128KiBを拡張していない。

全source/prefix/encoder/rank/oracle/presolve/facet/問題/cert/全pivot-round/state/週制約分解/日次/評価/stdioexit/freeze/partialfailure/resourceclosure保存。実行・独立照合はそれぞれ一巡complete。文書準備の構文確認では非ASCII bytes literalによりexit1となり、起動前にUnicode string.encode()へ修正した。旧準備sourceと失敗記録を別ファイルで保護し、人工学習・予測の再実行はない。既存変更/source/failed/closed rootsと旧handoff/index全文を保持した。

Mac Python3.14.8共通人工接続・独立照合pass、Mac資源観測pass。Windows固有/native・OS依存包括suiteは未実行として分離。I/O canaryはOS sandboxではなく、実timeout経路の新試験もしていない。

調整2014以前、自Q共有λ1、四季all/normal・元日両modeの平均under/over・総量MSE非増加、annualMSE厳密改善、同休業mean28・元支持・評価mode分離は不変。実四季性能ゲートは今回未評価。実fit/solve/予測/2014採点/2015参照再評価0、fit_ready=false/can_launch_learning=false・heartbeat PAUSED・PSI採用なし。実学習には既存AND条件と人の明示的な停止解除が必要で、自動起動しない。

2016–17/予約31–54/販促/正式holdout/CARE/課金API/新取得/外部研究データ送信/commit-push/依存lock/Xcode変更なし。

証跡：[実行](../../artifacts/macos-demand-active-pipeline-artificial-20261016-execution-records/root-closed.json)、[全state](../../artifacts/macos-demand-active-pipeline-artificial-20261016/root-closed.json)、[独立](../../artifacts/macos-demand-active-pipeline-artificial-20261016-readback-records/root-closed.json)、[文書閉鎖](../../artifacts/macos-demand-active-pipeline-artificial-20261016-doc-records/root-closed.json)。
