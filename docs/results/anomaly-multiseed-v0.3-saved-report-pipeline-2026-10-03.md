# 保存済み工程から続ける単一の報告実行入口（2026-10-03）

**要約・集計表・報告書・保存完了記録の四つから開始できる単一入口とCLI、工程ごとの続行requestを追加した。23項目を確認（初回22成功、試験条件を分けた1項目のみ再確認）。前回の完了記録を0.620秒で再利用し、aggregation/report/publicationの呼出しと新しい所有processはいずれも0回。**

起点17d6029b189ee53f43fae2f35001e96ea970550b、前保存点38,659bytes/SHA3f20f27fff28dcd02f98f6cb692c399938ab1c465dec5cbc855ef3bf85c23e58。最終実装6d48c39cdafdb883ce63fdd991ba063169e58cb7、clean候補sp02/banto-ai。新module/test2本、既存publicationに共有budgetを渡す2行変更。旧92codeのうち91不変、計94code/18data。[APIとCLI](../anomaly-v03-saved-report-pipeline.md)。

## 確認結果

| 開始位置・条件 | 結果 |
| --- | --- |
| summaries | 架空の全120要約を使い、集計→報告→保存読取りを各1回。出典・判定不能・旧失敗を保持 |
| tables | 集計関数を禁止しても成功。報告準備と保存だけを実行 |
| report | 報告関数を禁止しても成功。保存だけを実行 |
| publication | 集計/報告/保存/プロセス起動を禁止しても成功。過去の完了と現在のbytesを照合 |
| 途中停止 | 保存処理の失敗後も報告checkpointを保持し、別の試行から再生成せず続行 |
| 拒否 | 正式mode、欠落・重複summary、boolサイズ、不一致pin、不完全・昇格した完了記録、入力との重複、既存試行を拒否 |
| 資源・所有 | 最初の資源不足で段階実行を停止。未回収workerは元ownerを保持し、勝手に次へ進まない |
| CLI | requestの外部bytes/hashを必須とし、未照合のrequestを実行しない |

新しい単一入口12項目＋既存保存読取り11項目を対象にした。小さい数値テンプレートを各登録IDへ複写したfixtureで接続を確認しており、720件の独立した数値監査ではない。手検出1件を含むfixtureは分母ゼロ719件、今回再利用した前回のzero-alert報告書は分母ゼロ720件で区別する。

初回85b18eb/sp01は23項目中22成功、1error（40.771秒）。既存ディレクトリ拒否の試験先が同時に入力を含んでおり、FileExistsErrorより先に入力との包含拒否が働いた。試験先を別の既存directoryへ分け、原内容の保持も確認するように修正した。本体は無変更で、他22項目の成功記録を保全・再利用。修正した1項目を6d48c39/sp02で再確認しpass（26.814秒）。そのsetUp内では架空要約から保存までのfixtureを構築するが、実評価の再計算ではない。tests-1/verify.py/sp01はinitial-test-record.jsonのpinで保全、最終確認はtests-2/verify-fixed.py。

- [最初の23項目の記録](../../artifacts/saved-report-pipeline-2026-10-03/tests-1/test-results.json)
- [修正した1項目の再確認](../../artifacts/saved-report-pipeline-2026-10-03/tests-2/test-results.json)
- [初回記録の保全](../../artifacts/saved-report-pipeline-2026-10-03/initial-test-record.json)
- [前回完了記録の再利用結果](../../artifacts/saved-report-pipeline-2026-10-03/tests-2/reused-completed-publication/example.json)
- [外部保存点との対応](../../artifacts/saved-report-pipeline-2026-10-03/tests-2/source-anchor.json)
- [次回も使える続行request](../../artifacts/saved-report-pipeline-2026-10-03/tests-2/reused-completed-publication/publication-checkpoint.json)

再利用したpublication resultは5,304bytes/SHAf051e27d81e52f7d4a2d0128891abf04c37b123c339285e76c478b0d92e21bf6、marker SHA2b42b57c72c9557558addd9b698bd11dea1fff2b1bed0854272abb06e2c349f0。今回pipeline resultは2,326bytes/SHA462c689a58a7126b357b14bb8f728bc8fb8429a0771b443733976d86ba0d1e73。4payloadと出典pinは前保存点に一致し、複製した新publicationは作らない。

今回の保存例は前回の架空報告書4file/3,040,268bytesの保存完了記録を再利用する。実720評価のrawを読まず、新評価・mapper・再集計・bootstrap・正式gateを起動しない。過去のwriter/reader終了記録と今回の保存bytes照合を区別し、過去PIDへアクセスしない。実際の検出性能やsource/runtime全依存の真正性を保証しない。

## 資源と次工程

試験parent peak最大83.80MiB、完了記録再利用例のparent peak 40.50MiB。例monitorは6sample、観測中の新規directory最大738bytes（requestとcheckpoint）、監視/結果receipt等を含む終了後の保存量9,269bytes。例commit最小余裕25.91GiB。通常の試験監視と保存例はerrorなし/monitor終了確認済み/資源pass。意図的な資源停止は別の試験条件として確認した。 D空きは開始348.26GiB→終了348.26GiB。全体120秒/parent512MiB/32MiB、各子30秒/512MiB等は据置き。短時間の結果から長期メモリリーク不存在は推定しない。

正式null4欄/formal_ready=false、formal/promotion/S6/trust/execution_authenticated/full closure/analysis_authorized=falseを維持。登録観測の導出・正式40seed・契約/役割profile・全工程予算の受入は別。Phase2/3全体は未完了。

実計算c01d1c9/main6f1285d/closed/既存dirty文書とbrp2/旧候補を保全、banto-24 PAUSED。OS25H2/26200/9457、旧formal9168不変。別Bantoリリース申告・資源停止・D空き減少の履歴は保持し因果未断定。principal/保護root/UAC/ACL/同時書換え保留、Windows3.12必須化なし、push/mergeなし。

次は既存計画と受入記録を照合して、正式評価前の残件（運用契約、実入力への適用、版と実行環境の固定、全体の資源計画）を更新し、次に必要な実データ作業の範囲を具体化する。完成した接続工程を増設・反復せず、正式gate/holdoutや実720評価の再実行は起動しない。
