# 第2 dev seed・layout0 C2 core実評価・3候補比較（2026-10-12）

保存済み第2合成dev seed/layout0 coreを既存CLI C2で1回fresh compute。機械5/10、センサー10/10、precision15/20、正常区間の誤警報0件、未対応equipment5件。処理exit0/complete/1cell successを性能保証・採択・正式受入にしない。

## 入力と実行の対応

- run dev-seed7466813550306735603-layout0-core-c2-20261012、dataset anomaly-v03-dev-seed-7466813550306735603-layout-00-core。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\012\attempt-0001\result\payload\manifest.json / {"bytes": 75700, "sha256": "5060fceed11406c0393d8afd284cdbeb418df7052298c4dc97fdd7c887d32a0d"}。seed7466813550306735603/layout0/core/dev、同C0/C1 input10完全一致→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics。
- 元生成C0と実評価C2別field。元payload書込み・新dataset生成・replay・追加agent0。
- 実checkout fd5228270156ea345b2ae75f4e174213868fef2b、計算code661b27511826fcc87cb4a02930f276afbb8f95d9/science117/calculator16/candidate/compiled config不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 27.26882629992906秒、OS sampled private peak 209055744B。
- observations {"bytes": 9600489, "sha256": "79ba639be4e09f307cd7d4ba4ba63b0b60dd348c64b8e60e44c7f5ca6443ea18"}、configuration {"bytes": 5508, "sha256": "baa304f1f36016a56a36e034b06c060a54afdaf076ecb58dc881f65a2670ca0d"}、manifest {"bytes": 8048, "sha256": "b1458399cba2a9e6c72d9904cce9a27e9a2799cf02e0cb00d3fb3600d23ec004"}、evaluation {"bytes": 24741773, "sha256": "79b6c31387b82d46750d4ac21a40d8a7d86929d5a548c5913e0b060a437d5289"}。宣言pin≠full loaded runtime/native認証。
- C2閾値6/C0 4/C1 6/operator>/persistence2、全score原threshold flags確認。GT/matching/science変更0。

## 原指標と利用不能

|項目|原値|
|---|---|
|機械 recall|5/10|
|センサー recall|10/10|
|precision|15/20|
|clean / unmatched|0 / 5|
|source / equipment / incidents / events|37 / 20 / 20 / 40|
|scores 利用可 / 不能|13920 / 480|

48profiles全calibrated/fit各600/calibration各290/C2state48。18000observations/mask対応non-ok0、全480不能はmode_recipe_or_phase/score-residual null/thresholdfalse。各8target1740/1800利用可。
検出15件だけdelaycount15/min1/max2/mean1.3333333333333333/median1秒。機械5は2秒・sensor10は1秒、未検出5delaynullを補完しない。clean_rate 0/3365 / 原value 0.0、effective 3255秒/rate 0.0、false_alert_burden 5/20 / 原value 25.0。burden5/20の原25.0を単純確率へ読み替えない。

## 原15検出と機械5未検出

全15検出はcausal_detected/candidate1/event-target-source-equipment/support2score一致。support全30score原利用可・対象一致・score>6。source37は全20equipment内参照、原内訳 {"motor-01.vibration_feature": 12, "motor-01.motor_current": 15, "motor-01.motor_temperature": 10}、matched membership {"machine": {"motor-01.motor_current": 5, "motor-01.vibration_feature": 5}, "sensor": {"motor-01.motor_current": 10, "motor-01.motor_temperature": 10, "motor-01.vibration_feature": 2}}。source37をequipment37や誤警報37へしない。
未検出はmachine cycle00/03/04/05/07、対象motor-01.motor_current。全first_candidate_no_target_onset/candidate1/causalfalse/matchednull/delaynull。最初のequipment候補はあるが対象電流source onsetがなく、固定first-equipment-onset-no-retry-v1で未検出となった。

|miss cycle|候補source targets|target max score|target max streak|
|---|---|---|---|
|0|motor-01.vibration_feature|6.050001922357545|1|
|3|motor-01.vibration_feature|6.526359904986536|1|
|4|motor-01.vibration_feature|6.658500552098015|1|
|5|motor-01.vibration_feature|6.609399623260634|1|
|7|motor-01.vibration_feature|6.63534867544003|1|

全machine窓は6利用可/開始1phase不能。検出5は最大streak2、未検出5は最大1。sensor10窓は7全利用可/maxstreak3。未対応equipment5はmachine窓内でclean tagsがなく、正常区間の誤警報0とは別指標。全20原ledger/四target窓/episodes/480不能、5miss原候補とtarget窓を保存した。

### cycle0 machine / motor-01.motor_current

異常区間[7200,7203)、windowend 7206。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7200|False|None|0|mode_recipe_or_phase|
|7201|True|5.710824301246947|0|None|
|7202|True|6.050001922357545|1|None|
|7203|True|1.4954057717506408|0|None|
|7204|True|0.1318995462952832|0|None|
|7205|True|0.621184266952681|0|None|
|7206|True|0.2249271077978829|0|None|

### cycle0 sensor / motor-01.motor_temperature

異常区間[7207,7210)、windowend 7213。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7207|True|164.13068589085654|1|None|
|7208|True|164.82918434200442|2|None|
|7209|True|165.44919757811283|3|None|
|7210|True|0.25189677188424386|0|None|
|7211|True|1.6261941078704814|0|None|
|7212|True|0.36953156398243303|0|None|
|7213|True|0.26175005434508314|0|None|

