# v0.3 架空5役割Job所有と50,000 draw連続予算の保存点（2026-10-04）

状態: **S4受入前の限定技術証拠**。実走時のclean sourceは `3f708f60cd6d8a1b571e5298effa47893c18f955`、Windows 11 Pro 26H2/build 26300/UBR 9457、CPython 3.14.0 AMD64、local NTFSである。登録holdout観測を読まず、正式評価creditは0、`formal_permission=false`、gateは `s4_acceptance_not_frozen` のまま。26H2の保証A案は未採択である。

この保存点で[5役割Job owner](../../src/banto_ai/anomaly_v03_preformal_five_role_job_owner.py)、[50,000 drawから文書・sliceまでの連続予算入口](../../src/banto_ai/anomaly_v03_preformal_contiguous_document_budget.py)、[Linux CI journalの読み取り専用検証器](../../tools/ci_verify_regression_journals.py)を追加した。新規3試験moduleの32件、隣接既存29件（うち明示opt-in native 11件skip）、compileall、repository safetyは通過した。CI検証器の焦点試験は必須test IDの欠落・同一skip、未知のWindows skip、source/workflow hash差、共有fixture差を拒否する。ただしこのrevisionのUbuntu 3.12/3.14実jobやrunner image digestを取得した記録ではない。

## 5役割の外側Jobと候補profile

固定した架空join archiveは `artifacts/anomaly-v03-preformal-join-budget-20261004-a3/`、外部receipt 4,948 B / SHA-256 `4362850634b05d353d93418313ff7a04c7ac1e5dabb7faea2aba6e19b4dded93`。新ownerは専用のsuspended親CLIを非breakaway Windows Jobへ割り当ててから起動し、既存5役割fixtureをその親の中で実行する。保存後はroot exit 0、Jobの `ActiveProcesses=0` とメモリ、5役のresult/identity/profile pin、共有予算を開き直す。Job外のprocess、個々の孫exit code、in-memory codeや動的loadを認証するものではない。

| 試行とroot | 保存pin | 確認した結果 |
| --- | --- | --- |
| [Job trial-01-unprofiled](../../artifacts/anomaly-v03-preformal-five-role-job-owner-20261004/trial-01-unprofiled/receipt.json) | receipt 5,901 B / `a357c8dae4c4d2aa26ceca77c899b99de40df5790394b420e851fd260612db99` | `verified`、read-only `verified_retained`。Job累計1,080 process、終了時Active 0、Job peak 153,964,544 B。内側共有予算112.317秒/406標本、5役終了報告を照合。候補profileはなし |
| [同revisionの直接参照 trial-17](../../artifacts/anomaly-v03-preformal-five-role-26h2/trial-17-job-profile-reference/result.json) | top 7,215 B / `733ad221f3df34a1d9802c71c92a078c4ef95da9c873f72a16ff0f407359dda4`。予算4,906 B / `bd3a421c8ad4b7fda1fa1feffbf12976a737bf7f87cb412ff715c5a14cc5eddf` | 5役完走、共有予算156.781秒/550標本。Job所有の合格としては算入せず、別の候補profile作成元とする |
| [外部参照pinset](../../artifacts/anomaly-v03-preformal-profile-pinsets-26h2/trial-17-job-reference-pins.json) → [候補set](../../artifacts/anomaly-v03-preformal-role-profiles-26h2/trial-17-job-profile-candidates/candidate-set.json) | pinset 3,239 B / `a38ac81a5d493b604c7ebbda090b8f92971eed6324a9916aed006058ae49bc18`、set 2,165 B / `182db520d70e57b344d2cc6aab2b9e73d58318ccd0d9f14cbe3e02c7ed540a49` | 参照topと5役×5種類の保存raw pinを別rootに固定し、5つの作業前候補を作成。候補は未採択 |
| [Job trial-02-profiled](../../artifacts/anomaly-v03-preformal-five-role-job-owner-20261004/trial-02-profiled/receipt.json) | receipt 6,580 B / `404147a5744cd34061ab7f8af6f5990668606afcd8cf9ee1055ea57dc074bbea` | `verified`、read-only `verified_retained`。5役の作業前候補pinと前後依存・runtimeが一致。Job累計1,691 process、終了時Active 0、Job peak 165,343,232 B。内側共有予算167.347秒/588標本、5役終了報告を照合 |

候補は参照実行のdisk/native fileの2点観測から作った。今回のJob所有と候補照合を合わせても完全なsource/runtime閉包にはならず、保存receiptの `source_closure_complete`、`runtime_closure_complete`、`execution_authenticated` はfalseである。正式50,000 drawや登録形式保存readerを、この1 drawの5役試行へ接続した扱いにしない。

