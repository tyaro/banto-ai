# dev layout5 C1 core実評価（2026-10-12 JST）

## 入力と実評価

同保存chunk005/dev seed2486912926863618161/layout5/coreを既存CLI C1 c1-phase-level、新ID dev-layout5-core-c1-20261012で1cell実compute_evaluation。input10 pins→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metricsを保存。元生成identity candidate C0と実評価C1は別field。元payload書込み・生成・replay・production/test変更・類似owner・追加agent・holdout本文読取り0。

input manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\005\attempt-0001\result\payload\manifest.json
manifest 75699B/765ddbc639d74063b00c79b28a1e534bdb5d7859bee66d0bd4d1add2d69fc9a6、dataset anomaly-v03-dev-seed-2486912926863618161-layout-05-core。actual文書checkout78a987cde395a453d08976e0f376947a4d118ce4、計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。actualPython3.14.0 Windows AMD64、elapsed18.44782360002864秒/OScheckpoint sampled privatepeak147243008B。

## 原結果とtarget onset

CLI exit0/complete/1cell success。性能合格・候補採択・正式受入は未判定。

- 機械10/10・sensor10/10・precision20/20・clean誤警報0・未対応equipment0。
- 48calibrated、fit_samples各600/calibration各290、14400scores、利用可能13920/不能480。全不能mode_recipe_or_phase/score-residual null/thresholdfalse。
- mask-observation18000行対応、non-ok0/欠測0。
- source30/equipment20/events40/incidents20、全20causal_detected・原target source/equipment対応・support2。
- 検出delay20件min/max/mean/median全1秒。未検出0、補完forbidden。

全20対象窓phase不能0（machine10・sensor10とも0）。cycle00 currentとtemperatureはevent startの利用可能score超過/streak1→次sample超過/streak2、原target source onsetがstart+1000ms。前layout4 machine phase1/2秒をこのlayoutへ流用しない。原全20event-incident・target source-equipment・全50episodes・5選択motor4target窓を保存し、全20target onsetとcycle00原target score rowsをproofへ保持。
GT/固定C1 threshold6/persistence2/first-equipment-onset-no-retry-v1/config/science変更0。入力対応・保存・状態分類の実経路不具合は観測なし。

### cycle00 machine motor-01.motor_current

| sample | available | primary | score | residual | threshold | streak |
| ---: | --- | --- | ---: | ---: | --- | ---: |
| 7355 | True | None | 0.5300773923900349 | 0.039375999999999856 | False | 0 |
| 7356 | True | None | 0.20667160146511726 | 0.012987499999999486 | False | 0 |
| 7357 | True | None | 27.36713273805944 | -2.2369145 | True | 1 |
| 7358 | True | None | 27.929662847897188 | -2.2828144999999997 | True | 2 |
| 7359 | True | None | 27.74383795050253 | -2.267652 | True | 3 |
| 7360 | True | None | 0.05703736669248063 | -0.00853000000000037 | False | 0 |
| 7361 | True | None | 0.5430253893626487 | -0.04818449999999963 | False | 0 |
| 7362 | True | None | 1.3636330384806654 | 0.10739050000000017 | False | 0 |
| 7363 | True | None | 0.7992707227296013 | 0.061340999999999646 | False | 0 |
| 7364 | True | None | 1.0737461985449845 | 0.08373699999999928 | False | 0 |
| 7365 | True | None | 2.0272224791620226 | -0.16928849999999995 | False | 0 |
| 7366 | True | None | 0.5126009667554087 | -0.045701999999999465 | False | 0 |

### cycle00 sensor motor-01.motor_temperature

| sample | available | primary | score | residual | threshold | streak |
| ---: | --- | --- | ---: | ---: | --- | ---: |
| 7362 | True | None | 0.5331113858559138 | -0.043658999999998116 | False | 0 |
| 7363 | True | None | 1.1479249336309445 | -0.07823099999999883 | False | 0 |
| 7364 | True | None | 141.93954270670326 | 7.967817999999998 | True | 1 |
| 7365 | True | None | 142.53529226850083 | 8.001318000000001 | True | 2 |
| 7366 | True | None | 142.94762209954064 | 8.024503999999997 | True | 3 |
| 7367 | True | None | 0.5716305963291313 | -0.04582499999999712 | False | 0 |
| 7368 | True | None | 0.21569246261643654 | -0.02580999999999989 | False | 0 |
| 7369 | True | None | 0.21434980315630742 | -0.025734500000002214 | False | 0 |
| 7370 | True | None | 0.1267924011410787 | -0.0065515000000004875 | False | 0 |
| 7371 | True | None | 0.1568110656280951 | -0.022499000000003377 | False | 0 |
| 7372 | True | None | 0.2910503362916054 | -0.030047500000002003 | False | 0 |
| 7373 | True | None | 0.49897582514343736 | -0.04173950000000204 | False | 0 |


## 保存指標の比較

