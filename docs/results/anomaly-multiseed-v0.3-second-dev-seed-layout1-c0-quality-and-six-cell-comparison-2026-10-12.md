# 第2 dev seed・layout1 C0 qualityと6cell比較（2026-10-12）

保存済み合成dev quality-stressをC0で1回fresh compute。機械0/10・センサー0/10・precision0/1・正常区間誤警報1件。全20未検出と原delay nullを保持。同seed/layout1の3候補×2条件の保存比較を完成。処理成功を性能保証・採択・正式受入にしない。

## 入力と実行

- run dev-seed7466813550306735603-layout1-quality-c0-20261012 / dataset anomaly-v03-dev-seed-7466813550306735603-layout-01-quality-stress。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\013\attempt-0001\result\payload\manifest.json / {"bytes": 75699, "sha256": "d4743f431240dee56e5ead1d0709a998e502b6a7e8a4aecd3f00468dced8bd81"}。seed7466813550306735603/layout1/quality-stress/dev、同C1C2 input10pin一致→新snapshot→fresh calibration→原profiles/scores/episodes/events/incidents/metrics保存。
- 元生成C0・実評価C0は別field。元payload書込み・新生成・replay・追加agent0。
- checkout 4f634e35ec58dfe8fcf730917a812b5e4a3e6361、計算661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/candidate-compiled config不変。runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 19.407324300031178秒/privatepeak 152109056B。
- observations {"bytes": 9600492, "sha256": "ef8b9dcc9138899b773ce5aebb07592211e679e71d8578f4be21f97eb6b609a6"}、configuration {"bytes": 5513, "sha256": "44e5ad1e5047d41ebdf805f1eafe37d0476a744d8bbb9851e8bc5dbf26ab3312"}、manifest {"bytes": 8086, "sha256": "33e3a7a0761117a03839721b6b774ad08802423955045c4935578815b1017ee3"}、evaluation {"bytes": 14333141, "sha256": "cb770910f17bf3797f4bbd24ed1b5ac2db61d61fd6282a322b542d44d291cb0a"}。宣言source pinはfull loaded runtime/native認証ではない。
- C0 threshold4/C1C2 threshold6/operator>/persistence2・GT/matching/science不変。原score閾値判定全行確認。

## 原結果と未検出

|項目|原値|
|---|---|
|machine|0/10|
|sensor|0/10|
|precision|0/1|
|clean / unmatched|1 / 1|
|source / equipment / incidents / events|1 / 1 / 20 / 40|
|available / unavailable scores|13880 / 520|

48profiles全calibrated/fit_samples各0（C0計算経路）/calibration各290/C2stateなし48。18000observations-mask対応、non-ok30行。primary排他的不能phase480/current quality30/previous quality10＝520。全不能score-residual null/thresholdfalse。非排他的tags {"current_nonfinite": 30, "current_target_quality": 30, "mode_recipe_or_phase": 480, "previous_target_quality_or_nonfinite": 30} は重複加算しない。
全20no_candidate_in_window/candidate0/causalfalse/matchednull/delaynull。delaycount0/minmaxmeanmedian原null、補完0。全20対象窓maxstreak1、19窓は7全利用可/phase不能0、cycle09 sensorだけ3利用可4quality不能。欠測1窓だけで全20未検出を説明しない。固定persistence2不成立を保持。
clean_rate 1/3365原value 8.558692421991084、effective 3255秒/rate 8.847926267281107、burden 1/20原value 5.0。率・burdenを単純確率へしない。唯一clean source conveyor-01.motor_temperatureのequipment/source/support原対応を-save/episode-summaryへ保存。

## 選択原target窓

### cycle0 machine

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7237|True|21.85564691890034|1|None|
|7238|True|0.44566418013511394|0|None|
|7239|True|0.3599777800257367|0|None|
|7240|True|22.60970305645728|1|None|
|7241|True|0.44756217146194677|0|None|
|7242|True|1.5526913464028833|0|None|
|7243|True|1.4112119095817632|0|None|

### cycle0 sensor

|sample|available|score|streak|理由|
|---|---|---|---|---|
|7244|True|148.4267685947247|1|None|
|7245|True|0.09759336452919463|0|None|
|7246|True|0.75908529322452|0|None|
|7247|True|149.07045212524997|1|None|
|7248|True|0.9665094929755109|0|None|
|7249|True|0.9924514452630849|0|None|
|7250|True|0.7471635084224448|0|None|

### cycle9 machine

|sample|available|score|streak|理由|
|---|---|---|---|---|
|8857|True|22.634772358565883|1|None|
|8858|True|0.6774800958163559|0|None|
|8859|True|0.3075853111079068|0|None|
|8860|True|22.791079852627895|1|None|
|8861|True|0.1446111225103921|0|None|
|8862|True|0.6490655839942092|0|None|
|8863|True|1.0890674233375957|0|None|

### cycle9 sensor

|sample|available|score|streak|理由|
|---|---|---|---|---|
|8864|True|148.4980207571637|1|None|
|8865|False|None|0|current_target_quality|
|8866|False|None|0|current_target_quality|
|8867|False|None|0|current_target_quality|
|8868|False|None|0|previous_target_quality_or_nonfinite|
|8869|True|0.4299734676035973|0|None|
|8870|True|0.1664128886363712|0|None|

