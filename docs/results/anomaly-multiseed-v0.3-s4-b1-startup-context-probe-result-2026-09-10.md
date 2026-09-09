# S4-B1 最初のunload時context/stack実機診断（2026-09-10）

状態: **承認済み追加診断1回完了 / context・2 KiB stack取得 / 起動障害再現 / 原因未特定**。

ユーザーは「30秒・512 MiB上限で、実行状態と最大2 KiBのスタックを読み取る実機診断を1回」へ
「続けてください」と回答した。HEAD2b0dee1（実装c4fe99e）のcleanな候補worktreeでDebugDriver.runを1回実行した。
新規の専用fixtureを使用し、追加再試行・既存rootの削除/修復/再利用は行っていない。

## 結果

所要2.069秒、driver/observer status=observed、child exit=0xC0000142（3221225794）。
observedは診断観測の完了を表し、child起動成功やnative受入ではない。
通常event7件、Continue確認7件、exception/breakpoint/debug string/RIP eventなし。

| slot | event | 確認内容 |
| --- | --- | --- |
| 0 | CREATE_PROCESS | python.exeのimage取得confirmed |
| 1 | LOAD_DLL | ntdll.dllのimage取得confirmed |
| 2 | LOAD_DLL | kernel32.dllのimage取得confirmed |
| 3 | LOAD_DLL | KernelBase.dllのimage取得confirmed |
| 4 | UNLOAD_DLL | 同一保存記録のmodule3に対応。ここでcontext/stackを取得 |
| 5 | UNLOAD_DLL | 同一保存記録のmodule2に対応。追加取得なし |
| 6 | EXIT_PROCESS | 0xC0000142 |

初期threadのhandle/process identity照合はconfirmed、context state=completed、row status=confirmed。
GetThreadContextの保存領域1232 bytes、ContextFlags=0x00100003、stack要求/読取り長とも2048 bytes。
保存CONTEXT内のRIP/RSPはmetadataの値と一致し、event slot4/TIDも同じraw UNLOAD通知と一致した。
raw register/stack、PID/TID、絶対addressはprivate保存のみ。stack内容の公開・pointer追跡・unwind・symbol取得は行っていない。
この取得だけでは失敗したAPIや正確なcall stackを確定できない。
既存security取得も5対象すべてconfirmed。今回のACL内容まで前回と同一とは未比較のため断定しない。

## 終了・保存・照合

process_signaled=true、debug_ownership_resolved=true、driver/stop teardown=pass、failure_count=0。
TerminateProcess不要、drain待機0回、driver primary/secondaryなし、resource_stop=false。
最終driver結果を先にJSON出力/flushし、その後に任意詳細を表示した。前回のNone枠エラーは再発しなかった。
WriteFile/FlushFileBuffers=confirmed、evidence_file_closed=true、保存サイズ114419 bytes。
fixture_retention=unverified、native_accepted=false、formal_permission=falseを維持した。

実行process内の出力buffer SHA-256:

`c98e30a618e2933d5c206ec292e8dc4d3c5756f751c6cb541b0ea255ef0fb4fe`

実行後の別processで、temp直下4096項目・専用root32件以内のmetadata検索により同サイズ候補1件を選び、
ancestor/fileのheld-handle/reparse/NTFS/identity/stream検査付きで当該証跡のみ有界read-only読込みした。
読取りhashは上記実行時buffer hashと一致。全reader handleをcloseした。
B1DBG001形式、通常7件/drain0件、wait/continue inflight=false、未確定領域bytesがzeroであることを確認した。

hash一致は保存bytesと実行時bufferの一致確認であり、loaded code認証や永続媒体の耐障害性保証ではない。
保存metadataのdriver値はwrite/flush/file close前のscopeであり、それらの最終状態は今回の先行JSON出力で確認した。
前回runで失われた最終状態が、この成功によって遡って確認できたとは扱わない。

## 環境と資源

同runのpreflightは18 sources / 208782 bytes、verified。
Windows10.0.26200.9445、Python3.14.0、既存exe/python314.dll hashと一致。
Windows自動更新によるUBR固定の承認済み緩和は維持し、実測buildを記録した。

| 指標 | 実測 |
| --- | --- |
| memory sampler回数 | 64 |
| 親＋childの記録上peak commit | 24797184 bytes（約23.65 MiB） |
| 親＋childの記録上peak working | 34701312 bytes（約33.09 MiB） |
| 実行前のPC空きRAM/C/D | 8.57 GiB / 102.32 GiB / 75.36 GiB |
| 保存照合後のPC空きRAM/C/D | 9.28 GiB / 102.31 GiB / 75.36 GiB |

512 MiB未満でresource stopなし。ただしsampler値は実行全体の連続測定やリーク試験ではない。
PC全体の変化には別作業を含むため、増減の原因・リーク有無を単発値から判断しない。
追加の権限/ACL変更、code/registry/PEB変更、breakpoint追加、Procmon/CDB/loader snaps、他project操作はない。

