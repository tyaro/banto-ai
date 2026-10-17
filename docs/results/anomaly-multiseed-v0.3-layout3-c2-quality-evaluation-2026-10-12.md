# dev layout3 C2 quality-stress実評価（2026-10-12 JST）

## 原入力・設定・実結果

保存済み合成dev seed2486912926863618161/layout3/quality-stressを既存CLI C2 c2-phase-conditional、新ID dev-layout3-quality-c2-20261012で1cell実compute_evaluation。input10pins→新snapshot→fresh conditional fit/calibration→原profiles/scores/source-equipment episodes/events/incidents/metrics保存。元payload書込み・生成・replay・production/test変更・類似owner・追加agent・holdout本文読取り0。

input manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\003\attempt-0001\result\payload\manifest.json

manifest 75699B/40be5e90bb27173cf9d21252940f13beb86a17187ea0fb25afa77315c516056d、dataset anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress。元生成identity candidate C0と実評価C2は別field。actual文書checkout 082b559bc784cb5f3da70fbc4c3710631b49d6c2、計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。actualPython3.14.0 Windows AMD64、elapsed51.51303069991991秒/OScheckpoint privatepeak206020608B。

engineering900秒/2GiB private/output1GiB/single32MiB/files32 checkpoint上限を維持。blocking計算中断・full loaded runtime閉包・allwriter/global/native容量証明ではない。

## 原結果

CLI exit0/complete/1cell success。処理successを性能合格・正式受入・勝者・採択へしない。

- 機械10/10・sensor9/10・precision19/19・clean誤警報0・全未対応equipment0。
- 48calibrated、fit_samples各600/calibration各290、14400scores。利用可能13760・不能640。
- mask/observation18000行全対応、motor温度missing30観測行。
- source29/equipment19/events40/incidents20、19causal_detected・1no_candidate_in_window。
- 検出19件だけ原delay機械10件1秒/sensor9件2秒。count19/min1/max2/median1/mean1.4736842105263157秒。未検出1件delay null。
- clean_rate原0/3365/value0、effective_clean_seconds3255/effective_clean_rate0.0、false_alert_burden原0/20/value0。rate/burdenを単純確率へしない。

## 欠測がpeer入力へ及ぼす原変化

排他的primaryはphase480/peer_quality_or_nonfinite120/current_target_quality30/previous_target_quality_or_nonfinite10、合計640。非排他的tagsはphase480/peer120/current quality30/current nonfinite30/previous quality30、重複するため独立行として加算0。全不能score/residual null・threshold_exceeded=false。phaseタグと別primaryの重複0原row集合/result pinを保存。旧layout2 C2品質のphase-primary重複・不能604を今回へ流用0。

同quality C1の保存manifest availability13880/不能520と入力10pin一致、今回C2 availability13760/不能640。同motor温度のcurrent30+previous10に加え、current/conveyor_speed/vibration各40peer不能＝120を原C2 score内訳とC1保存availabilityから照合する。欠測30観測行と8target score不能640行は別量。

| target | C1 available | C2 available | C1−C2 | C2 primary不能 |
| --- | ---: | ---: | ---: | --- |
| conveyor-01.conveyor_speed | 1740 | 1740 | 0 | {'mode_recipe_or_phase': 60} |
| conveyor-01.motor_current | 1740 | 1740 | 0 | {'mode_recipe_or_phase': 60} |
| conveyor-01.motor_temperature | 1740 | 1740 | 0 | {'mode_recipe_or_phase': 60} |
| conveyor-01.vibration_feature | 1740 | 1740 | 0 | {'mode_recipe_or_phase': 60} |
| motor-01.conveyor_speed | 1740 | 1700 | 40 | {'mode_recipe_or_phase': 60, 'peer_quality_or_nonfinite': 40} |
| motor-01.motor_current | 1740 | 1700 | 40 | {'mode_recipe_or_phase': 60, 'peer_quality_or_nonfinite': 40} |
| motor-01.motor_temperature | 1700 | 1700 | 0 | {'current_target_quality': 30, 'mode_recipe_or_phase': 60, 'previous_target_quality_or_nonfinite': 10} |
| motor-01.vibration_feature | 1740 | 1700 | 40 | {'mode_recipe_or_phase': 60, 'peer_quality_or_nonfinite': 40} |

