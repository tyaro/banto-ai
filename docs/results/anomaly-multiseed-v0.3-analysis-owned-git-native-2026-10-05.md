# v0.3 analysis の直接 Git を所有した限定試走（2026-10-05）

clean source `d48349faf0ec442f7251a84da274e2c61edc2f93`、Windows 11 Pro 26H2 / build 26300.9457、CPython 3.14.0で、新しい `--own-analysis-git` を実行した。入力は先行の架空 archive だけ。登録 holdout 観測の生成・読取りと正式評価 credit は0。

## 実装と完了範囲

outer / Job invocation v4 は、子固定・producer・analysis 用の別 Git session を開く。`--own-analysis-git` は producer と子固定の所有範囲も含む。analysis の固定 source 27 file、HEAD/status と supervisor 境界の HEAD を所有 reader に渡し、before/after の動的 project source を同じ reader で検査する。依存検査へ入ってから immutable revision blob を cache し、各 working file の照合は両一覧で行う。候補 profile 指定は実行前に拒否する。

今回の analysis は固定29件 + 境界 HEAD 2件 + 動的 project source 43件 = **74件**。起動前7・親35・子固定26・producer88と合わせ、**230件**の直接 Git を保存した。外側は pinned owner → five-role result → analysis result → invocation / evidence / child stdout / dependencies / source-tool を読み、対象 path・pin・順序・件数を復元して検証する。3子 session の manifest 保存と検証が成功した後に Job子の成功応答を出す。既存 v1/v2/v3 の schema は維持する。

## 保存 root と raw pin

保存 root は `artifacts/anomaly-v03-preformal-analysis-owned-git-trial-20261005-a1/attempt`。外部 policy は `artifacts/anomaly-v03-preformal-analysis-owned-git-policy-20261005-a1/policy.json`。Git 管理外の raw と監査 helper は同じ workspace に保持する。入力 join receipt は `artifacts/anomaly-v03-preformal-join-budget-20261004-a3` の4,948 B / `4362850634b05d353d93418313ff7a04c7ac1e5dabb7faea2aba6e19b4dded93`を固定した。

| 保存 raw | bytes | SHA-256 |
| --- | ---: | --- |
| 外部 `policy.json` | 601 | `820508fb2eb11c9c66c82941fe4c488946d3198eb9a26d603e49aaf7c6ac5712` |
| 外側 `receipt.json` | 4,163 | `3aa4624bc2c367fb9402b1fbd842f94e24493b7f91b3d2d770191194aff6f719` |
| 起動前 `git/manifest.json` | 3,399 | `c1054ec00b22f15f2503b77b2eae3703da907f2ecf478d82b26d0c4faddf9636` |
| 親 `parent-git/manifest.json` | 14,303 | `4f9e50a6474dc59f664c3f446266e89daf795d4641875933901d395e00097343` |
| 子 `attempt/child-git/manifest.json` | 10,802 | `4e9c38dbf5ee4b2f9e7775a1e77f0d575dbfffd46b1955d6c5cc43e88243295d` |
| producer `attempt/producer-git/manifest.json` | 36,945 | `5abef8edd9fa7e2fbff19832abeb10a27296e630f5362b4c356018a7839156fd` |
| analysis `attempt/analysis-git/manifest.json` | 30,034 | `bb55703d99f001411216d8854b333b6a3dca64a849fd792a3ae2a8b6d1f674bd` |
| Job owner `attempt/receipt.json` | 5,905 | `5b729011cdd623af240d83ccb241e304440f985effd00cce90b01630cf8344f5` |
| analysis `result.json` | 2,969 | `ab48c4306c09fe3218b1a707eb786a737b60f1767d7687d306fa5df4d8269078` |
| analysis `dependencies.json` | 281,071 | `9e99a8d88c22e2c6e0191e66bf7147b902c604e481ea14811cac9b7f1ca50a14` |
| analysis `source-tool.json` | 205 | `35ffc726c06b0ed184fd328bf5179028c08248f0e6aac3ee10d64787578db2c3` |
| [別実装の raw 照合](../../artifacts/anomaly-v03-preformal-analysis-owned-git-trial-20261005-a1/audit.json) | 189,131 | `8a39e7f226a7428f4c26c1f0195d3f124fcb5e85a7824a581310450cfd7bb158` |
| [Git 起動禁止の保存 verifier](../../artifacts/anomaly-v03-preformal-analysis-owned-git-trial-20261005-a1/saved-verifier-no-launch.json) | 522 | `14ffa075785f89909d6f5fada34dd8322d9c9eb3f64dbb917c6b5edda976cf59` |

