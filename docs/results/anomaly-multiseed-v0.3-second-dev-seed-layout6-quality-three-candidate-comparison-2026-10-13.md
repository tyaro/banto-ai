# 第2dev seed・layout6 quality-stressの3候補とcore比較（2026-10-13）

保存済み同一合成dev quality-stress入力でC0+C1、次にC2を順次fresh compute。人の3候補集約許可に従い、既存CLI2候補上限を維持して解析・文書・Gitを1単位にまとめた。処理成功を性能保証・勝者採択・正式受入へしない。

## 入力と実行

- dataset anomaly-v03-dev-seed-7466813550306735603-layout-06-quality-stress / seed7466813550306735603/layout6/quality-stress。元生成候補C0と実評価候補を別fieldに保存。同seedの追加layout、新独立seedではない。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\018\attempt-0001\result\payload\manifest.json / {"bytes": 75699, "sha256": "a8a883a6e85a16f1ae8f152ea3b730252802b186b86df448944d6ea4f3ad0b9f"}。3候補input10全pin一致→各CLI新snapshot/fresh calibration/fit。元payload書込み・新dataset生成・replay0。
- checkout 2d76fadb522c75ded24c122fd5505a179a12544e / 計算661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/candidatecompiled不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}。
- C0 threshold4/C1C2 threshold6/operator>/persistence2/GT/matching不変。全原thresholdflag照合。宣言pinはfull loaded runtime/native認証ではない。
- 原manifest/result pins [{"candidate": "c0-diff-control", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout6-quality-c0-c1-20261013\\manifest.json", "manifest_pin": {"bytes": 11102, "sha256": "776ca5283c9218d375fa5c106491dc4ab9cf5939c9935ca5ae8ac1bb1e1c0142"}, "result_pin": {"bytes": 14333402, "sha256": "501e2748bbd7f95a588b6e06fa4f8cb5cd81bdaebd1c7ff337c213c1531b838a"}}, {"candidate": "c1-phase-level", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout6-quality-c0-c1-20261013\\manifest.json", "manifest_pin": {"bytes": 11102, "sha256": "776ca5283c9218d375fa5c106491dc4ab9cf5939c9935ca5ae8ac1bb1e1c0142"}, "result_pin": {"bytes": 14494355, "sha256": "13bcdc8d5f5a0881851e18146850318f1720aa223cfa6045eabbbc9c590a3119"}}, {"candidate": "c2-phase-conditional", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout6-quality-c2-20261013\\manifest.json", "manifest_pin": {"bytes": 8079, "sha256": "9ace80a46d8764ca7395ccad0b1455c0f8af47d9797b3423de0173fb17d06384"}, "result_pin": {"bytes": 25173543, "sha256": "12c730de11a295e47446914a556fab98b20f88fea12b0b90a821560716aff511"}}]。

|group|run|elapsed秒|sampled private peak B|
|---|---|---|---|
|c0-diff-control,c1-phase-level|dev-seed7466813550306735603-layout6-quality-c0-c1-20261013|32.542751000029966|149532672|
|c2-phase-conditional|dev-seed7466813550306735603-layout6-quality-c2-20261013|27.83419069997035|211386368|

CLI exit0/complete/成功cell2と1、原結果保存後だけsuccess計上。実CLI時間合計 60.376941700000316秒。単候補速度比較の再実行0、速度向上倍率は推定しない。

## 同一入力の原結果

|候補|machine|sensor|precision|clean / unmatched|source / equipment|available / unavailable|delay count / mean / median|
|---|---|---|---|---|---|---|
|c0-diff-control|0/10|0/10|0/1|1 / 1|1 / 1|13889 / 511|0 / None / None|
|c1-phase-level|0/10|9/10|9/19|0 / 10|19 / 19|13889 / 511|9 / 1.0 / 1.0|
|c2-phase-conditional|0/10|9/10|9/19|0 / 10|28 / 19|13796 / 604|9 / 1.0 / 1.0|

全14400scores、18000input-mask対応/nonok30。C0C1利用可13889/不能511（排他的phase471/currentquality30/previousquality10）、C2利用可13796/不能604（追加primary peer93）。phaseタグ480/品質40は9行重複、peerタグ120はphaseと27行重複。非排他的tagsを独立行として加算しない。全不能score/residualnull・thresholdfalse。48calibrated/calibration各290、fit sample countsとC2stateは以下の原値。全未検出delaynull補完0。clean_rate/burdenは原単位の指標で単純確率へしない。

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
|9|sensor|8841–8847|3|4|0|1|no_candidate_in_window|0|

### c1-phase-level

profiles {"calibration_counts": {"290": 48}, "fit_counts": {"600": 48}, "statuses": {"calibrated": 48}} / C2state 0 / incident reasons {"causal_detected": 9, "first_candidate_no_target_onset": 10, "no_candidate_in_window": 1}。
delay原 {"conditioned_on": "causal-detected-only", "count": 9, "max": 1.0, "mean": 1.0, "median": 1.0, "min": 1.0, "undetected_fill": "forbidden", "unit": "seconds"} / class別 {"machine": {}, "sensor": {"1.0": 9}}。未検出 11 件は全delaynull。
source内訳 {"conveyor-01.motor_temperature": 9, "conveyor-01.vibration_feature": 10}。原source support2score、equipment membership、全未検出窓と選択failed candidateを-save/target-episode-supportへ保存。cleanと全未対応equipmentを別々に保持。
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
|9|sensor|8841–8847|3|4|0|1|no_candidate_in_window|0|

### c2-phase-conditional

profiles {"calibration_counts": {"290": 48}, "fit_counts": {"600": 48}, "statuses": {"calibrated": 48}} / C2state 48 / incident reasons {"causal_detected": 9, "first_candidate_no_target_onset": 10, "no_candidate_in_window": 1}。
delay原 {"conditioned_on": "causal-detected-only", "count": 9, "max": 1.0, "mean": 1.0, "median": 1.0, "min": 1.0, "undetected_fill": "forbidden", "unit": "seconds"} / class別 {"machine": {}, "sensor": {"1.0": 9}}。未検出 11 件は全delaynull。
source内訳 {"conveyor-01.motor_current": 9, "conveyor-01.motor_temperature": 9, "conveyor-01.vibration_feature": 10}。原source support2score、equipment membership、全未検出窓と選択failed candidateを-save/target-episode-supportへ保存。cleanと全未対応equipmentを別々に保持。
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
|9|sensor|8841–8847|3|4|0|1|no_candidate_in_window|0|

## cycle09温度欠測の原窓

sensor spike[8841,8844)、matching window 8841–8847。先頭は全候補閾値超過/streak1→次3行current quality不能でreset→さらに1行previous quality不能→最後2行閾値未満/streak0。3利用可4不能/phase不能0/maxstreak1でpersistence2不成立、candidate0/no_candidate_in_window/causalfalse/matchednull/delaynull。欠測なし等の反実仮想再compute0。
原3候補event/incident/全対象7行を-save/cycle09-sensor-missへ保存。C2原primary peer93行と全関連120行（各target31peer＋9phase）を-save/peer-quality-propagationへ保存。温度current/previous品質不能40sample集合との一致・温度phase重複9行を-phase-quality-overlapに保存。
|sample|C0 score|C1 score|C2 score|reason|
|---|---|---|---|---|
|8841|192.12195175946974|171.94340284291576|172.85149166024186|None|
|8842|None|None|None|current_target_quality|
|8843|None|None|None|current_target_quality|
|8844|None|None|None|current_target_quality|
|8845|None|None|None|previous_target_quality_or_nonfinite|
|8846|0.3634819595361694|1.1598184953319401|1.1708346187832492|None|
|8847|1.266202237072548|0.493508723013494|0.4906461887865262|None|

## 同layout core保存指標との比較

|stratum|candidate|machine|sensor|precision|clean|
|---|---|---|---|---|---|
|core|c0-diff-control|0/10|0/10|0/1|1|
|core|c1-phase-level|0/10|10/10|10/20|0|
|core|c2-phase-conditional|0/10|10/10|10/20|0|
|quality-stress|c0-diff-control|0/10|0/10|0/1|1|
|quality-stress|c1-phase-level|0/10|9/10|9/19|0|
|quality-stress|c2-phase-conditional|0/10|9/10|9/19|0|

旧layout6coreはmanifest/config保存指標だけ比較・再compute0。同seed/layoutの別stratumで観測quality等のinputは異なり、独立新seedや欠測だけの反実仮想全差証明ではない。C1/C2の一部集計一致は全score/episode一致や候補採択の証明へしない。
C0対象窓の最大連続超過は1以下で、固定persistence2は成立していない。欠測温度1窓だけで全20未検出を説明しない。原窓・対象supportと未検出delaynullを保存し、検出を閾値・GT・matching変更で補わない。入力対応・保存・状態分類の実経路不具合は観測なし。全用途不適合や包括的実装認証へしない。

## 証拠・次工程・正式状態

- 新 representative-seed2-layout6-quality-three-candidates-20261013-records/analysis/save/finalを優先。DATA2 {"D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout6-quality-c0-c1-20261013": {"bytes": 41881918, "files": 22, "manifest_pin": {"bytes": 2592, "sha256": "45ad9ef417faa7759ed4db7202af1152d6d0298da2aeafc3ffbce6eca2e66a86"}}, "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout6-quality-c2-20261013": {"bytes": 38221177, "files": 19, "manifest_pin": {"bytes": 2255, "sha256": "e44ad918338f4a067101d19b78ccffa3b15e8b5a52e4ec1856f78e281107fc9e"}}}。原profiles/scores/events/incidents/episodes/metricsを保存、全20ledger/対象窓/全不能を-analysisに保存。
- 旧111cellモデル再compute0、第1seed72＋第2seed42＝114boardcells/使用seed2、114独立datasetではない。第2seed layout0–6全6cell比較完成。bootstrap/統計CI/勝者採択0。
- 旧523root/463helpers24failed439passedmissingexecution1と全失敗・審査拒否・原誤記を保持。今回instrumented helperfailure1（原save NameError）を保持。文書source準備の限定置換句読点scope失敗はisolate内/nestedtools-helper-trackedmutation0の原selected errorを-save/source-builder-errorへ保存。閉鎖外部固定root追記0/PID単独/native回収claim0。
- report/handoff/index3docs一回[skip ci] commit/push、prepare_result_index実使用。人の具体的通知後の同送信先同種合成dev報告・ユーザー名入りPC内pathの継続送信承認に従う。
- 次同seed/layout7 core、groups [["c0-diff-control", "c1-phase-level"], ["c2-phase-conditional"]] / IDs ["dev-seed7466813550306735603-layout7-core-c0-c1-20261013", "dev-seed7466813550306735603-layout7-core-c2-20261013"]。chunk019 manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\019\attempt-0001\result\payload\manifest.json / {"bytes": 75700, "sha256": "9dc8513ebff4fa25510a5f3fab4ea2531c48dfa0ee800dc5b7c095475c7fc6f8"}、identity/input10metadataのみ選択、次本文未読/model0。
- EvidenceStore全writepreflight/自動分割/失敗閉鎖reserveを維持。実行900秒/2GiB/output1GiB/single32MiB/files32、Git30秒/16entry/512KiB/stdout1MiB/stderr128KiBとnativeprotocol caps不変。checkpoint≠blocking中断/fullruntime/allwriter/globalmemory容量認証。
- ACTIVE/automation詳細転記0、新testCIagent0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件最終受入未完了/create_native早期拒否/全7役reader禁止/元capsunknown owner保持。Sol容量または人停止は保全後PAUSED。


C1/C2の機械10未検出はcoreと同じ停止中conveyor速度対象/onsetなし・振動-onlyの最初candidate。raw-event未対応equipment10をclean0へ混同しない。今回温度sensor1の追加未検出と独立に保存。前unitの自動審査拒否・原未起動証拠は閉鎖rootを保持し、生成sourceの新規抜粋・実装説明は今回送信payloadへ含めない。


初save helperはNameError（JSON falseをPython式へ誤投入）で文書wb/Git前に失敗。原failed script/traceback/live/executionと全prefixを閉鎖保存し、別save-continuationで文書のみ完成。モデル/解析/原helper再実行0、原failedを成功へしない。最新save-continuation/finalを優先。