## 次の低負荷工程

保存context/stackを対象に、取得imageのidentityと対応するimage範囲・unwind情報をどう検証できるかを先に調べる。
load baseの大小だけで所属moduleやreturn addressを決めず、raw stackをそのままcall stackとして表示しない。
実行中の追加メモリ取得を行わず、対応資料が不足する場合は不足として保持する。
この1回の承認で実childを再起動しない。原因未特定、required E2E/main統合/formal permissionは未達。

## 保存RIPと現在のntdll image情報の照合（2026-09-10）

追加child・remote memory取得・debugger起動なし。前節の保存証跡を同じ上限でread-only読込みし、
実行時buffer hashと一致することを再確認した。image rowのntdll.dllと同じslotのLOAD_DLL baseを対応させた。

最初は既存fixture向け_Boundで現在のSystem32/ntdll.dllを開こうとしたが、hardlink数1の条件で停止した。
production/fixtureの検査は変更せず、解析専用の一時的な読取り手順でnamed default streamを開いた。
既存held-handle検査でancestorのlocal NTFS/reparse/identityを確認し、対象fileは読取りのみ・share-readのみで保持した。
GetFileInformationByHandle/FILE_ID_INFO/normalized NT nameにより非directory・非reparse、volume/file IDと
完全なNT nameが保存image rowに一致することを読取り前後で確認した。ntdllのhardlink数は2だった。

最初の解析専用読取りは、前後のfile info全bytes比較で停止した。再確認では変化項目がaccess timeだけと判明した。
解析用の比較はaccess timeを記録対象に分け、creation/write time、attributes、size、link count、identity等は一致を要求した。
この調整は解析専用で、fixture側のhardlink/identity条件は緩和していない。
取得APIは同じhandleから既定data streamを読むだけで、DLLをload/executeしない。
各読み取り8 MiB/10秒上限、64 KiB単位。最後に全reader handleをcloseした。

現在のntdll.dll:

- file bytes: 2,522,080
- 読取り時SHA-256: `a74f7482085eab125ccc09152ab7e0b5994bcb13e1a7b29880bdbb24179ecb8b`
- machine: AMD64、optional header: PE32+
- SizeOfImage: 2,519,040 bytes
- 保存RIPから保存load baseを引いたRVA: `0x161304`
- 上記RVAは現在fileのimage範囲内・executable section内

[PE形式](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format)に従い、DOS/PE signature、machine、
section数（最大96）、raw file範囲とimage範囲を検査した。RVAからfile offsetへの変換は一意なsectionでのみ行った。
例外tableは1 MiB以下・12-byte単位とし、各entryのbegin/end/unwind RVAの範囲を確認した。
[x64 RUNTIME_FUNCTION](https://learn.microsoft.com/en-us/cpp/build/exception-handling-x64?view=msvc-170)の
begin<=RVA<endを満たすentryは1件で、begin=`0x1612f0`、end=`0x161308`、unwind RVA=`0x1b5630`だった。

export tableの照合ではNtUnmapViewOfSectionとZwUnmapViewOfSectionが同じ`0x1612f0`を指していた。
保存RIPはそこから`+0x14`、かつ上記RUNTIME_FUNCTION範囲内である。
直前export名の近さだけで所属を決めず、今回のsection/range/entryとの一致を併記した。
この時点の実行位置を、失敗した元のAPIやDLL初期化の原因と断定しない。

### 同一性と解釈の限界

volume/file ID/name一致は現在のfileと当時取得したimage handleの識別情報が一致することを示す。
当時のloaded bytes hashは保存していないため、今回読んだ全file bytesが当時のmemory imageと完全一致した証明ではない。
従って関数範囲との対応は、この現在fileを解析資料として適用した結果として扱う。
実行時のrelocation・patch・file変更履歴まで検証したことにはしない。

raw stack2048 bytesはまだunwindしていない。呼出し元を推定する前に、このentryのUNWIND_INFOを境界検査し、
保存CONTEXT/stack内だけで復元できるかを確認する。未対応unwind opcode、chain、epilogue、保存stack範囲外なら止め、
値を並べてcall stackと表示しない。PDB/symbol downloadや現行processへの追加照会は行っていない。

公開可能な照合要約のみartifacts/context-offline-2026-09-10/image-check.jsonへ保持した（Git対象外）。
DLL bytesや生stackの追加コピーは保存していない。複数の読取り試行と停止理由も上記の通り記録した。
今回code変更なし。test再実行・レビュー再委譲・負荷試験・権限設定変更なし。
開始空きRAM9.13 GiB/C102.31 GiB/D75.36 GiB。PC全体の値からリーク有無を判定しない。
