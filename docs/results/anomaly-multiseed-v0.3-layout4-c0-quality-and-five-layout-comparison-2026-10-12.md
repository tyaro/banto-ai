# dev layout4 C0 quality実評価・5layout保存比較（2026-10-12 JST）

## 入力・設定・実評価

同保存dev seed2486912926863618161/layout4/quality-stressを既存CLI C0 c0-diff-control、新ID dev-layout4-quality-c0-20261012で1cell実compute_evaluation。10input pins→新snapshot→fresh calibration→原profiles/scores/episodes/events/incidents/metrics。元payload書込み・生成・replay・production-test変更・追加agent・類似owner試験・holdout本文読取り0。
input manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\004\attempt-0001\result\payload\manifest.json
input manifest pin {'bytes': 75699, 'sha256': '54f358a6b69d9df9b27fd1e5762a2f3c63be0ab6e545df7aca8668d4d7f04fc3'}。dataset anomaly-v03-dev-seed-2486912926863618161-layout-04-quality-stress。元生成candidateと実評価candidateは別field（今回は両C0）。actual文書checkout05b75cee4fa64debee949b0274a92f56ebc8d9b6、計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。
actualPython3.14.0 Windows AMD64。elapsed18.62621269992087秒、OScheckpoint sampled privatepeak146530304B。engineering900秒/2GiB/output1GiB/single32MiB/files32はcheckpoint上限で、blocking中断/full loaded runtime/allwriter-global-native容量証明は未完了。

## 原結果と未検出の保存

CLI exit0/complete/1cell success。性能合格・候補採択・正式受入は未判定。

- 機械0/10、sensor0/10、precision0/3、clean誤警報3、未対応equipment3（全clean）。
- 48calibrated、fit各0/calibration各290、14400scores、利用可能13880/不能520。
- 排他的primary phase480/current quality30/previous quality10。非排他的phase480/current quality30/current nonfinite30/previous quality30を合算しない。phase-primary-other overlap0。
- 全不能score/residual null・thresholdfalse。温度missing30、mask/observation18000行対応。
- source3/equipment3/events40/incidents20。全20no_candidate_in_window/candidate0/causalfalse/matched-source-equipment null/support[]/delaynull。
- delay count0/min-max-mean-median原null、未検出補完forbidden。
- clean_rate原3/3365/value25.676077265973255、effective clean3255秒/value26.543778801843317。burden原3/20/value15.0を単純な確率へしない。

全20target windowの最大streakは各1、固定C0 threshold4/persistence2が成立しない。machine窓phase不能各1、sensor窓0。cycle09温度も最初の超過後に欠測resetが入り、後続streak2に至らない。欠測1件だけで全20missを説明しない。原20event-incident/全20motor4target windows/全6source-equipment episodes/欠測30入力をEXTRACTへ保存した。GT/config/threshold/persistence/matching/science変更0、入力対応・保存・状態分類の実経路不具合は観測なし。

### cycle00 machine motor-01.motor_current

| sample | available | primary | score | residual | threshold | streak |
| ---: | --- | --- | ---: | ---: | --- | ---: |
| 7318 | True | None | 1.6477604889059734 | -0.1951400000000003 | False | 0 |
| 7319 | True | None | 1.831386504393488 | 0.2074820000000006 | False | 0 |
| 7320 | False | mode_recipe_or_phase | None | None | False | 0 |
| 7321 | True | None | 0.1698103485753881 | 0.02210100000000015 | False | 0 |
| 7322 | True | None | 0.4560172135018981 | -0.05661100000000019 | False | 0 |
| 7323 | True | None | 54.13003315994726 | 6.808821999999999 | True | 1 |
| 7324 | True | None | 0.1759643090013353 | -0.021387999999999963 | False | 0 |
| 7325 | True | None | 0.32358780154489114 | -0.039954999999999075 | False | 0 |
| 7326 | True | None | 0.4273464366336899 | 0.05449199999999976 | False | 0 |
| 7327 | True | None | 0.6719623881387922 | -0.08377100000000048 | False | 0 |
| 7328 | True | None | 0.4018639519241493 | 0.051287000000000305 | False | 0 |
| 7329 | True | None | 0.0685959865309217 | 0.009370999999999796 | False | 0 |

