param(
    [int]$IntervalSeconds = 300,
    [int]$MaxLoops = 288
)

$ErrorActionPreference = "Continue"
$Workspace = Split-Path -Parent $PSScriptRoot
$Ssh = "C:\WINDOWS\System32\OpenSSH\ssh.exe"
$Scp = "C:\WINDOWS\System32\OpenSSH\scp.exe"
$Key = Join-Path ([Environment]::GetFolderPath("UserProfile")) ".ssh\id_ed25519_bridge"
$Login = "ph_teacher3@10.68.162.201"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

$MmkeNoEditRoot = "/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/no_edit_mmke_alt_eval_7models_20260612_161034"
$LocalNoEditDir = Join-Path $Workspace "downloads\mmke_no_edit_alt_eval_7models_20260612_161034"
$StartedFlag = Join-Path $PSScriptRoot "mmke_visual_top3_union_started.flag"
$LogPath = Join-Path $PSScriptRoot "chain_mmke_no_edit_to_visual_top3.log"
$Watcher = Join-Path $PSScriptRoot "watch_no_edit_result_backfill.ps1"

function Write-Log {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    [System.IO.File]::AppendAllText($LogPath, $line + [Environment]::NewLine, $Utf8NoBom)
}

function Invoke-G07 {
    param([string]$Script)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Script)
    $b64 = [Convert]::ToBase64String($bytes)
    $remote = "ssh -o BatchMode=yes -o ConnectTimeout=5 g07 'echo $b64 | base64 -d | bash'"
    $out = & $Ssh -i $Key -o StrictHostKeyChecking=no -o ConnectTimeout=10 $Login $remote 2>&1
    return ($out -join "`n")
}

function Get-RemoteCsvRows {
    $csvText = Invoke-G07 "cat '$MmkeNoEditRoot/no_edit_mmke_alt_7models_metrics.csv' 2>/dev/null || true"
    if ([string]::IsNullOrWhiteSpace($csvText) -or $csvText -notmatch "model,") {
        return @()
    }
    try {
        return @($csvText.Trim() -split "`n" | ConvertFrom-Csv)
    }
    catch {
        Write-Log "CSV parse failed: $($_.Exception.Message)"
        return @()
    }
}

function Get-RowValue {
    param($Row, [string]$Name)
    $prop = $Row.PSObject.Properties[$Name]
    if ($null -eq $prop) { return "" }
    return $prop.Value
}

function Test-MmkeDone {
    $rows = Get-RemoteCsvRows
    $notDone = @($rows | Where-Object { (Get-RowValue $_ "status") -ne "DONE" })
    Write-Log "MMKE no-edit poll rows=$($rows.Count) not_done=$($notDone.Count)"
    return ($rows.Count -ge 14 -and $notDone.Count -eq 0)
}

function Sync-NoEditSummary {
    New-Item -ItemType Directory -Force -Path $LocalNoEditDir | Out-Null
    & $Scp -i $Key -o StrictHostKeyChecking=no -o ConnectTimeout=10 `
        "${Login}:${MmkeNoEditRoot}/no_edit_mmke_alt_7models_metrics.csv" `
        "${Login}:${MmkeNoEditRoot}/no_edit_mmke_alt_7models_metrics.md" `
        $LocalNoEditDir 2>&1 | ForEach-Object { Write-Log "scp: $_" }
    if (Test-Path $Watcher) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $Watcher -IntervalSeconds 1 -MaxLoops 1 2>&1 |
            ForEach-Object { Write-Log "backfill: $_" }
    }
}

function Start-MmkeVisualTop3 {
    if (Test-Path $StartedFlag) {
        Write-Log "training already started: $([System.IO.File]::ReadAllText($StartedFlag))"
        return
    }

    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $trainRoot = "/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_$stamp"
    [System.IO.File]::WriteAllText($StartedFlag, $trainRoot, $Utf8NoBom)
    Write-Log "starting MMKE visual top3 union training: $trainRoot"

    $remoteScript = @"
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main || exit 1
RUN_ROOT="$trainRoot" GPU_ID=1 bash scripts/launch_mmke_visual_top3_union_train_eval_g07.sh
"@
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($remoteScript)
    $b64 = [Convert]::ToBase64String($bytes)
    $remote = "ssh -o BatchMode=yes -o ConnectTimeout=5 g07 'echo $b64 | base64 -d | bash'"
    & $Ssh -i $Key -o StrictHostKeyChecking=no -o ConnectTimeout=10 $Login $remote 2>&1 |
        ForEach-Object { Write-Log "train: $_" }
}

Write-Log "chain watcher started interval=$IntervalSeconds max_loops=$MaxLoops"

for ($i = 1; $i -le $MaxLoops; $i++) {
    try {
        if (Test-MmkeDone) {
            Write-Log "MMKE no-edit DONE; syncing summary"
            Sync-NoEditSummary
            Start-MmkeVisualTop3
            Write-Log "chain watcher finished"
            exit 0
        }
    }
    catch {
        Write-Log "loop error: $($_.Exception.Message)"
    }

    if ($i -lt $MaxLoops) {
        Start-Sleep -Seconds $IntervalSeconds
    }
}

Write-Log "chain watcher reached max loops without MMKE no-edit completion"
