# 合成dev layout5 quality-stress C1実評価（2026-10-12 JST）

## 実行と原結果

保存済みdev seed 2486912926863618161、layout5/quality-stressを既存CLI C1 c1-phase-level、新ID dev-layout5-quality-c1-20261012で一回実compute_evaluation。元生成C0と実評価C1は別field。入力10pin照合→新snapshot→fresh fit/calibration→原profile/score/episode/event/incident/metricsを保存。元payload書込み・新dataset生成・replay・production/test変更・類似owner・追加agent0。

CLI exit0/run complete/1cell success。機械10/10、sensor9/10、precision19/19、clean誤警報0、未対応equipment0。source29/equipment19/incidents20/events40。処理successを性能合格・候補採択・正式受入へしない。

48profiles全calibrated、fit samples各600/calibration各290。14400scoresの利用可能13880・不能520、同core C1の13920/480から利用可能40行減少。primary phase480/current quality30/previous quality-or-nonfinite10。非排他的tags phase480/current quality30/current nonfinite30/previous quality-or-nonfinite30を合算しない。phase-tag/primary-other overlap0を原row/pinで保存。全不能score/residual null・threshold_exceeded false。

原18000mask-observation行対応、motor-01.motor_temperature missing30観測。検出19件は原target source/equipment対応・support各2行。machine10件/sensor検出9件のdelay全1秒、count19/min-max-mean-median全1.0秒。未検出1件delay null・補完forbidden。対象窓phase不能はmachine全10/sensor全10で0。

## 唯一未検出の原経路

cycle09 sensor motor-01.motor_temperature、event start8984/end8987/window end8990。原incidentはno_candidate_in_window/candidate0/causal_detected false、matched-source/equipment null、support[]/delay null。

8984 score142.9970959885234>threshold6/streak1。その後8985–8987 current target missing、8988 previous target quality不能でstreak0へreset。8989 score0.5667934655587978/streak0、8990 score0.773616373132083/0でthreshold6未満。固定persistence2のsecond exceedanceが成立しない。phase起因へ補わない。

全20event/incident、19matched target-source-equipment、cycle00/01 machine-sensorとcycle09 sensorの5選択motor4target窓、全48source/equipment episode、missing30原入力をEXTRACTへ保存。proofは19onsetと未検出原target実12rows（8982–8993）をresult pinに結ぶ。前layout4のfalse13/raw12失敗は原保存のまま保持。GT/config/threshold6/persistence2/first-equipment-onset-no-retry-v1/science変更0。入力対応・保存・状態分類の実経路不具合は観測なし。

## 保存済み7cell C1比較

| layout | stratum | machine | sensor | precision | clean誤警報 | 利用可能score | 検出delay中央値秒 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | core | 10/10 | 10/10 | 20/20 | 0 | 13920 | 1.0 |
| 4 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13880 | 2.0 |
| 3 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13880 | 1.0 |
| 2 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13889 | 1.0 |
| 1 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13880 | 1.0 |
| 0 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13880 | 2.0 |
| 5 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13880 | 1.0 |

同layout5 core C1と旧layout0–4 quality C1はmanifest/config指標のみ比較、旧6result本文再展開・再compute0。全7cell宣言16calculator/candidate config/compiled config一致。同core-quality入力10filename集合は同じ、観測/mask等pin差を保持。旧layout2の利用可能13889/不能511と旧layout4のmachine delay2秒を原値保持。

同seed6layout C1quality+同layout5 coreであり、7独立seed/datasetではない。旧30cell比較と同layout5 core3候補完成保存を保持。bootstrap/統計CI・勝者・採択0。

## 入力・コード・環境

- 原input manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\005\attempt-0001\result\payload\manifest.json
- 原manifest: 75699B / 765ddbc639d74063b00c79b28a1e534bdb5d7859bee66d0bd4d1add2d69fc9a6
- dataset: anomaly-v03-dev-seed-2486912926863618161-layout-05-quality-stress / role dev / seed 2486912926863618161。
- 実文書checkout: 39ecf084105123de90602f59ef075c31d66fc4df。計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。
- Actual runtime: 3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)] / Windows / AMD64 / C:\Python314\python.exe。
- 経過18.963031899998896秒、OScheckpoint sampled private peak148238336B。global coupled peak/full memory閉包証明ではない。
- configuration: 5512B / 28dfa00b9fbf2ff1a56d640b207ab744dc14121b93ae9ed21f1a572b2d99b4d6
- run manifest: 8035B / eb7b5cf84dff69aab877fb292cf4196331c213eab51e31a2bf35bdfc014e6e74
- 原evaluation: 14510837B / 64b39999fa27298a733162103c6738554ff658dca3ef08bedd383c6bdf6df9b7
- numerical: 14505239B / 9b7124e3dc2384348a4fdc5cfec69475ca6ef836d261cd24a401c0df2fa6ce76
- 原target proof: 18996B / a3fcae6ba2d45ca00f0ff36fe98c1d469ed5f117bf375efd07b7b5b00a9995a6

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

DATA閉鎖{'bytes': 27558365, 'files': 19, 'manifest_pin': {'bytes': 2258, 'sha256': '2a64d2719fbb96fcc330d99264b1336985852734a8d5a2b7c033841d350ae879'}}、EXTRACT閉鎖{'bytes': 237414, 'files': 7, 'manifest_pin': {'bytes': 1084, 'sha256': '89093cc093c01001576b20048dbfd7ce94c7d1737579352838b43567d464e43b'}}。MAIN representative-layout5-quality-c1-20261012-prep/POST representative-layout5-quality-c1-post-20261012-prepの最終post-save/owners/root-closedを優先。

117science-source/旧136root count-byte-closurepins不変。外部固定layout1 C1 MAIN35file容量false/旧C2 cache補足保持。全原failed・Git未知返値・continuation、前qualityC1 false13/raw12・前C2docs準備foreground0対最終foreground4を原保存優先で保持。今回foreground0。元169helpers原11failed158passed/fullsaved creation-start token一致/CIM同original不在/repo helpercriticalなし、今回model/analysis2passed。foreground docs/closure fullcreation/fullstdioNone、selectedCLI≠helper全stdio/PID単独0/native回収claim0。

新書込み前script/failure/closure件数bytes確認。metadata512KiB32entry/reserve128KiB/single128KiB/recursive/Python-B/限定文字列置換、閉鎖/外部固定root追記・旧raw整理削除移動・上限緩和0。同GitHub同種合成dev結果・ユーザー名PC pathのリスク通知後継続承認内、handoff/report2を一回[skip ci] commit/push。原Git/APIはPOSTへ保存。Git512KiB16entry/stdout1MiB/累積30秒/preflight別量。automation詳細転記・設定更新0、ACTIVE維持。

次unitは同chunk005/layout5 quality-stressをC2 c2-phase-conditional、新ID dev-layout5-quality-c2-20261012で1cell実評価。manifest同765d/同quality10pins、元生成C0と実評価C2別field。次model未開始/生成0。完成core3候補・今回quality C1・旧30cell/replay/risk-owner/native/probe/collector/Git37/CI反復0。

CI38138556456/code661bの4130独立verifier保存/新query-download-verifier0/旧381365in_progress履歴/doc-onlyCI追跡0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読/正式5残件・最終受入未完了/create_native早期拒否/全7役whole.run reader起動禁止/元caps-unknown原owner-stop/追加agent禁止。未完了formal/nativeを少量dev開始条件に戻さず、engineering900秒2GiB/output1GiB/single32MiB/files32 checkpointはblocking/fullruntime/global-native容量証明ではない。Sol容量又は人の停止では保全後PAUSED・重複再試行0。
