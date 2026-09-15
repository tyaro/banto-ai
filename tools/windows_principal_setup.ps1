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
function Get-SetupExitDetails {
    param([int]$Code)
    $marked = ($Code -band 0x20000000) -ne 0
    $phase = if ($Code -ge 65536) { ($Code -shr 16) -band 8191 } else { $null }
    $detail = if ($Code -ge 65536 -and -not $marked) { $Code -band 65535 } else { $null }
    $inspection = $null
    if ($marked) {
        $step = ($Code -shr 8) -band 31
        $kind = ($Code -shr 13) -band 7
        $names = @('none','budget','volume-pin','parent-pin','volume-peer-access','parent-peer-access','root-identity','actual-policy','expected-policy','compare-details','exact-policy-comparison')
        $valid = $phase -eq 5 -and $step -ge 1 -and $step -lt $names.Count -and $kind -le 4
        $inspection = [ordered]@{ encoding_valid = $valid; step_id = $step; exception_kind = $kind; policy_difference_mask = ($Code -band 255); original_unknown_detail = 65535 }
        if ($valid) { $inspection.step = $names[$step] }
        $inspection.policy_difference_available = $valid -and $step -eq 10
    }
    return [ordered]@{ phase_number = $phase; native_detail = $detail; release_failed = (($Code -band 0x40000000) -ne 0); inspection_failure = $inspection }
}
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$artifacts = Join-Path $project 'artifacts/principal-setup-g-2026-09-16'
$library = Join-Path $artifacts "PrincipalSetup-$Build.dll"
$tests = Join-Path $artifacts "PrincipalSetupTests-$Build.exe"
$privilegeTests = Join-Path $artifacts "PrincipalPrivilegeTests-$Build.exe"
$compiler = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$powershell = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
if (-not [IO.Directory]::Exists($artifacts)) { throw 'Create the planned artifact directory first.' }
if ($Mode -eq 'Build') {
    if ([IO.File]::Exists($library) -or [IO.File]::Exists($tests) -or [IO.File]::Exists($privilegeTests)) { throw 'Build output already exists; do not overwrite evidence.' }
    & $compiler /nologo /target:library /platform:x64 /optimize+ /warnaserror+ "/out:$library" (Join-Path $project 'tests/fixtures/PrincipalSetup.cs')
    if ($LASTEXITCODE -ne 0) { throw 'Library compilation failed.' }
    & $compiler /nologo /target:exe /platform:x64 /optimize+ /warnaserror+ "/reference:$library" "/out:$tests" (Join-Path $project 'tests/PrincipalSetupTests.cs')
    if ($LASTEXITCODE -ne 0) { throw 'Test compilation failed.' }
    & $tests
    if ($LASTEXITCODE -ne 0) { throw 'Fault tests failed.' }
    & $compiler /nologo /target:exe /platform:x64 /optimize+ /warnaserror+ "/reference:$library" "/out:$privilegeTests" (Join-Path $project 'tests/PrincipalPrivilegeTests.cs')
    if ($LASTEXITCODE -ne 0) { throw 'Privilege test compilation failed.' }
    & $privilegeTests
    if ($LASTEXITCODE -ne 0) { throw 'Privilege tests failed.' }
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
        if ($check.Handle -eq [IntPtr]::Zero) { throw 'Missing loader process handle.' }
        if (-not $check.WaitForExit(10000)) { $check.Kill(); [void]$check.WaitForExit(5000); throw 'Owned loader check timed out.' }
        if ($null -eq $check.ExitCode -or $check.ExitCode -ne 0) { throw "Loader check failed: $($check.ExitCode)" }
        [ordered]@{ mode = 'unelevated-load-only'; account_root_apis_called = $false; process_id = $check.Id; exit_code = $check.ExitCode; command_chars = $arguments.Length; assembly_sha256 = $actual } | ConvertTo-Json
    } finally { $check.Dispose() }
    exit 0
}
# Load only observation functions before consuming the new attempt guard.
Import-Module (Join-Path $PSScriptRoot 'windows_process_observation.psm1') -ErrorAction Stop
$attempt = [ordered]@{ utc = [DateTime]::UtcNow.ToString('o'); approved = $true; assembly_sha256 = $actual; build = $Build; command_chars = $arguments.Length; phase = 'before-uac'; account = 'BantoS4Publisher'; root = 'C:\ProgramData\BantoAI-S4B2-principal-20260916g'; observer_wait_ms = 45000; api = 'System.Diagnostics.Process.Start(ProcessStartInfo)' }
$record = [IO.File]::Open($attemptFile, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
try { $data = [Text.Encoding]::UTF8.GetBytes(($attempt | ConvertTo-Json)); $record.Write($data, 0, $data.Length); $record.Flush($true) } finally { $record.Dispose() }
# The already-tested observer is shared with the configuration-free diagnostic.
$result = Invoke-ElevationDiagnosticObservation -ExpectedExitCode 0 -Launch {
    $startInfo = [Diagnostics.ProcessStartInfo]::new($powershell, $arguments)
    $startInfo.UseShellExecute = $true
    $startInfo.Verb = 'runas'
    $startInfo.WindowStyle = [Diagnostics.ProcessWindowStyle]::Hidden
    $startInfo.WorkingDirectory = 'C:\Windows\System32'
    [Diagnostics.Process]::Start($startInfo)
} -ReadId { param($process) $process.Id } -CaptureHandle {
    param($process)
    if ($process.Handle -eq [IntPtr]::Zero) { throw 'Missing setup process handle.' }
} -Wait { param($process) $process.WaitForExit(45000) } -ReadExit {
    param($process) $process.ExitCode
} -Dispose { param($process) $process.Dispose() }
# Setup can mutate the OS even when launch/exit is unconfirmed.
$result.os_configuration_change_status = 'unknown-until-success-verification'
$result.phase_number = $null
$result.native_detail = $null
$result.release_failed = $null
$result.inspection_failure = $null
if ($result.exit_observed) {
    $decoded = Get-SetupExitDetails -Code $result.exit_code
    foreach ($key in $decoded.Keys) { $result[$key] = $decoded[$key] }
}
$result.observer_termination_attempted = $false
$result.setup_exit_success = $result.expected_probe_result -and $null -eq $result.failure -and $null -eq $result.dispose_failure
$resultFile = Join-Path $artifacts 'launch-result.json'
$record = [IO.File]::Open($resultFile, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
try { $data = [Text.Encoding]::UTF8.GetBytes(($result | ConvertTo-Json -Depth 12)); $record.Write($data, 0, $data.Length); $record.Flush($true) } finally { $record.Dispose() }
$result | ConvertTo-Json -Depth 12
if (-not $result.setup_exit_success) { exit 1 }
