# v0.3 dev layout7 C0 core実評価

2026-10-12 JST。保存済みdev coreをC0で1cell fresh実評価。CLI exit0/complete・1cell successで終了した。機械0/10・sensor0/10・precision0/3・clean誤警報3。処理成功を性能合格・採択・正式受入へ読み替えない。

## 入力・設定・実行の対応

- run ID: dev-layout7-core-c0-20261012。
- 元manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\007\attempt-0001\result\payload\manifest.json、pin {"bytes": 75699, "sha256": "0963abc39d429bc6322694bf57f111ce12b0ce5c5a9009e177812cb3989dcaef"}。
- dataset anomaly-v03-dev-seed-2486912926863618161-layout-07-core、seed2486912926863618161/layout7/core/role dev。元生成C0と実評価C0は別fieldとして保持。
- 全10入力fileをpin照合して新snapshotへ保存し、fresh fit/calibration→原profiles/scores/episodes/events/incidents/metricsを保持。元payload書込み・新dataset生成・replay・追加agent0。
- actual checkout d6142cf364e4db2facb35be9cd071ee5dfc31133。計算source661b27511826fcc87cb4a02930f276afbb8f95d9から不変。既存7 layoutsの保存C0 coreとdeclared16 calculator sources/candidate config/compiled config一致。declared source pinはfull loaded runtime/native認証ではない。
- actual runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}。
- elapsed 25.937567599932663秒、OS sampled peak private 147099648 bytes。
- C0固定threshold4/persistence2、GT/matching/config/science変更0。48 calibrated profiles、fit各0/calibration各290。

## 原指標

| 指標 | 値 |
| --- | --- |
| machine recall | 0/10 |
| sensor recall | 0/10 |
| precision | 0/3 |
| clean_rate | 3/3365、原value 25.676077265973255 |
| effective_clean_rate | effective3255秒、原value 26.543778801843317 |
| false_alert_burden | 3/20、原value15.0 |
| delay_summary | 検出count0、全20 incidentはdelay null |
| availability | 13920 available / 480 unavailable（14400 scores） |

clean_rateとburdenは原尺度を保持し、単純確率へ変換しない。source3/equipment3、events40/incidents20。全3 equipmentはmatched_event_id null/clean文脈付き。原onsetはmotor-01 vibration7242、conveyor-01 temperature7712、motor-01 vibration8517。clean3と未対応3を別に保存。

不能480はprimary reasonとnonexclusive tagがともにmode_recipe_or_phaseのみ。不能score/residualはnull、threshold_exceeded false。18000観測行とquality-maskが対応し、欠測は0。

## 全20未検出の原経路

全incidentはno_candidate_in_window/candidate_count0/causal_detected false、matched null、delay null。検出遅延のnull補完0。全20窓の四target scores、原event/incident、source/equipment episodes、不能480行を保存。

機械異常10件の対象はconveyor-01.conveyor_speed、各窓7行が利用可能でphase利用不能0。各窓の最大scoreは51.90802420682417–53.507638645573905で閾値4を超えるが、最大streakは1。cycle00は7251 score51.131982601457715/streak1→7252 score0.4735015667198125/streak0、7254 score53.00939066172789/streak1→7255 score0.6132282878104693/streak0。固定連続2点を満たさず、対象source onsetとcandidate episodeはない。

sensor異常10件の対象はconveyor-01.motor_temperature、各窓の開始sample7230+180*k（k0–9）がphaseで利用不能、残る6行が利用可能。各窓最大streak1。cycle00は7230 score/residual null・streak0→7231 score3.724346289023876/streak0→7232 score3.0280868700292842/streak0→7233 score191.43560585329374/streak1→7234 score1.9811650997101447/streak0。欠測0でも利用不能phaseと連続超過不成立を原状態で保持する。

layout6では機械窓のC0 scoreが閾値未満だったが、今回layout7は閾値を超えてもstreak2に至らない。条件差を一つの原因へまとめず、元score/phase/persistenceを保持。入力対応・保存・状態分類の実経路不具合は観測していない。

## 保存済みC0 coreの8 layouts比較

旧7セルはmanifest/configだけを比較し、旧result本文再展開・モデル再compute0。全セルは同じ合成dev seedの別layoutであり、8独立seedではない。input10 file名は同じでpin差を保存。

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

既存42セル（layouts0–6の3候補×2strata）は保存board参照のまま継承。今回1セルを加えて43完了セル、layout7 core C1/C2とquality候補は未実施。bootstrap/統計CI・勝者・採択0。

## 原保存と補助記録

- model records: artifacts/representative-layout7-core-c0-20261012-records/root-closed.json。
- analysis/extract: artifacts/representative-layout7-core-c0-20261012-analysis/root-closed.json。
- DATA: artifacts/representative-anomaly-evaluation/dev-layout7-core-c0-20261012/root-closed.json、{"bytes": 26940730, "files": 19, "manifest_pin": {"bytes": 2225, "sha256": "a8f530fe2616253f74f068106aecad7a5e05fbc539319a76160a8bd9a7d90b66"}}。
- docs/Git: artifacts/representative-layout7-core-c0-20261012-save/root-closed.json、git-summary label。
- 最終保存: artifacts/representative-layout7-core-c0-20261012-final/root-closed.json、post-save label。

新共通EvidenceStoreでraw/JSONを256KiB partsへ自動分割。selected-windows 945501B/4parts、unavailable-scores 463420B/2parts、analysis 302574B/2parts。新検証root16MiB/512files、失敗reserve2MiB/16files（内閉鎖512KiB/4files）。 [保存API](../anomaly/execution/verification-records.md) の読取りCLIはrecord_integrityとrecorded_statusを区別する。

補助source構築の一回のtarget文字列不一致はfunctions.exec isolateでprocess/tools/tracked mutation前に停止し、原messageをmodel recordsのsource-builder-failure labelへ保存。誤った対象文字列だけを修正して新sourceを構築し、hash/seedの無限定置換0。analysis出力のcycle00_machine_four_target_rows表示名は最初のsensor窓を指していたが、canonical selected-windowsは原event_class/targetを保持。表示名誤りを別metadataに保存し、原stdio/evidenceを書換えない。これらをinstrumented helper/model/CI/native/Sol容量failureへ追加しない。

原failed16とmissing original execution1を保持。full creation/start_token一致・CIM同original不在を照合し、PIDだけ又はEOF/closedからnative回収を主張しない。redirectしたCLI rawはhelper全process stdioではない。過去閉鎖/外部固定rootへの追記・raw整理移動削除0。

## 次工程と制限

次は同保存chunk007/layout7/core C1 c1-phase-level、新IDdev-layout7-core-c1-20261012へ1cell評価。元manifestと10input pinは今回と同一、次modelは未実行。元生成candidate C0と次実評価candidate C1を別fieldに保持。

評価900秒/2GiB/output1GiB/single32MiB/files32、Git累積30秒/batch16entry512KiB/stdout1MiB/stderr128KiB、固定protocol/native契約は不変。engineering checkpointはblocking中断/full loaded runtime/native/global容量の証明ではない。今回handoff/report/index3文書を、同種合成dev結果/ユーザー名を含むPC内input path/同GitHub送信先への継続承認範囲で一回[skip ci] commit/pushし、原返値とHEAD/upstream/remote/cleanを別保存。

ACTIVE維持、automation設定へ結果/PC path転記0。CI381385/code661の4130success保存を継承し、新CIquery/download/verifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了、create_native早期拒否/全7役reader禁止/追加agent禁止を維持。Sol容量/人停止では原保全後PAUSED・重複再試行0。
