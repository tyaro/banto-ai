# v0.3 架空campaignのWindows Job所有・新規一区間（2026-10-04）

作業branch `codex/preformal-acceptance-scope`。このnative試行のclean source revisionは `a1c8461f7ead4f9867ae2c0b48dca367618401f5`。固定手作り系列だけを使い、登録holdout観測は読んでいない。26H2単一writer[S4改訂案](../anomaly-v03-s4-26h2-amendment-draft-v1.md)は未採択、旧gate `s4_acceptance_not_frozen`、正式credit 0を維持する。

## 変更と失敗保全

`d6811ec` で、prepare・run-budget・fresh再読取りの**外側CLI**を、停止状態の `CreateProcessW` → breakawayを許さない私有Jobへ割当 → `ResumeThread` の順で起動する経路へ接続した。stdout/stderrは限定した3 handleだけを継承する。成功reportには元process exit 0とJob accounting `ActiveProcesses=0` を必須とし、時間切れ・元process異常終了・観測失敗ではJob全体を停止・回収する。保存済みsupervisionのJob結果をprepareとcontrollerの再検証でも必須にした。元handleを回収できない例外はterminal receiptへ変換しない。

最初の新root `331c1516`・`j001` は、Job起動前に旧25H2 runtime policyを参照して `IntegrityError` となり、`prepare_exit` の失敗receipt 1,789 B / SHA-256 `80ff73b302c753ef9688efe9f3d3e9b5c293e0782ef561621d0173ce7a696a7b` を保存した。supervisionは `assignment_confirmed=false`、root PIDなし、正式flag false。このrootを再利用せず、Job監督を26H2のscoped policyへ合わせる修正を `a1c8461` に固定した。失敗rootの値を成功証拠へ加算しない。

Job接続時のcampaign関連82試験pass、26H2 policy修正後のprepare/controller関連29試験pass、Job native 13/13 pass（正常・親異常・timeoutと未回収handleの保全を含む）、repository safetyと差分検査pass。これらは限定実装の回帰である。

## 新root `5cd8e989` の実CLI結果

campaign rootは `D:\develop\banto-ai\artifacts\anomaly-v03-preformal-campaign-5cd8e989`、外部control rootは `D:\develop\banto-ai\artifacts\anomaly-v03-preformal-campaign-control-5cd8e989`。slot 0・attempt 1・path code `k001` をprepare→started→run-budget→fresh再読取り→completedの順で非上書き保存した。`tools/preformal_campaign_completion_store.py verify` は固定pinを指定してexit 0。terminal record count 2/head `958f4006…`、完了**宣言**1/480区間・6/2,880評価、欠番479である。

主要raw pinは **bytes / SHA-256**。`campaign`、`control` は上記rootを表す。

| 保存ファイル | bytes | SHA-256 |
| --- | ---: | --- |
| campaign `plan.json` | 96,230 | `1ac15dd20d0d5be58b552720315709f557e9893c20c7cab7d53a4d82279725a1` |
| control `checkpoint.json` | 348 | `9ecd6329d6072a6d84eed08ebdb033f10aacd3ac59fc47590dc596e3949a2bfb` |
| control `preflight-intention.json` | 1,598 | `202a0c59385feb5c4e0f693ff2d66e46c0282d3bdb7a2f5185b365633d077edc` |
| `artifacts/anomaly-v03-preformal-campaign-prepare-5cd8e989/receipt.json` | 2,179 | `640b796b31f3fcf5cd477dfa5b14e1542b79c914267f43c9e321610fb5370bbc` |
| `artifacts/anomaly-v03-preformal-generated-pinsets-k001/pins.json` | 75,735 | `13523e1fd70f5ad2f5d53c49ee9c2d8b9c8f4926a579e9e2129d8f4554b4f3d9` |
| campaign `journal/000001.json` (`started`) | 1,244 | `d85ab49867afb8d850546adf9e03caea70e1f76cdbabcabcbb71bce59e3ae19c` |
| control `checkpoint-000001.json` | 839 | `c45339f49f4bc0556349dc47d510f61b12f50cc6be5016af1ca03fbbf676ae2c` |
| `artifacts/anomaly-v03-preformal-campaign-run-intent-5cd8e989/request-pin.json` | 1,661 | `3d25b3048d291df8488a63b12b20c3e4032059d2013a63b567e6384e53ea2abb` |
| campaign `control/000-1/run-budget/receipt.json` | 6,928 | `913c7235bd891b7e1efd5c60a83953f385fab205cc63a2da78dd9a133383cb46` |
| `artifacts/anomaly-v03-preformal-campaign-reread-intent-5cd8e989/request-pin.json` | 2,119 | `9a87f6040b607c93fbcbd464c3056fa2ccaafe1384b1a531af6da62937657288` |
| campaign `control/000-1/saved-reread/receipt.json` | 2,470 | `3a1112638ccd615f3051188f116ad437cf9b5d0d37977ab8da459cae4d4019bf` |
| `artifacts/anomaly-v03-preformal-saved-row-reread-k001/rows.json` | 116,085 | `c7d3a0eac558801f3028d05f9029de020e0537ae02d752f0e3abdb214722f535` |
| campaign `journal/000002.json` (`completed`) | 6,641 | `958f4006858189cf064d21d38339fa743ff628306e5b1bb79de828fd6d438392` |
| control `checkpoint-000002.json` | 1,190 | `3aa07101e1e66e4c096c74da9a3ee5a95015296472f8532c857d1695a75cb0f7` |

