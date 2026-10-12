# layout9 C0 quality-stress実評価・10layouts×3候補×2条件比較（2026-10-12）

同保存dev quality-stressを既存CLI C0で一回fresh評価。exit0/complete/1cell success。機械0/10・sensor0/10・precision0/3・clean誤警報3。全20incident未検出、delayは原null。処理successを性能合格・採択・正式受入へしない。これにより同seedのlayout0–9で3候補×2条件の60cellが揃った。

## 入力と結果の対応

- run dev-layout9-quality-c0-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-09-quality-stress。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\009\attempt-0001\result\payload\manifest.json、pin {"bytes": 75699, "sha256": "7a71c5434cc8f526ada42d7a3f885bf711cabc256a7ff891c95a8969c6c58e5c"}。
- seed2486912926863618161/layout9/quality-stress/dev。input10 pins→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics。同C1/C2 quality input10 pins一致。元生成candidate C0/実評価candidate C0は別field保持。
- 元payload書込み/生成/replay/追加agent0。actual checkout 3cab343ae6198783fdc46d0c33b2306a25245255、計算661b27511826fcc87cb4a02930f276afbb8f95d9不変。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 16.316574200056493秒/privatepeak 148717568B。
- observations {"bytes": 9600605, "sha256": "366e4318ea59c94eadd2ffed97b5f5cfb2d235f9c89b28064f5f8adde2a9e184"}、configuration {"bytes": 5513, "sha256": "881bbd8174d1d7c99f42a1df676e33bbbdab7a3a6d6159894694b5cf946c9391"}、manifest {"bytes": 8065, "sha256": "f47b505e7e50da46cdf86104d566f05cfafff20dc9053efbba330de3f4f3aa5e"}、evaluation {"bytes": 14336324, "sha256": "81a93012d03f71468533d9ff72274bf70f235a2c0aa9f97c1b62a78619e89282"}。
- 保存configurationの閾値 {"c0-diff-control": 4.0, "c1-phase-level": 6.0, "c2-phase-conditional": 6.0}。今回C0 threshold 4.0/operator >/persistence 2。全14400scoreのthreshold_exceededを実4.0へ照合。GT/matching/config/science変更0。declared16/config一致はfull loaded runtime/native認証ではない。

## 原指標

| 指標 | 原値 |
| --- | --- |
| machine recall | 0/10 |
| sensor recall | 0/10 |
| precision | 0/3 |
| clean_rate | 3/3365、原value 25.676077265973255 |
| effective clean | 3255秒、原value 26.543778801843317 |
| burden | 3/20、原value 15.0 |
| detected delay | count0、min/max/mean/median原null |

48calibrated/原fit samples各0/calibration各290/C2 stateなし48、14400scores。source3/equipment3/events40/incidents20。source内訳 {"conveyor-01.motor_temperature": 1, "motor-01.vibration_feature": 2}。全equipment3はclean/未対応/matchednull。clean_rateとburdenの原valueは別定義の指標で、単純な確率へ変換しない。

## 未検出20件・欠測・persistence

原全20incidentはno_candidate_in_window/candidate0/causal_detected false/matchednull/delaynull。全対象窓のmaxstreak1、固定persistence2不成立。19対象窓は7rows全利用可でphase不能0。cycle09温度窓だけ利用3/不能4。欠測1窓で全20missを説明しない。
18000observations/mask対応、非ok観測30行。利用可能13880/不能520、排他的primary phase480＋current quality30＋previous quality10。重複tags {"current_nonfinite": 30, "current_target_quality": 30, "mode_recipe_or_phase": 480, "previous_target_quality_or_nonfinite": 30} を加算しない。全不能score/residual null・threshold_exceeded false。
cycle09温度8924はscore163.0216786818039/streak1、8925–8927 current quality不能、8928 previous quality不能でreset。原windowと非欠測cycle0の対象窓を以下に示す。

### cycle0 machine conveyor-01.conveyor_speed

| sample | available | score | streak | primary reason |
| --- | --- | --- | --- | --- |
| 7297 | True | 112.42986421742951 | 1 | None |
| 7298 | True | 0.43107591134641715 | 0 | None |
| 7299 | True | 0.4019799128053242 | 0 | None |
| 7300 | True | 113.4968258622553 | 1 | None |
| 7301 | True | 1.5207942030758337 | 0 | None |
| 7302 | True | 0.1539324615554391 | 0 | None |
| 7303 | True | 1.3327267711648838 | 0 | None |

### cycle0 sensor conveyor-01.motor_temperature

