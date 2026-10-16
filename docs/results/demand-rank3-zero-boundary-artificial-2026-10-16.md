# rank3・週係数非ゼロ解のrawP厳密ゼロ境界と両側

2026-10-16 JST。[事前契約](../research/demand-rank3-zero-boundary-artificial-contract-2026-10-16.md)・[Astra確認](../research/demand-rank3-zero-boundary-artificial-astra-review-2026-10-16.md)・[決定表](../research/demand-rank3-zero-boundary-artificial-decisions-2026-10-16.json)。

**非負制約によって解が変わるrank3人工1問題から、週変化を含む全3係数非ゼロ解を得て、同じ係数でrawPが厳密に0になる中央10件・負になる下側10件・正になる上側10件を確認した。全30日次予測・90人工評価scenarioを独立照合し、Astraが最終確認した。実学習と2015参照再評価は停止したままである。**

## 境界を作る方法と人工学習

前回のrank2境界を変更せず、Q2の新しい人工prefixを2013年固定6発行日×FIT10=60行で作成した。入力型・core・許容誤差は変更せず、手指定betaも使わない。全raw labelは観測済み0で、休業へ再分類していない。scale10・同休業mean28/unknown・自Q・元E/I/nE-nI各6/w-v各1/60・λ1/τ1/20/p32を保持した。

| profile | past56（最古から、全体c倍） | 旧x | B |
|---|---|---|---|
| A | 10/12.5/15/17.5各14日 | [1,c/8,0] | 227.5c |
| D | 7.5/10/12.5/17.5各14日 | [1,c/4,0] | 210c |
| W | 10/12.5/15各14日＋16.25/18.75各7日 | [1,c/4,c/4] | 227.5c |

店6はsmall W・c0=2^-10、残9店はA/D/W各3店・c=1。rはprofile毎に正で1/2<r<1、cによる二進縮小では不変だが、profile間で同じとは主張しない。large A/D/Wの旧特徴行列式は1/32で、weighted3行minorと罰則なしGram行列式>0をexact確認した。ridgeによる正定値性をrank3の代用にしていない。

solve前にG/rhs/Cを再構築し、固定small Wの元非負制約a・bへ、u=G^-1rhs、v=G^-1a、alpha=(a·u-b)/(a·v)、beta=u-alpha*vをchecked Cramerで射影した。small W平面上の別2×2縮約解と一致し、全3beta<0・非制約小群raw<0・元非負正dual2alpha・J尺度stationarity・Ju<Jc<J(0)・Jc-Ju=alpha²*(a·v)>0を保存した。小群P=0/全大群0<P<B、元full hinge under0/over減少も確認した。

新consumer compile/solverは人工各1回だけ。certificateはoracleに一致し、active正dualと独立full hinge/非負/J-KKT/gap0を持つ。今回のbeta概数は[-0.001608875576, -0.251246053, -0.107705836]。独立readerはsmall W平面の2×2縮約を主経路として、別determinant/Cramer射影と元制約を再構築した。旧rank2境界/旧8rank3 state/実rank3・集中・全削除・開始AND条件は変更しない。

## 厳密0とその前後の日次接続

発行日2014-04-02、FIT10、c=c0*(1-2^-20)/c0/c0*(1+2^-20)の固定3点で30予測。入力・mean28・fsum・旧level/週featureはbinary64で厳密に表せ、rは不変。inputをsolve後に探索/調整して0へ合わせたものではない。全raw総量は同じ式`rawP(c)=140*rW*beta0*(1-c/c0)=S*(c-c0)`、S=-140*rW*beta0/c0>0にexact一致する。

| 固定位置 | 件数 | rawP | floor_applied | 日次分岐 |
|---|---:|---|---|---|
| 下側 | 10 | 厳密に負（約-2.009312497e-07） | true | floor_zero・全日0 |
| 中央 | 10 | 厳密0 | false | floor_zero・全日0 |
| 上側 | 10 | 厳密に正（約2.009312497e-07） | false | changed_proportional |

中央のfloor_applied=falseはraw<0の場合だけclip実施と記録する既存定義による。branchはP=0なのでfloor_zeroとなり、両者を区別した。上側は全日次>0、日次=baseline_j*P/E・exact和P、表示丸め差を別保存した。各店で下上rawの厳密対称性と中央0も照合した。3点確認を一般的な連続性・すべての近傍・実需要性能の保証に拡張しない。

consumer/solver/encoder/connector/bridgeは無変更。独立証明済みcertificateのbetaだけを同Q/cutoff利用可能なinput-only bridgeへ渡し、全input/compiled/problem/cert/proof/legacy pinsを確認した。state/prefix/presolve/solver journalを日次前freeze、全30予測とtriplesをlabel生成前freezeした。外側synthetic fit=true/real=false、nested fit=falseはbridge component内でfitしない局所flagとして保持。

