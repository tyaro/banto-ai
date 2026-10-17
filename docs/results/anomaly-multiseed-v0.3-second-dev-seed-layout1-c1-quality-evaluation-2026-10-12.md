# 第2 dev seed・layout1 C1 quality-stress実評価（2026-10-12）

保存済み合成dev quality-stressをC1で1回fresh compute。機械10/10・センサー9/10・precision19/19・正常区間誤警報0件。未検出1件と原delay nullを保持。処理成功を性能保証・採択・正式受入にはしない。

## 入力と実行

- run dev-seed7466813550306735603-layout1-quality-c1-20261012 / dataset anomaly-v03-dev-seed-7466813550306735603-layout-01-quality-stress。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\013\attempt-0001\result\payload\manifest.json / {"bytes": 75699, "sha256": "d4743f431240dee56e5ead1d0709a998e502b6a7e8a4aecd3f00468dced8bd81"}。seed7466813550306735603/layout1/quality-stress/dev、input10pin→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics保存。
- 元生成C0・実評価C1は別field。元payload書込み・新生成・replay・追加agent0。
- checkout c70d1d3362056958ece2544f30e8f429bf638ed4、計算661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/candidate-compiled config不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 21.90913849999197秒/privatepeak 152440832B。
- observations {"bytes": 9600492, "sha256": "ef8b9dcc9138899b773ce5aebb07592211e679e71d8578f4be21f97eb6b609a6"}、configuration {"bytes": 5512, "sha256": "b2335b5625d63787d8add3df47304e210c70d8576711195e229cf6c8293725a5"}、manifest {"bytes": 8058, "sha256": "e52519f10609e7a3cdaf15cbfe2e95c04f43d85bc690dd248cf314d93bce72c2"}、evaluation {"bytes": 14510177, "sha256": "2aae9c8152367fb82644b00216e5d29ab1ff1f7d6217f8566c980d439f608bbb"}。宣言source pinはfull loaded runtime/native認証ではない。
- C0 threshold4/C1・C2 threshold6/operator>/persistence2・GT/matching/science不変。原score閾値判定を全行確認。

## 原結果と利用不能

|項目|原値|
|---|---|
|machine|10/10|
|sensor|9/10|
|precision|19/19|
|clean / unmatched|0 / 0|
|source / equipment / incidents / events|29 / 19 / 20 / 40|
|available / unavailable scores|13880 / 520|

48profiles全calibrated/fit各600/calibration各290/C2stateなし48。18000observations-mask対応、non-ok30行。primary排他的不能はphase480/current quality30/previous quality10＝520。全不能score-residual null/thresholdfalse。
非排他的tags {"current_nonfinite": 30, "current_target_quality": 30, "mode_recipe_or_phase": 480, "previous_target_quality_or_nonfinite": 30}。current quality/current nonfinite/previous qualityの各30を90独立行へ加算しない。motor-01温度だけ1700/1800利用可、他7targets1740/1800。C1core13920/480に対してquality13880/520。
検出19件だけdelaycount19/min=max=mean=median1秒。未検出1件delaynull補完0。clean_rate0/3365原0/effective3255秒rate0/burden0/20原0。率・burdenを単純確率へしない。

## 未検出cycle09温度の原スコア

sensor spike [8864,8867)、matching window8864–8870。8864score148.7727717285926/streak1→8865–8867current quality不能→8868previous quality不能でstreak reset→8869score1.1825322175941724/8870score1.4618306270076464はいずれも6未満/streak0。固定persistence2未成立、candidate0/no_candidate_in_window/causalfalse/matchednull/delaynull。対象窓内phase不能0。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|8864|True|148.7727717285926|1|None|
|8865|False|None|0|current_target_quality|
|8866|False|None|0|current_target_quality|
|8867|False|None|0|current_target_quality|
|8868|False|None|0|previous_target_quality_or_nonfinite|
|8869|True|1.1825322175941724|0|None|
|8870|True|1.4618306270076464|0|None|

原event/incident/全targetwindow/選択episodeなしを-save/selected-miss-summaryへ保存。GT・閾値・persistence・matching変更で成功へ補わない。

## 原19検出の対応

