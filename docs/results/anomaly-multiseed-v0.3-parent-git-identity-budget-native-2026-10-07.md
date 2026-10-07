# v0.3 親HEAD/clean確認のGit Job・共通予算接続（2026-10-07）

## 範囲と状態

code保存点 `9ddaed7b6aa63c0e12f036da5d4e828caddb819c`。generation-publication callerのpreflight/postflightにある親HEAD・clean確認の4呼出しを、callerの外部exe/環境/revision/policy pin・元handle identity・private Git Job・終了・保存receiptへ結んだ。親のblob照合、各worker内のGit、外部program/helperの実ロードcode・DLL/CRT、業務workerの異常子孫回収は残る。

`s4_acceptance_not_frozen`、`formal_permission=false`、正式credit0、登録holdout観測未読。7役native343c863や旧CI証跡は保全し、今回のcodeへ読み替えない。heartbeat banto-10はPAUSEDのまま。追加agent0、全7役nativeの反復0。

## 実装

[親Git identity](../../src/banto_ai/anomaly_v03_preformal_parent_git_identity.py)は新root作成前にpolicy raw pin/full revision/絶対path・測定rootからの分離とprivate Job opt-inを要求する。生成callerの任意 `parent_git_identity_policy` を実source境界へ渡す。preflightの2保存receipt欠落を生成開始前に拒否し、postflightで正確な4呼出し・raw pin・operation・Job終了を再照合してcheckedを設定する。

[Git Job executor](../../src/banto_ai/anomaly_v03_preformal_owned_git_job.py)の任意stop probeは、receipt root作成前、assign後のresume前、実行中に共通予算の停止を確認する。resume前の停止はsuspended treeを止め、実行中の停止はJobを終了・empty accounting/root exitへ結ぶ。観測失敗も停止し、未回収・未closeなら元handleを保持する。各Git呼出し10秒、head128 B/status64 KiB/stderr64 KiB、元Job制約を維持する。直接handle policyへstop probeを渡すsilent fallbackは拒否する。

任意optionなしのsource境界は従来のHEAD不一致時short-circuitとblob比較を保持。4 receipt directory＋各stdout/stderr/receiptは16 entry、file配置深さ2で、既存outer leaf1 MiB/32 entry/深さ2に収まる。共通321 MiB/672 entry/深さ12、親512 MiB、開始空き4 GiB commit/RAM・10 GiB diskは変更しない。

## 焦点試験

74件、9.465秒、fail0/error0/skip0、対象13 source/test/科学pin一致、safety PASS。停止前の起動拒否、resume前/実行中のJob停止、未回収handle、receipt/stdoutの結合、policy差替え・root内policy拒否、preflight欠落時の生成拒否、default経路を確認した。初回52件の例外名期待違い（ValueError基底を期待、実際はV03ValidationError）を保存して修正。69/71/72件の先行試行は74件へ加算しない。

## clean HEADの限定native

既存の `_source` 境界を使用し、前後の4 Git Jobと残る選択blob照合を一つのEnvelopeBudgetで測った。生成/reader/算術/publicationの業務workerは起動していない。nativeは1回、wall上限を90秒へ締め、tracked編集は実行終了後まで行っていない。

| 呼出し | 元PID | 秒 | Job member数 | 終端 |
| --- | ---: | ---: | ---: | --- |
| preflight head | 40540 | 0.057522 | 3 | exit0 / active0 / handles closed |
| preflight status | 40084 | 0.054638 | 3 | exit0 / active0 / handles closed |
| postflight head | 41952 | 0.057134 | 3 | exit0 / active0 / handles closed |
| postflight status | 45988 | 0.082112 | 3 | exit0 / active0 / handles closed |

4つの元creation identity/start tokenを保存・照合。各Job accountingの3 member終了であり、個別子孫exit codeやロードcodeの認証ではない。共通8.664910/90秒・sampler終了、親peak25,927,680 B、測定max16 entry/11,328 B/dir depth1。終端のresult/budgetを含むouterは18 entry・file配置深さ2。最低commit9,135,235,072 B、RAM8,973,004,800 B、disk391,460,765,696 B。選択65 sourceのworking/Git・前後pin一致。全7役の新native・正式全工程・容量2倍は未確認。

## 保存証拠

rawは `artifacts/preformal-parent-git-identity-20261007-prep/`、native rootは `artifacts/anomaly-v03-preformal-generation-publication-git-id01/`、外部policyは `artifacts/preformal-parent-git-identity-policy-20261007-01/`。別保存checkerはGit Job receipt・stdout/stderr・policy/result/budgetの15 fileと65 working/保存点Git sourceを照合し、数値/生成/Jobを再実行していない。

| 保存物 | bytes | SHA-256 |
| --- | ---: | --- |
| identity-result.json | 21718 | `19ed84e9a65c928deab35dc785c490195ca5e4ab04364ad6c4107b92fb33a85f` |
| resource-budget.json | 4361 | `38d8cbc241a192c3dfa9cd24c1833c5860ead7fe9477f383a500102f403d8388` |
| 外部policy.json | 626 | `93bbdf3aa88adf4391e5563d5edc870d99dfeb9fd7bdb313457af77c7fcfd0e9` |
| focused-final.json | 2149 | `ec63559265095ff468168e700d3aaadd8c1d43b68f8c6c823ba93d0d8aa17cbb` |
| saved-check.json | 3431 | `5e275282100ee9acad1cf89ee535521be768b6f60fca8be713673d6427f439d4` |

同codeの[CI37559835322](https://github.com/tyaro/banto-ai/actions/runs/37559835322)は文書保存時in_progress。旧CIの成功を代用しない。次はこのCIの保存・照合と、残るblob/worker内Gitの実使用境界を、元entry/depth/log上限に収める保存形式へ結ぶ。Git/helperのロード依存と業務worker異常子孫、正式契約/入力consumer/最終受入/容量2倍は残る。
