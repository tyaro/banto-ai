# 合成dev layout4 quality-stress C2実評価・peer不能120行（2026-10-12 JST）

## 実行と原結果

同保存dev seed 2486912926863618161、layout4/quality-stressを既存CLI C2 c2-phase-conditional、新ID dev-layout4-quality-c2-20261012で一回実compute_evaluation。元生成C0と実評価C2別field。元payload書込み・新dataset生成・replay・production/test変更・追加agent0。

CLI exit0/run complete/1cell success。機械10/10、sensor9/10、precision19/19、clean誤警報0、未対応equipment0。source39/equipment19/incidents20/events40保存。C1qualityのsource29と異なるため、同じ指標を原profile/score/episode同一へしない。処理success≠性能合格/候補採択/正式受入。

48profiles全calibrated、fit samples各600/calibration各290/C2 stateあり48。14400scoresの利用可能13760・不能640。同core C2の13920/480から不能160行増加、同quality C1の13880/520との差120行。

## 欠測・peer依存の原波及

原mask-observation18000行対応、motor-01.motor_temperature missing30観測。primary phase480/peer quality-or-nonfinite120/current target quality30/previous target quality-or-nonfinite10。非排他的tags phase480/peer120/current quality30/current nonfinite30/previous quality30は重複するため合算しない。phase-tag/primary-other overlap0原row/pin保存。全不能score/residual null/threshold_exceeded false、欠測を正常scoreへ補完0。

温度自身はcurrent30+previous10に加え、motor-01のcurrent/conveyor_speed/vibration各40行がpeer不能、合計120行。C2の同時current/previous peer入力依存で3targetへ波及した。全120原peer score rowsをresult pin付きEXTRACTへ保存し、primary target別40行/原null/streak0を確認した。C1qualityとの追加不能120行とcore C2との差160行を別保持する。

全19検出はtarget source-equipment対応/support各2。machine10件delay全2秒/sensor検出9件全1秒、検出19だけ中央値2秒/平均1.5263157894736843秒/min1max2。未検出1件delay null/補完forbidden。

## cycle09 sensor未検出の原経路

対象温度event8947–8950/window8953。原incidentはno_candidate_in_window/candidate0/causalfalse、matched-source/equipment null/support[]/delay null。8947score129.48303645987338>threshold6/streak1→8948–8950 current欠測/8951 previous不能でreset→8952score1.2549928171683875/0・8953score1.0122120776672292/0でthreshold6未満。固定persistence2のsecond exceedance不成立。このsensor窓phase不能0、旧layout3のstart phase説明を流用0。

8948–8951の3peer×4sample=12原peer rowsもscore/residual null/thresholdfalse/streak0。原target windowはsample8945–8956の実12行であり、前C1の誤期待13を流用せずraw件数とsample集合を照合した。

全20event-incident/19matched target-source-equipment、5選択motor4target窓、全58source/equipment episode、missing30原入力、全peer120原rowsを新EXTRACTへ保存。proofは19target onset/唯一miss target実12rows/cycle09 peer12rows/全peer数を原result pinへ結ぶ。原予測再compute0。GT/config/threshold6/persistence2/first-equipment-onset-no-retry-v1/science変更0。入力対応・保存・状態分類の実経路不具合観測なし。

## 保存済み7cell比較

| layout | stratum | candidate | machine | sensor | precision | clean誤警報 | 利用可能score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 4 | core | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 4 | quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 13880 |
| 3 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13760 |
| 2 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13796 |
| 1 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13760 |
| 0 | quality-stress | c2-phase-conditional | 4/10 | 9/10 | 13/19 | 0 | 13760 |
| 4 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13760 |

同layout4 core C2・quality C1と旧layout0–3 quality C2はmanifest/config指標のみ比較、旧6result本文再展開・再compute0。全7cell宣言16calculator/candidate config/compiled config一致。同quality C1/C2 input10pins全一致、core-quality filename集合一致/品質pin差保持。他layout差、旧layout0 C2機械4/10、旧layout2 quality利用可能13796/不能604を保持し、全layout不能640へ補わない。

同seed5layout C2quality+同layout4 core C2/quality C1比較であり、7独立seed/datasetではない。旧24cell比較/layout4 core3候補/quality C1と元failed保存保持。bootstrap/統計CI推定・勝者・採択0。

## 入力・コード・環境の対応

