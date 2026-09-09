# S4-B1 token/process/thread権限観測付き実機診断（2026-09-10）

状態: **承認済み追加診断1回完了 / 5対象取得済み / 起動障害再現 / 原因未特定**。

ユーザーは権限設定を変更せず30秒・512 MiB上限で診断1回を行う確認に「続けてください」と回答した。
HEAD1af72ed（実装c6fc191）のcleanな候補worktreeでDebugDriver.runを1回だけ呼び出した。
診断の再実行、権限変更、既存fixtureの削除・修復・再利用は行っていない。

## 取得結果

| 対象 | 観測結果 |
| --- | --- |
| 親primary token | default DACL取得confirmed、ACE3件、opaque ACE0件 |
| restricted primary token | 同上、親のdefault ACL bytesと一致 |
| 実child primary token | 同上、restricted tokenのdefault ACL bytesと一致 |
| 実child process | SD取得confirmed、owner/groupあり、DACL ACE3件、label対象SACL ACE1件 |
| 初期thread | 同上 |

security state=ready。NULL/空ACLや容量不足での停止は発生していない。
SDのcontrolは両objectとも34836。要求情報は0x17（owner/group/DACL/mandatory labelのみ）。
SID、SD/ACL raw、実path・identity・addressはprivate証跡へ保持し、公開要約には出していない。
ACL一致は今回の取得bytesの比較であり、子による特定objectへのアクセス許可や起動失敗との因果を証明しない。

通常event7件、Continue確認7件。python.exe、ntdll.dll、kernel32.dll、KernelBase.dllのimage取得4件がconfirmed。
同一証跡内のmodule対応ではKernelBase.dll→kernel32.dllの順にunloadし、0xC0000142で終了した。
breakpoint/exceptionは観測されていない。DLL名や順番から原因を断定しない。
保存metadataはdriver/observer observed、primary_reason=null、resource_stop=false。
process_signaled=true、debug_ownership_resolved=true、teardown=pass、Terminate不要、drain0回。
通常・drainともwait/continue inflight=false、未確定領域bytesはzero。

## 要約表示の不具合と確認可能範囲

DebugDriver.runから戻った後、対話用の要約生成がDebugImagesの未使用None枠に.getを呼び出して失敗した。
これはcollector内の例外ではない。shell processはexit1、呼出し全体のツール測定は約2.89秒だった。
要約を表示する前に失敗したため、実行process内の正確な所要時間、memory sampler最大値、
Write/Flush/file close後のdriver最終値とbuffer hashは取得できていない。
今回の最終Write/Flush/closeを前回の成功値や保存metadataから補完しない。

実診断を繰り返さず、別の短命processで最新の専用証跡1件をread-onlyで確認した。
temp直下4096項目・専用prefix候補32件以内、更新15分以内、最大155672 bytesの条件で選択した。
全ancestorとfileのheld-handle/reparse/NTFS/identity検査、stream検査付きreaderで107403 bytesを読み、
B1DBG001形式と上記内容を確認した。reader handleはclose済み。

保存fileの読取り時SHA-256:

`80d7ce1c602ca04e0a6d7f3488126acd0104f1f0fbcd28577c10a3a7d49d0c1c`

実行時buffer hashとの照合ではない。metadataのresult_scopeは保存write/flush/file closeより前である。
従って保存前の子終了・debug所有解放は確認できるが、保存APIの最終確認値は不明のまま保持する。
reader provenance_verified=false、native_accepted=false、formal_permission=false。

## 環境と資源

同じ証跡のsourceは17件、Windows10.0.26200.9445、Python3.14.0、exe/DLL hashは既存固定値と一致。
Windows自動更新に伴うUBR緩和は承認済みのB1条件に従い、実測値を保持した。
開始前の空きRAM8.25 GiB/C102.25 GiB/D75.36 GiB、実行後RAM8.17 GiB/C102.25 GiB/D75.36 GiB。
上限によるresource stopは保存記録ではfalseだが、今回のmemory peak値は取得できていない。
PC全体の単発値でリーク有無や変化の原因は判定しない。他プロジェクトへの操作・負荷試験はない。

次は保存したACL/SDの内容を範囲を限定してoffline比較できる。追加childはこの承認で繰り返さない。
通常起動成功・原因特定・required E2E・main統合・formal実行は未達。

