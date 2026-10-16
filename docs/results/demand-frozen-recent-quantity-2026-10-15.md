# 営業日数量・14日総量の改善検証：2014内では補正が支持されず

2026-10-15 JST。人の「休業相当日維持/営業日数量・総量過小改善/2014以前で調整/同仮定mean28比較/観測と欠測0仮定分離」を受け、[static比較](demand-open-quantity-2026-10-15.md)と[最近の係数を凍結する契約](../research/demand-frozen-recent-quantity-design-2026-10-15.md)の二工程を完了した。

同じ休業仮定のmean28を安定して上回る新しい補正は得られなかった。static/365日更新の両gated ridgeは2014inner60でalpha0となり、outer50の事前tie順により新比較の主はmatched_mean28。2015で方式を差し替えず、正負の結果を保存した。旧rolling+休業maskの成績とstateは維持し、新主を本番へ採用しない。

## 実装と2014内の選択

休業相当01-01/12-25とoperating_status unknown、別assumed_closure、原true0/nullを保持。原mean28+未来休業maskが対照。open_mean28は過去28日の休業相当日を除き、曜日2観測以上（不足は元mean28へ理由付きfallback）から数量を求める。非休業のtrue0は含める。context統計/残差profileも数量branchから休業相当日を除き、raw観測とモデル使用maskを別保存した。

fit310は元fit300+2014元日10窓で、全target末日<2014-07-01。原尺度u・72列・lambda0.01を固定し、非休業targetから暦支持45（Jan2〜4の3列追加）を計算。非休業4330dayだけで標準化し、gateを日次/14日総量の両損失に入れた。2014に使う休業相当2日も2013の全10店の0/欠測だけで支持されることを別保存。2013学習への固定仮説適用は後のfit時点の知識で、2013当時の確認済み営業予定とは呼ばない。

static比較ではinner60でdelta0.08934665666291555*uを推定したがouter50 joint0.085838010719で対照0.070886932612より悪化。static ridgeのalpha0。過去の数量関係の時間変化を検証するため、次の工程は2014内の各originで過去365日/全14label末日<originの全10店均等poolだけを使ってgated ridgeを12回fitした。

最近のfitでもinner60の日次covariance−0.00026473577974428026/総量−0.0004158709392923815でalpha0。outer50はmatched_mean28/open_mean28/recent_gated_ridgeの全てjoint0.070886932612で同点、事前順でmatched_mean28。全10窓の跨ぎ期間は校正/選択外、完了後のfitにのみ使用。

2014で方式/alphaを固定した後、2015-01-01以前の365日にある220窓（各店22）/最大label2014-12-15で最終stateを一回fitし、そのstateを2015前に保存・全2015で凍結した。成功runは13solve、2015fit/校正/alpha変更/NNfit0。2015のcontextは発行日前56日だけ、補正係数は2014以前だけから求めている。2014内で更新し2015で凍結する差は残るので、完全な同条件online評価や未知性能を主張しない。

## 固定主の2015結果

以下のprimaryは同仮定mean28そのものに戻るため、対照比の追加改善は0。元日0の処理は全10店で維持。original250（25origin×10店）とnewyear10（Jan1発行Jan1〜14）は20店日重複があるため合算しない。

### 元日追加10窓：観測140日/総量10

| 方式 | 日次scaled MSE | 総量scaled MSE | joint | 日次MAE | 総量MAE |
|---|---:|---:|---:|---:|---:|
| baseline_proxy | 0.262994588221 | 0.038582955907 | 0.150788772064 | 70.719664714 | 678.340042333 |
| prior | 0.273683765368 | 0.047972107418 | 0.160827936393 | 72.797285178 | 730.311046467 |
| candidate | 0.262994588221 | 0.038582955907 | 0.150788772064 | 70.719664714 | 678.340042333 |

主の同仮定mean28比0.000000%、旧rolling+休業mask比6.242177%（負は悪化）。

