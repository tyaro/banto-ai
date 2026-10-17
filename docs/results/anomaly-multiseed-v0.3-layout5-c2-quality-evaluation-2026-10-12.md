# 合成dev layout5 quality-stress C2実評価（2026-10-12 JST）

## 実行と原結果

保存済みdev seed 2486912926863618161、layout5/quality-stressを既存CLI C2 c2-phase-conditional、新ID dev-layout5-quality-c2-20261012で一回実compute_evaluation。元生成C0と実評価C2別field。input10pin照合→新snapshot→fresh fit/calibration→原profile/score/episode/event/incident/metrics保存。元payload書込み・新dataset生成・replay・production/test変更・類似owner・追加agent0。

CLI exit0/run complete/1cell success。機械10/10・sensor9/10・precision19/19、clean誤警報0/未対応equipment0。source38/equipment19/incidents20/events40。処理successを性能合格・候補採択・正式受入へしない。

48profiles全calibrated、fit600/calibration290各、C2state48。14400scoresは利用可能13760・不能640、同core C2の13920/480から利用可能160減。同quality C1の13880/520から120減。primary phase480/peer120/current quality30/previous quality-or-nonfinite10。非排他的tags phase480/peer120/current quality30/current nonfinite30/previous quality-or-nonfinite30を合算しない。phase-tag/primary-other overlap0を原row/pin保存。全不能score/residual null・threshold_exceeded false。

原18000mask-observation行対応、motor-01.motor_temperature missing30。温度自身current30+previous10に加え同motor current/conveyor_speed/vibration各40peer不能、全120原score rowsをEXTRACT保存。episode有無で不能行を成功scoreへ補わない。

全19検出は原target source/equipment対応・support各2行。machine10/sensor検出9のdelayは全1秒、count19/min-max-mean-median全1.0秒。未検出1件delay null・補完forbidden。対象窓phase不能はmachine全10/sensor全10で0。

## cycle09 sensor未検出とpeer波及

motor-01.motor_temperature、event start8984/end8987/window end8990。原incidentはno_candidate_in_window/candidate0/causal_detected false、matched-source/equipment null、support[]/delay null。
8984 score147.99270049039734>threshold6/streak1→8985–8987 current欠測/8988 previous不能でstreak0 reset→8989 score0.7129796682140745/0・8990 score0.7088258167107027/0、threshold6未満。固定persistence2のsecond exceedanceが成立しない。phase起因へ補わない。
同windowの8985–8988は他3target×4sample=12peer rowsもnull/thresholdfalse/streak0、原scoreをproofへ保存。全120peer rowsへの外部pin参照も保存。

原全20event/incident・19matched target-source-equipment・5選択motor4target窓・全57source/equipment episode・missing30入力をEXTRACT保存。proofは19onsetと未検出原target実12rows（8982–8993）及びcycle09 peer12rowsをresult pinへ結ぶ。GT/config/threshold6/persistence2/first-equipment-onset-no-retry-v1/science変更0。実入力対応・保存・分類不具合観測なし。

## 保存済み8cell比較

| layout | stratum | candidate | machine | sensor | precision | clean誤警報 | 利用可能score | delay中央値秒 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | core | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 13920 | 1.0 |
| 5 | quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 13880 | 1.0 |
| 4 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13760 | 2.0 |
| 3 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13760 | 1.0 |
| 2 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13796 | 1.0 |
| 1 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13760 | 1.0 |
| 0 | quality-stress | c2-phase-conditional | 4/10 | 9/10 | 13/19 | 0 | 13760 | 1.0 |
| 5 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13760 | 1.0 |

同layout5 core C2・quality C1及び旧layout0–4 quality C2をmanifest/config指標だけ比較。旧7result本文再展開・再compute0。全8cell宣言16calculator/candidate config/compiled config一致。同quality C1-C2 input10全一致、core-quality品質pin差保持。
C1qualitysource29対C2qualitysource38を別保持し、同検出指標を原prediction一致へしない。旧layout0 C2機械4/10・旧layout2quality利用可能13796/不能604・旧layout4machine delay2秒は原値保持。
同seed6layout C2quality+同layout5比較で8独立seed/datasetではない。旧30cellと同core3候補保存を保持。quality全候補比較は未完了。bootstrap/統計CI・勝者・採択0。

## 入力・コード・環境