### cycle00 sensor motor-01.motor_temperature

| sample | available | primary | score | residual | threshold | streak |
| ---: | --- | --- | ---: | ---: | --- | ---: |
| 7325 | True | None | 1.2372002230638381 | 0.1001999999999974 | False | 0 |
| 7326 | True | None | 1.9075015989412287 | 0.13316000000000017 | False | 0 |
| 7327 | True | None | 162.69856590240173 | 8.039563999999999 | True | 1 |
| 7328 | True | None | 1.333617056287099 | 0.10494100000000373 | False | 0 |
| 7329 | True | None | 0.21852923041528705 | 0.050109999999996546 | False | 0 |
| 7330 | True | None | 162.58768959471712 | -7.955382999999998 | True | 1 |
| 7331 | True | None | 0.8773809802423528 | 0.08250699999999966 | False | 0 |
| 7332 | True | None | 0.5581133437163556 | 0.06680800000000175 | False | 0 |
| 7333 | True | None | 0.7196893276769943 | 0.07475299999999763 | False | 0 |
| 7334 | False | current_target_quality | None | None | False | 0 |
| 7335 | False | current_target_quality | None | None | False | 0 |
| 7336 | False | current_target_quality | None | None | False | 0 |

### cycle09 sensor motor-01.motor_temperature

| sample | available | primary | score | residual | threshold | streak |
| ---: | --- | --- | ---: | ---: | --- | ---: |
| 8945 | True | None | 1.3798629703872272 | 0.10721499999999651 | False | 0 |
| 8946 | True | None | 0.7792558546778516 | 0.07768200000000292 | False | 0 |
| 8947 | True | None | 163.31928612675023 | 8.070085999999996 | True | 1 |
| 8948 | False | current_target_quality | None | None | False | 0 |
| 8949 | False | current_target_quality | None | None | False | 0 |
| 8950 | False | current_target_quality | None | None | False | 0 |
| 8951 | False | previous_target_quality_or_nonfinite | None | None | False | 0 |
| 8952 | True | None | 0.11867547569571948 | 0.045199999999997686 | False | 0 |
| 8953 | True | None | 0.47892179160271364 | 0.0629140000000028 | False | 0 |
| 8954 | True | None | 0.9703405551554086 | 0.08707799999999821 | False | 0 |
| 8955 | True | None | 0.3716857735504419 | 0.021087999999998885 | False | 0 |
| 8956 | True | None | 0.4325335198072474 | 0.01809599999999989 | False | 0 |


## 同seed5layout・30cellの保存比較

layout0–4×core/quality-stress×C0/C1/C2の30cell保存比較を完成。同seed1、layout5、strata2、unique dataset10、候補3。30独立seed/datasetとは数えない。旧29cellは保存manifest/configだけを読み、旧result本文・再compute0。同datasetのinput10 pins一致、全30cellの宣言16calculator source・candidate config・compiled config一致。宣言pinはfull loaded runtime/native認証ではない。
layout4 core C0両0/10/precision0/3/clean3、C1/C2両10/10/precision20/20/clean0。quality C0両0/10/precision0/3/clean3、C1/C2機械10/10/sensor9/10/precision19/19/clean0。C1/C2quality19検出のdelay中央値2秒/平均1.5263157894736843秒、未検出は原null。C1source29対C2source39、同指標から原予測同一を推定しない。旧layout0 C2機械4/10、layout1 C0clean2/grace未対応1、layout2 quality phase-quality重複とavailability差を原値のまま保持。bootstrap/統計CI/勝者/候補採択0。

