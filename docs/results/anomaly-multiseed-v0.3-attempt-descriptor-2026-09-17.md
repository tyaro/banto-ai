# 新campaignのattempt保存先・証拠metadata検証

2026-09-17 JST。実装savepoint **92772268ce968d9a4c74cb5d1811fddffb709c83**。
[仕様・CLI手順](../anomaly-v03-independent-audit-and-checkpoints.md#attemptの保存先と証拠metadataを検査する)。

## 結果と範囲

各試行の保存先と4種類の証拠宣言を、外部に保持したjournalと結び付けるvalidatorを追加した。別attemptのpathや、監視記録が欠けたverified宣言を拒否する。途中終了では不足した証拠をnullのまま保持できる。

対象は `anomaly_v03_attempt_descriptor.py` とCLIの `attempt-layout/attempt-validate`。fixed plan、追記store、旧trial用preflight reader、producer/独立ledger計算は変更していない。

- chunk/attempt/state、journal sequence/head、6件のidentity、source/runtime、outcomeをexactに一致させる。
- result/payload、marker、producer監視、audit結果/監視、descriptorの相対pathを固定する。
- marker/producer監視/auditのhashをjournalへ結び付け、audit監視を含むdescriptor全体を外部raw hashで固定する。
- verified_complete/inconclusiveは4証拠とaudit前後runtime一致を必須にする。producerと後日のauditのWindows build/UBR差は保持できる。
- CLIは64KiB以下のdescriptorを読み、検証後にjournal/descriptorを再照合する。

これは宣言metadataの整合性検証。入力descriptorの実際の保存場所と宣言pathの一致、成果物bytes/hash、directory topology、clean source、監視/検算本文は未検証である。`artifact_bytes_verified/filesystem_containment_verified/execution_authorized/resume_authorized/campaign_completed/independent_s6_complete/formal_permission=false`、`campaign_evaluations_credited=0`。実campaignの完了記録にはまだ接続していない。

## 確認

新規descriptor15＋既存store16＋checkpoint21の **52件pass、11.693秒、failure/error/skip0**。別attempt/roleのpath、不正hash/サイズ/型、外部pinや履歴の不一致、verifiedの不足証拠、途中失敗の監視保持、audit runtime変化、dev/smoke境界と最終chunkを確認した。読取り中の入力変更も拒否する。広い数値評価moduleや専用principal試験は実行していない。

独立レビューは新規P0〜P3所見0。担当は読取りのみ、進捗ポーリング0。repository safety/diff-check pass。

commit済み実装を使い、候補作業コピー内の `artifacts/attempt-descriptor-2026-09-17` で小規模CLI確認を行った。新worktreeなし。架空の証拠hash/サイズを使うmetadata fixtureで、datasetや成果物本文は作っていない。

| 確認 | PID | 終了コード | 秒 | peak private bytes |
| --- | ---: | ---: | ---: | ---: |
| 保存先の表示 | 32240 | 0 | 0.209 | 21479424 |
| 4証拠の宣言検証 | 32412 | 0 | 0.308 | 22265856 |
| 別attemptのmarker path拒否 | 2508 | 2（期待値） | 0.209 | 21499904 |
| audit監視欠落の拒否 | 28216 | 2（期待値） | 0.207 | 21508096 |

合計0.934秒、最大21.23MiB。所有processを各60秒/256MiB/出力2MiB上限で監視し、全終了確認、停止理由なし。CLIは入力7 filesを変更せず、attempt directory作成0、登録dataset生成0、evaluation0、ledger再検算0。

証拠17 files/310739 bytes（最終manifest除く）。`demo-evidence.json` は3087 bytes、SHA-256 **d01ba9162c32f313e84e61d94ff584ea77732eceb5d587eb7011915847d22808**。前回checkpoint-store証拠31 filesはすべて不変。

## 資源・保全

UTC2026-09-16T16:49:40（JST2026-09-17）の実演終了時、空きRAM14423298048/C151299223552/D169709887488 bytes（D約158.1GiB）。Windows build26200/UBR9445、boot2026-09-16T08:46:30.5+09:00、CPython3.14.0。実演前後runtime一致。Windows Updateのengineering緩和と正式pin維持を継続する。短いprocessの終了確認であり、長期リーク不在は未評価。

本流 **889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e** はclean。既存親policy結果書8461 bytes/SHA-256 **443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621** の未commit変更を保全し、今回のcommitから除外した。

§116の専用principal試験保留、旧保護root閉鎖、j/診断の消費済みguardを維持。principal/SAM/保護rootアクセス、UAC/ACL変更、service/task追加、push/merge/CIなし。

## 次の工程

固定pathにある実ファイルの読取りとhash/サイズ照合を実装し、descriptor・保存済み結果・終了監視・検算本文を結び付ける。小規模fixtureで境界を確認し、既存reader/auditを再利用する。実行controller、予算・source/consumer freeze、runtime inventory、profile/score導出の独立検算は残件。全dev/smoke/holdoutの長時間実行は開始していない。
