# 発行直前の水準・変化と前年情報の整合

2026-10-15 JST。人の新依頼「2015店17誤方向/店27行き過ぎをAstraと分析、発行直前水準・変化と前年が整合する場合のみ補正、2014以前調整、四季平均両側非増加、同mask mean28、label分離」に基づく。[Astra確認](demand-immediate-alignment-astra-review-2026-10-15.md)を先に保存する。

旧2窓のみを診断root macos-demand-immediate-diagnosis-20261015-recordsへ先に保存。店17 11/17の直近7日総量1460対前週1798、14日換算T7=2920対B3059.5、差−139.5/週差−338/前年差−56.350488。店27 10/6は4052.107対4457.173、T7=8104.214対B8840.504、差−736.29/週差−405.066/前年差−368.719022。両例とも全て下向きで、年の未校正幅は直前水準差より小さい。単純な符号確認と幅制限でこの既知2例を救済できるとは主張しない。次期反発は直前情報から保証できず、当該日/店を除く閾値や規則は作らない。新方式の全2015作動・性能を診断段階で計算していない。

仮説は「過去の前年適合だけでなく、現在の需要水準と変化も整合した場合に限れば別の誤方向/過大な端点差を抑えられる」。固定3候補 matched_mean28 / aligned_anchor / aligned_cap。旧no_cross信頼gate（o−14/28の未校正前年anchorが両blockでstrict総量MSE改善、各under/over非増加）を維持し、その先に現在の整合確認を追加する。旧validatedやraw-cap等を追加候補にしない。

発行o直前7日とその前7日の同曜日7組を使う。全7組が真の観測かつ両日とも休業相当01-01/12-25以外であることが必要。観測0は有効値、欠測は補完せず不支持、休業相当日に正値があってもrawを消さず不支持。support不足は窓全体B。直前週を将来14日の同曜日へ写し、現在open_maskの位置だけを和した水準をT7とする。現在休業相当予測0を維持する。

level_gap=T7−B総量、week_change=直前7日総量−前7日総量、year_gap=未校正current年anchor総量−B。旧no_cross支持・7組支持に加え、3値がabs>1e-8で全て同符号の場合だけalignedを許す。符号閾値は既定数量許容差であり調整しない。7/14/28/56/364は既定週周期/予測幅で固定、別期間/しきい値gridなし。

aligned_anchorは旧未校正annual_anchorの日別B比例端点。aligned_capはyear_gapを同方向のmin(abs(year_gap),abs(level_gap))へ制限し、B比例配分する。0以下の総量は発生させず、現在閉鎖mask0。capは直前週を反映した端点幅に対するもので、将来実績への非跨ぎや旧校正済み予測以下の最終幅を保証しない。gateと端点capは新alphaと独立に決め、別alphaの再校正で最終幅が増す場合も記録する。

2014奇数130/実観測完全120（四季30/30/40/20、各店3/3/4/2）だけで各候補・季節のalpha8個を一回校正。厳密有理数でunder/over凸区間を求め、各Q総量MSE非悪化上限内でC/Aをclip。2014通常選択120（各Q30、各店3、元日10別）で両label別の各Q総量MSE・平均過小量・平均過大量が同mask mean28以下なら適格。MSEtol1e-12/数量tol1e-8、適格な観測総量MSE最小・同点B、そのQだけ停止。選択側の係数縮小・候補差替えなし。

全年の不作動窓も採点分母へ残す。current年参照/過去2block/旧no_cross/最新7組/整合gate/端点cap/非ゼロ方向/最終変更数を四季別に区別して保存。支持のさらなる減少と、旧gateと新週情報の履歴重複は独立確認数と扱わない。2014既読探索/交互分割/context依存を保持する。Q4校正の欠測0感度は報告のみでfit/追加guard不使用。通常選択に欠測がなく両label同値は独立頑健性証拠ではない。

policy/四季方式を2015入力前に凍結、旧最終250窓last label2014Dec16/27state検証を再利用、新ridge/NN0。2015発行前実績は固定特徴計算だけ、係数/閾値/方式の学習更新0。通常250観測3490日240総量/欠測0仮定3500採点日250総量を別保存、元日10/140日別、20店日重複は合算0。raw0/null/営業unknown/休業相当01-01・12-25/同mask対照を維持。2015の負の結果・四季違反を隠さず、事後救済なし。2015は既読探索的開発で、未知holdoutではない。

fresh macos-demand-immediate-alignment-20261015 + execution/readback/doc-records。全stdio/exit/source/state/closure/全年入力・確定block・直前2週・日付・支持理由/端点/係数/二scenario/失敗prefixを保存。親900/子870秒、Mac sampled footprint/peakRSS各2GiB。artifact通常24files768MiB/総32files1GiB/single32MiB/失敗8files256MiB、EvidenceStore16MiB512files/part256KiB/reserve2MiB16files。

FIT10=6,7,10,13,15,17,19,23,26,27、既読2013–2015だけ。2016–17/予約31–54/販促/正式holdout/Windows native/CARE/課金API/新取得/外部送信/Git push/削除/本番採用なし。Astraは明示依頼read-only1名、heartbeat PAUSED保持。全Bでも有限終了、同じ候補/選択窓で追加探索しない。既存変更/失敗/closed rootsを上書きせず、改善してもPSI採用を認定しない。
