# 第2 dev seed・layout0 C0 core実評価（2026-10-12）

保存済み第2合成dev seedのlayout0 coreを既存CLI C0で1回fresh compute。機械0/10、センサー0/10、precision0/1、正常区間の誤警報1件。処理exit0/complete/1cell successを性能合格・採択・正式受入にしない。

## 入力と実行の対応

- run dev-seed7466813550306735603-layout0-core-c0-20261012、dataset anomaly-v03-dev-seed-7466813550306735603-layout-00-core。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\012\attempt-0001\result\payload\manifest.json / {"bytes": 75700, "sha256": "5060fceed11406c0393d8afd284cdbeb418df7052298c4dc97fdd7c887d32a0d"}。seed7466813550306735603/layout0/core/dev、10入力pin照合→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics保存。
- 元生成C0と実評価C0を別field保持。元payload書込み・新dataset生成・replay・追加agent0。観測本文は今回C0で初めて使用。
- 実checkout 6215506aa610bdbd15430262a80fe20725a64e82、計算code661b27511826fcc87cb4a02930f276afbb8f95d9・science117/calculator16/candidate/compiled config不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 22.28538369992748秒、OS sampled private peak 149995520B。
- observations {"bytes": 9600489, "sha256": "79ba639be4e09f307cd7d4ba4ba63b0b60dd348c64b8e60e44c7f5ca6443ea18"}、configuration {"bytes": 5503, "sha256": "617059c34a187d0dfebb64d8faff158c400e73a2b00c82a992b970e362bfa66f"}、manifest {"bytes": 8052, "sha256": "6f6f534f630f722129c407db5b1b02c11476b7398391cc1fbe50ad4930f7bf30"}、evaluation {"bytes": 13896268, "sha256": "9d29caa45e72517293709552f239a88f96801db3bf4343f20a50ef80d6f7477c"}。declared pin≠full loaded runtime/native認証。
- C0 threshold4.0/C1C2 6.0/operator>/persistence2、全score原threshold flag確認。GT/matching/science変更0。

## 原指標

|項目|原値|
|---|---|
|機械 recall|0/10|
|センサー recall|0/10|
|precision|0/1|
|clean / unmatched|1 / 1|
|source / equipment / incidents / events|1 / 1 / 20 / 40|
|scores 利用可 / 不能|13920 / 480|

48profiles全calibrated、fit_samples各0（C0定義上no-op）/calibration各290/C2stateなし48。18000observationsとquality-mask対応、non-ok0。全480不能はmode_recipe_or_phase、score/residual null・thresholdfalse。各8targetは1740/1800利用可。
全20missのdelayはnull、delaycount0/min/max/mean/medianすべて原null。検出遅延を未検出へ補完しない。clean_rate 1/3365 / 原value 8.558692421991084、effective 3255秒 / rate 8.847926267281107、burden 1/20 / 原value 5.0。rate/burdenを単純確率へ読み替えない。

## 未検出20件の原窓

全no_candidate_in_window/candidate0/causalfalse/matchednull/delaynull。機械10窓は各6利用可/開始1phase不能。cycle02/03最大streak0、他8件最大1。センサー10窓は各7rows全利用可/maxstreak1。固定persistence2が成立していない。phase不能は全20missの唯一の理由ではない。

### cycle0 machine / motor-01.motor_current

異常区間[7200,7203)、windowend 7206。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7200|False|None|0|mode_recipe_or_phase|
|7201|True|0.2824378788854591|0|None|
|7202|True|0.32681265641834484|0|None|
|7203|True|5.587219523868585|1|None|
|7204|True|1.070066377812133|0|None|
|7205|True|0.5809258196562641|0|None|
|7206|True|0.3530464331344378|0|None|

### cycle0 sensor / motor-01.motor_temperature

異常区間[7207,7210)、windowend 7213。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7207|True|147.18179046089153|1|None|
|7208|True|0.07114771994919825|0|None|
|7209|True|0.08782079583889192|0|None|
|7210|True|148.43067794758707|1|None|
|7211|True|1.5333208985533413|0|None|
|7212|True|0.8477795948898663|0|None|
|7213|True|0.061718169251513855|0|None|

### cycle9 machine / motor-01.motor_current

異常区間[8820,8823)、windowend 8826。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|8820|False|None|0|mode_recipe_or_phase|
|8821|True|0.7297303632960043|0|None|
|8822|True|0.5623380683147124|0|None|
|8823|True|6.219825590704386|1|None|
|8824|True|0.34773669329100715|0|None|
|8825|True|1.369960484169061|0|None|
|8826|True|0.2566362051359344|0|None|

### cycle9 sensor / motor-01.motor_temperature

異常区間[8827,8830)、windowend 8833。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|8827|True|147.16689584643012|1|None|
|8828|True|0.22698540259794736|0|None|
|8829|True|0.29147315501121634|0|None|
|8830|True|148.67399370173695|1|None|
|8831|True|0.30935039749292886|0|None|
|8832|True|0.8213620324246435|0|None|
|8833|True|0.8251597885995328|0|None|

