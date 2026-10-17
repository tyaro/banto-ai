# layout11 C0 core実評価（2026-10-12）

保存済みlayout11 coreを既存CLI C0で1回実評価した。処理はexit0/complete/1cell success。機械0/10、センサー1/10、precision1/3、正常区間の誤警報2件。処理完了を性能合格・採択・正式受入にしない。

## 入力と実行の対応

- run dev-layout11-core-c0-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-11-core。
- 元入力manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\011\attempt-0001\result\payload\manifest.json、pin {"bytes": 75714, "sha256": "ce20f3d40c4e286df89ac3fe4ae6411763fec86f573e9ca67073e2acf2e92177"}。
- seed2486912926863618161/layout11/core/dev。元10入力pin確認→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics保存。元payload書込み・新dataset生成・replay・追加agent0。
- 実checkout 474c16888aa668d547ed54ba8222ac3a1041803c、計算code661b27511826fcc87cb4a02930f276afbb8f95d9・science117・宣言calculator16は不変。固定candidate/compiled config一致。宣言pinはfull loaded runtime/native認証ではない。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 29.81805969995912秒、OS sampled private peak 150749184B。
- observations {"bytes": 9600597, "sha256": "d8ac35000efdd0b2de6f0205173d7a4a115567b89ff8cb0089cae77ab9736ef3"}、configuration {"bytes": 5504, "sha256": "78485f75e48ca1c4793458335290b02993e9339326c0045b517994b422c5f118"}、manifest {"bytes": 8043, "sha256": "954e4424e0b4a2e24c051cb0dab4a8d5ae92428e5702662dbb9d4822f80f8b5a"}、evaluation {"bytes": 13900461, "sha256": "1563d80ad0181d58abdb0ccce70678b8542467ec23778ea9e3c2629c76135342"}。
- configuration原値はC0閾値4.0、C1/C2閾値6.0、演算子>、persistence2。全14400scoreのthreshold_exceededをC0実値4.0へ照合した。GT・閾値・matching・科学式の変更0。

## 原指標と利用不能

|項目|今回の原値|
|---|---|
|機械 recall|0/10|
|センサー recall|1/10|
|precision|1/3|
|clean誤警報|2|
|source / equipment / incidents / events|3 / 3 / 20 / 40|
|scores 利用可 / 不能|13920 / 480|

48profilesは全calibrated、C0 fit_samples各0（定義上no-op）、calibration_samples各290、C2stateなし48。18000observations/quality-mask対応、non-ok入力0。不能480は全mode_recipe_or_phaseでscore/residual null・thresholdfalse。排他的理由と重複tagsを原記録で保持した。
検出1件だけdelay2秒（count1、min/max/mean/medianすべて2.0秒）。未検出19件はdelay nullで、集計へ代入しない。clean_rate 2/3365、原value 17.11738484398217、effective 3255秒 / 原rate 17.695852534562214。false_alert_burden 2/20 / 原value 10.0。rate/burdenの原valueを単純確率へ読み替えない。

## 検出1件の原対応

cycle02 sensor、conveyor-01.motor_temperature、固定加算8.0、原異常区間[7710,7713)（3観測）。開始7710はmode_recipe_or_phaseで不能、7711/7712は同cooldown profileで2連続閾値超過。原source episodeのonsetは7712、equipment episodeも同onset、event/target/support2scoreの対応を確認し、原matchingはcausal_detected=true / candidate1 / delay2秒だった。

|sample|available|score|streak|reason|
|---|---|---|---|---|
|7710|False|None|0|mode_recipe_or_phase|
|7711|True|4.204907244726188|1|None|
|7712|True|4.010680221818085|2|None|
|7713|True|101.35032786396381|3|None|
|7714|True|2.418437518765933|0|None|

この検出はC0の一定オフセット感度を示す証拠にはならない。C0は一次差分で、support7711/7712は同じ+8.0の区間内にあるため加算成分は差分で相殺される。今回の原残差は-0.410812 / -0.395047、score4.204907244726188 / 4.010680221818085で、フェーズ切替後の2点が閾値を超えてepisodeになっている。この説明は保存済み式と原窓からの推論で、正常対照の再計算や強い物理因果の証明はしていない。原matchingのcausal_detected=trueと原指標はそのまま保持する。
既存C0設計確認は ../results/anomaly-multiseed-v0.3-layout10-c0-core-evaluation-2026-10-12.md と artifacts/representative-layout10-core-c0-20261012-save のC0-design-review labelを参照。3観測/end-exclusiveが訂正版。旧four-sample誤記・初回analysis failureは原保存保持、再実行0。今回も既存baseline/閾値/persistenceを変更していない。

## 未検出19件・誤警報2件

