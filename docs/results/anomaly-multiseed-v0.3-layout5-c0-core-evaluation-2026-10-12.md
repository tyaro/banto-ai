# dev layout5 C0 core実評価（2026-10-12 JST）

## 入力・設定・実評価

同保存chunk005/dev seed2486912926863618161/layout5/coreを既存CLI C0 c0-diff-control、新ID dev-layout5-core-c0-20261012で1cell実compute_evaluation。input10pins→新snapshot→fresh calibration→原profiles/scores/episodes/events/incidents/metricsを保存。元生成identity candidateと実評価candidateは別field（今回は両C0）。元payload書込み・新dataset生成・replay・production/test変更・類似owner・追加agent・holdout本文読取り0。

input manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\005\attempt-0001\result\payload\manifest.json
manifest 75699B/765ddbc639d74063b00c79b28a1e534bdb5d7859bee66d0bd4d1add2d69fc9a6、dataset anomaly-v03-dev-seed-2486912926863618161-layout-05-core。actual文書checkout2faf56c4d64bdd9f5bd3287ad0fe8ea512c2dddf、計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。actualPython3.14.0 Windows AMD64、elapsed18.35416190000251秒/OScheckpoint sampled privatepeak145989632B。

## 原結果

CLI exit0/complete/1cell success。性能合格・勝者・採択・正式受入は未判定。

- 機械0/10・sensor0/10・precision0/3・clean誤警報3・未対応equipment3（全clean）。
- 48calibrated、fit_samples各0/calibration各290、14400scores。利用可能13920・不能480（全mode_recipe_or_phase、score/residual null・thresholdfalse）。
- mask-observation18000行全対応、non-ok0/欠測0。
- source3/equipment3/events40/incidents20、全20no_candidate_in_window/candidate0/causalfalse/matched-source-equipment null/support[]/delaynull。
- delay count0/min/max/mean/median原null、未検出delay補完forbidden。
- clean_rate原3/3365/value25.676077265973255、effective_clean_seconds3255/value26.543778801843317。false_alert_burden原3/20/value15.0は単純な確率へ変換しない。

## 全20target窓の原状態

全20event-incidentとmotor4target窓、全6source-equipment episodesをEXTRACTへ保存。対象窓最大streakは各1、固定C0 threshold4/persistence2が成立しない。機械10・sensor10の対象窓phase不能は全て0。layout4の機械窓phase1をこのlayoutへ流用しない。原窓内の利用可能scoreでも連続2超過がないことを保持し、phaseや欠測だけで全missを説明しない。
GT/固定config/threshold/persistence/first-equipment-onset-no-retry-v1/science変更0。入力対応・保存・状態分類の実経路不具合は観測なし。

### cycle00 machine motor-01.motor_current

| sample | available | primary | score | residual | threshold | streak |
| ---: | --- | --- | ---: | ---: | --- | ---: |
| 7355 | True | None | 0.014047911070767475 | -0.0011169999999998126 | False | 0 |
| 7356 | True | None | 0.33477915825149807 | -0.03385700000000025 | False | 0 |
| 7357 | True | None | 21.871128090431373 | -2.232271 | True | 1 |
| 7358 | True | None | 0.7183243564683505 | -0.0730090000000001 | False | 0 |
| 7359 | True | None | 0.37538487051675207 | 0.038636000000000115 | False | 0 |
| 7360 | True | None | 22.147677971552696 | 2.2611349999999995 | True | 1 |
| 7361 | True | None | 0.30701641070994445 | -0.031022999999999357 | False | 0 |
| 7362 | True | None | 1.316242245035118 | 0.13467800000000008 | False | 0 |
| 7363 | True | None | 0.10910152412497877 | -0.010820000000000718 | False | 0 |
| 7364 | True | None | 0.051646155624207615 | -0.004954999999999821 | False | 0 |
| 7365 | True | None | 2.06203545969206 | -0.21017399999999986 | False | 0 |
| 7366 | True | None | 0.584447959890117 | 0.05997700000000039 | False | 0 |

### cycle00 sensor motor-01.motor_temperature

| sample | available | primary | score | residual | threshold | streak |
| ---: | --- | --- | ---: | ---: | --- | ---: |
| 7362 | True | None | 0.5745573518034776 | -0.16489999999999938 | False | 0 |
| 7363 | True | None | 0.45135541797920115 | -0.15098000000000056 | False | 0 |
| 7364 | True | None | 71.01286447244391 | 7.923421999999999 | True | 1 |
| 7365 | True | None | 0.38663899986691325 | -0.05629899999999566 | False | 0 |
| 7366 | True | None | 0.31593064862241954 | -0.06428800000000479 | False | 0 |
| 7367 | True | None | 70.99302117247021 | -8.121146999999997 | True | 1 |
| 7368 | True | None | 0.43614989195114057 | -0.050705000000000666 | False | 0 |
| 7369 | True | None | 0.34948370401956513 | -0.06049700000000158 | False | 0 |
| 7370 | True | None | 0.5288965201512236 | -0.040225999999996986 | False | 0 |
| 7371 | True | None | 0.4129433207954244 | -0.05332700000000301 | False | 0 |
| 7372 | True | None | 0.6191118442511261 | -0.030032999999999532 | False | 0 |
| 7373 | True | None | 0.5064157075137166 | -0.042766000000000304 | False | 0 |


## 同seed6layout C0 core比較

