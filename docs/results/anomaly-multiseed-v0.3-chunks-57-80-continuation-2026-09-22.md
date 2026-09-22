# v0.3 完了済み57区間からの24区間継続

2026-09-22 JST。**現在は実行中であり、新規144評価の成功は未確定。** ユーザーの次工程への指示に基づき、保存点d3eda57942e2ca4cab68ad9c95ebf967238f555aと最新closedを照合し、`continue --max-chunks 24`を起動した。対象はchunk57〜80の24区間だけ。成功時は累計81区間/486評価、next81、残り39区間/234評価となる。実装変更なし。

## 開始確認と外部pin

実計算source/consumer/controllerはclean **c01d1c978f78bab51391392d56cdcb7aab5afaab**、`C:/Users/TKent/.codex/worktrees/v03p/banto-ai`。同じ`artifacts/v03-runs/r1`を閉鎖記録から継続する。今回のcontrolは000005。prepared raw SHA-256 **be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7** は不変。

開始closedは **`run/control/000004/closed.json`** / raw SHA-256 **f21ca40084af17fc0d961c529963c984ccd80d2b0cfea7803fab30c1ce7382a6**。journal171/next57/yielded、累積活動56201.874418秒から継続する。実行中にこの開始pinを使って重複起動しない。前回controller PID6872/collectorは終了済みで再実行しない。

前回manifestは候補`artifacts/chunks-33-56-continuation-2026-09-22/savepoint-evidence.json`、10290 bytes/SHA-256 **6f734135d9712a477fef2b2a88b5b234e47701737139324e7c941f8a8a21ef77**。記載48ファイルとmanifestの計49件を照合し、前回runの3679 files/7572651569 logical bytesはhash・一覧とも完全一致。追加invocationファイルと関連計算processが起動前にないことも確認した。

preflight UTC2026-09-22T09:43:30.024540+00:00、空きRAM13012176896/C165135929344/D119511711744 bytes。Windows11 Pro25H2/AMD64/26200.9457/local NTFS、CPython3.14.0/MSC1944/source v3.14.0:ebf955dとexe/DLL hashは前回と一致。Windows Updateはengineering実値記録で許容し、旧正式pinは不変。本流D:/develop/banto-aiは889cfc3/clean、実計算sourceはc01d1c9/clean。既存dirty親policy文書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保全・commit除外。

## 起動・監視・途中保存

候補`artifacts/chunks-57-80-continuation-2026-09-22`に起動記録と外部証拠を保存する。controller PID **39544** / 開始UTC **2026-09-22T09:45:32.9678597Z**（JST2026-09-22 18:45）。非表示background processで起動し、PID・開始日時・wrapperコマンドを照合した。実argv/runtimeはrequest.jsonへ保持する。前回wrapperのcontrol番号・開始pin・区間範囲だけを更新した。

wrapperは60秒ごとにcontroller private/peak、空きRAM/C/D、journal段階を記録し、区間ごとのverified receipt（sequence174〜243）を外部保持する。中間receiptはclosedの代用にしない。既存heartbeat **banto-24** を今回のFOLLOWUP.mdへ更新・再開した。30分ごとに1回だけ確認し、新規6/12/18区間の節目でこの結果文書とcurrent-handoffを中間保存する。追加agent、短い間隔の進捗poll、過去成果物の繰返し数値再計算は行わない。

## 予算と完了条件

前回実測では既存33区間の確認を含む最初の新規区間の開始が6273.6〜6333.7秒、fresh inspection65.347秒。単純換算は既存1区間188.1〜190.0秒、新規1区間875.5〜878.0秒。今回は既存57区間の照合に約3時間、新規24区間を含め31801〜31965秒（約8.8〜8.9時間）、追加保存約3GiBを見込む。

48時間候補予算の残り活動時間116598.125582秒（約32.39時間）。仮に残り63区間を24/24/15に分ける線形試算は累積約43.69〜43.85時間だが、固定費、layout/seed差、inventory増加、再試行・遅延を分離しておらず保証ではない。**今回の上限は24区間のみ**。32GiB候補出力上限、空きRAM4GiB/disk20GiBの開始条件、controller private2GiBの境界検査、producer/auditの既存所有process上限を維持する。全体上限は協調的な境界検査で、process treeの強制上限ではない。

