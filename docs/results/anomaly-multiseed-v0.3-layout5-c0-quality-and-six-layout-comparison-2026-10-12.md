# 合成dev layout5 C0 quality実評価と6layout比較（2026-10-12 JST）

## 今回の実計算

保存済みdev seed 2486912926863618161、layout5 quality-stressを既存CLI C0 c0-diff-control、新ID dev-layout5-quality-c0-20261012で1cell実compute_evaluation。input10pin照合→新snapshot→fresh calibration→原profiles/scores/episodes/events/incidents/metrics保存。元生成C0と実評価C0別field、元payload書込み・新dataset生成・replay・production/test変更・類似owner・追加agent0。

CLI exit0/complete/1cell success。機械0/10・sensor0/10・precision0/3、clean誤警報3/未対応equipment3。source3/equipment3/incidents20/events40。全20missはno_candidate_in_window/candidate0/causalfalse/matched-source-equipment null/support[]/delay null。delay count0/min-max-mean-median原null、補完forbidden。処理successを性能合格・採択・正式受入へしない。

48profiles全calibrated/fit samples各0/calibration各290。14400scores、利用可能13880/不能520。primary phase480/current quality30/previous quality-or-nonfinite10。非排他的tags phase480/current quality30/current nonfinite30/previous quality-or-nonfinite30を合算0、phase-tag/primary-other overlap0。全不能score/residual null/thresholdfalse。原18000mask-observation対応、motor-01.motor_temperature missing30。

全20対象窓maxstreak1、machine/sensor対象窓phase不能全0。固定C0threshold4/persistence2不成立。cycle09温度8984score70.538767145775/streak1→8985–8987current欠測/8988previous不能reset→8989score0.4281753989643912/0・8990score0.4620470800524433/0。欠測一件だけでC0全20missを説明しない。
全20event/incident/全20motor4target窓/全6source-equipment episodes/missing30をEXTRACT保存。proof全20target窓の原statsとcycle00 machine/sensor・cycle09 sensorの原target scores。GT/config/threshold4/persistence2/first-equipment-onset-no-retry-v1/science変更0、実入力対応・保存・分類不具合観測なし。

未対応3equipmentは全clean/null matched。原clean rate3/3365/value25.676077265973255、effective3255/value26.543778801843317、burden3/20/value15.0を原値保持し単純確率へしない。

## 36cell保存比較

| layout | stratum | candidate | machine | sensor | precision | clean | unmatched | available/unavailable | delay median/mean秒（検出のみ） |
| ---: | --- | --- | --- | --- | --- | ---: | ---: | --- | --- |
| 0 | core | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 3 | 13920/480 | None/None |
| 0 | core | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 0 | 13920/480 | 1.5/1.5 |
| 0 | core | c2-phase-conditional | 4/10 | 10/10 | 14/20 | 0 | 6 | 13920/480 | 1.0/1.2857142857142858 |
| 0 | quality-stress | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 3 | 13880/520 | None/None |
| 0 | quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 0 | 13880/520 | 2.0/1.5263157894736843 |
| 0 | quality-stress | c2-phase-conditional | 4/10 | 9/10 | 13/19 | 0 | 6 | 13760/640 | 1.0/1.3076923076923077 |
| 1 | core | c0-diff-control | 0/10 | 0/10 | 0/3 | 2 | 3 | 13920/480 | None/None |
| 1 | core | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 0 | 13920/480 | 1.0/1.0 |
| 1 | core | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 0 | 13920/480 | 1.0/1.0 |
| 1 | quality-stress | c0-diff-control | 0/10 | 0/10 | 0/3 | 2 | 3 | 13880/520 | None/None |
| 1 | quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 0 | 13880/520 | 1.0/1.0 |
| 1 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 0 | 13760/640 | 1.0/1.0 |
| 2 | core | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 3 | 13920/480 | None/None |
| 2 | core | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 0 | 13920/480 | 1.0/1.0 |
| 2 | core | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 0 | 13920/480 | 1.0/1.0 |
| 2 | quality-stress | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 3 | 13889/511 | None/None |
| 2 | quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 0 | 13889/511 | 1.0/1.0 |
| 2 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 0 | 13796/604 | 1.0/1.0 |
| 3 | core | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 3 | 13920/480 | None/None |
| 3 | core | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 0 | 13920/480 | 1.5/1.5 |
| 3 | core | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 0 | 13920/480 | 1.5/1.5 |
| 3 | quality-stress | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 3 | 13880/520 | None/None |
| 3 | quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 0 | 13880/520 | 1.0/1.4736842105263157 |
| 3 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 0 | 13760/640 | 1.0/1.4736842105263157 |
| 4 | core | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 3 | 13920/480 | None/None |
| 4 | core | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 0 | 13920/480 | 1.5/1.5 |
| 4 | core | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 0 | 13920/480 | 1.5/1.5 |
| 4 | quality-stress | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 3 | 13880/520 | None/None |
| 4 | quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 0 | 13880/520 | 2.0/1.5263157894736843 |
| 4 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 0 | 13760/640 | 2.0/1.5263157894736843 |
| 5 | core | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 3 | 13920/480 | None/None |
| 5 | core | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 0 | 13920/480 | 1.0/1.0 |
| 5 | core | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 0 | 13920/480 | 1.0/1.0 |
| 5 | quality-stress | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 3 | 13880/520 | None/None |
| 5 | quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 0 | 13880/520 | 1.0/1.0 |
| 5 | quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 0 | 13760/640 | 1.0/1.0 |

