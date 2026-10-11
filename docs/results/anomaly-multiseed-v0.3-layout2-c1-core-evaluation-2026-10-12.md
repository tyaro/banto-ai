# dev layout2 C1 core実評価（2026-10-12 JST）

## 原入力と実行範囲

保存済み合成dev seed2486912926863618161/layout2/coreを既存CLI C1 c1-phase-levelで一件実compute_evaluation。新ID dev-layout2-core-c1-20261012。10input pins照合→新input snapshot→fresh phase fit/calibration→原profile/score/episode/event/incident/metrics保存。元payload書込み・新dataset生成・replay・production/test変更・類似owner追加・追加agent・holdout本文読取り0。

input manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\002\attempt-0001\result\payload\manifest.json

manifest 75699B/c97c3564c28b679668c2f7425b33aaedadec0c90c45e5705e929131826797783、dataset anomaly-v03-dev-seed-2486912926863618161-layout-02-core。生成dataset identityのcandidate c0と実評価cell candidate c1を別fieldで保持。actual文書checkoutHEAD873e52055d6eeeb25bdc4e11b7670e6c1dacd32d、計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。actualPython3.14.0 Windows AMD64、elapsed17.21061579999514秒/OScheckpoint peak private147296256B。

既存engineering900秒/2GiB private/output1GiB/single32MiB/files32のcheckpoint上限を維持。blocking計算中断・full loaded runtime閉包・全writer/global/native容量証明ではない。

## 原実結果

CLI exit0/complete/1cell success。処理successをモデル性能合格・正式受入・勝者・採択へしない。

- 機械10/10・sensor10/10・precision20/20・clean誤警報0・全未対応equipment0。
- calibrated48、原fit_samples各600/calibration各290、score14400。利用可能13920・不能480、全primary/nonexclusive mode_recipe_or_phase。全不能score/residual null/threshold_exceeded=false。
- 原input mask/observation18000行対応/non-ok0、欠測不能・peer不能0。
- source30/equipment20/incidents20/events40、全20causal_detected/candidate1/対象sourceと原support2件・matched equipment対応。
- 全20原delay1秒、median/mean/min/max各1秒、未検出補完0。
- clean_rate原0/3365/value0、effective_clean_seconds3255/effective_clean_rate0、false_alert_burden0/20/value0を原値として保存。

## 対象source・support・incident対応

全20incident.selected_source_episode_idを原sourceへ、matched_episode_idを原equipmentへ対応し、source.full_target=event.full_target/source IDがequipment.source_episode_ids内/equipment.matched_event_id=event IDを確認。全source onsetはevent start+1000ms、incident.support_score_ids各2件。原source/equipment/event/incidentをmatched-target-pairsへまとめて保存し、時刻やsupportを後から生成しない。

| cycle / event class | event start sample | 原target source | 原onset_ms | support数 | delay秒 |
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

### cycle00 machine motor current / low_speed

| sample | available | 原score | streak | 原source onset ID |
| ---: | --- | ---: | ---: | --- |
| 7274 | True | 51.59165260396215 | 1 | None |
| 7275 | True | 51.395517836296015 | 2 | anomaly-v03-dev-seed-2486912926863618161-layout-02-core-c1-phase-level-score-motor-01-motor_current-7275-source |
| 7276 | True | 51.07311008305209 | 3 | anomaly-v03-dev-seed-2486912926863618161-layout-02-core-c1-phase-level-score-motor-01-motor_current-7275-source |
| 7277 | True | 1.6693689319622866 | 0 | None |
| 7278 | True | 0.7078108852228359 | 0 | None |
| 7279 | True | 1.1305197545185393 | 0 | None |
| 7280 | True | 1.5873851084651682 | 0 | None |

7274原score51.59165260396215/streak1→7275score51.395517836296015/streak2で対象current source onset7275。原support7274/7275、candidate equipmentとevent対応、delay1秒。固定C1threshold6/persistence2/second-exceedanceの実原結果。

### cycle00 sensor motor temperature / low_speed

