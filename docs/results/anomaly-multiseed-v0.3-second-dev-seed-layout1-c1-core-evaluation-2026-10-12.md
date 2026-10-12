# 第2 dev seed・layout1 C1 core実評価（2026-10-12）

保存済み合成dev coreをC1で1回fresh compute。機械10/10・センサー10/10・precision20/20・正常区間誤警報0件。処理成功を性能保証、採択、正式受入にはしない。

## 入力と実行

- run dev-seed7466813550306735603-layout1-core-c1-20261012 / dataset anomaly-v03-dev-seed-7466813550306735603-layout-01-core。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\013\attempt-0001\result\payload\manifest.json / {"bytes": 75699, "sha256": "d4743f431240dee56e5ead1d0709a998e502b6a7e8a4aecd3f00468dced8bd81"}。seed7466813550306735603/layout1/core/dev、同C0 input10完全一致→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics保存。
- 元生成C0・実評価C1は別field。元payload書込み・新生成・replay・追加agent0。
- checkout 9bdeea61cac1cd7905110051b055165b169635f7、計算661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/candidate-compiled config不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 16.77326859999448秒/privatepeak 150876160B。
- observations {"bytes": 9600485, "sha256": "5f1348946d4d32168c62eab56b3f23ca3e1293823c55c9641a2916ca555ebc73"}、configuration {"bytes": 5502, "sha256": "ab7f70ac5bef8444321273540895bdc21c24ce3f3fde3359115434944fa38825"}、manifest {"bytes": 8026, "sha256": "13962aed8b0478a08df77616e436175f878efb3d9f7e0169a7244eb431611350"}、evaluation {"bytes": 14071760, "sha256": "013d3e31c33c584255cb65541a0bfef042a5fd4d29914214193653d6db4162be"}。宣言source pinはfull loaded runtime/native認証ではない。
- C0 threshold4/C1・C2 threshold6/operator>/persistence2・GT/matching/science不変。原scoreの閾値判定を全行確認。

## 原結果

|項目|原値|
|---|---|
|machine|10/10|
|sensor|10/10|
|precision|20/20|
|clean / unmatched|0 / 0|
|source / equipment / incidents / events|30 / 20 / 20 / 40|
|available / unavailable scores|13920 / 480|

48profiles全calibrated/fit各600/calibration各290/C2stateなし48。18000observations-mask対応/non-ok0。全480不能はmode_recipe_or_phase、score-residual null/thresholdfalse。8target各1740/1800利用可能。
全20causal_detected/candidate1、検出delaycount20/min=max=mean=median1秒。未検出delay補完0。clean_rate0/3365原0/effective3255秒rate0/burden0/20原0。率とburdenを単純確率へしない。

## 原検出の対応

全20event→対象source→matched equipment→support2原scoreを照合。全40supportは対象一致/利用可/score>6。machine10・sensor10各onset=start+1秒。全20対象窓は7行全利用可/phase不能0/maxstreak3。開始観測streak1→次観測streak2でepisode成立。
全source30はmatched equipment20に参照される。source内訳 {"motor-01.motor_current": 10, "motor-01.vibration_feature": 10, "motor-01.motor_temperature": 10}、class membership {"machine": {"motor-01.motor_current": 10, "motor-01.vibration_feature": 10}, "sensor": {"motor-01.motor_temperature": 10}}。source30をequipment30や誤警報30へしない。

### cycle0 machine

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7237|True|32.340634478589514|1|None|
|7238|True|33.076186506193366|2|None|
|7239|True|34.14443967556706|3|None|
|7240|True|0.625264210096018|0|None|
|7241|True|0.8100681213173708|0|None|
|7242|True|1.307255682000615|0|None|
|7243|True|1.3185582059415404|0|None|

### cycle0 sensor

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7244|True|148.6943115911126|1|None|
|7245|True|149.15124998997467|2|None|
|7246|True|150.28858779449246|3|None|
|7247|True|1.3591696402125848|0|None|
|7248|True|0.6496215322748805|0|None|
|7249|True|0.20512238852683584|0|None|
|7250|True|0.09621392509611693|0|None|

