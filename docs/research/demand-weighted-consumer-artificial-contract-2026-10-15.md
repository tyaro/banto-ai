# 固定重みconsumer：人工の問題生成とβ0可行性契約

2026-10-15 JST。人の明示依頼により[学習開始条件](demand-weight-learning-entry-contract-2026-10-15.md)のうちconsumerの問題生成・baseline可行性を人工だけで検証する。**solve/fit/最適係数/実データr・旧x・ラベル数量/候補予測・性能評価/2015参照・再評価を起動しない。** 旧closed source/根/失敗/変更を保持し、今回もfit_ready=false/can_launch_learning=false。

## Consumerの入力境界

pure compile-only APIはfresh concrete payloadだけを受け、path/reader/全履歴/solver/外部I/Oを受け取らない。batchはschema/cutoff/excluded_origin/transforms/rows。各rowはinput、label、weightedの3役を分離する。inputは既存demand-input-v1、labelはdemand-label-v1、weightedは旧features/reasons・保存r・exact z・encoder state pin。r計算へlabelを渡さない。

cutoffは2014年の4Q開始だけ。current Qの2013発行日（2013-02-26から14日間隔の21日をQ選別）の全FIT10=(6,7,10,13,15,17,19,23,26,27)、primaryまたは事前指定1日を全店除くpayloadだけを受理する。元I行calendar・key・label可用性・past56日付/available・同休業mask/unknown・変換period2013/usable2014-01-01を、**全行の数量変換前**に検査する。他Q/未来/2015/未可用/余剰field/重複/部分日削除はエラー。これはtrusted API境界でありOS sandbox/認証ではない。

その後、raw有限非負int/float（bool不可）/入力None、既存past28曜日mean28支持と日次値のexact binary64一致を検査する。旧features/reasonsはpast14とbaseline/mask/2013尺度から固定式で再構築し一致確認する。過去56date/value/availableだけを固定encoder v2へ渡し、τ1/20・p32nearest-evenのr、z=r*x、canonical encoder-state pinまで一致確認する。rの格子/範囲/z積だけではraw履歴との来歴を証明したとしない。今回は全て人工。2013尺度は2014cutoff遡及前処理で、2013当時のprospective前処理とは呼ばない。

学習labelはraw観測complete14日だけ。営業日Noneも休業相当Noneも0補完して受け入れない。営業0・休業raw0/正値を消さない。休業相当01-01/12-25・営業unknownを維持し、他の祝日を一律0にしない。観測のみ/休業相当欠測だけ0仮定のlabel scenarioは、学習生成と別の人工β0日次コピー確認で区別する。

## 自Qの問題・目的・制約

元Eは旧特徴非NoneかつB>0、Iはcomplete raw全行。r0適格はx=[0,0,0]のまま正のwを持ち、目的定数に残る。旧不支持/B0はx=None,w0、Iとvには残る。各店のw=1/(10*nE)、v=1/(10*nI)、和は各1。旧4Q共通の1/(40*n)を流用せず、非ゼロrだけで再正規化しない。E/Iが欠けた店は停止し、β0成功や他店への再配分へ救済しない。全店r0でも旧Eがあればcompileは成立するが学習開始のrank条件は満たさない。

problemは既存coreと互換のrows（key,quarter,B,Y,unit,x,fit_weight,risk_weight）だけを生成する。旧solver/coreをimport/callしない。

```text
B = Fraction(math.fsum(baseline_daily))
Y = Fraction(math.fsum(raw_observed_actual))
unit = 14 * Fraction(scale)           # Fraction(14*scale)ではない
t = (Y-B)/unit, e=B-Y, h=unit*z
J(beta) = beta^T G beta - 2 rhs^T beta + C
G = I3 + sum_E w*z*z^T               # 切片含むλ1
rhs = sum_E w*z*t
C = sum_E w*t*t                      # r0適格も含む
nonnegative: -h*beta <= B
under/over: sum_I v*max(side*(e+h*beta),0) <= sum_I v*max(side*e,0)
```

非負は全I行のnormal/boundを保存（zero normalもtrivialとして保存）。hingeは元hinge row材料とbaseline RHSを保存する。任意のsubset Sに対するsupporting facet a=sum_S v*side*h、b=baseline_side−sum_S v*side*eを生成でき、β0でactiveな厳密positive集合/空/全など人工subsetを検査する。β0の2facetだけでhinge全体を表現できるとは呼ばない。solverのcut生成/KKT/最適性検証は今回未実行。

## β0のbaseline再現

β=[0,0,0]を固定の検査点として代入し、P=B、非負slack=B≥0、各行/自Qのpaired under/over差0、J(0)=C、penalty0をexact保存する。baseline feasible witnessであり、学習済み係数/最適解/certificate/改善実証ではない。β0ではz/unit/sign誤りを検出できないため、上記G/rhs/C/h/e/normal/facet/重みを別readerで独立再構築する。

日次はbaselineをそのままコピーし、canonical総量Bと日次exact Fraction総和を別保存する。binary64 fsum由来の差があっても日次を比例補正しない。β0日次コピー、canonical P=B、差の明示を分けて確認する。

## 人工確認と終了

4Q primary、事前固定21削除payload、全r0、旧不支持/一部B0、true0/null、float丸め/scale/unit、r/state/z改ざん、label/時点/他Q/欠測/店舗欠け/原分母、数値上限/solver呼出し禁止を試験する。削除payloadは残存E/Iから正しく1/(10n')へ再重みするfuture consumerの問題生成であり、前回の固定w幾何診断とは別。

独立readerはconsumer/encoder/旧feature/core/solverをimportせず、人工fixtureとbindingから全問題row/元E-I/目的多項式/hinge材料/facet/β0/日次scenarioをchecked arithmeticで照合する。人工入力は元case＋明示patchで完全再構築可能に保存し、展開payload pinも保存する。不一致/失敗/partialは別fresh rootに保持し、閉鎖sourceを修正しない。

各工程親900/子870秒、sampled Mac footprint/RSS各2GiB、整数/約分前積・和・比較各8192bit、既存solver限界は変更しない。artifact normal24files768MiB/total32files1GiB/single32MiB/failure8files256MiB、EvidenceStore16MiB512files/part256KiB/failure2MiB16files。stdio/exit/source/input/state/partial/failure/resource/closureを保存する。

人工完了はconsumer_artificial_readyだけを更新する。実weighted-label prefix統合/solve/非ゼロ係数の予測bridge/25solve計画実行/四季性能/実データ改善は未検証。学習再開の人の指示はなく、fit_ready/can_launch=false、2015停止、heartbeat PAUSED。調整2014以前・自Q共有λ1・元E/I・四季平均under/over非増加とMSE条件・同休業mean28・観測と休業欠測0仮定分離を維持する。Windowsnative/OS依存包括suite/2016–17/予約31–54/販促/正式holdout/CARE/課金API/新取得/外部送信/commit/push/依存lock/Xcode変更/PSI採用なし。
