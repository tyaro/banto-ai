# S4-B1 debug-event transport savepoint

状態: **dormant observation + owned stop / no launch**。
最新の事前検査候補: `05d65f8`。下記のtransport初回記録は`ac876b1`、比較基準`09a1150`。
production harnessとsource pinは変更していない。

## 今回の接続範囲

[DebugEventTransport](../../tests/fixtures/anomaly_v03_debug_transport.py)にx64 DEBUG_EVENTのABIと
WaitForDebugEventEx / ContinueDebugEvent / CloseHandleのbindingを実装した。
importだけではnative DLLを読まない。実起動entry、CreateProcess、attach、remote memory readはない。
testsではfake kernelだけを注入し、Windows debug APIを実行していない。

| 項目 | 実装 |
| --- | --- |
| ABI | DWORDを32-bit固定、pointer/ULONG_PTRを64-bit、DEBUG_EVENT 176 bytes、union offset 16 |
| 事前確保 | 256個のnative bufferとpointer、file-close確認・試行回数slot |
| 作成thread | bind/wait/decode/continue/closeで同じthread IDを要求 |
| Wait | 0〜100 ms、event limit 256。ERROR_SEM_TIMEOUT=121だけをeventなしと扱う |
| pending所有 | Wait呼出前にbufferを保持。decode失敗後もnative bytesを保持する |
| file handle | CREATE_PROCESS/LOAD_DLLのhFileのみ対象。API前にuncertainを記録し、明示FALSEのときだけ再試行可、最大2試行 |
| OS管理handle | eventのprocess/thread handleは手動closeしない |
| Continue | API呼出前にattempted。失敗時はuncertainで停止し、無条件再送しない |
| 例外 | 一般例外はDBG_EXCEPTION_NOT_HANDLED。breakpointは識別未実装のため拒否 |
| Exit | Continue成功はexit_continuedまで。process signaledやnative合格を主張しない |

