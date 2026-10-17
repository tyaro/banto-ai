# Anomaly v0.3 — dev layout3 core C1実評価（2026-10-12 JST）

## 入力・モデル・原結果

同保存dev seed **2486912926863618161 / layout3 / core** を既存CLI tools/evaluator/run_representative_anomaly.py、C1 c1-phase-level、新ID dev-layout3-core-c1-20261012で1cell実compute_evaluation。入力manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\003\attempt-0001\result\payload\manifest.json / {'bytes': 75699, 'sha256': '40be5e90bb27173cf9d21252940f13beb86a17187ea0fb25afa77315c516056d'}。dataset anomaly-v03-dev-seed-2486912926863618161-layout-03-core。元生成identity candidate C0と実評価candidate C1を別fieldで保持した。

input10pins→新snapshot→fresh phase fit/calibration→原profiles/scores/source・equipment episodes/events/incidents/metrics。元payload書込み・新dataset生成・replay・production/test変更・類似owner試験・追加agent・holdout観測読取り0。actual checkout03459b927756bcb269a77140543108e6e6a21882、計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。actual runtime {'executable': 'C:\\Python314\\python.exe', 'machine': 'AMD64', 'python': '3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]', 'system': 'Windows'}。宣言16calculator source/Git pinはfull loaded runtime/native閉包ではない。

CLI exit0 / complete / successful_cells1 / cell success。処理successを性能合格・勝者・採択・正式受入へしない。elapsed 17.948212299961597秒、OS checkpoint private peak 147709952B。engineering900秒/2GiB/output1GiB/single32MiB/files32 checkpointを保持し、blocking計算中断・全writer/global/coupled/native容量証明へしない。個別runtimeを速度順位へしない。

## 原指標・利用不能

- 機械10/10、sensor10/10、precision20/20、clean誤警報0、全未対応equipment0。
- profiles {'calibration_counts': {'290': 48}, 'fit_counts': {'600': 48}, 'statuses': {'calibrated': 48}}。scores14400 / available13920 / unavailable480。不能480は全mode_recipe_or_phase、原score/residual null・threshold_exceeded false。
- 原mask-observation18000行全対応、non-ok0/欠測0。原primary {'mode_recipe_or_phase': 480} / 非排他的tags {'mode_recipe_or_phase': 480}。
- source30 / equipment20 / incidents20 / events40。全20causal_detected、candidate1、原target source・equipment対応、support各2。
- 原delay summary {'conditioned_on': 'causal-detected-only', 'count': 20, 'max': 2.0, 'mean': 1.5, 'median': 1.5, 'min': 1.0, 'undetected_fill': 'forbidden', 'unit': 'seconds'}。検出20件で機械10件1秒・sensor10件2秒。未検出0で、遅延補完は行わない。
- 原clean_rate {'ci_lower': None, 'ci_status': 'not_evaluated', 'ci_upper': None, 'denominator': 3365, 'null_replicates': 0, 'numerator': 0, 'value': 0.0}、原effective_clean_rate 0.0、effective_clean_seconds 3255、原false_alert_burden {'ci_lower': None, 'ci_status': 'not_evaluated', 'ci_upper': None, 'denominator': 20, 'null_replicates': 0, 'numerator': 0, 'value': 0.0}。単位/denominatorを保持し、単純確率に変換しない。
- GT・固定C1threshold6・persistence2・first-equipment-onset-no-retry-v1・science変更0。入力対応・保存・状態分類の実経路不具合観測なし。

## 原source onsetとphase行の対応

全20件でselected source.full_targetがevent.full_targetと一致、source IDがequipment.source_episode_idsに含まれ、equipment.matched_event_idがevent IDと一致する。対象をequipment IDの文字列だけから補わない。原onset offset分布 {'1000': 10, '2000': 10}、原support長分布 {'2': 20}。原matchingのcausal delayとsource onset差も一致。

cycle00 machine current7311score71.37392314660907/streak1→7312score71.40461149369662/streak2、対象onset7312/start+1000ms。cycle00 sensor temperature7290はphase primary不能/null/thresholdfalse/streak0、7291score123.96236827886464/streak1→7292score124.2893627713266/streak2、対象onset7292/start+2000ms。

