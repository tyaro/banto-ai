# layout11 C0 quality実評価・12 layouts比較（2026-10-12）

保存済みlayout11 quality-stressを既存CLI C0で1回fresh compute。機械0/10、センサー1/10、precision1/3、正常区間の誤警報2件。今回で同合成devseedの12 layouts×3候補×2条件、72 cellsの保存比較がそろった。処理exit0/complete/1cell successを性能合格・採択・正式受入にしない。

## 入力と結果の対応

- run dev-layout11-quality-c0-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-11-quality-stress。
- 元inputmanifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\011\attempt-0001\result\payload\manifest.json / {"bytes": 75714, "sha256": "ce20f3d40c4e286df89ac3fe4ae6411763fec86f573e9ca67073e2acf2e92177"}。10pin照合→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics。元payload書込み・新dataset生成・replay・追加agent0。
- 元生成candidate C0と実評価candidate C0を別fieldで保持。実checkout 24e4efff69cdcc37a9020fe85839eb78d6aea3cb、計算code661b27511826fcc87cb4a02930f276afbb8f95d9、science117/calculator16/candidate/compiled config不変。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 29.740976899978705秒、OS sampled private peak 149192704B。
- observations {"bytes": 9600601, "sha256": "d1d5a20c34ebcbd5f91f64e76aadfd12c215d65dcf69e15fb9bb07d9c1ce4813"}、configuration {"bytes": 5514, "sha256": "9101cfde800c6b7f21d1f8b09731b5adbbcf0a10e31ea984ec825cd4c667802b"}、manifest {"bytes": 8077, "sha256": "0650a7e64725495f33d7a829bdcb1bdfa920a02f5066d79bcbc9455163cbf359"}、evaluation {"bytes": 14337745, "sha256": "540af0b366f478674da3a226ff665807571eaeca3a23d1ee20d70862008c11a1"}。宣言source pinはfull loaded runtime/native認証ではない。
- C0閾値4.0、C1/C2閾値6.0、演算子>、persistence2。全score原threshold flags確認。GT・matching・科学式変更0。

## 原指標と利用不能

|項目|原値|
|---|---|
|機械 recall|0/10|
|センサー recall|1/10|
|precision|1/3|
|clean / unmatched|2 / 2|
|source / equipment / incidents / events|3 / 3 / 20 / 40|
|scores 利用可 / 不能|13880 / 520|

48profiles calibrated、C0 fit_samples各0（定義上no-op）/calibration各290/C2stateなし48。18000observationsとmask対応、non-ok30。排他的不能理由phase480/current quality30/previous quality10、全不能score/residual null・thresholdfalse。同layoutcore13920/480から40減少し、C1quality13880/520と同数。C2qualityはpeer120の追加で13760/640。理由tagsの重複を独立行へ加算しない。
検出1件だけdelay2秒（count1、min/max/mean/median2.0）。未検出19delay null、集計への代入0。clean_rate 2/3365 / 原value 17.11738484398217、effective 3255秒 / rate 17.695852534562214、false_alert_burden 2/20 / 原value 10.0。rate/burdenは単純確率ではない。

## 検出1件とC0の設計上の意味

cycle02 conveyor-01.motor_temperature、固定+8.0の3観測[7710,7713)。7710phase不能、7711 score4.204907244726188/streak1、7712 score4.010680221818085/streak2、7713 score101.35032786396381/streak3、7714reset。原event-target-source-equipment-support2score一致、onset7712、固定matching causal_detected=true/candidate1/delay2秒。同core C0の原窓と同じだった。
support7711/7712は同+8.0区間内にあり、一次差分では一定加算成分が相殺される。今回の1検出は一定オフセット感度や強い物理因果の証明ではない。正常対照の再計算0、原matchingラベルと指標を保持する。既存[設計確認](anomaly-multiseed-v0.3-layout10-c0-core-evaluation-2026-10-12.md)と[coreの検出解釈](anomaly-multiseed-v0.3-layout11-c0-core-evaluation-2026-10-12.md)を参照。3観測/end-exclusive訂正、旧four-sample誤記・初回analysis failureを保持。C0 baseline/閾値/persistence変更0。

## 未検出19件と誤警報2件

