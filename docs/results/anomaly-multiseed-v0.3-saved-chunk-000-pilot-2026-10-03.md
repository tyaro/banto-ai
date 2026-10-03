# v0.3 保存済みdev/smoke区間0の要約実適用（2026-10-03）

**保存済み合成dev/smokeの区間0・6評価を、新しい1区間readerで一度だけ読み、現時点の独立profile/score/ledger検算から主・条件別要約を作成した。6評価は外部pin付きの過去監査と一致し、全枠結合は確認済み6/720、未確認714/720を保持した。** これはengineeringの限定確認であり、正式holdout、性能gate、S6ではない。

## 入力と範囲

source HEADは`da0f6770ebb56d0e7cf3db54348cad472bc47bc0`。外部起点は完走保存点8,366bytes/SHA256 `ca976322e0bb9e7b033b94948497a41acc79900668d01edbeebfc3fea8b22c8d`。そのevidenceに記録されたrun rootを明示して照合し、区間0の検証済みattempt1を選んだ。比較元は[全720評価の独立監査](anomaly-multiseed-v0.3-full-connected-audit-2026-09-24.md)の区間0保存報告34,306bytes/SHA256 `fd4342ac5b7054b2d6082ba897d571a291ee97fa98dd689d7118f8b89e31e61d`と、[dev/smoke比較](anomaly-multiseed-v0.3-dev-smoke-comparison-2026-09-24.md)の評価別記録である。過去報告は外部保存点からhashをたどって読んだ。

`read_chunk_summaries(..., chunk_index=0, expected_mode="engineering")`を所有子で1回実行した。対象は保存点/evidence、固定plan、過去audit、2 datasetの入力12file、評価6fileの計22file。元run rootと過去保存点には書き込まず、新しい出力を`artifacts/real-saved-chunk-000-2026-10-03`へ保存した。新producer、追加attempt、検出器評価は0回。

## 確認結果

| 項目 | 結果 |
| --- | --- |
| 新要約 | 6/6 success、151,954bytes/SHA256 `40a5328f863f3018a4906ce049b0f1d104a896ce968ba6536c5b5eb478f5c95d` |
| 元入力との対応 | 区間/attempt、6 identity/outcome、入力と評価file pinが一致。元区間監査の入力bytesは132,760,979 |
| 独立検算の比較 | 各評価のprofile/scoreとledger報告が保存済み区間0監査に完全一致。過去の評価別比較metricsも6/6一致 |
| 主count | 各評価13種類、計78組の整数分子/分母が保存済みledger指標と一致。effective clean seconds、分母0も照合 |
| 条件別要約 | 現行reader内で主/条件別の整合性とfull event-ledger bytes一致を確認 |
| 過去の生成監査との接続 | 外部pin付きの生成監査savepointと区間0報告を読み、plan・旧audit・両datasetの観測/quality mask/event ledger、計8入力pinが今回要約と一致。生成式は今回再計算せず、旧監査の2 dataset/36,000行の結論を同じ入力へ結ぶ |
| 全枠への部分結合 | `partial_summary_binding`、確認済み1/120区間・6/720評価、欠落119区間・未確認714評価、formal加算0 |

- [保存結果](../../artifacts/real-saved-chunk-000-2026-10-03/result.json) 1,749bytes/SHA256 `f561294b2edf6f0042bc04ecb9c45bdfc9c475f160115f3d56a06caca22acab7`
- [6評価の要約](../../artifacts/real-saved-chunk-000-2026-10-03/summary.json)、[過去監査との比較](../../artifacts/real-saved-chunk-000-2026-10-03/comparison.json)、[部分結合](../../artifacts/real-saved-chunk-000-2026-10-03/partial-binding.json)
- [生成監査との入力pin接続](../../artifacts/real-saved-chunk-000-2026-10-03/generation-link.json) 4,111bytes/SHA256 `ba63f07168356713be35b4ff145cc41b8662c0a03a9435c36f7df559e5d685ae`
- [所有process記録](../../artifacts/real-saved-chunk-000-2026-10-03/process-receipt.json)、[資源記録](../../artifacts/real-saved-chunk-000-2026-10-03/resource-budget.json)、[実行補助](../../artifacts/real-saved-chunk-000-2026-10-03/pilot.py)

## 資源・失敗境界

所有子はexit0、PID `19096`の終了・回収を確認し、17.934秒、peak private `159,682,560`bytes、stderr 0。親側は0.25秒間隔で76 sampleを採取し、peak private `48,054,272`bytes、観測中の新directory最大`192,200`bytes、commit最小余裕`27,592,302,592`bytes。120秒/親・子各512MiB、新directory32MiB/256entries、RAM/commit余裕各2GiB、disk余裕5GiBの限定条件内で、monitor終了も確認した。監視はsamplingと協調checkpoint、子は所有processの時間/private上限で停止する方式であり、全工程のhard quotaや正式予算ではない。

開始・終了の実runtimeはWindows 11 Pro 25H2/build26200/UBR9457、CPython3.14.0で一致した。旧正式OS pinのUBR9168を更新または受入した結果ではない。D側のsource HEAD一致は確認したが、全役割source/runtime closureや過去producer processの認証ではない。

## 残る範囲と次の判断

今回の新readerは区間0の保存済み観測からprofile/score/ledgerを検算した。正常生成・overlay・丸めは[別の保存済み全件監査](anomaly-multiseed-v0.3-independent-generation-audit-2026-09-24.md)の範囲であり、今回の入力pinと結んだが再計算しない。旧生成監査だけが使用した`events.jsonl` 2件を、今回readerが読んだ22 fileへ加算しない。接続確認の最初の補助scriptは手元実行でpath分類を誤り、receipt作成前に停止した。この停止は独立した保存receiptを持たない。分類を直してmetadataのみを確認し、元pilot・生payload・既存receiptは再実行・変更していない。残り119区間を読んだ扱いにせず、全120要約が揃うまで`run_pipeline(start_from="summaries")`は使わない。

次は、失敗attempt履歴を持つ区間119を別の限定確認対象にする必要性と、全120区間を新要約経路へ適用する時間・入力読取り・中間保存・停止予算を決める。既存720評価の再実行、正式40 seed、50,000回bootstrap、正式gate、promotionはこのpilotから許可されない。`formal_ready=false`、formal/promotion/S6/trust/execution_authenticated/full closure/analysis_authorized=falseを維持する。
