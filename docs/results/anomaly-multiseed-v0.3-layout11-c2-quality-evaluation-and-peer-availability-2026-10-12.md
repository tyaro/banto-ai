# layout11 C2 quality-stress実評価・欠測のpeer波及（2026-10-12）

保存済みlayout11 quality-stressを既存CLI C2で1回fresh評価した。exit0/complete/1cell success。機械10/10・sensor9/10・precision19/19・clean誤警報0。未検出cycle09温度は原no_candidate_in_window/candidate0/causalfalse/matchednull/delaynullを保持。処理successや単一合成dev結果を性能保証・勝者・採択・正式受入にしない。

## 入力と実行の対応

- run dev-layout11-quality-c2-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-11-quality-stress。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\011\attempt-0001\result\payload\manifest.json、pin {"bytes": 75714, "sha256": "ce20f3d40c4e286df89ac3fe4ae6411763fec86f573e9ca67073e2acf2e92177"}。
- seed2486912926863618161/layout11/quality-stress/dev。C1qualityと同input10 pins→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics保存。
- 元生成candidate C0/実評価candidate C2別field。元payload書込み・新dataset生成・replay・追加agent0。
- actual checkout f69440f9b7bdd5f907d09216610e4c2bdac1d221、計算661b27511826fcc87cb4a02930f276afbb8f95d9・science117不変。declared16/candidate/compiled config一致はfull loaded runtime/native認証ではない。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 43.61202390003018秒/private peak 209752064B。
- observations {"bytes": 9600601, "sha256": "d1d5a20c34ebcbd5f91f64e76aadfd12c215d65dcf69e15fb9bb07d9c1ce4813"}、configuration {"bytes": 5519, "sha256": "a57429df89ec948a02b3d3e18a7af63fe2c7d93aa2e4ba6145343df3b9eb524c"}、manifest {"bytes": 8057, "sha256": "ec0c13de33ee626b8f29c5440c6af5a0e5c00454b95844811e7288aded95617a"}、evaluation {"bytes": 25196955, "sha256": "b440f823f599fda2517e7a002c28003711c31b12d6c423a2e03ffd718848a61a"}、numerical {"bytes": 25191357, "sha256": "ef99d090f3fc4c742abccf37d251104b04e25f9f643d5ced6d8a330cb3dab20d"}。
- 原candidate閾値C0 4.0/C1 6.0/C2 6.0、operator>/persistence2。全14400scoreの原threshold_exceededをC2実値6.0へ照合。GT/設定/matching/科学式変更0。

## 保存C2core・同入力C1qualityとの比較

|candidate/stratum|machine|sensor|precision|clean|available / unavailable|source / equipment|
|---|---|---|---|---|---|---|
|C2 core（保存）|10/10|10/10|20/20|0|13920 / 480|44 / 20|
|C1 quality（保存）|10/10|9/10|19/19|0|13880 / 520|29 / 19|
|C2 quality（今回）|10/10|9/10|19/19|0|13760 / 640|42 / 19|

C2coreとqualityは共通input pinsがorigins.json/split-manifest.json/targets.jsonの3つで、全fingerprintは異なる。C1/C2qualityの10入力pinは完全一致。旧モデル再compute0。同seed/layoutの2条件を独立seedへしない。
C1qualityとC2qualityはrecall/precision/clean/遅延の原主要指標が同じだが、C2はpeer品質依存により利用不能が120行多い。sourceはC1の29→C2の42（13増）、C2core44→quality42（2減）。全42sourceは19匹配equipmentに参照、追加13をfalse alert数へ数えない。原source内訳 {"conveyor-01.motor_temperature": 13, "conveyor-01.vibration_feature": 19, "conveyor-01.conveyor_speed": 10}、equipment内の機械source {"conveyor-01.conveyor_speed": 10, "conveyor-01.motor_temperature": 4, "conveyor-01.vibration_feature": 10} / センサーsource {"conveyor-01.motor_temperature": 9, "conveyor-01.vibration_feature": 9}。

## 原利用不能640とpeer120

48profiles全calibrated、fit_samples各600/calibration_samples各290、C2stateあり48。18000observations/quality-mask対応、non-ok欠測30観測行。14400scores中13760利用可/640不能。排他的primaryはphase480/current quality30/previous quality10/peer120。phase tags480＋own quality primary40＋peer tags120−重複0＝640。C2coreから利用可160減、C1qualityから120減。
温度自身の不能はcurrent30+previous10。温度をpeerに使うconveyor-01のcurrent/speed/vibration各40行が追加不能（計120）。phaseとの重複はown0/peer0。重複tagsのcurrent_nonfiniteやprevious qualityを独立行として加算しない。全不能score/residual null・thresholdfalse、peer rowsはstreak0。

|full_target|unavailable total|primary counts|
|---|---|---|
|conveyor-01.conveyor_speed|100|{"mode_recipe_or_phase": 60, "peer_quality_or_nonfinite": 40}|
|conveyor-01.motor_current|100|{"mode_recipe_or_phase": 60, "peer_quality_or_nonfinite": 40}|
|conveyor-01.motor_temperature|100|{"current_target_quality": 30, "mode_recipe_or_phase": 60, "previous_target_quality_or_nonfinite": 10}|
|conveyor-01.vibration_feature|100|{"mode_recipe_or_phase": 60, "peer_quality_or_nonfinite": 40}|
|motor-01.conveyor_speed|60|{"mode_recipe_or_phase": 60}|
|motor-01.motor_current|60|{"mode_recipe_or_phase": 60}|
|motor-01.motor_temperature|60|{"mode_recipe_or_phase": 60}|
|motor-01.vibration_feature|60|{"mode_recipe_or_phase": 60}|

