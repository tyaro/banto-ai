# S4-B1 KernelBase初期化の戻り直前を観測する限定診断

状態: **v1実機1回終了 / v2の保存処理修正・fake/独立レビュー完了 / v2実機未実施 / no native acceptance**。

[v1の実機結果](anomaly-multiseed-v0.3-s4-b1-init-return-result-2026-09-10.md)を参照。
v1は設定後のregister照合で停止し、終了・証跡保存を確認した。読み戻し値自体は未保存だったため、v2で取得時点の保存を追加した。
以下の取得条件はv2でも維持する。過去の判断待ち/preflight記述はv1実行前の履歴で、追加実行の承認ではない。

## 目的と観測位置

[管理情報v2](anomaly-multiseed-v0.3-s4-b1-unload-entry-v2-result-2026-09-10.md)では、KernelBase.dllに
初期化失敗bitがあり、callback RVA0x5060が現在imageのKernelBaseDllInitializeと一致した。
ただし、内部のどの処理で失敗したかは未確定。

前回のUNLOAD位置でstage値を読む案は採用しない。
[UNLOAD_DLL_DEBUG_INFO](https://learn.microsoft.com/en-us/windows/win32/api/minwinbase/ns-minwinbase-unload_dll_debug_info)
は解放されたDLLの情報を通知するもので、通知内のbaseだけではその後の読取り可能性を保証できない。
現在fileの静的解析で見つけた段階値を、解放後まで保持される実行記録と扱わない。

今回の候補は、KernelBaseDllInitializeの共通return経路の**RVA0x50ba（MOVZX EAX,AL）直前**。
初期化callbackのreasonが1であることをEBXから確認し、ALとWORD RVA0x3aeea0を保存する。
reason1の通常経路では、基本初期化のALをそのまま返す経路と、ARI初期化の負statusからAL=0にする経路がここに合流する。
観測するのはこの位置の値であり、過去のCALL traceや最初の失敗APIの完全な特定ではない。

## 変更する条件

明示的な `DebugDriver(init_return=True)` のみで使い、既定はoff。unload_entry=Trueとは同時使用不可。
対象は新規の専用fixtureから起動する診断childの初期threadだけ。
**SetThreadContextのDEBUG_REGISTERS指定による設定を最大1回**追加し、DR0/DR7で1か所のprocessor execution breakpointを置く。
DR6には原因判定のためのinactive baselineも設定する。DLLコード・一般register・RIP/EFLAGSへの書換えはない。

[Microsoftのprocessor breakpoint説明](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/processor-breakpoints---ba-breakpoints-)
ではprocessor breakpointはコード上でも利用できる一方、debug registerの手動編集は推奨されていない。
本候補は独自の設定と照合を持つ限定診断であり、通常のdebugger engineと同等とは扱わない。
[SetThreadContext](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-setthreadcontext)
のContextFlagsでdebug部分だけを指定し、OSが設定値を補正する可能性も考慮して直後のGetで確認する。
したがって「読取り専用」という前回までの説明は今回には当てはまらず、実機実行は別の判断対象とする。

bootstrapのINT3等を正常処理扱いにする変更はない。transport/owned stopは変更しない。
今回設定した停止点も、**観測後に通常Continueしたり、例外をhandledとして返したりしない**。
取得が成立してもその場で診断を終了し、既存owned stopへ渡す。

## 取得と検証の順序

collector、16-byte aligned CONTEXT1232 bytes、2048-byte scratch、private証跡bufferはchild作成前に確保する。
新規handle取得・pointer chain・実行中のsymbol検索・OS DLLの変更は行わない。

1. normal LOAD_DLLを既存images collectorで確認し、名前がKernelBase.dllの行を1回だけ選ぶ。
   初期thread/PIDと借用process/thread handleの同一性、有界user address・64 KiB aligned baseを検査する。
   [debug event通知中は対象processの全threadが停止している](https://learn.microsoft.com/en-us/windows/win32/debug/debugging-events)条件で操作する。
2. LOAD時に下表のcode2窓2195 bytesを各1回読み、要求長とSHAを照合する。不一致なら設定前に停止する。
3. GetThreadContext(DEBUG_REGISTERS)で元のDR0〜3=0、DR7∈{0,0x400}、標準cause bits=0を要求する。
   使用中のdebug slotは上書きしない。元のdebug register bytesをprivate保存する。
4. DR0=base+0x50ba、DR7のL0だけを追加し、R/W0=00・LEN0=00のexecution/1-byteを指定する。
   DR6のBLD/RTMをinactiveの1にし、DEBUG_REGISTERSだけのSetThreadContextを1回呼ぶ。
   直後に再Getし、DR0〜3、DR7（bit10だけ補正可）、DR6を照合してからLOADを通常Continueする。
5. 設定後の最初の例外を選ぶ。他thread、別address、second chance、別exception code等なら停止し、後続で再試行しない。
   first-chance 0x80000004、例外flags=0/連結recordなし/parameters=0、address一致を要求する。
6. GetThreadContext(CONTROL | INTEGER | DEBUG_REGISTERS)を1回行い、rawをprivate保持する。
   RIP=base+0x50ba、EBX下位32 bits=1、TF=0、DR0〜3/DR7一致、DR6が設定確認時の値にB0だけを加えた値であることを要求する。
7. 同じpending eventでbase+0x3aeea0から**2 bytesを1回**読み、AL、AL==0、段階値を保存する。
   ALや段階値が既知の値に属するかで値を補完・破棄しない。未知値も実測値として残す。
8. `init_return_observed_stop` を理由に観測ループを終了する。
   成立時もdriver/observerのstatusはfailedとなり、collectorのconfirmedと意図的終了理由を別々に評価する。

v2では最大3回のGetごとに固定slotへ要求flags/取得状態を保持し、API成功とpost-budget通過後のdebug48 bytesと返却flagsを解釈前に保存する。
Set要求debug bytesと照合の個別boolもprivate保持する。hitのcontext1232 bytesもflags検査前に保持するが、有効性は別に判定する。
API失敗・中断・資源停止を有効なrawへ補完せず、Getの成功とflags/DRの一致を別々に評価する。

| LOAD時に照合するRVA範囲 | bytes | SHA-256 |
| --- | --- | --- |
| 0x5060..0x51c7 | 359 | 7c00209c3aa4a3e3ca691c3b49ace93f09e55fa8acd0db498a0402e3b434d79f |
| 0x4e6c0..0x4edec | 1836 | ff2bf35f46cc2d9a066260b8678a9e0ef6d0bacfb12c4374199e6bb58ae8870c |

現在KernelBase.dllの参照hashはbecad014fb8efa8cb5e314931cca92778ad42c649b12a6909632cacd68af4f40。
PE SizeOfImage=4202496、段階値のsection flags=0xc0000040。
有界PE relocation表236492 bytes/117072 DIR64 entriesに2 code窓との重なりはない。
参照fileの情報であり、実loaded bytesの2窓一致は今回の実機で判定する。LOAD時点の照合をimage全体やその後の完全一致とは扱わない。

[Intel SDM Volume3B §20.2.3–20.2.4](https://cdrdv2-public.intel.com/874250/253669-090-sdm-vol-3b.pdf)
を参照し、B0〜3/BD/BS/BTをmask0xe00fで照合する。BLD(bit11)/RTM(bit16)はactive-lowなので、設定時に1を要求する。
hit時はDR6全体のbaseline比較も行い、他の原因・reserved bits等の変化を推測で許容しない。
Windows側の正規化がこの条件と異なる場合も停止し、自動で条件を緩和しない。

## 停止と証跡の扱い

各Get/Set/Readの前後にpending event、所有handle、creator thread、時間・resourceを検査する。
Setの失敗・中断時は「設定されていない」と推測せず、failed/uncertainとして保持し、再Setや設定解除を試行しない。
初期化結果の取得成功後もDRを復元して実行再開する処理はない。
既存owned stopが**TerminateProcess成功確認後だけ**pending eventをDBG_NOT_HANDLEDで解放する。
終了要求が失敗した場合は通常Continueせず、process/handle所有未解消を失敗として残す。
drain中の新規Get/Set/Read、再設定・後続例外での再採取はない。

今回のEXIT値は停止要求によるものになり得るため、自然終了0xC0000142の再現確認には使わない。
自然終了は前回v2で既に記録済み。AL=0の取得も正式受入やharness全体の成功にはならない。
終了直後の最終reportを先に出力/flushし、その後は所有済みbufferからの詳細保存だけを行う。
private raw/context/部分bufferを一般向けreportに出さず、既存fixture・証跡を保持する。

## 上限と検証状況

- GetThreadContext最大3回、SetThreadContext最大1回。
- ReadProcessMemory最大3回/**2197 bytes**（code2195＋段階値2）。従来unload stack/entryの採取は併用しない。
- context metadataは8 KiB以内、全metadata64 KiB以内。既存30秒/256 events/親＋child512 MiB未満、空きdisk1 GiB以上を維持。
- owned stopは既存32 drain waits/5秒の条件。API前後の期限検査であり、同期APIを途中で強制中断する保証ではない。
- 観測前のthread作成/終了、DLL解放、process終了などでは取得未成立として停止する。

最初の関係fake7/7 pass（0.185秒）、debug＋preflight/event回帰155/155 pass（1.419秒）。
独立レビュー初回は新規P0〜P3=0、指定7/7 pass（0.170秒）。
DR6 baseline比較等の追加後、関係fake10/10 pass（0.184秒）、全回帰158/158 pass（1.104秒）。
追加部分の独立レビューも新規P0〜P3=0、指定10/10 pass（0.197秒）。完了通知のみを利用し、進捗ポーリングなし。
全metadata容量試験は20 sourcesと各collectorの予約枠を含む。保存後preflightは別記する。
試験はすべてfakeで、実child/実SetThreadContext/実target memory読取りはまだ行っていない。

参照recipeはignored artifacts/context-offline-2026-09-10/kernelbase-return-probe-recipe.jsonに保存した。
現在KernelBase.dllの有界held read2回（最初のrelocation表64 KiB仮定で停止した分を含む）、各reader close、参照hash一致。
表の上限を1 MiB以内にして再解析し、236492 bytesを検査した。実機診断の再試行ではない。
新規PDB取得・過去private証跡の再読取り・常駐helper・他project操作なし。

## 次の実機判断対象

source保存・preflight・独立確認後、**この設定変更を含む限定診断を新規fixtureで1回だけ実施すること**を提示する。
初期threadのdebug register設定1回と最大2197-byte読取りを含む。観測・不一致・失敗のいずれでも追加起動なし。
前回のv2承認は消化済みで、この新しいdebug register変更を含まない。実機未実施のまま個別の返答を待つ。

## 保存後の事前確認

実装・試験・計画を5fc0276に保存した。read-only preflightは2.293秒、20 sources/228061 bytes、verified。
Windows10.0.26200.9445/Python3.14.0、既存exe/python314.dll hash一致、resource_stop=false。
execution_authenticated/launch_authorized/native_accepted/formal_permissionはfalse。実child/実SetThreadContextは未実施。
ignored artifactsのinit-return-preflight.jsonへ保存した。これはsource/indexとruntimeの確認であり、停止点設定の実機成功を示さない。
repository safety/diff-check pass、mainは基準889cfc3のままclean。
PC空きRAM8.53→9.37 GiB、C105.06→105.04 GiB、D75.36 GiB。単発値からリーク有無は判断しない。
次の返答がこの実行範囲への了承なら、新規fixtureで上記診断を1回実施し、最終reportと保存の確認を先に行う。

## v2の検証と新しい実機判断対象

v1の承認1回は消化済み。v2は保存を解釈前へ移し、要求/返却bytesと不一致項目を残す修正に限定した。
DRの検査条件や時間・memory・取得回数を緩和しない。recipeはkernelbase-26200.9445-return-v2。
関係fake11/11（0.223秒）、全回帰159/159（1.229秒）pass。独立新規P0〜P3=0、指定11/11（0.213秒）pass。
v2を保存してread-only preflightを確認後、**同じ停止点設定最大1回・取得最大2197 bytesで、新規fixtureの限定診断1回**を提示する。
未保存のv1値を埋めるために自動で実行せず、別の返答を待つ。
