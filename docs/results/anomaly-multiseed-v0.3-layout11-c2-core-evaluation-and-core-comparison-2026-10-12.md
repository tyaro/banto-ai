# layout11 C2 core実評価・12layouts core比較（2026-10-12）

保存済みlayout11 coreを既存CLI C2で1回fresh評価した。exit0/complete/1cell success。機械10/10・sensor10/10・precision20/20・clean誤警報0。機械の検出遅延は各1秒、センサーは各2秒。単一合成dev結果・処理successを性能保証・勝者・採択・正式受入にしない。

## 入力と結果の対応

- run dev-layout11-core-c2-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-11-core。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\011\attempt-0001\result\payload\manifest.json、pin {"bytes": 75714, "sha256": "ce20f3d40c4e286df89ac3fe4ae6411763fec86f573e9ca67073e2acf2e92177"}。
- seed2486912926863618161/layout11/core/dev。input10は同C0/C1完全一致→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics保存。
- 元生成candidate C0/実評価candidate C2は別field。元payload書込み・新dataset生成・replay・追加agent0。
- actual checkout 794b68c783a8bfa5730743bf8789f6380b31590b、計算661b27511826fcc87cb4a02930f276afbb8f95d9・science117不変。宣言calculator16/candidate/compiled config一致はfull loaded runtime/native認証ではない。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 29.777498799958266秒/private peak 208510976B。
- observations {"bytes": 9600597, "sha256": "d8ac35000efdd0b2de6f0205173d7a4a115567b89ff8cb0089cae77ab9736ef3"}、configuration {"bytes": 5509, "sha256": "fd8c3f7d08d42e2579e438031444384f0da594538c01a46ba4d9b944b34feb10"}、manifest {"bytes": 8011, "sha256": "cc28cb7af0da7ae2aa2db9d3348d4c1f3951cdb28a3592e697be0567266d3aa2"}、evaluation {"bytes": 24756024, "sha256": "de8f82ec3b0282310cb1722c669df5b50be67d357593bf30cdf61fdd552de622"}、numerical {"bytes": 24750526, "sha256": "f2edf996208787983b592be369f4e6201e0fd4bb04abe42e03be1c313fcd6d21"}。
- 原candidate閾値C0 4.0/C1 6.0/C2 6.0、operator>/persistence2。全14400scoreの原threshold_exceededを今回C2実値6.0へ照合。GT・設定・matching・科学式の変更0。

## 同入力3候補の原指標

|candidate|machine|sensor|precision|clean|source / equipment|delay count / mean / median|
|---|---|---|---|---|---|---|
|c0-diff-control|0/10|1/10|1/3|2|3 / 3|1 / 2.0 / 2.0秒|
|c1-phase-level|10/10|10/10|20/20|0|30 / 20|20 / 1.5 / 1.5秒|
|c2-phase-conditional|10/10|10/10|20/20|0|44 / 20|20 / 1.5 / 1.5秒|

C1とC2は今回の原recall/precision/clean/遅延指標が同じだった。予測rawやモデルが同じという意味ではない。C2はsource44、C1はsource30で、追加14sourceは20件の匹配equipmentに参照されている。source数の差を誤警報の差や候補優劣にしない。
保存C0/C1のモデル再計算0。入力10pinsと固定candidate/compiled configは完全一致。C0の1検出における一定加算の差分相殺と固定matchingラベルの区別は [C0報告](anomaly-multiseed-v0.3-layout11-c0-core-evaluation-2026-10-12.md) と原C0-save/detection-interpretationを保持。C0baselineの変更0。

## 原検出・利用不能・source membership

48profilesすべてcalibrated、fit_samples各600/calibration_samples各290、C2stateあり48。18000observations/quality-mask対応、non-ok0。14400scoresの利用可13920、不能480は全mode_recipe_or_phaseでscore/residual null・thresholdfalse。
全20incidentsはcausal_detected=true/candidate1。event targetとselected_source full_target、source idとequipment membership、equipment matched_event_id、support2score/onsetを原照合した。機械10窓は各7rows全利用可/maxstreak3、onset=start+1秒。センサー10窓は各6利用可+開始1row phase不能/maxstreak2、onset=start+2秒。全20検出条件付きdelay count20/min1/max2/mean1.5/median1.5秒。未検出delay補完0。
原source内訳 {"conveyor-01.motor_temperature": 14, "conveyor-01.vibration_feature": 20, "conveyor-01.conveyor_speed": 10}。機械equipment内のsource内訳 {"conveyor-01.conveyor_speed": 10, "conveyor-01.motor_temperature": 4, "conveyor-01.vibration_feature": 10}、センサーequipment {"conveyor-01.motor_temperature": 10, "conveyor-01.vibration_feature": 10}。全44sourceは20匹配equipmentに参照、未参照source0/未対応equipment0/clean0。C1source内訳 {"conveyor-01.conveyor_speed": 10, "conveyor-01.motor_temperature": 10, "conveyor-01.vibration_feature": 10} と原membershipを新-saveへ保存し、14増をfalse alertへ数えない。

