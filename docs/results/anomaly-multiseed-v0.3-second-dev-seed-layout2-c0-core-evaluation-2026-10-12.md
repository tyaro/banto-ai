# 第2 dev seed・layout2 C0 core実評価（2026-10-12）

保存済み合成dev layout2 coreをC0で1回fresh compute。機械0/10・センサー0/10・precision0/1・正常区間誤警報1件。全20未検出と原delay nullを保持。処理成功を性能保証・採択・正式受入にしない。

## 入力と実行

- run dev-seed7466813550306735603-layout2-core-c0-20261012 / dataset anomaly-v03-dev-seed-7466813550306735603-layout-02-core。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\014\attempt-0001\result\payload\manifest.json / {"bytes": 75700, "sha256": "13a1f0848235ab785ddc31036c819927a40d5a62e7ff55adb91afe465275998a"}。seed7466813550306735603/layout2/core/dev、input10pin→新snapshot→fresh calibration→原profiles/scores/episodes/events/incidents/metrics保存。
- 元生成C0・実評価C0は別field。元payload書込み・新生成・replay・追加agent0。同seedの別layoutで新独立seedではない。
- checkout a7cda5df060bae97f300a3e1f2b24434e006ed62、計算661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/candidate-compiled config不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 19.24390559992753秒/privatepeak 149381120B。
- observations {"bytes": 9600481, "sha256": "9c35ac965771056b42b34064f191a4845fb1f2265cbdb858fb04a21a826642d9"}、configuration {"bytes": 5503, "sha256": "d5c9f207b007a5071e30661fb35ceecd5d7586ff131365381b558220d9f06e49"}、manifest {"bytes": 8052, "sha256": "ab237b43919196613fe11789242370e5f975ee295de6b693c5674d5cdc6ab531"}、evaluation {"bytes": 13896188, "sha256": "4f56fef529fa658d946914f555b1f7705827eae2b415339967d5443ba559fd62"}。宣言source pinはfull loaded runtime/native認証ではない。
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
全20no_candidate_in_window/candidate0/causalfalse/matchednull/delaynull。delaycount0/minmaxmeanmedian原null、補完0。全20対象窓7全利用可/phase不能0/maxstreak1、固定persistence2不成立。今回の対象窓内欠測やphase除外を未検出理由にしない。
clean_rate 1/3365原value 8.558692421991084、effective 3254秒/rate 8.850645359557468、burden 1/20原value 5.0。率・burdenを単純確率へしない。唯一clean source conveyor-01.motor_temperatureのequipment/source/support原対応を-save/episode-summaryへ保存。

## 選択原target窓

### cycle0 machine

異常区間[7274,7277)、magnitude 0.55、matching end 7280。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7274|True|29.7279594988413|1|None|
|7275|True|0.6163087734886655|0|None|
|7276|True|0.20074803449937176|0|None|
|7277|True|30.691076757029478|1|None|
|7278|True|1.5522939614868552|0|None|
|7279|True|1.498496796643984|0|None|
|7280|True|0.7521036767120269|0|None|

### cycle0 sensor

異常区間[7281,7284)、magnitude 8.0、matching end 7287。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7281|True|198.91005758049815|1|None|
|7282|True|0.12758388832385328|0|None|
|7283|True|0.8585138583924143|0|None|
|7284|True|198.85746536974872|1|None|
|7285|True|1.0712405400039853|0|None|
|7286|True|0.7156288384371721|0|None|
|7287|True|0.48344378342896904|0|None|

### cycle9 machine

異常区間[8894,8897)、magnitude 0.55、matching end 8900。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|8894|True|29.609347712415627|1|None|
|8895|True|0.49404033116224294|0|None|
|8896|True|0.2085124921587623|0|None|
|8897|True|29.381534883862965|1|None|
|8898|True|0.41941130846054003|0|None|
|8899|True|0.6120743342962355|0|None|
|8900|True|2.9443480376086404|0|None|

### cycle9 sensor

異常区間[8901,8904)、magnitude 8.0、matching end 8907。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|8901|True|198.63391744987058|1|None|
|8902|True|0.8534010715050421|0|None|
|8903|True|0.7934375126702928|0|None|
|8904|True|198.51118574521908|1|None|
|8905|True|0.18484213759209364|0|None|
|8906|True|1.467481523777979|0|None|
|8907|True|1.1729006132604036|0|None|

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

15C0core保存manifest指標比較/source16candidatecompiled一致、旧モデル再計算0。第1seed全72＋第2seed layout0/1各6＋layout2 C0core1＝85boardcells/実使用seed2。85独立datasetではない。layout2残5cell未完成/bootstrap統計CI勝者採択0。

## 証拠・次工程・正式状態

- records/analysis/save/final: artifacts/representative-seed2-layout2-core-c0-20261012-*。最終-final/post-save/root-closed優先。DATA artifacts/representative-anomaly-evaluation/dev-seed7466813550306735603-layout2-core-c0-20261012 / {"bytes": 26936837, "files": 19, "manifest_pin": {"bytes": 2232, "sha256": "381a9ce252586371ec9cd937c843d2d5e8b389b17823b80c30d7dc52fada125b"}}。
- 旧421root/390helper/22failed368passed/missingexecution1保持。旧C2quality final KeyError failed/root/原scriptとcontinuation保持。閉鎖・外部固定root追記整理0/fullstdio/native回収claim0。
- EvidenceStore16MiB512files/part256KiB/失敗予備2MiB16files/閉鎖512KiB4files、script・失敗・閉鎖全write preflight。実行900秒2GiBoutput1GiBsingle32MiBfiles32/Git累積30秒16entry512KiBstdout1MiBstderr128KiB/nativeprotocol維持。checkpoint≠blocking中断/fullruntime/global/allwriter容量証明。
- prepare_result_index実使用/report-handoff-index3docsを同種合成dev結果・PC内path継続送信承認内で一回[skip ci] commit/push。原Git/HEAD-upstream-lsremote-clean/docpins-save/-final。追加承認質問・bypass0。
- 次unit同第2seed/layout2 core C1 c1-phase-level、新ID dev-seed7466813550306735603-layout2-core-c1-20261012。同manifest/input10、本文今回C0読取済み/次model未開始。元生成C0/次評価C1別field、新独立seedではない。
- ACTIVE/automation詳細転記0。CI381385/4130保持/querydownloadverifiertests0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了。create_native早期拒否/全7役reader禁止/caps-unknown原owner保持/追加agent禁止。未完了formal/nativeをdev開始条件へ戻さない。Sol容量・人停止は原保全後PAUSED、重複再試行なし。