### cycle2 machine

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7597|True|33.544429726170456|1|None|
|7598|True|32.64306814339583|2|None|
|7599|True|33.65111567275539|3|None|
|7600|True|0.3160090428071485|0|None|
|7601|True|1.3414396422860484|0|None|
|7602|True|0.5122330900811904|0|None|
|7603|True|0.4766789486936802|0|None|

### cycle2 sensor

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7604|True|148.00978123879588|1|None|
|7605|True|148.2988639578289|2|None|
|7606|True|148.25410120547107|3|None|
|7607|True|0.3790398844672834|0|None|
|7608|True|0.766801172053732|0|None|
|7609|True|0.750398064750446|0|None|
|7610|True|0.9979485245447548|0|None|

原全20event/incident・全target窓・全不能・全episodesを-analysis、全matched target/supportを-save/target-onset-summaryへ保存。実入力対応・保存・状態分類の不具合は観測なし。

## 同入力C0と保存済みC1比較

|候補|machine|sensor|precision|clean|
|---|---|---|---|---|
|C0|0/10|0/10|0/1|1|
|C1|10/10|10/10|20/20|0|

同seed/layout1/core/input10、旧C0再compute0。旧C0全20窓利用可能/maxstreak1/全missdelaynullと[設計解釈](anomaly-multiseed-v0.3-second-dev-seed-layout1-c0-core-evaluation-2026-10-12.md)を保持。一次差分+persistence2と定常オフセットの相性に関する既存記録を保持し、新しい式監査・閾値変更・GT変更0。

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
|7466813550306735603|1|10/10|10/10|20/20|0|

保存manifest指標14C1core cellsを比較、旧モデル再計算0/source16/candidate-compiled一致。第1seed全72＋第2seed layout0全6/layout1 C0C1core2＝80boardcells/実使用seed2。80独立datasetではない。bootstrap/統計CI/勝者/採択0。

## 証拠・次工程・正式状態

- records/analysis/save/final: artifacts/representative-seed2-layout1-core-c1-20261012-*。最終-final/post-saveとroot-closed優先。DATA artifacts/representative-anomaly-evaluation/dev-seed7466813550306735603-layout1-core-c1-20261012 / {"bytes": 27112358, "files": 19, "manifest_pin": {"bytes": 2232, "sha256": "bc6174661bfa567077f14ccf342a3e720bc6a5f16648443ac1515c4d211bcea3"}}。
- 旧394root/368helper/21failed347passed/missingexecution1保持。閉鎖・外部固定root追記整理0。foreground AGENTS.md不在/rg該当なしは-saveへselectedtool metadata保存、fullcreation/stdioNone・instrumentedhelperfailureではない。
- EvidenceStore16MiB512files/part256KiB/失敗予備2MiB16files/閉鎖512KiB4files、script・失敗・閉鎖を含む全write preflight。実行900秒2GiBoutput1GiBsingle32MiBfiles32/Git累積30秒16entry512KiBstdout1MiBstderr128KiB/nativeprotocol維持。checkpoint≠blocking中断/fullruntime/global/allwriter容量証明。
- prepare_result_index実使用/report-handoff-index3docsを同種合成dev結果・PC内pathの継続送信承認内で一回[skip ci] commit/push。原Git/HEAD-upstream-lsremote-clean/docpinsは-save/-final。追加承認質問・bypass0。
- 次unit同seed/layout1/core C2 c2-phase-conditional、新ID dev-seed7466813550306735603-layout1-core-c2-20261012。同manifest/input10・本文C0C1読取済み・次model未開始。新独立seedではない。
- ACTIVE/automation詳細転記0。CI381385/4130保持/querydownloadverifiertests0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了。create_native早期拒否/全7役reader禁止/caps-unknown原owner保持/追加agent禁止。未完了formal/nativeをdev開始条件へ戻さない。Sol容量・人停止は原保全後PAUSED、重複再試行なし。
