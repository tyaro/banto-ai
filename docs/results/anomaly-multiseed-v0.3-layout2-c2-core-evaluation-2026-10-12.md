# dev layout2 C2 core実評価（2026-10-12 JST）

## 原入力と実行

保存済み合成dev seed2486912926863618161/layout2/coreを既存CLI C2 c2-phase-conditionalで1cell実compute_evaluation。新ID dev-layout2-core-c2-20261012。input10 pins照合→新snapshot→fresh fit/calibration→原profiles/scores/source-equipment episodes/events/incidents/metrics保存。元payload書込み・新dataset生成・replay・production/test変更・類似owner追加・追加agent・holdout本文読取り0。

input manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\002\attempt-0001\result\payload\manifest.json

manifest 75699B/c97c3564c28b679668c2f7425b33aaedadec0c90c45e5705e929131826797783、dataset anomaly-v03-dev-seed-2486912926863618161-layout-02-core。生成dataset identity candidate c0と実評価cell candidate C2を別fieldで保持。actual文書checkoutHEAD0374e0ced7f200811b926c4bc670b8992d758447、計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。actualPython3.14.0 Windows AMD64、elapsed118.49146509997081秒/OScheckpoint peak private205529088B。

既存engineering900秒/2GiB private/output1GiB/single32MiB/files32 checkpoint上限を維持。今回経過時間をモデルの性能や計算量比較へ使わない。blocking計算中断・full loaded runtime閉包・全writer/global/native容量証明ではない。

## 原実結果

CLI exit0/complete/1cell success。処理successを性能合格・正式受入・勝者・採択へしない。

- 機械10/10・sensor10/10・precision20/20・clean誤警報0・全未対応equipment0。
- calibrated48、原fit_samples各600/calibration各290、score14400。利用可能13920・不能480、全mode_recipe_or_phase。不能score/residual null/threshold_exceeded=false。
- 原mask/observation18000行対応/non-ok0、欠測不能・peer不能0。
- source49/equipment20/incidents20/events40、全20causal_detected/candidate1。
- 全20delay原1秒、median/mean/min/max各1秒、未検出補完0。
- clean_rate原0/3365/value0、effective_clean_seconds3254/effective_clean_rate0.0、false_alert_burden原0/20/value0。

全原sourceのtarget別件数: {'motor-01.motor_current': 20, 'motor-01.motor_temperature': 19, 'motor-01.vibration_feature': 10}。機械・sensorの集計がC1と一致しても、source30対49及びeffective_clean_seconds3255対3254の原差を保持し、score/episodeの一致を主張しない。

## 対象sourceと原incident対応

全20selected_source_episode_idを原sourceへ、matched_episode_idを原equipmentへ対応。source.full_target=event.full_target、source ID∈equipment.source_episode_ids、equipment.matched_event_id=event ID。原target-source onset=event start+1000ms、support_score_ids各2件。原event/incident/target-source/equipmentをmatched-target-pairsへ保存。

| cycle/class | event start sample | target source | onset_ms | support数 | delay秒 |
| --- | ---: | --- | ---: | ---: | ---: |
| 0/machine | 7274 | motor-01.motor_current | 1767232875000 | 2 | 1.0 |
| 0/sensor | 7281 | motor-01.motor_temperature | 1767232882000 | 2 | 1.0 |
| 1/machine | 7454 | motor-01.motor_current | 1767233055000 | 2 | 1.0 |
| 1/sensor | 7461 | motor-01.motor_temperature | 1767233062000 | 2 | 1.0 |
| 2/machine | 7634 | motor-01.motor_current | 1767233235000 | 2 | 1.0 |
| 2/sensor | 7641 | motor-01.motor_temperature | 1767233242000 | 2 | 1.0 |
| 3/machine | 7814 | motor-01.motor_current | 1767233415000 | 2 | 1.0 |
| 3/sensor | 7821 | motor-01.motor_temperature | 1767233422000 | 2 | 1.0 |
| 4/machine | 7994 | motor-01.motor_current | 1767233595000 | 2 | 1.0 |
| 4/sensor | 8001 | motor-01.motor_temperature | 1767233602000 | 2 | 1.0 |
| 5/machine | 8174 | motor-01.motor_current | 1767233775000 | 2 | 1.0 |
| 5/sensor | 8181 | motor-01.motor_temperature | 1767233782000 | 2 | 1.0 |
| 6/machine | 8354 | motor-01.motor_current | 1767233955000 | 2 | 1.0 |
| 6/sensor | 8361 | motor-01.motor_temperature | 1767233962000 | 2 | 1.0 |
| 7/machine | 8534 | motor-01.motor_current | 1767234135000 | 2 | 1.0 |
| 7/sensor | 8541 | motor-01.motor_temperature | 1767234142000 | 2 | 1.0 |
| 8/machine | 8714 | motor-01.motor_current | 1767234315000 | 2 | 1.0 |
| 8/sensor | 8721 | motor-01.motor_temperature | 1767234322000 | 2 | 1.0 |
| 9/machine | 8894 | motor-01.motor_current | 1767234495000 | 2 | 1.0 |
| 9/sensor | 8901 | motor-01.motor_temperature | 1767234502000 | 2 | 1.0 |

