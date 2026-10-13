# 第2dev seed・layout5 quality-stressの3候補とcore比較（2026-10-13）

保存済み同一合成dev quality-stress入力でC0+C1、次にC2を順次fresh compute。人の3候補集約許可に従い、既存CLI2候補上限を維持して解析・文書・Gitを1単位にまとめた。処理成功を性能保証・勝者採択・正式受入へしない。

## 入力と実行

- dataset anomaly-v03-dev-seed-7466813550306735603-layout-05-quality-stress / seed7466813550306735603/layout5/quality-stress。元生成候補C0と実評価候補を別fieldに保存。同seedの追加layout、新独立seedではない。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\017\attempt-0001\result\payload\manifest.json / {"bytes": 75699, "sha256": "16c4319322e2e6ecc5228c513240d1a935cb1047e2bf15c78c3f83741e501746"}。3候補input10全pin一致→各CLI新snapshot/fresh calibration/fit。元payload書込み・新dataset生成・replay0。
- checkout 0c628f5c0c55986242a7449d5953ce67dc10347d / 計算661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/candidatecompiled不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}。
- C0 threshold4/C1C2 threshold6/operator>/persistence2/GT/matching不変。全原thresholdflag照合。宣言pinはfull loaded runtime/native認証ではない。
- 原manifest/result pins [{"candidate": "c0-diff-control", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout5-quality-c0-c1-20261013\\manifest.json", "manifest_pin": {"bytes": 11087, "sha256": "51b6aace546f93ee71cc983b03102cb0c02a82afeb313a21ce8aa9616f033d7e"}, "result_pin": {"bytes": 14333311, "sha256": "048b01b588d52c1dd97f1933e0e27a4279152d2deae322558865ce02341b5a1f"}}, {"candidate": "c1-phase-level", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout5-quality-c0-c1-20261013\\manifest.json", "manifest_pin": {"bytes": 11087, "sha256": "51b6aace546f93ee71cc983b03102cb0c02a82afeb313a21ce8aa9616f033d7e"}, "result_pin": {"bytes": 14510583, "sha256": "a5d62f5d0bf90de31b5fb7b2a7d9363dd7edafc19de7ecdbd9f7305b2bc8b3f2"}}, {"candidate": "c2-phase-conditional", "manifest_path": "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout5-quality-c2-20261013\\manifest.json", "manifest_pin": {"bytes": 8065, "sha256": "a877c35c1e83b19565e46e3ced9df743a73f6238f3a023ea902b970c1d95117e"}, "result_pin": {"bytes": 25190622, "sha256": "cd9daf3052d789b5072af2d0aa337b26ae49fd4626d01c0fd6fdb46850424e8e"}}]。

|group|run|elapsed秒|sampled private peak B|
|---|---|---|---|
|c0-diff-control,c1-phase-level|dev-seed7466813550306735603-layout5-quality-c0-c1-20261013|32.411166599951684|151769088|
|c2-phase-conditional|dev-seed7466813550306735603-layout5-quality-c2-20261013|28.115688399993815|213307392|

CLI exit0/complete/成功cell2と1、原結果保存後だけsuccess計上。実CLI時間合計 60.5268549999455秒。単候補速度比較の再実行0、速度向上倍率は推定しない。

## 同一入力の原結果

|候補|machine|sensor|precision|clean / unmatched|source / equipment|available / unavailable|delay count / mean / median|
|---|---|---|---|---|---|---|
|c0-diff-control|0/10|0/10|0/1|1 / 1|1 / 1|13880 / 520|0 / None / None|
|c1-phase-level|10/10|9/10|19/19|0 / 0|29 / 19|13880 / 520|19 / 1.0 / 1.0|
|c2-phase-conditional|10/10|9/10|19/19|0 / 0|38 / 19|13760 / 640|19 / 1.0 / 1.0|

全14400scores、18000input-mask対応/nonok30。C0C1利用可13880/不能520（phase480/currentquality30/previousquality10）、C2利用可13760/不能640（さらにpeer120）。不能全score/residualnull・thresholdfalse、phasequality overlap0。48calibrated/calibration各290、fit sample countsとC2stateは以下の原値。全未検出delaynull補完0。clean_rate/burdenは原単位の指標で単純確率へしない。

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
|9|sensor|8984–8990|3|4|0|1|no_candidate_in_window|0|

### c1-phase-level

profiles {"calibration_counts": {"290": 48}, "fit_counts": {"600": 48}, "statuses": {"calibrated": 48}} / C2state 0 / incident reasons {"causal_detected": 19, "no_candidate_in_window": 1}。
delay原 {"conditioned_on": "causal-detected-only", "count": 19, "max": 1.0, "mean": 1.0, "median": 1.0, "min": 1.0, "undetected_fill": "forbidden", "unit": "seconds"} / class別 {"machine": {"1.0": 10}, "sensor": {"1.0": 9}}。未検出 1 件は全delaynull。
source内訳 {"motor-01.motor_current": 10, "motor-01.motor_temperature": 9, "motor-01.vibration_feature": 10}。原source support2score、equipment membership、全未検出窓と選択failed candidateを-save/target-episode-supportへ保存。cleanと全未対応equipmentを別々に保持。
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
|9|sensor|8984–8990|3|4|0|1|no_candidate_in_window|0|

### c2-phase-conditional

