# 第2 dev seed・layout2 C1 quality-stress実評価（2026-10-13）

保存済み合成dev quality-stressをC1で1回fresh compute。機械10/10・センサー9/10・precision19/19・正常区間誤警報0件。未検出1件と原delay nullを保持。処理成功を性能保証・採択・正式受入にはしない。

## 入力と実行

- run dev-seed7466813550306735603-layout2-quality-c1-20261013 / dataset anomaly-v03-dev-seed-7466813550306735603-layout-02-quality-stress。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\014\attempt-0001\result\payload\manifest.json / {"bytes": 75700, "sha256": "13a1f0848235ab785ddc31036c819927a40d5a62e7ff55adb91afe465275998a"}。seed7466813550306735603/layout2/quality-stress/dev、input10pin→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics保存。
- 元生成C0・実評価C1は別field。元payload書込み・新生成・replay・追加agent0。
- checkout eea7642de3804a130b8ed84e11c3f8c1cdc5692b、計算661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/candidate-compiled config不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 16.68219650001265秒/privatepeak 152334336B。
- observations {"bytes": 9600484, "sha256": "6938545c18ea01b4045a5248c2dbee7d6e7fc464d8491ad29e0c6ac984a4ac54"}、configuration {"bytes": 5512, "sha256": "a11bace09a71204818c8c8865b6b473c34f609729274544a87ae9d654dbf8909"}、manifest {"bytes": 8058, "sha256": "e4bbfb5a349d48129e0b69b44740a8c26ad46396a18f755c1b38c0d8ef5978c7"}、evaluation {"bytes": 14510302, "sha256": "165d6609152708c494fbaeebf160c5e29075105b3eeaf90e495bca3798c585bf"}。宣言source pinはfull loaded runtime/native認証ではない。
- C0 threshold4/C1・C2 threshold6/operator>/persistence2・GT/matching/science不変。原score閾値判定を全行確認。

## 原結果と利用不能

|項目|原値|
|---|---|
|machine|10/10|
|sensor|9/10|
|precision|19/19|
|clean / unmatched|0 / 0|
|source / equipment / incidents / events|29 / 19 / 20 / 40|
|available / unavailable scores|13889 / 511|

48profiles全calibrated/fit各600/calibration各290/C2stateなし48。18000observations-mask対応、non-ok30行。primary排他的不能はphase471/current quality30/previous quality10＝511。非排他的phase480とcurrent quality30の重複9行を原スコアで保存。quality不能40行のうち9行が元phase不能に重なるため、core比の不能増は31行。全不能score-residual null/thresholdfalse。
非排他的tags {"current_nonfinite": 30, "current_target_quality": 30, "mode_recipe_or_phase": 480, "previous_target_quality_or_nonfinite": 30}。current quality/current nonfinite/previous qualityの各30を90独立行へ加算しない。motor-01温度だけ1709/1800利用可、他7targets1740/1800。C1core13920/480に対してquality13889/511。
検出19件だけdelaycount19/min=max=mean=median1秒。未検出1件delaynull補完0。clean_rate0/3365原0/effective3254秒rate0/burden0/20原0。率・burdenを単純確率へしない。

## 未検出cycle09温度の原スコア

sensor spike [8901,8904)、matching window8901–8907。8901score165.48761451025524/streak1→8902–8904current quality不能→8905previous quality不能でstreak reset→8906score1.2330449546737592/8907score0.7095916249324966はいずれも6未満/streak0。固定persistence2未成立、candidate0/no_candidate_in_window/causalfalse/matchednull/delaynull。対象窓内phase不能0。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|8901|True|165.48761451025524|1|None|
|8902|False|None|0|current_target_quality|
|8903|False|None|0|current_target_quality|
|8904|False|None|0|current_target_quality|
|8905|False|None|0|previous_target_quality_or_nonfinite|
|8906|True|1.2330449546737592|0|None|
|8907|True|0.7095916249324966|0|None|

原event/incident/全targetwindow/選択episodeなしを-save/selected-miss-summaryへ保存。GT・閾値・persistence・matching変更で成功へ補わない。

