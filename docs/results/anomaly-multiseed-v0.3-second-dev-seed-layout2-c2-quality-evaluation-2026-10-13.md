# 第2 dev seed・layout2 C2 quality-stress実評価と再開（2026-10-13）

人の「再開しましょう」に従いbanto-10をACTIVEへ戻し、停止時未開始のC2 quality-stressを1cell実評価した。機械10/10・sensor9/10・precision19/19・正常区間誤警報0、未検出1delay nullを保持。処理成功を性能保証・正式受入へしない。

## 入力・実行

- run dev-seed7466813550306735603-layout2-quality-c2-20261013 / dataset anomaly-v03-dev-seed-7466813550306735603-layout-02-quality-stress / 元生成C0・実評価C2別field。
- 保存manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\014\attempt-0001\result\payload\manifest.json / {"bytes": 75700, "sha256": "13a1f0848235ab785ddc31036c819927a40d5a62e7ff55adb91afe465275998a"}。同C1quality input10一致→新snapshot/fresh fit/calibration。元payload書込み・生成・replay・追加agent0。
- checkout 610a00d35bddcf8d57041876eabbc8ad78cf63da / 計算661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/candidatecompiled不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"} / elapsed 48.04372910002712秒 / sampled private peak 212271104B。
- observations {"bytes": 9600484, "sha256": "6938545c18ea01b4045a5248c2dbee7d6e7fc464d8491ad29e0c6ac984a4ac54"} / config {"bytes": 5518, "sha256": "b060723db91f0e992b544939e8c3d762672cc6139473a50aa3e9bf25abf582b3"} / manifest {"bytes": 8064, "sha256": "de964736350d544e5c18e65ebf952e2f1842e13e593f18992a4c600512c47a40"} / result {"bytes": 25197757, "sha256": "677cce8a0a59991407b9baafe8b3597f4d10ffaa78a6795105e50608f620b6f9"}。
- C0threshold4/C1C2threshold6/operator>/persistence2・GT/matching科学不変。宣言source pinはfull loaded runtime/native認証ではない。

## 原結果と利用不能

|項目|原値|
|---|---|
|machine|10/10|
|sensor|9/10|
|precision|19/19|
|clean / unmatched|0 / 0|
|source / equipment / incidents / events|44 / 19 / 20 / 40|
|available / unavailable|13796 / 604|

48calibrated/fit各600/calibration各290/C2stateあり48。18000input-mask対応non-ok30。排他的primary phase471/current quality30/previous quality10/peer93＝604。非排他的tags {"current_nonfinite": 30, "current_target_quality": 30, "mode_recipe_or_phase": 480, "peer_quality_or_nonfinite": 120, "previous_target_quality_or_nonfinite": 30} は重複加算しない。
peerタグ120（他3target各40）のうち27（各9）はphase除外と重複し、primaryはphaseへ分類される。温度current qualityとphase重複9も別に原保存。C1quality511不能からC2は93増、C2core480不能から124増。motor-01四targets各1709/1800、conveyor-01四targets各1740/1800利用可。全不能score/residual null・thresholdfalse。
cycle09の温度8902–04 current quality、8905 previous quality不能が他3targetのpeer不能12行へ波及しstreak reset。全原primary93/tag120/重複27+9/選択12行を-save/peer-quality-propagation保存。
検出19だけdelaycount19/min=max=mean=median1秒、未検出delaynull補完0。clean_rate0/3365/effective3254rate0/burden0/20原0を単純確率へしない。

## 未検出と19検出の対応

唯一未検出cycle09 motor-01.motor_temperature sensor spike [8901,8904)/window8901–8907。first score167.15318248307418/streak1後、8902–04 current quality不能、8905 previous quality不能でreset。8906/8907は閾値6未満/streak0。persistence2不成立・candidate0/no_candidate_in_window/causalfalse/matchednull/delaynull。対象窓phase不能0。

|sample|available|score|streak|reason|
|---|---|---|---|---|
|8901|True|167.15318248307418|1|None|
|8902|False|None|0|current_target_quality|
|8903|False|None|0|current_target_quality|
|8904|False|None|0|current_target_quality|
|8905|False|None|0|previous_target_quality_or_nonfinite|
|8906|True|1.352050570778708|0|None|
|8907|True|0.8606458290098851|0|None|

