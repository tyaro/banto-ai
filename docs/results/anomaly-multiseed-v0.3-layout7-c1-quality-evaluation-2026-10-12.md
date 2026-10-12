# v0.3 dev layout7 C1 quality-stress実評価

2026-10-12 JST。保存済みquality-stressを既存CLI C1で1cell fresh評価。CLI exit0/complete・1cell success。機械10/10・sensor9/10・precision19/19・clean誤警報0。未検出1件は原causal_detected false/delay nullを保持し、性能成功・採択・正式受入へ補わない。

## 入力と実行の対応

- run ID dev-layout7-quality-c1-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-07-quality-stress。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\007\attempt-0001\result\payload\manifest.json、pin {"bytes": 75699, "sha256": "0963abc39d429bc6322694bf57f111ce12b0ce5c5a9009e177812cb3989dcaef"}。
- seed2486912926863618161/layout7/quality-stress/dev。元生成candidate C0と実評価C1は別field。
- input10 pins照合→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics。元payload書込み・新dataset生成・replay・追加agent0。
- actual checkout ec2bb1c80d4a68452d36d67afcc208d314ca4de1、計算source661b27511826fcc87cb4a02930f276afbb8f95d9から不変。宣言16calculator/candidate config/compiled config一致はfull loaded runtime/native認証ではない。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}。
- elapsed 16.418151800055057秒、OS sampled peak private 150757376 bytes。
- 48 calibrated/fit各600/calibration各290/14400scores、固定C1 threshold6/persistence2、GT/matching/config/science変更0。

## 原指標と欠測

| 指標 | 原値 |
| --- | --- |
| machine recall | 10/10 |
| sensor recall | 9/10 |
| precision | 19/19 |
| clean_rate | 0/3365、原value0.0 |
| effective clean | effective3255秒、原value0.0 |
| false_alert_burden | 0/20、原value0.0 |
| delay | causal-detected-only count19/min1/max2/平均1.4736842105263157/中央値1.0秒 |
| availability | 13880 available / 520 unavailable |

source29/equipment19/events40/incidents20。原sourceはconveyor-01 speed10/vibration10/temperature9、matched equipment19、未対応0/clean0を別に保持。precision19/19とsensor recall9/10は別指標。clean_rateとburdenは原尺度を保ち、単純確率へ変換しない。未検出1件のdelayはnull、遅延への補完0。coreの中央値1.5秒に対してquality中央値1秒という検出19件だけの集計差を、未検出を含む性能改善へ解釈しない。

18000観測行とquality-maskが対応し、conveyor-01.motor_temperature欠測30行を原観測付きで保存。primary reasonsはphase480/current quality30/previous quality10、合計520。非排他的tagsはphase480/current quality30/current nonfinite30/previous quality30であり、重複を足し合わせない。phaseとprimary品質の重複は0、core13920/480からqualityは利用可能40行減・不能40行増。全不能score/residual null・threshold_exceeded false。

## cycle09 sensor未検出の原経路

原eventはconveyor-01.motor_temperature spike/start8850/end8853/window_end8856。元GT/窓を変更しない。8850はmode_recipe_or_phaseで不能、8851–8853はcurrent target quality欠測、8854はprevious quality不能。すべてscore/residual null・thresholdfalse/streak0。8855 score0.18556754796868258/streak0、8856 score0.05361572473258108/streak0。対象source episodeなし、candidate_count0/no_candidate_in_window/causal_detected false/matched null/delay null。

coreの同イベントはphase後の8851/8852で連続超過していたが、今回qualityではそのscoreを補わず原nullを保存。phase開始不能とその後の欠測・previous resetが重なり、固定persistence2が成立しない。未検出を処理失敗に読み替えず、incidentのprocessed状態と検出falseを別に保持。入力対応・保存・状態分類の実経路不具合は観測していない。

## 検出19件と原証拠

