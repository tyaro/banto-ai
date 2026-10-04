# v0.3 架空一区間 wall-row・親Git所有の Windows 限定試走（2026-10-05）

同revisionの[Ubuntu CI 37237626121](https://github.com/tyaro/banto-ai/actions/runs/37237626121)は、新規テストの架空WindowsパスをLinuxの`Path`で扱った2件で両minor不合格。以下のnative保存pinは`b39e595`固定の実測証拠であり、テストfixture修正版へ読み替えない。

clean source `b39e595989f9fbdc509a6bdbf114ec47fe65d4f4`、Windows 11 Pro 26H2 / build 26300.9457、CPython 3.14.0で二つのopt-in試走を別rootへ保存した。登録holdout観測は読まず、正式許可・評価creditはともにfalse/0。二試走を正式の単一campaignや一つの全工程資源予算へ足さない。

## 単一wallから保存6行まで

新campaign `7aed7840`、path-code `w` のplanはreader必須source 15件すべてを含む選定source 48件を固定した。slot 0・attempt 1をprepare→run-budget→fresh saved-reread→completed journal→10保存rawの再読→6行bridgeまで、一つの協調wall上で実行した。外側receiptは `verified`、**746.0792751 / 900秒**、内側は745.8021359秒。保存verifierは `verified_retained`。3つの外側Jobはprepare 62、run-budget 689、saved-reread 278 processで、いずれもroot exit 0・終了確認・`ActiveProcesses=0`。これは協調的なslot 0の時間測定であり、hard wall quotaやproducerから最終文書までの全資源予算ではない。

| 保存raw | bytes | SHA-256 |
| --- | ---: | --- |
| campaign `plan.json` | 97,654 | `e22e589d7736c1d2e70be6601c2e39d886e173a1f577e1e1268845251f761bce` |
| campaign `journal/000001.json` (`started`) | 1,244 | `526be6e7858366371193a796ea2fb4592f62bb1865cb6d6210d47d67c03d2b8b` |
| campaign `journal/000002.json` (`completed`) | 6,641 | `cff5b0b47d20633a9676cf1ce34efb3b4bec512d17a5dbf9ee62fd371a57872a` |
| control `checkpoint-000002.json` | 1,190 | `5fe684cd1339ff1db5c5a22504f471b479666a5221c33707171e781499f11326` |
| inner `campaign-wall-7aed7840/receipt.json` | 2,242 | `ad56a21bad86472059d1eb6f94690abc1c0c3e2af789c3f8ef341e25daf3958e` |
| outer `campaign-wall-row-7aed7840/receipt.json` | 2,144 | `eff81ce9ed9c8f35ce7ed4dc00996e9af91dbe55df60e45f801bcd5baaf6ac8a` |
| outer `bridge-result.json` | 3,748 | `49a9cf8462f9b19d9325e72ed294c3f99bc1d6eae065d0622a9f53ff75339ec4` |
| saved-reread `rows.json` | 116,085 | `4f7d0a058a123e35e348488cf85120ea906a5e9ace9285cd34a78028b9587105` |
| [外部再hash 23 raw・48 source](../../artifacts/anomaly-v03-preformal-wall-row-native-trial-20261005-a1/external-rehash.json) | 9,250 | `91894926fbb57a03c8cb53a338fea769f71d649111f1e1f54fddfa10a3923058` |

別実装のread-only再hashは23 pathと48/48のworking/HEAD source bytesに不一致0。6保存行はすべて定義どおりの`inconclusive`で、bridgeは**1/480区間・6/2,880評価の部分結合**だけを返す。`campaign_coherence_authenticated=false`、`campaign_evaluations_credited=0`。旧`4aacbee4`のplanはreader必須source 15件中9件しか固定しておらず、新しい厳密なsource結合ではfail closedのまま保全する。

## 親の直接Git 42件

別rootの候補profileなし5役fixtureを同じclean sourceで実行した。Job前7件とv1親の初期・境界・保存照合に当たる直接35件を、個別の所有Git receipt/stdout/stderrと二つのmanifestへ固定した。外側receiptと保存verifierは`verified` / `verified_retained`、保存再検証でGitの再起動を禁止してもPASS。独立監査は42件の個別raw、5 unique sourceのworking/Git blob、5役終了を再照合した。Windows Jobは計1,080 process・終了時active 0・peak memory 154,836,992 B。5役共有予算は96.3075秒、親private peak 95,223,808 B、root最大25,306,947 B / 108 entries / depth 4でpass。

| 保存raw | bytes | SHA-256 |
| --- | ---: | --- |
| 外部policy `policy.json` | 581 | `58ed754771042c7dc9d0b31a694ca37bb5a63e0d1cb5bd706fcdf124a80ef4ac` |
| 親試走 `attempt/receipt.json` | 2,974 | `816c6af1ba6431fc500c84d42d849521b3eb1915221c429c75acda36618d0d85` |
| 起動前 `git/manifest.json` | 3,395 | `58f844f1b530fa01109b03f9e58785d1990c0839112e6019d77b740515a87952` |
| 親 `parent-git/manifest.json` | 14,299 | `78ec0abebb45afb064858db4fc29ce4ad00f68b1f2499667279a06dfb8b4c636` |
| v1 Job owner `attempt/receipt.json` | 5,903 | `fe744209b00b489a3dc8f6d08d07af7e37a1e18e86805de09f999c62c92bef67` |
| [独立raw監査](../../artifacts/anomaly-v03-preformal-parent-owned-git-trial-20261005-a1/audit.json) | 12,389 | `4e00a40032c4b89ec04e13229a6f44bd3bd7fcb32f03ebaa724f6733706c38e0` |

この入口は候補profile指定を実行前・CLI・保存verifierで拒否する。Job子の固定source Git約26件と、各roleのJob内親側で変動するsource/依存Git約366件は未所有である。Gitがロードしたコードや子孫、in-memory Python code、完全source/runtime閉包、個別孫exit codeも未認証。`parent_v1_git_owned=true`は**親の直接35件だけ**を意味し、`inner_v1_git_owned=false`、`source_closure_complete=false`、`runtime_closure_complete=false`、`execution_authenticated=false`、`formal_permission=false`を保つ。

## 次の受入境界

関連統合57試験、compileall、repository safety、差分検査はpass。同revisionのUbuntu CIとrunner由来候補は別証拠として照合する。S4-2には共通campaignの40 seed/480区間の保存行から寄与を再導出し、`inconclusive`のまま40 cluster/50,000 drawと全slice/sidecar・完全S6同形監査へ渡す固定経路が残る。S4-3にはJob子の固定26件から始める所有Git接続と全source/runtime閉包、S4-5にはproducerから別readerまでの単一全工程予算・容量2倍が残る。これらが採択されるまで旧gate `s4_acceptance_not_frozen`、S5未開放、正式credit 0を維持する。