- 原input manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\005\attempt-0001\result\payload\manifest.json
- 原manifest: 75699B / 765ddbc639d74063b00c79b28a1e534bdb5d7859bee66d0bd4d1add2d69fc9a6
- dataset: anomaly-v03-dev-seed-2486912926863618161-layout-05-quality-stress / role dev / seed 2486912926863618161。
- 実文書checkout: 938cebd32670f44c9b2733889b03ce409fb69f2e。計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。
- Actual runtime: 3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)] / Windows / AMD64 / C:\Python314\python.exe。
- elapsed29.815738399978727秒 / OScheckpoint sampled private peak206581760B。global coupled peak/full memory閉包証明ではない。
- configuration: 5518B / 600d472c7627d7c4d957d6e71d131bc8d4694c16dcfaf51435adc96cae025bf8
- run manifest: 8041B / 6e7c56697586c037338d0bf66b7605f5fe3cce192f88aeefd30761ee73d463eb
- evaluation: 25191802B / 0d8d656c85650e1fae456a9bb0aeb2039e420e745a58ed9267175b5e4365b5f6
- numerical: 25186204B / c4c9d7f57dfddee5ef93c286da83aaa92381f0aae53902eebe178e01a752e2c9
- 原target-peer proof: 23131B / 2f3d8bc2f008d9348887d5eeeab4febb71f8380c32c8302c434a9bc20d8b973a

入力10pins:

- dataset-manifest.json: 804B / ac1d40334cdca9c2b56d590dd0c83dde47cd1a4c73571530ecb474a50655550a
- event-ledger.jsonl: 19920B / e5511f8bc1f18d21bc2f8b7c59f0e05f5271a48bb4778446f23b02bd3eee9806
- events.jsonl: 19920B / e5511f8bc1f18d21bc2f8b7c59f0e05f5271a48bb4778446f23b02bd3eee9806
- fingerprint.json: 692B / 1ca4f08ef89dc3b8cd81208df3709eea257574ffe786ee1e6e4099e587de7b05
- generator-config.json: 22453B / 2f0e222c07454b413a8cf1daf771617c59864d5668add0d91990222db2e5bf71
- observations.jsonl: 9600602B / 6a9339b8553379564d8d7fc5bbf93e2aed2df9366f7611f13b9e95abc3f60495
- origins.json: 9002B / 707f661f7a76bd6a788af147980abc181ddd874b53bb37cf0211f42e0f7bb5e6
- quality-mask.jsonl: 2994930B / 96819536c0b547e6c497e54f39118e1ef7dc45602743e0c391afdf93ba750145
- split-manifest.json: 83B / 3876fbab57007aff3e7bd63da6dcf09af6a51b76f2632d2b00b4b60d38049b99
- targets.json: 232B / d70a6563ef48d7daf0f50dab761e20c1755e2473dda309093b0d819fad38cb8b

## 保全・次unit・正式gate

DATA{'bytes': 38239366, 'files': 19, 'manifest_pin': {'bytes': 2264, 'sha256': '1c6ca91215eed1dc7d3440d3e565095c6e05e711aab99a508e2006357f354aae'}}/EXTRACT{'bytes': 286842, 'files': 9, 'manifest_pin': {'bytes': 1344, 'sha256': '30a6e882ad6cf5c4c38096415e6904e4a69dc2e6f68e00af38b27490073ec03a'}}閉鎖。MAIN representative-layout5-quality-c2-20261012-prep/POST representative-layout5-quality-c2-post-20261012-prepの最終post-save/owners/root-closed優先。

117source/旧140root count-byte-closurepin不変、外部固定layout1 C1 MAIN35file容量false/旧C2 cache補足不変。全原failed・Git未知返値・continuation、前qualityC1 false13/raw12・前C2docs準備foreground0対最終foreground4保持。今回foreground0/172helpers11failed161passed/fullsaved identity一致/CIM同original不在/repohelpercritical0/model-analysis2passed。foreground creation-stdioNone/selectedCLI≠全stdio/PID単独0/native回収claim0。

metadata512KiB32entry/reserve128KiB/single128KiB/recursive/Python-B/限定置換、新書込み前script-failure-closure件数bytes確認。closed-frozen追記・旧raw整理削除移動・上限緩和0。同GitHub同種dev結果・ユーザー名PC pathのリスク通知後継続承認内でdocs2一回[skip ci] commit/push、原Git/APIはPOST保存。Git512KiB16entry/stdout1MiB/累積30秒/preflight別量。automation詳細転記・設定変更0/ACTIVE維持。

次unitは同chunk005/layout5 quality-stress C0、新ID dev-layout5-quality-c0-20261012で1cell実評価し、同layoutのcore-quality×3候補比較を完成。manifest同765d/同quality10pins、元生成C0と実評価C0別field、次model未開始/生成0。完成評価試験replayCI反復0。

CI381385/4130独立verifier保存/新query-download-verifier0/旧381365in_progress履歴/doc-onlyCI追跡0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読/正式5残件・最終受入未完了/create_native早期拒否/全7役whole.run reader禁止/元caps-unknown原owner-stop/追加agent禁止。未完了formal/nativeをdev開始条件に戻さない。engineering900秒2GiB/output1GiB/single32MiB/files32 checkpoint≠blocking/fullruntime/global-native容量証明。Sol容量又は人の停止では原保全後PAUSED・重複再試行0。
