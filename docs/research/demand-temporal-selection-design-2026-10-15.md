# 2014年内の時系列分離選択（実行前固定）

2026-10-15 JST、heartbeat banto-ai-mac。仮説は、同じ内部期間でNN checkpoint/補正係数/方式をまとめて選ぶ楽観性を減らすため、前半でNNと係数を固定し、後半で方式を選ぶと、既存店の翌年平均販売数量予測の改善が安定するか。既読開発から着想した探索的検証で、blind/未知性能/有意性/PSI採用を主張しない。

原fit10店(6,7,10,13,15,17,19,23,26,27)、fit300、原u、暦42列支持、56→14日、mean28、欠測扱いを固定。2014 time120をmetadataで2014-10-01境界に分割する。全14 label終了日<境界のinner60、origin>=境界のouter50、跨ぎ10はcheckpoint/alpha/方式選択の対象外。跨ぎpacketは旧rollingと同じく全label末日を過ぎてから後日のfitだけに入る。

新NNは原StatisticalFeatureMean30369parameter、CPUfloat32、seed20261014、Random(seed)の300fitから8件×最大4096更新、AdamW lr3e-4/betas(.9,.999)/eps1e-8/wd.01/foreach=false/fused=false、grad norm1。inner60のjoint MSEのみを0/128間隔で監視し、EarlyStopper(warmup512,patience6,min_relative1e-4)で停止。厳密最良checkpointを保存する。一軌跡のみ、旧time120選択NN3328はouter選択に使わない。fit/inner入力とtargetだけを学習中に組み立てる。

最良NNとrolling rawについて、inner60だけで原calibrate式のalpha[0,1]を独立固定する（日次/総量の非悪化上限あり）。calibrateが返すperiod表記はこのunitでinner60に訂正する。outer50に初めて適用し、joint最小、差<=1e-12のtie順mean28→新NN校正→rolling校正で主方式を選ぶ。outerではcheckpoint/alpha/λを変更しない。crossingのactualは選択器に渡さない。方式とstate pinとalphaをファイル保存してから2015 snapshotを解釈する。

rollingはclosed macos-demand-rolling-ridge-20261015のinternal raw120及び37個の因果的365日/72列/lambda0.01 stateを再利用。新ridge fit0。2015では各originのclosed stateをpast-only特徴に一度forwardし、rawを再構成して新inner alphaを適用。旧alpha0.5934170450546611で再blendした値と旧rolling_fixedを許容誤差1e-8で照合し、旧alphaは新選択の入力に使わない。全37poolの末日境界と均等支持をmetadataで再確認する。閉鎖rootに追記しない。

2015は旧250要求/3490観測日/240完全総量を保持。新NN、rolling、mean28、旧NN（比較のみ）を事前固定で報告。主candidateはouter選択を維持し2015で再選択しない。日次/総量/同等jointの尺度正規化MSEを主、MAE/WAPE/bias/店/四半期を副。暫定2%改善/日次総量非悪化/支持不変は研究進展の参考で、PSI在庫損失や採用を認定しない。全予測labelなし保存後に既存actualと欠測を付与する。

新root macos-demand-temporal-selection-20261015、execution/readback/doc-records。親900秒、子870秒、Mac sampled physical footprint/peakRSS各2GiB（hard OS capではない）、通常24files768MiB/全32files1GiB/single32MiB/失敗8files256MiB、EvidenceStore16MiB512files/part256KiB/reserve2MiB16filesを維持。契約/source/fixtures/stdout/stderr/exit/sampler/initial/final/innerbest/state/curve/journal/closure、失敗prefixも保存。元root/source不変を前後照合。

2013–2015既読許可済み10店舗限定、正式holdout/2016–17/予約31–54/販促数量/Windows native/CARE/課金API/新取得/外部送信/Git push/削除/追加agentなし。Windows固有・OS依存包括testはこの共通CPU研究と分離し新実行0。formal_permission=false/製品採用0。新しい人の直接発言なら新実験前にheartbeatをPAUSED、scheduler起動は継続。後付けgrid/再runなし。
