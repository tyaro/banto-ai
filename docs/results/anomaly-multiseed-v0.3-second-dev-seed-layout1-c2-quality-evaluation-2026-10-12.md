# 第2 dev seed・layout1 C2 quality-stress実評価（2026-10-12）

保存済み合成dev quality-stressをC2で1回fresh compute。機械10/10・センサー9/10・precision19/19・正常区間誤警報0件。未検出1件と原delay nullを保持。処理成功を性能保証・採択・正式受入にしない。

## 入力と実行

- run dev-seed7466813550306735603-layout1-quality-c2-20261012 / dataset anomaly-v03-dev-seed-7466813550306735603-layout-01-quality-stress。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\013\attempt-0001\result\payload\manifest.json / {"bytes": 75699, "sha256": "d4743f431240dee56e5ead1d0709a998e502b6a7e8a4aecd3f00468dced8bd81"}。seed7466813550306735603/layout1/quality-stress/dev、同C1quality input10pin一致→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics保存。
- 元生成C0・実評価C2は別field。元payload書込み・新生成・replay・追加agent0。
- checkout 279ff2083a3de54f17d3bfbc8d02dae538a06599、計算661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/candidate-compiled config不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 29.328248500009067秒/privatepeak 211423232B。
- observations {"bytes": 9600492, "sha256": "ef8b9dcc9138899b773ce5aebb07592211e679e71d8578f4be21f97eb6b609a6"}、configuration {"bytes": 5518, "sha256": "4d91afbd72572701c780d545a17904d4b8c009fc2f96f087142c4561e70ffcb5"}、manifest {"bytes": 8065, "sha256": "8da8f556921ba2ea7c60629cc5824d79c1ad867f755641dc887116ea32ad3ff7"}、evaluation {"bytes": 25212664, "sha256": "db73a8ecb7be1f6954fb0f03d4d5a26ef594ecf3d63bb54c1b5872c42cb82677"}。宣言source pinはfull loaded runtime/native認証ではない。
- C0 threshold4/C1・C2 threshold6/operator>/persistence2・GT/matching/science不変。原score閾値判定を全行確認。

## 原結果とpeer利用不能

|項目|原値|
|---|---|
|machine|10/10|
|sensor|9/10|
|precision|19/19|
|clean / unmatched|0 / 0|
|source / equipment / incidents / events|56 / 19 / 20 / 40|
|available / unavailable scores|13760 / 640|

48profiles全calibrated/fit各600/calibration各290/C2stateあり48。18000observations-mask対応、non-ok30行。primary排他的不能phase480/peer quality120/current quality30/previous quality10＝640。全不能score-residual null/thresholdfalse。
非排他的tags {"current_nonfinite": 30, "current_target_quality": 30, "mode_recipe_or_phase": 480, "peer_quality_or_nonfinite": 120, "previous_target_quality_or_nonfinite": 30} は重複加算しない。motor-01温度はcurrent30＋previous10、それに加え同motorのcurrent/conveyor_speed/vibration各40peer不能＝120。motor-01四target各1700/1800、conveyor-01四target各1740/1800利用可。C2core比160不能増/C1quality比120不能増。
cycle09の8865–8868で温度current/previous quality不能が他3targetのpeer不能12行へ波及。元8864current score12.723376172230127/streak1・vibration6.962351390636604/streak1の後、peer不能で両者もreset。原全120peer行と選択12行を-save/peer-quality-propagationへ保存。利用不能の増加を新独立観測や誤警報件数へしない。
検出19件だけdelaycount19/min=max=mean=median1秒。未検出1件delaynull補完0。clean_rate0/3365原0/effective3255秒rate0/burden0/20原0。率・burdenを単純確率へしない。

## 未検出cycle09温度の原スコア

sensor spike [8864,8867)、matching window8864–8870。8864score147.74342663246256/streak1→8865–8867current quality不能→8868previous quality不能でreset→8869score1.1188959557100555/8870score1.431822893423544はいずれも6未満/streak0。固定persistence2未成立、candidate0/no_candidate_in_window/causalfalse/matchednull/delaynull。対象窓内phase不能0。

|sample|available|score|streak|理由|
|---|---|---|---|---|
|8864|True|147.74342663246256|1|None|
|8865|False|None|0|current_target_quality|
|8866|False|None|0|current_target_quality|
|8867|False|None|0|current_target_quality|
|8868|False|None|0|previous_target_quality_or_nonfinite|
|8869|True|1.1188959557100555|0|None|
|8870|True|1.431822893423544|0|None|

原event/incident/全targetwindow/選択episodeなしを-save/selected-miss-summaryへ保存。GT・閾値・persistence・matching変更で成功へ補わない。

## 原19検出と56source

