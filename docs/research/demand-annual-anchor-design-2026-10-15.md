# 前年同曜日の季節変化アンカーによる方向確認と補正幅制限

2026-10-15 JST。人の「Q2過大/Q4過小を店・発行日別にAstraと分析し、誤方向/行き過ぎを抑える方法で改善」に従う。保存2014の固定quarter-consensusを診断すると問題のQ2過大/Q4過小増は全て誤方向で、実績を跨ぐ行き過ぎは0。Q2raw過大増は4/23店10・6/18店13、Q4raw過小増は11/5店6/15/17。同方向の一律縮小だけでは当該非増加条件を満たせない。診断はmacos-demand-quarter-error-diagnosis-20261015-recordsへ保存。旧cause-diagnosis.jsonと混同しない。

今回は前年度の同曜日区間という別情報を追加する一つの仮説を、固定3候補（matched_mean28 / annual_anchor / anchor_cap）で有限検証する。性能計算前に本契約と[Astraレビュー](demand-annual-anchor-astra-review-2026-10-15.md)を保存する。FIT10=6,7,10,13,15,17,19,23,26,27、既読2013–2015のみ、新取得0。対照は同休業仮定mean28、営業unknown/原0/null維持。01-01/12-25の休業相当は確定休業と呼ばない。

発行日oの前年対応発行日はa=o−364日（52週、曜日整合のため固定）。前年参照は[a−28,a)、対応targetは[a,a+14)。全て現在oより前で、2013–2014の保存rawからだけ取得する。2012を要求する初期窓は範囲を拡げず支持不足で窓全体Bへfallback。2015の前年特徴も2014以前だけであり、当該2015targetは使わない。

前年分母は特徴用open-weekday参照で、元mean28の履歴規則と完全同一ではない。前年参照28日は非休業相当かつ真の観測だけで曜日平均を作り、全7曜日で最低3件必要。前年対応targetのうち現年open_maskがTrueの位置だけを比率の分子・分母に同じように使う。いずれかが前年の欠測又は休業相当なら窓全体Bへfallbackする（部分穴埋め比率なし）。分子は対象前年実績の和、分母は同じ位置への前年曜日mean予測和。分母<=0又は非finite・支持不足・B総量0はB。比率r=分子/分母を現在B総量へ掛ける。前年の営業日観測0は実績として保持し比率へ含める。現年休業相当日の予測は常に0。364日による月日ずれ/祝日移動/前年1反復の限界を記録する。

annual_anchor端点はB日別値×r。anchor_capは旧未校正consensus_raw端点の総量差とannual_anchor総量差が非ゼロ同符号の時だけ、小さい絶対差を採用する。符号不一致/0/支持不足ならB。両端点ともBに比例配分し、日別形状を変えず総量方向・幅を切り分ける。旧3信号や最新週の線形外挿を追加探索しない。幅制限は将来実績の行き過ぎを保証するものではない。

2014奇数130窓の実観測完全総量120（各Q30/30/40/20、各店3/3/4/2）だけで各Q・各候補のalphaを1回校正。過小/過大平均非増加の凸区間と総量MSE非悪化上限の中でC/Aをclip、energy不足は0。平坦境界は80桁Decimalで計算する。固定8係数で追加grid/店別fit0。2014選択偶数130のうち元日10を除いた通常120（各Q30、各店3）で両labelの各Q総量MSE・平均過小量・平均過大量が同mask mean28以下なら適格。MSEtol1e-12/数量平均tol1e-8、観測MSE最小・同点B、不適格ならそのQのみB。選択側で係数を縮小し直さない。

欠測0校正感度は報告だけでfit/追加guardには使わない。通常選択は欠測なしで両label同値、独立頑健性証拠とは扱わない。元日別10を報告だけに保ち、個店/個窓の非悪化は要求/保証しない。既読2014の探索と交互分割/context依存/支持の薄さも保持する。

policy/state/四季方式を2015入力前に凍結。2015は発行前contextと前年raw特徴を再計算するだけ、係数・方式fit0。通常250観測3490日240完全総量と、欠測0仮定3500採点日250総量を別保存、元日10/140日を別保存して20店日重複を合算しない。2015四季の違反と負の結果も保存し、結果後の主昇格/差替えなし。旧27state/最終250窓last label2014Dec16を再利用、新ridge/NN0。

fresh macos-demand-annual-anchor-20261015 + execution/readback/doc-records、source/raw pin/全入力支持・fallback理由・端点/係数/標本journal/予測label前後/二scenario/stdio/exit/state/closureを保存。親900/子870秒、Mac sampled footprint/peakRSS各2GiB、従来artifact通常24files768MiB/総32files1GiB/single32MiB/失敗8files256MiB、EvidenceStore16MiB512files/part256KiB/reserve2MiB16files。旧変更/失敗/closed roots上書き削除なし。

全Bでも有限終了し、同じ選択窓で再校正・探索反復しない。2016–17/予約31–54/販促/正式holdout/Windows native/CARE/課金API/新取得/外部送信/Git push/本番採用なし。Astraは人が依頼したread-only1名のみ。heartbeat PAUSED維持、改善してもPSI製品採用と認定しない。
