# S4-B2 空ファイルの削除権限・共有条件

2026-09-14、基準d275ff0。実装savepoint **26bc403836a2b191e7e8344716c50cf49be50f47**。
[削除行列仕様](../anomaly-v03-delete-matrix-design.md)を実装・独立レビューし、新規max1枠delete-matrix-2026-09-14で1回確認した。
**子のDELETEが明示拒否でも、親のDELETE_CHILDが許可され、子handleがDELETEを共有していれば削除要求は通った。**
親をshare READで保持するだけでは、この条件の子削除を防げない。一方、子handleがDELETEを共有しない場合は共有違反で拒否された。

4ケース・保存・終了が完了し、worker exit0/0.843秒、最大1回枠は閉鎖。
283件pass/0.205秒。独立レビューの初回P2 1件を修正し、再レビューP0〜P3残件0。
同じworkerの同じprimary tokenによるpath指定DeleteFileWであり、保持parent handleの権限使用や独立process/tokenの証明ではない。
isolation/protected commit/formal permission/execution authenticated flagsはfalse、正式B2/S4受入は未完了。

## 4条件の実機結果

新規attempt直下に4つの兄弟case directoryを作り、それぞれに新規の空empty.binを1個作成した。
source-fixtureという外側rootは作らない。各親はCreateDirectory2W、access0x1600a7 exact、share READ=1、redirect拒否、非継承。
子はCREATE_NEW、access0x120081 exact（DELETE/WRITE_DACなし）、OPEN_REPARSE_POINT、非継承。
親/子の作成時DACLに必要なEveryone DENYを入れ、current user/SYSTEM/Administratorsのfull-control allowとともに保護する。
要求前に元handleからID/type/実権限/正確なSD、子の空長・allocation0・links1・DeletePending=falseを確認した。

| ケース | 親DELETE_CHILD | 子DELETE | 子share | DeleteFileW | 保持childからの後観測 |
| --- | --- | --- | --- | --- | --- |
| file-permission | 明示拒否 | 許可 | 7 | accepted | DeletePending=true、links0 |
| parent-permission | 許可 | 明示拒否 | 7 | accepted | DeletePending=true、links0 |
| sharing-block | 許可 | 明示拒否 | 3 | denied、WinError32 | DeletePending=false、links1 |
| both-denied | 明示拒否 | 明示拒否 | 7 | denied、WinError5 | DeletePending=false、links1 |

share7はREAD/WRITE/DELETE、share3はREAD/WRITE。全後観測で同handleのID/SDが初期値に一致し、空長・allocation0も維持。
開始tokenはprimary type1、非昇格、medium integrity、有効privilegeはSeChangeNotifyPrivilegeのみ。
token変更/生成/impersonation/AccessCheck、作成後のACL変更、payload書込み、rename、marker操作はない。
外部からのtoken変更や既存権限・競合を完全に監査した結果ではない。

観測は削除要求の受理、DeletePending、保持handleのclose確認まで。close後の名前消滅や外部handle不存在は検査していない。
Microsoftが説明するfile DELETEまたはparent DELETE_CHILD、DELETE共有、最後のhandle閉鎖に関する条件と対応する局所結果である。
[DeleteFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-deletefilew)、[FILE_STANDARD_INFO](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_standard_info)。

## 故障処理と検証

新規24＋既存259＝283件pass。failure/error/skip/expected failure/unexpected successは全て0。
accepted/denied、制御ケース失敗、権限・型・空長・DeletePending不一致、異常BOOL/error、要求/取得/closeの応答喪失、
descriptor解放不明、元例外と後発MemoryError、callback再入、親/祖先保持を模擬試験で確認した。
子を観測する実backendの経路も模擬し、保持handleのゼロ長確認なしに空内容のpinを作れないことを確認した。

初回独立P2は、終了時の状態判定が報告snapshotを作り、そこでのMemoryErrorにより元例外を上書きして親保持を見落とす問題。
状態判定を報告生成から分離し、その失敗では元例外とresource stopを残し、未終了親/祖先をworker終了まで保守的に保持するよう修正した。
反例に対応する4件を追加。初回279件pass後、修正後283件を再実行し、corrected-checks.jsonlを最終根拠とする。
実装/試験/入口/監視/仕様と修正箇所をread-onlyで独立レビュー、進捗ポーリングなし。
repository safety、PowerShell構文、差分空白検査pass。再レビュー後にコードを変更していない。

