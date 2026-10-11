# 合成dev layout6 C0 core実評価（2026-10-12 JST）

## 今回の実計算

保存済みdev seed2486912926863618161/layout6/coreを既存CLI C0 c0-diff-control、新IDdev-layout6-core-c0-20261012で1cell実compute_evaluation。input10pin照合→新snapshot→fresh calibration→原profiles/scores/episodes/events/incidents/metrics保存。元生成C0/実評価C0別field、元payload書込み・新dataset生成・replay・production/test変更・類似owner・追加agent0。

CLI exit0/complete/1cell success。機械0/10・sensor0/10・precision0/3、clean誤警報3/未対応equipment3全clean。source3/equipment3/incidents20/events40。全20no_candidate_in_window/candidate0/causalfalse/matched-source-equipment null/support[]/delay null。delaycount0/min-max-mean-median原null、補完forbidden。処理successを性能合格・勝者・採択・正式受入へしない。

48profiles全calibrated/fit samples各0/calibration各290。14400scores、利用可能13920/不能480全mode_recipe_or_phase、原score/residual null・thresholdfalse。原18000mask-observation対応/non-ok0/欠測0。不能行を正常scoreへ補完0。
原clean rate={'ci_lower': None, 'ci_status': 'not_evaluated', 'ci_upper': None, 'denominator': 3365, 'null_replicates': 0, 'numerator': 3, 'value': 25.676077265973255}、effective_clean_seconds=3254/rate=26.551936078672405、burden={'ci_lower': None, 'ci_status': 'not_evaluated', 'ci_upper': None, 'denominator': 20, 'null_replicates': 0, 'numerator': 3, 'value': 15.0}を保存。これらvalueを単純確率へしない。

## 全20未検出target窓の原経路

全machine窓10件maxstreak0、全sensor窓10件maxstreak1（全体0:10/1:10）。machine/sensor対象窓phase不能全0。前layout5の全20maxstreak1を流用しない。固定C0threshold4/persistence2の連続超過が成立せず候補なし。

機械対象はconveyor-01.conveyor_speed。cycle00はevent jam_or_slip/mode stopped/recipe stop/start7214/window7220。start score0.4635629678167226、対象窓最大score3.2024364338284195<4、全行利用可能/thresholdfalse/streak0。全10machine対象窓も利用可能score閾値未満・streak0を原rowsで確認。GT/configを変更して検出へ補わない。

sensor対象はconveyor-01.motor_temperature。cycle00 start7221score178.70503443570314/streak1→7222score0.18445529743711783/streak0、end7224score176.46595855974496/streak1→7225score0.03460551683975721/streak0。欠測起因ではなく、超過が連続しない原挙動を保存。7227までの対象windowはphase不能0、window外のphase行を窓内へ加算しない。

全20event/incident・全20conveyor4target窓・全6source/equipment episodesをEXTRACT保存。全20target stats及びcycle00原target rowsをproof保存。GT/config/threshold4/persistence2/first-equipment-onset-no-retry-v1/science変更0。実入力対応・保存・分類不具合観測なし。

### cycle00 machine conveyor-01.conveyor_speed

| sample | available | primary | score | residual | threshold | streak |
| ---: | --- | --- | ---: | ---: | --- | ---: |
| 7212 | True | None | 0.39413921103194505 | 0.0023 | False | 0 |
| 7213 | True | None | 0.19082678044795362 | 0.001152 | False | 0 |
| 7214 | True | None | 0.4635629678167226 | -0.002543 | False | 0 |
| 7215 | True | None | 0.048437238471011876 | 0.000348 | False | 0 |
| 7216 | True | None | 0.07482535010604216 | -0.000348 | False | 0 |
| 7217 | True | None | 0.2250073545792344 | 0.001345 | False | 0 |
| 7218 | True | None | 1.1213176430684162 | 0.006406 | False | 0 |
| 7219 | True | None | 3.2024364338284195 | -0.018008 | False | 0 |
| 7220 | True | None | 0.931996224693602 | 0.005337000000000001 | False | 0 |
| 7221 | True | None | 1.5050964210087556 | 0.008573 | False | 0 |
| 7222 | True | None | 1.2259845825066904 | -0.006848 | False | 0 |
| 7223 | True | None | 0.13592534013346114 | 0.0008419999999999999 | False | 0 |

### cycle00 sensor conveyor-01.motor_temperature

