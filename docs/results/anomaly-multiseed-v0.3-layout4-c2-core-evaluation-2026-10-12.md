# 合成dev layout4 core C2実評価・core3候補保存比較（2026-10-12 JST）

## 実行と原結果

保存済みdev seed 2486912926863618161、layout4/coreの同じ10入力を、既存CLI C2 c2-phase-conditionalへ新ID dev-layout4-core-c2-20261012で一回実評価した。元生成candidate C0と実評価C2は別field。新dataset生成・元payload書込み・replay・production/test変更・追加agent0。

CLI exit0、run complete、1cell success。機械10/10、sensor10/10、precision20/20、clean誤警報0、未対応equipment0。処理successは性能合格・候補採択・正式受入ではない。source41、equipment20、incidents20、events40を原結果に保持した。C1のsource30と異なるため、同じ指標やdelayを原profile/score/episode同一へ読み替えない。

48profiles全calibrated、fit samples各600、calibration各290、C2 stateあり48。14400scoresの利用可能13920・不能480。primary及び非排他的tags全mode_recipe_or_phase480、不能score/residual null/threshold_exceeded false。各8targetの不能60行。18000mask-observation行を対応照合しnon-ok/欠測0。利用不能を正常scoreへ補完0。

全20incident causal_detected、原target sourceとequipmentが対応、各support2行。machine10件の対象onset遅延全2秒、sensor10件全1秒。検出20件delay中央値・平均1.5秒/min1max2、未検出0/補完forbidden。

## 原conditional score・phaseと対象onset

machine10対象窓phase不能各1、sensor10窓0。旧layout3のsensor窓phase及び機械1秒/sensor2秒の説明を流用0。今回固定C2設定/threshold6/persistence2/first-equipment-onset-no-retry-v1を変更0。

cycle00 machine motor-01.motor_current: sample7320phase不能、score/residual null/streak0。7321score88.3131857811625/streak1→7322score89.30834424316983/streak2でtarget source成立、onset-start2000ms/delay2秒。原selected source IDはincidentと一致。7323score1.304344605601411/streak0。

cycle00 sensor motor-01.motor_temperature: 7327score130.10349735562022/streak1→7328score130.39143776213626/streak2でtarget source成立、onset-start1000ms/delay1秒。7329streak3、7330score0.3538299768154632/streak0。元2score supportとsource/equipment対応を保存した。

全20event-incident/全20matched target-source-equipment、cycle00/01 machine-sensorとcycle09 sensorの5選択motor4target窓、全61source/equipment episodesを新EXTRACTへ保存。原result pin付きproofは全20target onset/class別delay-phaseとcycle00の2target原rowsを保持。原予測再compute0。入力対応・保存・状態分類の実経路不具合は観測なし。GT/科学式/config/threshold/persistence/matching変更0。

## 保存済み7cell比較

| layout | candidate | machine | sensor | precision | clean誤警報 | 検出delay中央値秒 |
| --- | --- | --- | --- | --- | --- | --- |
| 4 | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | None |
| 4 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 1.5 |
| 3 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 1.5 |
| 2 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 1.0 |
| 1 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 1.0 |
| 0 | c2-phase-conditional | 4/10 | 10/10 | 14/20 | 0 | 1.0 |
| 4 | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 1.5 |

同layout4 core3候補の保存比較完成。C0両0/10/precision0/3/clean3/delaynull、C1/C2両10/10/precision20/20/clean0/検出delay中央値平均1.5秒。原C0の未検出20delaynullを補わない。C2旧layout0機械4/10/precision14/20と他layoutの差を保持。

旧layout4 C0/C1とlayout0–3 C2はmanifest/config指標だけ参照。旧6cell result本文再展開・再compute0。全7cell宣言16calculator source/candidate config/compiled config一致。同layout4 core C0/C1/C2のinput10pins一致、他layout差保持。旧layout0–3 24cell比較とlayout4 C0/C1保存を保持。

同seed5layoutのC2coreと同layout4 C0/C1比較であり、7独立seed/datasetではない。同dataset候補反復を独立評価数にしない。bootstrap/統計CI推定・勝者・候補採択0。

## 入力・コード・環境の対応

- 原input manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\004\attempt-0001\result\payload\manifest.json
- 原manifest: 75699B / 54f358a6b69d9df9b27fd1e5762a2f3c63be0ab6e545df7aca8668d4d7f04fc3
- 原dataset: anomaly-v03-dev-seed-2486912926863618161-layout-04-core / role dev / seed 2486912926863618161 / layout4/core。
- 実文書checkout: 4208aafe48f9d95dd28aec2b14fe5f77af8f7277。計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。
- Actual runtime: 3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)] / Windows / AMD64 / C:\Python314\python.exe。
- 経過30.898906099959277秒、OScheckpoint sampled private peak 205672448B。samplingはglobal coupled peak/full memory閉包証明ではない。
- configuration: 5508B / 1c64048a0971ff427515b4945e15f6b92b8cf757455dffc8e6c2069257ddae86
- run manifest: 8009B / 6e8f61b527186a10c6f7431b2fe351c70e3eb66d2133ef1fc2cab1701676b50c
- 原evaluation: 24749836B / d4edc6ff4c3b0f14c124ed088252810d3c5bc973bbbb2598a000585002790386
- numerical: 24744338B / 3690f367639f6855e3fadf1b3a02288ec6ce24b88d7a4561b469b376c25dcd0b
- 原target proof: 22084B / 5745c5aa56238d5d9edb7a3392adff2eefc8dfe89b813bf66a5a8a308f0e3d42

