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

初回仕様では、保存callbackが成功した後、root/stageのfrozen観測を再照合してから既存rename_requestの
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

## 初回結果と修正した2回目仕様

初回はclean a20988688e65d829a6619c399813da2a319d22a2で実行し、
file/stage/rootの固定と証跡3個保存は成功したが、SetFileInformationByHandleがWinError87を返した。
renameはpendingのまま停止、終了後読取りは未実行。source13＋sink14＋file1＝28 tracked handlesとtoken2個をcloseしworker exit1。
初回artifactは保存したまま再利用しない。上の31 handlesは正常時の読取り3個を含む期待値である。

インストール済みKernelBase.dll（10.0.26100.9278、4212112 bytes、
SHA256 becad014fb8efa8cb5e314931cca92778ad42c649b12a6909632cacd68af4f40）をファイルとして読取り、
export/例外表/既存Capstoneの静的解析を保存した。追加のrename/DLL関数呼出は行っていない。
class3分岐RVA0xf172cはRVA0xf1795でRtlDosPathNameToNtPathName_U_WithStatusを呼び、
入力RootDirectoryをRVA0xf17fcで複写してからRVA0xf1816でNtSetInformationFileを呼ぶ。
通常leaf payloadが絶対NT名へ変換され、非NULL親との組合せで拒否されたという推定が初回87と整合する。
実際の内部NTSTATUSや動的引数をtraceした証明ではなく、呼出先はPE import表から同定した。
現行Win32文書の相対RootDirectory説明だけでは、この実装の成立を保証できない。

2回目は別の新規attempt-2で、同じ保持親と単一leafを直接
[NtSetInformationFile](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntsetinformationfile)
へ渡すWindowsNtDirectoryBackendを明示選択する。初回失敗から自動fallbackする経路は作らない。
user modeのNt呼出を使い、FileRenameInformation=10、同じoffset0/8/16/20を保ち末尾paddingを含め40 bytesとする。
NtのFILE_RENAME_INFORMATIONのsizeof＋名前長を満たす。NTSTATUS0だけを成功とし、
他statusは既存RtlNtStatusToDosErrorで記録する。Win32 GetLastErrorは読まない。

[IO_STATUS_BLOCK](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_io_status_block)は
既存SDK winternl.h:223のunion/ULONG_PTR定義と照合し、Win64 sizeof16/Information offset8。
非pendingは返却NTSTATUSが根拠で、IOSBの値を別の成功要件にしない。
sourceはOVERLAPPEDなしの同期handle。予期せぬSTATUS_PENDINGは成功にせず資源停止とし、
caller保持backendへ入出力bufferを保持したまま所有終了し、workerをos._exit(80)で終える。
独立レビューP2を受け、呼出前にcompletion_unknownを立て、正常な非pending返却の検証後だけ解除する。
API内の返却喪失やpending判定前の中断も資源停止へ昇格し、同じbuffer保持・固定通知・worker即時終了へ接続する。
待機・再送信・別経路への変更はしない。通常エラー/成功時には従来の終端処理を使う。

root/stage/子の権限、DACL、証跡順、CWD、資源上限は初回と同じ。
親DACL固定後に内部target openが拒否される可能性も残るため、NT経路の成功を事前に仮定しない。
2回目で成功または失敗した時点で今回枠を終了する。3回目や旧fixture再操作はしない。

## 実結果・枠の終了と次の設計

修正91cd5acのclean HEAD/source24 files/監視hashを固定した2回目は、NTSTATUS0xc0000022→WinError5で失敗。
file/stage/root固定と3証跡保存、保持権限0x1600a7/0x1700a1は確認したが、相対rename成功は確認できなかった。
native返却は非pendingでcompletion_unknown=false。operation.renameは成功未確認のpendingで停止する。
各試行28 tracked handles/token2個close、worker exit1、終了後source再検査なし。最大2回枠は終了した。
最終167件pass、レビューP2を1件修正して残りP0〜P3=0。
[結果・記録・資源](results/anomaly-multiseed-v0.3-s4-b2-directory-rename-2026-09-14.md)を参照。

親のfrozen DACLによる内部target open拒否が候補だが、原因を分離する比較はまだ行っていない。
次は親private/frozenの条件差と、root固定・payload rename・marker commitの順序をpure modelから検討する。
rootをprivateに保つ間の競合/親経由deleteと、完了印前の保護を同時に満たす必要がある。
固定を後回しにするだけで受入へ進めず、新規比較の範囲・終了条件を具体化してから別枠を作る。
