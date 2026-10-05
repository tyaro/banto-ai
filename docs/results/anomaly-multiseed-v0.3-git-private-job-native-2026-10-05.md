# v0.3 Git 専用 Job 所有・停止回収の実機証拠（2026-10-05）

clean source `3c72f8dfc20fd4ef7f413fa6199da4ce1d1e61d3`、Windows 11 Pro 26H2 / build26300.9457、CPython3.14.0で試走した。先行の架空archiveを使用し、登録holdout未読、正式credit0。

## 実装と境界

外部Git policyに `process_ownership: windows-private-job-v1` を明示すると、直接receiptはv2、source session manifestはv2となる。既存5項目policyは従来の直接handle経路とv1保存schemaを使う。未知の方式やpolicyと保存formatの違いは拒否する。CLIの `--own-reader-git` と組み合わせ、起動前・親・子固定・各roleの全Gitへ同じ外部policyを渡した。

各Gitは停止状態で作成し、無名・breakaway不可・kill-on-close付きの専用Jobへの所属確認とrootの生成identity採取を終えてからresumeする。継承するhandleは複製したstdin/stdout/stderrの3個に限定する。明示環境はUnicode blockで渡し、親の環境を追加継承しない。この挙動は[MicrosoftのJob仕様](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)、[nested Job仕様](https://learn.microsoft.com/en-us/windows/win32/procthread/nested-jobs)、[CreateProcessW仕様](https://learn.microsoft.com/en-us/windows/desktop/api/processthreadsapi/nf-processthreadsapi-createprocessw)に沿う。Jobに属するprocessの範囲であり、全ての外部起動経路の保証ではない。

root非zero・時間切れ・出力超過・観測失敗ではJobを停止し、root handleの終了と `ActiveProcesses=0` を確認してからcloseする。未回収やclose失敗では正確なnative handleを例外へ保持し、呼出し側が一度捕捉してもsession終了時に元の例外を再送出する。manifestの `git_job_members_exit_confirmed` を各pin付きreceiptから復元する。loaded code・個別の子孫exit・完全source/runtime・正式評価のflagはfalse。

## 5役の試走と保存pin

保存rootは `artifacts/anomaly-v03-preformal-git-job-trial-20261005-a1/attempt`、外部policyは `artifacts/anomaly-v03-preformal-git-job-policy-20261005-a1/policy.json`。rawと照合helperはGit管理外に保持する。入力join receiptは `artifacts/anomaly-v03-preformal-join-budget-20261004-a3` の4,948 B / `4362850634b05d353d93418313ff7a04c7ac1e5dabb7faea2aba6e19b4dded93`に固定した。

| 保存raw | bytes | SHA-256 |
| --- | ---: | --- |
| 外部 `policy.json` | 646 | `b2b3fb93092a22ba50d000f384c8633fc09dfcbbb55401346790269878beb828` |
| 外側 `receipt.json` | 5,223 | `7bbc0e678e34ef9330c9f71ce8e418dfcb7458c5aca1e5ff60dd64a6e6320a90` |
| 起動前 `git/head/receipt.json` | 2,864 | `40cf3aa2e692b457b2e208a433b54a62a6836b6d60b4717766bc82ba524062dd` |
| 起動前 `git/manifest.json` | 3,415 | `2d220bd6c5be114d74ec8036f80ededdd5bfcf00efadafbb42b4bda3455ccb40` |
| reader `attempt/reader-git/manifest.json` | 15,440 | `a4a5ea8278a144f80ed920d0b758f7973331b2c4512bcec32a064a356ba8cdf6` |
| [別実装raw照合](../../artifacts/anomaly-v03-preformal-git-job-trial-20261005-a1/audit.json) | 291,819 | `303090c431d9b998d16a906d61fc7783f2e6b3301f7368d8942316ddc99c0bf0` |
| [Git起動禁止の保存verifier](../../artifacts/anomaly-v03-preformal-git-job-trial-20261005-a1/saved-verifier-no-launch.json) | 682 | `e981f9d34f30052590ba7a80452c2e11e9d1a01bea8da3cba9804120eddbb0a7` |
| [別rootのnative control a2](../../artifacts/anomaly-v03-preformal-git-job-trial-20261005-a1/smoke-a2/native-smoke.json) | 7,741 | `e36bf4fcacbce71586802ae444c4eafc6372d2d4161e58be599483cce2e71066` |
| [Unicode環境読戻しa2](../../artifacts/anomaly-v03-preformal-git-job-trial-20261005-a1/environment-control-a2/result.json) | 1,674 | `6fa161326a9c11c71f8d832d958b28871c5fc0d8802d8ed3da9d22f1b81055a6` |

起動前7 / 親35 / 子固定26 / producer88 / analysis74 / audit74 / writer39 / reader39、**382 Git callの全専用Jobが終了時active0**。8 manifestのaggregateはtrue。別実装は製品verifierのimport前に1,244 raw、382 rootの別PID/start token、main Git pin、出力とproject在庫、Job所属/resume・accounting・memory・停止不要の正常終了を照合して `passed`。全raw pinはauditの `raw_pins` に保存した。Git382 Jobの `total_processes` 合計は764だが、個別identityを認証したのはroot382件。子孫の個別exitは未認証。

main Gitは `C:\Program Files\Git\mingw64\bin\git.exe` 本体4,285,840 B / `6125857e3aab09c5c79b5328e7d55aedb014b3cdbd4cd60aaf47b8e13cda455b`・hardlink4に固定。製品保存verifierはbare Gitと所有Gitの両起動を禁止して `verified_retained` / `call_status=verified`。完全loaded codeは未認証。

5役Jobは計698 process・active0・limit terminated0、peak Job memory154,984,448 B。5役root共有標本予算は148.0050583秒 / 上限240秒、親private peak139,341,824 B、最大25,307,447 B / 108 entries / depth4でpass。Git Jobの計数と5役Jobの計数には包含があり、両者を加算しない。Git保存rootは5役root外で、正式同形全工程予算の成立ではない。

## 異常系・回帰・CI

関連55試験、compileall、差分チェック、repository safetyがpass。正常終了、root0でも子が残る時間切れ、root非zero、出力超過、identity/accounting観測失敗、未回収・close失敗時の元handle保持、保存scope/計数改変拒否を確認した。nativeでは実GitのHEAD/status/blobと欠落blobの4件、架空CLI→grandchildの正常/timeout/root非zeroの3件を別rootで実行。後者の各Jobは計4 process・終了時active0で、root exitは正常0、異常17、timeout57351。active1・旧format・loaded code trueへ再sealした3攻撃を保存verifierが拒否した。Unicode環境は子の `os.environ` から変数名を大小文字非依存・値を完全一致で読戻した。

初回native helperはJob内processを厳密に2件とした期待値で失敗。環境probe初回もWindows Pythonが変数名を大文字化するため、大小文字依存の比較で失敗した。製品変更は不要で、両初回rawと失敗metadataを保持し、別rootのa2を採用した。記録はtrial rootの `native-smoke-a1-failure.json` / `environment-a1-failure.json` / `implementation-checks.json` にある。初回を成功へ付け替えていない。

先行reader保存点 `11244e41b5342524b583f59dac465bb03315d120` の [Ubuntu CI 37271402955](https://github.com/tyaro/banto-ai/actions/runs/37271402955) は全3 job成功。両minor各2,895件・fail0/error0/skip237・共有29 fixture/必須28試験pass、8 raw保存とローカル全journal再検証済み。[CI診断](anomaly-multiseed-v0.3-preformal-ubuntu-ci-triage-2026-10-05.md)へsummary pinを記録した。新Git Job接続はpush後の新runで確認し、trial rootの `post-push-ci.json` へ状態を保存する。追加agentは作成していない。

## 受入までの残り

次はGitのDLL/helper・動的load、各役と起動helper自身を含む最終source/runtimeの事前profile結合、個別の子孫identity/exitと独立権限の実機証拠。Jobのempty accountingをこれらの代用にしない。共通campaignの40 seed / 480区間 / 2,880評価由来、正式同形全工程予算・容量2倍、26H2契約とrunner由来採択、最終凍結revisionのUbuntu/Windows・dev8/smoke2、完全S6と公開fresh readも残る。

`inner_v1_git_owned=false`、完全source/runtime false、`formal_permission=false`、正式credit0、gate `s4_acceptance_not_frozen`、S5閉鎖を維持する。実データ作業は保存済み合成dev/smokeの範囲。今回のnative試走は架空入力のみ。
