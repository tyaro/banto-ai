# v0.3 所有Git 7件から5役Jobへの Windows native 限定試走（2026-10-05）

架空入力だけを使い、clean source `a5deb31936cf769445c3e617d4648f05f4bc5d46` で opt-in [v2入口](../../src/banto_ai/anomaly_v03_preformal_five_role_owned_source_anchor_v2.py)を1回実行した。環境は Windows 11 Pro 26H2 / build 26300.9457、CPython 3.14.0。候補profileは指定せず、先行の架空join `anomaly-v03-preformal-join-budget-20261004-a3` を保存pinで入力にした。joinの旧source系譜を現revisionへ改名しない。新しい policy と試走rootを使用し、上書きや登録holdout観測の読取りは行っていない。

| 保存物 | bytes | SHA-256 |
| --- | ---: | --- |
| 外部policy `artifacts/anomaly-v03-preformal-owned-source-v2-policy-20261005-a1/policy.json` | 581 | `d036e6e93ed6f641c7268c528b738d2d6208f8eb6bc9de1b6eaa67996d09d2bb` |
| 外側 `artifacts/anomaly-v03-preformal-owned-source-v2-trial-20261005-a1/attempt/receipt.json` | 2,627 | `a187a3fcc485121d90c640ba0c054097ee7265ec1cf8f436576569cc59aeab65` |
| 同 `git/manifest.json` | 3,393 | `505d17910ef87f5055ad48dc296f2a14f373cc453c208e62dc9c8f01ba97a8fe` |
| 同 `attempt/receipt.json`（内側v1 owner） | 5,902 | `18b9debbc9da325c125a3a5bf7ba734572c47cbaa6e61b806a00a7baeec1b45a` |
| 同 `attempt/supervision.json` | 2,671 | `970b02b0c8773ab910076237cdf91483735170223227dddd3505f2cde5bae556` |
| 先行join a3 `receipt.json` | 4,948 | `4362850634b05d353d93418313ff7a04c7ac1e5dabb7faea2aba6e19b4dded93` |

外側は `status=verified`、保存verifierは `verified_retained`。別実装のread-only監査でも、外側・policy・manifest・内側ownerと7件の直接Git receipt / stdout / stderrを再hashし、全pin一致を確認した。GitはHEAD→clean status→選定source 4件→owner source 1件の順で、全7件がexit 0・直接handle終了確認・stderr 0。5 source stdoutは同revisionのGit blob OIDおよびworking rawと一致し、7件すべての開始時刻は内側owner起動より前である。

内側ownerとproducer/analysis/audit/writer/readerの監督記録はすべてexit 0・終了確認。Windows Jobは計1,074 process、終了時active 0、peak Job memory 156,233,728 B。owner監督は75.181秒で、5役共有予算は73.52秒・最大root 25,306,886 B / 108 entries / depth 4でpassした。これは現revisionの限定native試走と保存bytesの照合であり、候補profile必須の正式同形予算や全40 cluster/50,000 drawの実証ではない。

同じsource revisionの[Ubuntu予備CI 37230362806](anomaly-multiseed-v0.3-preformal-ubuntu-ci-triage-2026-10-05.md)は、Python 3.12/3.14各2,821件・fail0/error0/skip237、共有fixture 29件と必須28試験の比較・journal検証、smoke/品質/benchmark/safetyを含む3 jobすべて成功した。これはv2実装の予備回帰であり、Windowsの正式native受入やS4採択ではない。

所有Gitの証明範囲は**Job前の直接7呼び出しだけ**。内側v1 owner・子・chainのbare Git、Git loaded code/子孫、5役全source/runtime閉包、個別子孫exit code、登録保存readerからの全工程系譜は残る。保存receiptは `inner_v1_git_owned=false`、`source_closure_complete=false`、`runtime_closure_complete=false`、`execution_authenticated=false`、`formal_permission=false`、`new_evaluations=0` と明示する。S4は未採択、正式credit 0、gate `s4_acceptance_not_frozen`、S5未開放を維持する。

この文書を後でcommitするとHEADが試走revisionから変わり、v1 ownerの保存verifierは現在のclean HEAD照合で旧試走を拒否する。再検証が必要なら同じ絶対pathのcheckoutをclean `a5deb31936cf769445c3e617d4648f05f4bc5d46` に戻して実施する。外部pinに対するread-only raw再hashは後続HEADでも可能である。`artifacts/`はGit管理外で、別workspaceへcommitだけを移しても保存証拠は付属しない。
