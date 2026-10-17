# v0.3 dev layout7 C2 quality-stress実評価

2026-10-12 JST。保存済みquality-stressを既存CLI C2で1cell fresh評価。CLI exit0/complete・1cell success。機械10/10・sensor9/10・precision19/19・clean誤警報0。原未検出1件のcausal_detected false/delay nullを保持し、性能成功・採択・正式受入へ補わない。

## 入力と実行の対応

- run ID dev-layout7-quality-c2-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-07-quality-stress。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\007\attempt-0001\result\payload\manifest.json、pin {"bytes": 75699, "sha256": "0963abc39d429bc6322694bf57f111ce12b0ce5c5a9009e177812cb3989dcaef"}。
- seed2486912926863618161/layout7/quality-stress/dev。元生成C0と実評価C2は別field。
- input10 pinsは同quality C1と一致、同core C2との原pin差を保持。照合→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics。
- 元payload書込み・新dataset生成・replay・追加agent0。
- actual checkout 863e18cbe4fd42b80b046b59a13f7c917cb0aec8、計算source661b27511826fcc87cb4a02930f276afbb8f95d9から不変。宣言16calculator/candidate config/compiled config一致はfull loaded runtime/native認証ではない。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}。
- elapsed 26.553440600051545秒、OS sampled peak private 209035264 bytes。
- 48 calibrated/fit各600/calibration各290/C2state48/14400scores、固定C2 threshold6/persistence2、GT/matching/config/science変更0。

## 原指標

| 指標 | 原値 |
| --- | --- |
| machine recall | 10/10 |
| sensor recall | 9/10 |
| precision | 19/19 |
| clean_rate | 0/3365、原value0.0 |
| effective clean | effective3255秒、原value0.0 |
| false_alert_burden | 0/20、原value0.0 |
| delay | causal-detected-only count19/min1/max2/平均1.4736842105263157/中央値1.0秒 |
| availability | 13760 available / 640 unavailable |

source29/equipment19/events40/incidents20。原sourceはconveyor-01 speed10/vibration10/temperature9、原matched equipment19、未対応0/clean0を別に保持。precision19/19とsensor recall9/10を別指標で保存。clean_rate/burdenの原尺度を単純確率へ換算しない。未検出1件のdelayはnull、遅延補完0。core中央値1.5秒からquality中央値1秒の変化は検出19件だけの条件付き集計であり、未検出を含む性能改善へしない。

## 欠測とpeer波及

18000観測行とquality-maskが対応し、温度欠測30行を原観測付きで保存。primaryはphase480/current quality30/previous quality10/peer quality120、合計640。非排他的tagsはphase480/peer120/current30/current nonfinite30/previous30で、重複を合算しない。phase品質とpeer-phaseの重複は0。全不能score/residual null・threshold_exceeded false。

温度のcurrent30＋previous10に加え、C2 peer依存で同conveyor-01のmotor_current/conveyor_speed/vibration_featureが各40行、計120行利用不能になる。原peer rowsとdependenciesを保持し、C2 core13920→quality13760の利用可能減160、同quality C1の13880→C2の13760の減120を原行分類で照合した。peerの不能を検出失敗件数や独立欠測120観測へしない。

## cycle09 sensor未検出と19件の原対応

未検出はconveyor-01.motor_temperature spike/start8850/end8853/window_end8856。8850 phase不能→8851–8853 current欠測→8854 previous quality不能、全score/residual null・thresholdfalse/streak0。8855 score0.18755221484867296/streak0、8856 score0.039472621709745276/streak0。対象source episodeなし/candidate_count0/no_candidate_in_window/causal_detected false/matched null/delay null。coreやC1のscoreで補わない。processed状態と検出falseを区別し、固定persistence2/GT/matchingは変更しない。

検出19件はmachine10対象speed onset+1000ms、sensor9対象温度onset+2000ms、全target support2。原selected source full_target/support、equipment source membership/matched_event_id、incidentを照合。機械窓は7行利用可/phase0、sensor検出9窓は開始phase1行不能・6行利用可。温度を欠測にしたcycle09のpeer3targetsは8851–8854が不能であるが、機械対象窓8871–8877は利用可能で原検出を保持する。全20event/incident、matched target-source-equipment19、四target窓、全episodes、欠測30行、不能640行とpeer120行を保存。入力対応・保存・状態分類の実経路不具合は観測していない。

## 保存候補の比較

