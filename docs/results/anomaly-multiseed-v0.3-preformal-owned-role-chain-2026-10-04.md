# v0.3 架空入力の5役割連続実行と共有予算（2026-10-04）

状態: **26H2向けの未採択preformal fixture**。code保存点は `62e02877eaf536b11d2cfd71e96e8e54837845cc`。登録holdoutの観測は生成・読取りとも0件、正式評価creditも0件である。旧25H2正式入口は `s4_acceptance_not_frozen` のままで、S4採択・S5・S6・昇格を示さない。

## 到達した範囲

前回の[保存済み架空完成6評価のreaderと役割残件](anomaly-multiseed-v0.3-preformal-completed-reader-and-role-scope-2026-10-04.md)から、次を追加した。

- 手製の登録形式完成6評価と、校正済みprofileと実scoreが一部ある混合評価について、**報告scoreから独立ledgerを再計算し、同じ報告scoreとledgerから条件別sliceの件数を再計算**した。元観測からprofile/scoreを作った証拠ではない。slice入力は観測由来と主張しない。
- [既存の保存済み区間readerを使う架空1区間試験](../../tests/test_anomaly_v03_preformal_full_chunk_fixture.py)では、新規の実attempt形式pathからdev 1区間・2 dataset・6評価を読み、20入力pin、最新attempt、観測→48 profile/14,400 score→独立ledger→主/sliceを6件とも再導出した。全件は`inconclusive`である。外部savepoint pin、保存評価bytesの改変、新しい失敗attemptへの後戻りも拒否した。1試験28.947秒でpassし、一時rootは22 file・125,407,901 B（試験後削除）だった。**120区間完了anchorは試験用の架空足場で、残り119区間は未検証**。origins/quality-mask/split/targetsはpin付きplaceholderで、その意味の生成監査を通していない。登録holdout readerの受入ではない。
- [所有producer fixture](../../src/banto_ai/anomaly_v03_owned_producer_fixture.py)が外部pin付きの架空archiveだけを新規子で読み、2,880枠の純粋joinと1 draw投影を保存した。これは実登録producerではなく、`real_producer_executed=false` である。初回は親の出力inventory検査に型誤りがあり失敗receiptを保全し、修正後の別試行で通過した。
- [5役割fixture](../../src/banto_ai/anomaly_v03_platform_five_role_fixture.py)はfresh producer→analysis→audit→writer→別readerを直列に起動し、各所有子の別PID・開始識別子・終了/reap、受渡しpin、選択sourceと前後runtimeを照合した。producerの出力を今回のanalysisへ渡した。以前のjoin済み投影を子入力として再利用していない。
- [共有予算](../../src/banto_ai/anomaly_v03_preformal_chain_budget.py)はproducer開始前からreader終了後まで一つのrootとwallを0.25秒間隔で標本監視し、各所有子への協調probeを持つ。最終2 receipt用に128 KiBを容量上限内に予約する。OS hard quotaではない。

## 保存した実機試行

いずれも新規の架空rootで実施し、成功と失敗を上書きせず保全した。`bytes/SHA-256` は保存済みraw fileの値である。

| 試行 | 結果・停止位置 | 外側result / 共有budget | 確認した境界 |
| --- | --- | --- | --- |
| [trial-01](../../artifacts/anomaly-v03-preformal-five-role-26h2/trial-01/result.json) | 5子完走、80.266秒 | result 7,143 B / `3ae363d7f8b66a123b6559eaab135da7cff797cab23f2660392e7878e9794f23`; budget 4,818 B / `464d1763b6a942561fbd22d5d4e8a6f86a95e5bf3690f6b3a325b87881d920e1` | producer 15012、analysis 2228、audit 29792、writer 11616、reader 7824は全て別PIDでexit 0/reap確認。独立postcheckの123項目が一致。 |
| [trial-02-wall-stop](../../artifacts/anomaly-v03-preformal-five-role-26h2/trial-02-wall-stop/result.json) | 8秒設定でproducer中に `pipeline_wall_limit` | result 2,921 B / `cdea7571abffef00c8d182f48054d969cf885646cc8589a78bae26cc09ca12f0`; budget 3,180 B / `95fd51b9ebc69f6a879f0e0381736c5b8bd3638cddcd5bc306e695385c46a38d` | producer PID 12360を停止・回収。後続4子を起動しない。38標本、監視終了確認。 |
| [trial-03-dir-stop](../../artifacts/anomaly-v03-preformal-five-role-26h2/trial-03-dir-stop/result.json) | 12 MiB設定でanalysis準備中に `pipeline_directory_limit` | result 4,143 B / `ed614d00701ab99d250b452728d258e36a1d92ccf102dfec4be1bf5cd613967e`; budget 3,472 B / `863d50ff154c763ef5e7a7d2a4daec3503c5d5f6bab0de57b4f8b9a32fc4ac92` | producer PID 23556はexit 0/reap確認。analysis/audit/writer/readerの子は未起動。100標本、監視終了確認。 |

