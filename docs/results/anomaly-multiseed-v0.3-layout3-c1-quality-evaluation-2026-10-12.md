# dev layout3 C1 quality-stress実評価（2026-10-12 JST）

## 入力・設定・実結果の対応

保存済み合成dev seed2486912926863618161/layout3/quality-stressを既存CLI C1 c1-phase-level、新ID dev-layout3-quality-c1-20261012で1cell実compute_evaluation。input10pins→新snapshot→fresh phase fit/calibration→原profiles/scores/source-equipment episodes/events/incidents/metricsを保存。元payload書込み・生成・replay・production/test変更・類似owner試験・追加agent・holdout本文読取り0。

input manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\003\attempt-0001\result\payload\manifest.json

manifest 75699B/40be5e90bb27173cf9d21252940f13beb86a17187ea0fb25afa77315c516056d、dataset anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress。元生成identity candidate C0と実評価C1は別field。実文書checkout 263b94a9b5e28b8236dc0f2be00ff94a91150eb2、計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。actualPython3.14.0 Windows AMD64、elapsed32.84469880000688秒/OScheckpoint privatepeak149004288B。

engineering900秒/2GiB private/output1GiB/single32MiB/files32 checkpoint上限を維持。blocking計算中断・full loaded runtime閉包・allwriter/global/native容量証明ではない。

## 原結果

CLI exit0/complete/1cell success。処理successを性能合格・正式受入・勝者・採択へしない。

- 機械10/10・sensor9/10・precision19/19・clean誤警報0・全未対応equipment0。
- 48calibrated、fit_samples各600/calibration各290、14400scores。利用可能13880・不能520。
- mask/observation18000行全対応、motor温度missing30観測行。
- source29/equipment19/events40/incidents20、19causal_detected・1no_candidate_in_window。
- 検出19件だけ原delay：機械10件1秒、sensor9件2秒。count19/min1/max2/median1/mean1.4736842105263157秒。未検出1件delay null。
- clean_rate原0/3365/value0、effective_clean_seconds3255/effective_clean_rate0.0、false_alert_burden原0/20/value0。rate/burdenを単純確率へしない。

## 不能行と欠測

排他的primaryはphase480/current_target_quality30/previous_target_quality_or_nonfinite10、合計520。非排他的tagsはphase480/current quality30/current nonfinite30/previous quality30、重複するため独立行として加算しない。全不能score/residual null・threshold_exceeded=false。

今回phaseタグと別primaryの重複0行を原scoreから確認し、quality-phase-overlap.jsonへ空原row集合/result pinを保存。旧layout2 C1 qualityのphase/current重複9行・不能511を今回へ流用0。同layout3 core C1のavailable13920/unavailable480に対してqualityはavailable13880/unavailable520。欠測30観測行と8target score不能520行は別量。

## cycle09 sensor未検出の原窓

対象 motor-01.motor_temperature、event start/end sample8910/8913、window end8916。原candidate_count0/no_candidate_in_window/causal_detected=false/matched_episode_id=None/selected_source_episode_id=None/support[]/delay None。

| sample | available | primary reason | score | residual | threshold | streak | source |
| ---: | --- | --- | ---: | ---: | --- | ---: | --- |
| 8908 | True | None | 0.07489171021261573 | -0.00031049999999765987 | False | 0 | None |
| 8909 | True | None | 0.7572720732650313 | 0.03121550000000184 | False | 0 | None |
| 8910 | False | mode_recipe_or_phase | None | None | False | 0 | None |
| 8911 | False | current_target_quality | None | None | False | 0 | None |
| 8912 | False | current_target_quality | None | None | False | 0 | None |
| 8913 | False | current_target_quality | None | None | False | 0 | None |
| 8914 | False | previous_target_quality_or_nonfinite | None | None | False | 0 | None |
| 8915 | True | None | 0.7017050539113043 | 0.07241850000000127 | False | 0 | None |
| 8916 | True | None | 0.5603191771403424 | 0.06339299999999781 | False | 0 | None |
| 8917 | True | None | 0.6141916529273549 | 0.06683200000000156 | False | 0 | None |
| 8918 | True | None | 0.04461436785148424 | 0.02477649999999798 | False | 0 | None |
| 8919 | True | None | 0.810977358317196 | -0.024145000000004302 | False | 0 | None |

8910はphase不能。8911–8913はcurrent欠測、8914はprevious欠測でstreak0。復帰8915score0.7017050539113043/8916score0.5603191771403424はthreshold6未満。異常区間中の2連続available超過・固定persistence2は成立しない。不能行のscoreや未検出delayを補完0。旧layoutの「開始score超過/streak1」の説明を今回へ流用せず、この原窓を保持する。

GT・threshold6・persistence2・second-exceedance・first-equipment-onset-no-retry-v1・science変更0。実入力対応・保存・状態分類の不具合は観測なし。

## 検出19件の原対応

全19件でsource.full_target=event.full_target、source ID∈matched equipment.source_episode_ids、equipment.matched_event_id=event IDを照合。原support各2件、onset offset機械1000ms10件/sensor2000ms9件。未検出1件はこの表へ補わない。

