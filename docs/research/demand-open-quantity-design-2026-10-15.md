# 休業相当日0を保持する数量・14日総量の有限比較

2026-10-15 JST、人の「営業日の数量予測/14日総量の過小予測改善」「調整は2014以前」「同休業仮定mean28比較」「観測/欠測0仮定の2015評価分離」を今回の委任とする。旧成果は保護し、以下の一回の有限比較を実行前に固定する。

## 固定する休業仮説と情報時点

2015には前unitで2013/2014だけから固定した01-01/12-25の休業相当maskをそのまま使う。operating_status unknown/assumed_closure別field、原観測0/null/欠測maskを保持し、確認済み休業へ昇格しない。2014内部調整で使用する同2月日は2013年の全10店の0/欠測だけでも支持されることを、2014より前の情報として別に確認する。2013の学習窓には後の2014fit時点で判明した固定仮説を適用するが、2013当時確認済み営業予定という再現は主張しない。2014時間調整は2013証拠のみ、2015は既存2013/2014証拠で、2015label/maskによる変更0。

既存FIT10店/尺度uを維持。origin前56日だけのquantityを使用。営業日相当の曜日平均は過去28日で休業相当日と欠測を除外し、各曜日2観測以上で計算する。2件は28日に最大2休業相当日が入っても残る同曜日標本への固定規則で、2015最適化しない。2未満は原mean28でfallbackし理由を残す。原true0は休業仮定該当日だけ除外し、それ以外の営業状態不明の実0は平均に含める。raw観測とmodel用除外maskを別保存。56日のcontext統計/残差profileも休業相当日を数量branchから除くが、原履歴を変更しない。

## 四候補、調整は2014以前

候補順/tie<=1e-12は matched_mean28（原mean28+同休業mask）、open_mean28（休業日を過去平均から除く）、level_corrected（open_mean28+非休業日にdelta*u）、gated_ridge（open_mean28+共有回帰、休業gateを学習損失に含む）。δは日次/総量jointの最小二乗でinner60から一つだけ求め、過小の補正としてmax(0,C/E)とする。休業日はδを加えず0維持。

gated_ridgeは元fit300に2014-01-01発行/01-01〜14の10店を追加したfit310のみで一回solve。全target終了<2014-07-01、元fitに同originがないことを確認。元日の観測0を保持し、positive dayと14日総量を同時に学習する。全310targetは完全labelを要求、欠測を訓練label0へしない。原u、72列（intercept/8残差/2context/60future-calendar/lead）、lambda0.01を固定。暦56支持はfit310の観測済み非休業targetのみから再計算して、Jan2〜4の支持も取り込む。標準化はfit310の非休業dayだけでmean/popstd、std<=1e-12 inactive、intercept mean0/std1。

標準化Xに非休業maskを掛け、基準Bも休業日0、y=(Y−B)/u、.5日次MSE/u²+.5完全総量MSE/(14u)²+lambdaの正規方程式でbetaをsolveする。intercept非penalty。予測はgate*relu(B+uXbeta)で、休業を学習後に初めて取り除く総量齟齬を避ける。gated_ridgeのalpha[0,1]は原daily/total非悪化上限付きcalibrate式をinner60だけで固定。δ/alphaの再調整を2015でしない。

2014time120は境界2014-10-01でinner60/outer50/crossing10。innerでδとalphaを固定、outer50でjoint最小の方式を選ぶ。crossingは調整・選択外。既存の同店舗数量が既読である探索的比較、blind/未知性能/有意性は主張しない。新NN/seed/LR/grid0、新ridge1solve、2015年中のfit更新0。

## 固定2015評価と対照

上記state/暦支持/δ/alpha/主方式をファイルに保存してから2015snapshotを解釈する。contextの2015過去実績は発行日前のものだけ使い、2015targetをfit/calibrateに使わない。元のmatched mean28を閉鎖保存値へ照合する。選択主に加え事前四候補を副比較として保存し、2015結果後に主を差替えない。

original250とnewyear10を分離、20店日重複を明記して合算0。観測評価の原actual/null/complete_label、仮定付き評価の原欠測かつ休業仮定該当日だけ0というscenarioを維持しraw_actual/imputed flagを保存。非pattern欠測はnull、未解決labelがあれば部分総量を採点0。同休業仮定mean28を主対照、原休業mask付きrollingはprior比較。営業日相当の数量MSE/MAE/biasと全14日MSE/biasを併記し、元日0の誤差と正値日の誤差を混同しない。

新fixture：当日/未来getter拒否、休業0と非休業true0/欠測の平均、最低2件/理由付きfallback、calendar支持のfit限定、gateが学習と総量に入ること、閉鎖日delta/alpha非適用、δ/α内外情報分離、fixed finite tie、原null/scenarioの支持。

fresh macos-demand-open-quantity-20261015及びexecution/readback/doc-records。契約/source/config/310fit・60inner・50outerのinput/profile/support/正規化beta/delta/alpha/内外予測と選択/2015全260label前後予測/2cohort2labelのsummary/全stdio/exit/失敗prefix/closure、旧source/roots前後不変を保存。親900/子870秒/Mac sampled footprint・peakRSS各2GiB、通常24files768MiB/全32files1GiB/single32MiB/失敗8files256MiB、EvidenceStore16MiB512files/part256KiB/reserve2MiB16filesを維持。

既存変更/失敗/closed roots保持、2016–17/予約31–54/販促数量/正式holdout/Windows native/CARE/課金API/新取得/外部送信/push/削除/追加agentなし。共通Mac検査とWindows固有/OS依存包括suite未実行を分離。heartbeat PAUSED保持、formal_permission=false/製品採用0。改善しなくても負の結果を保存し、同gridを反復しない。