成功試行の共有予算は292標本、rootの最大観測24,700,323 B・106 entries・depth 4、親peak private 94,924,800 B、commit最低余裕16,434,110,464 B、RAM最低余裕16,156,696,576 B、D空き最低361,179,656,192 Bでpassした。最終rootは2 receiptを含む24,712,284 B・108 entriesで、48 MiB以内である。失敗試行の容量監視は**標本型**であり、12 MiB設定に対し最大16,361,497 Bを観測してから停止した。この超過量をhard capの達成と取り違えない。失敗時にも外側result・budget・producer結果を保全した。

選択sourceのrawはGit保存点と一致し、各役割でPython実行ファイル/DLLの実ファイルpinと開始・終了runtimeを照合した。analysis/auditは各27選択sourceに対して実観測project sourceが各43本、writer/readerは各15選択sourceに対して実観測が各32本ある。実観測値は終了後にGitと照合したが、事前の役割別許可集合ではない。成功試行当時のproducerは8選択sourceとPython binaryの照合のみで依存snapshotを取っていない。したがって各役割の動的ロード全依存、stdlib・拡張DLL・CRT・探索経路までの**完全source/runtime closureではない**。成功試行は架空40 cluster・1 draw、純粋join producer、架空5payloadの通常公開であり、50,000 drawの完全解析/監査、実保存登録reader、完全S6、正式DACL/独立token、実設備性能を含まない。共有root予算に外部保持の入力archiveと旧join rootの保存量は含まない。

## 正式開始前に残る作業

| 受入のまとまり | 現在の使える証拠 | なお必要な作業 |
| --- | --- | --- |
| 運用契約・platform | [26H2案v2](../anomaly-v03-formal-operations-contract-proposal-v2.md)と限定Windows fixture実測。既存CI workflowにはUbuntu 24.04 × CPython 3.12/3.14の両jobと比較jobがある | 旧25H2計画との差とwriter保証を版付きで採択。対象最終clean revisionで既存CIのpass/skip証拠、Windows native/stdlib/repository回帰、独立再監査を照合。現CI reporterのrunner image digestは`not_collected`で、信頼できる採取元も未決定。 |
| 登録入力・consumer | 架空登録形式の完成6評価をbyte→schema→報告score/ledger/主・sliceへ照合。devの発明1区間は既存実保存readerで観測→主/sliceまで再導出。旧dev/smokeの保存済み720評価はengineeringで全件要約済み | 登録用の**実保存attempt layout**を固定架空入力で読込み、外部に保持した終了/pin、元観測→profile/score→ledger→主/sliceを検証。今回のdev経路の架空120区間anchor・補助file placeholderは正式終了証拠や生成監査に使わない。その後S4の最終dev/smokeで全登録条件を確認。holdoutを事前測定に使わない。 |
| 5役割source/runtime・公開・監査 | 今回の5子と選択source、終了/reap、通常writer→別reader、失敗停止 | 実producerと完全な依存inventory/外部期待値、正式同形の全payloadと公開失敗・reader不一致、完全独立S6相当の架空入力検証。 |
| 全工程予算 | 架空1 drawの5役割共通wall/root正常値と二つの停止例。別保存点には架空50,000 drawの**算術のみ**の主・別監査値 | 登録reader、50,000 draw全表・slice・文書、完全独立監査、stage・公開・reader、失敗保全を一つの版付き予算で測る。旧正式計画§9の容量2倍条件を最終smoke実績から判定。 |

実データ作業の順序は、既に保存済みの合成dev/smoke 720評価を参考証拠として保持し、まず**発明した固定入力**で上記readerと停止・改変拒否を実証し、最終版契約/環境/全工程予算を確定した後に新版dev/smokeをS4として検証する。未使用40 seedの登録holdout 2,880評価はS4採択後のS5でのみ扱う。`formal_permission=false`、`execution_authenticated=false`、`source_closure_complete=false`、`runtime_closure_complete=false`、`independent_s6_complete=false`、`promotion_allowed=false`、`selected_candidate=null` を維持する。