機械10件は対象conveyor_speed onsetがevent開始+1000ms、sensor9件は対象温度onsetが+2000ms、全target support2。原selected target source full_target/support、equipment source membership/matched_event_id、incidentを照合。machine窓は7行利用可/phase0、sensor検出9窓は開始phase不能1行・6行利用可。全20原event/incident、matched target-source-equipment19、四target窓、全episodes、欠測30行、不能520行を保存。

## 保存C1の比較

旧7 layouts quality C1と同layout7 core C1の8保存セルをmanifest/configだけ比較し、今回を加えて9比較セル。旧result本文再展開・モデル再compute0。同core/quality input10 file名と固定候補設定は同じで、原pin差を保存。

| layout | 条件 | machine | sensor | precision | clean件数 | available | delay中央値秒 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13880 | 2.0 |
| 1 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13880 | 1.0 |
| 2 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13889 | 1.0 |
| 3 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13880 | 1.0 |
| 4 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13880 | 2.0 |
| 5 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13880 | 1.0 |
| 6 | quality-stress | 0/10 | 9/10 | 9/19 | 0 | 13889 | 1.0 |
| 7 | core | 10/10 | 10/10 | 20/20 | 0 | 13920 | 1.5 |
| 7 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13880 | 1.0 |

quality C1は同seed8 layouts、9比較は8 quality＋同core1であり9独立seedではない。過去layout6品質phase重複9行と今回重複0も別条件で保持。既存45完了boardをmetadata参照で継承し新1を加えて46セル。layout7 quality C2/C0は未実施。bootstrap/統計CI・勝者・採択0。

## 原保存・検証記録

- model records: artifacts/representative-layout7-quality-c1-20261012-records/root-closed.json。
- analysis/extract: artifacts/representative-layout7-quality-c1-20261012-analysis/root-closed.json。
- DATA: artifacts/representative-anomaly-evaluation/dev-layout7-quality-c1-20261012/root-closed.json、{"bytes": 27558717, "files": 19, "manifest_pin": {"bytes": 2228, "sha256": "c0f230c1fb9e372bf3c55bf0431eaa93c01d24950e4b706a57b6016d7198c0a3"}}。
- docs/Git: artifacts/representative-layout7-quality-c1-20261012-save/root-closed.json、git-summary/target-onset-summary/next-dev-selection labels。
- 最終保存: artifacts/representative-layout7-quality-c1-20261012-final/root-closed.json、post-save label。

共通EvidenceStoreでselected-windows 1032838B/4parts、unavailable-scores 518608B/2parts、analysis 324211B/2partsを自動分割保存。新検証root16MiB/512files、part256KiB、失敗reserve2MiB/16files（内閉鎖512KiB/4files）。 [保存方針](../anomaly/execution/verification-records.md) のreaderはrecord_integrityとrecorded_statusを区別。

今回helper/model失敗0、全過去failed16/missing original execution1を保持。full creation/start_token一致とCIM同original不在を照合。CLI redirect rawはhelper全process stdioではない。PID単独/EOF/closedからnative回収を補わない。閉鎖/外部固定root追記・原raw整理移動削除0。

同種合成dev結果・ユーザー名PC内input path・同 https://github.com/tyaro/banto-ai.git への継続承認範囲で、report/handoff/results index3を一回[skip ci] commit/push。原返値とHEAD/upstream/remote/clean/docpinsはGit記録を参照。

## 次工程と正式gate

次は同保存chunk007/layout7 quality-stressをC2 c2-phase-conditional、新IDdev-layout7-quality-c2-20261012へ1cell実評価。同manifest0963/input10 metadata、元生成C0/次実評価C2は別field。quality観測本文は今回C1で読取済み、次model未実行。元payload保持・新dataset生成0。

評価900秒/2GiB/output1GiB/single32MiB/files32、Git累積30秒/batch16entry512KiB/stdout1MiB/stderr128KiB、固定protocol/native契約は不変。checkpointはblocking中断/full loaded runtime/native/global容量の証明ではない。ACTIVE/automation設定へ結果・PC path転記0。CI381385/code661の4130success保存、新CIquery/download/verifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了/create_native早期拒否/全7役reader禁止/追加agent禁止を維持。Sol容量/人停止では原保全後PAUSED、重複再試行0。