| 副指標 | 同仮定mean28/主 | 旧rolling+休業mask |
|---|---:|---:|
| daily_bias | -39.180455405 | -42.725737486 |
| total_bias | -548.526375667 | -598.160324803 |
| daily_WAPE_percent | 23.327773020 | 23.928761245 |
| total_WAPE_percent | 15.774586042 | 16.857632687 |

### 原250窓：観測3490日/総量240

| 方式 | 日次scaled MSE | 総量scaled MSE | joint | 日次MAE | 総量MAE |
|---|---:|---:|---:|---:|---:|
| baseline_proxy | 0.134053954571 | 0.020878675703 | 0.077466315137 | 48.845588649 | 328.732636813 |
| prior | 0.132506798845 | 0.019618791454 | 0.076062795150 | 48.428857454 | 314.545816713 |
| candidate | 0.134053954571 | 0.020878675703 | 0.077466315137 | 48.845588649 | 328.732636813 |

主の同仮定mean28比0.000000%、旧rolling+休業mask比-1.845212%（負は悪化）。

| 副指標 | 同仮定mean28/主 | 旧rolling+休業mask |
|---|---:|---:|
| daily_bias | 1.179059349 | -0.102876029 |
| total_bias | 3.764422340 | -14.990657501 |
| daily_WAPE_percent | 17.067803322 | 16.960160066 |
| total_WAPE_percent | 7.852857053 | 7.564897374 |

### 原250窓：欠測10日を0と仮定/採点3500日/総量250

| 方式 | 日次scaled MSE | 総量scaled MSE | joint | 日次MAE | 総量MAE |
|---|---:|---:|---:|---:|---:|
| baseline_proxy | 0.133670943272 | 0.021120844073 | 0.077395893672 | 48.706029825 | 337.062916400 |
| prior | 0.132128207992 | 0.019884337854 | 0.076006272923 | 48.290489290 | 323.186777078 |
| candidate | 0.133670943272 | 0.021120844073 | 0.077395893672 | 48.706029825 | 337.062916400 |

主の同仮定mean28比0.000000%、旧rolling+休業mask比-1.828297%（負は悪化）。

| 副指標 | 同仮定mean28/主 | 旧rolling+休業mask |
|---|---:|---:|
| daily_bias | 1.175690608 | -0.102582097 |
| total_bias | 16.459668507 | -1.436149359 |
| daily_WAPE_percent | 17.067803322 | 16.960160066 |
| total_WAPE_percent | 8.104386707 | 7.822624891 |

元日追加では旧rolling+休業maskに対しjoint6.242177%改善、総量biasは−598.160325→−548.526376、総量MSE0.047972107418→0.038582955907。ただしこれは既に対照が出せる水準で、同仮定mean28を上回る成果ではない。原250窓では旧rollingの方が良く、新主は観測joint1.845212%悪化/欠測0仮定1.828297%悪化。元日だけ良い結果で全期間を改善したとは言わない。

観測onlyでは原actual/null/complete_labelを保持。欠測0仮定はChristmas10欠測だけscenario_actual0、raw_actualはnull/imputed flagを維持。原250窓は本当に観測された日3490、仮定で採点日3500/総量250になったものを実測と呼ばない。元日10窓は欠測なしなので両label定義は同じ成績。未解決labelがある期間を部分総量で採点しない。元日観測0の原因は休業と確定せず、ゼロだけのWAPEは未定義。

## 営業日相当の観測数量（休業相当日を除外）

| cohort | 真の観測日 | 方式 | scaled MSE | MAE | bias |
|---|---:|---|---:|---:|---:|
| newyear10 | 130 | baseline_proxy | 0.283224941162 | 76.159638923 | -42.194336590 |
| newyear10 | 130 | prior | 0.294736362704 | 78.397076346 | -46.012332677 |
| newyear10 | 130 | candidate | 0.283224941162 | 76.159638923 | -42.194336590 |
| original250 | 3490 | baseline_proxy | 0.134053954571 | 48.845588649 | 1.179059349 |
| original250 | 3490 | prior | 0.132506798845 | 48.428857454 | -0.102876029 |
| original250 | 3490 | candidate | 0.134053954571 | 48.845588649 | 1.179059349 |

