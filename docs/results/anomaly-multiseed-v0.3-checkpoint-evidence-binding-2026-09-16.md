# 進捗記録と保存済み6件の証拠照合

2026-09-16。実装commit **6b77db9bf603aceb09f73a72241a57992c64716d**。
`checkpoint_anomaly_v03.py preflight-trial` を追加し、参照journalと既存trialの実ファイル・終了監視・保存auditを結び付けた。[使い方](../anomaly-v03-independent-audit-and-checkpoints.md#保存済み6件とのpreflight証拠照合)。保存済み全6件への実適用で一致を確認した。

## 確認した範囲

外部reference hash→固定plan/3-record journal→marker/supervision/audit/audit-monitorのhashを照合する。旧producer、旧監査consumer、今回verifierは別のclean作業コピーと40桁revisionで固定し、参照先を取り違えない。
既存readerで全41 payloadを検査し、保存scoreから全6件のepisode/matching/metricsを再検算した。保存auditの安定項目との一致、journalのID/状態/runtime/終了確認、監視の正常終了・範囲・呼出し先も確認した。長時間の読取り後にjournal・reference・証拠を再読取りする。

これは旧trialを使ったpreflight参照検証。参照journalは今回作成した宣言で、過去の実行履歴を新campaignへ編入するものではない。`preflight_evidence_revalidated=true`、`campaign_evaluations_credited=0`、`campaign_attempt_roots_verified/resume_authorized/campaign_completed=false`。score/profile導出や完全S6受入は未完了で、性能合格も宣言しない。

## 検証結果

新規12＋既存checkpoint21＋saved-audit6＝**39件pass/5.393秒、failure/error/skip0**。独立レビューP0〜P3所見0、進捗poll0、repository safety/diff-check pass。
初回33件/7.166秒は1 failure。テストfixtureで保存consumerと比較先sourceが同じobjectを共有していたため、片側変更のつもりが両方に反映された。比較先を独立copyへ修正し、再確認した。初回をpassには数えない。広い重い評価moduleや専用principal試験は行っていない。

新clean detached worktree **C:/Users/TKent/.codex/worktrees/engineering-binding-20260916** / 6b77db9から実行。既存producer **engineering-v03-20260916** / 0086ffe、旧consumer **engineering-audit-20260916** / 0c8377d、既存trial-01と保存auditを使用した。
PID16484、UTC10:45:38.194649〜10:47:34.778884、**全体116.420秒/peak private195002368 bytes（185.97MiB）/exit0**、終了確認済み。10分/1GiB/ログ8MiBの所有process監視で停止理由なし・観測エラー0。binding内resourcesの96.628秒は既存audit部分だけであり、全体実測はbinding-process.jsonを使う。

参照/旧audit入力7 files、既存trial入力46 files、前回checkpoint証拠12 filesは実行前後不変。登録dataset生成0、producer score計算0、保存ledger再検算6件。既存trialの出力先は再使用・削除しない。
新証拠 `artifacts/checkpoint-evidence-binding-2026-09-16` は9 files/383006 bytes（最終manifest除く）。binding.jsonは3449 bytes/hash `5e680d45ed08cf645169372e193d66d5d744dd26cf38091b132b61567f0cd8d1`。
reference raw hashは `a2ccef6286fc8e4343957278c978a9851115a3679a8ce920716a26b017491f86`、plan canonical hashは `723ac6b91dac4d59d75de941875b205011175fb04d7d22ac03eec71a4f5c57ea`、journal headは `b71c725d4ad8a04b7a805c30cd76fc7b1510a8a182445f30d961caea2eb08b7c`。

終了後の空きRAM14151684096/C152356487168/D169743474688 bytes（D約158.1GiB）。今回の3 runtimeはOS26200.9445、開始時boot2026-09-16T08:46:30.5000000+09:00。Windows Updateのengineering緩和/正式pin維持を継続。容量の変化原因や長期リーク不在は断定しない。
本流889cfc3と上記producer/旧consumer/verifierはclean。既存親policy文書の未commit変更は8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621のまま保全・commit除外。

## 次の工程

通常の単一writer運用で、planとjournalを上書きせず追記するwriter、および新campaignのattempt保存先・終了監視・検算出力の契約を整える。まずmetadata fixtureで中断/再開を確認し、全dev/smokeの実行はまだ開始しない。
profile/score導出の独立検算、runtime inventory、全体/各chunkの予算、source/consumer freezeは引き続き残件。旧trialにcampaign creditを与えず、holdoutも開かない。§116の専用principal試験保留・旧root閉鎖・j消費済みguardを継続し、principal/SAM/保護rootアクセス、UAC/ACL変更、push/merge/CIなし。
native_launch_authorized/isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated/native_publication_performed/raw_consumer_payload_release_enabled=false、acceptance_status=not_completed、performance_status=not_evaluated。
