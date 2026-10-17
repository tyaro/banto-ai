# dev layout1 C0 quality実評価・3候補×2strata比較（2026-10-12 JST）

## 実行範囲と原入力

保存済み合成dev seed2486912926863618161/layout1/quality-stressを既存CLIでC0 c0-diff-control一件だけ実compute_evaluation。新ID dev-layout1-quality-c0-20261012、10input pins照合→新input snapshot→fresh calibration→原profile/score/source-equipment episode/event/incident/metrics保存。元payload書込み・新dataset生成・replay・production/test変更・類似owner追加・追加agent・holdout本文読取り0。

入力manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\001\attempt-0001\result\payload\manifest.json

原manifest 75699B/72e5a34c662f77c4728583b9e61cc9d2977edd2ecc9e5286194aae0d2c055dbf。dataset anomaly-v03-dev-seed-2486912926863618161-layout-01-quality-stress。生成dataset identityのcandidate c0と、実評価cell candidate c0を別fieldで保持。actual文書checkout HEAD155ff984554cd2d66dfdc4522852feb19f6c0304、計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。CPython3.14.0 Windows AMD64、elapsed22.988368000020273秒、OScheckpoint peak private146255872B。

既存engineering900秒/2GiB private/output1GiB/single32MiB/files32のcheckpointを維持。blocking計算の中断・full loaded runtime閉包・全writer/global/native容量証明ではない。

## 原実結果

CLI exit0/run complete/1cell success。処理successをモデル性能合格・勝者・採択・正式受入にしない。

- 機械0/10・sensor0/10・precision0/3・clean誤警報2。
- calibrated48、C0原fit_samples各0、calibration各290、score14400。利用可能13880・不能520。
- 排他的primary {'current_target_quality': 30, 'mode_recipe_or_phase': 480, 'previous_target_quality_or_nonfinite': 10}。nonexclusive tags {'current_nonfinite': 30, 'current_target_quality': 30, 'mode_recipe_or_phase': 480, 'previous_target_quality_or_nonfinite': 30}は重複するので加算しない。全不能score/residual null、threshold_exceeded=false。
- 原mask/observation18000行対応、motor温度missing30観測を保存。current30+previous10の追加不能40。C0はC2のpeer120不能を持たない。
- source3/equipment3/incidents20/events40。全20未検出delay null、検出delay count0、median/mean/min/max原null。
- 全未対応equipment3のうちgrace1（motor vibration7241）とclean2（conveyor temperature7712/motor vibration8517）を別に保持。clean2を全未対応3へ書換えない。
- clean_rate原2/3365/value17.11738484398217、effective_clean_seconds3255/effective_clean_rate17.695852534562214。false_alert_burden原3/20/value15.0を単純確率へしない。

## 未検出とscoreの対応

20incident原reasonは{'first_candidate_no_target_onset': 1, 'no_candidate_in_window': 19}。19件candidate0、cycle00 machine一件candidate1/vibration-only。全causal_detected=false、matched=null、delay=null、selected target source=null/support[]を保持。

### cycle00 machine対象motor current

| sample | available | 原score | streak | exclusion |
| ---: | --- | ---: | ---: | --- |
| 7237 | True | 24.13687965714981 | 1 | None |
| 7238 | True | 0.22323097384624419 | 0 | None |
| 7239 | True | 0.5394257262617007 | 0 | None |
| 7240 | True | 25.687805712066133 | 1 | None |
| 7241 | True | 1.6416314938890728 | 0 | None |
| 7242 | True | 0.5818988360216674 | 0 | None |
| 7243 | True | 1.5811823637267521 | 0 | None |
| 7244 | True | 1.302227540560579 | 0 | None |

対象currentは7237/7240だけstreak1で翌行reset0、固定persistence2不成立。vibration7240原score70.58355978759485/streak1→7241score6.125274573419384/streak2でequipment episodeが成立しても、対象current onsetがないため原first_candidate_no_target_onset。first-equipment-onset-no-retry-v1の選択を後から成功へ補わない。全motor4target windowと原selected equipment/sourceをextractへ保持。

