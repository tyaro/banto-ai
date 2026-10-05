# v0.3 fresh reader の直接 Git 所有・保存試走（2026-10-05）

clean source `2ae2905fdae4d4dc02fb725b9a68750c4e6b6830`、Windows 11 Pro 26H2 / build 26300.9457、CPython 3.14.0で、新しい `--own-reader-git` を実行した。入力は先行の架空 archive。登録holdoutは未読、正式評価creditは0。

## 実装と完了範囲

outer / Job invocation v7は、先行v6の全範囲にfresh readerの直接Gitを追加する。`--own-reader-git` はwriter・audit・analysis・producer・子固定Gitを含む。writer終了確認後、reader用に固定sourceを取得し、独立したcontextとimmutable revision blob cacheを作る。固定15 sourceをcacheへ入れ、観測した追加project sourceを一度取得し、working bytesは依存before/afterの両相で再照合する。候補profileは実行前に拒否する。

writerとreaderの保存結合を共通化した。外部pin付きowner → five-role result → publication result → 対象role result → invocation / evidence / child stdout / dependencies / source-toolを再読し、role・revision・固定source・動的在庫・Git順序を結ぶ。reader resultはpublication内の同じ行のcanonical bytesからpinを求めて再読する。全6子sessionのmanifest保存と検証が終わってからJob子が成功stdoutを出す。既存v1～v6の入口と保存schemaは維持した。

readerは前段17回 + 開始時HEAD/status 2回 + 境界HEAD 3回 + 追加project source 17回 = **39回**。起動前7 / 親35 / 子固定26 / producer88 / analysis74 / audit74 / writer39 / reader39、計 **382回**を別manifestへ保存した。publication両roleの依存在庫は各32 project file、固定sourceは各15件。これで当該架空経路の各role直接Gitを接続したが、完全source/runtime閉包は未完了。

## 保存rootと外部pin

保存rootは `artifacts/anomaly-v03-preformal-reader-owned-git-trial-20261005-a1/attempt`。外部policyは `artifacts/anomaly-v03-preformal-reader-owned-git-policy-20261005-a1/policy.json`。Git管理外のrawと照合helperは同じworkspaceに保持する。入力join receiptは `artifacts/anomaly-v03-preformal-join-budget-20261004-a3` の4,948 B / `4362850634b05d353d93418313ff7a04c7ac1e5dabb7faea2aba6e19b4dded93`に固定した。

| 保存raw | bytes | SHA-256 |
| --- | ---: | --- |
| 外部 `policy.json` | 601 | `98ade64653636e91f400a7fb2fd6dd6f5b233cf7ac69ea1b8edf778f20ad02ed` |
| 外側 `receipt.json` | 5,322 | `9ee3aceb1bc8e1d934f67e4575b3c241f8b3113df39f225e4b82c8d6866a0389` |
| reader `attempt/reader-git/manifest.json` | 15,420 | `8b33ac146921dc500fc8c6dea9664c160c39902fb9d35f5f927aad86b43c31af` |
| publication `result.json` | 4,884 | `02bbc376f2f942f59cdd0ea6dc302d2f0670b4d44dcd1ace8987c23f5d41eecb` |
| reader `result.json` | 1,533 | `f07deda722182b7c7b1bfd299cf31a9ed4d85b3982a3b0af868cd6867fb7a95b` |
| reader `dependencies.json` | 253,449 | `b9960f06a164755b48339adf25bdcf2781bfdad68d5e3143d25bf10a7e9e1c79` |
| [別実装raw照合](../../artifacts/anomaly-v03-preformal-reader-owned-git-trial-20261005-a1/audit.json) | 302,485 | `84ef9c59f98e793a5f853c4132addd3104ecfec220a6b3b2ff852ebae94b1297` |
| [Git起動禁止の保存verifier](../../artifacts/anomaly-v03-preformal-reader-owned-git-trial-20261005-a1/saved-verifier-no-launch.json) | 682 | `f716659a4121993af7bf9f9e7c58da9df15bfc839227e7c426ad6f4a4a3c99ce` |

