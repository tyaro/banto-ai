# 第2 dev seed・layout3 C2 quality-stress実評価とpeer欠測波及（2026-10-13）

保存済み合成dev quality-stressをC2で1cell fresh compute。機械10/10・sensor9/10・precision19/19・正常区間誤警報0。未検出1件のdelaynullを保持。処理成功を性能保証・採択・正式受入へしない。

## 入力と実行

- run dev-seed7466813550306735603-layout3-quality-c2-20261013 / dataset anomaly-v03-dev-seed-7466813550306735603-layout-03-quality-stress。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\015\attempt-0001\result\payload\manifest.json / {"bytes": 75700, "sha256": "479787c83a7c7af9934171a66b6c3fd684689c2b908f79b483a768acf8c278cf"}。同C1 quality input10完全一致→新snapshot/fresh fit/calibration。元生成C0と実評価C2別field。元payload書込み生成replayagent0。
- checkout ca05e5af6c8fec71c83818b140a714792e01f978 / 計算661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/candidatecompiled不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"} / elapsed 33.56626529991627秒 / sampled private peak 211382272B。
- observations {"bytes": 9600460, "sha256": "7120244e968597a3d37d89fe33e3772afbdad5ae20570f479ffbb09032947652"} / configuration {"bytes": 5518, "sha256": "952b9a6ecdee8440b4fc30bd322db9e450035b6888088442a160ed1aa0455433"} / manifest {"bytes": 8079, "sha256": "ee5ce63c318bb99c9794b8097fb71a42f6676255b69cebab61f8f7badddcbded"} / result {"bytes": 25199435, "sha256": "819cfe4a52e9e052d91c42612d7cc85b24f2711db87c03b7c56f9836607f0fd2"}。
- C0threshold4/C1C2threshold6/operator>/persistence2・GTmatching科学不変。全原thresholdflag確認。宣言pin≠full loaded runtime/native認証。

## 原結果と利用不能

|項目|原値|
|---|---|
|machine|10/10|
|sensor|9/10|
|precision|19/19|
|clean / unmatched|0 / 0|
|source / equipment / incidents / events|48 / 19 / 20 / 40|
|available / unavailable|13760 / 640|
|delay count / min / max / mean / median|19 / 1 / 2 / 1.4736842105263157 / 1秒|

48calibrated/fit各600/calibration各290/C2state48。18000input-mask対応nonok30。排他的phase480/current quality30/previous quality10/peer120＝640。phaseとquality/peer重複0。非排他的tags {"current_nonfinite": 30, "current_target_quality": 30, "mode_recipe_or_phase": 480, "peer_quality_or_nonfinite": 120, "previous_target_quality_or_nonfinite": 30} を独立行として加算しない。全不能score-residualnull/thresholdfalse。
motor-01温度自身current30+previous10の40不能sampleに対応してcurrent/conveyor_speed/vibration各40peer不能＝120。原scoreとsample集合一致を-save/peer-quality-propagationへ保存。motor-01全4target1700/1800利用可、conveyor全4target1740/1800。C2core13920/480との差160、同入力C1quality13880/520との差120。
検出19だけdelay機械10各1秒/sensor9各2秒、未検出1delaynull補完0。clean_rate0/3365原0/effective3255秒rate0/burden0/20原0を単純確率へしない。

## 未検出cycle09温度の原窓

sensor spike [8910,8913)、matching window8910–8916。8910phase不能nullscore-streak0、8911–8913current quality不能、8914previous quality不能、8915–8916は6未満/streak0。全対象窓閾値超過0/persistence2不成立/candidate0/no_candidate_in_window/causalfalse/matchednull/delaynull。2利用可5不能のうちphase1。

|sample|available|score|streak|reason|
|---|---|---|---|---|
|8910|False|None|0|mode_recipe_or_phase|
|8911|False|None|0|current_target_quality|
|8912|False|None|0|current_target_quality|
|8913|False|None|0|current_target_quality|
|8914|False|None|0|previous_target_quality_or_nonfinite|
|8915|True|0.6719849096023911|0|None|
|8916|True|0.9619024069046674|0|None|

原event/incident/全対象7行/選択episodeなしを-save/selected-miss-summaryに保存。phase除外なし・欠測なしの反実仮想再compute0、GT閾値persistence matching変更0。

