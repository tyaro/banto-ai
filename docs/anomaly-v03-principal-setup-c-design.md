# S4-B2 直接Shell起動による新規principal準備c

2026-09-15。[公開DLLの管理者load-only成功](results/anomaly-multiseed-v0.3-s4-b2-principal-loader-diagnostic-2026-09-15.md)を保存した後の、承認済み環境準備。従来の失敗原因は未確定であり、成功と読み替えない。

新rootを **C:\ProgramData\BantoAI-S4B2-principal-20260915c**、記録先を **artifacts/principal-setup-c-2026-09-15** に固定する。末尾なし/bの旧rootはunknown・閉鎖のまま存在確認/再open/列挙/hash/copy/deleteしない。旧attemptを消去・再利用せず、cもmax1で失敗後は再使用しない。
account名BantoS4Publisherを維持する。通常側で事前に対象SAMと新rootの不存在を確認し、helperも祖先保持後に再確認する。既存accountの再利用・reset・enable・削除や、既存rootの変更は行わない。

[準備launcher](../tools/windows_principal_setup.ps1)を直接Process.Start(ProcessStartInfo)/UseShellExecute=true/runas/Hidden/System32へ変更する。Windowsの管理者確認を維持し、cmdletによるWin32 errorのMessage-only変換を避ける。共有observerと終了code/一次・解放例外の成功条件、固定hashの有界inline loaderは変更しない。
C#変更は固定root名だけ。[準備仕様](anomaly-v03-principal-setup-design.md)のlinked U token/祖先保持・権限preflight、初期からdisabledの標準account、Users所属、BA所有/保護DACL/medium label・U/P readonly、B内unmanaged secret、失敗後のretry/補償なしを維持する。

新しいroot定数で通常権限compile、C#34件、通常load-only、差分の独立レビュー・savepointとDLL SHA固定を経て新規Runを一度実行する。既存の読取専用診断guardを再実行して確認することはない。C#内側40秒/private256MiB/working384MiB/空きRAM・C各2GiB、外側45秒待機を維持し、UAC待ちは別記録とする。
exit0・終了観測・観測/解放例外なしが揃った場合だけ、今回rootの既知bootstrap-result.jsonと対象SAMを読取確認する。prepared-preclose receipt単体を全終了証拠としない。失敗・timeoutでは新rootへ再訪せず、対象SAMの状態だけを別途確認する。通常側からの昇格process killやaccount/root自動削除はしない。

この準備はPを起動せず、rootもP/U read-only。Pのactivation/reset/logon/disable、protected code/process/thread/token/IPC、独立P-U干渉、namespace全期間、全publisher/frozen/marker/正式B2-S4は残件。成功しても全許可flags=false、acceptance_status=not_completedを維持する。Python3.14.0/既存.NET、Windows Update engineering緩和/正式pin不変、新runtime/service/task/VMなし。
