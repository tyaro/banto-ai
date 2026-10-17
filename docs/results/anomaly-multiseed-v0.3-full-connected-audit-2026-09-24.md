# v0.3 全720保存評価の観測・score・ledger検算（2026-09-24）

保存済み全120区間・720評価について、元観測から正常profile・残差・scoreを別実装で復元し、警報・異常との照合・集計まで一致を確認した。前回比較表の元データとも全720件が一致した。

検算本体は前回の実装 `2505fed6527a00891b9991720421b504a678899f` と同じ。実行時の候補HEADは `f727be6bfb02b8fb7385bd34ce1121a866d8f64f`。旧controller、producer、元データ、既存audit reportは変更していない。

## 対象と結果

| 項目 | 結果 |
| --- | --- |
| 区間 | 全120区間、重複・欠落なし |
| 評価 | dev 576 / smoke 144、計720件すべて一致 |
| 独立復元した正常profile | 34,560件 |
| 検算したscore | 10,368,000行 |
| source / equipment episodes | 17,272 / 9,949件 |
| incidents | 14,400件 |
| 過去の比較表との照合 | 全720評価の指標・件数・identity・attemptが一致 |
| 保存上の評価結果 | success 720 / inconclusive 0 |
| 今回の新規検算 | 区間1〜119、714評価 |
| 既存検算の再利用 | 区間0、6評価。外部pin付き報告と全対象入力のhash一致後に再利用 |
| 照合対象のユニークファイル | 2,281 files / 15,903,023,776 bytes / 240 datasets |
| 所要時間 | 1,196.095751秒、約19分56秒 |
| 中間保存 | 新規6区間ごと、19回 |

区間番号は0始まり。区間119は監査済みattempt2を使い、失敗したattempt1は保存したまま加算しなかった。前回までにprofile/scoreを検算した12評価も今回の720件に含まれるため、別に加算しない。ファイル数・bytesは各報告の対象入力を重複除外した値で、繰り返し読むsavepoint/evidenceなどは別。

## 検証の方法と保存

完走保存点のSHA256 `ca976322e0bb9e7b033b94948497a41acc79900668d01edbeebfc3fea8b22c8d` と、前回接続監査保存点のSHA256 `5a79114f8af267688e942b52763ad0d70b5cb8c55b650b3a1dcdf91ffe94d089` を外部起点にした。登録計画・最終verified attempt・入力bytes/hashを確認し、前回と同じ接続入口へ各区間を順次渡した。

数値検算器の浮動小数許容誤差は絶対/相対各1e-12、状態・ID・整数・閾値判定は厳密一致を維持した。数値計算とledger計算はproducer関数を呼ばない。登録identity/event・path検査などのmetadata helperは共有する。

今回の実行補助は、重複加算、不完全な報告、別区間・別identity、監査段階の欠落、評価結果の取り違え、資源下限を拒否する4試験が通過した。検算本体は前回41項目を通過したコードとhashが同一であり、同じ単体試験の再実行は省いた。各区間の実データはその都度検算した。

記録は `artifacts/full-connected-audit-2026-09-24`。`run.py`は既存入力の読取りと新OUTへの排他的な記録だけを行う。`chunk-001.json`〜`chunk-119.json`に報告、`checkpoint-*-running.json`に中間保存、`checkpoint-120-completed.json`に全件の報告pinを保持する。再利用した区間0は元報告への参照とpinを保持し、コピーや書換えをしない。`summary.json`には全件の照合と集計、最終文書commit/pinは`savepoint-evidence.json`に残す。

## 資源の観測

- 検証processの最大private memoryは約187.53MiB。各区間の処理後は初回83.82MiB、最後129.47MiB、最大129.89MiB。
- 新規119区間の境界で資源を記録。最小の空きRAMは14.59GiB、commit余裕は13.42GiB。
- 最後の空きRAMは15.47GiB、commit余裕15.58GiB。C/D空きは137.72/323.55GiB。
- 新規報告・中間保存等は集計時点で約7.96MBで、候補作業コピーのCドライブ上に保存した。

プロセスの最大使用量と区間境界での観測であり、継続的なメモリリーク不在の証明ではない。新しいproducer、登録seed生成、追加attempt、holdoutは起動していない。固定実計算sourceと本流はclean、過去の保存点・closed・既存dirty guardは不変。監視automation `banto-24` はPAUSEDを維持した。

## 研究結果と残る範囲

前回の比較結果は変わらない。C1の機械検知率は2200/2400（91.67%）、センサー検知率は2280/2400（95%）、警報正解率は4480/4680（95.73%）。C2はそれぞれ2158/2400（89.92%）、2280/2400（95%）、4438/4680（94.83%）。C1/C2の正常区間の誤警報は0件だが、全区間の未対応警報は200/242件ある。

**全720評価の保存観測→profile/score→ledgerの導出検算は完了した。** 保存観測自体の正常生成式・overlay・丸め前の値、bootstrap/信頼区間、正式gate/holdout、runtime/運用受入は今回の検算範囲に含めない。歴史的なpublication/source/runtime/supervisionの確認は完走保存点を前提とする。

`profile_derivation_verified`、`score_derivation_verified`、`ledger_derivation_verified`は全720件でtrue。`independent_s6_complete`、`formal_permission`、`promotion_allowed`はfalse、`performance_status=not_evaluated`、`campaign_evaluations_credited=0`を維持する。Phase 2/3全体や実設備での性能確認を完了扱いしない。

次は、正常生成・overlay・丸めの独立検算を設計し、保存観測の作成工程まで確認できるようにする。bootstrap/CIの独立検算と正式実行条件は別の残件として扱う。
