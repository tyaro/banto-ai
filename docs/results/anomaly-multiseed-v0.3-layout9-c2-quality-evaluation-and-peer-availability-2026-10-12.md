# layout9 C2 quality-stress実評価・peer入力欠測の波及（2026-10-12）

同保存dev quality-stressを既存CLI C2で一回fresh評価。exit0/complete/1cell success。機械10/10・sensor9/10・precision19/19・clean誤警報0。検出19件のdelayは全1秒、未検出1件のdelayは原null。単一合成dev seedの結果や処理successを性能保証・採択・正式受入へしない。

## 入力と結果の対応

- run dev-layout9-quality-c2-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-09-quality-stress。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\009\attempt-0001\result\payload\manifest.json、pin {"bytes": 75699, "sha256": "7a71c5434cc8f526ada42d7a3f885bf711cabc256a7ff891c95a8969c6c58e5c"}。
- seed2486912926863618161/layout9/quality-stress/dev。input10 pins→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics。同C1 quality input10 pins一致。元生成candidate C0/実評価candidate C2を別field保持。
- 元payload書込み/生成/replay/追加agent0。actual checkout 5a237e27d8633c1c882562436e26eab58bb4a10a、計算661b27511826fcc87cb4a02930f276afbb8f95d9不変。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 24.333815700025298秒/privatepeak 210329600B。
- observations {"bytes": 9600605, "sha256": "366e4318ea59c94eadd2ffed97b5f5cfb2d235f9c89b28064f5f8adde2a9e184"}、configuration {"bytes": 5518, "sha256": "45efc5ddfc3583dd126111f150e1e5939b8d0b925e444548a0c0143105b1a95c"}、manifest {"bytes": 8041, "sha256": "10a107435d9441ab6ca9708cdd9401c5b87d14104c1bd8417fb4dbd6f0f459e9"}、evaluation {"bytes": 25210650, "sha256": "859e813df77cd31d1f66a7f531b67eb149f138ce8601b68e9189afb37f70cb1e"}。
- 保存configurationの閾値 {"c0-diff-control": 4.0, "c1-phase-level": 6.0, "c2-phase-conditional": 6.0}。今回C2 threshold 6.0/operator >/persistence 2。全14400scoreのthreshold_exceededを実6.0へ照合。GT/matching/config/science変更0。declared16/config一致はfull loaded runtime/native認証ではない。

## 原指標

| 指標 | 原値 |
| --- | --- |
| machine recall | 10/10 |
| sensor recall | 9/10 |
| precision | 19/19 |
| clean_rate | 0/3365、原value 0.0 |
| effective clean | 3255秒、原value 0.0 |
| burden | 0/20、原value 0.0 |
| detected delay | count19、min/max/mean/median全1秒。未検出はnull |

48calibrated/fit samples各600/calibration各290/C2 stateあり48、14400scores。source52/equipment19/events40/incidents20。source内訳 {"conveyor-01.conveyor_speed": 19, "conveyor-01.vibration_feature": 10, "conveyor-01.motor_current": 9, "conveyor-01.motor_temperature": 14}、matched equipment所属 {"machine": {"conveyor-01.conveyor_speed": 10, "conveyor-01.vibration_feature": 10, "conveyor-01.motor_temperature": 5}, "sensor": {"conveyor-01.conveyor_speed": 9, "conveyor-01.motor_current": 9, "conveyor-01.motor_temperature": 9}}。source52は全件equipment19へ所属。C1 qualityのsource29→C2 52の増分23を誤警報23やprecision母数へ変換しない。C2 coreのsource55との違いも原値で保持。全equipment19 matched/clean0/未対応0。

## 欠測とpeer入力の波及

