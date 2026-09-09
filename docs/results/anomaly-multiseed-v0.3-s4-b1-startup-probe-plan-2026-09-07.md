# S4-B1 startup probe 準備savepoint

状態: **two separately authorized limited probes completed / startup failure reproduced / no native acceptance**。
次の未測定項目は[process/thread権限観測案](anomaly-multiseed-v0.3-s4-b1-process-security-plan-2026-09-10.md)に整理した。
読取りcollectorはc6fc191で実装済み。pure/fake231件・独立レビュー・17 source preflight通過（引継書§39）。
権限観測付き追加実機診断は未承認・未実行。保存記録のhash照合は引継書§38を参照。
最新: image identity/name付き追加1回を承認の上で実行し、4 image名と0xC0000142を記録した。
詳細は引継書§37と[image診断結果](anomaly-multiseed-v0.3-s4-b1-startup-image-probe-result-2026-09-10.md)を参照。
以下の準備中/未起動という記述は、この追加実行前の履歴として保持する。
次回向けimage identity/name観測の準備は末尾の2026-09-10追加案を参照。追加実機起動はまだ行っていない。
最新候補06f1e63はpure224件・独立再監査を通過。16 sourceの実read-only preflightもverified。詳細は引継書§36。
実行後の別工程による保存記録解析は引継書§35と下記実行記録を参照。追加probeは行っていない。
2026-09-10最新: 実行1回の承認を受け、2.346秒で0xC0000142と7 eventsを記録した。
breakpoint/exceptionは観測されず、終了・解放・private記録Write/Flushを確認した。
詳細は[実行記録](anomaly-multiseed-v0.3-s4-b1-startup-probe-result-2026-09-10.md)と引継書§34を参照。
以下の準備/承認待ちの記述は今回の実行前の履歴として保持する。

2026-09-10準備時の追記: ユーザーの「続けてください」を受け、下記限定案で保存処理の準備を進めた。
これは準備継続の指示として扱い、実childは起動していない。
2026-09-10更新: 承認によりUBR固定を記録へ変更。実10.0.26200.9445で14 sourceの事前照合が通過。
限定案の保存実装と初回実行条件は下記、最新の試験・監査・実preflightは引継書§33を参照。
初期breakpointの識別/継続は限定案の対象外で、全拒否を維持する。

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

## 限定案の保存実装と初回実行条件（2026-09-10）

DebugEvidence / EvidenceFileをdriverへ接続した。private記録は
新規fixtureのcontrol/startup-evidence.binに保存する。既存rootは使わない。
起動前に空のprivate fileをledgerへ追加し、その後にb1.2 requestを生成する。
保存先はprotected DACLのprivate方針で、取得handleからidentity/SD/stream/空sizeを検証する。
共有はreadのみ、同期write用handleを起動前から保持する。所有者/adminへの不変性は保証しない。

観測後はパス・source・temp・remote memoryを再読込みせず、既存ローカルbufferから記録する。
通常event256枠と停止drain256枠を別領域で保存し、未確認枠を含めた全事前bufferをコピーする。
confirmed count、pending、wait/continueの不確実性、file close状態をmetadataへ含める。
source/runtime、nonce、driver/observer/stopの公開状態も保存する。例外message/tracebackは含めない。
rawに含まれるaddressやpointerは値だけで、指示先の内容・DLL名を取得したことにはしない。

保存formatはlittle-endianの24-byte header（magic B1DBG001、metadata長、event size176、
region当たり256枠、region数2）、ASCII JSON metadata、通常raw領域45,056 bytes、
drain raw領域45,056 bytesの順。metadata最大65,536 bytes、全体最大155,672 bytes。
固定bufferとWriteFileの出力領域はchild起動前に確保する。
metadataのdriver結果は保存write/flush/file close前であることをresult_scopeへ明記する。
保存それ自体の成功・close結果をそのファイル自身で証明することはしない。

WriteFileは1回、全長確認後にFlushFileBuffersを1回だけ実行する。部分write・API失敗・OOM・中断では
確認できた段階を保持し、上書き/再試行/削除しない。flushedは両APIの成功確認でありreadbackや耐障害性の保証ではない。
最後に保持fileをcloseし、未解放/close失敗をouter teardownへ集約する。初期化途中の所有不確実性も成功扱いしない。
resource latchが立っていたらsnapshot/writeを始めず、既存のprivate_ownerを保持する。
この場合や途中保存失敗では、Python process終了後の完全な証跡保持を保証しない。

初回実行として提示する条件は以下。

1. 独立レビュー後のcommitを固定し、15 sourceのread-only preflightを確認する。
   OSは承認済みの26200/Professional/25H2条件と実UBR記録を用いる。
