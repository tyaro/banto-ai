# S4-B1 return観測v3の結果とConsoleInitializeの調査

状態: **v3限定1回終了 / AL=0・stage=600の観測と保存確認 / 内部の失敗API・statusは未確定 / no native acceptance**。

## 1. 実行範囲と直接観測

ユーザーの「お願いします。上限もう少し上げても大丈夫かと」を、準備済みv3の限定1回への了承として実行した。
前回の停止は上限不足ではなかったため、今回の取得・時間・memory・disk上限は据え置いた。
今後、必要な上限の小幅拡大を検討できる意向として記録し、再試行回数や無制限な取得の承認とは扱わない。

cleanなa7cf252（実装2127527）で、新規fixtureからDebugDriver(init_return=True)を1回起動した。
初期reportまで1.795秒、resource_stop=false、secondaryなし。
driver/observerはfailedだが、primary_reason=init_return_observed_stopによる**設計どおりの観測後停止**。
collectorはstate=completed/status=confirmedで、起動障害の解消やchild E2E成功を意味しない。

| 項目 | 同じ実行の観測値 |
| --- | --- |
| 対象 | CREATE/LOAD/例外のprocessと初期threadが一致 |
| 停止位置 | KernelBase LOAD base + RVA0x50ba、例外addressとRIPが一致 |
| 例外 | first chance 0x80000004、flags=0、parameters=0、chained recordなし |
| callback reason | EBX下位32 bits=1 |
| TF | 0 |
| AL | 0 |
| 段階値 | WORD RVA0x3aeea0=600 |
| 取得 | GetThreadContext 3回、SetThreadContext 1回、ReadProcessMemory 3回2197 bytes |
| code照合 | LOAD時の固定2窓2195 bytesが既存hashと一致 |

観測点はMOVZX EAX,ALの直前であり、RETを実行させる前に診断を終了した。
実際のcallback復帰や自然終了C0000142を、このrunで再観測したとは扱わない。

## 2. 設定と返却値

| 段階 | DR0 | DR1〜3 | DR6 | DR7 | ContextFlags |
| --- | --- | --- | --- | --- | --- |
| 初回Get | 0 | 0 | 0 | 0 | 0x100010 |
| Set要求 | target | 0 | 0x10800 | 1 | 0x100010 |
| 設定後Get | target | 0 | 0 | 1 | 0x100010 |
| hitのGet | target | 0 | 0xffff0ff1 | 0x401 | 0x100013 |

Setはverified、Get3回の返却flagsと生のdebug bytes、hitのCONTEXT1232 bytesをprivate証跡に保持した。
v3の比較mask0xe00fでarmは0、hitはB0だけ1。DR0/DR1〜3/DR7・baselineの検査もすべて一致した。
APIの返却表現をCPUの生registerと同一視せず、BLD/RTM/reserved bitsのhardware状態や複合原因の不存在は推定しない。

## 3. 終了・証跡の確認

通常5 events（CREATE、LOAD3件、例外1件）、通常Continueは4回。
観測した例外は通常Continueせず、TerminateProcess確認後にpendingを解放した。
drain1件のEXIT code1をContinueし、process signal、debug ownership解消、所有process/thread handle closeを確認した。
teardown pass、failure_count0、driver_teardown_failures0。code1は停止処理後の値で、元の自然終了値ではない。

最終reportを先に出力/flushし、private証跡111847 bytesをwrite/flush/closeした。
保存fileの有界held-handle readback1回で、実行時bufferのSHA-256と一致した。

`147926b48ab9dee968f965bed545848b899b138d3dfcae502d5ce42796499879`

raw CREATE/LOAD/例外のprocess・thread・位置の対応、CONTEXTのRIP/reason/AL/TF、DR値、stage=600を照合した。
normal/drainともwait/continue inflight=false、未確認領域はzero、readerはclose済み。
fixture_retention=unverified、native_accepted/formal_permission=falseを維持する。
証跡内metadataは保存前scopeであり、最終write/flush/closeは先行reportを根拠にする。

## 4. ConsoleInitializeへ絞り込めた範囲

