# 合成dev layout4 core C1実評価（2026-10-12 JST）

## 実行と原結果

保存済みdev seed 2486912926863618161、layout4/coreの同じ10入力を、既存CLIのC1 c1-phase-levelへ新ID dev-layout4-core-c1-20261012で一回実評価した。元生成candidate C0と実評価C1は別fieldに保持する。新dataset生成・元payload書込み・replay・production/test変更・追加agentは0。

CLI exit0、run complete、1cell success。機械10/10、sensor10/10、precision20/20、clean誤警報0、未対応equipment0。処理successは性能合格・候補採択・正式受入ではない。source30、equipment20、incidents20、events40を原結果に保持した。

48profilesは全calibrated、fit samples各600、calibration各290。14400scoresの利用可能13920・不能480。primary及び非排他的tagsは全mode_recipe_or_phase480で、不能score/residualはnull、threshold_exceeded false。8targetの不能各60行。18000mask-observation行を対応照合し、non-ok/欠測0。利用不能値を正常scoreへ補完しない。

全20incidentはcausal_detected、対象sourceとequipmentが対応し、各support2行。machine10件の対象onset遅延は全2秒、sensor10件は全1秒。検出20件のdelay中央値・平均1.5秒、min1/max2、未検出0/補完forbidden。

## 原score・phaseと対象onset

今回layout4ではmachine10対象窓のphase不能が各1行、sensor10窓は0行。旧layout3のsensor窓phase及び機械1秒/sensor2秒の説明を流用しない。

cycle00 machine motor-01.motor_current: sample7320はphase不能、score/residual null、streak0。7321はscore88.47382553947917/streak1、7322は89.4755251669796/streak2で対象source成立、onset-start2000ms/delay2秒。原selected source IDはincidentと一致する。7323はscore1.3417760735391209/streak0へ戻る。

cycle00 sensor motor-01.motor_temperature: 7327はscore128.8665769564381/streak1、7328は129.14023046234337/streak2で対象source成立、onset-start1000ms/delay1秒。7329はstreak3、7330はscore0.36479078143002547/streak0。固定threshold6/persistence2/first-equipment-onset-no-retry-v1を変更せず、原2scoreのsupportとsource/equipment対応を確認した。

全20event-incident、全20matched target-source-equipment、cycle00/01 machine-sensorとcycle09 sensorの5選択motor4target窓、全50source/equipment episodesを新EXTRACTへ保存した。原result pin付きproofは全20対象onset・class別delay/phase集計とcycle00の2target原rowsを保持する。原予測の再計算ではない。入力対応・保存・状態分類の実経路不具合は観測しなかった。GT/科学式/config/threshold/persistence/matching変更0。

## 保存済み6cell比較

| layout | candidate | machine | sensor | precision | clean誤警報 | 検出delay中央値秒 |
| --- | --- | --- | --- | --- | --- | --- |
| 4 | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | None |
| 3 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 1.5 |
| 2 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 1.0 |
| 1 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 1.0 |
| 0 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 1.5 |
| 4 | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 1.5 |

layout4 C0と旧layout0–3 C1は保存manifest/config指標だけ参照した。旧5cell result本文再展開・再compute0。全6cellの宣言16calculator source/candidate config/compiled config一致。同layout4 core C0/C1のinput10pins一致、他layout入力pin差を保持。旧layout0–3の3候補×2条件24cell比較とlayout4 C0の保存を保持した。

同seed5layoutのC1coreと同layout4 C0との比較であり、6独立seed/datasetではない。同datasetの候補反復を独立評価数にしない。bootstrap/統計CI推定・勝者・候補採択0。

## 入力・コード・環境の対応

- 原input manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\004\attempt-0001\result\payload\manifest.json
- 原manifest: 75699B / 54f358a6b69d9df9b27fd1e5762a2f3c63be0ab6e545df7aca8668d4d7f04fc3
- 原dataset: anomaly-v03-dev-seed-2486912926863618161-layout-04-core / role dev / seed 2486912926863618161 / layout4/core。
- 実文書checkout: 7f4fde13b54ceaa7a7412bd5a8439c31e06a1bb8。計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。
- Actual runtime: 3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)] / Windows / AMD64 / C:\Python314\python.exe。
- 経過20.877352899988182秒、OScheckpoint sampled private peak 147660800B。samplingはglobal coupled peak/full memory閉包証明ではない。
- configuration: 5502B / 2915450e0306c21610830f419750982f569e4c2e2dd4dd0fb7d2851a08d93a67
- run manifest: 8003B / dbe79c19d893d36df1defecaabe580c519333843cf4d61cad14f99b9f7468719
- 原evaluation: 14070110B / 40e6e044d8089932f192cd5c05d9fbe30dc0fb1708adb1dbd32ed42b53b74ede
- numerical: 14064612B / 8c0503dbe72459e1f76bf2bf9c09bea214110c4599e258a94202668be714b894
- 原target proof: 21516B / 4d956e8efe01952f9be517b7883a5a7f34c75d05c193edfa487a58ab6fc3c183

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

