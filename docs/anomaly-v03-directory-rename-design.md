# S4-B2 directory固定と保持親からの相対rename

2026-09-14、基準9375b3e。tests/fixturesの局所engineering接続。
[file固定](anomaly-v03-file-sealing-design.md)の次に、新規root/stageと小file1個だけで
directoryのDACL固定・保持権限・上書きなしstage→payloadを実検証する。

## 接続範囲と順序

WindowsDirectoryFixtureは既存private sinkの取得追跡を使い、作ったroot/stageだけ追加権限を要求する。
既存祖先は従来の読取り保持でDACLを変えない。root/stageは初回取得から一つずつ所有する。

| 対象 | 固定した要求/実権限期待値 | 条件 |
| --- | --- | --- |
| root | 0x1600a7：LIST/ADD_FILE/ADD_SUBDIRECTORY/TRAVERSE/READ_ATTRIBUTES/READ_CONTROL/WRITE_DAC/SYNCHRONIZE | 初回取得、share READ+WRITE、DELETE共有なし |
| stage | 0x1700a1：LIST/TRAVERSE/READ_ATTRIBUTES/READ_CONTROL/WRITE_DAC/DELETE/SYNCHRONIZE | 初回取得、share READ+WRITE、DELETE共有なし |
| stage/facts.json | writer0x12019f→固定用0x160081 | writer flush/証跡保存/close後だけ別世代で再取得、固定後証跡を保存してclose |

SealedFilesにrequire_marker=Falseの明示payload-only modeを追加する。
このmodeにはmarker-pending.jsonを含めない。既定のmarker必須条件は維持する。
directory設定は既存file設定のguard/LocalFree/一次例外維持を共用し、frozen directory policyを使う。

DirectoryRenameはcaller保持ownerのroot/stageを同期借用する。
全child writerと新世代fileのclose成功・停止なし、全子slotとfile planの対応を確認する。
root/stage両方の元ID/private SD・実権限を確認してから、stage→root順でfrozen DACLを設定する。
各directoryは設定直前にも元観測へ照合し、設定後ID/SDと非DACL属性不変、実権限の保持を確認する。
frozen directoryはEveryone deny0x10156、private allow3個＋Restricted Code read allow、継承ACEなし。

保存callbackが成功した後、root/stageのfrozen観測を再照合してから既存rename_requestの
FileRenameInfo=3、RootDirectory=保持root、固定leaf payload、replace/追加flags0を実APIへ渡す。
[FILE_RENAME_INFO](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_rename_info)の
相対名/RootDirectoryの定義と[SetFileInformationByHandle](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-setfileinformationbyhandle)
の返却条件に従う。Win64要求は既存の36 bytes、offset0/8/16/20を再利用する。
BOOL0直後だけGetLastError、signed非zeroで成功。絶対名・CWD解決・別API・上書きへのfallbackは作らない。

保持rootにADD権限があっても、固定DACL下でrenameが通るかは実機で判定する。
[driver側FILE_RENAME_INFORMATION](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_file_rename_information)
の同volume/共有/名前解決の制約も踏まえ、宣言やpure試験だけで成立としない。
API失敗・応答喪失ではpendingのまま停止し、再設定/rename再試行/rollback/削除をしない。
API成功応答はconfirmedとして記録し、以後は純guardと所有終了だけ。後発停止でconfirmedを消さない。
元pinのpathはstageのまま履歴として残し、成功後の同handleで旧名を観測しない。

これはBoundRename全modelの実装完了ではなく、同じ固定wireを使う局所directory操作である。
6工程journalはprepare pendingから終了時unknown/stopped、commit not_startedのまま。
local operationのdirectory_states/evidence/renameを別に記録し、未実行の前工程を成功にしない。

## private証跡と読取り確認

prepare.jsonはwriter解放前のroot/stage/file ID、private SD、raw file/marker bytesを保持する。
seal_payload.jsonは固定用file handleを閉じる前に、新fileのfrozen SDと元root/stage観測を保持する。
verify_final.jsonはdirectory固定後・rename前に、新root/stage SDと先に閉じたfile観測を保持する。
第三名は既存sinkの予約名であり、モデルverify_final工程を実行したという意味ではない。
最初の保存/子writer解放はEvidenceBarrierを通す。後の2保存は更新観測をprivate sinkへ直接保存する局所接続。
closed旧slotへの追加や、新file pinを元ownerへ認証/移管する処理はない。

成功した所有終了の後だけ別読取り確認を行い、root/payload/facts.jsonの3 objectsを再取得して
保存した元ID/bytes/frozen SDと照合する。新しい3 cellsもtrackedで順次closeする。
renameの未知応答や所有終了失敗後はこの読取り処理を行わない。
独立token/consumer/authenticated証明や敵対的同userに耐える検証ではない。

## 新規限定native仕様

| 項目 | 固定範囲 |
| --- | --- |
| root | 新規artifacts/directory-rename-2026-09-14/attempt-1またはattempt-2だけ |
| 前提 | pure/fault・独立レビュー完了、clean exact HEAD/監視hash固定、既存Windows CPython3.14.0 Win64 |
| 新規構造 | attempt/source-fixture/stage/facts.jsonと別private-evidence。file4096 bytes以下。markerは証跡内bytesのみ |
| native操作 | writer作成/write/flush、file再取得/固定、stage/root固定、証跡3個保存、相対no-replace rename1回、所有終了後の読取り照合 |
| CWD | 新規attempt。保持source-fixture rootとは別。CWDへ解決されても新規attempt内に限り、期待inventory不一致で拒否 |
| 範囲検査 | 実操作前にstage/payloadの解決先が作成済みsource-fixture直下であることを確認 |
| 予算 | source1 file4096 bytes以下、証跡各64KiB/3個、報告128KiB。private256MiB/working384MiB、空きRAM/drive各2GiB |
| 時間 | 境界40秒/外側45秒、hidden保持Processを約1秒監視し終了確認 |
| 回数 | 最大2。失敗原因特定・修正レビュー後だけ新規2回目。成功で終了、未使用枠繰越なし |
| 正常終了期待 | source13＋sink14＋file世代1＋最終reader3＝31 tracked handles、query token2個close、worker exit0 |
| 異常時 | 所有終了だけ、資源停止後は通常snapshot/JSONを作らず固定通知/exit80。不明close再試行・fixture自動削除なし |
| 対象外 | marker作成/.complete/全publication、独立token実操作、native競合/故障注入、旧root/別project/正式pin変更 |

31 handlesは祖先深さ・証跡3個による今回配置の期待値で、実記録を結果書へ残す。
4境界のメモリ観測や外側監視は、長期リーク不在・全期間最大メモリ・hard時間上限を保証しない。
build/bootを記録し、Windows Update後UBRのengineering緩和は正式OS pinへ波及させない。

次は実結果に基づく親権限/相対rename可否の確定と、marker/後続phaseの統合・独立token/故障/競合。
formal_permission/execution_authenticatedはfalse、acceptance_statusはnot_completedを維持する。