機械10件とセンサー9件は全no_candidate_in_window / candidate0 / causalfalse / matchednull / delaynull。対象最大streakは全1。機械10窓は各7rows利用可、センサー10窓は各6rows利用可・開始1rowがphase不能。周期2以外では2連続閾値超過が成立しなかった。phase不能を全未検出の唯一の理由へしない。
例cycle00 sensorは7350 phase不能、7351 score3.8954376228785/streak0、7352 score3.6010848140412537/0、7353 score101.48172216775801/1、7354 score2.493060612819509/0。大きな差分1点だけでは固定persistence2を満たさなかった。
clean2件はmotor-01.vibration_feature、原onset sample7242と8517。原equipmentはclean tags / matchednull、原sourceとsupport scoresを新-saveのepisode-summaryへ保持。新source3/equipment3のうち1件だけ対象検出で、2件を欠落させない。原20event/incident、全4target窓、匹配source/equipment、全不能・全episodesは-analysisへ保存した。

## 保存済みC0 coreの比較

旧layout0–10 C0coreの保存manifest指標だけと今回layout11 C0coreを比較した。12 cellsのcalculator16/candidate config/compiled configは一致、同devseedで入力layout pinsが異なる。旧モデルの再計算0。

|layout|machine|sensor|precision|clean|
|---|---|---|---|---|
|0|0/10|0/10|0/3|3|
|1|0/10|0/10|0/3|2|
|3|0/10|0/10|0/3|3|
|4|0/10|0/10|0/3|3|
|5|0/10|0/10|0/3|3|
|6|0/10|0/10|0/3|3|
|2|0/10|0/10|0/3|3|
|7|0/10|0/10|0/3|3|
|8|0/10|0/10|0/3|3|
|9|0/10|0/10|0/3|3|
|10|0/10|0/10|0/3|3|
|11|0/10|1/10|1/3|2|

完成boardは旧66＋今回1＝67 cells。layout0–10の3候補×2strataは保存済み、layout11はC0coreのみ。同合成devseed1で、67独立datasetではない。bootstrap・統計CI・勝者・採択0。今回の1検出で従来の弱さを解消したと扱わない。

## 証拠保存・次unit・正式状態

- model artifacts/representative-layout11-core-c0-20261012-records、analysis artifacts/representative-layout11-core-c0-20261012-analysis、docs/Git artifacts/representative-layout11-core-c0-20261012-save、最終同-finalのpost-saveを優先。
- analysis項目のbytes/分割parts {"all-episodes": {"bytes": 4392, "parts": 1}, "analysis": {"bytes": 457787, "parts": 2}, "analysis.finished": {"bytes": 37, "parts": 1}, "analysis.started": {"bytes": 17, "parts": 1}, "data-closure": {"bytes": 135, "parts": 1}, "data-closure.finished": {"bytes": 37, "parts": 1}, "data-closure.started": {"bytes": 17, "parts": 1}, "helper-execution": {"bytes": 268, "parts": 1}, "helper-live": {"bytes": 213, "parts": 1}, "incident-ledger": {"bytes": 20301, "parts": 1}, "matched-targets": {"bytes": 3360, "parts": 1}, "non-ok-input-records": {"bytes": 190, "parts": 1}, "policy": {"bytes": 211, "parts": 1}, "script": {"bytes": 12509, "parts": 1}, "selected-windows": {"bytes": 948863, "parts": 4}, "unavailable-scores": {"bytes": 463420, "parts": 2}}。
- DATA artifacts/representative-anomaly-evaluation/dev-layout11-core-c0-20261012/root-closed.json / {"bytes": 26942312, "files": 19, "manifest_pin": {"bytes": 2226, "sha256": "68162ff084be512f4f42405fc1e4e443d4b29bdd8c8178203cf4444606a21631"}}。
- 共有EvidenceStoreの新記録16MiB/512files、part256KiB、失敗2MiB/16files・閉鎖512KiB/4files予備枠を維持。書込み前preflight・自動分割・原失敗保存。元closed/frozen root追記整理0。
- foregroundの補助読取りは原extractを表示した後、handoff表示のcp932出力でUnicodeEncodeErrorになった。原script/selected traceを新-saveへ保存、処理開始/モデル/Git/CI/native失敗に読み替えない。full process identity/stdioは未保存。原抽出/model/完成試験の再実行0。
- 直前docs helperのconsole next_layout=10誤記と訂正future sourceは原-final保存を保持。今回のnext_layout表示は保存identityから取得する。
- 実行900秒/2GiB/output1GiB/single32MiB/files32、Git累積30秒/16entry/512KiB/stdout1MiB/stderr128KiB、protocol/native上限不変。
- 指定report/handoff/indexの3文書を同種合成dev結果・PC内path送信継続承認の範囲で一回[skip ci] commit/push。HEAD/upstream/lsremote/clean・原Gitbytesは-save/-finalへ保存。新送信承認質問0/bypass0。
- 次は同保存layout11/core C1 c1-phase-level、新ID dev-layout11-core-c1-20261012。同manifest/input10、本文は今回C0で読取済み、次model未開始、生成candidate C0と実評価C1を別fieldへ保持。
- ACTIVE。CI381385/4130の完成保存は保持、今回CIquery/download/verifier/tests0。formal gate=s4_acceptance_not_frozen / formal_permission=false / credit0 / holdout未読 / 正式5残件・最終受入未完了。create_native早期拒否・全7役reader禁止・caps-unknown原owner保持・追加agent禁止を維持。未完了formal/nativeを少量devの新条件へ戻さない。Sol容量/人停止時は原保全後PAUSED、重複再試行なし。
