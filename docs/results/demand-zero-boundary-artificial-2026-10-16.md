# rawP厳密ゼロ境界と両側：人工接続検証

2026-10-16 JST。[事前契約](../research/demand-zero-boundary-artificial-contract-2026-10-16.md)・[Astra確認](../research/demand-zero-boundary-artificial-astra-review-2026-10-16.md)・[決定表](../research/demand-zero-boundary-artificial-decisions-2026-10-16.json)。

**非負制約によって解が変わる人工1問題から非ゼロ係数を得て、同じ係数でrawPが厳密に0になる中央10件・負になる下側10件・正になる上側10件を確認した。全30日次予測・90人工評価scenarioを独立照合し、Astraが最終確認した。実学習と2015参照再評価は停止したままである。**

## 境界を作る方法と人工学習

既存の非ゼロ8係数を手修正せず、入力型を拡張せず、0判定の許容誤差も導入しなかった。新しいQ2人工prefixは2013年の元6発行日×FIT10=60行。past56は10/12.5/15/17.5各14日×c、店6だけc0=2^-10、他9店c=1。全rawラベルは観測済み0で、休業へ再分類していない。scale10・同休業mean28/unknown・自Q・元E/I/nE-nI各6/w-v各1/60・λ1/τ1/20/p32を保持した。

全行で同じr>1/2、旧x=[1,c/8,0]、B=227.5c、unit140。l0=c0/8、l1=1/8、W=9/10、d=l1-l0、H=1+l0²+W*r²*d²、k=13l0/rとすると、closed-form解はbeta0=-k/H、beta1=-13*(l0²/r+W*r*d²)/H、beta2=0となる。今回のbeta概数は[-0.001625734362, -0.1735466044, 0]。

solve前にG/rhs/C・閉形式とCramer半空間射影の一致、非制約解uの小群raw<0、元の小群1行の非負制約normal/bound/正dual、J尺度stationarity、Ju<Jc<J(0)、Jc-Ju=alpha²*(a·G^-1a)>0をpresolveへ保存した。全学習行のP=227.5*(c-c0)/Hから小群P=0、大群0<P<Bを確認した。元full hingeはunder0・over減少となる。

新consumer compile/solverは人工各1回だけ。certificateは閉形式と一致し、正dual activeと独立full hinge/非負/J-KKT/gap0を確認した。これはrank2・週係数0の人工境界用problemであり、以前のrank3・週係数非ゼロの結果を置き換えず、実データrank3/集中/全削除/開始AND条件も緩和しない。

## 厳密0とその前後の日次接続

発行日2014-04-02、FIT10、c=c0*(1-2^-20)/c0/c0*(1+2^-20)の固定3点で30予測。入力・mean28・fsum・旧levelはbinary64で厳密に表せ、rは不変。inputをsolve後に探索/調整して0へ合わせたものではない。全raw総量は同じ式`rawP(c)=227.5*(c-c0)/H`にexact一致する。

| 固定位置 | 件数 | rawP | floor_applied | 日次分岐 |
|---|---:|---|---|---|
| 下側 | 10 | 厳密に負（約-2.091504534e-07） | true | floor_zero・全日0 |
| 中央 | 10 | 厳密0 | false | floor_zero・全日0 |
| 上側 | 10 | 厳密に正（約2.091504534e-07） | false | changed_proportional |

中央のfloor_applied=falseはraw<0の場合だけclip実施と記録する既存定義による。branchはP=0なのでfloor_zeroとなり、両者を区別した。上側は全日次>0、日次=baseline_j*P/E・exact和P、表示丸め差を別保存した。各店で下上rawの厳密対称性と中央0も照合した。3点確認を一般的な連続性・すべての近傍・実需要性能の保証に拡張しない。

consumer/solver/encoder/connector/bridgeは無変更。独立証明済みcertificateのbetaだけを同Q/cutoff利用可能なinput-only bridgeへ渡し、全input/compiled/problem/cert/proof/legacy pinsを確認した。state/prefix/presolve/solver journalを日次前freeze、全30予測とtriplesをlabel生成前freezeした。外側synthetic fit=true/real=false、nested fit=falseはbridge component内でfitしない局所flagとして保持。