2. 同PCの空きRAM/C・D残容量を確認し、別プロジェクトの負荷が増えている場合は起動を見合わせる。
   既存のtemp空き1 GiB以上・親＋child512 MiB未満も維持する。
3. 実行は明示呼出1回、新規fixtureとrestricted child1個、通常観測30秒/256 eventsまで。
   最初の未識別breakpointで停止し、初期breakpointだったと断定しない。
4. 停止はowned childだけ。drain32回/5秒上限、停止結果が不明でも再試行しない。
   通常Popen、elevation、ACL緩和、loader snaps、追加DLL probeへのfallbackはない。
5. 実行結果は診断として記録し、native受入・main統合・formal permissionへ昇格させない。
   bootstrap_unverifiedによるdriver failedは限定範囲の停止理由として区別する。

実行前の承認確認は、この1回のrestricted child診断を対象とする。限定案の準備承認とは分ける。

b916de9で実装を保存。pure/fake213/213、独立再監査の新規P0〜P3=0。
commit後の15 source / 186,269 bytesの実read-only preflightはverified。
同期bufferの寿命と全長確認は[WriteFile](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-writefile)、
保存用handleのGENERIC_WRITE要求は[FlushFileBuffers](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers)、
共有/既存file openの指定は[CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)の仕様を参照した。

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

## 2026-09-10 追加案: event file handleのidentity/name記録

前回は7 eventとraw pointerだけを保存し、offline解析で匿名module3→2のunloadを対応付けた。
DLL名を後から推定せず、次回用のDebugImages collectorを準備した。
実行条件は従来の限定案を維持し、追加するのは通常観測中のCREATE_PROCESS/LOAD_DLLのfile情報照会だけ。

observerのevent検証後、file handleをcloseする前に、借用handleから次を行う。

1. FileIdInfoを取得し、volumeと128-bit file IDを保持する。
2. 同じhandleからGetFinalPathNameByHandleWでnormalized NT pathを取得する。
3. 同じhandleのFileIdInfoを再取得し、1と一致することを確認する。

前・各API間・終了後に既存の時間/メモリ予算を確認する。pathを使った再openやfile内容の読込はしない。
lpImageNameやbase addressからremote memoryを読まない。取得handleのcloseは既存transportだけが所有する。
file identityの一致は内容hashやloaded bytesの認証ではなく、名前から障害DLLや原因を断定しない。

collectorはchild起動前に16枠を確保する。各枠のname bufferは1024 wchar、identity bufferは2個。
images全体のJSONは24 KiB以下（外枠・区切り・未完成枠の予約分を含む）。event slotと状態、volume/file ID/nameをprivate metadataのimagesへ追加する。
名前長がbuffer以上、identity変化、API失敗、容量超過では再試行せず観測を停止し、部分bufferを保持する。
NULL hFileはno_file_handleと明示し、別手段へfallbackしない。停止drain中には新しい情報照会を行わない。
resource stop後は既存方針どおりsnapshot/writeを始めず、process終了後の完全保存は保証しない。

既存B1DBG001のheader/raw領域は変更しない。imagesは追加private metadataであり、旧記録への追記はしない。
旧offline readerの匿名対応はそのまま使える。collector sourceをallowlistへ追加し、次回は16 sourceを照合する。
今回の変更はproduction sourceやformal pinを変更せず、既存保存記録を改変しない。

Win32仕様の根拠:
[LOAD_DLL_DEBUG_INFO](https://learn.microsoft.com/en-us/windows/win32/api/minwinbase/ns-minwinbase-load_dll_debug_info)は
debugger側のread/read-sharing hFileとclose責務、およびimage name pointerの任意性を記載する。
[GetFinalPathNameByHandleW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfinalpathnamebyhandlew)は
NT path指定とbuffer不足時の長さを定義する。
[FILE_ID_INFO](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_id_info)はvolume/file IDの組によるfile比較を説明する。

次の実機診断は、review済みcommit固定・16 source preflight・空き資源確認の後、restricted child1個を1回だけ。
観測30秒/256 events/親＋child512 MiB未満、未識別breakpoint停止、drain32回/5秒の条件は変えない。
新しいfile情報照会による追加停止の可能性を結果として扱い、ACL緩和や別childへの再試行に進まない。
この案の準備継続は、追加の実機診断を実行する承認とは別に扱う。

準備savepoint: 06f1e63。pure/fake224/224、独立再監査の新規P0〜P3=0、指定fake50/50。
実read-only preflightは16 source / 192,088 bytes / verified、OS10.0.26200.9445と既存exe/DLL hash一致。
上記16枠のJSON上限は、独立監査P3を受け外枠と将来の部分row予約を含むよう是正済み。