| sample | available | primary | score | residual | threshold | streak |
| ---: | --- | --- | ---: | ---: | --- | ---: |
| 7219 | True | None | 0.7792299755587742 | -0.0006629999999994141 | False | 0 |
| 7220 | True | None | 0.14970526671392564 | -0.02897800000000217 | False | 0 |
| 7221 | True | None | 178.70503443570314 | 8.002151000000001 | True | 1 |
| 7222 | True | None | 0.18445529743711783 | -0.027414999999997747 | False | 0 |
| 7223 | True | None | 0.23236720799899244 | -0.046162999999999954 | False | 0 |
| 7224 | True | None | 176.46595855974496 | -7.972864000000005 | True | 1 |
| 7225 | True | None | 0.03460551683975721 | -0.03415499999999838 | False | 0 |
| 7226 | True | None | 0.6039902172993366 | -0.008545000000001579 | False | 0 |
| 7227 | True | None | 0.8335449627990186 | 0.0017800000000001148 | False | 0 |
| 7228 | True | None | 0.20828897173977615 | -0.04507999999999868 | False | 0 |
| 7229 | True | None | 0.6649528431744296 | -0.005803000000000225 | False | 0 |
| 7230 | False | mode_recipe_or_phase | None | None | False | 0 |


## 保存済み7layout C0 core比較

| layout C0 core | machine | sensor | precision | clean | unmatched | available/unavailable | delay median |
| ---: | --- | --- | --- | ---: | ---: | --- | --- |
| 0 | 0/10 | 0/10 | 0/3 | 3 | 3 | 13920/480 | None |
| 1 | 0/10 | 0/10 | 0/3 | 2 | 3 | 13920/480 | None |
| 2 | 0/10 | 0/10 | 0/3 | 3 | 3 | 13920/480 | None |
| 3 | 0/10 | 0/10 | 0/3 | 3 | 3 | 13920/480 | None |
| 4 | 0/10 | 0/10 | 0/3 | 3 | 3 | 13920/480 | None |
| 5 | 0/10 | 0/10 | 0/3 | 3 | 3 | 13920/480 | None |
| 6 | 0/10 | 0/10 | 0/3 | 3 | 3 | 13920/480 | None |

旧layout0–5はmanifest/config指標のみ比較、旧6result本文再展開・再compute0。全7cell宣言16calculator/candidate config/compiled config一致、入力10filename集合一致・layoutによるpin差保持。同seed7layout core C0であり7独立seedではない。旧layout1 clean2/未対応3を原値保持。
旧36cell board（同seed6layout×2strata12dataset×3候補）は閉鎖保存のまま保持。今回layout6はC0core1cellだけで全候補・strata比較未完了。bootstrap/統計CI・勝者・採択0。

## 入力・コード・環境

- input manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\006\attempt-0001\result\payload\manifest.json
- manifest: 75698B / 542248c4b9e6227749adce8d37c1769580ba0cb7426ebe12321ec192a775846d
- dataset: anomaly-v03-dev-seed-2486912926863618161-layout-06-core / role dev / seed 2486912926863618161。
- actual文書checkout: be44cf123c2ee8d34d18b3445e1d671577ebb6e9 / 計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。
- Actual runtime: 3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)] / Windows / AMD64 / C:\Python314\python.exe。
- elapsed18.051340200006962秒/private OScheckpoint sampled peak146124800B。global coupled peak/full memory閉包証明ではない。
- configuration: 5503B / d9e11a796da2ee1a4d32631cdd785cdee0a655b7fa249d0224577c2116caabf0
- manifest: 8032B / 621aa58bfd81f31007dbe6eec8242b73a73906d845b042ab475342d14b49926e
- evaluation: 13899056B / dc507be9d68d93d96676e25fa293ee5ee39e9e48a1cc6e1f0e80404695291d2f
- numerical: 13893558B / 7a15e6fa1ceed3e73c54dee3111520cc89160cfd1b36b167c9e7a48cfa9c378b
- target proof: {'bytes': 10987, 'sha256': 'e6dc06e847d38386dd866cf2871dc47860bdec2c4d26575f4bb745f9353081f9'}
- class proof: {'bytes': 8000, 'sha256': '9acf39127608e926ae531d73ef8fbd4098a27b87e7618d8cec28160931c2c7c7'}
- comparison: {'bytes': 26188, 'sha256': 'cf50f2c9b1e7dfbd4635a25c23d00a668d4ef3bfb83c5dc0e2e5368bf78f2b10'}

