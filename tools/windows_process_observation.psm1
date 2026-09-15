# Shared observation only: importing this module starts no process.
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
        no_retry = $true
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

Export-ModuleMember -Function Get-ElevationDiagnosticFailure, Invoke-ElevationDiagnosticObservation
