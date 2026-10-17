# dev layout2 C0 quality・18cell保存比較（2026-10-12 JST）

## 原入力と実行

保存済み合成dev seed2486912926863618161/layout2/quality-stressを既存CLI C0 c0-diff-controlで1cell実compute_evaluation。新ID dev-layout2-quality-c0-20261012。input10pins照合→新snapshot→fresh calibration→原profile/score/source-equipment episodes/events/incidents/metrics保存。元payload書込み・新dataset生成・replay・production/test変更・類似owner・追加agent・holdout本文読取り0。

input manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\002\attempt-0001\result\payload\manifest.json

manifest 75699B/c97c3564c28b679668c2f7425b33aaedadec0c90c45e5705e929131826797783、dataset anomaly-v03-dev-seed-2486912926863618161-layout-02-quality-stress。生成identityと実評価cellのcandidateを別fieldで保持。文書checkout3841646cc950bd713c502ed7aa3a4c60de0b0feb、計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。Python3.14.0 Windows AMD64、elapsed19.114797299960628秒/OScheckpoint peak private146567168B。

engineering900秒/2GiB private/output1GiB/single32MiB/files32 checkpoint上限を維持。blocking計算中断/full loaded runtime閉包/allwriter/global/native容量証明ではない。

## 原結果

CLI exit0/complete/1cell success。処理successをモデル性能合格・正式受入・勝者・採択へしない。

- 機械0/10・sensor0/10・precision0/3・clean誤警報3・全未対応equipment3（全clean）。
- calibrated48、原fit_samples各0/calibration各290、score14400。利用可能13889・不能511。
- 原mask-observation18000行対応、motor温度missing30観測。
- source3/equipment3/events40/incidents20、全20no_candidate_in_window/candidate0/causalfalse/matched-source-equipment null/support[]/delay null。検出delay count0、min/max/mean/median原None。
- clean_rate原3/3365/value25.676077265973255、effective_clean_seconds3254/effective_clean_rate26.551936078672405、false_alert_burden原3/20/value15.0を確率へ読み替えない。

排他的primary phase471/current quality30/previous quality10、合計511。非排他的phase480/current quality30/current nonfinite30/previous quality30を加算しない。phaseとcurrent qualityの同一行重複9を原score全fieldとresult pinへ保存。全不能score/residual null/thresholdfalse。同core C0不能480→quality511差31。旧layout0/1 quality不能520を流用しない。

## 全20未検出の原incident・target窓

| cycle/class | target最大streak | 原candidate数 | 原reason | 原delay秒 |
| --- | ---: | ---: | --- | --- |
| 0/machine | 1 | 0 | no_candidate_in_window | None |
| 0/sensor | 1 | 0 | no_candidate_in_window | None |
| 1/machine | 1 | 0 | no_candidate_in_window | None |
| 1/sensor | 1 | 0 | no_candidate_in_window | None |
| 2/machine | 1 | 0 | no_candidate_in_window | None |
| 2/sensor | 1 | 0 | no_candidate_in_window | None |
| 3/machine | 1 | 0 | no_candidate_in_window | None |
| 3/sensor | 1 | 0 | no_candidate_in_window | None |
| 4/machine | 1 | 0 | no_candidate_in_window | None |
| 4/sensor | 1 | 0 | no_candidate_in_window | None |
| 5/machine | 1 | 0 | no_candidate_in_window | None |
| 5/sensor | 1 | 0 | no_candidate_in_window | None |
| 6/machine | 1 | 0 | no_candidate_in_window | None |
| 6/sensor | 1 | 0 | no_candidate_in_window | None |
| 7/machine | 1 | 0 | no_candidate_in_window | None |
| 7/sensor | 1 | 0 | no_candidate_in_window | None |
| 8/machine | 1 | 0 | no_candidate_in_window | None |
| 8/sensor | 1 | 0 | no_candidate_in_window | None |
| 9/machine | 1 | 0 | no_candidate_in_window | None |
| 9/sensor | 1 | 0 | no_candidate_in_window | None |

原target窓最大streakの件数分布 {1: 20}。全20motor4target score窓をEXTRACTへ保存。欠測一件で全20missを説明しない。

### cycle00 machine / current

| sample | available | 原score | streak | primary exclusion |
| ---: | --- | ---: | ---: | --- |
| 7274 | True | 32.21755133935066 | 1 | None |
| 7275 | True | 0.3247037426630626 | 0 | None |
| 7276 | True | 0.09299239078738782 | 0 | None |
| 7277 | True | 33.3092916329281 | 1 | None |
| 7278 | True | 1.435643472357744 | 0 | None |
| 7279 | True | 0.27820537931136063 | 0 | None |
| 7280 | True | 1.440170168678071 | 0 | None |

