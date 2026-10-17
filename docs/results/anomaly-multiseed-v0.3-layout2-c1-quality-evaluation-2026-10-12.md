# dev layout2 C1 quality-stress実評価（2026-10-12 JST）

## 原入力と範囲

保存済み合成dev seed2486912926863618161/layout2/quality-stressを既存CLI C1 c1-phase-levelで1cell実compute_evaluation。新ID dev-layout2-quality-c1-20261012。input10pins照合→新snapshot→fresh phase fit/calibration→原profile/score/source-equipment episodes/events/incidents/metrics保存。元payload書込み・新dataset生成・replay・production/test変更・類似owner・追加agent・holdout本文読取り0。

input manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\002\attempt-0001\result\payload\manifest.json

manifest 75699B/c97c3564c28b679668c2f7425b33aaedadec0c90c45e5705e929131826797783、dataset anomaly-v03-dev-seed-2486912926863618161-layout-02-quality-stress。生成identity candidate c0と実評価C1を別fieldで保持。文書checkout f79a63216e85aa464c2d489b8004984f246c1dda、計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。Python3.14.0 Windows AMD64、elapsed64.78535999997985秒/OScheckpoint peak private147951616B。

engineering900秒/2GiB private/output1GiB/single32MiB/files32 checkpoint上限を維持。blocking計算中断/full loaded runtime閉包/allwriter/global/native容量証明ではない。

## 原結果

CLI exit0/complete/1cell success。処理successを性能合格・正式受入・勝者・採択へしない。

- 機械10/10・sensor9/10・precision19/19・clean誤警報0・全未対応equipment0。
- calibrated48、fit_samples各600/calibration各290、score14400。利用可能13889・不能511。
- 原mask-observation18000行対応、温度missing30観測行。他targetの欠測0。
- source29/equipment19/events40/incidents20、検出19件だけdelay原1秒/median mean min max各1秒。未検出1件delay null。
- clean_rate原0/3365/value0、effective_clean_seconds3254/effective_clean_rate0.0、false_alert_burden原0/20/value0。

## qualityとphaseの重複を原scoreで保持

排他的primaryはmode_recipe_or_phase471/current_target_quality30/previous_target_quality_or_nonfinite10、合計511。非排他的tagsはphase480/current quality30/current nonfinite30/previous quality30で、独立行として加算しない。全不能score/residual null/threshold_exceeded=false。

phaseタグ480行のうち9行はcurrent_target_qualityをprimaryとする同じ行。全9行はmotor-01.motor_temperature、sample 7260,7440,7620,7800,7980,8160,8340,8520,8700。原9score rowsとresult pinをMAIN quality-phase-overlap.jsonに保存。

同layout2 core C1の利用可能13920/不能480に対し今回利用可能13889/不能511。欠測30観測・current quality30行・previous quality10行には上記phase重複9行がある。旧layout0/1 qualityの利用可能13880/不能520を今回へ流用せず、原排他的内訳を用いる。原欠測30行と8target全score不能511行は別量。

## cycle09 sensor未検出の原対応

対象 motor-01.motor_temperature、event start/end sample8901/8904、matching window end8907。原reason no_candidate_in_window/candidate0/causal_detected=false/matched_episode_id=None/selected_source_episode_id=None/support[]/delay None。

| sample | available | 原score | streak | exclusion primary | tags |
| ---: | --- | ---: | ---: | --- | --- |
| 8901 | True | 172.3497212823758 | 1 | None |  |
| 8902 | False | None | 0 | current_target_quality | current_target_quality,current_nonfinite |
| 8903 | False | None | 0 | current_target_quality | current_target_quality,current_nonfinite,previous_target_quality_or_nonfinite |
| 8904 | False | None | 0 | current_target_quality | current_target_quality,current_nonfinite,previous_target_quality_or_nonfinite |
| 8905 | False | None | 0 | previous_target_quality_or_nonfinite | previous_target_quality_or_nonfinite |
| 8906 | True | 0.12350638684184247 | 0 | None |  |
| 8907 | True | 0.4271316657456361 | 0 | None |  |

