# 検算済みfixtureの通常公開・writer証跡・別reader接続（2026-10-02）

**生成済み5ファイルを、通常writerと終了後の別readerへ接続した。保存済み解析と主表＋slice検算の記録も外部bindingで結合し、数値再計算なしで公開・読取りを確認した。** [利用方法](../anomaly-v03-fixture-publication.md)。

開始revision596d31b298a649f50f5246e917889b51e1cc7f88、初回0c6dbae63254920e6320e0e4c0d9187d21f6e007/fp01、修正後a9de2f500020bb951dfd08d66b56e368859236b9/fp02。新module/test2本、既存evidence/budgetと試験4本を変更。旧74code中70本と18data不変、現在76code。編集先70b0、本流・実計算checkoutは変更しない。

## 確認した動作

新しい公開経路16項目が90.902秒で全pass（failure/error/skip0）。共通evidence16＋budget19の35passは初回からcode不変を照合して再利用し、関連51項目を確認。最終revisionで51項目すべてを再実行したとはしない。

外部pin違い、旧primary-only audit、別解析へのaudit参照、保存payload改変、pinを揃え直したmapping不一致、formal/holdout拒否、上書き・重複配置拒否、writer部分書込み、応答消失、reader失敗、役割改変、未終了ownerと記録失敗、資源不足停止を検査した。writer終了確認後だけreaderを起動する。共有budgetは通常公開マーカーの2リンクだけを明示許可し、見かけ容量へ両方を加算する。

初回tests-1は50項目中46pass/4failure、275.503秒。正常経路は120秒の共有上限で停止。tests-2は再確認ハーネスのテスト名重複により4件ともロードエラーで、本体未実行。修正したtests-3は同じ実装の失敗4項目だけを再確認し、3pass/1failure。正常経路146.192秒（writer45.034/reader99.862秒）で時間停止した。同revisionのGit blobを工程内で再利用する修正を加え、作業bytesと環境の前後検査は保持した。ほかの初回3失敗の原因を断定せず、記録を保全する。fp01/全失敗ログ/旧harnessを削除しない。

## 保存済み結果への適用

元解析はcf4d9c42c11c202984aacdd71ac5efb0368f22d0のresource工程、元検算はb6d578e7c577470ecb2fbef228413d6b2abf85bfのslice工程。保存点の連鎖で認証した12ファイルを使い、原本は変更しない。主9表/180gateと本文1,233行/補助2,835行/詳細9表の監査済み範囲を引き継ぐ。今回、数値検算をやり直した意味ではない。

保存例12.249秒。writer PID45580、reader PID42148、両子exit0/reaped/error0。元解析・検算再実行0、新評価0。 元5payloadは1,976,915bytes、公開5payloadは1,976,920bytes。各JSONにLFを1つ加えた差だけで、内容・数値は同一。

元executionのstagesとpublished=falseは当時の状態のまま保持する。後から実施したwriter/readerの実績は外部publication-bindingに記録する。markerは5payload inventoryを持ち、bindingは元/公開payload pin・解析/audit参照・writer/reader evidence pinを持つ。自己参照ハッシュを作らない。

選択source13本/Python2ファイル、保存入力12＋専用invocationを親期待値へ結合。writer: project30 / 全234file / module179 / native48、前後追加file 0・module 0; reader: project30 / 全234file / module179 / native48、前後追加file 0・module 0。依存は終了後のdisk/Git照合であり、正式な事前profileや全runtime閉包の受入ではない。

資源監視61sample、directory最大2.83MiB/39entries、親peak59.24MiB、子writer/reader peak50.16/49.18MiB、commit最小余裕13.82GiB。120秒/512MiB/32MiB等の上限は据置き。 観測はsampling/協調停止でhard quotaではない。再確認時146秒の停止は親の検査中に上限を超過した例として保全する。

## 保存先と次工程

- [呼出し結果](../../artifacts/fixture-publication-2026-10-01/tests-4/saved-fixture-publication/result.json)
- [解析・検算・公開・writer/readerの結合](../../artifacts/fixture-publication-2026-10-01/tests-4/saved-fixture-publication/publication-binding.json)
- [資源記録](../../artifacts/fixture-publication-2026-10-01/tests-4/saved-fixture-publication/resource-budget.json)
- [今回実施した16試験](../../artifacts/fixture-publication-2026-10-01/tests-4/test-results.json)
- [再利用した35試験の起点](../../artifacts/fixture-publication-2026-10-01/tests-4/reused-tests.json)

OUTは開始日に合わせartifacts/fixture-publication-2026-10-01、完了日はJST10月2日。文書revision、全pin、最終OS/資源はsavepoint-evidence.json/save-checks.jsonへ記録する。旧保存点の起点は31,897bytes/SHA5b3b86e6bb46b30318dfd77ae7752824ffc03553d219519e2d7453807cdfbc30。

次は登録producerの保存記録・coverageから集計済みconsumer入力への境界を、I/Oなしのfixture adapterとして具体化する。登録ID、予定全slot、最終attempt、入力pin、終了記録、集計countの対応を受け取り、欠落や失敗の成功化を拒否する。旧720評価を再読込み・再集計するだけの作業へ戻らず、正式40seedの実行や50,000反復はまだ開かない。

正式null4欄/ready=false、formal/promotion/S6/trust/execution_authenticated/full closure=falseを維持。登録観測・coverageの真正性、正式契約、最終役割profile、全工程予算は未受入。 旧4payload公開経路、実計算c01d1c9・本流clean6f1285d・closed・既存dirty文書を保全。banto-24 PAUSED、principal/保護root/UAC/ACL/同時書換え保留、Windows3.12必須化なし、正式gate/holdout/freeze・push/mergeなし。
