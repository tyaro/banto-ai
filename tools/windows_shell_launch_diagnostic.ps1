param([ValidateSet('Verify', 'Control', 'Run')][string]$Mode = 'Verify')
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
Import-Module (Join-Path $PSScriptRoot 'windows_process_observation.psm1') -ErrorAction Stop

function New-ShellDiagnosticStartInfo {
    param([bool]$Elevate)
    # Match the setup's 15331-character -Command shape using inert comment padding.
    # This fixed command has no DLL, setup entry, account, root or file operation.
    $body = @'
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
    $prefix = '-NoProfile -NonInteractive -Command "& { ' + $body + "`n<#"
    $suffix = '#> }"'
    $padding = 15331 - $prefix.Length - $suffix.Length
    if ($padding -lt 0) { throw 'Probe exceeds fixed bound.' }
    $info = [Diagnostics.ProcessStartInfo]::new()
    $info.FileName = Join-Path ([Environment]::SystemDirectory) 'WindowsPowerShell/v1.0/powershell.exe'
    $info.WorkingDirectory = [Environment]::SystemDirectory
    $info.Arguments = $prefix + ('x' * $padding) + $suffix
    $info.UseShellExecute = $true
    $info.WindowStyle = [Diagnostics.ProcessWindowStyle]::Hidden
    if ($Elevate) { $info.Verb = 'runas' }
    return $info
}

function Write-ShellDiagnosticJson {
    param([string]$Path, [object]$Value)
    $bytes = [Text.Encoding]::UTF8.GetBytes(($Value | ConvertTo-Json -Depth 12) + "`n")
    $stream = [IO.File]::Open($Path, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
    try { $stream.Write($bytes, 0, $bytes.Length); $stream.Flush($true) } finally { $stream.Dispose() }
}

if (-not [Environment]::Is64BitProcess) { throw 'Expected x64 observer.' }
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
try {
    if ($identity.User.Value -ne 'S-1-5-21-2169670816-255940906-2713565042-1001') { throw 'Unexpected observer SID.' }
    if (([Security.Principal.WindowsPrincipal]::new($identity)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Expected unelevated observer.' }
} finally { $identity.Dispose() }
$info = New-ShellDiagnosticStartInfo -Elevate ($Mode -eq 'Run')
$sha = [Security.Cryptography.SHA256]::Create()
try { $commandHash = [BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($info.Arguments))).Replace('-', '').ToLowerInvariant() }
finally { $sha.Dispose() }
$attempt = [ordered]@{
    utc = [DateTime]::UtcNow.ToString('o'); mode = $Mode; api = 'System.Diagnostics.Process.Start(ProcessStartInfo)'
    executable = $info.FileName; command_characters = $info.Arguments.Length; command_sha256 = $commandHash
    use_shell_execute = $info.UseShellExecute; verb = $info.Verb; window_style = $info.WindowStyle.ToString()
    observer_wait_ms = 15000; uac_wait_in_observer_bound = $false; os_configuration_changed = $false
    maximum_attempts = 1; setup_or_old_root_access = $false
}
if ($Mode -eq 'Verify') { $attempt | ConvertTo-Json; exit 0 }
$base = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../artifacts/shell-launch-diagnostic-2026-09-15'))
[IO.Directory]::CreateDirectory($base) | Out-Null
$prefix = $Mode.ToLowerInvariant()
Write-ShellDiagnosticJson -Path (Join-Path $base ($prefix + '-attempt.json')) -Value $attempt
$expected = 41
if ($Mode -eq 'Run') { $expected = 40 }
$result = Invoke-ElevationDiagnosticObservation -ExpectedExitCode $expected -Launch {
    # Preserve Win32Exception.NativeErrorCode instead of the cmdlet's message-only replacement.
    [Diagnostics.Process]::Start($info)
} -ReadId { param($process) $process.Id } -CaptureHandle {
    param($process) if ($process.Handle -eq [IntPtr]::Zero) { throw 'Missing handle.' }
} -Wait { param($process) $process.WaitForExit(15000) } -ReadExit {
    param($process) $process.ExitCode
} -Dispose { param($process) $process.Dispose() }
$result.os_configuration_changed = $false
Write-ShellDiagnosticJson -Path (Join-Path $base ($prefix + '-result.json')) -Value $result
$result | ConvertTo-Json -Depth 12
if (-not $result.expected_probe_result -or $null -ne $result.failure -or $null -ne $result.dispose_failure) { exit 1 }
