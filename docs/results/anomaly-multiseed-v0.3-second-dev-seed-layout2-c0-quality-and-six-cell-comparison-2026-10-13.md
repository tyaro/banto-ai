# 第2 dev seed・layout2 C0 qualityと6cell比較（2026-10-13）

保存済み合成dev quality-stress C0を1cell実評価。機械0/10・sensor0/10・precision0/1・正常区間誤警報1件。原全20未検出・delaynullを保持し、同seed/layout2の3候補×2条件を完成。処理成功≠性能合格・正式受入。

## 入力と実行

- run dev-seed7466813550306735603-layout2-quality-c0-20261013 / dataset anomaly-v03-dev-seed-7466813550306735603-layout-02-quality-stress。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\014\attempt-0001\result\payload\manifest.json / {"bytes": 75700, "sha256": "13a1f0848235ab785ddc31036c819927a40d5a62e7ff55adb91afe465275998a"}。同C1C2quality input10完全一致→新snapshot/fresh calibration。元生成C0と実評価C0は別field。元payload書込み・生成・replay・追加agent0。
- checkout 6e96ae7dfbc487a9086885df74b93c4486ae9d98 / 計算661b27511826fcc87cb4a02930f276afbb8f95d9 /source117/calculator16/candidatecompiled不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"} / elapsed 20.239910900010727秒 / sampled private peak 151724032B。
- observations {"bytes": 9600484, "sha256": "6938545c18ea01b4045a5248c2dbee7d6e7fc464d8491ad29e0c6ac984a4ac54"} / configuration {"bytes": 5513, "sha256": "7f5cf4f4cbdb9928b9785516eec9e4a9a6b48dc98d10f4774eea55d52ca9250a"} / manifest {"bytes": 8086, "sha256": "42305830ab11f0aac8f0ad910bf9b866a8e0aca457c32a9b13f0c4b5253c2284"} / result {"bytes": 14333331, "sha256": "2192abccfe6ebebb953d746505abd8fbb9801d2ae1f7334354eef440099737fc"}。
- C0threshold4/C1C2threshold6/operator>/persistence2・GTmatching科学不変。全rawthresholdflag確認、宣言pin≠full loaded runtime/native認証。

## 原結果

|項目|原値|
|---|---|
|machine|0/10|
|sensor|0/10|
|precision|0/1|
|clean / unmatched|1 / 1|
|source / equipment / incidents / events|1 / 1 / 20 / 40|
|available / unavailable|13889 / 511|

全20no_candidate_in_window/candidate0/causalfalse/matchednull/delaynull。delaycount0/minmaxmeanmedian原null/補完0。全20対象窓maxstreak1、19窓7全利用可/phase不能0、cycle09sensorのみ3利用可4quality不能。欠測1窓で全20未検出を説明しない。固定persistence2不成立。
48calibrated/fit_samples各0（C0経路）/calibration各290/C2stateなし48。18000input-mask対応nonok30。primaryphase471/currentquality30/previousquality10＝511。phaseタグ480とcurrentquality重複9を原保存、core480比不能増31。全不能score/residualnull・thresholdfalse、非排他的tags {"current_nonfinite": 30, "current_target_quality": 30, "mode_recipe_or_phase": 480, "previous_target_quality_or_nonfinite": 30} を重複加算しない。
clean_rate 1/3365原value 8.558692421991084 / effective 3254秒rate 8.850645359557468 / burden 1/20原value 5.0 を単純確率へしない。唯一clean source conveyor-01.motor_temperatureのequipment/source/support2score対応保存。

## 選択原対象窓

### cycle0 machine

|sample|available|score|streak|reason|
|---|---|---|---|---|
|7274|True|29.7279594988413|1|None|
|7275|True|0.6163087734886655|0|None|
|7276|True|0.20074803449937176|0|None|
|7277|True|30.691076757029478|1|None|
|7278|True|1.5522939614868552|0|None|
|7279|True|1.498496796643984|0|None|
|7280|True|0.7521036767120269|0|None|

### cycle0 sensor

|sample|available|score|streak|reason|
|---|---|---|---|---|
|7281|True|198.91005758049815|1|None|
|7282|True|0.12758388832385328|0|None|
|7283|True|0.8585138583924143|0|None|
|7284|True|198.85746536974872|1|None|
|7285|True|1.0712405400039853|0|None|
|7286|True|0.7156288384371721|0|None|
|7287|True|0.48344378342896904|0|None|

### cycle9 machine

|sample|available|score|streak|reason|
|---|---|---|---|---|
|8894|True|29.609347712415627|1|None|
|8895|True|0.49404033116224294|0|None|
|8896|True|0.2085124921587623|0|None|
|8897|True|29.381534883862965|1|None|
|8898|True|0.41941130846054003|0|None|
|8899|True|0.6120743342962355|0|None|
|8900|True|2.9443480376086404|0|None|

