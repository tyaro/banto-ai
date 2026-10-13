# 第2 dev seed・layout3 C2 core実評価と3候補比較（2026-10-13）

保存済み合成dev coreをC2で1cell実評価。機械10/10・sensor10/10・precision20/20・正常区間誤警報0。処理成功を性能保証・採択・正式受入へしない。

人の2026-10-13「再開ください」でACTIVEへ再開。前回自動審査のSelected model is at capacityは審査未完了の原証拠として-capacity-stopに保持し、helper/model/CI失敗へしない。停止prefixは以下の履歴に保持。今回は未保存C2文書のみ完成、C2モデル・解析再実行0。schedulerは実観測ACTIVE、設定変更0。新記録は-resume-preparation/-resume-save/-resume-finalを優先。
## 入力と実行

- run dev-seed7466813550306735603-layout3-core-c2-20261013 / dataset anomaly-v03-dev-seed-7466813550306735603-layout-03-core。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\015\attempt-0001\result\payload\manifest.json / {"bytes": 75700, "sha256": "479787c83a7c7af9934171a66b6c3fd684689c2b908f79b483a768acf8c278cf"}。同C0C1 input10完全一致→新snapshot/fresh fit/calibration。元生成C0と実評価C2別field。元payload書込み生成replayagent0。
- checkout 448eb18f5c93b8d4e28442c3065dc3a007ef200b / 計算661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/candidatecompiled不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"} / elapsed 29.373155900044367秒 / sampled private peak 209248256B。
- observations {"bytes": 9600457, "sha256": "55ebeb87fe63f7f9f337f56ca7b6d055cb4d19bd1d9acbcde6c10f3e677b2a70"} / configuration {"bytes": 5508, "sha256": "a8ad712d83589d082dd50d7425291fdc2437f6d299cb268f45469dcf2de576bd"} / manifest {"bytes": 8033, "sha256": "5b337e5501b822bdb0d188e8a74e520146e457f0ca13eb30efcc3e720b0c89b0"} / result {"bytes": 24757927, "sha256": "5e1dc2d547a665f73f6a85a7dad0750d25d87dc6bb44840fdf248519e0bca862"}。
- C0threshold4/C1C2threshold6/operator>/persistence2・GTmatching科学不変。全rawthresholdflag確認。宣言pin≠full loaded runtime/native認証。

## 原結果と検出対応

|項目|原値|
|---|---|
|machine|10/10|
|sensor|10/10|
|precision|20/20|
|clean / unmatched|0 / 0|
|source / equipment / incidents / events|50 / 20 / 20 / 40|
|available / unavailable|13920 / 480|
|delay count / min / max / mean / median|20 / 1 / 2 / 1.5 / 1.5秒|

48calibrated/fit各600/calibration各290/C2stateあり48。18000input-mask対応nonok0。480不能全mode_recipe_or_phase/score-residualnull/thresholdfalse、各target1740/1800利用可。
全20causal_detected/candidate1、全event→対象source→matched equipment→support2原scoreを照合。全40support対象一致/利用可/score>6。機械10件onset=start+1秒・delay1秒、センサー10件onset=start+2秒・delay2秒。
機械10窓7全利用可/phase不能0/maxstreak3。センサー10窓6利用可/開始phase不能1/maxstreak2。センサー開始行score/residualnull・streak0、次行score>6/streak1、さらに次行score>6/streak2でepisode成立。除外なしの反実仮想再compute0。
全50sourceは20matched equipment内参照、source内訳 {"motor-01.motor_current": 20, "motor-01.motor_temperature": 14, "motor-01.conveyor_speed": 6, "motor-01.vibration_feature": 10} / class membership {"machine": {"motor-01.conveyor_speed": 6, "motor-01.motor_current": 10, "motor-01.motor_temperature": 4, "motor-01.vibration_feature": 10}, "sensor": {"motor-01.motor_current": 10, "motor-01.motor_temperature": 10}}。source件数をequipment件数・誤警報件数へしない。
clean_rate0/3365原0/effective3255秒rate0/burden0/20原0を単純確率へしない。未検出delay補完0。

### cycle0 sensor

|sample|available|score|streak|reason|
|---|---|---|---|---|
|7290|False|None|0|mode_recipe_or_phase|
|7291|True|134.31706363715705|1|None|
|7292|True|134.82755678727173|2|None|
|7293|True|0.12160475315236631|0|None|
|7294|True|0.6665872055301584|0|None|
|7295|True|0.5809107612120596|0|None|
|7296|True|0.8127267991985665|0|None|

