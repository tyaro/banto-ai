param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{40}$')][string]$ExpectedHead,
    [Parameter(Mandatory=$true)][ValidateSet(1)][int]$Attempt
)
$ErrorActionPreference = 'Stop'
$probeRepo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$probeBase = Join-Path $probeRepo 'artifacts\directory-peer-2026-09-14'
$probeStdout = Join-Path $probeBase "attempt-$Attempt.stdout.txt"
$probeStderr = Join-Path $probeBase "attempt-$Attempt.stderr.txt"
$probeRecord = Join-Path $probeBase "attempt-$Attempt.supervision.json"
foreach ($probePath in @($probeStdout, $probeStderr, $probeRecord)) {
    if (Test-Path -LiteralPath $probePath) { throw 'supervision_record_already_exists' }
}
$probeOs = Get-CimInstance Win32_OperatingSystem
$probeVersion = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
$probeDrive = [IO.DriveInfo]::new([IO.Path]::GetPathRoot($probeRepo))
$probeAvailable = [int64]$probeOs.FreePhysicalMemory * 1024
$probeFreeDisk = $probeDrive.AvailableFreeSpace
if ($probeAvailable -lt 2GB -or $probeFreeDisk -lt 2GB) { throw 'preflight_resource_limit' }
$probeStart = [DateTime]::UtcNow.ToString('o')
$probeWatch = [Diagnostics.Stopwatch]::StartNew()
$probeArgs = @{
    FilePath = 'C:\Python314\python.exe'
    ArgumentList = @('-I', '-B', 'tests/fixtures/anomaly_v03_directory_peer_probe.py', '--expected-head', $ExpectedHead, '--attempt', "$Attempt")
    WorkingDirectory = $probeRepo
    WindowStyle = 'Hidden'
    PassThru = $true
    RedirectStandardOutput = $probeStdout
    RedirectStandardError = $probeStderr
}
$probePoints = [Collections.Generic.List[object]]::new()
$probeStopReason = $null
$probeProcess = $null
try {
    $probeProcess = Start-Process @probeArgs
    while (-not $probeProcess.WaitForExit(1000)) {
        $probeProcess.Refresh()
        if ($probeProcess.HasExited) { break }
        $probePrivate = $probeProcess.PrivateMemorySize64
        $probeWorking = $probeProcess.WorkingSet64
        $probePoints.Add([ordered]@{
            elapsed_seconds = [Math]::Round($probeWatch.Elapsed.TotalSeconds, 3)
            private_bytes = $probePrivate
            working_bytes = $probeWorking
        })
        if ($probeWatch.Elapsed.TotalSeconds -gt 45) { $probeStopReason = 'wall_time' }
        elseif ($probePrivate -gt 256MB -or $probeWorking -gt 384MB) { $probeStopReason = 'process_memory' }
        if ($probeStopReason) {
            $probeProcess.Kill()
            if (-not $probeProcess.WaitForExit(5000)) { throw 'worker_exit_not_confirmed' }
            break
        }
    }
    $probeProcess.WaitForExit()
} finally {
    if ($null -ne $probeProcess -and -not $probeProcess.HasExited) {
        $probeProcess.Kill()
        if (-not $probeProcess.WaitForExit(5000)) { throw 'worker_exit_not_confirmed' }
    }
}
$probeWatch.Stop()
$probeOutputBytes = (Get-Item -LiteralPath $probeStdout).Length + (Get-Item -LiteralPath $probeStderr).Length
if ($probeOutputBytes -gt 128KB -and -not $probeStopReason) { $probeStopReason = 'output_budget' }
$probeSummary = [ordered]@{
    utc_start = $probeStart
    utc_end = [DateTime]::UtcNow.ToString('o')
    attempt = $Attempt
    expected_head = $ExpectedHead
    worker_pid = $probeProcess.Id
    worker_exited = $probeProcess.HasExited
    exit_code = $probeProcess.ExitCode
    stop_reason = $probeStopReason
    elapsed_seconds = [Math]::Round($probeWatch.Elapsed.TotalSeconds, 3)
    observations = @($probePoints.ToArray())
    output_bytes = $probeOutputBytes
    preflight_available_ram_bytes = $probeAvailable
    preflight_available_disk_bytes = $probeFreeDisk
    os_build = "$($probeOs.BuildNumber).$($probeVersion.UBR)"
    boot = $probeOs.LastBootUpTime.ToString('o')
    isolation_certified = $false
    acceptance_status = 'not_completed'
}
$probeProcess.Dispose()
$probeJson = ($probeSummary | ConvertTo-Json -Depth 8) + [Environment]::NewLine
$probeStream = [IO.File]::Open($probeRecord, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
try {
    $probeBytes = [Text.UTF8Encoding]::new($false).GetBytes($probeJson)
    $probeStream.Write($probeBytes, 0, $probeBytes.Length)
} finally { $probeStream.Dispose() }
[pscustomobject]$probeSummary | Select-Object attempt,worker_exited,exit_code,stop_reason,elapsed_seconds,output_bytes | ConvertTo-Json -Compress
if ($probeSummary.exit_code -ne 0 -or $probeStopReason) { exit 1 }
