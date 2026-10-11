# dev layout2 C2 quality-stress実評価（2026-10-12 JST）

## 原入力と実行範囲

保存済み合成dev seed2486912926863618161/layout2/quality-stressを既存CLI C2 c2-phase-conditionalで1cell実compute_evaluation。新ID dev-layout2-quality-c2-20261012。input10pins照合→新snapshot→fresh fit/calibration→原profile/score/source-equipment episodes/events/incidents/metrics保存。元payload書込み・新dataset生成・replay・production/test変更・類似owner・追加agent・holdout本文読取り0。

input manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\002\attempt-0001\result\payload\manifest.json

manifest 75699B/c97c3564c28b679668c2f7425b33aaedadec0c90c45e5705e929131826797783、dataset anomaly-v03-dev-seed-2486912926863618161-layout-02-quality-stress。生成identity candidate c0と実評価C2を別fieldで保持。文書checkout88a79a2e85a35ca0652ae0a227f2043c00437a29、計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。Python3.14.0 Windows AMD64、elapsed31.396069999900647秒/OScheckpoint peak private208371712B。

engineering900秒/2GiB private/output1GiB/single32MiB/files32 checkpoint上限を維持。blocking計算中断/full loaded runtime閉包/allwriter/global/native容量証明ではない。

## 原結果

CLI exit0/complete/1cell success。処理successをモデル性能合格・正式受入・勝者・採択へしない。

- 機械10/10・sensor9/10・precision19/19・clean誤警報0・全未対応equipment0。
- calibrated48、fit_samples各600/calibration各290、score14400。利用可能13796・不能604。
- 原mask-observation18000行対応、motor温度missing30観測行。他targetの欠測0。
- source47/equipment19/events40/incidents20、検出19件だけdelay原1秒/median mean min max各1秒。未検出1件delay null。
- clean_rate原0/3365/value0、effective_clean_seconds3254/effective_clean_rate0.0、false_alert_burden原0/20/value0。

## peer依存とphase重複

排他的primaryはphase471/current quality30/peer quality93/previous quality10、合計604。非排他的tagsはphase480/peer120/current quality30/current nonfinite30/previous quality30。全不能score/residual null/threshold_exceeded=false、tagsを独立行として加算しない。

| peer対象 | peer tag行数 | peer primary行数 |
| --- | ---: | ---: |
| motor-01.conveyor_speed | 40 | 31 |
| motor-01.motor_current | 40 | 31 |
| motor-01.vibration_feature | 40 | 31 |

同motor温度の欠測30観測により、他3targetでcurrent/previous peer品質を要するscore各40行がpeer tagを持つ（合計120）。このうち各9行、計27行はphase除外と同じ行で、primaryはmode_recipe_or_phase。peerをprimaryとする独立不能は各31行、計93行。温度自身のcurrent quality30/previous quality10にもphaseとの重複9行があり、phase primaryは471。

MAIN quality-peer-phase-analysis.jsonに、原温度phase品質重複9score全field、原peer120scoreの選択field projection、peer-phase重複27score ID、全target別primary内訳と原result pinを保存。peer projectionはfull score recordではないことを明示し、原値から時刻・tags・scoreを生成しない。原全scoresはevaluation-0.jsonへ別保存。

同core C2の不能480→今回604の原差124。同入力quality C1の不能511→今回604の原差93で、peer tag120をそのまま差へ加算しない。旧layout0/1 C2 qualityの不能640を今回へ流用しない。原欠測30観測と8target score不能604行は別量。

## cycle09 sensor未検出

対象 motor-01.motor_temperature、start/end8901/8904、matching window end8907。原reason no_candidate_in_window/candidate0/causalfalse/matched-source-equipment null/support[]/delay None。

| sample | available | 原score | streak | exclusion primary | tags |
| ---: | --- | ---: | ---: | --- | --- |
| 8901 | True | 174.11693795872273 | 1 | None |  |
| 8902 | False | None | 0 | current_target_quality | current_target_quality,current_nonfinite |
| 8903 | False | None | 0 | current_target_quality | current_target_quality,current_nonfinite,previous_target_quality_or_nonfinite |
| 8904 | False | None | 0 | current_target_quality | current_target_quality,current_nonfinite,previous_target_quality_or_nonfinite |
| 8905 | False | None | 0 | previous_target_quality_or_nonfinite | previous_target_quality_or_nonfinite |
| 8906 | True | 0.4036919935733669 | 0 | None |  |
| 8907 | True | 0.581755153843359 | 0 | None |  |

8901原score174.11693795872273>threshold6/streak1。8902–8904 current quality不能、8905 previous quality不能でstreak0。8906復帰score0.4036919935733669、8907score0.581755153843359で固定persistence2不成立。同じwindowの他motor3targetも原peer不能を保存。C1同対象の原score172.3497212823758/復帰0.12350638684184247とは別結果として保持。

閾値6/persistence2/second-exceedance/GT/first-equipment-onset-no-retry-v1/science変更0。未検出を成功へ補わず、delay nullを0等に埋めない。実入力対応・保存・状態分類の実経路不具合観測なし。

