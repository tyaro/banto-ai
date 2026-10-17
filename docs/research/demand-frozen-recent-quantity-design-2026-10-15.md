# 最近の数量関係を2014までで学習し2015前に凍結する比較

2026-10-15 JST。同じ人の数量・総量改善委任を継続。[static数量比較](../results/demand-open-quantity-2026-10-15.md)の2014内の結果（ridge alpha0、Q3の一律上方deltaがQ4で悪化）から、古い数量関係を全期間固定する代わりに過去365日の関係を使う仮説を、2015の追加fitなしで検証する。原static root/負の結果を保持。

休業相当mask/未知営業状態/raw null/scenario/尺度u/最低2件のopen_mean28/72列/lambda0.01/暦45支持/conditional contextを前契約どおり固定。候補順matched_mean28/open_mean28/recent_gated_ridge、tie1e-12。global delta候補はstatic結果に基づき除き、新hyperparameter/gridを作らない。

2014time120の各originに、元fit300+元日2014の10+そのoriginより前に確定したtime packetだけから、packet origin>=origin−365かつ14label末日<originをmetadataで選び、全10店均等/最低140でgated ridgeをfit。標準化もそのpoolの非休業dayのみ。全10店の同origin予測を固定してからpacketを後日のpoolへ追加する。12originの2014raw予測は最初に保存し、inner60だけでalphaを前式で固定、outer50で方式を選択。crossing10はcalibration/選択外だがlabel確定後のfitには利用できる。

方式とalpha固定後、最終origin2015-01-01の前365日・全label確定packetをmetadataで選び、gated ridgeを一回fitしてstate/normalizationを保存する。2014元日packetは365日境界で含まれる。全targetは2014以前、当日の2015元日targetを含めない。合計13solve、NN0。2015の元日10窓と原250窓ではこの最終stateを全期間固定し、contextだけ発行日前の56日から作る。2015fit/calibration/α変更0。2014内部では更新して2015では凍結する差を明示し、完全な同条件online評価や未知性能を主張しない。

日次と14日総量・joint/MAE/WAPE/biasを同休業仮定mean28と比較。観測only/欠測0仮定、原250/元日10を分離し20重複合算0。副候補の2015結果後主昇格0、負の結果も保存。主がmean28なら新模型改善なしと報告。

fresh macos-demand-frozen-recent-quantity-20261015及びexecution/readback/doc-records。全13pool/label期限/均等支持/標準化・beta・state、2014raw予測/校正/選択/最終freeze、260予測前後/原labelとscenario、source/stdout/stderr/exit/失敗prefix/closureを保存。親900/子870秒・Mac footprint/peakRSS各2GiB、通常24files768MiB/全32files1GiB/single32MiB/失敗8files256MiB、EvidenceStore16MiB512files/part256KiB/reserve2MiB16files。

旧source/変更/失敗/closed roots保持、2016–17/予約31–54/販促/正式holdout/Windows native/CARE/新取得/課金API/外部送信/push/削除/追加agentなし。共通Mac検査とWindows固有/OS依存未実行を分離、formal_permission=false/採用0、heartbeat PAUSED保持。この有限比較を検証・文書保存まで完了して空回りしない。

初回はMacCheckpoint本体をcallbackとして渡したTypeErrorで最初の2014fit後に停止。2015評価は未開始。failed model/execution rootsを保持し、callbackをguard.checkへ修正。guardチェックをfit前及びjournal追加後に置いて、次回の失敗prefixに完了stateを残す。初回の最初の一時betaは保存されなかったことを記録し、修正後はfresh v2 rootへ同条件で実行する。科学条件や選択条件は変えない。
