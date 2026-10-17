# layout9 C1 quality-stress実評価・欠測による未検出（2026-10-12）

同保存dev quality-stressを既存CLI C1で一回fresh評価。exit0/complete/1cell success。機械10/10・sensor9/10・precision19/19・clean誤警報0。検出19件のdelayは全1秒、未検出1件のdelayは原null。単一合成dev seedの結果や処理successを性能保証・採択・正式受入へしない。

## 入力と結果の対応

- run dev-layout9-quality-c1-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-09-quality-stress。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\009\attempt-0001\result\payload\manifest.json、pin {"bytes": 75699, "sha256": "7a71c5434cc8f526ada42d7a3f885bf711cabc256a7ff891c95a8969c6c58e5c"}。
- seed2486912926863618161/layout9/quality-stress/dev。input10 pins→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics。元生成candidate C0/実評価candidate C1を別field保持。
- 元payload書込み/生成/replay/追加agent0。actual checkout c78e574861ca1345f22f1012fb9a050c2d6f36b6、計算661b27511826fcc87cb4a02930f276afbb8f95d9不変。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 16.1925135999918秒/privatepeak 150507520B。
- observations {"bytes": 9600605, "sha256": "366e4318ea59c94eadd2ffed97b5f5cfb2d235f9c89b28064f5f8adde2a9e184"}、configuration {"bytes": 5512, "sha256": "e6205c36f7369d283b00efd93afdedf5a30b8e7ac01e6d100399c282ec275ad3"}、manifest {"bytes": 8033, "sha256": "e5ed4c5bad756e2adf3b951300b0eb58e3c22dfa7752af9f82805da64d0972de"}、evaluation {"bytes": 14511914, "sha256": "67bacfe71783f9aa21fac6fdfc2dfea1e407be337df44ee047d672b4e197a720"}。
- 保存configurationから閾値 {"c0-diff-control": 4.0, "c1-phase-level": 6.0, "c2-phase-conditional": 6.0}。今回C1 threshold 6.0/operator >/persistence 2。全14400scoreのthreshold_exceededを実6.0へ照合。GT/matching/config/science変更0。
- declared16/candidate/compiled config一致はfull loaded runtime/native認証ではない。

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

48calibrated/fit samples各600/calibration各290/C2 stateなし48、14400scores。source29/equipment19/events40/incidents20。source内訳 {"conveyor-01.conveyor_speed": 10, "conveyor-01.vibration_feature": 10, "conveyor-01.motor_temperature": 9}、matched equipment所属 {"machine": {"conveyor-01.conveyor_speed": 10, "conveyor-01.vibration_feature": 10}, "sensor": {"conveyor-01.motor_temperature": 9}}。source29の全件はequipment19に所属し、source数をprecision母数や誤警報数へ変換しない。全equipment19 matched/clean0/未対応0。

## 欠測と利用不能行

18000observations/maskの原対応を確認し、非ok観測30行。score利用可能13880/不能520。排他的primaryはphase480＋current quality30＋previous quality10。重複tagは {"current_nonfinite": 30, "current_target_quality": 30, "mode_recipe_or_phase": 480, "previous_target_quality_or_nonfinite": 30} で、current quality/nonfinite/previous qualityの重なりを独立行へ加算しない。全不能score/residual null・threshold_exceeded false。
同layout9 C1 coreの保存指標13920/480からqualityは利用可能40減少。coreのsensor10/10に対してquality9/10。共通input pinは ["origins.json", "split-manifest.json", "targets.json"]。fingerprintを含む他7入力pinは異なり、同seed/layoutでもcoreとqualityを同一入力として扱わない。旧モデル再計算0。

## sensor未検出1件の原窓

cycle09/conveyor-01.motor_temperature、event sample8924–8927/window end8930。8924はscore122.17455879425036/streak1、8925–8927 current quality不能、8928 previous quality不能でstreak0へreset。8929はscore1.8520087533806118/streak0。閾値6/persistence2の第二超過を満たさず、原candidate0/no_candidate_in_window/causal_detected false/matchednull/delaynull。未検出を成功やdelay0へ補わない。

