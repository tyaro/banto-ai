# v0.3 保存行→50,000 draw・文書・sliceの共有予算（2026-10-05）

状態: **架空保存controlの接続試行が成功 / S4未採択 / 正式許可なし**。成功時のclean sourceは `b1e4aad4bc61e0d2d11b30b24c4b7166ad22ac5b`、初版は `6e2e4e8e5e9aa6ab91b10b76fc3cd869633181fa`。Windows 11 Pro 26H2/build26300/UBR9457・CPython3.14.0・local NTFSの候補環境で実測した。追加agentなし。正式gate `s4_acceptance_not_frozen`、`formal_permission=false`、正式credit0、登録holdout40 seed未読を維持する。[S4範囲案 v3](../anomaly-v03-s4-acceptance-scope-draft-v3.md)の条件2/5に対する部分証拠である。

## 実装と検証

[新入口 `run_saved_rows`](../../src/banto_ai/anomaly_v03_preformal_saved_row_document_budget.py)は、[前回の保存行projection](anomaly-multiseed-v0.3-saved-row-analysis-native-2026-10-05.md)を既存の50,000 draw計算・別process監査・文書・sliceへ接続する。架空480区間の各10 control rawを外部pinから検証・集約し、40 clusterと診断・coverage・sliceの4入力を導出する。callerが保存した4入力の期待pinとの一致を確認し、数値入力と文書に保存行projectionのpinを記録する。producer実行receiptは発行しない。

数値workerは凍結した50,000 draw／2,000,000 index bytes（SHA-256 `e375bf3feacb2f04bf5e1d40b141c1cfc5f69fa5437ea2704e323fd7523b22e5`）を生成する。別workerが独立のdraw生成・整数集計・type-7 interval・gate計算で全主表を監査する。同じsampler内で全文書候補、全slice／diagnostic series、別実装の件数監査へ進む。件数監査は親process内の別実装であり、3つ目の独立workerではない。既存数値fixtureの8 draw上限と1 draw入力は維持する。

最終確認は、固定した全controlのraw pinを文書作成前と終了前に再照合し、集約の重複計算を省いた。追加・欠落・外部pin差し替え・raw改変を拒否する。初版の関連34試験はpass（57.273秒）、最終確認修正後の焦点14試験もpass（7.898秒）。初回34試験runの1件は試験helperのkeyword引数ミスで、修正後に34件を再実行した。異なる版の試験数を単一runとして合算しない。

## 初回安全停止と新rootでの成功

前回作成した4,800 control raw・合計129,026,491 Bを再利用した。実観測を生成しておらず、共通campaign実行由来、raw観測からのprofile／score／ledger再導出は対象外。controlの歴史的revisionは架空の `aaaa…`、旧fixture構築sourceは `a9f1882`、今回のsourceは上記2 revisionとして区別する。

| 試行 | clean source | 結果 |
| --- | --- | --- |
| `trial-20261005-01` | `6e2e4e8` | 数値・別監査・文書・sliceを完了したがpostflightで `pipeline_commit_headroom`。659.792秒、最低余裕4,176,744,448 Bが下限4 GiB未満。全体はfailed。両workerはexit0・回収済み。4,821 raw／30 sourceの別照合は部分数値証拠として保存 |
| `trial-20261005-02` | `b1e4aad` | 開始前のcommit余裕10,267,774,976 B、空きRAM12,268,879,872 Bを確認。同じ上限・新しい非上書きrootで全段階完了。`status=measured`、共有予算pass、sampler終了確認 |

初回は停止理由をlatchし、終了時に余裕が回復してもfailedを保持した。最終確認の重複集約を省いた修正は別code保存点に固定。postflightは初回145.230秒、修正後2.939秒だった。成功試行の全体時間は初回より長く、環境負荷の異なる2試行から全体の速度改善は主張しない。初回receipt／metadataを上書きしていない。

成功試行は主9表・主推定117件・対応差72件・gate180件が独立算術と一致。profile未成立の2表とcoverageのinconclusive1枠を保持した。slice件数は本文1,233行・診断2,835行／9表。区間479のfailed attempt1を保持し、latest attempt2へ結ぶ。文書のstatus／provenance／analysis_consumer／bootstrapは未充足で、正式文書検証・候補選択・昇格は未許可。

| 成功試行のrole | 実worker PID | wall秒 | peak private B | 終了 |
| --- | ---: | ---: | ---: | --- |
| analysis | 844 | 201.271201 | 126,775,296 | 所有handleでexit0・回収確認 |
| audit | 17516 | 350.367753 | 29,671,424 | 所有handleでexit0・回収確認 |

共有wallは **733.392850／1,200秒**、root最大7,396,178 B・18 entries、親peak private211,824,640 B、最低commit余裕8,214,908,928 B、空きRAM7,970,578,432 B、空きdisk388,913,971,200 B。標本・協調監視でありhard quotaではない。外側result／budgetは予約し、最後のroot標本には含めない。controlロードとhelper importは時計外、validation／projection・両算術worker・文書／slice・再照合は時計内。

Git確認はbare Git、終了確認は2 arithmetic root worker。専用Git Job、5役全子孫回収、完全source/runtime在庫、producer→writer→fresh readerの全工程予算は未実施。30選定sourceのGit/disk pinと親候補runtimeは前後一致したが、閉包flagはfalseのままである。

