# CARE保全支援の5fold実学習とイベント評価

2026-10-16 JST。TimesFM3を参考にした自作モデルの実用性を調べる[計画](../research/timesfm-inspired-practical-evaluation-plan-2026-10-16.md)とCARE-A-MAINT-20261016-r1に沿い、固定5foldの実学習・校正・予測と警報の保存・イベント評価を完了した。共通支持での探索的追加価値4条件をすべて通過したが、異常12件中の検知は3件に留まり、9件を未検知として保存した。保全用途の十分性や製品採用を認定する結果ではない。

人の「次に進みましょう」を、前工程で明記した5fold実学習への実行指示として[新しい実行記録](../../artifacts/care-learning-campaign-launch2-20261016/permit.json)へ保存した。[固定契約](../research/care-a-maintenance-contract-2026-10-16.md)、[数値入力](care-numeric-consumer-2026-10-16.md)、[train profileとschedule](care-training-preparation-2026-10-16.md)は変更していない。固定JSONのfalse flagsは凍結時点の履歴として保持し、新phaseで実行範囲を明示した。

## 固定した実行と時点の分離

Farm Aの5 asset/22 file/3 Avg信号をすべて保持した。各foldは別assetをtest、次のassetをvalidation、残3 assetの各anchor prefixをtrainとし、各assetが一度testになった。既存SmallForecaster full V3/C128/H32・109,024 parametersをseed20261016で独立初期化し、全fold各4,096更新、AdamW、batch8、固定sampler20262016の実抽出列を使った。5foldは独立seed5回ではない。公式重みやMetroPTの学習済み重みを流用しない。

checkpointはvalidation anchor prefix先頭70%の固定train尺度pinballで512/1024/2048/4096から選択した。全foldで4096が選ばれたが、これを収束の保証や追加学習の理由にしない。選択後にだけ同prefix後半30%でlead1残差を校正し、手法別99.5%逆経験分位点を固定した。温度2信号の残差をtrain共通MADで割った最大値をscoreとし、厳密な閾値超過3連続で3点目の利用可能時刻にOPEN、非超過3連続でCLOSEとした。

| fold | 選択窓数 | 校正score数 | NN閾値 | baseline閾値 |
| --- | ---: | ---: | ---: | ---: |
| 0 | 817 | 12,794 | 0.615902505 | 3.102657494 |
| 1 | 1,020 | 15,431 | 0.612096556 | 1.753675975 |
| 2 | 1,002 | 15,561 | 0.484286959 | 1.888574127 |
| 3 | 746 | 14,873 | 0.545819214 | 1.753675975 |
| 4 | 1,017 | 12,348 | 0.541007746 | 2.173359114 |

モデルに渡す値は過去128点だけで、現在温度は自身の記録時刻+600秒以降に残差へ入れた。test statusは保存/入力/gateに使わない。gap/欠測では最後のeligible時刻+600秒で警報を閉じ、確認counterをresetし、file間でもstateを持ち越さない。baseline nativeは同じprofile/閾値で独立stateを持つ。

全5foldの選択state・閾値・neural/common baseline/native baselineの予測scoreと警報を閉鎖し、[全件freeze](../../artifacts/care-learning-scores-20261016/freeze-before-truth.json)を保存してからevaluatorだけがevent labelを読んだ。最終foldの採点も同じ子870秒内で完了した。学習/選択/校正/推論roleへのevent truth読取りは0。metadata labelは前工程で既読なので正式blind holdoutとは呼ばない。

## 主結果はasset macro

| 手法 | event検知率 | 正常1000記録時間あたり誤警報episode | 正常警報時間割合 | missを0としたearliness |
| --- | ---: | ---: | ---: | ---: |
| 自作NN 共通支持 | 20.00% | 0.846560 | 0.064965% | 0.105462 |
| 負荷bin baseline 共通支持 | 6.67% | 1.071044 | 0.165809% | 0.045134 |
| 負荷bin baseline native支持 | 13.33% | 1.259778 | 0.181823% | 0.062379 |

