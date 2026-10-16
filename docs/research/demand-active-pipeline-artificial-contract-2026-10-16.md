# 制約が非ゼロ解を変える人工pipeline事前契約

2026-10-16 JST。実学習・2015再評価停止を維持する。前回rank3検証は全ridge解が既に可行だったため、今回は制約が解を変える経路だけを新しい人工prefixで補う。既存source/失敗/closed roots/変更を上書き削除しない。実source/problem/quantity/labelは内容decodeせず既存保護hashのみ確認する。

## 固定設計と解析witness

前回rank3のA/B/C past56・FIT10位置mod3割当・2013年21発行日・scale10・自Q・mean28・休業maskを保持する。A=10/12/14/16各14日、B=8/10/12/16各14日、C=10/12/14各14日+15/17各7日。旧xは[1,.1,0]/[1,.2,0]/[1,.2,.2]のbinary64値。r>0、z=r*oldx、元E/I/w-v・λ1・τ1/20・p32nearest-evenを変更しない。

人工学習labelはA群がbaselineそのまま、B/C群が営業相当日baseline±1・休業0とする。正負×四季8primary・420行出現、input context210共有。targetはA=0、B/C=±1/10。店舗の実特性による分類ではなく人工rankを作る固定規則である。探索・期間変更・再調整・削除再fitはしない。

G=I+ΣwzzT、rhs=Σwztを元prefixから再構築する。3行minorと罰則なしGramの行列式>0を確認する。s=±1、n=s*[1,binary64(.1),0]、u=G^-1rhs、v=G^-1n、a=(n·u)/(n·v)、beta=u-a*vを3×3 Cramerの厳密有理数で計算する。

要求はn·u>0、n·v>0、a>0、uが元full hingeの少なくとも一側を厳密違反、beta!=uかつ全3成分非ゼロ、n·beta=0。A群ではP=B、B/C群ではPがBとYの厳密な間に入り、全P非負、元四季平均under/over両側非増加をexact確認する。Aのbaseline誤差0と一側のbaseline risk0からn·beta<=0は元full hinge可行集合に必須の半空間である。2Gbeta-2rhs+2a*n=0・2a>0、可行性と厳密凸性で一意最適を証明する。全Aを選ぶ元hinge facetのnormal/bound/正dualも構成し、J(u)<J(beta)<J(0)、J(beta)-J(u)=a²*(n·v)>0をchecked exactでsolve前に保存する。元solverを各一度だけ呼び、独立J尺度KKT/full hinge/非負/gap0とoracle一致、正dualを持つactive hingeがあることを要求する。不成立なら失敗を保存し、救済探索しない。

## 日次接続と独立照合

既存consumer/solver/encoder/connector/bridgeを変更しない。証明書のbetaだけを日次へ渡し、全pinを確認する。全8state/solver journalを予測前freeze、全640予測を評価label生成前freezeする。

前回と同じ2014-01-01/03-26/04-02/07-02/12-17、A/B/C×uniform/weekday×10店×正負=600件と、flat/missing/B0/open_zero×store6/historyA×5日×正負=40件、計640件を一巡実行する。weekdayはpastにweekday*.25を加える。週寄与、3項分解を保持する。加えて同じinputの代数式として、unconstrained_raw=B+unit*z·u、constraint_shift=unit*z·(beta-u)を保存し、raw-unconstrained_raw=constraint_shiftを確認する。これは非制約係数へ差し替えたconnector再実行ではない。非floor・B=Eの対応する支持inputでは日次の差もbaseline_j*constraint_shift/Eで照合し、全Q両signで制約の効果が非ゼロに伝わることを要求する。

元の12接続改変、rank1/週列0/drop週/二重rの4直接canaryを保持し、unconstrained uを証明書betaへ差し替える改変も拒否する（計17）。I/O canary追加1件は640件と別に数える。floorやcanonical B≠Eの比例配分への到達は必須にせず未到達なら限定する。

予測freeze後のstore6/100予測にmatching_truth/baseline_truth/open_missing、休業あり40予測にclosure_missing/positiveを加え380scenario。matching_truthは営業相当日max(baseline±1,0)の固定stress labelで、A群学習labelとは別であり「モデルが真値に一致する」との意味ではない。観測のみ/休業相当Noneだけ0仮定を分離、営業None/営業0/休業正値は維持する。baseline真値で悪化する反例も全保存する。実10店四季性能ゲートは未評価。

独立readerはconsumer/solver/encoder/connector/bridgeをimportせず、人工元prefixからfull encoder/r-z/ledger/元重み、別determinant実装のu/v/a/betaと厳密full hinge、全certificate、全640日次と制約差・週寄与・380scenario両modeを再構築する。全名前集合、配列長、strict bool、有限非負、positive scale、曜日support、全pin/freezeを検査する。runtime max_bits値自体の一致は主張しない。

## 資源・停止

各親900/子870秒・Mac sampled physical footprintとpeak RSS各2GiB、形成前約分しない整数積/和/比較8192bitと既存solver有限上限。artifact normal24files768MiB/total32files1GiB/single32MiB/failure8files256MiB、EvidenceStore16MiB512files/part256KiB/failure2MiB16files、stdout1MiB/stderr128KiBを維持。全source/input/rank/oracle/問題/証明/全pivot-round/日次/評価/stdioexit/state/partialfailure/resources/closure保存。

Astraが起動前と保存結果を確認する。調整2014以前のみ、四季all/normal・元日両modeの平均under/over・総量MSE非増加/annualMSE厳密改善、同休業mean28、観測のみ/欠測0仮定の分離は不変。人工rankやactive経路は実情報量/頑健性/将来性能を保証せず、実開始AND条件を緩和しない。

real_fit/real_problem_decoded/new2014_scores/new2015=false、fit_ready/can_launch_learning=false、heartbeat PAUSED。2015参照再評価/実学習/実予測/新取得/外部研究データ送信/commit-push/依存lock/Xcode変更/Windowsnative/OS依存包括suite/採用なし。人工検証から実適用へ自動接続しない。
