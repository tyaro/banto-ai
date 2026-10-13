# 第2 dev seed・layout3 C0 core実評価（2026-10-13）

保存済み合成dev layout3 coreをC0で1回fresh compute。機械0/10・センサー0/10・precision0/1・正常区間誤警報1件。全20未検出と原delay nullを保持。処理成功を性能保証・採択・正式受入にしない。

## 入力と実行

- run dev-seed7466813550306735603-layout3-core-c0-20261013 / dataset anomaly-v03-dev-seed-7466813550306735603-layout-03-core。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\015\attempt-0001\result\payload\manifest.json / {"bytes": 75700, "sha256": "479787c83a7c7af9934171a66b6c3fd684689c2b908f79b483a768acf8c278cf"}。seed7466813550306735603/layout3/core/dev、input10pin→新snapshot→fresh calibration→原profiles/scores/episodes/events/incidents/metrics保存。
- 元生成C0・実評価C0は別field。元payload書込み・新生成・replay・追加agent0。同seedの別layoutで新独立seedではない。
- checkout 7ab5f4b51bd51dd896bf01fe5e12f83799856da7、計算661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/candidate-compiled config不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 20.530790899996646秒/privatepeak 150568960B。
- observations {"bytes": 9600457, "sha256": "55ebeb87fe63f7f9f337f56ca7b6d055cb4d19bd1d9acbcde6c10f3e677b2a70"}、configuration {"bytes": 5503, "sha256": "fe128e7af4f09dda67022eddf4c18ead2271d6f43770d1a705d5bdaacf5c4268"}、manifest {"bytes": 8053, "sha256": "60eb7c11d1c7ca6a76dd43e6f12eec3b6fee18beb07c4761d25f9e189d7c8414"}、evaluation {"bytes": 13896116, "sha256": "9a72f0fd4f3dd07f47f3103e5b69f6416f9103d1427070d24b5e5db5ed1fb15c"}。宣言source pinはfull loaded runtime/native認証ではない。
- C0 threshold4/C1C2 threshold6/operator>/persistence2・GT/matching/science不変。原score閾値判定全行確認。

## 原結果と全20未検出

|項目|原値|
|---|---|
|machine|0/10|
|sensor|0/10|
|precision|0/1|
|clean / unmatched|1 / 1|
|source / equipment / incidents / events|1 / 1 / 20 / 40|
|available / unavailable scores|13920 / 480|

48profiles全calibrated/fit_samples各0（C0経路）/calibration各290/C2stateなし48。18000observations-mask対応/non-ok0。全480不能mode_recipe_or_phase/score-residual null/thresholdfalse、8targets各1740/1800利用可。
全20no_candidate_in_window/candidate0/causalfalse/matchednull/delaynull。delaycount0/minmaxmeanmedian原null、補完0。全20対象窓maxstreak1、固定persistence2不成立。機械10窓7全利用可/phase不能0、センサー10窓6利用可/開始sampleのphase不能1。機械未検出を欠測・phase除外で説明しない。sensor開始phase不能は原値を保持し、除外を外した反実仮想再computeは行わない。
clean_rate 1/3365原value 8.558692421991084、effective 3255秒/rate 8.847926267281107、burden 1/20原value 5.0。率・burdenを単純確率へしない。唯一clean source conveyor-01.motor_temperatureのequipment/source/support原対応を-save/episode-summaryへ保存。

## 選択原target窓

### cycle0 sensor

異常区間[7290,7293)、magnitude 8.0、matching end 7296。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7290|False|None|0|mode_recipe_or_phase|
|7291|True|3.7978526494290876|0|None|
|7292|True|3.7871939195955564|0|None|
|7293|True|147.71220920364235|1|None|
|7294|True|2.918824218592216|0|None|
|7295|True|1.5914955738813505|0|None|
|7296|True|1.8673740619686001|0|None|

### cycle0 machine

異常区間[7311,7314)、magnitude 0.55、matching end 7317。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7311|True|51.512203289600954|1|None|
|7312|True|0.4654187886655519|0|None|
|7313|True|0.46104749997481903|0|None|
|7314|True|51.85133481639464|1|None|
|7315|True|0.5230228628558438|0|None|
|7316|True|0.03017378040814431|0|None|
|7317|True|0.002025607625515141|0|None|

