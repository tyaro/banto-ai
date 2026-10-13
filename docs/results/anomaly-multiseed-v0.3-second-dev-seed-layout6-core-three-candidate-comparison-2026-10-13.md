# 第2dev seed・layout6 coreのC0/C1/C2比較（2026-10-13）

保存済み同一合成dev core入力でC0+C1、次にC2を順次fresh compute。人の3候補集約許可に従い、既存CLI2候補上限を維持して解析・文書・Gitを1単位にまとめた。処理成功を性能保証・勝者採択・正式受入へしない。

## 入力と実行

- dataset anomaly-v03-dev-seed-7466813550306735603-layout-06-core / seed7466813550306735603/layout6/core。元生成候補C0と実評価候補を別fieldに保存。同seedの追加layout、新独立seedではない。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\018\attempt-0001\result\payload\manifest.json / {"bytes": 75699, "sha256": "a8a883a6e85a16f1ae8f152ea3b730252802b186b86df448944d6ea4f3ad0b9f"}。3候補input10全pin一致→各CLI新snapshot/fresh calibration/fit。元payload書込み・新dataset生成・replay0。
- checkout d70cb71dcaefbe5c7c4d58fe26437661afa50df0 / 計算661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/candidatecompiled不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}。
- C0 threshold4/C1C2 threshold6/operator>/persistence2/GT/matching不変。全原thresholdflag照合。宣言pinはfull loaded runtime/native認証ではない。
- 原manifest/result pins [{"candidate": "c0-diff-control", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout6-core-c0-c1-20261013\\manifest.json", "manifest_pin": {"bytes": 11055, "sha256": "b1393ca51f2d6d50b636e5f36e90a577e11f2eadc508bd6a23af30c00987331c"}, "result_pin": {"bytes": 13896270, "sha256": "3b6a930746271532c17bf09af222d52f2b91b3dc157b26fe07350e7a8cc5f3d4"}}, {"candidate": "c1-phase-level", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout6-core-c0-c1-20261013\\manifest.json", "manifest_pin": {"bytes": 11055, "sha256": "b1393ca51f2d6d50b636e5f36e90a577e11f2eadc508bd6a23af30c00987331c"}, "result_pin": {"bytes": 14057074, "sha256": "eb3b1c0473bb16f0a73f598156f131967aaed0e42a93e817272e590dd8e7a46e"}}, {"candidate": "c2-phase-conditional", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout6-core-c2-20261013\\manifest.json", "manifest_pin": {"bytes": 8033, "sha256": "30c88d611c89766aca32f5878247014fd830a872034d6fcb890cf29da2f12a4d"}, "result_pin": {"bytes": 24733909, "sha256": "8430ff05cd96a8c58a5f04627a3bcf35ade92efb3612bb3015e179269599487f"}}]。

|group|run|elapsed秒|sampled private peak B|
|---|---|---|---|
|c0-diff-control,c1-phase-level|dev-seed7466813550306735603-layout6-core-c0-c1-20261013|34.49878060002811|152981504|
|c2-phase-conditional|dev-seed7466813550306735603-layout6-core-c2-20261013|31.94428570009768|210968576|

CLI exit0/complete/成功cell2と1、原結果保存後だけsuccess計上。実CLI時間合計 66.44306630012579秒。単候補速度比較の再実行0、速度向上倍率は推定しない。

## 同一入力の原結果

|候補|machine|sensor|precision|clean / unmatched|source / equipment|available / unavailable|delay count / mean / median|
|---|---|---|---|---|---|---|
|c0-diff-control|0/10|0/10|0/1|1 / 1|1 / 1|13920 / 480|0 / None / None|
|c1-phase-level|0/10|10/10|10/20|0 / 10|20 / 20|13920 / 480|10 / 1.0 / 1.0|
|c2-phase-conditional|0/10|10/10|10/20|0 / 10|30 / 20|13920 / 480|10 / 1.0 / 1.0|

全14400scores/利用可13920/不能480（mode_recipe_or_phase）。不能全score/residualnull・thresholdfalse。18000input-mask対応/nonok0。48calibrated/calibration各290、fit sample countsとC2stateは以下の原値。全未検出delaynull補完0。clean_rate/burdenは原単位の指標で単純確率へしない。

### c0-diff-control

profiles {"calibration_counts": {"290": 48}, "fit_counts": {"0": 48}, "statuses": {"calibrated": 48}} / C2state 0 / incident reasons {"no_candidate_in_window": 20}。
delay原 {"conditioned_on": "causal-detected-only", "count": 0, "max": null, "mean": null, "median": null, "min": null, "undetected_fill": "forbidden", "unit": "seconds"} / class別 {"machine": {}, "sensor": {}}。未検出 20 件は全delaynull。
source内訳 {"conveyor-01.motor_temperature": 1}。原source support2score、equipment membership、全未検出窓と選択failed candidateを-save/target-episode-supportへ保存。cleanと全未対応equipmentを別々に保持。
clean_rate {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 3365, "null_replicates": 0, "numerator": 1, "value": 8.558692421991084} / effective seconds 3254 / effective_rate 8.850645359557468 / burden {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 20, "null_replicates": 0, "numerator": 1, "value": 5.0}。
対象window分類は以下の全20原値（available/unavailable/phase/maxstreak）を参照。

|cycle|class|start–end|available|unavailable|phase|maximum streak|reason|candidate count|
|---|---|---|---|---|---|---|---|---|
|0|machine|7214–7220|7|0|0|0|no_candidate_in_window|0|
|0|sensor|7221–7227|7|0|0|1|no_candidate_in_window|0|
|1|machine|7394–7400|7|0|0|0|no_candidate_in_window|0|
|1|sensor|7401–7407|7|0|0|1|no_candidate_in_window|0|
|2|machine|7574–7580|7|0|0|0|no_candidate_in_window|0|
|2|sensor|7581–7587|7|0|0|1|no_candidate_in_window|0|
|3|machine|7754–7760|7|0|0|0|no_candidate_in_window|0|
|3|sensor|7761–7767|7|0|0|1|no_candidate_in_window|0|
|4|machine|7934–7940|7|0|0|0|no_candidate_in_window|0|
|4|sensor|7941–7947|7|0|0|1|no_candidate_in_window|0|
|5|machine|8114–8120|7|0|0|0|no_candidate_in_window|0|
|5|sensor|8121–8127|7|0|0|1|no_candidate_in_window|0|
|6|machine|8294–8300|7|0|0|0|no_candidate_in_window|0|
|6|sensor|8301–8307|7|0|0|1|no_candidate_in_window|0|
|7|machine|8474–8480|7|0|0|0|no_candidate_in_window|0|
|7|sensor|8481–8487|7|0|0|1|no_candidate_in_window|0|
|8|machine|8654–8660|7|0|0|0|no_candidate_in_window|0|
|8|sensor|8661–8667|7|0|0|1|no_candidate_in_window|0|
|9|machine|8834–8840|7|0|0|0|no_candidate_in_window|0|
|9|sensor|8841–8847|7|0|0|1|no_candidate_in_window|0|

### c1-phase-level

profiles {"calibration_counts": {"290": 48}, "fit_counts": {"600": 48}, "statuses": {"calibrated": 48}} / C2state 0 / incident reasons {"causal_detected": 10, "first_candidate_no_target_onset": 10}。
delay原 {"conditioned_on": "causal-detected-only", "count": 10, "max": 1.0, "mean": 1.0, "median": 1.0, "min": 1.0, "undetected_fill": "forbidden", "unit": "seconds"} / class別 {"machine": {}, "sensor": {"1.0": 10}}。未検出 10 件は全delaynull。
source内訳 {"conveyor-01.motor_temperature": 10, "conveyor-01.vibration_feature": 10}。原source support2score、equipment membership、全未検出窓と選択failed candidateを-save/target-episode-supportへ保存。cleanと全未対応equipmentを別々に保持。
clean_rate {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 3365, "null_replicates": 0, "numerator": 0, "value": 0.0} / effective seconds 3254 / effective_rate 0.0 / burden {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 20, "null_replicates": 0, "numerator": 10, "value": 50.0}。
対象window分類は以下の全20原値（available/unavailable/phase/maxstreak）を参照。

|cycle|class|start–end|available|unavailable|phase|maximum streak|reason|candidate count|
|---|---|---|---|---|---|---|---|---|
|0|machine|7214–7220|7|0|0|0|first_candidate_no_target_onset|1|
|0|sensor|7221–7227|7|0|0|3|causal_detected|1|
|1|machine|7394–7400|7|0|0|0|first_candidate_no_target_onset|1|
|1|sensor|7401–7407|7|0|0|3|causal_detected|1|
|2|machine|7574–7580|7|0|0|0|first_candidate_no_target_onset|1|
|2|sensor|7581–7587|7|0|0|3|causal_detected|1|
|3|machine|7754–7760|7|0|0|0|first_candidate_no_target_onset|1|
|3|sensor|7761–7767|7|0|0|3|causal_detected|1|
|4|machine|7934–7940|7|0|0|0|first_candidate_no_target_onset|1|
|4|sensor|7941–7947|7|0|0|3|causal_detected|1|
|5|machine|8114–8120|7|0|0|0|first_candidate_no_target_onset|1|
|5|sensor|8121–8127|7|0|0|3|causal_detected|1|
|6|machine|8294–8300|7|0|0|0|first_candidate_no_target_onset|1|
|6|sensor|8301–8307|7|0|0|3|causal_detected|1|
|7|machine|8474–8480|7|0|0|0|first_candidate_no_target_onset|1|
|7|sensor|8481–8487|7|0|0|3|causal_detected|1|
|8|machine|8654–8660|7|0|0|0|first_candidate_no_target_onset|1|
|8|sensor|8661–8667|7|0|0|3|causal_detected|1|
|9|machine|8834–8840|7|0|0|0|first_candidate_no_target_onset|1|
|9|sensor|8841–8847|7|0|0|3|causal_detected|1|

### c2-phase-conditional

profiles {"calibration_counts": {"290": 48}, "fit_counts": {"600": 48}, "statuses": {"calibrated": 48}} / C2state 48 / incident reasons {"causal_detected": 10, "first_candidate_no_target_onset": 10}。
delay原 {"conditioned_on": "causal-detected-only", "count": 10, "max": 1.0, "mean": 1.0, "median": 1.0, "min": 1.0, "undetected_fill": "forbidden", "unit": "seconds"} / class別 {"machine": {}, "sensor": {"1.0": 10}}。未検出 10 件は全delaynull。
source内訳 {"conveyor-01.motor_current": 10, "conveyor-01.motor_temperature": 10, "conveyor-01.vibration_feature": 10}。原source support2score、equipment membership、全未検出窓と選択failed candidateを-save/target-episode-supportへ保存。cleanと全未対応equipmentを別々に保持。
clean_rate {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 3365, "null_replicates": 0, "numerator": 0, "value": 0.0} / effective seconds 3254 / effective_rate 0.0 / burden {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 20, "null_replicates": 0, "numerator": 10, "value": 50.0}。
対象window分類は以下の全20原値（available/unavailable/phase/maxstreak）を参照。

|cycle|class|start–end|available|unavailable|phase|maximum streak|reason|candidate count|
|---|---|---|---|---|---|---|---|---|
|0|machine|7214–7220|7|0|0|0|first_candidate_no_target_onset|1|
|0|sensor|7221–7227|7|0|0|3|causal_detected|1|
|1|machine|7394–7400|7|0|0|0|first_candidate_no_target_onset|1|
|1|sensor|7401–7407|7|0|0|3|causal_detected|1|
|2|machine|7574–7580|7|0|0|0|first_candidate_no_target_onset|1|
|2|sensor|7581–7587|7|0|0|3|causal_detected|1|
|3|machine|7754–7760|7|0|0|0|first_candidate_no_target_onset|1|
|3|sensor|7761–7767|7|0|0|3|causal_detected|1|
|4|machine|7934–7940|7|0|0|0|first_candidate_no_target_onset|1|
|4|sensor|7941–7947|7|0|0|3|causal_detected|1|
|5|machine|8114–8120|7|0|0|0|first_candidate_no_target_onset|1|
|5|sensor|8121–8127|7|0|0|3|causal_detected|1|
|6|machine|8294–8300|7|0|0|0|first_candidate_no_target_onset|1|
|6|sensor|8301–8307|7|0|0|3|causal_detected|1|
|7|machine|8474–8480|7|0|0|0|first_candidate_no_target_onset|1|
|7|sensor|8481–8487|7|0|0|3|causal_detected|1|
|8|machine|8654–8660|7|0|0|0|first_candidate_no_target_onset|1|
|8|sensor|8661–8667|7|0|0|3|causal_detected|1|
|9|machine|8834–8840|7|0|0|0|first_candidate_no_target_onset|1|
|9|sensor|8841–8847|7|0|0|3|causal_detected|1|

## 停止中の搬送速度を対象にした機械異常の未検出

原全10machineはconveyor-01.conveyor_speed/jam_or_slip/magnitude0.55/operating mode stopped/recipe stop。全対象窓7行利用可/phase不能0、全候補全70対象scoreは各閾値未満/streak0で対象onsetなし。C0はcandidate0、C1/C2は各candidate1/vibration_featureだけのequipmentを選び、first_candidate_no_target_onset/causalfalse/matchednull/delaynull。振動の機械区間警報を搬送速度対象の検出へ補わない。
C1/C2の全未対応equipment10はraw-eventタグ、clean0と別に保持。precision10/20・burden10/20原50.0、delayは検出sensor10のみ各1秒。C1source20とC2source30は全score/episode一致ではない。C0source1/equipment1/clean1を原保存。
原全30machine窓/target dependency値/選択episode/sourceとC1/C2振動support原scoreを-save/stopped-speed-machine-missesおよびtarget-episode-supportに保存。cycle00の原対象値7214/7215/7216は0/0/0.002218。停止中という入力条件を含めて検出成績を記述し、GT/threshold/matching変更で未検出を補わない。実入力対応・保存・状態分類の不具合を観測した結果ではない。

- c0-diff-control machine対象窓最大score 2.4775460963245903 / threshold 4.0。
- c1-phase-level machine対象窓最大score 3.5862264702373 / threshold 6.0。
- c2-phase-conditional machine対象窓最大score 3.5470825203521885 / threshold 6.0。

## 前layout core保存指標との比較

|layout|candidate|machine|sensor|precision|clean|
|---|---|---|---|---|---|
|5|c0-diff-control|0/10|0/10|0/1|1|
|5|c1-phase-level|10/10|10/10|20/20|0|
|5|c2-phase-conditional|10/10|10/10|20/20|0|
|6|c0-diff-control|0/10|0/10|0/1|1|
|6|c1-phase-level|0/10|10/10|10/20|0|
|6|c2-phase-conditional|0/10|10/10|10/20|0|

旧layout5はmanifest/config保存指標だけ比較・再compute0。同seed別layoutで観測inputは異なり、独立新seedや1要因だけの反実仮想差証明ではない。C1/C2の一部集計一致は全score/episode一致や候補採択の証明へしない。
原対象窓ごとの利用可/不能/連続超過とmatching理由を上表に保持した。未検出を閾値・GT・matching変更で補わず、対象外のsource警報を対象の検出へ読み替えない。入力対応・保存・状態分類の実経路不具合は観測なし。全用途不適合や包括的実装認証へしない。

## 証拠・次工程・正式状態

- 新 representative-seed2-layout6-core-three-candidates-20261013-records/analysis/save/finalを優先。DATA2 {"D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout6-core-c0-c1-20261013": {"bytes": 41001036, "files": 22, "manifest_pin": {"bytes": 2582, "sha256": "becb587717e0a29a6d05e2127c271f8d254261ab60a563805cd5551c176e8dbd"}}, "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout6-core-c2-20261013": {"bytes": 37775075, "files": 19, "manifest_pin": {"bytes": 2245, "sha256": "1ac0c4f492a7cf606d30121950a4b8c743e6d3b2ffd216a94b6888e0eb8350c7"}}}。原profiles/scores/events/incidents/episodes/metricsを保存、全20ledger/対象窓/480不能を-analysisに保存。
- 旧108cellモデル再compute0、第1seed72＋第2seed39＝111boardcells/使用seed2、111独立datasetではない。第2seed layout0–5全6cell・layout6core3cell完成。bootstrap/統計CI/勝者採択0。
- 旧516root/459helpers24failed435passedmissingexecution1と全失敗・審査拒否・原誤記を保持。今回新helperfailure0。foreground source検索の不存在path exit1はselected原errorを-saveに保持、fullidentity/全stdioなし、モデルCI/helper失敗へしない。閉鎖外部固定root追記0/PID単独/native回収claim0。
- report/handoff/index3docs一回[skip ci] commit/push、prepare_result_index実使用。人の具体的通知後の同送信先同種合成dev報告・ユーザー名入りPC内pathの継続送信承認に従う。
- 次同seed/layout6 quality-stress、groups [["c0-diff-control", "c1-phase-level"], ["c2-phase-conditional"]] / IDs ["dev-seed7466813550306735603-layout6-quality-c0-c1-20261013", "dev-seed7466813550306735603-layout6-quality-c2-20261013"]。同chunk018 manifest/identity/input10metadataのみ選択、次本文未読/model0。
- EvidenceStore全writepreflight/自動分割/失敗閉鎖reserveを維持。実行900秒/2GiB/output1GiB/single32MiB/files32、Git30秒/16entry/512KiB/stdout1MiB/stderr128KiBとnativeprotocol caps不変。checkpoint≠blocking中断/fullruntime/allwriter/globalmemory容量認証。
- ACTIVE/automation詳細転記0、新testCIagent0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件最終受入未完了/create_native早期拒否/全7役reader禁止/元capsunknown owner保持。Sol容量または人停止は保全後PAUSED。
