# v0.3 登録summary固定入力と実行環境の変更（2026-10-04）

基準保存点は `5ecc2e17b619988ac6f658540f58df8966d49ca0`。コード保存点は `9854203`（登録summary境界と公開役割receipt pin）と `f714170`（OS非依存のpin試験）である。今回も正式40 seedの観測生成・読取り、50,000 draw、正式gate、S6、昇格は起動していない。[前回の受入残件](anomaly-multiseed-v0.3-registered-fixture-and-acceptance-proposal-2026-10-03.md)のうち、登録済み全枠への架空summary結合を一段進め、writer/reader役割の既存証拠を後続profile候補の参照元として固定した。

## 登録2,880枠と架空summaryの結合

[新しい純粋adapter](../../src/banto_ai/anomaly_v03_registered_summary_fixture.py)は、凍結registryと前回の登録manifestをそれぞれ呼出し側の外部pinで再検証し、別pin付きの架空summary bundleを受ける。最新attemptに結果markerのあるsuccess/inconclusive行だけを登録identity順で要求する。各行のattempt番号とattempt固有の**架空**summary marker、1評価の主count/分母/遅延、条件別cellのjoint・marginal・主count整合を検査する。完全な480区間の場合だけ、12 layoutの整数値を40 seed ordinal×3候補×2層へ集約し、主count、diagnostics、条件別rawと登録seed→`invented-00..39`の対応を返す。既存の1-draw文書fixtureへ投影できる形も検査した。

最新attemptが失敗していても結果marker付きの成功済み行は照合し、集約4欄はnullにする。global producerが区間開始前に失敗した場合も、producer state・failure・終了宣言、全予定枠、失敗履歴を保持する。過去attemptのsummary本文は読まず、最新以外を採用しない。summary markerはattemptラベルの取り違えを検出するための決定的な架空値で、実summaryの発生元や実workerの終了を認証しない。外部pinを元bundleとは独立に保持する必要がある。

固定の完全例は登録manifest 3,985,054 bytes / SHA-256 `e95e2ae3ade4c62e1feb608892fe5dc32415a9a3e0bb0c98cb773daa081697cd`、架空summary bundle 11,837,511 bytes / SHA-256 `76327102692637c98795fd5c551c108e38981b5f9da881d1d6ba4dbce2ac11a5`。これらは実観測のpinではない。[新規試験](../../tests/test_anomaly_v03_registered_summary_fixture.py)7件が52.865秒でpass。別レビューで、最新失敗内の成功行、attempt marker、global失敗情報を補った後、追加の具体的な誤受入は見つからなかった。戻り値は `real_saved_chunk_reader_used=false`、`actual_summary_origin_authenticated=false`、`registered_observations_read=false`、`campaign_evaluations_credited=0`、`formal_permission=false`を維持する。

## writer/reader役割の保存証拠と実process試験

[fixture公開役割](../../src/banto_ai/anomaly_v03_fixture_publication.py)のwriter/reader成功receiptに、`dependencies.json`、worker `report.json`、`supervision.json`の親保持pinを追加した。保存後に3ファイルを再読取りし、一致してから成功receiptを返す。後続の役割別事前profileを作る際、終了後依存一覧と子応答を外側の結果pinから参照できる。選択sourceや動的DLL/外部programの**完全閉包**は今回も未受入である。

OS非依存の[pin回帰](../../tests/test_anomaly_v03_fixture_publication.py)3件は0.115秒でpassし、writer/readerの親保持pin一致、3ファイルそれぞれの保存後改変拒否、誤role拒否を確認した。一方、cleanな `9854203` で実processの正常1件と改変3条件を含む2 test methodを試したところ、すべてwriter起動前の `unsupported engineering runtime` で停止した。追加pin検査へは到達していない。失敗を成功に変えず、同じ条件の試験を繰り返していない。

試験直前の読取資源標本は空きRAM 10.98 GiB、system commit余裕17.29 GiB、対象volume空き369.19 GiBだった。停止理由は資源ではなくplatform契約差である。Windows registryの実値はProfessional / **26H2 / build 26300 / UBR 9457**、`sys.getwindowsversion()`もbuild 26300。CPythonは3.14.0、MSC v.1944、64-bit AMD64。以前の保存済みdev/smoke実行時に記録した25H2/build26200/UBR9457を現在値へ書き換えない。

旧[正式計画§8](../anomaly-multiseed-evaluation-plan-v0.3.md#v03-runtime-acceptance)とfreeze registryは25H2/build26200/UBR9168を固定する。[採択済みengineering契約](../anomaly-v03-single-writer-evaluation-proposal.md)は25H2のままbuild/UBRをattemptごとに観測・照合する設計であり、26H2を許可しない。未採択の[正式運用改訂案v1](../anomaly-v03-formal-operations-contract-proposal-v1.md)が示したUBR9457の例も、build26200・25H2の範囲だった。今回のreleaseとbuildの変更はその範囲外である。形式だけを検査するconsumer evidence validatorが新値を受け得ても、実行許可やS4受入にはならない。

## 次の受入境界

現26H2/build26300を対象にするなら、運用契約と計画を**別版**で改訂し、exact OS tuple・registry/schema/runtime pin、失う保証、対象clean revision、Windows native試験、Linux 2 jobs、正式dev/smoke、5役割のsource/runtime profile、独立再監査を揃える。旧正式gateの `s4_acceptance_not_frozen`、protected DACL/独立token未受入を観測値で通過扱いにしない。実processのwriter/reader回帰は採択された新platform条件で改めて行う。

正式規模の資源測定にも不足が残る。純粋算術は固定架空40 cluster・50,000 drawを受けるが、既存owned workerは8 draw、文書fixtureは64 draw、独立fixture auditは8 drawまで。既存上限を緩めるだけでは全drawを含む文書/容量/時間と衝突するため、正式入力を読まない別ID・新rootの上限付き測定workerを設計し、主推論と別実装auditを別々に測る。これも完全S6や正式全工程予算の受入ではない。

登録40 seedの実保存形式readerと外部終了証拠の接続は未実装。今回の架空summaryは主・条件別算術の**形**を確認しただけで、保存済みdev/smokeの720評価を正式集団へ移していない。正式文書のnull欄、`formal_ready=false`、formal/promotion/S6/trust/execution_authenticated/full closure/analysis_authorized=falseを保持する。