## 保存後の別照合とraw pin

stdlibのみの別helperが外部terminal pinから4,821 rawを再読し、全480区間のcount・delay・exposure・profile・coverage・raw slice cellsを独立再集計した。入力・全主推定の文書対応・算術監査hash・slice件数監査・両worker終了・予算出力pin・30 sourceのGit/disk bytesが一致。consumerを同一試行内で再実行していない。この保存照合は実観測からの独立S6ではない。

成功rootは `artifacts/anomaly-v03-preformal-saved-row-document-budget/trial-20261005-02/`、helper rootは `artifacts/anomaly-v03-saved-row-50000-20261005-a2/`。次は成功root相対の **bytes／SHA-256**。

| ファイル | bytes | SHA-256 |
| --- | ---: | --- |
| `result.json` | 14,149 | `e3fd1948b525b6f28f134e87868b021433ff3e7969b661512ff96fd16df11da7` |
| `resource-budget.json` | 5,002 | `6bd1880578b0e73de0471fb092a727a7d0440d1ca10cbb74ceec149f79a52249` |
| `projection.json` | 554,130 | `593abe2a7b27ccf0bc0c636ab7d4230d2afb67794c3e62c6e120469712c6ecd0` |
| `input.json` | 155,375 | `1fbf2205c8d99d4a2b3f48d39b3b876030e77d82fc65b9e08b79a8615440aa0e` |
| `calculation.json` | 64,525 | `fa63adc17d4e4c319aea4021ff9294a5df0bb3f8b6a7a848c8eba019a5dd0a12` |
| `audit.json` | 566 | `8d3b3144b519c0a6c0d8fa46b52742fcc3015cfa5ffefc5f29d936cb3ed446c4` |
| `document.json` | 121,001 | `70ebeb7362522e80dd57bebe53f7ad6775cd9da4a72a0dc3d7d21eda41b77108` |
| `slices.json` | 1,928,882 | `91530bb83c6ceaaef49a0a3f25a6e50d93c1ffb01c586f989081ddee05c88efd` |
| `slice-count-audit.json` | 1,244 | `847e244b1fa03e0c1eae43827ec20cfe1c089debbf56bfa0bd1141e53bbf1bfa` |
| `analysis-supervision.json` | 519 | `06828b1f5bbad5e3351cc66c79e1a94fc12ccb35113ae8769ef1fd2e6b28f195` |
| `audit-supervision.json` | 518 | `a29c84e68f1f8e48e7042a7b74085eb1936ec936945ed53747e9ef2ba63e465b` |

helper rootの `request.json` は1,111 B／`445a173276a7a05ba324e5e1dc983a564f26ab3241b957e7375a7495857d1138`、`execution.json` は513 B／`215ee7de9bae164a455db0fb27fb251a59efaa4cb928ed9348cd4412c7cb3074`、`postcheck.json` は839,604 B／`2200096829a52dcbc565f2dd9a700def5b3111dfa65a1c00b1ffe8a4b6e2bf37`。成功helper sourceは `run.py` 5,147 B／`27829fa9cf5a31782f13c6a69b1cba07b0ae136026c3e0875a26cb29a976d0b0`、`postcheck.py` 14,240 B／`1e07a977c8a6e43d7233913cf98162789b9c02b31489bc67ba49c05f83f6ff53`。

初回root `trial-20261005-01/result.json` は9,365 B／`e8d789ea9de1a91b261001b04942dd49ec7ed393e62fcbdbb934ad628981c11f`、budgetは4,965 B／`2113acb65c6b49b84d08d71252ee8002734ba95da15b87fa3082053d198de726`。初回helper root `artifacts/anomaly-v03-saved-row-50000-20261005-a1/failed-postcheck.json` は839,634 B／`4351fbb61c5b92814d4dce90f80f47e21a66694838fb5382f50a891ab68a7d51`、状態は `partial_numerics_verified_budget_failed`。`artifacts/`はGit対象外で、別マシンへの移行にはrawも保全する。

## CIと残る受入

先行保存点 `f7abbe37609f2cb4bd2032b6e87b0d7a278f99bd` の [Ubuntu CI 37304712937](https://github.com/tyaro/banto-ai/actions/runs/37304712937) は全3 job成功。Python3.12／3.14各2,919試験・fail0／error0／skip237、共有29 fixture一致・必須28試験pass。8 rawと全journalをローカル再検証した。[CI診断](anomaly-multiseed-v0.3-preformal-ubuntu-ci-triage-2026-10-05.md)にpinを記録。この成功を新source `b1e4aad` のCIへ読み替えない。

次は50,000 draw文書・sliceをwriter／fresh readerへ接続し、producer／保存readerを含む共通外側予算を測る。共通campaign実行由来、raw観測からのprofile／score／ledger独立再導出、正式同形容量2倍、最終source/runtime在庫と異常時回収、26H2・保証A・runner代替同定の版付き採択と独立監査、最終revisionのLinux／Windows・dev8／smoke2受入は残る。保存済み合成dev/smoke720評価と今回の架空2,880枠を合算しない。S4の独立受入が完了してからS5へ進む。