## 原19検出の対応

machine10・sensor9の原event→対象source→matched equipment→support2scoreを照合、全38supportは対象一致/利用可/score>6。各onset=start+1秒。machine10窓とsensor9窓は7全利用可/maxstreak3、sensor未検出1窓は3利用可4不能/maxstreak1。
全source29はmatched equipment19内に参照。source内訳 {"motor-01.motor_current": 10, "motor-01.vibration_feature": 10, "motor-01.motor_temperature": 9}、class membership {"machine": {"motor-01.motor_current": 10, "motor-01.vibration_feature": 10}, "sensor": {"motor-01.motor_temperature": 9}}。source29をequipment29や誤警報29へしない。原全20incident/target窓/全511不能/全30non-ok入力/全episodesを-analysis、全matched target/supportを-save保存。実入力対応・保存・状態分類の不具合は観測なし。

## 保存済みcoreとC1quality比較

|条件|machine|sensor|precision|clean|available / unavailable|
|---|---|---|---|---|---|
|core|10/10|10/10|20/20|0|13920 / 480|
|quality-stress|10/10|9/10|19/19|0|13889 / 511|

同seed/layout2の別stratum。10input pinsの一致 {"dataset-manifest.json": false, "event-ledger.jsonl": false, "events.jsonl": false, "fingerprint.json": false, "generator-config.json": false, "observations.jsonl": false, "origins.json": true, "quality-mask.jsonl": false, "split-manifest.json": true, "targets.json": true}、一致3fileはorigins/split-manifest/targets。観測・quality-mask等は異なるため同一入力とは呼ばない。旧coreモデル再計算0/source16candidatecompiled一致。保存指標差と今回原resetを保持し、別入力の全差を欠測だけの反実仮想証明へしない。

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
|7466813550306735603|2|10/10|9/10|19/19|0|

保存manifest指標15C1quality cellsを比較、旧モデル再計算0。第1seed全72＋第2seed layout0/1全12/layout2 core全3/quality C1一件＝88boardcells/実使用seed2。88独立datasetではない。bootstrap/統計CI/勝者/採択0。

## 証拠・次工程・正式状態

- records/analysis/save/final: artifacts/representative-seed2-layout2-quality-c1-20261013-*。最終-final/post-saveとroot-closed優先。DATA artifacts/representative-anomaly-evaluation/dev-seed7466813550306735603-layout2-quality-c1-20261013 / {"bytes": 27557279, "files": 19, "manifest_pin": {"bytes": 2235, "sha256": "cbdb0e31900db84c59b5fcda6e558c8d207a59259f9ff48bd17ee924a0bd4fca"}}。
- 旧437root/402helper/22failed380passed/missingexecution1保持。旧失敗・誤記を保持し閉鎖・外部固定root追記整理0/fullstdio/native回収claim0。
- EvidenceStore16MiB512files/part256KiB/失敗予備2MiB16files/閉鎖512KiB4files、script・失敗・閉鎖を含む全write preflight。実行900秒2GiBoutput1GiBsingle32MiBfiles32/Git累積30秒16entry512KiBstdout1MiBstderr128KiB/nativeprotocol維持。checkpoint≠blocking中断/fullruntime/global/allwriter容量証明。
- prepare_result_index実使用/report-handoff-index3docsを同種合成dev結果・PC内path継続送信承認内で一回[skip ci] commit/push。原Git/HEAD-upstream-lsremote-clean/docpins-save/-final。追加承認質問・bypass0。
- 次unit同seed/layout2/quality-stress C2 c2-phase-conditional、新ID dev-seed7466813550306735603-layout2-quality-c2-20261013。同manifest/input10、本文今回C1読取済み・次model未開始。元生成C0/次評価C2別field、新独立seedではない。
- ACTIVE/automation詳細転記0。CI381385/4130保持/querydownloadverifiertests0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了。create_native早期拒否/全7役reader禁止/caps-unknown原owner保持/追加agent禁止。未完了formal/nativeをdev開始条件へ戻さない。Sol容量・人停止は原保全後PAUSED、重複再試行なし。