| event | target source | equipment | 原delay秒 | support件数 |
| --- | --- | --- | ---: | ---: |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-00-sensor | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_temperature-7292-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_temperature-7292-source-equipment | 2.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-00-machine | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_current-7312-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_current-7312-source-equipment | 1.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-01-sensor | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_temperature-7472-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_temperature-7472-source-equipment | 2.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-01-machine | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_current-7492-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_current-7492-source-equipment | 1.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-02-sensor | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_temperature-7652-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_temperature-7652-source-equipment | 2.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-02-machine | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_current-7672-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_current-7672-source-equipment | 1.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-03-sensor | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_temperature-7832-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_temperature-7832-source-equipment | 2.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-03-machine | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_current-7852-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_current-7852-source-equipment | 1.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-04-sensor | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_temperature-8012-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_temperature-8012-source-equipment | 2.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-04-machine | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_current-8032-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_current-8032-source-equipment | 1.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-05-sensor | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_temperature-8192-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_temperature-8192-source-equipment | 2.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-05-machine | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_current-8212-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_current-8212-source-equipment | 1.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-06-sensor | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_temperature-8372-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_temperature-8372-source-equipment | 2.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-06-machine | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_current-8392-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_current-8392-source-equipment | 1.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-07-sensor | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_temperature-8552-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_temperature-8552-source-equipment | 2.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-07-machine | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_current-8572-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_current-8572-source-equipment | 1.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-08-sensor | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_temperature-8732-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_temperature-8732-source-equipment | 2.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-08-machine | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_current-8752-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_current-8752-source-equipment | 1.0 | 2 |
| anomaly-v03-dev-seed-2486912926863618161-layout-03-cycle-09-machine | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_current-8932-source | anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress-c1-phase-level-score-motor-01-motor_current-8932-source-equipment | 1.0 | 2 |

全20event-incident、19matched target-source-equipment、5selected motor4target窓、30non-ok mask/observation、全source-equipment episodeを新EXTRACTへ保存。全sensor開始score行を照合したclaimはしない。

## 保存manifest/configだけのC1比較

| layout/stratum C1 | machine | sensor | precision | clean | available/unavailable | delay median/mean (検出だけ) |
| --- | --- | --- | --- | ---: | --- | --- |
| 3/core | 10/10 | 10/10 | 20/20 | 0 | 13920/480 | 1.5/1.5秒 |
| 2/quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13889/511 | 1.0/1.0秒 |
| 1/quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13880/520 | 1.0/1.0秒 |
| 0/quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13880/520 | 2.0/1.5263157894736843秒 |
| 3/quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13880/520 | 1.0/1.4736842105263157秒 |

今回と同layout3 core C1、旧layout0/1/2 quality C1の5cell。全宣言16calculator source/candidate_config/compiled_candidate_config一致、同seed/role devを保持。同core/quality・各layoutの入力pin差をfield別保存。旧4cell result本文再展開/再compute0。集計一致を学習profile/score/residual/episode同一へしない。

旧18cell完成比較とlayout3 core3候補の完成保存を保持。同seed4layoutのcore/quality比較で、新独立seedや5独立datasetではない。bootstrap・統計CI・勝者・採択0。完成model/replay/risk-owner/native/probe/collector/Git37/CI反復0。

## 原pinと閉鎖

| 原保存 | bytes | SHA256 |
| --- | ---: | --- |
| observations | 9600573 | 0a81a591db94635b1805534ce731b2352f2ad62ea34b03fb014939c64aff2ce8 |
| configuration | 5512 | e185e371531aff142c01ce00707185a1c66a5c2fd719747e924a902d2a4a1e40 |
| manifest | 8049 | a05cca45875f3de8e40762208c69ab17119e39a20ac87b0060846b0db87d517e |
| evaluation | 14509151 | dd1d674bc6f28bf1ccbf16a964d8ed908405783b2e6a935dd9584e79702520e4 |
| numerical | 14503553 | 771141b2226b84ac597a60ba5e9804f3bb5285259423f031d3553ec7236a0367 |
| phase-quality-overlap | 179 | eaadab3f6058522e25646c20d9cdee2487ff8516c87a3bdc7f8d7960d642156a |

| 保存manifest layout/stratum | bytes | SHA256 |
| --- | ---: | --- |
| 3/core | 8003 | 28789ebe65503df67d229dde0a37df6c9bec0f27f9b8f7d3149a923eb6ec130e |
| 2/quality-stress | 8034 | 67308ad3afa221abfa1e118dd9447bb721306c843440719e80de29941732d38f |
| 1/quality-stress | 8035 | 399af646470a861c738d4c6726772927936a4408aa445523e7440050a7a2cb54 |
| 0/quality-stress | 8042 | 3042be397642799af8c5ac6d0d2fb82c8f92f0a3d66a8fe983f8cc1b8e4431d3 |
| 3/quality-stress | 8049 | a05cca45875f3de8e40762208c69ab17119e39a20ac87b0060846b0db87d517e |

