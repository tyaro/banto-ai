# Anomaly v0.3 — dev layout3 core C0実評価（2026-10-12 JST）

## 実行・入力対応

保存済み合成dev seed **2486912926863618161 / layout3 / core** を既存CLI tools/evaluator/run_representative_anomaly.pyのC0 c0-diff-controlで1cell実compute_evaluation。新ID dev-layout3-core-c0-20261012。元payload生成identityと実評価candidateは別field。input10pinsを検証し、新snapshotからfresh calibration、profiles/scores/source・equipment episodes/events/incidents/metricsを保存した。元payload書込み・新dataset生成・replay・production/test変更・類似owner試験・追加agent・holdout観測読取りは0。

入力manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\003\attempt-0001\result\payload\manifest.json、pin {'bytes': 75699, 'sha256': '40be5e90bb27173cf9d21252940f13beb86a17187ea0fb25afa77315c516056d'}。dataset anomaly-v03-dev-seed-2486912926863618161-layout-03-core。宣言16calculator sourceと固定candidate/compiled configを旧C0 core保存3layoutと照合。文書checkout151a1dbe670b54985efba0fbbcdfdfeee19bf12d、計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。actual runtime {'executable': 'C:\\Python314\\python.exe', 'machine': 'AMD64', 'python': '3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]', 'system': 'Windows'}。宣言source pinはfull loaded runtime/native閉包ではない。

CLI exit0 / complete / successful_cells1 / cell success。処理successを性能合格・採択・正式受入へ読み替えない。elapsed 37.086205600062385秒、OS checkpoint peak private 145674240B。900秒/2GiB/output1GiB/single32MiB/files32 checkpointを維持。blocking計算中断・全writer/global/coupled/native容量の証明ではない。個別runtimeを速度順位や再現性証明へしない。

## 原指標・状態

- 機械0/10、sensor0/10、precision0/3。
- clean誤警報3、全未対応equipment3。今回は全3equipmentが原clean context。
- 原clean_rate {'ci_lower': None, 'ci_status': 'not_evaluated', 'ci_upper': None, 'denominator': 3365, 'null_replicates': 0, 'numerator': 3, 'value': 25.676077265973255}、原effective_clean_rate 26.543778801843317、原effective_clean_seconds 3255、原false_alert_burden {'ci_lower': None, 'ci_status': 'not_evaluated', 'ci_upper': None, 'denominator': 20, 'null_replicates': 0, 'numerator': 3, 'value': 15.0}。valueの単位・denominatorを保持し単純確率に変換しない。
- profiles {'calibration_counts': {'290': 48}, 'fit_counts': {'0': 48}, 'statuses': {'calibrated': 48}}。scores14400、available13920、unavailable480。原不能は全mode_recipe_or_phase、score/residual null・threshold_exceeded false。排他的primary {'mode_recipe_or_phase': 480}、非排他的tags {'mode_recipe_or_phase': 480}。
- 原observation/mask18000行全対応、non-ok0、欠測0。source3 / equipment3 / incidents20 / events40。
- 全20件no_candidate_in_window、candidate0、causal_detected false、matched/source/equipment null、support[]、delay null。原delay summary {'conditioned_on': 'causal-detected-only', 'count': 0, 'max': None, 'mean': None, 'median': None, 'min': None, 'undetected_fill': 'forbidden', 'unit': 'seconds'}。未検出への遅延補完0。
- GT・C0固定threshold4・persistence2・first-equipment-onset-no-retry-v1・science変更0。入力対応・保存・状態分類の実経路不具合は観測なし。

## 原target score窓

全20event/incident・全20motor4target窓・source/equipment全6recordを新EXTRACTへ保存。対象event窓の原streak最大値分布 {1: 20}。元scoreとsource episodeの成立を保持し、単発の大scoreをpersistence2成立へしない。対象窓不能行は全表の原値を使い、phase等の不能480を全missの原因へ補わない。

### cycle00 machine — motor-01.motor_current

| sample | available | 原score | streak | primary exclusion |
| ---: | --- | ---: | ---: | --- |
| 7309 | True | 0.18665908520214963 | 0 | None |
| 7310 | True | 0.5170908596128391 | 0 | None |
| 7311 | True | 48.42504917051087 | 1 | None |
| 7312 | True | 0.0015640615907367452 | 0 | None |
| 7313 | True | 0.13718807632375696 | 0 | None |
| 7314 | True | 48.685849959848674 | 1 | None |
| 7315 | True | 0.779965542772622 | 0 | None |
| 7316 | True | 0.3979110946432455 | 0 | None |
| 7317 | True | 0.571737961821917 | 0 | None |
| 7318 | True | 1.6477604889059734 | 0 | None |
| 7319 | True | 1.831386504393488 | 0 | None |
| 7320 | False | None | 0 | mode_recipe_or_phase |

