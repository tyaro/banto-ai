# S4-B1 実行環境のCPU構成をWindows APIで確認する修正

状態: **修正・pure/fake289件・独立レビュー・保存後preflight完了。修正済みcontrol1回への返答待ち、修正後のchildは未実行**。
直前の診断1回はchild_call/runtime_pinで停止した。個別の不一致項目は未観測。
今回の修正が実機の唯一原因を解消したとは、追加実測前には主張しない。

固定CPython3.14.0のplatform.machine()は、WindowsでWMIを使い、失敗するとPROCESSOR_*環境変数を参照する。
固定childはSystemRoot/TEMP/TMPだけを受け取るため、WMIも失敗するとCPU名が空になる。
実WMIを呼ばず、固定stdlibの_get_machine_win32にOSErrorと空の環境を注入して空値を再現した。
実child内のWMI失敗を直接観測したという意味ではない。
[CPython3.14.0 platform.py](https://github.com/python/cpython/blob/v3.14.0/Lib/platform.py#L789)。

## 修正と維持する条件

platform.machine()をIsWow64Process2(GetCurrentProcess(), USHORT*, USHORT*)に置き換える。
BOOL成功時だけ出力を使い、process machine0かつnative machine0x8664（native AMD64）だけを受理する。
API欠落・失敗・他architectureは拒否する。環境変数からの代用やWMIへのfallbackはない。
借用pseudo handleのみを使用し、新規process handle取得・CloseHandleはしない。
ABIとUNKNOWN/native machineの意味は[Microsoft仕様](https://learn.microsoft.com/en-us/windows/win32/api/wow64apiset/nf-wow64apiset-iswow64process2)に基づく。

OS版/UBR/edition条件、Python3.14.0・pointer64bit・compiler・git metadata・非free-threaded・exe/DLL hashを維持。
OS条件はruntime_pin、architecture不一致はruntime_architecture、Python metadataはruntime_python_metadataで分離する。
API欠落/失敗の2理由も含め、終了コード表の末尾へ4理由を追加。既存202 IDは変更しない。
子の環境、token recipe、保護DACL、起動条件、全必須操作は変更しない。

## 検証と次の1回

選抜82/82（0.470秒）pass後、実測exit278331392の旧理由ID維持回帰を1件追加。
全pure/fake289/289（9.282秒）pass。APIのBOOL/HANDLE/USHORT*、成功・失敗出力、API欠落、
pseudo handle非解放、CPU環境欠落、CPU環境偽装下のARM64/WOW64等拒否、metadata/hash維持を確認。
独立差分レビュー新規P0〜P3=0。担当のnative/query/再試験/編集なし、進捗ポーリングなし。
repository safety/diff-check pass。

source保存後read-only preflightを完了した候補で、runtime-machine-control-once.pyによる新規fixture1個のcontrol1回を行う。
親側で新APIの照合、実child token/AccessCheck、resume後のchild検証と全必須操作、report照合、cleanup/teardownまで必要。
失敗時は固定診断を保存し、自動再試行しない。既存失敗fixtureには再open/清掃/ACL修復/再利用しない。
RC＋Everyone、flags9、非昇格・同一user/session/integrity、privilege削減、protected DACL、source/runtime pinを維持。
30秒/親＋子512 MiB未満/temp空き1 GiB以上、資源停止後の追加hash/save/scan禁止を維持。
別projectへの操作や追加SID・既存ACL変更は含まない。成功時も受入/認証/formalの各flagはfalse。

直前に了承されたchild-diagnostic1回は実施済み。handoff §6の「追加probeは承認なしに繰り返さない」に従い、
修正済み候補の次のcontrol1回への返答を待つ。「お願いします」「続けてください」はこの1回への了承として扱い、再確認しない。

未実行runtime-machine-control-once.pyは3982 bytes、SHA4292c3aefc011adfc7a204b76304ba3648e523c72eca2531babe11ec1413d9e9。
前wrapperから新規summary出力先だけを変更。AST上harness呼出1箇所、追加のnative実行なし。


修正コードを6094466へ保存。保存後preflight2.822秒、27 sources/285764 bytes、verified。
resource_stopfalse、primary/secondaryなし、Windows10.0.26200.9445/Python3.14.0、既存exe/DLL hash一致。
保存sourceの分岐順から、親側のIsWow64Process2によるnative AMD64照合も通過したと判断できる。
修正後のrestricted childで成功した証拠ではない。runtime-machine-preflight.jsonへ保存。
最終09:17:16Zの空きRAM8.06 GiB、C108.38/D75.36 GiB、last bootは同じ。
点の資源量からリーク有無を断定せず、別projectや既存失敗fixtureへの操作なしを維持。
本流889cfc3 clean。今回追記は文書のみであり、source preflight・fake試験を再実行しない。
