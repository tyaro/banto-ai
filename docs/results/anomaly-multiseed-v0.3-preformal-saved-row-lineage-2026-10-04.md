# 架空登録形式の保存readerから部分cluster行への由来境界（2026-10-04）

## 今回の受入対象

g02で保存した架空登録形式の１区間について、外部指定pinを持つ`receipt.json`、`report.json`、所有生成・別readerの`result.json`を再読取りする。前回のreaderが検証した最新attemptの６評価を凍結した登録identity順と照合し、主count・有効稼働秒数・検出遅延histogram・slice件数を、保存reportのraw pin付き６行として取り出す。今回のconsumerは131 MBの評価/観測payloadを再読取りしない。観測→profile/score→要約の再導出はg02の保存reader結果を参照するものであり、今回の独立再実行ではない。

この区間のcoverageは全480区間中１、2,880評価中６、該当seedの12 layout中１である。40 cluster、診断、slice sourceはすべて`null`を維持する。別系譜のtrial-16架空40 clusterや保存済みdev/smoke 120区間を入力として補完しない。登録seedはschema目印で、正式holdout観測の生成・読取りは０、評価creditは０。

## 保存試行

[純粋境界](../../src/banto_ai/anomaly_v03_registered_saved_row_lineage.py)と[保存試行CLI](../../tools/preformal_saved_row_lineage_trial.py)を追加した。CLIは起動時に指定したbytes/SHA256で３つのg02入力と、過去の２役予算結果・資源receiptを読み、前回resultと予算receiptの相互pinを検査する。予算は**過去の生成子→別readerだけ**の測定であり、今回の行投影をその184.919秒に含めない。

| 保存済み入力 | bytes | SHA256 |
|---|---:|---|
| g02 `saved/receipt.json` | 6,438 | `38d6fcbb744fa1f72b6e012194a9eb2a1c0a6c08527f2e95b69c3cf013332d1e` |
| g02 `saved/report.json` | 117,923 | `d5cdd5ac255a76a6302f7d08763ae49eb3860a2a4c57e18fe2ed5c9f340ae6a8` |
| g02 `owned-generator/result.json` | 10,528 | `354c8ae043486c8f5ee2a99780ea5ee5a9395ed92daaca790187e8e9ab7c1179` |
| g02 `budgeted-result.json` | 1,654 | `d1a8c738e61fd0ad48d99675ca12cb2aea937152bafca29a543398061e9ceda7` |
| g02 `resource-budget.json` | 3,618 | `c1dd3e838930cd318ee8c51634d7d54faaacfcae7d70d3065f8e15a3878a72a2` |

[今回の部分由来result](../../artifacts/anomaly-v03-preformal-saved-row-lineage-01/result.json)は116,494 B / SHA256 `27fda6488b0487254a85394d7af090dcb9ff7c54903ea5436a814d1eb8a7c621`。`status=fixture_rows_bound_partial`、`chunk_index=0`、`latest_attempt=1`、６行、登録seed index 0→`invented-00`、layout 0のみを保存した。各行は凍結identity、最新attempt、評価raw pin、入力hash、報告主count・診断・sliceを保持する。`clusters/diagnostics/slice_source=null`、`saved_payload_bytes_rechecked=false`、`reader_execution_authenticated_here=false`、正式許可・正式評価credit０を確認した。[５試験](../../tests/test_anomaly_v03_registered_saved_row_lineage.py)は成功し、外部pin、失敗/古いattempt、行順、主count、sliceの改変を拒否した。予算resultのSHAを意図的に誤らせた別試行は読取り時に拒否され、出力rootを作らなかった。

[別実装の読取り専用postcheck](../../tools/preformal_saved_row_lineage_postcheck.py)は新しい境界moduleをimportせず、g02外部pinset・保存３件・過去２役予算２件と新resultをraw pinで再読取りした。６行の順序、identity、主count、診断、slice、入力/評価pinを元report/receiptへ照合し、不一致０。[postcheck結果](../../artifacts/anomaly-v03-preformal-saved-row-lineage-postcheck-01/postcheck-result.json)は1,907 B / SHA256 `79905a9495a671cc50dfff95a75da981cc2a2f64294f9e5303fc40fc502c463f`。これは元131 MBのpayload・観測導出を再計算した監査ではない。repository safetyはpass。

## 次の受入残件

1. １区間の契約を480区間すべてへ拡張し、各区間の最新attempt・外部pin・６行の観測由来を検証して2,880行を揃える。区間欠落・重複・順序逆転・古いattempt・異なるsource/pinは集約前に拒否する。
2. 同じ保存raw由来の12 layout×２層×３候補を登録seedごとに畳み、40 clusterの主count・診断・slice sourceを得る。既存の宣言marker専用集約器から数値演算を再利用する場合も、保存rawのSHAを合成markerと取り違えない。
3. producer→登録reader→40 cluster→50,000 draw→文書/slice→独立完全監査→writer→別readerを、対象容量と外部入力の範囲を固定した単一外側予算で測る。現在の算術・文書・slice・公開は別試行である。
4. 26H2運用契約、５役のsource/runtime完全閉包、最終revisionのLinux必須jobとrunner image、正式S6を独立に受け入れる。S4採択まで旧gate `s4_acceptance_not_frozen`を維持し、実登録holdout観測に進まない。

実データ作業はS4の正式採択後に固定手順で行う。保存済み合成dev/smokeの10 seed・720評価はengineering参考として扱い、正式40 seed・2,880評価へ算入しない。
