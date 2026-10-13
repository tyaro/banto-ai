# 第2 dev seed・layout3 C1 core実評価（2026-10-13）

保存済み合成dev coreをC1で1cell実評価。機械10/10・sensor10/10・precision20/20・正常区間誤警報0。処理成功を性能保証・採択・正式受入へしない。

## 入力と実行

- run dev-seed7466813550306735603-layout3-core-c1-20261013 / dataset anomaly-v03-dev-seed-7466813550306735603-layout-03-core。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\015\attempt-0001\result\payload\manifest.json / {"bytes": 75700, "sha256": "479787c83a7c7af9934171a66b6c3fd684689c2b908f79b483a768acf8c278cf"}。同C0 input10完全一致→新snapshot/fresh fit/calibration。元生成C0と実評価C1別field。元payload書込み生成replayagent0。
- checkout 49cb1b8bf08f8ce6d877366597f412d811c54ad6 / 計算661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/candidatecompiled不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"} / elapsed 16.96857040002942秒 / sampled private peak 152158208B。
- observations {"bytes": 9600457, "sha256": "55ebeb87fe63f7f9f337f56ca7b6d055cb4d19bd1d9acbcde6c10f3e677b2a70"} / configuration {"bytes": 5502, "sha256": "22571e0c0e10f112c7847591efa4101b61ce82d7cf0a9e6767f5dab01074c82d"} / manifest {"bytes": 8026, "sha256": "d424ba2a9b30d5d6faa16603aafc2790f49d1fcc91641f9cc6fbf629c5f80491"} / result {"bytes": 14070399, "sha256": "80cd151e4e84012c8f83427abb07d5fa7647bce3bb9c5555ebf8e5435c4df9a6"}。
- C0threshold4/C1C2threshold6/operator>/persistence2・GTmatching科学不変。全rawthresholdflag確認。宣言pin≠full loaded runtime/native認証。

## 原結果と検出対応

|項目|原値|
|---|---|
|machine|10/10|
|sensor|10/10|
|precision|20/20|
|clean / unmatched|0 / 0|
|source / equipment / incidents / events|30 / 20 / 20 / 40|
|available / unavailable|13920 / 480|
|delay count / min / max / mean / median|20 / 1 / 2 / 1.5 / 1.5秒|

48calibrated/fit各600/calibration各290/C2stateなし48。18000input-mask対応nonok0。480不能全mode_recipe_or_phase/score-residualnull/thresholdfalse、各target1740/1800利用可。
全20causal_detected/candidate1、全event→対象source→matched equipment→support2原scoreを照合。全40support対象一致/利用可/score>6。機械10件onset=start+1秒・delay1秒、センサー10件onset=start+2秒・delay2秒。
機械10窓7全利用可/phase不能0/maxstreak3。センサー10窓6利用可/開始phase不能1/maxstreak2。センサー開始行score/residualnull・streak0、次行score>6/streak1、さらに次行score>6/streak2でepisode成立。除外なしの反実仮想再compute0。
全30sourceは20matched equipment内参照、source内訳 {"motor-01.motor_temperature": 10, "motor-01.motor_current": 10, "motor-01.vibration_feature": 10} / class membership {"machine": {"motor-01.motor_current": 10, "motor-01.vibration_feature": 10}, "sensor": {"motor-01.motor_temperature": 10}}。source件数をequipment件数・誤警報件数へしない。
clean_rate0/3365原0/effective3255秒rate0/burden0/20原0を単純確率へしない。未検出delay補完0。

### cycle0 sensor

|sample|available|score|streak|reason|
|---|---|---|---|---|
|7290|False|None|0|mode_recipe_or_phase|
|7291|True|136.832903195076|1|None|
|7292|True|137.48155818742524|2|None|
|7293|True|0.11538328584153398|0|None|
|7294|True|0.7382280741574883|0|None|
|7295|True|0.5523502957551328|0|None|
|7296|True|0.9536056631782686|0|None|

### cycle0 machine

