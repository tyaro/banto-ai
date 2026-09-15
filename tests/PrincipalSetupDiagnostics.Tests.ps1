# Extract only the pure diagnostic function: do not execute the launcher or native entry.
$ErrorActionPreference = 'Stop'
$source = Join-Path $PSScriptRoot '../tools/windows_principal_setup.ps1'
$tokens = $null
$errors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile($source, [ref]$tokens, [ref]$errors)
if ($errors.Count -ne 0) { throw 'Launcher parse failed.' }
$functions = @($ast.FindAll({ param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Get-SetupLaunchFailure' }, $false))
if ($functions.Count -ne 1) { throw 'Expected one pure diagnostic function.' }
. ([scriptblock]::Create($functions[0].Extent.Text))
$native = [ComponentModel.Win32Exception]::new(1223, 'do-not-log-message')
$outer = [InvalidOperationException]::new('do-not-log-outer', $native)
$record = [Management.Automation.ErrorRecord]::new($outer, 'test', [Management.Automation.ErrorCategory]::OperationStopped, $null)
$actual = Get-SetupLaunchFailure -Failure $record -Stage 'request-uac' -OwnedProcessId $null
if ($actual.exception_chain.Count -ne 2 -or $actual.exception_chain[1].native_error -ne 1223) { throw 'Nested native error lost.' }
if ($actual.failure_stage -ne 'request-uac' -or $null -ne $actual.process_id) { throw 'Launch stage/unknown PID lost.' }
if (($actual | ConvertTo-Json -Depth 8).Contains('do-not-log')) { throw 'Exception message leaked.' }
$nested = $native
for ($i = 0; $i -lt 6; $i++) { $nested = [InvalidOperationException]::new('do-not-log', $nested) }
$record = [Management.Automation.ErrorRecord]::new($nested, 'test', [Management.Automation.ErrorCategory]::OperationStopped, $null)
$actual = Get-SetupLaunchFailure -Failure $record -Stage 'wait-for-exit' -OwnedProcessId 123
if ($actual.exception_chain.Count -ne 4 -or -not $actual.chain_truncated) { throw 'Unbounded exception chain.' }
if ($actual.process_id -ne 123 -or $actual.failure_stage -ne 'wait-for-exit') { throw 'Owned PID/stage lost.' }
if (-not $actual.no_retry -or -not $actual.launch_failed) { throw 'Failure/retry status lost.' }
[Console]::WriteLine('RESULT 6 diagnostic assertions passed; no launcher/native/account/root execution')

$decoders = @($ast.FindAll({ param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Get-SetupExitDetails' }, $false))
if ($decoders.Count -ne 1) { throw 'Expected one pure exit decoder.' }
. ([scriptblock]::Create($decoders[0].Extent.Text))
$legacy = Get-SetupExitDetails -Code 393215
if ($legacy.phase_number -ne 5 -or $legacy.native_detail -ne 65535 -or $null -ne $legacy.inspection_failure) { throw 'Legacy unknown code changed.' }
$tagged = Get-SetupExitDetails -Code (0x20000000 -bor (5 -shl 16) -bor (1 -shl 13) -bor (10 -shl 8) -bor 40)
if ($tagged.phase_number -ne 5 -or $null -ne $tagged.native_detail -or $tagged.inspection_failure.step -ne 'exact-policy-comparison' -or $tagged.inspection_failure.exception_kind -ne 1 -or $tagged.inspection_failure.policy_difference_mask -ne 40 -or -not $tagged.inspection_failure.policy_difference_available) { throw 'Inspection decode failed.' }
$released = Get-SetupExitDetails -Code (0x60000000 -bor (5 -shl 16) -bor (2 -shl 13) -bor (9 -shl 8))
if (-not $released.release_failed -or $released.inspection_failure.policy_difference_available) { throw 'Release/partial comparison lost.' }
$native = Get-SetupExitDetails -Code ((5 -shl 16) -bor 5)
if ($native.native_detail -ne 5 -or $null -ne $native.inspection_failure) { throw 'Native code changed.' }
$invalid = Get-SetupExitDetails -Code (0x20000000 -bor (4 -shl 16) -bor (31 -shl 8))
if ($invalid.inspection_failure.encoding_valid -or $invalid.inspection_failure.policy_difference_available) { throw 'Invalid diagnostic accepted.' }
$success = Get-SetupExitDetails -Code 0
if ($null -ne $success.phase_number -or $null -ne $success.inspection_failure -or $success.release_failed) { throw 'Success changed.' }
[Console]::WriteLine('RESULT 6 exit decoding assertions passed; no launcher/native/account/root execution')