### cycle00 sensorの原窓

|sample|available|score|streak|reason|
|---|---|---|---|---|
|7350|False|None|0|mode_recipe_or_phase|
|7351|True|172.55988027804378|1|None|
|7352|True|172.52633720930697|2|None|
|7353|True|1.9393159011089542|0|None|
|7354|True|1.6421604611330822|0|None|

開始sample7350はphase不能/streak0、その後7351/7352は温度対象の2連続閾値超過でonset7352になった。cycle00/02機械・センサー原窓とsource/equipment/supportを-save target-onset-summaryへ保存。全20event-incident/四target窓/全44source・20equipment/全不能streamは-analysisへ自動分割保存。
clean_rate0/3365原0.0、effective3255秒/rate0.0、false_alert_burden0/20原0.0。rate/burdenの原定義を単純確率へ読み替えない。入力保存・検出対応・失敗状態分類の実経路不具合は観測なし。

## 保存済みC2 core比較・完成範囲

|layout|machine|sensor|precision|clean|
|---|---|---|---|---|
|0|4/10|10/10|14/20|0|
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

旧layout0–10 C2coreと今回layout11 C2coreで12cells、同layout11 C0/C1を加えた原manifest比較14cells。declared16/candidate/compiled config一致、同devseedのlayout入力差を保持、旧モデル再compute0。完成board旧68＋新1＝69cells、layout0–10全6cell保持、layout11はcore3候補のみ完了。同合成devseed1で69独立datasetではない。bootstrap・統計CI・勝者・採択0。

## 記録・次unit・正式状態

- model artifacts/representative-layout11-core-c2-20261012-records、analysis artifacts/representative-layout11-core-c2-20261012-analysis、docs/Git artifacts/representative-layout11-core-c2-20261012-save、最終同-finalのpost-saveを優先。
- analysis items bytes/parts {"all-episodes": {"bytes": 53181, "parts": 1}, "analysis": {"bytes": 478154, "parts": 2}, "analysis.finished": {"bytes": 37, "parts": 1}, "analysis.started": {"bytes": 17, "parts": 1}, "data-closure": {"bytes": 135, "parts": 1}, "data-closure.finished": {"bytes": 37, "parts": 1}, "data-closure.started": {"bytes": 17, "parts": 1}, "helper-execution": {"bytes": 268, "parts": 1}, "helper-live": {"bytes": 213, "parts": 1}, "incident-ledger": {"bytes": 34444, "parts": 1}, "matched-targets": {"bytes": 67762, "parts": 1}, "non-ok-input-records": {"bytes": 195, "parts": 1}, "policy": {"bytes": 211, "parts": 1}, "script": {"bytes": 12981, "parts": 1}, "selected-windows": {"bytes": 1731645, "parts": 7}, "unavailable-scores": {"bytes": 816438, "parts": 4}}。
- DATA artifacts/representative-anomaly-evaluation/dev-layout11-core-c2-20261012/root-closed.json / {"bytes": 37797825, "files": 19, "manifest_pin": {"bytes": 2226, "sha256": "37f462058aa6186293f26fc724b960947136284b8dd3c184c7a479b43707ee36"}}。
- 新EvidenceStore記録16MiB/512files、part256KiB、failure2MiB/16files/closure512KiB/4files予備枠と全write preflight維持。closed/frozen root追記整理0、過去failed・原script・stdio状態保持、完成評価/試験/CIの反復0。
- report/handoff/index3文書をprepare_result_index実使用と継続送信承認内で一回[skip ci] commit/push。合成dev結果・ユーザー名を含むPC内pathの同GitHub送信承認を保持、追加確認0/bypass0。原Gitbytes/HEAD-upstream-lsremote-clean/docpinsは-save/-final。
- 次unitは同保存layout11/quality-stressをC1 c1-phase-level、新ID dev-layout11-quality-c1-20261012。元同manifest75714B/同pin、next dataset anomaly-v03-dev-seed-2486912926863618161-layout-11-quality-stress と元input10metadataだけを選択。quality観測本文は未読、次model未開始、生成candidate C0と実評価C1は別field。元payload書込み・生成0。
- 実行900秒/2GiB/output1GiB/single32MiB/files32、Git累積30秒/16entry/512KiB/stdout1MiB/stderr128KiB、protocol/native上限不変。checkpointはblocking中断/full runtime閉包/allwriter-global容量証明ではない。
- ACTIVE、automation詳細転記0。完成CI381385/4130保持、今回query/download/verifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了/create_native早期拒否/7役reader禁止/caps-unknown原owner保持/追加agent禁止。未完了formal/nativeをdev開始条件へ戻さない。Sol容量/人停止は原保全後PAUSED、重複再試行なし。