7274原score32.21755133935066/streak1→7275score0.3247037426630626/0、7277原score33.3092916329281/1→7278score1.435643472357744/0。固定C0threshold4/persistence2不成立。この対象窓はavailableであり欠測による未検出へしない。

### cycle00 sensor / temperature

| sample | available | 原score | streak | primary exclusion |
| ---: | --- | ---: | ---: | --- |
| 7281 | True | 184.62984497661753 | 1 | None |
| 7282 | True | 0.29369641246287376 | 0 | None |
| 7283 | True | 0.4089700250831749 | 0 | None |
| 7284 | True | 185.57947997582082 | 1 | None |
| 7285 | True | 0.18546382420233276 | 0 | None |
| 7286 | True | 0.6560543930619088 | 0 | None |
| 7287 | True | 1.8426291264630492 | 0 | None |

7281原score184.62984497661753/1→7282score0.29369641246287376/0、7284原score185.57947997582082/1→7285score0.18546382420233276/0。単発超過後の原reset、candidate0のまま。

### cycle09 sensor / temperature

| sample | available | 原score | streak | primary exclusion |
| ---: | --- | ---: | ---: | --- |
| 8901 | True | 184.0134310874735 | 1 | None |
| 8902 | False | None | 0 | current_target_quality |
| 8903 | False | None | 0 | current_target_quality |
| 8904 | False | None | 0 | current_target_quality |
| 8905 | False | None | 0 | previous_target_quality_or_nonfinite |
| 8906 | True | 0.12019538129225639 | 0 | None |
| 8907 | True | 0.8399779931856958 | 0 | None |

8901原score184.0134310874735/streak1→8902–8904current品質不能/8905previous品質不能でreset→8906score0.12019538129225639/0。原candidate0/no_candidate/delaynull。固定threshold4/persistence2/second-exceedance/GT/first-equipment-onset-no-retry-v1/science変更0、未検出やnullを成功へ補わない。実入力対応・保存・状態分類の実経路不具合観測なし。

### 全原source/equipment episodes

| kind | 原episode ID | 原onset_ms | 原matched event |
| --- | --- | ---: | --- |
| source | anomaly-v03-dev-seed-2486912926863618161-layout-02-quality-stress-c0-diff-control-score-conveyor-01-motor_temperature-7712-source | 1767233312000 | field absent |
| source | anomaly-v03-dev-seed-2486912926863618161-layout-02-quality-stress-c0-diff-control-score-motor-01-vibration_feature-7242-source | 1767232842000 | field absent |
| source | anomaly-v03-dev-seed-2486912926863618161-layout-02-quality-stress-c0-diff-control-score-motor-01-vibration_feature-8517-source | 1767234117000 | field absent |
| equipment | anomaly-v03-dev-seed-2486912926863618161-layout-02-quality-stress-c0-diff-control-score-motor-01-vibration_feature-7242-source-equipment | 1767232842000 | None |
| equipment | anomaly-v03-dev-seed-2486912926863618161-layout-02-quality-stress-c0-diff-control-score-conveyor-01-motor_temperature-7712-source-equipment | 1767233312000 | None |
| equipment | anomaly-v03-dev-seed-2486912926863618161-layout-02-quality-stress-c0-diff-control-score-motor-01-vibration_feature-8517-source-equipment | 1767234117000 | None |

3equipmentは原clean context/matched_event=None。clean誤警報3と全未対応3を原指標として保持。全20event/incident/target窓、30non-ok mask/observation、全source/equipmentを新EXTRACTへ保存。foreground overlap出力はtoolでtruncatedであり、helper全stdio保存ではない。原20window全recordsはEXTRACTとevaluation-0へ保存済み、truncated tool excerptから原値を補わない。

## 3候補×2strata×3layoutの保存比較

| layout/stratum | candidate | machine | sensor | precision | clean | available | delay count / median |
| --- | --- | --- | --- | --- | ---: | ---: | --- |
| 0/core | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13920 | 0 / None |
| 0/core | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 / 1.5 |
| 0/core | c2-phase-conditional | 4/10 | 10/10 | 14/20 | 0 | 13920 | 14 / 1.0 |
| 0/quality-stress | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13880 | 0 / None |
| 0/quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 13880 | 19 / 2.0 |
| 0/quality-stress | c2-phase-conditional | 4/10 | 9/10 | 13/19 | 0 | 13760 | 13 / 1.0 |
| 1/core | c0-diff-control | 0/10 | 0/10 | 0/3 | 2 | 13920 | 0 / None |
| 1/core | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 / 1.0 |
| 1/core | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 / 1.0 |
| 1/quality-stress | c0-diff-control | 0/10 | 0/10 | 0/3 | 2 | 13880 | 0 / None |
| 1/quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 13880 | 19 / 1.0 |
| 1/quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13760 | 19 / 1.0 |
| 2/core | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13920 | 0 / None |
| 2/core | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 / 1.0 |
| 2/core | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 / 1.0 |
| 2/quality-stress | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13889 | 0 / None |
| 2/quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 13889 | 19 / 1.0 |
| 2/quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13796 | 19 / 1.0 |

