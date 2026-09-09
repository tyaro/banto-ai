# S4-B1 最初のunload時context/stack実機診断（2026-09-10）

状態: **承認済み追加診断1回完了 / context・2 KiB stack取得 / 起動障害再現 / 原因未特定**。

最新追記: 末尾の「保存範囲までの10段復元」を参照。10件のCALL targetを照合し、保存stack範囲外で停止した。原因は未特定。
後続の関数名と内部statusの照合は[シンボル解析結果](anomaly-multiseed-v0.3-s4-b1-startup-symbol-analysis-2026-09-10.md)を参照。

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

## 保存スタックからの1段の復元（2026-09-10）

追加child・remote read・symbol downloadなし。保存証跡と現在ntdllを前節の有界read-only手順で読み、
両方の記録済みSHA-256と一致した。ntdllのvolume/file ID/name、access timeを除くfile infoも前後で一致し、
取得後に全reader handleをcloseした。以下は現在のidentity/hash一致imageを適用した条件付き解析である。
実行時loaded bytesの完全一致未証明という制約は維持する。

最初のRUNTIME_FUNCTIONのUNWIND_INFO（RVA0x1b5630）はversion1、flags0、prolog0、
code count0、frame register0。保存RIP RVA0x161304の現在image bytesはC3 CD 2E C3で、先頭C3はnear RET。
[x64 epilogue](https://learn.microsoft.com/en-us/cpp/build/prolog-and-epilog?view=msvc-170)と
[unwind仕様](https://learn.microsoft.com/en-us/cpp/build/exception-handling-x64?view=msvc-170)に照らし、
この限定形では保存RSP先頭の8 bytesを戻り先として取り出し、RSPを8進める1段のみを復元した。
stack全体の走査や、addressらしい値の列挙をcall stackの代用にしていない。

| 項目 | image相対値 |
| --- | --- |
| 観測した関数 | Nt/ZwUnmapViewOfSection、[0x1612f0,0x161308) |
| 観測RIP | 0x161304 |
| 保存stackから復元した戻り先 | ntdll RVA0xa7956 |
| 戻り先を含むRUNTIME_FUNCTION | [0xa7914,0xa7962) |
| 呼出し命令の位置 | RVA0xa7951 |
| 呼出し命令bytes | E8 9A 99 0B 00 |
| rel32を符号付きで計算した呼出し先 | RVA0x1612f0（観測関数beginと一致） |

戻り先はntdllのexecutable section内で、一意なRUNTIME_FUNCTION範囲に入った。
直前5 bytesのCALL rel32の終端が戻り先に一致し、そのtargetも観測したNt/ZwUnmapViewOfSectionと一致した。
このcallsite照合により1段の復元を補強した。ただし呼出し元の私有関数名や、元の起動失敗原因は未特定。

### 次のframeに必要な情報と未実施範囲

呼出し元のUNWIND_INFOはRVA0x1a3ca4、version1、flags0、prolog6、frame register0、codes06320230。
公開定義上のUWOP_ALLOC_SMALL（32 bytes）とUWOP_PUSH_NONVOL（RBX）に対応する形である。
戻り先以降のimage bytesは48 83 63 30 00 48 83 C4 20 5B C3 CC。
今回、このframeのbody/epilogue判別を含むunwindは実行しておらず、2段目の戻り先を確認済みとは扱わない。
次に進む場合は保存stack内のoffset、nonvolatile register復元、実行位置、callsiteを検査し、
未対応opcode/chain/保存範囲外ならそこで停止する。単純に全frameへ同じRSP加算を繰り返さない。

解析の公開可能なRVA/命令/状態だけをartifacts/context-offline-2026-09-10/first-unwind.jsonと
first-unwind-verified.jsonへ保存した。前者の未照合状態も残し、後者にCALL target照合結果を追記した。
絶対address・raw stackの追加コピーは保存していない。production/test code変更、実機再実行、設定変更なし。
開始空きRAM8.80 GiB/C102.31 GiB/D75.36 GiB。全体値の単発測定でリーク有無を判定しない。

## 保存スタックの限定複数段unwind（2026-09-10）

前節の1段復元をbyte-only helperへまとめ、対応形式の範囲だけ呼出し元をたどった。
[解析実装](../../tests/fixtures/anomaly_v03_offline_unwind.py)はPE bytes、image base、保存RIPと
2048-byte stackを引数に取り、最大16段で停止する。内部でfile/remote memory取得、child起動、
Windows unwind API、symbol downloadは行わない。既存環境のCapstone 5.0.7で命令境界を照合した。
この解析専用依存はpyproject.tomlのoptional extra `offline-analysis` に分離し、標準環境の依存は増やさない。
追加install/downloadは行っていない。

### 対応条件と停止条件

PE/section/RVA/例外tableの一意な有界mapping、RUNTIME_FUNCTION全体の命令decodeを要求する。
[Microsoft x64 unwind仕様](https://learn.microsoft.com/en-us/cpp/build/exception-handling-x64?view=msvc-170)に基づき、
version1/flags0/frame register0、prolog外のbodyを対象に、PUSH_NONVOL、ALLOC_SMALL、ALLOC_LARGE、
SAVE_NONVOLだけを扱う。復元する保存registerの値は内部だけに保持する。
[epilogue仕様](https://learn.microsoft.com/en-us/cpp/build/prolog-and-epilog?view=msvc-170)を踏まえ、
bare RET（C3）は現在のstackから戻る操作だけを行い、prolog効果を二重に巻き戻さない。
pop/ret/jmp/add/leaから始まるその他の位置は、未対応の可能なepilogueとして停止する。
一般的なx64 unwinderの完全実装ではなく、未対応opcode/flags/frame register/prolog、
不完全なdecode、保存stack範囲外やcallsite不一致では追加frameを採用しない。
各戻り先は同じimageのexecutable sectionと一意な関数範囲に入り、その直前のCALL rel32の
終端が戻り先、targetが直前frameの関数beginと一致することを要求する。

### 保存証跡への適用結果

証跡114419 bytesと現在ntdll2522080 bytesを既述の有界read-only手順で各1回読取り、
記録済みSHA-256一致を再確認した。ntdllのvolume/file ID/nameと、access timeを除くfile infoも
前後で一致した。全reader handleをcloseし、DLL bytesやraw stackの追加diskコピーは作らなかった。
実行時loaded bytesの完全一致は引き続き未証明であり、以下は現在のidentity/hash一致imageを適用した条件付き結果である。

| 段 | 実行位置RVA | RUNTIME_FUNCTION範囲 | 保存stack先頭からのRSP差分 |
| --- | --- | --- | --- |
| 観測frame | 0x161304 | [0x1612f0,0x161308) | 0 bytes |
| 呼出し元1 | 0xa7956 | [0xa7914,0xa7962) | 8 bytes |
| 呼出し元2 | 0x17fda | [0x17fb2,0x18016) | 56 bytes |

1段目は前節のbare RETとCALL照合を再現した。
2段目はbodyのALLOC_SMALL32 bytesとPUSH_NONVOL RBXを巻き戻し、保存stack offset40からRBX、
offset48から戻り先を取得した。CALL位置0x17fd5のtargetは0xa7914で、前frameの関数beginと一致した。
合計2回のunwindと2件のCALL target照合に成功した。私有関数名や元の起動失敗原因は特定していない。

呼出し元2から先は `unwind_flags_or_frame_register` で停止した。
この要約だけではflagsとframe registerのどちらが該当したかを区別していない。
handler/chain/frame pointerの特定形式を確認済みとは扱わず、3回目のunwindは成立していない。
次は停止したentryのheaderを境界検査して分類し、対応拡張が保存範囲内で可能かを検討する。
新たなchildの実行承認には進んでいない。

### 検証・保存・資源

synthetic PE/stackで2段成功、CALL不一致、未知形式、範囲外、epilogue/命令途中、PE境界を検証した。
独立レビューのP2 1件（命令operandに任意即値/絶対addressが入り得る）を修正し、公開出力をmnemonicだけにした。
movabs即値の非出力回帰試験を追加し、同担当が修正確認、新規P0〜P3=0。
依存がない環境でtest discoveryを壊さないようoptional extraと明示skipを追加し、追加差分も新規所見0。

最終pure/fakeはoffline unwind7件＋既存evidence reader5件の12/12 pass（0.118秒）。
独立担当も12/12 pass（0.110秒、依存分離前）を確認し、依存分離後はsite-packages無効環境の7件skipを確認した。
こちらでも同じ未導入条件でdiscovery成功・7件skipを確認した。これは任意offline解析試験に限る扱いで、
必須native試験のskip/受入には転用しない。repository safety/diff-check pass。レビューの進捗ポーリングなし。

初回の派生要約をartifacts/context-offline-2026-09-10/multi-unwind.jsonへ保持した。
修正後の参照要約multi-unwind-reviewed.jsonは、その既存要約からoperandのみ省いた派生物であり、
取得/解析を再実行した結果ではない。元要約のhashと変換内容を併記し、初回要約も履歴として保持した（いずれもGit対象外）。
実装中の空きRAM8.70→8.69→8.66 GiB、C102.31→102.30 GiB、D75.36 GiB。
PC全体のsnapshotからメモリリークを判定しない。追加実child・remote read・権限/設定変更・他project操作なし。
required E2E/main統合/native受入/formal permissionは未達のまま保存する。

## 保存範囲までの10段復元（2026-09-10）

前節の未対応停止を順に分類し、同じ保存証跡に対するoffline解析を拡張した。
最終実装は `b4ff9e7`（CHAININFO対応 `a647a7f`、非SP演算の判別 `68ea66e` を含む）。
新たなchild、GetThreadContext/ReadProcessMemory、Windows unwind API、symbol取得は実行していない。

### 停止形式の分類と対応

最初の停止RVA0x17fdaのUNWIND_INFOはRVA0x1a577c、version1/flags4/frame0、prolog10/code slots4だった。
codes0a74070005640600はRDI/RSIのSAVE_NONVOLで、連結先はRUNTIME_FUNCTION [0x17f40,0x17fb2)、
unwind RVA0x1a5774、version1/flags0/frame0、prolog6/codes06320230だった。
[MicrosoftのCHAININFO定義](https://learn.microsoft.com/en-us/cpp/build/exception-handling-x64?view=msvc-170#chained-unwind-info-structures)と照合した。

連結は最大8 records、各parentはpdataの完全一致entryで、前方循環・順序違反・範囲外なら拒否する。
secondaryはRSPを変えないSAVE_NONVOLだけに限定し、parentの全unwind codesを適用する。
CALL targetはsecondary断片のbeginではなくprimary procedureのentryと照合する。
この変更で呼出し元5段と5件のCALL targetが一致し、次のLEAで停止した。

RVA0x86444はLEAの直後にCALLが続くbodyだった。
[epilogue形式](https://learn.microsoft.com/en-us/cpp/build/prolog-and-epilog?view=msvc-170)に合わせて、
ADD/LEAはdestinationが明確な非SP registerの場合だけbodyとして扱うよう判別を狭めた。
RSP/ESP/SP/SPL、未知destination、その他のPOP/RET/JMP停止は維持する。一般epilogueの実行再現は追加しない。
これで6段目を照合した後、RVA0x1ff1bのversion1/flags2/frame0で停止した。

最後に、exception/termination handlerを持つprimaryのflags1/2/3をcontext復元の対象にした。
handler RVAはexecutableな一意のRUNTIME_FUNCTION先頭とraw mappingを検査するだけで、
handler codeのdecode/呼出しやlanguage-specific dataの解釈は行わない。CHAININFOとの混在flags5/6/7は拒否する。
これは保存した呼出し時のcontextを逆算する処理で、例外dispatchや終了処理の実行を再現するものではない。
[RtlVirtualUnwindのcontext復元とcallback情報](https://learn.microsoft.com/en-us/windows/win32/api/winnt/nf-winnt-rtlvirtualunwind)も参照したが、同API自体は使っていない。
handler有りという属性だけで、観測時にexceptionやhandler実行があったとは推定しない。

### 最終結果と保存範囲

観測frame（RVA0x161304）に加え、下表の10段を復元した。各行で直前CALLの終端が戻り先、
CALL targetが直前frameのprimary entryと一致した。全て同じntdll image内である。

| 呼出し元の段 | 戻り先RVA | 戻り先を読んだstack offset (bytes) | CALL位置RVA | 照合したtarget RVA |
| --- | --- | --- | --- | --- |
| 1 | 0xa7956 | 0 | 0xa7951 | 0x1612f0 |
| 2 | 0x17fda | 48 | 0x17fd5 | 0xa7914 |
| 3 | 0x8683e | 96 | 0x86839 | 0x17f40 |
| 4 | 0x867a2 | 192 | 0x8679d | 0x865c0 |
| 5 | 0x86444 | 288 | 0x8643f | 0x865c0 |
| 6 | 0x1ff1b | 352 | 0x1ff16 | 0x86390 |
| 7 | 0x1fac0 | 496 | 0x1fabb | 0x1fc30 |
| 8 | 0x3cd60 | 960 | 0x3cd5b | 0x1f9c0 |
| 9 | 0xb80e4 | 1200 | 0xb80df | 0x3cbf0 |
| 10 | 0x8dda6 | 1616 | 0x8dda1 | 0xb8024 |

最終frameはRVA0x8dda6、関数範囲[0x8c404,0x8e24a)、保存stack先頭からのRSP差分1624 bytes。
その先は `saved_stack_exhausted` で停止した。次frameを復元するには保存2048-byte window外の参照が必要となり、
11回目のunwind/CALL照合は成立していない。欠けた値の補完や追加memory取得は行っていない。
同じ関数断片内に戻る2行も、stack上の別位置と各CALL target照合に基づく別frameとして記録する。

volume/file ID/nameと既存hashの一致は維持したが、実行時loaded bytesの完全一致は依然未証明。
今回の結果も、現在の一致imageを適用した条件付き解析である。私有関数名、元の失敗API、起動失敗原因は未特定。
保存範囲内でこれ以上frame数を増やす根拠は得られていない。
次の低負荷工程は、既に復元した関数の役割を照合できるsymbol資料の同一性・取得量・保存上限を検討すること。
その資料確認と、新たな実機診断の承認は別に扱う。

### 検証・取得量・保存

独立レビューは各差分の完了通知を利用し、進捗ポーリングなし。
CHAININFO差分17/17 pass（ローカル0.129秒、独立0.122秒）、非SP判別18/18 pass（0.127秒、0.113秒）、
最終handler差分20/20 pass（0.122秒、0.125秒）。各独立レビューの新規P0〜P3=0。
最終20件はoptional offline解析15件＋既存evidence reader5件のsynthetic/pure試験である。
循環/深さ/不正連結、primary target不一致、stack範囲、SP aliases、handler entry/末尾切れを含む。
repository safety/diff-check pass。必須native試験の条件は変更していない。

今回は段階的な分類2回と保存証跡への適用3回で、ntdll2522080 bytesを合計5回read-only読取りした。
各回、保持handleによる非reparse/一意path/前後identity・file info（access timeを除く）、祖先のlocal NTFS、
8 MiB上限・64 KiB単位・10秒deadlineの検査を行い、同じSHA-256だった。全handleをcloseした。
分類2回は先にidentity一致済みのimage hashとの照合、適用3回では保存image rowのvolume/file ID/nameも直接照合した。
保存証跡114419 bytesは適用時の計3回、temp候補4096/root32以内の探索と既存held-handle/stream検査を経て読んだ。
毎回実行時buffer SHA-256と一致し、raw context/metadata/eventのRIP/RSP/TID整合も確認した。
追加のDLL bytes、raw context/stackのdiskコピーは作っていない。

公開可能な派生要約はartifacts/context-offline-2026-09-10内に新規5件、計16921 bytesを保存した（Git対象外）。
stopped-unwind-header.json、chain-unwind.json、epilogue-stop-check.json、chain-body-unwind.jsonは途中の確認履歴。
現在の参照結果はhandler-context-unwind.jsonで、handlers_invoked/loaded_bytes_match_proven/native_acceptedはいずれもfalse。
過去の証跡・要約は保持した。code/DLL取得のdownload/install、設定/権限変更、他project操作なし。
開始空きRAM8.94 GiB→解析後9.02 GiB、C102.30 GiB/D75.36 GiBは同値。
短時間のPC全体snapshotであり、リーク試験や別projectの状態判定は行っていない。全acceptance gate no。
