# v0.3 publication 前段と writer の直接 Git を所有した限定試走（2026-10-05）

clean source `0bdbfee93fa484e07de2d1f4639284776418d426`、Windows 11 Pro 26H2 / build 26300.9457、CPython 3.14.0で、新しい `--own-writer-git` を実行した。先行の架空 archive だけを入力とし、登録 holdout 観測の生成・読取りと正式評価 credit は0。

## 実装と完了範囲

outer / Job invocation v6 は、子固定・producer・analysis・audit・writer 用の別 Git session を開く。`--own-writer-git` は先行4範囲を含む。publication 前段の固定15 source、writer 開始時の HEAD/status、supervisor と保存検査の HEAD 3回、writer の動的 project source を所有 reader に渡す。固定 source の immutable revision blob は既存 cache に入れ、依存一覧に現れた追加 source だけ取得する。working file は before/after の両一覧で照合する。候補 profile は実行前に拒否する。

今回の writer 範囲は前段17件 + 開始時2件 + 境界 HEAD 3件 + 追加 project source 17件 = **39件**。起動前7・親35・子固定26・producer88・analysis74・audit74と合わせ、**343件**の直接 Git を保存した。writer の依存一覧は固定15を含む32 project file。writer と reader の Git context を分け、reader は新しい未所有 context と cache を使う。既存 v1～v5 の schema と既定経路の共有 cache は維持する。

外側は pinned owner → five-role result → publication result → writer result → invocation / evidence / child stdout / dependencies / source-tool を結ぶ。writer result は publication result 内の同じ行から canonical bytes の pin を求めて再読する。対象 path・pin・順序・件数を復元し、5子 session の manifest 保存と検証が成功した後に Job子の成功応答を出す。

## 保存 root と外部 pin

保存 root は `artifacts/anomaly-v03-preformal-writer-owned-git-trial-20261005-a1/attempt`、外部 policy は `artifacts/anomaly-v03-preformal-writer-owned-git-policy-20261005-a1/policy.json`。Git 管理外の raw と監査 helper は同じ workspace に保持する。入力 join receipt は `artifacts/anomaly-v03-preformal-join-budget-20261004-a3` の4,948 B / `4362850634b05d353d93418313ff7a04c7ac1e5dabb7faea2aba6e19b4dded93`を固定した。

| 保存 raw | bytes | SHA-256 |
| --- | ---: | --- |
| 外部 `policy.json` | 601 | `72a9df79b467be183b89fcc5fa66304a97d89c83758ee358ad9b218b51414fd6` |
| 外側 `receipt.json` | 4,926 | `b6110e4e31f80e3bd7e018457d6c940ab2ab00d622e0c975db734b70caf08a53` |
| writer `attempt/writer-git/manifest.json` | 15,432 | `f2878902e5b8ce57ecb3954250b4df5025db2b670ff450e66b3ddda2175d99b2` |
| publication `result.json` | 4,776 | `f3750433866749bb9dd1d49611955cb867a6b33bb1efd24e503d6584da32fa91` |
| writer `result.json` | 1,533 | `a5d82ab56dfd716984687d7cb07dd212a5e12d57b0aa99d6396f0039f65d5218` |
| writer `dependencies.json` | 253,449 | `d024c8bab95f4ce5c3012c441ca557c893e511e6eb44d0c1625faf0ecfaeeecd` |
| [別実装の raw 照合](../../artifacts/anomaly-v03-preformal-writer-owned-git-trial-20261005-a1/audit.json) | 272,568 | `0dca63b5e0e35c0a967ff4d26fc4e578a154b8c617e16c4509f7949a0958f04f` |
| [Git 起動禁止の保存 verifier](../../artifacts/anomaly-v03-preformal-writer-owned-git-trial-20261005-a1/saved-verifier-no-launch.json) | 628 | `4308ec7941fb886c8f0672346bec4e3fe1e62a6af3a3d795355006e0dee0b48b` |

別実装の `audit_native.py` は製品 verifier の import 前に1,120 raw、343件の別 PID/start token、exit0と元 handle の終了、stdout/stderr、working source/Git blob、producer 48 / analysis 43 / audit 43 / writer 32 project file の保存応答への結合を照合し `passed`。全 manifest と各 direct receipt の raw pin は上記 audit の `raw_pins` に保持する。main Git は `C:\Program Files\Git\mingw64\bin\git.exe` 本体4,285,840 B / `6125857e3aab09c5c79b5328e7d55aedb014b3cdbd4cd60aaf47b8e13cda455b`・hardlink4を固定した。その後 bare Git と所有 Git の両起動を禁止し、製品保存 verifier は `verified_retained` / `call_status=verified`。

5役は別 identity で終了確認済み。Job は計737 process・active0・limit terminated0、peak Job memory 153,915,392 B。5役 root の共有標本予算は102.6550968秒 / 上限240秒、親 private peak 139,538,432 B、最大25,307,777 B / 108 entries / depth4で pass。Git session root は5役 root の外で、この測定は正式の全工程予算を満たす証拠ではない。

## 検証と CI

関連44試験、compileall、差分検査、repository safety は pass。writer reader の伝播、固定 blob の cache、危険な path・source 不一致・profile の拒否、既定共有 context と所有 writer 時の reader context 分離、5子 manifest 保存前の成功応答拒否、保存 dependency raw と call order の改変拒否を確認した。実 Git を使う新 v6 と既存 v5 の保存再検証も pass。試験 fixture の入力欄と拒否メッセージ期待値を修正した経過は trial root の `implementation-checks.json`へ記録した。

先行保存点 `932b5b9c76ea203111a9fe9b086a508c65a35ad0` の [Ubuntu CI 37260191710](https://github.com/tyaro/banto-ai/actions/runs/37260191710) は全3 job成功、両minor各2,887件・fail0/error0/skip237、共有29 fixtureと必須28試験一致。8 raw保存とローカル全journal再検証を[CI診断](anomaly-multiseed-v0.3-preformal-ubuntu-ci-triage-2026-10-05.md)へ記録した。先行 `1c008b2` の [run 37258533095](https://github.com/tyaro/banto-ai/actions/runs/37258533095) も全3 job成功を確認した。今回の後続writer実装の CI は push 後の新 run で確認し、trial root の `post-push-ci.json`へ状態を別保存する。

## 残る受入と実データ作業

| 項目 | 次の作業 |
| --- | --- |
| S4-3 reader Git | fresh reader の固定 source と動的依存へ所有 reader を渡し、役別の保存 invocation / 応答 / inventory に結ぶ |
| S4-3 全閉包 | Git の loaded code・子孫、各役の完全 source/runtime、独立権限・異常停止と個別終了の受入証拠を揃える |
| S4-1 / S4-4 | 26H2 契約と runner の版付き同定を採択し、最終凍結 revision の Ubuntu 両minor / Windows native・dev 8 seed / smoke 2 seedを照合する |
| S4-2 / S4-5 | 共通campaignから登録形式保存readerと40 seed集約へ結び、producerから別readerまでの正式同形全工程予算・容量2倍を実測する |
| S5～S7 | S4採択後に未使用登録holdoutを正式実行し、保存rawからの完全S6独立監査・公開fresh read・結果報告を行う |

`writer_v1_git_owned=true` は publication 前段と writer 親側39件の範囲。`inner_v1_git_owned=false`、完全 source/runtime false、`formal_permission=false`、正式 credit0、gate `s4_acceptance_not_frozen`を維持する。実データ作業は保存済み合成 dev/smoke の範囲で、今回の trial は架空入力だけ。登録 holdout は開いていない。追加agentは作成していない。
