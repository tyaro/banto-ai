# CARE-A-MAINT-20261016-r1 — 保全・点検の有限比較契約

2026-10-16 JST。[確認結果とsource](../results/care-metadata-contract-2026-10-16.md)、[機械設定](../../examples/configs/care-a-maintenance-20261016-r1.json)、[入力/学習view](../../artifacts/care-input-contract-20261016/learning.json)、[evaluator view](../../artifacts/care-evaluator-contract-20261016/evaluation.json)を一組とする。不一致・品質不足では停止し、結果に合わせて条件や対象を動かさない。現在はmetadata/条件固定までで、CARE学習・採点の実行契約を自動解除しない。

## 目的と一候補

保全担当者の点検候補を示すため、自作full forecasterの残差検知が、負荷に応じた温度中央値という単純な正常profileを超えるかを調べる。予測MAE・分位点のcoverageを異常予兆の成功へ読み替えない。遅い温度上昇をcontext正規化が吸収し、固定profileより検知しにくい可能性も事前仮説として残す。差がなくても陰性結果で一巡を終える。

Farm Aの3 Avg信号（generator DE bearing温度、gearbox oil温度、grid power）をmetadataの物理的役割から固定した。イベントの故障種類に合うfileだけを選ばず、12 anomaly/10 normalの全22fileを保持する。温度は原本unit `�C`のnative数値、powerは匿名scaleを維持し、工学的な絶対閾値を追加しない。

入力tensorは3信号だけ。asset/event/idは照合キー、train_testは区間指定、Aのstatusはoffline prefixの学習/選択/校正filterだけ。これらはモデル特徴量やtest警報gateにしない。event label/start/end/descriptionは評価者の別rootに置く。

## splitと時点

5foldのtest/validation/train assetとanchorは[split manifest](../../artifacts/care-metadata-inventory-20261016/split-manifest.json)のまま。trainは3asset各1anchorのtrain区間、validationは次の1assetのanchor prefix、testは残り1assetの全prediction区間。各assetを一度testにする。fileをrandomに分けず、同じassetを同じfoldの別splitへ入れない。

匿名化のためfile間の実時系列は分からない。trainでもanchor以外のprefixを結合せず、推論でも各fileのstateをresetする。同じ匿名timestampを同じ物理的観測と決めつけてdedupしない。これにより計測される時間は**record上のexposure**であり、重複しない実設備稼働時間とは限らない。

10分間隔、C128＝過去21時間20分、H32＝次5時間20分、P32。学習origin nのcontext `[n−128,n)` とlabel `[n,n+32)` は同一file内。gapを跨がない。警報に使うのはlead1のp50だけ。32leadは補助的な予測学習であり、5時間20分前の故障予知に成功したという主張ではない。

timestampが集計開始/終了のどちらかは原本だけで確証がないため、全rowの利用可能時刻を**記録時刻＋600秒**に固定する。row n−1までで予測し、row nの温度が利用可能になってから残差を計算する。event境界も同じ600秒shiftで比較する。時計はfile-local/source-naiveで、実UTCやcalendar特徴へ変換しない。

## 学習・選択・校正

| 項目 | 固定条件 |
| --- | --- |
| モデル | 既存SmallForecaster full、V3/C128/H32/P32/D64/L2/4heads、109,024 parameters、q=.1/.5/.9。独立初期化、MetroPT重み流用なし |
| 乱数 | 全foldでinit20261016、sampler20262016。同じseedでもfold間は独立試験ではない。実batch列を保存 |
| 更新 | CPU float32、batch8、4096更新。AdamW lr3e−4/betas(.9,.999)/eps1e−8/wd.01、foreach/fused false、grad norm1。threads2/interop1/deterministic、scheduler/early stopなし |
| fit支持 | 各train anchorで全160rowが3信号finite・status0・600秒連続の窓。asset等確率→適格origin等確率で置換抽出 |
| 尺度 | trainの各finite/status0 binを一度、asset等重みでmean/population variance。T=max(sigma,1e−5)、floor=max(.01sigma,1e−5)、float64→float32有限正検査。forwardの平均/scaleはcontextだけ |
| loss | 既存context正規化pinball、全target/lead/q等重み |
| checkpoint | validation anchorのtrain prefix先頭floor(.7N)rowだけ。512/1024/2048/4096の固定train尺度pinballをorigin/target/lead/q等重みで比較、厳密同値は早いstep。label窓をcut外へ出さない |
| alarm校正 | 同anchorのprefix後半30%。過去128rowと現在温度がfinite・status0・連続のlead1残差。prefix先頭への過去context参照は可、未来suffixをcheckpoint選択へ返さない |

Aのstatus0は学習用の回顧的annotationで、無故障の真値や実運用で即時利用できるtagとはしない。testではstatusを無視し、停止・idle等を事後に消して性能を上げない。

## baselineと警報

baselineは各eligible train originの過去power[n−1]と温度[n]から作る。一度だけのtrain weighted quartileで最大4負荷binを作り、bin内の温度weighted medianを予測する。重みはasset均等、asset内pair均等。境界値は低いbin、empty binは最寄りnonempty bin（同距離は低い方）へ写す。nonempty binのpairが128未満なら停止し、testを見てbinを増減しない。

