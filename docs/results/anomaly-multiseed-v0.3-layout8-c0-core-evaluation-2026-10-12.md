# v0.3 dev layout8 C0 core実評価

2026-10-12 JST。保存済みdev coreを既存CLI C0で1cell fresh評価。CLI exit0/complete・1cell success。機械0/10・sensor0/10・precision0/3・clean誤警報3を原値で保持する。処理完了を性能合格・候補採択・正式受入へ読み替えない。

## 入力と実行の対応

- run ID dev-layout8-core-c0-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-08-core。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\008\attempt-0001\result\payload\manifest.json、pin {"bytes": 75698, "sha256": "c4dfa23be3bca2f563e587f4f83a33e20f5304f9bd518b791dcb6cc7b74b06b4"}。
- seed2486912926863618161/layout8/core/dev。元生成候補C0と実評価候補C0は別field。
- input10 pinsを照合→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metricsを保存。元payload書込み・新dataset生成・replay・追加agent0。
- actual checkout 8bb5403e7883892cd9d50060623747a007753db9、計算source661b27511826fcc87cb4a02930f276afbb8f95d9から不変。declared16/candidate config/compiled config一致はfull loaded runtime/native認証ではない。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}。
- elapsed 30.171495700022206秒、OS sampled peak private 147345408 bytes。
- 48 calibrated/fit各0/calibration各290/14400scores。固定C0 threshold4/persistence2、GT/matching/config/science変更0。
- input observations pin {"bytes": 9600600, "sha256": "21d68d9431838dc336794dbcc1832d1d7aedf49999cb0886f78839dbd9371ef2"}、configuration pin {"bytes": 5503, "sha256": "8fd5cef93984d11cca81b5d2ca180c6407ee908998fee917b06d53bcdbe4bbee"}、evaluation pin {"bytes": 13899459, "sha256": "70f190a19c584b65d1a82d6593525690b2f9c657c235b486adaa6c679a4377d1"}。

## 原指標

| 指標 | 原値 |
| --- | --- |
| machine recall | 0/10 |
| sensor recall | 0/10 |
| precision | 0/3 |
| clean_rate | 3/3365、原value25.676077265973255 |
| effective clean | effective3255秒、原value26.543778801843317 |
| false_alert_burden | 3/20、原value15.0 |
| delay | causal-detected-only count0、min/max/mean/median null |
| availability | 13920 available / 480 unavailable |

source3/equipment3/events40/incidents20。全20 incidentはprocessed、candidate_count0/no_candidate_in_window/causal_detected false/matched null/delay null。処理状態と検出結果を区別し、遅延補完0。全未対応equipment3とclean3を別指標で保持。clean_rate/burdenの原尺度を単純確率へ換算しない。

## phaseと対象窓の不成立

機械10件はconveyor-01.conveyor_speed、開始7260+180*k(k0–9)がphase不能でscore/residual null・thresholdfalse/streak0。各窓6行利用可能/1行phase不能/最大streak1、窓内最大score80.07506644738844–82.04061090947918。cycle00は7260 null/0→7261 score.12267601921717763/0→7262 .6104700644959261/0→7263 score80.07506644738844/1→7264 1.521855583098382/0。固定persistence2で対象source episodeが成立しない。

sensor10件はconveyor-01.motor_temperature、開始7267+180*k(k0–9)。各窓7行利用可能/phase不能0/最大streak1、最大score216.98763375414546–218.79276365682608。cycle00は7267 score216.98763375414546/1→7268 1.515764244981574/0、7270 score215.6408479931459/1→7271 .014407967311507841/0。閾値4の超過が離れているため連続2回にならない。

欠測0を18000観測行とmaskの対応で照合。不能480行は全mode_recipe_or_phase、全score/residual null・threshold_exceeded false。phase開始不能だけでsensorを含む全20 missを説明しない。原target score・event・incidentを結んで保存し、GT・threshold・persistence・matchingを変えて成功へ補わない。入力対応・保存・状態分類の実経路不具合は観測していない。

3件の原未対応equipmentはcleanタグ/元matched null。onset sample7242 motor-01 vibration、7712 conveyor-01 temperature、8517 motor-01 vibration。対象窓内の候補数0とclean3を別に保存。全20 event/incident、四target窓、全source/equipment episodes、不能480 score、欠測0原入力対応を保持。