policy は main Git `C:\Program Files\Git\mingw64\bin\git.exe` 本体4,285,840 B / `6125857e3aab09c5c79b5328e7d55aedb014b3cdbd4cd60aaf47b8e13cda455b`を固定した。別実装の `audit_native.py` は製品 verifier の import 前に766 raw、230件の別 PID/start token、exit0と元 handle の終了、stdout/stderr、working source/Git blob、producer 48 / analysis 43 project file の保存応答への結合を照合し `passed`。その後 bare Git と所有 Git の両起動を禁止して製品の保存 verifier を実行し、`verified_retained` / `call_status=verified`。

5役は別 identity で終了確認済み。Job は計877 process・active0・limit terminated0、peak Job memory 154,185,728 B。5役 root の共有標本予算は140.7967773秒 / 上限240秒、親 private peak 129,769,472 B、最大25,307,309 B / 108 entries / depth4で pass。Git session root は5役 root の外であり、この数値は正式の全工程予算を満たす証拠ではない。

## 検証と CI

関連38試験、compileall、差分検査、repository safety は pass。所有 reader の伝播、cache 開始前後の呼出し、危険な request・source 不一致・profile の拒否、3子 manifest 保存前の成功応答拒否、保存 dependency raw の改変拒否を検査した。実 Git を使う v4 と既存 v2/v3 保存再検証も pass。

先行保存点 `ab9751acaa49fb9f3c01bdd37241925762233d6e` の [Ubuntu CI 37252632842](https://github.com/tyaro/banto-ai/actions/runs/37252632842) は全3 job成功、両minor各2,878件・fail0/error0/skip237、共有29 fixtureと必須28試験一致。8 raw保存とローカル全journal再検証を[CI診断](anomaly-multiseed-v0.3-preformal-ubuntu-ci-triage-2026-10-05.md)へ記録した。この成功は今回の後続 analysis 実装の CI 結果ではない。push 後の run snapshot は trial root の `post-push-ci.json`へ別保存する。

## 残る受入と実データ作業

| 項目 | 次の作業 |
| --- | --- |
| S4-3 各役の Git | 次は audit、続いて writer / reader の固定 source と動的依存へ所有 reader を渡し、役別の保存 invocation / 応答 / inventory に結ぶ |
| S4-3 全閉包 | Git の loaded code・子孫、各役の完全 source/runtime、独立権限・異常停止と個別終了の受入証拠を揃える |
| S4-1 / S4-4 | 26H2 契約と runner の版付き同定を採択し、最終凍結 revision の Ubuntu 両minor / Windows native・dev 8 seed / smoke 2 seedを照合する |
| S4-2 / S4-5 | 共通campaignから登録形式保存readerと40 seed集約へ結び、producerから別readerまでの正式同形全工程予算・容量2倍を実測する |
| S5～S7 | S4採択後に未使用登録holdoutを正式実行し、保存rawからの完全S6独立監査・公開fresh read・結果報告を行う |

`analysis_v1_git_owned=true` は今回の analysis 親側74件の範囲。`inner_v1_git_owned=false`、完全 source/runtime false、`formal_permission=false`、正式 credit0、gate `s4_acceptance_not_frozen`を維持する。保存済み合成 dev/smoke は実設備・顧客データではなく、今回の trial は架空入力だけ。登録 holdout は開いていない。
