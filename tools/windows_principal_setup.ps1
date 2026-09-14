# Fixed engineering environment only. Build and tests run without elevation.
[CmdletBinding()]
param(
    [ValidateSet('Build', 'Verify', 'CheckLoader', 'Run')][string]$Mode = 'Verify',
    [ValidatePattern('^build-[0-9]{2}$')][string]$Build = 'build-01',
    [string]$ExpectedAssemblySha256 = ''
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
function Get-SetupLaunchFailure {
    param([System.Management.Automation.ErrorRecord]$Failure, [string]$Stage, [Nullable[int]]$OwnedProcessId)
    $chain = @()
    $current = $Failure.Exception
    for ($index = 0; $index -lt 4 -and $null -ne $current; $index++) {
        $native = $null
        if ($current -is [ComponentModel.Win32Exception]) { $native = $current.NativeErrorCode }
        $chain += [ordered]@{ exception_type = $current.GetType().FullName; hresult = $current.HResult; native_error = $native }
        $current = $current.InnerException
    }
    # Do not log Message/InvocationInfo/command text; they may contain arbitrary input.
    return [ordered]@{ utc = [DateTime]::UtcNow.ToString('o'); launch_failed = $true; failure_stage = $Stage; process_id = $OwnedProcessId; exception_chain = $chain; chain_truncated = ($null -ne $current); no_retry = $true }
}
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$artifacts = Join-Path $project 'artifacts/principal-setup-2026-09-15'
$library = Join-Path $artifacts "PrincipalSetup-$Build.dll"
$tests = Join-Path $artifacts "PrincipalSetupTests-$Build.exe"
$compiler = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$powershell = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
if (-not [IO.Directory]::Exists($artifacts)) { throw 'Create the planned artifact directory first.' }
if ($Mode -eq 'Build') {
    if ([IO.File]::Exists($library) -or [IO.File]::Exists($tests)) { throw 'Build output already exists; do not overwrite evidence.' }
    & $compiler /nologo /target:library /platform:x64 /optimize+ /warnaserror+ "/out:$library" (Join-Path $project 'tests/fixtures/PrincipalSetup.cs')
    if ($LASTEXITCODE -ne 0) { throw 'Library compilation failed.' }
    & $compiler /nologo /target:exe /platform:x64 /optimize+ /warnaserror+ "/reference:$library" "/out:$tests" (Join-Path $project 'tests/PrincipalSetupTests.cs')
    if ($LASTEXITCODE -ne 0) { throw 'Test compilation failed.' }
    & $tests
    if ($LASTEXITCODE -ne 0) { throw 'Fault tests failed.' }
    Get-FileHash -LiteralPath $library -Algorithm SHA256 | Select-Object Path, Hash
    exit 0
}
if ($ExpectedAssemblySha256 -cnotmatch '^[a-f0-9]{64}$') { throw 'An independently recorded lowercase assembly SHA256 is required.' }
$stream = [IO.File]::Open($library, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
try {
    $length = $stream.Length
    if ($length -eq 0 -or $length -gt 262144) { throw 'Assembly size outside bound.' }
    $bytes = [byte[]]::new($length)
    $offset = 0
    while ($offset -lt $length) {
        $read = $stream.Read($bytes, $offset, $length - $offset)
        if ($read -le 0) { throw 'Incomplete assembly read.' }
        $offset += $read
    }
    if ($stream.ReadByte() -ne -1) { throw 'Assembly grew beyond bound.' }
} finally { $stream.Dispose() }
$sha = [Security.Cryptography.SHA256]::Create()
try { $actual = [BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-', '').ToLowerInvariant() } finally { $sha.Dispose() }
if ($actual -cne $ExpectedAssemblySha256) { throw 'Assembly fingerprint mismatch.' }
if ($Mode -eq 'Verify') { [Console]::WriteLine('Assembly fingerprint verified; OS mutations=0'); exit 0 }
$attemptFile = Join-Path $artifacts 'launch-attempt.json'
if ($Mode -eq 'Run' -and [IO.File]::Exists($attemptFile)) { throw 'An attempt is already recorded; no retry.' }
# Pass compressed public code inline, avoiding any elevated read of a U-writable path.
# No elevated compiler, writable TEMP output, module import, worker logon or secret argument.
$packed = [IO.MemoryStream]::new()
$compressor = [IO.Compression.DeflateStream]::new($packed, [IO.Compression.CompressionLevel]::Optimal, $true)
try { $compressor.Write($bytes, 0, $bytes.Length) } finally { $compressor.Dispose() }
try { $payload = [Convert]::ToBase64String($packed.ToArray()) } finally { $packed.Dispose() }
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
  [Environment]::Exit([Banto.PrincipalSetup.Entry]::Run())
} catch { [Environment]::Exit(83) }
'@
$loader = $loader.Replace('__DATA__', $payload).Replace('__HASH__', $ExpectedAssemblySha256)
if ($Mode -eq 'CheckLoader') { $loader = $loader.Replace('[Environment]::Exit([Banto.PrincipalSetup.Entry]::Run())', '[Environment]::Exit(0)') }
# Literal ASCII code uses single quotes only; no shell interpolation or path arguments.
if ($loader.Contains('"') -or $loader.Length -gt 29000) { throw 'Loader quoting/command-length bound.' }
$arguments = '-NoProfile -NonInteractive -Command "& { ' + $loader + ' }"'
if ($Mode -eq 'CheckLoader') {
    $check = Start-Process -FilePath $powershell -WindowStyle Hidden -WorkingDirectory 'C:\Windows\System32' -ArgumentList $arguments -PassThru
    try {
        if (-not $check.WaitForExit(10000)) { $check.Kill(); [void]$check.WaitForExit(5000); throw 'Owned loader check timed out.' }
        if ($check.ExitCode -ne 0) { throw "Loader check failed: $($check.ExitCode)" }
        [ordered]@{ mode = 'unelevated-load-only'; account_root_apis_called = $false; process_id = $check.Id; exit_code = $check.ExitCode; command_chars = $arguments.Length; assembly_sha256 = $actual } | ConvertTo-Json
    } finally { $check.Dispose() }
    exit 0
}
$attempt = [ordered]@{ utc = [DateTime]::UtcNow.ToString('o'); approved = $true; assembly_sha256 = $actual; build = $Build; command_chars = $arguments.Length; phase = 'before-uac'; account = 'BantoS4Publisher'; root = 'C:\ProgramData\BantoAI-S4B2-principal-20260915' }
$record = [IO.File]::Open($attemptFile, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
try { $data = [Text.Encoding]::UTF8.GetBytes(($attempt | ConvertTo-Json)); $record.Write($data, 0, $data.Length); $record.Flush($true) } finally { $record.Dispose() }
$startedUtc = [DateTime]::UtcNow
$launchStage = 'request-uac'
$ownedProcessId = $null
try {
    $process = Start-Process -FilePath $powershell -Verb RunAs -WindowStyle Hidden -WorkingDirectory 'C:\Windows\System32' -ArgumentList $arguments -PassThru
    $launchStage = 'read-owned-process-id'
    $ownedProcessId = $process.Id
    $launchStage = 'wait-for-exit'
    $exited = $process.WaitForExit(45000)
    $launchStage = 'collect-exit-result'
    $result = [ordered]@{ utc = [DateTime]::UtcNow.ToString('o'); launch_elapsed_ms = ([DateTime]::UtcNow - $startedUtc).TotalMilliseconds; process_id = $process.Id; exit_observed = $exited; exit_code = $null; phase_number = $null; native_detail = $null; release_failed = $false; observer_termination_attempted = $false }
    if ($exited) {
        $result.exit_code = $process.ExitCode
        if ($process.ExitCode -ge 65536) { $result.phase_number = ($process.ExitCode -shr 16) -band 16383; $result.native_detail = $process.ExitCode -band 65535; $result.release_failed = ($process.ExitCode -band 0x40000000) -ne 0 }
    }
    $launchStage = 'dispose-observer-handle'
    $process.Dispose()
} catch {
    $result = Get-SetupLaunchFailure -Failure $_ -Stage $launchStage -OwnedProcessId $ownedProcessId
    $result.launch_elapsed_ms = ([DateTime]::UtcNow - $startedUtc).TotalMilliseconds
}
$resultFile = Join-Path $artifacts 'launch-result.json'
$record = [IO.File]::Open($resultFile, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
try { $data = [Text.Encoding]::UTF8.GetBytes(($result | ConvertTo-Json)); $record.Write($data, 0, $data.Length); $record.Flush($true) } finally { $record.Dispose() }
$result | ConvertTo-Json