8901原score172.3497212823758>threshold6、streak1。8902–8904 current quality不能、8905 previous quality不能でstreak0。8906復帰score0.12350638684184247、8907score0.4271316657456361、固定persistence2不成立。原episode/incidentを後から成立させず、GT・threshold6・persistence2・second-exceedance・first-equipment-onset-no-retry-v1・science変更0。実入力対応・保存・状態分類の実経路不具合観測なし。

## 検出19件のtarget sourceとequipment対応

原selected target source.full_target=event.full_target/source ID∈matched equipment.source_episode_ids/equipment.matched_event_id=event IDを全19件照合。原target onset=event start+1000ms、原support_score_ids各2件。未検出1件のnullはこの表に補わない。

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

## 同coreと旧quality C1の保存比較

| layout/stratum | candidate | machine | sensor | precision | clean | available | delay count / median |
| --- | --- | --- | --- | --- | ---: | ---: | --- |
| 0/quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 13880 | 19 / 2.0 |
| 1/quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 13880 | 19 / 1.0 |
| 2/core | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920 | 20 / 1.0 |
| 2/quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 13889 | 19 / 1.0 |

全4cellの宣言16calculator source/candidate_config/compiled_candidate_config一致、同seed/role devを保持。旧manifest/configだけ参照、旧result本文再展開/再compute0。同layout2 coreと今回qualityの入力pin差をfield別保存。旧layout0/1 qualityも別layoutの保存指標で、新独立seedではない。

旧layout0検出19件のdelaymedian2秒、layout1及び今回の検出19件は1秒。未検出delay補完0。集計一致をscore/episode同一へしない。bootstrap・統計CI・勝者・採択0、完成15cell/layout0-layout1全12/layout2core3/replay/risk tests/旧CI反復0。

## 原pin・保存root

| 原保存 | bytes | SHA256 |
| --- | ---: | --- |
| input observations | 9600603 | 9c4ba47cae6728cf74181a8f3ebcdfe2a13a95ce98862d9e042ea4b8f9a83d74 |
| configuration | 5512 | b9029a8292441959ceeb18fe905ae2b129e13c9e65fb5a034fe83c402f55b2b7 |
| manifest | 8034 | 67308ad3afa221abfa1e118dd9447bb721306c843440719e80de29941732d38f |
| evaluation-0 | 14510658 | a0e8790f838de36c9f4311b18d379fe0c19a088bca7c57dbcc33e91a0f517b5c |
| numerical | 14505060 | f40cbc1adfb64a156cd7d5fef51e7eef4bf9b829aae832a7e5c9580fb2155fae |
| quality-phase-overlap | 10013 | 5634f8cbb5fc593abfdb75f4e0eb4cb51b4c20495a674d67ef2b31cb4265261a |

| 保存manifest layout/stratum | bytes | SHA256 |
| --- | ---: | --- |
| 2/core | 8002 | 6a8a1537204cb240080e1f808e875975036fc6dba5b4925d2f893f46f189dd42 |
| 1/quality-stress | 8035 | 399af646470a861c738d4c6726772927936a4408aa445523e7440050a7a2cb54 |
| 0/quality-stress | 8042 | 3042be397642799af8c5ac6d0d2fb82c8f92f0a3d66a8fe983f8cc1b8e4431d3 |
| 2/quality-stress | 8034 | 67308ad3afa221abfa1e118dd9447bb721306c843440719e80de29941732d38f |

| 原extract | records | bytes | SHA256 |
| --- | ---: | ---: | --- |
| incident-ledger-001.json | 20 | 33930 | 489be00c62d8117e23a6e3cacecb3864c2593568798ba2abe059397a377417b2 |
| matched-target-pairs-001.json | 19 | 63661 | 78ec3df2b25ae4d19edcd91b838e37833caed57d46940e3cf799f8985ea11953 |
| selected-windows-001.json | 4 | 63408 | baee5cc268201fc151e53aa61dd50cb2329c1365885b5e7d0e612c4587309d55 |
| selected-windows-002.json | 1 | 13089 | 70735ada5ec2357dfee996adb533308c21e280788c5f1882b873cdda22b987ea |
| non-ok-input-records-001.json | 30 | 21959 | 6c8bb22d90a703e161e5bc0d225e58eb4f7eaf9533438aedcf9f45c562a3feee |
| all-source-equipment-episodes-001.json | 48 | 39449 | 6516426d261dc345ecf2edf56eccfa04859f6cebdbe02974cd4fdf3b81d2a0f9 |

