# S4-B1 Linux CI整備・互換性修正・実行結果

日付: 2026-09-11 JST。基準候補 `e9588dc`、実装 `3c69f9ea3203313ac1b300e3e74e6607cf891262`。
本流 `889cfc3` の変更・統合、Windows native control、正式campaign実行は含まない。

**最終結果: 候補 `7870362` のLinux CIは両minorで成功。各1099 methods中1032 pass / 67 skip、
failure/error0。保存された全test ID・結果・sourceを照合済み。S4完全受入は未完了。**

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

修正版を候補branchへpushした[2回目CI run 34516991115](https://github.com/tyaro/banto-ai/actions/runs/34516991115)
も両jobでfailureとなった。1099 methods中979 pass / 67 skip / 53 methods異常、
unittest集計failure174 / error42。元のget_last_error属性欠落は解消したが、
その先のfake launch構築が `os.environ["SystemRoot"]` に依存し、LinuxでKeyErrorになっていた。
後続のdebug/evidence検査へ波及したことを3.14 job logで確認した。
compile/safety/artifact保存pass、smoke/dataset quality/benchmarkはskip。
全予定/開始/終了ID・集計・source不変・未受入flagを照合し、両minorの結果とskip記録はexact一致。

初回と別の `artifacts/ci-evidence-2026-09-11/run-34516991115/` に保存した。
各ZIPのAPI digest・単一member・サイズを確認して取得・展開。
3.12 JSONLは779772 bytes / SHA-256 `b113673d508c70f1b7f171eac465beff62ad89a5a8eb762ce9b1def26fdd4cb0`、
3.14 JSONLは779774 bytes / SHA-256 `cd6ac56c2065326351d83694813cd3ef9982e2d42b080d9e39db889736f27857`。

初回の待機接続はGitHub CLIのunexpected EOFで2回終了したが、これは試験結果ではない。
直接APIの状態を60秒間隔で記録する単一の待機processへ切り替え、CI failureを確認した。
修正後の待機も60秒間隔・query timeout30秒・最大24回で区切る。このPCで全suiteは実行しない。

## fake launchの環境変数依存を除去

追加修正 **`7870362d76eb26a6086222b3947aaa102bd22c79`**。
単体launchテストでは既に仮設定していたSystemRootを、共通fake driverでもExitStack内で
`C:\Windows` に設定する。変更はtest_anomaly_v03_debug_driver.pyの2行だけ。
テスト終了時に元の環境へ復元し、実launch部品やホストの恒久設定は変更しない。

既失敗66 methodsを、今度は `get_last_error` 不存在に加え**環境変数を空にした条件**で確認した。
WinDLL生成は拒否し、**66/66 pass、5.652595秒、failure/error/skip0**。
mock属性・環境の残留なし、元の状態への復元も確認した。実行base38bb317と変更source hashを記録する。
`linux-host-independent-regression.json`（8961 bytes / SHA-256
`eb810beb5b9c0f8b0131b3457598fda9f5e2b35debd5540a686be4db747807f5`）へ保存。
これはWindows上での不足条件の模擬検査であり、実Linux ABIを再現したとは扱わない。
独立レビュー新規P0〜P3=0、担当の試験/native/ネット接続/編集なし、進捗ポーリングなし。
safety/diff-check pass。

7870362を候補branchへpushした[3回目CI run 34518948145](https://github.com/tyaro/banto-ai/actions/runs/34518948145)
は**両job成功**で終了した。sourceは `7870362d76eb26a6086222b3947aaa102bd22c79`、attempt1。
Python3.14 jobは19:25:12Z、3.12 jobは19:27:44Zに終了、待機processは19:28:25Zに成功を確認してexit0。
このCI回数は、既に終了したWindows native controlの試行枠とは別である。

## 最終CIの検証結果

| 実Python | 予定/実行method | pass | skip | failure/error | JSONL bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| 3.12.14 | 1099/1099 | 1032 | 67 | 0/0 | 739802 |
| 3.14.7 | 1099/1099 | 1032 | 67 | 0/0 | 739872 |

両jobともexpected failure0 / unexpected success0 / stopped=false / source_unchanged=true。
compile・全unittest・manifest/naive smoke・synthetic dataset生成/quality・benchmark・safety・artifact保存がすべてpass。
最終runtimeのOS/kernel/compiler/image観測値は下記の初回値と一致する。

保存先は `artifacts/ci-evidence-2026-09-11/run-34518948145/`。
3.12 JSONL SHA-256 `1b8161b06bf518784df7ca00699e145348b16a34a5755afacd5741525f187f95`、
3.14 JSONL SHA-256 `1335a3d6c360b9a3731da606a0838c035d2a4c6b898178c1d467d51b6ac05be9`。
約78KBの各ZIPについてAPI digestと実SHA-256を照合し、単一member・展開後16MiB以内を確認した。
3.12の最初の取得だけunexpected EOFで0 bytesとなり、別名で取り直した正しいZIPを採用。
取得失敗の空ファイルを証拠として使用せず、CI自体の再実行もしていない。

全予定/開始/終了IDの重複・欠落なし、全件の結果集計とsource/workflow/run/attemptを確認。
両minor間で予定ID/順序・終了結果・skip ID/reasonがexact一致した。
3回のCIを比較しても予定ID/順序とskip67件は同一で、初回に異常だった66 methodsはすべて最終pass。
試験削除やskip追加による成功ではない。共有fixture payloadそのものの比較とは区別する。
`recovery-comparison.json`（25642 bytes / SHA-256
`7bb1ab77ea30dbd886d93af8b1dbce64af83ba7e61f01a5322b32551e7edff13`）に各版のruntime・集計・修復66 IDsを保存した。

以後の保存は記録だけのcommitで、CIが実行したrevisionは7870362のまま。
記録だけのpushで同じ全suiteを再起動しない。本流の変更・統合はない。

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

skip67件は3回のCIの両minorでID・reasonが一致した。
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
| 2026-09-10 19:15:10 | 7.19 | 107.91 | 75.36 |
| 2026-09-10 19:26:08 | 7.85 | 107.90 | 75.36 |
| 2026-09-10 19:30:17 | 7.68 | 107.91 | 75.36 |

Windows26200.9445、boot `2026-09-09T10:43:08.5000000+09:00` を記録した。
点の変化からリークの有無を断定しない。ローカルの検証Pythonは終了済み。
19:15時点のowned CI待機Pythonはprivate11.27MiB / working set15.30MiB。
19:26時点もprivate11.27MiB / working set15.40MiB。待機は成功確認後に終了した。
この待機process単体の値であり、PC全体のRAM変化をこの作業へ帰属させない。
最終観測をresources-final.jsonに保存。今回の検証・取得・照合processも終了済み。
既存失敗fixture・別project・旧artifactへの操作、新runtimeの導入なし。
