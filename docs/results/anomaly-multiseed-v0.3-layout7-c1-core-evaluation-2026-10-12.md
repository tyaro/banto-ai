# v0.3 dev layout7 C1 core実評価

2026-10-12 JST。既存CLIで保存済みdev coreをC1で1cell fresh評価。CLI exit0/complete・1cell success。機械10/10・sensor10/10・precision20/20・clean誤警報0。合成devの同一seed条件であり、処理successやこの検出結果を性能合格・採択・正式受入へ補わない。

## 入力と実行条件

- ID dev-layout7-core-c1-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-07-core。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\007\attempt-0001\result\payload\manifest.json、pin {"bytes": 75699, "sha256": "0963abc39d429bc6322694bf57f111ce12b0ce5c5a9009e177812cb3989dcaef"}。
- seed2486912926863618161/layout7/core/role dev。元生成candidate C0と実評価candidate C1を別fieldで保持。10input pin照合→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics。
- 原payload書込み・新dataset生成・replay・追加agent0。保存済み同core C0とinput10 pinsが完全一致。
- actual checkout 305c6e16402712271bed2162bfb7200793327a5b。計算source661b27511826fcc87cb4a02930f276afbb8f95d9から不変。宣言16calculator/candidate config/compiled config一致はfull loaded runtime/native認証ではない。
- actual runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}。
- elapsed 56.616587699973024秒、OS sampled peak private 148983808 bytes。
- 48 calibrated profiles、fit各600/calibration各290、14400scores。固定C1 threshold6/persistence2、GT/matching/config/science変更0。

## 原指標と検出対応

| 指標 | 原値 |
| --- | --- |
| machine recall | 10/10 |
| sensor recall | 10/10 |
| precision | 20/20 |
| clean_rate | 0/3365、原value0.0 |
| effective_clean_rate | effective3255秒、原value0.0 |
| false_alert_burden | 0/20、原value0.0 |
| delay | count20/min1/max2/平均1.5/中央値1.5秒、causal-detected-only |
| availability | 13920 available / 480 unavailable |

source30/equipment20/events40/incidents20。temperature/speed/vibrationの各source10。全20 equipmentは原eventにmatched、未対応0とclean0を別指標で保存。clean_rate/burdenの原尺度を保ち、単純確率へ換算しない。全incidentはcausal_detected/candidate_count1。原selected target sourceのfull_target、support、equipment source membership、matched_event_id、incidentを照合し、対象onsetを他targetのonsetで補わない。

機械10件の対象はconveyor-01.conveyor_speed。全対象source onsetはevent開始+1000ms、固定support2。cycle00は7251 score75.81549660690442/streak1→7252 score76.61301809848732/streak2で対象source成立、7253 score77.1622722857481/streak3。原matched equipmentはspeedとvibrationの2sourcesを含み、選択対象speed onsetに対応。各機械窓7行は利用可能、phase不能0。

sensor10件の対象はconveyor-01.motor_temperature。各窓開始7230+180*k（k0–9）はphase不能でscore/residual null・thresholdfalse/streak0。残る6行で全対象source onsetがevent開始+2000ms、support2。cycle00は7231 score137.93097585039513/streak1→7232 score138.18032126903094/streak2で対象source成立。7233 score0.9929985988014204/streak0へ戻る。開始点の不能を除外したことにせず、原phaseと2秒遅延を保持。

全20検出はmachine10×1秒/sensor10×2秒。未検出0でありnull補完0。対象onset以降のstreakとepisodeを別に保持。入力対応・保存・状態分類の実経路不具合は観測していない。

## 利用不能と原保存

不能480はprimary reason/nonexclusive tagsともmode_recipe_or_phaseのみ。全不能score/residual null・threshold_exceeded false。観測とquality-maskの18000行が対応し、欠測0。全20原event/incidentとmatched target-source-equipment、全20窓四targets、全source/equipment、不能480行を保存。

## 同条件C0と8 layoutsの保存C1比較