[既存の静的解析](anomaly-multiseed-v0.3-s4-b1-unload-entry-v2-result-2026-09-10.md)では、
0x4ebdaでstage=600を書き、0x4ebe1でConsoleInitialize（RVA0xbeb60）を呼び、
0x4ebe6のTEST ALと0x4ebe8のJEでAL=0なら700を書かずに戻る。
今回のAL=0/stage=600はこの経路と整合し、**ConsoleInitializeのfalse戻りが有力候補**となった。

これは呼出し履歴の直接記録ではない。呼出先等によるstageの全書込みを否定できず、ARI側の失敗経路も完全には除外していない。
LOAD時の2窓一致はloaded image全体の一致や、その後の全コード不変を証明しない。
非介入時と同一経路になることも、この観測だけでは保証しない。

追加の静的解析では、現在KernelBase.dllを既存の10秒/8 MiB上限・同一handleで1回読み、既存hashとの一致とreader closeを確認した。
既存PDBだけを有界readし、GUID/age・section対応の照合を通してConsoleInitializeの名前を確認した。追加downloadなし。
関数範囲は[0xbeb60,0xbedaa)、139命令。公開解析結果14885 bytesを保存した。

| 失敗候補 | 静的な呼出しと分岐 | 次に状態を失う前の確認候補 |
| --- | --- | --- |
| RtlInitializeCriticalSection | 0xbeba2 CALL、0xbebae TEST EAX、0xbebb0 JS 0xbecc2 | 0xbecc2（XOR AL,AL前）。他のfalse経路もここへ合流する |
| ConsoleAllocate | 0xbeca6 CALL、0xbecab TEST EAX、0xbecad JNS。負なら0xbecafへ | 0xbecaf。ここは複数経路が共有し、後続cleanupが戻りstatusを上書きし得る |
| ConsoleCreateConnectionObject | 0xbecfa CALL、0xbecff TEST EAX、0xbed01 JS 0xbed34 | 0xbed34。C0000022ではlowbox確認後に回復・再割当へ進めるため、途中の負statusと最終失敗を区別する |
| ConsoleSanitizeStandardIoObjects | 0xbed93 CALL、0xbed98 TEST EAX、0xbed9a JNS。負ならcleanupへ | 0xbed9c（ConsoleCleanupConnectionStateを呼ぶ前） |

上表は通常の静的な戻り経路の候補であり、実行されたAPI/statusを確定した表ではない。
4候補を同時に設定して最初の一致地点で止める方式なら、回数を増やさず区別しやすい可能性がある。
ただし、共有出口の分類には先行する全候補が有効だったこと、初期thread・呼出元・stageの一致、
APIが返すDR値と地点の一致を検査する設計が必要。現時点では**案のみで、実装・実機設定・承認依頼は未実施**。
先に取得項目・上限・通常Continueしない終了方法を具体化して模擬検証し、最小の変更にする。

## 5. 独立確認・資源・保存物

公開要約2件と既存静的解析2件に限定した独立レビューは新規P0〜P3=0。
直接観測とConsoleInitializeの候補推定、実RET前の終了、自然終了との区別について確認した。
担当の完了通知を利用し、進捗ポーリングなし。独立担当はnative実行・private証跡・追加DLL/PDB参照・試験・変更を行っていない。
今回source変更なし。既存fake160件と独立レビュー済み実装を使い、同じfake試験は再実行していない。

同run preflightは20 sources/229453 bytes、verified。
Windows10.0.26200.9445/Python3.14.0、exe/python314.dllは既存hash一致。Windows UpdateのUBR緩和と実測記録を維持した。
親＋childのmemory sample72回、peak commit23420928 bytes（約22.34 MiB）、peak working34586624 bytes（約32.98 MiB）。
実行前のPC空きRAM9.90 GiB、C108.22 GiB、D75.36 GiB。単発の診断とPC空き量だけでリーク有無は判断しない。
時間・memory・disk上限への到達なし。既存fixture・証跡の再利用/削除/修復、常駐helper、他project操作なし。

ignored artifacts/context-offline-2026-09-10へ次の3件を保存した。

- init-return-v3-native-summary.jsonl
- init-return-v3-native-readback.json
- kernelbase-console-initialization-static.json

v3の承認済み1回は消化済み。追加の実機診断は行っていない。
本流統合、child E2E成功、native受入、formal permissionは引き続き未達。

保存前の空きRAM9.61 GiB、C108.21 GiB、D75.36 GiB。repository safety/diff-check pass、mainは基準889cfc3のままclean。
