# S4-B1 Linux共有手計算fixtureの記録と照合

日付: 2026-09-11。基準 `3f3f7ad`、実装savepoint `036ecb4`。
前段の全回帰成功は[CI記録](anomaly-multiseed-v0.3-s4-b1-ci-evidence-2026-09-11.md)を参照。
本記録は選択した共有fixtureのengineering証拠であり、S4正式受入ではない。

## 変更と対象

`tools/ci_shared_fixtures.py`は既存試験の実行中にpayloadを保存する。
非capture時はfactoryを評価せず、記録のためにfixture計算を再実行しない。
`ci_test_report.py`を`ci-unittest.2`に更新し、全29 payloadの採取完了も成功条件へ追加した。
旧形式の記録は履歴として保持し、新比較器への入力としては拒否する。

| 対象 | payload数 | 比較規則 |
| --- | ---: | --- |
| Q1〜Q5 | 5 | 量子化、overlay、null、signed zero、保存JSONの完全一致 |
| M1〜M9 | 9 | matching入力・判定・episode・拒否結果の完全一致 |
| seed registry / bootstrap / accounting | 3 | registry再計算、2,000,000 bootstrap bytesのhashと選択slice、zero-alert集計の完全一致 |
| C0〜C2 profile / score識別情報 | 6 | ID・判定・丸め済み入力・保存対象の完全一致 |
| C0〜C2 profile / score数値 | 6 | 同じ型と構造を要求し、floatのみ相対/絶対許容差1e-12 |

合計29 payload、所有試験19 methods。23 payloadはcanonical JSON bytesの完全一致、6 payloadは数値比較。
任意の全fixture・全計算値を収集する仕組みではない。実seedの観測生成・campaign・性能評価を実施しない。
科学config/schema/registry、正式OS pin、srcの計算実装を変更していない。

payloadは各512KiB/合計4MiB、JSONLは16MiBまで。逐次保存し、collectorはseen IDと累積bytesだけを保持する。
上限は保存量に適用され、factory/JSON構築や既存unittest全体のメモリ使用を制限するものではない。
collectorの途中失敗はラッチし、呼出側が例外を捕捉しても採取完了に戻さない。

比較器は同一source SHA/workflow hash/run/attempt、Ubuntu24.04 x86_64、Python minorとSOABIを照合する。
予定・開始・終了ID、集計、skip理由、fixture owner・version・長さ・hash・canonical bytesを再確認する。
欠落・重複・未完了・別source・失敗/expected failure・所有試験のskipは拒否する。
class/module skipで予定methodが未開始になる記録も保守的に拒否する。将来そうしたskipを追加する場合は明示対応が必要。
SHA-256や自己記録sourceは実行者の認証を意味しない。

両試験job成功後の第3 jobが同run/attemptの2 JSONLだけをdownloadし、比較結果を新規保存する。
[download-artifact公式README](https://github.com/actions/download-artifact)のv8と`digest-mismatch: error`を使用。
JSONLと比較結果をそれぞれ限定artifactとして14日保持し、raw native evidenceを広くuploadしない。

## ローカル検証

- 比較器・captureの新規13件と既存recorder14件: 27/27 pass、1.355秒、skip0。
- 実際の所有19 methodsを1 processで選抜: 19/19 pass、37.531秒、failure/error/skip0。
- 実payloadは29/29、合計1,178,567 bytes、JSONL 1,256,529 bytes。全所有試験のpass後に完了を確認。
- YAML構造、repository safety、diff-check: pass。
- 独立差分レビュー: 新規P0〜P3指摘0。担当の試験/native/ネット接続/編集なし、進捗ポーリングなし。

synthetic比較器試験は偽のLinux metadataを使う検査fixtureで、Linux実行証拠には数えない。
実採取はこのPCのPython3.14.0で行い、`local_run_started`にWindows・基準HEAD・未commit実装のraw hashを明記。
production比較器のLinux条件を緩めたり、Windows採取をLinux結果に読み替えたりしない。
記録は`artifacts/ci-shared-fixtures-2026-09-11/local-hand-fixtures.jsonl`に保存。
テストprocessはexit0で終了。追加Windows native control、全Windows suiteは実行していない。

## CI状態

`036ecb4`を候補branchへpush済み。[CI run34546440692](https://github.com/tyaro/banto-ai/actions/runs/34546440692)で
実Linux 3.12/3.14の全回帰と第3 jobの比較結果を確認中。
本流mainの統合ではない。以降のdocs-only savepointは、実際のCI実行revisionと区別する。

## 資源と残件

ローカル検証後UTC2026-09-11T00:25:35Z: RAM空き7.97GiB、C空き107.66GiB、D空き75.36GiB。
Windows build26200.9445、boot2026-09-09T10:43:08.5000000+09:00。`resources-local.json`へ保存。
Windows Updateの状態を記録し、B1 engineeringでのUBR緩和を維持する。
点の変化だけでリーク有無を断定しない。別project、既存failure fixture、共有runtimeを操作していない。

`acceptance_status=not_completed`、`formal_permission=false`、`execution_authenticated=false`を維持。
Windowsとのpayload照合、VM image digest、全Windows native受入、正式OS条件の整合、B2 publisher/marker、
runtime closureとproducer/consumer凍結は未完了。終了済みnative追加試行枠を再開しない。
