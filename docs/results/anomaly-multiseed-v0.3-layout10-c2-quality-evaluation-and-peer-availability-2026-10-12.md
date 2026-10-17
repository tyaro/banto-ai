# layout10 C2 quality-stress実評価・peer欠測とphase除外の重なり（2026-10-12）

同保存dev quality-stressを既存CLI C2で一回fresh評価。exit0/complete/1cell success。機械10/10・sensor9/10・precision19/19・clean誤警報0。検出19件delay全1秒、未検出1件delay原null。単一合成dev結果や処理successを性能保証・採択・正式受入へしない。

## 入力と原結果の対応

- run dev-layout10-quality-c2-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-10-quality-stress。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\010\attempt-0001\result\payload\manifest.json、pin {"bytes": 75715, "sha256": "1ede2721456af4d88ae82d606decb08b3e8fb2121295e9aea89ffddeda0b0c63"}。
- seed2486912926863618161/layout10/quality-stress/dev。input10 pins→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics。同C1 quality input10全一致。
- 元生成candidate C0/実評価candidate C2は別field。元payload書込み/生成/replay/追加agent0。
- actual checkout afa4f6a37144a6e72209f075fe79ab63f123ca34、計算661b27511826fcc87cb4a02930f276afbb8f95d9不変。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 40.2200069000246秒/privatepeak 210563072B。
- observations {"bytes": 9600486, "sha256": "3ee44d2690972cc664dc9f9e5b380e3ae8fbdd79863096b2a9040f5a8d790834"}、configuration {"bytes": 5519, "sha256": "0c592d1604395a6e69b25f1043c354e9b1c8b60b024e338a91be214ccc7a21d5"}、manifest {"bytes": 8041, "sha256": "d0c98d5ac2992a28a25379fca7ef462755e5a1682c3654d0db16fdad212003e5"}、evaluation {"bytes": 25203008, "sha256": "d70500b1647d29bc008008cecae463b84d3efa98de902c4d109e7ebcae6194ba"}。
- thresholds {"c0-diff-control": 4.0, "c1-phase-level": 6.0, "c2-phase-conditional": 6.0}。C2 threshold6/operator>/persistence2を全14400score原flagへ照合。GT/matching/config/science変更0。declared16/config一致はfull loaded runtime/native認証ではない。

## 原指標

| 指標 | 原値 |
| --- | --- |
| machine recall | 10/10 |
| sensor recall | 9/10 |
| precision | 19/19 |
| clean_rate | 0/3365、原value 0.0 |
| effective clean | 3254秒、原value 0.0 |
| burden | 0/20、原value 0.0 |
| detected delay | count19/min-max-mean-median全1秒。未検出null |

48calibrated/fit600/calibration290/C2stateあり48、source46/equipment19/events40/incidents20。source内訳 {"conveyor-01.conveyor_speed": 10, "conveyor-01.vibration_feature": 19, "conveyor-01.motor_current": 8, "conveyor-01.motor_temperature": 9}、matched equipment所属 {"machine": {"conveyor-01.conveyor_speed": 10, "conveyor-01.vibration_feature": 10}, "sensor": {"conveyor-01.motor_current": 8, "conveyor-01.motor_temperature": 9, "conveyor-01.vibration_feature": 9}}。source46の全件がequipment19へ所属。C1 quality source29→C2 46の増分17を誤警報17やprecision母数へ変換しない。C2core source49との差3も原値保持。全equipment19 matched/clean0/未対応0。

## 欠測とpeer入力の波及

18000observations/mask対応、非ok30。score利用可能13796/不能604。全不能score/residual null・threshold_exceeded false。
phase tag480、温度自身quality primary40、peer tag120。温度qualityとphaseの重なり9、peerとphaseの重なり27を原scoreで保存し、不能480＋40＋120−9−27＝604。排他的primaryはphase471/current quality30/previous quality10/peer93。peer tag120をprimary93や追加不能93と混同しない。
同conveyor-01のmotor_current/conveyor_speed/vibration_featureは各40peerタグ、各31primary peer除外、各9phaseと重なる。C2core13920/480→quality13796/604は124減少、C1quality13889/511からは93減少。非排他的tags {"current_nonfinite": 30, "current_target_quality": 30, "mode_recipe_or_phase": 480, "peer_quality_or_nonfinite": 120, "previous_target_quality_or_nonfinite": 30} を独立行へ加算しない。
core/quality共通input pin ["origins.json", "split-manifest.json", "targets.json"]、fingerprint含む他7差。同quality C1/C2はinput10全一致。旧model再計算0。