machine10・sensor9の原event→対象source→matched equipment→support2scoreを照合、全38supportは対象一致/利用可/score>6。各onset=start+1秒。machine10窓とsensor9窓は7全利用可/maxstreak3、sensor未検出1窓は3利用可4不能/maxstreak1。
全source29はmatched equipment19内に参照。source内訳 {"motor-01.motor_current": 10, "motor-01.vibration_feature": 10, "motor-01.motor_temperature": 9}、class membership {"machine": {"motor-01.motor_current": 10, "motor-01.vibration_feature": 10}, "sensor": {"motor-01.motor_temperature": 9}}。source29をequipment29や誤警報29へしない。原全20incident/target窓/全520不能/全30non-ok入力/全episodesを-analysis、全matched target/supportを-save保存。実入力対応・保存・状態分類の不具合は観測なし。

## 保存済みcoreとC1quality比較

|条件|machine|sensor|precision|clean|available / unavailable|
|---|---|---|---|---|---|
|core|10/10|10/10|20/20|0|13920 / 480|
|quality-stress|10/10|9/10|19/19|0|13880 / 520|

同seed/layout1の別stratum。10input pinsの一致 {"dataset-manifest.json": false, "event-ledger.jsonl": false, "events.jsonl": false, "fingerprint.json": false, "generator-config.json": false, "observations.jsonl": false, "origins.json": true, "quality-mask.jsonl": false, "split-manifest.json": true, "targets.json": true}、一致3fileはorigins/split-manifest/targets。観測・quality-mask等は異なるため同一入力とは呼ばない。旧coreモデル再計算0/source16candidatecompiled一致。保存指標差と今回原resetを保持し、別入力の全差を欠測だけの反実仮想証明へしない。

|seed|layout|machine|sensor|precision|clean|
|---|---|---|---|---|---|
|2486912926863618161|0|10/10|9/10|19/19|0|
|2486912926863618161|1|10/10|9/10|19/19|0|
|2486912926863618161|2|10/10|9/10|19/19|0|
|2486912926863618161|3|10/10|9/10|19/19|0|
|2486912926863618161|4|10/10|9/10|19/19|0|
|2486912926863618161|5|10/10|9/10|19/19|0|
|2486912926863618161|6|0/10|9/10|9/19|0|
|2486912926863618161|7|10/10|9/10|19/19|0|
|2486912926863618161|8|10/10|9/10|19/19|0|
|2486912926863618161|9|10/10|9/10|19/19|0|
|2486912926863618161|10|10/10|9/10|19/19|0|
|2486912926863618161|11|10/10|9/10|19/19|0|
|7466813550306735603|0|10/10|9/10|19/19|0|
|7466813550306735603|1|10/10|9/10|19/19|0|

保存manifest指標14C1quality cellsを比較、旧モデル再計算0。第1seed全72＋第2seed layout0全6/layout1 core全3/quality C1一件＝82boardcells/実使用seed2。82独立datasetではない。bootstrap/統計CI/勝者/採択0。

## 証拠・次工程・正式状態

- records/analysis/save/final: artifacts/representative-seed2-layout1-quality-c1-20261012-*。最終-final/post-saveとroot-closed優先。DATA artifacts/representative-anomaly-evaluation/dev-seed7466813550306735603-layout1-quality-c1-20261012 / {"bytes": 27557162, "files": 19, "manifest_pin": {"bytes": 2235, "sha256": "29205d9760fb4861b7dd9cb50a796a76809c479e991eedadfbec39d2866c0b1a"}}。
- 旧404root/376helper/21failed355passed/missingexecution1保持。旧失敗・誤記を保持し閉鎖・外部固定root追記整理0/fullstdio/native回収claim0。
- EvidenceStore16MiB512files/part256KiB/失敗予備2MiB16files/閉鎖512KiB4files、script・失敗・閉鎖を含む全write preflight。実行900秒2GiBoutput1GiBsingle32MiBfiles32/Git累積30秒16entry512KiBstdout1MiBstderr128KiB/nativeprotocol維持。checkpoint≠blocking中断/fullruntime/global/allwriter容量証明。
- prepare_result_index実使用/report-handoff-index3docsを同種合成dev結果・PC内path継続送信承認内で一回[skip ci] commit/push。原Git/HEAD-upstream-lsremote-clean/docpins-save/-final。追加承認質問・bypass0。
- 次unit同seed/layout1/quality-stress C2 c2-phase-conditional、新ID dev-seed7466813550306735603-layout1-quality-c2-20261012。同manifest/input10、本文今回C1読取済み・次model未開始。元生成C0/次評価C2別field、新独立seedではない。
- ACTIVE/automation詳細転記0。CI381385/4130保持/querydownloadverifiertests0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了。create_native早期拒否/全7役reader禁止/caps-unknown原owner保持/追加agent禁止。未完了formal/nativeをdev開始条件へ戻さない。Sol容量・人停止は原保全後PAUSED、重複再試行なし。
