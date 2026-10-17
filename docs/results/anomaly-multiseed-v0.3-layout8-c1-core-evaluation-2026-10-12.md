# v0.3 dev layout8 C1 core実評価

2026-10-12 JST。保存済みdev coreを既存CLI C1で1cell fresh評価。CLI exit0/complete・1cell success。機械10/10・sensor10/10・precision20/20・clean誤警報0。原入力・対象source・equipment・event・incidentの対応を保存し、今回の合成dev結果を候補採択・正式受入へ読み替えない。

## 入力と実行の対応

- run ID dev-layout8-core-c1-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-08-core。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\008\attempt-0001\result\payload\manifest.json、pin {"bytes": 75698, "sha256": "c4dfa23be3bca2f563e587f4f83a33e20f5304f9bd518b791dcb6cc7b74b06b4"}。
- seed2486912926863618161/layout8/core/dev。元生成候補C0と実評価候補C1は別field。
- input10 pinsは保存C0 coreと一致。照合→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics。元payload書込み・新dataset生成・replay・追加agent0。
- actual checkout 9210b1bccbe158e45f21d83945676a362c9e6823、計算source661b27511826fcc87cb4a02930f276afbb8f95d9から不変。declared16/candidate config/compiled config一致はfull loaded runtime/native認証ではない。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}。
- elapsed 19.442542600096203秒、OS sampled peak private 148848640 bytes。
- 48 calibrated/fit各600/calibration各290/14400scores。固定C1 threshold6/persistence2、GT/matching/config/science変更0。
- input observations pin {"bytes": 9600600, "sha256": "21d68d9431838dc336794dbcc1832d1d7aedf49999cb0886f78839dbd9371ef2"}、configuration pin {"bytes": 5502, "sha256": "7081a73bba1b42cff527e5685e764380be1f3ab92f7295607703f3418da59267"}、evaluation pin {"bytes": 14071762, "sha256": "cb6102b382d7ee765b0da143e902e11d7e3103bfe4909b391c1b09f75092ce52"}。

## 原指標

| 指標 | 原値 |
| --- | --- |
| machine recall | 10/10 |
| sensor recall | 10/10 |
| precision | 20/20 |
| clean_rate | 0/3365、原value0.0 |
| effective clean | effective3255秒、原value0.0 |
| false_alert_burden | 0/20、原value0.0 |
| delay | causal-detected-only count20/min1/max2/平均1.5/中央値1.5秒 |
| availability | 13920 available / 480 unavailable |

source30/equipment20/events40/incidents20。全20 incidentはprocessed/candidate_count1/causal_detected trueで原matched target sourceを保持。未対応equipment0とclean0を別指標で保持。clean_rate/burdenの原尺度を単純確率へ換算しない。未検出0、遅延補完0。

## phase窓と原target onset

機械10件はconveyor-01.conveyor_speed、開始7260+180*k(k0–9)がphase不能でscore/residual null・thresholdfalse/streak0。各窓6行利用可能/1行phase不能。cycle00の7261 score104.35099899992103/streak1→7262 score103.2435422775604/streak2で対象source episodeが成立し、原onsetは開始+2000ms。matched equipmentのsource membershipとmatched_event_id、incident.selected_source_episode_idが同じ対象を指すことを照合した。

sensor10件はconveyor-01.motor_temperature、開始7267+180*k(k0–9)。各窓7行利用可能/phase不能0。cycle00の7267 score127.93294711055334/streak1→7268 score128.69822818823172/streak2で対象source成立、原onsetは開始+1000ms。7269 score129.3046826706978/streak3が続いても原source onset時のsupport2を保持する。

全20 target sourceの原support_score_idsは各2、machine onset+2000msが10件、sensor+1000msが10件。sourceはspeed10/vibration10/temperature10。欠測0を18000観測行とmaskの対応で照合。不能480行は全mode_recipe_or_phase、全score/residual null・threshold_exceeded false。phaseと欠測を区別する。原全20 event/incident、matched target-source-equipment20、四target窓、全episodes、不能480 scoreを保存。入力対応・保存・状態分類の実経路不具合は観測していない。

