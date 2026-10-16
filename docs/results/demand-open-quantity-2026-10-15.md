# 営業日相当の数量・静的fitの有限比較（負の結果）

2026-10-15 JST。[固定契約](../research/demand-open-quantity-design-2026-10-15.md)によるfit310/inner60/outer50の比較を一回完了。休業相当01-01/12-25、raw quantity/null、同仮定mean28の対照、2015二cohort二labelを維持。新ridge1fit/NN0、2015fit/calibration0。

原fit300に2014元日の10窓を追加し、gateを学習の日次/14日総量損失に組み込んだ。標準化は非休業4330dayだけ、暦支持45（Jan2〜4を追加）、元尺度uとlambda0.01/72列を固定。原観測0は保持。過去28日の休業相当日を除く曜日平均は最低2件、少なければ原mean28の理由付きfallback。2014で使う固定月日は2013の全10店の0/欠測だけでも支持され、2015による変更はない。

inner60ではglobal delta=0.08934665666291555*u/非休業日を推定したが、共有回帰のcalibration alphaは0（日次covariance−0.00001213920615064093/総量−0.00013848343812205804）。outer50のjointはmean28/open_mean28/alpha0回帰とも0.070886932612、level_corrected0.085838010719で悪化。事前tie順で主はmatched_mean28へ固定し、2015で変更しない。

| cohort / label | 主joint | 同仮定mean28 joint | 主の同仮定対照比 |
|---|---:|---:|---:|
| 元日10窓・観測（仮定labelも同じ） | 0.150788772064 | 0.150788772064 | 0% |
| 原250窓・観測のみ | 0.077466315137 | 0.077466315137 | 0% |
| 原250窓・欠測0仮定 | 0.077395893672 | 0.077395893672 | 0% |

新主は対照そのものなので模型改善を認定しない。旧rolling+休業maskとの比較では元日joint6.242177%改善だが、原250窓観測1.845212%悪化/欠測0仮定1.828297%悪化。旧結果を上書き・本番方式変更しない。事前副比較のopen_mean28は原250窓観測joint0.076966643479（同対照約0.645%改善）、元日には変化なし。level_correctedは元日joint0.131835188686に改善したが、原250窓観測joint0.086516065124に悪化。2015を見て副方式を主へ昇格しない。一律上方補正の不安定さを保存する。

全260予測の休業mask、250窓3490日240総量/欠測0仮定3500日250総量、元日10窓140日10総量を維持、20店日重複を合算0。原actual/nullを保持し、side仮定の10個だけをimputed flag付き0とした。

macos-demand-open-quantity-20261015は21files/12,923,513B/complete。全source/config/310fit・inner/outer・beta/選択/260input・予測label前後/二labelsummary/closureを保存。execution-records complete、新8fixture/stdout/stderr/exit0。readback-records completeで310fitの期限制限/10gate/inner alphaのscalar再計算/選択・全260予測の主固定・閉鎖0・raw/scenario支持・sourceと原roots不変を確認。child6.033935秒/親11.614762秒/Mac footprint283,181,920B/peakRSS322,699,264B、全上限内。

次はこの2014内の負の結果に基づき、数量関係の時間変化を扱う。過去365日の確定labelだけで2014内の係数を更新し、そのraw予測をinner/outerで校正・選択、最終2014以前の係数を2015前に凍結する。2015labelでfitしない別契約へ進む。閉鎖した本負の結果を保持し、同staticfitを反復しない。

Windows固有/OS依存包括suiteは新実行0/未検証、2016–17/予約31–54/販促/正式holdout/CARE/新取得/外部送信/push/削除/追加agentなし。既読探索的評価/formal_permission=false/PSI採用0/原変更・失敗・closed roots保持/Mac未commit。
