# S4-B2 取得追跡・Windows private保存の限定試行

日付2026-09-14、基準af97323。tests/fixtures内のengineering部品。
B1ハーネスの終了済み試行枠、正式publisher、campaignとは別の保存確認を対象にする。

## 実装境界

TrackedOpenはopenerに事前確保したcellを渡し、OSから返ったraw handleを先に格納させてからinspectへ進む。
inspect/後続割当て失敗でも取得済みraw値を一度だけcloseする。closeの応答喪失では再closeしない。
raw値を記録する前にopenerが失敗した場合はunavailableであり、存在するか不明なhandleを推測しない。
残留資源の回収には限定worker終了が必要。無制限OOM下で漏れのない取得を保証しない。
CloseHandle対象の所有資源だけを受け取り、二重acquire/取得中close/握り潰しを拒否する。
固定batchの管理移管は[後続の接続](anomaly-v03-observed-evidence-design.md)で追加した。
[読取り世代の再取得](anomaly-v03-reader-reacquisition-design.md)を後続で確認した。動的slot追加やseal/rename用のlive移管は未実装。

WindowsPrivateSinkはB1の低水準Win/_Bound観測・SD検証部品を遅延importして再利用する。
B1のpublic harness、制限token生成、impersonation、別token/processのcontrolsは呼ばない。
既存祖先を最大16段までDELETE共有なしで保持し、新規rootをprivate protected DACLで作成する。
rootと各fileのowner/group/保護bit/ACEを既存private policyへ照合する。
private policyは現在user/SYSTEM/Administratorsのみ。owner/adminによる意図的な変更への防御ではない。

新fileはCREATE_NEW、非継承、DELETE_ON_CLOSEなし、GENERIC_READ/WRITE+READ_CONTROLで開く。
作成直後のraw値を登録し、同handleのidentity/path/local NTFS/link/reparse等を既存_Boundで照合する。
順序はprivate SD検証→WriteFile全bytes→FlushFileBuffers→同handle読戻し→SD再検証→CloseHandle。
writeが短い場合は継続せず停止する。書込/flush/読戻し/closeの失敗は成功扱いにしない。
完了後も3 filesを残し、既存file/rootの上書き、権限変更、自動削除はしない。
rootのCreateDirectoryと取得の隙間、hostile same-user、writable mapping、電源断耐久性は未保証。
補助的なidentity照会handleやSD文字列変換は既存部品を使うため、全native割当ての新規所有監査完了ではない。

保存先はprepare.json/seal_payload.json/verify_final.jsonのみ。各512KiB/attempt合計1.5MiBを上限にする。
入力不正や一度の失敗でsink全体を停止し、同じphaseを再保存しない。
保存中の再入/finishも拒否し、拒否を握り潰しても次のwrite/flush/readbackへ進まない。
例外の本文や物理pathは結果へコピーせず、固定reason/WinError/各段階の状態を記録する。

## 今回のnative試行仕様

この段階では独立レビューとpure/fault検証を通したclean savepointから以下だけを実行する。
別project連続稼働の同時負荷制約は終了済み。通常の資源確認は続ける。

| 項目 | 固定する今回の範囲 |
| --- | --- |
| runtime | このPCのWindows/既存CPython3.14.0 Win64。新runtime導入なし。実build/bootを記録 |
| worker | tests/fixtures/anomaly_v03_private_sink_probe.py。正確なclean HEADを必須 |
| 新規root | candidate内artifacts/private-sink-2026-09-14/attempt-1またはattempt-2/private-evidence |
| 実データ | synthetic JSON 3個、合計16KiB以下。source/customer dataを保存しない |
| 実操作 | 新規root/fileのprivate DACL作成・検証、write/flush/readback/close、終了後readback |
| 対象外 | rename/.complete、正式publisher、B1 control、token変更、他project/既存失敗rootの操作 |
| 資源 | worker private256MiB/working384MiB、空きRAM2GiB・対象drive空き2GiB以上 |
| 時間 | worker境界40秒、外側の上限45秒。外側は約1秒間隔でprocessメモリも監視 |
| 試行数 | 最大2。2回目は原因特定と修正レビュー後だけ、別の新規root。成功で終了、未使用枠の繰越なし |
| 失敗時 | 原因/段階/記録を残し停止。未知handleの再closeやfile/root清掃をしない。worker終了を確認 |
| 保存物 | private filesと128KiB以下のprobe-result、外側stdout/stderr/資源記録。過去記録を上書きしない |

境界と外側の観測はhardリアルタイムの上限保証ではない。監視検知時は当該workerだけを終了する。
資源停止時は所有終了と固定の最小通知/exit80だけに限定し、workerのsnapshot/通常JSON報告の保存を抑止する。
資源停止後の通常報告再試行は行わず、外側の監視記録で補う。外側の記録保存自体も失敗しうるため、欠落を成功扱いにしない。
B1の失敗物や無関係なprocessは終了・削除しない。別workerの終了後、残った新規private証跡を保持する。
成功には3 filesのexact inventory/hash、private SD検証、全追跡handleとtokenのclose確認が必要。
native保存smoke成功でもS4受入・独立token実効権限・観測認証・publisher成功は主張しない。
formal_permission/execution_authenticatedはfalse、acceptance_statusはnot_completedのまま。

## 実行結果と枠の終了

847de63のclean HEADで2026-09-14に1回目を実行し、3 files/478 bytesの保存・読戻し・所有終了が成功した。
外側0.400秒、追跡14 handles/token closed、worker exit0。今回枠はここで終了し、2回目の未使用枠を繰り越さない。
[結果・資源・記録上の注意点](results/anomaly-multiseed-v0.3-s4-b2-private-sink-2026-09-14.md)を参照。

## 次の境界

[後続の実観測接続](anomaly-v03-observed-evidence-design.md)で、取得済み3 slotsの一括管理移管と
native pin/descriptor/bytes→EvidenceBarrier→本sinkのprepare保存・選択解放を限定実機で確認した。
writer解放後の一時reader再取得は確認済み。続く[file権限固定](anomaly-v03-file-sealing-design.md)では
2 filesのWRITE_DAC/marker DELETE取得・固定とlive continuationを確認した。
directory/root seal・rename、動的slot追加、rename前後の同一物統合は残る。
今回のnative JSONは保存部品用の合成bytesであり、正式完了印や性能結果ではない。
正式OS整合、VM image digest、runtime closure/consumer凍結、native全受入は引き続き別の残件。
