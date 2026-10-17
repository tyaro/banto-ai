# layout10 C2 core実評価・11layouts core比較（2026-10-12）

同保存dev coreを既存CLI C2で一回fresh評価。exit0/complete/1cell success。機械10/10・sensor10/10・precision20/20・clean誤警報0、検出20件のdelayは全1秒。単一合成dev seedの結果を性能保証・採択・正式受入へしない。

## 入力と結果の対応

- run dev-layout10-core-c2-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-10-core。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\010\attempt-0001\result\payload\manifest.json、pin {"bytes": 75715, "sha256": "1ede2721456af4d88ae82d606decb08b3e8fb2121295e9aea89ffddeda0b0c63"}。
- seed2486912926863618161/layout10/core/dev。input10 pins→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics。同C0/C1 core input10 pins一致。
- 元生成candidate C0/実評価candidate C2は別field。元payload書込み/生成/replay/追加agent0。
- actual checkout aa1a8e487fbd24732330cabe83ceee8203a72aaf、計算661b27511826fcc87cb4a02930f276afbb8f95d9不変。declared16/candidate/compiled config一致はfull loaded runtime/native認証ではない。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 44.092413900070824秒/privatepeak 207876096B。
- observations {"bytes": 9600481, "sha256": "65d7034a0abc408d7d8e20f589f5fc1e6dd9b8693c325e431b636b31118ad762"}、configuration {"bytes": 5509, "sha256": "ffc53a5faee0237e8370f27945016fb806c57671c1779c0d99adebeab412ba51"}、manifest {"bytes": 8011, "sha256": "cf0c82eb900da37959f34977769589e8f01b0847c44e18674bb7c8c00e3a2f0e"}、evaluation {"bytes": 24762826, "sha256": "0ecf78ec5ef058ac31f41550a61f70e0f79be9c5cf11e68638f6908f2c3c9b34"}。
- 保存configurationから候補閾値 {"c0-diff-control": 4.0, "c1-phase-level": 6.0, "c2-phase-conditional": 6.0}、今回C2 threshold 6.0/operator >/persistence 2。全14400scoreのthreshold_exceededを実6.0へ照合。GT/matching/config/science変更0。

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

48calibrated/fit samples各600/calibration各290/C2 stateあり48、14400scores。利用可能13920/不能480は全mode_recipe_or_phase、不能score/residual null・threshold_exceeded false。18000observations/mask対応、欠測0。全20対象窓は7rows全利用可/phase不能0/maxstreak3。未検出delay補完0。

## target-source-equipment-incident対応

全20incident causal_detected true/candidate_count1。原target sourceのfull_targetとevent target一致、選択equipmentへの所属とmatched_event_idを確認した。machine10・sensor10ともonsetはevent start+1000ms、各target supportは2scores。固定second-exceedance/persistence2と整合。
原source49/equipment20/events40/incidents20。source内訳 {"conveyor-01.conveyor_speed": 10, "conveyor-01.vibration_feature": 20, "conveyor-01.motor_current": 9, "conveyor-01.motor_temperature": 10}。
matched equipmentのsource所属内訳 {"machine": {"conveyor-01.conveyor_speed": 10, "conveyor-01.vibration_feature": 10}, "sensor": {"conveyor-01.motor_current": 9, "conveyor-01.motor_temperature": 10, "conveyor-01.vibration_feature": 10}}。全equipmentのsource参照unique数 49、未参照source 0件も原episodeとして保存。source49をequipment誤警報49やprecision母数49へしない。clean0/未対応equipment0を原値で保持。
同条件C1の保存source30からC2は49へ19増加。C1内訳 {"conveyor-01.conveyor_speed": 10, "conveyor-01.motor_temperature": 10, "conveyor-01.vibration_feature": 10}。両候補のequipment20・precision20/20・clean0/未対応0は同じで、source増分19を誤警報19件へ変換しない。C1原モデル再計算0。

### 原対象窓の抜粋

#### cycle0 machine conveyor-01.conveyor_speed

| sample | score | streak |
| --- | --- | --- |
| 7334 | 166.51806091380024 | 1 |
| 7335 | 166.34675437000215 | 2 |
| 7336 | 167.41757612570194 | 3 |
| 7337 | 0.32585897586322005 | 0 |
| 7338 | 0.09311278245222984 | 0 |
| 7339 | 0.22979060690106493 | 0 |
| 7340 | 0.06294293838616224 | 0 |

#### cycle0 sensor conveyor-01.motor_temperature

| sample | score | streak |
| --- | --- | --- |
| 7341 | 156.8068452617999 | 1 |
| 7342 | 157.08534993369778 | 2 |
| 7343 | 156.5095925661822 | 3 |
| 7344 | 0.014860842441824739 | 0 |
| 7345 | 0.5517520127323283 | 0 |
| 7346 | 1.0592963566212268 | 0 |
| 7347 | 1.2580004089324481 | 0 |

