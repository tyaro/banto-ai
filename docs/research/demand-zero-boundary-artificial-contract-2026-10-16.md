# rawP厳密ゼロ境界と両側：人工接続事前契約

2026-10-16 JST。実学習・2015参照再評価停止を維持し、旧変更/source/失敗/closed rootsを保護する。実quantity/problem/labelsはdecodeせず既存保護hashのみ確認する。入力を有理文字列へ拡張せず、係数を手指定せず、許容誤差で0と見なさない。

## 固定した人工学習1問題

元consumerのQ2固定2013暦6日×FIT10=60行、excluded_origin=None、自Q・scale10・λ1・τ1/20・p32・元E/I/w-v・同休業mean28/unknownを保持する。past56は10/12.5/15/17.5各14日×c、店6だけc0=2^-10、他9店c=1。全rawラベルは観測済み0、休業へ再分類しない。新compile/solverは人工各1回のみ。旧8rank3 state/旧成果は変更しない。

全行で同じr>1/2、旧x=[1,c/8,0]、B=227.5c、unit140、元nE/nI各6・w/v各1/60をexact確認する。この人工problemは罰則なしrank2・週係数0で、実rank3/集中/開始AND条件を緩和する意味はない。

l0=c0/8、l1=1/8、W=9/10、d=l1-l0、k=13l0/r、H=1+l0²+W*r²*d²を固定し、閉形式beta0=-k/H、beta1=-13*(l0²/r+W*r*d²)/H、beta2=0を構成する。

G/rhs/Cを元prefixから再構築し、別のCramerでu=G^-1rhs、元小群の固定1行非負制約a=-140r[1,l0,0]、b=B0、v=G^-1a、alpha=(a·u-b)/(a·v)を求める。要求はuの小群rawP<0、alpha>0、beta=u-alpha*vで閉形式と一致、元制約KKT正dual2alpha・全非負/full hinge・Ju<Jc<J(0)・Jc-Ju=alpha²*(a·v)>0。全trainingのP=227.5*(c-c0)/Hにより小群0/大群0<P<B、under0/over減少をexact確認する。全証拠をsolve前に保存し、solver各1回のcertificateが同じ非ゼロbeta・正dual active・独立J-KKT/gap0を持つことを要求する。不成立はfailed保存し、label/履歴/scale/閾値変更で救済しない。

## 境界の固定30入力

2014-04-02、FIT10、lower/zero/upperの3点、計30予測。c=c0*(1-2^-20),c0,c0*(1+2^-20)。全raw input/mean28/fsum/旧levelはbinary64で厳密に表せ、相対historyとrは不変。モデルは同じ1証明付きstate、同じtransforms/scale10を使う。inputは学習結果を見て調整せず、学習の非負境界をそのまま再現する。

全rawP=227.5*(c-c0)/Hを厳密照合する。下側10件はraw<0/floor_applied=true/floor_zero、中央10件はraw=0/floor_applied=false/floor_zero、上側10件はraw>0/floor_applied=false/changed_proportional。全P=max(raw,0)、中央と下側は全日次/表示0、上側はbaseline_j*P/Eでexact和P。B=E、全target営業相当日・unknown。中央を負値clipと混同せず、前後rawの対称性・上側日次数量と0との差・表示丸め差も保存する。3点確認を一般の連続性/全近傍保証に拡張しない。

既存consumer/solver/encoder/connector/bridgeは無変更。compile→certificate独立証明→同Q/利用可能cutoffのinput-only日次へbetaだけを接続し、全pinを保存する。state/prefix/solver journal/presolveを予測前freeze、全30予測を評価ラベル生成前freezeする。外側synthetic fit=true/real=false、nested fit=falseはpure bridge内の局所flag。

固定改変は元12接続拒否と、lower/upperのrawを誤って0と扱う2直接canary、中央floor flagをtrueとする直接canaryの計15拒否。直接canaryは追加予測でない。中央I/O canary追加1件は30保存予測と別に数える（open各0・出力一致、OS sandboxではない）。

## 評価・独立検査・資源

全30予測freeze後、各baseline_truth/zero_truth/open_missingの90scenarioを生成する。open_missingはbaselineから営業日1つ0・別1つNoneにする。観測のみ/休業相当Noneだけ0仮定を別保存するが、今回はQ2全openなので両modeは同値となる。営業Noneを0へ補完しない。全観測0は営業ゼロとして保持する。baseline真値のunder悪化60セル（case×mode）を保存し、人工接続から未来非悪化/実性能/PSI採用を認定しない。以前の休業None差・丸め差・rank3のcoverageはそのまま保持する。

独立readerはconsumer/solver/encoder/connector/bridgeをimportせず、raw人工prefixからfull encoder/r-z/元ledger/重み、rank2、別2×2射影と閉形式/元非負KKT/J/全constraint、全30日次/境界符号とflag/表示/90scenario両modeを再構築する。全名前集合・長さ/strict型/有限非負/正scale/曜日支持・全pin/freezeを照合する。runtime max_bits値の別経路一致は主張しない。

各親900/子870秒、Mac sampled footprint/peak RSS各2GiB、整数形成/比較8192bit・旧solver有限上限。artifact normal24files768MiB/total32files1GiB/single32MiB/failure8files256MiB、EvidenceStore16MiB512files/part256KiB/failure2MiB16files、stdout1MiB/stderr128KiBを維持。全source/prefix/encoder/rank/oracle/問題/cert/pivot/state/raw/日次/label/stdioexit/freeze/partialfailure/resources/closureを保存し、Astraが起動前と結果を確認する。

調整2014以前、自Q共有λ1、四季all/normal・元日両modeの平均under/over・総量MSE非増加/annualMSE厳密改善、同休業mean28・元支持・観測/欠測0仮定分離は不変。今回Q2人工境界のみで実四季性能ゲート未評価。real_fit/real_problem_decoded/new2014_scores/new2015=false、fit_ready/can_launch_learning=false・heartbeat PAUSED・採用なし。2015参照再評価/実fit/新取得/外部研究データ送信/commit-push/依存lock/Xcode変更/Windowsnative/OS依存包括suite/追加agentなし。人工検証から実学習を自動起動しない。