| layout | stratum | candidate | machine | sensor | precision | clean | unmatched | available/unavailable | delay median/mean秒（検出のみ） |
| ---: | --- | --- | --- | --- | --- | ---: | ---: | --- | --- |
| 0 | core | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 3 | 13920/480 | None/None |
| 0 | core | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 0 | 13920/480 | 1.5/1.5 |
| 0 | core | c2-phase-conditional | 4/10 | 10/10 | 14/20 | 0 | 6 | 13920/480 | 1.0/1.2857142857142858 |
| 0 | quality-stress | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 3 | 13880/520 | None/None |
| 0 | quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 0 | 13880/520 | 2.0/1.5263157894736843 |
| 0 | quality-stress | c2-phase-conditional | 4/10 | 9/10 | 13/19 | 0 | 6 | 13760/640 | 1.0/1.3076923076923077 |
| 1 | core | c0-diff-control | 0/10 | 0/10 | 0/3 | 2 | 3 | 13920/480 | None/None |
| 1 | core | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 0 | 13920/480 | 1.0/1.0 |
| 1 | core | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 0 | 13920/480 | 1.0/1.0 |
| 1 | quality-stress | c0-diff-control | 0/10 | 0/10 | 0/3 | 2 | 3 | 13880/520 | None/None |
| 1 | quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 0 | 13880/520 | 1.0/1.0 |
| 1 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 0 | 13760/640 | 1.0/1.0 |
| 2 | core | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 3 | 13920/480 | None/None |
| 2 | core | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 0 | 13920/480 | 1.0/1.0 |
| 2 | core | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 0 | 13920/480 | 1.0/1.0 |
| 2 | quality-stress | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 3 | 13889/511 | None/None |
| 2 | quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 0 | 13889/511 | 1.0/1.0 |
| 2 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 0 | 13796/604 | 1.0/1.0 |
| 3 | core | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 3 | 13920/480 | None/None |
| 3 | core | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 0 | 13920/480 | 1.5/1.5 |
| 3 | core | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 0 | 13920/480 | 1.5/1.5 |
| 3 | quality-stress | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 3 | 13880/520 | None/None |
| 3 | quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 0 | 13880/520 | 1.0/1.4736842105263157 |
| 3 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 0 | 13760/640 | 1.0/1.4736842105263157 |
| 4 | core | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 3 | 13920/480 | None/None |
| 4 | core | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 0 | 13920/480 | 1.5/1.5 |
| 4 | core | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 0 | 13920/480 | 1.5/1.5 |
| 4 | quality-stress | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 3 | 13880/520 | None/None |
| 4 | quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 0 | 13880/520 | 2.0/1.5263157894736843 |
| 4 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 0 | 13760/640 | 2.0/1.5263157894736843 |

