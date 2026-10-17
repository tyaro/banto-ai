# v0.3 dev layout8 C2 core実評価とcore3候補比較

2026-10-12 JST。保存済みdev coreを既存CLI C2で1cell fresh評価。CLI exit0/complete・1cell success。機械10/10・sensor10/10・precision20/20・clean誤警報0。同入力のcore3候補比較を完成し、C0の未検出・原状態を保持する。合成devの結果を候補採択・正式受入へ読み替えない。

## 入力と実行の対応

- run ID dev-layout8-core-c2-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-08-core。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\008\attempt-0001\result\payload\manifest.json、pin {"bytes": 75698, "sha256": "c4dfa23be3bca2f563e587f4f83a33e20f5304f9bd518b791dcb6cc7b74b06b4"}。
- seed2486912926863618161/layout8/core/dev。元生成C0と実評価C2は別field。
- input10 pinsは保存C0/C1 coreと一致。照合→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics。元payload書込み・新dataset生成・replay・追加agent0。
- actual checkout da16cb2cb4913a5295b93b694246f4372048a496、計算source661b27511826fcc87cb4a02930f276afbb8f95d9から不変。declared16/candidate config/compiled config一致はfull loaded runtime/native認証ではない。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}。
- elapsed 75.7227242999943秒、OS sampled peak private 207241216 bytes。
- 48 calibrated/fit各600/calibration各290/C2state48/14400scores。固定C2 threshold6/persistence2、GT/matching/config/science変更0。
- input observations pin {"bytes": 9600600, "sha256": "21d68d9431838dc336794dbcc1832d1d7aedf49999cb0886f78839dbd9371ef2"}、configuration pin {"bytes": 5508, "sha256": "a6892030768b3e6e53eda8dd0ef85b9e662e203d7730cc00141a64701edd395f"}、evaluation pin {"bytes": 24750882, "sha256": "8532471e3dd93f16d965c370bd82276743fc7677494ce7212e43f0f9319fc163"}。

## 原指標

| 指標 | 原値 |
| --- | --- |
| machine recall | 10/10 |
| sensor recall | 10/10 |
| precision | 20/20 |
| clean_rate | 0/3365、原value0.0 |
| effective clean | effective3255秒、原value0.0 |
| false_alert_burden | 0/20、原value0.0 |
| delay | causal-detected-only count20/min1/max2/平均1.5/中央値1.5秒 |
| availability | 13920 available / 480 unavailable |

source40/equipment20/events40/incidents20。全20 processed/candidate_count1/causal_detected true、原matched target sourceを保持。未対応equipment0とclean0を別指標で保持。clean_rate/burdenの原尺度を単純確率へ換算しない。未検出0・遅延補完0。

## phase窓と原target onset

機械10件はconveyor-01.conveyor_speed、開始7260+180*k(k0–9)がphase不能/null-thresholdfalse/streak0。各窓6行利用可・1行phase不能。sensor10件はconveyor-01.motor_temperature、開始7267+180*kで各窓7行利用可・phase不能0。全20対象sourceのonset時support2を保存。machine onsetは開始+2000msが10件、sensor+1000msが10件。

| cycle00 class | sample | score | streak | available | exclusion |
| --- | --- | --- | --- | --- | --- |
| machine | 7260 | None | 0 | False | mode_recipe_or_phase |
| machine | 7261 | 106.21717122400052 | 1 | True | None |
| machine | 7262 | 105.13130317637201 | 2 | True | None |
| machine | 7263 | 0.6675833727916541 | 0 | True | None |
| machine | 7264 | 1.5571339926393934 | 0 | True | None |
| machine | 7265 | 1.0602350796666926 | 0 | True | None |
| machine | 7266 | 1.018832207295786 | 0 | True | None |
| sensor | 7267 | 128.0545187209908 | 1 | True | None |
| sensor | 7268 | 128.7820943762579 | 2 | True | None |
| sensor | 7269 | 129.33925954358838 | 3 | True | None |
| sensor | 7270 | 0.7902045671058465 | 0 | True | None |
| sensor | 7271 | 0.8461171094411511 | 0 | True | None |
| sensor | 7272 | 1.5328194385637701 | 0 | True | None |
| sensor | 7273 | 1.2516002447920376 | 0 | True | None |

機械7261→7262とsensor7267→7268の連続超過で対象source成立。sensor7269のstreak3を原onset時support2へ足さない。selected source full_target/support、equipment source membership/matched_event_id、incident.selected_source_episode_idを照合。18000観測行とmaskの対応/欠測0を確認し、不能480行は全mode_recipe_or_phase・score/residual null・threshold_exceeded false。全20 event/incident/target-source-equipment、四target窓、全episodes、不能480 scoreを保存。入力対応・保存・状態分類の実経路不具合は観測していない。

## C1とのsource構成差

