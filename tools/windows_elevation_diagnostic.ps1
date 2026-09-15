param([ValidateSet('Control', 'Run')][string]$Mode = 'Control')

# A separate, read-only identity probe. Never calls the principal setup helper.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Get-ElevationDiagnosticFailure {
    param([Management.Automation.ErrorRecord]$Failure, [string]$Stage)
    $chain = @()
    $current = $Failure.Exception
    for ($index = 0; $index -lt 4 -and $null -ne $current; $index++) {
        $native = $null
        if ($current -is [ComponentModel.Win32Exception]) { $native = $current.NativeErrorCode }
        $chain += [ordered]@{
            exception_type = $current.GetType().FullName
            hresult = $current.HResult
            native_error = $native
        }
        $current = $current.InnerException
    }
    return [ordered]@{ stage = $Stage; exception_chain = $chain; chain_truncated = ($null -ne $current) }
}

function Invoke-ElevationDiagnosticObservation {
    param(
        [scriptblock]$Launch, [scriptblock]$ReadId, [scriptblock]$CaptureHandle,
        [scriptblock]$Wait, [scriptblock]$ReadExit, [scriptblock]$Dispose,
        [int]$ExpectedExitCode
    )
    $result = [ordered]@{
        started_utc = [DateTime]::UtcNow.ToString('o')
        launch_returned = $false; process_id = $null; process_handle_captured = $false
        exit_observed = $false; exit_code = $null; expected_exit_code = $ExpectedExitCode
        expected_probe_result = $false; status = 'observation_failed'
        launch_elapsed_ms = $null; wait_elapsed_ms = $null; total_elapsed_ms = $null
        failure = $null; process_object_disposed = $false; dispose_failure = $null
        no_retry = $true; os_configuration_changed = $false
    }
    $watch = [Diagnostics.Stopwatch]::StartNew()
    $process = $null
    $stage = 'request-launch'
    $waitWatch = $null
    try {
        $process = & $Launch
        $result.launch_elapsed_ms = $watch.ElapsedMilliseconds
        $result.launch_returned = $true
        $stage = 'capture-process-id'
        $ownedId = & $ReadId $process
        if ($null -eq $ownedId -or $ownedId -isnot [int] -or $ownedId -le 0) { throw 'Invalid process id.' }
        $result.process_id = $ownedId
        $stage = 'capture-process-handle'
        & $CaptureHandle $process | Out-Null
        $result.process_handle_captured = $true
        $stage = 'wait-for-exit'
        $waitWatch = [Diagnostics.Stopwatch]::StartNew()
        $exited = & $Wait $process
        $result.wait_elapsed_ms = $waitWatch.ElapsedMilliseconds
        if ($exited -isnot [bool]) { throw 'Invalid exit observation.' }
        if (-not $exited) {
            $result.status = 'exit_unconfirmed_timeout'
        } else {
            $stage = 'read-exit-code'
            $code = & $ReadExit $process
            if ($null -eq $code -or $code -isnot [int]) { throw 'Missing or invalid exit code.' }
            $result.exit_observed = $true
            $result.exit_code = $code
            $result.expected_probe_result = ($code -eq $ExpectedExitCode)
            $result.status = 'exited'
        }
    } catch {
        $result.failure = Get-ElevationDiagnosticFailure -Failure $_ -Stage $stage
    } finally {
        if ($null -eq $result.launch_elapsed_ms) { $result.launch_elapsed_ms = $watch.ElapsedMilliseconds }
        if ($null -ne $waitWatch -and $null -eq $result.wait_elapsed_ms) {
            $result.wait_elapsed_ms = $waitWatch.ElapsedMilliseconds
        }
        if ($null -ne $process) {
            try {
                & $Dispose $process | Out-Null
                $result.process_object_disposed = $true
            } catch {
                $result.dispose_failure = Get-ElevationDiagnosticFailure -Failure $_ -Stage 'dispose-process-object'
            }
        }
        $result.total_elapsed_ms = $watch.ElapsedMilliseconds
        $result.completed_utc = [DateTime]::UtcNow.ToString('o')
    }
    return $result
}