| layout/stratum/candidate manifest | bytes | SHA256 |
| --- | ---: | --- |
| 0/core/c0-diff-control | 11019 | 0898a0ee0eb0a5a15af8e52d320832abe06220e30cb8cad0d02f7f774a01e094 |
| 0/core/c1-phase-level | 11019 | 0898a0ee0eb0a5a15af8e52d320832abe06220e30cb8cad0d02f7f774a01e094 |
| 0/core/c2-phase-conditional | 8015 | d70767ce2d8f174804565838011b709b0adced933787124cd5e02ee4285a96c9 |
| 0/quality-stress/c0-diff-control | 8057 | 15db2aeafb313691c8601220d3950580fa30ad7a16d543c5414700b16a9950ac |
| 0/quality-stress/c1-phase-level | 8042 | 3042be397642799af8c5ac6d0d2fb82c8f92f0a3d66a8fe983f8cc1b8e4431d3 |
| 0/quality-stress/c2-phase-conditional | 8062 | ef6829dbb07862056362ec19dc3934e5d94de6fc2c50fedc755a44d1e4751286 |
| 1/core/c0-diff-control | 8030 | 2617eca766b9a10e840ac5a7d5e9798cc1466e28989bbfdefae45484d4aa2236 |
| 1/core/c1-phase-level | 8024 | f1b3ebc59a9a4c0c762a1b1a6ead0bfdb2b8df1fac5d8e4731da9df68c0e2acd |
| 1/core/c2-phase-conditional | 8008 | 8005819bdc77823a6caddfb96dc33c49a6487186eaa69d4b48f5b37f020dde97 |
| 1/quality-stress/c0-diff-control | 8064 | c23b11cd12880e4102db387a452a475a104445431294298da6e0e14f98808233 |
| 1/quality-stress/c1-phase-level | 8035 | 399af646470a861c738d4c6726772927936a4408aa445523e7440050a7a2cb54 |
| 1/quality-stress/c2-phase-conditional | 8039 | a2157815936c182eccc93409dddd4dfa16821ba482417df4d5a2b218b092844a |
| 2/core/c0-diff-control | 8028 | dfaff1ed6a29deb373db3b0598001fe0807abefdfca2e6acaf08b72baaa6ad9b |
| 2/core/c1-phase-level | 8002 | 6a8a1537204cb240080e1f808e875975036fc6dba5b4925d2f893f46f189dd42 |
| 2/core/c2-phase-conditional | 8009 | c1cf4496d07b9b8b53f4f98ac8b12d2dd548b06beaecabad49e13f069f835d16 |
| 2/quality-stress/c0-diff-control | 8065 | 865ee2cc1b790907aab544288115f7f7e9af24b81fee2e2b1c471169eba9b9b0 |
| 2/quality-stress/c1-phase-level | 8034 | 67308ad3afa221abfa1e118dd9447bb721306c843440719e80de29941732d38f |
| 2/quality-stress/c2-phase-conditional | 8041 | 619ba0e5f5b6758c54886d41edde95ad26c1cbb7568476e689f77b3286eb4f92 |
| 3/core/c0-diff-control | 8032 | 6f132b35a0df2d2a838f5aaa2d2bd7bebeb03fec4df51ba7d6b5362b6c671d9f |
| 3/core/c1-phase-level | 8003 | 28789ebe65503df67d229dde0a37df6c9bec0f27f9b8f7d3149a923eb6ec130e |
| 3/core/c2-phase-conditional | 8009 | bbde7501279dc71ea668bfc6e8257ad89c0d8d68bdc3123cdd217a45a180d852 |
| 3/quality-stress/c1-phase-level | 8049 | a05cca45875f3de8e40762208c69ab17119e39a20ac87b0060846b0db87d517e |
| 3/quality-stress/c2-phase-conditional | 8055 | 6d76f7ee43f5dd9ff77450aa073ff3cf56848ecd69e1c3f5b7882c56bc729512 |
| 3/quality-stress/c0-diff-control | 8064 | 11c119b32b6c638978f4f7bd7cb0b392dc78a8aa957a6ca94e778c0765068554 |
| 4/core/c0-diff-control | 8031 | e10c8bc87c37d84acc726c12a7071259a2eaab3b3cddd2f87843f177d67564c5 |
| 4/core/c1-phase-level | 8003 | dbe79c19d893d36df1defecaabe580c519333843cf4d61cad14f99b9f7468719 |
| 4/core/c2-phase-conditional | 8009 | 6e8f61b527186a10c6f7431b2fe351c70e3eb66d2133ef1fc2cab1701676b50c |
| 4/quality-stress/c1-phase-level | 8049 | 8999f7ee03136d4c240e33cbbec8a076e460fd77e2fc69cacd52da3f67ec75cc |
| 4/quality-stress/c2-phase-conditional | 8055 | 4ffd57472ae45072e22d0b70b526d5dadabe3999163f74d9ca73de7f0468c9ae |
| 4/quality-stress/c0-diff-control | 8064 | 18906297879381f91ec703e543a502c83726946c7a492c6d498eda9675d2167c |

## 保存状態・前失敗・正式gate

