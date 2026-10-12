# dev layout6 C2 core実評価・core3候補保存比較（2026-10-12 JST）

## 入力と計算

同保存chunk006/dev seed2486912926863618161/layout6 core、C2 c2-phase-conditional、新IDdev-layout6-core-c2-20261012で1cell実compute_evaluation。input10 pin照合→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics。元生成identity C0/実評価C2別field、元payload書込み/生成/replay/production-test変更/追加agent/holdout本文読取り0。

input manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\006\attempt-0001\result\payload\manifest.json
manifest 75698B/542248c4b9e6227749adce8d37c1769580ba0cb7426ebe12321ec192a775846d、dataset anomaly-v03-dev-seed-2486912926863618161-layout-06-core。
actual文書checkout29be46ad7ceba6af6a9048a51a5a042b18bf1a7f、計算661b27511826fcc87cb4a02930f276afbb8f95d9不変。Python3.14.0 Windows AMD64、elapsed29.309303400106728秒/privatepeak206123008B。

## 原結果

CLI exit0/complete/1cell successは処理完了であり、性能合格・採択・正式受入は未判定。

- 機械0/10・sensor10/10・precision10/20・clean誤警報0/未対応equipment10全machine窓raw-event/vibration-only。
- 48calibrated/fit600/cal290各/C2state48、14400scores/利用可能13920/不能480全phase-null-thresholdfalse、18000mask対応/non-ok欠測0。
- source30/equipment20/events40/incidents20。10sensor原target source/equipment/support2/start+1000ms、検出delay10件min/max/mean/median全1秒。10machine delaynull/補完forbidden。
- burden10/20原value50.0とclean0を別保持し、単純確率へしない。

## 対象onsetの原対応

全machine10の対象conveyor_speed/stopped/stop窓7rowsはすべてavailable/score<6/thresholdfalse/streak0/source_episode_idnull。最初のcandidate1件はvibration-only/start+1000ms/support2。target onsetがなく、first_candidate_no_target_onset/causalfalse/sourcenull/matchednull/support[]/delaynull。対象窓phase不能全0。
cycle00 speed start7214 score3.1136615246871058/0→次3.23546619508402/0、窓最大3.504763113767704<6。vibration同2row scores[77.4124505885611, 76.30801932767972]/streak1→2で候補成立。
sensor10はmotor_temperature target onsetがstart+1000ms、cycle00 sample7221scores[167.4988286225642, 167.21546141800562]/streak1→2で成立。C2では同sensor equipmentのmotor_current sourceが10件加わりsource30、C1 source20と別保持。温度target以外のsourceを検出数に追加しない。各sensor equipmentのoriginal target/current source2を独立peer-source proofへ保存し、原全30source/20equipmentはEXTRACTに保存。
全10machine原event-incident/selectedsource-equipment/target70rows/vibration20supportrows・全10sensor対応・2cycle00四target窓をproof保存。GT/threshold6/persistence2/first-equipment-onset-no-retry-v1/config/science変更0。入力対応・保存・状態分類の実経路不具合は観測なし。

| cycle | speed window max score | max streak | first source | target onset | delay |
| ---: | ---: | ---: | --- | --- | --- |
| 0 | 3.504763113767704 | 0 | vibration_feature | null | null |
| 1 | 3.4179069249353646 | 0 | vibration_feature | null | null |
| 2 | 3.504773486067857 | 0 | vibration_feature | null | null |
| 3 | 3.3123144244574565 | 0 | vibration_feature | null | null |
| 4 | 3.6910015764712885 | 0 | vibration_feature | null | null |
| 5 | 3.6363493996098075 | 0 | vibration_feature | null | null |
| 6 | 3.430615938363438 | 0 | vibration_feature | null | null |
| 7 | 3.6124073104066596 | 0 | vibration_feature | null | null |
| 8 | 3.640753360483513 | 0 | vibration_feature | null | null |
| 9 | 3.4940607100128145 | 0 | vibration_feature | null | null |

### cycle00 machine conveyor-01.conveyor_speed

