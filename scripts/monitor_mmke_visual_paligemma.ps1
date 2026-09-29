param(
    [string]$SshHost = 'ph_teacher3@10.68.162.201',
    [string]$Node = 'g09',
    [string]$KeyPath = "$HOME\.ssh\id_ed25519_bridge",
    [int]$IntervalSeconds = 300,
    [switch]$Once,
    [switch]$Beep,
    [int]$SuppressMinutes = 30,
    [string]$AlertDir = 'md/Location/monitor_alerts'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'monitor_common.ps1')

$sshExe = Join-Path $env:WINDIR 'System32\OpenSSH\ssh.exe'
$stateDir = Join-Path $repoRoot $AlertDir
$logPath = Join-Path $stateDir 'mmke_visual_paligemma_alerts.log'

function Invoke-VisualProbe {
    $remote = @'
ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644/paligemma-3b
CTRL=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/paligemma_pending_followup_job3044208_20260713_204917
STATUS="$CTRL/paligemma_pending_followup_status.log"
CSV="$CTRL/paligemma_pending_followup_layer_status.csv"
WATCHDOG="$CTRL/paligemma_external_watchdog.log"

echo "=== PROBE mmke_visual_paligemma ==="
date '+PROBE_TIME=%F %T %Z'
echo "=== SLURM ==="
squeue -j 3044208 -o "%.18i %.9P %.25j %.8T %.10M %.6D %R" 2>/dev/null || true
echo "=== GPU ==="
nvidia-smi --query-gpu=index,name,memory.used,memory.free,utilization.gpu --format=csv,noheader,nounits 2>/dev/null || true
echo "=== WATCHDOG ==="
pgrep -af paligemma_job3044208_external_watchdog || echo NO_WATCHDOG

line=$(ps -eo pid,ppid,stat,etimes,cmd --no-headers | grep 'run_evqa_pilot500_blip2_visedit_sweep.py' | grep 'paligemma-3b' | grep -v grep | head -n 1)
if [ -z "$line" ]; then
  echo NO_CURRENT_PROCESS
else
  pid=$(echo "$line" | awk '{print $1}')
  stat=$(echo "$line" | awk '{print $3}')
  etimes=$(echo "$line" | awk '{print $4}')
  cmd=$(echo "$line" | cut -d' ' -f5-)
  layer=$(echo "$cmd" | sed -n 's/.*--layers \([0-9][0-9]*\).*/\1/p' | head -n 1)
  out=$(echo "$cmd" | sed -n 's/.*--out-root \([^ ]*\).*/\1/p' | head -n 1)
  mode=main
  echo "$out" | grep -q stable && mode=stable
  echo "CURRENT model=paligemma-3b dataset=mmke-visual mode=$mode layer=$layer etimes=$etimes pid=$pid stat=$stat"
  latest=$(find "$out" -maxdepth 1 -type f -name "*L${layer}*log" -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -n 1 | cut -d' ' -f2-)
  if [ -n "$latest" ]; then
    age=$(($(date +%s)-$(stat -c %Y "$latest")))
    echo "CURRENT_LOG=$latest"
    echo "CURRENT_LOG_AGE_SECONDS=$age"
    echo "=== CURRENT LOG KEY TAIL ==="
    grep -aE '\[ckpt\]|Epoch [0-9]+:|Waiting data:|Traceback|Error|CUDA|OutOfMemory|SANITIZE|grad_bad|loss=' "$latest" 2>/dev/null | tail -n 80 || true
  else
    echo CURRENT_LOG_MISSING
  fi
fi

echo "=== STATUS TAIL ==="
tail -n 80 "$STATUS" 2>/dev/null || echo "missing status log: $STATUS"
echo "=== CSV TAIL ==="
tail -n 30 "$CSV" 2>/dev/null || echo "missing csv: $CSV"
echo "=== WATCHDOG TAIL ==="
tail -n 30 "$WATCHDOG" 2>/dev/null || true
'@
    $payload = $remote -replace "`r", ''
    return ($payload | & $sshExe -i $KeyPath $SshHost "ssh $Node bash -s" 2>&1 | Out-String)
}

while ($true) {
    try {
        $text = Invoke-VisualProbe
        $alerts = Get-ExperimentMonitorAlerts `
            -Text $text `
            -GpuIndex 0 `
            -HighMemoryUsedMiB 76000 `
            -LowUtilPercent 5 `
            -WaitingDataSeconds 1800 `
            -MaxRuntimeSeconds 7200 `
            -StaleLogSeconds 1800 `
            -ExperimentName 'MMKE-visual/PaliGemma'
        $emit = Update-MonitorAlertState -StateDir $stateDir -Alerts $alerts -SuppressMinutes $SuppressMinutes
        if (@($emit).Count -gt 0) {
            Write-MonitorAlerts -Alerts $emit -LogPath $logPath -Beep:$Beep
        }
        else {
            Write-Host ("[{0}] MMKE-visual/PaliGemma monitor ok; alerts={1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), @($alerts).Count) -ForegroundColor Green
        }
    }
    catch {
        $alert = New-MonitorAlert 'MMKE-visual/PaliGemma' 'monitor_error' $_.Exception.Message 'MMKE-visual/PaliGemma|monitor_error'
        $emit = Update-MonitorAlertState -StateDir $stateDir -Alerts @($alert) -SuppressMinutes $SuppressMinutes
        Write-MonitorAlerts -Alerts $emit -LogPath $logPath -Beep:$Beep
    }

    if ($Once) { break }
    Start-Sleep -Seconds $IntervalSeconds
}
