# S4-B2 管理者起動の独立診断

2026-09-15。容量整理から権限分離の作業へ復帰する工程。専用principal準備の許可は継続し、OS設定を変更しない短い診断を新規max1で実行する。
[前回準備](results/anomaly-multiseed-v0.3-s4-b2-principal-setup-2026-09-15.md)は起動原因不明で閉鎖済み。旧attemptや未知rootへの存在確認・再open・列挙・hash・copy・deleteを行わない。

[診断](../tools/windows_elevation_diagnostic.ps1)は既存System32 WindowsPowerShellをHidden/NoProfile/NonInteractiveで起動し、固定公開commandから自processのWindowsIdentity SIDと管理者group有効性だけを照会して直ちに終了する。account/root API、準備DLL、Entry.Run、P logon、publisherを呼ばず、昇格側でfileを読み書きしない。観測codeは40=固定U SIDでadmin、41=固定U SIDで非admin、42=別SID、43=照会/解放例外。通常controlは41、RunAs診断は40を期待する。

通常observerも固定U SIDの非昇格に限定する。通常権限のControl、管理者確認付きRunをそれぞれ一度だけ実行し、ignored artifacts/elevation-diagnostic-2026-09-15へmode別CREATE_NEW/flush済みattemptを残してから起動する。既存・途中のattemptがあれば停止し、上書き/guard解除/自動再試行を行わない。結果は別のCREATE_NEW fileへ保存する。途中停止で結果がなければ成功としない。

起動要求、PID取得、process Handle確保、終了待ち、終了code取得、Process object解放を分けて記録する。Handleは待機前に確保する。null codeを0へ変換せず観測失敗とする。最大4段のexception type/HRESULT/native errorとstageだけを保存し、Message/command textをexceptionログへ入れない。解放例外は最初の失敗や既に観測した終了codeを上書きしない。

起動要求時間はUAC待ちを含めて別記録。Start-Process返却後のWaitForExitは15秒。UAC/OS起動やAPI自体の停止まで含めた絶対時間保証はない。timeoutでは終了未確認を保存し、通常observerから昇格processの強制終了や自動再起動を試みない。Process.Disposeは観測handleの解放でありprocess終了ではない。短いprobeによる工程で、新規常駐・runtime・service・task・VMは追加しない。

[故障試験](../tests/ElevationDiagnostic.Tests.ps1)はASTから関数だけを取り出し、fake processで起動・PID・handle・待機・終了code・解放の故障、timeout、異なるSID code、例外深度、CREATE_NEW guardを確認する。テストからUACや準備entryを起動しない。独立レビュー・savepoint後に通常control、続いて診断Runへ進む。

この診断成功は、今回の固定commandの終了code観測を確認するだけ。前回の失敗原因を遡及確定せず、account/root準備成功、起動経路全体の認証、権限隔離やB2/S4受入を意味しない。全許可flags=false、acceptance_status=not_completed。成功後は旧rootを避けた新規対象と保全条件を仕様に固定してから準備工程へ進む。Windows Updateによるengineering条件緩和を継続し、build/boot/resourceを記録する。
