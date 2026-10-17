# 第2 dev seed・layout1 C0 core実評価（2026-10-12）

保存済み第2合成dev seed/layout1 coreを既存CLI C0で1回fresh compute。機械0/10、センサー0/10、precision0/1、正常区間の誤警報1件。処理exit0/complete/1cell successを性能保証・採択・正式受入にしない。

## 入力と実行の対応

- run dev-seed7466813550306735603-layout1-core-c0-20261012、dataset anomaly-v03-dev-seed-7466813550306735603-layout-01-core。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\013\attempt-0001\result\payload\manifest.json / {"bytes": 75699, "sha256": "d4743f431240dee56e5ead1d0709a998e502b6a7e8a4aecd3f00468dced8bd81"}。seed7466813550306735603/layout1/core/dev、10input pin→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics。
- 元生成C0と実評価C0別field、元payload書込み・新dataset生成・replay・追加agent0。
- 実checkout 887f045261373b614fa4925a9fce8ce1a68e8814、計算code661b27511826fcc87cb4a02930f276afbb8f95d9/science117/calculator16/candidate/compiled config不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 16.446173299918883秒、OS sampled private peak 149532672B。
- observations {"bytes": 9600485, "sha256": "5f1348946d4d32168c62eab56b3f23ca3e1293823c55c9641a2916ca555ebc73"}、configuration {"bytes": 5503, "sha256": "387d6a262acc1be57e152996a51f5b4e84ad9bfefc3c1cdf182fffe02a174a7f"}、manifest {"bytes": 8053, "sha256": "11c9f0c04a2e2336699d204c813595817668aa076e7d04fb06611e78b0332534"}、evaluation {"bytes": 13896138, "sha256": "b9e3f08cb467fb34f2074057dad15b8ab646865d115704f6ac50a23b3a06fed3"}。宣言pin≠full loaded runtime/native認証。
- C0閾値4/C1C2 6/operator>/persistence2、全score原threshold flags確認。GT/matching/science変更0。

## 原指標と利用不能

|項目|原値|
|---|---|
|機械 recall|0/10|
|センサー recall|0/10|
|precision|0/1|
|clean / unmatched|1 / 1|
|source / equipment / incidents / events|1 / 1 / 20 / 40|
|scores 利用可 / 不能|13920 / 480|

48profiles calibrated/fit各0（C0定義上no-op）/calibration各290/C2stateなし48。18000observations/mask対応non-ok0。全480不能はmode_recipe_or_phase/score-residual null/thresholdfalse、各8target1740/1800利用可。
全20delaynull、delaycount0/minmaxmeanmedian原null。未検出への補完0。clean_rate 1/3365 / 原value 8.558692421991084、effective 3255秒/rate 8.847926267281107、burden 1/20 / 原value 5.0。rate/burdenを単純確率へ読み替えない。

## 全20未検出の対象窓

全no_candidate_in_window/candidate0/causalfalse/matchednull/delaynull。全machine10・sensor10の対象matching窓は各7観測すべて利用可能/phase不能0、最大streak1。固定persistence2未成立。この20未検出を対象窓内の欠測やphase除外で説明できない。

### cycle0 machine / motor-01.motor_current

異常区間[7237,7240)、windowend 7243。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7237|True|21.85564691890034|1|None|
|7238|True|0.44566418013511394|0|None|
|7239|True|0.3599777800257367|0|None|
|7240|True|22.60970305645728|1|None|
|7241|True|0.44756217146194677|0|None|
|7242|True|1.5526913464028833|0|None|
|7243|True|1.4112119095817632|0|None|

### cycle0 sensor / motor-01.motor_temperature

異常区間[7244,7247)、windowend 7250。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7244|True|148.4267685947247|1|None|
|7245|True|0.09759336452919463|0|None|
|7246|True|0.75908529322452|0|None|
|7247|True|149.07045212524997|1|None|
|7248|True|0.9665094929755109|0|None|
|7249|True|0.9924514452630849|0|None|
|7250|True|0.7471635084224448|0|None|

### cycle1 machine / motor-01.motor_current

異常区間[7417,7420)、windowend 7423。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7417|True|21.694175306769903|1|None|
|7418|True|0.5441145719174598|0|None|
|7419|True|0.1364102183190269|0|None|
|7420|True|23.33762227178426|1|None|
|7421|True|0.414402681322711|0|None|
|7422|True|0.04276016293414031|0|None|
|7423|True|0.9265123744914294|0|None|

### cycle1 sensor / motor-01.motor_temperature

異常区間[7424,7427)、windowend 7430。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7424|True|148.45985990394186|1|None|
|7425|True|0.8986184567812397|0|None|
|7426|True|0.7503389370845351|0|None|
|7427|True|149.5725783885682|1|None|
|7428|True|1.112077827966347|0|None|
|7429|True|0.5396650296384742|0|None|
|7430|True|0.44837609803819445|0|None|

