# S4-B1 Linux CI環境の固定とunittest記録

日付: 2026-09-11 JST。基準候補 `e9588dc`、実装 `3c69f9ea3203313ac1b300e3e74e6607cf891262`。
本流 `889cfc3` の変更・統合、Windows native control、正式campaign実行は含まない。

## 変更

Linux共通CIのOS labelを `ubuntu-latest` から `ubuntu-24.04` に固定した。
CPython3.12/3.14の2 jobsを維持し、片方の失敗で他方を自動キャンセルしない設定にした。
GitHubの[runner image資料](https://github.com/actions/runner-images#available-images)が案内する
明示OS labelを使う。これはOS系列の指定であり、VM image全体の不変なdigest pinではない。

`tools/ci_test_report.py` は従来と同じ `tests/` 全体・top-level repositoryのunittest discoveryを実行する。
特定のv0.3 fixtureだけへの置換や、任意のtest名で受入対象を省く引数は追加していない。
Linux Ubuntu24.04 x86_64 / CPython3.12・3.14 / 通常GILを確認し、このWindows PCではdiscovery前に拒否する。

実patch/build/compiler/SOABI、kernel/architecture、Git clean HEAD、workflow hash、
GitHub run/attemptと、全予定test ID・各開始・各結果・各終了をJSONLへ逐次記録する。
workflowの起動SHAと実checkoutのSHAを照合し、終了時にもsourceのclean状態と同一性を確認する。
成功・失敗・error・skip理由・expected failure・unexpected successを分ける。
class fixtureの失敗も保持し、subtest失敗は親test IDとordinalで記録する。任意のsubtest引数・例外本文はJSONLへ入れない。
通常のunittest console出力は従来どおりCI logへ出す。

記録先は `artifacts/ci-tests/unittest.jsonl` 1ファイル。新規作成のみ、最大16MiB、各行をflushする。
保存上限はunittestが保持する失敗tracebackやJSON構築時のメモリ全体の上限ではない。
予定ID重複・0件・10,000件超、記録上限、書込み失敗、source不整合を成功扱いにしない。
途中の例外や強制中断で `run_finished` がなければ記録は未完了である。
明示的なunittest停止要求がある場合は `stopped=true / unittest_success=false` と非0 exitを返す。
`run_finished` はrunnerから戻った記録であり、その有無だけで全件passやS4受入と判定しない。

CIは失敗後もrepository safetyを試行し、unittest JSONLだけをminor/run/attempt別に保存する。
保存期間14日、ファイル欠落はerror。設定は[upload-artifact公式資料](https://github.com/actions/upload-artifact#usage)を参照した。
生成データ・旧artifact・private reportの一括uploadは行わない。
smoke、dataset quality、benchmark、safety等の全工程の成否はCI job logと併せて確認する。

## ローカル検証・独立レビュー

新規記録処理の合成テストは初回12件pass。
独立レビューで、unittestが `stop()` して未実行ケースを残したときに成功と判定できるP2を1件検出した。
`shouldStop`を成功条件から除外し、停止フラグを記録するよう修正した。
2件中1件で停止・未実行維持・成功false・main exit1の回帰と、通常test failureのmain exit1を追加した。
修正後14/14 pass、1.037秒。再レビューで当該P2是正、新規P0〜P3=0を確認。
担当はread-only差分レビューだけを実施し、native/API query/試験/編集なし。進捗ポーリングなし。

既存SourceCollectorTestsの2件もpass、0.550728秒。
workflowがsource inventoryへ入り、未追跡・欠落・改変・履歴不足で拒否されることを模擬Git/専用tempで確認した。
計16個の異なるtest methodを検証した。これはこのPCでの全回帰試験ではない。
実CLIのWindows拒否は想定どおりexit2、標準出力なし、report領域の追加なし。
workflowをYAMLとして読み、OS・両minor・helper呼出・always safety・保存対象を照合した。
repository safety / diff-check pass。sourceの改行はrepositoryのLF方針にそろえた。

`artifacts/ci-evidence-2026-09-11/local-checks.json` にtest IDs・実条件・各source hash・結果を保存。
3159 bytes / SHA-256 `be688c8b9540565cdc0ed5a117761f4ac886d398ee8c5d95390a59211971b74d`。
14件と2件は別実行で、記録にも分けてある。helperの合成テストは実Linux受入を意味しない。

## GitHub CI

検証済み候補を `codex/s4-b1-windows-engineering` としてGitHubへ保存した。
push対象は新規候補branchのHEAD `3c69f9ea3203313ac1b300e3e74e6607cf891262`。
mainへのmerge、force push、正式受入flagの変更はない。
[初回CI run 34514721185](https://github.com/tyaro/banto-ai/actions/runs/34514721185) は両jobともfailureで終了した。
両方1099 methods実行、966 pass / 67 skip / 66 methodsで異常。
unittestの集計はfailure1 / error261で、subtestの複数errorと後続assertを含むためmethod数ではない。
compile・repository safety・artifact保存はpass、smoke・dataset quality・benchmarkは前段失敗によりskip。

259個の直接errorはfakeテストの `patch.object(ctypes, "get_last_error", ...)` が
Linuxにない属性を既存と仮定したためのAttributeErrorだった。
共通driver/evidenceの利用先へ波及し、後続の未設定変数error2・呼出回数failure1も発生した。
3.14 job logを取得して原因を照合。両minorの予定IDと順序・終了結果・skip記録はexact一致した。

| 初回保存物 | JSONL bytes | JSONL SHA-256 |
| --- | ---: | --- |
| Python3.12 | 787242 | `42a4eea57b66614be384c83f6862d5f095078a86ce531578c36a61fba5692d1e` |
| Python3.14 | 787185 | `07be14c44207553b8815d1e14959a213cd1f79f71fcc710ccc1714cba5af45d9` |

各ZIPは約79KB。GitHub APIのartifact digestと取得ZIPのSHA-256を照合し一致した。
展開前に単一member `unittest.jsonl`・16MiB以内を確認し、専用のminor別保存先へ格納した。
source SHA、workflow hash、run/attempt、開始・終了各1件、全予定/開始/終了ID、
件数、結果集計、source不変、未受入flagを逐次読取りで照合した。未開始methodは0。
初回のZIP、JSONL、API metadata、job logと照合記録はignoredの `artifacts/ci-evidence-2026-09-11/` に保持する。

## Linuxでのfakeテスト修正と再検証

修正savepoint **`9846f52775cc5841fca63430adac7216cfbe516c`**。
test_anomaly_v03_debug_driver/evidence/images/security.py、test_anomaly_v03_windows.pyの
5ファイル8箇所のmockへ `create=True` を追加した。
Linuxで存在しない属性もmockの有効期間だけ作成し、終了後に元の状態へ戻す。
期待値・検査対象・実装・native skipは変更していない。

初回に異常だった66個のmethodをJSONLから特定して選抜した。
このPCのPython3.14.0の専用検証processで、`ctypes.get_last_error` を一時的に除去し、
WinDLL生成を明示拒否した条件でも **66/66 pass、5.648702秒、failure/error/skip0**。
終了時にmock属性が残らないことを確認し、元の関数をfinallyで復元した。
これはLinuxの完全再現やWindows native受入ではなく、関数不存在のfake回帰確認である。
`linux-mock-regression.json`（9393 bytes / SHA-256
`e60b1b29b00b37fc150fc8a4bf3157f13352dc767b44a4c8a4fc254558e8eb2c`）へ
test IDs・各変更source hash・実条件・結果を保存した。
独立レビュー新規P0〜P3=0、担当の試験/native/ネット接続/編集なし、進捗ポーリングなし。
repository safety / diff-check pass。

修正版を候補branchへpushし、[修正後CI run 34516991115](https://github.com/tyaro/banto-ai/actions/runs/34516991115)
が9846f52に対して開始された。開始確認時in_progress。結果と新artifactを確認する。
初回失敗の記録を上書きせず、新runの証拠は別に保存する。

初回の待機接続はGitHub CLIのunexpected EOFで2回終了したが、これは試験結果ではない。
直接APIの状態を60秒間隔で記録する単一の待機processへ切り替え、CI failureを確認した。
修正後の待機も60秒間隔・query timeout30秒・最大24回で区切る。このPCで全suiteは実行しない。

## 観測したruntimeとskipの分類

初回の実環境はUbuntu24.04 x86_64、kernel `6.17.0-1022-azure`、
CPython **3.12.14 / 3.14.7**（両方GCC13.3.0、通常GIL）。
ImageOS `ubuntu24` / ImageVersion `20260907.300.1` を両jobで観測した。
正式Windows3.14.0 pinにこのLinuxのpatch値を適用しない。

| skip分類 | 各job件数 | 解釈 |
| --- | ---: | --- |
| Windows固有の公開45・junction1・置換trace1・native control2 | 49 | Linux上の明示skip。Windows受入での成功証拠にはならない |
| optional Capstone未導入によるoffline unwind | 16 | stdlib CIで未実行。既存Windowsの固定5.0.7選抜証拠とは分ける |
| Toto2のローカルartifact不存在 | 2 | 過去artifactの照合が未実行。新規生成・取得はしておらず、passと数えない |

skip67件は初回両minorでID・reasonが一致した。
Toto2の2件を含め、skipを受入済みに読み替えない。

## 受入として残る条件

開始・終了記録の `acceptance_status` は `not_completed`、`formal_permission` はfalseである。
ImageOS/ImageVersionは観測値として保存するが、VM image digestを導出したとは扱わない。
`runner_image_digest=null / runner_image_digest_status=not_collected` を明示する。
所定imageの厳密な同一性、必要なskipの分類、共有fixtureの両minor exact比較、
Windows3.14.0の全native受入、正式OS条件、B2、runtime closureとconsumer凍結は別の残件である。

## PCの資源・保全

| 観測UTC | 空きRAM GiB | C空き GiB | D空き GiB |
| --- | ---: | ---: | ---: |
| 2026-09-10 18:16:03 | 7.73 | 107.94 | 75.36 |
| 2026-09-10 18:31:02 | 8.09 | 107.93 | 75.36 |
| 2026-09-10 18:55:08 | 8.13 | 107.91 | 75.36 |

Windows26200.9445、boot `2026-09-09T10:43:08.5000000+09:00` を記録した。
点の変化からリークの有無を断定しない。ローカルの検証Pythonは終了済み。
既存失敗fixture・別project・旧artifactへの操作、新runtimeの導入なし。
