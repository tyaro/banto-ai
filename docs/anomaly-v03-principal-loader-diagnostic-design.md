# S4-B2 準備DLLの管理者load-only診断

2026-09-15。[直接Shell自己照会](results/anomaly-multiseed-v0.3-s4-b2-shell-launch-diagnostic-2026-09-15.md)の通常/管理者成功を受け、保存済み公開DLLの展開/hash/Assembly.Loadまでを調べる。アカウント作成を含む準備entryは呼ばない。

[診断](../tools/windows_principal_loader_diagnostic.ps1)は固定した公開code artifacts/principal-setup-b-2026-09-15/PrincipalSetup-build-01.dllだけを通常側で読む。SHA256は4ea7c99167a71c9ba6e26f2d6d3a74ad16226d8209dc3535d19660696440a88a。これは旧native fixtureや保護rootではない。旧launcher/guardを呼ばず、新規artifacts/principal-loader-diagnostic-2026-09-15へ記録する。

通常側はFileStreamから長さ1〜262144を割当て前に検査し、exact read/EOF、固定hashを確認した同じbytesをDeflateする。ASCII Commandは固定templateで生成し、29000文字以内のloaderに公開圧縮bytes/hashを埋め込む。B側はuser書換え可能なDLL pathを読み直さない。既存System32 WindowsPowerShell/NoProfile/NonInteractive/Hidden、直接Process.Start/UseShellExecute=true、RunだけrunasでWindowsの管理者確認を行う。

両modeのcommandは同一。B側は最大262145-byte bufferで展開し、0/262144超なら81、hash不一致82、その他例外83で終了。同じ検証済みbyte配列のAssembly.Loadだけを行い、Entry.Run/NativeBackend/workerを呼ばず、準備DLLのtypeをinstantiateしない。続いて固定U SIDと自processのadmin状態を照会し40=admin/41=非admin/42=別SIDを返す。通常Controlは41、Runは40を期待する。固定hashの既知C# buildを対象とし、任意のassemblyを安全に読み込めるとはしない。

Verifyは構築metadataを表示するだけ。Control/RunはそれぞれCREATE_NEW/flush済みguardによるmax1。共有observerでPID/Handle/15秒の終了待機/code/解放と一次・二次例外を分けて保存する。UAC/起動要求は15秒上限に含めない。timeoutは終了不明とし、昇格processの強制終了、retry、補償操作を行わない。読み込みだけの診断にC#準備Entry内のwatchdogを適用したとしない。

[確認](../tests/PrincipalLoaderDiagnostic.Tests.ps1)は関数ASTだけを取り出し、空/上限超stream、exact bytes、不一致hash、command構文/準備entry不在、同byte配列のLoad境界、圧縮往復、単回guardを確認する。テストはAssembly.Load・子process・UACを実行しない。独立レビュー・savepointの後に通常Control、管理者Runへ一度ずつ進む。既存C#34件/共有observer13ケースはsource不変なら反復しない。

成功は固定DLLの読み込みと自己照会/終了観測の確認に限定する。以前の準備失敗原因、account/root準備、P/U起動や権限隔離の証明ではない。末尾bなし/ありの旧保護rootはunknownのまま再訪せず、次rootの作成へ直行しない。全許可flags=false、acceptance_status=not_completed。空きRAM/C各2GiB以上を実行前に確認、build/bootを記録しWindows Update engineering緩和/正式pin不変を維持する。既存Python3.14.0/.NETだけを用い、service/task/VM/runtimeを追加しない。