cycle09 sample8911–8914の他3target原12scoreは全peer_quality_or_nonfinite/null residual-score/thresholdfalse/streak0。同窓8910は4target全phase不能、8915は4target復帰。全10cycleのpeer40各という集計と、この原12score窓をMAIN quality-peer-propagation-proof.jsonへ保存。全10cycleの全peer score行を個別extractしたclaimはしない。

## cycle09 sensor未検出の原対応

対象 motor-01.motor_temperature、event start/end8910/8913、matching window end8916。原candidate_count0/no_candidate_in_window/causal_detected=false/matched_episode_id=None/selected_source_episode_id=None/support[]/delay None。

| sample | available | primary | score | residual | threshold | streak |
| ---: | --- | --- | ---: | ---: | --- | ---: |
| 8908 | True | None | 0.12083875643554315 | 0.035989424044497974 | False | 0 |
| 8909 | True | None | 0.858034906168713 | 0.6382362007055061 | False | 0 |
| 8910 | False | mode_recipe_or_phase | None | None | False | 0 |
| 8911 | False | current_target_quality | None | None | False | 0 |
| 8912 | False | current_target_quality | None | None | False | 0 |
| 8913 | False | current_target_quality | None | None | False | 0 |
| 8914 | False | previous_target_quality_or_nonfinite | None | None | False | 0 |
| 8915 | True | None | 0.7460259364653167 | 1.2189466050861217 | False | 0 |
| 8916 | True | None | 0.6028213817344815 | 1.0620328329125646 | False | 0 |
| 8917 | True | None | 0.6314192199320494 | 1.093368391170637 | False | 0 |
| 8918 | True | None | 0.0558402166271126 | 0.34031643095144737 | False | 0 |
| 8919 | True | None | 0.7786389078527021 | -0.4516770176891651 | False | 0 |

8910phase不能→8911–8913current欠測→8914previous欠測でstreak0。8915復帰score0.7460259364653167/8916score0.6028213817344815はthreshold6未満。異常区間中の2連続available超過・persistence2不成立。不能行のscore・未検出delayを補完0。C1同窓の復帰scoreとの差を保持し、同じ検出集計から原profile/score/residual/episode一致を推定0。

GT・threshold6・persistence2・second-exceedance・first-equipment-onset-no-retry-v1・science変更0。実入力対応・保存・状態分類の不具合は観測なし。

## 検出19件の原target-source-equipment対応

全19件でsource.full_target=event.full_target、source ID∈matched equipment.source_episode_ids、equipment.matched_event_id=event IDを照合。原support各2件、onset offset機械1000ms10件/sensor2000ms9件。未検出1件のnullはこの表へ補わない。

| event | target source | equipment | 原delay秒 | support件数 |
| --- | --- | --- | ---: | ---: |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-00-sensor | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_temperature-7292-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_temperature-7292-source-equipment | 2.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-00-machine | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_current-7312-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_current-7312-source-equipment | 1.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-01-sensor | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_temperature-7472-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_temperature-7472-source-equipment | 2.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-01-machine | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_current-7492-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_current-7492-source-equipment | 1.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-02-sensor | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_temperature-7652-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_temperature-7652-source-equipment | 2.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-02-machine | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_current-7672-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_current-7672-source-equipment | 1.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-03-sensor | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_temperature-7832-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_temperature-7832-source-equipment | 2.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-03-machine | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_current-7852-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_current-7852-source-equipment | 1.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-04-sensor | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_temperature-8012-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_temperature-8012-source-equipment | 2.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-04-machine | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_current-8032-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_current-8032-source-equipment | 1.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-05-sensor | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_temperature-8192-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_temperature-8192-source-equipment | 2.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-05-machine | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_current-8212-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_current-8212-source-equipment | 1.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-06-sensor | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_temperature-8372-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_temperature-8372-source-equipment | 2.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-06-machine | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_current-8392-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_current-8392-source-equipment | 1.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-07-sensor | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_temperature-8552-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_temperature-8552-source-equipment | 2.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-07-machine | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_current-8572-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_current-8572-source-equipment | 1.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-08-sensor | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_temperature-8732-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_temperature-8732-source-equipment | 2.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-08-machine | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_current-8752-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_current-8752-source-equipment | 1.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-09-machine | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_current-8932-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c2-phase-conditional-score-motor-01-motor_current-8932-source-equipment | 1.0 | 2 |

