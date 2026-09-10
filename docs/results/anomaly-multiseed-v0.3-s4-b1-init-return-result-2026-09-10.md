# S4-B1 初期化return観測v1の実機結果

状態: **承認済み1回終了 / 設定読み戻しの照合で停止 / callback戻り値・段階値は未取得 / no native acceptance**。

ユーザーの「続けてください」を、停止点設定を含む限定実機1回への了承として扱った。
cleanな隔離worktreeのHEAD029fb99（実装5fc0276）で、新規fixtureのDebugDriver(init_return=True).runを1回実行した。
この1回は消化済み。追加のchild起動や設定の再試行は行っていない。

## 観測と終了・保存

初期reportまで2.085秒。driver/observerはfailed、primary_reason=return_debug_registers、secondaryなし、resource_stop=false。
KernelBase.dllのLOADでcode2窓2195 bytesを要求長どおり読み、SHAが両方一致した。
最初のGetThreadContext、SetThreadContext、2回目のGetThreadContextはいずれもAPI成功。
Get後のContextFlags検査まで通ったが、その後のDR0〜3/DR6/DR7の組合せ検査で停止した。
set_state=query_confirmedであり、設定結果の検証完了ではない。

| 項目 | 結果 |
| --- | --- |
| 元のdebug register | DR0〜3、DR6、DR7はすべて0。privateに保存済み |
| 実GetThreadContext | 2回。両方のAPI成功とflags検査通過を記録 |
| 実SetThreadContext | 1回。API成功、再Get後のregister一致検査で停止 |
| 実ReadProcessMemory | 2回/2195 bytes。LOAD時のcode2窓のみ |
| 設定後に読み戻したregisterの値 | **未保存・未確定** |
| callback戻り値/段階値 | **未取得**。停止点への到達は未観測 |
| 通常event/Continue | 4件/3件。CREATE python、LOAD ntdll、LOAD kernel32、LOAD KernelBase |
| 停止処理 | TerminateProcess要求確認後にpending LOADを解放、drain1件のEXIT code1をContinue |

自然終了は今回未観測。code1は停止処理後の値であり、元の起動障害の自然終了値とは扱わない。
process signal、debug ownership解消、所有process/thread handle close、teardown pass、failure_count0を確認した。

最終reportを先に出力/flushし、private証跡108274 bytesをwrite/flush/closeした。
実行時bufferと、保存fileの有界held-handle readbackのSHA-256は一致した。

`1c6f865ff148e20d2deaf9e2f822cb70096ab32d5511393464407b870cc385cb`

normal4/drain1、wait/continue inflight=false、未確認領域はzero。
metadataのdriver状態は証跡保存前のscopeで、最終write/flush/closeは先行reportを根拠とする。
fixture_retention=unverified、native_accepted/formal_permission=falseを維持する。

## 証跡保存の不足とv2修正

v1は設定読み戻しの値を_programmed検査の合格後にしかrowへ保存していなかった。
そのため、DR0、DR6のinactive bits/cause、DR7等のどれが不一致だったかは今回の保存証跡では分からない。
元のDR6/DR7が0だったという記録から、設定後の実値も0だったと推測して埋めない。
APIが拒否した、OSが特定のbitを消去した、停止点が有効だった等のいずれも、この結果だけでは確定できない。

v2では取得の成功と解釈の成功を分け、次を追加した。

- 最大3回のGetそれぞれに固定slotを用意し、要求flagsと取得状態を保持する。
- API成功と直後の予算検査を通った48-byte debug register群・返却flagsを、flagsやDRの意味を検査する前にprivate保存する。
- hit取得では同じ時点に1232-byte contextも保存する。生bytesの保存を、有効なcontextや観測成立と同義にしない。
- Setへ渡すdebug register要求bytesを保存する。set_stateがnot_started/uncertain/failed/verifiedのどれかも併せて判断する。
- DR照合の各boolとarm/hitの別を保存し、どの項目で停止したかを区別できるようにする。

API false、中断、資源停止、要求長不一致を成功したrawとして補完しない。
Getのflags不一致ではrawを保持してもreturn/stageを確定せず停止する。
DR0〜3/DR6/DR7の条件、DR7 bit10以外の差分拒否、DR6のbaseline比較は変更していない。
recipe名はkernelbase-26200.9445-return-v2。追加API呼出し、取得bytes、停止点、一般register/code書換えは増やさない。
次のv2実機は[更新した計画](anomaly-multiseed-v0.3-s4-b1-init-return-plan-2026-09-10.md)の別の1回として判断対象にする。

## 検証と資源

関係fake11/11 pass（0.223秒）、debug＋preflight/event全体159/159 pass（1.229秒）。
context8 KiB/全metadata64 KiBの既存容量確認も通過。repository safety/diff-check pass、mainは基準889cfc3のままclean。
既存の取得失敗・中断・資源停止・所有照合に加え、flags/DR不一致のraw保持と、外側driverが保存した証跡まで確認した。
独立差分レビュー新規P0〜P3=0、指定fake11/11 pass（0.213秒）。独立担当は実child・native・private証跡を扱っていない。
完了通知を利用し、進捗ポーリングなし。

v1の同run preflightは20 sources/228061 bytes、verified、resource_stop=false。
Windows10.0.26200.9445/Python3.14.0、既存exe/python314.dll hash一致。Windows UpdateによるUBR緩和と実測記録を維持した。
memory sample58回、親＋childの記録上peak commit23576576 bytes（約22.48 MiB）、peak working34148352 bytes（約32.57 MiB）。
PC空きRAM8.88→9.33 GiB、C105.81→105.82 GiB、D75.36 GiB。
短い診断のsampleとPC全体の単発値であり、継続的なリーク試験やリーク不存在の証明ではない。

公開要約はignored artifacts/context-offline-2026-09-10/init-return-native-summary.jsonlとinit-return-native-readback.json。
今回private証跡の有界readbackは1回、reader close済み。既存の証跡/fixtureは保持し、再利用/削除/修復なし。
実機後の追加DLL/PDB読取り・download、追加設定操作、常駐helper、他project操作なし。
本流統合、child E2E成功、native受入、formal permissionは未達。