### cycle9 sensor

|sample|available|score|streak|reason|
|---|---|---|---|---|
|8901|True|198.63391744987058|1|None|
|8902|False|None|0|current_target_quality|
|8903|False|None|0|current_target_quality|
|8904|False|None|0|current_target_quality|
|8905|False|None|0|previous_target_quality_or_nonfinite|
|8906|True|1.467481523777979|0|None|
|8907|True|1.1729006132604036|0|None|

cycle09温度8901score198.63391744987058/streak1後、8902–04 currentquality不能・8905 previousquality不能/reset、8906/07 score<4/streak0。全20ledger/targetwindows/511不能/30nonok/episodesを-analysis、選択窓・clean episode-supportを-save保存。実入力対応・保存・状態分類不具合は観測なし。

## 同seed/layout2 3候補×2条件

|stratum|candidate|machine|sensor|precision|clean|available|source / equipment|delaycount / median|
|---|---|---|---|---|---|---|---|---|
|core|c0-diff-control|0/10|0/10|0/1|1|13920|1 / 1|0 / None|
|core|c1-phase-level|10/10|10/10|20/20|0|13920|30 / 20|20 / 1.0|
|core|c2-phase-conditional|10/10|10/10|20/20|0|13920|47 / 20|20 / 1.0|
|quality-stress|c0-diff-control|0/10|0/10|0/1|1|13889|1 / 1|0 / None|
|quality-stress|c1-phase-level|10/10|9/10|19/19|0|13889|29 / 19|19 / 1.0|
|quality-stress|c2-phase-conditional|10/10|9/10|19/19|0|13796|44 / 19|19 / 1.0|

同stratum内input10完全一致/core-quality共通3 {"dataset-manifest.json": false, "event-ledger.jsonl": false, "events.jsonl": false, "fingerprint.json": false, "generator-config.json": false, "observations.jsonl": false, "origins.json": true, "quality-mask.jsonl": false, "split-manifest.json": true, "targets.json": true}。旧5cell再compute0/source16candidatecompiled一致。C0両条件全20未検出/clean1、C1C2 core20検出/quality19検出/clean0。C2qualityのpeer追加不能93、phasepeer重複27を先行C2原保存。指標一致を全scoreepisode一致・勝者・採択へしない。
既存の一次差分＋persistence2と3観測[end exclusive]定常加算成分の内部差分相殺解釈を保持。今回全maxstreak1と整合。新式監査・正常対照再compute・閾値GT変更0。機械乗算overlayを単純加算toyと同一視しない。
C0quality保存15cells指標比較。第1seed72＋第2seed layouts0/1/2各6＝90boardcells/使用seed2。90独立datasetではない。bootstrap/統計CI/勝者/採択0。

## 証拠・次工程・正式状態

- artifacts/representative-seed2-layout2-quality-c0-20261013-* の-final/post-save・root-closed優先。DATA artifacts/representative-anomaly-evaluation/dev-seed7466813550306735603-layout2-quality-c0-20261013 / {"bytes": 27380366, "files": 19, "manifest_pin": {"bytes": 2235, "sha256": "0446d72a5afd880f13cb9d2b127f2f53b26c1dfb4d833232807a5ca5f0921142"}}。
- 旧449root/412helpers23failed389passedmissingexecution1を保持。直前C2解析早期開始FileNotFoundと別continuation・停止再開記録・全旧失敗保全。閉鎖外部固定root追記整理0/fullstdioPID単独native回収claim0。
- prepare_result_index実使用/report-handoff-index3docsを合成dev結果・PC内path継続送信承認内で一回[skip ci] commit/push、原Git-save。追加承認質問/bypass0。
- 次は同seed/layout3 core C0、新ID dev-seed7466813550306735603-layout3-core-c0-20261013。新chunk015保存manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\015\attempt-0001\result\payload\manifest.json / {"bytes": 75700, "sha256": "479787c83a7c7af9934171a66b6c3fd684689c2b908f79b483a768acf8c278cf"}、identity/input10metadataだけ選択・次観測本文未読・次model0。新独立seedではない。
- EvidenceStore16MiB512files/part256KiB/失敗2MiB16files/閉鎖512KiB4files・全writepreflight。実行900秒2GiBoutput1GiBsingle32MiBfiles32/Git30秒16entry512KiBstdout1MiBstderr128KiB/nativeprotocol維持。checkpoint≠blocking中断/fullruntime/global/allwriter証明。
- ACTIVE/automation詳細転記0/CI3813854130querydownloadverifiertests0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件最終受入未完了/create_native早期拒否/7役reader禁止/追加agent禁止/capsunknown原owner保持。未完了formal/nativeをdev開始条件に戻さない。Sol容量人停止は保全後PAUSED/重複再試行なし。
