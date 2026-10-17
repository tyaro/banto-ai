# v0.3 dev layout7 C2 core実評価とcore3候補比較

2026-10-12 JST。既存CLIで保存済みdev coreのC2を1cell fresh評価し、layout7 coreの3候補比較を完成した。CLI exit0/complete・1cell success。機械10/10・sensor10/10・precision20/20・clean誤警報0。合成devの同一seed条件であり、処理成功やこの結果を性能合格・採択・正式受入へしない。

## 入力・設定・実行の対応

- run ID dev-layout7-core-c2-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-07-core。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\007\attempt-0001\result\payload\manifest.json、pin {"bytes": 75699, "sha256": "0963abc39d429bc6322694bf57f111ce12b0ce5c5a9009e177812cb3989dcaef"}。
- seed2486912926863618161/layout7/core/dev。元生成C0と実評価C2は別field。input10 pinsは保存C0/C1と同一、各候補で新snapshot/fresh fit/calibrationから原結果を保存。
- 元payload書込み・新dataset生成・replay・追加agent0。
- actual checkout 8a5a3f258034904d306745e471a36d56f48fb0b4、計算source661b27511826fcc87cb4a02930f276afbb8f95d9から不変。宣言16calculator/candidate config/compiled config一致はfull loaded runtime/native認証ではない。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}。
- elapsed 29.212133800028823秒、OS sampled peak private 206524416 bytes。候補間の速度順位や容量合格へ解釈しない。
- 48 calibrated/fit各600/calibration各290/C2state48/14400scores。固定C2 threshold6/persistence2、GT/matching/config/science変更0。

## 原指標と対象onset

| 指標 | 原値 |
| --- | --- |
| machine recall | 10/10 |
| sensor recall | 10/10 |
| precision | 20/20 |
| clean_rate | 0/3365、原value0.0 |
| effective clean | effective3255秒、原value0.0 |
| false_alert_burden | 0/20、原value0.0 |
| delay | count20/min1/max2/平均1.5/中央値1.5秒、causal-detected-only |
| availability | 13920 available / 480 unavailable |

source30/equipment20/events40/incidents20。sourceはconveyor-01 temperature/speed/vibration各10。全20 equipmentが原eventにmatched、未対応0/clean0を別に保持。全incidentはcausal_detected/candidate_count1。原selected target sourceのfull_target/support、equipmentのsource membership/matched_event_id、incidentを照合した。

機械10件の対象conveyor-01.conveyor_speed source onsetはevent開始+1000ms、support2。各窓7行利用可能/phase不能0。cycle00は7251 score72.8963352711141/streak1→7252 score73.65412140196715/streak2で対象source成立、7253 score74.23828801707882/streak3。原matched equipmentはspeedとvibrationのsourceを保持し、対象speed onsetに対応。

sensor10件の対象conveyor-01.motor_temperatureは各窓開始7230+180*k(k0–9)がphase不能、残る6行利用可能。対象source onsetはevent開始+2000ms、support2。cycle00 7230 score/residual null・thresholdfalse/streak0→7231 score139.4611899900228/streak1→7232 score139.64589496847458/streak2で対象source成立、7233 score1.1421376238086105/streak0。開始点の不能と2秒遅延を原状態で保持。

全20検出はmachine10×1秒/sensor10×2秒、未検出0/null補完0。不能480はprimary/nonexclusiveともmode_recipe_or_phaseのみで、全不能score/residual null・threshold_exceeded false。観測とquality-mask18000行が対応し、欠測0。全20event/incident、matched target-source-equipment、四target窓、全episodes、不能480行を保存。入力対応・保存・状態分類の実経路不具合は観測していない。

## 保存済み候補比較

同core C0/C1と過去7 layouts C2 coreの計9保存セルはmanifest/configだけを比較。旧result本文再展開・モデル再compute0。今回C2を加えて比較10セル。input10 names一致、同layout7ではpins完全一致、別layoutでは原pin差を保持。