| sample | available | score | streak | primary reason |
| --- | --- | --- | --- | --- |
| 7304 | True | 163.67997985965664 | 1 | None |
| 7305 | True | 1.0102196467589741 | 0 | None |
| 7306 | True | 0.040094830945744946 | 0 | None |
| 7307 | True | 164.41211782559895 | 1 | None |
| 7308 | True | 0.08347881106942702 | 0 | None |
| 7309 | True | 0.9321202852797177 | 0 | None |
| 7310 | True | 0.9068727352029627 | 0 | None |

### cycle9 machine conveyor-01.conveyor_speed

| sample | available | score | streak | primary reason |
| --- | --- | --- | --- | --- |
| 8917 | True | 112.47830336583873 | 1 | None |
| 8918 | True | 0.7007421771547485 | 0 | None |
| 8919 | True | 0.4239238223195644 | 0 | None |
| 8920 | True | 111.19580376533979 | 1 | None |
| 8921 | True | 2.071342510666457 | 0 | None |
| 8922 | True | 1.3424796198379074 | 0 | None |
| 8923 | True | 0.4548078431174066 | 0 | None |

### cycle9 sensor conveyor-01.motor_temperature

| sample | available | score | streak | primary reason |
| --- | --- | --- | --- | --- |
| 8924 | True | 163.0216786818039 | 1 | None |
| 8925 | False | None | 0 | current_target_quality |
| 8926 | False | None | 0 | current_target_quality |
| 8927 | False | None | 0 | current_target_quality |
| 8928 | False | None | 0 | previous_target_quality_or_nonfinite |
| 8929 | True | 0.712454303727509 | 0 | None |
| 8930 | True | 0.3187605662892527 | 0 | None |

原全20event/incident・四target窓・全episodes・不能520・非ok30を新analysisへ保存。入力対応・保存・状態分類の実経路不具合観測なし。

## 同seed10layouts・3候補×2条件の保存比較

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

旧59board＋今回1=60完了、layout0–9/core-quality/3candidateの60unique組を確認。1合成dev seedで、60独立datasetではない。各同layout-stratumの候補は入力を共有する。元生成C0と実評価candidateを別field保持し、遅延は検出件のみの原値、未検出はnull。
同layout9 quality C0は0/20・clean3、C1/C2は19/20・clean0。C0/C1利用13880、C2利用13760。C2 peer不能120を元指標で保持。core/quality共通inputは ["origins.json", "split-manifest.json", "targets.json"]、他7pins差。閾値C0 4.0/C1-C2 6.0、persistence2・科学式・GT・matchingは固定。同input10/宣言16/candidate/compiledconfig対応を保存manifestで照合、旧結果bodyの再計算0。
旧model/replay/試験/CI反復0、bootstrap/統計CI/勝者/採択0。60cellの完了はこの保存比較の完了で、正式受入完了ではない。

## 保存と次unit

- model artifacts/representative-layout9-quality-c0-20261012-records、分析 ...-analysis、docs/Git ...-save、最終 ...-final/root-closed.json post-save label優先。
- selected-windows {"bytes": 974333, "parts": 4}、unavailable-scores {"bytes": 520120, "parts": 2}、non-ok-input-records {"bytes": 22023, "parts": 1}。-save/ten-layout-comparison-summaryは全60原manifest指標対応。
- DATA artifacts/representative-anomaly-evaluation/dev-layout9-quality-c0-20261012/root-closed.json、{"bytes": 27383924, "files": 19, "manifest_pin": {"bytes": 2235, "sha256": "9d70d581446a751986450f349eb438e63a9e241198fe2b4f0a5968d96e5cd716"}}。
- 次は保存済みchunk010/同seed/layout10 core C0、新ID dev-layout10-core-c0-20261012。新manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\010\attempt-0001\result\payload\manifest.json、pin {"bytes": 75715, "sha256": "1ede2721456af4d88ae82d606decb08b3e8fb2121295e9aea89ffddeda0b0c63"}。dev identity/input10 metadataだけ選択、観測本文未読/次model未実行。新独立seedではない。

prepare_result_indexでhandoff/report/index3文書を準備、継続送信承認内で一回[skip ci] Git保存。原返値/pins/HEAD-upstream-remote-cleanは-save/-final保存。旧C0閾値誤記訂正とC1 fingerprint期待failure/continuationは原保持。今回helper failure0。
実行900秒2GiB/output1GiB/single32MiB/files32、Git30秒16entry512KiB/stdout1MiBstderr128KiB、protocol/native不変。新検証16MiB512files/part256KiB/失敗予備枠維持。closed/frozen root追記整理0/fullstdio-native回収claim0。
ACTIVE/automation詳細転記0。CI381385/4130再照会downloadverifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了/create_native早期拒否/7役reader禁止/追加agent禁止/caps-unknown原owner保持。未完了formal/nativeをdev開始条件へ戻さない。Sol容量/人停止は原保全後PAUSED、重複再試行なし。
