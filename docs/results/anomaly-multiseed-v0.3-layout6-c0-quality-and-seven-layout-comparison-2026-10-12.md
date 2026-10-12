# v0.3 dev layout6 C0 quality実評価と7 layoutsの保存比較

2026-10-12 JST。処理はcomplete・1cell successで終了した。機械・センサー検出はともに0/10、clean区間の誤警報は3件。処理成功を性能合格・候補採択・正式受入へ読み替えない。

## 実行条件と入力対応

- ID: dev-layout6-quality-c0-20261012。既存CLI tools/evaluator/run_representative_anomaly.py による1候補のfresh compute_evaluation。
- 元入力manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\006\attempt-0001\result\payload\manifest.json。
- 元manifest pin: {"bytes": 75698, "sha256": "542248c4b9e6227749adce8d37c1769580ba0cb7426ebe12321ec192a775846d"}。
- seed2486912926863618161/layout6/quality-stress/dev、dataset anomaly-v03-dev-seed-2486912926863618161-layout-06-quality-stress。元生成C0と今回実評価C0は別fieldを保持。
- 10入力fileをpin照合して新snapshotへ保存。元payload書込み、新dataset生成、replay、追加agentは0。
- checkout 2ac7c45b73aa7b3e12a98a1cca069b7bcd81f972。計算sourceは661b27511826fcc87cb4a02930f276afbb8f95d9から不変。宣言16calculator source、candidate/compiled configが全42セルの保存版と一致。これをfull loaded runtime/native認証へ補わない。
- 実runtime: {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}。
- elapsed 17.202453500009142秒、OS sampled peak private 148463616 bytes。
- 48 calibrated profiles、fit各0/calibration各290、14400 scores。固定C0閾値4・persistence2、GT/matching/config/science変更0。

## 指標と利用不能行

| 指標 | 原結果 |
| --- | --- |
| machine recall | 0/10 |
| sensor recall | 0/10 |
| precision | 0/3 |
| clean | 3 / scheduled3365秒、原value 25.676077265973255 |
| effective clean | effective3254秒、原value 26.551936078672405 |
| false alert burden | 3/20、原value15.0 |
| delay | 検出count0、全20 incidentのdelay null |
| availability | 13889 available / 511 unavailable |

clean_rateとburdenは原尺度を保持し、単純確率へ変換しない。source3/equipment3、events40/incidents20。3 equipmentはすべて未対応、clean文脈3と未対応3を別に保存した。

primary reasonはphase471/current quality30/previous quality10。非排他的tagsはphase480/current quality30/current nonfinite30/previous quality30であり、重複を足し合わせない。入力観測とquality-maskの18000行が対応し、欠測30行を原観測付きで保存。phaseとcurrent qualityの重複9行（7200+180*k、k0–8）により、480+40−9=511。不能行はscore/residual null、threshold_exceeded false。

## 未検出の原経路

全20 incidentはno_candidate_in_window、candidate_count0、causal_detected false、matched null、delay null。全対象窓にphase利用不能はない。

機械10件の対象conveyor-01.conveyor_speedは各7行が利用可能、最大scoreは3.2024364338284195で固定閾値4未満、streakは0。センサー10件の対象温度は各窓の最大streak1で、固定連続2点を満たさない。

欠測のないcycle00 sensorでもsample7221 score178.70503443570314/streak1→7222 score0.18445529743711783/streak0、7224 score176.46595855974496/streak1→7225 score0.03460551683975721/streak0。欠測だけで全20 missを説明しない。

cycle09 sensorは8841 score178.32500738826238/streak1→8842–8844 current欠測reset、8845 previous欠測reset→8846 score0.7410783103503487/streak0、8847 score1.3558848359969382/streak0。8850のphase利用不能は対象窓外。原20 event/incident、全20窓の四target scores、全source/equipment episodes、欠測30行、不能511行と重複9行を保持した。入力対応・評価保存・状態分類の実経路不具合は観測していない。

## 保存済み42セルの比較

