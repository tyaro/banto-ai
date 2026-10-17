# v0.3 選定source Git 7呼び出しの限定試走（2026-10-05）

S4受入前の架空データ技術試行。clean source `fdaf5eec58d110b5f048c703c740c8e10664fc07` で、[明示reader入口](../../src/banto_ai/anomaly_v03_preformal_five_role_job_owner.py)、[所有Git session](../../src/banto_ai/anomaly_v03_preformal_owned_source_git_session.py)、[限定CLI](../../tools/preformal_owned_source_git_trial.py)を実行した。対象は`owner._source`**1回**の選定source照合のみ。5役Jobや登録観測は起動・読取していない。

外部固定[policy](../../artifacts/anomaly-v03-preformal-owned-git-policy-20261005-04/policy.json)は601 B / SHA-256 `737ab0f226ac285ed608f51b776a716c0c11bf6dc036f03f663c2afdfb5c1513`、実行fileは`C:\Program Files\Git\mingw64\bin\git.exe` 4,285,840 B / `6125857e3aab09c5c79b5328e7d55aedb014b3cdbd4cd60aaf47b8e13cda455b`。非上書き[結果](../../artifacts/anomaly-v03-preformal-owned-source-git-trial-20261005-01/result.json)は1,654 B / `3c68e0577385c3693a5819970e096a3b297e8c8fdf87ea9c0da97d5e9891b2cc`、[session manifest](../../artifacts/anomaly-v03-preformal-owned-source-git-trial-20261005-01/git/manifest.json)は3,373 B / `c64173fd06dc09b078c69a84c3c4bfcb88a3e40a489f636a57b375f6f29646ed`。保存verifierと別実装のread-only照合が一致した。

| 順序 | 直接Git呼び出し | receipt SHA-256 |
| ---: | --- | --- |
| 1 | `HEAD` | `e88b3089231a406a30f71b95ff0e08e2922f940188c52e68132fc25b2c832a94` |
| 2 | clean `status` | `b79b2eaee1d12f0ba9f0f32826a67a59137f636441dab0f08d37c882344c5987` |
| 3 | five-role orchestrator blob | `401d1fe75f64cb87b0f5e4b0ca807a1a23fc294edf3aca24b1e256f2f755ed94` |
| 4 | four-role orchestrator blob | `596bd4c06a044abfeecb334ff49535709f012f92927bb034b9639edc5525e894` |
| 5 | producer fixture blob | `12f00a4bf5858b9e81e5c378774b2931c08c31022d4909b56489a91a48cfaa64` |
| 6 | shared chain budget blob | `c3732a82c5b2f733d552f7d7bd62f72a70538853edd30d7b860880f8f061a86e` |
| 7 | Job owner blob | `b86faed9a2cb1ac0e436eb8b9ee8bead09b8f51d9384c696978041224b833ed6` |

7件は別PID/Windows開始token、exit 0、stderr 0。blobの保存stdoutは指定revisionの選定source raw pinと一致し、Git実行fileの起動前後のpinも一致した。結果・manifest・各receiptの`formal_permission`、`source_closure_complete`、`runtime_closure_complete`、`execution_authenticated`はfalse。Gitのloaded code・子孫processも未認証。関連39試験、compileall、repository safetyがpassした。

この明示readerは既存v1の`owner.run_owned`、`child_main`、`chain.run_chain`、保存verifierへまだ伝播していない。既存5役Job内のbare Git、profile loader、four-role/producer内のGitを置換した証拠ではない。次に進むには、親preflight・監督前後・子pre/post・chain pre/postに**別々の非上書きphase root**を割り当て、外部policy pinと各manifest pinをv2 invocation/owner receiptへ結び、v2保存verifierで正確な7件の順序を再照合する。保存session verifier単独は列挙された呼び出しだけを検証し、7件の完全性は限定CLIが追加確認した。失敗Git callはsessionのfailed manifestとして保全するが、限定CLIの成功`result.json`は作らない。

受入表のS4-3は依然未完了。S4-2の共通40 seed系譜、S4-5のproducerから別readerまでの単一全工程予算、S4-1の26H2保証採択、S4-4の最終Linux/Windows/dev8/smoke2も残る。S5の未使用登録holdoutは開かず、正式credit0、gate`s4_acceptance_not_frozen`を維持する。`artifacts/`はGit管理外である。保存session verifierはGitコマンドを再起動せず、pin固定rawと現在の実行fileを照合するため、後続文書commitのHEADをこの試走のsourceへ読み替えない。
