# layout9 C0 core実評価（2026-10-12）

同保存dev coreを既存CLI C0で一回fresh評価。exit0/complete/1cell success。機械0/10・sensor0/10・precision0/3・clean誤警報3。処理成功を性能合格・採択・正式受入へしない。

## 入力と結果の対応

- run dev-layout9-core-c0-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-09-core。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\009\attempt-0001\result\payload\manifest.json、pin {"bytes": 75699, "sha256": "7a71c5434cc8f526ada42d7a3f885bf711cabc256a7ff891c95a8969c6c58e5c"}。
- seed2486912926863618161/layout9/core/dev。input10 pins→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics。元payload書込み/生成/replay/追加agent0。
- actual checkout 35e523bb2e17a1d88c5a6b6c9f380d3beb1b7c94、計算661b27511826fcc87cb4a02930f276afbb8f95d9不変。declared16/candidate/compiled config照合はfull loaded runtime/native認証ではない。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 34.972124799969606秒/privatepeak 148664320B。
- observations {"bytes": 9600601, "sha256": "03d6fbac9cd83c2995cb6859d6f32fd4852d177776c9d3d41e63f33131c88e5d"}、configuration {"bytes": 5503, "sha256": "a45b3991c4d58a319d0c88b8effd1d67ad26586e11a1e8a68fc31e045f84f9de"}、manifest {"bytes": 8032, "sha256": "fada1a28edae282d511cbf319bf609595f57ab7a2679c03f6689d293c5d8869c"}、evaluation {"bytes": 13899152, "sha256": "88b55cc240f890ffd3470ed819f2b6a92ff622c42f1708a77e7a5857cbd20b51"}。
- 原設定thresholds {"c0-diff-control": 4.0, "c1-phase-level": 6.0, "c2-phase-conditional": 6.0}、今回C0 threshold 4.0/operator >/persistence 2。原14400scoreのthreshold_exceededを実閾値へ照合。GT/matching/config/science変更0。

## 原指標と状態

| 指標 | 原値 |
| --- | --- |
| machine recall | 0/10 |
| sensor recall | 0/10 |
| precision | 0/3 |
| clean_rate | 3/3365、value 25.676077265973255 |
| effective clean | 3255秒、value 26.543778801843317 |
| burden | 3/20、value 15.0 |
| detected delay | count0、min/max/mean/median null |

原clean_rate/burdenを単純確率へ換算しない。3source/3equipmentは全clean・unmatched、clean3と全未対応3を別に保持。全20incidentはcandidate_count0/no_candidate_in_window/causal_detected false/matched null/delay null。

48calibrated/原fit samples各0/calibration各290。14400scores、利用可能13920/不能480は全mode_recipe_or_phase。不能score/residual null・threshold_exceeded false。18000observations/mask対応、欠測0。対象全20窓は各7rows全利用可でphase不能も0。最大streakは全1で固定persistence2不成立。欠測・phase不能を今回全20missの理由へ補わない。

## 原対象窓の抜粋

### cycle0 machine conveyor-01.conveyor_speed

| sample | score | streak |
| --- | --- | --- |
| 7297 | 112.42986421742951 | 1 |
| 7298 | 0.43107591134641715 | 0 |
| 7299 | 0.4019799128053242 | 0 |
| 7300 | 113.4968258622553 | 1 |
| 7301 | 1.5207942030758337 | 0 |
| 7302 | 0.1539324615554391 | 0 |
| 7303 | 1.3327267711648838 | 0 |

### cycle0 sensor conveyor-01.motor_temperature

| sample | score | streak |
| --- | --- | --- |
| 7304 | 163.67997985965664 | 1 |
| 7305 | 1.0102196467589741 | 0 |
| 7306 | 0.040094830945744946 | 0 |
| 7307 | 164.41211782559895 | 1 |
| 7308 | 0.08347881106942702 | 0 |
| 7309 | 0.9321202852797177 | 0 |
| 7310 | 0.9068727352029627 | 0 |

### cycle9 machine conveyor-01.conveyor_speed

| sample | score | streak |
| --- | --- | --- |
| 8917 | 112.47830336583873 | 1 |
| 8918 | 0.7007421771547485 | 0 |
| 8919 | 0.4239238223195644 | 0 |
| 8920 | 111.19580376533979 | 1 |
| 8921 | 2.071342510666457 | 0 |
| 8922 | 1.3424796198379074 | 0 |
| 8923 | 0.4548078431174066 | 0 |

