# S4-B2 新規principal準備bの起動停止

2026-09-15。[昇格診断成功](anomaly-multiseed-v0.3-s4-b2-elevation-diagnostic-2026-09-15.md)後、承認済み準備を新規rootで一度だけ実行した。実装 **4bdeaeda871ac5d65b27ae1b45f564f609b89b6d**、[準備b仕様](../anomaly-v03-principal-setup-b-design.md)。

新rootはC:\ProgramData\BantoAI-S4B2-principal-20260915b、accountはBantoS4Publisher。UTC02:57:08にSAM status2221、root attributes0xffffffff/Win32 error2を確認した。旧rootは一切確認していない。
C#変更は新root名だけ。34件pass、共有observer13ケースpass、独立所見0、repository safety/diff-check pass。通常load-only PID37216/exit0、15331文字、account/root entry未実行。
新build-01 DLL SHA256 **4ea7c99167a71c9ba6e26f2d6d3a74ad16226d8209dc3535d19660696440a88a**。

UTC02:58:09.5677728Zに新規max1を開始、03:00:12.7311008Zにrequest-launch失敗で終了。起動要求123157ms/全体123158ms、Start-Processは返却せずPID/Handle/exitなし。System.InvalidOperationException/HRESULT -2146233079、inner exceptionなし。待機45秒へは進んでいない。
UAC取消・画面未表示・policyや引数の問題などの原因は未確定。短い自己照会が成功したことを実際の準備commandの成功保証にしない。
UTC03:01:00の対象SAM読取でstatus2221/解放error0、account不存在を確認。新rootはunknownとし、存在確認/再open/列挙/hash/copy/deleteしていない。helper開始/終了はunknown、launcher sessionのみ終了確認。旧準備と今回のguardは両方閉鎖し、設定作成の再実行・自動削除は行わない。

input16876 bytes/SHA256 **801755b7393b0d282b519addfa88838aab59a1841cc55e53f0e6fedfffaa3018**、83 sourceをGit/raw照合。前回81 sourceのうち77不変、4変更/2追加。前回診断manifestと9 artifacts不変。
ignored artifacts/principal-setup-b-2026-09-15へ11 artifacts/論理61089 bytes、最終manifest19470 bytes/SHA256 **3813fb07fcb1ece244c094cacfdcf17d89393d1984865e9516f7da91258e46ab**（最終manifestは集計外）。
RAM10678808576/C131058606080/D202743431168 bytes→RAM10330025984/C130926686208/D202743431168 bytes。D空き約188.82GiB、build26200.9445/boot2026-09-09T10:43:08.5000000+09:00。Windows Update engineering緩和/正式pin不変。他project/process操作なし。
本流889cfc3/clean、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保全・commit除外。新runtime/service/task/VMなし。

停止後に、このPCのStartWithShellExecuteのILとPowerShell公式実装から、元Win32ExceptionがMessageだけのInvalidOperationExceptionへ置換されることを確認した。番号を失う理由は説明できるが、実際の起動失敗理由は説明できない。次は[設定を変更しない直接Process.Start診断](../anomaly-v03-shell-launch-diagnostic-design.md)。管理者確認画面の表示状況をユーザーへ質問中。方式の再承認を求める質問ではない。
環境準備/P-U起動/IPC/namespace全期間/全publisher/frozen/marker/正式B2-S4は未完了。全許可flags=false、acceptance_status=not_completed。
