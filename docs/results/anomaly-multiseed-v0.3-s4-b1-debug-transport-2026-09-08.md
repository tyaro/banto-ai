# S4-B1 debug-event transport savepoint

状態: **two separately authorized limited native diagnostics completed / no native acceptance**。
最新のprocess/thread権限観測準備は引継書§39を参照。c6fc191でcollector実装済み、pure/fake231件・独立レビュー・17 source preflight通過。
権限観測付き追加実機診断は未承認・未実行。offline hash照合は§38を参照。
最新は引継書§37と[image診断結果](anomaly-multiseed-v0.3-s4-b1-startup-image-probe-result-2026-09-10.md)。
image記録付き追加1回でpython.exe/ntdll.dll/kernel32.dll/KernelBase.dllを確認し、0xC0000142を再現した。
以下の次回準備/未起動という記述は、この追加実行前の履歴として保持する。
最新の次回準備は06f1e63（image identity/nameの有界取得）。pure224件・独立再監査・16 source preflight通過。
詳細は引継書§36を参照。追加の実機起動はまだ行っていない。
最新の保存記録解析は引継書§35を参照。eefae0fのoffline readerで匿名module3→2のunload対応を確認。実機の追加起動はない。
2026-09-10最新: 承認済み1回の実行で0xC0000142を再現し、7 events、process終了/所有解放、private保存を確認した。
詳細は引継書§34と[実行記録](anomaly-multiseed-v0.3-s4-b1-startup-probe-result-2026-09-10.md)を参照。
以下の未起動/承認待ちの記述は準備時の履歴として保持する。
最新候補: `b916de9`（2026-09-10）。限定案のprivate保存を接続、pure213件通過・独立再監査の新規所見0。
保存実装の試験・監査は引継書§33と初回probe計画を参照。
966723cでユーザー承認によりS4-B1のUBR固定を解除し、実測buildを記録する。
現在10.0.26200.9445で実read-only preflightはverified。下記の旧runtime停止記録は当時の状態。
productionの変更は_runtimeのUBR条件/記録のみ。source pin方式と他のruntime条件は維持する。

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

### 停止状態での作成とhandle所有移管（2026-09-08）

a73c966でSuspendedDebugLaunchを追加した。低レベル部品であり、import/constructorでは作成せず、
CLIや完成driverもない。create()を呼ぶ将来driverがpreflight/token/fixture検証を完了させる必要がある。
固定allowlistへ本部品を追加し、現時点のdiagnostic inputは11ファイルとなった。

core _startと同じ固定exe/-B/-I/child/root、最小環境、空lpDesktop、非継承handleを使い、
NO_WINDOW/UNICODE_ENV/CREATE_SUSPENDEDにDEBUG_ONLY_THIS_PROCESSだけを追加する。
STARTUPINFO、PROCESS_INFORMATION、pointer、可変command/environment、引数tuple、結果ownerを事前確保する。
API呼出前にuncertainを記録し、TRUEを確認するまで出力を有効なowned handleと推定しない。
明示FALSEでもraw出力は保持する。create再試行、通常Popen fallback、Resumeは行わない。

確認成功後にtransportへPIDをbindし、OwnedDebugStopへlaunch process/thread handleをadoptする。
移管後の中断・report失敗は既存owned stopを一度だけ試み、primary/secondary/未解放所有を保持する。
成否不確実、またはbind/adopt未完で終了を確認できない場合はraw outputとunconfirmed結果を残す。
この未解決経路があるため、部品のテスト成功だけで実probe実行可能とはしない。
fixture/tokenは借用し、清掃も解放もしない。将来driverが全所有を統合する必要がある。

pure/fault 173/173 pass（0.328秒）。API内部・TRUE直後のOOM、bind/adopt中断、初期/final report故障、
teardown中OOM、作成前resource latchをfakeで確認した。Windows API/child/debuggerは未実行。
同じ独立担当へb07094e..a73c966の3ファイルを限定して監査依頼した。

初回監査でP2を1件検出した。TRUE確認後のbind OOMでhandle未登録のstopを使用済みにし、
確定childの停止経路を失う問題である。ed12507で確認済みPIを通常bindより先にstopへ保持する。
終了時はPIからhandle/PIDを回復し、GetProcessId一致確認後にteardown用のPIDを設定する。
通常transportの停止/resource/inflightは変更しない。成否不確実なAPI出力には適用しない。
元のbind OOM反例でTerminateProcess→EXIT drain→owned handle 2件closeを確認した。
部分adoptとforeign PIDの反例も追加し、pure/fault 174/174 pass（0.367秒）。
D2 1/1（5.234秒）、repository safety pass。