### cycle0 machine

|sample|available|score|streak|reason|
|---|---|---|---|---|
|7311|True|80.65475368732542|1|None|
|7312|True|81.29733843991183|2|None|
|7313|True|81.38559325236514|3|None|
|7314|True|0.48188471960836005|0|None|
|7315|True|0.7990753003204992|0|None|
|7316|True|0.020437518139431517|0|None|
|7317|True|0.5106310204795045|0|None|

### cycle2 sensor

|sample|available|score|streak|reason|
|---|---|---|---|---|
|7650|False|None|0|mode_recipe_or_phase|
|7651|True|133.70559389400728|1|None|
|7652|True|133.09723839066893|2|None|
|7653|True|0.3962217810368368|0|None|
|7654|True|0.4916428642633266|0|None|
|7655|True|0.7827648435541387|0|None|
|7656|True|0.8529614050522932|0|None|

### cycle2 machine

|sample|available|score|streak|reason|
|---|---|---|---|---|
|7671|True|80.24068273133722|1|None|
|7672|True|80.7578431645031|2|None|
|7673|True|81.30145312914739|3|None|
|7674|True|1.1658500524586672|0|None|
|7675|True|0.41424325420712715|0|None|
|7676|True|0.4040588883196576|0|None|
|7677|True|1.8580062019869095|0|None|

全20ledger/targetwindows/480不能/episodesを-analysis、全20matched/support40・sensor先頭3行×10を-saveへ保存。実入力対応・保存・状態分類不具合は観測なし。

## 同入力3候補比較

|candidate|machine|sensor|precision|clean|source / equipment|delay median|
|---|---|---|---|---|---|---|
|C0|0/10|0/10|0/1|1|1 / 1|null|
|C1|10/10|10/10|20/20|0|30 / 20|1.5秒|
|C2|10/10|10/10|20/20|0|50 / 20|1.5秒|

同seed/layout3/core input10一致、旧C0C1再compute0/source16candidatecompiled一致。C1C2全metrics一致を全score/sourceepisode一致・勝者・採択へしない。C0既存差分/persistence解釈・原20miss/clean1を保持。新式監査・正常対照再compute・thresholdGT変更0。
C2core保存16cellsのmanifest指標比較。第1seed72＋第2seed layouts0/1/2各6＋layout3core3＝93boardcells/使用seed2。93独立datasetではない。bootstrap統計CI勝者採択0。

## 証拠・次工程・正式状態

- artifacts/representative-seed2-layout3-core-c2-20261013-* の-final/post-save・root-closed優先。DATA artifacts/representative-anomaly-evaluation/dev-seed7466813550306735603-layout3-core-c2-20261013 / {"bytes": 37798308, "files": 19, "manifest_pin": {"bytes": 2232, "sha256": "a124e50ba1072b008d51e23deacd1f636a984bb0a4fe83f05c3503180f4325a4"}}。
- 旧464root/424helpers23failed401passedmissingexecution1保全。旧sourcebuilder scope失敗・C2解析FileNotFound/別継続・KeyError/停止再開・誤記を保持。今回新sourcebuilderfailure0/newhelperfailure0。閉鎖外部固定root追記整理0/fullstdioPID単独native回収claim0。
- prepare_result_index実使用、report/handoff/index3docsを同種合成dev結果・PC内path継続送信承認内で一回[skip ci] commit/push、原Git-save。追加承認質問bypass0。
- 次unit同seed/layout3 quality-stress C1、新ID dev-seed7466813550306735603-layout3-quality-c1-20261013。同manifest/pin・quality identity/input10metadataのみ選択、次本文未読・model未開始。同seed別stratumで新独立seedではない。
- EvidenceStore16MiB512files/part256KiB/失敗2MiB16files/閉鎖512KiB4files・全writepreflight。実行900秒2GiBoutput1GiBsingle32MiBfiles32/Git30秒16entry512KiBstdout1MiBstderr128KiB/nativeprotocol維持。checkpoint≠blocking中断/fullruntime/global/allwriter容量証明。
- ACTIVE/automation詳細転記0/CI3813854130querydownloadverifiertests0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件最終受入未完了/create_native早期拒否/7役reader禁止/追加agent禁止/capsunknown原owner保持。未完了formal/nativeをdev開始条件へ戻さない。Sol容量人停止は保全後PAUSED/重複再試行なし。
