# S4-B1 DETACHED起動での初期化return比較結果

状態: **限定比較1回終了 / AL=1・stage=700観測 / 終了・保存確認済み / child E2Eは未確認 / no native acceptance**。

## 直接観測

ユーザーの「続けてください」をDETACHED比較の限定1回への了承として、cleanな1e04198（実装eaacd30）で実行した。
新規fixture1回、DebugDriver(init_return=True, detached_console=True)。初期reportまで1.990秒。
resource_stop=false、secondaryなし。collector completed/confirmed、primary=init_return_observed_stop。
driver/observerのfailedは観測後の意図的停止によるもので、今回の初期化値の確認失敗を意味しない。

| 項目 | 今回 |
| --- | --- |
| 起動要求flags | 0x40e、creation_state=createdをprivate証跡で確認 |
| 対象 | CREATE/KernelBase LOAD/例外で同じprocess・初期thread |
| 例外 | first chance 0x80000004、flags0、parameters0、chained recordなし |
| 地点 | RVA0x50ba、例外address/RIP一致 |
| reason/TF | EBX下位32 bits=1、TF=0 |
| AL | 1（returns_false=false） |
| stage | WORD RVA0x3aeea0=700 |
| 取得 | Get3/Set1/RPM3回2197 bytes |
| code照合 | LOAD時の固定2窓2195 bytes一致 |

設定前DR0〜3/DR6/DR7は0。DR0要求/読み戻し/hitはtargetに一致、DR1〜3は0。
DR6は要求0x10800→設定後0→hit0xffff0ff1、DR7は要求/設定後1→hit0x401。
返却ContextFlagsは0x100010/0x100010/0x100013。標準cause mask0xe00fでB0だけ1、全照合が一致した。
API値からBLD/RTM/reserved bitsのhardware状態や複合原因の不存在は推測しない。

## 比較で分かった範囲

| 観測 | 起動設定 | 同じreturn地点でのAL / stage |
| --- | --- | --- |
| [return v3](anomaly-multiseed-v0.3-s4-b1-init-return-v3-result-2026-09-10.md) | 保存済み実装のNO_WINDOW | 0 / 600 |
| 今回 | 証跡で要求確認したDETACHED | 1 / 700 |

途中の[4地点診断](anomaly-multiseed-v0.3-s4-b1-console-failure-result-2026-09-10.md)ではallocation候補でC0000022を観測した。
今回の比較は、コンソールの起動設定変更が観測した初期化失敗の回避に有効であるという仮説を支持する。
ただし単発比較で全条件を固定した因果証明ではなく、拒否されたobject/ACL/内部APIまでは確定していない。
loaded image全体の同一性や、非介入時の全経路の同一性も保証しない。

RVA0x50baはMOVZX EAX,ALの直前であり、RETやPythonのmain実行前に終了した。
AL1/stage700は今回の地点で成功側の値を持ったという観測で、実際のcallback復帰・Python起動・child E2E成功とは区別する。
次は[通常の制限付きchildを最後まで検証する計画](anomaly-multiseed-v0.3-s4-b1-detached-control-plan-2026-09-10.md)へ進む。

## 終了と証跡

通常5 events/Continue4。例外は通常Continueせず、TerminateProcess確認後にpendingを解放した。
drain1件のEXIT code1をContinueし、process signal/debug ownership解消/所有handle closeを確認。
自然終了は未観測。teardown pass、failure_count0、driver_teardown_failures0。

最終reportを先に出力/flushし、private証跡112070 bytesをwrite/flush/close。
bufferと保存fileの有界held-handle readback1回のSHA-256が一致した。

`a6c04ef33df6b6fc2a73c2b1e20612436188b4bad115c186c72bcb8e6e94d37e`

raw CREATE/LOAD/例外とCONTEXT1232 bytes、DR・RIP/reason/AL/TF・stage、起動要求flagsを照合した。
normal/drainともwait/continue inflight=false、未確認領域zero、reader close済み。
fixture_retention=unverified、native_accepted/formal_permission=falseを維持。最終保存の確認は先行reportを根拠にする。

同run preflightは21 sources/239171 bytes、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
memory sample72回、親＋child peak commit24428544 bytes（約23.30 MiB）、peak working34660352 bytes（約33.05 MiB）。
実行前PC空きRAM7.81 GiB/C107.93 GiB/D75.36 GiB。単発値からリーク有無は判断しない。
今回追加DLL/PDB読取り・downloadなし、既存fixture/証跡の削除・再利用なし、他project操作なし。

公開要約はignored artifacts/context-offline-2026-09-10/detached-return-native-summary.jsonlとdetached-return-native-readback.json。
承認済みの比較1回は消化済み。通常control harnessの実機実行はまだ行っていない。
本流統合、S4/native受入、formal permissionは未達。


結果解釈とcore修正の独立レビュー新規P0〜P3=0、指定pure61/61（0.173秒）pass。
成功側の観測と実RET/child E2E成功の区別を維持。担当のnative/private参照なし、進捗ポーリングなし。
coreの起動flags修正後、pure/fake全体234/234（2.074秒）pass、repository safety/diff-check pass。
保存前PC空きRAM8.32 GiB、C107.94 GiB、D75.36 GiB。mainは基準889cfc3のままclean。