全20event-incident、19matched target-source-equipment、5selectedmotor4target窓、30non-ok mask/observation、全source/equipment episodeを新EXTRACTへ保存。

## 保存manifest/config比較

| layout/stratum/candidate | machine | sensor | precision | clean | available/unavailable | 原delay median/mean秒 |
| --- | --- | --- | --- | ---: | --- | --- |
| 3/core/c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 13920/480 | 1.5/1.5 |
| 3/quality-stress/c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 13880/520 | 1.0/1.4736842105263157 |
| 2/quality-stress/c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13796/604 | 1.0/1.0 |
| 1/quality-stress/c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13760/640 | 1.0/1.0 |
| 0/quality-stress/c2-phase-conditional | 4/10 | 9/10 | 13/19 | 0 | 13760/640 | 1.0/1.3076923076923077 |
| 3/quality-stress/c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13760/640 | 1.0/1.4736842105263157 |

今回・同layout3 core C2・同quality C1・旧layout0/1/2 quality C2の6cell。全宣言16calculator source/candidate_config/compiled_candidate_config一致、同seed/role devを保持。同quality C1はinput10全pin一致、core/quality及び各layoutの入力pin差をfield別保存。旧5cell result本文再展開/再compute0。旧layout0 C2機械4/10/sensor9/10/precision13/19の原差を保持。

旧18cell完成比較とlayout3 core3候補・quality C1保存を保持。同seed4layout・2strata・複数候補で新独立seedや6独立datasetではない。bootstrap・統計CI・勝者・採択0。完成model/replay/risk-owner/native/probe/collector/Git37/CI反復0。

## 原pin・保存root・失敗履歴

| 原保存 | bytes | SHA256 |
| --- | ---: | --- |
| observations | 9600573 | 0a81a591db94635b1805534ce731b2352f2ad62ea34b03fb014939c64aff2ce8 |
| configuration | 5518 | 1e6abf37d2db77cabd2010963ecdd655ff83ad9d1125735317eb1cabf90b5994 |
| manifest | 8055 | 6d76f7ee43f5dd9ff77450aa073ff3cf56848ecd69e1c3f5b7882c56bc729512 |
| evaluation | 25178951 | e6be427baeeaafb83e8fc9dd8e279a814b0e1ec4c8de1e98530d4a41e7e4adb0 |
| numerical | 25173353 | 90fbf6bbe564a3140a0c34f680192e944d18e7cd96f21edf4cb8909709a2f05e |
| peer-propagation | 5053 | 2cba3651da2d7449e46f1c9b65c953ab3ad1b18c34f74ca3bd49de61892a4654 |
| phase-quality-overlap | 179 | cbfa8133e05ef45e615a9899e88a4bc886f4813d31c9b07dc6e92d23f69b1ebe |

| 保存manifest layout/stratum/candidate | bytes | SHA256 |
| --- | ---: | --- |
| 3/core/c2-phase-conditional | 8009 | bbde7501279dc71ea668bfc6e8257ad89c0d8d68bdc3123cdd217a45a180d852 |
| 3/quality-stress/c1-phase-level | 8049 | a05cca45875f3de8e40762208c69ab17119e39a20ac87b0060846b0db87d517e |
| 2/quality-stress/c2-phase-conditional | 8041 | 619ba0e5f5b6758c54886d41edde95ad26c1cbb7568476e689f77b3286eb4f92 |
| 1/quality-stress/c2-phase-conditional | 8039 | a2157815936c182eccc93409dddd4dfa16821ba482417df4d5a2b218b092844a |
| 0/quality-stress/c2-phase-conditional | 8062 | ef6829dbb07862056362ec19dc3934e5d94de6fc2c50fedc755a44d1e4751286 |
| 3/quality-stress/c2-phase-conditional | 8055 | 6d76f7ee43f5dd9ff77450aa073ff3cf56848ecd69e1c3f5b7882c56bc729512 |

