# 第2 dev seed・layout0 C0 quality実評価・6 cell比較（2026-10-12）

保存済み第2合成dev seed/layout0 quality-stressを既存CLI C0で1回fresh compute。機械0/10、センサー0/10、precision0/1、正常区間の誤警報1件。このseed/layoutの3候補×2strata=6cellsがそろった。処理exit0/complete/1cell successを性能保証・採択・正式受入にしない。

## 入力と実行の対応

- run dev-seed7466813550306735603-layout0-quality-c0-20261012、dataset anomaly-v03-dev-seed-7466813550306735603-layout-00-quality-stress。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\012\attempt-0001\result\payload\manifest.json / {"bytes": 75700, "sha256": "5060fceed11406c0393d8afd284cdbeb418df7052298c4dc97fdd7c887d32a0d"}。seed7466813550306735603/layout0/quality-stress/dev、同C1C2quality input10一致→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics保存。
- 元生成C0と実評価C0別field、元payload書込み・新dataset生成・replay・追加agent0。
- 実checkout 71ae1e9f79c07394196efa38488b2fc3300c2651、計算code661b27511826fcc87cb4a02930f276afbb8f95d9/science117/calculator16/candidate/compiled config不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 22.846715799998492秒、OS sampled private peak 151064576B。
- observations {"bytes": 9600492, "sha256": "380470273c84617da87cab7c37ffd3759891d24c947c86a934d35358d5a8ffb2"}、configuration {"bytes": 5513, "sha256": "d50e54429886455dc689f5b75f0437b7171c0cf1eadf3a4232ea818f5bb1dfd9"}、manifest {"bytes": 8086, "sha256": "2efbf561296b37a47673720496c01c97edac4f3c9f3b3cc47e3389ee36337ca4"}、evaluation {"bytes": 14333237, "sha256": "3bd6a5c4fb7bd2eda350ba2419f960ce0589ee067600db3732bd6e49aa3d1147"}。宣言pin≠full loaded runtime/native認証。
- C0閾値4/C1C2 6/operator>/persistence2、全score原threshold flags確認。GT/matching/science変更0。

## 原指標と利用不能

|項目|原値|
|---|---|
|機械 recall|0/10|
|センサー recall|0/10|
|precision|0/1|
|clean / unmatched|1 / 1|
|source / equipment / incidents / events|1 / 1 / 20 / 40|
|scores 利用可 / 不能|13880 / 520|

48profiles calibrated/fit各0（C0定義上no-op）/calibration各290/C2stateなし48。18000observations/mask対応non-ok30。phase480/current quality30/previous quality10排他的、全不能score-residual null・thresholdfalse。phase480＋own40−重複0=520。温度1700/1800・他7target1740/1800利用可。coreから40減/C1quality同数/C2qualityはpeer120追加。
全20delaynull、count0/minmaxmeanmedian原null、未検出へ補完0。clean_rate 1/3365 / 原value 8.558692421991084、effective 3255秒/rate 8.847926267281107、burden 1/20 / 原value 5.0。rate/burdenを単純確率へ読み替えない。

## 全20未検出と原欠測窓

全no_candidate_in_window/candidate0/causalfalse/matchednull/delaynull。機械10窓各6利用可1開始phase不能、cycle02/03最大streak0/他8最大1。sensor9窓は7全利用可/maxstreak1、cycle09温度は3利用可4不能/maxstreak1/phase0。どの対象も固定persistence2不成立。欠測1窓を全20missの説明へしない。
cycle09温度は異常[8827,8830)/windowend8833。8827score147.16689584643012/streak1→8828–30current quality欠測→8831previous quality/reset→8832/33閾値4未満。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|8827|True|147.16689584643012|1|None|
|8828|False|None|0|current_target_quality|
|8829|False|None|0|current_target_quality|
|8830|False|None|0|current_target_quality|
|8831|False|None|0|previous_target_quality_or_nonfinite|
|8832|True|0.8213620324246435|0|None|
|8833|True|0.8251597885995328|0|None|

唯一source/equipmentはclean tags/matchednull、原内訳 {"conveyor-01.motor_temperature": 1}、原support scoresは-save/episode-summaryへ保存。原全20event/incident/四target窓/episodes/520不能/non-ok30入力mask保存。入力対応・保存・分類の実経路不具合観測なし。
既存[一次差分とpersistence2の設計説明](anomaly-multiseed-v0.3-second-dev-seed-layout0-c0-core-evaluation-2026-10-12.md)を保持。一定3観測加算の内部成分は差分で相殺される。今回の原結果をあらゆる異常の検出不能証明にはしない。式監査再実行・正常対照再計算・閾値/GT変更・新candidate採択0。原four-sample誤記/analysis failure/threshold誤記/foregroundcp932/console誤記/前C1builder errorを保持。