| sample | available | score | streak | primary reason |
| --- | --- | --- | --- | --- |
| 8922 | True | 0.3858333908648343 | 0 | None |
| 8923 | True | 0.5772338182153808 | 0 | None |
| 8924 | True | 122.17455879425036 | 1 | None |
| 8925 | False | None | 0 | current_target_quality |
| 8926 | False | None | 0 | current_target_quality |
| 8927 | False | None | 0 | current_target_quality |
| 8928 | False | None | 0 | previous_target_quality_or_nonfinite |
| 8929 | True | 1.8520087533806118 | 0 | None |
| 8930 | True | 1.1740770094132578 | 0 | None |
| 8931 | True | 1.4203636440269838 | 0 | None |
| 8932 | True | 0.7164915780085538 | 0 | None |
| 8933 | True | 0.6423774730870725 | 0 | None |

検出19件は全target onset start+1000ms/support2。機械10・sensor9のtarget full_target/source-equipment-event対応を原ledgerで確認。検出19対象窓は各7rows全利用可/maxstreak3、未検出窓は利用可能3/不能4/maxstreak1。原全20event/incident・19targetlinks・四target窓・全episodes・不能520・非ok30を新analysis-continuationへ保存。入力対応・保存・状態分類の実経路不具合観測なし。

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
| 9 | core | 10/10 | 10/10 | 20/20 | 0 | 20 | 1.0 |
| 9 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 19 | 1.0 |

過去9layouts C1 quality＋同layout9 C1 core＋今回の11cellを保存指標で比較。C1 quality10layouts、旧57board＋今回1=58完了。同合成dev seed1/58独立datasetではない。layout0–8全54＋layout9 core全3/qualityC1が完成。旧model/replay/試験/CI反復0、bootstrap/統計CI/勝者/採択0。

## 分析補助scriptの失敗保全

初回analysisはcore/qualityのfingerprintも一致するとの誤要求でAssertionError。原script/helper-live/execution/analysis.failure/tracebackを failed rootへ閉鎖保存。原失敗をモデル/CI/native/Sol容量failureへ読み替えない。
別analysis-continuationで当該文字列だけを訂正し、保存された実入力pinの共通3項目を確認して未保存分析を完成。元helper/モデル再実行0、failed状態の書換え0。継続記録のprior-analysis-failureに原failureと閉鎖pinを保持。

## 保存と次unit

- model artifacts/representative-layout9-quality-c1-20261012-records、原failed ...-analysis、分析 ...-analysis-continuation、docs/Git ...-save、最終 ...-final/root-closed.json post-save label優先。
- selected-windows {"bytes": 1033898, "parts": 4}、matched-targets {"bytes": 63850, "parts": 1}、unavailable-scores {"bytes": 518559, "parts": 2}、non-ok-input-records {"bytes": 22022, "parts": 1}。
- DATA artifacts/representative-anomaly-evaluation/dev-layout9-quality-c1-20261012/root-closed.json、{"bytes": 27559449, "files": 19, "manifest_pin": {"bytes": 2235, "sha256": "96e172b8e08bce395cf3bad14ff1f4e4446dfef18de3e04308ebf0e638978ce6"}}。
- 次は同quality-stress C2、新ID dev-layout9-quality-c2-20261012。同manifest7a71/input10、本文C1読取済み/次model未実行、元生成C0/次評価C2別field。

prepare_result_indexを実使用し、handoff/report/index3文書を継続送信承認内で一回[skip ci] Git保存。原返値/pins/HEAD-upstream-remote-cleanは-save/-final保存。
実行900秒2GiB/output1GiB/single32MiB/files32、Git30秒16entry512KiB/stdout1MiBstderr128KiB、protocol/native不変。新検証16MiB512files/part256KiB/失敗予備枠維持。closed/frozen root追記整理0/fullstdio-native回収claim0。
ACTIVE/automation詳細転記0。CI381385/4130再照会downloadverifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了/create_native早期拒否/7役reader禁止/追加agent禁止/caps-unknown原owner保持。未完了formal/nativeをdev開始条件へ戻さない。Sol容量/人停止は原保全後PAUSED、重複再試行なし。
