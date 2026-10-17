# 第2 dev seed・layout1 C2 core実評価（2026-10-12）

保存済み合成dev coreをC2で1回fresh compute。機械10/10・センサー10/10・precision20/20・正常区間誤警報0件。原対象検出20件の遅延は全1秒。処理成功を性能保証・採択・正式受入にしない。

## 入力と実行

- run dev-seed7466813550306735603-layout1-core-c2-20261012 / dataset anomaly-v03-dev-seed-7466813550306735603-layout-01-core。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\013\attempt-0001\result\payload\manifest.json / {"bytes": 75699, "sha256": "d4743f431240dee56e5ead1d0709a998e502b6a7e8a4aecd3f00468dced8bd81"}。seed7466813550306735603/layout1/core/dev、同C0/C1 input10完全一致→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics保存。
- 元生成C0・実評価C2は別field。元payload書込み・新生成・replay・追加agent0。
- checkout 9e0570303d473d649becc54f3af5c2688a11b36c、計算661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/candidate-compiled config不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 25.47748970007524秒/privatepeak 208011264B。
- observations {"bytes": 9600485, "sha256": "5f1348946d4d32168c62eab56b3f23ca3e1293823c55c9641a2916ca555ebc73"}、configuration {"bytes": 5508, "sha256": "592d0ca5005cc55d2e127cabcaa4e5abd4ab3526304feff49527736270c99adb"}、manifest {"bytes": 8032, "sha256": "22f75014c78bc6c03071f4466ef73df90c6da5b32800173d93cc1ef65f034dec"}、evaluation {"bytes": 24771743, "sha256": "7840852c3aa3846ac798900263db619c7408a1ae62c25a17c3260c3dffddfb4f"}。宣言source pinはfull loaded runtime/native認証ではない。
- C0 threshold4/C1・C2 threshold6/operator>/persistence2・GT/matching/science不変。原score閾値判定を全行確認。

## 原結果

|項目|原値|
|---|---|
|machine|10/10|
|sensor|10/10|
|precision|20/20|
|clean / unmatched|0 / 0|
|source / equipment / incidents / events|59 / 20 / 20 / 40|
|available / unavailable scores|13920 / 480|

48profiles全calibrated/fit各600/calibration各290/C2stateあり48。18000observations-mask対応/non-ok0。全480不能はmode_recipe_or_phase、score-residual null/thresholdfalse。8target各1740/1800利用可能。
全20causal_detected/candidate1、検出delaycount20/min=max=mean=median1秒。未検出delay補完0。clean_rate0/3365原0/effective3255秒rate0/burden0/20原0。率とburdenを単純確率へしない。

## 原20対象検出と59sourceの対応

全20event→対象source→matched equipment→support2原scoreを照合。全40supportは対象一致/利用可/score>6。machine10・sensor10各onset=start+1秒。全20対象窓は7行全利用可/phase不能0/maxstreak3。開始観測streak1→次観測streak2でepisode成立。
全source59はmatched equipment20に参照される。source内訳 {"motor-01.motor_current": 20, "motor-01.motor_temperature": 19, "motor-01.vibration_feature": 20}、class membership {"machine": {"motor-01.motor_current": 10, "motor-01.motor_temperature": 9, "motor-01.vibration_feature": 10}, "sensor": {"motor-01.motor_current": 10, "motor-01.motor_temperature": 10, "motor-01.vibration_feature": 10}}。C1のsource30からC2の59への増加を、検出対象59件・equipment59件・誤警報59件にはしない。selected target episode20以外の39sourceを全てpeer-onlyと断定しない。

### cycle0 machine

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7237|True|31.410132478817573|1|None|
|7238|True|32.0757105798977|2|None|
|7239|True|33.18067741275602|3|None|
|7240|True|0.6779494670307077|0|None|
|7241|True|0.9476506143006415|0|None|
|7242|True|1.3204712217492418|0|None|
|7243|True|1.3402218966343264|0|None|

### cycle0 sensor

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7244|True|147.794683260984|1|None|
|7245|True|148.30911905352323|2|None|
|7246|True|149.43285125921122|3|None|
|7247|True|1.4474122051411906|0|None|
|7248|True|0.758384097110041|0|None|
|7249|True|0.3717627866850295|0|None|
|7250|True|0.018938225468067216|0|None|