旧layout0–4 C0 coreは保存manifest/config指標だけ読み、旧result本文再展開・再compute0。同seed1、layout0–5のcore6条件の比較であり、6独立seedとは数えない。input10filename集合一致・入力pin差、全6cell宣言16calculator source/candidate config/compiled config一致を保存した。旧layout1 C0clean2/全未対応3/grace1を原値のまま残す。全6C0coreの機械sensor0/10を性能合格へしない。
旧layout0–4×2strata×3候補30cell比較は閉鎖済み保存のまま保持。今回layout5 C0 core1cellを実追加したが、6layout全候補比較の完成は未宣言。bootstrap/統計CI/勝者/候補採択0。

| layout C0 core | machine | sensor | precision | clean | unmatched | available/unavailable | delay median |
| ---: | --- | --- | --- | ---: | ---: | --- | --- |
| 0 | 0/10 | 0/10 | 0/3 | 3 | 3 | 13920/480 | None |
| 1 | 0/10 | 0/10 | 0/3 | 2 | 3 | 13920/480 | None |
| 2 | 0/10 | 0/10 | 0/3 | 3 | 3 | 13920/480 | None |
| 3 | 0/10 | 0/10 | 0/3 | 3 | 3 | 13920/480 | None |
| 4 | 0/10 | 0/10 | 0/3 | 3 | 3 | 13920/480 | None |
| 5 | 0/10 | 0/10 | 0/3 | 3 | 3 | 13920/480 | None |

## 保存状態と既存制限

DATA {'files': 19, 'bytes': 26940258, 'manifest_pin': {'bytes': 2249, 'sha256': 'e02455f0ffa0c64cc7833aa0f1b9af0c21453c40a88c74f9af09c936fcaef800'}}、EXTRACT {'bytes': 277133, 'files': 7, 'manifest_pin': {'bytes': 1066, 'sha256': '0318928b55820e72e8ccb1635396bc497b183356ab7fa41d1d5f73d56781e068'}}閉鎖。MAIN representative-layout5-core-c0-20261012-prep/POST representative-layout5-core-c0-post-20261012-prepの最終post-save・owners-after-save・root-closedを優先。117science-source/旧124root count-byte-closurepin/外部固定C1 MAIN35files capfalse/旧C2cache補足不変。前qualityC1 false13/raw12失敗と別訂正文書Git、前qualityC2 docs準備0と最終foreground4を区別して原保存保持。元failed labels/Git unknown return/lsremote128/continuationsは書換えず、元helper/model/Git/CI/nativeを反復しない。今回current foreground failure0。
元160helpers原11failed149passed/full saved identity一致/CIM同original不在/repository helpercriticalなし。今回model/analysis2passed。foreground fullcreation/fullstdioNone、selectedCLIをhelper全stdioにしない、PID単独判定/native回収claim0。CIMdecimal100ns→microsecondtrunc/fulltokenを維持。
metadata512KiB32entry/reserve128KiB/single128KiB、script・失敗証拠・閉鎖分を含め新書込み前に件数bytes確認、Python-B/recursive/限定文字列置換。閉鎖/外部固定root追記・raw整理移動削除・上限緩和0。
同GitHub同種合成dev結果・ユーザー名PC内pathの送信はリスク通知後の人の継続承認内。handoff/report2一回[skip ci] commit/push、原Git/API・HEAD-upstream-ref-clean/docpinsはPOST保存。Git累積30秒/512KiB16entry/stdout1MiB/preflight別量。automation設定更新/詳細結果-PC path転記0、ACTIVE文書参照維持。
CI381385/4130保存、新query-download-verifier0/旧381365inprogress履歴/doc-onlyCI追跡0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読、正式5残件・最終受入未完了。create_native早期拒否/全7役reader起動禁止/元caps-unknown原owner-stop/追加agent禁止。未完了formal/nativeを少量dev開始条件へ戻さず、engineering900秒2GiB/output1GiB/single32MiB/files32 checkpointの限界を維持。Sol容量又は人の停止では保全後PAUSED・重複再試行0。

| 原保存 | bytes | SHA256 |
| --- | ---: | --- |
| observations | 9600600 | 072bbae0037c3d5b2d6d244c1263ef1369df3307d46ffcbc9056dfda68d789c7 |
| configuration | 5503 | 68bb61e9f3c916098f9ddc070a13c5145fc12f7e9703c5101da480b408bc4ce9 |
| manifest | 8031 | 0aba19847455ea6e4ba05c14a95a364b0b481922c3fc45cd077d3775b2e577f4 |
| evaluation | 13899099 | d8b567719d9475453846b42a29535811bc851e747c556172d2d40ebafd28f385 |
| numerical | 13893601 | 1738b52942894cd92aba49734ddb2610cbe8419f98fadb55ca8353f1f8585134 |
| comparison | 22430 | cac53d53a4cfdd2e1d889f94e857f5414748ac594e961c964df77f56dc22a2b4 |
| target-window-proof | 10980 | 4f3461861f3418f8f0b75c7c9e7dc4ebd93d56774134d91046317c1518962252 |

## 次の未完成unit

同chunk005/devseed/layout5/core、manifest同{'bytes': 75699, 'sha256': '765ddbc639d74063b00c79b28a1e534bdb5d7859bee66d0bd4d1add2d69fc9a6'}・同10input pinsをC1 c1-phase-level、新ID dev-layout5-core-c1-20261012で1cell実評価する。次dataset identity/input10/同layout qualitypair metadataを保存。nextmodel未開始/元payload書込み・生成0、quality観測本文未読。今回完成C0core/旧30cell/replay/risk-owner/native/probe/collector/Git37/CI反復0。
