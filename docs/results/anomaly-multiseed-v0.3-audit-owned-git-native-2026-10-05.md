# v0.3 audit の直接 Git を所有した限定試走（2026-10-05）

clean source `49871576449be1ee8890390b93e3f63fc3073301`、Windows 11 Pro 26H2 / build 26300.9457、CPython 3.14.0で、新しい `--own-audit-git` を実行した。入力は先行の架空 archive だけ。登録 holdout 観測の生成・読取りと正式評価 credit は0。

## 実装と完了範囲

outer / Job invocation v5 は、子固定・producer・analysis・audit 用の別 Git session を開く。`--own-audit-git` は analysis / producer / 子固定の所有範囲も含む。数値 worker 用の所有 reader と保存検査器を役割指定で共用し、audit の固定 source 27 file、HEAD/status、supervisor 境界の HEAD、before/after の動的 project source を検査する。依存検査へ入ってから immutable revision blob を cache し、各 working file は両一覧で照合する。候補 profile 指定は実行前に拒否する。

audit は固定29件 + 境界 HEAD 2件 + 動的 project source 43件 = **74件**。起動前7・親35・子固定26・producer88・analysis74と合わせ、**304件**の直接 Git を保存した。外側は pinned owner → five-role result → audit result → invocation / evidence / child stdout / dependencies / source-tool を読み、対象 path・pin・順序・件数を復元して検証する。4子 session の manifest 保存と検証が成功した後に Job子の成功応答を出す。既存 v1/v2/v3/v4 の schema は維持する。

## 保存 root と raw pin

保存 root は `artifacts/anomaly-v03-preformal-audit-owned-git-trial-20261005-a1/attempt`。外部 policy は `artifacts/anomaly-v03-preformal-audit-owned-git-policy-20261005-a1/policy.json`。Git 管理外の raw と監査 helper は同じ workspace に保持する。入力 join receipt は `artifacts/anomaly-v03-preformal-join-budget-20261004-a3` の4,948 B / `4362850634b05d353d93418313ff7a04c7ac1e5dabb7faea2aba6e19b4dded93`を固定した。

| 保存 raw | bytes | SHA-256 |
| --- | ---: | --- |
| 外部 `policy.json` | 601 | `3a13490813cbe47d835fa26f83d700eb3e4c0d14490651b39e7908bc66bce3d3` |
| 外側 `receipt.json` | 4,521 | `d488e15397aec6ed935b0c1469805edb6bc0a184b8b8cab4460b90da5e61f4ab` |
| 起動前 `git/manifest.json` | 3,393 | `2033bf51875136e86611b9c4c15eeaf8b387a43d316df1833cd3bd0ac1c7c9cf` |
| 親 `parent-git/manifest.json` | 14,297 | `0ae4fbaa13e14f81d438a6ed61cd2a305028a0f0d5ab3da483156619795ef1c0` |
| 子 `attempt/child-git/manifest.json` | 10,796 | `d26c029984537aacf2af9d21fb3ebab82a16f7bad9ff20092396ccd37a6fc912` |
| producer `attempt/producer-git/manifest.json` | 36,939 | `76ed5db0bef208af424576f84ed72a5cf395dcd616dc8fde13ea1381d1cdda6b` |
| analysis `attempt/analysis-git/manifest.json` | 30,028 | `0dfd4c2152e43cf53bb2cce5a017d510a78d4ea744d872e2bc0d7a316adeeca3` |
| audit `attempt/audit-git/manifest.json` | 29,800 | `d83075dfb142aa9fb303686117c4d9b5d1bf1517f81ea8b653f7e2d65566c289` |
| Job owner `attempt/receipt.json` | 5,903 | `19a4968f5c8851097b609b1919f69cab0999c29b090b6b8b999de3bd1617ee84` |
| audit `result.json` | 2,349 | `5d1014a0451ccd8f2afae87a011cf3914a943a9bbd4e4cb1f042c9c50ce50998` |
| audit `dependencies.json` | 281,071 | `ab4caea0484bc893e672da8f6c91a00b78ca723b5a5021dc1b66fd303524821a` |
| audit `source-tool.json` | 205 | `35ffc726c06b0ed184fd328bf5179028c08248f0e6aac3ee10d64787578db2c3` |
| [別実装の raw 照合](../../artifacts/anomaly-v03-preformal-audit-owned-git-trial-20261005-a1/audit.json) | 241,471 | `af3b9d7397794ed7e45cd1d582cbec72e49f2fbcd37eb955acaf3cb4573147e0` |
| [Git 起動禁止の保存 verifier](../../artifacts/anomaly-v03-preformal-audit-owned-git-trial-20261005-a1/saved-verifier-no-launch.json) | 574 | `e54542675771e7dfb3abe946d607cf9136c52334101abc181ee360160c26b620` |

