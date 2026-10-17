# 第2dev seed・layout11 coreのC0/C1/C2比較（2026-10-13）

保存済み同一合成dev core入力でC0+C1、次にC2を順次fresh compute。人の3候補集約許可に従い、既存CLI2候補上限を維持して解析・文書・Gitを1単位にまとめた。処理成功を性能保証・勝者採択・正式受入へしない。

## 入力と実行

- dataset anomaly-v03-dev-seed-7466813550306735603-layout-11-core / seed7466813550306735603/layout11/core。元生成候補C0と実評価候補を別fieldに保存。同seedの追加layout、新独立seedではない。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\023\attempt-0001\result\payload\manifest.json / {"bytes": 75715, "sha256": "c5802ccc7f4db87b9dd3b92e5f976aa0af59a773dda8b8b6d9e6e30eca6854c0"}。3候補input10全pin一致→各CLI新snapshot/fresh calibration/fit。元payload書込み・新dataset生成・replay0。
- checkout 49e52638616f7e2409c62732a8247a5b7edd3fe6 / 計算661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/candidatecompiled不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}。
- C0 threshold4/C1C2 threshold6/operator>/persistence2/GT/matching不変。全原thresholdflag照合。宣言pinはfull loaded runtime/native認証ではない。
- 原manifest/result pins [{"candidate": "c0-diff-control", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout11-core-c0-c1-20261013\\manifest.json", "manifest_pin": {"bytes": 11025, "sha256": "8fd85b9e91d931bbeebf689922706d56e58809bf9d2b69c71f969adb83eb7d91"}, "result_pin": {"bytes": 13899802, "sha256": "599150c67e823f1eaa811eb4d006db4e4591a0a812cde33b6f639bd85f322ea6"}}, {"candidate": "c1-phase-level", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout11-core-c0-c1-20261013\\manifest.json", "manifest_pin": {"bytes": 11025, "sha256": "8fd85b9e91d931bbeebf689922706d56e58809bf9d2b69c71f969adb83eb7d91"}, "result_pin": {"bytes": 14072782, "sha256": "6eda996b3db6a401d5aa7107429b6ed3bc497154a8c215146294d0da85741faa"}}, {"candidate": "c2-phase-conditional", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout11-core-c2-20261013\\manifest.json", "manifest_pin": {"bytes": 8035, "sha256": "20a34eeb68e18c66e18e5daf77a3ecabf126e131c2598207ad22a1434229d03a"}, "result_pin": {"bytes": 24753552, "sha256": "81f5eb07f9a574531be2304f9a6d78cadf043fca414b1638c253e78f9aad9147"}}]。

|group|run|elapsed秒|sampled private peak B|
|---|---|---|---|
|c0-diff-control,c1-phase-level|dev-seed7466813550306735603-layout11-core-c0-c1-20261013|31.816948399995454|151822336|
|c2-phase-conditional|dev-seed7466813550306735603-layout11-core-c2-20261013|26.656881999922916|211890176|

CLI exit0/complete/成功cell2と1、原結果保存後だけsuccess計上。実CLI時間合計 58.47383039991837秒。単候補速度比較の再実行0、速度向上倍率は推定しない。

## 同一入力の原結果

|候補|machine|sensor|precision|clean / unmatched|source / equipment|available / unavailable|delay count / mean / median|
|---|---|---|---|---|---|---|
|c0-diff-control|0/10|2/10|2/2|0 / 0|2 / 2|13920 / 480|2 / 2.5 / 2.5|
|c1-phase-level|10/10|10/10|20/20|0 / 0|30 / 20|13920 / 480|20 / 1.5 / 1.5|
|c2-phase-conditional|10/10|10/10|20/20|0 / 0|43 / 20|13920 / 480|20 / 1.5 / 1.5|

全14400scores/利用可13920/不能480（mode_recipe_or_phase）。不能全score/residualnull・thresholdfalse。18000input-mask対応/nonok0。48calibrated/calibration各290、fit sample countsとC2stateは以下の原値。全未検出delaynull補完0。clean_rate/burdenは原単位の指標で単純確率へしない。

### c0-diff-control

profiles {"calibration_counts": {"290": 48}, "fit_counts": {"0": 48}, "statuses": {"calibrated": 48}} / C2state 0 / incident reasons {"causal_detected": 2, "no_candidate_in_window": 18}。
delay原 {"conditioned_on": "causal-detected-only", "count": 2, "max": 3.0, "mean": 2.5, "median": 2.5, "min": 2.0, "undetected_fill": "forbidden", "unit": "seconds"} / class別 {"machine": {}, "sensor": {"2.0": 1, "3.0": 1}}。未検出 18 件は全delaynull。
source内訳 {"conveyor-01.motor_temperature": 2}。原source support2score、equipment membership、全未検出窓と選択failed candidateを-save/target-episode-supportへ保存。cleanと全未対応equipmentを別々に保持。
clean_rate {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 3365, "null_replicates": 0, "numerator": 0, "value": 0.0} / effective seconds 3255 / effective_rate 0.0 / burden {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 20, "null_replicates": 0, "numerator": 0, "value": 0.0}。
対象window分類は以下の全20原値（available/unavailable/phase/maxstreak）を参照。

|cycle|class|start–end|available|unavailable|phase|maximum streak|reason|candidate count|
|---|---|---|---|---|---|---|---|---|
|0|sensor|7350–7356|6|1|1|1|no_candidate_in_window|0|
|0|machine|7371–7377|7|0|0|1|no_candidate_in_window|0|
|1|sensor|7530–7536|6|1|1|1|no_candidate_in_window|0|
|1|machine|7551–7557|7|0|0|1|no_candidate_in_window|0|
|2|sensor|7710–7716|6|1|1|3|causal_detected|1|
|2|machine|7731–7737|7|0|0|1|no_candidate_in_window|0|
|3|sensor|7890–7896|6|1|1|1|no_candidate_in_window|0|
|3|machine|7911–7917|7|0|0|1|no_candidate_in_window|0|
|4|sensor|8070–8076|6|1|1|1|no_candidate_in_window|0|
|4|machine|8091–8097|7|0|0|1|no_candidate_in_window|0|
|5|sensor|8250–8256|6|1|1|1|no_candidate_in_window|0|
|5|machine|8271–8277|7|0|0|1|no_candidate_in_window|0|
|6|sensor|8430–8436|6|1|1|1|no_candidate_in_window|0|
|6|machine|8451–8457|7|0|0|1|no_candidate_in_window|0|
|7|sensor|8610–8616|6|1|1|1|no_candidate_in_window|0|
|7|machine|8631–8637|7|0|0|1|no_candidate_in_window|0|
|8|sensor|8790–8796|6|1|1|2|causal_detected|1|
|8|machine|8811–8817|7|0|0|1|no_candidate_in_window|0|
|9|sensor|8970–8976|6|1|1|1|no_candidate_in_window|0|
|9|machine|8991–8997|7|0|0|1|no_candidate_in_window|0|

### c1-phase-level

profiles {"calibration_counts": {"290": 48}, "fit_counts": {"600": 48}, "statuses": {"calibrated": 48}} / C2state 0 / incident reasons {"causal_detected": 20}。
delay原 {"conditioned_on": "causal-detected-only", "count": 20, "max": 2.0, "mean": 1.5, "median": 1.5, "min": 1.0, "undetected_fill": "forbidden", "unit": "seconds"} / class別 {"machine": {"1.0": 10}, "sensor": {"2.0": 10}}。未検出 0 件は全delaynull。
source内訳 {"conveyor-01.conveyor_speed": 10, "conveyor-01.motor_temperature": 10, "conveyor-01.vibration_feature": 10}。原source support2score、equipment membership、全未検出窓と選択failed candidateを-save/target-episode-supportへ保存。cleanと全未対応equipmentを別々に保持。
clean_rate {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 3365, "null_replicates": 0, "numerator": 0, "value": 0.0} / effective seconds 3255 / effective_rate 0.0 / burden {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 20, "null_replicates": 0, "numerator": 0, "value": 0.0}。
対象window分類は以下の全20原値（available/unavailable/phase/maxstreak）を参照。

|cycle|class|start–end|available|unavailable|phase|maximum streak|reason|candidate count|
|---|---|---|---|---|---|---|---|---|
|0|sensor|7350–7356|6|1|1|2|causal_detected|1|
|0|machine|7371–7377|7|0|0|3|causal_detected|1|
|1|sensor|7530–7536|6|1|1|2|causal_detected|1|
|1|machine|7551–7557|7|0|0|3|causal_detected|1|
|2|sensor|7710–7716|6|1|1|2|causal_detected|1|
|2|machine|7731–7737|7|0|0|3|causal_detected|1|
|3|sensor|7890–7896|6|1|1|2|causal_detected|1|
|3|machine|7911–7917|7|0|0|3|causal_detected|1|
|4|sensor|8070–8076|6|1|1|2|causal_detected|1|
|4|machine|8091–8097|7|0|0|3|causal_detected|1|
|5|sensor|8250–8256|6|1|1|2|causal_detected|1|
|5|machine|8271–8277|7|0|0|3|causal_detected|1|
|6|sensor|8430–8436|6|1|1|2|causal_detected|1|
|6|machine|8451–8457|7|0|0|3|causal_detected|1|
|7|sensor|8610–8616|6|1|1|2|causal_detected|1|
|7|machine|8631–8637|7|0|0|3|causal_detected|1|
|8|sensor|8790–8796|6|1|1|2|causal_detected|1|
|8|machine|8811–8817|7|0|0|3|causal_detected|1|
|9|sensor|8970–8976|6|1|1|2|causal_detected|1|
|9|machine|8991–8997|7|0|0|3|causal_detected|1|

### c2-phase-conditional

profiles {"calibration_counts": {"290": 48}, "fit_counts": {"600": 48}, "statuses": {"calibrated": 48}} / C2state 48 / incident reasons {"causal_detected": 20}。
delay原 {"conditioned_on": "causal-detected-only", "count": 20, "max": 2.0, "mean": 1.5, "median": 1.5, "min": 1.0, "undetected_fill": "forbidden", "unit": "seconds"} / class別 {"machine": {"1.0": 10}, "sensor": {"2.0": 10}}。未検出 0 件は全delaynull。
source内訳 {"conveyor-01.conveyor_speed": 10, "conveyor-01.motor_current": 1, "conveyor-01.motor_temperature": 12, "conveyor-01.vibration_feature": 20}。原source support2score、equipment membership、全未検出窓と選択failed candidateを-save/target-episode-supportへ保存。cleanと全未対応equipmentを別々に保持。
clean_rate {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 3365, "null_replicates": 0, "numerator": 0, "value": 0.0} / effective seconds 3255 / effective_rate 0.0 / burden {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 20, "null_replicates": 0, "numerator": 0, "value": 0.0}。
対象window分類は以下の全20原値（available/unavailable/phase/maxstreak）を参照。

|cycle|class|start–end|available|unavailable|phase|maximum streak|reason|candidate count|
|---|---|---|---|---|---|---|---|---|
|0|sensor|7350–7356|6|1|1|2|causal_detected|1|
|0|machine|7371–7377|7|0|0|3|causal_detected|1|
|1|sensor|7530–7536|6|1|1|2|causal_detected|1|
|1|machine|7551–7557|7|0|0|3|causal_detected|1|
|2|sensor|7710–7716|6|1|1|2|causal_detected|1|
|2|machine|7731–7737|7|0|0|3|causal_detected|1|
|3|sensor|7890–7896|6|1|1|2|causal_detected|1|
|3|machine|7911–7917|7|0|0|3|causal_detected|1|
|4|sensor|8070–8076|6|1|1|2|causal_detected|1|
|4|machine|8091–8097|7|0|0|3|causal_detected|1|
|5|sensor|8250–8256|6|1|1|2|causal_detected|1|
|5|machine|8271–8277|7|0|0|3|causal_detected|1|
|6|sensor|8430–8436|6|1|1|2|causal_detected|1|
|6|machine|8451–8457|7|0|0|3|causal_detected|1|
|7|sensor|8610–8616|6|1|1|2|causal_detected|1|
|7|machine|8631–8637|7|0|0|3|causal_detected|1|
|8|sensor|8790–8796|6|1|1|2|causal_detected|1|
|8|machine|8811–8817|7|0|0|3|causal_detected|1|
|9|sensor|8970–8976|6|1|1|2|causal_detected|1|
|9|machine|8991–8997|7|0|0|3|causal_detected|1|

## 前layout core保存指標との比較

|layout|candidate|machine|sensor|precision|clean|
|---|---|---|---|---|---|
|10|c0-diff-control|0/10|0/10|0/1|1|
|10|c1-phase-level|10/10|10/10|20/20|0|
|10|c2-phase-conditional|10/10|10/10|20/20|0|
|11|c0-diff-control|0/10|2/10|2/2|0|
|11|c1-phase-level|10/10|10/10|20/20|0|
|11|c2-phase-conditional|10/10|10/10|20/20|0|

旧layout10はmanifest/config保存指標だけ比較・再compute0。同seed別layoutで観測inputは異なり、独立新seedや1要因だけの反実仮想差証明ではない。C1/C2の一部集計一致は全score/episode一致や候補採択の証明へしない。
全候補の全20対象窓の利用可・不能・最大streakと、原選択episodeのtarget対応を上表と保存ledgerから確認した。未検出は原reasonとdelaynullを保持し、閾値・GT・matching変更で補わない。入力対応・保存・状態分類の実経路不具合は観測なし。全用途不適合や包括的実装認証へしない。

対象窓の原分類集約 {"c0-diff-control": {"machine": [{"available": 7, "unavailable": 0, "phase_unavailable": 0, "max_streak": 1, "window_count": 10}], "sensor": [{"available": 6, "unavailable": 1, "phase_unavailable": 1, "max_streak": 1, "window_count": 8}, {"available": 6, "unavailable": 1, "phase_unavailable": 1, "max_streak": 3, "window_count": 1}, {"available": 6, "unavailable": 1, "phase_unavailable": 1, "max_streak": 2, "window_count": 1}]}, "c1-phase-level": {"machine": [{"available": 7, "unavailable": 0, "phase_unavailable": 0, "max_streak": 3, "window_count": 10}], "sensor": [{"available": 6, "unavailable": 1, "phase_unavailable": 1, "max_streak": 2, "window_count": 10}]}, "c2-phase-conditional": {"machine": [{"available": 7, "unavailable": 0, "phase_unavailable": 0, "max_streak": 3, "window_count": 10}], "sensor": [{"available": 6, "unavailable": 1, "phase_unavailable": 1, "max_streak": 2, "window_count": 10}]}}。全対象score/streakと原episode supportを併せて保存し、対象窓の不能だけで全未検出を説明しない。
## 証拠・次工程・正式状態

- 新 representative-seed2-layout11-core-three-candidates-20261013-records/analysis/save/finalを優先。DATA2 {"D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout11-core-c0-c1-20261013": {"bytes": 41020827, "files": 22, "manifest_pin": {"bytes": 2583, "sha256": "5f9e53480601ca263ddbbd8e403fd85cebe6e3a9777ace3465f44630d7b2657a"}}, "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout11-core-c2-20261013": {"bytes": 37795333, "files": 19, "manifest_pin": {"bytes": 2246, "sha256": "59ef9a3491c65fd707670e0ae1cffeb74d45369ed4ecca2e1d82eaa422cba6af"}}}。原profiles/scores/events/incidents/episodes/metricsを保存、全20ledger/対象窓/480不能を-analysisに保存。
- 旧138cellモデル再compute0、第1seed72＋第2seed69＝141boardcells/使用seed2、141独立datasetではない。layout0–10全6cell・layout11core3cell完成。bootstrap/統計CI/勝者採択0。
- 旧580root/502helpers27failed475passedmissingexecution1と全失敗・審査拒否・原誤記を保持。今回新helperfailure0/閉鎖外部固定root追記0/PID単独/native回収claim0。
- report/handoff/index3docs一回[skip ci] commit/push、prepare_result_index実使用。人の具体的通知後の同送信先同種合成dev報告・ユーザー名入りPC内pathの継続送信承認に従う。
- 次同seed/layout11 quality-stress、groups [["c0-diff-control", "c1-phase-level"], ["c2-phase-conditional"]] / IDs ["dev-seed7466813550306735603-layout11-quality-c0-c1-20261013", "dev-seed7466813550306735603-layout11-quality-c2-20261013"]。同chunk023 manifest/identity/input10metadataのみ選択、次本文未読/model0。
- EvidenceStore全writepreflight/自動分割/失敗閉鎖reserveを維持。実行900秒/2GiB/output1GiB/single32MiB/files32、Git30秒/16entry/512KiB/stdout1MiB/stderr128KiBとnativeprotocol caps不変。checkpoint≠blocking中断/fullruntime/allwriter/globalmemory容量認証。
- ACTIVE/automation詳細転記0、新testCIagent0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件最終受入未完了/create_native早期拒否/全7役reader禁止/元capsunknown owner保持。Sol容量または人停止は保全後PAUSED。


## C0の原sensor検出2件

C0の機械0/10、sensor2/10、precision2/2、clean0/unmatched0。検出2件delay2秒と3秒、残る18件はdelaynull。原閾値4/persistence2のまま各sourceを支える2scoreがavailable/threshold_exceeded=true/score>4で、対象sourceとmatched equipment/eventの対応を確認した。原matchingのcausal_detectedを保存し、反実仮想因果証明や全条件での有効性へ一般化しない。
|cycle|event|spike start–end|delay seconds|support samples|support scores|support residuals|
|---|---|---|---|---|---|---|
|2|anomaly-v03-dev-seed-7466813550306735603-layout-11-cycle-02-sensor|7710–7713|2.0|7711,7712|4.561118830253336,4.323290053702135|-0.43861100000000164,-0.41924099999999953|
|8|anomaly-v03-dev-seed-7466813550306735603-layout-11-cycle-08-sensor|8790–8793|3.0|8792,8793|4.075773775617725,101.10517522244895|-0.39908199999999994,-8.301655999999998|

原event/incident/source/equipment/support2scoreを-save/c0-detected-sensor-evidenceへ保存。C0各sensor窓6利用可/phase不能1、最大streakは原値の1/2/3を表へ保持し、全窓maxstreak1へ補わない。C1C2のmachine delay1秒×10/sensor2秒×10、precision20/20/clean0。source C1 30/C2 43を別保持。