### cycle01 sensor（event内・matching窓内には欠測なし）

| sample | available | 原score | streak | exclusion |
| ---: | --- | ---: | ---: | --- |
| 7424 | True | 139.49845460413889 | 1 | None |
| 7425 | True | 0.13249641472748616 | 0 | None |
| 7426 | True | 0.09831784733996195 | 0 | None |
| 7427 | True | 139.8083797878649 | 1 | None |
| 7428 | True | 1.199526539173005 | 0 | None |
| 7429 | True | 0.8104032880277026 | 0 | None |
| 7430 | True | 1.0042503183617943 | 0 | None |
| 7431 | False | None | 0 | current_target_quality |

7424/7427温度の大きいscore各streak1は次のavailable行で0に戻る。欠測は7431からで、event/matching窓7424–7430の未検出を欠測だけで説明しない。

### cycle09 sensor（欠測resetあり）

| sample | available | 原score | streak | exclusion |
| ---: | --- | ---: | ---: | --- |
| 8864 | True | 138.82544532259593 | 1 | None |
| 8865 | False | None | 0 | current_target_quality |
| 8866 | False | None | 0 | current_target_quality |
| 8867 | False | None | 0 | current_target_quality |
| 8868 | False | None | 0 | previous_target_quality_or_nonfinite |
| 8869 | True | 0.10410432585740122 | 0 | None |
| 8870 | True | 1.0734440524407471 | 0 | None |
| 8871 | True | 0.3837202139755196 | 0 | None |

8864温度原score138.82544532259593/streak1の後、8865–8867 current欠測・8868 previous品質不良でreset、8869score0.10410432585740122/streak0。固定threshold4/persistence2不成立、candidate0/no_candidate_in_window/causalfalse/delaynull。欠測一件を全20missの説明へしない。

GT・C0threshold4/C1-C2threshold6・persistence2・matching・scienceは変更0。実入力対応・保存・状態分類の実経路不具合は観測なし。

## layout1 3候補×2strata比較完成

| stratum | candidate | machine | sensor | precision | clean誤警報 | available | delay count / median |
| --- | --- | --- | --- | --- | ---: | ---: | --- |
| core | c0-diff-control | 0/10 | 0/10 | 0/3 | 2 | 13920 | 0 / None |
| core | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 / 1.0 |
| core | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 / 1.0 |
| quality-stress | c0-diff-control | 0/10 | 0/10 | 0/3 | 2 | 13880 | 0 / None |
| quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 13880 | 19 / 1.0 |
| quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13760 | 19 / 1.0 |

今回C0 quality一件と保存済み旧5cellで比較を完成。旧5cell再compute0。core3候補の10input pins一致、quality3候補の10input pins一致、全6宣言16calculator source・candidate_config・compiled_candidate_config一致。C1/C2 qualityは集計19/19が同じでもsource29対38・利用可能13880対13760で原予測やepisode同一を主張しない。C0 core/qualityのclean2・全未対応3/未検出20も原値のまま。

## 旧layout0保存結果との比較

| stratum | candidate | machine | sensor | precision | clean誤警報 | available | delay count / median |
| --- | --- | --- | --- | --- | ---: | ---: | --- |
| core | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13920 | 0 / None |
| core | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 / 1.5 |
| core | c2-phase-conditional | 4/10 | 10/10 | 14/20 | 0 | 13920 | 14 / 1.0 |
| quality-stress | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13880 | 0 / None |
| quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 13880 | 19 / 2.0 |
| quality-stress | c2-phase-conditional | 4/10 | 9/10 | 13/19 | 0 | 13760 | 13 / 1.0 |

旧layout0全6cellはmanifest/config指標だけを参照、原未検出・過去failedを書換えない。C2機械recall layout0の4/10→layout1の10/10、C0両layout0/10、C1両10/10、quality sensorはC1/C2両9/10。これらは同seedのlayout/stratum条件差で、新独立seedではない。2layout×2strata×3candidate=12cellを12独立datasetにしない。bootstrap・統計CI・勝者・候補採択0。

## 原pinと保存root

