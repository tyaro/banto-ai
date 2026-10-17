# v0.3 保存済みdev/smoke全区間の要約・報告への実適用（2026-10-03）

**保存済み合成dev/smokeの120区間・720評価をengineeringの新要約readerで確認し、完全結合から記述表・報告書・保存後readerまで完了した。** 既存の評価payloadを読み直して要約を作ったが、新しいproducer評価は0件。正式holdout、50,000 draw、正式gate、S6、候補昇格は実行していない。これは実設備・顧客データの評価ではない。

## 入力と採用した結果

source HEADは`d4d6de6c37b573c740c7c900b5ac679bf2ba87d2`、`src` treeは`d9d5d0d021d9cc3e4616b79d069d382dc9f89a46`。入力は完走保存点8,366bytes/SHA256 `ca976322e0bb9e7b033b94948497a41acc79900668d01edbeebfc3fea8b22c8d`、evidence 2,197,895bytes/SHA256 `18a6749c9a168af3088d9f2729f9ab7a06af45faf7910863f648c6f018268dad`、全予定枠metadata 1,581,421bytes/SHA256 `a829bde9ae98725d0b6b4fd97288e7b846349e9c306694d248a54a85839c776c`を外部pinとして固定した。各区間は登録・最新attempt・入力/evaluation pin・旧監査を照合し、現行readerでprofile/score/ledgerと主・条件別要約を導出した。生成式の再計算は[旧独立生成監査](anomaly-multiseed-v0.3-independent-generation-audit-2026-09-24.md)の範囲に残す。

先行した[区間0](anomaly-multiseed-v0.3-saved-chunk-000-pilot-2026-10-03.md)と[区間119の限定pilot](../../artifacts/real-saved-chunk-119-2026-10-03/result.json)を再利用した。区間119のresultは2,244bytes/SHA256 `3fc326bd20032328a152e36b267dcc6d6484bf7cdd2709f77dbf6a2ce39733ef`で、保存済み失敗attempt1ではなく検証済みattempt2を選択した。残り118区間の成功結果は次の3つの新規attemptから採用し、失敗した子の結果は採用していない。

| 試行 | 新たに採用した区間 | その時点の結合 | 停止・終了 |
| --- | ---: | ---: | --- |
| [attempt-001](../../artifacts/real-saved-summary-batch-2026-10-03/attempt-001/result.json) | 57 | 59/120区間・354/720評価 | 区間56の子が時間上限で停止。親全体予算はpass |
| [attempt-002](../../artifacts/real-saved-summary-resume-2026-10-03/attempt-002/result.json) | 26 | 85/120区間・510/720評価 | 区間82の子が120秒上限で停止。親全体予算はpass |
| [attempt-003](../../artifacts/real-saved-summary-resume3-2026-10-03/attempt-003/result.json) | 35 | **120/120区間・720/720評価** | `verified_complete`、exit0、親全体予算pass |

最終resultは39,604bytes/SHA256 `572fe8141575638a193c4e55f5bed2054a1d377260dbc09bafd2d670a7df5256`。[完全結合](../../artifacts/real-saved-summary-resume3-2026-10-03/attempt-003/complete-binding.json)は86,901bytes/SHA256 `0dbf7b26807803a220eb8c93445a3181027ce47543195fec2a615ea820466a08`、`complete_summary_binding`、欠落0、正式campaign加算0。旧失敗の区間56・82は別rootに保全し、新attemptで成功した同区間だけを結合した。

## 全件の追加照合

[外部pin付きpostcheck](../../artifacts/real-saved-summary-final-postcheck-2026-10-03/postcheck-001/result.json)は、旧59件・次の26件・最後の35件のresult/summary実bytesを全番号で追跡し、完全結合と照合した。後続61件の所有process・資源・pin・比較記録はpostcheckが再読した。旧59件の所有process・資源はattempt-003 runnerが継承時に再認証した記録を受け取る。postcheck resultは2,631bytes/SHA256 `535348b7dcd133304ad9b752ddc78990c1213f3c8aaa906f678fac4c672198e8`、status `verified`、資源pass。再集計した[記述表](../../artifacts/real-saved-summary-final-postcheck-2026-10-03/postcheck-001/tables.json)は5,198,540bytes/SHA256 `72d9a47fa06f7756b5801e5b2e57e62f991496267a4d95f08af58aabf79c4ff7`。