ABIの定義は[DEBUG_EVENT](https://learn.microsoft.com/en-us/windows/win32/api/minwinbase/ns-minwinbase-debug_event)、
継続statusとOSによるhandle解放は
[ContinueDebugEvent](https://learn.microsoft.com/en-us/windows/win32/api/debugapi/nf-debugapi-continuedebugevent)を参照。
image/DLL handleの所有は
[WaitForDebugEvent](https://learn.microsoft.com/en-us/windows/win32/api/debugapi/nf-debugapi-waitfordebugevent)に基づく。

## 失敗状態の意味

Waitの成功返却前に例外が出た場合、bufferを保持するが、その中身の配送完了は未確認とする。
その状態でbuffer内の数値を無条件にhandleとしてcloseしない。上位driverはtransport自体を保持し、
未確認状態を解消したと報告してはならない。

呼出前thread照合を含め、decode/closeのMemoryErrorはresource latchを立てて停止する。
file handleのclose再試行は未解放を確定できる明示FALSEの場合だけ許す。
成功返却直後の記録前中断や、API内での副作用後例外ではuncertainを保持して再closeしない。
native file handleがcloseできなくても、そのbufferを捨てない。
運用driverは例外でtransportをローカル変数ごと失わず、private resultの寿命まで保持する必要がある。

このtransportだけではchildを止めたりdebugger終了時の状態を確定したりしない。
上位driver未接続のため、現状のclassを使って実probeを開始することは許可していない。

## 検証

- transport 13件＋既存event契約8件: 21/21 pass。
- B1の既存100件も合わせたpure/fault: 121/121 pass、0.243秒。
- D2 exact inventory: 1/1 pass、4.603秒。
- repository safety: pass。
- native/child/debugger/同一parent mutation/full suite: 今回は実行していない。

故障注入ではdecode直後OOM、Wait返却不確実、CloseHandle failure、Continue failure、
wrong thread、foreign PID、不正event、容量・待機上限、exitの段階を確認した。
このfake-kernel試験を実Windows APIの動作検証として扱わない。

## 未接続部分と次工程

1. 起動前のsource/runtime固定、新規fixture、restricted child作成との結合。
2. bootstrap breakpointの実体識別、固定された1回だけの適切な継続。
3. 累計30秒・512 MiB・private evidence 1 MiB制限を持つ上位driver。
4. primary保持、owned childの停止、bounded event drain、exit後signaled確認。
5. partial/uncertain ownershipを保持するprivate resultとsafe summary。
6. 完成driverへの故障注入、独立レビュー、初回probe実行条件の確認。

## 独立レビューと是正

同じ独立担当が9b41df5をread-only監査し、P0=0 / P1=0 / P2=2 / P3=0を報告した。
指定19件passに加え、ディスク変更なしの追加故障注入で次を再現した。

1. wait/continue前のthread照合OOMで停止latchが立たず、再呼出でAPIへ進む。
2. close成功後の記録前中断を明示的失敗と区別せず、同じhandleを再closeする。

ac876b1で両経路を修正した。2件目はAPI内例外に加え、True返却後の記録直前へ
sys.settraceでKeyboardInterruptを注入して再close禁止を確認した。
独立担当が9b41df5..ac876b1982ecf3dc5da73379a63217fca07b2f27を再監査し、
**前回P2の2件は修正確認済み、新規P0〜P3は0件**と報告した。
担当のpure試験は21/21 pass。元の反例、close中MemoryError、明示FALSE後の再試行、
True返却後KeyboardInterruptを確認した。native実行・編集はしていない。
この限定差分の確認を完成driverや実Windows E2Eの合格に拡張しない。

既知0xC0000142は未解消、Windows 3.12/required child未確認。全acceptance gateはno。

## 2026-09-08 owned-child停止controller checkpoint

34774a9で`OwnedDebugStop`を追加した。transportとresult容器をchild作成前に確保し、
未来launcherが所有するprocess/thread handleだけをadoptする。GetProcessIdで対象PIDを照合する。
launcher/attach/fixture作成/通常観測loop/初期bootstrap識別はまだ接続していない。

- TerminateProcessは非同期の要求として記録し、成功をprocess消失と同一視しない。
- pending eventは停止要求の成功後だけ処理する。追加drainは最大32回、各Waitは100ms以下、
  loop期限5秒。取得したnative bufferとimage/DLL file handleを保持する。
- wait/continueのinflight flagを別途保持し、stopによるstate変更でも不確実性を消さない。
  結果不明のContinueを再送しない。停止後の例外はNOT_HANDLEDで処理する。
- EXIT eventのContinueとowned process handleのsignaledを別々に確認する。
  未確認ならlaunch handleを保持する。解放は成否不明を先に記録し、一方の失敗でも他方を試す。
- safe resultはprivate_owner経由でprimary、buffers、未解放handleを保持する。
  要約生成自体の失敗もprimaryを上書きしない。fixture清掃・filesystem再走査は行わない。

停止要求と終了確認を分ける根拠:
[TerminateProcess](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-terminateprocess)。
これはevent/resource上限を持つ停止用部品であり、native launcherの代用品ではない。

検証: stop/transport/event 31/31、既存を含め131/131（0.493秒）、D2 1/1（6.742秒）、safety pass。
全てfake-kernel/pureで、native/child/debuggerは未実行。独立担当へ34774a9差分の監査を依頼済み。
監査結果は未受領。次は監査是正の後、起動と初期breakpoint識別、資源上限を持つ観測loopを接続する。

### 停止controllerの独立監査と是正

34774a9の独立監査でP2を2件検出した。processがsignaledの早期経路で未解決debug所有を
teardown passにする問題と、元transportのresource latchをowner/resultへ引き継がない問題である。
942c94aで、signaledとdebug_ownership_resolvedを分離し、未解決pending/inflight/file所有をfailureとして
保持するよう修正した。既存resource latchを開始時に取り込み、close/report障害後も解除せず伝播する。

追加反例: wait/continue不確実＋signaled、decode OOM後primaryを省略したstop。
修正後はstop/transport/event 33件、既存を含め133/133 pass（0.237秒）。
同じ独立担当が34774a9..942c94aa208d608f7b4703f10d8c27d059bb9b7cを再監査し、
前回P2の2件の修正と新規P0〜P3=0を確認した。担当のpureも33/33 pass。
元の反例とreport障害を追加注入し、未解決所有・resource latch・private owner保持を確認した。
native/child/debuggerは引き続き未実行。

### 有界観測loopの結合（2026-09-08）

116db41でDebugObserverを追加した。fake kernelでevent記録→hFile解放→Continue確認→
EXIT後のprocess signal確認を結合し、成功・失敗とも既存OwnedDebugStopへ所有を渡す。
通常観測は30秒未満、最大300 wait、256 event、合算memory sample 512 MiB以下を要求する。
時刻はsample前後で確認し、上限超過や既存resource latchがあれば通常観測を止める。
停止側の最大32 drain waitは別枠。これは注入されたsamplerを用いる部品であり、
実processのmemory計測・起動前確保・source/runtime pinは将来のlauncher側で接続する必要がある。

観測結果はprivate_ownerでrecorder、native buffer、終了controller、primary/secondaryを保持する。
exit code 80はchild resource stopとして通常完了させない。非zero exitを観測できても
status=observedは観測の完了だけを意味し、native_accepted/formal_permissionは常にfalse。
初期breakpoint識別は未実装で、全breakpointを通常Continue前に拒否する。
起動順から識別したと推定せず、owned停止後のdrainだけが例外を未処理として解放する。

追加12件を含めpure/fault 145/145 pass（1.070秒）、D2 exact inventory 1/1（13.689秒）、
repository safety pass。mainは889cfc3のままclean。今回もnative/child/debuggerは未実行。
独立レビューは同じ担当へ116db41の2ファイル差分に限定して依頼した。

初回監査でP2を2件検出した。recorder完了直後の中断を処理する際に二次例外が漏れる問題と、
owned stop入口の中断後に通常Continueできる問題である。abaebe6でrecorder停止の二次例外を保持し、
finally入口で通常transportを必ずstoppedにしてからowned stopへ渡すよう修正した。
pending/inflightは消さず、teardownは従来どおり所有を確認する。追加反例2件を含め147/147 pass（0.506秒）。
同じ独立担当が116db41..abaebe6fd478b8ead03056753c582cc2ba075213を再監査し、
前回P2の2件の修正と新規P0〜P3=0を確認した。担当の関連pureは47/47 pass。
元の2反例も独立再実行し、通常Continue拒否、private結果・未解放所有の保持を確認した。
完成launcher、bootstrap識別、実Windows E2Eは未確認。全acceptance gateはno。

### child作成前の記録確保とmemory adapter（2026-09-08）

38e7ebcでStartupEventsの固定slotとDebugObserver結果をPID判明前に確保可能にした。
PIDは一度だけbindする。未bindの受領、再bind、停止後bind、transportとのPID不一致を拒否する。
これにより将来のlauncherでchild作成後にrecorderを新規確保する必要がなくなる。

DebugMemoryは既存productionのPROCESS_MEMORY_COUNTERS_EX ABI（x64 80 bytes）を再利用し、
親のpseudo handleとowned child handleをGetProcessMemoryInfoに渡す。2つのnative buffer/pointerは
事前確保し、部分取得・OOM・中断・API失敗でも保持する。失敗後の再照会と通常transportを止める。
同thread、child PID、owned stop未開始、resource latchを確認する。handleは借用しcloseしない。
productionと同じPeakPagefileUsageの合計を使い、512 MiB**未満**を要求する。
前節の「以下」は38e7ebc以前の実装を指す。今回、ちょうど上限の値も拒否するよう整合した。
PeakWorkingSetSizeの合計は別に記録する。システムcommit診断と起動前preflightへの接続は未完了。
[GetProcessMemoryInfo](https://learn.microsoft.com/en-us/windows/win32/api/psapi/nf-psapi-getprocessmemoryinfo)、
[PROCESS_MEMORY_COUNTERS_EX](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-process_memory_counters_ex)

実装側pure/fault 156/156 pass（0.366秒）。Windows API実行はfake kernel/PSAPIに限る。
最初のABI test期待値88は誤りで、既存structと公式の2 DWORD + 9 SIZE_Tに合わせ80へ修正した。
独立レビューは同じ担当へ6aebb06..38e7ebcの6ファイルに限定して依頼した。

初期breakpointについて公式資料が保証するのは発生時期であり、固定の例外addressや特定exportとの
一致ではない。DbgBreakPoint exportのRVAだけからbootstrapを認定する案は採用しない。
実imageと対応するsymbol/命令位置を検証できる方法の確定が残る。全breakpoint拒否を維持する。
[Initial breakpoint](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/initial-breakpoint)

初回38e7ebcの独立監査でP2を1件検出した。前回のchild peakと今回のparent peakで上限到達が
確定してもchildを再照会し、その照会失敗でresource判定を落とす問題である。
deef50dでprocess別の確認済みpeakを保持し、各照会直後に既知合計を判定するよう修正した。
反例100+300 MiB→parent212 MiBでは3回目のAPI直後にresource stopを確定し、4回目を呼ばない。
追加反例を含めpure/fault 157/157 pass（0.341秒）。D2 1/1（4.905秒）、repository safety pass。
同じ独立担当が38e7ebc..deef50dbc98db6b82d2f3dcefd5f4941aef5365eを再監査し、
前回P2の修正、新規P0〜P3=0を確認した。関連pure 57/57 pass、元の反例も独立に再実行した。
追加照会なし、既知peakとresource latch保持を確認。実child/debugger/native APIは未実行。

### 固定source/runtime事前検査（2026-09-08）

916f908でStartupPreflightを追加した。固定allowlistはcore/child、package初期化2ファイル、
startup events/transport/stop/observer/memory/preflightの計10ファイル。
既存のbounded source/index readerを再利用し、全ファイルのdisk bytesとGit index bytesを照合する。
既存_runtimeでOS/Python/exe/DLLの固定条件を確認する。D2とproductionの2-source pinは変更しない。

事前検査は30秒未満、親peak commit 512 MiB未満、source bytes累計1 MiB以下を要求する。
既存readerの1ファイル上限は読込前に適用され、累計上限は各source読込後、index読込前に確認する。
各IO前後の予算確認に失敗すれば次の読込へ進まず、失敗時に診断目的の再読込もしない。
公開結果は固定相対path/hash/sizeとruntime情報だけで、private ownerが部分hash行と一次障害を保持する。
source bodiesを報告へ複製しない。既存readerに由来する例外/teardownはprivate primaryに保持する。

verifiedはdisk/index照合の成功だけを表す。loaded-code認証やprobe実行許可には使わず、
execution_authenticated/launch_authorized/native_accepted/formal_permissionはfalse。
将来launcherファイルを追加する際はこのallowlistにも追加し、child作成前に全体を確認する必要がある。
本番driver、fixture、CreateProcess/Resumeへの接続はまだない。

pure/fault 164/164 pass（0.321秒）。実preflight、Windows API、child、debuggerは未実行。
同じ独立担当へf059922..916f908の2ファイル差分を依頼した。

初回独立監査でP2を1件検出した。最終resource_stop書込みのOOMでprivate停止が立つ一方、
公開statusがverifiedのまま残る問題である。05d65f8でsecondary handlerにもreport_failedと
resource_stopを反映した。元の一次失敗とprivate ownerは保持する。追加反例を含め165/165 pass（0.306秒）。
D2 exact inventory 1/1（3.841秒）、repository safety pass。実preflightは依然未実行。
同じ独立担当が916f908..05d65f863d7ea89a9d4b78e475e3dab6d5866919を再監査し、
前回P2の修正と新規P0〜P3=0を確認した。指定pure 8/8 pass、sys.settraceによる元反例も再実行した。
report_failed/resource_stop=True、一次・二次例外とprivate ownerの保持を確認。全acceptance gateはno。
