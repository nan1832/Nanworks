Set-StrictMode -Version Latest

function New-MonitorAlert {
    param(
        [string]$ExperimentName,
        [string]$Kind,
        [string]$Message,
        [string]$Key
    )
    [pscustomobject]@{
        Time = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
        Experiment = $ExperimentName
        Kind = $Kind
        Message = $Message
        Key = if ($Key) { $Key } else { "$ExperimentName|$Kind|$Message" }
    }
}

function Get-ExperimentMonitorAlerts {
    param(
        [Parameter(Mandatory = $true)][string]$Text,
        [Parameter(Mandatory = $true)][int]$GpuIndex,
        [int]$HighMemoryUsedMiB = 76000,
        [int]$LowUtilPercent = 5,
        [int]$WaitingDataSeconds = 1800,
        [int]$MaxRuntimeSeconds = 0,
        [int]$StaleLogSeconds = 3600,
        [string]$ExperimentName = 'experiment'
    )

    $alerts = @()

    if ($Text -match 'CUDA out of memory|torch\.cuda\.OutOfMemoryError') {
        $alerts += New-MonitorAlert $ExperimentName 'oom' 'CUDA OOM detected in recent logs.' "$ExperimentName|oom"
    }

    if ($Text -match 'SANITIZE_NONFINITE_GRAD|grad_bad=') {
        $alerts += New-MonitorAlert $ExperimentName 'nonfinite_grad' 'Non-finite gradients detected.' "$ExperimentName|nonfinite_grad"
    }

    $waitingMatches = [regex]::Matches($Text, 'Waiting data:\s*(\d+)\s*s')
    if ($waitingMatches.Count -gt 0) {
        $maxWaiting = ($waitingMatches | ForEach-Object { [int]$_.Groups[1].Value } | Measure-Object -Maximum).Maximum
        if ($maxWaiting -ge $WaitingDataSeconds) {
            $alerts += New-MonitorAlert $ExperimentName 'waiting_data' "Waiting data reached ${maxWaiting}s." "$ExperimentName|waiting_data"
        }
    }

    $runtimeMatches = [regex]::Matches($Text, 'CURRENT\s+.*?etimes=(\d+)')
    foreach ($m in $runtimeMatches) {
        $runtime = [int]$m.Groups[1].Value
        if ($MaxRuntimeSeconds -gt 0 -and $runtime -ge $MaxRuntimeSeconds) {
            $alerts += New-MonitorAlert $ExperimentName 'runtime_exceeded' "Current process runtime ${runtime}s exceeded ${MaxRuntimeSeconds}s." "$ExperimentName|runtime_exceeded"
            break
        }
    }

    $logAgeMatches = [regex]::Matches($Text, 'CURRENT_LOG_AGE_SECONDS=(\d+)')
    foreach ($m in $logAgeMatches) {
        $age = [int]$m.Groups[1].Value
        if ($age -ge $StaleLogSeconds) {
            $alerts += New-MonitorAlert $ExperimentName 'stale_log' "Current log has not updated for ${age}s." "$ExperimentName|stale_log"
            break
        }
    }

    foreach ($line in ($Text -split "`n")) {
        $trimmed = $line.Trim()
        $gpuMatch = [regex]::Match($trimmed, '^(\d+)\s*,\s*[^,]+,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*$')
        if (-not $gpuMatch.Success) {
            $gpuMatch = [regex]::Match($trimmed, '^GPU\s+(\d+)\s*,\s*[^,]+,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*$')
        }
        if ($gpuMatch.Success -and [int]$gpuMatch.Groups[1].Value -eq $GpuIndex) {
            $used = [int]$gpuMatch.Groups[2].Value
            $util = [int]$gpuMatch.Groups[4].Value
            if ($used -ge $HighMemoryUsedMiB -and $util -le $LowUtilPercent) {
                $alerts += New-MonitorAlert $ExperimentName 'gpu_stalled' "GPU$GpuIndex uses ${used}MiB but util is ${util}%." "$ExperimentName|gpu_stalled"
            }
        }
    }

    if ($Text -match 'MODEL_STOP_AFTER_TRAIN_FAIL|MAIN_LAYER_FAILED|EVAL_NOT_RUN|TRAIN_END .*rc=(?!0)\d+') {
        $alerts += New-MonitorAlert $ExperimentName 'train_or_eval_failed' 'Recent status contains train/eval failure or skipped eval.' "$ExperimentName|train_or_eval_failed"
    }

    if ($Text -match 'WATCHDOG_KILL|MANUAL_STOP_STUCK|STOP_MAIN_') {
        $alerts += New-MonitorAlert $ExperimentName 'stopped_stuck_process' 'A stuck process was stopped or watchdog intervened.' "$ExperimentName|stopped_stuck_process"
    }

    if ($Text -match 'NO_CURRENT_PROCESS') {
        $alerts += New-MonitorAlert $ExperimentName 'no_current_process' 'No current training process found.' "$ExperimentName|no_current_process"
    }

    return @($alerts)
}

function Update-MonitorAlertState {
    param(
        [Parameter(Mandatory = $true)][string]$StateDir,
        [Parameter(Mandatory = $true)]$Alerts,
        [int]$SuppressMinutes = 30
    )

    New-Item -ItemType Directory -Force -Path $StateDir | Out-Null
    $statePath = Join-Path $StateDir 'alert_state.json'
    $state = @{}
    if (Test-Path -LiteralPath $statePath) {
        try {
            $loaded = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
            foreach ($p in $loaded.PSObject.Properties) {
                $state[$p.Name] = [datetime]$p.Value
            }
        }
        catch {
            $state = @{}
        }
    }

    $now = Get-Date
    $emit = @()
    foreach ($alert in @($Alerts)) {
        $key = [string]$alert.Key
        $last = $null
        if ($state.ContainsKey($key)) {
            $last = [datetime]$state[$key]
        }
        if ($null -eq $last -or ($now - $last).TotalMinutes -ge $SuppressMinutes) {
            $emit += $alert
            $state[$key] = $now
        }
    }

    $jsonObj = [ordered]@{}
    foreach ($key in $state.Keys) {
        $jsonObj[$key] = ([datetime]$state[$key]).ToString('o')
    }
    $jsonObj | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding UTF8
    return @($emit)
}

function Write-MonitorAlerts {
    param(
        [Parameter(Mandatory = $true)]$Alerts,
        [Parameter(Mandatory = $true)][string]$LogPath,
        [switch]$Beep
    )

    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $LogPath) | Out-Null
    foreach ($alert in @($Alerts)) {
        $line = "[{0}] {1} {2}: {3}" -f $alert.Time, $alert.Experiment, $alert.Kind, $alert.Message
        Add-Content -LiteralPath $LogPath -Value $line -Encoding ASCII
        Write-Host $line -ForegroundColor Red
        if ($Beep) {
            try { [console]::Beep(1000, 300) } catch { }
        }
    }
}
