# S4-B2 writer解放後の読取り世代の再取得

2026-09-14、基準c50aabc。tests/fixturesのengineering部品。
元のclosed slotを復活させず、別の短命reader世代で同一物と実権限を確認する。

## 接続範囲

ReacquiredReadersは全plan/最大8 cellsをnative取得前に保持する。
writer_index・親root・元pin・raw hash・単一相対名を固定し、元ownerとcell双方のclosed確認を必須にする。
親rootを既存owner.borrowedで保持し、その中で全readerを取得・検査・逆順解放してから戻る。
途中失敗でも同じborrow内で取得済みreaderを終了する。残る元root/祖先はその後に元ownerが終了する。
new readerは終了後のraw数値再利用を許容するが、旧closed slotを再closeしない。

各readerは元volume/file ID/type/raw hash、exact bytes、正規化SD bytesに照合する。
既存inspect_nativeへ外部guardを渡し、親owner/journalやreaderの停止を各観測境界で検査する。
write/DELETE等の余分な権限、read不足、同bytesの別ID、SD変化、閉鎖不明、再入の握り潰しは停止する。
応答喪失時もcaller保持holderから終了状態を確認でき、再acquire・不明handle再close・自動清掃はしない。

新readerはREAD_DATA/READ_ATTRIBUTES/READ_CONTROL/SYNCHRONIZE（0x120081）だけを要求する。
share READ、OPEN_EXISTING、OPEN_REPARSE_POINT、非継承で開き、create/truncate/write/flushは行わない。
[CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)の
取得/共有条件と[権限定数](https://learn.microsoft.com/en-us/windows/win32/fileio/file-access-rights-constants)を照合した。

[NtQueryObject](https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntqueryobject)の
ObjectBasicInformation/PUBLIC_OBJECT_BASIC_INFORMATIONでGrantedAccessを取得する。
ULONG4 fields＋Reserved[10]の56 bytes、GrantedAccess offset4、返却長56・NTSTATUS0を要求する。
元writerは0x12019f、new readerは0x120081をexact比較する。
NTSTATUS失敗は[RtlNtStatusToDosError](https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-rtlntstatustodoserror)で
WinErrorへ変換し、既知資源エラーの分類を引き継ぐ。query失敗を権限確認成功にしない。
これらは実ハンドルの読取り確認であり、他tokenのAccessCheck/実操作や永続的な書込み禁止の証明ではない。

readerはacquire終了までに閉じる。後続seal/renameへlive readerを渡すAPIや、既存ownerへの動的slot追加はない。
現在user/SYSTEM/Administratorsのprivate DACL自体は変更せず、owner/adminの変更・同user攻撃・mappingは対象外。
全受入flagsはfalse/not_completedのまま。

## 新規限定native仕様

既存observed prepare driverへ固定scenario用のbefore_release/after_release/finish/結果フックを追加する。
新entryはReaderScenarioを渡し、前回driverの旧rootは再利用しない。
reader失敗時も全reader終了→元group終了→元ancestor/sink終了の順で、資源停止後は固定通知/exit80に限定する。

| 項目 | 今回の固定範囲 |
| --- | --- |
| 前提 | pure/fault検証・独立レビュー後、exact clean HEADと監視script hashを固定 |
| runtime | 既存Windows CPython3.14.0 Win64。実build/boot記録、新規runtime導入なし |
| root | candidate artifacts/reader-reacquisition-2026-09-14/attempt-1またはattempt-2のみ |
| source/evidence | source2 files各4096 bytes以下、prepare証跡1個64KiB以下、probe報告128KiB以下 |
| 実操作 | 前回の新規source作成/prepare保存/選択解放に加え、writer権限2照会、reader2再取得・権限/同一物/SD照合・close |
| 対象外 | DACL seal・変更、WriteFileによる拒否試験、token変更、rename/.complete、正式publisher、他project/旧root操作 |
| 資源 | worker private256MiB/working384MiB、空きRAM/drive各2GiB以上。境界40秒・外側45秒、約1秒process監視 |
| 回数 | 最大2。原因特定と修正レビュー後だけ新rootで2回目。成功で終了、未使用枠繰越なし |
| 終了 | 旧tracked25＋new reader2、照会token2個のclose、exact source/evidence readback、worker exit0 |
| 異常時 | 全体停止、所有解放のみ。不明close再試行・自動削除なし。資源停止後はsnapshot/通常JSONを作らない |

hidden workerと保持Processのみを監視し、終了を確認する。監視scriptの前回検証済み構造を引き継ぐ。
hard時間上限、Start-Process内部の返却喪失、電源断耐久性、長期リーク不在の保証はしない。
公開前の局所試行なのでjournalはprepare unknown/stopped、teardown succeeded、commit not_startedを維持する。
正式OS整合、VM digest、runtime closure/consumer、独立token/競合/失敗native全受入、S4受入は残る。

## 実行結果

cbb5a82のclean HEADで1回目成功。元writer2個0x12019f→new reader2個0x120081を実照会し、
元ID/bytes/SD一致、27 tracked handles/token2個close、worker exit0、外側0.400秒、stderr0 bytesを確認した。
今回枠は成功で終了し、未使用枠を繰り越さない。[結果・保存記録](results/anomaly-multiseed-v0.3-s4-b2-reader-reacquisition-2026-09-14.md)を参照。

後続の[file権限固定](anomaly-v03-file-sealing-design.md)は内部hookを使う別のSealedFiles世代で、
WRITE_DAC/marker DELETE取得・frozen DACL読戻し・親borrow内のlive continuationを接続した。
通常ReacquiredReadersのread権限・終了契約は維持する。