両手法のscoreは2温度の `max(abs(y−p50)/R)`。共通Rはtrainだけの温度MAD×1.4826、floor1e−3 native。weighted quantileは逆経験CDFとし、累積重みがp以上になる最小値。各値のweight/同値結合/float64演算はlearning viewに固定した。

閾値は手法別にvalidation校正scoreの99.5%点（昇順index `ceil(.995N)−1`）、超過は厳密`>`。3連続超過でその3点目の利用可能時刻にOPEN、3連続非超過でその3点目にCLOSE。cooldown0。gap/欠測では直前eligible時刻＋600秒で閉じcounterをreset。file末も同様、別fileへalarm stateを持ち越さない。testイベントの正解で閾値・持続・resetを変えない。

baselineは共通支持の警報に加え、lagged power＋現在2温度が揃う1-lagの**native支持**でも、同じprofile/閾値・別alarm stateを保存する。モデルの128row待ちによる可用性低下を、baselineも待たせる比較だけで隠さない。native結果は追加モデルや追加調整ではない。

## 真値・主指標・判定

全5foldのcheckpoint、閾値、neural/common-baseline/native-baselineの予測・score・警報・支持をfreeze/pinした後に、evaluatorだけがlabel manifestを読む。監査では既にevent metadataを参照したため、正式な未知holdoutとは呼ばない。学習/推論consumerのtruth非依存は別途検証する。

主hitは、shift済みの推定異常期間 `[event_start,event_end]` 内で新たにOPENした最初のepisode。同一episodeを複数eventへ重複計上しない。期間開始前からactiveなepisodeは別表示し、主hitに加えない。未検知は残す。

先行時間proxyはevent_end利用可能時刻−OPEN時刻。event_endを実故障時刻と保証しない。正規化earlinessは `(end−open)/(end−start)` を[0,1]にclipし、miss=0で全anomalyを平均する。検知できたeventだけの平均を主指標にしない。実際の点検に何時間必要かは未設定なので、業務合格を出さない。

正常eventのprediction区間内OPENを誤警報episodeとし、eligibleな `[availability,availability+600秒)` をrecord-hourとして分母にする。anomaly fileの期間外警報は別表で、推定期間外を確実な健康truthと断定しない。主指標はasset macroのevent検知率、正常1000 record-hour当たり誤警報、正常警報時間割合、miss込みearliness。実数、pooled率、全event/asset、支持・censor時間も必須とする。

探索的追加価値の条件は、common支持でneuralのmacro検知率がstrict改善し、誤警報率・警報時間割合が非増加、earlinessが非低下。native baselineと可用性も必ず併記し、common支持での成功だけを運用優位へ広げない。これは固定した一比較の記述的判定で、制約を満たす係数探索ではない。

この最初の契約は元論文/公式CARE-scoreの完全再現ではなく、CARE合成scoreを合否に使わない。公式scoreとの比較を将来行う場合は、実装版と算式を別に固定して追加する。

## 品質・資源・終了

観測zeroはvalid、欠測/nonfinite/float32 overflowはinvalid mask。0埋め、補間、値のclampなし。testの共通支持は128過去3信号と現在2温度のfinite性/600秒連続だけで決め、status/event labelでは決めない。最低fit4096 origins/anchor、selection256、calibration512。各prediction fileの共通支持70%以上、各anomaly期間も70%以上かつ非空、各正常assetのeligible record-hour24時間以上を要求する。不足時はfile差替え/黙ったevent除外をせずcampaign incomplete。

70%は**構造監査後・センサー数量decode前**に決めた研究上の可用性床。最小の構造支持はevent22の892/1148＝77.7003%。有限値検査でさらに下がる可能性があり、数値入力の準備まで適格とは認定しない。支持の分母と条件を数量/性能確認後に緩めない。

5foldを順番に実行、各親900/子870秒、各physical footprint/peak RSS2GiB、親合計最大4500秒。第5foldはfreeze後採点も同じ子枠内。各artifact normal24file/768MiB、total32file/1GiB、single32MiB、失敗reserve8file/256MiB。Evidence16MiB/512file・part256KiB・失敗reserve2MiB/16file、stdio上限も維持。1foldでも未完/非有限/境界違反なら残りを止め、追加seed/延長/再探索なし。

次は22fileの3信号を、quality mask・source ID・file-local時刻offset付きの32byte/record中立形式へ準備する。one-event binary×22＋manifest＋closureを1root最大24fileに収め、source/stdio等は別の実行記録rootへ保存する。実consumerのlabel注入・未来入力・reset境界を確認してから、別の明示実行指示で有限学習へ進む。今の`can_launch_learning/predictions/scoring`はfalse。

Rustはこの入力意味、mask/時点、forward/loss/backward/optimizer、モデル/学習状態保存再開、alarm state/reset、bantoのAPI/jobを含めて最終移植する。p50を需要の平均数量や`Forecast.mean`へ読み替えない。需要・2015・Windows native/正式holdoutの既存境界、旧変更/失敗/closed roots、heartbeat PAUSEDを維持する。
