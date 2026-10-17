# Anomaly v0.3 — dev layout3 core C2実評価・3候補core比較（2026-10-12 JST）

## 入力・モデル・原結果

同保存dev seed **2486912926863618161 / layout3 / core** を既存CLI tools/evaluator/run_representative_anomaly.py、C2 c2-phase-conditional、新ID dev-layout3-core-c2-20261012で1cell実compute_evaluation。入力manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\003\attempt-0001\result\payload\manifest.json / {'bytes': 75699, 'sha256': '40be5e90bb27173cf9d21252940f13beb86a17187ea0fb25afa77315c516056d'}。dataset anomaly-v03-dev-seed-2486912926863618161-layout-03-core。元生成identity candidate C0と実評価candidate C2を別fieldで保持した。

input10pins→新snapshot→fresh fit/calibration→原profiles/scores/source・equipment episodes/events/incidents/metrics。元payload書込み・新dataset生成・replay・production/test変更・類似owner試験・追加agent・holdout観測読取り0。actual checkoutdeab5692a12731d396dcfefe520ccdb52d22403b、計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。actual runtime {'executable': 'C:\\Python314\\python.exe', 'machine': 'AMD64', 'python': '3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]', 'system': 'Windows'}。宣言16calculator source/Git pinはfull loaded runtime/native閉包ではない。

CLI exit0 / complete / successful_cells1 / cell success。処理successを性能合格・勝者・採択・正式受入へしない。elapsed 30.430585199967027秒、OS checkpoint private peak 205336576B。engineering900秒/2GiB/output1GiB/single32MiB/files32 checkpointを保持し、blocking計算中断・全writer/global/coupled/native容量証明へしない。個別runtimeを速度順位へしない。

## 原指標・利用不能

- 機械10/10、sensor10/10、precision20/20、clean誤警報0、全未対応equipment0。
- profiles {'calibration_counts': {'290': 48}, 'fit_counts': {'600': 48}, 'statuses': {'calibrated': 48}}。scores14400 / available13920 / unavailable480。不能480は全mode_recipe_or_phase、原score/residual null・threshold_exceeded false。
- 原mask-observation18000行全対応、non-ok0/欠測0。原primary {'mode_recipe_or_phase': 480} / 非排他的tags {'mode_recipe_or_phase': 480}。
- source30 / equipment20 / incidents20 / events40。全20causal_detected、candidate1、原target source・equipment対応、support各2。
- 原delay summary {'conditioned_on': 'causal-detected-only', 'count': 20, 'max': 2.0, 'mean': 1.5, 'median': 1.5, 'min': 1.0, 'undetected_fill': 'forbidden', 'unit': 'seconds'}。検出20件で機械10件1秒・sensor10件2秒。未検出0で、遅延補完は行わない。
- 原clean_rate {'ci_lower': None, 'ci_status': 'not_evaluated', 'ci_upper': None, 'denominator': 3365, 'null_replicates': 0, 'numerator': 0, 'value': 0.0}、原effective_clean_rate 0.0、effective_clean_seconds 3255、原false_alert_burden {'ci_lower': None, 'ci_status': 'not_evaluated', 'ci_upper': None, 'denominator': 20, 'null_replicates': 0, 'numerator': 0, 'value': 0.0}。単位/denominatorを保持し、単純確率に変換しない。
- GT・固定C2threshold6・persistence2・first-equipment-onset-no-retry-v1・science変更0。入力対応・保存・状態分類の実経路不具合観測なし。

## 原source onsetとphase行

全20件でselected source.full_target=event.full_target、source IDがequipment.source_episode_idsに含まれ、equipment.matched_event_id=event ID。対象をequipment ID文字列から補わない。原onset offset分布 {'1000': 10, '2000': 10}、support長 {'2': 20}、causal delay=原target source onset差を照合した。

cycle00 machine current7311score73.32411446782102/streak1→7312score73.32293454482667/streak2、対象onset7312/start+1000ms。cycle00 sensor temperature7290はphase primary不能/null/thresholdfalse/streak0、7291score124.57670674984136/streak1→7292score124.95564277092221/streak2、対象onset7292/start+2000ms。C1との集計・source/equipment件数一致から原profile/score/residual/episodeの同一性を推定しない。C1・C2双方の原resultは別candidateの原bytes/pinsで保持。

保存したsensor窓cycle00/01/09の3件で開始行phase不能→次available行streak1→次行streak2/原source onsetを照合。入力non-ok0はphase不能0を意味しない。全10sensorのdelay2秒は原matching値として保存し、全10開始score行を今回EXTRACT窓で読んだとのclaimはしない。

### cycle00 machine原target窓

