# CARE — 保全・点検支援のイベント評価設計

2026-10-16 JST。人が選んだ第一用途「保全・点検支援（異常の予兆）」を[上位計画](timesfm-inspired-practical-evaluation-plan-2026-10-16.md)の実際の判断へ結び付ける。今回のM1はMetroPTの有限予測比較であり、CARE学習の開始や故障予兆の有効性を認定するものではない。本書の初期案を下記の固定契約r1へ具体化した。学習/採点は未実施。

## 現行の固定契約（2026-10-16追補）

人の指示で[版・利用条件・sensor/asset確認](../results/care-metadata-contract-2026-10-16.md)を完了し、[CARE-A-MAINT-20261016-r1](care-a-maintenance-contract-2026-10-16.md)を固定した。公式v6のMD5/サイズと一致、CC BY-SA 4.0、95file/36asset、実label45 anomaly/50 normal。原本README44/51は古い記載。数量float decode/CARE学習/性能採点は0。

最初はラベル内容前に選んだFarm A/5asset/22file/3 Avg信号。asset留一の5fold、train3assetの各最小IDanchor、validation1assetのanchor train-prefixを70%選択/30%校正、test1assetの全prediction。入力/学習rootとevaluator/label rootを分離した。固定99.5%校正閾値・3連続警報/解除、全5fold予測freeze後採点、native baseline可用性も報告する。

公式の意味を確認した結果、event_start/endは故障前の推定異常区間であり、主評価はその中の検知へ固定した。file間の実時系列は匿名化で復元できず結合しない。以下の一般案を現行条件と混同せず、不一致時は固定契約/機械設定を優先する。次は数値入力/quality maskと実consumer境界の確認で、未解決事項のないmetadata監査を反復しない。Rustは学習を含む最終目的として維持する。

## 問いとデータの現在地

問いは「自作モデルによる予測残差が、運転状態を考慮した単純な統計検知に比べ、点検候補を早く示しつつ不要な警報を抑えられるか」。forecast MAEの微差を答えにせず、event単位の検知率・誤警報・先行時間で確認する。実際の停止回避・保全費用低減は別の用途検証とする。

[ローカル受領metadata](care-local-archive-metadata-2026-10-16.json)で確認済みなのは、原本SHA、中央directory、READMEまで。ZIP 5,503,439,673B、宣言展開19,987,485,991B。公式版/利用条件は未照合、観測CSV・event_info・feature_description payloadは未読。原本の全展開や新取得は今回行わない。metadataファイルの読取りと本設計保存のみ。

## 最初の一件へ進む順序

1. 公式の版・利用条件と、README/センサー説明を照合する。event結果を使う前に、物理量・単位・集計時点・利用可能時刻・運転状態の意味を固定する。観測列や全変数の探索から始めない。
2. assetとfileの対応を確定し、同一風車の複数event・重複履歴・同一timestampを一つのgroupへまとめる。CSV単位のrandom splitを使わない。assetキーはfarmも含め、番号の一致だけで別farmの設備を同一視しない。
3. train/validation/testをasset group単位で固定し、対象と分割理由を性能を見る前に保存する。fieldの意味が異なるfarmを列位置だけで結合しない。最初の同一sensor契約を満たす限定対象と、必要な正常運転/各splitの支持条件をmetadata段階で決める。実asset一覧が未確認なので本書でIDを推測して割り当てない。
4. 一つの予測残差法と、一つの運転状態別の統計検知を比較する契約へ落とす。変数・C/H・alarm score・閾値候補・持続/解除/reset・calibration・最小支持・資源予算を数量の採点前に固定する。MetroPTの1分32leadをCAREの時間幅へ機械的に流用しない。

油圧/XJTUの全実験をこの契約の前提にしない。M1の良かったtargetやseedを、そのままCAREの変数・モデル選択根拠にはしない。

## 学習・入力・labelの境界

