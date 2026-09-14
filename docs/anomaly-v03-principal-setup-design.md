# S4-B2 専用principal環境の準備

2026-09-15 engineering限定。[権限境界案](anomaly-v03-principal-boundary-design.md)へのユーザー「はい、それで続けて下さい」により、専用標準local accountと新規保護rootの準備を承認済み。歴史上の未承認記録は変更しない。
対象はBantoS4PublisherとC:\ProgramData\BantoAI-S4B2-principal-20260915だけ。今回はPをログオンさせず、無効accountと読取専用の環境rootを用意する。既存account/rootを再利用・変更しない。

## 実装と起動

[C# helper](../tests/fixtures/PrincipalSetup.cs)、[故障試験](../tests/PrincipalSetupTests.cs)、[起動処理](../tools/windows_principal_setup.ps1)を使用する。
既存.NET Framework64 compilerで通常権限のままDLL/testをcompileする。出力はignored artifacts/principal-setup-2026-09-15へbuild番号別に保存し、上書きしない。
Build/Verify/CheckLoaderはOS設定を変更しない。CheckLoaderは通常権限で同じloaderの展開/hash/Assembly.Loadまでを実行し、account/rootのentryを呼ばない。自分で起動した検査processだけを10秒で終了監視する。

Runはhashを外から固定して通常側のFileStreamを保持し、長さ1〜262144 bytesを割当て前に検査、exact readと終端を確認する。同じbytesをhash確認して圧縮する。
管理者側へ渡す引数は公開code bytesの圧縮表現とhashだけで、secretを含まない。ASCII commandのloader本体29000文字以下、Start-Process -Verb RunAs -WindowStyle Hidden、System32 working directory、WindowsPowerShell -NoProfile -NonInteractiveを使う。
B側はU書換え可能なDLL/pathを読まず、引数から最大262145 bytesへ有界展開し、上限超過を拒否。SHA256を確認した同じbyte配列をAssembly.Loadする。管理者側でのcompile、user TEMPへの出力、module importはしない。
P/InvokeはSystem32検索を指定する。起動する既存Windows/.NET環境自体の信頼を新たに証明するものではなく、execution_authenticated=falseを維持する。

launch-attempt.jsonを通常側でCREATE_NEW/flushしてからUACへ一度だけ進む。同じ記録があれば再起動しない。UAC承認は既存許可をWindowsで適用する操作であり、方式の追加承認ではない。取消/起動不明/timeoutを記録して反復しない。

## 作成順序と権限

1. Win64・管理者tokenを確認。Bのlinked tokenが固定U SID S-1-5-21-2169670816-255940906-2713565042-1001で非昇格であることを確認し、AccessCheck用impersonation tokenを取得する。別管理者資格情報によるUACでこの条件が揃わなければOS変更前に停止する。
2. C:\とC:\ProgramDataをaccess0x120080/share3（DELETE shareなし）、OPEN_REPARSE_POINT/BACKUP_SEMANTICS・非継承で保持。directory/no-reparse、volume/file ID、owner/group/DACL/labelを記録し、各作成・設定phaseの前に元handleで照合する。
3. linked U tokenのAccessCheck/MAXIMUM_ALLOWEDで各祖先のDELETE/DELETE_CHILD/WRITE_DAC/WRITE_OWNER（0xd0040）がないことを確認する。これは限定した祖先権限のpreflightであり、P/U process/tokenや全namespaceの隔離試験ではない。
4. NetUserGetInfoのuser-not-foundとrootのfile-not-foundを確認。アクセス拒否やその他の不明状態を未存在と解釈しない。
5. CreateDirectory2Wをaccess0x1600a7/share1/redirect-disallow1、明示SD/noninherit SAで一度呼ぶ。root owner/groupはBA、SY/BA full、固定Uは0x1200a9 read/traverse、protected DACLとprotected medium/no-write-up label。継承ACEなし。ID/no-reparse/実SDを元handleで確認してからaccount作成へ進む。
6. NetUserAdd level1をprivilege USER_PRIV_USER、flags UF_SCRIPT|UF_ACCOUNTDISABLE|UF_NORMAL_ACCOUNT=0x203で一度呼ぶ。**最初から無効**にする。password policyの緩和や別APIへのfallbackをしない。
7. level23の実名/flags/SIDを確認し、SIDをbuffer解放前に保持。固定Uと別のaccount SIDであることを確認する。Usersのwell-known SID S-1-5-32-545からローカライズされたalias名を解決し、level0/SIDで所属を追加する。既所属1378も最終検査を省略しない。
8. NetUserGetLocalGroups level0/LG_INCLUDE_INDIRECTで全応答成功、read/total各1、Usersだけであることを確認する。不明・追加group・部分応答では停止し、group自動削除はしない。Users-onlyが直接付与されたuser rightsや将来tokenの低権限性を証明するとはしない。
9. 元root handleのDACLへP SIDのread/traverseだけを加える。BA owner・SY/BA full・U/P readonly・protected medium labelをexact SDDLで再確認し、account SID/disabled状態とgroupも再確認する。Pにはこの準備rootへの作成権限をまだ与えない。

root/receiptのpolicyは O:BAG:BAD:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;0x1200a9;;;U)(A;;0x1200a9;;;P)S:P(ML;;NW;;;ME)。初期rootではP ACEだけを省く。U/P表記は実SIDへ展開する。
ルートの完全なnamespace不変性やPの起動経路を今回の準備成功から認定しない。protected code/runtime/worker用slot、process/thread/token SD、IPCとP/U同時試験は残件。

