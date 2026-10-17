# 第2dev seed・layout10 coreのC0/C1/C2比較（2026-10-13）

保存済み同一合成dev core入力でC0+C1、次にC2を順次fresh compute。人の3候補集約許可に従い、既存CLI2候補上限を維持して解析・文書・Gitを1単位にまとめた。処理成功を性能保証・勝者採択・正式受入へしない。

## 入力と実行

- dataset anomaly-v03-dev-seed-7466813550306735603-layout-10-core / seed7466813550306735603/layout10/core。元生成候補C0と実評価候補を別fieldに保存。同seedの追加layout、新独立seedではない。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\022\attempt-0001\result\payload\manifest.json / {"bytes": 75713, "sha256": "61b496ae02e6261906b52ac8c57aed5138188dc1519198f1d1e0bbb739ede944"}。3候補input10全pin一致→各CLI新snapshot/fresh calibration/fit。元payload書込み・新dataset生成・replay0。
- checkout fff81695bae8492fee8c89d9856f6deccfd1eb73 / 計算661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/candidatecompiled不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}。
- C0 threshold4/C1C2 threshold6/operator>/persistence2/GT/matching不変。全原thresholdflag照合。宣言pinはfull loaded runtime/native認証ではない。
- 原manifest/result pins [{"candidate": "c0-diff-control", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout10-core-c0-c1-20261013\\manifest.json", "manifest_pin": {"bytes": 11056, "sha256": "72461dd6127f6ab7f9874e7fde85af170fefd1ecf2a485c7b74b210dc80929e9"}, "result_pin": {"bytes": 13896467, "sha256": "f29eda1e70ddd5983b969a29108cbefa36dd8c4ddf135825fead474b52cba360"}}, {"candidate": "c1-phase-level", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout10-core-c0-c1-20261013\\manifest.json", "manifest_pin": {"bytes": 11056, "sha256": "72461dd6127f6ab7f9874e7fde85af170fefd1ecf2a485c7b74b210dc80929e9"}, "result_pin": {"bytes": 14073728, "sha256": "61598d2defdc6e46eb897a7b2305550019835860cae400a5eb1caa6678ac171d"}}, {"candidate": "c2-phase-conditional", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout10-core-c2-20261013\\manifest.json", "manifest_pin": {"bytes": 8035, "sha256": "901234fc62271f0416d073a206ad9fc2e245a482f3791f52ca2fd3f01ba553b3"}, "result_pin": {"bytes": 24740216, "sha256": "81a466348473a134d229fa1cf9ccae544ebacdce8d41cb7997733f1535f6f0a8"}}]。

|group|run|elapsed秒|sampled private peak B|
|---|---|---|---|
|c0-diff-control,c1-phase-level|dev-seed7466813550306735603-layout10-core-c0-c1-20261013|32.66597719991114|151261184|
|c2-phase-conditional|dev-seed7466813550306735603-layout10-core-c2-20261013|28.080913999932818|212619264|

CLI exit0/complete/成功cell2と1、原結果保存後だけsuccess計上。実CLI時間合計 60.74689119984396秒。単候補速度比較の再実行0、速度向上倍率は推定しない。

## 同一入力の原結果

|候補|machine|sensor|precision|clean / unmatched|source / equipment|available / unavailable|delay count / mean / median|
|---|---|---|---|---|---|---|
|c0-diff-control|0/10|0/10|0/1|1 / 1|1 / 1|13920 / 480|0 / None / None|
|c1-phase-level|10/10|10/10|20/20|0 / 0|30 / 20|13920 / 480|20 / 1.0 / 1.0|
|c2-phase-conditional|10/10|10/10|20/20|0 / 0|30 / 20|13920 / 480|20 / 1.0 / 1.0|

全14400scores/利用可13920/不能480（mode_recipe_or_phase）。不能全score/residualnull・thresholdfalse。18000input-mask対応/nonok0。48calibrated/calibration各290、fit sample countsとC2stateは以下の原値。全未検出delaynull補完0。clean_rate/burdenは原単位の指標で単純確率へしない。

### c0-diff-control

profiles {"calibration_counts": {"290": 48}, "fit_counts": {"0": 48}, "statuses": {"calibrated": 48}} / C2state 0 / incident reasons {"no_candidate_in_window": 20}。
delay原 {"conditioned_on": "causal-detected-only", "count": 0, "max": null, "mean": null, "median": null, "min": null, "undetected_fill": "forbidden", "unit": "seconds"} / class別 {"machine": {}, "sensor": {}}。未検出 20 件は全delaynull。
source内訳 {"conveyor-01.motor_temperature": 1}。原source support2score、equipment membership、全未検出窓と選択failed candidateを-save/target-episode-supportへ保存。cleanと全未対応equipmentを別々に保持。
clean_rate {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 3365, "null_replicates": 0, "numerator": 1, "value": 8.558692421991084} / effective seconds 3254 / effective_rate 8.850645359557468 / burden {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 20, "null_replicates": 0, "numerator": 1, "value": 5.0}。
対象window分類は以下の全20原値（available/unavailable/phase/maxstreak）を参照。

|cycle|class|start–end|available|unavailable|phase|maximum streak|reason|candidate count|
|---|---|---|---|---|---|---|---|---|
|0|machine|7334–7340|7|0|0|1|no_candidate_in_window|0|
|0|sensor|7341–7347|7|0|0|1|no_candidate_in_window|0|
|1|machine|7514–7520|7|0|0|1|no_candidate_in_window|0|
|1|sensor|7521–7527|7|0|0|1|no_candidate_in_window|0|
|2|machine|7694–7700|7|0|0|1|no_candidate_in_window|0|
|2|sensor|7701–7707|7|0|0|1|no_candidate_in_window|0|
|3|machine|7874–7880|7|0|0|1|no_candidate_in_window|0|
|3|sensor|7881–7887|7|0|0|1|no_candidate_in_window|0|
|4|machine|8054–8060|7|0|0|1|no_candidate_in_window|0|
|4|sensor|8061–8067|7|0|0|1|no_candidate_in_window|0|
|5|machine|8234–8240|7|0|0|1|no_candidate_in_window|0|
|5|sensor|8241–8247|7|0|0|1|no_candidate_in_window|0|
|6|machine|8414–8420|7|0|0|1|no_candidate_in_window|0|
|6|sensor|8421–8427|7|0|0|1|no_candidate_in_window|0|
|7|machine|8594–8600|7|0|0|1|no_candidate_in_window|0|
|7|sensor|8601–8607|7|0|0|1|no_candidate_in_window|0|
|8|machine|8774–8780|7|0|0|1|no_candidate_in_window|0|
|8|sensor|8781–8787|7|0|0|1|no_candidate_in_window|0|
|9|machine|8954–8960|7|0|0|1|no_candidate_in_window|0|
|9|sensor|8961–8967|7|0|0|1|no_candidate_in_window|0|

### c1-phase-level

profiles {"calibration_counts": {"290": 48}, "fit_counts": {"600": 48}, "statuses": {"calibrated": 48}} / C2state 0 / incident reasons {"causal_detected": 20}。
delay原 {"conditioned_on": "causal-detected-only", "count": 20, "max": 1.0, "mean": 1.0, "median": 1.0, "min": 1.0, "undetected_fill": "forbidden", "unit": "seconds"} / class別 {"machine": {"1.0": 10}, "sensor": {"1.0": 10}}。未検出 0 件は全delaynull。
source内訳 {"conveyor-01.conveyor_speed": 10, "conveyor-01.motor_temperature": 10, "conveyor-01.vibration_feature": 10}。原source support2score、equipment membership、全未検出窓と選択failed candidateを-save/target-episode-supportへ保存。cleanと全未対応equipmentを別々に保持。
clean_rate {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 3365, "null_replicates": 0, "numerator": 0, "value": 0.0} / effective seconds 3254 / effective_rate 0.0 / burden {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 20, "null_replicates": 0, "numerator": 0, "value": 0.0}。
対象window分類は以下の全20原値（available/unavailable/phase/maxstreak）を参照。

|cycle|class|start–end|available|unavailable|phase|maximum streak|reason|candidate count|
|---|---|---|---|---|---|---|---|---|
|0|machine|7334–7340|7|0|0|3|causal_detected|1|
|0|sensor|7341–7347|7|0|0|3|causal_detected|1|
|1|machine|7514–7520|7|0|0|3|causal_detected|1|
|1|sensor|7521–7527|7|0|0|3|causal_detected|1|
|2|machine|7694–7700|7|0|0|3|causal_detected|1|
|2|sensor|7701–7707|7|0|0|3|causal_detected|1|
|3|machine|7874–7880|7|0|0|3|causal_detected|1|
|3|sensor|7881–7887|7|0|0|3|causal_detected|1|
|4|machine|8054–8060|7|0|0|3|causal_detected|1|
|4|sensor|8061–8067|7|0|0|3|causal_detected|1|
|5|machine|8234–8240|7|0|0|3|causal_detected|1|
|5|sensor|8241–8247|7|0|0|3|causal_detected|1|
|6|machine|8414–8420|7|0|0|3|causal_detected|1|
|6|sensor|8421–8427|7|0|0|3|causal_detected|1|
|7|machine|8594–8600|7|0|0|3|causal_detected|1|
|7|sensor|8601–8607|7|0|0|3|causal_detected|1|
|8|machine|8774–8780|7|0|0|3|causal_detected|1|
|8|sensor|8781–8787|7|0|0|3|causal_detected|1|
|9|machine|8954–8960|7|0|0|3|causal_detected|1|
|9|sensor|8961–8967|7|0|0|3|causal_detected|1|

### c2-phase-conditional

profiles {"calibration_counts": {"290": 48}, "fit_counts": {"600": 48}, "statuses": {"calibrated": 48}} / C2state 48 / incident reasons {"causal_detected": 20}。
delay原 {"conditioned_on": "causal-detected-only", "count": 20, "max": 1.0, "mean": 1.0, "median": 1.0, "min": 1.0, "undetected_fill": "forbidden", "unit": "seconds"} / class別 {"machine": {"1.0": 10}, "sensor": {"1.0": 10}}。未検出 0 件は全delaynull。
source内訳 {"conveyor-01.conveyor_speed": 10, "conveyor-01.motor_temperature": 10, "conveyor-01.vibration_feature": 10}。原source support2score、equipment membership、全未検出窓と選択failed candidateを-save/target-episode-supportへ保存。cleanと全未対応equipmentを別々に保持。
clean_rate {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 3365, "null_replicates": 0, "numerator": 0, "value": 0.0} / effective seconds 3254 / effective_rate 0.0 / burden {"ci_lower": null, "ci_status": "not_evaluated", "ci_upper": null, "denominator": 20, "null_replicates": 0, "numerator": 0, "value": 0.0}。
対象window分類は以下の全20原値（available/unavailable/phase/maxstreak）を参照。

|cycle|class|start–end|available|unavailable|phase|maximum streak|reason|candidate count|
|---|---|---|---|---|---|---|---|---|
|0|machine|7334–7340|7|0|0|3|causal_detected|1|
|0|sensor|7341–7347|7|0|0|3|causal_detected|1|
|1|machine|7514–7520|7|0|0|3|causal_detected|1|
|1|sensor|7521–7527|7|0|0|3|causal_detected|1|
|2|machine|7694–7700|7|0|0|3|causal_detected|1|
|2|sensor|7701–7707|7|0|0|3|causal_detected|1|
|3|machine|7874–7880|7|0|0|3|causal_detected|1|
|3|sensor|7881–7887|7|0|0|3|causal_detected|1|
|4|machine|8054–8060|7|0|0|3|causal_detected|1|
|4|sensor|8061–8067|7|0|0|3|causal_detected|1|
|5|machine|8234–8240|7|0|0|3|causal_detected|1|
|5|sensor|8241–8247|7|0|0|3|causal_detected|1|
|6|machine|8414–8420|7|0|0|3|causal_detected|1|
|6|sensor|8421–8427|7|0|0|3|causal_detected|1|
|7|machine|8594–8600|7|0|0|3|causal_detected|1|
|7|sensor|8601–8607|7|0|0|3|causal_detected|1|
|8|machine|8774–8780|7|0|0|3|causal_detected|1|
|8|sensor|8781–8787|7|0|0|3|causal_detected|1|
|9|machine|8954–8960|7|0|0|3|causal_detected|1|
|9|sensor|8961–8967|7|0|0|3|causal_detected|1|

## 前layout core保存指標との比較

|layout|candidate|machine|sensor|precision|clean|
|---|---|---|---|---|---|
|9|c0-diff-control|0/10|0/10|0/1|1|
|9|c1-phase-level|10/10|10/10|20/20|0|
|9|c2-phase-conditional|10/10|10/10|20/20|0|
|10|c0-diff-control|0/10|0/10|0/1|1|
|10|c1-phase-level|10/10|10/10|20/20|0|
|10|c2-phase-conditional|10/10|10/10|20/20|0|

旧layout9はmanifest/config保存指標だけ比較・再compute0。同seed別layoutで観測inputは異なり、独立新seedや1要因だけの反実仮想差証明ではない。C1/C2の一部集計一致は全score/episode一致や候補採択の証明へしない。
全候補の全20対象窓の利用可・不能・最大streakと、原選択episodeのtarget対応を上表と保存ledgerから確認した。未検出は原reasonとdelaynullを保持し、閾値・GT・matching変更で補わない。入力対応・保存・状態分類の実経路不具合は観測なし。全用途不適合や包括的実装認証へしない。

対象窓の原分類集約 {"c0-diff-control": {"machine": [{"available": 7, "unavailable": 0, "phase_unavailable": 0, "max_streak": 1, "window_count": 10}], "sensor": [{"available": 7, "unavailable": 0, "phase_unavailable": 0, "max_streak": 1, "window_count": 10}]}, "c1-phase-level": {"machine": [{"available": 7, "unavailable": 0, "phase_unavailable": 0, "max_streak": 3, "window_count": 10}], "sensor": [{"available": 7, "unavailable": 0, "phase_unavailable": 0, "max_streak": 3, "window_count": 10}]}, "c2-phase-conditional": {"machine": [{"available": 7, "unavailable": 0, "phase_unavailable": 0, "max_streak": 3, "window_count": 10}], "sensor": [{"available": 7, "unavailable": 0, "phase_unavailable": 0, "max_streak": 3, "window_count": 10}]}}。全対象score/streakと原episode supportを併せて保存し、対象窓の不能だけで全未検出を説明しない。
## 証拠・次工程・正式状態

- 新 representative-seed2-layout10-core-three-candidates-20261013-records/analysis/save/finalを優先。DATA2 {"D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout10-core-c0-c1-20261013": {"bytes": 41018059, "files": 22, "manifest_pin": {"bytes": 2583, "sha256": "ae4102a9f5dcdf40f06011a5919aff22438110711b26a39241fbde541fe7fa42"}}, "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout10-core-c2-20261013": {"bytes": 37781555, "files": 19, "manifest_pin": {"bytes": 2246, "sha256": "017645d97c822c6faec49a9199d2178682c5d7056c3550eb263d2ff926bd2e93"}}}。原profiles/scores/events/incidents/episodes/metricsを保存、全20ledger/対象窓/480不能を-analysisに保存。
- 旧132cellモデル再compute0、第1seed72＋第2seed63＝135boardcells/使用seed2、135独立datasetではない。layout0–9全6cell・layout10core3cell完成。bootstrap/統計CI/勝者採択0。
- 旧567root/493helpers26failed467passedmissingexecution1と全失敗・審査拒否・原誤記を保持。今回新helperfailure0/閉鎖外部固定root追記0/PID単独/native回収claim0。
- report/handoff/index3docs一回[skip ci] commit/push、prepare_result_index実使用。人の具体的通知後の同送信先同種合成dev報告・ユーザー名入りPC内pathの継続送信承認に従う。
- 次同seed/layout10 quality-stress、groups [["c0-diff-control", "c1-phase-level"], ["c2-phase-conditional"]] / IDs ["dev-seed7466813550306735603-layout10-quality-c0-c1-20261013", "dev-seed7466813550306735603-layout10-quality-c2-20261013"]。同chunk022 manifest/identity/input10metadataのみ選択、次本文未読/model0。
- EvidenceStore全writepreflight/自動分割/失敗閉鎖reserveを維持。実行900秒/2GiB/output1GiB/single32MiB/files32、Git30秒/16entry/512KiB/stdout1MiB/stderr128KiBとnativeprotocol caps不変。checkpoint≠blocking中断/fullruntime/allwriter/globalmemory容量認証。
- ACTIVE/automation詳細転記0、新testCIagent0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件最終受入未完了/create_native早期拒否/全7役reader禁止/元capsunknown owner保持。Sol容量または人停止は保全後PAUSED。


全候補の全20対象窓は7行利用可/phase不能0。C0は全窓maxstreak1/candidate0/no_candidate_in_windowでpersistence2不成立。C1/C2は全窓maxstreak3、machine10/sensor10各delay1秒でprecision20/20/clean0。C1/C2 source30/equipment20という集計一致を全score/episode一致や候補採択へ読み替えない。effective clean seconds3254を原値として保持。
