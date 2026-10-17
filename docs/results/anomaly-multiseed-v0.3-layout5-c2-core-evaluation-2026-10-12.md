# dev layout5 C2 core実評価・core3候補比較（2026-10-12 JST）

## 入力と実評価

同保存chunk005/dev seed2486912926863618161/layout5/coreを既存CLI C2 c2-phase-conditional、新ID dev-layout5-core-c2-20261012で1cell実compute_evaluation。input10 pins→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics保存。元生成identity candidate C0と実評価C2別field。元payload書込み・生成・replay・production/test変更・類似owner・追加agent・holdout本文読取り0。

input manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\005\attempt-0001\result\payload\manifest.json
manifest 75699B/765ddbc639d74063b00c79b28a1e534bdb5d7859bee66d0bd4d1add2d69fc9a6、dataset anomaly-v03-dev-seed-2486912926863618161-layout-05-core。actual文書checkout9a0bb04fdbd49264eac39565977a707bd445622e、計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。actualPython3.14.0 Windows AMD64、elapsed30.3346959000919秒/OScheckpoint sampled privatepeak205369344B。

## 原結果とtarget onset

CLI exit0/complete/1cell success。性能合格・候補採択・正式受入は未判定。

- 機械10/10・sensor10/10・precision20/20・clean誤警報0・未対応equipment0。
- 48calibrated、fit_samples各600/calibration各290/C2stateあり48、14400scores、利用可能13920/不能480。全不能mode_recipe_or_phase/score-residual null/thresholdfalse。
- mask-observation18000行対応、non-ok0/欠測0。
- source40/equipment20/events40/incidents20、全20causal_detected・原target source/equipment対応・support2。
- 検出delay20件min/max/mean/median全1秒。未検出0、補完forbidden。

全20対象窓phase不能0（machine10・sensor10とも0）。cycle00 current・temperatureはevent startの利用可能score超過/streak1→次sample超過/streak2、target source onset start+1000ms。前layout4のmachine phase1/2秒を流用しない。原全20event-incident・target source-equipment・全60episodes・5選択motor4target窓をEXTRACT保存、全20target onsetとcycle00原target rowsをproof保存。
GT/固定C2 threshold6/persistence2/first-equipment-onset-no-retry-v1/config/science変更0。入力対応・保存・状態分類の実経路不具合は観測なし。

### cycle00 machine motor-01.motor_current

| sample | available | primary | score | residual | threshold | streak |
| ---: | --- | --- | ---: | ---: | --- | ---: |
| 7355 | True | None | 0.6390998466780761 | 0.6832483081179913 | False | 0 |
| 7356 | True | None | 0.402721920145217 | 0.4422999161818503 | False | 0 |
| 7357 | True | None | 30.0291256263067 | -30.57796004427639 | True | 1 |
| 7358 | True | None | 30.676213276443775 | -31.237559402935588 | True | 2 |
| 7359 | True | None | 30.447180006085947 | -31.004097679152665 | True | 3 |
| 7360 | True | None | 0.07917901649753109 | -0.04891877525738335 | False | 0 |
| 7361 | True | None | 0.5372489625044101 | -0.5158456939571701 | False | 0 |
| 7362 | True | None | 1.4406598388731484 | 1.5003067957382412 | False | 0 |
| 7363 | True | None | 1.0265136698049298 | 1.0781529384506028 | False | 0 |
| 7364 | True | None | 21.531338786549366 | -21.91586496590619 | True | 1 |
| 7365 | True | None | 24.767851387496105 | -25.214956882472134 | True | 2 |
| 7366 | True | None | 23.292273902167448 | -23.710848493494915 | True | 3 |

### cycle00 sensor motor-01.motor_temperature

| sample | available | primary | score | residual | threshold | streak |
| ---: | --- | --- | ---: | ---: | --- | ---: |
| 7362 | True | None | 0.7517922466580435 | -0.9966855351545388 | False | 0 |
| 7363 | True | None | 1.278739905378449 | -1.5877853928063987 | False | 0 |
| 7364 | True | None | 146.7303905130011 | 164.44042343144105 | True | 1 |
| 7365 | True | None | 147.81507560251688 | 165.65716135863252 | True | 2 |
| 7366 | True | None | 148.01386781341367 | 165.88015513347673 | True | 3 |
| 7367 | True | None | 0.6230048649794417 | -0.8522191887958975 | False | 0 |
| 7368 | True | None | 0.13202098027126952 | -0.30146144358624133 | False | 0 |
| 7369 | True | None | 0.3224400634599359 | -0.5150627208750359 | False | 0 |
| 7370 | True | None | 0.07237987972908781 | -0.07217620576296087 | False | 0 |
| 7371 | True | None | 0.3606587865255704 | -0.5579343066765378 | False | 0 |
| 7372 | True | None | 0.2497355100608874 | -0.4335068956358119 | False | 0 |
| 7373 | True | None | 0.49868953893869883 | -0.7127693396304852 | False | 0 |


## 保存指標によるcore3候補比較

同layout5 core C0/C1/C2比較を完成。同input10 pins全一致、8cell宣言16calculator source/candidate config/compiled config一致。他layout入力差を保持。

- C0機械sensor0/10・precision0/3・clean3・source3/equipment3・delaynull。
- C1機械sensor10/10・precision20/20・clean0・source30/equipment20・delay全1秒。
- C2機械sensor10/10・precision20/20・clean0・source40/equipment20・delay全1秒。

