# dev layout3 C0 quality実評価・4layout保存比較（2026-10-12 JST）

## 原入力・設定・実評価

保存済み合成dev seed2486912926863618161/layout3/quality-stressを既存CLI C0 c0-diff-control、新ID dev-layout3-quality-c0-20261012で1cell実compute_evaluation。input10pins→新snapshot→fresh calibration→原profiles/scores/episodes/events/incidents/metrics保存。元payload書込み・生成・replay・production/test変更・類似owner・追加agent・holdout本文読取り0。

input manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\003\attempt-0001\result\payload\manifest.json

manifest 75699B/40be5e90bb27173cf9d21252940f13beb86a17187ea0fb25afa77315c516056d、dataset anomaly-v03-dev-seed-2486912926863618161-layout-03-quality-stress。元生成identity candidateと実評価candidateは別field（今回は両C0）。actual文書checkout bd31c4a8042dfc1e637a59bf4dc39704543ce4fa、計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。actualPython3.14.0 Windows AMD64、elapsed56.12378370005172秒/OScheckpoint privatepeak146423808B。

engineering900秒/2GiB private/output1GiB/single32MiB/files32 checkpoint上限を維持。blocking計算中断・full loaded runtime閉包・allwriter/global/native容量証明ではない。

## 原結果

CLI exit0/complete/1cell success。処理successを性能合格・正式受入・勝者・採択へしない。

- 機械0/10・sensor0/10・precision0/3・clean誤警報3・全未対応equipment3（全clean）。
- 48calibrated、fit_samples各0/calibration各290、14400scores。利用可能13880・不能520。
- mask/observation18000行対応、motor温度missing30観測行。
- source3/equipment3/events40/incidents20、全20no_candidate_in_window/candidate0/causalfalse/matched-source-equipment null/support[]/delaynull。
- delay count0/min/max/mean/median原null、未検出delay補完0。
- clean_rate原3/3365/value25.676077265973255、effective_clean_seconds3255/effective_clean_rate26.543778801843317、false_alert_burden原3/20/value15.0。単純確率へ変換0。

排他的primary phase480/current quality30/previous quality10、合計520。非排他的phase480/current quality30/current nonfinite30/previous quality30を独立行として加算0。全不能score/residual null・threshold_exceeded=false、phaseと別primary重複0を原scoreで保存。旧layout2のprimary phase471/不能511/品質重複9を今回へ流用0。

## 全20対象窓の固定persistence不成立

全20event/incidentとmotor4target窓をEXTRACT保存し、event start〜window endの対象target maxstreakを原rowから照合。19件は最大1、cycle09sensorは0。sensor10窓の開始phase不能各1行、machine10窓はphase不能0を別保持。non-ok30観測とphase不能480scoreを同量へしない。

cycle00machine current7311score48.42504917051087/streak1→7312score0.0015640615907367452/0。7314score48.685849959848674/1→7315score0.779965542772622/0。cycle00sensorは7290phase不能、7291score3.482533841266633/0・7292score2.668957065219842/0、7293score132.9885637227601/1→7294score3.1991991525663153/0。threshold4/persistence2が成立せず、欠測cycle09だけで全20missを説明しない。

cycle09sensor8910phase不能→8911–8913current欠測→8914previous欠測、8915score1.5923395919017416/8916score1.2000966462706428はthreshold4未満/streak0。不能scoreと未検出delayを補わない。

### cycle00 sensor motor-01.motor_temperature

| sample | available | primary | score | residual | threshold | streak |
| ---: | --- | --- | ---: | ---: | --- | ---: |
| 7288 | True | None | 0.7817505746349682 | -0.0021850000000007697 | False | 0 |
| 7289 | True | None | 1.061538647861873 | -0.014265000000001749 | False | 0 |
| 7290 | False | mode_recipe_or_phase | None | None | False | 0 |
| 7291 | True | None | 3.482533841266633 | 0.24916200000000543 | False | 0 |
| 7292 | True | None | 2.668957065219842 | 0.2012549999999962 | False | 0 |
| 7293 | True | None | 132.9885637227601 | -7.786860000000001 | True | 1 |
| 7294 | True | None | 3.1991991525663153 | 0.2324780000000004 | False | 0 |
| 7295 | True | None | 1.5132694462180047 | 0.13320300000000174 | False | 0 |
| 7296 | True | None | 0.9342708321838027 | 0.09910899999999856 | False | 0 |
| 7297 | False | current_target_quality | None | None | False | 0 |
| 7298 | False | current_target_quality | None | None | False | 0 |
| 7299 | False | current_target_quality | None | None | False | 0 |

### cycle00 machine motor-01.motor_current

