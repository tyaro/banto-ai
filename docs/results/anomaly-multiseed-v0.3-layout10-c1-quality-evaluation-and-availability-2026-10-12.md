# layout10 C1 quality-stress実評価・欠測とphase除外の重なり（2026-10-12）

同保存dev quality-stressを既存CLI C1で一回fresh評価。exit0/complete/1cell success。機械10/10・sensor9/10・precision19/19・clean誤警報0。検出19件のdelay全1秒、未検出1件は原null。処理successや単一合成dev結果を性能保証・採択・正式受入へしない。

## 入力と原結果の対応

- run dev-layout10-quality-c1-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-10-quality-stress。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\010\attempt-0001\result\payload\manifest.json、pin {"bytes": 75715, "sha256": "1ede2721456af4d88ae82d606decb08b3e8fb2121295e9aea89ffddeda0b0c63"}。
- seed2486912926863618161/layout10/quality-stress/dev。input10 pins→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics。
- 元生成candidate C0/実評価candidate C1は別field。元payload書込み/生成/replay/追加agent0。
- actual checkout 5326e9a5ff8f7672491651cba5b45497ccafaa48、計算661b27511826fcc87cb4a02930f276afbb8f95d9不変。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 28.430985099985264秒/privatepeak 150470656B。
- observations {"bytes": 9600486, "sha256": "3ee44d2690972cc664dc9f9e5b380e3ae8fbdd79863096b2a9040f5a8d790834"}、configuration {"bytes": 5513, "sha256": "848b0893cd807b8c1646deedd075d868cc85f99b2a621d9cf2c142b499f10a57"}、manifest {"bytes": 8037, "sha256": "83e1e66297ccc5c9831d9154d1b906f44c326cbe7663d042606be5175528d680"}、evaluation {"bytes": 14512319, "sha256": "35b30a074cf7eb4f290f3407e319bbab1a2f7b47ed756a4b8f49473199543148"}。
- candidate thresholds {"c0-diff-control": 4.0, "c1-phase-level": 6.0, "c2-phase-conditional": 6.0}。C1 threshold6/operator>/persistence2を全14400scoreの原flagと照合。GT/matching/config/science変更0。
- declared16/candidate/compiledconfig一致はfull loaded runtime/native認証ではない。

## 原指標

| 指標 | 原値 |
| --- | --- |
| machine recall | 10/10 |
| sensor recall | 9/10 |
| precision | 19/19 |
| clean_rate | 0/3365、原value 0.0 |
| effective clean | 3254秒、原value 0.0 |
| burden | 0/20、原value 0.0 |
| delay | 検出count19/min-max-mean-median全1秒、未検出null |

48calibrated/fit600/calibration290/C2stateなし48、source29/equipment19/events40/incidents20。source内訳 {"conveyor-01.conveyor_speed": 10, "conveyor-01.vibration_feature": 10, "conveyor-01.motor_temperature": 9}、matched equipment所属 {"machine": {"conveyor-01.conveyor_speed": 10, "conveyor-01.vibration_feature": 10}, "sensor": {"conveyor-01.motor_temperature": 9}}。source29の全件がequipment19に所属。source数を誤警報数やprecision母数へしない。全equipment matched/clean0/未対応0。

## 欠測と利用不能行

18000observations/maskの対応と非ok観測30行を確認。全不能score/residual null・threshold_exceeded false。
phase tag480とquality primary40の重なり9を原scoreタグで確認。排他的primaryはphase471＋current quality30＋previous quality10＝511。core13920/480→quality13889/511、利用可能の減少は40−9＝31。phaseタグ480とprimary471を混同せず、重複を加算しない。
非排他的tags {"current_nonfinite": 30, "current_target_quality": 30, "mode_recipe_or_phase": 480, "previous_target_quality_or_nonfinite": 30}。current quality/nonfinite/previous qualityの重なりも独立行へ加算しない。
同layout10 C1 coreの保存sensor10/10に対してquality9/10。共通input pin ["origins.json", "split-manifest.json", "targets.json"]、fingerprintを含む他7入力pinは差。同seed/layoutを同一入力と扱わず旧model再計算0。

## sensor未検出1件の原窓

cycle09/conveyor-01.motor_temperature、event interval [8961,8964)/window end 8967。8961 score 161.71914093299674/streak1→8962–8964 current quality不能/8965 previous quality不能でreset→8966 score 2.019948261617119/streak0。threshold6/persistence2の第二超過が成立せず、原candidate0/no_candidate_in_window/causalfalse/matchednull/delaynull。