C1/C2の同指標と異なるsource数を別保存し、原profiles/scores/episodesの一致は未宣言。旧7cell（同layout5 C0/C1と旧layout0–4 C2）はmanifest/config指標だけ比較、旧result本文再展開・再compute0。旧layout0 C2機械4/10/precision14/20/未対応6、旧layout4 C2機械2秒・sensor1秒を原値のまま保持。
同seed6layout C2core+同layout5 C0/C1比較で8独立seed/datasetとは数えない。旧30cell比較は原閉鎖保存のまま保持。layout5 quality比較は未完了、bootstrap/統計CI/勝者/採択0。

| layout | candidate core | machine | sensor | precision | clean | unmatched | source/equipment | available/unavailable | delay median/mean秒 |
| ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| 5 | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 3 | 3/3 | 13920/480 | None/None |
| 5 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 0 | 30/20 | 13920/480 | 1.0/1.0 |
| 4 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 0 | 41/20 | 13920/480 | 1.5/1.5 |
| 3 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 0 | 30/20 | 13920/480 | 1.5/1.5 |
| 2 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 0 | 49/20 | 13920/480 | 1.0/1.0 |
| 1 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 0 | 40/20 | 13920/480 | 1.0/1.0 |
| 0 | c2-phase-conditional | 4/10 | 10/10 | 14/20 | 0 | 6 | 42/20 | 13920/480 | 1.0/1.2857142857142858 |
| 5 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 0 | 40/20 | 13920/480 | 1.0/1.0 |

## 保存状態と制限

DATA {'files': 19, 'bytes': 37792335, 'manifest_pin': {'bytes': 2254, 'sha256': 'a629fe97002bc8fce5bc0f703dd98cf45854a3bf552ebd2fa5e0c88457437fbe'}}、EXTRACT {'bytes': 233316, 'files': 7, 'manifest_pin': {'bytes': 1079, 'sha256': '9f9313c1b5918e2ef7ba8126651d4c239cf0b3747ecf5f379cc54562c435bb0f'}}閉鎖。MAIN representative-layout5-core-c2-20261012-prep/POST representative-layout5-core-c2-post-20261012-prep最終post-save・owners-after-save・root-closed優先。117science-source/旧132root count-byte-closurepin/外部固定C1 MAIN35files capfalse/旧C2cache補足不変。前qualityC1 false13/raw12失敗・別訂正文書Git、前qualityC2 docs準備0対最終foreground4、全原failed/Git未知返値/lsremote128/continuationsを保持。今回foreground failure0、元166helpers原11failed155passed/full saved identity一致/CIM同original不在/repohelpercriticalなし/model-analysis2passed。foreground fullcreation/fullstdioNone、selectedCLIをhelper全stdioにしない、PID単独判定/native回収claim0。CIMdecimal100ns→microsecondtrunc/fulltoken維持。
metadata512KiB32entry/reserve128KiB/single128KiB、script/失敗/閉鎖分を含め新書込み前に件数bytes確認、Python-B/recursive/限定文字列置換。閉鎖/外部固定root追記・raw整理移動削除・上限緩和0。
同GitHub同種dev結果・ユーザー名PC pathのリスク通知後継続承認内、handoff/report2一回[skip ci] commit/push。原Git/API・HEAD-upstream-ref-clean/docpinsはPOST保存。Git累積30秒/512KiB16entry/stdout1MiB/preflight別量。automation詳細転記/設定更新0、ACTIVE文書参照維持。
CI381385/4130保存維持、新query-download-verifier0/旧381365inprogress履歴/doc-onlyCI追跡0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読、正式5残件・最終受入未完了。create_native早期拒否/全7役reader起動禁止/元caps-unknown原owner-stop/追加agent禁止。未完了formal/nativeを少量dev開始条件へ戻さず、engineering900秒2GiB/output1GiB/single32MiB/files32 checkpointの限界維持。Sol容量又は人の停止では保全後PAUSED・重複再試行0。

| 原保存 | bytes | SHA256 |
| --- | ---: | --- |
| observations | 9600600 | 072bbae0037c3d5b2d6d244c1263ef1369df3307d46ffcbc9056dfda68d789c7 |
| configuration | 5508 | 3d213cf442dcc078df130aec889de877b3ace3aacc1db015e076e0d5dcbbca74 |
| manifest | 8007 | 2d41f0b2a41829b232f361dcc3c243da973b18daa0ae352ac2ed17c1aa2e9ff1 |
| evaluation | 24751203 | b26f449b672eb6ce17170bfd7c4a5106a08a685a3b0b801df6ecc35a355f8ba9 |
| numerical | 24745705 | 0dafe50ff03996eb2711a75acf793a4ad3dfefd89ce91964595079e39c6e882b |
| target-onset-proof | 24776 | 2ebcac217eab4b616ea74270a98d7bf0e6cd741f2b14a9a6c6f978d53c13164b |

## 次の未完成unit

同chunk005/devseed/layout5/quality-stress、同765d manifest/保存済みquality10 pinsをC1 c1-phase-level、新ID dev-layout5-quality-c1-20261012で1cell実評価。dataset anomaly-v03-dev-seed-2486912926863618161-layout-05-quality-stress、元生成C0と実評価C1別field。次quality入力はcoreと別pins、nextmodel未開始/元payload書込み・生成0/quality観測本文未読。完成coreC0/C1/C2・旧30cell/replay/risk-owner/native/probe/collector/Git37/CI反復0。
