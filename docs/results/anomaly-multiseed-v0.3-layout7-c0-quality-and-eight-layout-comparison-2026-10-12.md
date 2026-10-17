# v0.3 dev layout7 C0 quality-stressと8 layouts比較

2026-10-12 JST。保存済みquality-stressを既存CLI C0で1cell fresh評価し、同じseedの8 layouts × 2条件 × 3候補の48セル比較を完成した。今回の機械検出0/10・sensor検出0/10・precision0/3・clean誤警報3件を原値で保持する。処理完了を性能合格・候補採択・正式受入へ読み替えない。

## 入力と実行の対応

- run ID dev-layout7-quality-c0-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-07-quality-stress。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\007\attempt-0001\result\payload\manifest.json、pin {"bytes": 75699, "sha256": "0963abc39d429bc6322694bf57f111ce12b0ce5c5a9009e177812cb3989dcaef"}。
- seed2486912926863618161/layout7/quality-stress/dev。元生成候補C0と実評価候補C0は別field。
- input10 pinsは保存C1/C2 qualityと一致。照合→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metricsを保存。同coreとの原pin差を保持。
- 元payload書込み・新dataset生成・replay・追加agent0。
- actual checkout c989b412a3d84c1f8f99e668609763f03ecf90a4、計算source661b27511826fcc87cb4a02930f276afbb8f95d9から不変。declared16/candidate config/compiled config一致はfull loaded runtime/native認証ではない。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}。
- elapsed 15.628475499921478秒、OS sampled peak private 147701760 bytes。
- 48 calibrated/fit各0/calibration各290/14400scores。固定C0 threshold4/persistence2、GT/matching/config/science変更0。

## 今回の原指標

| 指標 | 原値 |
| --- | --- |
| machine recall | 0/10 |
| sensor recall | 0/10 |
| precision | 0/3 |
| clean_rate | 3/3365、原value25.676077265973255 |
| effective clean | effective3255秒、原value26.543778801843317 |
| false_alert_burden | 3/20、原value15.0 |
| delay | causal-detected-only count0、min/max/mean/median null |
| availability | 13880 available / 520 unavailable |

source3/equipment3/events40/incidents20。全未対応equipment3とclean3は別指標として保持。全20 incidentはprocessed、candidate_count0/no_candidate_in_window/causal_detected false/matched null/delay null。処理状態と検出結果を区別する。clean_rate/burdenの原尺度を単純確率へ換算しない。

## 不成立の対象窓

機械10件はconveyor-01.conveyor_speed。各窓7行利用可能/phase不能0、最大streak1。窓内最大scoreは51.90802420682417–53.507638645573905で閾値4を超えるが連続2回にならない。cycle00の7251 score51.131982601457715/streak1→7252 .4735015667198125/0、7254 score53.00939066172789/1→7255 .6132282878104693/0。固定persistence2で対象source episodeが成立しない。

sensor先行9件はconveyor-01.motor_temperature。開始7230+180*k(k0–8)はphase不能、各6行利用可能/最大streak1。cycle00は7230 null/0→7231 score3.724346289023876/0→7232 3.0280868700292842/0→7233 score191.43560585329374/1→7234 1.9811650997101447/0。phaseと欠測を区別し、欠測1件だけで全20 missを説明しない。

sensor cycle09の8850 phase不能→8851–8853 current欠測→8854 previous欠測は全score/residual null/thresholdfalse/streak0。8855 score1.3552407623269442/0、8856 score1.235410623285759/0。対象sourceなし/candidate0/delay null。別候補やcoreのscoreで補完しない。全20 event/incident、四target窓、全episodes、欠測30観測+mask、不能520 scoreを保存。入力対応・保存・状態分類の実経路不具合は観測していない。

## 欠測と利用可能性

18000観測行とmaskの対応を照合、欠測30行。primaryはphase480/current quality30/previous quality10で520行。非排他的tagsはphase480/current30/current nonfinite30/previous30で重複を合算しない。phase品質重複0。全不能score/residual null・threshold_exceeded false。C0 core13920→quality13880の利用可能減40を原行分類で保持。