| sample | available | 原score | streak | 原source onset ID |
| ---: | --- | ---: | ---: | --- |
| 7281 | True | 172.2153491040522 | 1 | None |
| 7282 | True | 172.35168015514307 | 2 | anomaly-v03-dev-seed-2486912926863618161-layout-02-core-c1-phase-level-score-motor-01-motor_temperature-7282-source |
| 7283 | True | 172.82027282404238 | 3 | anomaly-v03-dev-seed-2486912926863618161-layout-02-core-c1-phase-level-score-motor-01-motor_temperature-7282-source |
| 7284 | True | 0.06506487887255737 | 0 | None |
| 7285 | True | 0.42231565258883547 | 0 | None |
| 7286 | True | 0.39058407826176295 | 0 | None |
| 7287 | True | 0.850053378417086 | 0 | None |

7281原score172.2153491040522/streak1→7282score172.35168015514307/streak2で対象temperature source onset7282。原support7281/7282、delay1秒。cycle01 machine/sensor及びcycle09 sensorも全motor4target score窓・原selected source/equipmentを保存。GT・threshold6・persistence2・first-equipment-onset-no-retry-v1・science変更0。実入力対応・保存・状態分類実経路不具合観測なし。

## 同入力C0・旧layout C1 coreとの保存比較

| layout | candidate | machine | sensor | precision | clean誤警報 | available | delay count / median |
| ---: | --- | --- | --- | --- | ---: | ---: | --- |
| 0 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 / 1.5 |
| 1 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 / 1.0 |
| 2 | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13920 | 0 / None |
| 2 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 / 1.0 |

同layout2 C0 coreのinput10全pin一致、宣言16calculator source・candidate_config・compiled_candidate_config一致。C0の0/10・0/10・precision0/3・clean3・原20no_candidate/delaynullを今回C1へ書換えない。旧C0再compute0/原result本文再展開0。C0threshold4/C1threshold6は既存固定設定のまま。

旧layout0/1 C1も保存manifest/config指標だけ参照、旧モデル再compute0。旧layout0 delaymedian1.5秒・旧layout1 1秒、今回は全20原1秒。同seed別layoutで新独立seedではない。集計10/10一致から原score/episode同一を主張しない。bootstrap・統計CI・勝者・採択0。完成layout0/layout1全12cell・layout2C0・明示replay・既存risk testsを反復しない。

## 原pin・閉鎖root

| 原保存 | bytes | SHA256 |
| --- | ---: | --- |
| input observations | 9600596 | 57b2d660806a00eb3d14d5eb262163ff38273b497ee5665ba994598875dddc02 |
| configuration | 5502 | 61ae444efc9530c40bb3175b4bc787ed4788d7d6a398388764c678b700092ebe |
| manifest | 8002 | 6a8a1537204cb240080e1f808e875975036fc6dba5b4925d2f893f46f189dd42 |
| evaluation-0 | 14072138 | efbbaa232bc7632fbf03d1948ed24cc97d24448ace97bf095d2bfafdceaaf35d |
| numerical | 14066640 | d103130baebac6c539f4ef39778e98e38627a7cdb63ddd4319eb7444661c5589 |

| layout/candidate保存manifest | bytes | SHA256 |
| --- | ---: | --- |
| 2/c0-diff-control | 8028 | dfaff1ed6a29deb373db3b0598001fe0807abefdfca2e6acaf08b72baaa6ad9b |
| 1/c1-phase-level | 8024 | f1b3ebc59a9a4c0c762a1b1a6ead0bfdb2b8df1fac5d8e4731da9df68c0e2acd |
| 0/c1-phase-level | 11019 | 0898a0ee0eb0a5a15af8e52d320832abe06220e30cb8cad0d02f7f774a01e094 |
| 2/c1-phase-level | 8002 | 6a8a1537204cb240080e1f808e875975036fc6dba5b4925d2f893f46f189dd42 |

