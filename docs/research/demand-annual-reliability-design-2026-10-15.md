# 発行前の実績による前年情報の信頼性判定

2026-10-15 JST。人の新依頼「2015悪化原因をAstraと分析/前年の信頼性を発行前実績で判定/有効局面のみ補正/2014以前だけ調整/四季平均両側非増加/同休業mean28/label分離」に基づく。[Astraレビュー](demand-annual-reliability-astra-review-2026-10-15.md)を先に保存する。

旧固定annual-anchorの2015だけを別診断root（macos-demand-annual-2015-diagnosis-20261015-records）へ保存。通常観測240完全総量中74窓変更、誤方向32/実績跨ぎ16/実績方向26、純総量MSE差+.000935521157/平均過大+9.367099909/過小−1.891114936。誤方向は6/2店13、9/8店15/10等が大きい。跨ぎが必ずMSE悪化とは限らず分類と指標寄与を分ける。旧成績/予測/source/失敗を変更しない。新gateの2015性能は診断時に計算せず、悪化日専用の閾値/除外店は作らない。

仮説は「前年の形が直近の2つの確定区間で有効だった局面に限れば、前年1反復の誤方向/過剰補正を減らせる」。固定3候補 matched_mean28 / validated_anchor / no_cross_anchor。両新候補は前回の未校正annual_anchor端点（日別B比例）を使い、信頼gateだけ変える。raw-cap/別期間/閾値grid/店別係数を追加しない。

current発行日oのlag14とlag28の過去発行日i=o−lagを再構築する。各iの参照は[i−28,i)、actualは[i,i+14)。2actual区間は非重複、全ラベルは現在oより前。現在past56（o−56..o）の真の観測/欠測を使い、参照曜日meanは原matched_mean28の観測0込み・欠測除外・各曜日>=3件、未来休業相当01-01/12-25は予測0。当時保存予測ではなく現在の休業仮定による反実仮想hindcastで、真のactual14に欠測があればそのblockは不支持。positive実績と休業仮定の矛盾があっても実績を消さない。

各iの未校正前年anchorには[i−392,i−350)の42日（参照28+target14）も必要。lag28では最古o−420。既読2013–2014のFIT10保存rawだけから追加42日×2を取得し、2012はNoneとして支持不足、取得範囲を広げない。全日付がi未満/現在o未満であることを検査。前年targetの必要日に欠測/休業相当、全年曜日支持不足、0分母ならBへfallbackし、fallbackや無変化を検証成功とは数えない。元の前年比率/364日/同じ対象位置・現在mask・原0/nullを保持する。currentanchor自体も支持が必要。

validated_anchor: 両blockとも、未校正anchor総量の二乗誤差/(14u)^2 が同Bより厳密に1e-12を超えて改善した場合のみcurrentanchor端点を許す。uは当該rowの2013固定model尺度。比較閾値は既定数値許容差で、選択しない。両block支持・真の14日実績・strict改善が必要。どちらか失敗/不足ならcurrent候補B。

no_cross_anchor: validated条件に加え、両blockそれぞれで平均でない単窓の過小量と過大量がB以下（tol1e-8）の場合だけ許す。過去の通り越しも抑える条件だが、current/futureの実績方向や両側非悪化の保証ではない。別校正alphaによりvalidatedより最終補正が大きくなる場合もある。gateは新alphaと独立した未校正端点で固定し、alpha依存の循環校正を避ける。

2014奇数130窓/実観測完全総量120（四季30/30/40/20、各店3/3/4/2）だけで各Q・2候補のalpha8個を一度校正。過小/過大の凸適格区間を80桁Decimalで求め、各Q総量MSE非悪化上限の中でC/Aをclip。2014偶数130から元日10を除く通常120（各Q30/各店3）で、両label別に各Q総量MSE・平均過小・平均過大が同mask mean28以下なら適格。MSEtol1e-12/数量tol1e-8、適格な観測総量MSE最小・tieはB、不適格ならそのQだけB。選択側の縮小/再調整なし。

全年の全窓を採点分母に残し、完全数とcurrentannual支持・過去block支持・各gate作動・非ゼロ方向支持を区別して保存。2014Q1はJan15/Feb12が年参照不足でfallbackとなり、暦上Mar12だけ支持可能。薄い支持/2014再利用/交互分割/context依存を明記。元日10別報告、Q4校正欠測0感度は報告のみでfit/追加guard不使用。通常選択に欠測がないため両label同値は独立証拠ではない。

policy/四季方式/旧最終state（250窓last label2014Dec16、旧27state検証継承）を2015入力前に凍結。2015の発行前実績で固定特徴とgateを再計算するだけで、係数/閾値/方式のfit・更新をしない。通常250観測3490日240完全総量/欠測0仮定3500採点日250総量を分離、元日10/140日別・20店日重複合算0。2015四季の違反・負の結果も保持し、事後の主差替えなし。2015は既読探索的開発評価であり未知holdoutではない。

fresh macos-demand-annual-reliability-20261015 + execution/readback/doc-records。全stdio/exit/source/state/closure/原校正pin/実績ブロックと前年追加入力・日付・支持理由/端点/係数/二scenario/失敗prefixを保存。親900/子870秒/Mac sampled footprint・peakRSS各2GiB。artifact通常24files768MiB/総32files1GiB/single32MiB/失敗8files256MiB、EvidenceStore16MiB512files/part256KiB/reserve2MiB16filesを維持。

全Bでも有限終了、同じ候補や選択窓で探索を反復しない。FIT10（6,7,10,13,15,17,19,23,26,27）/既読2013–2015のみ。2016–17/予約31–54/販促/正式holdout/Windows native/CARE/課金API/新取得/外部送信/Git push/削除/本番採用なし。既存変更/失敗/closed roots保持、heartbeat PAUSED維持。Astraは人の明示依頼read-only1名のみ、改善してもPSI採用を認定しない。
