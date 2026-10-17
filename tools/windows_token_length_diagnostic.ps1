# Bounded, unelevated, read-only query of this process's token; no preparation entry.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
Import-Module (Join-Path $PSScriptRoot 'windows_process_observation.psm1') -ErrorAction Stop
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$base = Join-Path $project 'artifacts/token-length-diagnostic-2026-09-15'
$library = Join-Path $project 'artifacts/principal-setup-c-2026-09-15/PrincipalSetup-build-01.dll'
if (-not [Environment]::Is64BitProcess) { throw 'Expected x64 process.' }
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
try {
    if ($identity.User.Value -ne 'S-1-5-21-2169670816-255940906-2713565042-1001') { throw 'Unexpected SID.' }
    if (([Security.Principal.WindowsPrincipal]::new($identity)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Expected unelevated observer.' }
} finally { $identity.Dispose() }
# Load the reviewed public P/Invoke declarations. Never call Entry, NativeBackend or SAM/root APIs.
$stream = [IO.File]::OpenRead($library)
try {
    if ($stream.Length -ne 22528) { throw 'Unexpected assembly length.' }
    $bytes = [byte[]]::new(22528)
    $offset = 0
    while ($offset -lt $bytes.Length) {
        $count = $stream.Read($bytes, $offset, $bytes.Length - $offset)
        if ($count -le 0) { throw 'Truncated assembly.' }
        $offset += $count
    }
    if ($stream.ReadByte() -ne -1) { throw 'Assembly changed.' }
} finally { $stream.Dispose() }
$sha = [Security.Cryptography.SHA256]::Create()
try { $hash = [BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-', '').ToLowerInvariant() } finally { $sha.Dispose() }
if ($hash -cne '48eb8f4dfbaa09a38fb4642af23f49412534da150b4ef9ca6eb41725a91893bf') { throw 'Assembly hash mismatch.' }
[IO.Directory]::CreateDirectory($base) | Out-Null
$guard = [IO.File]::Open((Join-Path $base 'attempt.txt'), [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
try {
    $record = [Text.Encoding]::UTF8.GetBytes([DateTime]::UtcNow.ToString('o') + "`nmax1; own-token; four fixed queries; no UAC or OS configuration`n")
    $guard.Write($record, 0, $record.Length); $guard.Flush($true)
} finally { $guard.Dispose() }
$token = [IntPtr]::Zero
$tokenAcquired = $false
$openSucceeded = $false
$results = @()
$failure = $null
$closeFailure = $null
$tokenClosed = $false
$stage = 'load-public-interop'
try {
    [Reflection.Assembly]::Load($bytes) | Out-Null
    $stage = 'open-own-token'
    $openSucceeded = [Banto.PrincipalSetup.Native]::OpenProcessToken([Banto.PrincipalSetup.Native]::GetCurrentProcess(), 0x000a, [ref]$token)
    $openError = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
    if (-not $openSucceeded) { throw [ComponentModel.Win32Exception]::new($openError) }
    if ($token -eq [IntPtr]::Zero -or $token -eq [IntPtr]::new(-1)) { throw 'Invalid confirmed token handle.' }
    $tokenAcquired = $true
    foreach ($case in @(@{ Class = 19; Length = 64 }, @{ Class = 19; Length = 8 }, @{ Class = 20; Length = 64 }, @{ Class = 20; Length = 4 })) {
        $stage = 'query-class-' + $case.Class + '-length-' + $case.Length
        $buffer = [Runtime.InteropServices.Marshal]::AllocHGlobal(64)
        try {
            for ($index = 0; $index -lt 64; $index++) { [Runtime.InteropServices.Marshal]::WriteByte($buffer, $index, 0) }
            $needed = [uint32]0
            $ok = [Banto.PrincipalSetup.Native]::GetTokenInformation($token, $case.Class, $buffer, $case.Length, [ref]$needed)
            $errorCode = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
            $row = [ordered]@{ token_information_class = $case.Class; supplied_length = $case.Length; success = $ok; native_error = $(if ($ok) { $null } else { $errorCode }); required_length = $needed; returned_linked_handle_closed = $null; elevation_value = $null }
            $results += $row
            if ($ok -and $case.Class -eq 19) {
                if ($needed -ne 8) { throw 'Unexpected linked-token ABI.' }
                $linked = [Runtime.InteropServices.Marshal]::ReadIntPtr($buffer)
                if ($linked -eq [IntPtr]::Zero -or $linked -eq [IntPtr]::new(-1)) { throw 'Invalid linked handle.' }
                $row.returned_linked_handle_closed = [Banto.PrincipalSetup.Native]::CloseHandle($linked)
                if (-not $row.returned_linked_handle_closed) { throw [ComponentModel.Win32Exception]::new([Runtime.InteropServices.Marshal]::GetLastWin32Error()) }
            }
            if ($ok -and $case.Class -eq 20) {
                if ($needed -ne 4) { throw 'Unexpected elevation ABI.' }
                $row.elevation_value = [Runtime.InteropServices.Marshal]::ReadInt32($buffer)
            }
        } finally { [Runtime.InteropServices.Marshal]::FreeHGlobal($buffer) }
    }
} catch {
    $failure = Get-ElevationDiagnosticFailure -Failure $_ -Stage $stage
} finally {
    if ($tokenAcquired) {
        try {
            if (-not [Banto.PrincipalSetup.Native]::CloseHandle($token)) { throw [ComponentModel.Win32Exception]::new([Runtime.InteropServices.Marshal]::GetLastWin32Error()) }
            $tokenClosed = $true
        } catch { $closeFailure = Get-ElevationDiagnosticFailure -Failure $_ -Stage 'close-own-token' }
    }
}
$result = [ordered]@{ utc = [DateTime]::UtcNow.ToString('o'); observer_elevated = $false; queries = $results; open_process_token_succeeded = $openSucceeded; token_acquired_confirmed = $tokenAcquired; unconfirmed_token_output_nonzero = (-not $tokenAcquired -and $token -ne [IntPtr]::Zero); owned_token_closed = $tokenClosed; failure = $failure; close_failure = $closeFailure; os_configuration_changed = $false; preparation_entry_called = $false; old_roots_accessed = $false; no_retry = $true }
$output = [Text.Encoding]::UTF8.GetBytes(($result | ConvertTo-Json -Depth 6) + "`n")
$file = [IO.File]::Open((Join-Path $base 'result.json'), [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
try { $file.Write($output, 0, $output.Length); $file.Flush($true) } finally { $file.Dispose() }
$result | ConvertTo-Json -Depth 6
if ($null -ne $failure -or $null -ne $closeFailure) { exit 1 }