営業日相当は確認済みopenではなく、固定休業仮定に該当しない日という意味。欠測0仮定で追加した10日はこの数量評価に含めない。元日後の正値130日では過小が残り、同仮定mean28を上回る数量補正は選択できなかった。

## 事前副候補の結果と不採用理由

staticのopen_mean28は原250窓の観測joint0.076966643479で同仮定mean28比0.645018%改善、欠測0仮定joint0.076900571903で0.639985%改善したが、元日追加では変化なし。改善は得られても2014outerでは同点なので主へ昇格しない。旧rollingよりも原250窓で劣る。

staticのlevel_correctedは元日joint0.131835188686で同対照より良いが、原250窓観測joint0.086516065124に悪化（同仮定mean280.077466315137）。2014outerで既に悪化しており、一律の上方補正は採用しない。新しいrecent_gated_ridgeはalpha0なのでopen_mean28と同じ成績。

同休業仮定mean28を安定して上回る主方式の追加改善0。今回のfinite比較は負の結果として閉じ、2015で倍率・lambda・期間や方式を合わせ直さない。閉鎖した旧主結果の1.811781%/欠測0仮定1.795471%改善は元reportのまま保持する。採用、PSI発注損失、因果、有意性は認定0。

## 保存・実行の失敗・検証

staticはmacos-demand-open-quantity-20261015（21files/12,923,513B/complete）、同execution/readback complete。新8fixture pass。最新はmacos-demand-frozen-recent-quantity-20261015-v2（19files/4,995,287B/complete）、同execution/readback complete、新7fixture pass。合計15種類の新境界確認。

recent初回はMacCheckpoint本体をcallbackとして渡す実装ミスで、最初の2014fit後・2015評価前にTypeErrorとなった。failed model/execution rootを保持。最初の一時betaは保存前に失われ、保存済みとは主張しない。guard.checkを渡し、fit前及びjournal追加後に計測する順へ修正し、v2の全13stateを保存。科学条件を変更せず、当該実装修正で一回再実行した。初回summaryが存在しない段階で表示inspectionがFileNotFoundErrorになった記録も隠さない。

readbackで430past packetのmetadataから全13poolの365日/ラベル末日<origin/均等支持を独立再構成し、全stateの標準化と正規方程式残差を確認（新solve0）。final220窓/last label2014-12-15、inner alpha scalar再計算、outerの固定tie、2015中fitなし、260予測の主役固定/休業0/raw null/scenario支持、scalar日次・総量MSE/MAE、原source/閉鎖root/失敗保持を確認。

成功recent child2.610132秒/親5.092324秒、Mac sampled footprint286,983,008B/peakRSS323,682,304B。static child6.033935秒/親11.614762秒/footprint283,181,920B/RSS322,699,264B。親900/子870秒/各2GiB/保存上限内。hard OS cap/Windows private bytes同等性の主張0。全child stdio/exit/source/state/closureと既知NumPy警告を保存。

doc-recordsは両契約/結果/引継ぎ/報告値/links/closure/PAUSED設定/Git差分空白を照合。共通CPU/Macの新検査をpass、Windows固有/OS依存包括suiteは新実行0/未検証。2016–17/予約31–54/販促/正式holdout/CARE/課金API/新取得/外部送信/push/削除/追加agentなし、原変更・失敗・closed roots保持、Mac未commit/formal_permission=false/製品採用0。

次に必要なのは、2014内の複数季節で水準補正の符号が再現するか、元日直後の正値数量を学習・検証で分けて支持を確保できるかという設計。現在の内検証はQ3/Q4で、元日影響の検証支持が不足する。2年/同暦10店を独立例として水増しせず、2015元日の好結果だけで季節限定補正を選ばない。今回の直接委任の二比較を完了しheartbeat PAUSEDを保持する。