## 検出19件のtarget source対応

全19selected target source.full_target=event.full_target/source ID∈matched equipment.source_episode_ids/equipment.matched_event_id=event IDを照合。原target onset=event start+1000ms、support_score_ids各2件。

| cycle/class | 原target source | onset_ms | support数 | delay秒 |
| --- | --- | ---: | ---: | ---: |
| 0/machine | motor-01.motor_current | 1767232875000 | 2 | 1.0 |
| 0/sensor | motor-01.motor_temperature | 1767232882000 | 2 | 1.0 |
| 1/machine | motor-01.motor_current | 1767233055000 | 2 | 1.0 |
| 1/sensor | motor-01.motor_temperature | 1767233062000 | 2 | 1.0 |
| 2/machine | motor-01.motor_current | 1767233235000 | 2 | 1.0 |
| 2/sensor | motor-01.motor_temperature | 1767233242000 | 2 | 1.0 |
| 3/machine | motor-01.motor_current | 1767233415000 | 2 | 1.0 |
| 3/sensor | motor-01.motor_temperature | 1767233422000 | 2 | 1.0 |
| 4/machine | motor-01.motor_current | 1767233595000 | 2 | 1.0 |
| 4/sensor | motor-01.motor_temperature | 1767233602000 | 2 | 1.0 |
| 5/machine | motor-01.motor_current | 1767233775000 | 2 | 1.0 |
| 5/sensor | motor-01.motor_temperature | 1767233782000 | 2 | 1.0 |
| 6/machine | motor-01.motor_current | 1767233955000 | 2 | 1.0 |
| 6/sensor | motor-01.motor_temperature | 1767233962000 | 2 | 1.0 |
| 7/machine | motor-01.motor_current | 1767234135000 | 2 | 1.0 |
| 7/sensor | motor-01.motor_temperature | 1767234142000 | 2 | 1.0 |
| 8/machine | motor-01.motor_current | 1767234315000 | 2 | 1.0 |
| 8/sensor | motor-01.motor_temperature | 1767234322000 | 2 | 1.0 |
| 9/machine | motor-01.motor_current | 1767234495000 | 2 | 1.0 |

全20event/incident、19matched target-source-equipment、5selectedmotor4target窓、30non-ok mask/observation、全source/equipmentを新EXTRACTへ保存。

## 同core・quality C1・旧quality C2の保存比較

| layout/stratum | candidate | machine | sensor | precision | clean | available | delay count / median |
| --- | --- | --- | --- | --- | ---: | ---: | --- |
| 0/quality-stress | c2-phase-conditional | 4/10 | 9/10 | 13/19 | 0 | 13760 | 13 / 1.0 |
| 1/quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13760 | 19 / 1.0 |
| 2/core | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 / 1.0 |
| 2/quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 13889 | 19 / 1.0 |
| 2/quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13796 | 19 / 1.0 |

全5cellの宣言16calculator source/candidate_config/compiled_candidate_config一致、同seed/role devを保持。同layout2 quality C1/C2のinput10全pin一致、core対quality/別layoutのinput pin差を保存。旧manifest/config指標だけ参照、旧4比較cell result本文再展開/再compute0。

C1/C2 qualityの機械・sensor・precision・clean・delay集計が一致しても、原score・source29対47・利用不能511対604の差を保持し、原予測/episode同一を主張しない。旧layout0 C2機械4/10と旧layout1/今回10/10を別layoutの原結果として保持。

同seed別layout/strata、新独立seedではない。bootstrap・統計CI・勝者・採択0。完成16cell/layout0-layout1全12/layout2core3及びqualityC1/replay/risk tests/旧CI反復0。

## 原pin・保存root

| 原保存 | bytes | SHA256 |
| --- | ---: | --- |
| input observations | 9600603 | 9c4ba47cae6728cf74181a8f3ebcdfe2a13a95ce98862d9e042ea4b8f9a83d74 |
| configuration | 5518 | 07ea61faac9b621046b1bd5f5de19f182e77a1650d9084552c12952d0cfcea74 |
| manifest | 8041 | 619ba0e5f5b6758c54886d41edde95ad26c1cbb7568476e689f77b3286eb4f92 |
| evaluation-0 | 25202644 | 773a0d1b468374657021d60ad8dd6691969cd0a4c0860bf931edceb6f7f4b821 |
| numerical | 25197046 | 2defbfb5ce07aa920526dffb8a7fabebbe803e0f3144c8d6a2ed997905b1e97d |
| quality-peer-phase analysis | 69057 | ab196709ea30f11663783eb1600b1dd1e641e1fce40ff20704dcd3720dc7c49e |