| 原extract | records | bytes | SHA256 |
| --- | ---: | ---: | --- |
| incident-ledger-001.json | 20 | 33890 | ad48b9ae1f4876b251d730919371d42bf0f21659ff3e9de59b67da7640d5a023 |
| matched-target-pairs-001.json | 19 | 63509 | 08eabfc4aa5c7daf9e8ca93d696f94fcfeb509dad1e27a73405cf4b4f8d7e88b |
| selected-windows-001.json | 4 | 63099 | 713702710532895719fe8338935db812466c8c2881b1796df8d0bc0fd8506c25 |
| selected-windows-002.json | 1 | 13088 | a6366bfb38cf6a3a61dac6922a3f85531523e9dbd1cac36c81bbff1173f2a7cf |
| non-ok-input-records-001.json | 30 | 21923 | 8fd41b6d8bc998f73ed3bbdd0d199ec350c871182b2d1d6a8e0a510b624b06e2 |
| all-source-equipment-episodes-001.json | 48 | 39295 | d07ca7cf3462f8424c224e9efeb5f25d9abffffeb1d20e23e0b8e03079f10696 |

DATA dev-layout3-quality-c1-20261012閉鎖{'bytes': 27555959, 'files': 19, 'manifest_pin': {'bytes': 2258, 'sha256': 'ad6fb336aeace3945ba1c8c53210fb0bb981d1097c57af12b83e17d9d5d0c49e'}}、EXTRACT representative-layout3-quality-c1-extract-20261012-prep閉鎖{'bytes': 235888, 'files': 7, 'manifest_pin': {'bytes': 1084, 'sha256': '510a95641062a5b93b1db5a9de0c6485b299c6b433790df0607d36ec14145258'}}。MAIN representative-layout3-quality-c1-20261012-prep/POST representative-layout3-quality-c1-post-20261012-prepの最終post-save/owners/root-closedを優先。

117science-source/旧85root count-byte-closurepin/外部固定C1 MAIN35file226520B容量false/旧C2 cache補足pin不変。過去failed/capacityfalse/closure limitsを保持。前layout3 C2閉鎖builderの限定置換expected1/actual2はnestedtools-process-trackedmutation0、原エラーを閉鎖POSTへ保全後、新限定sourceの初processで未保存metadata閉鎖完成。元helper/model/Git再実行0。前layout3 C0失敗、前layout2 C0 commitTimeout原failed/commit返値Noneと別既存commit確認・別push-only一回完成、前C2core lsremote128/Connection resetと別metadata continuationを保持。元failed書換え0。

今回初期owner script名selector missはselected chunk3685aa/exit1をstartup-path-selector-error.jsonへ保全。source評価/モデル開始前のforeground読取り失敗で、instrumented helper/model/CI/native/Sol failureではない。実名・cached sourceを照合し新owner scriptを使う。元script/helper再実行0、foreground fullcreation/stdioNone。

文書保存前元132helpersはfull saved creation-start_token/live-execution一致・原11failed121passed/CIM同original不在/repo helpercriticalなし。今回model/analysis2passed。CIMdecimal100ns→microsecond truncation/full token比較、PID単独0/native回収claim0。selectedCLIを全helperstdioにしない。

新metadata512KiB32entry/reserve128KiB/single128KiB、recursive full coverage/Python-B。新書込み前script・失敗証拠・閉鎖分の件数/bytesを確認、対象文字列限定/hash-seed無限定置換0。閉鎖または外部固定root追記・原raw削除移動・上限緩和0。

## Git継続承認と次unit

送信リスク通知後の人の明示承認で、同送信先 https://github.com/tyaro/banto-ai.git へ同種合成dev結果・ユーザー名を含むPC内入力pathの報告を継続送信できる。report/current-handoff2を一回[skip ci] commit/pushし、original Git/API returns・HEAD/upstream/remote ref/clean/docpinsはPOSTへ保存。後追い文書再commit0。Git512KiB16entry/stdout1MiB/累積30秒、preflight別量を維持。

次unitは同保存chunk003/dev seed/layout3/quality-stressをC2 c2-phase-conditional、新ID dev-layout3-quality-c2-20261012で1cell実評価。manifest40be/同quality10input pins/元生成C0と実評価C2別field/元payload書込み・生成・replay0。次モデル未開始。

automation設定への詳細結果・PC内path転記/更新0、文書参照短指示ACTIVE維持。CI381385/code661の4130success独立verifier完成保存維持、新query/download/verifier0/doc-onlyCI追跡0。旧381365/a54961最後in_progressは履歴のまま。CI成功≠model性能/native/正式受入。

formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読/正式5残件・最終受入未完了/create_native早期拒否/全7役whole.run reader実起動禁止/元caps-unknown原owner-stop/追加agent禁止。未完了formal/native証明を少量dev開始条件に戻さない。Sol容量又は人の停止では保全後PAUSED、重複再試行0。
