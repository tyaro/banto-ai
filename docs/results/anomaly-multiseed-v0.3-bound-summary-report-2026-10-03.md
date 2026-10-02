# 結合済み記述集計から報告payloadへの接続（2026-10-03）

**結合済みdev/smoke記述集計表から報告書と保存用payloadを準備する処理を追加。新10項目pass（25.650秒）。前回保存した架空集計表とschemaの2file/9,068,695bytesを一度だけ読み、1.011秒で4payload/3,040,268bytesを準備した。**

起点2b052a39c21111f9b4f5d787a959d3ff15a38c07。前保存点25,396bytes/SHA0d766f23c23ea0e20d76b1a5227684d0b4b6cea9c6622f8f1aa9b32389fb00d9。実装c9556345cd16d7df3f762e8f50b95ec0a3d7887e、clean候補br01/banto-ai。新module/test2本のみ、旧88code/18data不変、計90code。[API](../anomaly-v03-bound-summary-report.md)。

## 確認内容

| 対象 | 結果 |
| --- | --- |
| 入力境界 | 外部table/schema pin、完了720枠、coverage、閉じた権限を確認。正式mode・部分集計・誤った母数・改変pinを拒否 |
| 報告書 | 2cohort/18候補表/234主指標/5,670診断項目。mapperと内部対応検査を各1回 |
| 表示 | 架空データと明記し、実評価720件の結果に見える表現を置換。判定不能1評価を両表示で明示 |
| 内容保持 | dev576/smoke144、48profileの判定不能診断、旧失敗1件、null4欄・ready=false・出典を保持 |
| 手計算試験 | 1件の検出を含む表について、role recall1/960、precision1/1、遅延1秒とnullを報告側でも確認 |
| 改変・途中失敗 | 主指標・遅延・profile不一致、renderer失敗、出力サイズ超過を拒否し部分payloadを返さない |
| 副作用 | file/process起動・journal再生・再結合・再集計・score/ledger検算・bootstrapを禁止した状態で成功 |

新10項目はfailure/error/skip0。旧88codeは変更せず既存suiteは反復しない。試験の手計算検出1件を含む入力（分母ゼロ719件）と、今回保存した前回由来のzero-alert例（分母ゼロ720件）は別物。保存例はsuccess719/inconclusive1、旧失敗1件、全role precisionと空の遅延中央値nullを保持する。各layoutの実数値監査ではない。

- [10項目の記録](../../artifacts/bound-summary-report-2026-10-03/tests-1/test-results.json)
- [保存例の結果](../../artifacts/bound-summary-report-2026-10-03/tests-1/retained-tables-report/result.json)
- [報告書の見本・架空データ](../../artifacts/bound-summary-report-2026-10-03/tests-1/retained-tables-report/report.md)
- [条件別詳細・架空データ](../../artifacts/bound-summary-report-2026-10-03/tests-1/retained-tables-report/report.html)
- [全数値と出典](../../artifacts/bound-summary-report-2026-10-03/tests-1/retained-tables-report/report.json)
- [準備receipt](../../artifacts/bound-summary-report-2026-10-03/tests-1/retained-tables-report/consumer-receipt.json)
- [再利用元の外部pin](../../artifacts/bound-summary-report-2026-10-03/tests-1/retained-tables-report/source-anchor.json)

| 保存payload | bytes | SHA256 |
| --- | --- | --- |
| consumer-receipt.json | 89,509 | 6a80d94f51c2ba1c82e6385cb950bc22bc97aa55bea1c06c58c9ec0cbcd49e8b |
| report.html | 420,210 | b8de5db12d044305637ba98fccfc4f5f788b0878dfe9469fe0e1186d61b1423f |
| report.json | 2,527,580 | f20084c9f70acb85f125e3c2991e67ea2aff82babbe596f2825fd597d9eb37d8 |
| report.md | 2,969 | cc2c4a0b9e8da314b70dd8ceec8493512e568b52047674e55092e7b498eebd16 |

入力は既存tables.json（9,025,425bytes/SHA4eb9780514557bddbd00b7e2a46e9d43e282cc14566ad6bafe9725a63ed00185）とschema（43,270bytes/SHA0efa7a217dabda904581b766adf8f14df934afc0b0244b9f3b652a25f3b8f926）。HTMLは18details/54tables/2,610rows、scriptなしを構造検査。既存rendererのレイアウトは変更せず、今回のブラウザ描画による目視検査は行っていない。Markdownは内容を確認した。

保存例は前回の架空集計表を変更せず再利用した接続確認用であり、実際の検出性能を示す結果ではない。実720評価のraw payload読取り、入力再生成、再集計、全区間の再結合、score/ledger検算、新評価、bootstrap、正式gate、所有worker/公開process起動は0。外部pinで固定した過去の集計表を信頼する境界であり、現在の元payloadや実producerの認証ではない。

## 資源と次工程

試験peak 120.71MiB、例peak 59.34MiB、例directory観測最大2.90MiB、commit最小余裕26.60GiB。監視は試験72/例8sample、errorなし、終了確認済み、資源pass。120秒/512MiB/32MiB等の上限据置き。 D空きは開始348.26GiB→例終了348.26GiBでほぼ横ばい。短時間の結果から長期メモリリークの不存在は推定しない。

実計算c01d1c9/main6f1285d/closed/既存dirty文書とbt01/旧候補を保全、banto-24 PAUSED。OS25H2/26200/9457を記録し旧formal9168不変。前工程の別Bantoリリース申告・資源停止・D空き減少の記録も保持し、因果未断定。principal/保護root/UAC/ACL/同時書換え保留、Windows3.12必須化なし、push/mergeなし。

次は今回の4個の準備済みpayloadを、通常のローカル保存と書込み終了後の読取りへ接続する。新しい出典情報とfixture/engineeringの区別を維持し、報告書の再生成・再集計・既存720評価の反復をしない。

正式null4欄/ready=false、formal/promotion/S6/trust/execution_authenticated/full closure/analysis_authorized=falseを維持。正式40seed・生成導出・契約/役割profile/全工程予算は未受入。Phase2/3全体は未完了。