同quality C1、同core C2、過去7 layouts quality C2の9保存セルはmanifest/configだけを比較。今回を加えて10比較セル。旧result本文再展開・モデル再compute0。入力file名、declared16/candidate config/compiled config一致、同quality input10 pins一致、別layout/stratum pin差を保存。

| layout | 条件 | 候補 | machine | sensor | precision | clean件数 | available |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | quality-stress | C2 | 4/10 | 9/10 | 13/19 | 0 | 13760 |
| 1 | quality-stress | C2 | 10/10 | 9/10 | 19/19 | 0 | 13760 |
| 2 | quality-stress | C2 | 10/10 | 9/10 | 19/19 | 0 | 13796 |
| 3 | quality-stress | C2 | 10/10 | 9/10 | 19/19 | 0 | 13760 |
| 4 | quality-stress | C2 | 10/10 | 9/10 | 19/19 | 0 | 13760 |
| 5 | quality-stress | C2 | 10/10 | 9/10 | 19/19 | 0 | 13760 |
| 6 | quality-stress | C2 | 0/10 | 9/10 | 9/19 | 0 | 13796 |
| 7 | core | C2 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 7 | quality-stress | C1 | 10/10 | 9/10 | 19/19 | 0 | 13880 |
| 7 | quality-stress | C2 | 10/10 | 9/10 | 19/19 | 0 | 13760 |

同quality C1/C2はこの条件の検出/precision/clean/delay集計が一致し、availabilityとscore/原結果bytesは別。旧layout6 peer-phase重複27/primarypeer93と今回重複0/primarypeer120を原条件で保持。C2 quality8layoutsは同じseedであり独立seedではない。既存46完了boardをmetadataで継承し新1を加えて47セル。layout7 quality C0は未実施。bootstrap/統計CI・勝者・採択0。

## 原保存と検証記録

- model records: artifacts/representative-layout7-quality-c2-20261012-records/root-closed.json。
- analysis/extract: artifacts/representative-layout7-quality-c2-20261012-analysis/root-closed.json。
- DATA: artifacts/representative-anomaly-evaluation/dev-layout7-quality-c2-20261012/root-closed.json、{"bytes": 38228854, "files": 19, "manifest_pin": {"bytes": 2228, "sha256": "2954c5e73d0f890d605ae3e01a56dabd9bc325855d37e8cffb78100fa2c7f354"}}。
- docs/Git: artifacts/representative-layout7-quality-c2-20261012-save/root-closed.json、git-summary/target-onset-summary/peer-summary/next-dev-selection labels。
- 最終保存: artifacts/representative-layout7-quality-c2-20261012-final/root-closed.json、post-save label。

共通EvidenceStoreでselected-windows 1752983B/7parts、unavailable-scores 1113246B/5parts、analysis 334850B/2partsを自動分割保存。原peer120行はpeer-unavailable-scores label。新検証root16MiB/512files、part256KiB、失敗reserve2MiB/16files（内閉鎖512KiB/4files）。 [保存方針](../anomaly/execution/verification-records.md) はrecord_integrityとrecorded_statusを区別。

今回helper/model失敗0、全過去failed16/missing original execution1を保持。full creation/start_token一致/CIM同original不在を照合。CLI redirect rawはhelper全process stdioではない。PID単独/EOF/closedからnative回収を補わない。閉鎖/外部固定root追記・原raw整理移動削除0。

同種合成dev結果・ユーザー名PC内input path・同 https://github.com/tyaro/banto-ai.git への継続承認範囲で、report/handoff/results index3を一回[skip ci] commit/push。原返値/HEAD-upstream-remote-clean/docpinsはGit記録を参照。

## 次工程と正式gate

次は同保存chunk007/layout7 qualityをC0 c0-diff-control、新IDdev-layout7-quality-c0-20261012へ1cell評価。同manifest0963/input10、生成C0/次実評価C0は別field。観測本文はC1/C2で読取済み、次model未実行。元payload保持・新dataset生成0。

評価900秒/2GiB/output1GiB/single32MiB/files32、Git累積30秒/batch16entry512KiB/stdout1MiB/stderr128KiB、固定protocol/native契約は不変。checkpointはblocking中断/full loaded runtime/native/global容量の証明ではない。ACTIVE/automation設定へ結果・PC path転記0。CI381385/code661の4130success保存、新CIquery/download/verifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了/create_native早期拒否/全7役reader禁止/追加agent禁止を維持。Sol容量/人停止では原保全後PAUSED、重複再試行0。
