$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
Import-Module (Join-Path $PSScriptRoot '../tools/windows_process_observation.psm1') -ErrorAction Stop
$tokens = $null
$errors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot '../tools/windows_shell_launch_diagnostic.ps1'), [ref]$tokens, [ref]$errors)
if ($errors.Count -ne 0) { throw 'Parse failed.' }
$function = @($ast.FindAll({ param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'New-ShellDiagnosticStartInfo' }, $false))
if ($function.Count -ne 1) { throw 'Expected one pure builder.' }
. ([scriptblock]::Create($function[0].Extent.Text))
$ordinary = New-ShellDiagnosticStartInfo -Elevate $false
$elevated = New-ShellDiagnosticStartInfo -Elevate $true
if ($ordinary.Arguments -cne $elevated.Arguments -or $ordinary.Arguments.Length -ne 15331) { throw 'Argument comparison not controlled.' }
if (-not $ordinary.UseShellExecute -or -not $elevated.UseShellExecute -or $ordinary.Verb -ne '' -or $elevated.Verb -ne 'runas' -or $elevated.WindowStyle -ne [Diagnostics.ProcessWindowStyle]::Hidden) { throw 'Shell settings differ.' }
# Validate the actual .NET failure-to-ErrorRecord path without starting a child or UAC.
$missing = Join-Path ([IO.Path]::GetTempPath()) ('banto-missing-executable-' + [Guid]::NewGuid().ToString('N') + '.exe')
if ([IO.File]::Exists($missing) -or [IO.Directory]::Exists($missing)) { throw 'Missing executable control unexpectedly exists.' }
$info = [Diagnostics.ProcessStartInfo]::new($missing)
$info.UseShellExecute = $false
$actual = Invoke-ElevationDiagnosticObservation -ExpectedExitCode 40 -Launch {
    [Diagnostics.Process]::Start($info)
} -ReadId { throw 'No process expected.' } -CaptureHandle { throw 'No process expected.' } -Wait { throw 'No process expected.' } -ReadExit { throw 'No process expected.' } -Dispose { throw 'No process expected.' }
if ($actual.launch_returned -or $null -ne $actual.process_id -or $actual.failure.stage -ne 'request-launch') { throw 'Missing-file failure continued.' }
if (2 -notin @($actual.failure.exception_chain | ForEach-Object { $_.native_error })) { throw 'Native file-not-found code lost.' }
[Console]::WriteLine('RESULT 3 shell diagnostic cases passed; real missing-executable error 2 retained; no child or UAC')