cycle09温度8864score148.4980207571637/streak1→8865–67current quality不能→8868previous quality不能/reset→8869/70原score<4/streak0。persistence2未成立/candidate0/null delay。全原20event/incident/target窓・520不能・30non-ok・episodesを-analysis、選択窓/唯一clean episode-supportを-save保存。実入力対応・保存・状態分類の不具合は観測なし。

## 同seed/layout1・3候補×2条件

|条件|候補|machine|sensor|precision|clean|available|source / equipment|delaycount / median|
|---|---|---|---|---|---|---|---|---|
|core|c0-diff-control|0/10|0/10|0/1|1|13920|1 / 1|0 / None|
|core|c1-phase-level|10/10|10/10|20/20|0|13920|30 / 20|20 / 1.0|
|core|c2-phase-conditional|10/10|10/10|20/20|0|13920|59 / 20|20 / 1.0|
|quality-stress|c0-diff-control|0/10|0/10|0/1|1|13880|1 / 1|0 / None|
|quality-stress|c1-phase-level|10/10|9/10|19/19|0|13880|29 / 19|19 / 1.0|
|quality-stress|c2-phase-conditional|10/10|9/10|19/19|0|13760|56 / 19|19 / 1.0|

同stratum内3候補のinput10は完全一致。coreとqualityは別入力で共通3pins {"dataset-manifest.json": false, "event-ledger.jsonl": false, "events.jsonl": false, "fingerprint.json": false, "generator-config.json": false, "observations.jsonl": false, "origins.json": true, "quality-mask.jsonl": false, "split-manifest.json": true, "targets.json": true}。旧5cell再計算0/source16candidatecompiled一致。C0両条件全20未検出/clean1、C1C2 core検出20/quality検出19/clean0。C2quality peer不能120増を記録し、同指標でも全score/sourceepisode一致・候補採択へしない。
一次差分とpersistence2、3観測[end exclusive]の定常加算成分が内部差分で相殺される既存C0設計解釈を保持。今回の原maxstreak1との整合を記述し、新しい式監査・正常対照再compute・閾値/GT変更0。機械異常の乗算overlayを単純加算toyと同一視しない。勝者・正式採択0。

## 保存済みC0quality比較

|seed|layout|machine|sensor|precision|clean|
|---|---|---|---|---|---|
|2486912926863618161|0|0/10|0/10|0/3|3|
|2486912926863618161|1|0/10|0/10|0/3|2|
|2486912926863618161|2|0/10|0/10|0/3|3|
|2486912926863618161|3|0/10|0/10|0/3|3|
|2486912926863618161|4|0/10|0/10|0/3|3|
|2486912926863618161|5|0/10|0/10|0/3|3|
|2486912926863618161|6|0/10|0/10|0/3|3|
|2486912926863618161|7|0/10|0/10|0/3|3|
|2486912926863618161|8|0/10|0/10|0/3|3|
|2486912926863618161|9|0/10|0/10|0/3|3|
|2486912926863618161|10|0/10|0/10|0/3|3|
|2486912926863618161|11|0/10|1/10|1/3|2|
|7466813550306735603|0|0/10|0/10|0/1|1|
|7466813550306735603|1|0/10|0/10|0/1|1|

14C0quality保存manifest指標比較、旧モデル再計算0。第1seed全72＋第2seed layout0/1各6＝84boardcells/実使用seed2。84独立datasetではない。bootstrap/統計CI/勝者/採択0。

## 証拠・次工程・正式状態

- records/analysis/save/final: artifacts/representative-seed2-layout1-quality-c0-20261012-*。最終-final/post-save/root-closed優先。DATA artifacts/representative-anomaly-evaluation/dev-seed7466813550306735603-layout1-quality-c0-20261012 / {"bytes": 27380184, "files": 19, "manifest_pin": {"bytes": 2235, "sha256": "d3c7a1f3e451f3a5655710ff0db5c053008e038e8f4127567983d0b514b5de6e"}}。
- 旧416root/386helper/22failed364passed/missingexecution1保持。直前C2quality final KeyErrorのfailed/root/原scriptを保持し、元continuation最新postを継承。閉鎖・外部固定root追記整理0/fullstdio/native回収claim0。
- EvidenceStore16MiB512files/part256KiB/失敗予備2MiB16files/閉鎖512KiB4files、script・失敗・閉鎖を含む全write preflight。実行900秒2GiBoutput1GiBsingle32MiBfiles32/Git累積30秒16entry512KiBstdout1MiBstderr128KiB/nativeprotocol維持。checkpoint≠blocking中断/fullruntime/global/allwriter容量証明。
- prepare_result_index実使用/report-handoff-index3docsを同種合成dev結果・PC内path継続送信承認内で一回[skip ci] commit/push。原Git/HEAD-upstream-lsremote-clean/docpins-save/-final。追加承認質問・bypass0。
- 次unit同第2seed/layout2 core C0 c0-diff-control、新ID dev-seed7466813550306735603-layout2-core-c0-20261012。新chunk014manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\014\attempt-0001\result\payload\manifest.json / {"bytes": 75700, "sha256": "13a1f0848235ab785ddc31036c819927a40d5a62e7ff55adb91afe465275998a"}からidentity/input10 metadataだけ選択。次観測本文未読/次model未開始。元生成C0/次評価C0別field、新独立seedではない。
- ACTIVE/automation詳細転記0。CI381385/4130保持/querydownloadverifiertests0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了。create_native早期拒否/全7役reader禁止/caps-unknown原owner保持/追加agent禁止。未完了formal/nativeをdev開始条件へ戻さない。Sol容量・人停止は原保全後PAUSED、重複再試行なし。