### cycle00 machine current / low_speed

| sample | available | 原score | streak | source onset ID |
| ---: | --- | ---: | ---: | --- |
| 7274 | True | 49.28458394946862 | 1 | None |
| 7275 | True | 49.02404495283814 | 2 | anomaly-v03-dev-seed-2486912926863618161-layout-02-core-c2-phase-conditional-score-motor-01-motor_current-7275-source |
| 7276 | True | 48.646628952799794 | 3 | anomaly-v03-dev-seed-2486912926863618161-layout-02-core-c2-phase-conditional-score-motor-01-motor_current-7275-source |
| 7277 | True | 1.6715656745824374 | 0 | None |
| 7278 | True | 0.6840906770091375 | 0 | None |
| 7279 | True | 1.104263684280336 | 0 | None |
| 7280 | True | 1.6758919781843638 | 0 | None |

7274原score49.28458394946862/streak1→7275score49.02404495283814/streak2、対象current onset7275/support7274-7275、delay1秒。C1の同sample原score51.59165260396215/51.395517836296015とは別結果として保持。

### cycle00 sensor temperature / low_speed

| sample | available | 原score | streak | source onset ID |
| ---: | --- | ---: | ---: | --- |
| 7281 | True | 174.14501313657786 | 1 | None |
| 7282 | True | 174.11704162166737 | 2 | anomaly-v03-dev-seed-2486912926863618161-layout-02-core-c2-phase-conditional-score-motor-01-motor_temperature-7282-source |
| 7283 | True | 174.4433396772872 | 3 | anomaly-v03-dev-seed-2486912926863618161-layout-02-core-c2-phase-conditional-score-motor-01-motor_temperature-7282-source |
| 7284 | True | 0.08245306277919735 | 0 | None |
| 7285 | True | 0.35138651373352914 | 0 | None |
| 7286 | True | 0.44231525133233385 | 0 | None |
| 7287 | True | 0.9616198684535403 | 0 | None |

7281原score174.14501313657786/streak1→7282score174.11704162166737/streak2、対象temperature onset7282/support7281-7282、delay1秒。原matched equipment IDはmotor_currentを含むが、実対象selected sourceはmotor_temperatureで、そのsource IDがequipment.source_episode_ids内に存在することを照合。ID名から対象sourceを補わない。

cycle01 machine/sensorとcycle09 sensorも原motor4target score窓・selected source/equipmentを保存。threshold6/persistence2/second-exceedance/GT/first-equipment-onset-no-retry-v1/science変更0。実入力対応・保存・状態分類の実経路不具合観測なし。

## 3候補coreと旧layout C2の保存比較

| layout | candidate | machine | sensor | precision | clean誤警報 | available | delay count / median |
| ---: | --- | --- | --- | --- | ---: | ---: | --- |
| 0 | c2-phase-conditional | 4/10 | 10/10 | 14/20 | 0 | 13920 | 14 / 1.0 |
| 1 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 / 1.0 |
| 2 | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13920 | 0 / None |
| 2 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 / 1.0 |
| 2 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 / 1.0 |

同layout2 coreのC0/C1/C2比較が完成。同入力10pin/宣言16calculator source/candidate_config/compiled_candidate_config一致。C0の機械0/10・sensor0/10・precision0/3・clean3・原20no_candidate/delaynullを保持。C0threshold4/C1-C2threshold6は既存固定設定のまま。

旧layout0/1 C2は保存manifest/config指標のみ参照、旧evaluation本文再展開・モデル再compute0。layout0機械4/10・sensor10/10・precision14/20、layout1機械10/10・sensor10/10・precision20/20の原差を保存。同seed別layoutで新独立seedではない。集計一致を原予測/score/episode同一へせず、bootstrap・統計CI・勝者・採択0。今回新actual1cell、旧完成4比較cell再compute0、完成layout0/layout1全12cell・layout2C0/C1・明示replay・risk tests反復0。

## 原pinと閉鎖

| 原保存 | bytes | SHA256 |
| --- | ---: | --- |
| input observations | 9600596 | 57b2d660806a00eb3d14d5eb262163ff38273b497ee5665ba994598875dddc02 |
| configuration | 5508 | 8e546225138f5b4e841394e44a894e5940a9d343c5473b4ed6b6e2cac4d57da2 |
| manifest | 8009 | c1cf4496d07b9b8b53f4f98ac8b12d2dd548b06beaecabad49e13f069f835d16 |
| evaluation-0 | 24761031 | 86bbddc3b84bdb1b114d84f7d408cc2f6d46cc435db779922b9775b483aba9c5 |
| numerical | 24755533 | 66feb8be78abbdaeeaafff9b5e13dc7f6bcc0762ab4d13b2bb59a5b828fccf54 |

