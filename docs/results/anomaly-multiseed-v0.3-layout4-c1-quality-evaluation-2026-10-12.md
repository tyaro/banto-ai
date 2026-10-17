# 合成dev layout4 quality-stress C1実評価（2026-10-12 JST）

## 実行と原結果

保存済みdev seed 2486912926863618161、layout4/quality-stressを既存CLI C1 c1-phase-level、新ID dev-layout4-quality-c1-20261012で一回実compute_evaluation。元生成C0と実評価C1別field。元payload書込み・新dataset生成・replay・production/test変更・追加agent0。同core完成C0/C1/C2を再計算0。

CLI exit0/run complete/1cell success。機械10/10、sensor9/10、precision19/19、clean誤警報0、未対応equipment0。source29/equipment19/incidents20/events40を保存。処理successは性能合格・候補採択・正式受入ではない。

48profiles全calibrated、fit samples各600/calibration各290。14400scoresの利用可能13880・不能520。同core C1の13920/480から利用可能40行減少。primary phase480/current target quality30/previous target quality-or-nonfinite10。非排他的tags phase480/current quality30/current nonfinite30/previous quality-or-nonfinite30は重複するため合算しない。phase-tag/primary-other overlap0を原row/pinで保存。全不能score/residual null/threshold_exceeded false、欠測を正常scoreへ補完0。

原18000mask-observation行対応、motor-01.motor_temperature missing30観測。他の原入力を改変しない。全19検出のtarget source/equipment対応、support各2行。machine10件delay全2秒、sensor検出9件全1秒。検出19だけdelay中央値2秒/平均1.5263157894736843秒/min1max2。未検出1件delay null、補完forbidden。

## 未検出cycle09 sensorの原経路

対象motor-01.motor_temperature、event start8947/end8950/window end8953。原incidentはno_candidate_in_window/candidate0/causal_detected false、matched-source/equipment null、support[]/delay null。

8947 score128.11372973003026>threshold6/streak1。その後8948–8950 current target missing、8951 previous target quality不能でstreak0へreset。8952はscore1.2064712737455632/streak0、8953は0.9110746840746275/0でthreshold6未満。固定persistence2のsecond exceedanceが成立しない。このsensor窓phase不能は0、旧layout3のsensor start phase不能を流用しない。

全20incident/event、19matched target-source-equipment、cycle00/01 machine-sensorとcycle09 sensorの5選択motor4target窓、全48source/equipment episode及びmissing30原入力を新EXTRACTへ保存。proofは19対象onsetと唯一未検出の原target12rowsをresult pinに結ぶ。GT/config/threshold6/persistence2/first-equipment-onset-no-retry-v1/science変更0。入力対応・保存・状態分類の実経路不具合は観測なし。今回の未検出を設定変更や形式的成功へ補わない。

## 保存済み6cell C1比較

| layout | stratum | machine | sensor | precision | clean誤警報 | 利用可能score | 検出delay中央値秒 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 4 | core | 10/10 | 10/10 | 20/20 | 0 | 13920 | 1.5 |
| 3 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13880 | 1.0 |
| 2 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13889 | 1.0 |
| 1 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13880 | 1.0 |
| 0 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13880 | 2.0 |
| 4 | quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13880 | 2.0 |

同layout4 core C1と旧layout0–3 quality C1はmanifest/config指標のみ比較、旧5cell result本文再展開・再compute0。全6cell宣言16calculator/candidate config/compiled config一致。同core-qualityの入力10filename集合は同じ、quality観測/mask等のpin差を保持。旧layout2の利用可能13889/不能511差を保持し、全layoutの不能520へ補わない。

同seed5layoutのC1qualityと同layout4 core C1の比較であり、6独立seed/datasetではない。同datasetへの候補反復を独立評価数にしない。旧layout0–3 24cell比較とlayout4 core3候補完成保存を保持。bootstrap/統計CI推定・勝者・採択0。

## 入力・コード・環境の対応

- 原input manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\004\attempt-0001\result\payload\manifest.json
- 原manifest: 75699B / 54f358a6b69d9df9b27fd1e5762a2f3c63be0ab6e545df7aca8668d4d7f04fc3
- 原dataset: anomaly-v03-dev-seed-2486912926863618161-layout-04-quality-stress / role dev / seed 2486912926863618161 / layout4/quality-stress。
- 実文書checkout: 0628b972e471bbd2428e0c527cad4982dbf2d063。計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。
- Actual runtime: 3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)] / Windows / AMD64 / C:\Python314\python.exe。
- 経過18.20072770002298秒、OScheckpoint sampled private peak148131840B。samplingはglobal coupled peak/full memory閉包証明ではない。
- configuration: 5512B / fc2aee8a6c18c21f62b1ff14ebf0537ddbfe2002a3dd6deb4320c20c2cf58b32
- run manifest: 8049B / 8999f7ee03136d4c240e33cbbec8a076e460fd77e2fc69cacd52da3f67ec75cc
- 原evaluation: 14508303B / 9f34f035237397eb12b0a35ee9de67b7c7767997344554ada21a5022467be382
- numerical: 14502705B / 9b9c158e6cabcf832aad9412e6ba4a857ab04f0933bb0e6b1617dea780b29157
- 原target proof: 18973B / aef6e1fe6840bdcb23948fc3e064a187d3f77d200b495fa0c77cc2935eb9cb97

