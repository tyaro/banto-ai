# v0.3 producer の直接 Git を所有した限定試走（2026-10-05）

clean source `e7432e7d2c4e5237ec6b74b791fcc141de40fdb5`、Windows 11 Pro 26H2 / build 26300.9457、CPython 3.14.0で、新しい `--own-producer-git` を実行した。入力は先行の架空 archive だけで、登録 holdout 観測の生成・読取り、正式評価 credit は0。

## 実装と完了範囲

code `a6fdfb6` で producer へ所有 Git reader を渡し、`e7432e7` で保存依存一覧の project bytecode cache 分類を修正した。新しい outer / Job invocation v3 は、子の固定26件に加えて producer 用の別 session を開く。`--own-producer-git` は `--own-child-git` の範囲も含む。v1/v2 の保存 schema は維持する。

producer の source 検査4回は各 HEAD + 9 source blob、計40件。子の before/after 依存一覧に現れた project source 48 file の Git blobは2一覧を通じて cache し、合計88件。project 内の `.pyc` は既存分類 `bytecode-cache-candidate` として扱い、source Git 対象には加えない。候補 profile loader は bare Git を使うため、この opt-in では実行前に拒否する。

外側は起動前7件・親35件・子固定26件・producer88件、**計156件**を別 manifest で保存・検証して `verified`。producer manifest は pinned owner → five-role result → producer result → invocation / child stdout / dependencies pair へ結び、対象 path・pin・順序・件数を復元して検査する。両子 session の manifest 保存後に Job子の成功応答を出す。

## 成功 root と raw pin

保存 root は `artifacts/anomaly-v03-preformal-producer-owned-git-trial-20261005-a2/attempt`。外部 policy は `artifacts/anomaly-v03-preformal-producer-owned-git-policy-20261005-a2/policy.json`。これらは Git 管理外で、同じ workspace に保持する。

| 保存 raw | bytes | SHA-256 |
| --- | ---: | --- |
| 外部 `policy.json` | 601 | `cda1eb2cb23db4fe91940599f095c5347086071c7ad618951170485146d75818` |
| 外側 `receipt.json` | 3,757 | `1c0bd2ff206d4f88e0d7feeea5fe4b87dc73fc60a5421ed1c3ea81b5a3d46de6` |
| 起動前 `git/manifest.json` | 3,399 | `9ee6200be61220e345ed559752b616076d00e06ae6cfe19b3b632a1e80fd4b87` |
| 親 `parent-git/manifest.json` | 14,303 | `49eccd74676ec9409602f9f18498095c20ce2640f7713347e83f46f79ca9e231` |
| 子 `attempt/child-git/manifest.json` | 10,802 | `a3cdcf5b0fec6975a43023a7caf71d2a31af5d98127d2234f35e49b72456f533` |
| producer `attempt/producer-git/manifest.json` | 36,945 | `a99d28f6f1aa9d7de85db42ecf6a4ce5e36f869774cab1ed42c8e63abdea9166` |
| Job owner `attempt/receipt.json` | 5,908 | `bd122f4e5cd0e82a1832185ce2890b010f731f2976d59641f940645718c29a1c` |
| producer `dependencies.json` | 300,859 | `dcd6e02c9c6683683e38c126109210c9470128d2dfe63052cd32b785292e9e35` |
| [別実装の raw 照合](../../artifacts/anomaly-v03-preformal-producer-owned-git-trial-20261005-a2/audit.json) | 132,456 | `639fb58f24517f4a87d502c067f9946082daa7befa0cf724acf2d9b4eeec2b0c` |
| [Git 起動禁止の保存 verifier](../../artifacts/anomaly-v03-preformal-producer-owned-git-trial-20261005-a2/saved-verifier-no-launch.json) | 464 | `25389621f86ba588f477662d253dff09378e5e221a50dbd36a29258dd6fbf833` |