同じ合成dev seedの7 layouts × core/quality-stress × 3候補。42独立dataset/seedではない。今回fresh実評価はC0 qualityの1セルだけ。既存41セルはmanifest/configの保存指標だけを読む。明示replayは比較セルへ数えず、過去failed runはfailedのまま除外。bootstrap、統計CI、勝者、採択は0。

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

layout6 quality C1/C2はともにmachine0/10・sensor9/10・precision9/19・clean0。C0/C1のavailability13889/511に対しC2は13796/604であり、peer依存差も原尺度で保持。layoutや条件による挙動差を新seedの一般化性能へ補わない。

## 検証記録・失敗の保全

今回の補助記録は [新共通APIの方針](../anomaly/execution/verification-records.md) に従う。新rootのみ16MiB/512files、part256KiB、失敗用2MiB/16files（内終了manifest512KiB/4files）。対象窓972080Bは4parts、利用不能行511226Bは2partsとして順序・part/stream SHA・完全性を保持。旧rootへ追記しない。

比較補助処理の初回は過去failed runにidentityを要求してKeyError。元source・例外・trace・終了identityをfailed rootへ閉鎖保存し、元script/modelを再実行しなかった。別continuationが非complete runを除外する箇所だけを限定訂正し、未完了分析を完成。過去failed runのmanifest/failureも別labelに原保存した。この補助失敗をモデル/CI/native/Sol容量failureへ読み替えない。

- model: artifacts/representative-layout6-quality-c0-20261012-records/root-closed.json
- 原analysis failure: artifacts/representative-layout6-quality-c0-20261012-analysis-records/root-closed.json
- analysis/原extract: artifacts/representative-layout6-quality-c0-20261012-analysis-continuation/root-closed.json
- DATA: artifacts/representative-anomaly-evaluation/dev-layout6-quality-c0-20261012/root-closed.json、{"bytes": 27383988, "files": 19, "manifest_pin": {"bytes": 2228, "sha256": "c13f047441108742a573a9cb74a9a2c4b288b11d16062177bebfacdd6dddd21a"}}。
- docs/Git: artifacts/representative-layout6-quality-c0-20261012-save/root-closed.json、git-summary label。
- 最終metadata: artifacts/representative-layout6-quality-c0-20261012-final/root-closed.json、post-save label。

新formatは tools/check_verification_record.py で読取可能。record_integrity成功とrecorded_status、モデル性能を別に扱う。redirectしたCLI rawはhelper全process stdioではない。原helperのfull creation/start_token照合、CIM同original不在を保存し、PID単独/native回収claimへしない。原missing execution record1を復元したことにしない。

## 次工程と正式gate

次は保存済みchunk007/layout7/coreをC0で新ID dev-layout7-core-c0-20261012へ1cell実評価。今回選択はmanifest/10input pin metadataだけで、次の観測本文とmodelは未着手。元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\007\attempt-0001\result\payload\manifest.json、pin {"bytes": 75699, "sha256": "0963abc39d429bc6322694bf57f111ce12b0ce5c5a9009e177812cb3989dcaef"}。同seed別layout、独立seedではない。

実行側900秒/2GiB/output1GiB/single32MiB/files32、Git累積30秒/16entry・512KiB/stdout1MiB/stderr128KiBと固定protocol/native契約は不変。engineering checkpointはblocking中断・full runtime/native/global容量の証明ではない。

同種合成dev報告とユーザー名を含むPC内入力pathを同GitHub送信先へ送る継続承認を保持し、今回3文書を一回[skip ci] commit/pushする。原返値・HEAD/upstream/remote/clean/docpinはGit記録を参照。

ACTIVE維持、automation設定へ詳細結果やPC pathを転記しない。CI38138556456/code661の4130success保存を継承し、新CI照会/download/verifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読、正式5残件・最終受入未完了、create_native早期拒否/全7役reader禁止/追加agent禁止を維持。Sol容量又は人の停止では原保全後PAUSED、重複再試行なし。
