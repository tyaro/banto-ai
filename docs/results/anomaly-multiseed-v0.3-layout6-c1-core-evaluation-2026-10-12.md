## 最新の保存状態（2026-10-12 JST）

送信内容・ユーザー名PC path・指定2文書・GitHub送信先の具体的リスク通知後、人の「進めてください」を受領。承認待ち解除。新専用 representative-layout6-core-c1-approved-save-20261012-prep のpost-save/doc-save/doc-git-save/owners-after-save/root-closedを最終保存として優先。以下の自動審査2拒否・Git未開始・返答待ちは承認受領前の原履歴として保持。元script/完成C1model再実行0/closed-root追記0。次unit samecoreC2未開始、formal_permission=false/credit0/正式受入未完了。

---

# dev layout6 C1 core実評価（2026-10-12 JST）

## 入力と実評価

同保存chunk006/dev seed2486912926863618161/layout6/coreをC1 c1-phase-level、新IDdev-layout6-core-c1-20261012で1cell実compute_evaluation。input10 pins→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics。元生成identity C0と実評価C1は別field。元payload書込み・生成・replay・production/test変更・追加agent・holdout観測本文読取り0。

input manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\006\attempt-0001\result\payload\manifest.json
manifest 75698B/542248c4b9e6227749adce8d37c1769580ba0cb7426ebe12321ec192a775846d、dataset anomaly-v03-dev-seed-2486912926863618161-layout-06-core。
actual文書checkouta37366f6784b65eebde6f6d17a1f59e982b4b311、計算661b27511826fcc87cb4a02930f276afbb8f95d9不変。
actualPython3.14.0 Windows AMD64、elapsed19.074605999980122秒/privatepeak147554304B。

## 原結果

CLI exit0/complete/1cell successは処理完了。性能合格/候補採択/正式受入は未判定。

- 機械0/10・sensor10/10・precision10/20・clean誤警報0、未対応equipment10。
- 48calibrated/fit600/calibration290各、14400scores/利用可能13920/不能480全mode_recipe_or_phase/score-residualnull/thresholdfalse。
- 18000mask-observation対応/non-ok欠測0、source20/equipment20/events40/incidents20。
- 検出sensor10だけdelay min/max/mean/median全1秒、machine10 delaynull/undetected_fill forbidden。
- false_alert_burden10/20の原value50.0とclean0を別保持。未対応10はmachine窓内raw-event/vibration episodeでcleanではない。

## machine10未検出の対応

全10machine eventはconveyor-01.conveyor_speed/jam_or_slip/stopped/stop。対象窓7rowsはすべて利用可能/phase不能0、score<6/thresholdfalse/streak0/target source_episode_idnull。
最初のequipment candidateは1件/vibration_featureだけ、start+1000ms onset/support2。対象conveyor_speedのonsetがなく、固定first-equipment-onset-no-retry-v1はfirst_candidate_no_target_onset/causalfalse/selected_sourcenull/matchednull/support[]/delaynullを返す。vibration episodeの成立をtarget検出へ補わない。
cycle00 speed sample7214 score0.261294540272591/streak0→次0.08876261601917787/0、窓最大2.7210242357026293<6。vibration同startと次のscoreは[77.95145538078287, 76.83207340274976]、streak1→2で候補成立。
sensor全10はmotor_temperatureの原target source/equipment対応/support2/start+1000ms。cycle00 start7221と次score[158.85603150463174, 158.61892671169386]、streak1→2。
全10machine event-incident/元selected equipment-source/原target窓70rows/元vibration support20rows・全10sensor対応/2cycle00四target窓をproofへ保存。GT/threshold6/persistence2/matching/config/science変更0。実入力対応・保存・状態分類の不具合は観測なし。

| machine cycle | target max score | target max streak | selected source | target onset | delay |
| ---: | ---: | ---: | --- | --- | --- |
| 0 | 2.7210242357026293 | 0 | vibration_feature | null | null |
| 1 | 2.7130086626794316 | 0 | vibration_feature | null | null |
| 2 | 1.5368218736525463 | 0 | vibration_feature | null | null |
| 3 | 1.403710800332891 | 0 | vibration_feature | null | null |
| 4 | 2.0077696394745055 | 0 | vibration_feature | null | null |
| 5 | 1.387942459959388 | 0 | vibration_feature | null | null |
| 6 | 1.2867622758960762 | 0 | vibration_feature | null | null |
| 7 | 1.0808540311854147 | 0 | vibration_feature | null | null |
| 8 | 1.1527313827213 | 0 | vibration_feature | null | null |
| 9 | 1.4374813292994766 | 0 | vibration_feature | null | null |

### cycle00 machine conveyor-01.conveyor_speed