| 保存manifest layout/stratum/candidate | bytes | SHA256 |
| --- | ---: | --- |
| 2/core/c2-phase-conditional | 8009 | c1cf4496d07b9b8b53f4f98ac8b12d2dd548b06beaecabad49e13f069f835d16 |
| 2/quality-stress/c1-phase-level | 8034 | 67308ad3afa221abfa1e118dd9447bb721306c843440719e80de29941732d38f |
| 1/quality-stress/c2-phase-conditional | 8039 | a2157815936c182eccc93409dddd4dfa16821ba482417df4d5a2b218b092844a |
| 0/quality-stress/c2-phase-conditional | 8062 | ef6829dbb07862056362ec19dc3934e5d94de6fc2c50fedc755a44d1e4751286 |
| 2/quality-stress/c2-phase-conditional | 8041 | 619ba0e5f5b6758c54886d41edde95ad26c1cbb7568476e689f77b3286eb4f92 |

| 原extract | records | bytes | SHA256 |
| --- | ---: | ---: | --- |
| incident-ledger-001.json | 20 | 34512 | b077e643e8408c25ad21e829a21410395f31ebb36fd227a1c69a4f434975cac2 |
| matched-target-pairs-001.json | 18 | 63951 | ea8688b740373613bd2fb0a53ccad471612e70e67e5e8e1e0772ff24ad3ec1ef |
| matched-target-pairs-002.json | 1 | 3798 | 8ca90b468b156893cb0a5c22bdbb39d8a8747768d15065626a319e9f132fe168 |
| selected-windows-001.json | 3 | 52639 | 46e9841a267d8e580835281f8f701fe33164a59c6cc6cb4437ca83dbcbf1a3a0 |
| selected-windows-002.json | 2 | 29714 | a7f7e5fb15d970d2dbf4c9f3af4c969384c7da9700eefa4fd0386036f8f91de4 |
| non-ok-input-records-001.json | 30 | 21965 | cd3f8feb7d423af9801d7e985fef9a797bb8ea2d5a7b3614b8b364d11ba48d69 |
| all-source-equipment-episodes-001.json | 66 | 58961 | 4bc16b694780ce6f759978d7c321b0181f7b5abac2998803b8dc22320fe80485 |

DATA dev-layout2-quality-c2-20261012閉鎖{'bytes': 38249728, 'files': 19, 'manifest_pin': {'bytes': 2264, 'sha256': '4f8cf82618095a173d350e5e920c72e874f7cfafe41b4783ac8213533aaed94f'}}、EXTRACT representative-layout2-quality-c2-extract-20261012-prep閉鎖{'bytes': 266753, 'files': 8, 'manifest_pin': {'bytes': 1213, 'sha256': '8120dfdcde15ad92e760e8140359090e5148f9692f6aa57d395b3ae4953435d1'}}。MAIN representative-layout2-quality-c2-20261012-prep/POST representative-layout2-quality-c2-post-20261012-prepのpost-save/owners/root-closedを最終Git状態として優先。

117science-source/旧62root count-byte-closure pin/旧C1 MAIN外部固定35file226520B/旧C2 cache補足pin不変。前coreC2 Git helperは一回commit/push exit0後lsremote128/Connection resetでfailed、別metadata continuationのfresh GitHub ref API/statusで同HEAD/clean確認した履歴を保持。元failed→passed書換え/元helper-lsremote-push反復0。前qualityC1のforeground日付selector missも原selected証拠保持。今回新failed0。

新metadataはpython-B/recursive full coverage、512KiB32entry/reserve128KiB/single128KiB。新書込み前script/失敗/closure分を確認し、対象文字列だけ変更/hash-seed無限定置換0。原root追記・raw削除移動・上限緩和0。

元115instrumented helpers full saved creation-start_token/live-execution一致、原10failed105passed/CIM同original不在/repo helpercriticalなし、今回model/analysis2passed。CIMdecimal100ns→microsecond truncation/full saved token/PID単独0/native回収claim0。foreground fullcreation/stdioNone、selectedCLIを全helperstdioにしない。

## Git継続承認・次unit・formal状態

送信リスク通知後の人の「承認します」による同送信先 https://github.com/tyaro/banto-ai.git への今後同種合成dev結果・ユーザー名を含むPC内入力path報告の継続承認で、report/current-handoff2文書を一回[skip ci] commit/pushする。保存後original Git/API returns/HEAD-upstream-remote ref-clean/docpinsはPOSTを優先、後追い文書再commit0。Git512KiB16entry/stdout1MiB/累積30秒を維持し、remote refはAPI照合。

次unitは同保存chunk002/dev seed/layout2quality-stressをC0 c0-diff-control、新ID dev-layout2-quality-c0-20261012で1cell実評価。manifestc97c/quality input10pinsを維持し、生成identity c0と実評価cellを別fieldにする。元payload書込み/生成/完成cell再compute0。

automation詳細結果・PC内path転記/設定更新0、文書参照短指示ACTIVE維持。CI381385/code661bの4130success独立verifier完成保存維持、新query/download/verifier0/doc-onlyCI追跡0。旧381365/a54961最後in_progressは履歴のまま。CI成功≠モデル性能/native/正式受入。

formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読/正式5残件・最終受入未完了/create_native早期拒否/全7役whole.run reader実起動禁止/元caps-unknown原owner-stop/追加agent禁止。未完了formal/native証明を少量dev開始条件に戻さない。Sol容量又は人の停止では保全後PAUSED、重複再試行0。