同layout5 core C0と旧layout0–4 C1は保存manifest/configだけ読み、旧6result本文再展開・再compute0。同layout5 C0/C1 input10 pins全一致、全7cell宣言16calculator source/candidate config/compiled config一致、他layout入力差を保持。C0両0/10/precision0/3/clean3/delaynullとC1両10/10/precision20/20/clean0/delay1秒を別保存。処理successから原予測同一や勝者を推定しない。
同seed6layoutのC1coreと同layout5 C0比較であり、7独立seed/datasetではない。旧30cell比較と完成C0core保存は不変。layout5のC2/quality比較は未完了。bootstrap/統計CI/勝者/採択0。

| layout | candidate core | machine | sensor | precision | clean | available/unavailable | delay median/mean秒 |
| ---: | --- | --- | --- | --- | ---: | --- | --- |
| 5 | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13920/480 | None/None |
| 4 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920/480 | 1.5/1.5 |
| 3 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920/480 | 1.5/1.5 |
| 2 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920/480 | 1.0/1.0 |
| 1 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920/480 | 1.0/1.0 |
| 0 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920/480 | 1.5/1.5 |
| 5 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920/480 | 1.0/1.0 |

## 保存状態と制限

DATA {'files': 19, 'bytes': 27113536, 'manifest_pin': {'bytes': 2248, 'sha256': 'b05c1d516036dd45b620fdfae5508f29821758e34a0de240c368ce97e8d1b32b'}}、EXTRACT {'bytes': 214578, 'files': 6, 'manifest_pin': {'bytes': 950, 'sha256': '9d5a795275de9a0cc177c826ecc840295c1375c933cd840a8a4d9e9c7e9e0339'}}閉鎖。MAIN representative-layout5-core-c1-20261012-prep/POST representative-layout5-core-c1-post-20261012-prep最終post-save・owners-after-save・root-closed優先。117science-source/旧128root count-byte-closurepin/外部固定C1 MAIN35files capfalse/旧C2cache補足不変。前qualityC1 false13/raw12失敗・別訂正文書Git、前qualityC2 docs準備0対最終foreground4、全原failed/Git未知返値/lsremote128/continuationsを保持。今回foreground failure0、元163helpers原11failed152passed/full saved identity一致/CIM同original不在/repohelpercriticalなし/model-analysis2passed。foreground fullcreation/fullstdioNone、selectedCLIをhelper全stdioにしない、PID単独判定/native回収claim0。CIMdecimal100ns→microsecondtrunc/fulltoken維持。
metadata512KiB32entry/reserve128KiB/single128KiB、script/失敗/閉鎖分を含め新書込み前に件数bytes確認、Python-B/recursive/限定文字列置換。閉鎖/外部固定root追記・raw整理移動削除・上限緩和0。
同GitHub同種dev結果・ユーザー名PC pathのリスク通知後継続承認内、handoff/report2一回[skip ci] commit/push。原Git/API・HEAD-upstream-ref-clean/docpinsはPOST保存。Git累積30秒/512KiB16entry/stdout1MiB/preflight別量。automation詳細転記/設定更新0、ACTIVE文書参照維持。
CI381385/4130保存維持、新query-download-verifier0/旧381365inprogress履歴/doc-onlyCI追跡0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読、正式5残件・最終受入未完了。create_native早期拒否/全7役reader起動禁止/元caps-unknown原owner-stop/追加agent禁止。未完了formal/nativeを少量dev開始条件へ戻さず、engineering900秒2GiB/output1GiB/single32MiB/files32 checkpointの限界を維持。Sol容量又は人の停止では保全後PAUSED・重複再試行0。

| 原保存 | bytes | SHA256 |
| --- | ---: | --- |
| observations | 9600600 | 072bbae0037c3d5b2d6d244c1263ef1369df3307d46ffcbc9056dfda68d789c7 |
| configuration | 5502 | 3228b177ac6f076098457b4a40940c45bcf5cae346ba9c266fa3805280a8d04f |
| manifest | 8002 | 6d2a9531ce48d79b9d010b0ff8d819f465a0abe2dc33ba5bc072bb9f72664841 |
| evaluation | 14072439 | 25bcd36b75b432dacf10b4e751992aee9e87bb58ea3a7731de49ed4d0e64bc67 |
| numerical | 14066941 | c032c7174e43d64c77b9aa6eef36029d09cff0da81a7e3025238cf066ef0f87d |
| target-onset-proof | 24033 | df9bfbc6db1dc601fbe2ea6b947f8a4835d81ce9aeece87a435e0e48e6a117bc |

## 次の未完成unit

同chunk005/devseed/layout5/core、同765d manifest/同input10 pinsをC2 c2-phase-conditional、新ID dev-layout5-core-c2-20261012で1cell実評価。元生成C0と実評価C2別field。nextmodel未開始/元payload書込み・生成0/quality観測本文未読。完成C0/C1core・旧30cell/replay/risk-owner/native/probe/collector/Git37/CI反復0。
