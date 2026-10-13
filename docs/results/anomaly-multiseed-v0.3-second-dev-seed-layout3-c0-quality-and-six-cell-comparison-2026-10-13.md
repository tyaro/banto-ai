# 第2 dev seed・layout3 C0 qualityと6cell比較（2026-10-13）

人の2026-10-13「承認します」は、直前の具体的リスク通知（今回layout3 C0合成dev結果・ユーザー名を含むPC内入力path・指定3文書・https://github.com/tyaro/banto-ai.git・今後同送信先の同種報告）への回答。承認待ち解除、今回3文書を一回[skip ci] commit/push。原2自動審査拒否/Git helper未起動・SyntaxError isolate前・launcher206未起動は閉鎖rootに保持し、モデル/CI/helper失敗へしない。完成C0モデル・解析再実行0。 初human-approved-saveは既存報告へpending_reportを渡しFileExistsError/failed、tracked編集commitpush前停止。原失敗保持・existing-report modeに限定訂正、新human-approved-save-continuationとhuman-approved-finalを優先。補助source準備のscope誤指定（元-localと原-local）はisolate内/nestedtools-process-trackedmutation0で原selected errorを保持、helper/model/CI失敗へしない。


保存済み合成dev quality-stressをC0で1cell fresh compute。機械0/10・sensor0/10・precision0/1・正常区間誤警報1件。全20未検出の原delaynullを保持し、同seed/layout3の3候補×2条件比較を完成。処理成功を性能保証・採択・正式受入へしない。

今回の初回export自動審査拒否は-export-reviewへ原保存、元docs helper未起動/Git0。既存2026-10-11の具体的リスク通知（C0合成dev結果・ユーザー名を含むPC内入力path・同GitHub送信先・今後の同種報告送信）後の人の「承認します」と、同一入力pathを同送信先へ保存済みC1C2報告を-export-authorization-checkで照合し、明示継続承認証拠付きで再審査。original rejection保持・helper/model/CI失敗へしない・bypass0。文書source準備のfunctions.exec SyntaxError missing ) after argument listはisolate評価前/nestedtools・process・trackedmutation0、原selected errorを-saveに保存。再審査も実行前拒否。理由は保存artifact中の承認だけでは信頼できる今回payloadの人の明示承認にならないとの判断。Git helper起動0/commit-push0。local draft保存の初回foreground launcher error206も未起動原証拠として-local-preparationに保全。今回-local-save/-pending-export-finalを優先し、承認までGit再試行・次モデル開始0。毎heartbeat同じ承認質問・状態不変通知を繰り返さない。
## 入力と実行

- run dev-seed7466813550306735603-layout3-quality-c0-20261013 / dataset anomaly-v03-dev-seed-7466813550306735603-layout-03-quality-stress。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\015\attempt-0001\result\payload\manifest.json / {"bytes": 75700, "sha256": "479787c83a7c7af9934171a66b6c3fd684689c2b908f79b483a768acf8c278cf"}。同C1C2quality input10完全一致→新snapshot/fresh calibration。元生成C0と実評価C0別field。元payload書込み生成replayagent0。
- checkout b0aa0a49980332d9397144b68b04d9344836afaa / 計算661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/candidatecompiled不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"} / elapsed 17.435779899940826秒 / sampled private peak 152010752B。
- observations {"bytes": 9600460, "sha256": "7120244e968597a3d37d89fe33e3772afbdad5ae20570f479ffbb09032947652"} / configuration {"bytes": 5513, "sha256": "038c005e0e07114574491d797a978e41056df3f48d078392720e4e8ba076cf8d"} / manifest {"bytes": 8086, "sha256": "e9a29efd91e24dba099dd32c35d5a38a74b9ad3d80d8455285180de2eff7735f"} / result {"bytes": 14333156, "sha256": "4d7a05888e8db8a5da9bdf02bce432d485922d6413840c7cf0b5b553ef2f3cb8"}。
- C0threshold4/C1C2threshold6/operator>/persistence2・GTmatching科学不変。全原thresholdflag確認、宣言pin≠full loaded runtime/native認証。

