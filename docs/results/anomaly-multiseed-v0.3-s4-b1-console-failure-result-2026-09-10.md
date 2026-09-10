# S4-B1 ConsoleInitialize失敗候補の実機結果

状態: **限定1回終了 / allocation候補でC0000022観測 / 終了・保存確認済み / no native acceptance**。

## 直接観測と解釈

ユーザーの「続けてください」を4地点の限定診断1回への了承として、cleanな67ad5ae（実装78617f2）で新規fixture1回を実行した。
初期reportまで1.870秒、resource_stop=false。collector completed/confirmed、primary=console_failure_observed_stop。
driver/observerのfailedは観測後に通常Continueせず終了する設計による。child E2E成功や起動障害解消ではない。

| 項目 | 同じ実行で確認した値 |
| --- | --- |
| process/thread | CREATE/KernelBase LOAD/例外で一致、初期thread |
| 例外 | first chance 0x80000004、flags0、parameters0、chained recordなし |
| 地点 | DR1、RVA0xbecaf、例外address/RIPが一致 |
| frame | RSP16-byte整列、RBP=RSP+0x70 |
| caller slot | RSP+0x88の8 bytesがbase+0x4ebe6に一致 |
| stage | WORD RVA0x3aeea0=600、生bytes5802 |
| EAX下位32 bits | 0xc0000022、負値 |
| TF | 0 |
| code照合 | 固定2窓2422 bytes一致 |
| 取得 | Get3/Set1/RPM4回2432 bytes |

[Microsoft NTSTATUS定義](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-erref/596a1078-e883-4972-9bbc-49e60bebca55)
によればC0000022はSTATUS_ACCESS_DENIED（要求したアクセス権が認められていない状態）。
直接観測は上表の地点と値であり、拒否されたobject/ACL/内部APIはまだ特定していない。

LOADから4地点を同時に設定し、先行例外を通常Continueせず最初の一致地点で停止した。
静的なConsoleAllocate CALL後の負分岐と整合し、**コンソール確保経路からアクセス拒否が返ったことが有力**。
0xbecafは共有出口なので、これを過去の全命令履歴の証明と扱わない。
またConsoleAllocate内部にも複数の失敗元がある。connection_recovery_path_present=falseは今回の選択地点の注記であり、
ConsoleAllocate内部も含む全回復経路の不存在を証明しない。

## DR値と証跡

設定前DR0〜3/DR6/DR7はすべて0。
Set要求はDR0〜3が計画の4地点、DR6=0x10800、DR7=0x55。
設定後GetはDR0〜3一致、DR6=0、DR7=0x55。hitでは全4地点一致、DR6=0xffff0ff2、DR7=0x455。
返却flagsは0x100010/0x100010/0x100013。標準cause mask0xe00fではB1のみ、その他の照合もすべて一致した。
API表現をCPU生registerや複合原因の不存在に読み替えない。

通常5 events/Continue4、TerminateProcess確認後にpending例外を解放し、drain1件のEXIT code1をContinueした。
実RETや自然終了C0000142はこのrunでは未観測。process signaled/debug ownership解消/所有handle closeを確認した。
teardown pass、failure_count0、driver_teardown_failures0、secondaryなし。

最終reportを先に出力/flushし、private証跡112171 bytesをwrite/flush/closeした。
bufferと保存fileの有界held-handle readback1回のSHA-256は一致した。

`3430591eddf072ac619aa18c1a5102abf5ad22129d07cc0227fe32f83d74a812`

raw events、CONTEXT1232 bytes、DR4地点、caller slot、stage bytes、EAXを照合した。
normal/drainのwait/continue inflight=false、未確認領域zero、reader close済み。
fixture_retention=unverified、native_accepted/formal_permission=falseを維持。最終保存の確認は先行reportを根拠とする。
今回の証跡には起動flags専用項目がまだない。使用したclean実装の固定flagsは0x08000406だが、後付けの項目を過去証跡へ追加しない。

## 次に比較する起動条件

現在の診断launchはCREATE_NO_WINDOWを使用している。
[Microsoftの生成flags説明](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags)
では、これはconsole windowなしで起動する指定で、DETACHED_PROCESSと併用した場合は無視される。
[コンソール生成の説明](https://learn.microsoft.com/en-us/windows/console/creation-of-a-console)
では、DETACHED_PROCESSで生成したconsole processはコンソールに接続していないと説明されている。

この違いと今回のallocation候補を根拠に、NO_WINDOWをDETACHEDへ置換する限定比較を準備する。
今回のアクセス拒否を回避できるという点は、これから確認する仮説である。
token/ACL・inherit handles=false・desktop空文字・固定child/environment・所有/停止方法は変更しない。
DETACHED自体をsecurity boundaryや将来のconsole作成禁止とは扱わない。
[比較診断計画](anomaly-multiseed-v0.3-s4-b1-detached-return-plan-2026-09-10.md)で既存return観測のAL/stageを比較する。

追加の静的解析では、現在KernelBase.dllを10秒/8 MiB以内の同一handleで1回読み、既存hash一致とcloseを確認した。
既存PDBの有界readのみ、追加downloadなし。ConsoleAllocateは[0xbf41c,0xbf7eb)の214命令、
ConsoleShouldAllocateConsoleは[0xbefd4,0xbf074)の40命令。
前者はNtCreateFile、ConsoleLaunchServerProcess、接続/標準IO初期化等の負statusを返す候補を持つ。
後者はactivation context設定とprocess parameters上の値などにより分岐する。
今回どの内部CALLが拒否されたか、NO_WINDOW/DETACHEDがこのbuildでどの内部値になるかは直接取得していない。

## 資源・保存物

同run preflightは21 sources/238228 bytes、verified、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
Windows UpdateのUBR緩和と実測記録は維持。
親＋child sample74回、peak commit24358912 bytes（約23.23 MiB）、peak working34574336 bytes（約32.97 MiB）。
実行前PC空きRAM9.23 GiB/C108.21 GiB/D75.36 GiB。時間・memory・disk上限への到達なし。
単発の値からリーク有無は判断しない。既存fixture・証跡を保持し、他project操作・常駐helperなし。

ignored artifacts/context-offline-2026-09-10へ次を保存した。

- console-failure-native-summary.jsonl
- console-failure-native-readback.json
- kernelbase-console-allocation-static.json

console_failure v1の承認済み1回は消化済み。追加の実機起動なし。本流統合・child E2E・native受入・formal permissionは未達。


結果解釈と比較修正をまとめた独立レビュー新規P0〜P3=0、指定fake46/46（0.824秒）pass。
拒否された内部API/object/ACLや根本原因の確定とは区別する留保を維持。進捗ポーリングなし、担当のnative/private参照なし。
比較修正後の全体fake173/173（1.762秒）pass。repository safety/diff-check pass、mainは基準889cfc3のままclean。
保存前の空きRAM8.88 GiB、C108.21 GiB、D75.36 GiB。比較用の追加実機診断は行っていない。
