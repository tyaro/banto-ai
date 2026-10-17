# 第2dev seed・layout10 quality-stressの3候補とcore比較（2026-10-13）

保存済み同一合成dev quality-stress入力でC0+C1、次にC2を順次fresh compute。人の3候補集約許可に従い、既存CLI2候補上限を維持して解析・文書・Gitを1単位にまとめた。処理成功を性能保証・勝者採択・正式受入へしない。

## 入力と実行

- dataset anomaly-v03-dev-seed-7466813550306735603-layout-10-quality-stress / seed7466813550306735603/layout10/quality-stress。元生成候補C0と実評価候補を別fieldに保存。同seedの追加layout、新独立seedではない。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\022\attempt-0001\result\payload\manifest.json / {"bytes": 75713, "sha256": "61b496ae02e6261906b52ac8c57aed5138188dc1519198f1d1e0bbb739ede944"}。3候補input10全pin一致→各CLI新snapshot/fresh calibration/fit。元payload書込み・新dataset生成・replay0。
- checkout e3d3d75092129b2a54612536aeff6dfc89cb029d / 計算661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/candidatecompiled不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}。
- C0 threshold4/C1C2 threshold6/operator>/persistence2/GT/matching不変。全原thresholdflag照合。宣言pinはfull loaded runtime/native認証ではない。
- 原manifest/result pins [{"candidate": "c0-diff-control", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout10-quality-c0-c1-20261013\\manifest.json", "manifest_pin": {"bytes": 11087, "sha256": "534d63da81edde35c7d178c71d1d7866daff69f15afb09f5c894ed2ede52f478"}, "result_pin": {"bytes": 14333631, "sha256": "23f1c3869f7e2aa76a973caa62abf8d86263fe6302fbe02ec96e399be353da5a"}}, {"candidate": "c1-phase-level", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout10-quality-c0-c1-20261013\\manifest.json", "manifest_pin": {"bytes": 11087, "sha256": "534d63da81edde35c7d178c71d1d7866daff69f15afb09f5c894ed2ede52f478"}, "result_pin": {"bytes": 14512185, "sha256": "5ef4425621b44aa0630ff7b6e36ecefaf4b61dd54074584e5eedc854e3c56f51"}}, {"candidate": "c2-phase-conditional", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout10-quality-c2-20261013\\manifest.json", "manifest_pin": {"bytes": 8067, "sha256": "44b130baa7eee0308b6ba21731686ab4714f637c81640bf28d27bb462fcabbc0"}, "result_pin": {"bytes": 25181472, "sha256": "cc062c658f3536d3a47f29c07d566c6e2448fd506dc634d15b148037fee24a55"}}]。

|group|run|elapsed秒|sampled private peak B|
|---|---|---|---|
|c0-diff-control,c1-phase-level|dev-seed7466813550306735603-layout10-quality-c0-c1-20261013|32.3072564000031|150802432|
|c2-phase-conditional|dev-seed7466813550306735603-layout10-quality-c2-20261013|26.268060199916363|210599936|

CLI exit0/complete/成功cell2と1、原結果保存後だけsuccess計上。実CLI時間合計 58.57531659991946秒。単候補速度比較の再実行0、速度向上倍率は推定しない。

## 同一入力の原結果

|候補|machine|sensor|precision|clean / unmatched|source / equipment|available / unavailable|delay count / mean / median|
|---|---|---|---|---|---|---|
|c0-diff-control|0/10|0/10|0/1|1 / 1|1 / 1|13889 / 511|0 / None / None|
|c1-phase-level|10/10|9/10|19/19|0 / 0|29 / 19|13889 / 511|19 / 1.0 / 1.0|
|c2-phase-conditional|10/10|9/10|19/19|0 / 0|29 / 19|13796 / 604|19 / 1.0 / 1.0|

全14400scoresの利用可・不能数と排他的primary reasonは下記原結果の集計を参照。不能全score/residualnull・thresholdfalse。18000input-mask対応/nonok30。48calibrated/calibration各290、fit sample countsとC2stateは以下の原値。全未検出delaynull補完0。clean_rate/burdenは原単位の指標で単純確率へしない。

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
|9|sensor|8961–8967|3|4|0|1|no_candidate_in_window|0|

### c1-phase-level

profiles {"calibration_counts": {"290": 48}, "fit_counts": {"600": 48}, "statuses": {"calibrated": 48}} / C2state 0 / incident reasons {"causal_detected": 19, "no_candidate_in_window": 1}。
delay原 {"conditioned_on": "causal-detected-only", "count": 19, "max": 1.0, "mean": 1.0, "median": 1.0, "min": 1.0, "undetected_fill": "forbidden", "unit": "seconds"} / class別 {"machine": {"1.0": 10}, "sensor": {"1.0": 9}}。未検出 1 件は全delaynull。
source内訳 {"conveyor-01.conveyor_speed": 10, "conveyor-01.motor_temperature": 9, "conveyor-01.vibration_feature": 10}。原source support2score、equipment membership、全未検出窓と選択failed candidateを-save/target-episode-supportへ保存。cleanと全未対応equipmentを別々に保持。
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
|9|sensor|8961–8967|3|4|0|1|no_candidate_in_window|0|

### c2-phase-conditional

profiles {"calibration_counts": {"290": 48}, "fit_counts": {"600": 48}, "statuses": {"calibrated": 48}} / C2state 48 / incident reasons {"causal_detected": 19, "no_candidate_in_window": 1}。
delay原 {"conditioned_on": "causal-detected-only", "count": 19, "max": 1.0, "mean": 1.0, "median": 1.0, "min": 1.0, "undetected_fill": "forbidden", "unit": "seconds"} / class別 {"machine": {"1.0": 10}, "sensor": {"1.0": 9}}。未検出 1 件は全delaynull。
source内訳 {"conveyor-01.conveyor_speed": 10, "conveyor-01.motor_temperature": 9, "conveyor-01.vibration_feature": 10}。原source support2score、equipment membership、全未検出窓と選択failed candidateを-save/target-episode-supportへ保存。cleanと全未対応equipmentを別々に保持。
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
|9|sensor|8961–8967|3|4|0|1|no_candidate_in_window|0|

## 同layout core保存指標との比較

|stratum|candidate|machine|sensor|precision|clean|
|---|---|---|---|---|---|
|core|c0-diff-control|0/10|0/10|0/1|1|
|core|c1-phase-level|10/10|10/10|20/20|0|
|core|c2-phase-conditional|10/10|10/10|20/20|0|
|quality-stress|c0-diff-control|0/10|0/10|0/1|1|
|quality-stress|c1-phase-level|10/10|9/10|19/19|0|
|quality-stress|c2-phase-conditional|10/10|9/10|19/19|0|

旧layout10coreはmanifest/config保存指標だけ比較・再compute0。同seed/layoutの別stratumでinput品質等は異なり、独立新seedや欠測だけの反実仮想全差証明ではない。C1/C2の一部集計一致は全score/episode一致や候補採択の証明へしない。
全候補の全20対象窓の利用可・不能・最大streakと、原選択episodeのtarget対応を上表と保存ledgerから確認した。未検出は原reasonとdelaynullを保持し、閾値・GT・matching変更で補わない。入力対応・保存・状態分類の実経路不具合は観測なし。全用途不適合や包括的実装認証へしない。

対象窓の原分類集約 {"c0-diff-control": {"machine": [{"available": 7, "unavailable": 0, "phase_unavailable": 0, "max_streak": 1, "window_count": 10}], "sensor": [{"available": 7, "unavailable": 0, "phase_unavailable": 0, "max_streak": 1, "window_count": 9}, {"available": 3, "unavailable": 4, "phase_unavailable": 0, "max_streak": 1, "window_count": 1}]}, "c1-phase-level": {"machine": [{"available": 7, "unavailable": 0, "phase_unavailable": 0, "max_streak": 3, "window_count": 10}], "sensor": [{"available": 7, "unavailable": 0, "phase_unavailable": 0, "max_streak": 3, "window_count": 9}, {"available": 3, "unavailable": 4, "phase_unavailable": 0, "max_streak": 1, "window_count": 1}]}, "c2-phase-conditional": {"machine": [{"available": 7, "unavailable": 0, "phase_unavailable": 0, "max_streak": 3, "window_count": 10}], "sensor": [{"available": 7, "unavailable": 0, "phase_unavailable": 0, "max_streak": 3, "window_count": 9}, {"available": 3, "unavailable": 4, "phase_unavailable": 0, "max_streak": 1, "window_count": 1}]}}。全対象score/streakと原episode supportを併せて保存し、phase不能や欠測温度1窓だけで全未検出を説明しない。
## 証拠・次工程・正式状態

- 新 representative-seed2-layout10-quality-three-candidates-20261013-records/analysis/save/finalを優先。DATA2 {"D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout10-quality-c0-c1-20261013": {"bytes": 41900141, "files": 22, "manifest_pin": {"bytes": 2593, "sha256": "a055007b1556e2733b4bddcd482cf62eb6a744f0265d85c53bb225133a389040"}}, "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout10-quality-c2-20261013": {"bytes": 38229273, "files": 19, "manifest_pin": {"bytes": 2256, "sha256": "72cae7c6c3d48ab0cb286baff5a1179486653a0449c92e2506b24af6aaf714dd"}}}。原profiles/scores/events/incidents/episodes/metricsを保存、全20ledger/対象窓/480不能を-analysisに保存。
- 旧135cellモデル再compute0、第1seed72＋第2seed66＝138boardcells/使用seed2、138独立datasetではない。layout0–10全6cell比較完成。bootstrap/統計CI/勝者採択0。
- 旧574root/498helpers27failed471passedmissingexecution1と全失敗・審査拒否・原誤記を保持。今回新helperfailure0/閉鎖外部固定root追記0/PID単独/native回収claim0。
- report/handoff/index3docs一回[skip ci] commit/push、prepare_result_index実使用。人の具体的通知後の同送信先同種合成dev報告・ユーザー名入りPC内pathの継続送信承認に従う。
- 次同seed/layout11 core、groups [["c0-diff-control", "c1-phase-level"], ["c2-phase-conditional"]] / IDs ["dev-seed7466813550306735603-layout11-core-c0-c1-20261013", "dev-seed7466813550306735603-layout11-core-c2-20261013"]。chunk023 manifest/identity/input10metadataのみ選択、次本文未読/model0。
- EvidenceStore全writepreflight/自動分割/失敗閉鎖reserveを維持。実行900秒/2GiB/output1GiB/single32MiB/files32、Git30秒/16entry/512KiB/stdout1MiB/stderr128KiBとnativeprotocol caps不変。checkpoint≠blocking中断/fullruntime/allwriter/globalmemory容量認証。
- ACTIVE/automation詳細転記0、新testCIagent0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件最終受入未完了/create_native早期拒否/全7役reader禁止/元capsunknown owner保持。Sol容量または人停止は保全後PAUSED。


## cycle09 sensorの原未検出窓

spike[8961,8964)、matching window 8961–8967。先頭閾値超過streak1→current品質不能3行→previous品質不能1行→最後2行は閾値未満/streak0。3利用可4不能/phase0/maxstreak1、candidate0/no_candidate_in_window/causalfalse/matchednull/delaynull。原event/incident/全候補の対象7行をcycle09-sensor-missへ保存。
|sample|C0 score|C1 score|C2 score|reason|
|---|---|---|---|---|
|8961|191.2043295128039|147.91166453908394|147.2179149123294|None|
|8962|None|None|None|current_target_quality|
|8963|None|None|None|current_target_quality|
|8964|None|None|None|current_target_quality|
|8965|None|None|None|previous_target_quality_or_nonfinite|
|8966|0.7538588709718984|0.33284470615547873|0.33324718865734304|None|
|8967|1.4688087419404192|0.3908887439901756|0.4490715588441102|None|

C0C1 available13889/unavailable511（primary phase471/current30/previous10）、C2 available13796/unavailable604（追加primary peer93）。phaseタグ480と温度品質不能40samplesは9行重複。current/speed/vibration各40関連行はprimary peer31＋phase9、peerタグ120とphaseの重複27を追加不能へ加算しない。core比不能増31/31/124。原全関連120行・primary peer93行と温度40行をpeer-quality-propagationへ保存。


前layout10 coreはcommit後pushがEmpty reply from server/exit128で原helper failed。原script/raw/live-executionを閉鎖保存し、新save-continuationはリモートが元HEADのままと実観測後、同commitを一度送信してHEAD/upstream/remote/cleanと全文書pinsを照合した。新commit/model/元helper再実行0、元push失敗は成功へ書換えない。保守的累積Git5.361530400114134秒/30秒内。旧報告helperfailure0はGit前snapshotで、最新finalのcurrenthelperfailure1/全27failedを優先。