| 原保存 | bytes | SHA256 |
| --- | ---: | --- |
| input observations | 9600602 | 6b177a9251d5d61bdb23075376e5c167c8f87b5ec1f46dbcac8a74fc4c7a341e |
| configuration | 5513 | fb31238bad82251f4b2176ee9a485fa794e09a83db62248a5a28f506418bea45 |
| manifest | 8064 | c23b11cd12880e4102db387a452a475a104445431294298da6e0e14f98808233 |
| evaluation-0 | 14336618 | a56b60b857586cd2501059c48084a3583a8fba292855ab9a1913921ac1ef096f |
| numerical | 14331020 | 7511ab943d7e3f936f64223a61cb7200d314c0d9eeb2c22579dd98f7c39244a1 |

| layout/stratum/candidate | 保存manifest bytes | SHA256 |
| --- | ---: | --- |
| 1/core/c0-diff-control | 8030 | 2617eca766b9a10e840ac5a7d5e9798cc1466e28989bbfdefae45484d4aa2236 |
| 1/core/c1-phase-level | 8024 | f1b3ebc59a9a4c0c762a1b1a6ead0bfdb2b8df1fac5d8e4731da9df68c0e2acd |
| 1/core/c2-phase-conditional | 8008 | 8005819bdc77823a6caddfb96dc33c49a6487186eaa69d4b48f5b37f020dde97 |
| 1/quality-stress/c1-phase-level | 8035 | 399af646470a861c738d4c6726772927936a4408aa445523e7440050a7a2cb54 |
| 1/quality-stress/c2-phase-conditional | 8039 | a2157815936c182eccc93409dddd4dfa16821ba482417df4d5a2b218b092844a |
| 0/core/c0-diff-control | 11019 | 0898a0ee0eb0a5a15af8e52d320832abe06220e30cb8cad0d02f7f774a01e094 |
| 0/core/c1-phase-level | 11019 | 0898a0ee0eb0a5a15af8e52d320832abe06220e30cb8cad0d02f7f774a01e094 |
| 0/core/c2-phase-conditional | 8015 | d70767ce2d8f174804565838011b709b0adced933787124cd5e02ee4285a96c9 |
| 0/quality-stress/c0-diff-control | 8057 | 15db2aeafb313691c8601220d3950580fa30ad7a16d543c5414700b16a9950ac |
| 0/quality-stress/c1-phase-level | 8042 | 3042be397642799af8c5ac6d0d2fb82c8f92f0a3d66a8fe983f8cc1b8e4431d3 |
| 0/quality-stress/c2-phase-conditional | 8062 | ef6829dbb07862056362ec19dc3934e5d94de6fc2c50fedc755a44d1e4751286 |
| 1/quality-stress/c0-diff-control | 8064 | c23b11cd12880e4102db387a452a475a104445431294298da6e0e14f98808233 |

| 原extract | records | bytes | SHA256 |
| --- | ---: | ---: | --- |
| incident-ledger-001.json | 20 | 20050 | 7f19e51b8f7441f3eb87f1331eccf71e3a36577ca0809d33a46e9889bb9db866 |
| selected-windows-001.json | 4 | 52986 | e952d68cb19d31b2b92c27fccc068345500941e1672ad49b0ca5d5cffdcad396 |
| selected-windows-002.json | 1 | 13004 | f0278cdd5b56f9ccf3d1c825bd21ea1c0de8e56811bdad53e195ce6786aa2866 |
| non-ok-input-records-001.json | 30 | 21952 | 990a135a54330a0c21bc799cc31af8652f423ffba90b55384727bedd22b5978e |
| all-source-equipment-episodes-001.json | 6 | 4716 | d6ebc3d68a34bfd423ac1f0b412a8ba9152f514105c252c4b5a1c96bfa2a508d |