DATA dev-layout2-quality-c1-20261012閉鎖{'bytes': 27557705, 'files': 19, 'manifest_pin': {'bytes': 2258, 'sha256': '1614be57ca2a59f0e42a96e7cacde087bc4ee0335d8d70cd5a17e85d076c24b2'}}、EXTRACT representative-layout2-quality-c1-extract-20261012-prep閉鎖{'bytes': 236580, 'files': 7, 'manifest_pin': {'bytes': 1084, 'sha256': 'b3ee92bea76a7e787314967c3c94567e153878e2ca84d0de3254cbdf01676067'}}。MAIN representative-layout2-quality-c1-20261012-prep/POST representative-layout2-quality-c1-post-20261012-prepのpost-save/owners/root-closedを最終Git状態として優先。

117science-source/旧58root count-byte-closure pin/旧C1 MAIN外部固定35file226520B/旧C2 cache補足pin不変。前C2 Git helperは一回commit/push exit0後ls-remote exit128/Connection resetでfailed、元script/calls/stdout-stderrを閉鎖POSTへ保全。別metadata continuationの未実行GitHub branch-ref APIとstatusでHEAD f79a632/remote同SHA/clean確認。元failedをpassedへせず、元helper/lsremote/push反復0。今回Git保存後のremote refはAPIで照合する。

過去failed/capacityfalse/coverage limits/旧scope-roster/foreground metadata失敗を保持。今回旧script root日付selector missはselected chunk/exit1のみ保存、元source評価/モデル開始0、実名確認後の読取りへ継続。foreground fullcreation/stdioNone。原script再実行・root追記・raw削除移動・上限緩和0。

元112instrumented helpers full saved creation-start_token/live-execution一致、原10failed102passed/CIM同original不在/repo helpercriticalなし、今回model/analysis2passed。CIMdecimal100ns→microsecond truncation/full saved token/PID単独0/native回収claim0。selectedCLIを全helperstdioにしない。新metadataはpython-B/recursive full coverage、512KiB32entry/reserve128KiB/single128KiB。新書込み前script/失敗/closure分を数え、対象文字列だけ変更/hash-seed無限定置換0。

## Git継続承認と次unit

送信リスク通知後の人の「承認します」による、同送信先 https://github.com/tyaro/banto-ai.git への今後同種合成dev結果・ユーザー名を含むPC内入力path報告の継続承認でreport/current-handoff2文書を一回[skip ci] commit/pushする。保存後Git original returns/HEAD/upstream/remote ref API/clean/docpinsはPOST優先、後追い文書再commit0。Git512KiB16entry/stdout1MiB/累積30秒維持。

次unitは同保存chunk002/dev seed/layout2/quality-stressをC2 c2-phase-conditional、新ID dev-layout2-quality-c2-20261012で1cell実評価。manifest c97c pin/同quality10input pinsを維持。元payload書込み/生成/完成cell再compute0。生成identity c0と実評価C2は別field。

automation詳細結果・PC内path転記/設定更新0、文書参照短指示ACTIVE維持。CI381385/code661bの4130success独立verifier完成保存維持、新query/download/verifier0/doc-onlyCI追跡0。旧381365/a54961最後in_progressは履歴のまま。CI成功≠モデル性能/native/正式受入。

formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読/正式5残件・最終受入未完了/create_native早期拒否/全7役whole.run reader実起動禁止/元caps-unknown原owner-stop/追加agent禁止。未完了formal/native証明を少量dev開始条件に戻さない。Sol容量又は人の停止では保全後PAUSED、重複再試行0。
