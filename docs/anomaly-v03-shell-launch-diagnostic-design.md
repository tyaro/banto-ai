# S4-B2 起動APIと長い引数の独立診断

2026-09-15。短いEncodedCommand診断は管理者起動成功、準備用15331文字のCommandは約123秒後にrequest-launch失敗で、PID/内側native errorが得られなかった。起動原因は未確定。両準備rootはunknownで閉鎖し再訪しない。

[PowerShell公開実装](https://github.com/PowerShell/PowerShell/blob/master/src/Microsoft.PowerShell.Commands.Management/commands/management/Process.cs)のStartWithShellExecuteは、Win32ExceptionをMessageのみのInvalidOperationExceptionへ置き換える。このPCのWindows PowerShellについても、実際のManagement assemblyの同名methodのILを実行せず読取り、Win32Exception catchとInvalidOperationException(string) constructorを確認した。例外chainの深掘りだけで番号が戻るという前提が不足していた。これは**エラー番号欠落の理由**であり、準備起動が失敗した理由そのものではない。

[新診断](../tools/windows_shell_launch_diagnostic.ps1)では[Process.Start(ProcessStartInfo)](https://learn.microsoft.com/en-us/dotnet/api/system.diagnostics.process.start?view=netframework-4.8.1)を通常側から直接呼ぶ。UseShellExecute=true、RunだけVerb=runas、Hidden/System32/NoProfile/NonInteractive、固定U SID・admin自己照会を維持する。Windowsの通常の管理者確認はそのまま必要で、権限確認を迂回しない。

引数は準備と同じASCII Command形式/15331文字へ固定し、不足長は無害なcommentで埋める。DLL bytes・準備Entry・account/root/file操作を含まない。ControlとRunで引数/hashは同一、違いはrunasの指定と期待codeだけ。paddingによる比較は引数長/形状の限定controlであり、準備の実内容・AMSI・各種policyまで同等とは主張しない。2003年のShellExecute長制限資料だけから現在のWindowsの失敗原因を確定しない。

既定Verifyは引数/hash/設定を表示するだけ。Control/Runは新規artifacts/shell-launch-diagnostic-2026-09-15にそれぞれCREATE_NEW/flush済みguardでmax1を記録する。旧診断/旧準備guardは再利用しない。共有observerで15秒の終了待機と一次/解放例外の分離を行う。UAC待ちはこの15秒に含めず、timeoutでは終了不明として記録する。昇格processの強制終了や再起動をしない。

[確認](../tests/ShellLaunchDiagnostic.Tests.ps1)はbuilderの引数同一性とShell設定、存在しない一意なexeへの非昇格Process.Startで実際のWin32 code2を保持できることを検証する。子process/UAC/account/root操作はない。34件のC#準備試験と共有observer13ケースは前工程から不変。

Controlで通常終了を確認し、管理者確認画面の表示状況をユーザーに確認してからRunを新規max1で行う。先の質問の未回答を承認や「画面なし」と解釈しない。環境方式の再承認を要求するものではない。準備の再実行や次rootの作成には進まない。
成功しても旧失敗原因の遡及確定、権限隔離/正式B2-S4完了にはしない。全許可flags=false、acceptance_status=not_completed。Python3.14.0/既存.NET、Windows Update engineering緩和/正式pin不変を維持する。