## 未検出1件と原peer窓

cycle09 sensor、conveyor-01.motor_temperature、加算8.0、原異常区間[8970,8973)（3観測）、matching窓end8976。8970は4targetsともphase不能、温度8971–8973 current quality/8974 previous qualityで不能。current/speed/vibrationの8971–8974もpeer不能（原12rows）。全null/streak0/thresholdfalseで、温度の窓は2利用可5不能/maxstreak0。8975/8976で利用が戻っても閾値6未満。固定persistence2の原candidateなし、delaynullを補完しない。

|sample|available|score|streak|reason|
|---|---|---|---|
|8970|False|None|0|mode_recipe_or_phase|
|8971|False|None|0|current_target_quality|
|8972|False|None|0|current_target_quality|
|8973|False|None|0|current_target_quality|
|8974|False|None|0|previous_target_quality_or_nonfinite|
|8975|True|2.765250775124146|0|None|
|8976|True|2.8732611338148093|0|None|

原温度event/incident・四target window・全peer120/peerタグ120・重複0の記録を新-analysis/-saveに保持。機械10検出の各窓7利用可/maxstreak3、検出センサー9件は各6利用可1phase不能/maxstreak2。19件のevent target・selected source full_target・equipment membership・matched_event_id/support2scoreを原照合した。
機械10件はdelay1秒、センサー9件はdelay2秒。検出19件条件付きmin1/max2/mean1.4736842105263157/median1秒、未検出1件はnull。clean_rate0/3365原0、effective3255/rate0、false_alert_burden0/20原0は原定義を保持。入力保存・失敗状態分類・検出対応の実経路不具合観測なし。

## 保存済みC2 quality比較・完成範囲

|layout|machine|sensor|precision|clean|
|---|---|---|---|---|
|1|10/10|9/10|19/19|0|
|2|10/10|9/10|19/19|0|
|3|10/10|9/10|19/19|0|
|4|10/10|9/10|19/19|0|
|5|10/10|9/10|19/19|0|
|6|0/10|9/10|9/19|0|
|0|4/10|9/10|13/19|0|
|7|10/10|9/10|19/19|0|
|8|10/10|9/10|19/19|0|
|9|10/10|9/10|19/19|0|
|10|10/10|9/10|19/19|0|
|11|10/10|9/10|19/19|0|

旧layout0–10 C2qualityと今回で12cells、同layout11 C2core/C1quality加え14原manifest比較。declared16/candidate/compiled config一致、旧モデル再compute0。完成board旧70＋新1＝71cells、layout0–10全6cell保持/layout11core3候補＋qualityC1/C2の5cell完了。残るqualityC0は未実行。同合成devseed1で71独立datasetではない。bootstrap・統計CI・勝者・採択0。

## 記録・Git保存・次unit・正式状態

- model artifacts/representative-layout11-quality-c2-20261012-records、analysis artifacts/representative-layout11-quality-c2-20261012-analysis、docs/Git artifacts/representative-layout11-quality-c2-20261012-save、最終同-finalのpost-saveを優先。
- analysis項目bytes/parts {"all-episodes": {"bytes": 53606, "parts": 1}, "analysis": {"bytes": 490918, "parts": 2}, "analysis.finished": {"bytes": 37, "parts": 1}, "analysis.started": {"bytes": 17, "parts": 1}, "data-closure": {"bytes": 135, "parts": 1}, "data-closure.finished": {"bytes": 37, "parts": 1}, "data-closure.started": {"bytes": 17, "parts": 1}, "helper-execution": {"bytes": 268, "parts": 1}, "helper-live": {"bytes": 213, "parts": 1}, "incident-ledger": {"bytes": 35232, "parts": 1}, "matched-targets": {"bytes": 67654, "parts": 1}, "non-ok-input-records": {"bytes": 22191, "parts": 1}, "policy": {"bytes": 211, "parts": 1}, "script": {"bytes": 13757, "parts": 1}, "selected-windows": {"bytes": 1765995, "parts": 7}, "unavailable-scores": {"bytes": 1113958, "parts": 5}}。
- DATA artifacts/representative-anomaly-evaluation/dev-layout11-quality-c2-20261012/root-closed.json / {"bytes": 38245276, "files": 19, "manifest_pin": {"bytes": 2236, "sha256": "8b14c516eb97ebf5bbcca8890ed39e862f69bb88323bde08cac603537d6faa3a"}}。
- EvidenceStore新記録16MiB/512files/part256KiB/failure2MiB16files・closure512KiB4files予備枠と全新write preflight維持。closed/frozen root追記整理0/原failed・誤記保持/完成評価試験CI反復0。
- prepare_result_index実使用でreport/handoff/index3文書を同種合成dev結果・ユーザー名を含むPC内pathのGitHub継続送信承認内で1回[skip ci] commit/push。原Gitbytes/HEAD-upstream-remote-clean/docpinsは-save/-final、追加確認0/bypass0。
- 次unit同保存layout11 quality-stress C0 c0-diff-control、新ID dev-layout11-quality-c0-20261012。同manifest/input10、本文C1/C2読取済み/次model未実行、生成C0/実評価C0別field。元payload書込み・生成0。
- 実行900秒/2GiB/output1GiB/single32MiB/files32、Git累積30秒/16entry/512KiB/stdout1MiB/stderr128KiB、protocol/native不変。checkpointはblocking中断/full runtime閉包/allwriter-global容量証明ではない。
- ACTIVE/automation詳細転記0。CI381385/4130保存query/download/verifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了/create_native早期拒否/7役reader禁止/caps-unknown原owner保持/追加agent禁止。未完了formal/nativeをdev開始条件へ戻さない。Sol容量/人停止は原保全後PAUSED、重複再試行なし。
