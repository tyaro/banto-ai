# S4-B1 process/thread権限の読取り観測案（2026-09-10）

状態: **設計案 / collector未実装 / 追加実機診断未承認・未実行**。

保存記録を実行時hashと照合し、python.exe→ntdll.dll→kernel32.dll→KernelBase.dllの観測、
KernelBase.dll→kernel32.dllのunload、例外なしの0xC0000142終了を確認した。
この順序だけでは原因を特定できないため、同じ情報だけを取る再実行は提案しない。

## 確認したコード上の不足

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

## 次に準備する範囲

変更を加える前の読取り観測として、次の5対象に絞る。

| 対象 | 保持したい情報 | タイミング |
| --- | --- | --- |
| 親primary token | TokenDefaultDacl | 既存の親token ownerが保持中、child作成前 |
| restricted primary token | TokenDefaultDacl | 作成済みrestricted token保持中、child作成前 |
| 実child primary token | TokenDefaultDacl | 実child検証中、Resume前 |
| 実child process | 実objectのSD（owner/group/DACLと取得可能なlabel） | 作成時handle保持中、Resume前 |
| 初期thread | 実objectのSD（同上） | 作成時handle保持中、Resume前 |

既存ownerからhandleを借りる。新しいprocess/threadを開かず、collector側でcloseしない。
バッファと状態枠をchild作成前に確保し、固定容量へ1回取得する設計を優先する。
容量不足や不確実なAPI結果では停止し、可変サイズの再試行や失敗後の再取得に進まない。
token内pointerを解釈する場合は、所有している返却buffer内の範囲を検査してから扱う。
SD/ACLの整合性検査でもNULL・未知ACE・label取得不能を欠落や許可へ変換しない。

全体のprivate JSON64KiBと既存images24KiB上限に収まる保存枠を設計する。
raw SDの無制限hex化は避け、上限・partial保持・resource時の保存抑止をfault試験する。
当時の記録や実行条件は変更せず、新しいcollectorを接続した場合だけsource allowlistへ追加する。

既存_Win.securityはSE_FILE_OBJECTとprotected DACLを前提とし、通常のkernel object観測にはそのまま使えない。
_Win.accessのgeneric mappingもfile用である。process/thread用に誤用した結果を権限の証拠にしない。
この段階はdescriptor取得までを対象とし、AccessCheckを追加するならobject種別・specific rights・
generic mappingを別に検証する。Python側でACEを足し合わせてOSの判定の代用にしない。

## 実行へ進む前の条件

collectorの実装、pointer/buffer境界・API失敗・OOM・保存容量のfault試験、既存停止への接続、独立レビューが必要。
完成後に追加実機診断1回の具体的な条件を提示する。今回の継続指示で追加childを起動したことにはしない。
token/SD/ACL/desktopの変更、権限緩和、通常Popenへのfallback、loader snapsはこの案の対象外。
read-onlyで取得できても、それだけで起動障害との因果関係やnative受入を成立させない。