| sample | available | 原score | streak | primary exclusion | 原source ID |
| ---: | --- | ---: | ---: | --- | --- |
| 7311 | True | 73.32411446782102 | 1 | None | None |
| 7312 | True | 73.32293454482667 | 2 | None | anomaly-v03-dev-seed-2486912926863618161-layout-03-core-c2-phase-conditional-score-motor-01-motor_current-7312-source |
| 7313 | True | 73.08045935859363 | 3 | None | anomaly-v03-dev-seed-2486912926863618161-layout-03-core-c2-phase-conditional-score-motor-01-motor_current-7312-source |
| 7314 | True | 0.30076520871409784 | 0 | None | None |
| 7315 | True | 0.855047600539907 | 0 | None | None |
| 7316 | True | 0.794478212584882 | 0 | None | None |
| 7317 | True | 0.27086619004077167 | 0 | None | None |

### cycle00 sensor原target窓

| sample | available | 原score | streak | primary exclusion | 原source ID |
| ---: | --- | ---: | ---: | --- | --- |
| 7290 | False | None | 0 | mode_recipe_or_phase | None |
| 7291 | True | 124.57670674984136 | 1 | None | None |
| 7292 | True | 124.95564277092221 | 2 | None | anomaly-v03-dev-seed-2486912926863618161-layout-03-core-c2-phase-conditional-score-motor-01-motor_temperature-7292-source |
| 7293 | True | 0.6615518594830726 | 0 | None | None |
| 7294 | True | 0.5877252138717503 | 0 | None | None |
| 7295 | True | 0.3783934184971549 | 0 | None | None |
| 7296 | True | 0.011100605395849604 | 0 | None | None |

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

全20event-incident / 20matched target-source-equipment / 5selectedmotor4target窓 / 全source-equipmentを新EXTRACTへ保存。原EXTRACT parts [{'kind': 'incident-ledger', 'path': 'D:\\develop\\banto-ai\\artifacts\\representative-layout3-core-c2-extract-20261012-prep\\incident-ledger-001.json', 'pin': {'bytes': 33774, 'sha256': '293fc9b709494a05e28ea2306922363e304433c4e6b538e991d68d519e80db46'}, 'records': 20}, {'kind': 'matched-target-pairs', 'path': 'D:\\develop\\banto-ai\\artifacts\\representative-layout3-core-c2-extract-20261012-prep\\matched-target-pairs-001.json', 'pin': {'bytes': 65254, 'sha256': 'ca2e94298f928d0b0e7cdf3b6687ef224a38ada440166ad77aa51d375ea8e404'}, 'records': 20}, {'kind': 'selected-windows', 'path': 'D:\\develop\\banto-ai\\artifacts\\representative-layout3-core-c2-extract-20261012-prep\\selected-windows-001.json', 'pin': {'bytes': 62222, 'sha256': 'eb6ddbd47c3ae82ec033d1bac8b270436c880bb86080a5014599cb505be96de4'}, 'records': 4}, {'kind': 'selected-windows', 'path': 'D:\\develop\\banto-ai\\artifacts\\representative-layout3-core-c2-extract-20261012-prep\\selected-windows-002.json', 'pin': {'bytes': 15090, 'sha256': 'bfcc22126707e7dabf22e0d4362d762583e862c41c790aed95df799827949fa8'}, 'records': 1}, {'kind': 'all-source-equipment-episodes', 'path': 'D:\\develop\\banto-ai\\artifacts\\representative-layout3-core-c2-extract-20261012-prep\\all-source-equipment-episodes-001.json', 'pin': {'bytes': 39984, 'sha256': '236eb697e22786d5fd4fbaa9aa916b8f3ca93c84c15487d9ab1c5d54edc99121'}, 'records': 50}]。表は選択fieldであり、full bodyはevaluation/EXTRACTを優先する。

## 同core3候補と旧C2 core保存比較

| layout | candidate | machine | sensor | precision | clean | available | delay count / median | manifest pin |
| ---: | --- | --- | --- | --- | ---: | ---: | --- | --- |
| 0 | c2-phase-conditional | 4/10 | 10/10 | 14/20 | 0 | 13920 | 14 / 1.0 | {'bytes': 8015, 'sha256': 'd70767ce2d8f174804565838011b709b0adced933787124cd5e02ee4285a96c9'} |
| 1 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 / 1.0 | {'bytes': 8008, 'sha256': '8005819bdc77823a6caddfb96dc33c49a6487186eaa69d4b48f5b37f020dde97'} |
| 2 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 / 1.0 | {'bytes': 8009, 'sha256': 'c1cf4496d07b9b8b53f4f98ac8b12d2dd548b06beaecabad49e13f069f835d16'} |
| 3 | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13920 | 0 / None | {'bytes': 8032, 'sha256': '6f132b35a0df2d2a838f5aaa2d2bd7bebeb03fec4df51ba7d6b5362b6c671d9f'} |
| 3 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 / 1.5 | {'bytes': 8003, 'sha256': '28789ebe65503df67d229dde0a37df6c9bec0f27f9b8f7d3149a923eb6ec130e'} |
| 3 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 / 1.5 | {'bytes': 8009, 'sha256': 'bbde7501279dc71ea668bfc6e8257ad89c0d8d68bdc3123cdd217a45a180d852'} |

