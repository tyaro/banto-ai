# S4-B1 Linux共有手計算fixtureの記録と照合

日付: 2026-09-11。基準 `3f3f7ad`、実装savepoint `036ecb4`。
前段の全回帰成功は[CI記録](anomaly-multiseed-v0.3-s4-b1-ci-evidence-2026-09-11.md)を参照。
本記録は選択した共有fixtureのengineering証拠であり、S4正式受入ではない。

**最終結果: CIの3 jobs成功。各1112 methods中1045 pass / 67 skip。29 payloadはLinux両minor間で完全一致。
同じ29 payloadのWindows選抜採取との58照合も完全一致。CI receiptを手元で再計算して一致を確認した。**

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

`036ecb4`の[CI run34546440692](https://github.com/tyaro/banto-ai/actions/runs/34546440692)は3 jobsすべてsuccess。
各minorで1112 methodsを実行し、1045 pass / 67 skip、failure/error/expected failure/unexpected success0。
未開始・重複IDなし、stopped=false、source_unchanged=true、shared_fixtures_complete=true。
compile/manifests/smoke/quality/benchmark/safety/upload、比較jobのdownload/比較/safety/uploadもすべて成功した。
前回成功CIの1099 methodsの相対順序・結果とskip ID/reasonを保持し、追加13 methodsは両minor全pass。
skip内訳はWindows固有49、optional Capstone16、Toto2ローカルartifact不存在2であり、passへ算入しない。

実runtimeはUbuntu24.04 x86_64、CPython3.12.14/3.14.7、GCC13.3.0、kernel6.17.0-1022-azure。
ImageVersion20260907.300.1は観測値で、VM image digestではない。digestはnull/not_collectedを維持する。
両minorのpayloadは各1,178,567 bytes、最大249,753 bytes。29件すべてでraw SHA-256も一致し、
今回の実結果には数値許容差を使わなければ一致しないpayloadはなかった。今後の比較規則の許容差は維持する。

3 artifactのZIPをAPI metadataの長さ・SHA-256と照合してから、所定の単一memberだけを展開した。
source SHA、workflow hash、run/attempt、全予定/開始/終了ID、集計、各payloadを再検証し、
手元で算出したcomparisonとCI receiptの全内容が一致した。
source SHAは`036ecb474dc8fd975263e0ddbb387f5763750109`、workflow SHA-256は
`a596ec774116951417b0c5fa972ff97db0a2abb5b7a87b291a5eb44ac7bc528e`。

| 保存済み記録 | bytes | SHA-256 |
| --- | ---: | --- |
| Linux3.12 unittest JSONL | 1992469 | `df8351ae7258d5196c693f35bc90666e3b254fca8aa131abbd6a25ae3dd90b99` |
| Linux3.14 unittest JSONL | 1992511 | `3390a4e74c6ab1722eaa7fb7fc779c1ad450fd7c95bbe9b8e3b7cb7496064517` |
| CI comparison receipt | 11842 | `d04d10961ae7d9b14122c3a5e9798e1faa51e060ef13ccb53adea10b850702f3` |
| Windows選抜JSONL | 1256529 | `e8422f8eb81c9e59d0c1afb0febb3316c3c19da0bc9769151ffb6a504224ed06` |
| Windows/Linux選抜照合 | 15786 | `79bb4603018b0f8c21f5d6d460c36dd40380ce15a77fe3b1f54505c8c63b72b6` |

CI記録は`artifacts/ci-shared-fixtures-2026-09-11/run-34546440692/`へ保存。
同runのJSONLからの再照合は`locally-verified-comparison.json`、取得検証は`artifact-download-verification.json`、
要約は`verification-summary.json`。前回1099件保持の検証は親folderの`regression-inventory-comparison.json`。
主要local記録の長さとhashを`evidence-index.json`にまとめた。

状態照会・取得で複数回のEOF/connection resetを観測した。接続エラーはCI失敗として数えず、CIの再実行もしていない。
最初の待機processは完了を検出してraw runを保存した後、jobs取得時に接続エラーでexit1。
完了済みrun metadataから取得だけを再開し、取得済みの正しいZIPはdigestを再確認して再利用した。
comparison-attempt1.zip、python3.14-attempt1/2.zipは取得失敗の0 bytesとして保持し、証拠には使っていない。
comparison-attempt2、python3.12-attempt1、python3.14-attempt3が検証済みZIP。最終取得/再照合processはexit0。
本流mainの統合ではない。以降のdocs-only savepointは、実際のCI実行revisionと区別する。

## Windows選抜採取との比較

既に取得済みのWindows19 methods/29 payloadを読取専用でLinux両minorへ比較し、58/58完全一致。
各payloadのhash/bytes/canonical形式、ownerと全19 passを確認し、識別情報はexact、数値部は所定許容差で判定した。
今回の数値部もraw bytesが一致した。採取時に記録した5ファイルは036ecb4のGit blobとraw hash完全一致。
基準3f3f7adから036ecb4への10ファイル差分も照合し、計算srcの変更がないことを確認した。
ローカル検証は選抜fixtureだけであり、Windows全suite/native受入・完全runtime inventoryを証明しない。
既存Windows記録を変更したり、Linux専用のproduction比較器のruntime条件を緩めたりしていない。
`windows-linux-selected-comparison.json`はこの限定比較を明記し、未受入flagを維持する。

## 資源と残件

ローカル検証後UTC2026-09-11T00:25:35Z: RAM空き7.97GiB、C空き107.66GiB、D空き75.36GiB。
Windows build26200.9445、boot2026-09-09T10:43:08.5000000+09:00。`resources-local.json`へ保存。
Windows Updateの状態を記録し、B1 engineeringでのUBR緩和を維持する。
UTC00:36:01Z: RAM7.47GiB/C107.67GiB/D75.36GiB、待機Python private18.64MiB/working25.33MiB。
00:30時点のprivate18.61MiB/working25.22MiBと大幅な増加はなかった。
最終UTC00:46:47Z: RAM8.55GiB/C107.67GiB/D75.36GiB、build/boot同一。`resources-final.json`へ保存。
今回のローカル試験・待機・取得・照合processはすべて終了しており、バックグラウンド処理は残していない。
点の変化だけでリーク有無を断定しない。別project、既存failure fixture、共有runtimeを操作していない。

`acceptance_status=not_completed`、`formal_permission=false`、`execution_authenticated=false`を維持。
選択範囲外のplatform間検査、VM image digest、全Windows native受入、正式OS条件の整合、B2 publisher/marker、
runtime closureとproducer/consumer凍結は未完了。終了済みnative追加試行枠を再開しない。
