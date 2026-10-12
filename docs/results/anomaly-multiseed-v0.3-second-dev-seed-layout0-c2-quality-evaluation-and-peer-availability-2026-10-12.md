# 第2 dev seed・layout0 C2 quality実評価・peer利用不能（2026-10-12）

保存済み第2合成dev seed/layout0 quality-stressを既存CLI C2で1回fresh compute。機械5/10、センサー9/10、precision14/19、正常区間の誤警報0件・未対応equipment5件。処理exit0/complete/1cell successを性能保証・採択・正式受入にしない。

## 入力と実行の対応

- run dev-seed7466813550306735603-layout0-quality-c2-20261012、dataset anomaly-v03-dev-seed-7466813550306735603-layout-00-quality-stress。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\012\attempt-0001\result\payload\manifest.json / {"bytes": 75700, "sha256": "5060fceed11406c0393d8afd284cdbeb418df7052298c4dc97fdd7c887d32a0d"}。seed7466813550306735603/layout0/quality-stress/dev、同C1quality input10完全一致→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics。
- 元生成C0と実評価C2別field、元payload書込み・新dataset生成・replay・追加agent0。
- 実checkout fb6b529956503bce932e0841bc3a2d9855aab172、計算code661b27511826fcc87cb4a02930f276afbb8f95d9/science117/calculator16/candidate/compiled config不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 33.32775010005571秒、OS sampled private peak 211550208B。
- observations {"bytes": 9600492, "sha256": "380470273c84617da87cab7c37ffd3759891d24c947c86a934d35358d5a8ffb2"}、configuration {"bytes": 5518, "sha256": "fd10e54426dc19e5868c2592f10fc7c6681742688d2e2383fb874729f145bbc2"}、manifest {"bytes": 8094, "sha256": "3967e1fbea32c6fab6467ba6c7f99fe81d86fa93bb09bbc39bdb671e455dd3bf"}、evaluation {"bytes": 25181829, "sha256": "4aad270e4cee2e3998a3f30b00dd9c1b0ba63058ee7205ab967ff21374a1959c"}。宣言pin≠full loaded runtime/native認証。
- C2閾値6/C0 4/C1 6/operator>/persistence2、全score原threshold flags確認。GT/matching/science変更0。

## 原指標とpeer利用不能

|項目|原値|
|---|---|
|機械 recall|5/10|
|センサー recall|9/10|
|precision|14/19|
|clean / unmatched|0 / 5|
|source / equipment / incidents / events|35 / 19 / 20 / 40|
|scores 利用可 / 不能|13760 / 640|

48profiles全calibrated/fit各600/calibration各290/C2state48、18000observations/mask対応non-ok30。排他的phase480/current quality30/previous quality10/peer120、全不能score/residual null・thresholdfalse。phase480＋own40＋peer120−重複0=640。tagsを独立行へ加算しない。
温度自身100不能（phase60＋own40）、同motor current/speed/vibrationも各100不能（phase60＋peer40）。peer内訳 {"motor-01.motor_current": 40, "motor-01.conveyor_speed": 40, "motor-01.vibration_feature": 40}。core13920/480から160減、同C1quality13880/520から120減。peer依存による不能を入力欠測30と独立に保持する。
検出14だけdelaycount14/min1/max2/mean1.3571428571428572/median1秒。machine5各2秒/sensor9各1秒、未検出6delaynull補完0。clean_rate 0/3365 / 原value 0.0、effective 3255秒/rate 0.0、burden 5/20 / 原value 25.0。burden5/20原25.0を単純確率へ読み替えない。

## sensor1未検出と欠測波及

cycle09 motor-01.motor_temperature、異常[8827,8830)/windowend8833。8827score166.92760890244307/streak1→8828–30current quality欠測→8831previous quality/reset→8832/33閾値6未満。窓3利用可4不能/maxstreak1/phase不能0、原no_candidate_in_window/candidate0/causalfalse/matchednull/delaynull。固定persistence2不成立。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|8827|True|166.92760890244307|1|None|
|8828|False|None|0|current_target_quality|
|8829|False|None|0|current_target_quality|
|8830|False|None|0|current_target_quality|
|8831|False|None|0|previous_target_quality_or_nonfinite|
|8832|True|1.2937188501560848|0|None|
|8833|True|1.9195223233070773|0|None|

同motorのcurrent/speed/vibrationは8828–8831の4観測ずつpeer不能、合計12原rows/全nullstreak0thresholdfalse。原peer120全rowsとmiss四target窓を保存。温度だけの40追加不能と他3targetのpeer120を混ぜない。

## 機械5未検出と原14検出