| sample | target | score | residual | available | threshold | streak |
| ---: | --- | ---: | ---: | --- | --- | ---: |
| 7212 | conveyor-01.conveyor_speed | 0.49398103447765684 | 0.39856275913796496 | True | False | 0 |
| 7212 | conveyor-01.vibration_feature | 1.0748780243899372 | 0.7627733022428923 | True | False | 0 |
| 7213 | conveyor-01.conveyor_speed | 0.6172072866107102 | 0.5171457104757141 | True | False | 0 |
| 7213 | conveyor-01.vibration_feature | 0.29760217504083136 | -0.0018348271398179775 | True | False | 0 |
| 7214 | conveyor-01.conveyor_speed | 3.1136615246871058 | -3.073139858056835 | True | False | 0 |
| 7214 | conveyor-01.vibration_feature | 77.4124505885611 | 75.85622771586671 | True | True | 1 |
| 7215 | conveyor-01.conveyor_speed | 3.23546619508402 | -3.1903547944227646 | True | False | 0 |
| 7215 | conveyor-01.vibration_feature | 76.30801932767972 | 74.76979601839219 | True | True | 2 |
| 7216 | conveyor-01.conveyor_speed | 3.504763113767704 | -3.4495043088394857 | True | False | 0 |
| 7216 | conveyor-01.vibration_feature | 76.10528943750026 | 74.57037013602381 | True | True | 3 |
| 7217 | conveyor-01.conveyor_speed | 0.2651453213732808 | 0.17834982754530995 | True | False | 0 |
| 7217 | conveyor-01.vibration_feature | 0.6190258747465528 | -0.9035240524959871 | True | False | 0 |
| 7218 | conveyor-01.conveyor_speed | 1.9117540345500907 | 1.762912512257395 | True | False | 0 |
| 7218 | conveyor-01.vibration_feature | 1.3832245527196654 | -1.6552681368272675 | True | False | 0 |
| 7219 | conveyor-01.conveyor_speed | 2.7143733574025273 | -2.6888973083465557 | True | False | 0 |
| 7219 | conveyor-01.vibration_feature | 1.780312513299108 | 1.4567109119326431 | True | False | 0 |
| 7220 | conveyor-01.conveyor_speed | 1.4930302349089346 | -1.513575738840638 | True | False | 0 |
| 7220 | conveyor-01.vibration_feature | 0.6321687709748098 | 0.3272791409388748 | True | False | 0 |
| 7221 | conveyor-01.conveyor_speed | 4.622796182686168 | 4.371799608652131 | True | False | 0 |
| 7221 | conveyor-01.vibration_feature | 4.1307596372036794 | -4.358025032104404 | True | False | 0 |
| 7222 | conveyor-01.conveyor_speed | 2.9110157873650295 | 2.724520982502701 | True | False | 0 |
| 7222 | conveyor-01.vibration_feature | 4.192874834863632 | -4.4191279019913114 | True | False | 0 |
| 7223 | conveyor-01.conveyor_speed | 2.9191447345093824 | 2.732343621972455 | True | False | 0 |
| 7223 | conveyor-01.vibration_feature | 4.107645441156835 | -4.3352875416544405 | True | False | 0 |

### cycle00 sensor conveyor-01.motor_temperature

