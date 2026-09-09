# S4-B1 保存stackのシンボル・loader内部status照合

状態: **offline解析 / symbol対応確認 / 内部status0xC0000142確認 / 原因未特定 / no native acceptance**。

2026-09-10、[context付き診断結果](anomaly-multiseed-v0.3-s4-b1-startup-context-probe-result-2026-09-10.md)の
保存2048-byte stackから復元済みの11 framesをMicrosoft公開PDBと照合した。
10個の一意なprimary entryすべてに一致する関数名があり、重複frameを含む11位置の名前を付けられた。
さらにLdrpLoadDllInternalで参照するstatusの保存位置を特定し、観測時の値0xC0000142を確認した。
追加実child、対象processへの追加memory/context取得、handler実行は行っていない。

## 1. 対応するPDBの取得と同一性

現在ntdllを既存の有界held-handle手順で読取り、SHA-256が既存記録と一致した。
PE debug directoryの範囲・CODEVIEW type2・RSDS signatureを検査し、RVAとfile pointer双方の内容一致を要求した。
PDB名はntdll.pdbの1件に限定し、任意pathを開いたりURLとして利用したりしていない。

| 項目 | 値 |
| --- | --- |
| image SHA-256 | a74f7482085eab125ccc09152ab7e0b5994bcb13e1a7b29880bdbb24179ecb8b |
| CodeView GUID | c3093720-177d-a685-1519-dcffe8df53fe |
| image CodeView age | 1 |
| symbol key | C3093720177DA6851519DCFFE8DF53FE1 |
| PDB bytes | 1912832（約1.82 MiB） |
| PDB SHA-256 | 879596b54dc0b944e47160dcba01bac56fbc13eaed41fcad50897c6fdd730d1f |
| PDB Info age / DBI age | 4 / 1 |
| DBI machine / flags | AMD64 0x8664 / 2（private symbols stripped） |
| MSF block size / block count / streams | 4096 / 467 / 129 |

