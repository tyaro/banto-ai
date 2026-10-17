# 第2dev seed・layout7 quality-stressの3候補とcore比較（2026-10-13）

保存済み同一合成dev quality-stress入力でC0+C1、次にC2を順次fresh compute。人の3候補集約許可に従い、既存CLI2候補上限を維持して解析・文書・Gitを1単位にまとめた。処理成功を性能保証・勝者採択・正式受入へしない。

## 入力と実行

- dataset anomaly-v03-dev-seed-7466813550306735603-layout-07-quality-stress / seed7466813550306735603/layout7/quality-stress。元生成候補C0と実評価候補を別fieldに保存。同seedの追加layout、新独立seedではない。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\019\attempt-0001\result\payload\manifest.json / {"bytes": 75700, "sha256": "9dc8513ebff4fa25510a5f3fab4ea2531c48dfa0ee800dc5b7c095475c7fc6f8"}。3候補input10全pin一致→各CLI新snapshot/fresh calibration/fit。元payload書込み・新dataset生成・replay0。
- checkout d831c93d9af6e952c8604d072e8d197c63ca3765 / 計算661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/candidatecompiled不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}。
- C0 threshold4/C1C2 threshold6/operator>/persistence2/GT/matching不変。全原thresholdflag照合。宣言pinはfull loaded runtime/native認証ではない。
- 原manifest/result pins [{"candidate": "c0-diff-control", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout7-quality-c0-c1-20261013\\manifest.json", "manifest_pin": {"bytes": 11102, "sha256": "709bc1e89cfeeeb0496694c32ead38055e8a97c5de9347913353e22ea1d9c84c"}, "result_pin": {"bytes": 14333423, "sha256": "eca1f20e812bb4dad8263477430d2bdce570ae3dab48973b27cb9d68258e78cb"}}, {"candidate": "c1-phase-level", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout7-quality-c0-c1-20261013\\manifest.json", "manifest_pin": {"bytes": 11102, "sha256": "709bc1e89cfeeeb0496694c32ead38055e8a97c5de9347913353e22ea1d9c84c"}, "result_pin": {"bytes": 14510603, "sha256": "94f6972e5a7af279609dca8b6ebd334d82295c9fa7774f77db1ad5c4bb993542"}}, {"candidate": "c2-phase-conditional", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout7-quality-c2-20261013\\manifest.json", "manifest_pin": {"bytes": 8080, "sha256": "f2ff34945283ed6983ef98db80fbcbaa4b31d6ff7dd2a618076ed564e5097295"}, "result_pin": {"bytes": 25190996, "sha256": "5c1dc7c48772015edd094f070490622ce1668be3228659f42d4f56227f056a0c"}}]。

|group|run|elapsed秒|sampled private peak B|
|---|---|---|---|
|c0-diff-control,c1-phase-level|dev-seed7466813550306735603-layout7-quality-c0-c1-20261013|32.173685399931855|150114304|
|c2-phase-conditional|dev-seed7466813550306735603-layout7-quality-c2-20261013|28.956608599983156|211296256|

CLI exit0/complete/成功cell2と1、原結果保存後だけsuccess計上。実CLI時間合計 61.13029399991501秒。単候補速度比較の再実行0、速度向上倍率は推定しない。

## 同一入力の原結果

|候補|machine|sensor|precision|clean / unmatched|source / equipment|available / unavailable|delay count / mean / median|
|---|---|---|---|---|---|---|
|c0-diff-control|0/10|0/10|0/1|1 / 1|1 / 1|13880 / 520|0 / None / None|
|c1-phase-level|10/10|9/10|19/19|0 / 0|29 / 19|13880 / 520|19 / 1.4736842105263157 / 1.0|
|c2-phase-conditional|10/10|9/10|19/19|0 / 0|39 / 19|13760 / 640|19 / 1.4736842105263157 / 1.0|

全14400scoresの利用可・不能数と排他的primary reasonは下記原結果の集計を参照。不能全score/residualnull・thresholdfalse。18000input-mask対応/nonok30。48calibrated/calibration各290、fit sample countsとC2stateは以下の原値。全未検出delaynull補完0。clean_rate/burdenは原単位の指標で単純確率へしない。

### c0-diff-control

profiles {"calibration_counts": {"290": 48}, "fit_counts": {"0": 48}, "statuses": {"calibrated": 48}} / C2state 0 / incident reasons {"no_candidate_in_window": 20}。
delay原 {"conditioned_on": "causal-detected-only", "count": 0, "max": null, "mean": null, "median": null, "min": null, "undetected_fill": "forbidden", "unit": "seconds"} / class別 {"machine": {}, "sensor": {}}。未検出 20 件は全delaynull。
source内訳 {"conveyor-01.motor_temperature": 1}。原source support2score、equipment membership、全未検出窓と選択failed candidateを-save/target-episode-supportへ保存。cleanと全未対応equipmentを別々に保持。
clean_rate {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 3365, "null_replicates": 0, "numerator": 1, "value": 8.558692421991084} / effective seconds 3255 / effective_rate 8.847926267281107 / burden {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 20, "null_replicates": 0, "numerator": 1, "value": 5.0}。
対象window分類は以下の全20原値（available/unavailable/phase/maxstreak）を参照。

|cycle|class|start–end|available|unavailable|phase|maximum streak|reason|candidate count|
|---|---|---|---|---|---|---|---|---|
|0|sensor|7230–7236|6|1|1|1|no_candidate_in_window|0|
|0|machine|7251–7257|7|0|0|1|no_candidate_in_window|0|
|1|sensor|7410–7416|6|1|1|1|no_candidate_in_window|0|
|1|machine|7431–7437|7|0|0|1|no_candidate_in_window|0|
|2|sensor|7590–7596|6|1|1|1|no_candidate_in_window|0|
|2|machine|7611–7617|7|0|0|1|no_candidate_in_window|0|
|3|sensor|7770–7776|6|1|1|1|no_candidate_in_window|0|
|3|machine|7791–7797|7|0|0|1|no_candidate_in_window|0|
|4|sensor|7950–7956|6|1|1|1|no_candidate_in_window|0|
|4|machine|7971–7977|7|0|0|1|no_candidate_in_window|0|
|5|sensor|8130–8136|6|1|1|1|no_candidate_in_window|0|
|5|machine|8151–8157|7|0|0|1|no_candidate_in_window|0|
|6|sensor|8310–8316|6|1|1|1|no_candidate_in_window|0|
|6|machine|8331–8337|7|0|0|1|no_candidate_in_window|0|
|7|sensor|8490–8496|6|1|1|1|no_candidate_in_window|0|
|7|machine|8511–8517|7|0|0|1|no_candidate_in_window|0|
|8|sensor|8670–8676|6|1|1|1|no_candidate_in_window|0|
|8|machine|8691–8697|7|0|0|1|no_candidate_in_window|0|
|9|sensor|8850–8856|2|5|1|0|no_candidate_in_window|0|
|9|machine|8871–8877|7|0|0|1|no_candidate_in_window|0|

### c1-phase-level

profiles {"calibration_counts": {"290": 48}, "fit_counts": {"600": 48}, "statuses": {"calibrated": 48}} / C2state 0 / incident reasons {"causal_detected": 19, "no_candidate_in_window": 1}。
delay原 {"conditioned_on": "causal-detected-only", "count": 19, "max": 2.0, "mean": 1.4736842105263157, "median": 1.0, "min": 1.0, "undetected_fill": "forbidden", "unit": "seconds"} / class別 {"machine": {"1.0": 10}, "sensor": {"2.0": 9}}。未検出 1 件は全delaynull。
source内訳 {"conveyor-01.conveyor_speed": 10, "conveyor-01.motor_temperature": 9, "conveyor-01.vibration_feature": 10}。原source support2score、equipment membership、全未検出窓と選択failed candidateを-save/target-episode-supportへ保存。cleanと全未対応equipmentを別々に保持。
clean_rate {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 3365, "null_replicates": 0, "numerator": 0, "value": 0.0} / effective seconds 3255 / effective_rate 0.0 / burden {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 20, "null_replicates": 0, "numerator": 0, "value": 0.0}。
対象window分類は以下の全20原値（available/unavailable/phase/maxstreak）を参照。

|cycle|class|start–end|available|unavailable|phase|maximum streak|reason|candidate count|
|---|---|---|---|---|---|---|---|---|
|0|sensor|7230–7236|6|1|1|2|causal_detected|1|
|0|machine|7251–7257|7|0|0|3|causal_detected|1|
|1|sensor|7410–7416|6|1|1|2|causal_detected|1|
|1|machine|7431–7437|7|0|0|3|causal_detected|1|
|2|sensor|7590–7596|6|1|1|2|causal_detected|1|
|2|machine|7611–7617|7|0|0|3|causal_detected|1|
|3|sensor|7770–7776|6|1|1|2|causal_detected|1|
|3|machine|7791–7797|7|0|0|3|causal_detected|1|
|4|sensor|7950–7956|6|1|1|2|causal_detected|1|
|4|machine|7971–7977|7|0|0|3|causal_detected|1|
|5|sensor|8130–8136|6|1|1|2|causal_detected|1|
|5|machine|8151–8157|7|0|0|3|causal_detected|1|
|6|sensor|8310–8316|6|1|1|2|causal_detected|1|
|6|machine|8331–8337|7|0|0|3|causal_detected|1|
|7|sensor|8490–8496|6|1|1|2|causal_detected|1|
|7|machine|8511–8517|7|0|0|3|causal_detected|1|
|8|sensor|8670–8676|6|1|1|2|causal_detected|1|
|8|machine|8691–8697|7|0|0|3|causal_detected|1|
|9|sensor|8850–8856|2|5|1|0|no_candidate_in_window|0|
|9|machine|8871–8877|7|0|0|3|causal_detected|1|

### c2-phase-conditional

profiles {"calibration_counts": {"290": 48}, "fit_counts": {"600": 48}, "statuses": {"calibrated": 48}} / C2state 48 / incident reasons {"causal_detected": 19, "no_candidate_in_window": 1}。
delay原 {"conditioned_on": "causal-detected-only", "count": 19, "max": 2.0, "mean": 1.4736842105263157, "median": 1.0, "min": 1.0, "undetected_fill": "forbidden", "unit": "seconds"} / class別 {"machine": {"1.0": 10}, "sensor": {"2.0": 9}}。未検出 1 件は全delaynull。
source内訳 {"conveyor-01.conveyor_speed": 19, "conveyor-01.motor_temperature": 10, "conveyor-01.vibration_feature": 10}。原source support2score、equipment membership、全未検出窓と選択failed candidateを-save/target-episode-supportへ保存。cleanと全未対応equipmentを別々に保持。
clean_rate {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 3365, "null_replicates": 0, "numerator": 0, "value": 0.0} / effective seconds 3255 / effective_rate 0.0 / burden {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 20, "null_replicates": 0, "numerator": 0, "value": 0.0}。
対象window分類は以下の全20原値（available/unavailable/phase/maxstreak）を参照。

|cycle|class|start–end|available|unavailable|phase|maximum streak|reason|candidate count|
|---|---|---|---|---|---|---|---|---|
|0|sensor|7230–7236|6|1|1|2|causal_detected|1|
|0|machine|7251–7257|7|0|0|3|causal_detected|1|
|1|sensor|7410–7416|6|1|1|2|causal_detected|1|
|1|machine|7431–7437|7|0|0|3|causal_detected|1|
|2|sensor|7590–7596|6|1|1|2|causal_detected|1|
|2|machine|7611–7617|7|0|0|3|causal_detected|1|
|3|sensor|7770–7776|6|1|1|2|causal_detected|1|
|3|machine|7791–7797|7|0|0|3|causal_detected|1|
|4|sensor|7950–7956|6|1|1|2|causal_detected|1|
|4|machine|7971–7977|7|0|0|3|causal_detected|1|
|5|sensor|8130–8136|6|1|1|2|causal_detected|1|
|5|machine|8151–8157|7|0|0|3|causal_detected|1|
|6|sensor|8310–8316|6|1|1|2|causal_detected|1|
|6|machine|8331–8337|7|0|0|3|causal_detected|1|
|7|sensor|8490–8496|6|1|1|2|causal_detected|1|
|7|machine|8511–8517|7|0|0|3|causal_detected|1|
|8|sensor|8670–8676|6|1|1|2|causal_detected|1|
|8|machine|8691–8697|7|0|0|3|causal_detected|1|
|9|sensor|8850–8856|2|5|1|0|no_candidate_in_window|0|
|9|machine|8871–8877|7|0|0|3|causal_detected|1|

## 同layout core保存指標との比較

|stratum|candidate|machine|sensor|precision|clean|
|---|---|---|---|---|---|
|core|c0-diff-control|0/10|0/10|0/1|1|
|core|c1-phase-level|10/10|10/10|20/20|0|
|core|c2-phase-conditional|10/10|10/10|20/20|0|
|quality-stress|c0-diff-control|0/10|0/10|0/1|1|
|quality-stress|c1-phase-level|10/10|9/10|19/19|0|
|quality-stress|c2-phase-conditional|10/10|9/10|19/19|0|

旧layout7coreはmanifest/config保存指標だけ比較・再compute0。同seed/layoutの別stratumでinput品質等は異なり、独立新seedや欠測だけの反実仮想全差証明ではない。C1/C2の一部集計一致は全score/episode一致や候補採択の証明へしない。
全候補の全20対象窓の利用可・不能・最大streakと、原選択episodeのtarget対応を上表と保存ledgerから確認した。未検出は原reasonとdelaynullを保持し、閾値・GT・matching変更で補わない。入力対応・保存・状態分類の実経路不具合は観測なし。全用途不適合や包括的実装認証へしない。

対象窓の原分類集約 {"c0-diff-control": {"machine": [{"available": 7, "unavailable": 0, "phase_unavailable": 0, "max_streak": 1, "window_count": 10}], "sensor": [{"available": 6, "unavailable": 1, "phase_unavailable": 1, "max_streak": 1, "window_count": 9}, {"available": 2, "unavailable": 5, "phase_unavailable": 1, "max_streak": 0, "window_count": 1}]}, "c1-phase-level": {"machine": [{"available": 7, "unavailable": 0, "phase_unavailable": 0, "max_streak": 3, "window_count": 10}], "sensor": [{"available": 6, "unavailable": 1, "phase_unavailable": 1, "max_streak": 2, "window_count": 9}, {"available": 2, "unavailable": 5, "phase_unavailable": 1, "max_streak": 0, "window_count": 1}]}, "c2-phase-conditional": {"machine": [{"available": 7, "unavailable": 0, "phase_unavailable": 0, "max_streak": 3, "window_count": 10}], "sensor": [{"available": 6, "unavailable": 1, "phase_unavailable": 1, "max_streak": 2, "window_count": 9}, {"available": 2, "unavailable": 5, "phase_unavailable": 1, "max_streak": 0, "window_count": 1}]}}。sensor先頭のphase不能を全未検出の説明へ広げず、全対象score/streakと原episode supportを併せて保存。
## 証拠・次工程・正式状態

- 新 representative-seed2-layout7-quality-three-candidates-20261013-records/analysis/save/finalを優先。DATA2 {"D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout7-quality-c0-c1-20261013": {"bytes": 41898367, "files": 22, "manifest_pin": {"bytes": 2592, "sha256": "7fff19beab6671c78580c5904234011056042366ea4ed8f28ba9b48b7f190edf"}}, "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout7-quality-c2-20261013": {"bytes": 38238811, "files": 19, "manifest_pin": {"bytes": 2255, "sha256": "a16287db20e13923635433680336d3e41406561bb265402a46a6734aeacdc1e7"}}}。原profiles/scores/events/incidents/episodes/metricsを保存、全20ledger/対象窓/480不能を-analysisに保存。
- 旧117cellモデル再compute0、第1seed72＋第2seed48＝120boardcells/使用seed2、120独立datasetではない。layout0–7全6cell比較完成。bootstrap/統計CI/勝者採択0。
- 旧536root/472helpers25failed447passedmissingexecution1と全失敗・審査拒否・原誤記を保持。今回新helperfailure0/閉鎖外部固定root追記0/PID単独/native回収claim0。
- report/handoff/index3docs一回[skip ci] commit/push、prepare_result_index実使用。人の具体的通知後の同送信先同種合成dev報告・ユーザー名入りPC内pathの継続送信承認に従う。
- 次同seed/layout8 core、groups [["c0-diff-control", "c1-phase-level"], ["c2-phase-conditional"]] / IDs ["dev-seed7466813550306735603-layout8-core-c0-c1-20261013", "dev-seed7466813550306735603-layout8-core-c2-20261013"]。chunk020 manifest/identity/input10metadataのみ選択、次本文未読/model0。
- EvidenceStore全writepreflight/自動分割/失敗閉鎖reserveを維持。実行900秒/2GiB/output1GiB/single32MiB/files32、Git30秒/16entry/512KiB/stdout1MiB/stderr128KiBとnativeprotocol caps不変。checkpoint≠blocking中断/fullruntime/allwriter/globalmemory容量認証。
- ACTIVE/automation詳細転記0、新testCIagent0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件最終受入未完了/create_native早期拒否/全7役reader禁止/元capsunknown owner保持。Sol容量または人停止は保全後PAUSED。


## cycle09 sensorの原未検出窓

spike[8850,8853)、matching window 8850–8856。先頭phase不能→current品質不能3行→previous品質不能1行→最後2行は閾値未満/streak0。2利用可5不能（phase1含む）/maxstreak0、candidate0/no_candidate_in_window/causalfalse/matchednull/delaynull。原event/incident/全候補の対象7行をcycle09-sensor-missへ保存。
|sample|C0 score|C1 score|C2 score|reason|
|---|---|---|---|---|
|8850|None|None|None|mode_recipe_or_phase|
|8851|None|None|None|current_target_quality|
|8852|None|None|None|current_target_quality|
|8853|None|None|None|current_target_quality|
|8854|None|None|None|previous_target_quality_or_nonfinite|
|8855|2.192556965261168|0.9896192777500126|0.9785011710592963|None|
|8856|1.6315128155141683|1.2067358341740928|1.3005568622462567|None|

C0C1 available13880/unavailable520（phase480/current30/previous10）、C2 available13760/unavailable640（追加peer120）。温度品質不能40samples→current/speed/vibration各40行peer不能、phase品質重複0/phasepeer重複0。core比不能増40/40/160。非排他的tagを独立行として加算しない。原全関連120行と温度40行をpeer-quality-propagationへ保存。