| sample | target | score | residual | available | threshold | streak |
| ---: | --- | ---: | ---: | --- | --- | ---: |
| 7219 | conveyor-01.motor_current | 1.2084165686312582 | 1.1522795384005107 | True | False | 0 |
| 7219 | conveyor-01.motor_temperature | 0.8210677715985252 | -0.6598149270067203 | True | False | 0 |
| 7220 | conveyor-01.motor_current | 1.4044721148437245 | 1.3484754156818584 | True | False | 0 |
| 7220 | conveyor-01.motor_temperature | 0.42941276405691975 | -0.3139078245691264 | True | False | 0 |
| 7221 | conveyor-01.motor_current | 11.49972557616973 | -11.564958738619797 | True | True | 1 |
| 7221 | conveyor-01.motor_temperature | 167.4988286225642 | 147.9992000815421 | True | True | 1 |
| 7222 | conveyor-01.motor_current | 11.556295230465583 | -11.621568883889799 | True | True | 2 |
| 7222 | conveyor-01.motor_temperature | 167.21546141800562 | 147.74893204776936 | True | True | 2 |
| 7223 | conveyor-01.motor_current | 10.489470010530148 | -10.55398006034143 | True | True | 3 |
| 7223 | conveyor-01.motor_temperature | 166.22665042668987 | 146.87562074501997 | True | True | 3 |
| 7224 | conveyor-01.motor_current | 0.9074495181345626 | 0.8510970641185142 | True | False | 0 |
| 7224 | conveyor-01.motor_temperature | 0.7614662943248575 | -0.6071752979767138 | True | False | 0 |
| 7225 | conveyor-01.motor_current | 0.6171503182951898 | -0.6745940381733683 | True | False | 0 |
| 7225 | conveyor-01.motor_temperature | 0.9679602903489927 | -0.7895494243381158 | True | False | 0 |
| 7226 | conveyor-01.motor_current | 0.7322527954144152 | -0.7897789024219409 | True | False | 0 |
| 7226 | conveyor-01.motor_temperature | 1.4317484838309231 | -1.1991640777012764 | True | False | 0 |
| 7227 | conveyor-01.motor_current | 0.40443565912985024 | 0.3477231618818704 | True | False | 0 |
| 7227 | conveyor-01.motor_temperature | 1.334466758928332 | -1.1132455041270277 | True | False | 0 |
| 7228 | conveyor-01.motor_current | 0.1892784926337118 | -0.24641595384285808 | True | False | 0 |
| 7228 | conveyor-01.motor_temperature | 1.9933356989233038 | -1.6951541776567003 | True | False | 0 |
| 7229 | conveyor-01.motor_current | 0.5882677345123271 | 0.5316868191151621 | True | False | 0 |
| 7229 | conveyor-01.motor_temperature | 1.8849542025915182 | -1.5994323596482938 | True | False | 0 |
| 7230 | conveyor-01.motor_current | None | None | False | False | 0 |
| 7230 | conveyor-01.motor_temperature | None | None | False | False | 0 |


## 保存manifest/config比較

同layout6 core3候補比較完成。C0両0/10・precision0/3・clean3/delaynull、C1/C2 machine0/sensor10・precision10/20・clean0/detected10delay1秒。C1 source20とC2 source30を区別し、score/residual/予測同一を指標一致から推定しない。
同layout6 C0/C1と旧layout0–5 C2はmanifest/configだけ9cell比較、旧8本文再展開・再compute0。同layout6 input10全一致/宣言16calculator/candidate-config/compiled-config一致、他layout入力差保持。旧layout0 C2 machine4と旧layout1–5 machine10を今回のmachine0へ書換えない。同seed7layoutcore C2+同layout6 C0/C1で9独立seed-dataset0。旧36cellboard不変/layout6quality未完了/bootstrap統計CI勝者採択0。

| layout | candidate core | machine | sensor | precision | clean | available/unavailable | detected delay median/mean秒 |
| ---: | --- | --- | --- | --- | ---: | --- | --- |
| 6 | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13920/480 | None/None |
| 6 | c1-phase-level | 0/10 | 10/10 | 10/20 | 0 | 13920/480 | 1.0/1.0 |
| 5 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 13920/480 | 1.0/1.0 |
| 4 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 13920/480 | 1.5/1.5 |
| 3 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 13920/480 | 1.5/1.5 |
| 2 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 13920/480 | 1.0/1.0 |
| 1 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 13920/480 | 1.0/1.0 |
| 0 | c2-phase-conditional | 4/10 | 10/10 | 14/20 | 0 | 13920/480 | 1.0/1.2857142857142858 |
| 6 | c2-phase-conditional | 0/10 | 10/10 | 10/20 | 0 | 13920/480 | 1.0/1.0 |

## 保存状態