policy は main Git `C:\Program Files\Git\mingw64\bin\git.exe` 本体4,285,840 B / `6125857e3aab09c5c79b5328e7d55aedb014b3cdbd4cd60aaf47b8e13cda455b`と hardlink4を固定した。別実装の `audit_native.py` は製品 verifier の import 前に995 raw、304件の別 PID/start token、exit0と元 handle の終了、stdout/stderr、working source/Git blob、producer 48 / analysis 43 / audit 43 project file の保存応答への結合を照合し `passed`。その後 bare Git と所有 Git の両起動を禁止して製品の保存 verifier を実行し、`verified_retained` / `call_status=verified`。

5役は別 identity で終了確認済み。Job は計674 process・active0・limit terminated0、peak Job memory 154,640,384 B。5役 root の共有標本予算は138.5428261秒 / 上限240秒、親 private peak 137,437,184 B、最大25,307,480 B / 108 entries / depth4で pass。Git session root は5役 root の外であり、正式の全工程予算を満たす証拠ではない。

## 検証と CI

関連40試験、compileall、差分検査、repository safety は pass。audit reader の伝播、役別 call ID と cache、source 不一致・profile の拒否、4子 manifest 保存前の成功応答拒否、保存 dependency raw 改変と analysis/audit 取り違えの拒否を検査した。実 Git を使う新 v5 と既存 v4 の保存再検証も pass。取り違え試験の初回 fixture は hash 検査で先に拒否されたため、入れ替えた bytes と pin を一致させて role scope の拒否まで確認する fixture に修正し、再実行した。

先行保存点 `1c008b2aaea00d4d0354ba74c43cf66160bdfaca` の [Ubuntu CI 37258533095](https://github.com/tyaro/banto-ai/actions/runs/37258533095) は本保存時点で両minorの unittest が実行中。状態を trial root の `prior-ci-snapshot.json`へ保存した。直近の確認済み成功は `ab9751a` の [run 37252632842](https://github.com/tyaro/banto-ai/actions/runs/37252632842)で、[CI診断](anomaly-multiseed-v0.3-preformal-ubuntu-ci-triage-2026-10-05.md)に固定 source と raw pin を記録済み。今回の後続実装の CI 結果は push 後の新 run で確認し、`post-push-ci.json`へ別保存する。

## 残る受入と実データ作業

| 項目 | 次の作業 |
| --- | --- |
| S4-3 各役の Git | 次は writer、続いて reader の固定 source と動的依存へ所有 reader を渡し、役別の保存 invocation / 応答 / inventory に結ぶ |
| S4-3 全閉包 | Git の loaded code・子孫、各役の完全 source/runtime、独立権限・異常停止と個別終了の受入証拠を揃える |
| S4-1 / S4-4 | 26H2 契約と runner の版付き同定を採択し、最終凍結 revision の Ubuntu 両minor / Windows native・dev 8 seed / smoke 2 seedを照合する |
| S4-2 / S4-5 | 共通campaignから登録形式保存readerと40 seed集約へ結び、producerから別readerまでの正式同形全工程予算・容量2倍を実測する |
| S5～S7 | S4採択後に未使用登録holdoutを正式実行し、保存rawからの完全S6独立監査・公開fresh read・結果報告を行う |

`audit_v1_git_owned=true` は今回の audit 親側74件の範囲。`inner_v1_git_owned=false`、完全 source/runtime false、`formal_permission=false`、正式 credit0、gate `s4_acceptance_not_frozen`を維持する。保存済み合成 dev/smoke は実設備・顧客データではなく、今回の trial は架空入力だけ。登録 holdout は開いていない。追加agentは作成していない。