### cycle1 machine / motor-01.motor_current

異常区間[7380,7383)、windowend 7386。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7380|False|None|0|mode_recipe_or_phase|
|7381|True|6.733114766497357|1|None|
|7382|True|6.756337930044082|2|None|
|7383|True|0.8075881695184628|0|None|
|7384|True|0.5297998064744927|0|None|
|7385|True|0.5144763252907204|0|None|
|7386|True|1.0220007633023922|0|None|

### cycle1 sensor / motor-01.motor_temperature

異常区間[7387,7390)、windowend 7393。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7387|True|166.2088921107904|1|None|
|7388|True|165.57346287389544|2|None|
|7389|True|166.17738659959983|3|None|
|7390|True|0.9907160730372683|0|None|
|7391|True|0.7561997741444284|0|None|
|7392|True|1.2449600758245645|0|None|
|7393|True|1.4557689983719033|0|None|

入力対応・保存・状態分類の実経路不具合は観測なし。未検出を閾値/GT/matching変更で成功へ補わない。

## 同入力3候補と保存済みC2比較

|candidate|machine|sensor|precision|clean|unmatched|
|---|---|---|---|---|---|
|c0-diff-control|0/10|0/10|0/1|1|1|
|c1-phase-level|10/10|10/10|20/20|0|0|
|c2-phase-conditional|5/10|10/10|15/20|0|5|

同第2seed/layout0/core/input10完全一致。C0/C1原指標を保存manifestだけから比較し、旧model再compute0。C0の一次差分と一定3観測の説明/旧誤記を保持し、3候補を3独立datasetに数えない。

|seed|layout|machine|sensor|precision|clean|
|---|---|---|---|---|---|
|2486912926863618161|0|4/10|10/10|14/20|0|
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
|7466813550306735603|0|5/10|10/10|15/20|0|

第1seed/layout0–11 C2core＋今回第2seed/layout0 C2coreの13保存指標。source16/candidatecompiled一致/input差保持。第1seed全72cells＋第2seed core3cells＝board75cells/実使用seed2、第2seed quality/残layouts未完了。75独立datasetではない。bootstrap/統計CI/勝者/採択0。

## 証拠・次unit・正式状態

- model artifacts/representative-seed2-layout0-core-c2-20261012-records、analysis artifacts/representative-seed2-layout0-core-c2-20261012-analysis、docs/Git artifacts/representative-seed2-layout0-core-c2-20261012-save、最終同-final/post-save優先。
- DATA artifacts/representative-anomaly-evaluation/dev-seed7466813550306735603-layout0-core-c2-20261012/root-closed.json / {"bytes": 37782327, "files": 19, "manifest_pin": {"bytes": 2232, "sha256": "6e07b2b42bac52809c732208381b3952fb2ac8b6a90a3dcef19706f9e084c397"}}。analysis項目bytes/parts {"all-episodes": {"bytes": 44686, "parts": 1}, "analysis": {"bytes": 811294, "parts": 4}, "analysis.finished": {"bytes": 37, "parts": 1}, "analysis.started": {"bytes": 17, "parts": 1}, "data-closure": {"bytes": 135, "parts": 1}, "data-closure.finished": {"bytes": 37, "parts": 1}, "data-closure.started": {"bytes": 17, "parts": 1}, "helper-execution": {"bytes": 268, "parts": 1}, "helper-live": {"bytes": 213, "parts": 1}, "incident-ledger": {"bytes": 31479, "parts": 1}, "matched-targets": {"bytes": 49497, "parts": 1}, "non-ok-input-records": {"bytes": 195, "parts": 1}, "policy": {"bytes": 211, "parts": 1}, "script": {"bytes": 13454, "parts": 1}, "selected-windows": {"bytes": 1678045, "parts": 7}, "unavailable-scores": {"bytes": 816330, "parts": 4}}。
- EvidenceStore16MiB512files/part256KiB/失敗2MiB16files・閉鎖512KiB4files予備枠、全write preflight。旧369root/348helpers21failed327passedmissingexecution1保持、過去C1 source-builder scope errorと原template/trace/失敗式、C0誤記/analysis failure/foregroundcp932/console誤記を保持。今回新builder/helper失敗0、閉鎖root追記整理0。
- 実行900秒2GiBoutput1GiBsingle32MiBfiles32/Git累積30秒16entry512KiBstdout1MiBstderr128KiB/protocolnative不変。checkpoint≠blocking中断/fullruntime/global/allwriter容量証明。
- prepare_result_index実使用で3文書を同種合成dev結果・PC内pathのGitHub継続送信承認内で1回[skip ci] commit/push。原Git/HEAD-upstream-lsremote-clean/docpinsは-save/-final、追加確認0/bypass0。
- 次unit同seed/layout0 quality-stress C1、新ID dev-seed7466813550306735603-layout0-quality-c1-20261012。同manifestのquality identity/input10 metadataだけ選択、観測本文未読/次model未開始。元生成C0/次評価C1別field、新seed追加ではない。
- ACTIVE/automation詳細転記0。CI381385/4130保持query/download/verifier/tests0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了。create_native早期拒否・全7役reader禁止・caps-unknown原owner保持・追加agent禁止。未完了formal/nativeをdev開始条件へ戻さない。Sol容量/人停止は原保全後PAUSED、重複再試行なし。