|sample|available|score|streak|reason|
|---|---|---|---|---|
|7311|True|75.05043803432586|1|None|
|7312|True|75.81380643168114|2|None|
|7313|True|75.77607798682851|3|None|
|7314|True|0.5288660771206829|0|None|
|7315|True|0.6964458818948359|0|None|
|7316|True|0.009702271310164845|0|None|
|7317|True|0.518985936429871|0|None|

### cycle2 sensor

|sample|available|score|streak|reason|
|---|---|---|---|---|
|7650|False|None|0|mode_recipe_or_phase|
|7651|True|136.4167360227475|1|None|
|7652|True|135.7721711254581|2|None|
|7653|True|0.24173313906200689|0|None|
|7654|True|0.3898201433187556|0|None|
|7655|True|0.7376145598985626|0|None|
|7656|True|0.719532931322024|0|None|

### cycle2 machine

|sample|available|score|streak|reason|
|---|---|---|---|---|
|7671|True|74.6579574998458|1|None|
|7672|True|75.26909655557903|2|None|
|7673|True|75.6430853865243|3|None|
|7674|True|1.052016841878442|0|None|
|7675|True|0.2292803437009753|0|None|
|7676|True|0.46209458283248256|0|None|
|7677|True|2.0239219859204653|0|None|

全20ledger/targetwindows/480不能/episodesを-analysis、全20matched/support40・sensor先頭3行×10を-saveへ保存。実入力対応・保存・状態分類不具合は観測なし。

## 同入力C0と保存済みC1比較

|candidate|machine|sensor|precision|clean|
|---|---|---|---|---|
|C0|0/10|0/10|0/1|1|
|C1|10/10|10/10|20/20|0|

同seed/layout3/core input10一致、旧C0再compute0/source16candidatecompiled一致。旧C0は機械窓全利用可・センサー開始phase不能1・全maxstreak1/all20miss原delaynull。一次差分＋persistence2と定常加算成分の内部差分相殺の既存解釈を保持。新式監査・正常対照再compute・thresholdGT変更0。
C1core保存16cellsのmanifest指標比較。第1seed72＋第2seed layouts0/1/2各6＋layout3 C0C1core2＝92boardcells/使用seed2。92独立datasetではない。bootstrap統計CI勝者採択0。

## 証拠・次工程・正式状態

- artifacts/representative-seed2-layout3-core-c1-20261013-* の-final/post-save・root-closed優先。DATA artifacts/representative-anomaly-evaluation/dev-seed7466813550306735603-layout3-core-c1-20261013 / {"bytes": 27110749, "files": 19, "manifest_pin": {"bytes": 2232, "sha256": "603b22d40e7fb4bd9d825dca1877934f9dee9138c2c15caf1c7d6ae813b52e9b"}}。
- 旧459root/420helpers23failed397passedmissingexecution1保全。旧sourcebuilder scope失敗・C2解析FileNotFound/別継続・KeyError/停止再開・誤記を保持。今回新sourcebuilderfailure0/newhelperfailure0。閉鎖外部固定root追記整理0/fullstdioPID単独native回収claim0。
- prepare_result_index実使用、report/handoff/index3docsを同種合成dev結果・PC内path継続送信承認内で一回[skip ci] commit/push、原Git-save。追加承認質問bypass0。
- 次unit同seed/layout3 core C2、新ID dev-seed7466813550306735603-layout3-core-c2-20261013。同manifest/input10/本文C0C1読取済み・未開始。新独立seedではない。
- EvidenceStore16MiB512files/part256KiB/失敗2MiB16files/閉鎖512KiB4files・全writepreflight。実行900秒2GiBoutput1GiBsingle32MiBfiles32/Git30秒16entry512KiBstdout1MiBstderr128KiB/nativeprotocol維持。checkpoint≠blocking中断/fullruntime/global/allwriter容量証明。
- ACTIVE/automation詳細転記0/CI3813854130querydownloadverifiertests0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件最終受入未完了/create_native早期拒否/7役reader禁止/追加agent禁止/capsunknown原owner保持。未完了formal/nativeをdev開始条件へ戻さない。Sol容量人停止は保全後PAUSED/重複再試行なし。