ed12507の再監査で、成功後のcapture_creation自体がOOMになると同じP2が残ることを確認した。
11b7efdではAPI呼出前のconstructorでstopからlaunch owner（PIとcreation_state）への参照を接続する。
成功後に所有移譲関数を呼ばず、stopはcreation_state=createdの場合だけPIを回復する。
uncertain/failed/not_startedの出力から推測してclose/terminateしない。
成功確認直後の次行への中断注入でも既存owned stopへ到達する。修正後pure/fault 175/175（3.255秒）。
同じ独立担当がed12507..11b7efdf53775d15f829f7339a19bbafcd965250を再監査し、
P2残件の修正と新規P0〜P3=0を確認した。指定pure 30/30 pass。
成功確認直後OOM＋未終了fake processでTerminate→EXIT drain→signaled→owned handle 2件closeを独立確認した。
一次例外/private owner/通常停止を保持し、成否不確実時の推測操作禁止も維持。mainは889cfc3のままclean。

### 準備済みfixtureでのsession統合（2026-09-08）

a059067でDebugSessionを追加した。preflight、suspended create、実childのexe/PIDとtoken profile、
duplicate impersonation profile、parent AccessCheck、Resume、観測、終了を接続する。
既存coreのidentity/profile/access検証を再利用し、production harnessは変更していない。
diagnostic allowlistへsessionを追加し12ファイルとした。

sessionは事前確保済みlaunch/observerを受け取り、fixtureと親/restricted tokenは借用する。
実childのprimary/duplicate tokenだけをsessionの固定slotで所有し、終了時に1回ずつcloseする。
close前にuncertainを記録し、成否不確実なhandleを再closeしない。一次/二次例外とprivate ownerを保持する。
preflight失敗はcreateへ進まず、child検証失敗はResumeへ進まない。
Resume前にuncertainを記録し、戻り値1だけをresumedとする。再Resumeはしない。
preflight後の30秒時計をcreate前からobserver終了まで共用し、検証各段階でもメモリ/時間を確認する。

新規fixture/親restricted token作成と全体の清掃を担う外側driver、CLI、初期breakpoint識別、
system commit情報の接続はまだ残る。transportは全breakpointを拒否するため、実観測は未開始。
sessionのobservedもnative_accepted/formal_permissionはfalse。

pure/fault 182/182 pass（0.410秒）。新規7件で実行順、preflight/検証/Resume故障、検証中deadline、
token close中断、observer/report OOMをfakeで確認した。実preflight/child/debugger/native APIは未実行。
同じ独立担当へae30ac3..a059067の3ファイルに限定して監査を依頼した。

初回監査でP2を1件検出した。既存token helperがAPI取得成功後に返る前の中断で、sessionのtoken slotが
空のままになり、token_teardown=passとしてしまう問題である。cbac022でH出力buffer 2個とpointerを
session constructorに確保した。OpenProcessToken/ DuplicateTokenExは既存helperと同じ権限/型で直接呼ぶ。
API前uncertain、成功確認後acquired、slot記録を分け、確定後slot記録前の中断はbufferから解放する。
API成否不確実の出力は保持し、推測closeせずtoken_teardown=failedとする。
双方の取得API内部中断と、取得確定後slot代入前の中断を追加し、184/184 pass（0.351秒）。
D2 1/1（3.783秒）、repository safety pass。実child等は引き続き未実行。
同じ独立担当がa059067..cbac022c9e4c43d9180327016c4a1939efc6dbd3を再監査し、
P2修正と新規P0〜P3=0を確認した。指定pure 56/56 pass。
両APIの未確定所有/取得確定後のslot代入中断、一次例外/private owner、Resume抑止と二重close防止を確認した。

### システム全体のmemory情報（2026-09-09）

同PCで別プロジェクトの連続稼働試験中との指示を受け、短時間のpure/fake検証だけを行った。
作業時点のread-only確認: RAM総量31.70 GiB、空き9.83 GiB、C空き102.65 GiB、D空き75.36 GiB。
これは一時点の観測であり、別プロジェクトのmemory leak有無を判定する証拠ではない。
他プロジェクトのprocess/設定/ファイルへ変更は加えない。既存failure rootも削除しない。

b749c08でDebugMemoryに既存_Performance（x64 104 bytes）のbuffer/pointerを事前確保した。
GetPerformanceInfoのcommit/limit/physical/availableのpage数をPageSizeでbytesへ換算して保持する。
API前uncertain、全field検査/換算後confirmedを区別し、失敗時はraw bufferを保持して後続照会を止める。
新規system値は診断情報であり、既存の親＋child peak commit 512 MiB未満という判定は変更しない。
[PERFORMANCE_INFORMATION](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-performance_information)

追加故障注入はFALSE/OOM/中断、不正fieldと後続query抑止。pure/fake 186/186 pass（0.440秒）、
repository safety/diff-check pass。今回はproduction source/allowlist/D2対象を変更していないため、
前回D2結果を引き継ぎ、ディスク走査を追加実行しなかった。実native sampler/child/debuggerは未実行。
独立担当にも今回の3ファイルと関連pureの1回実行に限定した監査を依頼した。
独立担当が33f6e44..b749c08926030e9494c32f3810b05d3ea0077d1fを監査し、新規P0〜P3=0。
関連pureは1回、25/25 pass。成功sample後の部分書込みOOMでもraw/uncertain保持と再照会抑止を確認した。
終了付近の空きRAM9.45 GiB、C102.64 GiB、D75.36 GiB。併行稼働中の全PC測定のため、
開始時との差だけで本作業または他プロジェクトのリークと断定しない。今回のテストprocessは終了済み。