原全20event/incident/四target窓/episodes/480不能保存。唯一source/equipmentはclean tags/matchednull、原内訳 {"conveyor-01.motor_temperature": 1}。原support scoresは-save/episode-summary保存。入力対応・保存・状態分類の実経路不具合観測なし。
既存[一次差分とpersistence2の設計説明](anomaly-multiseed-v0.3-second-dev-seed-layout0-c0-core-evaluation-2026-10-12.md)を保持。一定3観測加算の内部成分は差分で相殺される。今回も原対象窓で2連続超過がないが、これをあらゆる異常の検出不能証明へしない。乗算machineを加算例と同一にしない。式監査再実行・正常対照再計算・閾値/GT変更・新candidate採択0。原four-sample誤記/analysis failure/threshold誤記/foregroundcp932/console誤記/前C1builder errorを保持。

## 保存済みC0 core比較

|seed|layout|machine|sensor|precision|clean|
|---|---|---|---|---|---|
|2486912926863618161|0|0/10|0/10|0/3|3|
|2486912926863618161|1|0/10|0/10|0/3|2|
|2486912926863618161|2|0/10|0/10|0/3|3|
|2486912926863618161|3|0/10|0/10|0/3|3|
|2486912926863618161|4|0/10|0/10|0/3|3|
|2486912926863618161|5|0/10|0/10|0/3|3|
|2486912926863618161|6|0/10|0/10|0/3|3|
|2486912926863618161|7|0/10|0/10|0/3|3|
|2486912926863618161|8|0/10|0/10|0/3|3|
|2486912926863618161|9|0/10|0/10|0/3|3|
|2486912926863618161|10|0/10|0/10|0/3|3|
|2486912926863618161|11|0/10|1/10|1/3|2|
|7466813550306735603|0|0/10|0/10|0/1|1|
|7466813550306735603|1|0/10|0/10|0/1|1|

第1seed/layout0–11と第2seed/layout0–1 C0coreの14保存manifest原指標。旧model再compute0/source16candidatecompiled一致/input差保持。第1seed全72＋第2seed/layout0全6＋今回1=79boardcells/実使用seed2。同seedのlayout差を新独立seedへ数えず、79独立datasetではない。layout1 C1C2/quality・残layouts未完成。bootstrap/統計CI/勝者/採択0。

## 証拠・次unit・正式状態

- model artifacts/representative-seed2-layout1-core-c0-20261012-records、analysis artifacts/representative-seed2-layout1-core-c0-20261012-analysis、docs/Git artifacts/representative-seed2-layout1-core-c0-20261012-save、最終同-final/post-save優先。
- DATA artifacts/representative-anomaly-evaluation/dev-seed7466813550306735603-layout1-core-c0-20261012/root-closed.json / {"bytes": 26936792, "files": 19, "manifest_pin": {"bytes": 2232, "sha256": "45a013e11571619f07f2ef161ee7a42e4ff892dd7abfb69eb48726ec9a4819f4"}}。analysis項目bytes/parts {"all-episodes": {"bytes": 1608, "parts": 1}, "analysis": {"bytes": 853676, "parts": 4}, "analysis.finished": {"bytes": 37, "parts": 1}, "analysis.started": {"bytes": 17, "parts": 1}, "data-closure": {"bytes": 135, "parts": 1}, "data-closure.finished": {"bytes": 37, "parts": 1}, "data-closure.started": {"bytes": 17, "parts": 1}, "helper-execution": {"bytes": 268, "parts": 1}, "helper-live": {"bytes": 213, "parts": 1}, "incident-ledger": {"bytes": 19369, "parts": 1}, "matched-targets": {"bytes": 190, "parts": 1}, "non-ok-input-records": {"bytes": 190, "parts": 1}, "policy": {"bytes": 211, "parts": 1}, "script": {"bytes": 13347, "parts": 1}, "selected-windows": {"bytes": 927546, "parts": 4}, "unavailable-scores": {"bytes": 463391, "parts": 2}}。
- EvidenceStore16MiB512files/part256KiB/失敗2MiB16files・閉鎖512KiB4files予備枠と全write preflight維持。旧389root/364helpers21failed343passedmissingexecution1保持、原失敗を新successへ書換えず、今回newbuilder/helperfailure0/closed-frozen root追記整理0。
- 実行900秒2GiBoutput1GiBsingle32MiBfiles32/Git累積30秒16entry512KiBstdout1MiBstderr128KiB/protocolnative不変。checkpoint≠blocking中断/fullruntime/global/allwriter容量証明。
- prepare_result_index実使用で3文書を同種合成dev結果・PC内pathのGitHub継続送信承認内で1回[skip ci] commit/push。原Git/HEAD-upstream-lsremote-clean/docpinsは-save/-final、追加確認0/bypass0。
- 次unit同seed/layout1 core C1、新ID dev-seed7466813550306735603-layout1-core-c1-20261012。同manifest/input10、本文今回C0読取済み/次model未開始、元生成C0/次評価C1別field、新独立seed追加ではない。
- ACTIVE/automation詳細転記0。CI381385/4130保持query/download/verifier/tests0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了。create_native早期拒否・全7役reader禁止・caps-unknown原owner保持・追加agent禁止。未完了formal/nativeをdev開始条件へ戻さない。Sol容量/人停止は原保全後PAUSED、重複再試行なし。