19検出のevent→対象source→matched equipment→support2scoreを照合。全38support対象一致/利用可/score>6、machine10/sensor9 onset=start+1秒。19窓7全利用可/maxstreak3・未検出窓3利用可4不能/maxstreak1。
全44sourceは19matched equipment内参照。source内訳 {"motor-01.motor_current": 19, "motor-01.vibration_feature": 16, "motor-01.motor_temperature": 9} / class membership {"machine": {"motor-01.motor_current": 10, "motor-01.vibration_feature": 10}, "sensor": {"motor-01.motor_current": 9, "motor-01.motor_temperature": 9, "motor-01.vibration_feature": 6}}。source件数をequipment件数・誤警報件数へしない。全incident/windows/unavailable/non-ok/episodesは-analysis-continuationへ、support原値は-saveへ保存。入力対応・保存・状態分類の実モデル経路不具合は観測なし。

## 保存指標の比較

|条件|machine|sensor|precision|clean|available / unavailable|source / equipment|
|---|---|---|---|---|---|---|
|C2 core|10/10|10/10|20/20|0|13920 / 480|47 / 20|
|C1 quality|10/10|9/10|19/19|0|13889 / 511|29 / 19|
|C2 quality|10/10|9/10|19/19|0|13796 / 604|44 / 19|

同quality input10完全一致、core対quality共通3file（origins/split/targets）。旧モデル再compute0、source16candidatecompiled一致。指標一致を全score/episode一致・勝者・採択へしない。別stratum全差を欠測だけの反実仮想証明へしない。
C2quality保存15cellsのmanifest指標比較。第1seed72＋第2seed layout0/1全12/layout2core3/qualityC1C2二件＝89boardcells/使用seed2。89独立datasetではない。bootstrap/統計CI/勝者/採択0。

## 再開・補助解析失敗の保全

automation status PAUSED→ACTIVE、人の明示再開で旧停止を解除。status/updated_at以外の設定不変、評価詳細・PC内path設定転記0。停止記録rootは保持。
元 -analysis はモデル証拠root閉鎖前に開始され、root-closed.json未作成のFileNotFoundErrorでfailed。原script・traceback・helper fullcreation/status・失敗を閉鎖保持、書換え追加0。モデルはその後exit0/complete、再compute0。別 -analysis-continuation が完了済み原結果から未保存解析を完成。補助解析失敗をモデル/CI/native/Sol容量失敗へしない。
- 原失敗root D:\develop\banto-ai\artifacts\representative-seed2-layout2-quality-c2-20261013-analysis / {"bytes": 19823, "files": 9, "manifest_pin": {"bytes": 415, "sha256": "5a7ad9820742ed73187d8ef2ddce95f8fbb7e196dca2216a660e6b2112656247"}}。
- records/analysis-continuation/save/final: artifacts/representative-seed2-layout2-quality-c2-20261013-*。最終-final/post-save・root-closed優先。DATA artifacts/representative-anomaly-evaluation/dev-seed7466813550306735603-layout2-quality-c2-20261013 / {"bytes": 38244764, "files": 19, "manifest_pin": {"bytes": 2235, "sha256": "9dbf4d1cc413eddf7f4eac501bd97ede4a02c162de64f04825b6a1ec439a862f"}}。
- 旧442root+停止root+今回原failed解析root＝444priorroot不変。停止後407helper基準、今回原failed1を追加して保全。最終helper/root集計は-final。fullstdio/PID単独/native回収claim0。
- prepare_result_index実使用、report/handoff/index3docsを同種合成dev報告・PC内path継続送信承認範囲で一回[skip ci] commit/push。追加承認質問・bypass0。
- 次unit同seed/layout2 quality-stress C0、新ID dev-seed7466813550306735603-layout2-quality-c0-20261013。同manifest/input10本文C1C2読取済み・未開始。完成89cell反復0。
- EvidenceStore16MiB512files/part256KiB/失敗2MiB16files/閉鎖512KiB4filesと全writepreflight。実行900秒2GiBoutput1GiBsingle32MiBfiles32/Git30秒16entry512KiBstdout1MiBstderr128KiB/nativeprotocol維持。checkpoint≠blocking中断/fullruntime/global/allwriter容量証明。
- CI381385/4130querydownloadverifiertests0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件最終受入未完了/create_native早期拒否/全7役reader禁止/capsunknown原owner・追加agent禁止を維持。Sol容量人停止は原保全後PAUSED/重複再試行なし。