### cycle9 sensor conveyor-01.motor_temperature

| sample | score | streak |
| --- | --- | --- |
| 8924 | 163.0216786818039 | 1 |
| 8925 | 0.6460155396455997 | 0 |
| 8926 | 0.129690844692103 | 0 |
| 8927 | 163.90630611213007 | 1 |
| 8928 | 0.8419914498597701 | 0 |
| 8929 | 0.712454303727509 | 0 |
| 8930 | 0.3187605662892527 | 0 |

原全20event/incident・全4target窓・episodes・不能480を新analysisへ保存。入力対応・保存・状態分類の実経路不具合は観測なし。

## C0 coreの10 layouts保存比較

| layout | machine | sensor | precision | clean |
| --- | --- | --- | --- | --- |
| 0 | 0/10 | 0/10 | 0/3 | 3 |
| 1 | 0/10 | 0/10 | 0/3 | 2 |
| 2 | 0/10 | 0/10 | 0/3 | 3 |
| 3 | 0/10 | 0/10 | 0/3 | 3 |
| 4 | 0/10 | 0/10 | 0/3 | 3 |
| 5 | 0/10 | 0/10 | 0/3 | 3 |
| 6 | 0/10 | 0/10 | 0/3 | 3 |
| 7 | 0/10 | 0/10 | 0/3 | 3 |
| 8 | 0/10 | 0/10 | 0/3 | 3 |
| 9 | 0/10 | 0/10 | 0/3 | 3 |

旧9layouts C0 core manifest指標だけと比較。宣言calculator16/candidate/compiledconfig一致、入力layout pin差保持。旧54board＋今回1=55完了。同合成dev seed1で、55独立datasetではない。layout0–8の54cellが完成、layout9は今回C0 core一件だけ。旧model再計算0/bootstrap/統計CI/勝者/採択0。

## C0閾値の文書表記訂正

直前layout8 C0 quality報告のthreshold6表記は誤りだった。保存configurationのcandidate/compiled両fieldはC0 4.0/C1 6.0/C2 6.0。誤った一文だけを実設定へ訂正し、今回照合注記を追加。元doc bytes/Git/raw artifactを保持し、旧モデルを再計算せず指標や原結果を変更していない。新しい文書生成は現在candidateの閾値を保存configurationから取得する。

## 保存・次unit

- model artifacts/representative-layout9-core-c0-20261012-records、analysis ...-analysis、docs/Git ...-save、最終 ...-final/root-closed.jsonとpost-save label優先。
- selected-windows {"bytes": 943141, "parts": 4}、unavailable-scores {"bytes": 463420, "parts": 2}、analysis {"bytes": 380888, "parts": 2}。
- DATA artifacts/representative-anomaly-evaluation/dev-layout9-core-c0-20261012/root-closed.json、{"bytes": 26940319, "files": 19, "manifest_pin": {"bytes": 2225, "sha256": "8246905de12be6d101d867c965f2b845f5366fd68c81fb1d17db63e5c396c2bb"}}。
- 次は同chunk009/同layout9 core C1、新ID dev-layout9-core-c1-20261012。同manifest/input10、本文は今回C0で読取済み/次model未実行。元生成candidate C0/次実評価C1を別field保持。

修正済みprepare_result_indexで索引を作り、handoff/新report/index/直前reportの閾値訂正4文書を継続送信承認内で一回[skip ci] Git保存。原結果/pins/HEAD-upstream-remote-cleanは-save/-finalへ保持。

実行900秒2GiB/output1GiB/single32MiB/files32、Git30秒16entry512KiB/stdout1MiBstderr128KiB、protocol/native不変。新検証16MiB512files/part256KiB/失敗予備枠維持。closed/frozen root追記整理0/fullstdio-native回収claim0。
ACTIVE。旧完成CI381385/4130再照会downloadverifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了/create_native早期拒否/7役reader禁止/追加agent禁止/caps-unknown原owner保持。未完了formal/nativeをdev開始条件へ戻さない。Sol容量/人停止は原保全後PAUSED、重複再試行なし。
