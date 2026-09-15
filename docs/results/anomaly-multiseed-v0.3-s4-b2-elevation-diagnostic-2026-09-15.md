# S4-B2 管理者起動の独立診断結果

2026-09-15、容量整理後に再開。実装savepoint **d7253c8dd16ece6c128656e716371863d4e5bc2f**、[診断仕様](../anomaly-v03-elevation-diagnostic-design.md)。OS設定を変更しない固定SID/admin自己照会を通常権限とRunAsで各max1実行した。

| 観測 | 通常Control | 管理者Run |
| --- | --- | --- |
| 開始UTC | 02:35:56.8737001Z | 02:36:06.9315709Z |
| PID | 37092 | 39144 |
| 起動要求ms（UACを含む） | 102 | 5260 |
| 終了待機ms | 355 | 650 |
| 合計ms | 492 | 5958 |
| 終了code | 41（固定U SID/非admin） | 40（固定U SID/admin） |

両方ともprocess Handle確保、終了観測、Process object解放を確認。一次/解放例外なし。今回の昇格起動・終了観測は成功。前回principal準備の失敗原因はunknownのままで、UAC取消と断定しない。account/root API・準備Entry・P logon・publisherは呼んでいない。旧root/fixtureへ再訪なし、閉鎖setup attemptや診断guardを再使用しない。

故障試験13ケースpass、独立P0〜P3所見0件、repository safety/staged diff-check pass。前回78 source不変、新規3 sourceを含む81 sourceをGit/raw照合した。既存401件は対象不変のため再実行なし。
input14957 bytes/SHA256 **0cfa96e306e113c4e0fc2510073e5c3095ff2c230bed82a47ad32a5b0609578d**。
ignored artifacts/elevation-diagnostic-2026-09-15へ9 artifacts/論理18269 bytes、最終manifest17286 bytes/SHA256 **9e4c0c8fb6f45208820c590fc5d7141fd03b62de45512dd3e3be45e26ef1bf89** を保存した（manifest自身はartifact集計外）。

UTC02:34:43 RAM10575945728/C130994171904/D203548798976 bytes→02:38:48 RAM10558652416/C130972598272/D203548774400 bytes。D空き約189.57GiB、他project/process操作なし。短い観測から長期リーク不在は主張しない。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00。Windows Update engineering緩和/正式pin不変。既存Python3.14.0/.NETのみ、新runtime/service/task/VMなし。本流889cfc3/clean、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保全しcommit除外。

次は新規rootと準備記録の場所を固定し、実機確認済みの観測処理を準備launcherへ適用する。専用環境の許可は継続。準備成功・P/U起動・IPC・namespace全期間・全publisher・frozen/marker契約・B2/S4受入は未完了。全許可flags=false、acceptance_status=not_completed。