machine未検出cycle00/03/04/05/07は全first_candidate_no_target_onset/candidate1/causalfalse/matchednull/delaynull、coreと同じ。最初のequipment候補はmotor vibration sourceだけで対象current onsetなし。固定first-equipment-onset-no-retry-v1を保持し、後続を採り直して成功へ補わない。
全machine窓6利用可1開始phase不能、検出5最大streak2/未検出5最大1。sensor検出9窓7全利用可/maxstreak3。未対応equipment5はmachine窓内/clean tagsなし、clean0と別に保存。
14原event-target-source-equipment/support2scoreを照合、support28score原利用可/対象一致/score>6。35sourceは全19equipment内参照、原内訳 {"motor-01.vibration_feature": 12, "motor-01.motor_current": 14, "motor-01.motor_temperature": 9}。source35を誤警報35へしない。原全ledger/四target窓/episodes/640不能・非ok30入力mask保存。入力対応・保存・状態分類の実経路不具合観測なし。GT/threshold/matching/science変更0。

## C2 core・同quality C1との保存比較

|候補/stratum|machine|sensor|precision|clean|available|
|---|---|---|---|---|---|
|C2 core|5/10|10/10|15/20|0|13920|
|C1 quality-stress|10/10|9/10|19/19|0|13880|
|C2 quality-stress|5/10|9/10|14/19|0|13760|

同seed/layout core-quality共通pinsはorigins/split-manifest/targets3・fingerprint差保持。同quality C1/C2はinput10完全一致。原core/C1保存manifestだけ比較/旧model再compute0、declared16candidatecompiled一致。C2core source37→quality35。欠測の利用不能波及と検出指標差を原窓から保存し、設定変更で成功へ補わない。

## 保存済みC2 quality比較

|seed|layout|machine|sensor|precision|clean|
|---|---|---|---|---|---|
|2486912926863618161|0|4/10|9/10|13/19|0|
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
|7466813550306735603|0|5/10|9/10|14/19|0|

第1seed/layout0–11と今回のC2quality13保存指標、旧model再compute0。第1seed全72＋第2seed core3/qualityC1C2=5、board77cells/実使用seed2。第2seed qualityC0・残layouts未完成、77独立datasetではない。bootstrap/統計CI/勝者/採択0。

## 証拠・次unit・正式状態

- model artifacts/representative-seed2-layout0-quality-c2-20261012-records、analysis artifacts/representative-seed2-layout0-quality-c2-20261012-analysis、docs/Git artifacts/representative-seed2-layout0-quality-c2-20261012-save、最終同-final/post-save優先。
- DATA artifacts/representative-anomaly-evaluation/dev-seed7466813550306735603-layout0-quality-c2-20261012/root-closed.json / {"bytes": 38228791, "files": 19, "manifest_pin": {"bytes": 2242, "sha256": "abf625c5f54de826f78c712f6aadeeecebda566eb3c0c2ba780ae4f546554314"}}。analysis項目bytes/parts {"all-episodes": {"bytes": 44784, "parts": 1}, "analysis": {"bytes": 833023, "parts": 4}, "analysis.finished": {"bytes": 37, "parts": 1}, "analysis.started": {"bytes": 17, "parts": 1}, "data-closure": {"bytes": 135, "parts": 1}, "data-closure.finished": {"bytes": 37, "parts": 1}, "data-closure.started": {"bytes": 17, "parts": 1}, "helper-execution": {"bytes": 268, "parts": 1}, "helper-live": {"bytes": 213, "parts": 1}, "incident-ledger": {"bytes": 32097, "parts": 1}, "matched-targets": {"bytes": 48609, "parts": 1}, "non-ok-input-records": {"bytes": 21897, "parts": 1}, "policy": {"bytes": 211, "parts": 1}, "script": {"bytes": 13753, "parts": 1}, "selected-windows": {"bytes": 1711595, "parts": 7}, "unavailable-scores": {"bytes": 1107526, "parts": 5}}。
- EvidenceStore16MiB512files/part256KiB/失敗2MiB16files・閉鎖512KiB4files予備枠と全write preflight維持。旧379root/356helpers21failed335passedmissingexecution1保持、原C1builder error/template/trace・C0誤記/analysis failure/foregroundcp932/console誤記保全。今回newbuilder/helperfailure0/closed-frozen root追記整理0。
- 実行900秒2GiBoutput1GiBsingle32MiBfiles32/Git累積30秒16entry512KiBstdout1MiBstderr128KiB/protocolnative不変。checkpoint≠blocking中断/fullruntime/global/allwriter容量証明。
- prepare_result_index実使用で3文書を同種合成dev結果・PC内pathのGitHub継続送信承認内で1回[skip ci] commit/push。原Git/HEAD-upstream-lsremote-clean/docpinsは-save/-final、追加確認0/bypass0。
- 次unit同seed/layout0 quality-stress C0、新ID dev-seed7466813550306735603-layout0-quality-c0-20261012。同manifest/input10、本文C1C2読取済み/次model未開始、元生成C0/次評価C0別field。新seed追加ではない。
- ACTIVE/automation詳細転記0。CI381385/4130保持query/download/verifier/tests0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了。create_native早期拒否・全7役reader禁止・caps-unknown原owner保持・追加agent禁止。未完了formal/nativeをdev開始条件へ戻さない。Sol容量/人停止は原保全後PAUSED、重複再試行なし。
