# S4-B2 管理者起動確認後の新規principal準備

2026-09-15。[独立の昇格診断](results/anomaly-multiseed-v0.3-s4-b2-elevation-diagnostic-2026-09-15.md)で通常control/RunAsの開始・終了code・解放を確認した後の新規工程。専用標準accountと保護rootの準備は承認済みで、承認の再取得を要しない。

対象rootを **C:\ProgramData\BantoAI-S4B2-principal-20260915b**、通常側記録を **artifacts/principal-setup-b-2026-09-15** へ固定する。前回の末尾bなしroot、旧launch-attempt、旧fixtureは閉鎖状態のまま、存在確認/再open/列挙/hash/copy/deleteを行わない。旧guardを消去・上書きしない。新しい名前は失敗後に再使用せず、今回もmax1とする。

account名はBantoS4Publisherを維持する。既存accountの再使用・reset・enable・削除はしない。新root/同名accountの未存在をC# helperが祖先保持後に検査し、存在・アクセス拒否・結果不明なら作成前に停止する。前回のSAM不存在観測を今回の未存在保証に流用しない。今回のrootは作成前後とも前回rootと区別する。

権限・資格情報・disabled状態・作成/解放順・資源watchdogは[既存準備仕様](anomaly-v03-principal-setup-design.md)を継承し、C#変更は固定root名だけ。既存.NET compilerで新buildを通常compileし、34件の故障試験、通常権限のload-only確認、独立レビュー、savepoint、公開DLL SHA固定の後にRunAsを一度だけ実行する。Pをログオンさせず、rootはP/U read-onlyの準備状態。

管理者起動の観測関数を[共有module](../tools/windows_process_observation.psm1)へ移し、[診断](../tools/windows_elevation_diagnostic.ps1)と[準備launcher](../tools/windows_principal_setup.ps1)から利用する。moduleのimportはOS変更やprocess起動を行わない。通常側だけでimportし、昇格側の固定有界inline DLL loaderは従来どおり。診断の旧guardを使った実機再確認はしない。

共有関数は起動返却・PID・Handle・終了観測/code・一次/解放例外を分離する。準備の待機は45秒、C#内側watchdog40秒、private256MiB/working384MiB、空きRAM/C各2GiBを維持する。起動要求時間はUACを含み別記録。exit0と観測/解放例外なしを揃えてsetup_exit_success=trueとする。未知code・timeoutを成功としない。共有関数からOS設定未変更を推定せず、準備launcherはunknown-until-success-verificationを記録する。

成功してprocess終了を確認した場合だけ、今回の永続準備rootの既知bootstrap-result.jsonと対象accountを通常側で読取確認する。receiptはprepared-precloseであり、単独では終了成功の証拠ではない。失敗時は今回rootを再訪しない。例外/timeout時もobserverから昇格processをkillせず、retry/補償/自動削除なし。

この工程はaccount/root準備だけ。Pのactivation/reset/logon/disable、protected code/process/thread/token/IPC、独立P-U干渉、namespace共通保持期間、全publisher/frozen/marker/正式B2/S4受入は残件。成功しても全許可flags=false、acceptance_status=not_completedを維持する。既存Python3.14.0を利用し、新runtime/service/task/VMを追加しない。Windows Update engineering緩和と正式pin不変、他project無操作を維持し、resourceとセーブポイントを記録する。
