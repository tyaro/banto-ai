# 第2 dev seed・layout2 C2 core実評価（2026-10-13）

保存済み合成dev coreをC2で1回fresh compute。機械10/10・センサー10/10・precision20/20・正常区間誤警報0件。原対象検出20件の遅延は全1秒。処理成功を性能保証・採択・正式受入にしない。

## 入力と実行

- run dev-seed7466813550306735603-layout2-core-c2-20261012 / dataset anomaly-v03-dev-seed-7466813550306735603-layout-02-core。前日に保存した未着手runIDは保持し、今回の文書・metadataは実行日2026-10-13 JSTで保存。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\014\attempt-0001\result\payload\manifest.json / {"bytes": 75700, "sha256": "13a1f0848235ab785ddc31036c819927a40d5a62e7ff55adb91afe465275998a"}。seed7466813550306735603/layout2/core/dev、同C0/C1 input10完全一致→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics保存。
- 元生成C0・実評価C2は別field。元payload書込み・新生成・replay・追加agent0。
- checkout e92c406374fb351e819f971e0a56e4f7d16b42aa、計算661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/candidate-compiled config不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 31.94950129999779秒/privatepeak 210726912B。
- observations {"bytes": 9600481, "sha256": "9c35ac965771056b42b34064f191a4845fb1f2265cbdb858fb04a21a826642d9"}、configuration {"bytes": 5508, "sha256": "a89918c69a112d7186438c78584f518f520798e2e872eb9e4abdbdb8dd771d52"}、manifest {"bytes": 8032, "sha256": "1f75087e34b3172d38b4db00c463df1e678f4d0253ef129d15e671aafd9ed032"}、evaluation {"bytes": 24757464, "sha256": "f6792b44a135c625f29f884cbebcc3739280e5b5ae8e7179dcef9d49127aa1e1"}。宣言source pinはfull loaded runtime/native認証ではない。
- C0 threshold4/C1・C2 threshold6/operator>/persistence2・GT/matching/science不変。原scoreの閾値判定を全行確認。

## 原結果

|項目|原値|
|---|---|
|machine|10/10|
|sensor|10/10|
|precision|20/20|
|clean / unmatched|0 / 0|
|source / equipment / incidents / events|47 / 20 / 20 / 40|
|available / unavailable scores|13920 / 480|

48profiles全calibrated/fit各600/calibration各290/C2stateあり48。18000observations-mask対応/non-ok0。全480不能mode_recipe_or_phase/score-residual null/thresholdfalse、8target各1740/1800利用可。
全20causal_detected/candidate1、検出delaycount20/min=max=mean=median1秒。未検出delay補完0。clean_rate0/3365原0/effective 3254秒rate0/burden0/20原0。率・burdenを単純確率へしない。

## 原20対象検出と47source

全20event→対象source→matched equipment→support2原scoreを照合。全40supportは対象一致/利用可/score>6。machine10・sensor10各onset=start+1秒。全20対象窓7行全利用可/phase不能0/maxstreak3。開始観測streak1→次観測streak2でepisode成立。
全source47はmatched equipment20内に参照。source内訳 {"motor-01.motor_current": 20, "motor-01.vibration_feature": 17, "motor-01.motor_temperature": 10}、class membership {"machine": {"motor-01.motor_current": 10, "motor-01.vibration_feature": 10}, "sensor": {"motor-01.motor_current": 10, "motor-01.motor_temperature": 10, "motor-01.vibration_feature": 7}}。C1 source30とC2 source47の差を検出対象47件・equipment47件・誤警報47件にはしない。

### cycle0 machine

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7274|True|44.72164399396629|1|None|
|7275|True|44.54893773731316|2|None|
|7276|True|44.77700349031299|3|None|
|7277|True|1.26196579070491|0|None|
|7278|True|1.0818417841517138|0|None|
|7279|True|0.706873110870668|0|None|
|7280|True|0.03933180721702853|0|None|

### cycle0 sensor

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7281|True|166.90536862307096|1|None|
|7282|True|167.4377629193333|2|None|
|7283|True|167.2072521346107|3|None|
|7284|True|0.5492746561000766|0|None|
|7285|True|0.3060651435363347|0|None|
|7286|True|0.004425178640207327|0|None|
|7287|True|0.13227900219045374|0|None|

