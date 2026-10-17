# v0.3 dev layout8 C1 quality-stress実評価

2026-10-12 JST。保存済みquality-stressを既存CLI C1で1cell fresh評価。CLI exit0/complete・1cell success。機械10/10・sensor9/10・precision19/19・clean誤警報0。未検出1件のcausal_detected false/delay nullを保持し、処理完了を性能合格・候補採択・正式受入へ読み替えない。

## 入力と実行の対応

- run ID dev-layout8-quality-c1-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-08-quality-stress。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\008\attempt-0001\result\payload\manifest.json、pin {"bytes": 75698, "sha256": "c4dfa23be3bca2f563e587f4f83a33e20f5304f9bd518b791dcb6cc7b74b06b4"}。
- seed2486912926863618161/layout8/quality-stress/dev。元生成C0と実評価C1は別field。
- input10 pinsを照合→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics。同coreとの原pin差を保持。元payload書込み・新dataset生成・replay・追加agent0。
- actual checkout 50f403471eba7febdfa9b29b83e012eb618e6402、計算source661b27511826fcc87cb4a02930f276afbb8f95d9から不変。declared16/candidate config/compiled config一致はfull loaded runtime/native認証ではない。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}。
- elapsed 19.660849999985658秒、OS sampled peak private 149213184 bytes。
- 48 calibrated/fit各600/calibration各290/14400scores。固定C1 threshold6/persistence2、GT/matching/config/science変更0。
- input observations pin {"bytes": 9600604, "sha256": "9f812738c1fd9805d257a10ca30ded867afc56bc4642437914451a34b5a25d61"}、configuration pin {"bytes": 5512, "sha256": "51b9550ce48faa37215bd766acec52344b134d21e58f92674d63b3d888a2080d"}、evaluation pin {"bytes": 14509926, "sha256": "00e38ec1635ce0040c06869236efc5a3553479a5aa564ba8d20251cbe544c894"}。

## 原指標

| 指標 | 原値 |
| --- | --- |
| machine recall | 10/10 |
| sensor recall | 9/10 |
| precision | 19/19 |
| clean_rate | 0/3365、原value0.0 |
| effective clean | effective3255秒、原value0.0 |
| false_alert_burden | 0/20、原value0.0 |
| delay | causal-detected-only count19/min1/max2/平均1.5263157894736843/中央値2.0秒 |
| availability | 13880 available / 520 unavailable |

source29/equipment19/events40/incidents20。19 incidentは原causal_detected trueでtarget sourceとの対応を保持。未対応equipment0とclean0を別指標で保存し、clean_rate/burdenの原尺度を単純確率へ換算しない。未検出1件のdelayはnull、補完0。coreの中央値1.5秒とqualityの2秒は検出件数が異なる条件付き集計として保持。

## 欠測と利用不能行

18000観測行とquality-maskの対応を照合、温度欠測30行を原観測付きで保存。primaryはphase480/current quality30/previous quality10、合計520。非排他的tagsはphase480/current30/current nonfinite30/previous30で重複を合算しない。phase品質重複0。全不能score/residual null・threshold_exceeded false。core13920→quality13880の利用可能減40を原行分類で保持。

## cycle09 sensor未検出

未検出はconveyor-01.motor_temperature、start8887/end8890/window_end8893。元incidentはprocessed/candidate0/no_candidate_in_window/causal_detected false/matched null/delay null。

| sample | score | streak | available | exclusion |
| --- | --- | --- | --- | --- |
| 8887 | 129.08390958971867 | 1 | True | None |
| 8888 | None | 0 | False | current_target_quality |
| 8889 | None | 0 | False | current_target_quality |
| 8890 | None | 0 | False | current_target_quality |
| 8891 | None | 0 | False | previous_target_quality_or_nonfinite |
| 8892 | 1.0707546856152381 | 0 | True | None |
| 8893 | 1.2077548237333684 | 0 | True | None |

8887のscore129.08390958971867/streak1の後、8888–8890はcurrent欠測、8891はprevious欠測でnull/reset。8892/8893は基準内でstreak0、固定persistence2が成立しない。phase不能0の対象窓であり、欠測とphaseを区別する。別候補やcoreのscoreをnull行へ補わず、GT/threshold/persistence/matchingは変更しない。

