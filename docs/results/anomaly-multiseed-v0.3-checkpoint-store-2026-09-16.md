# 進捗metadataの追記保存と受付結果の回復

2026-09-16。実装commit **d8ceed423e9ccd36540e88aa2bf559351366ad2e**。
通常の単一writerでplan/journalを上書きせず保存するAPIと `store-*` CLIを追加した。[使い方](../anomaly-v03-independent-audit-and-checkpoints.md#metadataを上書きせず保存追記する)。中断前の履歴を保持し、確定後にreceiptだけ失われた場合は読取りだけで再取得できる。

## 実装と確認

- metadata専用rootはplan.json/journal/pendingのexact構成。既存rootを拒否し、初期化失敗の部分rootも再使用しない。
- plan/head/件数を持つ外部receiptと次recordのhashを受け、全履歴・次の状態遷移・上限を検査してから追記する。既存保存部品のexclusive write→flush/読戻し→置換禁止renameを使い、renameを1件の確定点とする。
- 書込み/flush/rename前に失敗したpendingは残して停止する。自動cleanupや自動公開を行わない。確定後のreceipt喪失は、旧prefix＋保持していた厳密1件のintentと一致する場合だけ読み戻す。余分な末尾・異なるintent・旧head不一致を拒否する。
- receiptと状態復元はmetadataの宣言を扱い、execution_authorized/resume_authorized/campaign_completed/formal_permission=false。verifiedというrecordを保存しても、成果物の再照合やcampaign実行が済んだとは扱わない。

readerを共通moduleへ移し、既存inspect/preflightも同じ読取りを使う。新規store16＋既存checkpoint21＋evidence12＝**49件pass/11.620秒、failure/error/skip0**。初回から成功。独立P0〜P3所見0、進捗poll0、repository safety/diff-check pass。
途中書込み・flush失敗・rename前停止・rename直後のreceipt喪失、再初期化/二重追記、別rootのreceipt、変更された履歴、上限拒否を小さなfixtureで確認した。専用principal・同時writerの追加試験はしていない。

## 小規模CLI実演

候補作業コピーのcommit済み実装から `artifacts/checkpoint-store-2026-09-16/store-demo` を新設した。sourceの完全照合を要する評価実行ではなく、metadata fixtureの保存実演。新しい作業コピーや登録datasetは作っていない。
plan表示用inputと4 recordsはfixtureで、running→interrupted→次attemptのrunning→saved_pending_verification。marker hashは架空値と明示し、評価結果の保存成功を主張しない。

9 processの経過時間合計**3.004秒**、1回0.208〜0.412秒、最大private **21671936 bytes（20.67MiB）**。通常8回はexit0、旧receiptによる二重追記1回は期待したexit2で拒否。各所有processへ60秒/256MiB/ログ2MiB上限を付け、全終了確認、停止理由なし。初期receiptと追記receiptの回復でstore bytes不変、二重追記拒否でも不変だった。
4回の追記それぞれで、既存のplan/record bytes不変を確認した。最終record_count4/attempt_count2/failed_attempt_count1、saved_pending_verification1/not_started119、next_action=verify_saved_attempt。前回証拠10 files不変。登録dataset生成0/evaluation0/ledger再検算0。

証拠directoryは30 files/576625 bytes（最終manifest除く）。`demo-evidence.json` は4035 bytes/hash `27b73abe6731633482722841300b3dc23c4dca16405c5ff261101fced87633c5`。末尾record hashは `6cd532df861745864576afe49220ece2c7df0d76e78e65e47e8ceb4ac16c0abd`。
UTC12:37:26の空きRAM14465695744/C151697453056/D169742598144 bytes（D約158.1GiB）。OS26200.9445、開始時boot2026-09-16T08:46:30.5000000+09:00。Windows Update engineering緩和/正式pin維持。小規模処理の実測であり、長期リーク不在の評価ではない。
本流889cfc3/clean。既存親policy文書の未commit変更は8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621のまま保全・commit除外。

## 次の工程

新campaignのattempt出力契約をvalidatorへ具体化する。metadata専用storeへ実データを混在させず、別formatのattempt descriptorで固定chunk/attemptを基点にresult・producer-control・auditのpathとhash、6件identity、source/runtimeを結び付ける案をガイドへ記録した。まずmetadata fixtureで検査し、その後にcontroller接続を準備する。
予算、source/consumer freeze、runtime inventory、profile/score導出の独立検算は残件。全dev/smoke・holdout実行は未開始。§116の専用principal試験保留・旧root閉鎖・j消費済みguardを継続し、principal/SAM/保護rootアクセス、UAC/ACL変更、push/merge/CIなし。
native_launch_authorized/isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated/native_publication_performed/raw_consumer_payload_release_enabled=false、acceptance_status=not_completed、performance_status=not_evaluated。