全missはno_candidate_in_window/candidate0/causalfalse/matchednull/delaynull。機械10窓は7利用可/0不能/maxstreak1。未検出sensor8窓は6利用可/開始1phase不能/maxstreak1。cycle09だけ2利用可/5不能/maxstreak0で、欠測1窓を全19missの説明にはしない。

|cycle09 sample|available|score|streak|理由|
|---|---|---|---|---|
|8970|False|None|0|mode_recipe_or_phase|
|8971|False|None|0|current_target_quality|
|8972|False|None|0|current_target_quality|
|8973|False|None|0|current_target_quality|
|8974|False|None|0|previous_target_quality_or_nonfinite|
|8975|True|2.3272931156276915|0|None|
|8976|True|1.8329967384571064|0|None|

cycle09原異常[8970,8973)/windowend8976、開始phase不能の後、8971–8973current quality、8974previous qualityでreset。8975/8976は閾値4未満。最大score 2.3272931156276915、episode不成立。全20ledger/四target窓/原episodes/全520不能/非ok30入力maskを-analysisへ保存した。
clean2はmotor-01.vibration_feature、原onset7242/8517、clean tags/matchednull。原sourceとsupport scoresを-save/episode-summaryへ保存。source3/equipment3のうち対象検出1・未対応2を別に保持。入力対応・保存・状態分類の実経路不具合は観測なし。

## 12 layouts × 3候補 × 2条件の保存比較

同devseed1、旧71＋今回1＝72。以下は保存manifestの原指標。旧モデル再計算0。各layout/同stratumの3候補input10完全一致、同layout core/qualityの共通pinsはorigins/split-manifest/targets3、観測とquality等の差を保持。calculator16・candidate/compiled config一致。72独立datasetや複数独立seedとは数えない。