入力10pins:

- dataset-manifest.json: 784B / cf651a9ee1b2a75ddd9adfcaa42e6e3a00cbefde517096409050d6a96e0bbdaf
- event-ledger.jsonl: 19580B / de003141343ac151ddd7bab6d61290a76089733582174ac6226e2dbb1e57b360
- events.jsonl: 14590B / 2a65c2bd22005707b3afce0dcb626fd29c74f68484006f143ee2512cf9540a50
- fingerprint.json: 692B / 8b1c35cb5ece4f14989d6bc1c54eec2dc029dd59c351cc2d234c419119111209
- generator-config.json: 22093B / d6ba940efb2209db97bd01360782bbad575055351898b9673095c99518954b05
- observations.jsonl: 9600501B / 0afb767f74925aab25f32c77f1f5e5637d517f661e979d15ca48348eebb8240f
- origins.json: 9002B / 707f661f7a76bd6a788af147980abc181ddd874b53bb37cf0211f42e0f7bb5e6
- quality-mask.jsonl: 2994780B / 47724904f123cb8418036f10a7421f5227bc303f5d4f611f691a0a85f8013270
- split-manifest.json: 83B / 3876fbab57007aff3e7bd63da6dcf09af6a51b76f2632d2b00b4b60d38049b99
- targets.json: 232B / d70a6563ef48d7daf0f50dab761e20c1755e2473dda309093b0d819fad38cb8b

## 保全・次unit・正式gate

DATA{'files': 19, 'bytes': 26940258, 'manifest_pin': {'bytes': 2249, 'sha256': '48bbe2f0caa13e3f105eb5ab0287a90674a9fdf29c5682a020b4670e59dd4da3'}}/EXTRACT{'bytes': 278784, 'files': 7, 'manifest_pin': {'bytes': 1066, 'sha256': '4643208f3b72cbaf102a5c93b8db8a6724d1c59ddb8e10cf655c3cedf08392de'}}閉鎖。MAIN representative-layout6-core-c0-20261012-prep/POST representative-layout6-core-c0-post-20261012-prepの最終post-save/owners/root-closed優先。
117source/旧149root/frozen35capfalse/cache補足・全原failed/Git未知返値/continuations不変。前qualityC1 false13/raw12・前C2docs準備0対最終foreground4保持。前handoff整理は旧全文Git32db5134/prefix-tail-boundary保存を維持。今回foreground0/178helpers11failed167passed/fullidentity一致/CIM同original不在/repohelpercritical0/model-analysis2passed。foreground creation-stdioNone/selectedCLI≠全stdio/PID単独0/native回収claim0。
metadata512KiB32entry/reserve128KiB/single128KiB/recursive/Python-B/限定置換/新書込み前script-failure-closure件数bytes確認。MAIN preflight21file373120Bにproof2/meta/closureを足す予定幅がreserve超過となるため、docs.pyを未起動のまま保持し、新POST/docs-split-proof.pyでproof2をPOSTへ初保存。MAIN容量超過実書込み0/原script再実行0/閉鎖root追記0。closed-frozen追記・旧raw整理削除移動・上限緩和0。同GitHub同種dev結果/ユーザー名PC pathリスク通知後継続承認内でdocs2一回[skip ci] commit/push、原Git/APIはPOST保存。Git512KiB16entry/stdout1MiB/累積30秒/preflight別量。automation詳細転記設定変更0/ACTIVE。

次unitは同chunk006/layout6 core C1、新IDdev-layout6-core-c1-20261012/同manifest5422/同core10pins/qualitypair metadata保存。元生成C0/実評価C1別field、nextmodel未開始/生成0/quality観測body未読。完成評価試験replayCI反復0。
CI381385/4130独立verifier保存/新query-download-verifier0/旧381365in_progress履歴/doc-onlyCI追跡0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読/正式5残件・最終受入未完了/create_native早期拒否/全7役whole.run reader禁止/元caps-unknown原owner-stop/追加agent禁止。未完了formal/nativeを少量dev開始条件に戻さない。engineering900秒2GiB/output1GiB/single32MiB/files32 checkpointはblocking/fullruntime/global-native容量証明ではない。Sol容量/人の停止では原保全後PAUSED・重複再試行0。