## 8 layouts × 2条件 × 3候補の保存結果

既存47セルのboardを保存metadataから継承し、今回1セルを加えて48セル。旧モデル再compute・replay0。今回と過去7 C0 quality・同core C0・同quality C1/C2の11セルはmanifest/configの対応を照合。declared16/candidate config/compiled config一致、同quality input10 pins一致、別layout/stratumの原pin差を保存。残りのboardは既存保存の対応証拠を継承した。

| layout | 条件 | 候補 | machine | sensor | precision | clean件数 | available |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | core | C0 | 0/10 | 0/10 | 0/3 | 3 | 13920 |
| 0 | core | C1 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 0 | core | C2 | 4/10 | 10/10 | 14/20 | 0 | 13920 |
| 0 | quality-stress | C0 | 0/10 | 0/10 | 0/3 | 3 | 13880 |
| 0 | quality-stress | C1 | 10/10 | 9/10 | 19/19 | 0 | 13880 |
| 0 | quality-stress | C2 | 4/10 | 9/10 | 13/19 | 0 | 13760 |
| 1 | core | C0 | 0/10 | 0/10 | 0/3 | 2 | 13920 |
| 1 | core | C1 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 1 | core | C2 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 1 | quality-stress | C0 | 0/10 | 0/10 | 0/3 | 2 | 13880 |
| 1 | quality-stress | C1 | 10/10 | 9/10 | 19/19 | 0 | 13880 |
| 1 | quality-stress | C2 | 10/10 | 9/10 | 19/19 | 0 | 13760 |
| 2 | core | C0 | 0/10 | 0/10 | 0/3 | 3 | 13920 |
| 2 | core | C1 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 2 | core | C2 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 2 | quality-stress | C0 | 0/10 | 0/10 | 0/3 | 3 | 13889 |
| 2 | quality-stress | C1 | 10/10 | 9/10 | 19/19 | 0 | 13889 |
| 2 | quality-stress | C2 | 10/10 | 9/10 | 19/19 | 0 | 13796 |
| 3 | core | C0 | 0/10 | 0/10 | 0/3 | 3 | 13920 |
| 3 | core | C1 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 3 | core | C2 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 3 | quality-stress | C0 | 0/10 | 0/10 | 0/3 | 3 | 13880 |
| 3 | quality-stress | C1 | 10/10 | 9/10 | 19/19 | 0 | 13880 |
| 3 | quality-stress | C2 | 10/10 | 9/10 | 19/19 | 0 | 13760 |
| 4 | core | C0 | 0/10 | 0/10 | 0/3 | 3 | 13920 |
| 4 | core | C1 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 4 | core | C2 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 4 | quality-stress | C0 | 0/10 | 0/10 | 0/3 | 3 | 13880 |
| 4 | quality-stress | C1 | 10/10 | 9/10 | 19/19 | 0 | 13880 |
| 4 | quality-stress | C2 | 10/10 | 9/10 | 19/19 | 0 | 13760 |
| 5 | core | C0 | 0/10 | 0/10 | 0/3 | 3 | 13920 |
| 5 | core | C1 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 5 | core | C2 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 5 | quality-stress | C0 | 0/10 | 0/10 | 0/3 | 3 | 13880 |
| 5 | quality-stress | C1 | 10/10 | 9/10 | 19/19 | 0 | 13880 |
| 5 | quality-stress | C2 | 10/10 | 9/10 | 19/19 | 0 | 13760 |
| 6 | core | C0 | 0/10 | 0/10 | 0/3 | 3 | 13920 |
| 6 | core | C1 | 0/10 | 10/10 | 10/20 | 0 | 13920 |
| 6 | core | C2 | 0/10 | 10/10 | 10/20 | 0 | 13920 |
| 6 | quality-stress | C0 | 0/10 | 0/10 | 0/3 | 3 | 13889 |
| 6 | quality-stress | C1 | 0/10 | 9/10 | 9/19 | 0 | 13889 |
| 6 | quality-stress | C2 | 0/10 | 9/10 | 9/19 | 0 | 13796 |
| 7 | core | C0 | 0/10 | 0/10 | 0/3 | 3 | 13920 |
| 7 | core | C1 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 7 | core | C2 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 7 | quality-stress | C0 | 0/10 | 0/10 | 0/3 | 3 | 13880 |
| 7 | quality-stress | C1 | 10/10 | 9/10 | 19/19 | 0 | 13880 |
| 7 | quality-stress | C2 | 10/10 | 9/10 | 19/19 | 0 | 13760 |