## 非ゼロ週項の境界・日次への伝達

全30件のweekly=unit*z2*beta2は厳密に負で、3成分の和とrawPが一致する。raw_without_weekly=B+component0+component1>0で、rawP-without=weekly。中央の厳密0は週項を含めた相殺であり、週項を除くと0にはならない。この違いも直接canaryで検出した。

上側10件はfloorされず、daily_j-baseline_j*without/E=baseline_j*weekly/Eをexact照合した。係数差替えの追加予測ではなく、同じ予測の代数分解である。下側・中央のfloor後日次へraw寄与の線形解釈を拡張しない。

## 人工評価と検査範囲

全30予測のbaseline_truth/zero_truth/open_missingから90scenarioを生成し、観測のみ/休業相当Noneだけ0仮定を分けて保存・照合した。今回Q2全openなので両modeは同値である。open_missingは営業日1つ0/別1つNone、Noneは0へ補完せずtotal評価不完全のままにした。観測0を休業へ変更していない。

baseline真値でunderが悪化する60セル（case×mode）も保存した。今回の人工境界で実10店四季性能ゲート・未来非悪化・PSI採用を認定しない。以前の休業None差・丸め差・rank3のcoverageと旧記録は保持した。今回の境界ケース自体は全営業相当日・B=E・週特徴非ゼロである。

元12接続改変とlower/upper誤0・中央誤flagの3直接canaryに、cert週beta0差替え・週項drop・二重r・週列0でrank2退化の4検査を加え、計19拒否を確認した。直接canaryは追加予測でない。中央のI/O canary追加1件は30予測と別に数え、指定関数open各0・出力一致を確認した（OS sandboxではない）。

独立readerはconsumer/solver/encoder/connector/bridgeをimportせず、raw prefixからfull encoder/r-z/元ledger/重み、rank3/罰則なしGram/3行minor、別2×2縮約/Cramer/元非負KKT/J/全constraint、全30日次/符号/flag/週分解/表示、90scenario両modeを再構築した。full state比較13,470・daily比較750、実装check489。runtime max_bits値自体の別経路一致は主張しない。

## 資源・保存・停止

| Mac実行 | 秒 | sampled physical footprint | peak RSS |
|---|---:|---:|---:|
| 人工compile/solver/境界接続 | 2.082960 | 28,934,648B | 41,435,136B |
| 独立照合 | 1.035460 | 33,505,784B | 45,301,760B |

各親900/子870秒・Mac footprint/RSS各2GiB、整数形成/比較8192bit・既存solver有限上限は不変。実行最大601bit・独立最大453bit。artifact 19files/3,035,572B・最大1,229,497B。normal24files768MiB/total32files1GiB/single32MiB/failure8files256MiB、EvidenceStore16MiB512files/part256KiB/failure2MiB16files、stdout1MiB/stderr128KiBを維持した。

全source/人工prefix/fullencoder/rank/oracle/問題/cert/全pivot/state/raw/日次/label/stdioexit/freeze/triples/partialfailure/resourceclosureを保存し、旧変更/source/failed/closed rootsと旧handoff/index全文を保護した。

Mac Python3.14.8共通人工接続・独立照合/資源観測pass。Windows固有/native・OS依存包括suiteは未実行として分離。実timeout経路の新試験はなし。

調整2014以前、自Q共有λ1、四季all/normal・元日両modeの平均under/over・総量MSE非増加/annualMSE厳密改善、同休業mean28/元支持/観測と欠測0仮定の分離は不変。今回はQ2人工境界だけで実四季性能ゲート未評価。実problem/quantity/labels内容decode・実fit/solve/予測/2014採点/2015参照再評価0、fit_ready=false/can_launch_learning=false・heartbeat PAUSED・採用なし。実開始AND条件を緩和せず、人の明示解除なしに実学習を起動しない。

2016–17/予約31–54/販促/正式holdout/CARE/課金API/新取得/外部研究データ送信/commit-push/依存lock/Xcode変更/追加agentなし。

証跡：[実行](../../artifacts/macos-demand-rank3-zero-boundary-artificial-20261016-execution-records/root-closed.json)、[全state/予測](../../artifacts/macos-demand-rank3-zero-boundary-artificial-20261016/root-closed.json)、[独立](../../artifacts/macos-demand-rank3-zero-boundary-artificial-20261016-readback-records/root-closed.json)、[文書閉鎖](../../artifacts/macos-demand-rank3-zero-boundary-artificial-20261016-doc-records/root-closed.json)。
