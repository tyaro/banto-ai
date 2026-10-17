# 第2dev seed・layout8 coreのC0/C1/C2比較（2026-10-13）

保存済み同一合成dev core入力でC0+C1、次にC2を順次fresh compute。人の3候補集約許可に従い、既存CLI2候補上限を維持して解析・文書・Gitを1単位にまとめた。処理成功を性能保証・勝者採択・正式受入へしない。

## 入力と実行

- dataset anomaly-v03-dev-seed-7466813550306735603-layout-08-core / seed7466813550306735603/layout8/core。元生成候補C0と実評価候補を別fieldに保存。同seedの追加layout、新独立seedではない。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\020\attempt-0001\result\payload\manifest.json / {"bytes": 75700, "sha256": "2dd0b78a5de7cda8675220d5f364c195a582ce87559fea40b7cddd7c0be2aa5e"}。3候補input10全pin一致→各CLI新snapshot/fresh calibration/fit。元payload書込み・新dataset生成・replay0。
- checkout 2bbda81d86bb778bba56e9d44ada167fc025b214 / 計算661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/candidatecompiled不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}。
- C0 threshold4/C1C2 threshold6/operator>/persistence2/GT/matching不変。全原thresholdflag照合。宣言pinはfull loaded runtime/native認証ではない。
- 原manifest/result pins [{"candidate": "c0-diff-control", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout8-core-c0-c1-20261013\\manifest.json", "manifest_pin": {"bytes": 11054, "sha256": "7fba5e2bd4bf932934568d277b15b91ee2bf14ba9de27c0e5a68eef589725535"}, "result_pin": {"bytes": 13896537, "sha256": "9c5df4f160bcb13caedadd031394ceaec22fd202f82a3a9f0948bd04a2970603"}}, {"candidate": "c1-phase-level", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout8-core-c0-c1-20261013\\manifest.json", "manifest_pin": {"bytes": 11054, "sha256": "7fba5e2bd4bf932934568d277b15b91ee2bf14ba9de27c0e5a68eef589725535"}, "result_pin": {"bytes": 14071307, "sha256": "9c15d9588c08f5c302d154cb49f6be4a403a1abbf50802acc1a28d2bf0b35e86"}}, {"candidate": "c2-phase-conditional", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout8-core-c2-20261013\\manifest.json", "manifest_pin": {"bytes": 8033, "sha256": "62a878dc218bd4d61b5b9108731c2d8dd836b761e71147787319f535003a477a"}, "result_pin": {"bytes": 24749299, "sha256": "7d2ebedb5d54e24db41cedf180f7dc06a2e8d1f03889af88ef7b7df9a447b24d"}}]。

|group|run|elapsed秒|sampled private peak B|
|---|---|---|---|
|c0-diff-control,c1-phase-level|dev-seed7466813550306735603-layout8-core-c0-c1-20261013|31.44273719994817|151556096|
|c2-phase-conditional|dev-seed7466813550306735603-layout8-core-c2-20261013|27.258746800012887|213106688|

CLI exit0/complete/成功cell2と1、原結果保存後だけsuccess計上。実CLI時間合計 58.701483999961056秒。単候補速度比較の再実行0、速度向上倍率は推定しない。

## 同一入力の原結果

|候補|machine|sensor|precision|clean / unmatched|source / equipment|available / unavailable|delay count / mean / median|
|---|---|---|---|---|---|---|
|c0-diff-control|0/10|0/10|0/1|1 / 1|1 / 1|13920 / 480|0 / None / None|
|c1-phase-level|10/10|10/10|20/20|0 / 0|30 / 20|13920 / 480|20 / 1.5 / 1.5|
|c2-phase-conditional|10/10|10/10|20/20|0 / 0|40 / 20|13920 / 480|20 / 1.5 / 1.5|

全14400scores/利用可13920/不能480（mode_recipe_or_phase）。不能全score/residualnull・thresholdfalse。18000input-mask対応/nonok0。48calibrated/calibration各290、fit sample countsとC2stateは以下の原値。全未検出delaynull補完0。clean_rate/burdenは原単位の指標で単純確率へしない。

### c0-diff-control

profiles {"calibration_counts": {"290": 48}, "fit_counts": {"0": 48}, "statuses": {"calibrated": 48}} / C2state 0 / incident reasons {"no_candidate_in_window": 20}。
delay原 {"conditioned_on": "causal-detected-only", "count": 0, "max": null, "mean": null, "median": null, "min": null, "undetected_fill": "forbidden", "unit": "seconds"} / class別 {"machine": {}, "sensor": {}}。未検出 20 件は全delaynull。
source内訳 {"conveyor-01.motor_temperature": 1}。原source support2score、equipment membership、全未検出窓と選択failed candidateを-save/target-episode-supportへ保存。cleanと全未対応equipmentを別々に保持。
clean_rate {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 3365, "null_replicates": 0, "numerator": 1, "value": 8.558692421991084} / effective seconds 3255 / effective_rate 8.847926267281107 / burden {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 20, "null_replicates": 0, "numerator": 1, "value": 5.0}。
対象window分類は以下の全20原値（available/unavailable/phase/maxstreak）を参照。

|cycle|class|start–end|available|unavailable|phase|maximum streak|reason|candidate count|
|---|---|---|---|---|---|---|---|---|
|0|machine|7260–7266|6|1|1|1|no_candidate_in_window|0|
|0|sensor|7267–7273|7|0|0|1|no_candidate_in_window|0|
|1|machine|7440–7446|6|1|1|1|no_candidate_in_window|0|
|1|sensor|7447–7453|7|0|0|1|no_candidate_in_window|0|
|2|machine|7620–7626|6|1|1|1|no_candidate_in_window|0|
|2|sensor|7627–7633|7|0|0|1|no_candidate_in_window|0|
|3|machine|7800–7806|6|1|1|1|no_candidate_in_window|0|
|3|sensor|7807–7813|7|0|0|1|no_candidate_in_window|0|
|4|machine|7980–7986|6|1|1|1|no_candidate_in_window|0|
|4|sensor|7987–7993|7|0|0|1|no_candidate_in_window|0|
|5|machine|8160–8166|6|1|1|1|no_candidate_in_window|0|
|5|sensor|8167–8173|7|0|0|1|no_candidate_in_window|0|
|6|machine|8340–8346|6|1|1|1|no_candidate_in_window|0|
|6|sensor|8347–8353|7|0|0|1|no_candidate_in_window|0|
|7|machine|8520–8526|6|1|1|1|no_candidate_in_window|0|
|7|sensor|8527–8533|7|0|0|1|no_candidate_in_window|0|
|8|machine|8700–8706|6|1|1|1|no_candidate_in_window|0|
|8|sensor|8707–8713|7|0|0|1|no_candidate_in_window|0|
|9|machine|8880–8886|6|1|1|1|no_candidate_in_window|0|
|9|sensor|8887–8893|7|0|0|1|no_candidate_in_window|0|

### c1-phase-level

profiles {"calibration_counts": {"290": 48}, "fit_counts": {"600": 48}, "statuses": {"calibrated": 48}} / C2state 0 / incident reasons {"causal_detected": 20}。
delay原 {"conditioned_on": "causal-detected-only", "count": 20, "max": 2.0, "mean": 1.5, "median": 1.5, "min": 1.0, "undetected_fill": "forbidden", "unit": "seconds"} / class別 {"machine": {"2.0": 10}, "sensor": {"1.0": 10}}。未検出 0 件は全delaynull。
source内訳 {"conveyor-01.conveyor_speed": 10, "conveyor-01.motor_temperature": 10, "conveyor-01.vibration_feature": 10}。原source support2score、equipment membership、全未検出窓と選択failed candidateを-save/target-episode-supportへ保存。cleanと全未対応equipmentを別々に保持。
clean_rate {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 3365, "null_replicates": 0, "numerator": 0, "value": 0.0} / effective seconds 3255 / effective_rate 0.0 / burden {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 20, "null_replicates": 0, "numerator": 0, "value": 0.0}。
対象window分類は以下の全20原値（available/unavailable/phase/maxstreak）を参照。

|cycle|class|start–end|available|unavailable|phase|maximum streak|reason|candidate count|
|---|---|---|---|---|---|---|---|---|
|0|machine|7260–7266|6|1|1|2|causal_detected|1|
|0|sensor|7267–7273|7|0|0|3|causal_detected|1|
|1|machine|7440–7446|6|1|1|2|causal_detected|1|
|1|sensor|7447–7453|7|0|0|3|causal_detected|1|
|2|machine|7620–7626|6|1|1|2|causal_detected|1|
|2|sensor|7627–7633|7|0|0|3|causal_detected|1|
|3|machine|7800–7806|6|1|1|2|causal_detected|1|
|3|sensor|7807–7813|7|0|0|3|causal_detected|1|
|4|machine|7980–7986|6|1|1|2|causal_detected|1|
|4|sensor|7987–7993|7|0|0|3|causal_detected|1|
|5|machine|8160–8166|6|1|1|2|causal_detected|1|
|5|sensor|8167–8173|7|0|0|3|causal_detected|1|
|6|machine|8340–8346|6|1|1|2|causal_detected|1|
|6|sensor|8347–8353|7|0|0|3|causal_detected|1|
|7|machine|8520–8526|6|1|1|2|causal_detected|1|
|7|sensor|8527–8533|7|0|0|3|causal_detected|1|
|8|machine|8700–8706|6|1|1|2|causal_detected|1|
|8|sensor|8707–8713|7|0|0|3|causal_detected|1|
|9|machine|8880–8886|6|1|1|2|causal_detected|1|
|9|sensor|8887–8893|7|0|0|3|causal_detected|1|

### c2-phase-conditional

profiles {"calibration_counts": {"290": 48}, "fit_counts": {"600": 48}, "statuses": {"calibrated": 48}} / C2state 48 / incident reasons {"causal_detected": 20}。
delay原 {"conditioned_on": "causal-detected-only", "count": 20, "max": 2.0, "mean": 1.5, "median": 1.5, "min": 1.0, "undetected_fill": "forbidden", "unit": "seconds"} / class別 {"machine": {"2.0": 10}, "sensor": {"1.0": 10}}。未検出 0 件は全delaynull。
source内訳 {"conveyor-01.conveyor_speed": 10, "conveyor-01.motor_current": 10, "conveyor-01.motor_temperature": 10, "conveyor-01.vibration_feature": 10}。原source support2score、equipment membership、全未検出窓と選択failed candidateを-save/target-episode-supportへ保存。cleanと全未対応equipmentを別々に保持。
clean_rate {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 3365, "null_replicates": 0, "numerator": 0, "value": 0.0} / effective seconds 3255 / effective_rate 0.0 / burden {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 20, "null_replicates": 0, "numerator": 0, "value": 0.0}。
対象window分類は以下の全20原値（available/unavailable/phase/maxstreak）を参照。

|cycle|class|start–end|available|unavailable|phase|maximum streak|reason|candidate count|
|---|---|---|---|---|---|---|---|---|
|0|machine|7260–7266|6|1|1|2|causal_detected|1|
|0|sensor|7267–7273|7|0|0|3|causal_detected|1|
|1|machine|7440–7446|6|1|1|2|causal_detected|1|
|1|sensor|7447–7453|7|0|0|3|causal_detected|1|
|2|machine|7620–7626|6|1|1|2|causal_detected|1|
|2|sensor|7627–7633|7|0|0|3|causal_detected|1|
|3|machine|7800–7806|6|1|1|2|causal_detected|1|
|3|sensor|7807–7813|7|0|0|3|causal_detected|1|
|4|machine|7980–7986|6|1|1|2|causal_detected|1|
|4|sensor|7987–7993|7|0|0|3|causal_detected|1|
|5|machine|8160–8166|6|1|1|2|causal_detected|1|
|5|sensor|8167–8173|7|0|0|3|causal_detected|1|
|6|machine|8340–8346|6|1|1|2|causal_detected|1|
|6|sensor|8347–8353|7|0|0|3|causal_detected|1|
|7|machine|8520–8526|6|1|1|2|causal_detected|1|
|7|sensor|8527–8533|7|0|0|3|causal_detected|1|
|8|machine|8700–8706|6|1|1|2|causal_detected|1|
|8|sensor|8707–8713|7|0|0|3|causal_detected|1|
|9|machine|8880–8886|6|1|1|2|causal_detected|1|
|9|sensor|8887–8893|7|0|0|3|causal_detected|1|

## 前layout core保存指標との比較

|layout|candidate|machine|sensor|precision|clean|
|---|---|---|---|---|---|
|7|c0-diff-control|0/10|0/10|0/1|1|
|7|c1-phase-level|10/10|10/10|20/20|0|
|7|c2-phase-conditional|10/10|10/10|20/20|0|
|8|c0-diff-control|0/10|0/10|0/1|1|
|8|c1-phase-level|10/10|10/10|20/20|0|
|8|c2-phase-conditional|10/10|10/10|20/20|0|

旧layout7はmanifest/config保存指標だけ比較・再compute0。同seed別layoutで観測inputは異なり、独立新seedや1要因だけの反実仮想差証明ではない。C1/C2の一部集計一致は全score/episode一致や候補採択の証明へしない。
全候補の全20対象窓の利用可・不能・最大streakと、原選択episodeのtarget対応を上表と保存ledgerから確認した。未検出は原reasonとdelaynullを保持し、閾値・GT・matching変更で補わない。入力対応・保存・状態分類の実経路不具合は観測なし。全用途不適合や包括的実装認証へしない。

対象窓の原分類集約 {"c0-diff-control": {"machine": [{"available": 6, "unavailable": 1, "phase_unavailable": 1, "max_streak": 1, "window_count": 10}], "sensor": [{"available": 7, "unavailable": 0, "phase_unavailable": 0, "max_streak": 1, "window_count": 10}]}, "c1-phase-level": {"machine": [{"available": 6, "unavailable": 1, "phase_unavailable": 1, "max_streak": 2, "window_count": 10}], "sensor": [{"available": 7, "unavailable": 0, "phase_unavailable": 0, "max_streak": 3, "window_count": 10}]}, "c2-phase-conditional": {"machine": [{"available": 6, "unavailable": 1, "phase_unavailable": 1, "max_streak": 2, "window_count": 10}], "sensor": [{"available": 7, "unavailable": 0, "phase_unavailable": 0, "max_streak": 3, "window_count": 10}]}}。全対象score/streakと原episode supportを併せて保存し、対象窓の不能だけで全未検出を説明しない。
## 証拠・次工程・正式状態

- 新 representative-seed2-layout8-core-three-candidates-20261013-records/analysis/save/finalを優先。DATA2 {"D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout8-core-c0-c1-20261013": {"bytes": 41015700, "files": 22, "manifest_pin": {"bytes": 2582, "sha256": "d92b500e523c166cedac277777e81e5e462bb8c1beb46a9c981348992ff382e5"}}, "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout8-core-c2-20261013": {"bytes": 37790630, "files": 19, "manifest_pin": {"bytes": 2245, "sha256": "5651f1c651abc45d243f81a286a4b53ddd0b6d8aeb557f68b8d82bbb4ebea3f0"}}}。原profiles/scores/events/incidents/episodes/metricsを保存、全20ledger/対象窓/480不能を-analysisに保存。
- 旧120cellモデル再compute0、第1seed72＋第2seed51＝123boardcells/使用seed2、123独立datasetではない。layout0–7全6cell・layout8core3cell完成。bootstrap/統計CI/勝者採択0。
- 旧542root/476helpers25failed451passedmissingexecution1と全失敗・審査拒否・原誤記を保持。今回新helperfailure0/閉鎖外部固定root追記0/PID単独/native回収claim0。
- report/handoff/index3docs一回[skip ci] commit/push、prepare_result_index実使用。人の具体的通知後の同送信先同種合成dev報告・ユーザー名入りPC内pathの継続送信承認に従う。
- 次同seed/layout8 quality-stress、groups [["c0-diff-control", "c1-phase-level"], ["c2-phase-conditional"]] / IDs ["dev-seed7466813550306735603-layout8-quality-c0-c1-20261013", "dev-seed7466813550306735603-layout8-quality-c2-20261013"]。同chunk020 manifest/identity/input10metadataのみ選択、次本文未読/model0。
- EvidenceStore全writepreflight/自動分割/失敗閉鎖reserveを維持。実行900秒/2GiB/output1GiB/single32MiB/files32、Git30秒/16entry/512KiB/stdout1MiB/stderr128KiBとnativeprotocol caps不変。checkpoint≠blocking中断/fullruntime/allwriter/globalmemory容量認証。
- ACTIVE/automation詳細転記0、新testCIagent0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件最終受入未完了/create_native早期拒否/全7役reader禁止/元capsunknown owner保持。Sol容量または人停止は保全後PAUSED。


機械10窓は各先頭1行phase不能、残り6行利用可。C1/C2は原maxstreak2でdelay2秒×10、sensor10窓は7行利用可/maxstreak3でdelay1秒×10。C0は全20窓maxstreak1/no_candidate_in_window/candidate0で固定persistence2不成立。全対象score・原episode supportを保存し、phase不能だけでC0全20未検出を説明しない。