## 人工評価と検査範囲

全30予測のbaseline_truth/zero_truth/open_missingから90scenarioを生成し、観測のみ/休業相当Noneだけ0仮定を分けて保存・照合した。今回Q2全openなので両modeは同値である。open_missingは営業日1つ0/別1つNone、Noneは0へ補完せずtotal評価不完全のままにした。観測0を休業へ変更していない。

baseline真値でunderが悪化する60セル（case×mode）も保存した。今回の人工境界で実10店四季性能ゲート・未来非悪化・PSI採用を認定しない。以前の休業None差・丸め差・rank3のcoverageと旧記録は保持した。今回の境界ケース自体は全営業相当日・B=E・週特徴0である。

元12接続改変とlower/upperを許容誤差で0にしてしまう2直接canary、中央の負値flagをtrueにする直接canaryの計15拒否を確認した。直接canaryは追加予測でない。中央のI/O canary追加1件は30予測と別に数え、指定関数open各0・出力一致を確認した（OS sandboxではない）。

独立readerはconsumer/solver/encoder/connector/bridgeをimportせず、raw prefixからfull encoder/r-z/元ledger/重み、rank2、別2×2射影/閉形式/元非負KKT/J/全constraint、全30日次/符号/flag/表示、90scenario両modeを再構築した。full state比較13,470・daily比較750、実装check317。runtime max_bits値自体の別経路一致は主張しない。

## 資源・保存・停止

| Mac実行 | 秒 | sampled physical footprint | peak RSS |
|---|---:|---:|---:|
| 人工compile/solver/境界接続 | 1.986161 | 28,262,904B | 40,763,392B |
| 独立照合 | 0.968175 | 31,867,384B | 44,171,264B |

各親900/子870秒・Mac footprint/RSS各2GiB、整数形成/比較8192bit・既存solver有限上限は不変。実行最大367bit・独立最大301bit。artifact 19files/2,675,401B・最大1,118,105B。normal24files768MiB/total32files1GiB/single32MiB/failure8files256MiB、EvidenceStore16MiB512files/part256KiB/failure2MiB16files、stdout1MiB/stderr128KiBを維持した。

全source/人工prefix/fullencoder/rank/oracle/問題/cert/全pivot/state/raw/日次/label/stdioexit/freeze/triples/partialfailure/resourceclosureを保存し、旧変更/source/failed/closed rootsと旧handoff/index全文を保護した。

Mac Python3.14.8共通人工接続・独立照合/資源観測pass。Windows固有/native・OS依存包括suiteは未実行として分離。実timeout経路の新試験はなし。

調整2014以前、自Q共有λ1、四季all/normal・元日両modeの平均under/over・総量MSE非増加/annualMSE厳密改善、同休業mean28/元支持/観測と欠測0仮定の分離は不変。今回はQ2人工境界だけで実四季性能ゲート未評価。実problem/quantity/labels内容decode・実fit/solve/予測/2014採点/2015参照再評価0、fit_ready=false/can_launch_learning=false・heartbeat PAUSED・採用なし。実開始AND条件を緩和せず、人の明示解除なしに実学習を起動しない。

2016–17/予約31–54/販促/正式holdout/CARE/課金API/新取得/外部研究データ送信/commit-push/依存lock/Xcode変更/追加agentなし。

証跡：[実行](../../artifacts/macos-demand-zero-boundary-artificial-20261016-execution-records/root-closed.json)、[全state/予測](../../artifacts/macos-demand-zero-boundary-artificial-20261016/root-closed.json)、[独立](../../artifacts/macos-demand-zero-boundary-artificial-20261016-readback-records/root-closed.json)、[文書閉鎖](../../artifacts/macos-demand-zero-boundary-artificial-20261016-doc-records/root-closed.json)。
