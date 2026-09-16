# 固定campaign計画と進捗記録の復元

2026-09-16。実装commit **9c9975294fe4c22c1cc8dbffbcc140cf00c687e1**。
固定plan/validatorとjournal reader/reducerを実装した。[使い方と境界](../anomaly-v03-independent-audit-and-checkpoints.md#実装済みのmetadata-cli)。実行controller・追記writer・保存済み成果物の再照合は未接続で、データ生成や評価計算は行っていない。

## 実装と検証

- dev96 chunks/576 evaluations→smoke24/144、合計120/720を登録順に固定。2層×3候補の順序・identity・hash・参照revision・runtime方針を検査する。予算は未確定のままnull、metadata_only/execution_authorized=false。
- 外部に保持したplan hash・record件数・末尾hashを必須にし、欠落・並替え・重複・途中JSON・余分なファイル・source/context差分を拒否する。末尾hashを読み込んだjournalから自動取得して検証根拠にしない。
- running→保存済み検証待ち→検証済み宣言を区別。markerのみでは完了扱いせず、失敗/中断後は同じchunkの新attemptを要求する。旧attemptの理由・監視証拠・contextを保持し、integrity失敗後は停止する。
- 全120 chunksが検証済みと宣言されても、evidence_revalidated/resume_authorized/campaign_completed/independent_s6_completeはfalse。保存内容の再照合なしで実行再開・成果物省略・性能合格へ進めない。

新規テスト初回19件pass/1.530秒。独立レビューでP2が1件あり、公開前に停止したattemptではmarkerなしのsupervision hashを記録できない条件を修正した。失敗時のhash保持とretry後の履歴、読取り途中の変更拒否を追加確認し、**最終21件pass/1.993秒、failure/error/skip0**。再レビュー所見0、進捗poll0。repository safety/diff-check pass。広い重い評価moduleは実行していない。

## 小規模CLI実演

`artifacts/checkpoint-metadata-2026-09-16` にmetadata fixtureだけを作成した。planの参照revisionはproducer/consumerとも実装commit。attempt証拠hashは明示的な架空値で、既存trialや新campaignの実績を表していない。

| 処理 | PID | 経過秒 | peak private bytes | 結果 |
| --- | ---: | ---: | ---: | --- |
| plan表示 | 22784 | 0.224 | 19,853,312 | exit0 |
| fixture journal読取り | 8076 | 0.310 | 21,057,536 | exit0 |

所有する各processだけを60秒/256MiB/出力2MiBで監視し、両processの終了を確認。停止理由なし。最大約20.08MiBはこの小規模実演の値で、長時間リーク不在を証明しない。
4 recordsでattempt1のresource_limit失敗（markerなし・監視hashあり）、attempt2の保存済み検証待ちを再現。復元結果はfailed history1、attempts2、saved_pending_verification1、not_started119、next_action=verify_saved_attempt。失敗側の監視hashを保持した。
plan・外部pin・journalの6入力ファイルは実行前後不変。前回独立ledger検算の証拠9ファイルも全て不変。

canonical plan hashは `49cb7052e0bcf4cbc978d536b798b1649255018d16810813ee2ca57aee3ab707`、末尾record hashは `330ce5fafe673a213242b3776add48a1c09de0c5b5cc1b3449d1198c0e5051a8`。
`demo-evidence.json` のSHA-256は `e551aa7751d8edcd2cda0efc16c0c649f95f69040039b1ce6cdf220484dea3d2`。実演証拠11ファイル308504 bytes（最終保存manifestを除く）。

UTC04:46:36の空きRAM15,625,842,688/C151,835,779,072/D171,825,303,552 bytes（D約160.0GiB）。OS26200.9445/boot2026-09-16T08:46:30.5000000+09:00。Windows Updateのengineering緩和と正式pin維持を継続。
本流889cfc3/clean、既存producer0086ffe/consumer0c8377dもclean。既存親policy文書の未commit変更は8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621のまま保全・commit除外。

## 次の工程

保存済み6件を読取り専用で参照する証拠照合を接続し、journalの宣言と実ファイルのhash/来歴/監視/検算を結び付ける。旧trialはpreflight参照に限定し、新campaign coverageを充足させない。その後に追記writerとcontrollerを接続する。
profile/score導出の独立検算、runtime inventory、全体と各区切りの予算、source/consumer freezeは残件。全dev/smoke・holdoutの実行開始はまだ行わない。専用principal等の追加試験は保留のまま、旧保護root/SAMアクセスやUAC/ACL変更、push/merge/CIなし。
formal_permission/native_launch_authorized/isolation_certified/protected_commit_allowed/future_immutability_proven/execution_authenticated/native_publication_performed/raw_consumer_payload_release_enabled=false、acceptance_status=not_completed、performance_status=not_evaluated。
