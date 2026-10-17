# S4-B1 DETACHED UNLOAD診断の結果

状態: **bootstrap_unverifiedで既定停止 / UNLOAD未観測 / teardown・証跡保存pass / no native acceptance**。

ユーザーの「お願いします」を[計画](anomaly-multiseed-v0.3-s4-b1-detached-unload-plan-2026-09-10.md)の1回への了承として、
cleanなaf3a0b2（実装021956c）で新規fixture1回を実行した。再試行なし。
wrapper2427 bytes/hashb8ce387f512c150804a6e4de9b6c596f2f5bc063eee7f3e004d4f83a0c8112a7を照合済み。
初期reportまで2.168秒、driver/observer failed、primary=bootstrap_unverified、winerror0、secondaryなし。
requested_creation_flags=0x40e/creation_state=created/ownership transferredを証跡でも照合した。

## 観測した経過

通常18 events/Continue17。python.exeと13 DLLのload、3件のcreate_thread、最後に初期threadのfirst-chance BREAKPOINT。
DLLはntdll/kernel32/KernelBaseに続き、ucrtbase/vcruntime140/python314/version/ws2_32/msvcrt/rpcrt4/advapi32/sechost/bcrypt。
UNLOADは来なかった。DebugContextはready/not_observed、entry not_started、Get/RPM/Set各0回。
DLLのロード確認は、その初期化やPython mainの完了確認とは区別する。

例外はslot17、0x80000003、first_chance1、flags0、chained record null、parameters1、初期thread/PID一致。
addressはntdll load baseに対するRVA0x122239。parameter[0]=0を追加照合した。
既定の全breakpoint拒否規則によって停止し、通常のDBG_CONTINUEでは解放しなかった。
自然EXITは未観測であり、今回0xC0000142を再観測したとは扱わない。

Terminate要求後の所有stopでpendingを解放し、drain4件（3 exit_threadと1 exit_process、全code1）をContinueした。
process signaled、debug ownership解消、所有process/thread handle close、teardown pass/failure_count0、
driver teardown failures0を確認。強制停止によるcode1を自然なアプリ終了理由に読み替えない。

## 証跡と追加の静的照合

private証跡110163 bytes/hash051289d145635778ec9073fc44440694ffc110304af6442d770b2d427ff99cfb。
write/flush confirmed、file closed。正常/drain両領域のinflight false、未確認buffer部分の非zeroなし。
有界held-file read1回でraw events/例外/launch/stopとhashを照合しreader close。
独立設計レビューでparameter契約の明確化が必要となり、同じhashの証跡をさらに1回読み、
parameter[0]=0/未使用parameter領域も0を確認した。合計2回。追加child診断はしていない。
探索は既存の専用prefix、root数32/entry数4096/10秒以内と候補file metadataに限定し、
内容を読んだprivate証跡は各回とも当該1 file。既存fixtureの削除・repair・再利用なし。
公開要約はdetached-unload-native-summary.jsonl/readback.jsonとdetached-bootstrap-parameter-check.jsonに保存。

現在ntdll.dllを有界の同一handleで1回読み、hash a74f7482085eab125ccc09152ab7e0b5994bcb13e1a7b29880bdbb24179ecb8bを確認。
2522080 file bytes/SizeOfImage2519040、close確認。既存PDB1912832 bytes/hash
879596b54dc0b944e47160dcba01bac56fbc13eaed41fcad50897c6fdd730d1fを参照し、追加downloadなし。
GUID/DBI age/PE section照合済みpublic symbolで、0x122204..0x122242はLdrpDoDebuggerBreak、
0x122239はint3命令だった。静的関数62 bytesのSHA-256は
cc1cef07481f3ac8e2dc416ffe823e0fd00b0c493355ade7e14aa31067bfa009。
prologueはsub rsp,0x38、caller slot候補はRSP+0x38。
固定direct CALLは8c2db→8c2e0（_LdrpInitialize）、8dbdc→8dbe1と8df3f→8df44（LdrpInitializeProcess）。
ntdll-bootstrap-static.jsonへ保存。実childのcode一致やcallerはまだ取得していない。

Microsoftの[初期breakpointの説明](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/initial-breakpoint)とも整合する候補だが、
RVA/symbolだけで今回の例外を通常継続できるとは扱わない。識別条件を実childの有界読取りで確認する次段を準備する。

## 環境と資源

同run preflight22 sources/242703 bytes、verified、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
last boot2026-09-09T10:43:08.5000000+09:00、Windows Update後のUBR緩和を維持して実測値を記録。
memory samples125、親＋child peak commit26464256 bytes（25.24 MiB）/peak working35581952 bytes（33.93 MiB）。
実行前空きRAM8.44 GiB、C107.92/D75.36 GiB。単発値からリーク有無は判定しない。他project操作なし。
fixture retentionはunverified、全acceptance gate no。本流889cfc3はcleanのまま。

次は[検証した初期停止点を1回継続する計画](anomaly-multiseed-v0.3-s4-b1-bootstrap-unload-plan-2026-09-10.md)を参照。


準備作業後の空きRAM8.06 GiB、C107.92/D75.36 GiB。次の候補はpure/fake245件・独立実装レビューを通過。追加実機なし。
