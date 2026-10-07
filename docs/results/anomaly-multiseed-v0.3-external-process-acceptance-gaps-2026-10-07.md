# v0.3 外部program・異常時子孫回収の受入残件（2026-10-07）

再開後の追補: [親HEAD/cleanの4 Git Job](anomaly-multiseed-v0.3-parent-git-identity-budget-native-2026-10-07.md)をcode9ddaed7で共通予算へ接続し、74焦点試験・clean限定native・別保存checkerがpass。親blob/worker内Git・実ロード依存・業務異常子孫は残る。以下は先行source監査時点の保存記録。

## 保存範囲

clean `6f1270f05614e7127ecdd876da77dcc1805c1858` とnative code `343c8639b0acfb2be535c02b5aaf4288b8f3d43e` の選択15 sourceについて、working rawと両Git blobが一致することを確認した。保存した[静的source監査](../../artifacts/preformal-external-process-gap-audit-20261007/source-gap-audit.json)は5,938 B / SHA-256 `1624adfb0966372c1e9441d79ab1a625e5990f0cfbdb621f1a4cfcd2049aa3cf`。ASTで位置を記録した裸のGit呼出し構文は16箇所で、実行回数や全source閉包の数ではない。

新しいnative・業務worker・追加agentは0。登録holdout観測未読、正式credit0、`s4_acceptance_not_frozen`、`formal_permission=false`。全7役r7の成功終了・14phaseと独立保存checkerは保全し、今回はsourceの残件のみ整理した。

## 実経路と残件

| 境界 | 保存sourceで確認した事実 | 残る受入証拠 |
| --- | --- | --- |
| producer / initial-reader / saved-reader / writer / fresh reader | [直接supervisor](../../src/banto_ai/anomaly_v03_process_supervisor.py)のPopen・元handle、stop時kill、wait、未回収時の所有権保全。生成と公開の実入口から使用する。 | private Job等により、異常時の業務子孫を停止し、root exitと対象tree終了を確認する実経路の証拠。直接worker終了だけで子孫終了を判定しない。 |
| analysis / audit | [実draw bridge](../../src/banto_ai/anomaly_v03_preformal_bound_draw_bridge.py)の `_supervise` が直接Popen、元handle在庫、kill/wait、未回収時に `UnreapedMeasurement` を保持。 | 2役と各外部helperの異常終了・time/memory/output停止を、同じouter budgetとtree回収へ結ぶ。 |
| source境界のGit | [generator](../../src/banto_ai/anomaly_v03_preformal_owned_generated_attempt.py)、[initial-reader](../../src/banto_ai/anomaly_v03_preformal_owned_saved_attempt.py)、[saved-reader](../../src/banto_ai/anomaly_v03_preformal_saved_row_reread.py)、common/document/draw側の選択source比較に `check_output(['git', ...], timeout=10)` が残る。 | caller保持の絶対exe path・raw pin・環境・元handle・入力出力・終了を、実際に使う各境界へ結ぶ。外部program/helperの実ロード依存も別途照合する。 |
| 7役runtime在庫 | [runtime observer](../../src/banto_ai/anomaly_v03_role_runtime_observation.py)の前後stdlib・import/native/cache在庫。親post-exitはcaller source manifestを使用し、fresh Gitを起動しない。 | 外部programのロード、途中だけの依存と異常子孫は、この候補の認証範囲外。境界在庫の成功を全runtime閉包へ読み替えない。 |
| 既存Git Job prototype | [owned Git](../../src/banto_ai/anomaly_v03_preformal_owned_git.py)にexe/PATH・links・環境の外部pin、[Git Job](../../src/banto_ai/anomaly_v03_preformal_owned_git_job.py)にsuspended起動/assign/resume、TerminateJobObject・active_processes=0・root exit・未確認handle保全がある。 | [five-role parent-owned v7](../../src/banto_ai/anomaly_v03_preformal_five_role_parent_owned_git.py)はcandidate profileを拒否し、今回の全7役callerと接続されていない。Gitの実ロードcode・全外部helper閉包も未認証。 |

prototypeの全統合を追加必須にしない。再利用する機構は最終経路の必要な境界を選び、既存限界と外部pinを保持して採択前の限定試験へ結ぶ。

## 次の小さい実装単位

1. 実callerとworkerのGit使用境界を外部program policyへ結ぶ。絶対exe/raw pin、許可argv・環境、source full revisionと要求出力pin、元process handle、exclusive stdout/stderr/receiptを入力として固定する。各10秒の既存上限と共通時計・資源・log上限を維持する。
2. 起動前にprivate Jobへ所有させ、rootと対象業務子孫のexit/reap・accounting終了を確認する停止経路を、7役の実入口へ結ぶ。未確認時は元Job/process/thread handleとrawを保持し、成功扱い・次worker開始を拒否する。
3. 実際に使うGit・helper・DLL/CRTを外部期待pinへ照合する。在庫の採取箇所と、親確認・子実行・終了後確認の担当を版付き契約へ固定する。exe本体のpinだけでロード依存を認証済みにしない。
4. 新しい限定試験はpin/role/root/identityの差替え、起動・accounting観測失敗、root先行終了、子孫残存、time/memory/output停止、未回収handle保持、停止後のworker起動拒否を対象にする。今回この異常fixtureは実行していない。既存の全工程nativeは反復しない。

保証A/B・26H2・runner同定の改訂採択、正式登録入力consumer、最終同revisionのLinux/Windows・dev8/smoke2・独立受入、正式共通予算と容量2倍は、[証拠索引の5残件](anomaly-multiseed-v0.3-preformal-evidence-index-2026-10-07.md)に残る。

CI37547050883（HEAD21d3866）とCI37548282365（HEAD6f1270f）は監査開始時進行中。完成したrawを各HEADへ固定して保存・runner v2照合する。文書だけの保存は新しいCIを起動せず、この2件の追跡を継続する。