| sample | target | score | available | threshold | streak |
| ---: | --- | ---: | --- | --- | ---: |
| 7212 | conveyor-01.conveyor_speed | 0.5016303281320674 | True | False | 0 |
| 7212 | conveyor-01.vibration_feature | 1.1306403339006366 | True | False | 0 |
| 7213 | conveyor-01.conveyor_speed | 0.5930867022983856 | True | False | 0 |
| 7213 | conveyor-01.vibration_feature | 0.3741142789926042 | True | False | 0 |
| 7214 | conveyor-01.conveyor_speed | 0.261294540272591 | True | False | 0 |
| 7214 | conveyor-01.vibration_feature | 77.95145538078287 | True | True | 1 |
| 7215 | conveyor-01.conveyor_speed | 0.08876261601917787 | True | False | 0 |
| 7215 | conveyor-01.vibration_feature | 76.83207340274976 | True | True | 2 |
| 7216 | conveyor-01.conveyor_speed | 0.1863949234984513 | True | False | 0 |
| 7216 | conveyor-01.vibration_feature | 76.61743772380161 | True | True | 3 |
| 7217 | conveyor-01.conveyor_speed | 0.23698501553010706 | True | False | 0 |
| 7217 | conveyor-01.vibration_feature | 0.6296346329493548 | True | False | 0 |
| 7218 | conveyor-01.conveyor_speed | 1.8849079873976275 | True | False | 0 |
| 7218 | conveyor-01.vibration_feature | 1.3257378897527106 | True | False | 0 |
| 7219 | conveyor-01.conveyor_speed | 2.7210242357026293 | True | False | 0 |
| 7219 | conveyor-01.vibration_feature | 1.7054370224433695 | True | False | 0 |
| 7220 | conveyor-01.conveyor_speed | 1.52591543822754 | True | False | 0 |
| 7220 | conveyor-01.vibration_feature | 0.6140679613719167 | True | False | 0 |
| 7221 | conveyor-01.conveyor_speed | 0.901489159436817 | True | False | 0 |
| 7221 | conveyor-01.vibration_feature | 0.3824472353039901 | True | False | 0 |
| 7222 | conveyor-01.conveyor_speed | 0.8526073042789575 | True | False | 0 |
| 7222 | conveyor-01.vibration_feature | 0.23834028019987702 | True | False | 0 |
| 7223 | conveyor-01.conveyor_speed | 0.8148946902189959 | True | False | 0 |
| 7223 | conveyor-01.vibration_feature | 0.33057014984205024 | True | False | 0 |

### cycle00 sensor conveyor-01.motor_temperature

| sample | target | score | available | threshold | streak |
| ---: | --- | ---: | --- | --- | ---: |
| 7219 | conveyor-01.motor_temperature | 0.5453052823093711 | True | False | 0 |
| 7220 | conveyor-01.motor_temperature | 0.2218848931148976 | True | False | 0 |
| 7221 | conveyor-01.motor_temperature | 158.85603150463174 | True | True | 1 |
| 7222 | conveyor-01.motor_temperature | 158.61892671169386 | True | True | 2 |
| 7223 | conveyor-01.motor_temperature | 157.76280982869304 | True | True | 3 |
| 7224 | conveyor-01.motor_temperature | 0.679206644940405 | True | False | 0 |
| 7225 | conveyor-01.motor_temperature | 0.8808976200904012 | True | False | 0 |
| 7226 | conveyor-01.motor_temperature | 1.4315442631987834 | True | False | 0 |
| 7227 | conveyor-01.motor_temperature | 1.1911036018065626 | True | False | 0 |
| 7228 | conveyor-01.motor_temperature | 1.8979403714745717 | True | False | 0 |
| 7229 | conveyor-01.motor_temperature | 1.7833493187952032 | True | False | 0 |
| 7230 | conveyor-01.motor_temperature | None | False | False | 0 |


## 保存manifest/configによる比較

同layout6 C0と旧layout0–5 C1coreの保存manifest/configだけを比較し、旧7result本文再展開・再compute0。
同layout6 input10 pins全一致、全8cell宣言16calculator source/candidate config/compiled config一致、他layout入力pin差を保持。
layout6 C0 machine0/sensor0/precision0/3/clean3/delaynull、C1 machine0/sensor10/precision10/20/clean0/detected10delay1秒。旧layout0–5 C1のmachine10を今回へ流用しない。
同seed7layout C1core+同layout6 C0の比較で8独立seed/dataset0。旧36cell board不変、layout6 C2/quality未完了/bootstrap/統計CI/勝者/採択0。

| layout | candidate core | machine | sensor | precision | clean | available/unavailable | delay median/mean秒 |
| ---: | --- | --- | --- | --- | ---: | --- | --- |
| 6 | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13920/480 | None/None |
| 5 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920/480 | 1.0/1.0 |
| 4 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920/480 | 1.5/1.5 |
| 3 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920/480 | 1.5/1.5 |
| 2 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920/480 | 1.0/1.0 |
| 1 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920/480 | 1.0/1.0 |
| 0 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920/480 | 1.5/1.5 |
| 6 | c1-phase-level | 0/10 | 10/10 | 10/20 | 0 | 13920/480 | 1.0/1.0 |

