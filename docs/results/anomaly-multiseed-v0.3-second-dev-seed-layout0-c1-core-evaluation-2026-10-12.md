# 第2 dev seed・layout0 C1 core実評価（2026-10-12）

保存済み第2合成dev seed/layout0 coreを既存CLI C1で1回fresh compute。機械10/10、センサー10/10、precision20/20、正常区間の誤警報0件。処理exit0/complete/1cell successを性能保証・採択・正式受入にしない。

## 入力と実行の対応

- run dev-seed7466813550306735603-layout0-core-c1-20261012、dataset anomaly-v03-dev-seed-7466813550306735603-layout-00-core。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\012\attempt-0001\result\payload\manifest.json / {"bytes": 75700, "sha256": "5060fceed11406c0393d8afd284cdbeb418df7052298c4dc97fdd7c887d32a0d"}。seed7466813550306735603/layout0/core/dev、同C0 input10完全一致→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics保存。
- 元生成C0と実評価C1は別field。元payload書込み・新dataset生成・replay・追加agent0。
- 実checkout 57e523e8e2585c70f7fc01f7b56e49dc676a35a3、計算code661b27511826fcc87cb4a02930f276afbb8f95d9・science117/calculator16/candidate/compiled config不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 17.657240600092337秒、OS sampled private peak 151076864B。
- observations {"bytes": 9600489, "sha256": "79ba639be4e09f307cd7d4ba4ba63b0b60dd348c64b8e60e44c7f5ca6443ea18"}、configuration {"bytes": 5502, "sha256": "0f4a61ee74cdc7ef36e64a682eba022e4ce9b77449c9e14219eb5dba647826c2"}、manifest {"bytes": 8027, "sha256": "7e9377bf10e88737c970ddf71a42f4f23e0b370b2a0c51784ebf39cc3629972a"}、evaluation {"bytes": 14069689, "sha256": "ab93575b8776b0432c278213b63afdc739047626396c186641b266fdefeb2939"}。宣言source pin≠full loaded runtime/native認証。
- C1 threshold6.0/C0 4.0/C2 6.0/operator>/persistence2、全score原threshold flags確認。GT/matching/science変更0。

## 原指標と利用不能

|項目|原値|
|---|---|
|機械 recall|10/10|
|センサー recall|10/10|
|precision|20/20|
|clean / unmatched|0 / 0|
|source / equipment / incidents / events|30 / 20 / 20 / 40|
|scores 利用可 / 不能|13920 / 480|

48profiles全calibrated、fit_samples各600/calibration各290/C2stateなし48。18000observationsとquality-mask対応/non-ok0、全480不能mode_recipe_or_phase/score-residual null/thresholdfalse。各8target1740/1800利用可。
検出20だけdelaycount20、min1/max2/mean-median1.5秒。クラス別原delay {"machine": {"2.0": 10}, "sensor": {"1.0": 10}}。clean_rate 0/3365 / 原value 0.0、effective 3255秒/rate 0.0、burden 0/20 / 原value 0.0。未検出delayの補完0、rate/burdenを単純確率へ読み替えない。

## 原20検出の対応

全20causal_detected/candidate1。原event-target-source-equipment/support2scoreを照合し、support全40scoreは原利用可・対象一致・閾値6超過。機械10のsource onsetはstart+2秒、センサー10はstart+1秒。全source30は20matched equipment内参照、未参照0。source内訳 {"motor-01.motor_current": 10, "motor-01.vibration_feature": 10, "motor-01.motor_temperature": 10}、クラス別membership {"machine": {"motor-01.motor_current": 10, "motor-01.vibration_feature": 10}, "sensor": {"motor-01.motor_temperature": 10}}。source30をequipment30や誤警報30へしない。
機械10窓は6利用可/開始1phase不能/maxstreak2、センサー10窓は7全利用可/maxstreak3。開始不能により機械は次2観測でepisode、センサーは開始から2観測でepisode成立。原スコアを下に示す。

### cycle0 machine / motor-01.motor_current

異常区間[7200,7203)、windowend 7206。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7200|False|None|0|mode_recipe_or_phase|
|7201|True|7.280784693834243|1|None|
|7202|True|7.617059648755455|2|None|
|7203|True|1.377841747477024|0|None|
|7204|True|0.2702126615487694|0|None|
|7205|True|0.5066263516316913|0|None|
|7206|True|0.34500437392633454|0|None|

### cycle0 sensor / motor-01.motor_temperature

異常区間[7207,7210)、windowend 7213。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7207|True|156.4058807785043|1|None|
|7208|True|156.91693885028286|2|None|
|7209|True|157.4273757486834|3|None|
|7210|True|0.19130661054328565|0|None|
|7211|True|1.7373775683909436|0|None|
|7212|True|0.3841365748467117|0|None|
|7213|True|0.31906126859316447|0|None|

### cycle2 machine / motor-01.motor_current

異常区間[7560,7563)、windowend 7566。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7560|False|None|0|mode_recipe_or_phase|
|7561|True|7.95951243670283|1|None|
|7562|True|7.892666169272409|2|None|
|7563|True|1.4539665093763925|0|None|
|7564|True|0.23587048708394567|0|None|
|7565|True|0.8351202906216625|0|None|
|7566|True|1.4776736499910457|0|None|

### cycle2 sensor / motor-01.motor_temperature

異常区間[7567,7570)、windowend 7573。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7567|True|156.64293237137557|1|None|
|7568|True|156.01937289893735|2|None|
|7569|True|156.09445599850122|3|None|
|7570|True|1.8204964822875949|0|None|
|7571|True|1.9394265344136175|0|None|
|7572|True|2.6978792287995983|0|None|
|7573|True|1.1450049434801226|0|None|

