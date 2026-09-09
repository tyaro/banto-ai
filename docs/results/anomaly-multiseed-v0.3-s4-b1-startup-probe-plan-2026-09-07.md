# S4-B1 startup probe 準備savepoint

状態: **dormant driver tested / read-only preflight verified / probe not run**。
2026-09-10更新: 承認によりUBR固定を記録へ変更。実10.0.26200.9445で14 sourceの事前照合が通過。
初期breakpoint識別と初回probe準備は残る。最新詳細は引継書§32と下記transport記録を参照。

## 2026-09-10 次の診断範囲の判断案（実行前）

現状のdriverは全breakpointをbootstrap_unverifiedとして拒否する。初期breakpointの
address/image/symbolを検証して正常継続する仕組みはない。既存の200件のpure/fake試験に加え、
outer driverから実際のsession/observer/transport/stop部品を通すfake統合試験を追加した。
CREATE→LOAD_DLL→BREAKPOINTを受けた後、正常な停止、Terminate失敗、停止後ContinueのOOMを確認する。
停止に成功してもdriverはfailedのままで、通常観測のexit codeへ停止処理のexitを混入させない。
ここでいう実際の部品とはPython実装であり、Win32、filesystem、runtimeはすべてfakeである。

次工程は、当初の「初期breakpointを検証してDLL初期化を観測する」範囲を維持するか、
最初の観測を次の限定範囲へ分けるかで変わる。

| 方針 | 得られるもの | 残るもの |
| --- | --- | --- |
| 当初範囲を維持 | 検証可能なbootstrap識別を実装した後、初期化中のevent観測を目指す | 識別根拠の調査・実装・故障試験が必要。継続可能性はまだ未確認 |
| 限定した初回観測（提案） | 新規childを1個だけ起動し、最初の未識別breakpointで停止。それまでのevent順序・例外codeとaddress・停止結果を保持 | breakpointが初期breakpointかどうか、以後のDLL初期化障害原因は判定しない |

限定案でもbreakpointを握り潰したり通常継続したりしない。停止処理が要求するContinueは
Terminate成功後にのみ行い、例外はnot-handledとする。時間30秒、event256件、親＋child512 MiB未満、
停止drainは最大32回/5秒の既存上限を維持し、追加probeの自動再試行はしない。
Windows条件は§31の承認済み条件を使う。既存failure rootは再利用・削除しない。

これは範囲の判断案であり、実行準備完了や実行承認ではない。限定案を選んだ場合も、次が必要である。

- raw bufferは現在private_ownerを参照しているPython process内にだけ保持される。
  fixture保持はraw eventの永続保存ではない。process終了前に有界private記録を残す手順と失敗時の扱いを実装・確認する。
- 保存対象は取得済みbufferと状態に限定する。image_name等は対象process内のpointerであり、DLL名の取得済み証拠として扱わない。
  観測後にsource/temp/remote memoryを追加読込みして欠落を補わない。
- 公開要約とprivate情報を分け、保存容量・アクセス権・停止結果の不確実性を確認する。
  メモリ不足時の永続保存成功は保証しない。
- 完成差分をfault試験・独立レビューしたうえで、実行1回の具体的な条件を提示する。

PCで別プロジェクトが連続稼働しているため、範囲の判断までは短命のpure/fake試験だけを続ける。

更新: 2026-09-08にevent transport、owned停止、有界観測loopを結合した。初期breakpointは識別未完のため拒否する。
以下は09a1150時点の計画を保持する。現在の接続済み範囲と未接続部分は
[transport記録](anomaly-multiseed-v0.3-s4-b1-debug-transport-2026-09-08.md)を参照。
基準: `673f762`（cleanup/evidence修正`9797500`の独立再監査記録済み）。
このsavepointではchild・debuggerを起動していない。受入harnessへの接続もない。

## 観測の目的と限界

次の1回の候補観測で、DLL load/unload、first/second-chance exception、exit code、
初期化前breakpoint到達の有無を時系列で保持する。
DLL load eventや最後のDLL名だけからfaulting DLLとは判定しない。
例外addressが得られても、その所在と根本原因は別である。
初期化routineがFALSEを返すだけなら、有用な例外が得られない可能性も残す。