## 原結果

|項目|原値|
|---|---|
|machine|0/10|
|sensor|0/10|
|precision|0/1|
|clean / unmatched|1 / 1|
|source / equipment / incidents / events|1 / 1 / 20 / 40|
|available / unavailable|13880 / 520|

全20no_candidate_in_window/candidate0/causalfalse/matchednull/delaynull、delaycount0/minmaxmeanmedian原null/補完0。機械10対象窓は7全利用可/phase不能0/maxstreak1。sensor9窓6利用可/開始phase不能1/maxstreak1、cycle09sensor窓2利用可5不能phase1/maxstreak0。固定persistence2がどの対象窓でも成立しない。欠測1窓で全20未検出を説明しない。
48calibrated/fit_samples各0（C0経路）/calibration各290/C2stateなし48。18000input-mask対応nonok30。排他的phase480/current quality30/previous quality10＝520。phaseとquality重複0/core比不能増40。全不能score/residualnull/thresholdfalse。非排他的tags {"current_nonfinite": 30, "current_target_quality": 30, "mode_recipe_or_phase": 480, "previous_target_quality_or_nonfinite": 30} を独立行として加算しない。
clean_rate 1/3365原value 8.558692421991084 / effective 3255秒rate 8.847926267281107 / burden 1/20原value 5.0 を単純確率へしない。唯一clean source conveyor-01.motor_temperatureのequipment/source/support2score原対応保存。

## 選択原対象窓

### cycle0 sensor

|sample|available|score|streak|reason|
|---|---|---|---|---|
|7290|False|None|0|mode_recipe_or_phase|
|7291|True|3.7978526494290876|0|None|
|7292|True|3.7871939195955564|0|None|
|7293|True|147.71220920364235|1|None|
|7294|True|2.918824218592216|0|None|
|7295|True|1.5914955738813505|0|None|
|7296|True|1.8673740619686001|0|None|

### cycle0 machine

|sample|available|score|streak|reason|
|---|---|---|---|---|
|7311|True|51.512203289600954|1|None|
|7312|True|0.4654187886655519|0|None|
|7313|True|0.46104749997481903|0|None|
|7314|True|51.85133481639464|1|None|
|7315|True|0.5230228628558438|0|None|
|7316|True|0.03017378040814431|0|None|
|7317|True|0.002025607625515141|0|None|

### cycle9 sensor

|sample|available|score|streak|reason|
|---|---|---|---|---|
|8910|False|None|0|mode_recipe_or_phase|
|8911|False|None|0|current_target_quality|
|8912|False|None|0|current_target_quality|
|8913|False|None|0|current_target_quality|
|8914|False|None|0|previous_target_quality_or_nonfinite|
|8915|True|2.1593710838076743|0|None|
|8916|True|1.8216458748855051|0|None|

### cycle9 machine

|sample|available|score|streak|reason|
|---|---|---|---|---|
|8931|True|52.42506188457643|1|None|
|8932|True|0.19342952456521037|0|None|
|8933|True|0.2861136477464607|0|None|
|8934|True|50.76000327144329|1|None|
|8935|True|0.20112957702882595|0|None|
|8936|True|0.6942347182282874|0|None|
|8937|True|0.29925494868494745|0|None|

cycle09温度8910phase不能nullscore-streak0、8911–13current quality不能/8914previous quality不能、8915–16score<4/streak0。原20ledger/targetwindows/520不能/30nonok/全episodesを-analysis、選択4窓・clean episode/supportを-saveに保存。実入力対応・保存・状態分類不具合は観測なし。

## 同seed/layout3 3候補×2条件

