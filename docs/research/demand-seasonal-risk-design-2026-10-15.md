# 四季平均の両側誤差制約付き総量補正

2026-10-15 JST。人が「総量固定を外し、2014四季ごとの平均で過小/過大非増加、14日総量MSE改善、2014以前調整、同休業mean28、観測only/欠測0分離、Astra確認」を明示したため、旧全窓の普遍保証を期間平均の検証条件へ変更する。[Astraレビュー](demand-seasonal-risk-astra-review-2026-10-15.md)を保存してから実施する。総量は動かせる一方、個別窓/各店/元日/2015の両側非悪化保証はなくなる。

FIT10店(6,7,10,13,15,17,19,23,26,27)、既読2013–2015のみ、休業相当01-01/12-25、営業unknown、raw0/null維持。対照は同mask mean28。モデル用2013尺度・2014の過去26fit及び2015前最終250窓/last label2014Dec16の閉鎖raw/stateを再利用し、新ridge/NN fit0。旧選択済みshapeを新blendの基点には使わず、B=mean28を基点とする。既読探索的研究で未知holdoutではない。

事前候補順 matched_mean28 / signed_raw_blend / signed_recent14_blend。rawは保存済み非負14日回帰予測。recent14は発行日前14日だけの非休業・真の観測の同曜日平均。各weekday2観測以上なら使用、未満なら該当leadのBへfallbackし理由/支持数を保存。真の0と欠測を区別し、過去休業仮定日は除外、未来休業仮定日は0。14日は既定の予測horizonで期間gridなし。支持は各weekday最大2観測で高分散。旧方法の2015副結果から昇格する候補選択ではない。

各候補をp=(1−alpha_q)*b+alpha_q*rawとし、発行日quarterごとのalphaを全14日共通にする。alphaは0..1、したがって非負/休業0を維持するが総量差D=sum(raw)−sum(B)は正負を許す。日次上方制約/総量等式は課さない。

2014はJan1+14*k/k0..25の260窓。奇数130は校正、完全な実観測14labelだけで総量係数を求める。Q1/Q2/Q3/Q4の完全校正支持30/30/40/20（各店3/3/4/2）。店等重みで総量MSEは各店の `(P−Y)/(14*u2013)` の二乗平均、過小/過大は全完全窓を分母としたmax(Y−P,0)/max(P−Y,0)の販売数量単位平均。欠測0ラベルを係数fitへ混ぜない。

校正でe=B−Y、D=raw総量−Bとし、alpha上のunder/overそれぞれの凸piecewise-linear関数が基準alpha0以下となる区間をbreakpoint走査で一度求める。交点は−e/D（0..1のみ）。両側区間と0..1の共通区間は0を含む。総量MSEの解析解cov/energyをその区間へclip（energy<=1e-24は0）。校正の数値許容差を改善幅へ加算せず、境界は必要なら0側へ丸める。上限/交点/初期傾き/支持/energy/covariance/両側変化量を保存する。grid探索なし。

偶数側はJan1を除く通常120（各Q30）で四季方式選択する。観測onlyと欠測0仮定を別に計算し、各Qの総量MSE・平均過小量・平均過大量が同mask mean28以下である候補だけを適格とする。MSE比較tol1e-12/販売数量平均tol1e-8。適格候補で観測only総量MSE最小、tieはmean28、baseline常に適格。日次数量MSE/MAE/biasも報告するが新しい選択目的へ混ぜない。元日10は別報告で方式選択へ混ぜず、元日や元日込みQ1の非悪化とは認定しない。元日改善で通常Q1悪化を隠さない。選択群に欠測はなく両scenarioが同値になる支持も明記する。全2014/校正/四季/元日/年末の両label評価を保存する。

方式/四季係数/stateを2015入力前に凍結する。2015原250窓と元日10窓を合算せず（20店日重複）、予測をlabel前保存し、観測only/休業欠測0仮定を別に採点。2015採点尺度は旧u、原観測3490日240完全総量と仮定3500日250総量、元日140日10総量を維持。2015四季も記述評価するが再校正しない。期間平均の条件が2015へ移る保証はなく、悪化も保存し2015後の方式差替えをしない。

fresh macos-demand-seasonal-risk-20261015とexecution/readback/doc-records。3候補/quarteralpha8個（baseline0）を超えて増やさない。全て0/選択全baselineでも可とし、同じ候補で再探索せず原因を残す。全stdio/exit/source/Astraレビュー/state/closure/失敗prefixを保存。親900/子870秒/Mac sampled footprint・peak RSS各2GiB。artifact通常24files768MiB/全32files1GiB/single32MiB/失敗8files256MiB、EvidenceStore16MiB512files/part256KiB/reserve2MiB16files。旧変更/失敗/closed roots保持。2016–17/予約31–54/販促/正式holdout/Windows native/CARE/課金API/新取得/外部送信/Git push/削除/本番採用なし。agentは明示依頼Astraのread-only確認のみ。heartbeat PAUSED保持。有限検証と文書保存まで完了する。
