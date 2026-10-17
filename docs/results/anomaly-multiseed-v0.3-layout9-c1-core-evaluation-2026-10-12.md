# layout9 C1 core実評価（2026-10-12）

同保存dev coreを既存CLI C1で一回fresh評価。exit0/complete/1cell success。機械10/10・sensor10/10・precision20/20・clean誤警報0。検出20件のdelayは全1秒。処理successや単一dev結果を性能保証・採択・正式受入へしない。

## 入力と結果の対応

- run dev-layout9-core-c1-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-09-core。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\009\attempt-0001\result\payload\manifest.json、pin {"bytes": 75699, "sha256": "7a71c5434cc8f526ada42d7a3f885bf711cabc256a7ff891c95a8969c6c58e5c"}。
- seed2486912926863618161/layout9/core/dev。input10 pins→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics。同C0 input10 pins一致。
- 元生成candidate C0/実評価candidate C1は別field。元payload書込み/生成/replay/追加agent0。
- actual checkout 4f227b25eb81f466a31d67c45f585266ca1fac08、計算661b27511826fcc87cb4a02930f276afbb8f95d9不変。declared16/candidate/compiled config一致はfull loaded runtime/native認証ではない。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 16.29790290002711秒/privatepeak 149180416B。
- observations {"bytes": 9600601, "sha256": "03d6fbac9cd83c2995cb6859d6f32fd4852d177776c9d3d41e63f33131c88e5d"}、configuration {"bytes": 5502, "sha256": "70f7c42d52dcde6ebdb9f7eb72b8e4e40603638fb0adbdfd20fa5108ae5f6977"}、manifest {"bytes": 8002, "sha256": "0f3cb8b311ee0ac24e2699b3e12a20972b56c53470887ecdcaf14b82c7d51f1d"}、evaluation {"bytes": 14073572, "sha256": "41e90c33da9980be5b486e29fb8d4ff3340a1d6b6eab20c439ac25d6a36dbb86"}。
- 保存configurationから候補閾値 {"c0-diff-control": 4.0, "c1-phase-level": 6.0, "c2-phase-conditional": 6.0}、今回C1 threshold 6.0/operator >/persistence 2。全14400scoreのthreshold_exceededを実6.0へ照合。GT/matching/config/science変更0。

## 原指標とavailability

| 指標 | 原値 |
| --- | --- |
| machine recall | 10/10 |
| sensor recall | 10/10 |
| precision | 20/20 |
| clean_rate | 0/3365、原value 0.0 |
| effective clean | 3255秒、原value 0.0 |
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
| 7297 | 170.22512163053486 | 1 |
| 7298 | 170.97610357455957 | 2 |
| 7299 | 170.09888960317414 | 3 |
| 7300 | 2.1247414292860745 | 0 |
| 7301 | 0.5288431615012958 | 0 |
| 7302 | 0.14361358581566816 | 0 |
| 7303 | 1.9210936663955307 | 0 |

#### cycle0 sensor conveyor-01.motor_temperature

| sample | score | streak |
| --- | --- | --- |
| 7304 | 123.08077462015436 | 1 |
| 7305 | 122.42351960942031 | 2 |
| 7306 | 122.28575692463538 | 3 |
| 7307 | 0.9079305382202058 | 0 |
| 7308 | 0.8787303361252329 | 0 |
| 7309 | 1.127483073845495 | 0 |
| 7310 | 1.3713652579304645 | 0 |

#### cycle9 machine conveyor-01.conveyor_speed

| sample | score | streak |
| --- | --- | --- |
| 8917 | 170.19085160748185 | 1 |
| 8918 | 171.3508549057866 | 2 |
| 8919 | 170.44035709906194 | 3 |
| 8920 | 1.7068443855821125 | 0 |
| 8921 | 1.0880115952007035 | 0 |
| 8922 | 0.7964698523217411 | 0 |
| 8923 | 0.1373266391404746 | 0 |

#### cycle9 sensor conveyor-01.motor_temperature

| sample | score | streak |
| --- | --- | --- |
| 8924 | 122.17455879425036 | 1 |
| 8925 | 121.79122618606706 | 2 |
| 8926 | 121.58607723389792 | 3 |
| 8927 | 1.2271829984965168 | 0 |
| 8928 | 1.7684695106490844 | 0 |
| 8929 | 1.8520087533806118 | 0 |
| 8930 | 1.1740770094132578 | 0 |

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
| 9 | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | None |
| 9 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 1.0 |

同layout9 C0 core＋過去9layouts C1 core＋今回を11セル比較。C1 coreは10layouts保存済み。同core C0は0/20検出・clean3、今回C1は20/20・clean0。旧manifest指標だけを使い、旧model再計算0。
旧55board＋今回1=56完了。同合成dev seed1で、56独立datasetではない。layout0–8の54cell完成を保持、layout9はcore C0/C1の2件。bootstrap/統計CI/勝者/採択0。

## 保存・次unit

- model artifacts/representative-layout9-core-c1-20261012-records、analysis ...-analysis、docs/Git ...-save、最終 ...-final/root-closed.jsonとpost-save label優先。
- selected-windows {"bytes": 1001301, "parts": 4}、matched-targets {"bytes": 63858, "parts": 1}、unavailable-scores {"bytes": 461979, "parts": 2}、analysis {"bytes": 390842, "parts": 2}。
- DATA artifacts/representative-anomaly-evaluation/dev-layout9-core-c1-20261012/root-closed.json、{"bytes": 27114677, "files": 19, "manifest_pin": {"bytes": 2225, "sha256": "65568fedac52dd56a999dd3e148f8620b233209079eea5009a9ddce390b77d0e"}}。
- 次は同chunk009/同layout9 core C2、新ID dev-layout9-core-c2-20261012。同manifest/input10、本文はC0/C1で読取済み/次model未実行。元生成candidate C0/次実評価C2を別field保持。

prepare_result_indexで索引候補を作り、handoff/report/index3文書を継続送信承認内で一回[skip ci] Git保存。原返値/pins/HEAD-upstream-remote-cleanは-save/-finalへ保持。
直前C0の閾値表記訂正は保存済み。今回も閾値は現在candidateのconfigurationから取得する。過去failed/helper/source変換失敗は原保存を保持し、今回successへ書き換えない。

実行900秒2GiB/output1GiB/single32MiB/files32、Git30秒16entry512KiB/stdout1MiBstderr128KiB、protocol/native不変。新検証16MiB512files/part256KiB/失敗予備枠維持。closed/frozen root追記整理0/fullstdio-native回収claim0。
ACTIVE。旧完成CI381385/4130再照会downloadverifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了/create_native早期拒否/7役reader禁止/追加agent禁止/caps-unknown原owner保持。未完了formal/nativeをdev開始条件へ戻さない。Sol容量/人停止は原保全後PAUSED、重複再試行なし。