保存したsensor窓cycle00/01/09の3件で開始行phase不能→次available行streak1→次行streak2/原source onsetを照合。cycle01温度7470phase不能→7471score125.07174338508165/1→7472score125.0683597111154/2。cycle09温度8910phase不能→8911score125.10977838688764/1→8912score125.79237194895235/2。入力non-ok0はphase不能0を意味しない。全10sensorのdelay2秒は原matching値として保存し、全10開始score行を今回EXTRACT窓で読んだとのclaimはしない。

### cycle00 machine原target窓

| sample | available | 原score | streak | primary exclusion | 原source ID |
| ---: | --- | ---: | ---: | --- | --- |
| 7311 | True | 71.37392314660907 | 1 | None | None |
| 7312 | True | 71.40461149369662 | 2 | None | anomaly-v03-dev-seed-2486912926863618161-layout-03-core-c1-phase-level-score-motor-01-motor_current-7312-source |
| 7313 | True | 71.13285088337297 | 3 | None | anomaly-v03-dev-seed-2486912926863618161-layout-03-core-c1-phase-level-score-motor-01-motor_current-7312-source |
| 7314 | True | 0.32723303052667807 | 0 | None | None |
| 7315 | True | 0.868388756794096 | 0 | None | None |
| 7316 | True | 0.8120647586143619 | 0 | None | None |
| 7317 | True | 0.2569999253935632 | 0 | None | None |

### cycle00 sensor原target窓

| sample | available | 原score | streak | primary exclusion | 原source ID |
| ---: | --- | ---: | ---: | --- | --- |
| 7290 | False | None | 0 | mode_recipe_or_phase | None |
| 7291 | True | 123.96236827886464 | 1 | None | None |
| 7292 | True | 124.2893627713266 | 2 | None | anomaly-v03-dev-seed-2486912926863618161-layout-03-core-c1-phase-level-score-motor-01-motor_temperature-7292-source |
| 7293 | True | 0.6657535180196908 | 0 | None | None |
| 7294 | True | 0.55945759349153 | 0 | None | None |
| 7295 | True | 0.3464506177680973 | 0 | None | None |
| 7296 | True | 0.04014196545625425 | 0 | None | None |

### 全20event・target source原対応の選択field

| cycle / class | target | event start sample | 原source onset_ms | 原onset offset_ms | support数 | 原delay秒 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 0 / sensor | motor-01.motor_temperature | 7290 | 1767232892000 | 2000 | 2 | 2.0 |
| 0 / machine | motor-01.motor_current | 7311 | 1767232912000 | 1000 | 2 | 1.0 |
| 1 / sensor | motor-01.motor_temperature | 7470 | 1767233072000 | 2000 | 2 | 2.0 |
| 1 / machine | motor-01.motor_current | 7491 | 1767233092000 | 1000 | 2 | 1.0 |
| 2 / sensor | motor-01.motor_temperature | 7650 | 1767233252000 | 2000 | 2 | 2.0 |
| 2 / machine | motor-01.motor_current | 7671 | 1767233272000 | 1000 | 2 | 1.0 |
| 3 / sensor | motor-01.motor_temperature | 7830 | 1767233432000 | 2000 | 2 | 2.0 |
| 3 / machine | motor-01.motor_current | 7851 | 1767233452000 | 1000 | 2 | 1.0 |
| 4 / sensor | motor-01.motor_temperature | 8010 | 1767233612000 | 2000 | 2 | 2.0 |
| 4 / machine | motor-01.motor_current | 8031 | 1767233632000 | 1000 | 2 | 1.0 |
| 5 / sensor | motor-01.motor_temperature | 8190 | 1767233792000 | 2000 | 2 | 2.0 |
| 5 / machine | motor-01.motor_current | 8211 | 1767233812000 | 1000 | 2 | 1.0 |
| 6 / sensor | motor-01.motor_temperature | 8370 | 1767233972000 | 2000 | 2 | 2.0 |
| 6 / machine | motor-01.motor_current | 8391 | 1767233992000 | 1000 | 2 | 1.0 |
| 7 / sensor | motor-01.motor_temperature | 8550 | 1767234152000 | 2000 | 2 | 2.0 |
| 7 / machine | motor-01.motor_current | 8571 | 1767234172000 | 1000 | 2 | 1.0 |
| 8 / sensor | motor-01.motor_temperature | 8730 | 1767234332000 | 2000 | 2 | 2.0 |
| 8 / machine | motor-01.motor_current | 8751 | 1767234352000 | 1000 | 2 | 1.0 |
| 9 / sensor | motor-01.motor_temperature | 8910 | 1767234512000 | 2000 | 2 | 2.0 |
| 9 / machine | motor-01.motor_current | 8931 | 1767234532000 | 1000 | 2 | 1.0 |