profiles {"calibration_counts": {"290": 48}, "fit_counts": {"600": 48}, "statuses": {"calibrated": 48}} / C2state 48 / incident reasons {"causal_detected": 19, "no_candidate_in_window": 1}。
delay原 {"conditioned_on": "causal-detected-only", "count": 19, "max": 1.0, "mean": 1.0, "median": 1.0, "min": 1.0, "undetected_fill": "forbidden", "unit": "seconds"} / class別 {"machine": {"1.0": 10}, "sensor": {"1.0": 9}}。未検出 1 件は全delaynull。
source内訳 {"motor-01.motor_current": 19, "motor-01.motor_temperature": 9, "motor-01.vibration_feature": 10}。原source support2score、equipment membership、全未検出窓と選択failed candidateを-save/target-episode-supportへ保存。cleanと全未対応equipmentを別々に保持。
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
|9|sensor|8984–8990|3|4|0|1|no_candidate_in_window|0|

## cycle09温度欠測の原窓

sensor spike[8984,8987)、matching window 8984–8990。先頭は全候補閾値超過/streak1→次3行current quality不能でreset→さらに1行previous quality不能→最後2行閾値未満/streak0。3利用可4不能/phase不能0/maxstreak1でpersistence2不成立、candidate0/no_candidate_in_window/causalfalse/matchednull/delaynull。欠測なし等の反実仮想再compute0。
原3候補event/incident/全対象7行を-save/cycle09-sensor-missへ保存。C2原peer120行と温度current/previous品質不能40sample集合の一致を-save/peer-quality-propagationへ保存。
|sample|C0 score|C1 score|C2 score|reason|
|---|---|---|---|---|
|8984|68.6812004960617|148.54228550629463|154.52028281897776|None|
|8985|None|None|None|current_target_quality|
|8986|None|None|None|current_target_quality|
|8987|None|None|None|current_target_quality|
|8988|None|None|None|previous_target_quality_or_nonfinite|
|8989|0.46786471468433466|1.1598229299568326|1.0525764133142872|None|
|8990|0.18747822117074184|0.4500280186335995|0.6455832574939439|None|

## 同layout core保存指標との比較

|stratum|candidate|machine|sensor|precision|clean|
|---|---|---|---|---|---|
|core|c0-diff-control|0/10|0/10|0/1|1|
|core|c1-phase-level|10/10|10/10|20/20|0|
|core|c2-phase-conditional|10/10|10/10|20/20|0|
|quality-stress|c0-diff-control|0/10|0/10|0/1|1|
|quality-stress|c1-phase-level|10/10|9/10|19/19|0|
|quality-stress|c2-phase-conditional|10/10|9/10|19/19|0|

旧layout5coreはmanifest/config保存指標だけ比較・再compute0。同seed/layoutの別stratumで観測quality等のinputは異なり、独立新seedや欠測だけの反実仮想全差証明ではない。C1/C2の一部集計一致は全score/episode一致や候補採択の証明へしない。
C0対象窓の最大連続超過は1以下で、固定persistence2は成立していない。欠測温度1窓だけで全20未検出を説明しない。原窓・対象supportと未検出delaynullを保存し、検出を閾値・GT・matching変更で補わない。入力対応・保存・状態分類の実経路不具合は観測なし。全用途不適合や包括的実装認証へしない。

## 証拠・次工程・正式状態

- 新 representative-seed2-layout5-quality-three-candidates-20261013-records/analysis/save/finalを優先。DATA2 {"D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout5-quality-c0-c1-20261013": {"bytes": 41897925, "files": 22, "manifest_pin": {"bytes": 2592, "sha256": "adb927396b4e6d050321e37e5ee06787f935a85947a54558c1051fc3529cf5b1"}}, "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout5-quality-c2-20261013": {"bytes": 38238127, "files": 19, "manifest_pin": {"bytes": 2255, "sha256": "e62e89ae0f46b33090e772383144b30f81873f78b837ea36f212b671ab7622ed"}}}。原profiles/scores/events/incidents/episodes/metricsを保存、全20ledger/対象窓/全不能を-analysisに保存。
- 旧105cellモデル再compute0、第1seed72＋第2seed36＝108boardcells/使用seed2、108独立datasetではない。第2seed layout0–5全6cell比較完成。bootstrap/統計CI/勝者採択0。
- 旧510root/455helpers24failed431passedmissingexecution1と全失敗・審査拒否・原誤記を保持。今回新helperfailure0/閉鎖外部固定root追記0/PID単独/native回収claim0。
- report/handoff/index3docs一回[skip ci] commit/push、prepare_result_index実使用。人の具体的通知後の同送信先同種合成dev報告・ユーザー名入りPC内pathの継続送信承認に従う。
- 次同seed/layout6 core、groups [["c0-diff-control", "c1-phase-level"], ["c2-phase-conditional"]] / IDs ["dev-seed7466813550306735603-layout6-core-c0-c1-20261013", "dev-seed7466813550306735603-layout6-core-c2-20261013"]。chunk018 manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\018\attempt-0001\result\payload\manifest.json / {"bytes": 75699, "sha256": "a8a883a6e85a16f1ae8f152ea3b730252802b186b86df448944d6ea4f3ad0b9f"}、identity/input10metadataのみ選択、次本文未読/model0。
- EvidenceStore全writepreflight/自動分割/失敗閉鎖reserveを維持。実行900秒/2GiB/output1GiB/single32MiB/files32、Git30秒/16entry/512KiB/stdout1MiB/stderr128KiBとnativeprotocol caps不変。checkpoint≠blocking中断/fullruntime/allwriter/globalmemory容量認証。
- ACTIVE/automation詳細転記0、新testCIagent0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件最終受入未完了/create_native早期拒否/全7役reader禁止/元capsunknown owner保持。Sol容量または人停止は保全後PAUSED。
