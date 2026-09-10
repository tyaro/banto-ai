# S4-B1 ConsoleInitializeの最初の失敗候補を観測する限定診断

状態: **修正保存・全体fake・独立レビュー/preflight完了 / 限定1回の返答待ち・実機未実施 / no native acceptance**。

## 目的

[return観測v3](anomaly-multiseed-v0.3-s4-b1-init-return-v3-result-2026-09-10.md)でAL=0・stage=600を観測した。
ConsoleInitializeのfalse戻りと整合するが、内部API/statusや非介入時の経路はまだ確定していない。
今回はcleanupで失われる前のEAX下位32 bitsを、最初の失敗分岐候補で取得する。

## 観測地点と解釈

| DR slot | RVA | 命令 | 確認する候補 |
| --- | --- | --- | --- |
| DR0 | 0xbecc2 | XOR AL,AL | RtlInitializeCriticalSection後の負status候補 |
| DR1 | 0xbecaf | LEA RCX,cleanup対象 | ConsoleAllocate後の負status候補 |
| DR2 | 0xbed34 | CMP EAX,0xc0000022 | ConsoleCreateConnectionObject後の負status候補 |
| DR3 | 0xbed9c | LEA RCX,local状態 | ConsoleSanitizeStandardIoObjects後の負status候補 |

共有出口の0xbecc2/0xbecafには別経路からも到達できる。
全4地点をLOADから有効にし、途中の例外を一度も通常Continueせず最初の一致例外で止めることが、候補を区別する前提になる。
それでも先行命令の実行履歴を直接取得するものではなく、候補名を実行APIの確定や根本原因の証明として扱わない。
特にDR2の負statusはlowbox条件により回復できる。途中の失敗と最終的な初期化失敗を区別し、connection_recovery_path_presentを記録する。
未知の負statusもそのまま保持し、特定のエラー番号への一致を取得条件にしない。

## 設定・取得と拒否条件

DebugDriver(console_failure=True)のみで有効、既定off。unload_entry/init_returnとの同時使用は拒否する。
既存の借用初期threadに対し、SetThreadContext(DEBUG_REGISTERS)を最大1回だけ行う。
未使用のDR0〜3、DR7=0または0x400、標準causeがclearであることを設定前に確認する。

現在KernelBase LOADのbase/初期thread/所有handleを検査し、次のcode2窓をReadProcessMemoryで照合する。

| RVA | bytes | SHA-256 |
| --- | --- | --- |
| 0x4e6c0 | 1836 | ff2bf35f46cc2d9a066260b8678a9e0ef6d0bacfb12c4374199e6bb58ae8870c |
| 0xbeb60 | 586 | d162a1ead64d7d54975d3b4440ee8280b3a924113f1a870f284f5a6d36aceeb3 |

DR0〜3を固定4地点、DR7のlocal enableを0x55にする。R/W・LEN等は0、bit10は元の値を保持する。
DR6は従来どおり0x10800のinactive bitsを要求する。DLLコード、一般register、RIP/EFLAGSは書き換えない。
要求bytesを保存し、Setのuncertain/query_confirmed/verifiedを区別する。
設定後Getで全4地点とDR7（bit10だけの正規化を許容）、DR6標準cause mask0xe00fが0であることを確認する。
Get API返却値の全debug bytesとflagsを解釈前に保存する。API表現をCPU生registerと同一視しない。

設定後の最初の例外だけを検査する。初期thread・first chance SINGLE_STEP・flags0・parameters0・chained recordなしを要求する。
例外addressとRIPが同じ候補地点、DR0〜3全一致、DR7全4local enable、DR6の標準causeは対応するB0〜3の1bitだけ、TF=0を要求する。
別地点、複数cause、BD/BS/BT、別thread・予期しない例外等は追加取得せず停止する。
最初の例外に対応しないthread作成/終了・process終了・DLL解放等も未取得として停止し、再設定しない。

## 呼出元と値の確認

hitのGetにはCONTROL/INTEGERを含め、CONTEXT1232 bytesを保存する。
静的に検査したprologueはpush rbp/rsi/rdi、mov rbp,rsp、sub rsp,0x70で、4地点とも復元前にある。
RSPがuser範囲内で16-byte整列、RBP=RSP+0x70、RSPから0x90 bytesまでが範囲内であることを確認する。
その後、**RSP+0x88の8 bytesだけ**を読み、呼出元return addressがKernelBase base+0x4ebe6と一致することを検査する。
これは_KernelBaseBaseDllInitialize内のConsoleInitialize CALL直後に当たる。
frame slotの生bytesを先にprivate保存し、不一致ならstage取得へ進まない。取得したpointerを追跡しない。
通常の呼出しframeとの整合確認であり、全call stackや根本callback reasonを直接証明するものではない。