## 同seed/layoutの3候補×2条件

|stratum|candidate|machine|sensor|precision|clean|unmatched|available|delay count / median秒|
|---|---|---|---|---|---|---|---|---|
|core|c0-diff-control|0/10|0/10|0/1|1|1|13920|0 / None|
|core|c1-phase-level|10/10|10/10|20/20|0|0|13920|20 / 1.5|
|core|c2-phase-conditional|5/10|10/10|15/20|0|5|13920|15 / 1.0|
|quality-stress|c0-diff-control|0/10|0/10|0/1|1|1|13880|0 / None|
|quality-stress|c1-phase-level|10/10|9/10|19/19|0|0|13880|19 / 2.0|
|quality-stress|c2-phase-conditional|5/10|9/10|14/19|0|5|13760|14 / 1.0|

同stratumはinput10全候補一致、core-quality共通origins/split-manifest/targets3・fingerprint差保持。6cellsは同合成devseed/layoutの候補・条件比較で6独立datasetではない。旧モデル再計算0/calculator16candidatecompiled一致。clean誤警報とmachine窓内の未対応equipmentを別原指標として保持。

## 保存済みC0 quality比較

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

第1seed/layout0–11と今回のC0quality13保存manifest指標。第1seed全72＋第2seed/layout0全6＝78boardcells/実使用seed2。第2seed残layouts未完成、78独立datasetではない。bootstrap/統計CI/勝者/採択0。

## 証拠・次unit・正式状態

- model artifacts/representative-seed2-layout0-quality-c0-20261012-records、analysis artifacts/representative-seed2-layout0-quality-c0-20261012-analysis、docs/Git artifacts/representative-seed2-layout0-quality-c0-20261012-save、最終同-final/post-save優先。
- DATA artifacts/representative-anomaly-evaluation/dev-seed7466813550306735603-layout0-quality-c0-20261012/root-closed.json / {"bytes": 27380167, "files": 19, "manifest_pin": {"bytes": 2242, "sha256": "ae2708eabce1d689ddfb4fa8977463e72be897546af46f0715b53283251c01dc"}}。analysis項目bytes/parts {"all-episodes": {"bytes": 1688, "parts": 1}, "analysis": {"bytes": 843407, "parts": 4}, "analysis.finished": {"bytes": 37, "parts": 1}, "analysis.started": {"bytes": 17, "parts": 1}, "data-closure": {"bytes": 135, "parts": 1}, "data-closure.finished": {"bytes": 37, "parts": 1}, "data-closure.started": {"bytes": 17, "parts": 1}, "helper-execution": {"bytes": 267, "parts": 1}, "helper-live": {"bytes": 213, "parts": 1}, "incident-ledger": {"bytes": 19749, "parts": 1}, "matched-targets": {"bytes": 190, "parts": 1}, "non-ok-input-records": {"bytes": 21892, "parts": 1}, "policy": {"bytes": 211, "parts": 1}, "script": {"bytes": 13737, "parts": 1}, "selected-windows": {"bytes": 949168, "parts": 4}, "unavailable-scores": {"bytes": 519410, "parts": 2}}。
- EvidenceStore16MiB512files/part256KiB/失敗2MiB16files・閉鎖512KiB4files予備枠と全write preflight維持。旧384root/360helpers21failed339passedmissingexecution1保持、原失敗を新successへ書換えず、今回newbuilder/helperfailure0/closed-frozen root追記整理0。
- 実行900秒2GiBoutput1GiBsingle32MiBfiles32/Git累積30秒16entry512KiBstdout1MiBstderr128KiB/protocolnative不変。checkpoint≠blocking中断/fullruntime/global/allwriter容量証明。
- prepare_result_index実使用で3文書を同種合成dev結果・PC内pathのGitHub継続送信承認内で1回[skip ci] commit/push。原Git/HEAD-upstream-lsremote-clean/docpinsは-save/-final、追加確認0/bypass0。
- 次unit 保存済みchunk013 dev/core seed7466813550306735603/layout1 C0、新ID dev-seed7466813550306735603-layout1-core-c0-20261012。manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\013\attempt-0001\result\payload\manifest.json / {"bytes": 75699, "sha256": "d4743f431240dee56e5ead1d0709a998e502b6a7e8a4aecd3f00468dced8bd81"}。identity/input10 metadataだけ選択、観測本文未読/次model未開始。新独立seed選択=False。 原nextmanifest bytesを-save/next-input-manifestへ保存。
- ACTIVE/automation詳細転記0。CI381385/4130保持query/download/verifier/tests0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了。create_native早期拒否・全7役reader禁止・caps-unknown原owner保持・追加agent禁止。未完了formal/nativeをdev開始条件へ戻さない。Sol容量/人停止は原保全後PAUSED、重複再試行なし。