layout2 core/qualityの6cell比較が完成。C0両machine/sensor0/10・precision0/3・clean3。C1/C2 coreはmachine/sensor10/10・precision20/20、qualityはmachine10/10・sensor9/10・precision19/19、clean0。

同layout2 qualityのC0/C1 input10全pin・利用可能13889/不能511が一致。C2もinput10全pin一致だが利用可能13796/不能604、peerタグ120中27phase重複の原差を保持。C1/C2集計一致でもsource29/47、score/episodeの原差を保持。C0threshold4/C1-C2threshold6は既存固定設定のまま。

全18cellで宣言16calculator source/candidate_config/compiled_candidate_config一致。同stratum/layoutのinput10一致とlayout/strata差をfield別保存。旧17比較cellのmanifest/configだけ参照、旧result本文再展開/再compute0。18cellは同じdev seedの3layout×core/quality×3candidateで、18独立datasetや新独立seedではない。元初回core C0/C1は同2cell run、明示replayは独立cell比較へ追加0。bootstrap・統計CI・勝者・採択0。

C0の全20未検出、旧layout0 C2 machine4/10とlayout1/2 C2 machine10/10、quality sensor9/10と原null、旧誤警報を今回successへ書換えない。今回新actual1cell、旧モデル/replay/risk tests/native/probe/collector/Git37/CI反復0。

## 原pin・保存root

| 原保存 | bytes | SHA256 |
| --- | ---: | --- |
| input observations | 9600603 | 9c4ba47cae6728cf74181a8f3ebcdfe2a13a95ce98862d9e042ea4b8f9a83d74 |
| configuration | 5513 | c202ea15ac3575845cb619f1efdce92245742c3d9ffba582f39eeeb4bac047dc |
| manifest | 8065 | 865ee2cc1b790907aab544288115f7f7e9af24b81fee2e2b1c471169eba9b9b0 |
| evaluation-0 | 14336365 | e00a733635b59a84edc74f7c45b8e9d6988196716f27e68787b8cfa4754ceda5 |
| numerical | 14330767 | a93a216c33a98fd03c7935316e2f8f0e643182869fc042e9fab0bf9155491264 |
| saved18cellcomparison | 67597 | 335a8e4b5e54c0f2a722ec09f5ff8994e44b06a2d0b9ba6e9d54b6dd9ad2ff0d |
| quality-phase-overlap | 10040 | 524b5b362a748c0d2af45847609061477c1cf76d51be40e6837aa01dc194e7d6 |

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
| 2/quality-stress/c1-phase-level | 8034 | 67308ad3afa221abfa1e118dd9447bb721306c843440719e80de29941732d38f |
| 2/quality-stress/c2-phase-conditional | 8041 | 619ba0e5f5b6758c54886d41edde95ad26c1cbb7568476e689f77b3286eb4f92 |
| 2/quality-stress/c0-diff-control | 8065 | 865ee2cc1b790907aab544288115f7f7e9af24b81fee2e2b1c471169eba9b9b0 |

| 原extract | records | bytes | SHA256 |
| --- | ---: | ---: | --- |
| incident-ledger-001.json | 20 | 19769 | 9b84fe419b9d78931c23e95535bb11981d274b2211b41ee254a3af6068ae01db |
| selected-windows-001.json | 5 | 63220 | c6dd39c29bb913cc5865ed52a137c200ddf15c75a011e10e562a489378ffc40a |
| selected-windows-002.json | 5 | 63229 | 1089d5d42b3ebd52740178cb71de57cfa7b0724cdad35f64650fb989e81cb9ae |
| selected-windows-003.json | 5 | 63243 | c9558a20ae668f8aa44519c775e20355843daeb238856b3c2b9c1f9b67db406d |
| selected-windows-004.json | 5 | 63587 | e28a0f5567f55ced138bffae08c171ab2c3ad62a4c9f40f965b66143d2a66071 |
| non-ok-input-records-001.json | 30 | 21960 | f6b33188e7917de90021cffd2b488b89801365f1bbb1b7a5f5461dccc00c5558 |
| all-source-equipment-episodes-001.json | 6 | 4716 | c56784cf30c032a29c49a9603444eddc4e2fd350f0913326fc61de5acdabe35d |