### cycle00 sensor — motor-01.motor_temperature

| sample | available | 原score | streak | primary exclusion |
| ---: | --- | ---: | ---: | --- |
| 7288 | True | 0.7817505746349682 | 0 | None |
| 7289 | True | 1.061538647861873 | 0 | None |
| 7290 | False | None | 0 | mode_recipe_or_phase |
| 7291 | True | 3.482533841266633 | 0 | None |
| 7292 | True | 2.668957065219842 | 0 | None |
| 7293 | True | 132.9885637227601 | 1 | None |
| 7294 | True | 3.1991991525663153 | 0 | None |
| 7295 | True | 1.5132694462180047 | 0 | None |
| 7296 | True | 0.9342708321838027 | 0 | None |
| 7297 | True | 1.183267068441485 | 0 | None |
| 7298 | True | 1.9017422946966407 | 0 | None |
| 7299 | True | 0.44745279176902225 | 0 | None |

### 全20incidentの対象窓

| cycle | class | target | start–window end | 原max streak | 対象窓不能行 |
| ---: | --- | --- | --- | ---: | ---: |
| 0 | sensor | motor-01.motor_temperature | 7290–7296 | 1 | 1 |
| 0 | machine | motor-01.motor_current | 7311–7317 | 1 | 0 |
| 1 | sensor | motor-01.motor_temperature | 7470–7476 | 1 | 1 |
| 1 | machine | motor-01.motor_current | 7491–7497 | 1 | 0 |
| 2 | sensor | motor-01.motor_temperature | 7650–7656 | 1 | 1 |
| 2 | machine | motor-01.motor_current | 7671–7677 | 1 | 0 |
| 3 | sensor | motor-01.motor_temperature | 7830–7836 | 1 | 1 |
| 3 | machine | motor-01.motor_current | 7851–7857 | 1 | 0 |
| 4 | sensor | motor-01.motor_temperature | 8010–8016 | 1 | 1 |
| 4 | machine | motor-01.motor_current | 8031–8037 | 1 | 0 |
| 5 | sensor | motor-01.motor_temperature | 8190–8196 | 1 | 1 |
| 5 | machine | motor-01.motor_current | 8211–8217 | 1 | 0 |
| 6 | sensor | motor-01.motor_temperature | 8370–8376 | 1 | 1 |
| 6 | machine | motor-01.motor_current | 8391–8397 | 1 | 0 |
| 7 | sensor | motor-01.motor_temperature | 8550–8556 | 1 | 1 |
| 7 | machine | motor-01.motor_current | 8571–8577 | 1 | 0 |
| 8 | sensor | motor-01.motor_temperature | 8730–8736 | 1 | 1 |
| 8 | machine | motor-01.motor_current | 8751–8757 | 1 | 0 |
| 9 | sensor | motor-01.motor_temperature | 8910–8916 | 1 | 1 |
| 9 | machine | motor-01.motor_current | 8931–8937 | 1 | 0 |

### 原episode全6recordの選択field

| kind | episode_id | onset_ms | end_ms | 原context_tags | matched_event_id |
| --- | --- | ---: | ---: | --- | --- |
| source | anomaly-v03-dev-seed-2486912926863618161-layout-03-core-c0-diff-control-score-conveyor-01-motor_temperature-7712-source | 1767233312000 | 1767233313000 | field absent | field absent |
| source | anomaly-v03-dev-seed-2486912926863618161-layout-03-core-c0-diff-control-score-motor-01-vibration_feature-7242-source | 1767232842000 | 1767232843000 | field absent | field absent |
| source | anomaly-v03-dev-seed-2486912926863618161-layout-03-core-c0-diff-control-score-motor-01-vibration_feature-8517-source | 1767234117000 | 1767234118000 | field absent | field absent |
| equipment | anomaly-v03-dev-seed-2486912926863618161-layout-03-core-c0-diff-control-score-motor-01-vibration_feature-7242-source-equipment | 1767232842000 | 1767232843000 | ['clean'] | None |
| equipment | anomaly-v03-dev-seed-2486912926863618161-layout-03-core-c0-diff-control-score-conveyor-01-motor_temperature-7712-source-equipment | 1767233312000 | 1767233313000 | ['clean'] | None |
| equipment | anomaly-v03-dev-seed-2486912926863618161-layout-03-core-c0-diff-control-score-motor-01-vibration_feature-8517-source-equipment | 1767234117000 | 1767234118000 | ['clean'] | None |

