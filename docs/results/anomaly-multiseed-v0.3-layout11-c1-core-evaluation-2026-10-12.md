# layout11 C1 core実評価（2026-10-12）

保存済みlayout11 coreを既存CLI C1で1回fresh評価した。exit0/complete/1cell success、機械10/10・sensor10/10・precision20/20・clean誤警報0。機械10件の検出遅延は各1秒、センサー10件は各2秒。単一合成devの結果と処理successを性能保証・勝者・採択・正式受入にしない。

## 入力と結果の対応

- run dev-layout11-core-c1-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-11-core。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\011\attempt-0001\result\payload\manifest.json、pin {"bytes": 75714, "sha256": "ce20f3d40c4e286df89ac3fe4ae6411763fec86f573e9ca67073e2acf2e92177"}。
- seed2486912926863618161/layout11/core/dev、同C0 input10 pins一致→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics保存。
- 元生成candidate C0 / 実評価candidate C1を別fieldで保持。元payload書込み・新dataset生成・replay・追加agent0。
- actual checkout 68fc7140b9623e3f5ccb0d08c9a9fdb38551075e、計算661b27511826fcc87cb4a02930f276afbb8f95d9・science117不変。宣言calculator16/candidate/compiled config一致はfull loaded runtime/native認証ではない。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 18.715148799936287秒/private peak 150966272B。
- observations {"bytes": 9600597, "sha256": "d8ac35000efdd0b2de6f0205173d7a4a115567b89ff8cb0089cae77ab9736ef3"}、configuration {"bytes": 5503, "sha256": "e5032fc62acdb110c87a051d278d1ec89a237f7d70296364c5da9f0ede4259da"}、manifest {"bytes": 8005, "sha256": "cb34c9e90027c8feb10af76b79379973f8e1e1746065282ce821e9e7c927dd08"}、evaluation {"bytes": 14073124, "sha256": "824d91c08b2cecd5cb7c1b10421a5d90a6c96d0515ced388d37bf26204247799"}、numerical {"bytes": 14067626, "sha256": "dba289e187b10da26c1247e2f06c44f8de99a9613240f24f0a5113b2e36df44d"}。
- candidate閾値はC0 4.0 / C1 6.0 / C2 6.0、operator> / persistence2。全14400scoreの原threshold_exceededを今回C1実値6.0へ照合、設定・GT・matching・科学式の変更0。

## 同入力C0との原指標比較

|candidate|machine|sensor|precision|clean|delay count / mean / median|
|---|---|---|---|---|---|
|C0（保存済み）|0/10|1/10|1/3|2|1 / 2.0 / 2.0秒|
|C1（今回）|10/10|10/10|20/20|0|20 / 1.5 / 1.5秒|

C0原結果の再計算0。両candidateの観測・targets・origin・split・quality等10入力pinは完全一致、固定candidate config/compiled configも一致。旧C0の1検出は固定matchingの原ラベルを保持し、そのsupport内で一定加算が差分相殺される点は [C0報告](anomaly-multiseed-v0.3-layout11-c0-core-evaluation-2026-10-12.md) と新C0-saveのdetection-interpretation labelを参照する。今回C1の結果でC0の定義・閾値・baselineを変更していない。

## 利用可能性・検出遅延

48profilesすべてcalibrated、fit_samples各600/calibration_samples各290。18000observationsとquality-maskのequipment/quality対応、non-ok0。14400scoresの利用可13920、不能480は全mode_recipe_or_phase。不能はscore/residual null・thresholdfalseで、欠落やsuccessへの補完なし。
全20incidentsはcausal_detected=true / candidate_count1。原event targetとselected_source full_target、source episode idとequipment membership、equipment matched_event_idを照合した。未検出0、source30/equipment20の全sourceが匹配equipmentに参照されている。source内訳 {"conveyor-01.motor_temperature": 10, "conveyor-01.conveyor_speed": 10, "conveyor-01.vibration_feature": 10}、機械episodeのsource内訳 {"conveyor-01.conveyor_speed": 10, "conveyor-01.vibration_feature": 10}、センサーepisode {"conveyor-01.motor_temperature": 10}。複数sourceを追加equipment誤警報として数えない。
機械10窓は各7rows全利用可/maxstreak3、onset=start+1秒/support2score。センサー10窓は各6rows利用可+開始1row phase不能/maxstreak2、onset=start+2秒/support2score。センサー開始rowは不能としてstreak0、残る2異常観測の連続閾値超過でepisodeが成立した。全機械遅延1秒・全センサー遅延2秒、20検出条件付きmin1/max2/mean1.5/median1.5秒。全20検出なので未検出delayの代入0。

### cycle00 sensorの原スコア窓