全5 assetを等重みにした値である。共通支持でNNの検知率がstrict改善、誤警報率・警報時間割合が非増加、earlinessが非低下という事前4条件はすべてtrueだった。[判定](../../artifacts/care-learning-scores-20261016/decision.json)はこの一比較の記述的な探索判定であり、統計的有意性や業務合格ではない。

## 実件数と可用性

| 手法 | 異常の検知件数 | 正常fileの誤警報episode | 正常eligible記録時間 h | 同じ共通支持でのlead1 MAE generator / oil |
| --- | ---: | ---: | ---: | ---: |
| 自作NN 共通支持 | 3/12 | 3 | 4,246.667 | 1.101104 / 0.833559 |
| 負荷bin baseline 共通支持 | 1/12 | 5 | 4,246.667 | 7.124159 / 3.425806 |
| 負荷bin baseline native支持 | 2/12 | 6 | 4,343.167 | 7.124159 / 3.425806 |

MAEの温度単位は原本の「�C」を持つnative数値のままで、単位記号の修復や工学的閾値への変換はしていない。baseline native欄のMAEも比較用の共通支持で計算し、native警報の母集団とは分けた。予測誤差の低下だけで予兆検知の成功とは扱わない。

22 file/50,593 prediction行のうち、NNの過去入力が利用可能なのは47,851、現在温度とcadenceも揃う共通支持は47,834、native baselineは50,560だった。最小file支持77.7003%、異常区間81.9900%、正常asset24記録時間以上の固定床をすべて維持した。時間は匿名fileごとの利用可能record区間の和で、重複しない物理equipment-hourとは限らない。

baseline nativeだけが検知したevent22を残した。OPEN ordinal52632/52659はいずれもflags12（nativeとbaseline発行だけ）で、過去128点内のordinal52619に時刻gapがある。NNは履歴復帰待ちで発行できず、共通支持だけにbaselineを制限するとこの検知を隠す。共通支持での改善を、そのまま可用性込みの全面的優位へ広げない。

## 未検知とasset差

| asset | NN検知/異常数 | baseline共通 | baseline native |
| --- | ---: | ---: | ---: |
| A:0 | 2/3 | 0/3 | 0/3 |
| A:10 | 1/3 | 1/3 | 1/3 |
| A:11 | 0/1 | 0/1 | 0/1 |
| A:13 | 0/2 | 0/2 | 0/2 |
| A:21 | 0/3 | 0/3 | 1/3 |

NNの未検知eventは10, 22, 26, 42, 45, 51, 68, 72, 84の9件。A:11、A:13、A:21では検知0だった。またA:21の正常誤警報はNN2件、共通baseline1件で、平均の改善が全assetの非悪化を意味しない。これらを対象から除外したり、閾値・連続数・信号・checkpointをtest結果に合わせて変えない。

| NN検知event | asset | earliness | 注釈区間終端までのlead proxy h |
| --- | --- | ---: | ---: |
| 0 | A:0 | 0.800099 | 268.833 |
| 40 | A:10 | 0.685601 | 519.000 |
| 73 | A:0 | 0.096230 | 16.167 |

proxyは推定異常区間の終端までの時間で、実故障や保全期限までの先行時間を保証しない。元の注釈区間が長いこともあり、日数だけを故障予知の成功と読まない。未検知はearliness0で全異常の平均に含めた。注釈開始前からactiveだったepisode件数はNN/共通/nativeで0/0/0、anomaly fileの注釈区間外OPENは2/2/2で別保存した。区間外を確実な健康truthとして正常誤警報に混ぜない。

全event・asset・支持・censor・episodeは[per-event](../../artifacts/care-learning-scores-20261016/per-event.json)と[全指標](../../artifacts/care-learning-scores-20261016/metrics.json)に保存した。必要な点検準備時間や許容誤警報は未設定である。

## 独立検算と学習状態