| layout/candidate保存manifest | bytes | SHA256 |
| --- | ---: | --- |
| 2/c0-diff-control | 8028 | dfaff1ed6a29deb373db3b0598001fe0807abefdfca2e6acaf08b72baaa6ad9b |
| 2/c1-phase-level | 8002 | 6a8a1537204cb240080e1f808e875975036fc6dba5b4925d2f893f46f189dd42 |
| 1/c2-phase-conditional | 8008 | 8005819bdc77823a6caddfb96dc33c49a6487186eaa69d4b48f5b37f020dde97 |
| 0/c2-phase-conditional | 8015 | d70767ce2d8f174804565838011b709b0adced933787124cd5e02ee4285a96c9 |
| 2/c2-phase-conditional | 8009 | c1cf4496d07b9b8b53f4f98ac8b12d2dd548b06beaecabad49e13f069f835d16 |

| 原extract | records | bytes | SHA256 |
| --- | ---: | ---: | --- |
| incident-ledger-001.json | 20 | 33694 | d31b20f9fdfcda12a64701cece8ab7fad204d2414f8587214545354cb709f8f8 |
| matched-target-pairs-001.json | 19 | 64235 | 476315bd99e251df38153f00a6738a773a946ec44f9b1cb528e637850a318445 |
| matched-target-pairs-002.json | 1 | 3529 | 7df4e4928fe0be9056a10be576a538169b67393d5300dffd8e51b86a53357cfa |
| selected-windows-001.json | 3 | 51629 | 9fee0c06a7e1a88aa318b59e13b0f7e56c49c49216a7af3b2cfdccd4624f8a32 |
| selected-windows-002.json | 2 | 32507 | 05561672325317f61bdcbf42e36d1714cedc6ed7d6ccd8f4c360c4e34e4219a1 |
| all-source-equipment-episodes-001.json | 69 | 58237 | b099b9f22c8201393b26182ebb48cce61938729ffc824c2d7798bebb0fc1e071 |

DATA dev-layout2-core-c2-20261012閉鎖{'bytes': 37801721, 'files': 19, 'manifest_pin': {'bytes': 2254, 'sha256': '150b390b0b940948fd4e9ad421f2b23a3826a1f0436fb6e1333209a947691799'}}。EXTRACT representative-layout2-core-c2-extract-20261012-prep閉鎖{'bytes': 244910, 'files': 7, 'manifest_pin': {'bytes': 1079, 'sha256': '7742559d1d96606653c0c50cee70c139ade3e25d8db8304e55dbc2494e5b37b6'}}。MAIN representative-layout2-core-c2-20261012-prepとPOST representative-layout2-core-c2-post-20261012-prepのpost-save/owners/root-closedを最終Git状態として優先。

117science-source/旧53root count-byte-closure pin/旧C1 MAIN外部固定35file226520B/旧C2 cache補足pin不変。過去failed/capacityfalse/coverage limits/旧scope-roster表示/foreground metadata失敗を保全。閉鎖・外部固定root追記・旧helper再実行・raw削除移動・上限緩和0。新metadataはpython-B/recursive full coverage、512KiB32entry/reserve128KiB/single128KiB。新script/失敗証拠/closure分を新書込み前に確認し、対象文字列のみ変更/hash-seed無限定置換0。

元108instrumented helpers full saved creation-start_token/live-execution一致、原9failed99passed/CIM同original不在/repo helpercriticalなし。今回model/analysis2passed/newfailed0。CIMdecimal100ns→microsecond truncation/full saved token/PID単独0/native回収claim0。foreground fullcreation/stdioNone、selectedCLIを全helperstdioへしない。

## 承認・次unit・正式状態

送信リスク通知後の人の「承認します」による、同送信先 https://github.com/tyaro/banto-ai.git への今後の同種合成dev結果・ユーザー名を含むPC内入力path報告の継続承認で、report/current-handoff2文書を一回[skip ci] commit/pushする。保存後HEAD/upstream/lsremote/clean/docpinsはPOSTを優先し、後追い文書再commit0。原審査拒否/元Githelper未起動は履歴保持。Git512KiB16entry/stdout1MiB/累積30秒上限を維持。

次unitは同保存chunk002/seed2486912926863618161/layout2/quality-stressをC1 c1-phase-level、新ID dev-layout2-quality-c1-20261012で1cell実評価。dataset anomaly-v03-dev-seed-2486912926863618161-layout-02-quality-stress、同manifest c97c pin維持。qualityはmetadata10pinsのみ保存、観測本文未読/compute0。生成identity c0と次実評価C1を別fieldで保持。元payload書込み/生成/旧評価再実行0。

automationの詳細結果・PC内path転記/設定更新0、短い文書参照指示ACTIVEを維持。CI381385/code661bの4130success独立verifier完成保存維持、今回CIquery/download/verifier0/doc-onlyCI追跡0。旧381365/a54961最後in_progressは履歴のまま。CI成功をモデル性能/native/正式受入へしない。

formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読/正式5残件・最終受入未完了/create_native早期拒否/全7役whole.run reader実起動禁止/元caps-unknown原owner-stop/追加agent禁止。未完了formal/native証明を少量dev開始条件へ戻さない。Sol容量又は人の停止では保全後PAUSED、重複再試行0。
