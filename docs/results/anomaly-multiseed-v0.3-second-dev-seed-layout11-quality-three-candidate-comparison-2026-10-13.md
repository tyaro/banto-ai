# 第2dev seed・layout11 quality-stressの3候補とcore比較（2026-10-13）

保存済み同一合成dev quality-stress入力でC0+C1、次にC2を順次fresh compute。人の3候補集約許可に従い、既存CLI2候補上限を維持して解析・文書・Gitを1単位にまとめた。処理成功を性能保証・勝者採択・正式受入へしない。

## 入力と実行

- dataset anomaly-v03-dev-seed-7466813550306735603-layout-11-quality-stress / seed7466813550306735603/layout11/quality-stress。元生成候補C0と実評価候補を別fieldに保存。同seedの追加layout、新独立seedではない。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\023\attempt-0001\result\payload\manifest.json / {"bytes": 75715, "sha256": "c5802ccc7f4db87b9dd3b92e5f976aa0af59a773dda8b8b6d9e6e30eca6854c0"}。3候補input10全pin一致→各CLI新snapshot/fresh calibration/fit。元payload書込み・新dataset生成・replay0。
- checkout 359e3c6a552e2313f7e352b764ac574fe34a5498 / 計算661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/candidatecompiled不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}。
- C0 threshold4/C1C2 threshold6/operator>/persistence2/GT/matching不変。全原thresholdflag照合。宣言pinはfull loaded runtime/native認証ではない。
- 原manifest/result pins [{"candidate": "c0-diff-control", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout11-quality-c0-c1-20261013\\manifest.json", "manifest_pin": {"bytes": 11072, "sha256": "e5171225a781d61f89303b171775f05f13ec49499912d9feda33c49b93b1bf7b"}, "result_pin": {"bytes": 14337041, "sha256": "0a1544ea731bcb46d5974590ad1ddb7f9b50e203ffe2ff6fca0296bce713d48f"}}, {"candidate": "c1-phase-level", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout11-quality-c0-c1-20261013\\manifest.json", "manifest_pin": {"bytes": 11072, "sha256": "e5171225a781d61f89303b171775f05f13ec49499912d9feda33c49b93b1bf7b"}, "result_pin": {"bytes": 14511153, "sha256": "9dc38bac891883d1a39005e87fe0e8e821334a79918cfba53bcc5fc6e5f724f6"}}, {"candidate": "c2-phase-conditional", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout11-quality-c2-20261013\\manifest.json", "manifest_pin": {"bytes": 8082, "sha256": "4fa80d023006dd4b2efe856aae0a08d1e2b02836ce4c10c851b5101fd6a3adf2"}, "result_pin": {"bytes": 25193227, "sha256": "97d7e7ac1a8ed1f7d5d7eaffefb6ce909c8a46d2e9cce448b706729eeeff907f"}}]。

|group|run|elapsed秒|sampled private peak B|
|---|---|---|---|
|c0-diff-control,c1-phase-level|dev-seed7466813550306735603-layout11-quality-c0-c1-20261013|32.206504899892025|151273472|
|c2-phase-conditional|dev-seed7466813550306735603-layout11-quality-c2-20261013|26.127026900066994|210714624|

CLI exit0/complete/成功cell2と1、原結果保存後だけsuccess計上。実CLI時間合計 58.33353179995902秒。単候補速度比較の再実行0、速度向上倍率は推定しない。

## 同一入力の原結果

|候補|machine|sensor|precision|clean / unmatched|source / equipment|available / unavailable|delay count / mean / median|
|---|---|---|---|---|---|---|
|c0-diff-control|0/10|2/10|2/2|0 / 0|2 / 2|13880 / 520|2 / 2.5 / 2.5|
|c1-phase-level|10/10|9/10|19/19|0 / 0|29 / 19|13880 / 520|19 / 1.4736842105263157 / 1.0|
|c2-phase-conditional|10/10|9/10|19/19|0 / 0|40 / 19|13760 / 640|19 / 1.4736842105263157 / 1.0|

全14400scoresの利用可・不能数と排他的primary reasonは下記原結果の集計を参照。不能全score/residualnull・thresholdfalse。18000input-mask対応/nonok30。48calibrated/calibration各290、fit sample countsとC2stateは以下の原値。全未検出delaynull補完0。clean_rate/burdenは原単位の指標で単純確率へしない。

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
|9|sensor|8970–8976|2|5|1|0|no_candidate_in_window|0|
|9|machine|8991–8997|7|0|0|1|no_candidate_in_window|0|

### c1-phase-level

profiles {"calibration_counts": {"290": 48}, "fit_counts": {"600": 48}, "statuses": {"calibrated": 48}} / C2state 0 / incident reasons {"causal_detected": 19, "no_candidate_in_window": 1}。
delay原 {"conditioned_on": "causal-detected-only", "count": 19, "max": 2.0, "mean": 1.4736842105263157, "median": 1.0, "min": 1.0, "undetected_fill": "forbidden", "unit": "seconds"} / class別 {"machine": {"1.0": 10}, "sensor": {"2.0": 9}}。未検出 1 件は全delaynull。
source内訳 {"conveyor-01.conveyor_speed": 10, "conveyor-01.motor_temperature": 9, "conveyor-01.vibration_feature": 10}。原source support2score、equipment membership、全未検出窓と選択failed candidateを-save/target-episode-supportへ保存。cleanと全未対応equipmentを別々に保持。
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
|9|sensor|8970–8976|2|5|1|0|no_candidate_in_window|0|
|9|machine|8991–8997|7|0|0|3|causal_detected|1|

### c2-phase-conditional

profiles {"calibration_counts": {"290": 48}, "fit_counts": {"600": 48}, "statuses": {"calibrated": 48}} / C2state 48 / incident reasons {"causal_detected": 19, "no_candidate_in_window": 1}。
delay原 {"conditioned_on": "causal-detected-only", "count": 19, "max": 2.0, "mean": 1.4736842105263157, "median": 1.0, "min": 1.0, "undetected_fill": "forbidden", "unit": "seconds"} / class別 {"machine": {"1.0": 10}, "sensor": {"2.0": 9}}。未検出 1 件は全delaynull。
source内訳 {"conveyor-01.conveyor_speed": 10, "conveyor-01.motor_temperature": 11, "conveyor-01.vibration_feature": 19}。原source support2score、equipment membership、全未検出窓と選択failed candidateを-save/target-episode-supportへ保存。cleanと全未対応equipmentを別々に保持。
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
|9|sensor|8970–8976|2|5|1|0|no_candidate_in_window|0|
|9|machine|8991–8997|7|0|0|3|causal_detected|1|

## 同layout core保存指標との比較

|stratum|candidate|machine|sensor|precision|clean|
|---|---|---|---|---|---|
|core|c0-diff-control|0/10|2/10|2/2|0|
|core|c1-phase-level|10/10|10/10|20/20|0|
|core|c2-phase-conditional|10/10|10/10|20/20|0|
|quality-stress|c0-diff-control|0/10|2/10|2/2|0|
|quality-stress|c1-phase-level|10/10|9/10|19/19|0|
|quality-stress|c2-phase-conditional|10/10|9/10|19/19|0|

C0はcoreとqualityでsensor2/10、delay2秒・3秒、clean0。qualityの原matched event/source/equipment/2support scoreをc0-detected-sensor-evidenceへ保存。固定matchingのcausal_detectedは反実仮想の因果証明ではない。全sensor窓のstreakを一律1とはしない。

旧layout11coreはmanifest/config保存指標だけ比較・再compute0。同seed/layoutの別stratumでinput品質等は異なり、独立新seedや欠測だけの反実仮想全差証明ではない。C1/C2の一部集計一致は全score/episode一致や候補採択の証明へしない。
全候補の全20対象窓の利用可・不能・最大streakと、原選択episodeのtarget対応を上表と保存ledgerから確認した。未検出は原reasonとdelaynullを保持し、閾値・GT・matching変更で補わない。入力対応・保存・状態分類の実経路不具合は観測なし。全用途不適合や包括的実装認証へしない。

対象窓の原分類集約 {"c0-diff-control": {"machine": [{"available": 7, "unavailable": 0, "phase_unavailable": 0, "max_streak": 1, "window_count": 10}], "sensor": [{"available": 6, "unavailable": 1, "phase_unavailable": 1, "max_streak": 1, "window_count": 7}, {"available": 6, "unavailable": 1, "phase_unavailable": 1, "max_streak": 3, "window_count": 1}, {"available": 6, "unavailable": 1, "phase_unavailable": 1, "max_streak": 2, "window_count": 1}, {"available": 2, "unavailable": 5, "phase_unavailable": 1, "max_streak": 0, "window_count": 1}]}, "c1-phase-level": {"machine": [{"available": 7, "unavailable": 0, "phase_unavailable": 0, "max_streak": 3, "window_count": 10}], "sensor": [{"available": 6, "unavailable": 1, "phase_unavailable": 1, "max_streak": 2, "window_count": 9}, {"available": 2, "unavailable": 5, "phase_unavailable": 1, "max_streak": 0, "window_count": 1}]}, "c2-phase-conditional": {"machine": [{"available": 7, "unavailable": 0, "phase_unavailable": 0, "max_streak": 3, "window_count": 10}], "sensor": [{"available": 6, "unavailable": 1, "phase_unavailable": 1, "max_streak": 2, "window_count": 9}, {"available": 2, "unavailable": 5, "phase_unavailable": 1, "max_streak": 0, "window_count": 1}]}}。全対象score/streakと原episode supportを併せて保存し、phase不能や欠測温度1窓だけで全未検出を説明しない。
## 証拠・次工程・正式状態

- 新 representative-seed2-layout11-quality-three-candidates-20261013-records/analysis/save/finalを優先。DATA2 {"D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout11-quality-c0-c1-20261013": {"bytes": 41902955, "files": 22, "manifest_pin": {"bytes": 2593, "sha256": "fe3e4d9cb2ae62546dfe648b4885eb0196bb4cadf1becd76270bfe98a4b80439"}}, "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout11-quality-c2-20261013": {"bytes": 38241526, "files": 19, "manifest_pin": {"bytes": 2256, "sha256": "6a6899c7dfae8634952e82c311754043a369dbd158e08739c9a7cd2faddc107d"}}}。原profiles/scores/events/incidents/episodes/metricsを保存、全20ledger/対象窓/480不能を-analysisに保存。
- 旧141cellモデル再compute0、第1seed72＋第2seed72＝144boardcells/使用seed2、144独立datasetではない。layout0–11全6cell比較完成。bootstrap/統計CI/勝者採択0。
- 旧586root/506helpers27failed479passedmissingexecution1と全失敗・審査拒否・原誤記を保持。今回新helperfailure0/閉鎖外部固定root追記0/PID単独/native回収claim0。
- report/handoff/index3docs一回[skip ci] commit/push、prepare_result_index実使用。人の具体的通知後の同送信先同種合成dev報告・ユーザー名入りPC内pathの継続送信承認に従う。
- 次保存dev seed/layout0 core、groups [["c0-diff-control", "c1-phase-level"], ["c2-phase-conditional"]] / IDs ["dev-seed7126204254162853479-layout0-core-c0-c1-20261013", "dev-seed7126204254162853479-layout0-core-c2-20261013"]。chunk024 manifest/identity/input10metadataのみ選択、次本文未読/model0。
- EvidenceStore全writepreflight/自動分割/失敗閉鎖reserveを維持。実行900秒/2GiB/output1GiB/single32MiB/files32、Git30秒/16entry/512KiB/stdout1MiB/stderr128KiBとnativeprotocol caps不変。checkpoint≠blocking中断/fullruntime/allwriter/globalmemory容量認証。
- ACTIVE/automation詳細転記0、新testCIagent0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件最終受入未完了/create_native早期拒否/全7役reader禁止/元capsunknown owner保持。Sol容量または人停止は保全後PAUSED。


## cycle09 sensorの原未検出窓

spike[8970,8973)、matching window 8970–8976。先頭phase不能streak0→current品質不能3行→previous品質不能1行→最後2行は閾値未満/streak0。2利用可5不能/phase1/maxstreak0、candidate0/no_candidate_in_window/causalfalse/matchednull/delaynull。原event/incident/全候補の対象7行をcycle09-sensor-missへ保存。
|sample|C0 score|C1 score|C2 score|reason|
|---|---|---|---|---|
|8970|None|None|None|mode_recipe_or_phase|
|8971|None|None|None|current_target_quality|
|8972|None|None|None|current_target_quality|
|8973|None|None|None|current_target_quality|
|8974|None|None|None|previous_target_quality_or_nonfinite|
|8975|2.3028504912149037|1.9839301469823614|1.7706836263014123|None|
|8976|1.5216498764462016|1.3672438673981244|1.4930912405305032|None|

C0C1 available13880/unavailable520（phase480/current30/previous10）、C2 available13760/unavailable640（追加peer120）。温度品質不能40samples→current/speed/vibration各40行peer不能、phase品質重複0/phasepeer重複0。core比不能増40/40/160。非排他的tagを独立行として加算しない。原全関連120行と温度40行をpeer-quality-propagationへ保存。
