param([ValidateSet('Verify', 'Control', 'Run')][string]$Mode = 'Verify')
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
Import-Module (Join-Path $PSScriptRoot 'windows_process_observation.psm1') -ErrorAction Stop

function Read-PrincipalDiagnosticBytes {
    param([IO.Stream]$Stream)
    $length = $Stream.Length
    if ($length -le 0 -or $length -gt 262144) { throw 'Assembly size outside bound.' }
    $bytes = [byte[]]::new($length)
    $offset = 0
    while ($offset -lt $length) {
        $read = $Stream.Read($bytes, $offset, $length - $offset)
        if ($read -le 0) { throw 'Incomplete assembly read.' }
        $offset += $read
    }
    if ($Stream.ReadByte() -ne -1) { throw 'Assembly grew beyond bound.' }
    return ,$bytes
}

function New-PrincipalLoaderDiagnosticCommand {
    param([byte[]]$Bytes)
    $expected = '4ea7c99167a71c9ba6e26f2d6d3a74ad16226d8209dc3535d19660696440a88a'
    if ($null -eq $Bytes -or $Bytes.Length -eq 0 -or $Bytes.Length -gt 262144) { throw 'Assembly size outside bound.' }
    $sha = [Security.Cryptography.SHA256]::Create()
    try { $actual = [BitConverter]::ToString($sha.ComputeHash($Bytes)).Replace('-', '').ToLowerInvariant() }
    finally { $sha.Dispose() }
    if ($actual -cne $expected) { throw 'Assembly fingerprint mismatch.' }
    $packed = [IO.MemoryStream]::new()
    try {
        $compressor = [IO.Compression.DeflateStream]::new($packed, [IO.Compression.CompressionLevel]::Optimal, $true)
        try { $compressor.Write($Bytes, 0, $Bytes.Length) } finally { $compressor.Dispose() }
        $payload = [Convert]::ToBase64String($packed.ToArray())
    } finally { $packed.Dispose() }
    # Fixed load-only code: never contains or invokes the preparation entry point.
    $loader = @'
$ErrorActionPreference = 'Stop'
try {
  $env:PSModulePath = 'C:\Windows\System32\WindowsPowerShell\v1.0\Modules'
  $compressed = [Convert]::FromBase64String('__DATA__')
  $inputStream = [IO.MemoryStream]::new($compressed, $false)
  $decoder = [IO.Compression.DeflateStream]::new($inputStream, [IO.Compression.CompressionMode]::Decompress)
  $buffer = [byte[]]::new(262145)
  $count = 0
  while ($count -lt $buffer.Length) {
    $n = $decoder.Read($buffer, $count, $buffer.Length - $count)
    if ($n -eq 0) { break }
    $count += $n
  }
  $decoder.Dispose()
  $inputStream.Dispose()
  if ($count -eq 0 -or $count -gt 262144) { [Environment]::Exit(81) }
  $bytes = [byte[]]::new($count)
  [Buffer]::BlockCopy($buffer, 0, $bytes, 0, $count)
  $sha = [Security.Cryptography.SHA256]::Create()
  $actual = [BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-', '').ToLowerInvariant()
  $sha.Dispose()
  if ($actual -cne '__HASH__') { [Environment]::Exit(82) }
  $assembly = [Reflection.Assembly]::Load($bytes)
  $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  try {
    if ($identity.User.Value -ne 'S-1-5-21-2169670816-255940906-2713565042-1001') { $code = 42 }
    elseif (([Security.Principal.WindowsPrincipal]::new($identity)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { $code = 40 }
    else { $code = 41 }
  } finally { $identity.Dispose() }
  [Environment]::Exit($code)
} catch { [Environment]::Exit(83) }
'@
    $loader = $loader.Replace('__DATA__', $payload).Replace('__HASH__', $expected)
    if ($loader.Contains('"') -or $loader.Length -gt 29000) { throw 'Loader quoting/command bound.' }
    return '-NoProfile -NonInteractive -Command "& { ' + $loader + ' }"'
}

function Write-PrincipalDiagnosticJson {
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
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
# This is saved public program code, not an old fixture or protected-root path.
$library = Join-Path $project 'artifacts/principal-setup-b-2026-09-15/PrincipalSetup-build-01.dll'
$stream = [IO.File]::Open($library, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
try { $bytes = Read-PrincipalDiagnosticBytes -Stream $stream } finally { $stream.Dispose() }
$arguments = New-PrincipalLoaderDiagnosticCommand -Bytes $bytes
$sha = [Security.Cryptography.SHA256]::Create()
try { $commandHash = [BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($arguments))).Replace('-', '').ToLowerInvariant() }
finally { $sha.Dispose() }
$info = [Diagnostics.ProcessStartInfo]::new()
$info.FileName = Join-Path ([Environment]::SystemDirectory) 'WindowsPowerShell/v1.0/powershell.exe'
$info.WorkingDirectory = [Environment]::SystemDirectory
$info.Arguments = $arguments
$info.UseShellExecute = $true
$info.WindowStyle = [Diagnostics.ProcessWindowStyle]::Hidden
if ($Mode -eq 'Run') { $info.Verb = 'runas' }
$attempt = [ordered]@{
    utc = [DateTime]::UtcNow.ToString('o'); mode = $Mode; api = 'System.Diagnostics.Process.Start(ProcessStartInfo)'
    executable = $info.FileName; command_characters = $arguments.Length; command_sha256 = $commandHash
    assembly_sha256 = '4ea7c99167a71c9ba6e26f2d6d3a74ad16226d8209dc3535d19660696440a88a'; assembly_bytes = $bytes.Length
    observer_wait_ms = 15000; uac_wait_in_observer_bound = $false; maximum_attempts = 1
    preparation_entry_called = $false; os_configuration_changed = $false; old_roots_accessed = $false
}
if ($Mode -eq 'Verify') { $attempt | ConvertTo-Json; exit 0 }
$base = Join-Path $project 'artifacts/principal-loader-diagnostic-2026-09-15'
[IO.Directory]::CreateDirectory($base) | Out-Null
$prefix = $Mode.ToLowerInvariant()
Write-PrincipalDiagnosticJson -Path (Join-Path $base ($prefix + '-attempt.json')) -Value $attempt
$expected = 41
if ($Mode -eq 'Run') { $expected = 40 }
$result = Invoke-ElevationDiagnosticObservation -ExpectedExitCode $expected -Launch {
    [Diagnostics.Process]::Start($info)
} -ReadId { param($process) $process.Id } -CaptureHandle {
    param($process) if ($process.Handle -eq [IntPtr]::Zero) { throw 'Missing handle.' }
} -Wait { param($process) $process.WaitForExit(15000) } -ReadExit {
    param($process) $process.ExitCode
} -Dispose { param($process) $process.Dispose() }
$result.preparation_entry_called = $false
$result.os_configuration_changed = $false
Write-PrincipalDiagnosticJson -Path (Join-Path $base ($prefix + '-result.json')) -Value $result
$result | ConvertTo-Json -Depth 12
if (-not $result.expected_probe_result -or $null -ne $result.failure -or $null -ne $result.dispose_failure) { exit 1 }