DATA dev-layout2-quality-c0-20261012閉鎖{'bytes': 27383477, 'files': 19, 'manifest_pin': {'bytes': 2259, 'sha256': '1a452a1cc062960cf32a81dc5224d1a63f939f44f2fdf521ea886847bea19151'}}、EXTRACT representative-layout2-quality-c0-extract-20261012-prep閉鎖{'bytes': 300924, 'files': 8, 'manifest_pin': {'bytes': 1200, 'sha256': '691e501ff0332e8a3028131de0f260345d89b5d385220667ffe2b449d9dc87ca'}}。18cell保存指標はMAIN saved-18-cell-comparison.json/{'bytes': 67597, 'sha256': '335a8e4b5e54c0f2a722ec09f5ff8994e44b06a2d0b9ba6e9d54b6dd9ad2ff0d'}へ分離保存。MAIN representative-layout2-quality-c0-20261012-prep/POST representative-layout2-quality-c0-post-20261012-prepのpost-save/owners/root-closedを最終Git状態として優先。

117science-source/旧66root count-byte-closure pin/旧C1 MAIN外部固定35file226520B/旧C2 cache補足pin不変。前coreC2 Gitの一回commit/push exit0後lsremote128/Connection reset failedと別metadata continuationのAPI/status一致を履歴保持。元failed書換え・元helper/lsremote/push反復0。前qualityC1日付selector foreground miss/旧capacityfalse/coverage limits/scope-roster保全。今回newfailed0。

元118instrumented helpers full saved creation-start_token/live-execution一致、原10failed108passed/CIM同original不在/repo helpercriticalなし、今回model/analysis2passed。CIMdecimal100ns→microsecond truncation/full saved token/PID単独0/native回収claim0。foreground fullcreation/stdioNone、selectedCLIを全helperstdioにしない。

新metadataはpython-B/recursive full coverage、512KiB32entry/reserve128KiB/single128KiB。新書込み前script/失敗/closure分確認、比較18cellを単一128KiB以内の別metadataへ保存。閉鎖・外部固定root追記・raw削除移動・上限緩和0。補助scriptは対象文字列限定、hash/seed無限定置換0。

## 次の保存済みdev pairのmetadata選択

次manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\003\attempt-0001\result\payload\manifest.json

次manifest 75699B/40be5e90bb27173cf9d21252940f13beb86a17187ea0fb25afa77315c516056d、core dataset anomaly-v03-dev-seed-2486912926863618161-layout-03-core。同seed2486912926863618161/layout3のcore-quality pairを未読sibling chunk003 manifestのmetadataから選択。生成candidate c0と次実評価cellを別fieldで保持、core/quality各10file pin。NEXT representative-layout2-quality-c0-next-dev-20261012-prep閉鎖{'files': 7, 'bytes': 86975, 'manifest_pin': {'bytes': 1065, 'sha256': '7053f9512d2734efbda2a03606bf19b378cb55827ca41dab291ec7ea4c34c2f9'}}、原manifest rawとcapture/selection pinsを保存。観測本文未読/新モデル未開始/元payload書込み/生成0。新独立seedではない。

次unitはC0 c0-diff-control、新ID dev-layout3-core-c0-20261012へ1cell実評価。今回manifestc97cと次40be pinを混同せず、CLI外部manifest pinとdataset identityを別fieldで渡す。今回及び旧完成18cell/replay/CI再実行0。

## Git継続承認と正式状態

送信リスク通知後の人の「承認します」による、同送信先 https://github.com/tyaro/banto-ai.git への今後同種合成dev結果・ユーザー名を含むPC内入力path報告の継続承認で、report/current-handoff2文書を一回[skip ci] commit/pushする。保存後original Git/API returns/HEAD-upstream-remote ref-clean/docpinsはPOST優先、後追い文書再commit0。Git512KiB16entry/stdout1MiB/累積30秒維持、remote refはAPI照合。

automation詳細結果・PC内path転記/設定更新0、文書参照短指示ACTIVE維持。CI381385/code661bの4130success独立verifier完成保存維持、新query/download/verifier0/doc-onlyCI追跡0。旧381365/a54961最後in_progress履歴を維持。CI成功≠モデル性能/native/正式受入。

formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読/正式5残件・最終受入未完了/create_native早期拒否/全7役whole.run reader実起動禁止/元caps-unknown原owner-stop/追加agent禁止。未完了formal/native証明を少量dev開始条件に戻さない。Sol容量又は人の停止では保全後PAUSED、重複再試行0。