machine10・sensor9の原event→対象source→matched equipment→support2scoreを照合、全38supportは対象一致/利用可/score>6。各onset=start+1秒。machine10窓とsensor9窓は7全利用可/maxstreak3、sensor未検出1窓は3利用可4不能/maxstreak1。
全source56はmatched equipment19内に参照。source内訳 {"motor-01.motor_current": 19, "motor-01.motor_temperature": 18, "motor-01.vibration_feature": 19}、class membership {"machine": {"motor-01.motor_current": 10, "motor-01.motor_temperature": 9, "motor-01.vibration_feature": 10}, "sensor": {"motor-01.motor_current": 9, "motor-01.motor_temperature": 9, "motor-01.vibration_feature": 9}}。source56をequipment56や誤警報56へしない。原全20incident/target窓/全640不能/30non-ok入力/全episodesを-analysis、全matched target/supportを-save保存。実入力対応・保存・状態分類の不具合は観測なし。

## 保存済み比較

|条件|machine|sensor|precision|clean|available / unavailable|source / equipment|
|---|---|---|---|---|---|---|
|C2 core|10/10|10/10|20/20|0|13920 / 480|59 / 20|
|C1 quality|10/10|9/10|19/19|0|13880 / 520|29 / 19|
|C2 quality|10/10|9/10|19/19|0|13760 / 640|56 / 19|

C1qualityとC2qualityは同input10。C2coreとqualityは同seed/layoutの別stratum、10input pins一致 {"dataset-manifest.json": false, "event-ledger.jsonl": false, "events.jsonl": false, "fingerprint.json": false, "generator-config.json": false, "observations.jsonl": false, "origins.json": true, "quality-mask.jsonl": false, "split-manifest.json": true, "targets.json": true}、共通3fileはorigins/split-manifest/targets。旧core/C1モデル再計算0/source16candidatecompiled一致。別入力coreの全差を欠測だけの反実仮想証明へしない。C1/C2同qualityの指標一致を全スコア・sourceepisode一致や勝者へしない。

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

保存manifest指標14C2quality cellsを比較、旧モデル再計算0。第1seed全72＋第2seed layout0全6/layout1 core全3/quality C1C2二件＝83boardcells/実使用seed2。83独立datasetではない。bootstrap/統計CI/勝者/採択0。

## 証拠・次工程・正式状態

- records/analysis/save/final: artifacts/representative-seed2-layout1-quality-c2-20261012-*。最終-final/post-saveとroot-closed優先。DATA artifacts/representative-anomaly-evaluation/dev-seed7466813550306735603-layout1-quality-c2-20261012 / {"bytes": 38259680, "files": 19, "manifest_pin": {"bytes": 2235, "sha256": "d2864738fa7da820429f01e0333a1ba52f370938ca1de395d78b5fa2577cb236"}}。
- 旧409root/380helper/21failed359passed/missingexecution1保持。旧失敗・誤記を保持し閉鎖・外部固定root追記整理0/fullstdio/native回収claim0。
- EvidenceStore16MiB512files/part256KiB/失敗予備2MiB16files/閉鎖512KiB4files、script・失敗・閉鎖を含む全write preflight。実行900秒2GiBoutput1GiBsingle32MiBfiles32/Git累積30秒16entry512KiBstdout1MiBstderr128KiB/nativeprotocol維持。checkpoint≠blocking中断/fullruntime/global/allwriter容量証明。
- prepare_result_index実使用/report-handoff-index3docsを同種合成dev結果・PC内path継続送信承認内で一回[skip ci] commit/push。原Git/HEAD-upstream-lsremote-clean/docpins-save/-final。追加承認質問・bypass0。
- 次unit同seed/layout1/quality-stress C0 c0-diff-control、新ID dev-seed7466813550306735603-layout1-quality-c0-20261012。同manifest/input10、本文C1C2読取済み・次model未開始。元生成C0/次評価C0別field、新独立seedではない。完成83cellを反復しない。
- ACTIVE/automation詳細転記0。CI381385/4130保持/querydownloadverifiertests0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了。create_native早期拒否/全7役reader禁止/caps-unknown原owner保持/追加agent禁止。未完了formal/nativeをdev開始条件へ戻さない。Sol容量・人停止は原保全後PAUSED、重複再試行なし。

## 最終metadata失敗の保全と継続

実評価と報告push後、元-final helperはpost-save生成中のKeyError current_foreground_metadata_readoutでfailed。前回の保存field名はprior_foreground_metadata_readout。元script/traceback/failure/creation-live-execution failedと原CIM観測を閉鎖して保持し、原helper/script/model/Git再実行0。元root16file216787B/closure {"bytes": 415, "sha256": "c7312e23fd368987345b14c9b159997be87d9da6b6b2bf1d151967d950b268a7"}。
補正文書の原Gitと失敗referenceは artifacts/representative-seed2-layout1-quality-c2-20261012-final-metadata-correction-save。最新post-save/閉鎖は同-final-metadata-continuationを優先。新metadata組立てでは旧field参照一箇所だけをprior_foreground_metadata_readoutへ訂正。原failedを書換えず、モデル/CI/native/Sol容量失敗へしない。全writepreflight・新専用rootを維持。
この追補2文書も継続送信承認内で一回[skip ci]。正式未完了、次C0未開始、同kind結果/PCpath承認範囲と実行caps不変。