| sample | available | score | streak | primary reason |
| --- | --- | --- | --- | --- |
| 8959 | True | 0.41447082553722686 | 0 | None |
| 8960 | True | 0.7583502426564577 | 0 | None |
| 8961 | True | 161.71914093299674 | 1 | None |
| 8962 | False | None | 0 | current_target_quality |
| 8963 | False | None | 0 | current_target_quality |
| 8964 | False | None | 0 | current_target_quality |
| 8965 | False | None | 0 | previous_target_quality_or_nonfinite |
| 8966 | True | 2.019948261617119 | 0 | None |
| 8967 | True | 1.13077520570599 | 0 | None |
| 8968 | True | 1.692477232236185 | 0 | None |
| 8969 | True | 0.5713047199082516 | 0 | None |
| 8970 | False | None | 0 | mode_recipe_or_phase |

検出19件のtarget onsetは全start+1000ms/support2。検出窓各7rows利用可/maxstreak3、miss窓利用3不能4/maxstreak1。原20event/incident・19targetlinks・全窓・episodes・不能511・非ok30とphase-quality重複9原scoresを新analysis/-saveへ保存。入力対応・保存・状態分類の実経路不具合観測なし。

## 保存済みC1比較

| layout | stratum | machine | sensor | precision | clean | delay count | delay median |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 19 | 2.0 |
| 1 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 19 | 1.0 |
| 2 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 19 | 1.0 |
| 3 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 19 | 1.0 |
| 4 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 19 | 2.0 |
| 5 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 19 | 1.0 |
| 6 | quality-stress | 0/10 | 9/10 | 9/19 | 0 | 9 | 1.0 |
| 7 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 19 | 1.0 |
| 8 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 19 | 2.0 |
| 9 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 19 | 1.0 |
| 10 | core | 10/10 | 10/10 | 20/20 | 0 | 20 | 1.0 |
| 10 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 19 | 1.0 |

過去10layouts C1quality＋同layout10 C1core＋今回の12cellを保存指標で比較。C1quality11layouts。旧63board＋新1＝64完了、layout0–9全60＋layout10core全3/qualityC1完成。同seed1/64独立datasetではない。旧model/replay/試験/CI反復0、bootstrap/統計CI/勝者/採択0。

## 保存・過去の失敗・次unit

- model artifacts/representative-layout10-quality-c1-20261012-records、analysis ...-analysis、docs/Git ...-save、最終 ...-final/root-closed.json post-save label優先。
- selected-windows {"bytes": 1037821, "parts": 4}、matched-targets {"bytes": 64059, "parts": 1}、unavailable-scores {"bytes": 509812, "parts": 2}、non-ok-input-records {"bytes": 22104, "parts": 1}。
- DATA artifacts/representative-anomaly-evaluation/dev-layout10-quality-c1-20261012/root-closed.json、{"bytes": 27560106, "files": 19, "manifest_pin": {"bytes": 2236, "sha256": "75822eece17caa2c7e498e131b3d1df55bde3d30e901a5d82d2de134b49eb3e2"}}。
- 過去layout9のfingerprint共通pin誤要求のfailed script/live/execution/failureを保持。今回は共通3pinの訂正済み期待で新analysisを一回完了し、過去失敗を上書き/再実行0。C0設計3点/end-exclusive訂正版・過去source前処理失敗も保持。
- 次は同quality-stress C2、新ID dev-layout10-quality-c2-20261012。同manifest1ede/input10、本文C1読取済み/次model未実行、元生成C0/次評価C2別field。

prepare_result_indexを実使用し、handoff/report/index3文書を継続送信承認内で一回[skip ci] commit/push。原Git返値/pins/HEAD-upstream-remote-cleanは-save/-finalへ保存。
実行900秒2GiB/output1GiB/single32MiB/files32、Git30秒16entry512KiB/stdout1MiBstderr128KiB、protocol/native不変。検証16MiB512files/part256KiB/失敗予備枠維持。closed/frozen root追記整理0/fullstdio-native回収claim0。
ACTIVE/automation詳細転記0。CI381385/4130再照会downloadverifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了/create_native早期拒否/7役reader禁止/追加agent禁止/caps-unknown原owner保持。未完了formal/nativeをdev開始条件へ戻さない。Sol容量/人停止は原保全後PAUSED、重複再試行なし。