## 原保存と制限

MAIN representative-layout6-core-c1-20261012-prep/POST representative-layout6-core-c1-post-20261012-prepの原docs/proof/Git、FINAL representative-layout6-core-c1-final-save-20261012-prepの最終post-save.json・owners-after-save.json・root-closed.jsonを優先。DATA {'files': 19, 'bytes': 27098400, 'manifest_pin': {'bytes': 2248, 'sha256': '5ac14f55355916a3a9125e969aede6f176239e7ef6b858fbae1b0155b0c108e2'}}、EXTRACT {'bytes': 285189, 'files': 8, 'manifest_pin': {'bytes': 1190, 'sha256': '9f0c2b143ce4dc17aa6ad8a66598a7963ff6028fae92c0b1362c0d336bb016d4'}}閉鎖。117science-sourceと旧154root count-byte-closurepin、外部固定C1 MAIN35files capfalse、C2cache補足不変。前layout6 C0 docs準備foreground0/最終2、元POST post-saveなし閉鎖・別FINAL補完/primaryと訂正Gitを別保存。前qualityC1 false13/raw12・前qualityC2docs準備0/最終4・全原failed/Git未知返値/継続保全は原文書と最新FINAL優先。
今回foreground3は補助保存の相対pathガード拒否と、未作成scriptへの2呼出し。モデル未開始/スクリプト書込み前の原selected trace/sourceをMAIN/foreground-preparation-errors.jsonへ保存、絶対pathで初保存後実評価。instrumented helper/モデル/CI/native/Sol容量失敗へしない。元182helpers11failed171passed、fullidentity一致/CIM同original不在/repohelpercritical0/model-analysis2passed。foreground fullcreation/fullstdioNone・selectedCLI≠全helper stdio・PID単独0/native回収claim0。
metadata512KiB32entry/reserve128KiB/single128KiB/Python-B/recursive/限定文字列置換。script・失敗・閉鎖を含め新書込み前件数bytesを確認し、今回docs script/proofはPOSTへ初保存、MAINへ後付けコピー0。閉鎖/外部固定rootへの追記・整理移動・削除・上限緩和0。
同GitHub同種合成dev結果・ユーザー名PC pathのリスク通知後継続送信承認内、今回handoff/report2のcommit/pushは自動承認審査2回の実行前拒否で未開始。元Git helper/process/commit/push0、bypass/indirect execution0、POST/git-doc.py原script未起動保持。原拒否と送信リスク通知後の新async承認依頼をFINALに保全。保存済み継続送信承認の照合後も、審査はtrusted user content不足として再度拒否。今回C1合成dev結果/ユーザー名PC path/指定2文書/同GitHub送信先と今後の同種送信を具体的に通知し返答待ち。第三再審査/別経路Git/新C2評価を開始せず、完成C1結果と文書2差分をローカル保持。Git512KiB16entry/stdout1MiB/累積30秒/preflight別量。automation詳細転記/設定更新0/ACTIVE文書参照維持。
CI381385/4130保存、新query-download-verifier0/旧381365inprogress履歴/doc-onlyCI追跡0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読・正式5残件/最終受入未完了/create_native早期拒否/全7役reader禁止/元caps-unknown原owner-stop/追加agent禁止。未完了formal/nativeを少量dev開始条件へ戻さない。engineering900秒2GiB/output1GiB/single32MiB/files32 checkpointはblocking中断/full runtime/native/global容量証明ではない。Sol容量/人の停止では保全後PAUSED・重複再試行0。

| 原保存 | bytes | SHA256 |
| --- | ---: | --- |
| observations | 9600501 | 0afb767f74925aab25f32c77f1f5e5637d517f661e979d15ca48348eebb8240f |
| configuration | 5502 | 7a321f15f57d823b29d671f544f8b1acf79f88537a171e6e7a8a4ed8ce0b3c9e |
| manifest | 8004 | 93d2773e5d2bed80dfca84cfd02fe95462ce9d25083c05745ec04bbf02093531 |
| evaluation | 14057258 | 6399fe9d70fd4427d9e58769fff8c9d563f3b148a9033b4acbf207a4b796993c |
| numerical | 14051760 | da9945ea51578661f2db3426c29bcecb9c476aaa1df378e0a3640423ecff2f1a |
| machine/sensor proof | 115019 | 1ba317da97a085812215f003231cae4bdf9b1a2cc31fbe103079154d22155b95 |

## 次の未完成unit

同chunk006/layout6/core/input10/manifest5422をC2 c2-phase-conditional、新IDdev-layout6-core-c2-20261012で1cell実評価。元生成C0と実評価C2別field。nextmodel未開始/生成0/qualitypair metadata保存・quality観測本文未読。完成評価/replay/試験/CI反復0。