原20event/incident・全4target窓・全480不能・全episodesを-analysisへ保存。唯一equipmentはclean tags/matchednullで、原sourceとsupport scoresを-save/episode-summaryへ保存。原source内訳 {"conveyor-01.motor_temperature": 1}。入力対応・保存・状態分類の実経路不具合は観測なし。

## C0の設計との関係

既存[設計確認](anomaly-multiseed-v0.3-layout10-c0-core-evaluation-2026-10-12.md)の一次差分とpersistence2の説明を保持。一定加算の3観測[start,end)では加算成分の差分は境界に現れ、内部で相殺される。今回もセンサー窓では2連続超過がない。これは原窓と既存式からの説明で、あらゆる異常を検出不能とする証明ではない。機械側の乗算異常を加算の例と同一にしない。
旧four-sample誤記・初回analysis failure・C0閾値6という旧説明・foregroundcp932・console next_layout誤記は原証拠保存。訂正版は3観測/end-exclusive/C0threshold4。設計監査や正常対照の再計算、閾値/GT変更、新candidate採択0。

## 保存済みC0 coreとの比較

以下は第1seed/layout0–11 C0coreと今回第2seed/layout0の保存manifest原指標。計算source16/candidate/compiled config一致、input pinsはseed/layoutで異なる。旧モデル再計算0。

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

第1seedの12layouts×3候補×2strata=72cells完成を保持。今回第2seedでC0core1cellだけを追加し、board73cells/実使用seed2。第2seedの候補比較や全layoutsは未完成。73独立datasetではなく、2seedがあるだけで統計的な保証にもならない。bootstrap/統計CI/勝者/採択0。

## 証拠・次unit・正式状態

- model artifacts/representative-seed2-layout0-core-c0-20261012-records、analysis artifacts/representative-seed2-layout0-core-c0-20261012-analysis、docs/Git artifacts/representative-seed2-layout0-core-c0-20261012-save、最終同-final/post-save優先。
- DATA artifacts/representative-anomaly-evaluation/dev-seed7466813550306735603-layout0-core-c0-20261012/root-closed.json / {"bytes": 26936815, "files": 19, "manifest_pin": {"bytes": 2232, "sha256": "31fc3c02f03149aed1910a3822e80c4c420dc9c41a99383f57aa488a98c4f3e4"}}。analysis項目のbytes/parts {"all-episodes": {"bytes": 1608, "parts": 1}, "analysis": {"bytes": 790340, "parts": 4}, "analysis.finished": {"bytes": 37, "parts": 1}, "analysis.started": {"bytes": 17, "parts": 1}, "data-closure": {"bytes": 135, "parts": 1}, "data-closure.finished": {"bytes": 37, "parts": 1}, "data-closure.started": {"bytes": 17, "parts": 1}, "helper-execution": {"bytes": 268, "parts": 1}, "helper-live": {"bytes": 213, "parts": 1}, "incident-ledger": {"bytes": 19349, "parts": 1}, "matched-targets": {"bytes": 190, "parts": 1}, "non-ok-input-records": {"bytes": 190, "parts": 1}, "policy": {"bytes": 211, "parts": 1}, "script": {"bytes": 13161, "parts": 1}, "selected-windows": {"bytes": 918240, "parts": 4}, "unavailable-scores": {"bytes": 463393, "parts": 2}}。
- EvidenceStore16MiB512files/part256KiB/失敗2MiB16files・閉鎖512KiB4files予備枠、全write preflight。旧359root count-byte-closure/340helpers21failed319passedmissingexecution1保持。closed/frozen root追記整理0/fullstdio/native回収claim0。
- 実行900秒2GiBoutput1GiBsingle32MiBfiles32、Git累積30秒16entry512KiBstdout1MiBstderr128KiB、protocol/native不変。checkpoint≠blocking中断/fullruntime/global/allwriter容量証明。
- prepare_result_indexを実使用しreport/handoff/index3文書を同種合成dev結果・PC内pathのGitHub継続送信承認内で1回[skip ci] commit/push。原Git/HEAD-upstream-lsremote-clean/docpinsは-save/-final。追加承認質問0/bypass0。
- 次は同seed/layout0/core C1 c1-phase-level、新ID dev-seed7466813550306735603-layout0-core-c1-20261012。同manifest/input10、本文は今回C0読取済み、次model未開始。元生成C0/次評価C1別field、新seed追加ではない。
- ACTIVE/automation詳細転記0。CI381385/4130保持、CIquery/download/verifier/tests0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読/正式5残件・最終受入未完了。create_native早期拒否・全7役reader禁止・caps-unknown原owner保持・追加agent禁止。未完了formal/nativeをdev開始条件へ戻さない。Sol容量/人停止は原保全後PAUSED、重複再試行なし。
