# layout11 C1 quality-stress実評価・phase境界と欠測（2026-10-12）

保存済みlayout11 quality-stressを既存CLI C1で1回fresh評価した。exit0/complete/1cell success。機械10/10・sensor9/10・precision19/19・clean誤警報0。唯一の未検出はcycle09 conveyor-01.motor_temperatureで、phase境界と欠測により異常3観測を利用できなかった。原no_candidate_in_window / candidate0 / causalfalse / matchednull / delaynullを保持。処理successを性能保証・勝者・採択・正式受入にしない。

## 入力と結果の対応

- run dev-layout11-quality-c1-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-11-quality-stress。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\011\attempt-0001\result\payload\manifest.json、pin {"bytes": 75714, "sha256": "ce20f3d40c4e286df89ac3fe4ae6411763fec86f573e9ca67073e2acf2e92177"}。
- seed2486912926863618161/layout11/quality-stress/dev。元10入力pin→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics保存。
- 元生成candidate C0/実評価C1は別field。元payload書込み・新dataset生成・replay・追加agent0。
- actual checkout cba3e350fb322df6e20d87dfe950a3ebccf6a9c3、計算661b27511826fcc87cb4a02930f276afbb8f95d9・science117不変。declared calculator16/candidate/compiled config一致はfull loaded runtime/native認証ではない。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 17.176455999957398秒/private peak 151003136B。
- observations {"bytes": 9600601, "sha256": "d1d5a20c34ebcbd5f91f64e76aadfd12c215d65dcf69e15fb9bb07d9c1ce4813"}、configuration {"bytes": 5513, "sha256": "c6cac770d29ca23a83359748483a1befa6217f8d280f477420388db60e2c8b93"}、manifest {"bytes": 8052, "sha256": "82b9cc1b62f00010dc7afd78acb9b3a412f16f12dfb9379d1814937ff4bd2625"}、evaluation {"bytes": 14511512, "sha256": "096c842d76935f05100038be112f03c0b4da71f9edbe1268c72ab8d3a3c2b697"}、numerical {"bytes": 14505914, "sha256": "668c5a949a008dfa319ad95ad96f771618e49657fbe0d35b848517d99455eb53"}。
- 原閾値C0 4.0/C1 6.0/C2 6.0、operator>/persistence2。全14400scoreの原threshold_exceededを今回C1実値6.0へ照合。設定/GT/matching/科学式変更0。

## 保存coreとの比較

|stratum|machine|sensor|precision|clean|available / unavailable|delay count / mean / median|
|---|---|---|---|---|---|---|
|core（保存済み）|10/10|10/10|20/20|0|13920 / 480|20 / 1.5 / 1.5秒|
|quality（今回）|10/10|9/10|19/19|0|13880 / 520|19 / 1.4736842105263157 / 1.0秒|

coreのモデル再計算0。同seed/layoutでもcoreとqualityのinput fingerprintは異なる。共通pinsはorigins.json / split-manifest.json / targets.jsonの3つ、残り7つは差分を保存した。2条件を独立seedへ数えない。機械10検出は維持、センサー1件を欠落させず原未検出として保持。
48profilesは全calibrated、fit_samples各600/calibration_samples各290、C2stateなし48。18000observations/quality-mask対応でnon-ok欠測30観測行。14400scores中13880利用可/520不能。排他的理由はphase480 / current quality30 / previous quality10。phaseタグ480＋quality primary40−重複0＝520、利用可はcoreから40減った。重複tagsのcurrent_nonfiniteやprevious qualityを独立行として加算しない。全不能score/residual null・thresholdfalseを原記録から確認した。

## 未検出1件の原窓

cycle09 sensor、conveyor-01.motor_temperature、加算8.0、原異常区間[8970,8973)（3観測）、matching窓end8976。開始8970はmode_recipe_or_phase、8971–8973はcurrent quality、8974はprevious qualityで不能。8975/8976は異常終了後でscore2.7525248033959744 / 2.759479975176426、streak0。matching窓内は利用可2/不能5/maxstreak0で、固定persistence2を満たす原candidateなし。

|sample|available|score|streak|reason|
|---|---|---|---|---|
|8970|False|None|0|mode_recipe_or_phase|
|8971|False|None|0|current_target_quality|
|8972|False|None|0|current_target_quality|
|8973|False|None|0|current_target_quality|
|8974|False|None|0|previous_target_quality_or_nonfinite|
|8975|True|2.7525248033959744|0|None|
|8976|True|2.759479975176426|0|None|

