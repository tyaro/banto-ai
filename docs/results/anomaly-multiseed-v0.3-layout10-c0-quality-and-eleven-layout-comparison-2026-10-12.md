# layout10 C0 quality-stress実評価・11layouts×3候補×2条件比較（2026-10-12）

同保存dev quality-stressを既存CLI C0で一回fresh評価。exit0/complete/1cell success。機械0/10・sensor0/10・precision0/3・clean誤警報3。全20incident未検出、delay原null。処理successを性能合格・採択・正式受入へしない。同seedのlayout0–10で3候補×2条件の66cellが揃った。

## 入力と原結果の対応

- run dev-layout10-quality-c0-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-10-quality-stress。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\010\attempt-0001\result\payload\manifest.json、pin {"bytes": 75715, "sha256": "1ede2721456af4d88ae82d606decb08b3e8fb2121295e9aea89ffddeda0b0c63"}。
- seed2486912926863618161/layout10/quality-stress/dev。input10 pins→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics。同C1/C2 quality input10全一致。
- 元生成C0/実評価C0は別field。元payload書込み/生成/replay/追加agent0。actual checkout d207378ca8d3483433e798954d3f393747fae0dd、計算661b27511826fcc87cb4a02930f276afbb8f95d9不変。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 70.30588250001892秒/privatepeak 149819392B。
- observations {"bytes": 9600486, "sha256": "3ee44d2690972cc664dc9f9e5b380e3ae8fbdd79863096b2a9040f5a8d790834"}、configuration {"bytes": 5514, "sha256": "db3e9a267ce2c1fad07f99d067a2d9da098d113808b8e969d1cbfb80d7e3c914"}、manifest {"bytes": 8066, "sha256": "02f7acf309fdc5db25fa2a498c43c85cf0ea648014b7a08d2ac8bdcfcfd338d8"}、evaluation {"bytes": 14336743, "sha256": "1dd00063fb25a9af35b148cab345ec492d2e69c04b3c2250a70c0d03b7acd64f"}。
- thresholds {"c0-diff-control": 4.0, "c1-phase-level": 6.0, "c2-phase-conditional": 6.0}。C0 threshold4/operator>/persistence2を全14400score原flagへ照合。GT/matching/config/science変更0。declared16/config一致はfull loaded runtime/native認証ではない。

## 原指標

| 指標 | 原値 |
| --- | --- |
| machine recall | 0/10 |
| sensor recall | 0/10 |
| precision | 0/3 |
| clean_rate | 3/3365、原value 25.676077265973255 |
| effective clean | 3254秒、原value 26.551936078672405 |
| burden | 3/20、原value 15.0 |
| delay | count0/min-max-mean-median原null |

48calibrated/原fit samples各0/cal290/C2stateなし48、source3/equipment3/events40/incidents20。fit0はC0 no-op定義。source内訳 {"conveyor-01.motor_temperature": 1, "motor-01.vibration_feature": 2}。全equipment3はclean/未対応/matchednull。clean_rateとburdenの原valueを単純な確率に変換しない。

## 未検出20件・欠測・persistence

全20incident no_candidate_in_window/candidate0/causalfalse/matchednull/delaynull。全対象窓maxstreak1。19対象窓は7rows全利用可でphase不能0、cycle09温度だけ利用3/不能4。欠測1窓を全20missの説明へしない。
18000observations/mask対応、非ok30。利用可能13889/不能511、全不能score/residual null・threshold_exceeded false。
phase tag480＋quality primary40−重複9＝不能511。排他的primary phase471/current quality30/previous quality10。C0 core13920/480→quality13889/511は利用可能31減少。原重複9scoresを-save/availability-summaryへ保持し、タグを独立行として加算しない。
非排他的tags {"current_nonfinite": 30, "current_target_quality": 30, "mode_recipe_or_phase": 480, "previous_target_quality_or_nonfinite": 30}。
cycle09温度sample 8961 score 198.663211819175/streak1→8962–8964 current quality不能/8965 previous quality不能でreset。非欠測の他19窓もmaxstreak1でpersistence2不成立。

### cycle0 machine conveyor-01.conveyor_speed

| sample | available | score | streak | primary reason |
| --- | --- | --- | --- | --- |
| 7334 | True | 134.1567757011945 | 1 | None |
| 7335 | True | 0.09732206501640103 | 0 | None |
| 7336 | True | 0.45354336862854516 | 0 | None |
| 7337 | True | 134.3643835812005 | 1 | None |
| 7338 | True | 0.33236048844403343 | 0 | None |
| 7339 | True | 0.13320722798571494 | 0 | None |
| 7340 | True | 0.4037550535139447 | 0 | None |

