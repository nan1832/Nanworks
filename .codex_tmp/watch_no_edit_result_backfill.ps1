param(
    [int]$IntervalSeconds = 300,
    [int]$MaxLoops = 180
)

$ErrorActionPreference = "Continue"
$Workspace = Split-Path -Parent $PSScriptRoot
$Ssh = "C:\WINDOWS\System32\OpenSSH\ssh.exe"
$Key = Join-Path ([Environment]::GetFolderPath("UserProfile")) ".ssh\id_ed25519_bridge"
$Login = "ph_teacher3@10.68.162.201"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$LogPath = Join-Path $PSScriptRoot "watch_no_edit_result_backfill.log"

$EvqaRoot = "/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/no_edit_full_evqa_alt_7models_g07_fixed_20260612_105148"
$MmkeRoot = "/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/no_edit_mmke_alt_eval_7models_20260612_161034"
$EvqaMd = Join-Path $Workspace "md\Location\no_edit_full_evqa_alt_7models_eval_manual.md"
$MmkeMd = Join-Path $Workspace "md\Location\no_edit_mmke_alt_7models_eval_manual.md"

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

function Read-RemoteCsv {
    param([string]$Path)
    $text = Invoke-G07 "cat '$Path' 2>/dev/null || true"
    if ([string]::IsNullOrWhiteSpace($text) -or $text -notmatch "model,") {
        return @()
    }
    try {
        return @($text.Trim() -split "`n" | ConvertFrom-Csv)
    }
    catch {
        Write-Log "CSV parse failed for $Path : $($_.Exception.Message)"
        return @()
    }
}

function Get-RowValue {
    param($Row, [string]$Name)
    $prop = $Row.PSObject.Properties[$Name]
    if ($null -eq $prop) {
        return ""
    }
    return $prop.Value
}

function Format-Metric {
    param($Value)
    if ($null -eq $Value -or [string]::IsNullOrWhiteSpace([string]$Value)) {
        return "-"
    }
    $num = 0.0
    if ([double]::TryParse([string]$Value, [ref]$num)) {
        return ("{0:F2}" -f $num)
    }
    return [string]$Value
}

function Replace-Section {
    param(
        [string]$Path,
        [string]$StartMarker,
        [string]$EndMarker,
        [string]$Section
    )
    $content = [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8)
    $block = "$StartMarker`n$Section`n$EndMarker"
    $pattern = [regex]::Escape($StartMarker) + ".*?" + [regex]::Escape($EndMarker)
    if ($content -match $pattern) {
        $content = [regex]::Replace(
            $content,
            $pattern,
            [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $block },
            [System.Text.RegularExpressions.RegexOptions]::Singleline
        )
    }
    else {
        $content = $content.TrimEnd() + "`n`n" + $block + "`n"
    }
    [System.IO.File]::WriteAllText($Path, $content, $Utf8NoBom)
}

function Build-EvqaSection {
    param([array]$Rows)
    $lines = @()
    $lines += "## Results Backfill"
    $lines += ""
    $lines += "Source server directory: $EvqaRoot"
    $lines += ""
    $lines += "Backfill time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    $lines += ""
    $lines += "| Model | Eval samples | Rel-alt | T-Gen-alt | M-Gen-alt | T-Loc | M-Loc | Average | Status |"
    $lines += "|---|---:|---:|---:|---:|---:|---:|---:|---|"
    foreach ($r in $Rows) {
        $lines += "| $(Get-RowValue $r 'model') | $(Get-RowValue $r 'eval_samples') | $(Format-Metric (Get-RowValue $r 'Rel')) | $(Format-Metric (Get-RowValue $r 'T-Gen')) | $(Format-Metric (Get-RowValue $r 'M-Gen')) | $(Format-Metric (Get-RowValue $r 'T-Loc')) | $(Format-Metric (Get-RowValue $r 'M-Loc')) | $(Format-Metric (Get-RowValue $r 'Average')) | $(Get-RowValue $r 'status') |"
    }
    return ($lines -join "`n")
}

function Build-MmkeSection {
    param([array]$Rows)
    $lines = @()
    $lines += "## Results Backfill"
    $lines += ""
    $lines += "Source server directory: $MmkeRoot"
    $lines += ""
    $lines += "Split: eval. Backfill time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    $lines += ""
    $lines += "| Task | Split | Model | Samples | Rel-alt | T-Gen-alt | M-Gen-alt | T-Loc | M-Loc | Average | Status |"
    $lines += "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|"
    foreach ($r in $Rows) {
        $lines += "| $(Get-RowValue $r 'task') | $(Get-RowValue $r 'split') | $(Get-RowValue $r 'model') | $(Get-RowValue $r 'eval_samples') | $(Format-Metric (Get-RowValue $r 'Rel')) | $(Format-Metric (Get-RowValue $r 'T-Gen')) | $(Format-Metric (Get-RowValue $r 'M-Gen')) | $(Format-Metric (Get-RowValue $r 'T-Loc')) | $(Format-Metric (Get-RowValue $r 'M-Loc')) | $(Format-Metric (Get-RowValue $r 'Average')) | $(Get-RowValue $r 'status') |"
    }
    return ($lines -join "`n")
}

$evqaDone = $false
$mmkeDone = $false
Write-Log "watcher started interval=$IntervalSeconds max_loops=$MaxLoops"

for ($i = 1; $i -le $MaxLoops; $i++) {
    try {
        if (-not $evqaDone) {
            $rows = Read-RemoteCsv "$EvqaRoot/no_edit_full_evqa_alt_7models_metrics.csv"
            $llava = @($rows | Where-Object { (Get-RowValue $_ "model") -eq "llava-v1.5-7b" }) | Select-Object -First 1
            if ($rows.Count -ge 7 -and $llava -and (Get-RowValue $llava "status") -eq "DONE") {
                Replace-Section $EvqaMd "<!-- NO_EDIT_EVQA_RESULTS_START -->" "<!-- NO_EDIT_EVQA_RESULTS_END -->" (Build-EvqaSection $rows)
                Write-Log "EVQA results backfilled"
                $evqaDone = $true
            }
            else {
                $status = if ($llava) { Get-RowValue $llava "status" } else { "missing" }
                Write-Log "EVQA not ready rows=$($rows.Count) llava_status=$status"
            }
        }

        if (-not $mmkeDone) {
            $rows = Read-RemoteCsv "$MmkeRoot/no_edit_mmke_alt_7models_metrics.csv"
            $notDone = @($rows | Where-Object { (Get-RowValue $_ "status") -ne "DONE" })
            if ($rows.Count -ge 14 -and $notDone.Count -eq 0) {
                Replace-Section $MmkeMd "<!-- NO_EDIT_MMKE_RESULTS_START -->" "<!-- NO_EDIT_MMKE_RESULTS_END -->" (Build-MmkeSection $rows)
                Write-Log "MMKE results backfilled"
                $mmkeDone = $true
            }
            else {
                Write-Log "MMKE not ready rows=$($rows.Count) not_done=$($notDone.Count)"
            }
        }

        if ($evqaDone -and $mmkeDone) {
            Write-Log "watcher complete"
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

Write-Log "watcher reached max loops evqa_done=$evqaDone mmke_done=$mmkeDone"