MAIN representative-layout6-core-c2-20261012-prep/POST representative-layout6-core-c2-post-20261012-prepの原docs・proof・Git、FINAL representative-layout6-core-c2-final-save-20261012-prep/post-save.json・owners-after-save.json・root-closed.jsonを最終保存として優先。DATA {'files': 19, 'bytes': 37775955, 'manifest_pin': {'bytes': 2254, 'sha256': '90ea795507668574544cd973001000878930f1d13aba09b81443693a58e09b6b'}}、EXTRACT {'bytes': 305654, 'files': 8, 'manifest_pin': {'bytes': 1196, 'sha256': 'f6eca97f361b040b3710df4498a5c4bbd58478424c03eef4e551ae6fa6b55f19'}}閉鎖。117science/旧161root count-byte-closurepin/frozen35capfalse/cache補足不変。前layout6 C0 foreground2/C1 foreground3・pending-read display1・審査2拒否と元Git script未起動、別approved-save29beの原Git成功を別保存。既存失敗を今回の成功へ書換えない。
今回foreground0、元185helpers11failed174passed/fullidentity一致/CIM同original不在/repohelpercritical0/model-analysis2passed。foreground creation/fullstdioNone・selectedCLI≠全stdio・PID単独/native回収claim0。metadata512KiB32entry/reserve128KiB/single128KiB/recursive/Python-B/限定文字列置換、新script・失敗・閉鎖分を含め書込み前容量確認、docs/proof初保存POST・owner/final保存先を最初から分ける。閉鎖/外部固定root追記・原raw整理移動削除・上限緩和0。
C1の具体的合成dev結果/ユーザー名PC path/指定2文書/同GitHub送信先と今後の同種送信のリスク通知後、人の「進めてください」を受領し継続承認を記録、C1 docsを29beで保存済み。同送信先/同種合成dev報告の継続承認範囲で今回handoff/C2 report2を直接一回[skip ci] commit/push。原Git返値・HEAD-upstream-GitHub ref-clean/docpinsはPOST、最終保存はFINAL。Git512KiB16entry/stdout1MiB/累積30秒/preflight別量。automation詳細転記/設定更新0/ACTIVE維持。
CI381385/4130保存、新query-download-verifier0/旧381365inprogress履歴/doc-onlyCI追跡0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了/create_native早期拒否/全7役reader禁止/元caps-unknown原owner-stop/追加agent禁止。未完了formal/nativeをdev開始条件へ戻さない。engineering900秒2GiB/output1GiB/single32MiB/files32 checkpoint≠blocking中断/full runtime/native/global容量証明。Sol容量/人の停止では原保全後PAUSED・重複再試行0。

| 原保存 | bytes | SHA256 |
| --- | ---: | --- |
| observations | 9600501 | 0afb767f74925aab25f32c77f1f5e5637d517f661e979d15ca48348eebb8240f |
| configuration | 5508 | d14165327068590b85f79e9c1ef211beacfb4cdf4fbf8ffe13ccbfcfcda8ab3e |
| manifest | 8010 | 51d3f926524a28a8a8c32cbfa40fceec7312f15eaa81b0b9a2b91e9f2d70a6ab |
| evaluation | 24734777 | 4fc2a52f73dd1ab6fa0bb43c8fe443903920a66b55ef6fadd007f4fcbb1790a6 |
| numerical | 24729279 | 5b373d9bbfe49fecf1eb20b831c45f9b5a8a4bc96bfed571b137c53b71966437 |
| machine-sensor proof | 118971 | 5aa70738f12af6ee2d258dabefbf0011da6d598e75383fe6ea1d7181bd2415a3 |
| sensor peer-source proof | 42200 | a50a92b6080e06d7b0a8bf800e2d207e12f70b56051bf44a4bc569f88a9b57b2 |

## 次の未完成unit

同chunk006/layout6 quality-stress、同manifest5422、保存済みqualitypair metadata/input10をC1 c1-phase-level、新IDdev-layout6-quality-c1-20261012で1cell実評価。dataset anomaly-v03-dev-seed-2486912926863618161-layout-06-quality-stress。quality観測本文未読/次model未開始/生成0。完成core3候補・旧評価/replay/試験/CI反復0。