### cycle2 machine

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7634|True|44.63716405298395|1|None|
|7635|True|43.28765077151349|2|None|
|7636|True|44.301686810101316|3|None|
|7637|True|1.115111880074795|0|None|
|7638|True|1.3863513077207676|0|None|
|7639|True|0.9894027310751788|0|None|
|7640|True|0.446095505114125|0|None|

### cycle2 sensor

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7641|True|164.20943244396597|1|None|
|7642|True|163.9129563410416|2|None|
|7643|True|164.0120147430103|3|None|
|7644|True|3.0814414601700717|0|None|
|7645|True|2.1876728942336343|0|None|
|7646|True|2.259037434839038|0|None|
|7647|True|2.3301486348518643|0|None|

原全20event/incident・全target窓・全不能・全episodesを-analysis、全matched target/supportを-save/target-onset-summaryへ保存。実入力対応・保存・状態分類の不具合は観測なし。

## 同入力3候補・保存済みC2core比較

|候補|machine|sensor|precision|clean|source / equipment|
|---|---|---|---|---|---|
|c0-diff-control|0/10|0/10|0/1|1|1 / 1|
|c1-phase-level|10/10|10/10|20/20|0|30 / 20|
|c2-phase-conditional|10/10|10/10|20/20|0|47 / 20|

同seed/layout2/core/input10、旧C0/C1再compute0。旧C0全20窓利用可能/maxstreak1/全missdelaynullと[既存設計解釈](anomaly-multiseed-v0.3-second-dev-seed-layout2-c0-core-evaluation-2026-10-12.md)を保持。新しい式監査・閾値変更・GT変更0。C1/C2今回指標一致を全スコア・sourceepisode完全一致や候補優劣へ補わない。

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
|7466813550306735603|2|10/10|10/10|20/20|0|

保存manifest指標15C2core cells比較、旧モデル再計算0/source16/candidate-compiled一致。第1seed全72＋第2seed layout0/1各6/layout2 core全3＝87boardcells/実使用seed2。87独立datasetではない。bootstrap/統計CI/勝者/採択0。

## 証拠・次工程・正式状態

- records/analysis/save/final: artifacts/representative-seed2-layout2-core-c2-20261013-*。最終-final/post-saveとroot-closed優先。DATA artifacts/representative-anomaly-evaluation/dev-seed7466813550306735603-layout2-core-c2-20261012 / {"bytes": 37798088, "files": 19, "manifest_pin": {"bytes": 2232, "sha256": "57fb383e4d69624055e74fe9fb47626975ef6c923ad905c0b279a12a23f8c4f5"}}。
- 旧432root/398helper/22failed376passed/missingexecution1保持。旧C2quality final KeyError failedとcontinuation、前回C1 foreground builder scope error（helper failureではない）を保全。閉鎖・外部固定root追記整理0/fullstdio/native回収claim0。
- EvidenceStore16MiB512files/part256KiB/失敗予備2MiB16files/閉鎖512KiB4files、script・失敗・閉鎖全write preflight。実行900秒2GiBoutput1GiBsingle32MiBfiles32/Git累積30秒16entry512KiBstdout1MiBstderr128KiB/nativeprotocol維持。checkpoint≠blocking中断/fullruntime/global/allwriter容量証明。
- prepare_result_index実使用/report-handoff-index3docsを同種合成dev結果・PC内path継続送信承認内で一回[skip ci] commit/push。原Git/HEAD-upstream-lsremote-clean/docpins-save/-final。追加承認質問・bypass0。
- 次unit同seed/layout2の保存済みquality-stress C1 c1-phase-level、新ID dev-seed7466813550306735603-layout2-quality-c1-20261013。同manifest pinから10file identity metadataだけ選択、次観測本文未読/次model未開始。元生成C0/次評価C1別field、新独立seedではない。
- ACTIVE/automation詳細転記0。CI381385/4130保持/querydownloadverifiertests0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了。create_native早期拒否/全7役reader禁止/caps-unknown原owner保持/追加agent禁止。未完了formal/nativeをdev開始条件へ戻さない。Sol容量・人停止は原保全後PAUSED、重複再試行なし。