|stratum|candidate|machine|sensor|precision|clean|available|source / equipment|delaycount / median|
|---|---|---|---|---|---|---|---|---|
|core|c0-diff-control|0/10|0/10|0/1|1|13920|1 / 1|0 / None|
|core|c1-phase-level|10/10|10/10|20/20|0|13920|30 / 20|20 / 1.5|
|core|c2-phase-conditional|10/10|10/10|20/20|0|13920|50 / 20|20 / 1.5|
|quality-stress|c0-diff-control|0/10|0/10|0/1|1|13880|1 / 1|0 / None|
|quality-stress|c1-phase-level|10/10|9/10|19/19|0|13880|29 / 19|19 / 1.0|
|quality-stress|c2-phase-conditional|10/10|9/10|19/19|0|13760|48 / 19|19 / 1.0|

同stratum内input10全一致/core-quality共通3 {"dataset-manifest.json": false, "event-ledger.jsonl": false, "events.jsonl": false, "fingerprint.json": false, "generator-config.json": false, "observations.jsonl": false, "origins.json": true, "quality-mask.jsonl": false, "split-manifest.json": true, "targets.json": true}。旧5cell再compute0/source16candidatecompiled一致。C0両条件全20miss/clean1、C1C2core20検出/quality19検出/clean0。C2qualityはpeer120追加不能、C1qualityとのavailability差を保存済み原証拠で保持。指標一致を全scoreepisode一致・勝者・採択へしない。
既存一次差分＋persistence2と3観測[end exclusive]定常加算成分の内部差分相殺解釈を保持。今回19対象窓maxstreak1/1対象窓maxstreak0と整合。新式監査・正常対照再compute・閾値GT変更0。機械乗算overlayを単純加算toyと同一視しない。
C0quality保存16cellsのmanifest指標比較。第1seed72＋第2seed layouts0/1/2/3各6＝96boardcells/使用seed2。96独立datasetではない。bootstrap統計CI勝者採択0。

## 証拠・次工程・正式状態

- artifacts/representative-seed2-layout3-quality-c0-20261013-* の-final/post-save/root-closed優先。DATA artifacts/representative-anomaly-evaluation/dev-seed7466813550306735603-layout3-quality-c0-20261013 / {"bytes": 27379927, "files": 19, "manifest_pin": {"bytes": 2235, "sha256": "a4e3b73cd863ee11861e3c9a07d492c508f405a94ab951f45066f38ed78f2bcd"}}。
- 旧481root/436helpers23failed413passedmissingexecution1保全。過去容量審査/foreground失敗/旧helperfailure/停止再開/誤記保持。新sourcebuilder SyntaxError1（isolate評価前）/instrumentedhelperfailure0。閉鎖外部固定root追記整理0/fullstdioPID単独native回収claim0。
- prepare_result_index実使用でreport/handoff/index3docsローカル保存。自動承認審査2回拒否/Git helper未起動・commit/push0/bypass0。今回payloadの信頼できる人の明示承認を待つ。
- 次同seed/layout4 core C0、新ID dev-seed7466813550306735603-layout4-core-c0-20261013。新chunk016保存manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\016\attempt-0001\result\payload\manifest.json / {"bytes": 75699, "sha256": "45d694bc6600878955dad80cb3ae87fb8333647a839758c7c10ea87af8052c24"}。identity/input10metadataだけ選択、観測本文未読/次model0。新独立seedではない。
- EvidenceStore16MiB512files/part256KiB/失敗2MiB16files/閉鎖512KiB4files・全writepreflight。実行900秒2GiBoutput1GiBsingle32MiBfiles32/Git30秒16entry512KiBstdout1MiBstderr128KiB/nativeprotocol caps維持。checkpoint≠blocking中断/fullruntime/global/allwriter容量証明。
- ACTIVE/automation詳細転記0/CI3813854130querydownloadverifiertests0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件最終受入未完了/create_native早期拒否/7役reader禁止/追加agent禁止/capsunknown原owner保持。未完了formal/nativeをdev開始条件へ戻さない。Sol容量人停止は保全後PAUSED。
