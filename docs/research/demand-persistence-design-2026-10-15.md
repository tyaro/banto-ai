# 週変化の持続性と非減速による保留

2026-10-15 JST。人の新依頼「6/2店7過大補正をAstraと分析/持続性・反転兆候を発行前実績から判定/2014以前調整/四季平均両側非増加/同休業mean28/観測と欠測0分離」に従う。[Astraレビュー](demand-persistence-astra-review-2026-10-15.md)を性能計算前に保存する。

旧固定immediate-alignmentの2015店7だけを先に診断root macos-demand-persistence-diagnosis-20261015-recordsへ保存。4週総量4793.058→4620.009→4814.129→4923.27497。直近2週増加幅194.12→109.14597と減速だが、最新7同曜日差は5曜増/2曜減、中央値+16.56897で全体下降へ転じた証拠ではない。旧B誤差+233.863485へ+181.839130補正し過大+415.702615となった。新候補性能/係数は診断時に計算しない。既知例の減速から仮説を得た探索であり、2014だけで係数を決めても2015が独立検証へ戻るわけではない。

仮説は「前年の適合・直前整合に加え、曜日に広がった変化の持続と増勢/減勢が弱まっていない条件を確かめると誤方向を抑えられる」。固定3候補 matched_mean28 / persistent_anchor / nonweakening_anchor。中央値のみ等の追加候補、別期間、別減速閾値のgridは追加しない。2候補の端点は同じ未校正annual_anchor（日別B比例）、gateだけを変え、新alphaへ依存させない。旧cap方式を追加候補にしない。

旧aligned gate（過去2blockで前年未校正端点のstrict総量MSE改善・両側非増加、現在year_gap/直近水準差/週差の同符号）を維持。現在発行前の最新3週21日を暦上の同曜日7組へ並べ、全21日が真の観測かつ休業相当01-01/12-25以外であることを要求。真の観測0は有効、欠測は補完せず不支持、休業相当日に正値があってもrawを消さず不支持。支持不足は窓全体B。

3週をold/previous/recentとし、各曜日jの差d_old[j]=previous[j]−old[j]、d_recent[j]=recent[j]−previous[j]。Δ_old=sum(d_old)、Δ_recent=sum(d_recent)、m_old=median(d_old)、m_recent=median(d_recent)。符号関数はabs<=1e-8を0とする既定数量許容差。年の未校正総量差の符号をsとする。

persistent_anchorは旧aligned支持、21日支持に加え、Δ_old/Δ_recent/m_old/m_recentの全符号が非ゼロのsと一致した時だけ前年端点を許す。総量の方向と7曜の過半数方向を両推移で確認し、一部曜日の大きい増減だけで全体を判断しない。ただし既知店7も広い上昇であり、救済を保証しない。

nonweakening_anchorは同じ持続条件に加え、s*Δ_recent >= s*Δ_old−1e-8を要求する。これはs*(W_recent−2W_previous+W_old)>=−EPSという二階差で、正方向でも勢いが弱まる局面を保守的に保留する。反転確認/予測ではなく、自然に安定水準へ近づく良い減速局面を落としたり一時的加速を通したりし得る。中央週の揺れを二倍で受け、中央値確認があっても加速度部分は総量差に依存する。

期間は7日周期と既定の14/28/56/364だけ、年参照最古o−420は既読2013–2014FIT10 rawのみ。2012へ拡張せず支持不足B。最新週差・中央値・旧no_crossは同じ実績を共有し、独立裏付けが増えたとは扱わない。作動集合は旧alignedの部分集合だが、別alpha再校正で補正幅が増す場合があるため、作動数と最終幅を区別する。将来の方向/非跨ぎ/個窓・個店非悪化は保証しない。

2014奇数130/実観測完全120（四季30/30/40/20、各店3/3/4/2）のみで8季節alphaを一回校正。厳密有理数でunder/over凸適格区間を求め、各Q総量MSE非悪化上限内のC/Aへclip。2014通常選択120（各Q30/各店3、元日10別）で両label別の各Q総量MSE・平均過小・平均過大非増加を要求。MSEtol1e-12/数量tol1e-8、観測総量MSE最小・同点B、不適格Qだけ停止。選択側再校正/候補差替えなし。

不作動窓も全て採点分母へ残す。現在年参照/過去2block/旧aligned/21日支持/総量・中央値持続/非減速/非ゼロ端点/最終変更を四季・店別に保存。支持の薄さと2014既読探索・交互分割/context依存を明記。通常選択に欠測がないため両label同値は独立頑健性証拠ではない。Q4校正欠測0感度は報告だけ、fit/追加guard不使用。

policy/方式/旧最終250窓last label2014Dec16状態・27state検証を2015入力前に凍結、新ridge/NN0。2015発行前実績は固定特徴計算だけ、係数/閾値/方式の学習更新0。通常250観測3490日240総量と欠測0仮定3500採点日250総量は別保存、元日10/140日別、20店日重複合算0。原0/null/営業unknown/休業相当01-01・12-25/同mask mean28を維持。設計着想には既読2015診断を使用したと明記し、2015の反例・負の結果・四季違反も保存、結果後救済なし。

fresh macos-demand-persistence-20261015 + execution/readback/doc-records。全stdio/exit/source/state/closure/年・確定block・直前3週入力と日付・支持理由/端点/8係数/二scenario/失敗prefixを保存。親900/子870秒、Mac sampled footprint/peakRSS各2GiB。artifact通常24files768MiB/総32files1GiB/single32MiB/失敗8files256MiB、EvidenceStore16MiB512files/part256KiB/reserve2MiB16filesを維持。

FIT10=6,7,10,13,15,17,19,23,26,27、既読2013–2015のみ。2016–17/予約31–54/販促/正式holdout/Windows native/CARE/課金API/新取得/外部送信/Git push/削除/本番採用なし。Astraは明示依頼read-only1名、heartbeat PAUSED維持。旧変更/失敗/closed rootsを保持、支持消失/全B/2015未再現でも有限終了し追加探索しない。改善してもPSI採用を認定しない。