## 保存と失敗保全

DATA閉鎖{'bytes': 27110732, 'files': 19, 'manifest_pin': {'bytes': 2248, 'sha256': '083306d28d1b34f827e35baa548db638cd718b58bf64204913501ef86db150e6'}}、EXTRACT閉鎖{'bytes': 213885, 'files': 6, 'manifest_pin': {'bytes': 950, 'sha256': '3f61955317daf829b4e405f74effa2eb05ee7e00d99b9324c36d633202706bc1'}}。MAIN representative-layout4-core-c1-20261012-prep/POST representative-layout4-core-c1-post-20261012-prepの最終post-save/owners/root-closedを優先する。

117science-source/旧102root count-byte-closurepins不変。外部固定layout1 C1 MAIN35file容量falseと旧C2 cache補足を保持。全過去failed、Git commit timeout/unknown return、lsremote128、別metadata continuation、前layout4 C0 foreground4失敗を保持し、元script再実行0/failed書換え0。

今回foreground1失敗は文書source生成functions.exec SyntaxError Unexpected identifier c1（Markdown backtick由来）、isolate評価前でnestedtools/process/書込み/tracked mutation0。原selected errorをMAIN doc-builder-orchestration-failure.jsonへ保持。文書script・評価・Gitはこの失敗時に未起動。別の構文で新sourceを初めて保存し、原model/analysisを再実行0。この失敗をinstrumented-helper/model/CI/native/Sol容量failureへしない。元144helpersは11failed133passed、原live-execution full creation/start token一致、CIM同original不在、repo helpercriticalなし、今回model/analysis2passed。foreground fullcreation/全stdioNone、selectedCLIをhelper全stdioへしない。PID単独判定/native回収claim0。

新書込み前にscript/failure/closureも件数・bytes確認。metadata512KiB32entry/reserve128KiB/single128KiB/recursive/Python-B。元payload・閉鎖/外部固定root追記・旧raw整理削除移動・上限緩和0。helper sourceは限定対象文字列で新rootへ生成、hash/seed無限定置換0。CIMdecimal100ns→microsecondtrunc/fullsavedtoken照合。

同GitHub同種合成dev結果・ユーザー名を含むPC内pathの継続送信承認に基づき、handoffと本報告2文書を一回[skip ci] commit/pushし、原Git/API終端はPOSTに保存する。Git512KiB16entry/stdout1MiB/累積30秒、preflight別量。automation設定更新・詳細結果/PCpath転記0。

## 次の未完成unit・正式gate

同chunk004/dev seed/layout4/coreをC2 c2-phase-conditional、新ID dev-layout4-core-c2-20261012で1cell実評価。manifest/input10pinsは今回と同じ。元生成C0と実評価C2別field。qualityはmetadata10pinsのみ/観測本文未読/次model未開始。完成C1/C0、旧24cell、replay、risk-owner/native/probe/collector/Git37/CIを反復しない。

CI38138556456/code661bの4130成功独立verifier保存維持、新query-download-verifier0、旧381365/a54961最後in_progress歴史、doc-onlyCI追跡0。CI成功をモデル性能/native/正式受入へしない。

formal gate=s4_acceptance_not_frozen、formal_permission=false、credit0、holdout観測未読、正式5残件・最終受入未完了。create_native早期拒否・全7役whole.run reader起動禁止・元caps/unknown原owner-stop・追加agent禁止維持。未完了formal/native証明を少量dev開始の新条件に戻さない。engineering900秒/2GiB/output1GiB/single32MiB/files32 checkpoint≠blocking中断/full loaded runtime/native/allwriter-global容量証明。Sol容量又は人の停止では保全後PAUSED・重複再試行0。