続いてWORD RVA0x3aeea0を2 bytes読み、raw bytes・stage・EAX下位32 bitsを保持する。
stage=600かつEAXのbit31=1を要求し、異なる値も保存して確認不成立として停止する。
確定するのは地点・呼出元slot・stage・負statusの整合であり、child E2E成功や最終原因ではない。

## 上限と終了

- GetThreadContext最大3回、SetThreadContext最大1回。停止点は1か所から4か所へ変更する。
- RPMは固定順序の最大4回、**2432 bytes**（code2422＋caller8＋stage2）。従来2197 bytesから235 bytes増。
- 既存2048-byte scratchを再利用。新規のstack全域取得・pointer追跡・追加handle・symbol取得は観測中に行わない。
- context metadata8 KiB、全metadata64 KiB、30秒/256 events/親＋child512 MiB未満/空きdisk1 GiB以上を維持する。
- owned stopは既存32 drain waits/5秒。API前後の期限検査であり、同期APIの途中強制中断保証ではない。

観測が成立してもconsole_failure_observed_stopで既存owned stopへ進み、通常Continue/例外のhandled化をしない。
TerminateProcess確認後だけpendingを解放する。停止要求が失敗したらpendingと所有未解消を保持する。
DR復元・再設定・再起動・自動再試行をしない。EXITは意図的停止後の値と区別する。
最終reportを先に出力/flushし、所有済みbufferから証跡を保存する。private値を一般向けreportへ出さない。
既存fixture・証跡の保持と、resource_stop後の追加照会/書込み抑制を維持する。

## 準備の確認

現在KernelBase.dllの有界同一handle read1回、既存hashとclose確認。追加PDB読取り/download、過去private証跡参照なし。
停止地点4件の命令境界・bytes、code2窓hash、frameの関係を既存解析と照合した。
relocation表236492 bytes/117072 DIR64を有界解析し、code2窓との重なりなし。
kernelbase-console-probe-recipe.jsonをignored artifacts/context-offline-2026-09-10へ保存した。

関係fake11/11 pass（0.442秒）。全4地点の取得・生値保持と、API境界の失敗/割込み/OOM/資源停止/対象変化、short read、
DR/例外/stack/caller/stage/statusの不一致、停止要求失敗、通常Continue前のowned terminationを確認した。
初回は試験helperの新オプション未対応により16 subtestが失敗し、helperの受渡しを修正後に全件pass。
実child・実SetThreadContextによる診断は未実施。全体回帰・独立レビュー・保存後preflightは追記する。

## 実機判断対象

v3の限定1回承認は消化済み。今回は4地点の設定とcaller slot8 bytesを含む新しい診断である。
ユーザーの上限小幅拡大の意向を踏まえ、取得量だけ235 bytes増やし、時間・memory・disk・設定API回数は据え置いた。
準備をすべて完了した後、**新規fixtureでこの限定診断を1回実施すること**を判断対象として提示する。
この新方式はまだ実行しておらず、過去の返答を再実行の承認として使わない。


## 全体検証・独立レビュー

debug＋preflight/event全体171/171 pass（1.762秒）。21 sourcesと各collectorの予約枠を含む全metadata容量確認も通過した。
独立差分レビュー新規P0〜P3=0、指定fake11/11 pass（0.475秒）。
4地点/DR/causeとframe slot計算、失敗後の取得抑止、private保存、Terminate後だけのpending解放を確認した。
共有出口と回復可能なconnection分岐について、候補分類と根本原因を分ける留保を維持する。
担当の完了通知のみを利用し、進捗ポーリングなし。独立担当のnative実行/private証跡参照/source変更なし。

repository safety/diff-check pass、mainは基準889cfc3のままclean。
PC空きRAM9.46→9.76 GiB、C108.21→108.20 GiB、D75.36 GiB。単発値からリーク有無は未判定。
新規の常駐helper・他project操作なし。実機診断は未実施。


## 保存後の事前確認と再開条件

実装・試験・計画を78617f2に保存した。read-only preflightは1.939秒、21 sources/238228 bytes、verified、resource_stop=false。
Windows10.0.26200.9445/Python3.14.0、既存exe/python314.dll hash一致。console-failure-preflight.jsonへ保存済み。
execution_authenticated/launch_authorized/native_accepted/formal_permissionはfalse。この事前確認でchild起動・SetThreadContextは行っていない。
試験後の変更は文書と試験file末尾の空行のみで、実装の変更はない。repository safety/diff-check pass。

準備は完了。今回の判断対象は、上記4地点の設定を含む限定診断を、新規fixtureで1回実施すること。
この問いへの「続けてください」は当該console_failure v1の1回への了承として扱い、再確認せず実行する。
観測・不一致・失敗のいずれでも自動再試行しない。最終report・終了・証跡保存の確認を先に行う。
