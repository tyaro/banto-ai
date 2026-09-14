# S4-B2 held-handle rename adapterの具体設計

日付2026-09-11、基準be61da8。tests/fixturesの注入backend用prototype。
実Win32 backend/fixture所有権/DACL/token/正式入口へは接続しない。

## 今回固定する接続面

前段の6状態modelのうち、rename_payloadとcommit_markerだけを実行するsingle-use adapter。
同じ親のstage→payload、marker-pending.json→.completeの2通りに限定する。
本体と完了印はともに保持したsource handleを使い、上書きなしのrename要求を構成する。
完了印はpending fileのrenameで確定する案で、既存S3のhardlink marker契約を変更するものではない。
実機接続前の案であり、pending名消失後の失敗証跡は別のprivate snapshotへ保持する設計が必要。

source/parentのObjectPinは正の64-bit handle、volume ID、16-byte file ID、種別、
markerの場合は期待するcontent hashを持つ。handle値の型検査は実handleの有効性や所有権の証明ではない。
同volume・別identity・別handle・正しい種別を要求し、既存journalのmarker digestとも一致を要求する。
1個のadapterは1回限り。別journalを渡しても同じadapterを再使用できない。

backendはparentとsourceのnative handle/名前/identity/親子関係をfresh recheckし、
markerは全bytesとhash、link/reparse/stream/SDの固定条件も確認する責務を持つ。
この確認を担うnative backend自体は未実装。成功応答を信用できるtrusted adapter内部の契約である。
実装済みの模擬backendはメモリ内の独立した名前表とobject/handle表で検証する。
journal.beginが先に通らなければbackendを呼ばない。失敗後は再検査/cleanup/再試行をしない。
各再検査が戻った直後にもjournalのpendingを確認する。backendが停止や再入エラーを
握り潰して正常returnしても、次の再検査やrenameを呼ばない。
借用したhandleをadapterで閉じず、所有側のteardownに戻す。

## Windows APIの根拠とABI

[SetFileInformationByHandle](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-setfileinformationbyhandle)の
FileRenameInfo（class 3）と非zero成功/zero失敗を対象にする。zero直後にGetLastErrorを取得し、
エラー未取得や不正return値も成功にしない。実装ではbackendがWin32 BOOLをsigned intとして返す契約。

[FILE_RENAME_INFO](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_rename_info)の
ReplaceIfExists=false、RootDirectory=保持親handle、FileNameLength=UTF-16LEのbytes長を使う案。
宛先は固定leafだけで、絶対path・CWD・任意pathの入力を持たない。replace/POSIX/ignore系flagは0。
Win64のoffset 0/8/16/20、名前後の任意NULを含む小さなbufferを構成する。
公式ページの表示にはunionと旧BOOLEANが同時に並ぶが、導入済みSDK
C:/Program Files (x86)/Windows Kits/10/Include/10.0.26100.0/um/WinBase.h:9112
では条件付きunion/旧BOOLEANのいずれかであることをread-onlyで確認した。
このoffsetはWin64専用で、他ABIへ転用しない。Pythonのwcharサイズやhostのlongサイズへ依存しない。

RootDirectoryによる相対名解決は現行公式ページの記述に基づく接続案であり、このPCの実APIで確認していない。
既存D2のRootDirectory=NULL＋absolute target経路は変更しない。
driver/Windows版に依存しうるため、native採取の受入条件として実挙動を検証する必要がある。
compile/SDK header参照や模擬APIのpassをnative acceptanceへ読み替えない。

## 失敗とcommitの扱い

要求構成は副作用前に終え、begin→parent/source再検査→API→succeedの順にする。
同名targetの出現はOSのno-replace判定へ任せ、exists確認→上書きrenameや削除へfallbackしない。
APIが物を移動した後に応答が失われた場合、journalはunknownで停止する。
明確な成功応答の後は追加readbackを行わず、commit confirmedを保持する。
成功応答のjournal記録前にMemoryErrorがあればunknownのままである。
記録後の異常はconfirmedを維持して全体停止とする。teardownは必須の別工程である。

直接/因果連鎖/context/ExceptionGroupのMemoryErrorを資源停止として扱う。
同じ例外graphでAdapterError/OSErrorの整数winerrorも調べ、8/14/39/112/1450〜1455/1816を
資源停止とする。メモリ、ディスク、system pool、working set/pagefile/quota不足の対応は
[0〜499](https://learn.microsoft.com/en-us/windows/win32/debug/system-error-codes--0-499-)・
[1300〜1699](https://learn.microsoft.com/en-us/windows/win32/debug/system-error-codes--1300-1699-)・
[1700〜3999](https://learn.microsoft.com/en-us/windows/win32/debug/system-error-codes--1700-3999-)の公式定義に基づく。
これは選んだ既知資源コードの分類で、全OS/driver固有エラーの網羅を主張しない。
未知コードも成功や再試行にはせず停止する。backendの資源予算超過はBudgetStopを送出する契約。
例外graphは64 nodes/128 pendingまで。超過時も資源停止とする。snapshotのOOM安全性は主張しない。
backendの元例外は伝播するが、journalへ例外本文・pathを複写しない。
返却型やpinの不正、再実行、資源停止を含むすべての異常で後続backend呼出を止める。

## native接続前の残件

終端の所有handle解放は[所有終了・権限接続設計](anomaly-v03-handle-lifecycle-design.md)の
注入backend部品で具体化した。取得途中の所有移管、事前writer/子handle解放、実権限検証は別の残件である。

新規fixtureの所有確認と全ancestorのhandle保持、DELETE等の取得rights、share mode、link/reparse/ADSの検査、
payload子handle保持とdirectory renameの両立、marker/親directoryのDACL保護とcommit可能性、
flush/close/競合時の実証跡とprivate bytes保持、独立tokenの実効権限を別途実装・検証する。
権限固定後に必要rightsを名前経由で取り直すことを前提にしない。
B1の終了済み試行枠を流用せず、具体的なnative試行範囲と資源上限を確定してから実機へ進む。

2026-09-14の[file権限固定](anomaly-v03-file-sealing-design.md)で、marker DELETEをDACL固定前に取得し、
固定後も同handleの実権限を保持して親borrow内の継続処理へ渡す範囲を限定実機確認した。
継続処理は観測のみで、このBoundRenameの実API接続、directory/root固定と親の追加権限は未完了。

続く[directory固定試行](anomaly-v03-directory-rename-design.md)は別のsingle-use DirectoryRenameで、
子解放後のstage/root固定・権限保持・証跡3個保存を実行した。Win32相対要求は87、明示的NT要求は5で失敗し2回枠を終了。
既存BoundRenameをnative成功済みとは扱わない。非NULL保持親・固定済み親でのrenameは成立未確認のため、
次は親保護と名前変更順序を見直す。初回Win32 wrapperの静的変換推定と、NT呼出しのbuffer寿命修正は上記設計を参照。

[親policy比較](anomaly-v03-parent-policy-rename-design.md)で、同じ保持親のNT要求がprivateでは成功しfrozenでは5で拒否された。
BoundRenameの既定wire/契約は不変。次の候補は同一親内の直接NT leaf/NULL RootDirectoryを明示する別adapterで、
保持親の観測/寿命を残した設計・pure故障検証を先に行う。実機成功やCWD/競合に関する保証はまだない。

[同一親内NT leaf試行](anomaly-v03-same-parent-rename-design.md)は182件pass・独立指摘0を経て実行し、親frozen下で5を返した。
API形式だけでは解消せず、1回枠は終了。[順序案と既取得権限の論点](anomaly-v03-publication-order-options.md)を次の検討対象にする。
