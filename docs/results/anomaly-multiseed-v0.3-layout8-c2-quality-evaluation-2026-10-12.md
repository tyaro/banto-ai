# v0.3 dev layout8 C2 quality-stress実評価

2026-10-12 JST。既存CLI C2で保存済みdev quality-stressを1cell fresh評価。exit0/complete・1cell success。機械10/10・sensor9/10・precision19/19・clean誤警報0。未検出1件のcausal_detected false/delay nullを保持し、処理成功を性能合格・採択・正式受入へ補わない。

## 入力と結果の対応

- run dev-layout8-quality-c2-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-08-quality-stress。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\008\attempt-0001\result\payload\manifest.json、pin {"bytes": 75698, "sha256": "c4dfa23be3bca2f563e587f4f83a33e20f5304f9bd518b791dcb6cc7b74b06b4"}。
- seed2486912926863618161/layout8/quality-stress/dev。元生成C0と実評価C2は別field。同quality C1 input10 pins一致、同coreとの原pin差保持。
- pins照合→新snapshot→fresh fit/calibration→profiles/scores/episodes/events/incidents/metrics原保存。元payload書込み/新dataset生成/replay/追加agent0。
- actual checkout c7471bfbe4b8af3704d236b50f7bc6b210517016、計算661b27511826fcc87cb4a02930f276afbb8f95d9から不変。declared16/candidate config/compiled config一致はfull loaded runtime/native認証ではない。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 38.659413000103086秒/privatepeak 209678336B。
- 48 calibrated/fit各600/cal290/C2state48/14400scores、固定threshold6/persistence2。GT/matching/config/science変更0。
- observations {"bytes": 9600604, "sha256": "9f812738c1fd9805d257a10ca30ded867afc56bc4642437914451a34b5a25d61"}、configuration {"bytes": 5518, "sha256": "8c99b99b5830a04631850373d22db654f256529b843b39fead4f675ed717b286"}、evaluation {"bytes": 25191202, "sha256": "716f045bebd3f4defab24841946d27eb0365f2f3d961ccfb76fad4a79cc338b6"}。

## 原指標

| 指標 | 原値 |
| --- | --- |
| machine recall | 10/10 |
| sensor recall | 9/10 |
| precision | 19/19 |
| clean_rate | 0/3365、原value0.0 |
| effective clean | 3255秒、原value0.0 |
| false_alert_burden | 0/20、原value0.0 |
| delay | detected-only19/min1/max2/mean1.5263157894736843/median2.0秒 |
| availability | 13760 available /640 unavailable |

source38/equipment19/events40/incidents20、未対応0/clean0は別保持。未検出1件delay null・補完0。clean_rate/burdenを単純確率にしない。core中央値1.5とquality2秒は検出件数の異なる条件付き集計。

## 温度欠測とpeer波及

18000観測行とmask対応、欠測30。primary phase480/current quality30/previous quality10/peer120、合計640。非排他的tags phase480/peer120/current30/current nonfinite30/previous30を合算しない。phase品質/peer-phase重複0。全不能score/residual null・thresholdfalse。
温度自身current30+previous10に加え、同conveyor-01 current/speed/vibration各40=peer120行。core13920→quality13760の減160、同quality C1の13880→C2の13760の減120を原行分類から照合。peer120を独立欠測120観測/検出失敗120件へしない。

## cycle09 sensor未検出

conveyor-01.motor_temperature/start8887/end8890/window_end8893、processed/candidate0/no_candidate_in_window/causalfalse/matchednull/delaynull。

| sample | score | streak | available | exclusion |
| --- | --- | --- | --- | --- |
| 8887 | 129.20611791394634 | 1 | True | None |
| 8888 | None | 0 | False | current_target_quality |
| 8889 | None | 0 | False | current_target_quality |
| 8890 | None | 0 | False | current_target_quality |
| 8891 | None | 0 | False | previous_target_quality_or_nonfinite |
| 8892 | 1.0033883671119703 | 0 | True | None |
| 8893 | 1.2266865465509507 | 0 | True | None |

8887のscore129.20611791394634/streak1後、8888–8890 current欠測→8891 previous欠測でnull/reset。8892 score1.0033883671119703/0・8893 1.2266865465509507/0。固定persistence2不成立。対象窓phase不能0、別候補/core scoreでnullを補わない。peer3targets8888–8891不能でも機械窓8880–8886は開始phase以外利用可で検出を保持。

## 原19件の対応とsource構成