#### cycle9 machine conveyor-01.conveyor_speed

| sample | score | streak |
| --- | --- | --- |
| 8954 | 167.13737271933616 | 1 |
| 8955 | 167.540874188522 | 2 |
| 8956 | 167.82238711514307 | 3 |
| 8957 | 0.26783768919647 | 0 |
| 8958 | 0.8259710827842152 | 0 |
| 8959 | 0.535417641431204 | 0 |
| 8960 | 0.5705400040232207 | 0 |

#### cycle9 sensor conveyor-01.motor_temperature

| sample | score | streak |
| --- | --- | --- |
| 8961 | 156.0873274122774 | 1 |
| 8962 | 156.72571821579638 | 2 |
| 8963 | 155.55088055030643 | 3 |
| 8964 | 1.2715588021066004 | 0 |
| 8965 | 1.8174075902725928 | 0 |
| 8966 | 2.077727670127084 | 0 |
| 8967 | 0.9745062962277924 | 0 |

全20event/incident・20target links・全4target窓・全episodes・不能480を新analysisへ保存。原入力対応・保存・状態分類の実経路不具合観測なし。

## 保存済みcore比較

| layout | candidate | machine | sensor | precision | clean | delay count | delay median |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | c2-phase-conditional | 4/10 | 10/10 | 14/20 | 0 | 14 | 1.0 |
| 1 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 20 | 1.0 |
| 2 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 20 | 1.0 |
| 3 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 20 | 1.5 |
| 4 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 20 | 1.5 |
| 5 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 20 | 1.0 |
| 6 | c2-phase-conditional | 0/10 | 10/10 | 10/20 | 0 | 10 | 1.0 |
| 7 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 20 | 1.5 |
| 8 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 20 | 1.5 |
| 9 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 20 | 1.0 |
| 10 | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 0 | None |
| 10 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 20 | 1.0 |
| 10 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 20 | 1.0 |

同layout10 C0/C1 core＋過去10layouts C2 core＋今回を13セル比較。C2 coreは11layouts保存済み。同core C0は0/20検出・clean3、C1/C2は20/20・clean0。遅延は検出件だけの原値で未検出を補完しない。
旧62board＋今回1=63完了。同合成dev seed1で、63独立datasetではない。layout0–9の60cell完成を保持、layout10のcore C0/C1/C2が完成し、quality-stress3候補は未実行。旧manifest指標だけを使い、旧model再計算/replay/試験/CI反復0。bootstrap/統計CI/勝者/採択0。

## 保存・次unit

- model artifacts/representative-layout10-core-c2-20261012-records、analysis ...-analysis、docs/Git ...-save、最終 ...-final/root-closed.jsonとpost-save label優先。
- selected-windows {"bytes": 1749885, "parts": 7}、matched-targets {"bytes": 68089, "parts": 1}、unavailable-scores {"bytes": 816438, "parts": 4}、analysis {"bytes": 439836, "parts": 2}。
- DATA artifacts/representative-anomaly-evaluation/dev-layout10-core-c2-20261012/root-closed.json、{"bytes": 37804181, "files": 19, "manifest_pin": {"bytes": 2226, "sha256": "03a1f3d62c71b72f9ef5a3a51b0fb5eac11c8093ab0501a3607d048fb3931987"}}。
- 次は同chunk010/同seed/layout10 quality-stress C1、新ID dev-layout10-quality-c1-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-10-quality-stress。同manifestからidentity/input10 metadataだけ選択、quality観測本文未読/次model未実行。元生成candidate C0/次実評価C1を別field保持。

prepare_result_indexで索引候補を作り、handoff/report/index3文書を継続送信承認内で一回[skip ci] Git保存。原返値/pins/HEAD-upstream-remote-cleanは-save/-finalへ保持。
C0設計確認は同layout10 C0報告/-save訂正版（sensor一定加算3観測/end-exclusive）を参照。初回C0analysis failureと旧four-sample誤記、前回C1source前処理拒否は原保存を保持。C0 baseline変更0。今回閾値6.0は現在C2 configurationから取得し、過去failed/helperをsuccessへ書き換えない。

実行900秒2GiB/output1GiB/single32MiB/files32、Git30秒16entry512KiB/stdout1MiBstderr128KiB、protocol/native不変。新検証16MiB512files/part256KiB/失敗予備枠維持。closed/frozen root追記整理0/fullstdio-native回収claim0。
ACTIVE。旧完成CI381385/4130再照会downloadverifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了/create_native早期拒否/7役reader禁止/追加agent禁止/caps-unknown原owner保持。未完了formal/nativeをdev開始条件へ戻さない。Sol容量/人停止は原保全後PAUSED、重複再試行なし。
