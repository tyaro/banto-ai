# rank3・週係数非ゼロ解のrawP厳密ゼロ境界：事前契約

2026-10-16 JST。実学習・2015参照再評価停止を維持する。旧変更/source/失敗/closed rootsは保護し上書き削除しない。実quantity/problem/labelsはdecodeせず既存保護hashのみ確認する。入力型・core・0判定を変更せず、手指定beta・許容誤差0・結果を見たfixture探索は行わない。

## 固定Q2人工prefix

元2013年Q2固定6発行日×FIT10=60行、excluded_origin=None、自Q・scale10・λ1・τ1/20・p32・元E/I/nE-nI各6/w-v各1/60・同休業mean28/unknownを保持する。全raw labelは観測済み0で休業へ再分類しない。新consumer compile/solverは人工各1回、旧rank2境界と旧rank3成果は変更しない。

| profile | past56（最古から） | 旧x | B |
|---|---|---|---|
| A | 10/12.5/15/17.5各14日×c | [1,c/8,0] | 227.5c |
| D | 7.5/10/12.5/17.5各14日×c | [1,c/4,0] | 210c |
| W | 10/12.5/15各14日、16.25/18.75各7日×c | [1,c/4,c/4] | 227.5c |

店6だけW・c0=2^-10、残9店はFIT位置1,2,3からA/D/Wを繰り返して各3店・c=1。rはprofile毎に正・scale cに不変だがprofile間で同じとは主張しない。z=r*oldx、unit140。large A/D/Wの3行minorと罰則なしGramの行列式>0でrank3を厳密確認する。

G/rhs/Cをraw prefixから再構築し、Cramerで非制約u=G^-1rhsを求める。固定smallW先頭1行の元非負制約a=-140*rW*[1,c0/4,c0/4]、b=B0、v=G^-1a、alpha=(a·u-b)/(a·v)を使いbeta=u-alpha*vを構成する。要求は非制約小群raw<0・alpha>0・全3beta<0（週betaも非ゼロ）・a·beta=b・元非負正dual2alpha/J尺度stationarity・全training小群P=0/他群0<P<B・full hinge under0/over減少・Ju<Jc<J(0)・Jc-Ju=alpha²*(a·v)>0。すべてsolve前に保存してからsolverを一度呼び、同じbeta・active正dual・独立full hinge/非負/KKT/gap0を要求する。不成立はfailed保存しlabel/期間/重み/fixture/係数変更で救済しない。

## 固定境界30予測と週項の接続

2014-04-02、FIT10、Wprofileのみ、c=c0*(1-2^-20)/c0/c0*(1+2^-20)の30予測。同じ1証明付きstate/transforms/scaleを使う。入力/mean28/fsum/旧level/週featureはbinary64で厳密に表せる。学習smallWの非負境界を同数値inputで再現し、solve後の入力調整を行わない。

学習のactive等式からrawP(c)=140*rW*beta0*(1-c/c0)=S*(c-c0)、S=-140*rW*beta0/c0>0。全30件でこの式をexactに照合する。lower10はstrict負/floor_applied=true/floor_zero、zero10は厳密0/floor_applied=false/floor_zero、upper10はstrict正/floor_applied=false/changed_proportional。全P=max(raw,0)、lower/zeroは全日0、upperはbaseline_j*P/Eでexact和P。全targetは営業相当日・unknown、B=E。下上raw対称性、上の日次と0との差、表示差を保存し、固定3点から一般連続性/全近傍/実性能を認定しない。

各30件で3成分unit*zj*betajを保存し、特にweekly=unit*rW*(c/4)*beta2!=0を要求する。raw_without_weekly=B+component0+component1、raw-without=weeklyを確認し、without>0も固定条件にする。中央は週項を含めて厳密0となる。upper10でdaily_j-baseline_j*without/E=baseline_j*weekly/Eをexact照合する。これは同じ予測の代数分解でbeta差替え再予測ではなく、floor後に線形週寄与を拡張しない。

既存consumer/solver/encoder/connector/bridge無変更。certificate独立証明後にbetaだけを同Q/cutoff利用可能なinput-only日次へ渡し、全pinを保存する。prefix/presolve/state/solver journalを予測前freeze、30予測/triplesを評価label前freezeする。外側synthetic fit=true/real=false、nested fit=falseはbridge component内だけのflag。

元15拒否（12接続改変・lower/upper誤0・中央誤floorflag）にcert週beta0差替え/週項drop/二重r/週列0でrank2への退化の4検査を加え、計19拒否。直接検査は追加予測ではない。中央I/O canary追加1件は30件と別でopen各0・出力一致を確認する（OS sandboxではない）。

## 評価・独立検査・保存

30予測freeze後に各baseline_truth/zero_truth/open_missingの90scenario。open_missingは営業日1つ0・別1つNoneでNoneを0に補完しない。観測のみ/休業相当Noneだけ0仮定は別保存するがQ2全openなので同値となる。観測0は営業0のまま。baseline真値under悪化60セルを保存し、人工接続から未来非悪化/実性能/PSI採用を認定しない。旧休業差・丸め差coverageは保持する。

独立readerはconsumer/solver/encoder/connector/bridgeをimportせず、raw prefixからfull encoder/r-z/元ledger/重み・別6項determinantのrank3/Gramを再構築する。smallW平面の2×2縮約で別にbetaを求め、Cramer射影/KKT/J/全元constraintとcertificateを照合する。30日次/raw符号/flag/3項週分解/upper日次週寄与/triples/表示・90scenario両modeを再構築し、名前集合/長さ/strict型/有限非負/正scale/曜日support/全pin/freezeを照合する。runtime max_bits値の別経路同値再現は主張しない。

各親900/子870秒、Mac sampled footprint/peak RSS各2GiB、整数形成/比較8192bit・既存solver有限上限。artifact normal24files768MiB/total32files1GiB/single32MiB/failure8files256MiB、EvidenceStore16MiB512files/part256KiB/failure2MiB16files、stdout1MiB/stderr128KiBを維持。全source/prefix/encoder/rank/oracle/問題/cert/全pivot/state/raw/週項/日次/label/stdioexit/freeze/triples/partialfailure/resources/closureを保存し、Astraが起動前と保存結果を確認する。

調整2014以前、自Q共有λ1、四季all/normal・元日両modeの平均under/over・総量MSE非増加/annualMSE厳密改善、同休業mean28/元支持/観測と欠測0仮定の分離は不変。今回はQ2人工境界だけで実四季性能ゲート未評価。real_fit/real_problem_decoded/new2014_scores/new2015=false、fit_ready/can_launch_learning=false・heartbeat PAUSED・採用なし。実rank3/集中/全削除/開始AND条件を緩和しない。2015参照再評価/実fit/新取得/外部研究データ送信/commit-push/依存lock/Xcode変更/Windowsnative/OS依存包括suite/追加agentなし。人工検証から実学習を自動起動しない。