- 学習・尺度・正常profileはtrainだけ。checkpoint、alarm thresholdや持続条件の選択はvalidationだけ。test eventや将来値で学習条件・変数・正常profileを調整しない。
- 正常運転statusは無故障の保証ではない。学習prefixをevent labelで除外/選別する場合は、train labelだけを使う独立のoffline選別として記録し、検知時入力へ混ぜない。testの正常期間指定は評価用label側に隔離する。
- 発行時点で確定したセンサー、必要ならその時点で既知の運転条件のみを入力とする。未来status、train_test区分、event_label、event_start/endを入力にしない。全寿命・全期間の統計を正規化へ使わない。
- gap、欠測、品質不良、mode不明を0や正常へ変換しない。警報を出せない区間・reset・warmupを全手法共通で記録し、評価可能時間の減少も表示する。
- test assetで個別calibrationが必要なら、labelを使わない事前prefixと評価期間の境界を先に固定し、未学習assetという主張と条件を分ける。現段階では自動適応を追加しない。

## 警報時刻とイベントの評価

将来の予測を時刻oで出しても、残差は対象実績が利用できる時刻tになるまで計算できない。**残差に基づく警報時刻はt以降の実利用可能時刻**とし、oへ遡らせない。持続条件が成立した時刻に警報を確定する。集約区間末と転送/確定遅延の扱いを契約へ記載する。

公式FAQでevent_start〜event_endが故障前の推定異常区間と確認したため、主hitはこの区間内にOPENした警報とする。event_endへの先行時間はproxyで、実故障/保全時刻とは保証しない。元案のevent_start前窓[t0−W,t0)だけを成功とする条件は採用しない。警報利用時刻と境界は同じrecord可用性時計で比較し、実際の点検時間要件は未設定のまま開示する。

連続警報をepisodeへまとめる規則、解除/refractory、重複event、matchingの順序をtest前に固定する。同一episodeを複数eventの成功へ重複計上しない。最初の有効な未対応episodeを対応付け、未検知event・対応しないepisodeも全件残す。必要な観測履歴が不足するeventは理由付きで別表示し、検知率の分母を都合よく縮めない。

主表は、対象event数/評価可能event数、先行検知率、開始後検知率、未検知数、誤警報episode/正常equipment-hour、警報が継続した時間割合、先行時間の分布を示す。点単位のaccuracyやPRだけで合格にしない。asset等重み、farm/asset/event別、全support/除外と悪化を併記し、長い記録だけで全体を支配させない。

正常equipment-hourは実際に評価できた区間の長さから算出する。event周辺の除外窓は閾値選択と独立に事前固定し、広げて誤警報を隠さない。相関した多数の点を独立標本として扱わず、少数eventでは不確実性と実数を示す。

## 未決条件と終了点

| 未決 | 次に確定する根拠 |
| --- | --- |
| 版/利用条件、asset重複、sensor/status/event時刻の意味 | 公式情報と限定metadataの照合 |
| 限定対象・分割・入力変数・C/H・支持条件 | 物理量/設備対応と取得可用性。test成績を使わない |
| 点検に必要なW、許容する誤警報・遅延・業務損失 | 保全判断の要件。未確定なら業務合否を出さない |
| 残差scoreと統計baseline、threshold/持続/解除、資源上限 | 上記を満たす一候補の実行前契約 |

これらが揃う前にCARE学習やtest event採点を始めない。支持不足・意味不明・profile汚染・資源超過は不成立として保存し、eventやassetの事後差替えで救済しない。予測だけ改善してevent指標が改善しない結果も残す。用件未定時は記述的な結果までで、製品採用を認定しない。

Rustへの最終移植は、予測だけでなく学習/backward/optimizer、モデル/学習状態の保存再開、alarm state/resetと時刻の意味、bantoでのjob/API利用まで維持する。現在はPython参照の評価と保存資産を作る段階で、CARE検知成功やRust実装の成立と混同しない。
