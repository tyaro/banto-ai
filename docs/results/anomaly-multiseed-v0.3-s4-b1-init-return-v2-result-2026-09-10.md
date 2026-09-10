# S4-B1 初期化return観測v2の実機結果

状態: **承認済み1回終了 / DR6の返却表現が停止理由と判明 / callback戻り値・段階値は未取得 / no native acceptance**。

ユーザーの「続けてください」を、保存処理修正版の限定実機1回への了承として扱った。
cleanな隔離worktreeのHEAD0f19157（実装e601921）で、DebugDriver(init_return=True).runを新規fixtureで1回実行した。
今回の1回は消化済みで、診断の追加起動や設定の再試行は行っていない。

## 取得結果と停止理由

初期reportまで1.819秒。driver/observerはfailed、primary_reason=return_debug_registers、secondaryなし、resource_stop=false。
KernelBase.dllのLOADで固定code2窓2195 bytesを完全readし、両SHAが一致した。
初回Get、Set、2回目GetのAPI成功とflags0x100010の一致を確認した。

| 項目 | 元の値 | Setへの要求値 | 2回目Getの返却値 |
| --- | --- | --- | --- |
| DR0 | 0 | LOAD base+0x50ba | 要求した停止位置と一致 |
| DR1〜3 | すべて0 | すべて0 | すべて0 |
| DR6 | 0 | 0x10800 | **0** |
| DR7 | 0 | 1 | **1** |

要求bytesと両Getのdebug48 bytesをprivate証跡に保存し、保存後にも同じ関係を再確認した。
判定はdr0_matches、dr1_to_dr3_zero、dr7_matches、dr6_standard_cause_matchesがtrue、
**dr6_inactive_bits_setだけがfalse**だった。API失敗や停止位置の不一致ではない。
ただしv2全体の検証は未成立で、set_state=query_confirmedのまま。
停止点での例外は未観測、callback戻り値と段階値は未取得である。
[v1の未保存値](anomaly-multiseed-v0.3-s4-b1-init-return-result-2026-09-10.md)を今回の値で埋めない。

## 前提の修正

v1/v2はCPUのDR6でactive-lowとなるBLD/RTMをSet要求で1にした後、Getの返却値にも両bitの1を求めていた。
さらにhitでは返却DR6全体がbaseline+B0だけになったことを求めていた。
今回、CONTEXT.Dr6は要求0x10800に対して0を返しており、CPU registerの生のbit表現を要求どおり保持するという前提は成立しなかった。

[MicrosoftのSetThreadContext仕様](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-setthreadcontext)
は、OSが管理する一部の設定値が補正されることを説明している。
この仕様は特定のDR6 bitや、すべてのWindows版で0を返すことまでは保証していない。
**今回の返却値が0だったのは実測事実**であり、内部の補正処理やCPUのBLD/RTM状態まで特定したわけではない。

v3はSetへの要求値と取得回数を変えず、CONTEXT.Dr6で比較する範囲を、標準causeのB0〜3/BD/BS/BT（mask0xe00f）に揃える。
armでその範囲が0、最初のhitでB0だけが1であることを要求し、baseline差分も同じ範囲で確認する。
DR6全体の返却bytesは従来どおり保存する。BLD/RTMやreserved bitsのAPI表現から、hardwareの状態を推測しない。

DR0、DR1〜3、DR7、初期thread、first chance、exception address、RIP、reason1、TF=0の条件は維持する。
B0がない場合、B1〜3/BD/BS/BTが併記された場合は段階値を読まず停止する。
arm前にcauseがclearであることと設定後の最初の例外だけを選ぶ条件も維持する。
これは一致する命令位置での値を取得するための判定であり、複合した例外原因が他にないことの網羅的証明ではない。
観測後は通常Continueせず、既存owned stopで診断を終了する。

## 終了と証跡保存

通常eventはCREATE python、LOAD ntdll、LOAD kernel32、LOAD KernelBaseの4件、通常Continueは3件。
TerminateProcess成功確認後にpending LOADを解放し、drain1件のEXIT code1をContinueした。
code1は停止処理後の値であり、元の自然終了値ではない。
process signal、debug ownership解消、所有process/thread handle close、teardown pass、failure_count0を確認した。

最終reportを先に出力/flushし、private証跡108952 bytesをwrite/flush/closeした。
実行時bufferと保存fileの有界held-handle readbackのSHA-256は一致した。

`27cd3c147d687b6c8ff5655476837402c49219c17739b7fa4368da1794b87103`

normal4/drain1、wait/continue inflight=false、未確認領域はzero。
metadataのdriver状態は保存前のscopeで、最終write/flush/closeは先行reportを根拠とする。
fixture_retention=unverified、native_accepted/formal_permission=falseを維持する。

## 検証・資源・保存物

v3の関係fake12/12 pass（0.349秒）、debug＋preflight/event全体160/160 pass（1.470秒）。
armのDR6=0からhitの0xFFFF0FF1へ表現が変わるケースを外側driverの証跡まで検査した。
同時にB0なし/B1〜3/BD/BS/BTの拒否と、生の返却値の保持を確認した。追加native試験ではない。
独立差分レビュー新規P0〜P3=0、指定fake12/12 pass（0.377秒）。hardware状態をAPI値から推測しない留保を維持した。
担当の完了通知を利用し、進捗ポーリングなし。独立担当はnative実行・private証跡参照を行っていない。

v2の同run preflightは20 sources/229087 bytes、verified、resource_stop=false。
Windows10.0.26200.9445/Python3.14.0、既存exe/python314.dll hash一致。Windows UpdateのUBR緩和と実測記録は維持した。
memory sample58回、親＋childの記録上peak commit23416832 bytes（約22.33 MiB）、peak working34217984 bytes（約32.63 MiB）。
PC空きRAM8.46→9.36 GiB、C105.72→105.71 GiB、D75.36 GiB。単発値からリーク有無は判断しない。

公開要約はignored artifacts/context-offline-2026-09-10/init-return-v2-native-summary.jsonlとinit-return-v2-native-readback.json。
今回private証跡の有界readbackは1回、reader close済み。既存fixture・証跡は保持し、再利用/削除/修復なし。
追加DLL/PDB読取り・download・常駐helper・他project操作なし。
次はv3保存・事前確認後、[同じ範囲の限定実機1回](anomaly-multiseed-v0.3-s4-b1-init-return-plan-2026-09-10.md)を判断対象とする。
本流統合、child E2E成功、native受入、formal permissionは未達。