C2 source40はspeed10/temperature10/vibration20。machine10のmatched equipmentにspeed+vibration、sensor10にもtemperature+vibrationが所属する。cycle00 sensorのequipment onset7268はtemperature sourceと同onsetのvibration sourceを含み、incidentの対象はtemperatureである。全sensor equipment10件の原membershipを照合。

保存C1 source counts metadataはspeed10/temperature10/vibration10、合計30。C2の追加10vibration sourceを追加equipment誤警報10件へしない。equipment20/未対応0/clean0/precision20/20を別に保持。C1/C2の検出・delay・availability集計が一致してもscore/source構成/result bytesは別であり、数値同一や再計算一致を主張しない。

## core3候補と過去C2 coreの比較

同input10の保存C0/C1と過去8 layouts C2 coreをmanifest/configだけ比較。今回を加えて11比較セル、C2 coreは9 layouts。declared16/candidate config/compiled config一致、同layout8input10一致、別layout原pin差を保持。旧result本文再展開・旧モデル再compute0。

| layout | 候補 | machine | sensor | precision | clean件数 | available |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | C2 | 4/10 | 10/10 | 14/20 | 0 | 13920 |
| 1 | C2 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 2 | C2 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 3 | C2 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 4 | C2 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 5 | C2 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 6 | C2 | 0/10 | 10/10 | 10/20 | 0 | 13920 |
| 7 | C2 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 8 | C0 | 0/10 | 0/10 | 0/3 | 3 | 13920 |
| 8 | C1 | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| 8 | C2 | 10/10 | 10/10 | 20/20 | 0 | 13920 |

layout8 core3候補比較完成。C0の機械0/sensor0/precision0/3/clean3/delay nullを保持し、C1/C2の成功へ書き換えない。旧50boardに今回1セルを加えて51完了セル。1つの合成dev seedのlayout差であり9独立seed/51独立datasetではない。layout8 quality3候補は未実施。原failed runと明示replayをboardへ混ぜず保持。bootstrap/統計CI・勝者・採択0。

## 原保存と検証記録

- model: artifacts/representative-layout8-core-c2-20261012-records/root-closed.json。
- analysis/extract: artifacts/representative-layout8-core-c2-20261012-analysis/root-closed.json。
- DATA: artifacts/representative-anomaly-evaluation/dev-layout8-core-c2-20261012/root-closed.json、{"bytes": 37792235, "files": 19, "manifest_pin": {"bytes": 2225, "sha256": "517f9421c5fbcac4400cb92ec7b76f7443b9399f9996adef97e4f55116c5c28b"}}。
- docs/Git: artifacts/representative-layout8-core-c2-20261012-save/root-closed.json、git-summary/target-onset-summary/next-dev-selection/source-builder-failure labels。
- 最終保存: artifacts/representative-layout8-core-c2-20261012-final/root-closed.json、post-save label。

EvidenceStoreでselected-windows 1734927B/7parts、unavailable-scores 816438B/4parts、analysis 361210B/2partsを自動分割。新検証root16MiB/512files、part256KiB、失敗reserve2MiB/16files（内閉鎖512KiB/4files）。 [保存方針](../anomaly/execution/verification-records.md) はrecord_integrityとrecorded_statusを区別。

文書source変換の索引見出し対象不一致1件はfunctions.exec内/nested tools・process・tracked mutation・Git helper開始0。原selected errorを保存し、元builderのFS source/full process logs/creation identityはNoneで補わない。新helper/model失敗へ追加せず過去failed16/missing original execution1を保持。CLI rawはhelper全process stdioではない。full creation/start_token/CIM照合、PID単独/EOF/closedからnative回収を補わない。閉鎖/外部固定root追記・原raw整理移動削除0。

同種合成dev結果・ユーザー名PC内input pathを同 https://github.com/tyaro/banto-ai.git へ送信する継続承認内でreport/handoff/index3を一回[skip ci] commit/push。原返値・HEAD-upstream-remote-clean/docpinsはGit記録。

## 次工程と正式gate

次は同chunk008/seed2486912926863618161/layout8/quality-stress、dataset anomaly-v03-dev-seed-2486912926863618161-layout-08-quality-stress、C1 c1-phase-level、新ID dev-layout8-quality-c1-20261012へ1cell実評価。元manifest c4df/input10metadata選択のみ、次quality観測本文未読/model未実行。元生成C0/次評価C1別field、元payload保持/生成0。

評価900秒/2GiB/output1GiB/single32MiB/files32、Git累積30秒/batch16entry512KiB/stdout1MiB/stderr128KiB、固定protocol/native契約は不変。checkpointはblocking中断/full loaded runtime/native/global容量証明ではない。ACTIVE/automation結果・PC path転記0。CI381385/code661の4130success保存、新CIquery/download/verifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了/create_native早期拒否/全7役reader禁止/追加agent禁止。Sol容量/人停止では原保全後PAUSED・重複再試行0。
