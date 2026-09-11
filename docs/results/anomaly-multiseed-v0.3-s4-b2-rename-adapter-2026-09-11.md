# S4-B2 保持handleによるrename部品の模擬検証

日付2026-09-11。基準be61da850cad0ec8f071f4b86c44759ea7157502。
実装savepoint **dd318aec56f8e43909ff6df6192d62e11aa914bd**。

**固定2操作の注入backend用prototypeを作成し、新規18＋既存16＝34 testsがpass。**
最初の独立レビューP2を修正し、再レビューと最後の小差分確認の残件はP0〜P3 0件。
実Windows publisher/受入は未実装・未実行である。

## 実装と確認した範囲

[具体設計](../anomaly-v03-rename-adapter-design.md)とtests/fixtures/anomaly_v03_rename_adapter.pyに、
stage→payloadとmarker-pending.json→.completeだけを扱うsingle-use部品を追加した。
親/sourceの保持handle、volume/file ID、種別、markerの期待hashを束ねて、
前回のjournalのbegin→再検査→rename要求→succeedへ接続する。

要求はWin64の固定byte buffer。上書きflagは0、宛先は保持した親の下の固定leafだけ。
本体・完了印ともrenameを使う接続案であり、既存S3のhardlink marker契約は変更しない。
借用handleは閉じず、所有側のteardownが必要な状態を維持する。
実Win32の相対RootDirectory、DACL、share mode、driver挙動はこの試験では証明しない。

模擬backendは別のhandle/object/name表を持ち、要求はpacking関数を使わずoffsetから読み取る。

- 同名targetがAPI直前に現れても置換せず、既存物と元sourceを残す。
- 名前の交換後も要求に渡すsourceは保持したhandle。模擬表では元objectへ結び付く。
- 親/sourceのidentity・volume・種別・名前・marker bytesの変化を拒否する。
- backend内で停止や再入エラーを握り潰しても、次のbackend呼出を止める。
- BOOL/errorの型違い、未取得エラー、順序違反、別journalでの再利用を拒否する。
- APIが実際に模擬表を変更してから応答を失うと、commit unknownのまま停止する。
- journal記録後の失敗・teardown失敗はcommit confirmedを残し、全体を停止する。
- 資源不足や通常例外、KeyboardInterruptの各境界で後続呼出がないことを確認する。

backendはtrusted内部契約である。模擬成功は実APIの成功を保証せず、偽の成功応答を独立認証しない。
実機操作や完了印の意味検査をこの部品だけで証明しない。
retry/cleanup/formal_permission/execution_authenticatedはfalse、acceptance_statusはnot_completed。

## レビューと検証

最初の独立レビューで、Win32の資源不足が一般的なAPI失敗に分類されresource_stopが立たないP2を検出。
AdapterError/OSErrorの既知winerrorを直接・cause/context/ExceptionGroupのbounded graphで分類する修正を入れた。
対象は8/14/39/112/1450〜1455/1816。MemoryError/BudgetStopとgraph上限超過も資源停止。
未知エラーも停止し、全OS/driverの資源エラーを網羅するとは主張しない。根拠は設計書の公式資料を参照。

初回34/34 pass、0.028秒。その後、公式定義で確認した1451〜1454のpool/quota不足を実装とsubtestsへ追加し、
最終34/34 pass、0.021秒。両回ともfailure/error/skip/expected failure/unexpected success0。
追加した4 casesは既存method内のsubtestsであり、method数を38とは数えない。
元の初回記録も保存し、実装変更に対応した再検証として区別した。
独立担当は読取りだけを行い、試験/native/ネット/編集なし。進捗ポーリングなし。
repository safety / staged diff-check pass。試験対象4ファイルのraw bytesは保存commitのGit blobと一致した。

ローカルWindows CPython3.14.0による選抜試験のみ。旧Linux CIのpass数へ加算しない。
src/科学config/schema/registry/正式OS pin、本流889cfc3は変更なし。
前回実行済みのsource boundary 3件を今回の実行数に含めず、追加の全回帰/native controlは起動していない。

## 記録と資源

新規ignored root artifacts/rename-adapter-2026-09-11/へ保存した。

| 記録 | bytes | SHA-256 |
| --- | ---: | --- |
| initial-checks.jsonl | 24222 | ee08e158f3cec87e146970a0a30c051bcd7fac08bd083076ebcc22de9bc0d274 |
| final-checks.jsonl | 24224 | 63cfad456db4af0c3f6a9e56fcef7619e358bd958094ebbafa1e4dde71ca846f |
| resources-final.json | 475 | 4d6e13e4a703bf898f79a98b4207ce8ec9352f384d0a3671443d4fee4c3ee1ea |

各JSONLにtest IDs/結果、実行時の未commit raw source hashと基準revision、Python版を記録。
savepoint-evidence.jsonに確定commit、raw/Git blob一致、レビュー是正、開始資源と記録hashを保存した。

開始UTC02:46:02Z RAM空き8.54GiB/C105.38GiB/D75.36GiB。
最終03:04:14Z RAM7.60GiB/C105.37GiB/D75.36GiB。
build26200.9445、boot2026-09-09T10:43:08.5000000+09:00を記録した。
RAMの点変化を本作業のリークへ帰属させない。短い試験・記録processは終了し、常駐処理なし。
別project/旧failure fixture/共有runtimeへの操作、新runtime導入、push/merge/CI起動はない。

## 次の接続境界

native backendのfixture/全ancestor保持と所有終了、marker/親directoryの保護、
payload子handleとdirectory renameの両立、flush/close失敗とprivate bytes保持を具体化する。
この模擬backendをproduction実装と数えず、実APIの根拠と実試行の範囲・資源上限をレビュー可能にしてから接続する。
前回成功で終了したB1試行枠は流用しない。Windows全受入、正式OS整合、VM image digest、
runtime closure/consumer凍結、S4受入は引き続き未完了。