## 保存C0と過去C1 coreの比較

同input10の保存C0 coreと、過去8 layouts C1 coreをmanifest/configだけ比較。今回を加えて10比較セル、うちC1 coreは9 layouts。declared16/candidate config/compiled config一致、同layout8 inputpins一致、別layoutの原pin差を保持。旧result本文再展開・モデル再compute0。

| layout | 候補 | machine | sensor | precision | clean件数 | available |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | C1 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 1 | C1 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 2 | C1 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 3 | C1 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 4 | C1 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 5 | C1 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 6 | C1 | 0/10 | 10/10 | 10/20 | 0 | 13920 |
| 7 | C1 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 8 | C0 | 0/10 | 0/10 | 0/3 | 3 | 13920 |
| 8 | C1 | 10/10 | 10/10 | 20/20 | 0 | 13920 |

C0の機械0/sensor0/precision0/3/clean3/delay nullを保持し、今回の成功へ書き換えない。既存49完了boardをmetadataで継承し今回1セルを加えて50セル。1つの合成dev seedのlayout差であり9独立seed/50独立datasetではない。layout8 C2 coreとqualityは未実施。原failed runと明示replayをboardへ混ぜず保持。bootstrap/統計CI・勝者・採択0。

## 原保存と検証記録

- model: artifacts/representative-layout8-core-c1-20261012-records/root-closed.json。
- analysis/extract: artifacts/representative-layout8-core-c1-20261012-analysis/root-closed.json。
- DATA: artifacts/representative-anomaly-evaluation/dev-layout8-core-c1-20261012/root-closed.json、{"bytes": 27113087, "files": 19, "manifest_pin": {"bytes": 2225, "sha256": "8ab9077bbb6d646bf4b0ac0804352de90b46d47a5f9446fccf89d003bfac1130"}}。
- docs/Git: artifacts/representative-layout8-core-c1-20261012-save/root-closed.json、git-summary/target-onset-summary/next-dev-selection labels。
- 最終保存: artifacts/representative-layout8-core-c1-20261012-final/root-closed.json、post-save label。

共通EvidenceStoreでselected-windows 1003032B/4parts、unavailable-scores 461979B/2parts、analysis 350763B/2partsを自動分割。新検証root16MiB/512files、part256KiB、失敗reserve2MiB/16files（内閉鎖512KiB/4files）。 [保存方針](../anomaly/execution/verification-records.md) はrecord_integrityとrecorded_statusを区別。

今回helper/model失敗0、全過去failed16/missing original execution1保持。CLI redirect rawはhelper全process stdioではない。full creation/start_tokenとCIM照合、PID単独/EOF/closedからnative回収を補わない。閉鎖/外部固定root追記・原raw整理移動削除0。

同種合成dev結果・ユーザー名PC内input path・同 https://github.com/tyaro/banto-ai.git への継続承認範囲で、report/handoff/results index3を一回[skip ci] commit/push。原返値/HEAD-upstream-remote-clean/docpinsはGit記録を参照。

## 次工程と正式gate

次は同保存chunk008/同seed/layout8/core、C2 c2-phase-conditional、新ID dev-layout8-core-c2-20261012へ1cell実評価。同manifest/input10、観測本文はC0/C1読取済み/次model未実行。元生成C0/次実評価C2別field、元payload保持・新dataset生成0。

評価900秒/2GiB/output1GiB/single32MiB/files32、Git累積30秒/batch16entry512KiB/stdout1MiB/stderr128KiB、固定protocol/native契約は不変。checkpointはblocking中断/full loaded runtime/native/global容量証明ではない。ACTIVE/automation設定へ結果・PC path転記0。CI381385/code661の4130success保存、新CIquery/download/verifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了/create_native早期拒否/全7役reader禁止/追加agent禁止。Sol容量/人停止では原保全後PAUSED・重複再試行0。