### cycle9 sensor

異常区間[8910,8913)、magnitude 8.0、matching end 8916。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|8910|False|None|0|mode_recipe_or_phase|
|8911|True|2.679580455772133|0|None|
|8912|True|3.0393498559408787|0|None|
|8913|True|145.81277509852927|1|None|
|8914|True|2.1521037680121387|0|None|
|8915|True|2.1593710838076743|0|None|
|8916|True|1.8216458748855051|0|None|

### cycle9 machine

異常区間[8931,8934)、magnitude 0.55、matching end 8937。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|8931|True|52.42506188457643|1|None|
|8932|True|0.19342952456521037|0|None|
|8933|True|0.2861136477464607|0|None|
|8934|True|50.76000327144329|1|None|
|8935|True|0.20112957702882595|0|None|
|8936|True|0.6942347182282874|0|None|
|8937|True|0.29925494868494745|0|None|

原全20event/incident/四target窓・480不能・episodesを-analysis、選択窓/唯一clean episode-supportを-save保存。原scoreの大きな単発超過をpersistence2成立へ補わない。実入力対応・保存・状態分類の不具合は観測なし。
一次差分とpersistence2、3観測[end exclusive]の定常加算成分が内部差分で相殺される既存C0設計解釈を保持。今回の原maxstreak1との整合を記述し、新しい式監査・正常対照再compute・閾値/GT変更0。機械異常の乗算overlayを単純加算toyと同一視しない。

## 保存済みC0core比較

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
|7466813550306735603|1|0/10|0/10|0/1|1|
|7466813550306735603|2|0/10|0/10|0/1|1|
|7466813550306735603|3|0/10|0/10|0/1|1|

16C0core保存manifest指標比較/source16candidatecompiled一致、旧モデル再計算0。第1seed全72＋第2seed layouts0/1/2各6＋layout3 C0core1＝91boardcells/実使用seed2。91独立datasetではない。layout3残5cell未完成/bootstrap統計CI勝者採択0。

## 証拠・次工程・正式状態

- records/analysis/save/final: artifacts/representative-seed2-layout3-core-c0-20261013-*。最終-final/post-save/root-closed優先。DATA artifacts/representative-anomaly-evaluation/dev-seed7466813550306735603-layout3-core-c0-20261013 / {"bytes": 26936522, "files": 19, "manifest_pin": {"bytes": 2232, "sha256": "5b99fd26064013d6c22e760914f85e2ee41b41316cda513c00f891c790ca7bee"}}。
- 旧454root/416helper/23failed393passed/missingexecution1保持。旧C2quality final KeyError failed/root/原scriptとcontinuation保持。閉鎖・外部固定root追記整理0/fullstdio/native回収claim0。
- EvidenceStore16MiB512files/part256KiB/失敗予備2MiB16files/閉鎖512KiB4files、script・失敗・閉鎖全write preflight。実行900秒2GiBoutput1GiBsingle32MiBfiles32/Git累積30秒16entry512KiBstdout1MiBstderr128KiB/nativeprotocol維持。checkpoint≠blocking中断/fullruntime/global/allwriter容量証明。
- prepare_result_index実使用/report-handoff-index3docsを同種合成dev結果・PC内path継続送信承認内で一回[skip ci] commit/push。原Git/HEAD-upstream-lsremote-clean/docpins-save/-final。追加承認質問・bypass0。
- 次unit同第2seed/layout3 core C1 c1-phase-level、新ID dev-seed7466813550306735603-layout3-core-c1-20261013。同manifest/input10、本文今回C0読取済み/次model未開始。元生成C0/次評価C1別field、新独立seedではない。
- ACTIVE/automation詳細転記0。CI381385/4130保持/querydownloadverifiertests0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了。create_native早期拒否/全7役reader禁止/caps-unknown原owner保持/追加agent禁止。未完了formal/nativeをdev開始条件へ戻さない。Sol容量・人停止は原保全後PAUSED、重複再試行なし。