sourceにないcontext/matching fieldはfield absentと明示し、原field不存在をnullへ補わない。equipmentのmatched_event_id原null・context_tagsは別に保持。全bodyとpinはEXTRACT/evaluationを優先し、この表は選択field表示。

## 同seed C0 coreの4layout保存比較

| layout | machine | sensor | precision | clean | 全未対応equipment | available scores | 原manifest pin |
| ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 0 | 0/10 | 0/10 | 0/3 | 3 | 3 | 13920 | {'bytes': 11019, 'sha256': '0898a0ee0eb0a5a15af8e52d320832abe06220e30cb8cad0d02f7f774a01e094'} |
| 1 | 0/10 | 0/10 | 0/3 | 2 | 3 | 13920 | {'bytes': 8030, 'sha256': '2617eca766b9a10e840ac5a7d5e9798cc1466e28989bbfdefae45484d4aa2236'} |
| 2 | 0/10 | 0/10 | 0/3 | 3 | 3 | 13920 | {'bytes': 8028, 'sha256': 'dfaff1ed6a29deb373db3b0598001fe0807abefdfca2e6acaf08b72baaa6ad9b'} |
| 3 | 0/10 | 0/10 | 0/3 | 3 | 3 | 13920 | {'bytes': 8032, 'sha256': '6f132b35a0df2d2a838f5aaa2d2bd7bebeb03fec4df51ba7d6b5362b6c671d9f'} |

旧layout0/1/2は保存manifest・configurationの指標だけ読取り、旧result本文再展開・旧モデル再compute0。全4宣言16calculator source・candidate/compiled config一致、input10ファイル名同じ・各layout原pin差を保存。layout1 clean2と全未対応3は異なる原指標であり、全未対応をcleanへ補わない。同seed4layout/core/C0で4独立seedではない。完成した前18cell比較を保持し、今回をその18cell再実行や新独立seedへ補わない。bootstrap/CI推定・勝者・採択0。

比較metadata D:\develop\banto-ai\artifacts\representative-layout3-core-c0-20261012-prep\saved-four-core-c0-comparison.json / {'bytes': 14914, 'sha256': '48b3495d718c31b6d12a249bdf0eb19027204d483f4731aff3d901e0d81fb7a6'}。原extract parts [{'kind': 'incident-ledger', 'path': 'D:\\develop\\banto-ai\\artifacts\\representative-layout3-core-c0-extract-20261012-prep\\incident-ledger-001.json', 'pin': {'bytes': 19329, 'sha256': '062912425d4db7366786c4886d9dc4770e1d539b583fc8632cb60612d23cb727'}, 'records': 20}, {'kind': 'selected-windows', 'path': 'D:\\develop\\banto-ai\\artifacts\\representative-layout3-core-c0-extract-20261012-prep\\selected-windows-001.json', 'pin': {'bytes': 63292, 'sha256': '3e31cb8e49412823e72d329697f6915c9196986d52d9689c1453d1015b2ef55e'}, 'records': 5}, {'kind': 'selected-windows', 'path': 'D:\\develop\\banto-ai\\artifacts\\representative-layout3-core-c0-extract-20261012-prep\\selected-windows-002.json', 'pin': {'bytes': 63252, 'sha256': 'a2c4b5eb6944fb0e4686c431fa14ee7685a69cd1f5192484fb67eab394e5d58b'}, 'records': 5}, {'kind': 'selected-windows', 'path': 'D:\\develop\\banto-ai\\artifacts\\representative-layout3-core-c0-extract-20261012-prep\\selected-windows-003.json', 'pin': {'bytes': 63267, 'sha256': '6c487196a2b3d6e535552e3068335ddd1a14fd5d85dcbb608187a637b7d53de9'}, 'records': 5}, {'kind': 'selected-windows', 'path': 'D:\\develop\\banto-ai\\artifacts\\representative-layout3-core-c0-extract-20261012-prep\\selected-windows-004.json', 'pin': {'bytes': 63227, 'sha256': '8d22dc9bdf9f4160248f807c24acfeacdae41c08a7416eaa061d37f322ae546b'}, 'records': 5}, {'kind': 'all-source-equipment-episodes', 'path': 'D:\\develop\\banto-ai\\artifacts\\representative-layout3-core-c0-extract-20261012-prep\\all-source-equipment-episodes-001.json', 'pin': {'bytes': 4476, 'sha256': 'd7b3ccd9fb2bcded3a81e68ed94a89bf975e9b1e68f3b82939fc99bbaafa979c'}, 'records': 6}]。

## 保存・provenance・既存失敗