[Microsoft公開symbol server](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/microsoft-public-symbols)の
[対象PDB](https://msdl.microsoft.com/download/symbols/ntdll.pdb/C3093720177DA6851519DCFFE8DF53FE1/ntdll.pdb)を利用した。
HEADはmsdlで302、Microsoftのblob配信先で200の計2回、本文GETは1回、所要3.352秒。
非圧縮・16 MiB上限・64 KiB単位・socket timeout5秒・全体30秒のdeadline検査を適用した。
HEAD/GETのContent-LengthとETagを照合した。redirectはHTTPSのmsdlまたはblob.core.windows.netに限定し、
最大4回のHEAD内に収めた。CAB展開・file.ptr追跡・再download・global symbol cache設定はない。

### ageの検証規則

初回の単純なInfo age完全一致検査は4と1の差で停止したため、解析結果を採用せず一次実装を確認した。
[Microsoft PDB1::OpenValidate4](https://github.com/microsoft/microsoft-pdb/blob/master/PDB/dbi/pdb.cpp#L783-L815)は
Info ageがimage age以上、DBI ageがimage ageと一致する条件を使用する。
[LLVMのPDB識別子生成](https://github.com/llvm/llvm-project/blob/main/lldb/source/Plugins/ObjectFile/PDB/ObjectFilePDB.cpp#L27-L31)も
GUIDとDBI ageを利用する。この規則でGUID一致・Info4>=image1・DBI1=image1を検証した。
古いDBI age0の例外は採用せず、imageより古いInfo ageやDBI不一致は拒否する。
InfoとDBIの二つのageを同じ値として記録せず、上表に別々に残した。PDBの変更履歴自体を確定したわけではない。

## 2. 関数名の照合結果

[byte-only PDB reader](../../tests/fixtures/anomaly_v03_offline_symbols.py)を3db6a98で保存した。
[MSF](https://llvm.org/docs/PDB/MsfFile.html)のdirectory/stream範囲・block重複、
[PDB Info](https://llvm.org/docs/PDB/PdbStream.html)と[DBI](https://llvm.org/docs/PDB/DbiStream.html)のidentityを検査する。
PDBのsection headersは現在PEのsection headers全bytesと一致した。OMAPがあれば対応外として停止する。
[LLVMのS_PUB32定義](https://github.com/llvm/llvm-project/blob/main/llvm/include/llvm/DebugInfo/CodeView/SymbolRecord.h)に沿い、
Function flag付きpublic recordのsection:offsetをRVAへ変換し、要求したprimary entryとの完全一致だけを採用した。
近いsymbol名を代用せず、aliasは列挙する。record7378件、public function4864件を走査した。

下表は外側の呼出し元から観測位置へ向かう順である。

| 保存RIP・復元位置RVA | primary entry RVA | 完全一致したsymbol |
| --- | --- | --- |
| 0x8dda6 | 0x8c404 | LdrpInitializeProcess |
| 0xb80e4 | 0xb8024 | LdrpInitializeKernel32Functions |
| 0x3cd60 | 0x3cbf0 | LdrLoadDll |
| 0x1fac0 | 0x1f9c0 | LdrpLoadDll |
| 0x1ff1b | 0x1fc30 | LdrpLoadDllInternal |
| 0x86444 | 0x86390 | LdrpDecrementModuleLoadCountEx |
| 0x867a2 | 0x865c0 | LdrpUnloadNode |
| 0x8683e | 0x865c0 | LdrpUnloadNode |
| 0x17fda | 0x17f40 | LdrpDereferenceModule |
| 0xa7956 | 0xa7914 | LdrpUnmapModule |
| 0x161304 | 0x1612f0 | ZwUnmapViewOfSection, NtUnmapViewOfSection |

これらはprocess初期化、Kernel32関連初期化、DLL読込み、参照解放/unload/unmapに対応する名前である。
名前とCALL照合から観測経路を整理できるが、どのDLLのどの初期化処理が先に失敗したかを示すtraceではない。
Kernel32関連の呼出し経路にあるという事実だけで、Kernel32本体を故障箇所と断定しない。

## 3. loader内部の保存status

現在imageのLdrpLoadDllInternal（entry0x1fc30）を有界decodeし、保存戻り先0x1ff1bの直前を確認した。
RVA0x1fef8でCMP dword [RBX],0、0x1fefbでJGE 0x20038、0x1ff16で
LdrpDecrementModuleLoadCountEx（0x86390）へのCALLがある。
対象CMPのoperand幅4 bytes、base RBX、indexなし、displacement0も機械的に照合した。

3e8d64dで、検証済みcallerごとの復元済みnonvolatile registerをprivate属性に保持する処理を追加した。
初期CONTEXTから与えていないregisterは未知として欠落を維持し、CALL不一致の途中結果は保持しない。
公開dict/JSONやreprへregisterの値を含めない。byte-only helper内にfile/native readはない。

保存証跡を1回再読取りし実行時buffer hash一致を確認、現在ntdllの保存image rowとのidentity/name一致も再確認した。
同じ10段のunwind/CALL照合を経てLdrpLoadDllInternalのRBXを復元したところ、参照先は保存stack offset584だった。
4-byte alignedかつ[0,2044]内であることを確認して、既存stack bytesからDWORDを読んだ。
得られた値は **0xC0000142**（符号付き32-bitで負）で、[NTSTATUS定義](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-erref/596a1078-e883-4972-9bbc-49e60bebca55)の
STATUS_DLL_INIT_FAILEDに対応し、最終EXIT_PROCESSの値と一致した。
絶対RBX/RSPやraw register/stackのコピーは要約へ出していない。保存範囲外へのpointer追跡もない。

これはunload通知時点で保存されていた値である。CMPが実行された過去時点にも同じ値だったこと、
その値を最初に書いた命令、元の失敗API/DLLまでは確認していない。
解放処理中に既にDLL初期化失敗の値が存在したことを補強するが、根本原因の特定ではない。
現在fileと実行時loaded bytesの完全一致未証明という制約も全解析に残る。

## 4. 検証・保存・次工程

symbol parserはsynthetic8件、関係試験28/28 pass（0.176秒）。独立レビュー新規P0〜P3=0、指定23/23 pass（0.142秒）。
private register保持追加後の最終対象は29/29 pass（0.125秒）、追加差分も新規所見0、独立指定16/16 pass（0.123秒）。
repository safety/diff-check pass。独立担当の完了通知を利用し、進捗ポーリングは行っていない。

今回の新規artifactはartifacts/context-offline-2026-09-10内に6件、合計1923059 bytes（Git対象外）。
公開PDB1件とsymbol-key.json、symbol-download.json、public-symbol-match.json、
load-internal-callsite.json、saved-loader-status.jsonを保存した。既存artifactは保持した。
symbol-download.jsonのinternal未検証状態は取得時点の記録で、検証済み結果はpublic-symbol-match.jsonを参照する。
PDBは保存済みcacheを再使用でき、同一fileの再downloadは不要。

現在ntdll2522080 bytesのheld-handle readは今回計3回、保存証跡114419 bytesは1回。
いずれも既存の上限とhash検査を使い、全reader handleをcloseした。ntdll/context/stackの追加diskコピーなし。
空きRAM8.69→8.78 GiB、C102.30→102.29 GiB、D75.36 GiB。PC全体の単発値からリーク有無は判定しない。
追加child/remote memory取得/handler実行/設定や権限変更/他project操作なし。main統合・native受入・formal permissionは未達。

次は、この内部statusを書き込む静的な候補箇所と、保存情報で遡れる限界を整理する。
追加の観測が必要なら、変更内容・上限・停止条件を具体化してから個別の実機承認gateへ進める。
このoffline解析を根拠に既存の診断を自動再実行しない。