同seed1/layout0–5×core・qualityの12datasets×3候補=36cell。完成済み35cellはmanifest/configのみ比較、旧result本文再展開・再compute0。全36宣言16calculator/candidate config/compiled config一致、各dataset3候補のinput10pins全一致。同seed-layout-strataへの候補反復を36独立seed/datasetへしない。bootstrap/統計CI・勝者・採択0。

今回layout5 coreはC0両0/10precision0/3clean3、C1/C2両10/10precision20/20clean0/delay全1秒。qualityはC0両0/10precision0/3clean3、C1/C2機械10/10・sensor9/10precision19/19clean0/detected19全1秒。未検出は原null。
quality利用可能はC0/C1 13880、C2 13760。core各13920。C2qualityのpeer120波及・C1source29対C2source38は原前報告保持し、同検出指標を原prediction同一へしない。旧layout0C2機械4/10・layout1C0clean2/未対応3・layout2qualityavailabilityとtag重複差・layout3sensor start phase・layout4machine phase/delay2秒を原値保持。

BOARD {'bytes': 261905, 'files': 10, 'manifest_pin': {'bytes': 1533, 'sha256': '7d1a17f14b2379a6043b3fd9218493e29c67faee50490198efd96dbe851f2c59'}}は6parts/36cell index・宣言16source/config pins・次原chunk006 manifest metadata/selectionを閉鎖保存。旧30cell board不変。

## 入力・コード・環境

- input manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\005\attempt-0001\result\payload\manifest.json
- manifest: 75699B / 765ddbc639d74063b00c79b28a1e534bdb5d7859bee66d0bd4d1add2d69fc9a6
- dataset: anomaly-v03-dev-seed-2486912926863618161-layout-05-quality-stress / role dev / seed 2486912926863618161。
- actual文書checkout: 32db5134e857ebca46ba8d5da726b5a99c8fb424 / 計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。
- Actual runtime: 3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)] / Windows / AMD64 / C:\Python314\python.exe。
- elapsed18.458679899922572秒/private OScheckpoint sampled peak146788352B。global coupled peak/full memory閉包証明ではない。
- configuration: 5513B / ab433209bd1be08e098e48a40d424b591b31cbe5721494b8c78a47378f7e308c
- manifest: 8065B / 5ad81a9eb0deb5d10b2c6faea90736bcfd8bcc675d2bff6b17753bcb189d02cc
- evaluation: 14336265B / e4baa4d168e972ccfc78d225b6b07d4cdfb517af63bc9ea61ae40b353834295c
- numerical: 14330667B / b943a0b1e923fe9b3f7e2138ef81ac45253a09011052597a31298a93aa1181b1
- 原target-window proof: {'bytes': 15914, 'sha256': 'b2a2906da64a52e8720010599bd4d500ea4f36227d84daeac1d659e901ad8c16'}
- comparison index: {'bytes': 4424, 'sha256': '327e9392710b941ad5390abe2e341735e7db3eac40ca9043e3a9b5512e52a886'}

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

