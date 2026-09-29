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
$logPath = Join-Path $stateDir 'mmke_entity_epoch50_alerts.log'

function Invoke-EntityProbe {
    $remote = @'
ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000
STATUS="$ROOT/mmke_entity_3p4_pending_job3044841_status.log"
CSV="$ROOT/mmke_entity_3p4_pending_job3044841_layer_status.csv"

echo "=== PROBE mmke_entity_epoch50 ==="
date '+PROBE_TIME=%F %T %Z'
echo "=== SLURM ==="
squeue -j 3044841 -o "%.18i %.9P %.25j %.8T %.10M %.6D %R" 2>/dev/null || true
echo "=== GPU ==="
nvidia-smi --query-gpu=index,name,memory.used,memory.free,utilization.gpu --format=csv,noheader,nounits 2>/dev/null || true

line=$(ps -eo pid,ppid,stat,etimes,cmd --no-headers | grep 'run_evqa_pilot500_blip2_visedit_sweep.py' | grep 'mmke_entity' | grep -v grep | head -n 1)
if [ -z "$line" ]; then
  echo NO_CURRENT_PROCESS
else
  pid=$(echo "$line" | awk '{print $1}')
  stat=$(echo "$line" | awk '{print $3}')
  etimes=$(echo "$line" | awk '{print $4}')
  cmd=$(echo "$line" | cut -d' ' -f5-)
  model=$(echo "$cmd" | sed -n 's/.*--model-name \([^ ]*\).*/\1/p' | head -n 1)
  layer=$(echo "$cmd" | sed -n 's/.*--layers \([0-9][0-9]*\).*/\1/p' | head -n 1)
  out=$(echo "$cmd" | sed -n 's/.*--out-root \([^ ]*\).*/\1/p' | head -n 1)
  echo "CURRENT model=$model dataset=mmke-entity layer=$layer etimes=$etimes pid=$pid stat=$stat"
  latest=$(find "$out" -maxdepth 1 -type f -name "*L${layer}*log" -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -n 1 | cut -d' ' -f2-)
  if [ -n "$latest" ]; then
    age=$(($(date +%s)-$(stat -c %Y "$latest")))
    echo "CURRENT_LOG=$latest"
    echo "CURRENT_LOG_AGE_SECONDS=$age"
    echo "=== CURRENT LOG KEY TAIL ==="
    grep -aE '\[ckpt\]|Epoch [0-9]+:|Waiting data:|Traceback|Error|CUDA|OutOfMemory|SANITIZE|grad_bad|loss=' "$latest" 2>/dev/null | tail -n 100 || true
  else
    echo CURRENT_LOG_MISSING
  fi
fi

echo "=== STATUS TAIL ==="
tail -n 100 "$STATUS" 2>/dev/null || echo "missing status log: $STATUS"
echo "=== CSV TAIL ==="
tail -n 30 "$CSV" 2>/dev/null || echo "missing csv: $CSV"
'@
    $payload = $remote -replace "`r", ''
    return ($payload | & $sshExe -i $KeyPath $SshHost "ssh $Node bash -s" 2>&1 | Out-String)
}

while ($true) {
    try {
        $text = Invoke-EntityProbe
        $alerts = Get-ExperimentMonitorAlerts `
            -Text $text `
            -GpuIndex 1 `
            -HighMemoryUsedMiB 76000 `
            -LowUtilPercent 5 `
            -WaitingDataSeconds 1800 `
            -MaxRuntimeSeconds 0 `
            -StaleLogSeconds 3600 `
            -ExperimentName 'MMKE-entity/epoch50'
        $emit = Update-MonitorAlertState -StateDir $stateDir -Alerts $alerts -SuppressMinutes $SuppressMinutes
        if (@($emit).Count -gt 0) {
            Write-MonitorAlerts -Alerts $emit -LogPath $logPath -Beep:$Beep
        }
        else {
            Write-Host ("[{0}] MMKE-entity/epoch50 monitor ok; alerts={1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), @($alerts).Count) -ForegroundColor Green
        }
    }
    catch {
        $alert = New-MonitorAlert 'MMKE-entity/epoch50' 'monitor_error' $_.Exception.Message 'MMKE-entity/epoch50|monitor_error'
        $emit = Update-MonitorAlertState -StateDir $stateDir -Alerts @($alert) -SuppressMinutes $SuppressMinutes
        Write-MonitorAlerts -Alerts $emit -LogPath $logPath -Beep:$Beep
    }

    if ($Once) { break }
    Start-Sleep -Seconds $IntervalSeconds
}