## 保存済みC0 coreとの比較

過去8 layoutsのC0 coreはmanifest/configだけを比較。今回を加えて9比較セル。declared16/candidate config/compiled config一致、別layoutのinput10 pin差を保持。旧result本文再展開・モデル再compute0。

| layout | machine | sensor | precision | clean件数 | available |
| --- | --- | --- | --- | --- | --- |
| 0 | 0/10 | 0/10 | 0/3 | 3 | 13920 |
| 1 | 0/10 | 0/10 | 0/3 | 2 | 13920 |
| 2 | 0/10 | 0/10 | 0/3 | 3 | 13920 |
| 3 | 0/10 | 0/10 | 0/3 | 3 | 13920 |
| 4 | 0/10 | 0/10 | 0/3 | 3 | 13920 |
| 5 | 0/10 | 0/10 | 0/3 | 3 | 13920 |
| 6 | 0/10 | 0/10 | 0/3 | 3 | 13920 |
| 7 | 0/10 | 0/10 | 0/3 | 3 | 13920 |
| 8 | 0/10 | 0/10 | 0/3 | 3 | 13920 |

既存8 layouts×2条件×3候補の48完了boardをmetadataで継承し、今回1セルを加えて49セル。同じseedのlayout差であり独立seed9件/49独立datasetではない。layout8の他候補とqualityは未実施。原failed runや明示replayを比較boardへ混ぜず保持。bootstrap/統計CI・勝者・採択0。

## 原保存と検証記録

- model: artifacts/representative-layout8-core-c0-20261012-records/root-closed.json。
- analysis/extract: artifacts/representative-layout8-core-c0-20261012-analysis/root-closed.json。
- DATA: artifacts/representative-anomaly-evaluation/dev-layout8-core-c0-20261012/root-closed.json、{"bytes": 26940845, "files": 19, "manifest_pin": {"bytes": 2225, "sha256": "fa9531f4d076da4d3a94308e9511598a73e1437487fc5c58446827c3a415ad96"}}。
- docs/Git: artifacts/representative-layout8-core-c0-20261012-save/root-closed.json、git-summary/target-onset-summary/next-dev-selection labels。
- 最終保存: artifacts/representative-layout8-core-c0-20261012-final/root-closed.json、post-save label。

共通EvidenceStoreでselected-windows 946989B/4parts、unavailable-scores 463420B/2parts、analysis 340768B/2partsを自動分割。新検証root16MiB/512files、part256KiB、失敗reserve2MiB/16files（内閉鎖512KiB/4files）。 [保存方針](../anomaly/execution/verification-records.md) はrecord_integrityとrecorded_statusを区別。

今回helper/model失敗0、全過去failed16/missing original execution1保持。CLI redirect rawはhelper全process stdioではない。full creation/start_tokenとCIM照合、PID単独/EOF/closedからnative回収を補わない。閉鎖/外部固定root追記・原raw整理移動削除0。

同種合成dev結果・ユーザー名PC内input path・同 https://github.com/tyaro/banto-ai.git への継続承認範囲で、report/handoff/results index3を一回[skip ci] commit/push。原返値/HEAD-upstream-remote-clean/docpinsはGit記録を参照。

## 次工程と正式gate

次は同保存chunk008/同seed/layout8/core、C1 c1-phase-level、新ID dev-layout8-core-c1-20261012へ1cell実評価。同manifest/input10、観測本文は今回C0で読取済み/次model未実行。元生成C0/次実評価C1別field、元payload保持・新dataset生成0。

評価900秒/2GiB/output1GiB/single32MiB/files32、Git累積30秒/batch16entry512KiB/stdout1MiB/stderr128KiB、固定protocol/native契約は不変。checkpointはblocking中断/full loaded runtime/native/global容量証明ではない。ACTIVE/automation設定へ結果・PC path転記0。CI381385/code661の4130success保存、新CIquery/download/verifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了/create_native早期拒否/全7役reader禁止/追加agent禁止。Sol容量/人停止では原保全後PAUSED・重複再試行0。
