# S4-B1 process/thread権限の読取り観測案（2026-09-10）

状態: **collector実装・試験・独立レビュー完了 / read-only preflight verified / 追加実機診断未承認・未実行**。

実装c6fc191、pure/fake231/231、独立レビュー新規P0〜P3=0。詳細は引継書§39。

保存記録を実行時hashと照合し、python.exe→ntdll.dll→kernel32.dll→KernelBase.dllの観測、
KernelBase.dll→kernel32.dllのunload、例外なしの0xC0000142終了を確認した。
この順序だけでは原因を特定できないため、同じ情報だけを取る再実行は提案しない。

## 観測追加前に確認したコード上の不足

- SuspendedDebugLaunchはCreateProcessAsUserWのprocess/thread SECURITY_ATTRIBUTESへ両方Noneを渡す。
- _Win.profileはuser/groups/privileges/restricted等を取得するが、TokenDefaultDaclを取得していない。
- DebugSession._validate_childの_access_matrixはcontrol/frozenの5つのfile/directoryを対象とし、
  子process・初期thread自身のsecurity descriptorを取得していない。
- 親が保持する作成時handleで検証・停止できたことは、子のsecurity contextによる別のアクセスが
  許可されたという証拠ではない。今回の初期化でそのアクセスが必要だったかも未確認。

従ってprocess/threadの既定ACLとrestricted tokenによるアクセスは未測定の仮説候補である。
default DACLが原因、または特定ACEが不足すると断定しない。DLL名だけを根拠にACLを変更しない。

## 仕様の根拠と区別

[CreateProcessAsUserW](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessasuserw)の
lpProcessAttributes/lpThreadAttributes説明では、NULLの場合にhTokenで参照されるuserのdefault security descriptorを使う。
一般的なprocess作成の説明だけから、このAPIでどのtoken由来かを決めない。実objectのSDも別に取得する。

[TOKEN_DEFAULT_DACL](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-token_default_dacl)は
既定SDの作成に使うACLを保持する構造である。
[GetTokenInformation](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-gettokeninformation)は
TokenDefaultDaclでdefault ACLがない場合、構造内pointerがNULLになると定義する。
NULL、空ACL、非空ACL、照会失敗を同じ状態にしない。

この候補のCreateRestrictedToken flagsは9（DISABLE_MAX_PRIVILEGE | WRITE_RESTRICTED）。
[CreateRestrictedToken](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-createrestrictedtoken)の
WRITE_RESTRICTED説明はrestricting SIDをwrite access評価時に考慮するとする。
一般的なrestricted tokenの二重アクセス検査の説明だけで、全read/executeが拒否されるとは推論しない。

## 実装した観測範囲

変更を加える前の読取り観測として、次の5対象に絞る。

| 対象 | 保持したい情報 | タイミング |
| --- | --- | --- |
| 親primary token | TokenDefaultDacl | 既存の親token ownerが保持中、child作成前 |
| restricted primary token | TokenDefaultDacl | 作成済みrestricted token保持中、child作成前 |
| 実child primary token | TokenDefaultDacl | 実child検証中、Resume前 |
| 実child process | 実objectのSD（owner/group/DACLと取得可能なlabel） | 作成時handle保持中、Resume前 |
| 初期thread | 実objectのSD（同上） | 作成時handle保持中、Resume前 |

既存ownerからhandleを借りる。新しいprocess/threadを開かず、collector側でcloseしない。
各対象1 KiBのバッファと状態枠をchild作成前に確保し、固定容量へ1回取得する。
容量不足や不確実なAPI結果では停止し、可変サイズの再試行や失敗後の再取得に進まない。
token内pointerを解釈する場合は、所有している返却buffer内の範囲を検査してから扱う。
SD/ACLの整合性検査でもNULL・未知ACE・label取得不能を欠落や許可へ変換しない。

securityの5対象最大rawを含むJSONは16 KiB未満となることを試験済み。
全体のprivate JSON64KiBと既存images24KiB上限を維持し、resource時は保存を抑止する。
過去の記録は変更せず、collectorをsource allowlistへ追加した（合計17件）。

既存_Win.securityはSE_FILE_OBJECTとprotected DACLを前提とし、通常のkernel object観測にはそのまま使えない。
_Win.accessのgeneric mappingもfile用である。process/thread用に誤用した結果を権限の証拠にしない。
この段階はdescriptor取得までを対象とし、AccessCheckを追加するならobject種別・specific rights・
generic mappingを別に検証する。Python側でACEを足し合わせてOSの判定の代用にしない。

## 実行へ進む前の条件

collectorの実装、pointer/buffer境界・API失敗・OOM・保存容量のfault試験、既存停止への接続、独立レビューは完了。
実read-only preflightも17 sources / 199,864 bytesでverified。追加childは未起動。
token/SD/ACL/desktopの変更、権限緩和、通常Popenへのfallback、loader snapsはこの案の対象外。
read-onlyで取得できても、それだけで起動障害との因果関係やnative受入を成立させない。

## APIと停止・保存の具体条件

TokenDefaultDaclはGetTokenInformationのclass6で取得する。
[GetKernelObjectSecurity](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-getkernelobjectsecurity)は
self-relative SDを返す。要求0x17はOWNER/GROUP/DACL/LABELであり、audit SACLは含まない。
[LABEL_SECURITY_INFORMATION](https://learn.microsoft.com/en-us/windows/win32/secauthz/security-information)の読取りはREAD_CONTROLを使用する。
NULL ACLと空ACLを分離し、返却範囲・SID長・ACL/ACE長・alignmentを検査する。
未知ACEはopaqueとして保存し、file用protected DACL検査・generic mappingは使わない。
親照会失敗ではchildを作成せず、fixture作成前なら保存fileは存在しない。
子照会失敗ではResumeせず、既存の所有process停止・解放へ進む。resource停止時は証跡書込みを抑止する。

## 次回の判断対象：追加実機診断1回

- 新規の専用fixtureでrestricted childを1回だけ起動し、上記5対象と既存image/eventを観測する。
- 観測30秒以内、最大256 events、親＋child peak commit512 MiB未満を維持する。
- 全breakpointで停止し、停止後drainは最大32回/5秒。照会の再試行や診断の自動再実行はしない。
- token/ACL/desktop/権限は変更しない。既存証跡を削除・再利用しない。
- OS更新は承認済みB1条件に従って実測UBRを記録し、他のruntime/source pinを照合する。
- 結果は記録しても起動成功・原因確定・native受入とは扱わない。失敗なら状態を保存して再判断する。

この1回については実施前に判断を求める。準備完了だけを実行承認として扱わない。
