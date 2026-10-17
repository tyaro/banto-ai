# 季節ごとの方向一致補正・独立した採用と停止

2026-10-15 JST。人の新しい明示指示「年間共通係数で全季節を止めず、季節ごとに採用/停止をAstraと検討、四季平均過小/過大非増加、2014以前調整、同休業mean28、観測only/欠測0分離」に従う。[Astra確認](demand-quarter-consensus-astra-review-2026-10-15.md)を保存してから評価する。今回変えるのは年間共通alphaの制約だけで、特徴/gate/候補/期間/尺度/選択窓を変えない。

FIT10店=(6,7,10,13,15,17,19,23,26,27)、既読2013–2015のみ。対照は同mask mean28、休業相当01-01/12-25、営業unknown、raw0/null維持。旧原因分析/モデル/変更/失敗/closed rootsを保持。候補順matched_mean28 / consensus_bias / consensus_raw。前回のpast56から得るh14/h28/trend7の3方向一致、観測支持、raw方向一致、min残差加法・B比率配分を全て固定し再利用。反転に遅れる既知反例も保持する。

閉鎖macos-demand-adaptive-consensus-20261015の校正ファイルから、2014奇数130窓の真の完全総量30/30/40/20（各店3/3/4/2）で求めた各Q・各候補のenergy A、covariance C、under/over適格上限、MSE非悪化上限、標本journalを再利用。係数は各Qでalpha=0..Uの範囲へC/Aをclip（A<=1e-24なら0）、UはそのQだけの上限とする。4Q共通の最小上限を取らない。固定2候補×4Qの係数8個であり、新しい候補/閾値/期間gridを追加しない。校正MSEと両側平均の非悪化も各Qで独立確認する。

旧共有係数のsourceは変更せず、新policyへ別名保存。発行日のquarterでalphaを選び、同一窓の全14日に共通適用。target日のquarterに切り替えない。他Qの係数/棄却が、このQの係数へ影響しないことをfixtureと独立読戻しで確認する。新ridge/NN fitなし、旧27state・最終2015Jan1前250窓/last label2014Dec16を維持。

2014偶数側130は元日10を除く通常120（各Q30）で方式選択する。観測only/欠測0仮定別に各Q総量MSE・平均過小量・平均過大量が同mask mean28以下なら適格。MSEtol1e-12/販売数量平均tol1e-8。適格候補の観測only総量MSE最小、tieはmean28、不適格ならそのQだけmean28へ戻す。選択側で係数/gateを縮め直さない。Q1停止がQ2/Q4の採用を妨げない。元日10は報告だけで、元日込みQ1/個店/個窓の非悪化は保証しない。

校正の欠測0仮定は別感度評価として保存するがfitにも追加guardにも使わない。選択群に欠測がないため両label gateは同値で、独立頑健性証拠にはならない。2014は既読で繰り返し参照した探索的研究、季節係数8個へ自由度が増えることと小さいQ4支持を明記し、未知性能や将来の両側非悪化を主張しない。

policy/state/四季方式を2015入力前に凍結する。2015の発行前contextで同じgate特徴を計算するだけで、係数/方式のfitや候補の事後誤差による再調整はしない。通常250（観測3490日240総量）と元日10（140日10総量）は20店日重複のため合算なし。欠測0仮定は通常3500採点日250総量として別に保存し、raw nullを観測0へ昇格しない。2015四季の条件違反/負の結果も保存、結果後差替えなし。

fresh macos-demand-quarter-consensus-20261015及びexecution/readback/doc-records。全source/Astraレビュー/state/旧校正pin/新季節係数/支持・理由/予測label前後/2scenario/stdio/exit/closure/失敗prefixを保存。親900/子870秒/Mac sampled footprint・peak RSS各2GiB、artifact通常24files768MiB/全32files1GiB/single32MiB/失敗8files256MiB、EvidenceStore16MiB512files/part256KiB/reserve2MiB16files。

候補3・校正8係数で有限終了。全baselineでも負の結果を保存し、同じ候補の追加探索をしない。2016–17/予約31–54/販促/正式holdout/Windows native/CARE/課金API/新取得/外部送信/Git push/削除/本番採用なし。agentは今回明示依頼Astra read-only確認のみ、heartbeat PAUSED維持。共通MacとWindows固有/OS依存未実行を分ける。