全20event-incident / 全20matched target-source-equipment / 5selected motor4target窓 / 全source-equipmentを新EXTRACTへ保存。原EXTRACT parts [{'kind': 'incident-ledger', 'path': 'D:\\develop\\banto-ai\\artifacts\\representative-layout3-core-c1-extract-20261012-prep\\incident-ledger-001.json', 'pin': {'bytes': 33048, 'sha256': '7946367a4292d16d9186e401da0e039b44044cf578d3b3488f9d83a734833fbc'}, 'records': 20}, {'kind': 'matched-target-pairs', 'path': 'D:\\develop\\banto-ai\\artifacts\\representative-layout3-core-c1-extract-20261012-prep\\matched-target-pairs-001.json', 'pin': {'bytes': 63508, 'sha256': '46daba12e57f75dad000e858f97e0e12a11ea10fa984dac8e5728e3c7639cc36'}, 'records': 20}, {'kind': 'selected-windows', 'path': 'D:\\develop\\banto-ai\\artifacts\\representative-layout3-core-c1-extract-20261012-prep\\selected-windows-001.json', 'pin': {'bytes': 61872, 'sha256': '06fcf211c97a5ccb11dc51e986519633671e645bb2399907f1091daeab816cc3'}, 'records': 4}, {'kind': 'selected-windows', 'path': 'D:\\develop\\banto-ai\\artifacts\\representative-layout3-core-c1-extract-20261012-prep\\selected-windows-002.json', 'pin': {'bytes': 15063, 'sha256': 'f1ecd4f08a80c103305e2246518459851a4f96de88429bce7b602f6d1722e87c'}, 'records': 1}, {'kind': 'all-source-equipment-episodes', 'path': 'D:\\develop\\banto-ai\\artifacts\\representative-layout3-core-c1-extract-20261012-prep\\all-source-equipment-episodes-001.json', 'pin': {'bytes': 38658, 'sha256': '6208ca51d5b2aa91548bea940dba7b180a5f73e057624c5d769a7ea37e41ea74'}, 'records': 50}]。表は選択fieldであり、full original result/bodyはevaluation/EXTRACTを優先する。

## 同core C0と旧C1 core保存比較

| layout | candidate | machine | sensor | precision | clean | available | delay count / median | manifest pin |
| ---: | --- | --- | --- | --- | ---: | ---: | --- | --- |
| 0 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 / 1.5 | {'bytes': 11019, 'sha256': '0898a0ee0eb0a5a15af8e52d320832abe06220e30cb8cad0d02f7f774a01e094'} |
| 1 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 / 1.0 | {'bytes': 8024, 'sha256': 'f1b3ebc59a9a4c0c762a1b1a6ead0bfdb2b8df1fac5d8e4731da9df68c0e2acd'} |
| 2 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 / 1.0 | {'bytes': 8002, 'sha256': '6a8a1537204cb240080e1f808e875975036fc6dba5b4925d2f893f46f189dd42'} |
| 3 | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13920 | 0 / None | {'bytes': 8032, 'sha256': '6f132b35a0df2d2a838f5aaa2d2bd7bebeb03fec4df51ba7d6b5362b6c671d9f'} |
| 3 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 / 1.5 | {'bytes': 8003, 'sha256': '28789ebe65503df67d229dde0a37df6c9bec0f27f9b8f7d3149a923eb6ec130e'} |

同layout3 C0とC1はinput10pin全一致。全5比較cellの宣言16calculator sources/candidate・compiled config一致。旧layout0/1/2 C1と同core C0は保存manifest/config指標だけ読取り、旧result本文再展開・旧4cell再compute0。C0原machine/sensor0/10・precision0/3・clean3・全20miss/null delayを保持。候補のfit/calibration状態・原予測を集計一致やconfig一致から同一へしない。

同seed4layout/coreでC1評価4条件、同core候補C0/C1の比較を含む保存5cell。5独立seed/datasetや候補採択ではない。旧18cell完成比較・今回C0保存を維持。bootstrap/CI推定・勝者・採択0。

## 閉鎖保存・provenance・送信