| layout | 候補 | machine | sensor | precision | clean件数 | delay中央値秒 |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | C1 | 10/10 | 10/10 | 20/20 | 0 | 1.5 |
| 1 | C1 | 10/10 | 10/10 | 20/20 | 0 | 1.0 |
| 2 | C1 | 10/10 | 10/10 | 20/20 | 0 | 1.0 |
| 3 | C1 | 10/10 | 10/10 | 20/20 | 0 | 1.5 |
| 4 | C1 | 10/10 | 10/10 | 20/20 | 0 | 1.5 |
| 5 | C1 | 10/10 | 10/10 | 20/20 | 0 | 1.0 |
| 6 | C1 | 0/10 | 10/10 | 10/20 | 0 | 1.0 |
| 7 | C0 | 0/10 | 0/10 | 0/3 | 3 | None |
| 7 | C1 | 10/10 | 10/10 | 20/20 | 0 | 1.5 |

比較9セルは保存C1 core layouts0–6の7セル、同入力layout7 C0、今回C1。旧8セルはmanifest/configのみ、旧result本文再展開・モデル再compute0。同input pinのC0は機械0/10・sensor0/10・precision0/3・clean3、delay nullとして保存済みであり、その原結果を書換えない。C0/C1の固定candidate差を保つ。

既存43完了boardをmetadata参照で継承し新1を加えて44セル。8 layoutsは同一seedであり独立seed/datasetへ数えない。layout6 C1 machine0/10等の条件差を保持。layout7 core C2/quality候補は未実施。bootstrap/統計CI・勝者・採択0。

## 検証記録とGit保存

- model records: artifacts/representative-layout7-core-c1-20261012-records/root-closed.json。
- analysis/extract: artifacts/representative-layout7-core-c1-20261012-analysis/root-closed.json。
- DATA: artifacts/representative-anomaly-evaluation/dev-layout7-core-c1-20261012/root-closed.json、{"bytes": 27113858, "files": 19, "manifest_pin": {"bytes": 2225, "sha256": "9ab32c03e79e9a44aeaac019cf369e15aa9a56019648294ff4ae8eeef9c282ea"}}。
- docs/Git: artifacts/representative-layout7-core-c1-20261012-save/root-closed.json、git-summary/target-onset-summary labels。
- 最終保存: artifacts/representative-layout7-core-c1-20261012-final/root-closed.json、post-save label。

新共通EvidenceStoreで自動分割。selected-windows 1000285B/4parts、unavailable-scores 461979B/2parts、analysis 312604B/2parts。新検証root16MiB/512files・part256KiB・失敗reserve2MiB/16files（内閉鎖512KiB/4files）。 [読取り・保存方針](../anomaly/execution/verification-records.md) はrecord_integrityとrecorded_statusを区別する。

今回helper/model失敗0、全過去failed16/missing original execution1を保持。full creation/start_token一致とCIM同original不在を照合。redirectしたCLI rawはhelper全process stdioではない。PID単独/EOF/closedからnative回収を補わない。原閉鎖/外部固定root追記・raw整理移動削除0。前回C0 commit説明の旧layout6表記は原metadataに保持し、今回説明はlayout7 C1 coreへ対象文字列を限定訂正。commit履歴書換え/旧Git再実行0。

同種合成dev結果/ユーザー名PC input path/同 https://github.com/tyaro/banto-ai.git への継続承認範囲で、今回report/handoff/results index3を一回[skip ci] commit/push。原返値、HEAD/upstream/remote/clean、docpinsはGit記録を参照。

## 次工程と正式gate

次は同chunk007/layout7/core C2 c2-phase-conditional、新IDdev-layout7-core-c2-20261012へ1cell実評価。元manifest/input10同一、元生成C0と次実評価C2は別field、次model未実行。

評価900秒/2GiB/output1GiB/single32MiB/files32、Git累積30秒/batch16entry512KiB/stdout1MiB/stderr128KiB、固定protocol/native契約は不変。checkpointはblocking中断/full loaded runtime/native/global容量の証明ではない。ACTIVE/automation設定へ結果・PC path転記0。CI381385/code661の4130success保存、新CIquery/download/verifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読、正式5残件/最終受入未完了、create_native早期拒否/全7役reader禁止/追加agent禁止を維持。Sol容量/人停止では原保全後PAUSED、重複再試行0。
