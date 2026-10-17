# S4-B1 bcrypt後始末前で EAX/EBP=C0000022、EDI=0 を取得

状態: **限定診断1回完了 / 混合候補値を確認 / 所有終了・証跡保存・readback完了 / child E2E未達**。

[準備済み計画](anomaly-multiseed-v0.3-s4-b1-bcrypt-detail-plan-2026-09-10.md)への「お願いします」を1回への了承として、
cleanな7fff7f8（実装0f34ece）で新規fixture1個を実行した。
wrapper2760 bytes/hash21855bf61836619d7f0aaa58a0167de136f0ba9b034cf6fbddf0cc9c5853565aを起動前照合、run1回、自動再試行なし。

## 観測と終了

初期reportまで2.709秒。primary=bcrypt_detail_observed_stop、secondaryなし、resource_stop=false。
driver/observer failedは観測後に通常継続を意図して止めた結果。context completed/status confirmed、Set verified。
要求flags0x40e、creation created、ownership transferred。通常19 events/Continue18。

| 項目 | 実測 |
| --- | --- |
| bootstrap | slot17、verified、Continue confirmed |
| DLL | bcrypt.dll、confirmed LOAD slot16 |
| hit | slot18、DR2、bcrypt RVA5dd5 |
| candidate / domain | cleanup_candidates / mixed_cleanup_candidates |
| EAX / EBP | C0000022 / C0000022 |
| EDI | 0 |
| caller RVA | 5ab5、RSP+128の固定return slot |
| RSI / R15 | bcryptbase+25b10 / 0 |
| DR6 arm / hit | 0 / ffff0ff4 |
| DR7 arm / hit | 55 / 455 |

初期PID/TID、first-chance80000004/flags0/chained null/parameters0、RIP/TF0、全DR address/cause/local enable、
load寿命とcaller等を照合した。collector Get3/Set1/RPM4回1798 bytes、bootstrap込みGet4/Set1/RPM7回1873 bytes。
イベント作成失敗後のGetLastError地点5dafは未観測。5dd5をCreateEvent失敗の直接観測とは扱わない。
EAX/EDI/EBPは混合候補として保存し、特定APIの確定値へ読み替えていない。

hitは通常Continueせずowned terminateを要求、pending解放後drain4（thread exit3/process exit1、全code1）をContinue。
process signal/debug ownership解消、teardown pass/failure_count0、所有process/thread handles closed、
driver teardown failures0。自然EXIT未観測、code1は意図した停止の結果。fixture存在unverified、cleanup/repairなし。

## 証跡と資源

private117656 bytes/hash562d2d593fe971756d0b3f8d0cc39b19dbf070e00b3742a4ac7100d613ce9526、
write/flush confirmed、evidence file closed。有界held-file read1回でhash、全events、
bootstrap code/CONTEXT/caller、debug CONTEXT、hit CONTEXT/caller/混合値、LOAD/launch/stopを照合しreader close。
全inflight false、未確定buffer領域zero。
公開要約bcrypt-detail-native-summary.jsonl、readback bcrypt-detail-native-readback.jsonを保存。

同run preflight26 sources/273838 bytes、verified、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
memory171 samples、親＋child peak commit26103808 bytes（24.89 MiB）/working36925440 bytes（35.21 MiB）。
実行前空きRAM8.10 GiB、C107.99/D75.36 GiB。last boot2026-09-09T10:43:08.5000000+09:00。
承認済みUBR固定緩和を維持して実測buildを記録する。単発値からリーク有無は未判定。他project操作なし。

## 静的な候補の絞り込み

前回保存したbcrypt-reference-entry.jsonのbytes/hashを照合し、cacheだけで解析。追加DLL/PDB read/downloadなし。
7f50..814e（510 bytes/hash4595d1a8c776d1e51cd099df30d75df59f4afaafc567670c70e6c53ac98752de）には、
内部helper8154の負値、NtDeviceIoControlFile戻り値、応答値の変換経路がある。
8154..81e4（144 bytes/hashb7c1827567ac4c348697ba1b03d391b1f2f5f21cca52c139ac99237f61c35a9c）はNtOpenFileを呼ぶ。
EAX/EBP負値・EDI0の実測は、7f50の負値を後始末前に保持する静的経路と整合するが、直接のAPI戻り観測ではない。

固定文字列はRVA1f098の\\Device\\KsecDD（終端込み30 bytes）。
参照命令列のNtOpenFile要求はaccess100003/share7/options20、デバイス制御コード390400、初期化command10500。
これらは静的参照値で、既存handleの実対象・実行時IATの認証ではない。
NtOpenFileは既存device等を開くAPI、NtDeviceIoControlFileは対象handleへ制御要求を渡すAPIである。
[Microsoft NtOpenFile](https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntopenfile)、
[Microsoft NtDeviceIoControlFile](https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntdeviceiocontrolfile)

bcrypt-call-7f50-static.json、bcrypt-call-8154-static.json、bcrypt-device-recipe.jsonへ保存。
token/DACL/ACL・デバイス設定は変更していない。
次は[デバイス経路の観測計画](anomaly-multiseed-v0.3-s4-b1-bcrypt-device-plan-2026-09-10.md)を参照。
全acceptance gate no、本流統合/formal/B2/publisher未実施。

作業後空きRAM7.82 GiB、C107.98/D75.36 GiB。本流889cfc3 clean、追加nativeなし。
