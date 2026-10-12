# layout9 C2 core実評価・10layouts core比較（2026-10-12）

同保存dev coreを既存CLI C2で一回fresh評価。exit0/complete/1cell success。機械10/10・sensor10/10・precision20/20・clean誤警報0、検出20件のdelayは全1秒。単一合成dev seedの結果を性能保証・採択・正式受入へしない。

## 入力と結果の対応

- run dev-layout9-core-c2-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-09-core。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\009\attempt-0001\result\payload\manifest.json、pin {"bytes": 75699, "sha256": "7a71c5434cc8f526ada42d7a3f885bf711cabc256a7ff891c95a8969c6c58e5c"}。
- seed2486912926863618161/layout9/core/dev。input10 pins→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics。同C0/C1 core input10 pins一致。
- 元生成candidate C0/実評価candidate C2は別field。元payload書込み/生成/replay/追加agent0。
- actual checkout f21319399a05ece475c450d3f9d535defab1a22e、計算661b27511826fcc87cb4a02930f276afbb8f95d9不変。declared16/candidate/compiled config一致はfull loaded runtime/native認証ではない。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 25.69968630000949秒/privatepeak 207876096B。
- observations {"bytes": 9600601, "sha256": "03d6fbac9cd83c2995cb6859d6f32fd4852d177776c9d3d41e63f33131c88e5d"}、configuration {"bytes": 5508, "sha256": "48a6eb7b5e32f32aaede035beebfadbebd52bfee2b42dd7631681617c49d2223"}、manifest {"bytes": 8008, "sha256": "65a35fca8bd7907c11bd5d7c9f61094fb05cf5c48cdc7dc764b549db720b06a1"}、evaluation {"bytes": 24770147, "sha256": "310e80e21578e47b6224b549616cada145644a63783e26390d151a50d36dfa40"}。
- 保存configurationから候補閾値 {"c0-diff-control": 4.0, "c1-phase-level": 6.0, "c2-phase-conditional": 6.0}、今回C2 threshold 6.0/operator >/persistence 2。全14400scoreのthreshold_exceededを実6.0へ照合。GT/matching/config/science変更0。

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

48calibrated/fit samples各600/calibration各290/C2 stateあり48、14400scores。利用可能13920/不能480は全mode_recipe_or_phase、不能score/residual null・threshold_exceeded false。18000observations/mask対応、欠測0。全20対象窓は7rows全利用可/phase不能0/maxstreak3。未検出delay補完0。

## target-source-equipment-incident対応

全20incident causal_detected true/candidate_count1。原target sourceのfull_targetとevent target一致、選択equipmentへの所属とmatched_event_idを確認した。machine10・sensor10ともonsetはevent start+1000ms、各target supportは2scores。固定second-exceedance/persistence2と整合。
原source55/equipment20/events40/incidents20。source内訳 {"conveyor-01.conveyor_speed": 20, "conveyor-01.vibration_feature": 10, "conveyor-01.motor_current": 10, "conveyor-01.motor_temperature": 15}。
matched equipmentのsource所属内訳 {"machine": {"conveyor-01.conveyor_speed": 10, "conveyor-01.vibration_feature": 10, "conveyor-01.motor_temperature": 5}, "sensor": {"conveyor-01.conveyor_speed": 10, "conveyor-01.motor_current": 10, "conveyor-01.motor_temperature": 10}}。全equipmentのsource参照unique数 55、未参照source 0件も原episodeとして保存。source55をequipment誤警報55やprecision母数55へしない。clean0/未対応equipment0を原値で保持。
同条件C1の保存source30からC2は55へ25増加。C1内訳 {"conveyor-01.conveyor_speed": 10, "conveyor-01.motor_temperature": 10, "conveyor-01.vibration_feature": 10}。両候補のequipment20・precision20/20・clean0/未対応0は同じで、source増分25を誤警報25件へ変換しない。C1原モデル再計算0。

### 原対象窓の抜粋

#### cycle0 machine conveyor-01.conveyor_speed

| sample | score | streak |
| --- | --- | --- |
| 7297 | 165.7832506614489 | 1 |
| 7298 | 166.54818131564818 | 2 |
| 7299 | 165.62353566196802 | 3 |
| 7300 | 2.2243860860551807 | 0 |
| 7301 | 0.43874165635499446 | 0 |
| 7302 | 0.12218779969895693 | 0 |
| 7303 | 1.973353350261262 | 0 |