同core C1では開始phase不能後の8971/8972が利用でき、onset8972・delay2秒で検出されていた。今回qualityではその2点が欠測で利用できない。元core windowの再compute0、保存指標・今回原窓・input quality maskで対応を保存。未検出delayはnullのまま、検出遅延平均を良くするための代入や集計追加をしない。
残るセンサー9件は各窓6利用可1開始phase不能/maxstreak2、機械10件は各7利用可/maxstreak3。原event target・selected source full_target・equipment membership・matched_event_idを19件すべて照合。機械10件はdelay1秒、センサー9件はdelay2秒、検出19条件付きmin1/max2/mean1.4736842105263157/median1秒。
source29/equipment19、原source内訳 {"conveyor-01.motor_temperature": 9, "conveyor-01.conveyor_speed": 10, "conveyor-01.vibration_feature": 10}、equipment内の機械source {"conveyor-01.conveyor_speed": 10, "conveyor-01.vibration_feature": 10} / センサーsource {"conveyor-01.motor_temperature": 9}。全29sourceは19匹配equipmentに参照、未対応/clean0。clean_rate0/3365原0、effective3255/rate0、false_alert_burden0/20原0は原定義を保持。

## 保存済みC1 quality比較と完成範囲

|layout|machine|sensor|precision|clean|
|---|---|---|---|---|
|1|10/10|9/10|19/19|0|
|2|10/10|9/10|19/19|0|
|3|10/10|9/10|19/19|0|
|4|10/10|9/10|19/19|0|
|5|10/10|9/10|19/19|0|
|6|0/10|9/10|9/19|0|
|0|10/10|9/10|19/19|0|
|7|10/10|9/10|19/19|0|
|8|10/10|9/10|19/19|0|
|9|10/10|9/10|19/19|0|
|10|10/10|9/10|19/19|0|
|11|10/10|9/10|19/19|0|

旧layout0–10 C1qualityと今回layout11で12cells、同layout11 C1coreを加え13原manifest比較。declared16/candidate/compiled config一致、旧モデル再compute0。完成board旧69＋新1＝70cells、layout0–10全6cell保持/layout11core3候補＋qualityC1のみ。同合成devseed1で70独立datasetではない。bootstrap・統計CI・勝者・採択0。入力保存・状態分類の実経路不具合観測なし。

## 記録・次unit・正式状態

- model artifacts/representative-layout11-quality-c1-20261012-records、analysis artifacts/representative-layout11-quality-c1-20261012-analysis、docs/Git artifacts/representative-layout11-quality-c1-20261012-save、最終同-finalのpost-saveを優先。
- analysis items bytes/parts {"all-episodes": {"bytes": 39029, "parts": 1}, "analysis": {"bytes": 479460, "parts": 2}, "analysis.finished": {"bytes": 37, "parts": 1}, "analysis.started": {"bytes": 17, "parts": 1}, "data-closure": {"bytes": 135, "parts": 1}, "data-closure.finished": {"bytes": 37, "parts": 1}, "data-closure.started": {"bytes": 17, "parts": 1}, "helper-execution": {"bytes": 268, "parts": 1}, "helper-live": {"bytes": 213, "parts": 1}, "incident-ledger": {"bytes": 34542, "parts": 1}, "matched-targets": {"bytes": 64211, "parts": 1}, "non-ok-input-records": {"bytes": 22185, "parts": 1}, "policy": {"bytes": 211, "parts": 1}, "script": {"bytes": 13139, "parts": 1}, "selected-windows": {"bytes": 1033849, "parts": 4}, "unavailable-scores": {"bytes": 518806, "parts": 2}}。
- DATA artifacts/representative-anomaly-evaluation/dev-layout11-quality-c1-20261012/root-closed.json / {"bytes": 27559804, "files": 19, "manifest_pin": {"bytes": 2236, "sha256": "359fa0f5a2027454f05ac009394bb7ef8fcf1776d6f3e52414be4c3ef21fc233"}}。
- EvidenceStore新記録16MiB/512files、part256KiB、failure2MiB/16files・closure512KiB/4files予備枠と全write preflightを維持。closed/frozen root追記整理0、原failed/誤記保持、完成評価・試験・CI反復0。
- prepare_result_index実使用でreport/handoff/index3文書を同種合成dev結果・ユーザー名を含むPC内pathのGitHub継続送信承認内で1回[skip ci] commit/push。原Gitbytes/HEAD-upstream-remote-clean/docpinsは-save/-final、追加確認0/bypass0。
- 次unit同保存layout11 quality-stress C2 c2-phase-conditional、新ID dev-layout11-quality-c2-20261012。同manifest/input10、本文C1で読取済み/次model未実行。元生成C0/次評価C2別field。元payload書込み/生成0。
- 実行900秒/2GiB/output1GiB/single32MiB/files32、Git累積30秒/16entry/512KiB/stdout1MiB/stderr128KiB、protocol/native上限不変。checkpointはblocking中断/full runtime閉包/allwriter-global容量証明ではない。
- ACTIVE/automation詳細転記0。CI381385/4130保持、query/download/verifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了/create_native早期拒否/7役reader禁止/caps-unknown原owner保持/追加agent禁止。未完了formal/nativeをdev開始条件へ戻さない。Sol容量/人停止は原保全後PAUSED、重複再試行なし。