原pins {'observations': {'bytes': 9600569, 'sha256': '4e23ec5d61336d1f2ce9cb116743af9f42944e8aba528f7aaddee939dd0e69d1'}, 'configuration': {'bytes': 5503, 'sha256': '14aa9e9cd499dd721736863eec5b3e0b3f9702d88023f6a5936844503c8b468e'}, 'manifest': {'bytes': 8032, 'sha256': '6f132b35a0df2d2a838f5aaa2d2bd7bebeb03fec4df51ba7d6b5362b6c671d9f'}, 'evaluation': {'bytes': 13898997, 'sha256': '4dd060dd7e465eab075e2ae395f2c6508ea73c475a9ec99e42bcbb8f2548a102'}, 'numerical': {'bytes': 13893499, 'sha256': '57a4fec096067475919cf90133d4f2b69c225611a5c23e6cdaa5bd6af9138068'}}。DATA閉鎖 {'files': 19, 'bytes': 26939466, 'manifest_pin': {'bytes': 2249, 'sha256': '18119b25d23a8de6bc1983e5ee93d08778ca2a3655b7cd2fa48c18c934aa72d9'}}、EXTRACT閉鎖 {'bytes': 277909, 'files': 7, 'manifest_pin': {'bytes': 1066, 'sha256': '17a8319b9249c07d1260a7a0524561e943d0ed8e95730013bab6a44ebde999bf'}}。MAIN representative-layout3-core-c0-20261012-prep とPOST representative-layout3-core-c0-post-20261012-prepの最終post-save / owners / root-closedをGit・閉鎖状態として優先する。117science-source、旧73root count/bytes/closurepin、外部固定C1 MAIN35file226520B/capacityfalse、旧C2 cache補足pinを保持。閉鎖root追記・原helper再実行・原raw整理・receipt移動・上限緩和0。metadata512KiB32entry/reserve128KiB/single128KiB、新script/失敗証拠/closure分も書込み前に数える。Python-B/recursive coverage、対象文字列限定の変更、hash/seed無限定置換0。

今回model/analysis2helper passed。元123helpers full saved creation-start_token/live-execution一致、原11failed112passed、CIM同original不在/repo helpercriticalなし。PID単独/native回収claim0。foreground docs/closureのfull process creation/stdio None、選択CLI出力をhelper全stdioへしない。

前layout2 C0文書Git helperはcommit待機Timeoutでfailed、原commit終了返値None/原6call exit0/原elapsed145.8506676000543秒を保持。その後の別read-only unitでcommit151a1db完成・clean・Git processなしを観測し、新push-only unitで未実施pushを一回実行、remoteAPI/upstream/cleanを確認済み。元commit/helperを再実行せず、元failedをpassedへ書換えない。別foreground inspect名衝突import failure（instrumented開始/Git0）も保全。今回のモデル・CI・native・Sol容量失敗へ読み替えない。前C2core Git lsremote128/Connection resetと別metadata continuationも保持。

今回文書builderのfunctions.exec SyntaxError Unexpected identifier toolsはisolate評価前/nestedtools0/process0/trackedmutation0としてMAINに保全。inline backtick引用を除いたbuilderを初めて実process実行した。原tool errorをinstrumented helperのfailedへ追加せず、モデル・CI・native・Sol容量failureへしない。

同GitHubへの同種合成dev結果とユーザー名PC内path送信は、具体的リスク通知後の人の継続明示承認内。今回reportとhandoffを一回skip ciで保存し、Git/API original returns・HEAD-upstream-remote ref-clean・full doc pinsは最終POSTへ保存する。承認の反復質問0、automation詳細転記/更新0、ACTIVE維持。

## 次unit・正式gate

次は同manifest/dev seed/layout3/coreをC1 c1-phase-level、新ID dev-layout3-core-c1-20261012で1cell実評価する。input10pin/manifest40beを保持し、元生成candidate C0と実評価candidate C1を別fieldにする。完成C0や旧18cell/明示replay/旧risk-owner/native/probe/collector/Git37/完成CIを反復しない。quality pairはmetadata保存のみ、観測本文未読。

formal gate=s4_acceptance_not_frozen / formal_permission=false / credit0 / holdout観測未読 / 正式5残件・最終受入未完了。create_native早期拒否、全7役whole.run reader実起動禁止、元caps/unknown原owner-stop、追加agent禁止を維持。CI381385/4130保存はモデル性能・native・正式受入ではない。新CIquery/download/verifier0、旧381365最後in_progressを歴史のまま保持、doc-onlyCI追跡0。未完了formal/native全証明を少量dev評価開始条件へ戻さない。Sol容量または人の停止では原証拠保全後PAUSED・重複再試行0。
