# S4-B2 固定済み親内のNT leaf rename設計

2026-09-14、基準7aa4d30。[親policy比較](anomaly-v03-parent-policy-rename-design.md)の2条件枠は終了済み。
今回は親frozenを維持し、sourceの同じ親で名前だけを変える明示adapterを別に設ける。

## 名前解決と所有の契約

[FILE_RENAME_INFORMATIONの公式説明](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_file_rename_information)は、
単一file名＋NULL RootDirectoryを同じdirectory内の名前変更として区別している。
直接NtSetInformationFileへ渡すこの形式を試す。Win32 wrapperのDOS path変換は通さない。
sourceの親を使う形式の文書根拠であり、親frozen下で必ず成功するという保証ではない。

SameParentDirectoryRenameは既存DirectoryRenameを継承し、parent_policy=frozenを固定する。
元root/stageのslot結合、全子fileとの対応、元ID/SD、親・sourceの保持、実権限、子writer/新世代のcloseを残す。
stage→rootのDACL固定と読戻し、証跡保存後の再検査が成功したときだけ名前変更を1回要求する。
APIのRootDirectoryフィールドがNULLでも、保持rootや検査を省かない。
作成時に保持した祖先/root/stageのviewは期待するpath・identityを照合し、相対名から別親を開く経路は追加しない。

固定wireは36 bytes、flags0、RootDirectory0、FileNameLength14、単一UTF-16LE leaf payload、末尾NUL。
callerから名前・path・親・flags・stepを受け取らない。native bufferは既存と同じ40 bytes/class10、IOSB16 bytes。
WindowsNtSameParentBackendだけがこのwireを受け付け、既定WindowsNtDirectoryBackendは非NULL保持親wireのまま。
旧encoder/BoundRename/S3 hardlink marker/D2契約は変更しない。失敗後のAPI/絶対path/親policy/別wireへのfallbackなし。

NTSTATUS処理、返却喪失前のcompletion_unknown、buffer保持、STATUS_PENDING時の資源停止は既存backendと共通。
成功応答後の後発停止でもconfirmedを消さず、未知・拒否はpendingで停止して後続IOを止める。
unknown completion時は所有終了後にbufferを保持したworkerをexit80で終え、再送信・待機・cleanupを再開しない。

## 1回だけの新規実機仕様

| 項目 | 固定範囲 |
| --- | --- |
| root/entry | 新規artifacts/same-parent-rename-2026-09-14/attempt-1、tests/fixtures/anomaly_v03_same_parent_probe.py |
| 回数 | 1回だけ。成功・失敗を問わず枠を閉じる。entry/監視ともattempt-2を受け付けない |
| 前提 | pure/fault・独立レビュー完了、clean exact HEAD/source hash/監視hash固定、既存CPython3.14.0 Win64 |
| 親policy | root/stage/fileすべてfrozen。親private比較modeとの併用不可 |
| 取得 | root0x1600a7/stage0x1700a1、share READ+WRITE・DELETE共有なし。writer0x12019f→file0x160081 |
| 内容 | source-fixture/stage/facts.json45 bytes。markerは証跡内bytesのみ、別private sinkへ3証跡 |
| API | NtSetInformationFile/class10/40 bytes、source保持handle、NULL RootDirectory、固定leaf payload、上書きなし |
| CWD | 新規attempt親。保持source-fixtureとは別。完了時はsource-fixture/payloadだけに期待inventoryがあることを確認 |
| 終了後検査 | 成功・teardown確認後のみroot/payload/factsをreadonlyで再取得し、元ID/bytes/frozen SDへ照合してclose |
| 資源 | source4096 bytes、証跡各64KiB/3個、報告128KiB、private256MiB/working384MiB、空きRAM/disk各2GiB |
| 時間 | worker境界40秒、外側45秒、hidden保持Processを約1秒監視して終了確認 |
| 所有終了 | 成功時source13＋sink14＋file1＋最終reader3＝31 handles、照会token2個。rename失敗時は28 handles＋token2個 |
| 失敗時 | 所有終了のみ。失敗sourceを終了後に再検査・hash取得・再利用・削除しない。資源停止後の通常reportなし |

選択modeとname_resolution=source_parent/root_directory_is_nullをreportへ保存する。
既定の保持親方式・過去2条件のentryは維持するが、その終了済み枠を再実行しない。
Windows Update後のengineering UBR緩和、実build/boot記録、正式OS pin不変を維持する。
1回の短時間観測は長期リーク不在・全期間最大メモリ・hard時間上限を証明しない。

## 受入との境界

成功時でも、新規1fileの局所的な名前変更と終了後同一物確認の結果だけを主張する。
native同名衝突/競合、独立token実操作、rename後の保持handle内再検査、marker commit、全6工程の統合は別の残件。
衝突・応答喪失・親入替え・close不明・異なるwireの拒否をpure backendで確認してから実機を起動する。
private証跡3個はいずれもrename前。verify_final予約名をmodelの完了に読み替えない。
journalはprepare unknown/stopped、teardown succeeded、commit not_startedを維持し、marker file/.completeを作らない。
formal_permission/execution_authenticated=false、acceptance_status=not_completed。科学仕様・production入口・既存正式pinは変更しない。
