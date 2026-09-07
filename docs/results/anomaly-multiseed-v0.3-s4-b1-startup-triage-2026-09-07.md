# S4-B1 child起動障害の既存証跡点検

対象: `74c42ee`。2026-09-07 23:23 JST時点のread-only調査。
結論: faulting DLLは未特定。追加child起動、ACL変更、token変更は行っていない。
本書は自己点検であり、独立レビューやB1受入ではない。

## 既存ログの検索結果

| 対象 | 範囲 | 結果 |
| --- | --- | --- |
| Application event log | 直近3日、ID 1000/1001、最大150件 | 26件を取得。query errorなし。Python/cmd該当0件 |
| ProgramData WER ReportArchive / ReportQueue | 直近3日更新、Python/cmdのAppCrash/AppHang/Critical名、各最大32 directories | 該当0件。列挙errorなし |
| LocalAppData WER ReportArchive / ReportQueue | 同上 | 両rootは不存在（PathNotFound） |

Applicationの取得イベントは2026-09-05 07:41から2026-09-07 21:55 JSTまで。
AppName/P1の実行名で絞り込み、他applicationのmessage・path・内容は記録していない。
WERはdirectory名による検索であり、任意名の全reportや他ログを網羅した調査ではない。
該当なしは「障害なし」や「WERが必ず記録しない」の証明にはならない。

## ソースと公式仕様の照合

`_start`はCreateProcessAsUserWへrestricted token、`bInheritHandles=False`、
`lpDesktop=""`、CREATE_NO_WINDOW / CREATE_UNICODE_ENVIRONMENT / CREATE_SUSPENDEDを渡す。
process/threadのsecurity attributesはNULLで、環境はSystemRoot/TEMP/TMPのみである。
今回これらの実引数は変更していない。

公式仕様では、空のlpDesktopはwindow stationの接続規則へ委ねられる。
この値だけからchildが非対話desktopに接続すると断定できない。
同じAPI資料のRemarksには既定の非対話stationという説明もあるため、
今回の空文字指定では引数固有の規則を参照し、実際の接続先は未観測として扱う。
コードの「no interactive desktop」というコメントのみ訂正した。
[CreateProcessAsUserW](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessasuserw)

接続規則は明示設定、継承handle、名前指定、logon session等を参照する。
指定も継承もないdesktopは接続stationのdefaultが選択される。
既存WinSta0/defaultへのAccessCheck成功と、失敗childがそこへ接続した実測は別である。
これからdesktop原因を断定したり、反対にdesktop関連を全面的に除外したりはしない。
[Window station接続](https://learn.microsoft.com/en-us/windows/win32/winstation/process-connection-to-a-window-station)、
[Desktop接続](https://learn.microsoft.com/en-us/windows/win32/winstation/thread-connection-to-a-desktop)

CreateProcessAsUserWの成功はDLL初期化完了を意味しない。
親がprocess/token handleを取得できたという既存記録と、その後の初期化失敗は矛盾しない。
process/threadの既定security descriptorも未測定であり、その原因性は未証明である。
[CreateProcessAsUserWの戻り値とsecurity attributes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessasuserw)

## 仮説と不足している証拠

| 仮説 | 既存記録が示す範囲 | 次に必要な証拠 |
| --- | --- | --- |
| Python/fixture固有 | cmdでも同じ終了code。Python固有原因だけでは説明が不十分 | 初期化失敗moduleとstage |
| 単純な環境不足 | 既存の2環境条件では結果不変 | module/stageを特定後、必要なら関連する単一条件の比較 |
| station/desktopへの接続失敗 | WinSta0/defaultのAccessCheckはpass。実接続先は未観測 | 失敗childの接続先または失敗したobject/API |
| token default DACL / process・thread SD | 引数とtoken検証はあるが原因性は未証明 | 実SDと失敗accessの対応 |
| その他DLL初期化経路 | 既存ログからmodule名を取得できず | 失敗module、初期化stage、関連status |

次の実行調査はcleanup/evidenceの独立レビュー後に別savepointで設計する。
目的は失敗module/stage/objectの観測であり、先にtokenやdesktop指定を変更して通すことではない。
既存failure rootsを再利用せず、追加probeの停止条件・資源上限・owned teardown・
private evidenceの保持先を具体化してから扱う。今回そのprobeを実装・実行した事実はない。

formal permission、integration readiness、native acceptanceは全てnoのまま。
