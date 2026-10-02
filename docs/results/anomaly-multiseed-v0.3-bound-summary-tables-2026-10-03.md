# 結合済み要約からdev/smoke比較表への接続（2026-10-03）

**全120区間の結合済み要約からdev/smoke記述集計を作る処理を追加。新12項目pass（17.589秒）。前回の結合記録＋架空要約121file/17,877,645bytesを再利用し、4.894秒で90seed別表・18role別表・12比較・10seed群へ接続した。**

起点16af80f87c190e9a6bb0170bdd8a0c49f41b4729。前保存点46,454bytes/SHA0fb33d405ea6b7a564cba4db7a70e511cd3fbf7216823536baeaf606186965f5。実装e70d55e6ebe84a6171ccdf2c53abbaf8a85d5fee、clean候補bt01/banto-ai。新module/test2本のみ、旧86code/18data不変、計88code。[API](../anomaly-v03-bound-summary-tables.md)。

## 確認内容

| 対象 | 結果 |
| --- | --- |
| 入口 | 外部binding pin、全120区間/720枠、要約hash/ID/attempt、共通保存点を確認。欠落・部分供給・正式modeを拒否 |
| 集計 | dev8とsmoke2を分離、seed/candidate/stratum別に整数countと遅延度数を合算。主表と条件別内訳を108表で照合 |
| 手計算試験 | 1評価の検出1件＋他11評価のprecision0/0を合算しprecision1/1を保持。sensor recall1/120、overall1/240、遅延1秒を確認 |
| 診断の保持 | 判定不能1評価、48profile診断、旧失敗1件、最新attempt2、不明な失敗slotを保持 |
| 副作用 | file/process起動・journal再生・旧全件結合・score/ledger検算・bootstrapを禁止した状態で全件接続が成功 |
| 改変拒否 | pin変更、末尾要約変更、重複・順序・holdout付替え・bool index/attempt、主/slice/共通contextの不一致を拒否 |

新12項目はfailure/error/skip0。既存86codeは不変のため旧16件等のsuiteは再実行しない。試験用の要約は手計算テンプレートを他IDへ複写したもので、各layoutの実数値検算ではない。保存例は前回のzero-alert要約を変更せず使用し、success719/inconclusive1、precision分母ゼロ720件、全role表のprecisionと空の遅延中央値nullを保持した。

- [12項目の記録](../../artifacts/bound-summary-tables-2026-10-03/tests-1/test-results.json)
- [保存例の結果](../../artifacts/bound-summary-tables-2026-10-03/tests-1/retained-summary-tables/result.json)
- [比較表と条件別内訳](../../artifacts/bound-summary-tables-2026-10-03/tests-1/retained-summary-tables/tables.json)
- [再利用元の外部pin](../../artifacts/bound-summary-tables-2026-10-03/tests-1/retained-summary-tables/source-anchor.json)

出力は9,025,425bytes/SHA4eb9780514557bddbd00b7e2a46e9d43e282cc14566ad6bafe9725a63ed00185。各seedのcore/quality-stress12評価、overall24評価、各roleの条件別dev96・smoke24評価、overalldev192・smoke48評価。12比較はc0に対する記述的差で、CI・合否・候補選択を付けない。

保存例は前回の架空メタデータ/count要約をそのまま使い、入力生成・全区間結合を再実行しない。実720評価のraw payloadは読まず、観測→score/ledger検算・新評価・bootstrap・正式gate・所有worker/公開processは0。期待pinで固定した過去の記録を信頼する境界であり、現在の元payloadや実producerの認証ではない。

## 資源と次工程

試験peak 94.44MiB、例peak 81.38MiB、例directory観測最大8.62MiB、commit最小余裕26.86GiB。監視は試験54/例19sample、errorなし、終了確認済み、資源pass。120秒/512MiB/32MiB等の上限据置き。 D空きは開始348.26GiB→例終了348.26GiBでほぼ横ばい。短時間の結果から長期メモリリークの不存在は推定しない。

実計算c01d1c9/main6f1285d/closed/既存dirty文書とsc02/旧候補を保全、banto-24 PAUSED。OS25H2/26200/9457を記録し旧formal9168不変。前工程の別Bantoリリース申告・資源停止・D空き減少の記録も保持し、因果未断定。principal/保護root/UAC/ACL/同時書換え保留、Windows3.12必須化なし、push/mergeなし。

次は今回の結合済み記述集計表を、既存の報告文書・保存payload準備へ接続する。元binding/summaryへの参照と正式欄の未充足を保ち、今回の集計や既存720評価を反復しない。

正式null4欄/ready=false、formal/promotion/S6/trust/execution_authenticated/full closure/analysis_authorized=falseを維持。正式40seed・生成導出・契約/役割profile/全工程予算は未受入。Phase2/3全体は未完了。
