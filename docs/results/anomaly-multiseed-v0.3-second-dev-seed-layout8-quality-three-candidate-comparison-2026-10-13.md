# 第2dev seed・layout8 quality-stressの3候補とcore比較（2026-10-13）

保存済み同一合成dev quality-stress入力でC0+C1、次にC2を順次fresh compute。人の3候補集約許可に従い、既存CLI2候補上限を維持して解析・文書・Gitを1単位にまとめた。処理成功を性能保証・勝者採択・正式受入へしない。

## 入力と実行

- dataset anomaly-v03-dev-seed-7466813550306735603-layout-08-quality-stress / seed7466813550306735603/layout8/quality-stress。元生成候補C0と実評価候補を別fieldに保存。同seedの追加layout、新独立seedではない。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\020\attempt-0001\result\payload\manifest.json / {"bytes": 75700, "sha256": "2dd0b78a5de7cda8675220d5f364c195a582ce87559fea40b7cddd7c0be2aa5e"}。3候補input10全pin一致→各CLI新snapshot/fresh calibration/fit。元payload書込み・新dataset生成・replay0。
- checkout bfcc23bc97d453e48359eb5eb0a280efd45ec969 / 計算661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/candidatecompiled不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}。
- C0 threshold4/C1C2 threshold6/operator>/persistence2/GT/matching不変。全原thresholdflag照合。宣言pinはfull loaded runtime/native認証ではない。
- 原manifest/result pins [{"candidate": "c0-diff-control", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout8-quality-c0-c1-20261013\\manifest.json", "manifest_pin": {"bytes": 11102, "sha256": "bfec76befa298c4ab549164785cfdbf7ccab1b2421916b245c678640ca976e84"}, "result_pin": {"bytes": 14333533, "sha256": "1800166d412db5015c3d06e1cd7a930b9214fe8abec7027c6af59af588a0a49c"}}, {"candidate": "c1-phase-level", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout8-quality-c0-c1-20261013\\manifest.json", "manifest_pin": {"bytes": 11102, "sha256": "bfec76befa298c4ab549164785cfdbf7ccab1b2421916b245c678640ca976e84"}, "result_pin": {"bytes": 14509473, "sha256": "939574a029e2133522d116ec146cf08d72c187f5153c559d2f2c3a84789b4edb"}}, {"candidate": "c2-phase-conditional", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout8-quality-c2-20261013\\manifest.json", "manifest_pin": {"bytes": 8080, "sha256": "727c46c92b2095c60ec41ea4e9ee3daec4965fc51dcab5061a03529c98cf7d4a"}, "result_pin": {"bytes": 25189717, "sha256": "ea2e59a28d3a65d25294a79d4ea800e1fe984d3ba7bcb136411bd3e7b25648d4"}}]。

|group|run|elapsed秒|sampled private peak B|
|---|---|---|---|
|c0-diff-control,c1-phase-level|dev-seed7466813550306735603-layout8-quality-c0-c1-20261013|32.559355999925174|150016000|
|c2-phase-conditional|dev-seed7466813550306735603-layout8-quality-c2-20261013|28.489790700026788|213626880|

CLI exit0/complete/成功cell2と1、原結果保存後だけsuccess計上。実CLI時間合計 61.04914669995196秒。単候補速度比較の再実行0、速度向上倍率は推定しない。

## 同一入力の原結果

|候補|machine|sensor|precision|clean / unmatched|source / equipment|available / unavailable|delay count / mean / median|
|---|---|---|---|---|---|---|
|c0-diff-control|0/10|0/10|0/1|1 / 1|1 / 1|13880 / 520|0 / None / None|
|c1-phase-level|10/10|9/10|19/19|0 / 0|29 / 19|13880 / 520|19 / 1.5263157894736843 / 2.0|
|c2-phase-conditional|10/10|9/10|19/19|0 / 0|38 / 19|13760 / 640|19 / 1.5263157894736843 / 2.0|

全14400scoresの利用可・不能数と排他的primary reasonは下記原結果の集計を参照。不能全score/residualnull・thresholdfalse。18000input-mask対応/nonok30。48calibrated/calibration各290、fit sample countsとC2stateは以下の原値。全未検出delaynull補完0。clean_rate/burdenは原単位の指標で単純確率へしない。

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
|9|sensor|8887–8893|3|4|0|1|no_candidate_in_window|0|

### c1-phase-level

profiles {"calibration_counts": {"290": 48}, "fit_counts": {"600": 48}, "statuses": {"calibrated": 48}} / C2state 0 / incident reasons {"causal_detected": 19, "no_candidate_in_window": 1}。
delay原 {"conditioned_on": "causal-detected-only", "count": 19, "max": 2.0, "mean": 1.5263157894736843, "median": 2.0, "min": 1.0, "undetected_fill": "forbidden", "unit": "seconds"} / class別 {"machine": {"2.0": 10}, "sensor": {"1.0": 9}}。未検出 1 件は全delaynull。
source内訳 {"conveyor-01.conveyor_speed": 10, "conveyor-01.motor_temperature": 9, "conveyor-01.vibration_feature": 10}。原source support2score、equipment membership、全未検出窓と選択failed candidateを-save/target-episode-supportへ保存。cleanと全未対応equipmentを別々に保持。
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
|9|sensor|8887–8893|3|4|0|1|no_candidate_in_window|0|

### c2-phase-conditional

profiles {"calibration_counts": {"290": 48}, "fit_counts": {"600": 48}, "statuses": {"calibrated": 48}} / C2state 48 / incident reasons {"causal_detected": 19, "no_candidate_in_window": 1}。
delay原 {"conditioned_on": "causal-detected-only", "count": 19, "max": 2.0, "mean": 1.5263157894736843, "median": 2.0, "min": 1.0, "undetected_fill": "forbidden", "unit": "seconds"} / class別 {"machine": {"2.0": 10}, "sensor": {"1.0": 9}}。未検出 1 件は全delaynull。
source内訳 {"conveyor-01.conveyor_speed": 10, "conveyor-01.motor_current": 9, "conveyor-01.motor_temperature": 9, "conveyor-01.vibration_feature": 10}。原source support2score、equipment membership、全未検出窓と選択failed candidateを-save/target-episode-supportへ保存。cleanと全未対応equipmentを別々に保持。
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
|9|sensor|8887–8893|3|4|0|1|no_candidate_in_window|0|

## 同layout core保存指標との比較

|stratum|candidate|machine|sensor|precision|clean|
|---|---|---|---|---|---|
|core|c0-diff-control|0/10|0/10|0/1|1|
|core|c1-phase-level|10/10|10/10|20/20|0|
|core|c2-phase-conditional|10/10|10/10|20/20|0|
|quality-stress|c0-diff-control|0/10|0/10|0/1|1|
|quality-stress|c1-phase-level|10/10|9/10|19/19|0|
|quality-stress|c2-phase-conditional|10/10|9/10|19/19|0|

旧layout8coreはmanifest/config保存指標だけ比較・再compute0。同seed/layoutの別stratumでinput品質等は異なり、独立新seedや欠測だけの反実仮想全差証明ではない。C1/C2の一部集計一致は全score/episode一致や候補採択の証明へしない。
全候補の全20対象窓の利用可・不能・最大streakと、原選択episodeのtarget対応を上表と保存ledgerから確認した。未検出は原reasonとdelaynullを保持し、閾値・GT・matching変更で補わない。入力対応・保存・状態分類の実経路不具合は観測なし。全用途不適合や包括的実装認証へしない。

対象窓の原分類集約 {"c0-diff-control": {"machine": [{"available": 6, "unavailable": 1, "phase_unavailable": 1, "max_streak": 1, "window_count": 10}], "sensor": [{"available": 7, "unavailable": 0, "phase_unavailable": 0, "max_streak": 1, "window_count": 9}, {"available": 3, "unavailable": 4, "phase_unavailable": 0, "max_streak": 1, "window_count": 1}]}, "c1-phase-level": {"machine": [{"available": 6, "unavailable": 1, "phase_unavailable": 1, "max_streak": 2, "window_count": 10}], "sensor": [{"available": 7, "unavailable": 0, "phase_unavailable": 0, "max_streak": 3, "window_count": 9}, {"available": 3, "unavailable": 4, "phase_unavailable": 0, "max_streak": 1, "window_count": 1}]}, "c2-phase-conditional": {"machine": [{"available": 6, "unavailable": 1, "phase_unavailable": 1, "max_streak": 2, "window_count": 10}], "sensor": [{"available": 7, "unavailable": 0, "phase_unavailable": 0, "max_streak": 3, "window_count": 9}, {"available": 3, "unavailable": 4, "phase_unavailable": 0, "max_streak": 1, "window_count": 1}]}}。全対象score/streakと原episode supportを併せて保存し、phase不能や欠測温度1窓だけで全未検出を説明しない。
## 証拠・次工程・正式状態

- 新 representative-seed2-layout8-quality-three-candidates-20261013-records/analysis/save/finalを優先。DATA2 {"D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout8-quality-c0-c1-20261013": {"bytes": 41897346, "files": 22, "manifest_pin": {"bytes": 2592, "sha256": "7e387f3333565529ab97c4412c521e09aa9c31751cee42888aad3b4806e547b8"}}, "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout8-quality-c2-20261013": {"bytes": 38237531, "files": 19, "manifest_pin": {"bytes": 2255, "sha256": "690bc12e28d5365a1c4b9ebccda62d8cea60cfffa11febd7453936a74e26f9b2"}}}。原profiles/scores/events/incidents/episodes/metricsを保存、全20ledger/対象窓/480不能を-analysisに保存。
- 旧123cellモデル再compute0、第1seed72＋第2seed54＝126boardcells/使用seed2、126独立datasetではない。layout0–8全6cell比較完成。bootstrap/統計CI/勝者採択0。
- 旧548root/480helpers25failed455passedmissingexecution1と全失敗・審査拒否・原誤記を保持。今回新helperfailure0/閉鎖外部固定root追記0/PID単独/native回収claim0。
- report/handoff/index3docs一回[skip ci] commit/push、prepare_result_index実使用。人の具体的通知後の同送信先同種合成dev報告・ユーザー名入りPC内pathの継続送信承認に従う。
- 次同seed/layout9 core、groups [["c0-diff-control", "c1-phase-level"], ["c2-phase-conditional"]] / IDs ["dev-seed7466813550306735603-layout9-core-c0-c1-20261013", "dev-seed7466813550306735603-layout9-core-c2-20261013"]。chunk021 manifest/identity/input10metadataのみ選択、次本文未読/model0。
- EvidenceStore全writepreflight/自動分割/失敗閉鎖reserveを維持。実行900秒/2GiB/output1GiB/single32MiB/files32、Git30秒/16entry/512KiB/stdout1MiB/stderr128KiBとnativeprotocol caps不変。checkpoint≠blocking中断/fullruntime/allwriter/globalmemory容量認証。
- ACTIVE/automation詳細転記0、新testCIagent0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件最終受入未完了/create_native早期拒否/全7役reader禁止/元capsunknown owner保持。Sol容量または人停止は保全後PAUSED。


## cycle09 sensorの原未検出窓

spike[8887,8890)、matching window 8887–8893。先頭閾値超過streak1→current品質不能3行→previous品質不能1行→最後2行は閾値未満/streak0。3利用可4不能/phase0/maxstreak1、candidate0/no_candidate_in_window/causalfalse/matchednull/delaynull。原event/incident/全候補の対象7行をcycle09-sensor-missへ保存。
|sample|C0 score|C1 score|C2 score|reason|
|---|---|---|---|---|
|8887|234.0623890234814|132.38530339552426|132.98640730322097|None|
|8888|None|None|None|current_target_quality|
|8889|None|None|None|current_target_quality|
|8890|None|None|None|current_target_quality|
|8891|None|None|None|previous_target_quality_or_nonfinite|
|8892|0.8416603065512616|0.8387134009011655|0.9005689761832698|None|
|8893|0.5904700431009148|1.0466740238809462|1.1975825566107483|None|

C0C1 available13880/unavailable520（phase480/current30/previous10）、C2 available13760/unavailable640（追加peer120）。温度品質不能40samples→current/speed/vibration各40行peer不能、phase品質重複0/phasepeer重複0。core比不能増40/40/160。非排他的tagを独立行として加算しない。原全関連120行と温度40行をpeer-quality-propagationへ保存。
