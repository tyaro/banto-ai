# layout10 C1 core実評価（2026-10-12）

同保存dev coreを既存CLI C1で一回fresh評価。exit0/complete/1cell success。機械10/10・sensor10/10・precision20/20・clean誤警報0。検出20件のdelayは全1秒。処理successや単一dev結果を性能保証・採択・正式受入へしない。

## 入力と結果の対応

- run dev-layout10-core-c1-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-10-core。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\010\attempt-0001\result\payload\manifest.json、pin {"bytes": 75715, "sha256": "1ede2721456af4d88ae82d606decb08b3e8fb2121295e9aea89ffddeda0b0c63"}。
- seed2486912926863618161/layout10/core/dev。input10 pins→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics。同C0 input10 pins一致。
- 元生成candidate C0/実評価candidate C1は別field。元payload書込み/生成/replay/追加agent0。
- actual checkout 8d7c57778bdc419d6b13c778e2d9f7eb4454c58c、計算661b27511826fcc87cb4a02930f276afbb8f95d9不変。declared16/candidate/compiled config一致はfull loaded runtime/native認証ではない。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 17.699710899963975秒/privatepeak 149934080B。
- observations {"bytes": 9600481, "sha256": "65d7034a0abc408d7d8e20f589f5fc1e6dd9b8693c325e431b636b31118ad762"}、configuration {"bytes": 5503, "sha256": "30744335cdc9376d1d79708c4d986f402a93469f82cbc6311e6ff2fd082f4ddc"}、manifest {"bytes": 8005, "sha256": "22bc59c989b89e197ede954171c16600b140dc9a3fc45a298d67eb924c0f2d21"}、evaluation {"bytes": 14073862, "sha256": "d5359f4d7a35cd98b821bdc7de3ba37977d032d4802023e99e3fc5b2fa031570"}。
- 保存configurationから候補閾値 {"c0-diff-control": 4.0, "c1-phase-level": 6.0, "c2-phase-conditional": 6.0}、今回C1 threshold 6.0/operator >/persistence 2。全14400scoreのthreshold_exceededを実6.0へ照合。GT/matching/config/science変更0。

## 原指標とavailability

| 指標 | 原値 |
| --- | --- |
| machine recall | 10/10 |
| sensor recall | 10/10 |
| precision | 20/20 |
| clean_rate | 0/3365、原value 0.0 |
| effective clean | 3254秒、原value 0.0 |
| burden | 0/20、原value 0.0 |
| detected delay | count20、min/max/mean/median全1秒 |

48calibrated/fit samples各600/calibration各290、14400scores。利用可能13920/不能480は全mode_recipe_or_phase、不能score/residual null・threshold_exceeded false。18000observations/mask対応、欠測0。全20対象窓は7rows全利用可/phase不能0。未検出delay補完0。

## target-source-equipment-incident対応

全20incident causal_detected true/candidate_count1。原target sourceのfull_targetとevent target一致、選択equipmentへの所属とmatched_event_idを確認した。machine10・sensor10ともonsetはevent start+1000ms、各target supportは2scores。固定second-exceedance/persistence2と整合。
原source30/equipment20/events40/incidents20。source内訳 {"conveyor-01.conveyor_speed": 10, "conveyor-01.vibration_feature": 10, "conveyor-01.motor_temperature": 10}。
matched equipmentのsource所属内訳 {"machine": {"conveyor-01.conveyor_speed": 10, "conveyor-01.vibration_feature": 10}, "sensor": {"conveyor-01.motor_temperature": 10}}。source30をequipment誤警報30やprecision母数30へしない。clean0/未対応equipment0を原値で保持。

### 原対象窓の抜粋

#### cycle0 machine conveyor-01.conveyor_speed

| sample | score | streak |
| --- | --- | --- |
| 7334 | 167.24502791712752 | 1 |
| 7335 | 167.07553656937813 | 2 |
| 7336 | 168.14442745250918 | 3 |
| 7337 | 0.33786374636496264 | 0 |
| 7338 | 0.08085879793595409 | 0 |
| 7339 | 0.2227886617567264 | 0 |
| 7340 | 0.06248447531683671 | 0 |

#### cycle0 sensor conveyor-01.motor_temperature

| sample | score | streak |
| --- | --- | --- |
| 7341 | 162.35645281022542 | 1 |
| 7342 | 162.79178500749663 | 2 |
| 7343 | 162.05164050212764 | 3 |
| 7344 | 0.011662577130955247 | 0 |
| 7345 | 0.5406286079393724 | 0 |
| 7346 | 1.1494858164624937 | 0 |
| 7347 | 1.3016041926340896 | 0 |

