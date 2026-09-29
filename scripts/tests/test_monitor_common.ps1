Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
. (Join-Path $repoRoot 'scripts/monitor_common.ps1')

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) {
        throw $Message
    }
}

function Assert-Equal {
    param($Expected, $Actual, [string]$Message)
    if ($Expected -ne $Actual) {
        throw "$Message Expected=[$Expected] Actual=[$Actual]"
    }
}

$sample = @'
GPU 1, NVIDIA A800 80GB PCIe, 81117, 39, 0
torch.cuda.OutOfMemoryError: CUDA out of memory. Tried to allocate 176.00 MiB.
Waiting data: 45000 s
SANITIZE_NONFINITE_GRAD_BEFORE_STEP loss=33.4 reasons=['layer grad_bad=1/1']
CURRENT model=instructblip-vicuna-7b layer=0 etimes=48722
'@

$alerts = Get-ExperimentMonitorAlerts `
    -Text $sample `
    -GpuIndex 1 `
    -HighMemoryUsedMiB 76000 `
    -LowUtilPercent 5 `
    -WaitingDataSeconds 1800 `
    -MaxRuntimeSeconds 7200 `
    -ExperimentName 'unit'

Assert-True ($alerts.Count -ge 4) 'Expected multiple alerts from sample text.'
Assert-True (@($alerts | Where-Object Kind -eq 'oom').Count -ge 1) 'Expected OOM alert.'
Assert-True (@($alerts | Where-Object Kind -eq 'waiting_data').Count -ge 1) 'Expected Waiting data alert.'
Assert-True (@($alerts | Where-Object Kind -eq 'nonfinite_grad').Count -ge 1) 'Expected nonfinite gradient alert.'
Assert-True (@($alerts | Where-Object Kind -eq 'gpu_stalled').Count -ge 1) 'Expected GPU stalled alert.'
Assert-True (@($alerts | Where-Object Kind -eq 'runtime_exceeded').Count -ge 1) 'Expected runtime exceeded alert.'

$stateDir = Join-Path $env:TEMP ('monitor_common_test_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
try {
    $first = Update-MonitorAlertState -StateDir $stateDir -Alerts $alerts -SuppressMinutes 60
    $second = Update-MonitorAlertState -StateDir $stateDir -Alerts $alerts -SuppressMinutes 60
    Assert-True (@($first).Count -gt 0) 'First alert pass should emit alerts.'
    Assert-Equal 0 @($second).Count 'Second alert pass should suppress duplicates.'
}
finally {
    Remove-Item -LiteralPath $stateDir -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host 'monitor_common tests passed'
