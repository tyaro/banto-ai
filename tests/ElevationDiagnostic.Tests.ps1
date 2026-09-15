# Import observation functions and extract the writer AST only; no process or UAC is started.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
Import-Module (Join-Path $PSScriptRoot '../tools/windows_process_observation.psm1') -ErrorAction Stop
$source = Join-Path $PSScriptRoot '../tools/windows_elevation_diagnostic.ps1'
$tokens = $null
$errors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile($source, [ref]$tokens, [ref]$errors)
if ($errors.Count -ne 0) { throw 'Diagnostic parse failed.' }
foreach ($name in @('Write-ElevationDiagnosticJson')) {
    $definitions = @($ast.FindAll({ param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name }, $false))
    if ($definitions.Count -ne 1) { throw 'Expected exactly one function.' }
    . ([scriptblock]::Create($definitions[0].Extent.Text))
}
function Assert-Probe { param([bool]$Condition, [string]$Message) if (-not $Condition) { throw $Message } }
$cases = @('success', 'wrong-code', 'null-code', 'launch-error', 'id-error', 'handle-error', 'wait-error', 'timeout', 'exit-error', 'dispose-error', 'double-error')
foreach ($case in $cases) {
    $calls = [Collections.Generic.List[string]]::new()
    $actual = Invoke-ElevationDiagnosticObservation -ExpectedExitCode 40 -Launch {
        $calls.Add('launch')
        if ($case -eq 'launch-error') { throw [InvalidOperationException]::new('omit-message', [ComponentModel.Win32Exception]::new(1223)) }
        return [pscustomobject]@{ Fake = $true }
    } -ReadId {
        param($process) $calls.Add('id')
        if ($case -eq 'id-error') { throw 'omit-message' }
        return 123
    } -CaptureHandle {
        param($process) $calls.Add('handle')
        if ($case -eq 'handle-error') { throw 'omit-message' }
    } -Wait {
        param($process) $calls.Add('wait')
        if ($case -in @('wait-error', 'double-error')) { throw 'omit-message' }
        return ($case -ne 'timeout')
    } -ReadExit {
        param($process) $calls.Add('exit')
        if ($case -eq 'exit-error') { throw 'omit-message' }
        if ($case -eq 'null-code') { return $null }
        if ($case -eq 'wrong-code') { return 42 }
        return 40
    } -Dispose {
        param($process) $calls.Add('dispose')
        if ($case -in @('dispose-error', 'double-error')) { throw 'omit-message' }
    }
    Assert-Probe (-not (($actual | ConvertTo-Json -Depth 12).Contains('omit-message'))) "$case leaked message"
    Assert-Probe ($actual.no_retry -and -not $actual.Contains('os_configuration_changed')) "$case scope flags"
    if ($case -eq 'launch-error') {
        Assert-Probe (($calls -join ',') -eq 'launch') 'Launch failure continued'
        Assert-Probe ($null -eq $actual.process_id -and $actual.failure.stage -eq 'request-launch') 'Unknown launch lost'
        Assert-Probe (1223 -in @($actual.failure.exception_chain | ForEach-Object { $_.native_error })) 'Native error lost'
    } else {
        Assert-Probe (@($calls | Where-Object { $_ -eq 'dispose' }).Count -eq 1) "$case dispose count"
        Assert-Probe ($actual.launch_returned) "$case launch return lost"
    }
    switch ($case) {
        'success' { Assert-Probe ($actual.expected_probe_result -and $actual.exit_code -eq 40 -and $actual.process_object_disposed) 'Success lost' }
        'wrong-code' { Assert-Probe ($actual.exit_observed -and -not $actual.expected_probe_result -and $actual.exit_code -eq 42) 'Wrong identity accepted' }
        'null-code' { Assert-Probe (-not $actual.exit_observed -and $actual.failure.stage -eq 'read-exit-code') 'Null code accepted' }
        'id-error' { Assert-Probe ($null -eq $actual.process_id -and ($calls -join ',') -eq 'launch,id,dispose') 'ID failure continued' }
        'handle-error' { Assert-Probe ($actual.process_id -eq 123 -and -not $actual.process_handle_captured -and ($calls -join ',') -eq 'launch,id,handle,dispose') 'Handle failure continued' }
        'wait-error' { Assert-Probe ($actual.failure.stage -eq 'wait-for-exit' -and -not $calls.Contains('exit')) 'Wait error lost' }
        'timeout' { Assert-Probe ($actual.status -eq 'exit_unconfirmed_timeout' -and -not $actual.exit_observed -and -not $calls.Contains('exit')) 'Timeout read exit' }
        'exit-error' { Assert-Probe ($actual.failure.stage -eq 'read-exit-code' -and -not $actual.exit_observed) 'Exit error lost' }
        'dispose-error' { Assert-Probe ($actual.exit_observed -and $null -eq $actual.failure -and $null -ne $actual.dispose_failure) 'Dispose masked observation' }
        'double-error' { Assert-Probe ($actual.failure.stage -eq 'wait-for-exit' -and $actual.dispose_failure.stage -eq 'dispose-process-object') 'Secondary failure masked first' }
    }
}
$nested = [ComponentModel.Win32Exception]::new(5)
for ($index = 0; $index -lt 6; $index++) { $nested = [InvalidOperationException]::new('omit-message', $nested) }
$record = [Management.Automation.ErrorRecord]::new($nested, 'test', [Management.Automation.ErrorCategory]::OperationStopped, $null)
$actual = Get-ElevationDiagnosticFailure -Failure $record -Stage 'test'
Assert-Probe ($actual.exception_chain.Count -eq 4 -and $actual.chain_truncated) 'Exception chain not bounded'
$guard = Join-Path ([IO.Path]::GetTempPath()) ('banto-elevation-guard-' + [Guid]::NewGuid().ToString('N') + '.json')
try {
    Write-ElevationDiagnosticJson -Path $guard -Value @{ attempt = 1 }
    $before = [IO.File]::ReadAllText($guard)
    $rejected = $false
    try { Write-ElevationDiagnosticJson -Path $guard -Value @{ attempt = 2 } } catch [IO.IOException] { $rejected = $true }
    Assert-Probe ($rejected -and [IO.File]::ReadAllText($guard) -eq $before) 'Attempt guard overwritten'
} finally { if ([IO.File]::Exists($guard)) { [IO.File]::Delete($guard) } }
[Console]::WriteLine('RESULT 13 diagnostic cases passed; no child process, UAC, account or protected-root operations')