原全20event/incident・四target窓・全480不能・全episodesを-analysisへ、全matched target/support原対応を-save/target-onset-summaryへ保存。入力対応・保存・状態分類の実経路不具合は観測なし。

## 同入力C0と保存済みC1比較

|候補|machine|sensor|precision|clean|
|---|---|---|---|---|
|C0|0/10|0/10|0/1|1|
|C1|10/10|10/10|20/20|0|

同第2seed/layout0/coreの同input10。C0の原delaycount0/nullを保持し再計算0。C0の一次差分とpersistence2に関する[既存報告](anomaly-multiseed-v0.3-second-dev-seed-layout0-c0-core-evaluation-2026-10-12.md)を保持し、候補追加を新独立datasetに数えない。

|seed|layout|machine|sensor|precision|clean|
|---|---|---|---|---|---|
|2486912926863618161|0|10/10|10/10|20/20|0|
|2486912926863618161|1|10/10|10/10|20/20|0|
|2486912926863618161|2|10/10|10/10|20/20|0|
|2486912926863618161|3|10/10|10/10|20/20|0|
|2486912926863618161|4|10/10|10/10|20/20|0|
|2486912926863618161|5|10/10|10/10|20/20|0|
|2486912926863618161|6|0/10|10/10|10/20|0|
|2486912926863618161|7|10/10|10/10|20/20|0|
|2486912926863618161|8|10/10|10/10|20/20|0|
|2486912926863618161|9|10/10|10/10|20/20|0|
|2486912926863618161|10|10/10|10/10|20/20|0|
|2486912926863618161|11|10/10|10/10|20/20|0|
|7466813550306735603|0|10/10|10/10|20/20|0|

以上は第1seed/layout0–11 C1coreと今回第2seed/layout0 C1coreの保存manifest指標13cells。旧モデル再計算0/source16candidatecompiled一致/input差保持。第1seed全72cells＋第2seed C0/C1core2cells＝board74cells/実使用seed2。第2seed C2/quality/残layoutsは未完了。74独立datasetではない。bootstrap/統計CI/勝者/採択0。

## 証拠・次unit・正式状態

- model artifacts/representative-seed2-layout0-core-c1-20261012-records、analysis artifacts/representative-seed2-layout0-core-c1-20261012-analysis、docs/Git artifacts/representative-seed2-layout0-core-c1-20261012-save、最終同-final/post-save優先。
- DATA artifacts/representative-anomaly-evaluation/dev-seed7466813550306735603-layout0-core-c1-20261012/root-closed.json / {"bytes": 27110182, "files": 19, "manifest_pin": {"bytes": 2232, "sha256": "38af2e26e37fea19fffc968dc395ff2a65464954e99547410d6f8594cd0b8f86"}}。analysis項目bytes/parts {"all-episodes": {"bytes": 37273, "parts": 1}, "analysis": {"bytes": 800659, "parts": 4}, "analysis.finished": {"bytes": 37, "parts": 1}, "analysis.started": {"bytes": 17, "parts": 1}, "builder-original-template": {"bytes": 13161, "parts": 1}, "data-closure": {"bytes": 135, "parts": 1}, "data-closure.finished": {"bytes": 37, "parts": 1}, "data-closure.started": {"bytes": 17, "parts": 1}, "helper-execution": {"bytes": 268, "parts": 1}, "helper-live": {"bytes": 213, "parts": 1}, "incident-ledger": {"bytes": 33068, "parts": 1}, "matched-targets": {"bytes": 62728, "parts": 1}, "non-ok-input-records": {"bytes": 189, "parts": 1}, "policy": {"bytes": 211, "parts": 1}, "script": {"bytes": 13438, "parts": 1}, "selected-windows": {"bytes": 972643, "parts": 4}, "source-builder-failure": {"bytes": 846, "parts": 1}, "unavailable-scores": {"bytes": 461952, "parts": 2}}。
- 補助sourceの生成時、C0 profile keyの置換は1箇所を期待したがJSONとconsoleの2箇所に一致し、foreground JS scope errorになった。nested tools/process/追跡変更0。元template・式・原selected traceを-analysisへ保存し、JSON keyとconsole keyへ限定して別sourceを生成した。モデル再実行0/helper failure/CI/native/Sol失敗へしない。
- EvidenceStore16MiB512files/part256KiB/失敗2MiB16files・閉鎖512KiB4files予備枠、全write preflight。旧364root/344helpers21failed323passedmissingexecution1保持。closed/frozen root追記整理0/fullstdio/native回収claim0。
- 実行900秒2GiBoutput1GiBsingle32MiBfiles32/Git累積30秒16entry512KiBstdout1MiBstderr128KiB/protocolnative不変。checkpoint≠blocking中断/fullruntime/global/allwriter容量証明。
- prepare_result_index実使用でreport/handoff/index3文書を同種合成dev結果・PC内pathのGitHub継続送信承認内で1回[skip ci] commit/push。原Git/HEAD-upstream-lsremote-clean/docpinsは-save/-final、追加確認0/bypass0。
- 次は同seed/layout0/core C2 c2-phase-conditional、新ID dev-seed7466813550306735603-layout0-core-c2-20261012。同manifest/input10、本文C0/C1読取済み/次model未開始。元生成C0/次評価C2別field、新独立seed追加ではない。
- ACTIVE/automation詳細転記0。CI381385/4130保持、CIquery/download/verifier/tests0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了。create_native早期拒否・全7役reader禁止・caps-unknown原owner保持・追加agent禁止。未完了formal/nativeをdev開始条件へ戻さない。Sol容量/人停止は原保全後PAUSED、重複再試行なし。