## 引継ぎ整理と保全

Git512KiB batch上限を維持するためcurrent-handoffのlayout5直近履歴を残し、それ以前は保存済み全文 [Git版](https://github.com/tyaro/banto-ai/blob/32db5134e857ebca46ba8d5da726b5a99c8fb424/docs/current-handoff.md)と個別報告への参照へ整理。旧全文{'bytes': 512118, 'sha256': 'c969f7a0e93874bfaede56c8f8be558004ee0cfc741215d50ab7eff81e34dc14'}、残すprefix{'bytes': 21499, 'sha256': 'ea600d739f3c71bc79fb72412f86e45798579a338b02aabfa807abcf212dda53'}、古いtail{'bytes': 490619, 'sha256': '645ebbf38520f295e4fe557a577fb752e4e44c8676126460b4b0c711bc3f59e2'}、境界byte21499をMAIN/handoff-history-reference.json {'bytes': 954, 'sha256': '8aaf24f6a45ade72bc01f7f8108d77a3897b122a5968d2bdb2b4bd4b37ae7359'}に保存。原失敗・停止・承認履歴は旧Git版と原POSTを優先。元raw/閉鎖root変更0・cap上限緩和0。

DATA{'files': 19, 'bytes': 27383857, 'manifest_pin': {'bytes': 2259, 'sha256': '4f1264c8eef2b05e269ca375592ad02c7cc4ea5c935f684d3372cd66c0366cd3'}}/EXTRACT{'bytes': 302364, 'files': 8, 'manifest_pin': {'bytes': 1200, 'sha256': 'b49fd3a2499ee499b4a05bcabeb76ec6c700bc7212663acd694e2c5b3d4ef84d'}}/BOARD{'bytes': 261905, 'files': 10, 'manifest_pin': {'bytes': 1533, 'sha256': '7d1a17f14b2379a6043b3fd9218493e29c67faee50490198efd96dbe851f2c59'}}閉鎖。MAIN representative-layout5-quality-c0-20261012-prep/POST representative-layout5-quality-c0-post-20261012-prep最終post-save/owners/root-closed優先。
117source/旧144root/frozen35capfalse/cache補足不変。全原failed・Git未知返値・continuation、前qualityC1 false13/raw12・前C2docs準備foreground0対最終foreground4保持。今回foreground0/175helpers11failed164passed/fullsaved identity一致/CIM同original不在/repohelpercritical0/model-analysis2passed。foreground creation-stdioNone/selectedCLI≠全stdio/PID単独0/native回収claim0。
metadata512KiB32entry/reserve128KiB/single128KiB/recursive/Python-B/限定置換/新書込み前script-failure-closure件数bytes確認。closed-frozen追記・旧raw整理削除移動・上限緩和0。同GitHub同種dev結果/ユーザー名PC pathリスク通知後継続承認内でdocs2一回[skip ci] commit/push、原Git/APIはPOST保存。Git512KiB16entry/stdout1MiB/累積30秒/preflight別量。automation詳細転記設定変更0/ACTIVE維持。

## 次unit・正式gate

同保存chunk006/devseed/layout6 core C0、新ID dev-layout6-core-c0-20261012で1cell実評価。manifest {'bytes': 75698, 'sha256': '542248c4b9e6227749adce8d37c1769580ba0cb7426ebe12321ec192a775846d'}、dataset anomaly-v03-dev-seed-2486912926863618161-layout-06-core、next input10/qualitypair metadata保存。新独立seedではなく同seed次layout。元観測/元生成評価body未読・次model未開始/生成0。完成36cell/試験replayCI反復0。

CI381385/4130独立verifier保存/新query-download-verifier0/旧381365in_progress履歴/doc-onlyCI追跡0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読/正式5残件・最終受入未完了/create_native早期拒否/全7役whole.run reader禁止/元caps-unknown原owner-stop/追加agent禁止。未完了formal/nativeを少量dev開始条件に戻さない。engineering900秒2GiB/output1GiB/single32MiB/files32 checkpointはblocking/fullruntime/global-native容量証明ではない。Sol容量/人の停止では原保全後PAUSED・重複再試行0。