### 外側driverと親token所有（2026-09-09）

6d97709でDebugTokensを追加。親token、restricted token、disable SID/RC SIDの出力bufferを事前保持し、
API成功確認/不確実を区別する。flags9、privileged groups disable、RC制限はproductionと同じ。
SIDはLocalFree、tokenはCloseHandleを使い、成否不確実な解放を再試行しない。
独立監査はdf49fdb..6d97709305820f518f255e4b1e22329e7c3f8798、新規P0〜P3=0、指定pure5/5 pass。
LocalFree非NULL返却の追加反例も保持/再試行抑止を確認した。

b4c1365でDebugDriverを追加。preflight→temp空き1 GiB以上確認→親/restricted token→
新規core fixture/b1.2 request→事前確保したtransport/stop/memory/observer/launch/sessionを接続する。
事前検査済み結果はsessionで再実行せず使う。diagnostic allowlistはtokens/driverを含む14ファイル。
既存_Winのkernel32をtransportへ渡した場合にも必要なdebug bindingを設定する。

driverは通常CLIへ接続しておらず、importだけでは実行しない。実driverは今回未実行。
診断fixtureは成功/失敗とも証拠として残し、handleだけを解放する。既存failure rootには触らず、
失敗/resource stop後にfilesystemを再読込して清掃・ACL修復・削除する経路はない。
retention=unverifiedとprivate ownerを返し、観測成功をnative受入にはしない。
親tokenとfixtureはdriver所有、実child tokenはsession所有、child process/threadはstop所有。

pure/fake196/196 pass（0.482秒）、safety/diff-check pass。テストは短命processで逐次実行した。
今回の開始付近は空きRAM9.86 GiB、C102.63 GiB、D75.36 GiB。
独立担当へ6d97709..b4c1365の6ファイルに絞った監査を依頼した。

初回監査P2 1件: outer teardownがchild token不確実性とstopの未解決所有を集約せずpassとする問題。
94bbdceでsession.tokens_resolvedを共通化し、child作成状態、stop teardown、process signaled、
debug所有、launch handlesを最終判定へ含めた。元の2反例にcreate不確実も追加。
修正後pure/fake197/197 pass（0.674秒）。同じ独立担当がb4c1365..94bbdcefd44301fb52ff69305933b77e7d0282daを
再監査しP2解消、新規P0〜P3=0、指定pure41/41 pass。不確実操作の再実行はしない。

### 実read-only preflightで判明したruntime差分（2026-09-09）

StartupPreflightだけを1回実行した（0.502秒）。fixture/child/debuggerは作成・起動していない。
結果はfailed、reason=runtime_pin、resource_stop=false、sources_checked=0、source_bytes=0。
OS確認段階で停止したため、exe/DLL hashと14 sourceの実照合は未到達。
read-only registry/既存Python照会で以下を確認した。

| 条件 | 固定 | 現在 |
| --- | --- | --- |
| Windows build / UBR | 26200 / 9168 | 26200 / 9445 |
| Edition / DisplayVersion | Professional / 25H2 | 一致 |
| Python / machine | 3.14.0 / AMD64 | 一致 |
| compiler / git tag | MSC v.1944 64 bit (AMD64) / tags/v3.14.0, ebf955d | 一致 |
| free threading | 無効 | 無効 |

固定runtime条件やOSに変更は加えていない。現在OS向けの別候補条件を設けるか、元条件を維持して
実機検証を保留するかはユーザー判断が必要。現PCをダウングレードする案は採用しない。
別プロジェクト連続稼働への配慮を継続する。全acceptance gateはno。

### 承認済み更新リビジョンの記録化（2026-09-10）

自動Windows Updateに追従するよう、ユーザーが固定条件の緩和と状態記録を承認した。
966723cでUBRを有効なuint32として扱い、返却buildを10.0.26200.<実測UBR>とした。
OS release/edition/architectureとPython/hash条件、実行前後のruntime drift確認は維持する。
旧9168・現在9445・別9446の記録、異常値/別release/別architecture/Python hashの拒否をpureで確認した。
200/200 pass（1.169秒）、D2 1/1（12.838秒）、safety/diff-check pass。
独立監査d3a53f9..966723c4bf4ddcf786aeb744288a3ca88fa96211は新規P0〜P3=0、指定pure60/60 pass。

実read-only preflightでOS/Python/hash条件を通過した後、2つの初期化ファイルでCRLF/LFだけの差を検出した。
src/banto_ai/__init__.py（96→93 bytes）、tests/__init__.py（110→106 bytes）をworktree内でLFへ整合し、
内容の変更なくGit indexと一致させた。再検査はverified、14 source、172259 bytes、resource_stop=false。
観測runtime.build=10.0.26200.9445、python=3.14.0、exe/python314.dll hashは固定値と一致。
実driver/child/debuggerは未実行。UBR差分による判断待ちは解消し、初期breakpoint識別と初回probe準備が残る。