終了後はexit0/yielded/新規24/next81を確認し、collect.pyのIO/hash照合を1回実行する。全所有process終了、各監査、前回3679ファイル不変を確認し、5文書の最終保存（長い引継書§140）とfinalize_evidence.pyを完了してheartbeatを停止する。異常終了でも記録を保全し、成功専用collectorや未閉鎖invocationを再使用せず判断点を報告して停止する。追加invocationは自動起動しない。

campaign加算0/正式許可false、独立監査は保存score以降のみ。完全runtime inventory/独立S6、全120区間/holdout/性能評価、Phase 2/3全体の完了は追加しない。保護ProgramData roots/principal/SAM参照、UAC/ACL/service/task/VM変更、push/merge/CIなし。

## 中間保存: 新規6区間の節目

UTC2026-09-22T13:54:34.490327+00:00（JST22:54）の診断で、新規7区間/42評価（chunk57〜63）のverified receiptを保持し、累計64区間/384評価となった。journal193の最新状態はchunk64/attempt1/running、経過14940.8秒。PID39544の開始日時・wrapperコマンドが起動記録に一致し、同じcontrollerが継続中。stdout/stderr/console-stderrは空で、終了報告はまだない。

空きRAM12935745536/C163327361024/D119511687168 bytes、controller private125571072/peak231378944 bytes。資源に余裕があることを確認し、6区間の節目としてこの文書とcurrent-handoffだけを中間保存する。対象節目・観測値・commitは今回の外部followup-state.jsonへ保持する。次の中間保存は新規12区間到達後。中間receiptは未閉鎖control000005の再開pinに使わず、今回全24区間の終了・最終照合は未完了として扱う。

## 中間保存: 新規12区間の節目

UTC2026-09-22T15:28:42.991649+00:00（JST2026-09-23 00:28）の診断で、新規13区間/78評価（chunk57〜69）のverified receiptを保持し、累計70区間/420評価となった。journal212の最新状態はchunk70/attempt1/saved_pending_verification、経過20589.2秒。PID39544の開始日時・wrapperコマンドが起動記録に一致し、同じcontrollerが継続中。stdout/stderr/console-stderrは空で、終了報告はまだない。

空きRAM13024149504/C162465112064/D119511662592 bytes、controller private154185728/peak231895040 bytes。資源に余裕があることを確認し、この文書とcurrent-handoffだけを中間保存する。最初の6区間の節目は8f2358705e2a525947ac37d8afccb364db60c957で保存済み。各節目のcommit・観測値は今回の外部followup-state.jsonへ保持する。次の中間保存は新規18区間到達後。未閉鎖状態の再使用や追加起動は行わず、今回全24区間の終了・最終照合は未完了として扱う。

## 中間保存: 新規18区間の節目

UTC2026-09-22T16:31:48.312054+00:00（JST2026-09-23 01:31）の診断で、新規18区間/108評価（chunk57〜74）のverified receiptを保持し、累計75区間/450評価となった。journal226の最新状態はchunk75/attempt1/running、経過24374.5秒。PID39544の開始日時・wrapperコマンドが起動記録に一致し、同じcontrollerが継続中。stdout/stderr/console-stderrは空で、終了報告はまだない。

空きRAM12878155776/C159643848704/D119511638016 bytes、controller private133644288/peak231895040 bytes。資源に余裕があることを確認し、この文書とcurrent-handoffだけを中間保存する。6/12区間の節目は8f2358705e2a525947ac37d8afccb364db60c957/ba25ca0b88a8431f2ac7bb41692bc1846465ba17で保存済み。各節目のcommit・観測値は今回の外部followup-state.jsonへ保持する。次は今回の全24区間が終了した後に最終照合・保存を行う。未閉鎖状態の再使用や追加起動は行わず、今回全24区間の終了・最終照合は未完了として扱う。
