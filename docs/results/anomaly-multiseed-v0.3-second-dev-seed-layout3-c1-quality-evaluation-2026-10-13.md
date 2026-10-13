# 第2 dev seed・layout3 C1 quality-stress実評価（2026-10-13）

保存済み合成dev quality-stressをC1で1回fresh compute。機械10/10・センサー9/10・precision19/19・正常区間誤警報0件。未検出1件と原delay nullを保持。処理成功を性能保証・採択・正式受入へしない。

## 入力と実行

- run dev-seed7466813550306735603-layout3-quality-c1-20261013 / dataset anomaly-v03-dev-seed-7466813550306735603-layout-03-quality-stress。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\015\attempt-0001\result\payload\manifest.json / {"bytes": 75700, "sha256": "479787c83a7c7af9934171a66b6c3fd684689c2b908f79b483a768acf8c278cf"}。seed7466813550306735603/layout3/quality-stress/dev、input10pin→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics保存。
- 元生成C0/実評価C1別field。元payload書込み・新生成・replay・追加agent0。checkout f067d5bd6a4966707dde69f715cf60c8220c9c87、計算661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/candidatecompiled不変。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"} / elapsed 38.64196399995126秒 / sampled private peak 152977408B。
- observations {"bytes": 9600460, "sha256": "7120244e968597a3d37d89fe33e3772afbdad5ae20570f479ffbb09032947652"} / configuration {"bytes": 5512, "sha256": "a6717a76bdc14ff726ca2bac9fc217ac02948cfdfcf92f06bddcb15f4dd6672c"} / manifest {"bytes": 8073, "sha256": "8300d11c8b2b456012ffe2e5d3fd2b4f5b40f61e9a63e52a58f45a30353e63bc"} / evaluation {"bytes": 14508837, "sha256": "a11f1413eeb4c9c457081a31da90c1c95863f885cbc6d158e92facb7ec651b8c"}。
- C0threshold4/C1C2threshold6/operator>/persistence2・GTmatching科学不変。全raw閾値flag確認。宣言pin≠full loaded runtime/native認証。

## 原結果

|項目|原値|
|---|---|
|machine|10/10|
|sensor|9/10|
|precision|19/19|
|clean / unmatched|0 / 0|
|source / equipment / incidents / events|29 / 19 / 20 / 40|
|available / unavailable|13880 / 520|
|delay count / min / max / mean / median|19 / 1 / 2 / 1.4736842105263157 / 1秒|

48calibrated/fit各600/calibration各290/C2stateなし48。18000input-mask対応nonok30。排他的primaryphase480/current quality30/previous quality10＝520。phaseとquality不能の重複0、core比不能増40。非排他的tags {"current_nonfinite": 30, "current_target_quality": 30, "mode_recipe_or_phase": 480, "previous_target_quality_or_nonfinite": 30} は重複加算しない。全不能score-residualnull/thresholdfalse。温度1700/1800利用可、他7target1740/1800。
検出19件だけのdelayを保存、未検出1件delaynull補完0。機械10delay1秒・sensor9delay2秒。clean_rate0/3365原0/effective3255秒rate0/burden0/20原0を単純確率へしない。

## 未検出cycle09温度の原窓

sensor spike [8910,8913)、matching window8910–8916。8910はmode_recipe_or_phaseでscore/residualnull。8911–8913current quality不能、8914previous quality不能、いずれもstreak0。8915score0.7119662554614771/8916score1.0714004008988312はいずれも6未満/streak0。対象窓には閾値超過0、固定persistence2不成立/candidate0/no_candidate_in_window/causalfalse/matchednull/delaynull。

|sample|available|score|streak|reason|
|---|---|---|---|---|
|8910|False|None|0|mode_recipe_or_phase|
|8911|False|None|0|current_target_quality|
|8912|False|None|0|current_target_quality|
|8913|False|None|0|current_target_quality|
|8914|False|None|0|previous_target_quality_or_nonfinite|
|8915|True|0.7119662554614771|0|None|
|8916|True|1.0714004008988312|0|None|