## 資格情報、失敗と寿命

passwordはB内でBCryptGenRandom/system-preferred RNGからunmanaged32 bytesを生成し、固定complexity prefixと64hex文字＋NULをunmanaged UTF16 bufferへ直接書く。managed secret配列/string、引数、ログ、artifactへ変換しない。
NetUserAddのpassword fieldはIntPtr。通常返却時はrandom/password領域をzeroして解放する。OS/NetAPI内部、paging、強制終了時の残存コピーまで消去できるという主張はしない。
生成passwordを保存せず使わない。将来の有界起動ではB側で別secretへresetする仕様が必要。無効accountを自動で有効化しない。

各phaseで最初の失敗を保持し、次のphase・retry・補償操作を呼ばない。account/root作成の失敗や応答不明ではraw handle/descriptorをB process終了まで保持し、失敗名を再open/列挙/hash/copy/deleteしない。
LocalFree/NetApiBufferFreeの戻りを検査する。operationが失敗し解放も失敗した場合は元例外/codeを保持し、事前確保stateへ解放失敗を記録する。Exception.DataやExceptionDispatchInfoの追加割当てに依存しない。成功した内側処理の後の解放失敗も後続account/ACL操作を停止させる。
終了codeはphase<<16|detail（Win32/NetAPIの1〜65534、それ以外65535）、解放失敗はbit30。nested解放も最初のcodeを維持する。80はwatchdog、81/82/83はloaderの上限/hash/例外。最初の失敗を変更する自動再試行はない。

成功途中の記録bootstrap-result.jsonは新root内でCREATE_NEW、64KiB以下、明示SD/noninheritで書込み・flushする。**prepared-preclose**と明記し、SID/disabled/group/元root ID・SD/resourceを記す。receipt自身のclose、root、ProgramData、volume、token3個の順で一度だけcloseする。
close失敗では以後のancestorを先に閉じずB終了まで保持する。exit0は後続close/watchdog停止まで完了した意味で、preclose receipt単体を全終了証拠にしない。
helper結果が成功しprocess終了を確認した場合だけ、永続環境rootの既知receiptとaccountを通常側で読取確認できる。環境rootを旧native test source/閉鎖枠の再訪許可に転用しない。失敗時にrootの列挙や結果fileの探索をしない。

## 資源と後続作業

B helperの内側上限40秒、観測private256MiB/working384MiB、空きRAM/C disk各2GiB。500msの自己watchdogがblocking API中にも自processを終了できるよう、通常U observerのkill権限に依存しない。
通常側はStart-Processが返った後45秒以内の終了を待つ。UAC待ち/PowerShell初期化/loaderは内側helper時間に含まれず、別の起動経過として記録する。OS停止/スケジューリング停止で厳密な壁時計保証を主張しない。
通常側の準備出力、compile/test各buildとsource/hash/resourceを保存する。root/OS SAMの物理容量やPC全体の変動をartifact論理bytesに含めたとしない。他project/processを走査・停止しない。
Windows Updateはbuild/bootを記録してengineering緩和を継続。正式OS pin/VM digestは変更しない。既存Python3.14.0を維持し、Python3.12、新runtime、service/task/VM/profileを追加しない。
この工程はpublisher/logon/独立P-U干渉/namespace一貫性/全期間/全publisher/正式B2/S4受入を実行・完了させない。account/root自動削除なし。全許可flags=false、acceptance_status=not_completed。

## 一次資料

[NetUserAdd](https://learn.microsoft.com/en-us/windows/win32/api/lmaccess/nf-lmaccess-netuseradd)、[USER_INFO_1](https://learn.microsoft.com/en-us/windows/win32/api/lmaccess/ns-lmaccess-user_info_1)、[USER_INFO_23](https://learn.microsoft.com/en-us/windows/win32/api/lmaccess/ns-lmaccess-user_info_23)、[NetLocalGroupAddMembers](https://learn.microsoft.com/en-us/windows/win32/api/lmaccess/nf-lmaccess-netlocalgroupaddmembers)、[NetUserGetLocalGroups](https://learn.microsoft.com/en-us/windows/win32/api/lmaccess/nf-lmaccess-netusergetlocalgroups)、[BCryptGenRandom](https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/nf-bcrypt-bcryptgenrandom)、[CreateDirectory2W](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createdirectory2w)、[System32 DLL search](https://learn.microsoft.com/en-us/dotnet/api/system.runtime.interopservices.defaultdllimportsearchpathsattribute?view=netframework-4.8.1)。