## 保存ACL/SDのoffline比較（2026-09-10、追加childなし）

前節と同じ上限・held-handle検査で最新証跡1件107403 bytesを読み、記録済みSHA-256との一致を確認した。
既存parserで返却保存bytesのSD/ACL境界を再検査し、ACE type/flags/mask/SIDの対応を比較した。
SIDは実process ownerと一致するものをowner、別の同一SIDを匿名Aとして扱う。
匿名Aの所属種別や有効性はこの証跡だけから決めていない。ユーザー識別子は公開しない。

| ACE対象（同じ順序） | 3 tokenのdefault ACL | process DACL | thread DACL |
| --- | --- | --- | --- |
| owner | 0x10000000 | 0x001fffff | 0x001fffff |
| SYSTEM（S-1-5-18） | 0x10000000 | 0x001fffff | 0x001fffff |
| 匿名A | 0xa0000000 | 0x00121411 | 0x00121848 |

全9 token ACEおよび全6 object DACL ACEはtype0（allow）、flags0。3 token間のACL bytesは完全一致。
process/threadのownerとgroupはともに同じowner SID。両objectのDACL bytes/SD bytesは互いに異なる。
上表は記録されたmaskの比較であり、アクセス許可のOS判定ではない。

[Generic Access Rights](https://learn.microsoft.com/en-us/windows/win32/secauthz/generic-access-rights)では
0x10000000はGENERIC_ALL、0xa0000000はGENERIC_READとGENERIC_EXECUTEの組合せであり、
generic権限はobject種別に応じて具体的な権限へ対応する。
したがってtokenのgeneric bitsと実process/threadのspecific bitsの数値差だけを、権限の欠落や破損としない。
この観測だけではWindows内部のmapping全体や適用経路を検証したことにはならない。

[Process rights](https://learn.microsoft.com/en-us/windows/win32/procthread/process-security-and-access-rights)の定義と照合すると、
匿名Aのprocess maskはREAD_CONTROL、SYNCHRONIZE、PROCESS_QUERY_INFORMATION、
PROCESS_QUERY_LIMITED_INFORMATION、PROCESS_VM_READ、PROCESS_TERMINATEの組合せ。
[Thread rights](https://learn.microsoft.com/en-us/windows/win32/procthread/thread-security-and-access-rights)と照合すると、
thread maskにはREAD_CONTROL、SYNCHRONIZE、THREAD_GET_CONTEXT、THREAD_QUERY_INFORMATION、
THREAD_QUERY_LIMITED_INFORMATIONが含まれ、さらに0x1000のbitがある。
この0x1000は参照した公開thread rights表に説明がないため、今回の解析では未解釈として保持する。
file用mappingを使ったり、processの0x1000の意味をthreadへ転用したりしない。

両objectのlabel ACEはtype17、flags0、mask0x3、SID S-1-16-8192で一致。
[Mandatory label ACE仕様](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-dtyp/25fa6565-6cb0-46ab-a30a-016b32c4939a)により
mediumラベルとNO_WRITE_UP | NO_READ_UPを表す。これは対象より低いintegrityからのアクセスに関する方針であり、
このラベルだけで今回のchildが拒否されたとは判断しない。

## この比較で残る確認点

今回得たのは記述されたACL/SDであり、実child tokenで特定操作を要求したAccessCheckや、
初期化処理が実際に失敗したアクセスの記録ではない。拒否ACEがないこともアクセス成功の保証ではない。
親/restricted/childでdefault ACLが異なるという仮説は、今回の取得範囲では支持されない。
一方、restricted SID評価やobject固有権限、他の初期化対象、WinSta/desktopの実child接続は未解決。
権限緩和やACL変更を行う根拠は得られていない。

次の低負荷工程は、同じfixtureの保存requestを別途有界read-onlyで読み、証跡のnonce/sourceと照合した上で、
匿名Aのtoken内の所属・属性とintegrityを比較すること。tokenの再作成や追加childは不要。
requestは親が準備したprofileであり、実child token全体の独立保存記録とは区別する。
診断時のmemory peak・最終保存API状態が不明という前節の制約は、この比較でも解消していない。