## 原19検出の対応

全event→対象source→matched equipment→support2原scoreを照合。38support全対象一致/利用可/score>6。機械10窓7全利用可/maxstreak3、sensor9検出窓6利用可/開始phase不能1/maxstreak2、先頭null-streak0→次score>6/streak1→さらに次score>6/streak2。全48sourceは19matched equipment内参照、内訳 {"motor-01.motor_current": 19, "motor-01.motor_temperature": 13, "motor-01.conveyor_speed": 6, "motor-01.vibration_feature": 10} / class membership {"machine": {"motor-01.conveyor_speed": 6, "motor-01.motor_current": 10, "motor-01.motor_temperature": 4, "motor-01.vibration_feature": 10}, "sensor": {"motor-01.motor_current": 9, "motor-01.motor_temperature": 9}}。
原全20ledger/窓/640不能/30nonokinput/全episodesを-analysis、matched/support38・9sensor先頭3行を-save保存。実入力対応・保存・状態分類不具合は観測なし。

## 保存済みcoreおよび同入力C1qualityとの比較

|条件|machine|sensor|precision|clean|source / equipment|available / unavailable|
|---|---|---|---|---|---|---|
|C2core|10/10|10/10|20/20|0|50 / 20|13920 / 480|
|C1quality|10/10|9/10|19/19|0|29 / 19|13880 / 520|
|C2quality|10/10|9/10|19/19|0|48 / 19|13760 / 640|

C2coreとのinput10共通3(origins/split/targets)で観測quality等は異なる。欠測だけの反実仮想全差証明へしない。同C1qualityとのinput10全一致、検出/precision/clean/burden/delay指標は一致するがavailabilityは異なる。source29対48と全scoreepisodeの一致・勝者採択を混同しない。旧core/C1quality再compute0/source16candidatecompiled一致。

## C2quality保存指標比較

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
|7466813550306735603|1|10/10|9/10|19/19|0|
|7466813550306735603|2|10/10|9/10|19/19|0|
|7466813550306735603|3|10/10|9/10|19/19|0|

保存C2quality16cellsのmanifest指標比較。第1seed72＋第2seed layouts0/1/2各6/layout3core3+quality2＝95boardcells/使用seed2。95独立datasetではない。bootstrap統計CI勝者採択0。

## 証拠・次工程・正式状態

- artifacts/representative-seed2-layout3-quality-c2-20261013-* の-final/post-save/root-closed優先。DATA artifacts/representative-anomaly-evaluation/dev-seed7466813550306735603-layout3-quality-c2-20261013 / {"bytes": 38246208, "files": 19, "manifest_pin": {"bytes": 2235, "sha256": "611cd4e6d02a36abb06299c0e816211dedd5bd9ffc977037b80aee7cb7e67d8d"}}。
- 旧476root/432helpers23failed409passedmissingexecution1不変、過去容量審査失敗/foreground読取り失敗/旧helperfailure/停止再開/誤記保持。今回は新builder/helperfailure0。閉鎖外部固定root追記整理0/fullstdioPID単独native回収claim0。
- prepare_result_index実使用/report-handoff-index3docsを同種dev結果・PC内path継続送信承認範囲で一回[skip ci] commit/push。原Git-summary。追加確認bypass0。
- 次同seed/layout3 quality-stress C0 c0-diff-control、新ID dev-seed7466813550306735603-layout3-quality-c0-20261013。同manifest/input10/本文C1C2読取済み/次model0。同条件別候補、新独立seedではない。
- EvidenceStore16MiB512files/part256KiB/失敗2MiB16files/閉鎖512KiB4files・全writepreflight。実行900秒2GiBoutput1GiBsingle32MiBfiles32/Git30秒16entry512KiBstdout1MiBstderr128KiB/nativeprotocol caps維持。checkpoint≠blocking中断/fullruntime/global/allwriter容量証明。
- ACTIVE/automation詳細転記0/CI3813854130querydownloadverifiertests0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件最終受入未完了/create_native早期拒否/全7役reader禁止/追加agent禁止/capsunknown原owner保持。未完了formal/nativeをdev開始条件へ戻さない。Sol容量人停止は保全後PAUSED。