### cycle0 sensor conveyor-01.motor_temperature

| sample | available | score | streak | primary reason |
| --- | --- | --- | --- | --- |
| 7341 | True | 200.07145157058935 | 1 | None |
| 7342 | True | 0.29744180759662947 | 0 | None |
| 7343 | True | 1.5461921161353323 | 0 | None |
| 7344 | True | 201.3335593701093 | 1 | None |
| 7345 | True | 1.3984592664452322 | 0 | None |
| 7346 | True | 1.3714441161462856 | 0 | None |
| 7347 | True | 1.2159569177592162 | 0 | None |

### cycle9 machine conveyor-01.conveyor_speed

| sample | available | score | streak | primary reason |
| --- | --- | --- | --- | --- |
| 8954 | True | 133.7537721694181 | 1 | None |
| 8955 | True | 0.5401562488844595 | 0 | None |
| 8956 | True | 0.15594076054750913 | 0 | None |
| 8957 | True | 134.21708532063514 | 1 | None |
| 8958 | True | 0.4631252707826736 | 0 | None |
| 8959 | True | 1.3429693450525368 | 0 | None |
| 8960 | True | 0.5031438033087248 | 0 | None |

### cycle9 sensor conveyor-01.motor_temperature

| sample | available | score | streak | primary reason |
| --- | --- | --- | --- | --- |
| 8961 | True | 198.663211819175 | 1 | None |
| 8962 | False | None | 0 | current_target_quality |
| 8963 | False | None | 0 | current_target_quality |
| 8964 | False | None | 0 | current_target_quality |
| 8965 | False | None | 0 | previous_target_quality_or_nonfinite |
| 8966 | True | 0.6660235109801386 | 0 | None |
| 8967 | True | 0.07381639678888953 | 0 | None |

全20event/incident・四target窓・全episodes・不能511・非ok30を新analysisへ保存。入力対応・保存・状態分類の実経路不具合観測なし。C0設計レビューは同layout10 coreの既保存-save/C0-design-review訂正版（sensor加算3観測/end-exclusive）を優先。旧four-sample誤記・原analysis failureを保持し、今回再分析/式変更/threshold変更0。

## 同seed11layouts・3候補×2条件の保存比較

| layout | stratum | candidate | machine | sensor | precision | clean | available | delay count | delay median |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | core | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13920 | 0 | None |
| 0 | core | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 | 1.5 |
| 0 | core | c2-phase-conditional | 4/10 | 10/10 | 14/20 | 0 | 13920 | 14 | 1.0 |
| 0 | quality-stress | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13880 | 0 | None |
| 0 | quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 13880 | 19 | 2.0 |
| 0 | quality-stress | c2-phase-conditional | 4/10 | 9/10 | 13/19 | 0 | 13760 | 13 | 1.0 |
| 1 | core | c0-diff-control | 0/10 | 0/10 | 0/3 | 2 | 13920 | 0 | None |
| 1 | core | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 | 1.0 |
| 1 | core | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 | 1.0 |
| 1 | quality-stress | c0-diff-control | 0/10 | 0/10 | 0/3 | 2 | 13880 | 0 | None |
| 1 | quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 13880 | 19 | 1.0 |
| 1 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13760 | 19 | 1.0 |
| 2 | core | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13920 | 0 | None |
| 2 | core | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 | 1.0 |
| 2 | core | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 | 1.0 |
| 2 | quality-stress | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13889 | 0 | None |
| 2 | quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 13889 | 19 | 1.0 |
| 2 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13796 | 19 | 1.0 |
| 3 | core | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13920 | 0 | None |
| 3 | core | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 | 1.5 |
| 3 | core | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 | 1.5 |
| 3 | quality-stress | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13880 | 0 | None |
| 3 | quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 13880 | 19 | 1.0 |
| 3 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13760 | 19 | 1.0 |
| 4 | core | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13920 | 0 | None |
| 4 | core | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 | 1.5 |
| 4 | core | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 | 1.5 |
| 4 | quality-stress | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13880 | 0 | None |
| 4 | quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 13880 | 19 | 2.0 |
| 4 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13760 | 19 | 2.0 |
| 5 | core | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13920 | 0 | None |
| 5 | core | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 | 1.0 |
| 5 | core | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 | 1.0 |
| 5 | quality-stress | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13880 | 0 | None |
| 5 | quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 13880 | 19 | 1.0 |
| 5 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13760 | 19 | 1.0 |
| 6 | core | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13920 | 0 | None |
| 6 | core | c1-phase-level | 0/10 | 10/10 | 10/20 | 0 | 13920 | 10 | 1.0 |
| 6 | core | c2-phase-conditional | 0/10 | 10/10 | 10/20 | 0 | 13920 | 10 | 1.0 |
| 6 | quality-stress | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13889 | 0 | None |
| 6 | quality-stress | c1-phase-level | 0/10 | 9/10 | 9/19 | 0 | 13889 | 9 | 1.0 |
| 6 | quality-stress | c2-phase-conditional | 0/10 | 9/10 | 9/19 | 0 | 13796 | 9 | 1.0 |
| 7 | core | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13920 | 0 | None |
| 7 | core | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 | 1.5 |
| 7 | core | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 | 1.5 |
| 7 | quality-stress | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13880 | 0 | None |
| 7 | quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 13880 | 19 | 1.0 |
| 7 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13760 | 19 | 1.0 |
| 8 | core | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13920 | 0 | None |
| 8 | core | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 | 1.5 |
| 8 | core | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 | 1.5 |
| 8 | quality-stress | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13880 | 0 | None |
| 8 | quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 13880 | 19 | 2.0 |
| 8 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13760 | 19 | 2.0 |
| 9 | core | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13920 | 0 | None |
| 9 | core | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 | 1.0 |
| 9 | core | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 | 1.0 |
| 9 | quality-stress | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13880 | 0 | None |
| 9 | quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 13880 | 19 | 1.0 |
| 9 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13760 | 19 | 1.0 |
| 10 | core | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13920 | 0 | None |
| 10 | core | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 | 1.0 |
| 10 | core | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 | 1.0 |
| 10 | quality-stress | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13889 | 0 | None |
| 10 | quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 13889 | 19 | 1.0 |
| 10 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13796 | 19 | 1.0 |