原event/incident/対象7行/選択episodeなしを-save/selected-miss-summaryへ保存。GT・閾値・persistence・matching変更、除外なしや欠測なしの反実仮想再compute0。

## 検出19件と同seed core比較

全19event→対象source→matched equipment→support2原scoreを照合、全38support対象一致/利用可/score>6。機械10窓7全利用可/maxstreak3。sensor9窓6利用可/開始phase不能1/maxstreak2、開始nullscore-streak0→次行score>6/streak1→さらに次行score>6/streak2で成立。全source29は19matched equipment内参照、内訳 {"motor-01.motor_temperature": 9, "motor-01.motor_current": 10, "motor-01.vibration_feature": 10} / class membership {"machine": {"motor-01.motor_current": 10, "motor-01.vibration_feature": 10}, "sensor": {"motor-01.motor_temperature": 9}}。
同seed/layout3 C1 core保存は機械10/10・sensor10/10・precision20/20・clean0、13920利用可480不能。10input pins共通3(origins/split-manifest/targets)、観測quality等は異なる。同一入力・欠測だけの反実仮想証明へしない。旧core再compute0/source16candidatecompiled一致。
原全20incident/窓/全520不能/30nonokinput/全episodesを-analysis、全matched/supportと9sensor先頭3行を-saveへ保存。入力対応・保存・状態分類の実経路不具合は観測なし。

## 保存済みC1 quality比較

|seed|layout|machine|sensor|precision|clean|
|---|---|---|---|---|---|
|2486912926863618161|0|10/10|9/10|19/19|0|
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
|7466813550306735603|0|10/10|9/10|19/19|0|
|7466813550306735603|1|10/10|9/10|19/19|0|
|7466813550306735603|2|10/10|9/10|19/19|0|
|7466813550306735603|3|10/10|9/10|19/19|0|

C1quality保存16cellsのmanifest指標比較のみ。第1seed全72＋第2seed layouts0/1/2各6/layout3core3+qualityC1一件＝94boardcells/使用seed2。94独立datasetではない。bootstrap/統計CI/勝者/採択0。

## 証拠・次工程・正式状態

- artifacts/representative-seed2-layout3-quality-c1-20261013-* の-final/post-save/root-closed優先。DATA artifacts/representative-anomaly-evaluation/dev-seed7466813550306735603-layout3-quality-c1-20261013 / {"bytes": 27555580, "files": 19, "manifest_pin": {"bytes": 2235, "sha256": "62fe13d1462deaff5136721ae0f48b016f79ed8c152d989f56d627ec03a51aaf"}}。
- 旧471root/428helpers23failed405passedmissingexecution1と前回容量審査失敗を保持。今回foreground読取りpath日付誤指定/FileNotFoundとeventにseedfieldを要求したKeyErrorを選択tool証拠として保存、full creation/全stdioなし・instrumented helper/model/CI/native失敗へしない。元helper/完成モデル再実行0。
- EvidenceStore16MiB512files/part256KiB/失敗予備2MiB16files/閉鎖512KiB4files、全writepreflight。実行900秒2GiBoutput1GiBsingle32MiBfiles32/Git30秒16entry512KiBstdout1MiBstderr128KiB/nativeprotocol維持。checkpoint≠blocking中断/fullruntime/global/allwriter容量証明。
- prepare_result_index実使用、report-handoff-index3docsを同種dev結果・PC内path継続送信承認内で一回[skip ci] commit/push。原Git-summary。追加承認質問bypass0。
- 次同seed/layout3 quality-stress C2、新ID dev-seed7466813550306735603-layout3-quality-c2-20261013。同manifest/input10/観測本文C1読取済み/次model0。元生成C0と次評価C2別field、新独立seedではない。
- ACTIVE/automation詳細転記0/CI3813854130querydownloadverifiertests0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件最終受入未完了/create_native早期拒否/7役reader禁止/追加agent禁止/capsunknown原owner保持。未完了formal/nativeをdev開始条件へ戻さない。Sol容量人停止は保全後PAUSED。