| sample | available | primary | score | residual | threshold | streak |
| ---: | --- | --- | ---: | ---: | --- | ---: |
| 7309 | True | None | 0.18665908520214963 | -0.026054999999999495 | False | 0 |
| 7310 | True | None | 0.5170908596128391 | -0.0642940000000003 | False | 0 |
| 7311 | True | None | 48.42504917051087 | -5.608411 | True | 1 |
| 7312 | True | None | 0.0015640615907367452 | -0.004273000000000415 | False | 0 |
| 7313 | True | None | 0.13718807632375696 | 0.011422000000000487 | False | 0 |
| 7314 | True | None | 48.685849959848674 | 5.629683999999999 | True | 1 |
| 7315 | True | None | 0.779965542772622 | -0.094714999999999 | False | 0 |
| 7316 | True | None | 0.3979110946432455 | 0.04159399999999991 | False | 0 |
| 7317 | True | None | 0.571737961821917 | 0.06170999999999971 | False | 0 |
| 7318 | True | None | 1.6477604889059734 | -0.1951400000000003 | False | 0 |
| 7319 | True | None | 1.831386504393488 | 0.2074820000000006 | False | 0 |
| 7320 | False | mode_recipe_or_phase | None | None | False | 0 |

### cycle09 sensor motor-01.motor_temperature

| sample | available | primary | score | residual | threshold | streak |
| ---: | --- | --- | ---: | ---: | --- | ---: |
| 8908 | True | None | 0.22527803760277895 | 0.04129400000000061 | False | 0 |
| 8909 | True | None | 0.12774595346711465 | 0.026051999999999964 | False | 0 |
| 8910 | False | mode_recipe_or_phase | None | None | False | 0 |
| 8911 | False | current_target_quality | None | None | False | 0 |
| 8912 | False | current_target_quality | None | None | False | 0 |
| 8913 | False | current_target_quality | None | None | False | 0 |
| 8914 | False | previous_target_quality_or_nonfinite | None | None | False | 0 |
| 8915 | True | None | 1.5923395919017416 | 0.13785899999999884 | False | 0 |
| 8916 | True | None | 1.2000966462706428 | 0.11476199999999892 | False | 0 |
| 8917 | True | None | 1.1144543041995312 | 0.1097190000000019 | False | 0 |
| 8918 | True | None | 0.011870711304346419 | 0.044793999999999556 | False | 0 |
| 8919 | True | None | 0.07788137631138801 | 0.04868099999999842 | False | 0 |


GT・threshold4・persistence2・second-exceedance・first-equipment-onset-no-retry-v1・science変更0。実入力対応・保存・状態分類の不具合は観測なし。全20原incident/全20motor4target窓/30non-ok mask-observation/全6source-equipment episodeを保存。

## 3候補×2条件×4layout、24cellの保存比較完成

| layout | stratum | candidate | machine | sensor | precision | clean | unmatched | available/unavailable | delay median/mean秒 (検出のみ) |
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

今回のnew実評価は1cell。旧23cellは保存manifest/configだけを参照し、原result本文再展開・再compute0。全宣言16calculator source/candidate_config/compiled_candidate_config一致、同datasetの3候補はinput10全pin一致。同seed4layout×2strataの8dataset、3候補24cellで24独立dataset/seedではない。明示replayを独立データ数へ加算0。

layout3 core：C0機械/sensor0/10・precision0/3・clean3、C1/C2機械/sensor10/10・precision20/20・clean0。quality：C0機械/sensor0/10・precision0/3・clean3、C1/C2機械10/10・sensor9/10・precision19/19・clean0。C1/C2の同検出集計を原profile/score/residual/episode同一へしない。quality利用不能はC0/C1 520、C2は640（peer120波及）。

旧layout0 C2機械4/10、旧layout1 C0 clean2と全未対応3、layout2品質primary重複/不能差、各原delay中央値差・未検出nullを保持。bootstrap・統計CI・勝者・採択0。

24cell原manifest/config/result/numerical/input10pinsとmetricsを新comparison rootの4分割JSON/indexに保存（旧resultbody読取り0）。comparison rootには次dev manifest metadataとselectionも保存、閉鎖後追記0。

## 原pin・閉鎖・失敗履歴

| 原保存 | bytes | SHA256 |
| --- | ---: | --- |
| observations | 9600573 | 0a81a591db94635b1805534ce731b2352f2ad62ea34b03fb014939c64aff2ce8 |
| configuration | 5513 | cb06b060c21858c522a2969f317a4df4ce00ff32828a468a9bc71e7096fca7df |
| manifest | 8064 | 11c119b32b6c638978f4f7bd7cb0b392dc78a8aa957a6ca94e778c0765068554 |
| evaluation | 14336216 | 86a26719e89a476b67f46a761969affcf8483ae226dea1b678a2ce1a710c6899 |
| numerical | 14330618 | 7b716beb89bae9b2695eaec27684dce017dc895224b6a936f265d38439cd992f |
| target-window-proof | 15831 | 2d596d9b5982f0a4769e908cbf4c538794aa1c6a846defdd52e494887fed404e |
| comparison-index | 3965 | 0e9b55d767e8c9e1048b71689028da54b09631a640f30c01007afb7da3a09a1d |

