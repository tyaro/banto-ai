param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{40}$')][string]$ExpectedHead,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{64}$')][string]$InputSha256,
    [Parameter(Mandatory=$true)][ValidateSet(1)][int]$Attempt
)
$ErrorActionPreference = 'Stop'
$heldRepo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$heldBase = Join-Path $heldRepo 'artifacts\namespace-diagnostic-2026-09-15'
$heldStdout = Join-Path $heldBase 'attempt-1.stdout.txt'
$heldStderr = Join-Path $heldBase 'attempt-1.stderr.txt'
$heldRecord = Join-Path $heldBase 'attempt-1.supervision.json'
$heldPin = Join-Path $heldBase 'input-pin.json'
# A permanent exclusive claim serializes this supervisor; never reuse its slot.
$heldClaim = [IO.File]::Open((Join-Path $heldBase 'attempt-1.claim'), [IO.FileMode]::CreateNew,
    [IO.FileAccess]::Write, [IO.FileShare]::Read)
$heldClaim.Dispose()
foreach ($heldPath in @($heldStdout,$heldStderr,$heldRecord)) {
    if (Test-Path -LiteralPath $heldPath) { throw 'held_supervision_record_exists' }
}
if ((Get-FileHash -LiteralPath $heldPin -Algorithm SHA256).Hash.ToLowerInvariant() -ne $InputSha256) {
    throw 'held_supervision_pin_mismatch'
}
$heldOs = Get-CimInstance Win32_OperatingSystem
$heldVersion = Get-ItemProperty -LiteralPath 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
$heldDrive = [IO.DriveInfo]::new([IO.Path]::GetPathRoot($heldRepo))
$heldAvailable = [int64]$heldOs.FreePhysicalMemory * 1024
$heldFreeDisk = $heldDrive.AvailableFreeSpace
if ($heldAvailable -lt 2GB -or $heldFreeDisk -lt 2GB) { throw 'held_preflight_resource_limit' }
$heldStart = [DateTime]::UtcNow.ToString('o')
$heldWatch = [Diagnostics.Stopwatch]::StartNew()
$heldArgs = @{
    FilePath = 'C:\Python314\python.exe'
    ArgumentList = @('-I','-B','tests/fixtures/anomaly_v03_namespace_create_probe.py',
        '--expected-head',$ExpectedHead,'--input-sha256',$InputSha256,'--attempt',"$Attempt")
    WorkingDirectory = $heldRepo
    WindowStyle = 'Hidden'
    PassThru = $true
    RedirectStandardOutput = $heldStdout
    RedirectStandardError = $heldStderr
}
$heldPoints = [Collections.Generic.List[object]]::new()
$heldStopReason = $null
$heldErrorType = $null
$heldProcess = $null
$heldExited = $false
$heldExitCode = $null
$heldPid = $null
$heldMaxObservedWorking = $null
try {
    $heldProcess = Start-Process @heldArgs
    $heldPid = $heldProcess.Id
    while (-not $heldProcess.WaitForExit(500)) {
        $heldProcess.Refresh()
        if ($heldProcess.HasExited) { break }
        if ($heldPoints.Count -ge 96) { $heldStopReason = 'point_budget'; break }
        $heldPrivate = $heldProcess.PrivateMemorySize64
        $heldWorking = $heldProcess.WorkingSet64
        if ($null -eq $heldMaxObservedWorking -or $heldWorking -gt $heldMaxObservedWorking) {
            $heldMaxObservedWorking = $heldWorking
        }
        $heldFree = $heldDrive.AvailableFreeSpace
        $heldOutput = (Get-Item -LiteralPath $heldStdout).Length + (Get-Item -LiteralPath $heldStderr).Length
        $heldPoints.Add([ordered]@{
            elapsed_seconds = [Math]::Round($heldWatch.Elapsed.TotalSeconds,3)
            private_bytes = $heldPrivate
            working_bytes = $heldWorking
            free_disk_bytes = $heldFree
            output_bytes = $heldOutput
        })
        if ($heldWatch.Elapsed.TotalSeconds -gt 45) { $heldStopReason = 'wall_time' }
        elseif ($heldPrivate -gt 256MB -or $heldWorking -gt 384MB) { $heldStopReason = 'process_memory' }
        elseif ($heldFree -lt 2GB) { $heldStopReason = 'free_disk' }
        elseif ($heldOutput -gt 384KB) { $heldStopReason = 'output_budget' }
        if ($heldStopReason) { break }
    }
} catch {
    $heldErrorType = $_.Exception.GetType().FullName
    if (-not $heldStopReason) { $heldStopReason = 'supervisor_error' }
} finally {
    if ($null -ne $heldProcess) {
        try {
            if (-not $heldProcess.HasExited) {
                $heldProcess.Kill()  # Only the exact process object created above.
                if (-not $heldProcess.WaitForExit(5000)) { throw 'held_worker_exit_not_confirmed' }
            }
            $heldExited = $heldProcess.HasExited
            if ($heldExited) {
                $heldProcess.WaitForExit() # Drain the completed redirect operation.
                $heldExitCode = $heldProcess.ExitCode
            }
        } catch {
            $heldErrorType = $_.Exception.GetType().FullName
            $heldStopReason = 'worker_exit_not_confirmed'
        }
        $heldProcess.Dispose()
    }
}
$heldWatch.Stop()
$heldOutputBytes = 0
foreach ($heldPath in @($heldStdout,$heldStderr)) {
    if (Test-Path -LiteralPath $heldPath) { $heldOutputBytes += (Get-Item -LiteralPath $heldPath).Length }
}
if ($heldOutputBytes -gt 384KB -and -not $heldStopReason) { $heldStopReason = 'output_budget' }
if ($heldWatch.Elapsed.TotalSeconds -gt 45 -and -not $heldStopReason) { $heldStopReason = 'wall_time' }
$heldSummary = [ordered]@{
    utc_start = $heldStart
    utc_end = [DateTime]::UtcNow.ToString('o')
    attempt = $Attempt
    expected_head = $ExpectedHead
    input_sha256 = $InputSha256
    worker_pid = $heldPid
    worker_exited = $heldExited
    exit_code = $heldExitCode
    stop_reason = $heldStopReason
    supervisor_error_type = $heldErrorType
    elapsed_seconds = [Math]::Round($heldWatch.Elapsed.TotalSeconds,3)
    observations = @($heldPoints.ToArray())
    max_observed_working_bytes = $heldMaxObservedWorking
    output_bytes = $heldOutputBytes
    preflight_available_ram_bytes = $heldAvailable
    preflight_available_disk_bytes = $heldFreeDisk
    os_build = "$($heldOs.BuildNumber).$($heldVersion.UBR)"
    boot = $heldOs.LastBootUpTime.ToString('o')
    isolation_certified = $false
    formal_permission = $false
    execution_authenticated = $false
    acceptance_status = 'not_completed'
}
$heldJson = ($heldSummary | ConvertTo-Json -Depth 8) + [Environment]::NewLine
$heldStream = [IO.File]::Open($heldRecord,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
try {
    $heldBytes = [Text.UTF8Encoding]::new($false).GetBytes($heldJson)
    $heldStream.Write($heldBytes,0,$heldBytes.Length)
} finally { $heldStream.Dispose() }
[pscustomobject]$heldSummary | Select-Object attempt,worker_exited,exit_code,stop_reason,elapsed_seconds,output_bytes | ConvertTo-Json -Compress
if (-not $heldExited -or $heldExitCode -ne 0 -or $heldStopReason) { exit 1 }
