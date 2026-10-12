# 第2 dev seed・layout2 C1 core実評価（2026-10-12）

保存済み合成dev coreをC1で1回fresh compute。機械10/10・センサー10/10・precision20/20・正常区間誤警報0件。処理成功を性能保証、採択、正式受入にはしない。

## 入力と実行

- run dev-seed7466813550306735603-layout2-core-c1-20261012 / dataset anomaly-v03-dev-seed-7466813550306735603-layout-02-core。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\014\attempt-0001\result\payload\manifest.json / {"bytes": 75700, "sha256": "13a1f0848235ab785ddc31036c819927a40d5a62e7ff55adb91afe465275998a"}。seed7466813550306735603/layout2/core/dev、同C0 input10完全一致→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics保存。
- 元生成C0・実評価C1は別field。元payload書込み・新生成・replay・追加agent0。
- checkout 4edfcb9dd35c647c8b6a8d7141b9fdb503cf56a8、計算661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/candidate-compiled config不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 16.699286099988967秒/privatepeak 151949312B。
- observations {"bytes": 9600481, "sha256": "9c35ac965771056b42b34064f191a4845fb1f2265cbdb858fb04a21a826642d9"}、configuration {"bytes": 5502, "sha256": "64961d43f2ecba507bcf1613faf99efb364e10aac7366aa065e20e44cc73a9c3"}、manifest {"bytes": 8027, "sha256": "19b32f0160958161b49fd1864eaa5d660235368af404fb56a53419c3bf6cf7ba"}、evaluation {"bytes": 14071778, "sha256": "2d5eb9242299e7d907742587ea73e11c732a6edaccaf05bad8417f066a72ba9a"}。宣言source pinはfull loaded runtime/native認証ではない。
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
|7274|True|48.06906137421353|1|None|
|7275|True|47.92332869991485|2|None|
|7276|True|48.208204884787314|3|None|
|7277|True|1.3150575217679514|0|None|
|7278|True|1.023273548232248|0|None|
|7279|True|0.8351191496427547|0|None|
|7280|True|0.0023355207980450313|0|None|

### cycle0 sensor

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7281|True|165.23518547283598|1|None|
|7282|True|165.9671079144219|2|None|
|7283|True|165.55621676030694|3|None|
|7284|True|0.4609394261892856|0|None|
|7285|True|0.347448519741102|0|None|
|7286|True|0.02284677822119194|0|None|
|7287|True|0.0727093041311009|0|None|

### cycle2 machine

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7634|True|48.18226244230754|1|None|
|7635|True|46.88309474621468|2|None|
|7636|True|47.922780665020895|3|None|
|7637|True|1.0802946671978526|0|None|
|7638|True|1.4494089132690702|0|None|
|7639|True|0.9815910337983844|0|None|
|7640|True|0.36333120344032666|0|None|

### cycle2 sensor

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7641|True|162.58052192969754|1|None|
|7642|True|162.4135980432902|2|None|
|7643|True|162.4558036995344|3|None|
|7644|True|3.1749179111595796|0|None|
|7645|True|2.1431186063816265|0|None|
|7646|True|2.32940137081184|0|None|
|7647|True|2.359636718683643|0|None|

原全20event/incident・全target窓・全不能・全episodesを-analysis、全matched target/supportを-save/target-onset-summaryへ保存。実入力対応・保存・状態分類の不具合は観測なし。

## 同入力C0と保存済みC1比較

|候補|machine|sensor|precision|clean|
|---|---|---|---|---|
|C0|0/10|0/10|0/1|1|
|C1|10/10|10/10|20/20|0|

同seed/layout2/core/input10、旧C0再compute0。旧C0全20窓利用可能/maxstreak1/全missdelaynullと[設計解釈](anomaly-multiseed-v0.3-second-dev-seed-layout2-c0-core-evaluation-2026-10-12.md)を保持。一次差分+persistence2と定常オフセットの相性に関する既存記録を保持し、新しい式監査・閾値変更・GT変更0。

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
|7466813550306735603|2|10/10|10/10|20/20|0|

保存manifest指標15C1core cellsを比較、旧モデル再計算0/source16/candidate-compiled一致。第1seed全72＋第2seed layout0/1各6/layout2 C0C1core2＝86boardcells/実使用seed2。86独立datasetではない。bootstrap/統計CI/勝者/採択0。

## 証拠・次工程・正式状態

- records/analysis/save/final: artifacts/representative-seed2-layout2-core-c1-20261012-*。最終-final/post-saveとroot-closed優先。DATA artifacts/representative-anomaly-evaluation/dev-seed7466813550306735603-layout2-core-c1-20261012 / {"bytes": 27112373, "files": 19, "manifest_pin": {"bytes": 2232, "sha256": "9000a3a77a5fabe078cfbcf8a1838569752baee5e675f6850226a2903a6625c3"}}。
- 旧426root/394helper/22failed372passed/missingexecution1保持。旧C2quality final KeyError failedとcontinuation原保全。閉鎖・外部固定root追記整理0/fullstdio/native回収claim0。今回foreground文書source生成は次unit表現2箇所に一致しscope errorになったがnestedtools/追跡変更/モデル反復0。元input template・失敗式・selected traceを新-builder-errorへ保存（途中派生source/fullJS cell未保存）。reportとhandoffへ別々に限定した訂正sourceだけ実行、helper failureへしない。
- EvidenceStore16MiB512files/part256KiB/失敗予備2MiB16files/閉鎖512KiB4files、script・失敗・閉鎖を含む全write preflight。実行900秒2GiBoutput1GiBsingle32MiBfiles32/Git累積30秒16entry512KiBstdout1MiBstderr128KiB/nativeprotocol維持。checkpoint≠blocking中断/fullruntime/global/allwriter容量証明。
- prepare_result_index実使用/report-handoff-index3docsを同種合成dev結果・PC内pathの継続送信承認内で一回[skip ci] commit/push。原Git/HEAD-upstream-lsremote-clean/docpinsは-save/-final。追加承認質問・bypass0。
- 次unit同seed/layout2/core C2 c2-phase-conditional、新ID dev-seed7466813550306735603-layout2-core-c2-20261012。同manifest/input10・本文C0C1読取済み・次model未開始。新独立seedではない。
- ACTIVE/automation詳細転記0。CI381385/4130保持/querydownloadverifiertests0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了。create_native早期拒否/全7役reader禁止/caps-unknown原owner保持/追加agent禁止。未完了formal/nativeをdev開始条件へ戻さない。Sol容量・人停止は原保全後PAUSED、重複再試行なし。