| 保存manifest layout/stratum/candidate | bytes | SHA256 |
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

DATA閉鎖{'bytes': 27383058, 'files': 19, 'manifest_pin': {'bytes': 2259, 'sha256': '2f0bb47172f794352ebc12d4548979e1beffe98a0eb8b50309a2e4f50724ebfc'}}、EXTRACT閉鎖{'bytes': 302912, 'files': 8, 'manifest_pin': {'bytes': 1200, 'sha256': '0ab7178522922a783de4843134ae02a799effef6ffe7c5cd6c3a1b19c2b6de3d'}}、COMPARISON閉鎖{'bytes': 202859, 'files': 8, 'manifest_pin': {'bytes': 1294, 'sha256': '01336888d61dc16a56128914afe5261fd90fd836518135256be995a159617147'}}。MAIN representative-layout3-quality-c0-20261012-prep/POST representative-layout3-quality-c0-post-20261012-prepの最終post-save/owners/root-closedを優先。

117science-source/旧93root count-byte-closurepin/外部固定C1 MAIN35file226520B容量false/旧C2 cache補足pin不変。過去failed/capacityfalse/closure limitsを保持。前qualityC1 selector miss、前coreC2 builder限定置換拒否、前C0失敗と未保存metadata別continuation、前layout2 C0 commitTimeout原failed/commit返値Noneと別既存commit確認・別push-only一回完成、前C2core lsremote128/Connection resetと別metadata continuationを保持。元failed書換え・元helper/model/Git反復0。

文書保存前138helpersはfull saved creation-start_token/live-execution一致・原11failed127passed/CIM同original不在/repo helpercriticalなし。今回model/analysis2passed、新foreground失敗0。CIMdecimal100ns→microsecond truncation/full token比較、PID単独0/native回収claim0。foreground fullcreation/stdioNone、selectedCLIを全helperstdioにしない。

新metadata512KiB32entry/reserve128KiB/single128KiB、recursive full coverage/Python-B。新書込み前script・失敗証拠・閉鎖分の件数/bytesを確認、対象文字列限定/hash-seed無限定置換0。閉鎖・外部固定root追記・原raw整理削除移動・上限緩和0。

## 次の保存済みdev入力とGit承認

sibling chunk004 manifestをmetadataだけ一回読取り、新comparison rootへ原bytes保存。pin 75699B/54f358a6b69d9df9b27fd1e5762a2f3c63be0ab6e545df7aca8668d4d7f04fc3。同dev seed2486912926863618161/layout4のcore/quality pair、各input10pinsを保存。新独立seedではない。次観測本文・原生成evaluation本文読取り0/元payload書込み・生成0。

次input manifest: C:/Users/TKent/.codex/worktrees/v03p/banto-ai/artifacts/v03-runs/r1/run/attempts/chunks/004/attempt-0001/result/payload/manifest.json

次unitは同保存layout4 core dataset anomaly-v03-dev-seed-2486912926863618161-layout-04-core をC0、新ID dev-layout4-core-c0-20261012で1cell実評価。manifest54f/input10pinsを維持。次model未開始、完成layout0–3の24cell・明示replay・旧risk-owner/native/probe/collector/Git37/CI反復0。

送信リスク通知後の人の明示承認で、同GitHub https://github.com/tyaro/banto-ai.git へ同種合成dev結果・ユーザー名を含むPC内入力pathを継続送信できる。report/current-handoff2を一回[skip ci] commit/pushし、original Git/API returns・HEAD/upstream/remote ref/clean/docpinsはPOST保存。後追い文書再commit0。Git512KiB16entry/stdout1MiB/累積30秒、preflight別量維持。

automation設定への詳細結果・PC内path転記/更新0、文書参照短指示ACTIVE維持。CI381385/code661の4130success独立verifier保存維持、新query/download/verifier0/doc-onlyCI追跡0。旧381365/a54961最後in_progressは履歴のまま。CI成功≠model性能/native/正式受入。

formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読/正式5残件・最終受入未完了/create_native早期拒否/全7役whole.run reader実起動禁止/元caps-unknown原owner-stop/追加agent禁止。未完了formal/native証明を少量dev開始条件に戻さない。Sol容量又は人の停止では保全後PAUSED、重複再試行0。