## 50,000 drawから文書・sliceへの連続予算

別入口は、旧clean `94be9ed2702d2f383acb952ea1cf24b21b9754fc` の架空producer [trial-16 result](../../artifacts/anomaly-v03-preformal-five-role-26h2/trial-16-two-role-enforced/producer/result.json) 2,927 B / SHA-256 `49d1d331a3d6bd7500746c791f2a8e1bcfb687c373ed526640201b28412e51d1` と4投影fileを外部固定する。[投影pinset](../../artifacts/anomaly-v03-preformal-contiguous-document-input-20261004-01/projection-pins.json)は462 B / `a1a30bf2fb3e5faacd38fa606cce16c4d603131219177aeebcaa35eb45826243`。旧producerの実行とその入力9,778,170 Bは今回の時計・root容量の外にある。

新入口の候補上限は共有wall 1,200秒、親private 512 MiB、root論理96 MiB、system commit最低余裕4 GiBなどである。50,000 draw主子と別算術監査子を順に所有し、両子の終了・保存pin・draw hashを照合してから、同じsamplerの下で文書、slice、件数監査、postflightへ進む。標本・協調停止でありhard quotaではない。2件の実機試行はいずれも **`pipeline_commit_headroom` で安全停止**した。

| 非上書き試行 | terminal raw pin | 監視・停止した位置 |
| --- | --- | --- |
| [trial-20261004-01](../../artifacts/anomaly-v03-preformal-contiguous-document-budget/trial-20261004-01/result.json) | result 7,644 B / `b254b6608d78d7c442aa53c368d7cb9eb7221b4c81f28e2aee0e0f5be90798da`、budget 3,609 B / `0fe4b5d61a34d6c5b01042980093af3c9b8e57e9ac4725b4fc6696fc277b5582` | 226.156秒/877標本。主子は完了・回収、監査子は下限割れで停止・回収。最低commit余裕1,879,265,280 B。文書・sliceは未開始 |
| [trial-20261004-02](../../artifacts/anomaly-v03-preformal-contiguous-document-budget/trial-20261004-02/result.json) | result 7,644 B / `32ef10e862959c4f73a161eacb8fc646a3fe9d93d9660643bc2476affada5cfd`、budget 3,607 B / `98b0cf5415101a19492e31c4bd4681c0abf9bd7378db2feb6a5409050ccb4422` | 375.749秒/1,390標本。同じ停止理由、主子は完了・回収、監査子は停止・回収。最低commit余裕3,941,183,488 B。文書・sliceは未開始 |

両失敗rootのresultと5つずつの実在する参照file pinを別途raw SHA-256で再照合し、12/12一致した。どちらも `status=failed`、`stage=audit`、`formal_permission=false`、文書・slice fileなしを確認した。1回目の終了後にcommit余裕が13,871,894,528～14,048,198,656 Bへ戻ったため、上限を変えず新rootで2回目を実行した。再び下限割れしたので、これ以上の即時再試行や下限緩和は行わない。実行中に他processの大きなprivate memoryを観測したが、下限割れの因果までは確定しない。別試行の主子成功を監査子・文書の成功へ足さない。

## 正式受入への差分

- S4-1: 26H2契約と保証Aの独立採択は未完了。旧25H2の正式入口と `s4_acceptance_not_frozen` を維持。
- S4-2: 1 drawの架空5役と旧producerの40 cluster/50,000 drawは別系譜。登録形式保存行から40 clusterへの由来、全slice/sidecar、実保存readerは未接続。
- S4-3: 同一revision・候補profile必須・外側Job内の5役終了証拠を得た。動的load、in-memory code、Job外process、個別孫exit codeと正式役割の完全閉包は未了。
- S4-4: CI journal検証器は作成したが、最終revisionのUbuntu両job、runner同定、Windows正式native、dev 8/smoke 2の受入は未実施。
- S4-5: 主・別算術→文書・sliceの単一時計入口を作ったが、実機2件は監査中に資源停止。連続成功、前段producer・登録reader、完全S6、writer→別reader、容量2倍の実測は未了。

`artifacts/` はGit管理外で、このworkspaceの保存bytesを保持する。read-only Job verifierと連続入口のsource照合は実走時のclean HEAD `3f708f6` を要求する。後続の文書commitでHEADが変わるため、過去rootを新revisionの成功証拠として通さない。次の全工程試行は資源圧迫が落ち着いた時点で、同じ4 GiB下限・新root・固定した外部入力pinで行い、成功と失敗の両attemptを保全する。
