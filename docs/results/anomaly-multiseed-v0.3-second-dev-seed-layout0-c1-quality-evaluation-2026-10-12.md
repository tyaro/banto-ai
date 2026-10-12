# 第2 dev seed・layout0 C1 quality実評価（2026-10-12）

保存済み第2合成dev seed/layout0 quality-stressを既存CLI C1で1回fresh compute。機械10/10、センサー9/10、precision19/19、正常区間の誤警報0件。処理exit0/complete/1cell successを性能保証・採択・正式受入にしない。

## 入力と実行の対応

- run dev-seed7466813550306735603-layout0-quality-c1-20261012、dataset anomaly-v03-dev-seed-7466813550306735603-layout-00-quality-stress。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\012\attempt-0001\result\payload\manifest.json / {"bytes": 75700, "sha256": "5060fceed11406c0393d8afd284cdbeb418df7052298c4dc97fdd7c887d32a0d"}。seed7466813550306735603/layout0/quality-stress/dev、10入力pin照合→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics保存。
- 元生成C0と実評価C1別field。元payload書込み・新dataset生成・replay・追加agent0。quality本文は今回初使用。
- 実checkout 294c6fb3bf0e5927da20491f6ac3783c89049ad0、計算code661b27511826fcc87cb4a02930f276afbb8f95d9/science117/calculator16/candidate/compiled config不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 19.868410900002345秒、OS sampled private peak 153485312B。
- observations {"bytes": 9600492, "sha256": "380470273c84617da87cab7c37ffd3759891d24c947c86a934d35358d5a8ffb2"}、configuration {"bytes": 5512, "sha256": "ed2682942b8cdda52ec8df50846219d3b8bd2970de69c7e0d8e317a4e8c58cf4"}、manifest {"bytes": 8074, "sha256": "e75dcf1c5402d80255d111250212b8f55a0510b3d8c723c559d0785e7dabbb24"}、evaluation {"bytes": 14507901, "sha256": "2a54b74bfbe6eed05306c8c348ee75314dcc62b6bd91cd34ae6c9161ddb1c20f"}。宣言pin≠full loaded runtime/native認証。
- C1閾値6/C0 4/C2 6/operator>/persistence2、全score原threshold flags確認。GT/matching/science変更0。

## 原指標と利用不能

|項目|原値|
|---|---|
|機械 recall|10/10|
|センサー recall|9/10|
|precision|19/19|
|clean / unmatched|0 / 0|
|source / equipment / incidents / events|29 / 19 / 20 / 40|
|scores 利用可 / 不能|13880 / 520|

48profiles全calibrated/fit各600/calibration各290/C2stateなし48。18000observations/mask対応non-ok30。排他的phase480/current quality30/previous quality10、全不能score/residual null・thresholdfalse。phaseタグ480＋own quality40−重複0=520。motor温度1700/1800、他7targets1740/1800利用可。tagsを独立行へ加算しない。
検出19だけdelaycount19/min1/max2/mean1.5263157894736843/median2秒。機械10各2秒・sensor9各1秒、未検出1delaynull補完0。clean_rate 0/3365 / 原value 0.0、effective 3255秒/rate 0.0、burden 0/20 / 原value 0.0。rate/burdenを単純確率へ読み替えない。

## 欠測によるsensor1未検出の原窓

cycle09 motor-01.motor_temperature、加算3観測[8827,8830)/windowend8833。8827 score158.9782484753409でstreak1、8828–8830current quality欠測、8831previous qualityでreset、8832/8833閾値6未満。原no_candidate_in_window/candidate0/causalfalse/matchednull/delaynull、窓3利用可4不能/maxstreak1/phase不能0。固定persistence2のepisodeが成立しなかった。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|8827|True|158.9782484753409|1|None|
|8828|False|None|0|current_target_quality|
|8829|False|None|0|current_target_quality|
|8830|False|None|0|current_target_quality|
|8831|False|None|0|previous_target_quality_or_nonfinite|
|8832|True|1.0727023342742896|0|None|
|8833|True|1.9504301771073045|0|None|

閾値・GT・matchingを変更して成功へ補わない。原event/incident/四target窓/非ok30入力mask/全520不能を-analysisへ、miss窓は-save/quality-detection-summaryへ保存。

## 原19検出の対応