DATA {'files': 19, 'bytes': 27383492, 'manifest_pin': {'bytes': 2259, 'sha256': '71ea83c9bbc33a1ec4c5554772039002ba1cacae8b2f1c5be885090a5c05e2c8'}}、EXTRACT {'bytes': 302809, 'files': 8, 'manifest_pin': {'bytes': 1200, 'sha256': 'e824ae557fd8ed81ad927638174e97e230bc24ec60e51f3edd37bb45a28f24f5'}}、BOARD {'bytes': 232410, 'files': 9, 'manifest_pin': {'bytes': 1414, 'sha256': '009333bb234002750e8b8f35f9a20771f538cb9609266990c074d6643a7a164c'}}。MAIN/POSTの最終post-save・owners-after-save・root-closedを優先する。新metadataは512KiB32entry/reserve128KiB/single128KiB、script/失敗証拠/閉鎖分を含め新書込み前に件数bytes確認、Python-B/recursive file coverageを維持。閉鎖/外部固定root追記・raw整理移動削除・上限緩和0。
117science-source/旧119root count-byte-closurepin/外部固定C1 MAIN35files capfalse/旧C2cache補足不変。前C1 false13/raw12閉鎖失敗と別訂正文書Git、前C2 owner準備foreground4（guard拒否/未作成script呼出し/quote syntax/command幅事前拒否）を原最終POSTのまま保持。前C2のdocs-preparation時点0と最終foreground4を区別し、前helper/model/Git/CI/native/Sol失敗へ読み替えない。今回current foreground failure0。
元157helpers原11failed146passed/full saved identity一致/CIM同original不在/repo helpercriticalなし。今回model/analysis2passed。foreground fullcreation/fullstdioNone、selectedCLIをhelper全stdioにしない、PID単独判定/native回収claim0。CIMdecimal100ns→microsecondtrunc/fulltokenを維持。
同GitHub同種合成dev結果・ユーザー名PC内pathの送信はリスク通知後の人の継続承認内。handoff/report2一回[skip ci] commit/push、原Git/API・HEAD-upstream-ref-clean/docpinsはPOST保存。Git累積30秒/512KiB16entry/stdout1MiB/preflight別量。automation設定更新/詳細結果-PC path転記0、ACTIVEの文書参照を維持。
CI381385/4130保存を維持、新query-download-verifier0/旧381365inprogress履歴/doc-onlyCI追跡0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読、正式5残件・最終受入未完了。create_native早期拒否/全7役reader起動禁止/元caps-unknown原owner-stop/追加agent禁止。未完了formal/native証明を少量dev開始条件へ戻さない。Sol容量又は人の停止では保全後PAUSED、重複再試行0。

| 原保存 | bytes | SHA256 |
| --- | ---: | --- |
| observations | 9600460 | 236a92b486a1c0d3f329f6a41e1c12858742e5ea0b1bc7e857430bb89a593804 |
| configuration | 5513 | 235ca1c2ced95edd758aa1e3bd313046f808519aa923d5c5759ab8eac0f60f07 |
| manifest | 8064 | 18906297879381f91ec703e543a502c83726946c7a492c6d498eda9675d2167c |
| evaluation | 14336404 | f069cc91d508232e0cc019f8547b21f36efc43691166e64195f0d6395a54d350 |
| numerical | 14330806 | 7db924e8196225ecdcf2b7fdd80df6d7a497c8cbe679626041dbea94d6aee19e |
| target-window-proof | 15904 | 957701477d6c06ea094bf71a96c22dbeed6bcfe28026ec6f4f41f0b6ba42f4ed |
| comparison-index | 4198 | 3403f97d11d9260cee2baf95682494ed1d6e548399bffd0f94e8458cf351d839 |

## 次の未完成unit

同保存chunk005 manifestmetadataから同devseed/layout5/core-quality pairを選択した。next manifest {'bytes': 75699, 'sha256': '765ddbc639d74063b00c79b28a1e534bdb5d7859bee66d0bd4d1add2d69fc9a6'}、path C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\005\attempt-0001\result\payload\manifest.json、dataset anomaly-v03-dev-seed-2486912926863618161-layout-05-core。新独立seedではなくlayout差。次candidate c0-diff-control、新ID dev-layout5-core-c0-20261012で1cell実評価する。next10pins/quality pair metadataをBOARDへ保存、next観測本文・元生成評価本文は未読、nextmodel未開始/生成0。完成30cell/replay/risk-owner/native/probe/collector/Git37/CIは反復しない。