| layout | 候補 | machine | sensor | precision | clean件数 | delay中央値秒 |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | C2 | 4/10 | 10/10 | 14/20 | 0 | 1.0 |
| 1 | C2 | 10/10 | 10/10 | 20/20 | 0 | 1.0 |
| 2 | C2 | 10/10 | 10/10 | 20/20 | 0 | 1.0 |
| 3 | C2 | 10/10 | 10/10 | 20/20 | 0 | 1.5 |
| 4 | C2 | 10/10 | 10/10 | 20/20 | 0 | 1.5 |
| 5 | C2 | 10/10 | 10/10 | 20/20 | 0 | 1.0 |
| 6 | C2 | 0/10 | 10/10 | 10/20 | 0 | 1.0 |
| 7 | C0 | 0/10 | 0/10 | 0/3 | 3 | None |
| 7 | C1 | 10/10 | 10/10 | 20/20 | 0 | 1.5 |
| 7 | C2 | 10/10 | 10/10 | 20/20 | 0 | 1.5 |

layout7 core3候補比較完成。C0の0/10・0/10・precision0/3・clean3・delay nullを原値で保持。C1/C2はこの条件の集計指標と対象onset offsetsが一致するが、score/原結果bytesの一致を主張しない。fixed候補差と別layoutでの機械検出差を保持し、勝者や採択へしない。

既存44完了boardをmetadata参照で継承して新1を加え45セル。same seed8layoutsであり、45独立dataset/seedではない。layout7 quality3候補は未実施。bootstrap/統計CI0。

## 原保存・検証記録

- model records: artifacts/representative-layout7-core-c2-20261012-records/root-closed.json。
- analysis/extract: artifacts/representative-layout7-core-c2-20261012-analysis/root-closed.json。
- DATA: artifacts/representative-anomaly-evaluation/dev-layout7-core-c2-20261012/root-closed.json、{"bytes": 37781370, "files": 19, "manifest_pin": {"bytes": 2225, "sha256": "95ec52e9e9168d8b1ed3db4d83418502dc7615a82affdd23a204863b750f6433"}}。
- docs/Git: artifacts/representative-layout7-core-c2-20261012-save/root-closed.json、git-summary/target-onset-summary/next-dev-selection labels。
- 最終保存: artifacts/representative-layout7-core-c2-20261012-final/root-closed.json、post-save label。

共通EvidenceStoreがselected-windows 1718420B/7parts、unavailable-scores 816438B/4parts、analysis 323042B/2partsを自動分割保存。新検証root16MiB/512files、part256KiB、失敗reserve2MiB/16files（内閉鎖512KiB/4files）。 [保存方針](../anomaly/execution/verification-records.md) はrecord_integrity/recorded_statusを区別する。

今回helper/model失敗0、全過去failed16/missing original execution1を保持。full creation/start_token一致とCIM同original不在を照合。CLI redirect rawはhelper全process stdioではない。PID単独/EOF/closedからnative回収を補わない。閉鎖/外部固定root追記・原raw整理移動削除0。

同種合成dev結果・ユーザー名PC内input path・同 https://github.com/tyaro/banto-ai.git への継続承認範囲で、report/handoff/results index3を一回[skip ci] commit/push。原返値とHEAD/upstream/remote/clean/docpinsはGit記録を参照。

## 次工程と正式gate

次は同保存chunk007/layout7 quality-stressをC1 c1-phase-level、新IDdev-layout7-quality-c1-20261012へ1cell評価する。dataset anomaly-v03-dev-seed-2486912926863618161-layout-07-quality-stress、同manifest0963 pin/input10 metadata選択のみ。元生成C0と次実評価C1は別field。次quality観測本文は未読、next model未実行、元payload保持・新dataset生成0。

評価900秒/2GiB/output1GiB/single32MiB/files32、Git累積30秒/batch16entry512KiB/stdout1MiB/stderr128KiB、固定protocol/native契約は不変。checkpointはblocking中断/full loaded runtime/native/global容量の証明ではない。ACTIVE/automation設定へ結果・PC path転記0。CI381385/code661の4130success保存、新CIquery/download/verifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了/create_native早期拒否/全7役reader禁止/追加agent禁止を維持。Sol容量/人停止では原保全後PAUSED、重複再試行0。