3外側CLIの保存supervisionを実ファイルからhashした結果は次のとおり。いずれもJob割当・root再開・root exit 0・Job `ActiveProcesses=0`・観測エラー0で、`all_assigned_processes_exit_confirmed=true`。`total_processes` はJob accounting上の累計であり、個々のexit codeを示さない。

| 工程 | supervision bytes / SHA-256 | Job累計process | 経過秒 |
| --- | --- | ---: | ---: |
| prepare | 2,397 / `357e0e80617a786768e6f844bafad2bc3f539f8e6784c7f417b7132e11e17c85` | 62 | 166.291 |
| run-budget | 2,753 / `d3820fa28d84dbdbb9349049a7d7e9b77b6cacf07f42144d710704eb9bba7c75` | 689 | 251.350 |
| saved-reread | 2,892 / `2896f9fedd53adf9039ea59e1033a230eff17b9ad297ae00d7fba0f1a22be448` | 278 | 62.294 |

独立したread-only hash照合でmanifestの保存22 raw・計131,144,120 Bが22/22一致し、planとmanifestの選択source 60参照・39 unique rawも不一致0だった。保存行は6件。sourceの選択rawは`selected-working-git-raw-only-not-source-closure`であり、全役割と動的loadの完全閉包ではない。今回の外側Job所有は、Job外に作成されたprocess、個々の子孫exit code、孫のprivate memory、全工程の単一予算・容量2倍を認証しない。外側receiptの`descendant_exit_confirmed=false`も保守値として維持する。

`status=partial_declarations_unverified`、`campaign_coherence_authenticated=false`、`launch_authorized=false`、`resume_authorized=false`、`formal_permission=false`、`campaign_evaluations_credited=0`。先行campaign `72f754b3` や失敗 `331c1516` とcoverageを加算しない。`artifacts/` はGit管理外で、文書commit後はHEADが計画の固定sourceと異なるため、read-only再検証には同じcheckoutをcleanな `a1c8461f7ead4f9867ae2c0b48dca367618401f5` に戻し、同じ絶対rootと上記pinを指定する。

## 正式受入まで

次は、Job外processを含む5役割のsource/runtimeと失敗時保全、登録入力→profile/score/ledger→全slice/sidecar→40 cluster/50,000 draw→完全S6同形監査→公開・別readerまでを固定し、単一外側予算と容量2倍を測る。最終clean revisionでLinux Python 3.12/3.14両jobの外部runner同定、Windows 26H2 native、dev 8・smoke 2を一つのS4受入記録に結ぶ。保証Aの版付き採択と独立監査が済むまでS5は起動しない。採択後にのみ未使用登録holdout 40 seed・480区間・960 dataset・2,880評価を新rootで実行し、S6独立再導出とS7報告へ進む。架空480区間の完走を新しいS4必須条件にはしない。