#### cycle9 machine conveyor-01.conveyor_speed

| sample | score | streak |
| --- | --- | --- |
| 8954 | 167.8537362459453 | 1 |
| 8955 | 168.23947923682726 | 2 |
| 8956 | 168.54418675359423 | 3 |
| 8957 | 0.24658105386606752 | 0 |
| 8958 | 0.8292590923067606 | 0 |
| 8959 | 0.5456349329041125 | 0 |
| 8960 | 0.5813235210681764 | 0 |

#### cycle9 sensor conveyor-01.motor_temperature

| sample | score | streak |
| --- | --- | --- |
| 8961 | 161.71914093299674 | 1 |
| 8962 | 162.26294014632074 | 2 |
| 8963 | 161.09401670130669 | 3 |
| 8964 | 1.3818083918994226 | 0 |
| 8965 | 1.9806085209224282 | 0 |
| 8966 | 2.019948261617119 | 0 |
| 8967 | 1.13077520570599 | 0 |

全20event/incident・20target links・全4target窓・全episodes・不能480を新analysisへ保存。原入力対応・保存・状態分類の実経路不具合観測なし。

## 保存済みC0とC1 coreの比較

| layout | candidate | machine | sensor | precision | clean | delay median |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 1.5 |
| 1 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 1.0 |
| 2 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 1.0 |
| 3 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 1.5 |
| 4 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 1.5 |
| 5 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 1.0 |
| 6 | c1-phase-level | 0/10 | 10/10 | 10/20 | 0 | 1.0 |
| 7 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 1.5 |
| 8 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 1.5 |
| 9 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 1.0 |
| 10 | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | None |
| 10 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 1.0 |

同layout10 C0 core＋過去10layouts C1 core＋今回を12セル比較。C1 coreは11layouts保存済み。同core C0は0/20検出・clean3、今回C1は20/20・clean0。旧manifest指標だけを使い、旧model再計算0。
旧61board＋今回1=62完了。同合成dev seed1で、62独立datasetではない。layout0–9の60cell完成を保持、layout10はcore C0/C1の2件。bootstrap/統計CI/勝者/採択0。

## 保存・次unit

- model artifacts/representative-layout10-core-c1-20261012-records、analysis ...-analysis、docs/Git ...-save、最終 ...-final/root-closed.jsonとpost-save label優先。
- selected-windows {"bytes": 1006889, "parts": 4}、matched-targets {"bytes": 64078, "parts": 1}、unavailable-scores {"bytes": 461979, "parts": 2}、analysis {"bytes": 429375, "parts": 2}。
- DATA artifacts/representative-anomaly-evaluation/dev-layout10-core-c1-20261012/root-closed.json、{"bytes": 27115187, "files": 19, "manifest_pin": {"bytes": 2226, "sha256": "99a20a17d52d7ea2af304f21decdcb259d65d8eb6a757527445c06779ed4572a"}}。
- 次は同chunk010/同layout10 core C2、新ID dev-layout10-core-c2-20261012。同manifest/input10、本文はC0/C1で読取済み/次model未実行。元生成candidate C0/次実評価C2を別field保持。

prepare_result_indexで索引候補を作り、handoff/report/index3文書を継続送信承認内で一回[skip ci] Git保存。原返値/pins/HEAD-upstream-remote-cleanは-save/-finalへ保持。
C0の差分と連続2点条件の設計確認は同layout10 C0報告と-save/C0-design-review訂正版を参照。一定加算はend-exclusiveの3観測で、旧four-sample fieldの誤記と初回analysis NameErrorを原保存した。C0 baseline/GT/閾値変更0。今回も閾値はcandidateのconfigurationから取得し、過去failed/helperをsuccessへ書き換えない。

実行900秒2GiB/output1GiB/single32MiB/files32、Git30秒16entry512KiB/stdout1MiBstderr128KiB、protocol/native不変。新検証16MiB512files/part256KiB/失敗予備枠維持。closed/frozen root追記整理0/fullstdio-native回収claim0。
ACTIVE。旧完成CI381385/4130再照会downloadverifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了/create_native早期拒否/7役reader禁止/追加agent禁止/caps-unknown原owner保持。未完了formal/nativeをdev開始条件へ戻さない。Sol容量/人停止は原保全後PAUSED、重複再試行なし。