18000observations/mask対応、非ok観測30行。score利用可能13760/不能640。排他的primaryはphase480＋peer120＋current quality30＋previous quality10。重複tag {"current_nonfinite": 30, "current_target_quality": 30, "mode_recipe_or_phase": 480, "peer_quality_or_nonfinite": 120, "previous_target_quality_or_nonfinite": 30} を独立行として加算しない。全不能score/residual null・threshold_exceeded false。
温度自身current quality30＋previous quality10に加え、同conveyor-01のmotor_current/conveyor_speed/vibration_featureが各40行peer不能。計120行の原peer scoreを別labelへ保存。C2 core13920/480からquality13760/640へ160行減少、同C1 quality13880/520から120行減少。
core/quality共通input pinは ["origins.json", "split-manifest.json", "targets.json"]。fingerprintを含む他7入力pinは異なる。同quality C1/C2はinput10全一致。旧モデル再計算0。

| target | primary unavailable |
| --- | --- |
| conveyor-01.conveyor_speed | {"mode_recipe_or_phase": 60, "peer_quality_or_nonfinite": 40} |
| conveyor-01.motor_current | {"mode_recipe_or_phase": 60, "peer_quality_or_nonfinite": 40} |
| conveyor-01.motor_temperature | {"current_target_quality": 30, "mode_recipe_or_phase": 60, "previous_target_quality_or_nonfinite": 10} |
| conveyor-01.vibration_feature | {"mode_recipe_or_phase": 60, "peer_quality_or_nonfinite": 40} |
| motor-01.conveyor_speed | {"mode_recipe_or_phase": 60} |
| motor-01.motor_current | {"mode_recipe_or_phase": 60} |
| motor-01.motor_temperature | {"mode_recipe_or_phase": 60} |
| motor-01.vibration_feature | {"mode_recipe_or_phase": 60} |

## sensor未検出1件と同equipment peer原窓

cycle09/conveyor-01.motor_temperature、event sample8924–8927/window end8930。8924 temperature116.95485164961896/current9.407477805506149/speed7.986745183570076は各streak1。8925–8927温度current quality不能、8928温度previous quality不能。3peer targetも8925–8928すべてpeer不能/null/streak0でreset。8929温度1.8239345202892916/streak0。
固定threshold6/persistence2の第二超過を満たさず、candidate0/no_candidate_in_window/causal_detected false/matchednull/delaynull。温度対象窓は利用可能3/不能4/maxstreak1。未検出を成功やdelay0へ補わない。

| sample | target | available | score | streak | primary reason |
| --- | --- | --- | --- | --- | --- |
| 8924 | conveyor-01.motor_current | True | 9.407477805506149 | 1 | None |
| 8924 | conveyor-01.motor_temperature | True | 116.95485164961896 | 1 | None |
| 8924 | conveyor-01.conveyor_speed | True | 7.986745183570076 | 1 | None |
| 8924 | conveyor-01.vibration_feature | True | 0.5857223648017066 | 0 | None |
| 8925 | conveyor-01.motor_current | False | None | 0 | peer_quality_or_nonfinite |
| 8925 | conveyor-01.motor_temperature | False | None | 0 | current_target_quality |
| 8925 | conveyor-01.conveyor_speed | False | None | 0 | peer_quality_or_nonfinite |
| 8925 | conveyor-01.vibration_feature | False | None | 0 | peer_quality_or_nonfinite |
| 8926 | conveyor-01.motor_current | False | None | 0 | peer_quality_or_nonfinite |
| 8926 | conveyor-01.motor_temperature | False | None | 0 | current_target_quality |
| 8926 | conveyor-01.conveyor_speed | False | None | 0 | peer_quality_or_nonfinite |
| 8926 | conveyor-01.vibration_feature | False | None | 0 | peer_quality_or_nonfinite |
| 8927 | conveyor-01.motor_current | False | None | 0 | peer_quality_or_nonfinite |
| 8927 | conveyor-01.motor_temperature | False | None | 0 | current_target_quality |
| 8927 | conveyor-01.conveyor_speed | False | None | 0 | peer_quality_or_nonfinite |
| 8927 | conveyor-01.vibration_feature | False | None | 0 | peer_quality_or_nonfinite |
| 8928 | conveyor-01.motor_current | False | None | 0 | peer_quality_or_nonfinite |
| 8928 | conveyor-01.motor_temperature | False | None | 0 | previous_target_quality_or_nonfinite |
| 8928 | conveyor-01.conveyor_speed | False | None | 0 | peer_quality_or_nonfinite |
| 8928 | conveyor-01.vibration_feature | False | None | 0 | peer_quality_or_nonfinite |
| 8929 | conveyor-01.motor_current | True | 0.11496151179169285 | 0 | None |
| 8929 | conveyor-01.motor_temperature | True | 1.8239345202892916 | 0 | None |
| 8929 | conveyor-01.conveyor_speed | True | 1.066649141676816 | 0 | None |
| 8929 | conveyor-01.vibration_feature | True | 0.6524307199211712 | 0 | None |
| 8930 | conveyor-01.motor_current | True | 0.6595252076816429 | 0 | None |
| 8930 | conveyor-01.motor_temperature | True | 1.1270927988251052 | 0 | None |
| 8930 | conveyor-01.conveyor_speed | True | 1.3168505523742802 | 0 | None |
| 8930 | conveyor-01.vibration_feature | True | 0.8029208562081962 | 0 | None |

