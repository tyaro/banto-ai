# S4-B1 bcryptデバイス経路の限定診断結果

状態: **診断1回完了 / open helperの負値を確認 / child E2E未達**。

ユーザーの「お願いします」を[実行計画](anomaly-multiseed-v0.3-s4-b1-bcrypt-device-plan-2026-09-10.md)の1回への了承として、
cleanなbe05b42（実装d557a20）で2026-09-10に実行した。再試行なし。
DebugDriver(bcrypt_device=True, detached_console=True, bootstrap=True)。
初期reportまで2.654秒、primary=bcrypt_device_observed_stop、secondaryなし、resource_stop=false。
driver/observerのfailedは意図した観測停止であり、起動成功を意味しない。

## 確認できたこと

検証済みbootstrap slot17を継続後、slot18で最初のhardware exceptionを取得した。
bcrypt LOAD slot16と初期process/thread、RIP、DR、固定frame/caller、参照3窓を照合した。

| 項目 | 実測 |
| --- | --- |
| recipe | bcrypt-26200.9445-device-v1 |
| hit | DR0 / bcrypt RVA8129 |
| candidate / domain | open_helper_8154 / open_helper_negative |
| 保存されたhelper戻り値 | R12D=C0000022 |
| caller | RVA5d53、RSP+b8の8 bytes |
| frame | RSI=RSP+60、RDI/R14=0、R15=8、RSP16-byte整列 |
| context / Set | completed、confirmed / verified |
| DR6 | 0 → 0 → ffff0ff1 |
| DR7 | 0 → 15 → 415 |

数値はhex。8129はhelper8154から保存したR12DをEAXへ移す直前である。
間にLeaveCriticalSectionがあるため、その時点のEAXをhelperの戻り値と同一視しない。

照合済み参照コードではhelper8154が固定名 \Device\KsecDD に対しNtOpenFileを呼ぶ。
呼出後に別のstatus-producing callはなく、戻りEAXが呼出元のR12Dに保存される。
静的要求値はDesiredAccess100003、ShareAccess7、OpenOptions20。
この参照と今回のR12D負値は、**KsecDDを開くhelperがアクセス拒否を返した経路**を支持する。
NtOpenFileは既存デバイス等を開き、NTSTATUSを返す。
[Microsoft NtOpenFile仕様](https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntopenfile)。
C0000022はSTATUS_ACCESS_DENIEDに対応する。
[Microsoft NTSTATUS表](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-erref/596a1078-e883-4972-9bbc-49e60bebca55)。

過去のCALLそのもの、実行時IATの宛先、実行時OBJECT_ATTRIBUTESの内容を直接取得したものではない。
NtDeviceIoControlFile失敗、応答値、イベント作成失敗は今回未観測。
デバイスDACL、拒否された個別access bit、driver固有の拒否判定はこのchild診断だけでは未特定。
§42のtoken default DACLにRCの直接ACEがないことを原因と断定しない。

## 取得上限・終了処理・証跡

通常19 events / Continue18。collector Get3/Set1/RPM4回1766 bytes、
bootstrap込みGet4/Set1/RPM7回1841 bytes。DR3はzero/disabled。
参照窓は59e0/1068、7f50/660、固定名1f098/30 bytes。最後の窓は文字列である。

hitの通常Continueなし。所有processへのterminate要求、pending解放、drain4
（thread3/process1、全exit1）とContinue、signal、debug ownership解消、owned process/thread handle closeを確認。
teardown pass / failure_count0 / driver teardown failures0。
自然EXITは未観測で、exit1は意図した終了処理による値。fixture存在はunverified、cleanup/repairなし。

private evidenceは117759 bytes、
SHA-256 f04e02ae4ccab8a2f0f512d612f954d11e9380be9b097d4d6ffae4fdfac31d35。
write/flush/file close確認済み。有界held-file readbackを1回だけ実行し、全normal/drain events、
bootstrap、raw debug CONTEXT、R12D、frame/caller、LOAD、launch、stop、hashを照合した。
全inflight false、未確定buffer領域zero、reader close。生SID/SDDL/handle/絶対temp pathは公開要約に含めない。

作業用の公開要約はartifacts/context-offline-2026-09-10/配下の
bcrypt-device-native-summary.jsonl、bcrypt-device-native-readback.jsonに保存した。
実行wrapper bcrypt-device-once.pyは2760 bytes、
SHA-256 6ef9ba31f8ddebdf112453375f365f5cdee0f8b9f4db845bdc928b3469aee0a0を実行直前に照合した。

## 環境・資源・範囲

同run preflightはverified、27 sources/277511 bytes、Windows10.0.26200.9445/Python3.14.0、
既存exe/dll hash一致。requested creation flags40e、creationcreated、ownership transferred。
事前のpure/fake272/272と独立レビュー（P2是正済み、新規P0〜P3=0）のコードを変更せず実行した。
同じコードの全体fakeを本結果のためだけに再実行していない。