入力10pins:

- dataset-manifest.json: 784B / 5da248906b096c1fa1eb7b11e8848dc9ca0e80c112a4c67121dda55df0f3ad87
- event-ledger.jsonl: 19410B / 21d7d663aa759899b2b74c94e809ee1617b1fdf01c3945e17d18fdc49348fa9d
- events.jsonl: 14460B / ae58e600b2eef13c2af2bcac30e05d4a34b8ec442615f9e9b4672305817d522c
- fingerprint.json: 692B / ee69ceb47e0c9ed99b3df0442bdaa181febf8100380da5e10b86e84ac46ecdb0
- generator-config.json: 21923B / 136c2c977eeb2aba171d98008104e2608db59e44378fe91e410a1341f524360c
- observations.jsonl: 9600454B / f72cfa13f68593cfb180508801ff2b0dd34eb4b25377ce93f36e466556838e42
- origins.json: 9002B / 707f661f7a76bd6a788af147980abc181ddd874b53bb37cf0211f42e0f7bb5e6
- quality-mask.jsonl: 2994780B / 47724904f123cb8418036f10a7421f5227bc303f5d4f611f691a0a85f8013270
- split-manifest.json: 83B / 3876fbab57007aff3e7bd63da6dcf09af6a51b76f2632d2b00b4b60d38049b99
- targets.json: 232B / d70a6563ef48d7daf0f50dab761e20c1755e2473dda309093b0d819fad38cb8b

## 保存・失敗保全

DATA閉鎖{'bytes': 37790494, 'files': 19, 'manifest_pin': {'bytes': 2254, 'sha256': '4c611dca5c17543c66676c5f023deab6256a8860da368ade588a25b776f639eb'}}、EXTRACT閉鎖{'bytes': 234367, 'files': 7, 'manifest_pin': {'bytes': 1079, 'sha256': 'c8a99c98dff94286c2b0e04f5769ea171c72c56f6cd28d179106d212a715acf5'}}。MAIN representative-layout4-core-c2-20261012-prep/POST representative-layout4-core-c2-post-20261012-prepの最終post-save/owners/root-closed優先。

117science-source/旧106root count-byte-closurepins不変。外部固定layout1 C1 MAIN35file容量falseと旧C2 cache補足を保持。過去failed、Git commit timeout/unknown return、lsremote128、別metadata continuation、前layout4 C0 foreground4及びC1 doc-builder失敗を保持・元script再実行0/failed書換え0。

今回foreground1失敗は開始時rg literal src/banto_ai/anomaly* Windows path syntax os error123/exit1。原selected traceをMAIN startup-source-selector-tool-error.jsonへ保持し、対象patternを-gの別selectorへ限定訂正。元helper/model/Git未開始/tracked mutation0、instrumented-helper/model/CI/native/Sol failureへしない。元147helpers原11failed136passed/fullsaved creation-start token一致/CIM同original不在/repo helpercriticalなし、今回model/analysis2passed。Foreground docs/closure fullcreation/fullstdioNone、selectedCLIをhelper全stdioへしない/PID単独0/native回収claim0。

新書込み前script/failure/closureも件数bytes確認。metadata512KiB32entry/reserve128KiB/single128KiB/recursive/Python-B/限定文字列/hash-seed無限定置換0。元payload・閉鎖/外部固定root追記・旧raw整理削除移動・上限緩和0。CIMdecimal100ns→microsecondtrunc/fullsavedtoken照合。

同GitHub同種合成dev結果・ユーザー名PC内pathの継続送信承認内で、handoff/report2を一回[skip ci] commit/pushし、原Git/API終端はPOST保存。Git512KiB16entry/stdout1MiB/累積30秒/preflight別量。automation設定更新・詳細結果/PCpath転記0。

## 次の未完成unit・正式gate

同chunk004/dev seed/layout4の保存quality-stressをC1 c1-phase-level、新ID dev-layout4-quality-c1-20261012で1cell実評価。dataset anomaly-v03-dev-seed-2486912926863618161-layout-04-quality-stress。manifest同54f、quality10pins metadataはprepared-docs/POSTに保存。元生成C0と実評価C1別field。今回はquality観測本文未読/次model未開始。新seed生成0。同coreの完成C0/C1/C2・旧24cell/replay/risk-owner/native/probe/collector/Git37/CI反復0。

CI38138556456/code661bの4130成功独立verifier保存維持、新query-download-verifier0、旧381365/a54961最後in_progress歴史、doc-onlyCI追跡0。CI成功≠モデル性能/native/正式受入。

formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読/正式5残件・最終受入未完了。create_native早期拒否・全7役whole.run reader起動禁止・元caps/unknown原owner-stop・追加agent禁止維持。未完了formal/native証明を少量dev開始の新条件に戻さない。engineering900秒/2GiB/output1GiB/single32MiB/files32 checkpoint≠blocking中断/full loaded runtime/native/allwriter-global容量証明。Sol容量又は人の停止では保全後PAUSED・重複再試行0。
