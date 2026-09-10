# S4-B1 bcrypt内部の初期化処理から C0000022 を取得

状態: **限定診断1回完了 / call_59e0の候補値を確認 / 所有終了・証跡保存とreadback完了 / child E2E未達**。

[保存済み計画](anomaly-multiseed-v0.3-s4-b1-bcrypt-failure-plan-2026-09-10.md)への「お願いします」を1回への了承として、
cleanな01ba29a（実装1c56b89）で新規fixture1個を実行した。
wrapper2735 bytes/SHA-256 7a452b75ccfc721ecfd53ca8293b0fc9ccaae599fc6c0aec9555a57f49c1b2a8を起動前照合、run1回、自動再試行なし。

## 観測と終了

初期reportまで2.497秒。primary=bcrypt_failure_observed_stop、secondaryなし、resource_stop=false。
driver/observer failedは観測後に意図して通常継続を止めた結果で、context completed/status confirmed、Set verified。
要求flags0x40e、creation created、ownership transferred。通常19 events/Continue18。

| 項目 | 実測 |
| --- | --- |
| bootstrap | slot17、verified、Continue confirmed |
| 対象DLL | bcrypt.dll、confirmed LOAD slot16 |
| hit | slot18、DR2、bcrypt RVA b22d |
| 呼出し候補 | call_59e0 |
| EAX / EBX | C0000022 / C0000022 |
| caller RVA | 111cf（固定frameのreturn slot） |
| DR6 arm / hit | 0 / ffff0ff4 |
| DR7 arm / hit | 55 / 455 |

初期process/thread、first-chance80000004/flags0/chained null/parameters0、RIP/TF0、
4つのDR address/単一cause/local enable、bcrypt load寿命、RSP整列/callerを照合した。
collectorはGet3/Set1/RPM3回730 bytes、bootstrap込みGet4/Set1/RPM6回805 bytes。

collectorのstatus_domainはunclassified_nonzeroのまま保持した。
数値C0000022はWindowsのNTSTATUS表ではSTATUS_ACCESS_DENIED（アクセス拒否）に対応する。
ただし今回の観測だけでは、具体的なAPI・対象object・拒否した権限までは特定していない。
[Microsoft NTSTATUS定義](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-erref/596a1078-e883-4972-9bbc-49e60bebca55)

hitは通常Continueせずowned terminateを要求、pending解放後drain4（thread exit3/process exit1、全code1）をContinue。
process signal/debug ownership解消、teardown pass/failure_count0、所有process/thread handles closed、
driver teardown failures0。自然EXITは未観測、code1は意図した停止の結果。fixture保持は存在unverified、cleanup/repairなし。

## 保存と資源

private117453 bytes/SHA-256 61994b9cac08a1861dca18c3c6bcb092ee8aaa8be746ca1a580b05cc54668013、
write/flush confirmed、evidence file closed。
有界held-file read1回でhash、全normal/drain events、bootstrap code/CONTEXT/caller、
3回のdebug CONTEXT、hit CONTEXT/固定caller、module LOAD/launch/stopを照合しreader close。
全inflight false、未確定buffer領域zero。公開要約bcrypt-failure-native-summary.jsonl、
readback bcrypt-failure-native-readback.jsonを保存。private address/path/rawは公開要約に出していない。

同run preflight25 sources/270313 bytes、verified、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
memory169 samples、親＋child peak commit26005504 bytes（24.80 MiB）、working36855808 bytes（35.15 MiB）。
実行前空きRAM8.03 GiB、C108.00/D75.36 GiB。last boot2026-09-09T10:43:08.5000000+09:00。
Windows Update後のUBRは記録し、承認済み固定条件緩和を維持する。単発値からリーク有無は未判定。他project操作なし。

## 静的な追加切り分け

前回保存したbcrypt-reference-entry.jsonの参照bytes/hashを再照合し、cacheだけで解析した。追加DLL/PDB read/downloadなし。
59e0..5bee（526 bytes/hashbbd5eca24408795c3fcee6428d84a34b43eb7a1296a06f47e34d0f8756b288f2）では、
RtlInitializeCriticalSectionの負値、5bf4の負値、固定allocation等の失敗が返り得る。
5bf4..5e0c（536 bytes/hash162e399544b17a5a96af1d8ec63d4a0d0c04eee8422df0febb544b59152f922f）には、
NULL引数のCreateEventW、GetLastError、2回の73cc、7f50等の経路がある。過去の実行経路を静的解析だけで断定しない。

CreateEventWはsecurity attributesがNULLならcreator token由来の既定security descriptorを使う。
[Microsoft CreateEventW仕様](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-createeventw)
引継書§42では既定DACLにRC直接ACEがないことを観測済みだが、今回の失敗との因果関係は未確認。
token/DACL/ACLの変更は行っていない。

bcrypt-call-59e0-static.json、bcrypt-call-5bf4-static.json、bcrypt-detail-recipe.jsonへ保存。
次は[詳細経路の観測計画](anomaly-multiseed-v0.3-s4-b1-bcrypt-detail-plan-2026-09-10.md)を参照。
全acceptance gate no、本流統合/formal/B2/publisherは未実施。

作業後空きRAM8.41 GiB、C107.99/D75.36 GiB。本流889cfc3 clean、追加nativeなし。