入力10pins:

- dataset-manifest.json: 804B / 61c66baa70f9a8cf7db349fd80753e43dcd1c73ee7393cf67030cc1a2d17ddea
- event-ledger.jsonl: 19800B / 5a8b5b003ce5c42cb324486aa83e65f33bf5ab908b9c7fd266888e818b90e439
- events.jsonl: 19800B / 5a8b5b003ce5c42cb324486aa83e65f33bf5ab908b9c7fd266888e818b90e439
- fingerprint.json: 692B / 188747cbaff88e030e11b32d5a0f3f2d7cc234a399f3b49394a400ac11440aa3
- generator-config.json: 22333B / 03bcdef4a70d2e2628d619d3182a4ed8b6106f6a508b3fbcf21bdd08c1e39b98
- observations.jsonl: 9600460B / 236a92b486a1c0d3f329f6a41e1c12858742e5ea0b1bc7e857430bb89a593804
- origins.json: 9002B / 707f661f7a76bd6a788af147980abc181ddd874b53bb37cf0211f42e0f7bb5e6
- quality-mask.jsonl: 2994930B / 15b2b9ca0a33ad970e062c942efaba3556148d2665d1a424a03261b7ac5c046a
- split-manifest.json: 83B / 3876fbab57007aff3e7bd63da6dcf09af6a51b76f2632d2b00b4b60d38049b99
- targets.json: 232B / d70a6563ef48d7daf0f50dab761e20c1755e2473dda309093b0d819fad38cb8b

## 保存・失敗履歴

DATA閉鎖{'bytes': 27555357, 'files': 19, 'manifest_pin': {'bytes': 2258, 'sha256': 'd04f459e5d3b2ee14691e64ec4dc5ff310d59ebe3d3ce238273a2a540c36d498'}}、EXTRACT閉鎖{'bytes': 236641, 'files': 7, 'manifest_pin': {'bytes': 1084, 'sha256': '2cee77816b93132c6b08c31860ebb21d25c5aa67164bf58944f21795745cac84'}}。MAIN representative-layout4-quality-c1-20261012-prep/POST representative-layout4-quality-c1-post-20261012-prepの最終post-save/owners/root-closedを優先する。

117science-source/旧110root count-byte-closurepins不変。外部固定layout1 C1 MAIN35file容量false/旧C2 cache補足保持。過去failed、Git commit timeout/unknown return、lsremote128、別metadata continuation、前layout4 C0 foreground4/C1 doc-builder/C2 selector失敗を保持・元script再実行0/failed書換え0。今回foreground1失敗は最終metadata閉鎖のtarget行数期待13対原12のAssertionError/exit1。元close-post.py/selectedtraceをPOSTへ保全し、元script再実行0/model-Git反復0。原保存12行(sample8945–8956)を確認し、報告行数と未完了metadataを新専用continuationへ訂正。原model/analysis/Gitはpassedのまま、instrumented-helper/model/CI/native/Sol失敗へしない。最終保存はrepresentative-layout4-quality-c1-metadata-continuation-20261012-prep/post-save・owners・root-closedを優先。元150helpers原11failed139passed/fullsaved creation-start token一致/CIM同original不在/repo helpercriticalなし、今回model/analysis2passed。foreground docs/closure fullcreation/fullstdioNone、selectedCLIをhelper全stdioへしない/PID単独0/native回収claim0。

新書込み前script/failure/closure件数bytes確認、metadata512KiB32entry/reserve128KiB/single128KiB/recursive/Python-B/限定文字列/hash-seed無限定置換0。元payload・閉鎖/外部固定root追記・旧raw整理削除移動・上限緩和0。CIMdecimal100ns→microsecondtrunc/fullsavedtoken照合。

同GitHub同種合成dev結果・ユーザー名PC内pathのリスク通知後継続承認内で、handoff/report2を一回[skip ci] commit/pushし、原Git/API終端はPOSTへ保存。Git512KiB16entry/stdout1MiB/累積30秒/preflight別量。automation設定更新・詳細結果/PCpath転記0。

## 次の未完成unit・正式gate

同chunk004/dev seed/layout4のquality-stressをC2 c2-phase-conditional、新ID dev-layout4-quality-c2-20261012で1cell実評価。manifest同54f/同quality10pins、元生成C0と実評価C2別field。次model未開始/生成0。同core完成C0/C1/C2、今回quality C1、旧24cell/replay/risk-owner/native/probe/collector/Git37/CI反復0。

CI38138556456/code661bの4130成功独立verifier保存維持、新query-download-verifier0/旧381365/a54961最後in_progress歴史/doc-onlyCI追跡0。CI成功≠モデル性能/native/正式受入。

formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読/正式5残件・最終受入未完了。create_native早期拒否・全7役whole.run reader起動禁止・元caps/unknown原owner-stop・追加agent禁止維持。未完了formal/native証明を少量dev開始条件に戻さない。engineering900秒/2GiB/output1GiB/single32MiB/files32 checkpoint≠blocking中断/full loaded runtime/native/allwriter-global容量証明。Sol容量又は人の停止では保全後PAUSED・重複再試行0。