旧65board＋新1＝66完了、layout0–10/core-quality/3candidateの66unique組を原保存manifestで確認。同合成dev seed1/66独立datasetではない。各同layout-stratumの候補は入力共有。元生成candidateと実評価candidateは別field、未検出delay補完0。
同layout10 quality C0は0/20・clean3、C1/C2は19/20・clean0。C0/C1利用13889、C2利用13796。C2 peer primary93/tag120/phase重複27を既保存原指標で保持。core/quality共通input ["origins.json", "split-manifest.json", "targets.json"]、他7差。閾値C0 4.0/C1-C2 6.0、persistence2・科学式・GT・matchingは固定。同input10/宣言16/candidate/compiledconfigを保存manifestで照合。
旧model/replay/試験/CI反復0、bootstrap/統計CI/勝者/採択0。66cell保存比較の完了は正式受入完了ではない。

## 保存と次unit

- model artifacts/representative-layout10-quality-c0-20261012-records、analysis ...-analysis、docs/Git ...-save、最終 ...-final/root-closed.json post-save label優先。
- selected-windows {"bytes": 978344, "parts": 4}、unavailable-scores {"bytes": 511346, "parts": 2}、non-ok-input-records {"bytes": 22105, "parts": 1}。-save/eleven-layout-comparison-summaryは全66原manifest対応。
- DATA artifacts/representative-anomaly-evaluation/dev-layout10-quality-c0-20261012/root-closed.json、{"bytes": 27384592, "files": 19, "manifest_pin": {"bytes": 2236, "sha256": "6d475a431f414b5c3e7917de5f06c160a0e5364abd2c58dbc77af2bb1acae445"}}。
- 次は保存済みchunk011/同seed/layout11 core C0、新ID dev-layout11-core-c0-20261012。manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\011\attempt-0001\result\payload\manifest.json、pin {"bytes": 75714, "sha256": "ce20f3d40c4e286df89ac3fe4ae6411763fec86f573e9ca67073e2acf2e92177"}。dev identity/input10 metadataだけ選択、観測本文未読/次model未実行。新独立seedではない。原nextmanifest bytesは-save/next-input-manifestへ保存。

prepare_result_indexでhandoff/report/index3文書を準備、継続送信承認内で一回[skip ci] commit/push。原返値/pins/HEAD-upstream-remote-cleanは-save/-final保存。旧C0 threshold表記訂正/C1 fingerprint期待failed・continuation/前回source前処理拒否は原保持。今回helper failure0。
実行900秒2GiB/output1GiB/single32MiB/files32、Git30秒16entry512KiB/stdout1MiBstderr128KiB、protocol/native不変。検証16MiB512files/part256KiB/失敗予備枠維持。closed/frozen root追記整理0/fullstdio-native回収claim0。
ACTIVE/automation詳細転記0。CI381385/4130再照会downloadverifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了/create_native早期拒否/7役reader禁止/追加agent禁止/caps-unknown原owner保持。未完了formal/nativeをdev開始条件へ戻さない。Sol容量/人停止は原保全後PAUSED、重複再試行なし。