|layout|stratum|candidate|machine|sensor|precision|clean|available|delay count / median秒|
|---|---|---|---|---|---|---|---|---|
|0|core|c0-diff-control|0/10|0/10|0/3|3|13920|0 / None|
|0|core|c1-phase-level|10/10|10/10|20/20|0|13920|20 / 1.5|
|0|core|c2-phase-conditional|4/10|10/10|14/20|0|13920|14 / 1.0|
|0|quality-stress|c0-diff-control|0/10|0/10|0/3|3|13880|0 / None|
|0|quality-stress|c1-phase-level|10/10|9/10|19/19|0|13880|19 / 2.0|
|0|quality-stress|c2-phase-conditional|4/10|9/10|13/19|0|13760|13 / 1.0|
|1|core|c0-diff-control|0/10|0/10|0/3|2|13920|0 / None|
|1|core|c1-phase-level|10/10|10/10|20/20|0|13920|20 / 1.0|
|1|core|c2-phase-conditional|10/10|10/10|20/20|0|13920|20 / 1.0|
|1|quality-stress|c0-diff-control|0/10|0/10|0/3|2|13880|0 / None|
|1|quality-stress|c1-phase-level|10/10|9/10|19/19|0|13880|19 / 1.0|
|1|quality-stress|c2-phase-conditional|10/10|9/10|19/19|0|13760|19 / 1.0|
|2|core|c0-diff-control|0/10|0/10|0/3|3|13920|0 / None|
|2|core|c1-phase-level|10/10|10/10|20/20|0|13920|20 / 1.0|
|2|core|c2-phase-conditional|10/10|10/10|20/20|0|13920|20 / 1.0|
|2|quality-stress|c0-diff-control|0/10|0/10|0/3|3|13889|0 / None|
|2|quality-stress|c1-phase-level|10/10|9/10|19/19|0|13889|19 / 1.0|
|2|quality-stress|c2-phase-conditional|10/10|9/10|19/19|0|13796|19 / 1.0|
|3|core|c0-diff-control|0/10|0/10|0/3|3|13920|0 / None|
|3|core|c1-phase-level|10/10|10/10|20/20|0|13920|20 / 1.5|
|3|core|c2-phase-conditional|10/10|10/10|20/20|0|13920|20 / 1.5|
|3|quality-stress|c0-diff-control|0/10|0/10|0/3|3|13880|0 / None|
|3|quality-stress|c1-phase-level|10/10|9/10|19/19|0|13880|19 / 1.0|
|3|quality-stress|c2-phase-conditional|10/10|9/10|19/19|0|13760|19 / 1.0|
|4|core|c0-diff-control|0/10|0/10|0/3|3|13920|0 / None|
|4|core|c1-phase-level|10/10|10/10|20/20|0|13920|20 / 1.5|
|4|core|c2-phase-conditional|10/10|10/10|20/20|0|13920|20 / 1.5|
|4|quality-stress|c0-diff-control|0/10|0/10|0/3|3|13880|0 / None|
|4|quality-stress|c1-phase-level|10/10|9/10|19/19|0|13880|19 / 2.0|
|4|quality-stress|c2-phase-conditional|10/10|9/10|19/19|0|13760|19 / 2.0|
|5|core|c0-diff-control|0/10|0/10|0/3|3|13920|0 / None|
|5|core|c1-phase-level|10/10|10/10|20/20|0|13920|20 / 1.0|
|5|core|c2-phase-conditional|10/10|10/10|20/20|0|13920|20 / 1.0|
|5|quality-stress|c0-diff-control|0/10|0/10|0/3|3|13880|0 / None|
|5|quality-stress|c1-phase-level|10/10|9/10|19/19|0|13880|19 / 1.0|
|5|quality-stress|c2-phase-conditional|10/10|9/10|19/19|0|13760|19 / 1.0|
|6|core|c0-diff-control|0/10|0/10|0/3|3|13920|0 / None|
|6|core|c1-phase-level|0/10|10/10|10/20|0|13920|10 / 1.0|
|6|core|c2-phase-conditional|0/10|10/10|10/20|0|13920|10 / 1.0|
|6|quality-stress|c0-diff-control|0/10|0/10|0/3|3|13889|0 / None|
|6|quality-stress|c1-phase-level|0/10|9/10|9/19|0|13889|9 / 1.0|
|6|quality-stress|c2-phase-conditional|0/10|9/10|9/19|0|13796|9 / 1.0|
|7|core|c0-diff-control|0/10|0/10|0/3|3|13920|0 / None|
|7|core|c1-phase-level|10/10|10/10|20/20|0|13920|20 / 1.5|
|7|core|c2-phase-conditional|10/10|10/10|20/20|0|13920|20 / 1.5|
|7|quality-stress|c0-diff-control|0/10|0/10|0/3|3|13880|0 / None|
|7|quality-stress|c1-phase-level|10/10|9/10|19/19|0|13880|19 / 1.0|
|7|quality-stress|c2-phase-conditional|10/10|9/10|19/19|0|13760|19 / 1.0|
|8|core|c0-diff-control|0/10|0/10|0/3|3|13920|0 / None|
|8|core|c1-phase-level|10/10|10/10|20/20|0|13920|20 / 1.5|
|8|core|c2-phase-conditional|10/10|10/10|20/20|0|13920|20 / 1.5|
|8|quality-stress|c0-diff-control|0/10|0/10|0/3|3|13880|0 / None|
|8|quality-stress|c1-phase-level|10/10|9/10|19/19|0|13880|19 / 2.0|
|8|quality-stress|c2-phase-conditional|10/10|9/10|19/19|0|13760|19 / 2.0|
|9|core|c0-diff-control|0/10|0/10|0/3|3|13920|0 / None|
|9|core|c1-phase-level|10/10|10/10|20/20|0|13920|20 / 1.0|
|9|core|c2-phase-conditional|10/10|10/10|20/20|0|13920|20 / 1.0|
|9|quality-stress|c0-diff-control|0/10|0/10|0/3|3|13880|0 / None|
|9|quality-stress|c1-phase-level|10/10|9/10|19/19|0|13880|19 / 1.0|
|9|quality-stress|c2-phase-conditional|10/10|9/10|19/19|0|13760|19 / 1.0|
|10|core|c0-diff-control|0/10|0/10|0/3|3|13920|0 / None|
|10|core|c1-phase-level|10/10|10/10|20/20|0|13920|20 / 1.0|
|10|core|c2-phase-conditional|10/10|10/10|20/20|0|13920|20 / 1.0|
|10|quality-stress|c0-diff-control|0/10|0/10|0/3|3|13889|0 / None|
|10|quality-stress|c1-phase-level|10/10|9/10|19/19|0|13889|19 / 1.0|
|10|quality-stress|c2-phase-conditional|10/10|9/10|19/19|0|13796|19 / 1.0|
|11|core|c0-diff-control|0/10|1/10|1/3|2|13920|1 / 2.0|
|11|core|c1-phase-level|10/10|10/10|20/20|0|13920|20 / 1.5|
|11|core|c2-phase-conditional|10/10|10/10|20/20|0|13920|20 / 1.5|
|11|quality-stress|c0-diff-control|0/10|1/10|1/3|2|13880|1 / 2.0|
|11|quality-stress|c1-phase-level|10/10|9/10|19/19|0|13880|19 / 1.0|
|11|quality-stress|c2-phase-conditional|10/10|9/10|19/19|0|13760|19 / 1.0|