別実装 `audit_native.py` は製品verifierのimport前に1,244 rawを照合し、382個の別PID/start token、exit0と直接handle終了、stdout/stderr、working source/Git blob、producer48 / analysis43 / audit43 / writer32 / reader32 project fileへの保存結合が `passed`。全manifestと各direct receiptのpinは上記auditの `raw_pins` に保持する。main Gitは `C:\Program Files\Git\mingw64\bin\git.exe` 本体4,285,840 B / `6125857e3aab09c5c79b5328e7d55aedb014b3cdbd4cd60aaf47b8e13cda455b`・hardlink4に固定した。その後bare Gitと所有Gitの両起動を禁止して、製品保存verifierも `verified_retained` / `call_status=verified`。

5役は別identityで終了確認済み。Jobは計698 process・active0・limit terminated0、peak Job memory 155,148,288 B。5役rootの共有標本予算は119.5176918秒 / 上限240秒、親private peak 136,318,976 B、最大25,308,006 B / 108 entries / depth4でpass。Git session rootは5役rootの外にあり、正式同形の全工程予算の証拠ではない。Job総process数やwallの先行試走との差を性能比較へ読み替えない。

## 検証とCI

関連46試験、compileall、差分チェック、repository safetyがpass。新v7と既存v6を実Gitで検証し、Git再起動禁止の保存検証、readerのcall orderとdependency raw改変拒否を確認した。routing、独立cache、固定source15件、危険なpath、reader単独指定拒否、既存contextの挙動、6子manifest完了前の成功stdout拒否も確認した。実行コマンドはtrial rootの `implementation-checks.json` へ保存した。追加agentは作成していない。

先行保存点 `d5283e4448a53816a3c5599ce1a92eae91164b07` の [writer Ubuntu CI 37268237350](https://github.com/tyaro/banto-ai/actions/runs/37268237350) は全3 job成功。両minor各2,892件・fail0/error0/skip237・共有29 fixture/必須28試験pass、8 raw保存とローカル全journal再検証済み。[CI診断](anomaly-multiseed-v0.3-preformal-ubuntu-ci-triage-2026-10-05.md)のsummary pinへ結んだ。trial rootの `predecessor-ci.json` は終了前のsnapshot、`post-push-ci.json` はwriter成功とreader文書保存点 `bbd658d` の新run開始を記録する。今回のreader接続は新runで確認し、CI証拠追記後のpush状態を `post-ci-evidence-push.json` へ別保存する。

## 受入までの残りと実データ作業

| 事項 | 次の作業 |
| --- | --- |
| S4-3 全閉包 | Gitのloaded code・子孫、各役の完全source/runtime、独立権限、異常停止と個別終了の実機証拠を揃える |
| S4-2 共通campaign | 登録形式の保存readerから40 seed / 480区間 / 2,880評価の共通由来を完成させる |
| S4-5 全工程予算 | producerからfresh readerまで正式同形の単一予算へ結び、容量2倍を測定する |
| S4-1 / S4-4 採択と回帰 | 26H2契約改訂、runner image digest又は版付き代替同定を採択し、最終凍結revisionのUbuntu両minor / Windows native・dev8 / smoke2を照合する |
| S5～S7 | S4成立後に未使用登録holdoutを正式実行し、保存rawから完全S6独立監査・公開fresh read・結果報告を行う |

`reader_v1_git_owned=true` は今回のreader直接39回の範囲。`inner_v1_git_owned=false`、完全source/runtime false、`formal_permission=false`、正式credit0、gate `s4_acceptance_not_frozen`、S5閉鎖を維持する。実データ作業の現範囲は保存済み合成dev/smoke。今回のnative試走は架空入力のみで、登録holdoutを開いていない。