48セルは1つの合成dev seedの8 layouts・2strata・3候補であり、48独立dataset/seedではない。layout7はC1/C2 coreがmachine10/sensor10、qualityがmachine10/sensor9、C0は両条件machine0/sensor0/clean3。同quality C1/C2の集計が一致してもavailability/score/原bytesは別。bootstrap/統計CI・勝者・候補採択0。過去のfailed runや明示replayを比較boardへ混ぜず、原状態を保持。

## 原保存と検証記録

- model: artifacts/representative-layout7-quality-c0-20261012-records/root-closed.json。
- analysis/extract: artifacts/representative-layout7-quality-c0-20261012-analysis/root-closed.json。
- DATA: artifacts/representative-anomaly-evaluation/dev-layout7-quality-c0-20261012/root-closed.json、{"bytes": 27384378, "files": 19, "manifest_pin": {"bytes": 2228, "sha256": "c832fbee57b4ba82e65cf63e2717c59d7db857002a560f455335eb6d0fd6e47d"}}。
- docs/Git: artifacts/representative-layout7-quality-c0-20261012-save/root-closed.json、git-summary/target-onset-summary/next-dev-selection labels。
- 最終保存: artifacts/representative-layout7-quality-c0-20261012-final/root-closed.json、post-save label。

共通EvidenceStoreでselected-windows 976606B/4parts、unavailable-scores 520169B/2parts、analysis 345562B/2partsを自動分割。新検証root16MiB/512files、part256KiB、失敗reserve2MiB/16files（内閉鎖512KiB/4files）。 [保存方針](../anomaly/execution/verification-records.md) はrecord_integrityとrecorded_statusを区別。実行側と固定protocol/native上限は不変。

今回helper/model失敗0、全過去failed16/missing original execution1保持。CLI redirect rawはhelper全process stdioではない。full creation/start_tokenとCIM照合、PID単独/EOF/closedからnative回収を補わない。閉鎖/外部固定root追記・原raw整理移動削除0。

同種合成dev結果・ユーザー名PC内input path・同 https://github.com/tyaro/banto-ai.git への継続承認範囲で、report/handoff/results index3を一回[skip ci] commit/push。原返値/HEAD-upstream-remote-clean/docpinsはGit記録を参照。

## 次工程と正式gate

未読のchunk008 manifest metadataだけを確認した。次は同seed/layout8/core、dataset anomaly-v03-dev-seed-2486912926863618161-layout-08-core、C0 c0-diff-control、新ID dev-layout8-core-c0-20261012へ1cell実評価。元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\008\attempt-0001\result\payload\manifest.json、pin {"bytes": 75698, "sha256": "c4dfa23be3bca2f563e587f4f83a33e20f5304f9bd518b791dcb6cc7b74b06b4"}、10input metadata保持。新独立seedではない。next観測本文未読/model未実行、元payload保持・新dataset生成0。

評価900秒/2GiB/output1GiB/single32MiB/files32、Git累積30秒/batch16entry512KiB/stdout1MiB/stderr128KiB、固定protocol/native契約は不変。checkpointはblocking中断/full loaded runtime/native/global容量証明ではない。ACTIVE/automation設定へ結果・PC path転記0。CI381385/code661の4130success保存、新CIquery/download/verifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了/create_native早期拒否/全7役reader禁止/追加agent禁止。Sol容量/人停止では原保全後PAUSED・重複再試行0。