| 原extract | records | bytes | SHA256 |
| --- | ---: | ---: | --- |
| incident-ledger-001.json | 20 | 34580 | 5d0a2453fecd5a6cbf3f326611085f3ac4b5ac8a31e1b57605369112d56e1c07 |
| matched-target-pairs-001.json | 19 | 65171 | 4c112daa2fc3d866cc761350681fd27a9a6073fbf7c00cbae65b55494736e636 |
| selected-windows-001.json | 4 | 63856 | ec191423703a6a7f0c55718ac5d2175a8c5b9eacffca41156b471378f38d6ccd |
| selected-windows-002.json | 1 | 13296 | 3e1dcc27e13aeafa5e8641c2fc1e68ff62339b2e7824df50c59b67a15640d230 |
| non-ok-input-records-001.json | 30 | 21929 | 4c748c46d893a65df24aadaead81d26ec8e8fccc650a5ec178300dda703d89cd |
| all-source-equipment-episodes-001.json | 48 | 40573 | d9be6868d85c7f08f6d1e38a97aa080cd23de2b920b3632a043aeccb6d2cdf72 |

DATA dev-layout3-quality-c2-20261012閉鎖{'bytes': 38225795, 'files': 19, 'manifest_pin': {'bytes': 2264, 'sha256': '3a1688a4f8e4701e5a0666edf688d6c5f2191b9ffc9d47a4ff7c01dca0acc786'}}、EXTRACT representative-layout3-quality-c2-extract-20261012-prep閉鎖{'bytes': 240495, 'files': 7, 'manifest_pin': {'bytes': 1090, 'sha256': '226715107d97cfac67474d576bcb379ae68fb5b4cb202c9b36dad54b62afc76c'}}。MAIN representative-layout3-quality-c2-20261012-prep/POST representative-layout3-quality-c2-post-20261012-prepの最終post-save/owners/root-closedを優先。

117science-source/旧89root count-byte-closurepin/外部固定C1 MAIN35file226520B容量false/旧C2 cache補足pin不変。過去failed/capacityfalse/closure limitsを保持。前quality C1 owner script selector miss、前layout3 coreC2 builder限定置換expected1/actual2拒否、前C0 foreground失敗と未保存metadata別continuation、前layout2 C0 commitTimeout原failed/commit返値Noneと別既存commit確認・別push-only一回完成、前C2core lsremote128/Connection resetと別metadata continuationを保持。元failed書換え・原helper/model/Git反復0。

文書保存前135helpersはfull saved creation-start_token/live-execution一致・原11failed124passed/CIM同original不在/repo helpercriticalなし。今回model/analysis2passed、新foreground失敗0。CIM decimal100ns→microsecond truncation/full token比較、PID単独0/native回収claim0。foreground fullcreation/stdioNone、selectedCLIを全helperstdioにしない。

新metadata512KiB32entry/reserve128KiB/single128KiB、recursive full coverage/Python-B。新書込み前script・失敗証拠・閉鎖分件数/bytes確認、対象文字列限定/hash-seed無限定置換0。閉鎖・外部固定root追記・原raw削除移動・上限緩和0。

## Git承認・次unit・正式gate

送信リスク通知後の人の明示承認で、同送信先 https://github.com/tyaro/banto-ai.git へ同種合成dev結果・ユーザー名を含むPC内入力pathの報告を継続送信できる。report/current-handoff2を一回[skip ci] commit/pushし、original Git/API returns・HEAD/upstream/remote ref/clean/docpinsはPOST保存。後追い文書再commit0。Git512KiB16entry/stdout1MiB/累積30秒、preflight別量を維持。

次unitは同保存chunk003/dev seed/layout3/quality-stressをC0 c0-diff-control、新ID dev-layout3-quality-c0-20261012で1cell実評価し、同layout3の3候補×2strata保存比較を完成する。manifest40be/同quality10input pins/元payload書込み・生成・replay0。次モデル未開始。

automation設定への詳細結果・PC内path転記/更新0、文書参照短指示ACTIVE維持。CI381385/code661の4130success独立verifier完成保存維持、新query/download/verifier0/doc-onlyCI追跡0。旧381365/a54961最後in_progressは履歴のまま。CI成功≠model性能/native/正式受入。

formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読/正式5残件・最終受入未完了/create_native早期拒否/全7役whole.run reader実起動禁止/元caps-unknown原owner-stop/追加agent禁止。未完了formal/native証明を少量dev開始条件に戻さない。Sol容量又は人の停止では保全後PAUSED、重複再試行0。