## 原検出19件の対応

machine10はspeed target onset開始+2000ms、sensor9はtemperature target onset開始+1000ms、原onset時support2。machine窓は開始phase1行不能・6行利用可、検出sensor9窓は7行利用可・phase不能0。原sourceはspeed10/vibration10/temperature9。全20event/incident、matched target-source-equipment19、四target窓、全episodes、欠測30行、不能520行を保存。processed状態と検出結果を区別し、入力対応・保存・状態分類の実経路不具合は観測していない。

## 保存C1 coreと過去C1 qualityの比較

同layout8 core C1と過去8 layouts quality C1の保存9セルをmanifest/configだけ比較。今回を加えて10比較セル、C1 qualityは9 layouts。declared16/candidate config/compiled config一致、各input10 pin差を保持。旧result本文再展開・旧モデル再compute0。

| layout | 条件 | machine | sensor | precision | clean件数 | available |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13880 |
| 1 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13880 |
| 2 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13889 |
| 3 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13880 |
| 4 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13880 |
| 5 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13880 |
| 6 | quality-stress | 0/10 | 9/10 | 9/19 | 0 | 13889 |
| 7 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13880 |
| 8 | core | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 8 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13880 |

旧51boardに今回1セルを加えて52完了セル。1つの合成dev seedのlayout差であり9独立seed/52独立datasetではない。layout8 C0/C2 qualityは未実施。原failed runと明示replayをboardへ混ぜず保持。bootstrap/統計CI・勝者・採択0。

## 原保存と検証記録

- model: artifacts/representative-layout8-quality-c1-20261012-records/root-closed.json。
- analysis/extract: artifacts/representative-layout8-quality-c1-20261012-analysis/root-closed.json。
- DATA: artifacts/representative-anomaly-evaluation/dev-layout8-quality-c1-20261012/root-closed.json、{"bytes": 27557725, "files": 19, "manifest_pin": {"bytes": 2228, "sha256": "e02d57eebd62f068686bd07f11084cd2ac49aa054284cbcebac6587e1037dda5"}}。
- docs/Git: artifacts/representative-layout8-quality-c1-20261012-save/root-closed.json、git-summary/target-onset-summary/next-dev-selection labels。
- 最終保存: artifacts/representative-layout8-quality-c1-20261012-final/root-closed.json、post-save label。

EvidenceStoreでselected-windows 1035427B/4parts、unavailable-scores 518713B/2parts、analysis 362417B/2partsを自動分割。新検証root16MiB/512files、part256KiB、失敗reserve2MiB/16files（内閉鎖512KiB/4files）。 [保存方針](../anomaly/execution/verification-records.md) はrecord_integrityとrecorded_statusを区別。

今回helper/model失敗0、全過去failed16/missing original execution1保持。CLI rawはhelper全process stdioではない。full creation/start_token/CIM照合、PID単独/EOF/closedからnative回収を補わない。閉鎖/外部固定root追記・原raw整理移動削除0。

同種合成dev結果・ユーザー名PC内input pathを同 https://github.com/tyaro/banto-ai.git へ送信する継続承認内でreport/handoff/index3を一回[skip ci] commit/push。原返値・HEAD-upstream-remote-clean/docpinsはGit記録。

## 次工程と正式gate

次は同chunk008/seed2486912926863618161/layout8/quality-stressをC2 c2-phase-conditional、新ID dev-layout8-quality-c2-20261012へ1cell実評価。同manifest/input10、quality本文は今回C1読取済み/次model未実行。元生成C0/次評価C2別field、元payload保持/生成0。

評価900秒/2GiB/output1GiB/single32MiB/files32、Git累積30秒/batch16entry512KiB/stdout1MiB/stderr128KiB、固定protocol/native契約不変。checkpointはblocking中断/full loaded runtime/native/global容量証明ではない。ACTIVE/automation結果・PC path転記0。CI381385/code661の4130success保存、新CIquery/download/verifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了/create_native早期拒否/全7役reader禁止/追加agent禁止。Sol容量/人停止では原保全後PAUSED・重複再試行0。