追加した12の人工確認でOPEN/CLOSE時刻、厳密超過、gap/欠測/file reset、native独立state、校正index、開始前active、miss=0、macro、portable record、5fold freeze条件を検証した。実行後は[独立検算](../../artifacts/care-learning-independent-20261016/summary.json)で、保存済み全20 checkpointのvalidation予測から選択を再現し、全校正scoreのorder statistic、22 fileの支持・run単位の警報episode、asset/pooled指標と判定を照合した。全件一致で、追加model生成・forward・学習・再校正はない。

各foldで4 checkpointのmodel/AdamW/RNG/sampler位置、全4,096 loss/grad norm、選択stateを保存した。選択された全5状態をparameter/buffer、AdamW step/1次・2次moment、RNG bytes、schedule hash/位置付きの中立binary/layoutへ書き出し、全tensorをcheckpointと独立にunpack照合した。Rustの学習/backward/optimizer/checkpoint再開/推論とbanto API/job/model管理の参照に使えるが、Rust実装・Rust再開の成立はまだ検証していない。PyTorch RNGはbackend固有である。

## 時間と資源と保存

| unit | 選択step | 親観測秒 | sampled Mac footprint B | child peak RSS B |
| --- | ---: | ---: | ---: | ---: |
| fold 0 | 4096 | 35.659 | 407,471,088 | 400,752,640 |
| fold 1 | 4096 | 34.827 | 413,238,304 | 396,165,120 |
| fold 2 | 4096 | 32.244 | 409,011,280 | 371,425,280 |
| fold 3 | 4096 | 31.072 | 402,949,152 | 413,696,000 |
| fold 4 | 4096 | 33.813 | 410,190,880 | 399,736,832 |

実学習parentは固定5件、すべてexit0、計167.616秒（上限4,500秒）。各親900/子870秒、最大sampled footprint413,238,304B/peak RSS413,696,000Bで各2GiB内。最終foldには全freeze/採点を含む。別の保存値検算は2.698秒/exit0、追加学習のunitではない。資源上限は既存のsample/checkpoint観測でありOS hard capではない。

各fold rootは21file・約15.5〜18.3MBでnormal24file/768MiB、single32MiB内。source/stdio/exit/phase/state/journal/選択/校正/予測/episode/freeze/結果/closureと旧変更・原本・closed rootsを保存した。EvidenceStoreは16MiB/512file・part256KiB・failure reserve2MiB/16fileを維持する。

起動前のhelper importパス修正で、親cwdからの相対Python指定が一度失敗した。最初の未起動campaignを閉鎖のまま保持し、明示workdirで修正してfresh launch2 declarationを保存後に5unitを開始した。実学習の失敗や再試行ではなく、科学契約r1は不変。全foldのstderrに既存TorchのNumPy未導入warningが残ったが、tensor/list経路は正常終了し、依存追加はしていない。

Mac Python3.14.8/CPU既存Torchの共通学習・評価経路とMac資源観測はpass。Windows固有機能とOS依存包括test suiteは未実行として分ける。新取得・外部研究data送信・Git push・本番採用・追加agentはない。

## 計画上の位置と次の工程

M1のMetroPT予測比較に続き、CAREの保全・点検向け最初の有限比較も完了した。今回の値を既読testとして固定し、追加seed、更新延長、testでの閾値/連続数/信号変更を自動追加しない。未検知9件・asset差・gapによる可用性差は、保存済み予測から次の仮説を整理できる。新候補を評価するなら、使用済み情報と開発/評価の分離を実行前に記録する。

最終目的はTimesFM3参考自作モデルの産業と需要/PSIでの実用性、保全・点検支援の第一優先、学習を含むRust移植とbanto統合のまま。次の実装工程は、保存済みmodel/optimizerとbatch参照を使うRust R0契約/backend・配布条件の整理へ進められる。Rustの前処理/forwardだけで学習移植の完了とはしない。

需要2015再評価停止、調整2014以前、同休業mean28、四季平均過小量・過大量非増加、観測のみ/欠測0仮定の評価分離、正式holdout等の境界とheartbeat PAUSEDを維持する。