| target | primary unavailable |
| --- | --- |
| conveyor-01.conveyor_speed | {"mode_recipe_or_phase": 60, "peer_quality_or_nonfinite": 31} |
| conveyor-01.motor_current | {"mode_recipe_or_phase": 60, "peer_quality_or_nonfinite": 31} |
| conveyor-01.motor_temperature | {"current_target_quality": 30, "mode_recipe_or_phase": 51, "previous_target_quality_or_nonfinite": 10} |
| conveyor-01.vibration_feature | {"mode_recipe_or_phase": 60, "peer_quality_or_nonfinite": 31} |
| motor-01.conveyor_speed | {"mode_recipe_or_phase": 60} |
| motor-01.motor_current | {"mode_recipe_or_phase": 60} |
| motor-01.motor_temperature | {"mode_recipe_or_phase": 60} |
| motor-01.vibration_feature | {"mode_recipe_or_phase": 60} |

## sensor未検出1件とpeer原窓

cycle09/conveyor-01.motor_temperature、event interval [8961,8964)/window end 8967。8961 temperature 156.0873274122774/streak1→8962–8964 current quality不能/8965 previous quality不能でreset→8966 temperature 2.077727670127084/streak0。3peer targetも8962–8965は全peer不能/null/streak0。固定threshold6/persistence2不成立、candidate0/no_candidate_in_window/causalfalse/matchednull/delaynull。
原event startの各target score/streak [{"sample": 8961, "full_target": "conveyor-01.motor_current", "score": 7.361784086227646, "streak": 1}, {"sample": 8961, "full_target": "conveyor-01.motor_temperature", "score": 156.0873274122774, "streak": 1}, {"sample": 8961, "full_target": "conveyor-01.conveyor_speed", "score": 1.8065169146116222, "streak": 0}, {"sample": 8961, "full_target": "conveyor-01.vibration_feature", "score": 7.456169373089204, "streak": 1}]。speedは閾値を超えておらず、temperature/current/vibrationはstreak1。後続欠測で継続が成立しない。

| sample | target | available | score | streak | primary reason |
| --- | --- | --- | --- | --- | --- |
| 8961 | conveyor-01.motor_current | True | 7.361784086227646 | 1 | None |
| 8961 | conveyor-01.motor_temperature | True | 156.0873274122774 | 1 | None |
| 8961 | conveyor-01.conveyor_speed | True | 1.8065169146116222 | 0 | None |
| 8961 | conveyor-01.vibration_feature | True | 7.456169373089204 | 1 | None |
| 8962 | conveyor-01.motor_current | False | None | 0 | peer_quality_or_nonfinite |
| 8962 | conveyor-01.motor_temperature | False | None | 0 | current_target_quality |
| 8962 | conveyor-01.conveyor_speed | False | None | 0 | peer_quality_or_nonfinite |
| 8962 | conveyor-01.vibration_feature | False | None | 0 | peer_quality_or_nonfinite |
| 8963 | conveyor-01.motor_current | False | None | 0 | peer_quality_or_nonfinite |
| 8963 | conveyor-01.motor_temperature | False | None | 0 | current_target_quality |
| 8963 | conveyor-01.conveyor_speed | False | None | 0 | peer_quality_or_nonfinite |
| 8963 | conveyor-01.vibration_feature | False | None | 0 | peer_quality_or_nonfinite |
| 8964 | conveyor-01.motor_current | False | None | 0 | peer_quality_or_nonfinite |
| 8964 | conveyor-01.motor_temperature | False | None | 0 | current_target_quality |
| 8964 | conveyor-01.conveyor_speed | False | None | 0 | peer_quality_or_nonfinite |
| 8964 | conveyor-01.vibration_feature | False | None | 0 | peer_quality_or_nonfinite |
| 8965 | conveyor-01.motor_current | False | None | 0 | peer_quality_or_nonfinite |
| 8965 | conveyor-01.motor_temperature | False | None | 0 | previous_target_quality_or_nonfinite |
| 8965 | conveyor-01.conveyor_speed | False | None | 0 | peer_quality_or_nonfinite |
| 8965 | conveyor-01.vibration_feature | False | None | 0 | peer_quality_or_nonfinite |
| 8966 | conveyor-01.motor_current | True | 1.3894344243678685 | 0 | None |
| 8966 | conveyor-01.motor_temperature | True | 2.077727670127084 | 0 | None |
| 8966 | conveyor-01.conveyor_speed | True | 0.3710036341740231 | 0 | None |
| 8966 | conveyor-01.vibration_feature | True | 1.299628104159852 | 0 | None |
| 8967 | conveyor-01.motor_current | True | 1.4195389245722374 | 0 | None |
| 8967 | conveyor-01.motor_temperature | True | 0.9745062962277924 | 0 | None |
| 8967 | conveyor-01.conveyor_speed | True | 0.6851319377836058 | 0 | None |
| 8967 | conveyor-01.vibration_feature | True | 0.2642353452214535 | 0 | None |