#### cycle0 sensor conveyor-01.motor_temperature

| sample | score | streak |
| --- | --- | --- |
| 7304 | 117.71079080474243 | 1 |
| 7305 | 117.11814184412272 | 2 |
| 7306 | 116.98989790545495 | 3 |
| 7307 | 0.9019373496709859 | 0 |
| 7308 | 0.8516698950805734 | 0 |
| 7309 | 1.0919758432651432 | 0 |
| 7310 | 1.489527978314834 | 0 |

#### cycle9 machine conveyor-01.conveyor_speed

| sample | score | streak |
| --- | --- | --- |
| 8917 | 165.75817775070522 | 1 |
| 8918 | 166.89457393131926 | 2 |
| 8919 | 166.0637561037054 | 3 |
| 8920 | 1.5957441571068298 | 0 |
| 8921 | 1.0311724417490693 | 0 |
| 8922 | 0.8061012022657325 | 0 |
| 8923 | 0.08327867410561683 | 0 |

#### cycle9 sensor conveyor-01.motor_temperature

| sample | score | streak |
| --- | --- | --- |
| 8924 | 116.95485164961896 | 1 |
| 8925 | 116.55936809133834 | 2 |
| 8926 | 116.35419966361432 | 3 |
| 8927 | 1.1451413296137831 | 0 |
| 8928 | 1.762518846352484 | 0 |
| 8929 | 1.8239345202892916 | 0 |
| 8930 | 1.1270927988251052 | 0 |

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
| 9 | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 0 | None |
| 9 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 20 | 1.0 |
| 9 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 20 | 1.0 |

同layout9 C0/C1 core＋過去9layouts C2 core＋今回を12セル比較。C2 coreは10layouts保存済み。同core C0は0/20検出・clean3、C1/C2は20/20・clean0。遅延は検出件だけの原値で未検出を補完しない。
旧56board＋今回1=57完了。同合成dev seed1で、57独立datasetではない。layout0–8の54cell完成を保持、layout9のcore C0/C1/C2が完成し、quality-stress3候補は未実行。旧manifest指標だけを使い、旧model再計算/replay/試験/CI反復0。bootstrap/統計CI/勝者/採択0。

## 保存・次unit

- model artifacts/representative-layout9-core-c2-20261012-records、analysis ...-analysis、docs/Git ...-save、最終 ...-final/root-closed.jsonとpost-save label優先。
- selected-windows {"bytes": 1752801, "parts": 7}、matched-targets {"bytes": 68589, "parts": 1}、unavailable-scores {"bytes": 816438, "parts": 4}、analysis {"bytes": 401297, "parts": 2}。
- DATA artifacts/representative-anomaly-evaluation/dev-layout9-core-c2-20261012/root-closed.json、{"bytes": 37811282, "files": 19, "manifest_pin": {"bytes": 2225, "sha256": "e65d5709f835ca2370169d2c839ff7bded26724d31439114e204e86b85011c37"}}。
- 次は同chunk009/同seed/layout9 quality-stress C1、新ID dev-layout9-quality-c1-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-09-quality-stress。同manifestからidentity/input10 metadataだけ選択、quality観測本文未読/次model未実行。元生成candidate C0/次実評価C1を別field保持。

prepare_result_indexで索引候補を作り、handoff/report/index3文書を継続送信承認内で一回[skip ci] Git保存。原返値/pins/HEAD-upstream-remote-cleanは-save/-finalへ保持。
C0閾値4.0の表記訂正は保存済み。今回閾値6.0は現在C2 configurationから取得。過去failed/helper/source変換失敗は原保存を保持し、今回successへ書き換えない。

実行900秒2GiB/output1GiB/single32MiB/files32、Git30秒16entry512KiB/stdout1MiBstderr128KiB、protocol/native不変。新検証16MiB512files/part256KiB/失敗予備枠維持。closed/frozen root追記整理0/fullstdio-native回収claim0。
ACTIVE。旧完成CI381385/4130再照会downloadverifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了/create_native早期拒否/7役reader禁止/追加agent禁止/caps-unknown原owner保持。未完了formal/nativeをdev開始条件へ戻さない。Sol容量/人停止は原保全後PAUSED、重複再試行なし。