bootstrap・統計CI・勝者・採択0。C0の弱さと一次差分/persistenceの組合せに関する既存説明を維持し、今回1検出で解消したとは扱わない。未検出delay nullは中央値等へ代入しない。

## 証拠保存・次unit・正式状態

- model artifacts/representative-layout11-quality-c0-20261012-records、analysis artifacts/representative-layout11-quality-c0-20261012-analysis、docs/Git artifacts/representative-layout11-quality-c0-20261012-save、最終同-final/post-save label優先。
- DATA artifacts/representative-anomaly-evaluation/dev-layout11-quality-c0-20261012/root-closed.json / {"bytes": 27386090, "files": 19, "manifest_pin": {"bytes": 2236, "sha256": "136c6b753b875d567bc05225c8a3530061856df8b8b96df3b17b2feab1ae7e28"}}。analysis保存parts {"all-episodes": {"bytes": 4632, "parts": 1}, "analysis": {"bytes": 780126, "parts": 3}, "analysis.finished": {"bytes": 37, "parts": 1}, "analysis.started": {"bytes": 17, "parts": 1}, "data-closure": {"bytes": 135, "parts": 1}, "data-closure.finished": {"bytes": 37, "parts": 1}, "data-closure.started": {"bytes": 17, "parts": 1}, "helper-execution": {"bytes": 268, "parts": 1}, "helper-live": {"bytes": 213, "parts": 1}, "incident-ledger": {"bytes": 20761, "parts": 1}, "matched-targets": {"bytes": 3520, "parts": 1}, "non-ok-input-records": {"bytes": 22186, "parts": 1}, "policy": {"bytes": 211, "parts": 1}, "script": {"bytes": 13341, "parts": 1}, "selected-windows": {"bytes": 980011, "parts": 4}, "unavailable-scores": {"bytes": 520367, "parts": 2}}。
- 新記録EvidenceStore16MiB512files/part256KiB/失敗2MiB16files・閉鎖512KiB4files予備枠、全write preflight。既存closed/frozen root追記整理0、原failed21・missingexecution1/foregroundcp932/console誤記保持。
- 実行900秒2GiBoutput1GiBsingle32MiBfiles32、Git累積30秒16entry512KiBstdout1MiBstderr128KiB、protocol/native不変。checkpoint≠blocking中断/fullruntime/global/allwriter容量証明。
- prepare_result_index実使用、report/handoff/index3文書を同種合成dev報告・PC内pathのGitHub継続送信承認で1回[skip ci] commit/push。原Gitbytes/HEAD-upstream-lsremote-clean/docpinsは-save/-final。追加確認0/bypass0。
- 次unit 保存済みchunk012のdev/core、seed7466813550306735603/layout0、C0 c0-diff-control、新ID dev-seed7466813550306735603-layout0-core-c0-20261012。manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\012\attempt-0001\result\payload\manifest.json / {"bytes": 75700, "sha256": "5060fceed11406c0393d8afd284cdbeb418df7052298c4dc97fdd7c887d32a0d"}。選択はidentity/input10 metadataだけ、観測本文未読・次model未開始。 次の別seedを選択しただけで、独立seed実評価を完了したとは数えない。
- ACTIVE/automation詳細転記0。CI381385/4130保持、CIquery/download/verifier/tests0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読/正式5残件・最終受入未完了。create_native早期拒否・全7役reader禁止・caps-unknown原owner保持・追加agent禁止。未完了formal/nativeをdev開始条件へ戻さない。Sol容量/人停止は原保全後PAUSED、重複再試行なし。