[比較記録](../../artifacts/real-saved-summary-final-postcheck-2026-10-03/postcheck-001/comparison.json)では、保存済み独立監査のseed別90行、role別18行、paired12行・144点、slice108行、選択attempt120件と一致した。主指標の整数分子/分母1,404組も一致し、nullと分母0を保持した。float比較の許容差は絶対・相対とも`1e-12`。このpostcheckは旧独立監査の保存結果との照合であり、集計算術を別実装で再導出するS6や生成監査の再実行ではない。

## engineeringの報告と資源

全120要約と完全結合を外部pinで固定した[request](../../artifacts/real-saved-report-prep-3root-2026-10-03/request.json) 26,757bytes/SHA256 `1cddb58a22d283cd0a3f0a0216260429fe86bc57d1f392e87e160b679a8c729e`から、保存済み報告入口を`start_from=summaries`で1回実行した。[pipeline結果](../../artifacts/real-saved-report-prep-3root-2026-10-03/attempt-001/result.json)は2,877bytes/SHA256 `f2f0d6a8ff112b0c37f52bc3fc64cb2e1c39faaf80403b03076933e1ec52f1d5`、`verified`。記述集計・報告準備・公開を各1回実行し、writer終了後に別readerが4payloadを確認した。公開済みの[Markdown報告](../../artifacts/real-saved-report-prep-3root-2026-10-03/attempt-001/publication/published/payload/report.md)、[全数値JSON](../../artifacts/real-saved-report-prep-3root-2026-10-03/attempt-001/publication/published/payload/report.json)、HTML、consumer receiptを保存した。報告はdev8 seed/576評価とsmoke2 seed/144評価の記述結果を明示し、信頼区間・正式性能判定・候補採択を行わない。

各要約attemptは全体60分、親・子各512MiB、試行directory256MiB/2,000entries、RAM/commit余裕各2GiB、disk余裕5GiB、子1区間120秒を上限にした。全体実測は順に2,806.091秒、1,243.560秒、1,087.228秒でいずれも全体資源pass・monitor終了確認済み。停止した区間56の子は時間記録905.577秒、区間82は120.031秒で、どちらも終了・回収済み。56の長い経過と前後の処理時間差の原因は記録だけでは断定しない。区間82は次試行で33.333秒・exit0となった。上限を引き上げず、別rootの固定planで続行した。監視はsamplingと協調checkpointで、OSのhard quotaではない。

報告工程は8.447秒、親peak private75,059,200bytes、新directory最大11,087,861bytesで資源pass。報告工程自体のraw評価payload再読込み、新評価、bootstrap、正式gateは0。報告内の`independent_numerical_audit_performed=false`は、この工程が独立監査を起動しなかったことを示す。上記postcheckは別工程の保存証拠である。

## 残る正式受入

今回完了したのは、既存合成dev/smokeの保存済み720評価を新readerから記述報告へつなぐengineeringの実適用である。[正式評価前の5まとまり](anomaly-multiseed-v0.3-preformal-acceptance-scope-2026-10-03.md)のうち、正式運用契約、未使用40 seedの登録入力・consumer、役割別source/runtimeとOS差分、正式結果の独立S6/公開監査、producerからreaderまでの全工程予算は未受入。旧正式OS pinのUBR9168と今回の観測UBR9457を同一視しない。公開報告の`formal_ready=false`、正式`status`/`provenance`/`analysis_consumer`/`bootstrap`はnullを維持する。`formal_permission=false`、`promotion_allowed=false`、`independent_s6_complete=false`、`result_trusted=false`、`execution_authenticated=false`、`source_closure_complete=false`、`runtime_closure_complete=false`も維持する。
