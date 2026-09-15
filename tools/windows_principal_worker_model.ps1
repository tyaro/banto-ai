# Only pure model tests and a read-only, normal-U token diagnostic.
[CmdletBinding()]
param([ValidateSet('Build', 'Diagnose')][string]$Mode = 'Build',
      [ValidatePattern('^build-[0-9]{2}$')][string]$Build = 'build-01',
      [string]$ExpectedDiagnosticSha256 = '')
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$artifacts = Join-Path $project 'artifacts/principal-worker-lifecycle-2026-09-16'
$model = Join-Path $artifacts "PrincipalWorkerLifecycleTests-$Build.exe"
$diagnostic = Join-Path $artifacts "PrincipalLaunchCapabilityDiagnostic-$Build.exe"
$queryTests = Join-Path $artifacts "PrincipalQueryHandleTests-$Build.exe"
$privilegeTests = Join-Path $artifacts "PrincipalPrivilegeTests-$Build.exe"
$compiler = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not [IO.Directory]::Exists($artifacts)) { throw 'Create planned artifact directory first' }
if ($Mode -eq 'Build') {
    if ([IO.File]::Exists($model) -or [IO.File]::Exists($diagnostic) -or [IO.File]::Exists($queryTests) -or [IO.File]::Exists($privilegeTests)) { throw 'Build output exists; preserve evidence' }
    & $compiler /nologo /target:exe /platform:x64 /optimize+ /warnaserror+ "/out:$model" (Join-Path $project 'tests/fixtures/PrincipalWorkerLifecycle.cs') (Join-Path $project 'tests/PrincipalWorkerLifecycleTests.cs')
    if ($LASTEXITCODE -ne 0) { throw 'Model compilation failed' }
    & $model
    if ($LASTEXITCODE -ne 0) { throw 'Model tests failed' }
    # Compile against the existing parser source; Main never instantiates its native backend.
    & $compiler /nologo /target:exe /platform:x64 /optimize+ /warnaserror+ /main:PrincipalLaunchCapabilityDiagnostic "/out:$diagnostic" (Join-Path $project 'tests/fixtures/PrincipalSetup.cs') (Join-Path $project 'tests/fixtures/PrincipalLaunchCapabilityDiagnostic.cs')
    if ($LASTEXITCODE -ne 0) { throw 'Diagnostic compilation failed' }
    & $compiler /nologo /target:exe /platform:x64 /optimize+ /warnaserror+ /main:PrincipalQueryHandleTests "/out:$queryTests" (Join-Path $project 'tests/fixtures/PrincipalSetup.cs') (Join-Path $project 'tests/fixtures/PrincipalLaunchCapabilityDiagnostic.cs') (Join-Path $project 'tests/PrincipalQueryHandleTests.cs')
    if ($LASTEXITCODE -ne 0) { throw 'Query lease tests compilation failed' }
    & $queryTests
    if ($LASTEXITCODE -ne 0) { throw 'Query lease tests failed' }
    & $compiler /nologo /target:exe /platform:x64 /optimize+ /warnaserror+ "/out:$privilegeTests" (Join-Path $project 'tests/fixtures/PrincipalSetup.cs') (Join-Path $project 'tests/PrincipalPrivilegeTests.cs')
    if ($LASTEXITCODE -ne 0) { throw 'Privilege parser tests compilation failed' }
    & $privilegeTests
    if ($LASTEXITCODE -ne 0) { throw 'Privilege parser tests failed' }
    Get-FileHash -LiteralPath $diagnostic -Algorithm SHA256 | Select-Object Path, Hash
    exit 0
}
if ($ExpectedDiagnosticSha256 -cnotmatch '^[a-f0-9]{64}$') { throw 'Recorded lowercase SHA256 required' }
$inputStream = [IO.File]::Open($diagnostic, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
try {
    $length = $inputStream.Length
    if ($length -le 0 -or $length -gt 65536) { throw 'Diagnostic size bound' }
    $bytes = [byte[]]::new($length)
    $offset = 0
    while ($offset -lt $length) {
        $read = $inputStream.Read($bytes, $offset, $length - $offset)
        if ($read -le 0) { throw 'Incomplete diagnostic read' }
        $offset += $read
    }
    if ($inputStream.ReadByte() -ne -1) { throw 'Diagnostic grew beyond bound' }
} finally { $inputStream.Dispose() }
$sha = [Security.Cryptography.SHA256]::Create()
try { $actual = [BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-', '').ToLowerInvariant() } finally { $sha.Dispose() }
if ($actual -cne $ExpectedDiagnosticSha256) { throw 'Diagnostic hash mismatch' }
$output = Join-Path $artifacts 'launch-capability.json'
$stream = [IO.File]::Open($output, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
try {
    # Load exactly the hashed bytes; do not execute a second path read. No RunAs/UAC.
    $assembly = [Reflection.Assembly]::Load($bytes)
    $writer = [IO.StringWriter]::new([Globalization.CultureInfo]::InvariantCulture)
    $original = [Console]::Out
    try { [Console]::SetOut($writer); $exitCode = $assembly.EntryPoint.Invoke($null, @()) }
    finally { [Console]::SetOut($original) }
    $text = $writer.ToString()
    if ($text.Length -gt 8192) { throw 'Diagnostic output bound' }
    $encoded = [Text.UTF8Encoding]::new($false).GetBytes($text)
    $stream.Write($encoded, 0, $encoded.Length); $stream.Flush($true)
    [Console]::Write($text)
} finally { $stream.Dispose() }
if ($exitCode -ne 0) { throw 'Read-only query incomplete; preserve output and do not retry' }