layout3 core C0/C1/C2比較完成。input10pin全一致、全6比較cellの宣言16calculator sources/candidate・compiled config一致。旧layout0/1/2 C2と同core C0/C1は保存manifest/config指標だけ読取り、旧result本文再展開・旧5cell再compute0。C0原machine/sensor0/10・precision0/3・clean3・全20miss/null delay、旧layout0 C2機械4/10・sensor10/10・precision14/20の原値を保持。C1/C2の現在集計一致やconfig一致を原予測の同一へしない。

同seed4layout/coreのC2評価4条件＋同core C0/C1比較で保存6cell。6独立seed/dataset、候補採択ではない。旧18cell完成比較とlayout3 C0/C1保存を維持。bootstrap/CI推定・勝者・採択0。

## 閉鎖保存・provenance・送信

原pins {'observations': {'bytes': 9600569, 'sha256': '4e23ec5d61336d1f2ce9cb116743af9f42944e8aba528f7aaddee939dd0e69d1'}, 'configuration': {'bytes': 5508, 'sha256': '456f28b5b2db50ba3ea3cfc8baffc7f7de5424b612326cef4193df9295c34564'}, 'manifest': {'bytes': 8009, 'sha256': 'bbde7501279dc71ea668bfc6e8257ad89c0d8d68bdc3123cdd217a45a180d852'}, 'evaluation': {'bytes': 24737853, 'sha256': 'f3dce186d97e25b2243cff49bc236fefc8dbe274b75b3b1f29c6244efa1f3812'}, 'numerical': {'bytes': 24732355, 'sha256': '004811cb96f5095b17c735234b7904506ae33eb26c69dc04c05989d0c5b1c9f2'}}。DATA閉鎖 {'files': 19, 'bytes': 37778296, 'manifest_pin': {'bytes': 2254, 'sha256': '20ce49627d557b7cb9f9660dc4eccba3d4e6982d29534471380f7ae4ee79922b'}}、EXTRACT閉鎖 {'bytes': 217280, 'files': 6, 'manifest_pin': {'bytes': 956, 'sha256': 'ffba75a788b4b6a5e97ded8b2590013c654e9b51bfba1b3f11164634f860546b'}}。MAIN representative-layout3-core-c2-20261012-prep / POST representative-layout3-core-c2-post-20261012-prepの最終post-save/owners/root-closedをGitと最終保存状態として優先する。117science-source、旧81root count-byte-closurepin、外部固定C1 MAIN35file226520B/capacityfalse、旧C2 cache補足を保持。

元129helpers原11failed118passed、full saved creation-start_token/live-execution一致、CIM同original不在/repo helpercriticalなし。今回model/analysis2passed/newfailed0、新foreground失敗0。前layout3 C0 tool SyntaxError・POSTprepare guard import失敗・closure全窓phase不能0誤期待を元script/selected traceへ保持、別continuationは未保存metadataだけ完成。元helper・モデル・Git再実行0、原failed書換え0。前layout2 C0 commitTimeout原failed/原commit返値None/6calls exit0→別read-only既存commit確認→別未実施push-only一回完成、前C2core lsremote128/Connection resetと別metadata continuationも保持。これらを今回model/CI/native/Sol容量failureへ読み替えない。

閉鎖root追記/原raw整理/receipt移動/上限緩和0。metadata512KiB32entry/reserve128KiB/single128KiBで新script・失敗証拠・closure分も書込み前に確認する。Python-B/recursive coverage、対象文字列限定、hash/seed無限定置換0。CIM decimal100ns→microsecond truncation/full saved token、PID単独/native回収claim0。foreground docs/closure full process creation/stdio None、selected CLIをhelper全stdioへしない。

同GitHubへの同種合成dev報告とユーザー名PC内path送信は、具体的リスク通知後の人の継続明示承認範囲。report/handoff2文書を一回skip ci commit/push、Git/API原返値・HEAD/upstream/remote ref/clean・full doc pinsはPOSTへ保存する。累積Git30秒を最初のGitcallから測り各callでresetしない。preflight/source-doc scanは別量で保持し、全経路blocking wallを証明しない。承認の反復質問・automation詳細転記/更新0、ACTIVE維持。

## 次unit・正式gate

次は同保存manifest/dev seed/layout3のquality-stressをC1 c1-phase-level、新ID dev-layout3-quality-c1-20261012で1cell実評価する。次dataset anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress、元生成identity C0と実評価C1別field。quality metadata input10pinsとmanifest40beを保持。次観測本文は未読・model未開始・元payload書込み/生成/replay0。同seed別stratumで新独立seedではない。完成core3候補、旧18cell/明示replay/旧risk-owner/native/probe/collector/Git37/CIを反復しない。

formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読/正式5残件・最終受入未完了。create_native早期拒否/全7役whole.run reader実起動禁止/元caps-unknown原owner-stop/追加agent禁止を維持。CI381385/4130保存はモデル性能・native・正式受入ではない。新CIquery-download-verifier0、旧381365最後in_progressの履歴を保持、doc-onlyCI追跡0。未完了formal/native全証明を少量dev開始条件へ戻さない。Sol容量/人の停止では原証拠保全後PAUSED・重複再試行0。