デバッグevent受領中は対象threadが停止するため、タイミングは通常起動と変わる。
将来の観測driverでDEBUG_ONLY_THIS_PROCESSを追加しても、その結果をrequired E2Eの代用にしない。
token、desktop、環境、固定実行file、-B/-I、CREATE_SUSPENDEDは元の条件を維持する設計とする。
今回これらのflagsや引数を実際に変更した事実はない。
[Debugging events](https://learn.microsoft.com/en-us/windows/win32/debug/debugging-events)、
[Initial breakpoint](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/initial-breakpoint)

## 利用可能ツールの確認

PATHではcdb/windbg/gflags/dumpbin/Procmon/Procmon64を検出しなかった。
追加の既知path確認でWindows SDKのx64 cdb/windbg/gflagsを検出した。
これはインストールの網羅的調査ではない。

- CDB: `C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe`
- file version: `10.0.26100.7175 (WinBuild.160101.0800)`
- size: 178,536 bytes
- SHA-256: `6d5dbb10dce97d2df4e8e9cea7ca7c7a0d8cf7522835149adf184acd2ec5c02b`

実行・install・registry変更はしていない。
現段階は小さいWin32 event adapterを候補とし、CDBによるattachやloader snapsを自動fallbackにしない。
GFlagsのimage/system registry設定は対象外。
[Loader snaps](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/show-loader-snaps)

## 今回追加したoffline契約

[StartupEvents](../../tests/fixtures/anomaly_v03_startup_events.py) はIOのないテスト用部品。
native handleは受け取らず、native APIも呼ばない。将来のadapterとは未接続。

| 境界 | 契約 |
| --- | --- |
| 対象 | 固定PID 1個。別PID、重複create、不正型を拒否 |
| 容量 | 事前確保256 event slots。満杯では既存記録を上書きしない |
| 時間 | 単調経過30,000 ms未満。境界超過・時刻逆行を拒否 |
| event処理 | receive後にpendingを保持。継続API成功を確認するまで次eventを受けない |
| 終了 | exit観測、Continue成功、process handle signaledを別段階にする |
| 失敗 | stop後は再開・継続確認・完了への昇格を禁止。resource latchを解除しない |
| 公開要約 | event件数と観測exitのみ。PID/TIDを出さず、faulting_moduleは常に未特定 |

この部品はnative観測の真偽を認証しない。adapterが行っていないContinue/waitを
recorder呼出だけで代替することは禁止する。reportはallocationするためOOM handlerで呼ばない。
容量・時間・型の拒否時はadapterが停止を確定しなければならない。
eventをOSから受け取った後の所有権は、recorderに渡す前からadapter側で保持する。

## native adapterを接続する前の必須項目

1. 明示的な単一実行entryを別の診断driverとして用意し、importや通常testsで起動させない。
   source/runtimeを固定し、diagnostic driverを含む入力のpinsを記録する。D2既存pinは変更しない。
2. 新規専用fixture、事前collector、raw event buffer、owned handle slotsをchild作成前に確保する。
   既存failure rootは再利用しない。child終了を確認できないままfixture清掃へ進まない。
3. WaitForDebugEvent/ContinueDebugEventは作成threadで扱う。待機は100 ms以下で区切り、
   総時間30秒・256 events・private evidence 1 MiB・既存512 MiB資源上限を適用する。
   resource stop後はsource/temp/artifact/remote memoryを再読込しない。
4. CreateProcessAsUser由来のowned handle、debug eventのOS管理process/thread handle、
   debuggerがcloseすべきimage/DLL file handleを別の台帳で管理する。二重closeをしない。
   EXIT eventをContinueしてからowned/duplicate handleのsignaledを確認する。
5. event buffer受領直後からpending eventとfile handleを所有し、validation/allocation失敗でも捨てない。
   Continue失敗時は同じeventを無条件再送せず、診断を停止する。
6. 初期bootstrap breakpointの識別と継続規則を具体化する。単に最初のbreakpointを握り潰さない。
   それ以外の例外はnot-handledとして元の処理へ渡す。PEB/コード/SDへの書込みはしない。
7. timeout・上限・例外時は自分で作成したchildだけを停止し、残るdebug eventを処理する
   終了手順も有界にする。待機失敗を終了済みにせず、証跡と未解放所有を保持する。
8. 実運用前にABI、Continue失敗、event受領直後OOM、file close失敗、exit前後のwait、
   debugger停止時のchild停止をfake/fault試験し、独立レビューで確認する。

Win32のhandle所有とContinueによる終了解放は
[WaitForDebugEvent](https://learn.microsoft.com/en-us/windows/win32/api/debugapi/nf-debugapi-waitfordebugevent)に基づく。
公式の無限待機sampleをそのまま採用しない。
[Debugger main loop](https://learn.microsoft.com/en-us/windows/win32/debug/writing-the-debugger-s-main-loop)

## 検証と次の工程

offline試験8/8 pass。対象PID、型、容量、時刻、pending保持、停止latch、exit/Continue/wait分離、
first/second chance分離、public redactionを確認した。新規production sourceは追加していない。

次は上記adapterの実装と故障注入・独立レビュー。native probe自体の実行準備はまだ未完了である。
初回実行条件が具体化した時点で、引継書の追加probe承認条件に従う。
Windows 3.12、required child、B1受入、main統合、formal permissionは引き続き未達/no。