原pins {'observations': {'bytes': 9600569, 'sha256': '4e23ec5d61336d1f2ce9cb116743af9f42944e8aba528f7aaddee939dd0e69d1'}, 'configuration': {'bytes': 5502, 'sha256': '342c14696ae5d8ddf7c43b3e21f2c9fd8106962eb091a764d03894272ee64882'}, 'manifest': {'bytes': 8003, 'sha256': '28789ebe65503df67d229dde0a37df6c9bec0f27f9b8f7d3149a923eb6ec130e'}, 'evaluation': {'bytes': 14070694, 'sha256': '254f13030f559907a8e92df40e9e9fe8fcbfca8c071c9d67ddfa4486dde3fcbd'}, 'numerical': {'bytes': 14065196, 'sha256': '1d8d90873e47cc2b70748dd55c2c632d7be5768dc6c6858f4f45513de299c8db'}}。DATA閉鎖 {'files': 19, 'bytes': 27111101, 'manifest_pin': {'bytes': 2248, 'sha256': '2977fa2b5afa13110015b8910bc30a1cce2c70acdd29e2ea64d6fe70d825eac6'}}、EXTRACT閉鎖 {'bytes': 213099, 'files': 6, 'manifest_pin': {'bytes': 950, 'sha256': '115026023c19e4e9c9f496825c5c49be833a8d7bfb389fdb08fee2197af27227'}}。MAIN representative-layout3-core-c1-20261012-prep / POST representative-layout3-core-c1-post-20261012-prepの最終post-save/owners/root-closedをGitと最終保存状態として優先する。117science-source、旧77root count-byte-closurepin、外部固定C1 MAIN35file226520B/capacityfalse、旧C2 cache補足を保持。

元126helpers原11failed115passed、full saved creation-start_token/live-execution一致、CIM同original不在/repo helpercriticalなし。今回model/analysis2passed/newfailed0。新foreground失敗0。前layout3 C0のtool SyntaxError（isolate評価前/tools-process-trackedmutation0）、POSTprepare guard import失敗、closureの全窓phase不能0誤期待を原script/selected traceとして保持。別continuationは未保存metadataだけ完成し、元helperやモデル・Gitを再実行していない。元instrumented failedへ補わず、モデル・CI・native・Sol容量failureへ読み替えない。

前layout2 C0 commit待機Timeout原Git helperfailed/commit返値None/6calls exit0を保持。別read-only観測で既存commit/clean/残存Gitなしを確認し、未実施pushだけ別unit一回で完成。前C2core lsremote128/Connection resetと別metadata continuationも保持。原failedを書換えず、旧script・CI・評価・nativeを反復しない。

閉鎖root追記/原raw整理/receipt移動/上限緩和0。metadata512KiB32entry/reserve128KiB/single128KiBで新script・失敗証拠・closure分も書込み前に確認する。Python-B/recursive coverage、対象文字列限定、hash/seed無限定置換0。CIM decimal100ns→microsecond truncation/full saved token、PID単独/native回収claim0。foreground docs/closure full process creation/stdio None、selected CLIをhelper全stdioへしない。

同GitHub送信先への同種合成dev報告とユーザー名PC内path送信は、具体的リスク通知後の人の継続明示承認範囲。report/handoff2文書を一回skip ci commit/push、Git/API原返値・HEAD/upstream/remote ref/clean・full doc pinsはPOSTへ保存する。累積Git30秒を最初のGitcallから測り、各callでresetしない。preflight/source-doc scanは別量で保持し、全経路blocking wallを証明しない。承認の反復質問・automation詳細転記/更新0、ACTIVE維持。

## 次unit・正式gate

次は同manifest/dev seed/layout3/coreをC2 c2-phase-conditional、新ID dev-layout3-core-c2-20261012で1cell実評価する。input10pins/manifest40be不変、生成identity C0と実評価C2別field、元payload書込み/生成/replay0。完成C0/C1や旧18cell/明示replay/旧risk-owner/native/probe/collector/Git37/CIを反復しない。quality pairは保存metadata10pinsのみ・観測本文未読。

formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読/正式5残件・最終受入未完了。create_native早期拒否/全7役whole.run reader実起動禁止/元caps-unknown原owner-stop/追加agent禁止を維持。CI381385/4130保存はモデル性能・native・正式受入ではない。新CIquery-download-verifier0、旧381365最後in_progressの履歴を保持、doc-onlyCI追跡0。未完了formal/native全証明を少量dev開始条件へ戻さない。Sol容量/人の停止では原証拠保全後PAUSED・重複再試行0。