machine10 speed onset+2000ms、sensor9 temperature+1000ms、原onset時support2。source speed10/temperature9/vibration19。machine equipment speed+vibration10、sensor equipment temperature+vibration9所属を照合。保存C1 quality source29(vibration10)とC2 source38(vibration19)の差保持。追加vibration9を誤警報equipment9にせずequipment19/precision19/19/clean0/未対応0原値保持。C1/C2の検出・delay集計一致とavailability/score/source構成/resultbytesの差を分けて保存。
全20 event/incident・matched target-source-equipment19・四target窓・全episodes・欠測30・不能640/peer120を原保存。processedと検出を区別。実入力保存分類不具合は観測していない。

## 保存候補との比較

同core C2・同quality C1・過去8 layouts quality C2をmanifest/configだけ比較。新評価込み11セル、C2quality9layouts。declared16/candidate config/compiled config一致/同quality10pins一致/別layout-stratum pin差保持。旧result本文再展開・再compute0。

| layout | 条件 | 候補 | machine | sensor | precision | clean件数 | available |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | quality-stress | C2 | 4/10 | 9/10 | 13/19 | 0 | 13760 |
| 1 | quality-stress | C2 | 10/10 | 9/10 | 19/19 | 0 | 13760 |
| 2 | quality-stress | C2 | 10/10 | 9/10 | 19/19 | 0 | 13796 |
| 3 | quality-stress | C2 | 10/10 | 9/10 | 19/19 | 0 | 13760 |
| 4 | quality-stress | C2 | 10/10 | 9/10 | 19/19 | 0 | 13760 |
| 5 | quality-stress | C2 | 10/10 | 9/10 | 19/19 | 0 | 13760 |
| 6 | quality-stress | C2 | 0/10 | 9/10 | 9/19 | 0 | 13796 |
| 7 | quality-stress | C2 | 10/10 | 9/10 | 19/19 | 0 | 13760 |
| 8 | core | C2 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 8 | quality-stress | C1 | 10/10 | 9/10 | 19/19 | 0 | 13880 |
| 8 | quality-stress | C2 | 10/10 | 9/10 | 19/19 | 0 | 13760 |

旧52board＋新1=53完了。同seed1のlayout差であり9独立seed/53独立datasetではない。layout8 C0quality未実施。原failed run/明示replayをboardへ混ぜず保持。bootstrap/統計CI・勝者・採択0。

## 保存と上限

- model: artifacts/representative-layout8-quality-c2-20261012-records/root-closed.json。
- analysis: artifacts/representative-layout8-quality-c2-20261012-analysis/root-closed.json。
- DATA: artifacts/representative-anomaly-evaluation/dev-layout8-quality-c2-20261012/root-closed.json {"bytes": 38239031, "files": 19, "manifest_pin": {"bytes": 2228, "sha256": "5518db4a73a44be04131a83f3bc794ae0040a4095494f78e0b16c3485c3f9c74"}}。
- docs/Git: artifacts/representative-layout8-quality-c2-20261012-save/root-closed.json（git-summary/target-onset-summary/peer-summary/next-dev-selection/source-builder-failure labels）。
- FINAL: artifacts/representative-layout8-quality-c2-20261012-final/root-closed.json（post-save label）。

EvidenceStore自動分割：selected-windows 1768934B/7parts、unavailable-scores 1113686B/5parts、analysis 373067B/2parts。peer120原rows保存。新記録16MiB/512files/part256KiB/失敗reserve2MiB16files（内closure512KiB4files）。 [記録方針](../anomaly/execution/verification-records.md) はintegrityとrecorded_statusを区別。
文書source変換の索引リンク置換不一致1件はnested tools/process/tracked mutation/Git helper開始0。原selected error保存、元builder FSsource/full process logs/creation Noneを補わない。helper/model/CI/native/Sol失敗へ追加せず旧failed16/missing original execution1保持。CLI rawはhelper全stdioではない。full creation/start_tokenとCIM照合/PID単独-native回収claim0。閉鎖/外部固定root追記・原raw整理移動削除0。
同種合成dev結果・ユーザー名PC内input path・同 https://github.com/tyaro/banto-ai.git への継続承認内でreport/handoff/index3を一回[skip ci] commit/push。Git原返値/HEAD-upstream-remote-clean/docpins保持。

## 次unitと正式gate

同保存chunk008/seed2486912926863618161/layout8 quality-stress C0 c0-diff-control、新ID dev-layout8-quality-c0-20261012へ1cell評価。同manifest/input10、本文C1/C2読取済み/次model未実行。元生成C0/次実評価C0別field、元payload保持生成0。
実行900秒2GiB/output1GiB/single32MiB/files32、Git累積30秒/16entry512KiB/stdout1MiBstderr128KiB、固定protocol/native不変。checkpointはblocking中断/full runtime/global容量証明ではない。ACTIVE/automation結果-PC path転記0。CI381385/code661の4130保存・新querydownloadverifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了/create_native早期拒否/7役reader禁止/追加agent禁止。Sol容量/人停止は原保全後PAUSED・重複再試行0。