- 原input manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\004\attempt-0001\result\payload\manifest.json
- 原manifest: 75699B / 54f358a6b69d9df9b27fd1e5762a2f3c63be0ab6e545df7aca8668d4d7f04fc3
- 原dataset: anomaly-v03-dev-seed-2486912926863618161-layout-04-quality-stress / role dev / seed 2486912926863618161 / layout4/quality-stress。
- 実文書checkout: 634655a1983fb1e612b826a9ff03a43457b2eb69。計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。
- Actual runtime: 3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)] / Windows / AMD64 / C:\Python314\python.exe。
- 経過29.57753899996169秒、OScheckpoint sampled private peak206241792B。sampling≠global coupled peak/full memory閉包証明。
- configuration: 5518B / d7e443f5ba01185ad053e456b5103a75d62fcd4bb841f1a7642219ee5ae9ed83
- run manifest: 8055B / 4ffd57472ae45072e22d0b70b526d5dadabe3999163f74d9ca73de7f0468c9ae
- 原evaluation: 25190335B / 3347a0287625ab5093a0d4384130a13f9b6306de0656900ab1c7e455cb13ece4
- numerical: 25184737B / 6215b124d7495c29505b4811063bbb920e369a494cdb6171b1e4526ab1bc8766
- 原peer proof: 22839B / 68631effbbe32c01a504f7a80581201cbbe8c79f23c64f2969dcebee02db35c6

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

DATA閉鎖{'bytes': 38237425, 'files': 19, 'manifest_pin': {'bytes': 2264, 'sha256': '11d1bdd2641b378ddeff1ec6265c02dbf0e0230a541b5fe4747983fa40273fcf'}}、EXTRACT閉鎖{'bytes': 287784, 'files': 9, 'manifest_pin': {'bytes': 1344, 'sha256': 'e142f9cbdbaa7bcff965e9181ff15bfb4e4f64c13cbe933bbe7cea8970dc4fa5'}}。MAIN representative-layout4-quality-c2-20261012-prep/POST representative-layout4-quality-c2-post-20261012-prepの最終post-save/owners/root-closed優先。

117science-source/旧115root count-byte-closurepins不変。外部固定layout1 C1 MAIN35file容量false/旧C2 cache補足、過去failed/Git timeout未知return/lsremote128/continuations保持。前qualityC1 false13対raw12のforeground closure失敗・原script未再実行・訂正文書Git別保存は前continuationを優先し、元failedをpassedへ書換え0。今回newforeground failure0。元154helpers原11failed143passed/fullsaved creation-start token一致/CIM同original不在/repo helpercriticalなし、今回model/analysis2passed。foreground docs/closure fullcreation/fullstdioNone/selectedCLIをhelper全stdioへしない/PID単独0/native回収claim0。

新書込み前script/failure/closure件数bytes確認、metadata512KiB32entry/reserve128KiB/single128KiB/recursive/Python-B/限定文字列/hash-seed無限定置換0。閉鎖/外部固定root追記・元payload/原raw整理削除移動・上限緩和0。CIMdecimal100ns→microsecondtrunc/fulltoken。同GitHub同種dev結果/ユーザー名PC内pathのリスク通知後継続承認内で、handoff/report2を一回[skip ci] commit/pushし、原Git/API終端はPOST保存。Git512KiB16entry/stdout1MiB/累積30秒/preflight別量。automation設定更新・詳細結果/PCpath転記0。

## 次の未完成unit・正式gate

同保存chunk004/dev seed/layout4 quality-stressをC0 c0-diff-control、新ID dev-layout4-quality-c0-20261012で1cell実評価し、同layout4のcore/quality×3候補保存比較を完成する。manifest同54f/同quality10pins、元生成C0と実評価C0別field。次model未開始/生成0。完成core C0/C1/C2・quality C1/C2/旧24cell/replay/risk-owner/native/probe/collector/Git37/CI反復0。

CI38138556456/code661bの4130成功独立verifier保存維持/新query-download-verifier0/旧381365/a54961最後in_progress歴史/doc-onlyCI追跡0。CI成功≠モデル性能/native/正式受入。
formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読/正式5残件・最終受入未完了。create_native早期拒否/全7役whole.run reader起動禁止/元caps-unknown原owner-stop/追加agent禁止維持。未完了formal/native証明を少量dev開始条件に戻さず、engineering900秒/2GiB/output1GiB/single32MiB/files32 checkpoint≠blocking中断/full loaded runtime/native/allwriter-global容量証明。Sol容量又は人の停止では保全後PAUSED・重複再試行0。