function Write-ElevationDiagnosticJson {
    param([string]$Path, [object]$Value)
    $bytes = [Text.Encoding]::UTF8.GetBytes(($Value | ConvertTo-Json -Depth 12) + "`n")
    $stream = [IO.File]::Open($Path, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
    try { $stream.Write($bytes, 0, $bytes.Length); $stream.Flush($true) } finally { $stream.Dispose() }
}

$base = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../artifacts/elevation-diagnostic-2026-09-15'))
$systemDirectory = [Environment]::SystemDirectory
$executable = Join-Path $systemDirectory 'WindowsPowerShell/v1.0/powershell.exe'
if (-not [Environment]::Is64BitProcess -or -not [IO.File]::Exists($executable)) { throw 'Expected existing Windows x64 runtime.' }
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
try {
    if ($identity.User.Value -ne 'S-1-5-21-2169670816-255940906-2713565042-1001') { throw 'Unexpected observer identity.' }
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Observer must be unelevated.' }
} finally { $identity.Dispose() }

# Public fixed command: queries only its own identity and exits. No script/module/DLL paths.
$probe = @'
$ErrorActionPreference = 'Stop'
$code = 43
try {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    try {
        if ($identity.User.Value -ne 'S-1-5-21-2169670816-255940906-2713565042-1001') { $code = 42 }
        elseif (([Security.Principal.WindowsPrincipal]::new($identity)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { $code = 40 }
        else { $code = 41 }
    } finally { $identity.Dispose() }
} catch { $code = 43 }
exit $code
'@
$encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($probe))
$arguments = '-NoLogo -NoProfile -NonInteractive -EncodedCommand ' + $encoded
$sha = [Security.Cryptography.SHA256]::Create()
try { $probeHash = ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($probe)))).Replace('-', '').ToLowerInvariant() }
finally { $sha.Dispose() }
[IO.Directory]::CreateDirectory($base) | Out-Null
$prefix = $Mode.ToLowerInvariant()
$attempt = [ordered]@{
    utc = [DateTime]::UtcNow.ToString('o'); mode = $Mode; executable = $executable
    probe_sha256 = $probeHash; command_characters = $arguments.Length
    observer_wait_ms = 15000; uac_wait_in_observer_bound = $false
    os_configuration_changed = $false; maximum_attempts = 1; old_setup_invoked = $false
}
# Persistent per-mode max1 guard. Existing or partial records always prevent another launch.
Write-ElevationDiagnosticJson -Path (Join-Path $base ($prefix + '-attempt.json')) -Value $attempt
$expected = 41
if ($Mode -eq 'Run') { $expected = 40 }
$result = Invoke-ElevationDiagnosticObservation -ExpectedExitCode $expected -Launch {
    $options = @{
        FilePath = $executable; ArgumentList = $arguments; WorkingDirectory = $systemDirectory
        WindowStyle = 'Hidden'; PassThru = $true; ErrorAction = 'Stop'
    }
    if ($Mode -eq 'Run') { $options.Verb = 'RunAs' }
    Start-Process @options
} -ReadId { param($process) $process.Id } -CaptureHandle {
    param($process)
    if ($process.Handle -eq [IntPtr]::Zero) { throw 'Missing process handle.' }
} -Wait { param($process) $process.WaitForExit(15000) } -ReadExit {
    param($process) $process.ExitCode
} -Dispose { param($process) $process.Dispose() }
Write-ElevationDiagnosticJson -Path (Join-Path $base ($prefix + '-result.json')) -Value $result
$result | ConvertTo-Json -Depth 12
if (-not $result.expected_probe_result -or $null -ne $result.failure -or $null -ne $result.dispose_failure) { exit 1 }