全19causal_detected/candidate1/event-target-source-equipment/support2scoreを原結果へ照合。support38score原利用可/対象一致/score>6。機械10窓各6利用可/開始1phase不能/maxstreak2、検出sensor9窓各7全利用可/maxstreak3。全29sourceは19matched equipment内参照、原内訳 {"motor-01.motor_current": 10, "motor-01.vibration_feature": 10, "motor-01.motor_temperature": 9}。source29をequipment29や誤警報29へしない。原全ledger/episodes/選択cycle00窓保存。入力対応・保存・分類の実経路不具合観測なし。

## 同C1 coreとの比較

|stratum|machine|sensor|precision|clean|available|
|---|---|---|---|---|---|
|core|10/10|10/10|20/20|0|13920|
|quality-stress|10/10|9/10|19/19|0|13880|

同seed/layout0のcoreとqualityで共通inputはorigins/split-manifest/targets3、観測/quality/fingerprint等の差保持。利用可40減とsensor1未検出を原窓へ対応させ、旧core再計算0。同候補設定/calculator16/compiled config一致。

## 保存済みC1 quality比較

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

第1seed/layout0–11 C1quality＋今回の13保存manifest指標、旧model再compute0/source16candidatecompiled一致/input差保持。第1seed全72＋第2seed core3/qualityC1=4cells、board76cells/実使用seed2。第2seed qualityC0/C2・残layouts未完成、76独立datasetではない。bootstrap/統計CI/勝者/採択0。

## 証拠・次unit・正式状態

- model artifacts/representative-seed2-layout0-quality-c1-20261012-records、analysis artifacts/representative-seed2-layout0-quality-c1-20261012-analysis、docs/Git artifacts/representative-seed2-layout0-quality-c1-20261012-save、最終同-final/post-save優先。
- DATA artifacts/representative-anomaly-evaluation/dev-seed7466813550306735603-layout0-quality-c1-20261012/root-closed.json / {"bytes": 27554804, "files": 19, "manifest_pin": {"bytes": 2242, "sha256": "cca72d62fe1b6334143e7f99be84700bd7e8e908e3dbcdde53120875372de726"}}。analysis項目bytes/parts {"all-episodes": {"bytes": 37967, "parts": 1}, "analysis": {"bytes": 822124, "parts": 4}, "analysis.finished": {"bytes": 37, "parts": 1}, "analysis.started": {"bytes": 17, "parts": 1}, "data-closure": {"bytes": 135, "parts": 1}, "data-closure.finished": {"bytes": 37, "parts": 1}, "data-closure.started": {"bytes": 17, "parts": 1}, "helper-execution": {"bytes": 267, "parts": 1}, "helper-live": {"bytes": 213, "parts": 1}, "incident-ledger": {"bytes": 33910, "parts": 1}, "matched-targets": {"bytes": 62768, "parts": 1}, "non-ok-input-records": {"bytes": 21891, "parts": 1}, "policy": {"bytes": 211, "parts": 1}, "script": {"bytes": 13719, "parts": 1}, "selected-windows": {"bytes": 1004863, "parts": 4}, "unavailable-scores": {"bytes": 517849, "parts": 2}}。
- EvidenceStore16MiB512files/part256KiB/失敗2MiB16files・閉鎖512KiB4files予備枠と全write preflight維持。旧374root/352helpers21failed331passedmissingexecution1保持、原C1builder error/template/trace・C0誤記/analysis failure/foregroundcp932/console誤記保全。今回newbuilder/helperfailure0/closed-frozen root追記整理0。
- 実行900秒2GiBoutput1GiBsingle32MiBfiles32/Git累積30秒16entry512KiBstdout1MiBstderr128KiB/protocolnative不変。checkpoint≠blocking中断/fullruntime/global/allwriter容量証明。
- prepare_result_index実使用で3文書を同種合成dev結果・PC内pathのGitHub継続送信承認内で1回[skip ci] commit/push。原Git/HEAD-upstream-lsremote-clean/docpinsは-save/-final、追加確認0/bypass0。
- 次unit同seed/layout0 quality-stress C2、新ID dev-seed7466813550306735603-layout0-quality-c2-20261012。同manifest/input10、本文C1読取済み/次model未開始、元生成C0/次評価C2別field。新seed追加ではない。
- ACTIVE/automation詳細転記0。CI381385/4130保持query/download/verifier/tests0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了。create_native早期拒否・全7役reader禁止・caps-unknown原owner保持・追加agent禁止。未完了formal/nativeをdev開始条件へ戻さない。Sol容量/人停止は原保全後PAUSED、重複再試行なし。