要求の返却が不明なら、その子/親/path入力/祖先を保持し、再読取・後続ケース・証跡書込みを止めてworker終了へ進む。
既知応答後の読取失敗は既知資源を閉じて失敗扱い。close/freeは単回、未知状態を成功や未実行へ読み替えない。

## 保存・実行条件・資源

clean detached checkoutはC:\Users\TKent\.codex\worktrees\delete-matrix-20260914\banto-ai、HEAD26bc403。
49 sourceのraw/Git blob/両checkout一致を実行前後で照合した。
launch-plan.json10786 bytes/hash71a4b962ccd51507e1ec5fcfddd3e35d6946fdfeec3ad0d95fafce139761d776。
既存Python3.14.0 x64、C:\Python314\python.exe、-I -B。追加runtimeや常駐監視はない。
40秒/外側45秒、private256MiB/working384MiB、空きRAM/disk各2GiB。新contextの資源点上限256、基底の既定64は維持。

| 観測 | 値 |
| --- | --- |
| UTC開始/終了 | 13:11:17.5783595 / 13:11:18.4303207 |
| 外側監視 | 0.843秒、worker終了確認/exit0、停止理由なし |
| 終了台帳 | case親4＋子4＋sink等12＝handle20本、query token1本closed |
| descriptor | case親/子各4と祖先SDの解放確認 |
| prepare.json | 9118 bytes/hash26c2c3ab9ad4696ea4e44886ed2510a4082bebd0b36189aa39f64abb183b7ce3 |
| stdout/stderr | 52366 / 0 bytes |
| 内部資源点 | 209点、最後0.413秒、private最大21422080/working29589504 bytes |
| OS報告working peak | 35758080 bytes。外側1秒周期前に終了し、外側memory観測0点 |

成功した既知prepareだけをbytes/hash/行列/tokenと照合して保存。caseのclose後/失敗後の列挙・open・hash/copy/deleteなし。
4件のDeleteFileWは新規caseの保持中だけ。再試行/cleanupを行わず、拒否された空ファイルもそのまま残す。
ignored artifacts/delete-matrix-2026-09-14/へ14 artifacts/論理610560 bytes（manifest自身/別checkout複製を除く）。
corrected-checks.jsonl207263 bytes/hash99f81e6d596e1c4773740344953604435ba9aa952e5e52a3b9b49d66fcefb795。
savepoint-evidence.json28705 bytes/hash5e4755ba021b5221d12cd1cb1da5e3d2d1e7eba32262fe7da587ce35d525df5a。
前回peer manifest/12 artifacts不変、前回44 source中43不変。既存sourceの変更はacquisition backendの方針/内容pin/状態判定hookだけ。

UTC12:56:23の空きRAM16.44GiB/C117.52GiB/D53.16GiB、13:11:51はRAM15.54GiB/C117.51GiB/D53.16GiB。
PC全体の空き変動の原因は未特定。点観測から長期リーク不在や全期間最大を主張しない。他processへの操作なし。
build26200.9445、boot2026-09-09T10:43:08.5000000+09:00。Windows Updateのengineering緩和を適用し、正式pinは変更しない。
worker/監視は終了済み。新規detached checkout1個とfixtureを保存して残す。
既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621は保持しcommitから除外。
本流889cfc3 clean不変、旧batch/旧source/S3/D2/production、push/merge/CI、別project、新account/serviceへ操作なし。

## 次の境界

子のDELETE共有拒否が効いたのは、その子handleを保持していた期間だけ。全子・公開前後・consumer観測期間の保護へ一般化しない。
次は既存のsealed-file保持と公開順序modelにこの寿命条件を接続し、close/移管の間隙、親側権限、全consumerの共通観測期間を整理する。
親/子のACLと共有だけで全期間を閉じられない場合は、専用principal等の運用変更を具体的な判断材料にする。現時点で追加accountは作らない。
保持parentを直接使うAPI、独立process/token、競合、外側parentの事前権限、marker/全publisher、正式OS/VM digest・B2/S4受入は未完了。
今回のcaseと最大1回枠は再利用しない。