policy は `C:\Program Files\Git\mingw64\bin\git.exe` 本体4,285,840 B / `6125857e3aab09c5c79b5328e7d55aedb014b3cdbd4cd60aaf47b8e13cda455b`を固定した。別実装の `audit_native.py` は製品 verifier の import 前に536 raw、156件の別 PID/start token、exit0と元 handle の終了、stdout/stderr、working source/Git blob、producer 子応答と48 project file の結合を照合した。その後 bare Git と所有 Git の両起動を禁止して製品の保存 verifier を実行し、`verified_retained` / `call_status=verified`。

5役は別 identity で終了確認済み。Job は計1,080 process・active0、peak Job memory 153,911,296 B。5役 root の共有標本予算は143.5860226秒、親 private peak 120,991,744 B、最大25,307,086 B / 108 entries / depth4で pass。各 Git manifest の root は5役 root の外で、この数値を正式の全工程予算には使わない。

## 初回失敗の保持と検証

clean `a6fdfb6dd7a617c839f4c9e4428e7f293066e852` の `...trial-20261005-a1/attempt` は5役が完了した後、外側の保存依存 category 検査で `owner_rejected`。producer の `.pyc` cache candidate を project source と同じ分類と想定した新 verifier の不備だった。親の最後の保存再検証7件へ進まず、7+28+26+88 =149直接 Gitを保存した。外側 receipt 3,784 B / `7e783a78720fbed90d40a77e55cd75b485f67cb312037574242791fcb0d56a8d` は変更していない。

修正版で515 rawを別照合し、[a1 audit](../../artifacts/anomaly-v03-preformal-producer-owned-git-trial-20261005-a1/audit.json) 127,291 B / `7b4834d9c03c733f9e1112b1e1661be62483aa47ea5ca624946f5305e7955224`。Git起動禁止の再検証476 B / `8f1e320e37550c03bcff78a526c3a54f3807787338c16203fc0748ae56548545` は `call_status=failed` を維持し、所有完了 flags は false。Job active0を確認した。

関連45試験、compileall、差分検査、repository safety は pass。修正後の試験には project bytecode candidate を含め、Git cache・不正 request/profile の拒否、両 manifest 完了前の成功応答拒否、保存 manifest の対象 path 改変と dependency raw 改変の拒否を確認した。先行 `400e370` の [Ubuntu CI 37246057077](https://github.com/tyaro/banto-ai/actions/runs/37246057077) は各minor2,874件と共有比較の全3 job成功で、[生 raw・再検証](anomaly-multiseed-v0.3-preformal-ubuntu-ci-triage-2026-10-05.md)を保存した。これは今回の後続実装の CI 結果ではない。

## 残る受入範囲

| 項目 | 次の作業 |
| --- | --- |
| S4-3 各役の Git | analysis / audit / writer / reader の固定 source と動的依存 Git に所有 reader を渡し、役別の pinned invocation / 応答 / inventory へ結ぶ |
| S4-3 全閉包 | Git の loaded code・子孫、各役の完全 source/runtime、独立権限・異常停止と個別終了の受入証拠を揃える |
| S4-4 最終回帰 | 最終凍結 revision の Ubuntu 両minor / Windows nativeを照合し、runner digestまたは版付き代替同定を採択する |
| S4-1 / S4-5 | 26H2 契約を採択し、producerからreaderまでの正式同形全工程予算・容量2倍を測定する |
| S5～S7 | 共通campaign / 登録40 seed由来 / 実保存登録reader、正式性能算術、完全S6と公開監査を接続する |

`producer_v1_git_owned=true` は今回の producer 親側88件の範囲。`inner_v1_git_owned=false`、完全 source/runtime false、`formal_permission=false`、正式 credit0、gate `s4_acceptance_not_frozen`を維持する。実データ作業は保存済み合成 dev/smoke の既存範囲であり、今回の trial は架空入力だけ。登録 holdout は開いていない。