|sample|available|score|streak|reason|
|---|---|---|---|---|
|7350|False|None|0|mode_recipe_or_phase|
|7351|True|164.67004498460383|1|None|
|7352|True|164.4857952175422|2|None|
|7353|True|1.8208224487099873|0|None|
|7354|True|1.567104010671072|0|None|

cycle00/02の機械・センサー原窓とepisodeリンクを-saveのtarget-onset-summaryへ保存した。全20原event/incident、equipmentごとの四target窓、source/equipment、全不能streamは-analysisへ自動分割して保存。
clean_rate0/3365原0.0、effective3255秒/rate0.0、false_alert_burden0/20原0.0。原valueの定義を一般の確率へ読み替えない。検出・episode状態分類と入力/出力対応に実経路の不具合は観測されなかった。

## 保存済みC1 core比較と完成範囲

|layout|machine|sensor|precision|clean|
|---|---|---|---|---|
|0|10/10|10/10|20/20|0|
|1|10/10|10/10|20/20|0|
|2|10/10|10/10|20/20|0|
|3|10/10|10/10|20/20|0|
|4|10/10|10/10|20/20|0|
|5|10/10|10/10|20/20|0|
|6|0/10|10/10|10/20|0|
|7|10/10|10/10|20/20|0|
|8|10/10|10/10|20/20|0|
|9|10/10|10/10|20/20|0|
|10|10/10|10/10|20/20|0|
|11|10/10|10/10|20/20|0|

旧layout0–10 C1coreと今回layout11 C1coreで12cells、同layout11 C0を加えた原manifest比較は13cells。同devseedでlayout差、input pins差を保持、旧model再compute0。完成boardは旧67＋今回1＝68cells。layout0–10の3候補×2strata保存を保持し、layout11はC0core/C1coreだけ。同合成devseed1、68独立datasetではない。bootstrap・統計CI・勝者・採択0。

## 記録・Git保存・次unit

- model artifacts/representative-layout11-core-c1-20261012-records、analysis artifacts/representative-layout11-core-c1-20261012-analysis、docs/Git artifacts/representative-layout11-core-c1-20261012-save、最終同-finalのpost-saveを優先。
- analysis item bytes/parts {"all-episodes": {"bytes": 38373, "parts": 1}, "analysis": {"bytes": 467634, "parts": 2}, "analysis.finished": {"bytes": 37, "parts": 1}, "analysis.started": {"bytes": 17, "parts": 1}, "data-closure": {"bytes": 135, "parts": 1}, "data-closure.finished": {"bytes": 37, "parts": 1}, "data-closure.started": {"bytes": 17, "parts": 1}, "helper-execution": {"bytes": 267, "parts": 1}, "helper-live": {"bytes": 213, "parts": 1}, "incident-ledger": {"bytes": 33718, "parts": 1}, "matched-targets": {"bytes": 64238, "parts": 1}, "non-ok-input-records": {"bytes": 189, "parts": 1}, "policy": {"bytes": 211, "parts": 1}, "script": {"bytes": 12620, "parts": 1}, "selected-windows": {"bytes": 1001420, "parts": 4}, "unavailable-scores": {"bytes": 461979, "parts": 2}}。
- DATA artifacts/representative-anomaly-evaluation/dev-layout11-core-c1-20261012/root-closed.json / {"bytes": 27114895, "files": 19, "manifest_pin": {"bytes": 2226, "sha256": "cdc4746cce2f5b3a29e785606fed0b688c286af07ca23651fdbc68c8775b6bdd"}}。
- 共有EvidenceStoreの新記録16MiB/512files、part256KiB、失敗2MiB/16files・閉鎖512KiB/4files予備枠と全新write preflightを維持。閉鎖/外部固定root追記整理0。過去failedと原script/stdio状態は保持、完成model/replay/tests/CI再実行0。
- prepare_result_indexで索引を生成しreport/handoff/index3文書を同種合成dev結果・ユーザー名を含むPC内pathのGitHub継続送信承認内で一回[skip ci] commit/push。原GitbytesとHEAD/upstream/lsremote/clean/docpinsは-save/-finalへ保存。
- 次unitは同保存layout11/core C2 c2-phase-conditional、新ID dev-layout11-core-c2-20261012。同manifest/input10、本文C0/C1で読取済み、次model未開始、生成candidate C0と実評価C2は別field。
- 実行900秒/2GiB/output1GiB/single32MiB/files32、Git累積30秒/16entry/512KiB/stdout1MiB/stderr128KiB、protocol/native上限不変。checkpointはblocking中断・full runtime閉包・global/allwriter容量証明ではない。
- ACTIVE、automation詳細転記0。完成CI381385/4130保存、今回query/download/verifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了。create_native早期拒否・7役reader禁止・caps-unknown原owner保持・追加agent禁止。未完了formal/nativeをdev開始条件に戻さない。Sol容量/人停止時は原保全後PAUSED、重複再試行なし。