data dev-layout1-quality-c0-20261012は{'bytes': 27383727, 'files': 19, 'manifest_pin': {'bytes': 2259, 'sha256': '1ccdc511bd60ba0b7cf500fb2673017639c8d974d637a68f4214c049571ce5a3'}}。EXTRACT representative-layout1-quality-c0-extract-20261012-prepは{'bytes': 113661, 'files': 6, 'manifest_pin': {'bytes': 953, 'sha256': 'd45ea35a578ae83c50c643adba5b6e31d2c9f973b1393bbc2405d3fe87f94834'}}。MAIN representative-layout1-quality-c0-20261012-prep、POST representative-layout1-quality-c0-post-20261012-prepのpost-save/owners/root-closedを最終Git保存状態として優先。新metadataはrecursive count/bytes/pins、python -B、512KiB/32entry/reserve128KiB/single128KiB。全新書込み前にscript・失敗・終端・closure reserve確認。閉鎖/外部固定済みroot追加・元helper再実行・raw削除移動・上限緩和0。

117science-source・旧41root count-byte-closure pin・C1 MAIN外部固定35file226520B・旧C2 cache補足pin不変。C1 MAIN entrycap超過を容量成功へ補わず内部root-closed未発行、C2 core原closureのcache coverage補足を原時点の完全閉包へしない。前回C2 quality原scope旧C1文字列/roster表示旧33対実37、原foreground close.pyのlarge stdout null TypeErrorと別metadata continuation完了を保全。

## 今回の準備toolエラーとowner照合

新script配置のforeground初回はrelative root対absolute ALLOWEDでAssertionError、file書込み前拒否。続くprepare/evaluate未存在path起動2件はsource評価前exit1、instrumented helper開始/モデルcompute0。原selected chunks903104/19940d/8f6c24をforeground-preparation-tool-errors.jsonへ保持。絶対rootで新scriptを配置した別continuation後だけ準備と今回C0を初めて実行。元builder再実行・元helper再実行0。foreground full creation/stdout-stderr None、selected traceを全process logにしない。モデル・CI・native・Sol容量failureへ読み替えない。

元99instrumented helpers full saved creation-start_token/live-execution一致、CIM同original不在、原9failed90passed、今回model/analysis2passed。repo helper-critical ownerなし。CIMdecimal100ns→microsecondtrunc/full token比較、PID単独判定0/native回収claim0。

## Git保存承認・CI・formal状態・次unit

人の送信リスク通知後「承認します」による https://github.com/tyaro/banto-ai.git への同種合成dev結果・ユーザー名を含むPC内path報告の継続送信承認を適用。report/current-handoff2文書を一回[skip ci] commit/pushする。原拒否/元未起動Githelperは履歴保全。Git保存後HEAD/upstream/lsremote/clean・docpinsはPOST優先、文書への後追い再commit0。Git caps512KiB16entry/stdout1MiB/累積30秒を維持。

CI38138556456/code661bの4130success独立verifier完成保存を維持、今回CIquery/download/verifier0、doc-onlyCI追跡0。旧381365/a54961最後in_progressは履歴のまま。CI成功はモデル性能/native/正式受入成功ではない。heartbeat banto-10は詳細payloadを含まない文書参照指示ACTIVEのまま、今回automation更新/詳細結果・PC内path転記0。

次の保存済みdev pairをchunk002 manifestmetadataだけで選択。manifest 75699B/c97c3564c28b679668c2f7425b33aaedadec0c90c45e5705e929131826797783、path C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\002\attempt-0001\result\payload\manifest.json。core dataset anomaly-v03-dev-seed-2486912926863618161-layout-02-core、same seed2486912926863618161/layout2、quality pairもmetadata10pins保存。新seedではない。初回shape inspectionと選択はいずれもmetadataのみ、次観測本文未読/次モデルcompute0/元payload書込み0/生成0。次unitはC0 c0-diff-control、新ID dev-next-core-c0-20261012の1cell実評価。新manifest pinを今回72e pinと混同しない。完成layout0/layout1全12cell・replay・旧risk-owner/native/probe/collector/Git37/CI反復0、追加agent禁止。

formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読/正式5残件・最終受入未完了/create_native早期拒否/全7役whole.run reader実起動禁止/元caps-unknown原owner-stop保持。未完成formal/native全証明を少量dev開始条件へ戻さない。Sol容量又は人の停止では原証拠保全後PAUSED、重複再試行0。