検出19件は全target onset start+1000ms/support2。機械10・sensor9のtarget full_target/source-equipment-event対応を確認。検出19窓は各7rows全利用可/maxstreak3。全20event/incident・19targetlinks・四target窓・全episodes・不能640・非ok30を新analysisへ保存。入力対応・保存・状態分類の実経路不具合観測なし。

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
| 9 | core | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 20 | 1.0 |
| 9 | quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 19 | 1.0 |
| 9 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 19 | 1.0 |

過去9layouts C2 quality＋同layout9 C2 core/C1 quality＋今回の12cellを保存指標で比較。C2 quality10layouts、旧58board＋今回1=59完了。同合成dev seed1/59独立datasetではない。layout0–8全54＋layout9 core全3/qualityC1/C2完成、qualityC0は未実行。旧model/replay/試験/CI反復0、bootstrap/統計CI/勝者/採択0。

## 保存と次unit

- model artifacts/representative-layout9-quality-c2-20261012-records、分析 ...-analysis、docs/Git ...-save、最終 ...-final/root-closed.json post-save label優先。
- selected-windows {"bytes": 1786948, "parts": 7}、matched-targets {"bytes": 68492, "parts": 1}、unavailable-scores {"bytes": 1113090, "parts": 5}、non-ok-input-records {"bytes": 22028, "parts": 1}。peer120は-save/peer-unavailable-scores label。
- DATA artifacts/representative-anomaly-evaluation/dev-layout9-quality-c2-20261012/root-closed.json、{"bytes": 38258217, "files": 19, "manifest_pin": {"bytes": 2235, "sha256": "43c33a82c9da9642858212ac1a3fbd2e44ccf44c52122affa1ec7128e7c380b4"}}。
- 次は同quality-stress C0、新ID dev-layout9-quality-c0-20261012。同manifest7a71/input10、本文C1/C2読取済み/次model未実行、元生成C0/次評価C0のfieldは別に保持。

prepare_result_indexを実使用し、handoff/report/index3文書を継続送信承認内で一回[skip ci] Git保存。原返値/pins/HEAD-upstream-remote-cleanは-save/-final保存。C1分析の旧fingerprint期待誤り/原failed/訂正continuationは保持し、今回successへ書き換えない。今回helper failure0。
実行900秒2GiB/output1GiB/single32MiB/files32、Git30秒16entry512KiB/stdout1MiBstderr128KiB、protocol/native不変。新検証16MiB512files/part256KiB/失敗予備枠維持。closed/frozen root追記整理0/fullstdio-native回収claim0。
ACTIVE/automation詳細転記0。CI381385/4130再照会downloadverifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了/create_native早期拒否/7役reader禁止/追加agent禁止/caps-unknown原owner保持。未完了formal/nativeをdev開始条件へ戻さない。Sol容量/人停止は原保全後PAUSED、重複再試行なし。
