# 第2dev seed・layout5 coreのC0/C1/C2比較（2026-10-13）

保存済み同一合成dev core入力でC0+C1、次にC2を順次fresh compute。人の3候補集約許可に従い、既存CLI2候補上限を維持して解析・文書・Gitを1単位にまとめた。処理成功を性能保証・勝者採択・正式受入へしない。

## 入力と実行

- dataset anomaly-v03-dev-seed-7466813550306735603-layout-05-core / seed7466813550306735603/layout5/core。元生成候補C0と実評価候補を別fieldに保存。同seedの追加layout、新独立seedではない。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\017\attempt-0001\result\payload\manifest.json / {"bytes": 75699, "sha256": "16c4319322e2e6ecc5228c513240d1a935cb1047e2bf15c78c3f83741e501746"}。3候補input10全pin一致→各CLI新snapshot/fresh calibration/fit。元payload書込み・新dataset生成・replay0。
- checkout 301a70fb5ee9b9bcf140c4c51e28b01a3089238d / 計算661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/candidatecompiled不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}。
- C0 threshold4/C1C2 threshold6/operator>/persistence2/GT/matching不変。全原thresholdflag照合。宣言pinはfull loaded runtime/native認証ではない。
- 原manifest/result pins [{"candidate": "c0-diff-control", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout5-core-c0-c1-20261013\\manifest.json", "manifest_pin": {"bytes": 11055, "sha256": "14c2dc1f6ae95395d70e63c623bab1a62ddbf348f77d910624986adb35918d88"}, "result_pin": {"bytes": 13896312, "sha256": "d035f8d2987140ee2ebebb60753fbb469c9ea23610e04c76837930e473d67ca1"}}, {"candidate": "c1-phase-level", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout5-core-c0-c1-20261013\\manifest.json", "manifest_pin": {"bytes": 11055, "sha256": "14c2dc1f6ae95395d70e63c623bab1a62ddbf348f77d910624986adb35918d88"}, "result_pin": {"bytes": 14072191, "sha256": "e6823d0d1ec23aea4df56e96e92a78bc2d19b5b0f9969a907fef0b5044585db2"}}, {"candidate": "c2-phase-conditional", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout5-core-c2-20261013\\manifest.json", "manifest_pin": {"bytes": 8032, "sha256": "3f0af4eaa041d4e3b8c4e19532412bef7ff91cc8fd2c20c3db79516356205c7d"}, "result_pin": {"bytes": 24750002, "sha256": "cccb32dcd1369e4326547df377c48b4e6fd64f8683582d3ac255b757f34fc075"}}]。

|group|run|elapsed秒|sampled private peak B|
|---|---|---|---|
|c0-diff-control,c1-phase-level|dev-seed7466813550306735603-layout5-core-c0-c1-20261013|32.144750499981456|151216128|
|c2-phase-conditional|dev-seed7466813550306735603-layout5-core-c2-20261013|26.04621479997877|211001344|

CLI exit0/complete/成功cell2と1、原結果保存後だけsuccess計上。実CLI時間合計 58.190965299960226秒。単候補速度比較の再実行0、速度向上倍率は推定しない。

## 同一入力の原結果

|候補|machine|sensor|precision|clean / unmatched|source / equipment|available / unavailable|delay count / mean / median|
|---|---|---|---|---|---|---|
|c0-diff-control|0/10|0/10|0/1|1 / 1|1 / 1|13920 / 480|0 / None / None|
|c1-phase-level|10/10|10/10|20/20|0 / 0|30 / 20|13920 / 480|20 / 1.0 / 1.0|
|c2-phase-conditional|10/10|10/10|20/20|0 / 0|40 / 20|13920 / 480|20 / 1.0 / 1.0|

全14400scores/利用可13920/不能480（mode_recipe_or_phase）。不能全score/residualnull・thresholdfalse。18000input-mask対応/nonok0。48calibrated/calibration各290、fit sample countsとC2stateは以下の原値。全未検出delaynull補完0。clean_rate/burdenは原単位の指標で単純確率へしない。

### c0-diff-control

profiles {"calibration_counts": {"290": 48}, "fit_counts": {"0": 48}, "statuses": {"calibrated": 48}} / C2state 0 / incident reasons {"no_candidate_in_window": 20}。
delay原 {"conditioned_on": "causal-detected-only", "count": 0, "max": null, "mean": null, "median": null, "min": null, "undetected_fill": "forbidden", "unit": "seconds"} / class別 {"machine": {}, "sensor": {}}。未検出 20 件は全delaynull。
source内訳 {"conveyor-01.motor_temperature": 1}。原source support2score、equipment membership、全未検出窓と選択failed candidateを-save/target-episode-supportへ保存。cleanと全未対応equipmentを別々に保持。
clean_rate {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 3365, "null_replicates": 0, "numerator": 1, "value": 8.558692421991084} / effective seconds 3255 / effective_rate 8.847926267281107 / burden {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 20, "null_replicates": 0, "numerator": 1, "value": 5.0}。
対象window分類は以下の全20原値（available/unavailable/phase/maxstreak）を参照。

|cycle|class|start–end|available|unavailable|phase|maximum streak|reason|candidate count|
|---|---|---|---|---|---|---|---|---|
|0|machine|7357–7363|7|0|0|1|no_candidate_in_window|0|
|0|sensor|7364–7370|7|0|0|1|no_candidate_in_window|0|
|1|machine|7537–7543|7|0|0|1|no_candidate_in_window|0|
|1|sensor|7544–7550|7|0|0|1|no_candidate_in_window|0|
|2|machine|7717–7723|7|0|0|1|no_candidate_in_window|0|
|2|sensor|7724–7730|7|0|0|1|no_candidate_in_window|0|
|3|machine|7897–7903|7|0|0|1|no_candidate_in_window|0|
|3|sensor|7904–7910|7|0|0|1|no_candidate_in_window|0|
|4|machine|8077–8083|7|0|0|1|no_candidate_in_window|0|
|4|sensor|8084–8090|7|0|0|1|no_candidate_in_window|0|
|5|machine|8257–8263|7|0|0|1|no_candidate_in_window|0|
|5|sensor|8264–8270|7|0|0|1|no_candidate_in_window|0|
|6|machine|8437–8443|7|0|0|1|no_candidate_in_window|0|
|6|sensor|8444–8450|7|0|0|1|no_candidate_in_window|0|
|7|machine|8617–8623|7|0|0|1|no_candidate_in_window|0|
|7|sensor|8624–8630|7|0|0|1|no_candidate_in_window|0|
|8|machine|8797–8803|7|0|0|1|no_candidate_in_window|0|
|8|sensor|8804–8810|7|0|0|1|no_candidate_in_window|0|
|9|machine|8977–8983|7|0|0|1|no_candidate_in_window|0|
|9|sensor|8984–8990|7|0|0|1|no_candidate_in_window|0|

### c1-phase-level

profiles {"calibration_counts": {"290": 48}, "fit_counts": {"600": 48}, "statuses": {"calibrated": 48}} / C2state 0 / incident reasons {"causal_detected": 20}。
delay原 {"conditioned_on": "causal-detected-only", "count": 20, "max": 1.0, "mean": 1.0, "median": 1.0, "min": 1.0, "undetected_fill": "forbidden", "unit": "seconds"} / class別 {"machine": {"1.0": 10}, "sensor": {"1.0": 10}}。未検出 0 件は全delaynull。
source内訳 {"motor-01.motor_current": 10, "motor-01.motor_temperature": 10, "motor-01.vibration_feature": 10}。原source support2score、equipment membership、全未検出窓と選択failed candidateを-save/target-episode-supportへ保存。cleanと全未対応equipmentを別々に保持。
clean_rate {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 3365, "null_replicates": 0, "numerator": 0, "value": 0.0} / effective seconds 3255 / effective_rate 0.0 / burden {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 20, "null_replicates": 0, "numerator": 0, "value": 0.0}。
対象window分類は以下の全20原値（available/unavailable/phase/maxstreak）を参照。

|cycle|class|start–end|available|unavailable|phase|maximum streak|reason|candidate count|
|---|---|---|---|---|---|---|---|---|
|0|machine|7357–7363|7|0|0|3|causal_detected|1|
|0|sensor|7364–7370|7|0|0|3|causal_detected|1|
|1|machine|7537–7543|7|0|0|3|causal_detected|1|
|1|sensor|7544–7550|7|0|0|3|causal_detected|1|
|2|machine|7717–7723|7|0|0|3|causal_detected|1|
|2|sensor|7724–7730|7|0|0|3|causal_detected|1|
|3|machine|7897–7903|7|0|0|3|causal_detected|1|
|3|sensor|7904–7910|7|0|0|3|causal_detected|1|
|4|machine|8077–8083|7|0|0|3|causal_detected|1|
|4|sensor|8084–8090|7|0|0|3|causal_detected|1|
|5|machine|8257–8263|7|0|0|3|causal_detected|1|
|5|sensor|8264–8270|7|0|0|3|causal_detected|1|
|6|machine|8437–8443|7|0|0|3|causal_detected|1|
|6|sensor|8444–8450|7|0|0|3|causal_detected|1|
|7|machine|8617–8623|7|0|0|3|causal_detected|1|
|7|sensor|8624–8630|7|0|0|3|causal_detected|1|
|8|machine|8797–8803|7|0|0|3|causal_detected|1|
|8|sensor|8804–8810|7|0|0|3|causal_detected|1|
|9|machine|8977–8983|7|0|0|3|causal_detected|1|
|9|sensor|8984–8990|7|0|0|3|causal_detected|1|

### c2-phase-conditional

profiles {"calibration_counts": {"290": 48}, "fit_counts": {"600": 48}, "statuses": {"calibrated": 48}} / C2state 48 / incident reasons {"causal_detected": 20}。
delay原 {"conditioned_on": "causal-detected-only", "count": 20, "max": 1.0, "mean": 1.0, "median": 1.0, "min": 1.0, "undetected_fill": "forbidden", "unit": "seconds"} / class別 {"machine": {"1.0": 10}, "sensor": {"1.0": 10}}。未検出 0 件は全delaynull。
source内訳 {"motor-01.motor_current": 20, "motor-01.motor_temperature": 10, "motor-01.vibration_feature": 10}。原source support2score、equipment membership、全未検出窓と選択failed candidateを-save/target-episode-supportへ保存。cleanと全未対応equipmentを別々に保持。
clean_rate {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 3365, "null_replicates": 0, "numerator": 0, "value": 0.0} / effective seconds 3255 / effective_rate 0.0 / burden {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 20, "null_replicates": 0, "numerator": 0, "value": 0.0}。
対象window分類は以下の全20原値（available/unavailable/phase/maxstreak）を参照。

|cycle|class|start–end|available|unavailable|phase|maximum streak|reason|candidate count|
|---|---|---|---|---|---|---|---|---|
|0|machine|7357–7363|7|0|0|3|causal_detected|1|
|0|sensor|7364–7370|7|0|0|3|causal_detected|1|
|1|machine|7537–7543|7|0|0|3|causal_detected|1|
|1|sensor|7544–7550|7|0|0|3|causal_detected|1|
|2|machine|7717–7723|7|0|0|3|causal_detected|1|
|2|sensor|7724–7730|7|0|0|3|causal_detected|1|
|3|machine|7897–7903|7|0|0|3|causal_detected|1|
|3|sensor|7904–7910|7|0|0|3|causal_detected|1|
|4|machine|8077–8083|7|0|0|3|causal_detected|1|
|4|sensor|8084–8090|7|0|0|3|causal_detected|1|
|5|machine|8257–8263|7|0|0|3|causal_detected|1|
|5|sensor|8264–8270|7|0|0|3|causal_detected|1|
|6|machine|8437–8443|7|0|0|3|causal_detected|1|
|6|sensor|8444–8450|7|0|0|3|causal_detected|1|
|7|machine|8617–8623|7|0|0|3|causal_detected|1|
|7|sensor|8624–8630|7|0|0|3|causal_detected|1|
|8|machine|8797–8803|7|0|0|3|causal_detected|1|
|8|sensor|8804–8810|7|0|0|3|causal_detected|1|
|9|machine|8977–8983|7|0|0|3|causal_detected|1|
|9|sensor|8984–8990|7|0|0|3|causal_detected|1|

## 前layout core保存指標との比較

|layout|candidate|machine|sensor|precision|clean|
|---|---|---|---|---|---|
|4|c0-diff-control|0/10|0/10|0/2|1|
|4|c1-phase-level|10/10|10/10|20/20|0|
|4|c2-phase-conditional|10/10|10/10|20/20|0|
|5|c0-diff-control|0/10|0/10|0/1|1|
|5|c1-phase-level|10/10|10/10|20/20|0|
|5|c2-phase-conditional|10/10|10/10|20/20|0|

旧layout4はmanifest/config保存指標だけ比較・再compute0。同seed別layoutで観測inputは異なり、独立新seedや1要因だけの反実仮想差証明ではない。C1/C2の一部集計一致は全score/episode一致や候補採択の証明へしない。
全候補の全20対象窓は7行すべて利用可/phase不能0。C0は全窓maxstreak1・candidate0/no_candidate_in_windowでpersistence2不成立。対象窓の不能行だけでは今回全20missを説明できない。C1/C2は全窓maxstreak3で全20delay1秒。C0の唯一cleanはconveyor-01.motor_temperature onset7712で、原support7711/7712を保存。検出を閾値・GT・matching変更で補わない。入力対応・保存・状態分類の実経路不具合は観測なし。全用途不適合や包括的実装認証へしない。

## 証拠・次工程・正式状態

- 新 representative-seed2-layout5-core-three-candidates-20261013-records/analysis/save/finalを優先。DATA2 {"D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout5-core-c0-c1-20261013": {"bytes": 41016105, "files": 22, "manifest_pin": {"bytes": 2582, "sha256": "cea050c5acac9301a455b48d6b918da45d447c7d4838363fb42206591e0e4ace"}}, "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout5-core-c2-20261013": {"bytes": 37791077, "files": 19, "manifest_pin": {"bytes": 2245, "sha256": "1216499599afab9f89dca7c81f0fdbb8c2af4ec847596a93741ea16260a4cf70"}}}。原profiles/scores/events/incidents/episodes/metricsを保存、全20ledger/対象窓/480不能を-analysisに保存。
- 旧102cellモデル再compute0、第1seed72＋第2seed33＝105boardcells/使用seed2、105独立datasetではない。layout0–4全6cell・layout5core3cell完成。bootstrap/統計CI/勝者採択0。
- 旧504root/451helpers24failed427passedmissingexecution1と全失敗・審査拒否・原誤記を保持。今回新helperfailure0/閉鎖外部固定root追記0/PID単独/native回収claim0。
- report/handoff/index3docs一回[skip ci] commit/push、prepare_result_index実使用。人の具体的通知後の同送信先同種合成dev報告・ユーザー名入りPC内pathの継続送信承認に従う。
- 次同seed/layout5 quality-stress、groups [["c0-diff-control", "c1-phase-level"], ["c2-phase-conditional"]] / IDs ["dev-seed7466813550306735603-layout5-quality-c0-c1-20261013", "dev-seed7466813550306735603-layout5-quality-c2-20261013"]。同chunk017 manifest/identity/input10metadataのみ選択、次本文未読/model0。
- EvidenceStore全writepreflight/自動分割/失敗閉鎖reserveを維持。実行900秒/2GiB/output1GiB/single32MiB/files32、Git30秒/16entry/512KiB/stdout1MiB/stderr128KiBとnativeprotocol caps不変。checkpoint≠blocking中断/fullruntime/allwriter/globalmemory容量認証。
- ACTIVE/automation詳細転記0、新testCIagent0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件最終受入未完了/create_native早期拒否/全7役reader禁止/元capsunknown owner保持。Sol容量または人停止は保全後PAUSED。