| 原extract | records | bytes | SHA256 |
| --- | ---: | ---: | --- |
| incident-ledger-001.json | 20 | 33088 | 68e301f49cd55f6352b48de74802fc80dca7680c95c5be97d066fefc3faaf99a |
| matched-target-pairs-001.json | 20 | 63668 | 338389b8b79ba414f4111cc35ca1dae846c822d29edb0d7cc6be0ef1b30f7730 |
| selected-windows-001.json | 4 | 62488 | ef741849c7716fca9a30ff6efdf4b1ba925df35e8dca910b9f0b22b658d0230f |
| selected-windows-002.json | 1 | 15187 | daf55228f699b251a2f0452fe0da04ae75f8919b16b0123c7bd4003cb8ef9ccf |
| all-source-equipment-episodes-001.json | 50 | 38818 | ad1929cee6188eeedd14f9a3493b8ce90f103db4c9f546e5d7dad12d68e64af8 |

data dev-layout2-core-c1-20261012閉鎖{'bytes': 27112791, 'files': 19, 'manifest_pin': {'bytes': 2248, 'sha256': '6f7e0209f78909cbd37d2cbee34891863f1a806fb4de61c8229bf467cb3d5382'}}。EXTRACT representative-layout2-core-c1-extract-20261012-prep閉鎖{'bytes': 214199, 'files': 6, 'manifest_pin': {'bytes': 950, 'sha256': '9e8ace9a0f7b4eb6e3887e22431e2d40fe465c6418427c785b77d062bb094682'}}。MAIN representative-layout2-core-c1-20261012-prep/POST representative-layout2-core-c1-post-20261012-prepのpost-save/owners/root-closedを最終Git状態として優先。

新metadataはpython -B/recursive count-byte-pin、512KiB32entry/reserve128KiB/single128KiB。書込み前にscript/失敗/終端/closure reserve確認、closed/外部固定root追加・原helper再実行・raw削除移動・上限緩和0。EXTRACTscopeは実candidateから作成。117science-source・旧49root count-byte-closure pin・C1 MAIN外部固定35file226520B・旧C2 cache補足pin不変。過去C1 MAIN容量超過/原failed、旧C2 coverage補足、旧scope/roster文字列/foreground metadata失敗を保全し、今回successへ書換えない。

元105instrumented helpers full saved creation-start_token/live-execution一致、原9failed96passed/CIM同original不在/repo helper-criticalownerなし、今回model/analysis2passed。CIMdecimal100ns→microsecondtrunc/full saved token/PID単独0/native回収claim0。foreground fullcreation/stdioNone、selectedCLIを全helperstdioにしない。補助scriptはcandidate/filename/対象comparison block等の正確文字列だけ変更、hash/seed無限定置換0、今回newfailed0。

## Git承認・次unit・formal状態

送信リスク通知後の人の「承認します」による同送信先 https://github.com/tyaro/banto-ai.git への同種合成dev結果・ユーザー名を含むPC内input path報告の継続承認でreport/current-handoff2文書を一回[skip ci] commit/pushする。保存後HEAD/upstream/lsremote/clean/docpinsはPOSTを優先し後追い文書再commit0。原自動審査拒否/元Githelper未起動は履歴保全。Git caps512KiB16entry/stdout1MiB/累積30秒維持。automationは文書参照短指示ACTIVEのまま、今回詳細結果・PC内path転記/設定更新0。

次unitは同保存chunk002 manifest/dev seed/layout2/core、candidate C2 c2-phase-conditional、新ID dev-layout2-core-c2-20261012で1cell実評価。input manifest c97c3564c28b679668c2f7425b33aaedadec0c90c45e5705e929131826797783維持。生成dataset identity c0を実評価C2と混同せず別fieldにする。元payload書込み/生成/旧cell再実行0。同layout2 quality pairは保存metadata10pinsだけ、次quality観測本文未読/compute0。

CI38138556456/code661bの4130success独立verifier完成保存を維持、今回CIquery/download/verifier0/doc-onlyCI追跡0。旧381365/a54961最後in_progressは履歴のまま。CI成功はモデル性能/native/正式受入成功ではない。

formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読/正式5残件・最終受入未完了/create_native早期拒否/全7役whole.run reader実起動禁止/元caps-unknown原owner-stop/追加agent禁止。未完了formal/native全証明を少量dev開始条件へ戻さない。Sol容量又は人の停止では原証拠保全後PAUSED、重複再試行0。