### cycle2 machine

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7597|True|32.47785167993975|1|None|
|7598|True|31.70068087886889|2|None|
|7599|True|32.69763360575887|3|None|
|7600|True|0.2874311733012893|0|None|
|7601|True|1.400384762170382|0|None|
|7602|True|0.5516516737692919|0|None|
|7603|True|0.46568031965961904|0|None|

### cycle2 sensor

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7604|True|147.11245462147173|1|None|
|7605|True|147.42299965340172|2|None|
|7606|True|147.4386652444205|3|None|
|7607|True|0.33462669603907386|0|None|
|7608|True|0.692123933077841|0|None|
|7609|True|0.8122812433930332|0|None|
|7610|True|0.935169794289217|0|None|

原全20event/incident・全target窓・全不能・全episodesを-analysis、全matched target/supportを-save/target-onset-summaryへ保存。実入力対応・保存・状態分類の不具合は観測なし。

## 同入力3候補・保存済みC2core比較

|候補|machine|sensor|precision|clean|source / equipment|
|---|---|---|---|---|---|
|c0-diff-control|0/10|0/10|0/1|1|1 / 1|
|c1-phase-level|10/10|10/10|20/20|0|30 / 20|
|c2-phase-conditional|10/10|10/10|20/20|0|59 / 20|

同seed/layout1/core/input10、旧C0/C1再compute0。旧C0全20窓利用可能/maxstreak1/全missdelaynullと[既存設計解釈](anomaly-multiseed-v0.3-second-dev-seed-layout1-c0-core-evaluation-2026-10-12.md)を保持。新しい式監査・閾値変更・GT変更0。C1/C2の今回指標一致をスコア・sourceepisode完全一致や候補優劣へ補わない。

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
|7466813550306735603|1|10/10|10/10|20/20|0|

保存manifest指標14C2core cells比較、旧モデル再計算0/source16/candidate-compiled一致。第1seed全72＋第2seed layout0全6/layout1 core全3＝81boardcells/実使用seed2。81独立datasetではない。bootstrap/統計CI/勝者/採択0。

## 証拠・次工程・正式状態

- records/analysis/save/final: artifacts/representative-seed2-layout1-core-c2-20261012-*。最終-final/post-saveとroot-closed優先。DATA artifacts/representative-anomaly-evaluation/dev-seed7466813550306735603-layout1-core-c2-20261012 / {"bytes": 37812371, "files": 19, "manifest_pin": {"bytes": 2232, "sha256": "8f84a2fbc647d6cc2c09fe294c4f14926bc602f6a3722234bb3c9ce94e6e0bad"}}。
- 旧399root/372helper/21failed351passed/missingexecution1保持。閉鎖・外部固定root追記整理0。foregroundrg該当なしとmetadata readoutの39source label訂正を-saveへ保存/fullcreationstdioNone/helperfailureではない。元peer_only_sources_count39は59-20の差でありpeer-only認証ではない。
- EvidenceStore16MiB512files/part256KiB/失敗予備2MiB16files/閉鎖512KiB4files、script・失敗・閉鎖を含む全write preflight。実行900秒2GiBoutput1GiBsingle32MiBfiles32/Git累積30秒16entry512KiBstdout1MiBstderr128KiB/nativeprotocol維持。checkpoint≠blocking中断/fullruntime/global/allwriter容量証明。
- prepare_result_index実使用/report-handoff-index3docsを同種合成dev結果・PC内pathの継続送信承認内で一回[skip ci] commit/push。原Git/HEAD-upstream-lsremote-clean/docpins-save/-final。追加承認質問・bypass0。
- 次unit同seed/layout1の保存済みquality-stress C1 c1-phase-level、新ID dev-seed7466813550306735603-layout1-quality-c1-20261012。同manifest pinから10file identity metadataだけ選択、次観測本文未読/次model未開始。元生成C0/次評価C1別field、新独立seedではない。
- ACTIVE/automation詳細転記0。CI381385/4130保持/querydownloadverifiertests0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了。create_native早期拒否/全7役reader禁止/caps-unknown原owner保持/追加agent禁止。未完了formal/nativeをdev開始条件へ戻さない。Sol容量・人停止は原保全後PAUSED、重複再試行なし。