検出19件のtarget onset全start+1000ms/support2。検出窓各7rows利用可/maxstreak3、miss温度窓利用3不能4/maxstreak1。全20event/incident・19targetlinks・全窓・episodes・不能604・非ok30を新analysisへ保存。入力対応・保存・状態分類の実経路不具合観測なし。

## 保存済みC2 quality・同layout core/C1 quality比較

| layout | stratum | candidate | machine | sensor | precision | clean | delay count | delay median |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | quality-stress | c2-phase-conditional | 4/10 | 9/10 | 13/19 | 0 | 13 | 1.0 |
| 1 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 19 | 1.0 |
| 2 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 19 | 1.0 |
| 3 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 19 | 1.0 |
| 4 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 19 | 2.0 |
| 5 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 19 | 1.0 |
| 6 | quality-stress | c2-phase-conditional | 0/10 | 9/10 | 9/19 | 0 | 9 | 1.0 |
| 7 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 19 | 1.0 |
| 8 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 19 | 2.0 |
| 9 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 19 | 1.0 |
| 10 | core | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 20 | 1.0 |
| 10 | quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 19 | 1.0 |
| 10 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 19 | 1.0 |

過去10layouts C2quality＋同layout10 C2core/C1quality＋今回の13cellを保存指標で比較。C2quality11layouts。旧64board＋新1＝65完了、layout0–9全60＋layout10core全3/qualityC1/C2完成、qualityC0未実行。同seed1/65独立datasetではない。旧model/replay/試験/CI反復0、bootstrap/統計CI/勝者/採択0。

## 保存と次unit

- model artifacts/representative-layout10-quality-c2-20261012-records、analysis ...-analysis、docs/Git ...-save、最終 ...-final/root-closed.json post-save label優先。
- selected-windows {"bytes": 1779841, "parts": 7}、matched-targets {"bytes": 67922, "parts": 1}、unavailable-scores {"bytes": 1051432, "parts": 5}、non-ok-input-records {"bytes": 22110, "parts": 1}。
- -save/peer-unavailable-scoresはprimary93、peer-tagged-scoresはtag120、phase-peer-overlap-scoresは重複27を原rowで別保存。
- DATA artifacts/representative-anomaly-evaluation/dev-layout10-quality-c2-20261012/root-closed.json、{"bytes": 38250823, "files": 19, "manifest_pin": {"bytes": 2236, "sha256": "fd3db4042e2e009fc71ef28608cb7d334800d0ee2a29cbbd71b4e96a77e72d22"}}。
- 次は同quality-stress C0、新ID dev-layout10-quality-c0-20261012。同manifest1ede/input10、本文C1/C2読取済み/次model未実行、元生成C0/次評価C0はfield別保持。

prepare_result_index実使用、handoff/report/index3文書を継続送信承認内で一回[skip ci] Git保存。原返値/pins/HEAD-upstream-remote-cleanは-save/-final保存。旧layout9 fingerprint期待失敗/C0設計3点訂正版・原failed/前回source前処理拒否を保持し、今回successへ書換え0。今回helper failure0。
実行900秒2GiB/output1GiB/single32MiB/files32、Git30秒16entry512KiB/stdout1MiBstderr128KiB、protocol/native不変。検証16MiB512files/part256KiB/失敗予備枠維持。closed/frozen root追記整理0/fullstdio-native回収claim0。
ACTIVE/automation詳細転記0。CI381385/4130再照会downloadverifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了/create_native早期拒否/7役reader禁止/追加agent禁止/caps-unknown原owner保持。未完了formal/nativeをdev開始条件へ戻さない。Sol容量/人停止は原保全後PAUSED、重複再試行なし。