親＋child memory171 samples、peak commit26034176 bytes（24.83 MiB）、
peak working36872192 bytes（35.16 MiB）。
作業前08:03:33Z→08:09:28Zの空きRAM8.32→7.99 GiB、C108.00→107.99 GiB、D75.36 GiB。
last bootは2026-09-09 10:43:08 +09:00。
Windows UpdateのUBR固定緩和を維持して実測状態を記録する。単発値からメモリリークの有無を判定しない。
別projectのprocess、サービス、テスト、ファイルを操作していない。

今回のchild診断1回への了承は消化済み。token/DACL/ACL/core変更なし。
追加DLL/PDB読込み・downloadなし。全acceptance gate no。
本流889cfc3 clean、本流統合/formal/B2/publisher未実施。

## 次の判断のための読み取り

失敗地点をさらに細分化するchild breakpoint追加に先立ち、固定KsecDDの権限メタデータを親contextから確認する。
ユーザーの継続指示に基づく読み取り専用作業であり、child診断の再実行ではない。
READ_CONTROL|SYNCHRONIZEで固定名を1回open、owner/group/DACLを固定4096 bytesで1回queryしcloseする。
token作成・変更、impersonation、ACL変更、IOCTL、data read/write、handle継承、retryなし。
これは一般の権限情報確認であり、restricted childを親権限で動かす代替経路ではない。
返されたSDを匿名化して保存し、AccessCheckやdriver固有の許可判定が未実施であることを明示する。
[GetKernelObjectSecurityの必要権限と返却形式](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-getkernelobjectsecurity)。

制限を弱める修正はこの結果から自動採用しない。権限の構成変更が必要なら、影響を具体化してユーザーへ提示する。

## KsecDDの読み取り専用メタデータ確認

2026-09-10T08:15:48Z、独立レビューのP2 2件を修正して是正確認後、固定scriptを1回実行した。
NtOpenFile(open status0)→GetKernelObjectSecurity→CloseHandleは各1回、全confirmed、elapsed0.002秒。
READ_CONTROL|SYNCHRONIZE（120000）、share7/options20、owner/group/DACL（information7）、容量4096 bytes。
返却188 bytes、parse confirmed、resource_stop=false。追加child/token/ACL変更/IOCTLなし。
SACLは要求しておらず、返却SDのSACL absentを対象のSACL不存在とは読み替えない。

返却DACLは6 ACE、すべてallow/flags0、opaque ACEなし。匿名化した観測値は次のとおり。

| trustee | allow mask（hex） |
| --- | --- |
| Everyone | 1201bf |
| LocalSystem | 1f01ff |
| Administrators | 1f01ff |
| RestrictedCode（RC） | 1200a9 |
| 未分類1 | 1201bf |
| 未分類2 | 1201bf |

ownerはAdministrators、groupはLocalSystem。未分類SIDを推測で命名しない。
SD hash80855ee5cacdab07dcb48643d08ae3898dd45bef77695ab67057a08395cd8521。
生SD/SIDは公開・privateとも新たに保存していない。保存した匿名化summaryのみを既知pathから1回有界readし、
呼出数・完了・資源状態・ACE数とmaskを照合した。これはchild private evidenceの再readではない。
ksecdd-security-readonly.jsonは1576 bytes、
SHA-256 c3227d3fdefc1adaec0c50b7211fc2444ecc7da51c705902ceff087b4b383aeb。
実行scriptは7993 bytes、
SHA-256 4eff849764ccb4165b4ac5bea749b2e6d263164dd3b37c3830b2532d681921bf。
構文/AST確認、独立P2 2点是正済み・新規P0〜P3=0。進捗ポーリングなし。
確認済み取得だけをcloseし、不確実出力の推測closeと資源停止後のJSON/追加保存を抑止した。

静的要求100003とRC allow1200a9の差分はmask0x2である。
mask0x2はfile objectのFILE_WRITE_DATAに対応する。
[Microsoft access rights](https://learn.microsoft.com/en-us/windows/win32/fileio/file-access-rights-constants)。
既存token recipeはflags9で、restricting SIDはRCのみ。
WRITE_RESTRICTEDはwrite accessでrestricting SIDを考慮する。
[Microsoft CreateRestrictedToken](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-createrestrictedtoken)。

**推論:** 今回のDACLではRCへのallowが初期化要求のwrite bitを満たさず、childのopen helper負値と整合する。
RC ACEが「存在しない」のではなく、存在するが当該write bitを含まない。
これは単純なmask照合で、実AccessCheckの結果ではない。
別時点に親contextで開いたhandleへのmetadataであり、childが試みた実行時対象identityやdriver固有判定の認証、
起動障害の唯一の原因の証明ではない。新しいtokenや起動回避策は試していない。

次は[権限構成の判断資料](anomaly-multiseed-v0.3-s4-b1-token-compatibility-decision-2026-09-10.md)を参照。

結果追記・判断資料の独立レビューも新規P0〜P3=0。repository safety/diff-check pass。
最終08:20:29Zの空きRAM8.69 GiB、C108.47/D75.36 GiB。本流889cfc3 clean。
runtime/core/test sourceを変更していないためfake全体や保存後preflightを再実行しない。
