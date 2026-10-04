# v0.3 架空slot 0の共有wallとWindows Jobメモリ（2026-10-04）

状態: **正式S4受入前の限定技術証拠**。作業branchは`codex/preformal-acceptance-scope`、実走時のclean sourceは`772ee3d6e2ea5f02c6c53a72bae6d4daf6942d29`。固定した手作り系列のslot 0だけを新rootで実行した。登録holdout観測は読まず、正式評価creditは0、`formal_permission=false`、gateは`s4_acceptance_not_frozen`のままである。使用tupleはWindows 11 Pro 26H2/build 26300/UBR 9457、CPython 3.14.0 AMD64、local NTFS。26H2の[運用契約案v2](../anomaly-v03-formal-operations-contract-proposal-v2.md)と[改訂案v1](../anomaly-v03-s4-26h2-amendment-draft-v1.md)は未採択。

## 固定rootと結果

| 項目 | 保存値 |
| --- | --- |
| campaign / attempt | `4aacbee4` / slot 0・attempt 1・`l001` |
| campaign root | `artifacts/anomaly-v03-preformal-campaign-4aacbee4/` |
| control root | `artifacts/anomaly-v03-preformal-campaign-control-4aacbee4/` |
| 共有wall root | `artifacts/anomaly-v03-preformal-campaign-wall-4aacbee4/` |
| plan raw pin | 96,713 B / `a135a6eba189a90eec699f0ec6c1ce06cd6acbc7298967fe0b31ec427e83aa99` |
| 初期checkpoint pin | 348 B / `b8d250b01745f9b19c1b9d8b40ca986eb5c9c64636fa4c8395b401d34357e567` |
| preflight intention pin | 1,598 B / `30d7671feb2a92607bd9615d9312cd9b2c51b432e524e54015f129b3ea01da06` |
| 共有wall claim pin | 776 B / `714d03ee96e31590b8b619fbdd5b384060eb78061fa306f03e80e814581e7756` |
| 共有wall receipt pin | 2,230 B / `91714388f56d14649db5ad700e71dc2a6d3a0be41fcc80188c7c6a5ef7d6b38e` |
| terminal checkpoint | 1,190 B / `ef2e5f2a178099f5216216403123f69632d5f4cd2bf0637a4db40217fba8fd21`。count 2、head `9019c96ba559fc00ea7a9b1eb203422a7cf7b4ac344c5256e21bbfd3650ac33e` |

単一processの`time.monotonic()`でpreflight前から完了記録まで測った経過は**503.798秒 / 900秒**だった。prepare、run-budget、fresh saved-rereadへ各開始時の残時間を渡し、工程後に同じ時計を再確認した。完了receiptは`status=verified`、`last_stage=completed`。terminal count/headは480区間中1区間・2,880評価中6評価の**架空の部分宣言**であり、正式coverageを示さない。外部wall receipt pinからのread-only `verify_completed`はclaim、11個の証拠pin、2つのrequest rawと保存済みcompletion chainを再開封し、`verified_retained`を返した。

| 外側Job | 経過秒 | 起動時wall上限秒 | Job累計process | 終了時Active | Job peak bytes | 単一process peak bytes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| prepare | 131.818 | 898.064 | 62 | 0 | 335,925,248 | 334,647,296 |
| run-budget | 206.329 | 735.972 | 689 | 0 | 387,227,648 | 359,415,808 |
| saved-reread | 53.349 | 492.066 | 278 | 0 | 343,425,024 | 316,145,664 |

3件ともroot exit 0、Job割当・root再開・終了時`ActiveProcesses=0`、観測エラー0、停止理由なし。Job peakは終了後の`QueryInformationJobObject(JobObjectExtendedLimitInformation)`による保存値であり、取得不能・値の不整合は成功扱いを拒否する。[Microsoftの構造体仕様](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information)にある`PeakProcessMemoryUsed`と`PeakJobMemoryUsed`を記録した。3件のJob経過の和391.496秒と共有経過との差**112.302秒**にはpreflight、工程間の保存・照合、完了処理等が入る。独立したread-only raw hash照合で、manifestの22出力・131,144,120 Bが実ファイルと22/22一致した。

## この証拠の範囲

共有wallは**一区間の協調・標本境界による計測**であり、Python側の各precheck/後処理をOS hard quotaで強制停止するものではない。Job peakメモリはJob内の観測値であり、Job外process、個々の子孫exit code、5役割全体のsource/runtime閉包、全工程の容量・private・commit/RAM予算を認証しない。保存receiptも`hard_wall_quota_authenticated=false`、`full_end_to_end_budget_measured=false`、`campaign_coherence_authenticated=false`を明示する。先行の[Job所有試行](anomaly-multiseed-v0.3-campaign-job-ownership-2026-10-04.md)とは別root・別revisionで、時間やbytesを足して正式予算にしない。

S4の残件は[引き継ぎ表](anomaly-multiseed-v0.3-session-handoff-and-remaining-acceptance-2026-10-04.md#正式受入までの残件)に従う。特に、26H2契約と公開保証の採択、登録形式の保存readerと全slice/sidecar、40架空cluster・50,000 drawの全文書、完全独立S6同形audit、writer・別readerまでの**一つの外側予算**、smoke bytesに基づく容量2倍、5役割閉包、最終revisionでのLinux両job・Windows native・dev 8/smoke 2と独立受入は未了。これらを固定・採択するまでS5は起動しない。実データ作業は、既保存の合成engineering dev/smokeの確認と、S4採択後に限る未使用登録holdout 40 seedの正式実行を区別する。

`artifacts/`はGit管理外で、上記raw証拠はこのworkspaceに保存される。後日CLIで再照合する場合、同じcheckout・絶対path・cleanな固定source `772ee3d6e2ea5f02c6c53a72bae6d4daf6942d29` が必要で、文書commit後の新HEADではsource一致検査が拒否する。保存receipt pinは外側に保持し、既存rootを上書きしない。
