param(
    [string]$SshKey = "$env:USERPROFILE\.ssh\id_ed25519_bridge",
    [string]$BridgeHost = "bridge-server",
    [string]$GpuHost = "g07",
    [string]$OutRoot = "/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/llava",
    [int]$IntervalSeconds = 1800
)

$ErrorActionPreference = "SilentlyContinue"
$localLog = Join-Path $PSScriptRoot "llava_sweep_done_local.log"

function Write-LocalLog {
    param([string]$Message)
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $localLog -Value "[$stamp] $Message"
}

function Show-Notice {
    param([string]$Title, [string]$Message)
    try {
        $shell = New-Object -ComObject WScript.Shell
        [void]$shell.Popup($Message, 30, $Title, 64)
    } catch {
        try {
            & msg.exe $env:USERNAME "$Title $Message" | Out-Null
        } catch {
            Write-LocalLog "Notification failed: $Title $Message"
        }
    }
}

Write-LocalLog "Local watcher started. BridgeHost=$BridgeHost GpuHost=$GpuHost OutRoot=$OutRoot"

while ($true) {
    $remote = "OUT='$OutRoot'; if [ -f `"`$OUT/FULL_LAYER_TARGET0003_DONE.txt`" ]; then echo DONE; cat `"`$OUT/FULL_LAYER_TARGET0003_DONE.txt`"; elif [ -f `"`$OUT/FULL_LAYER_TARGET0003_FAILED.txt`" ]; then echo FAILED; cat `"`$OUT/FULL_LAYER_TARGET0003_FAILED.txt`"; else echo RUNNING; fi"
    $result = & ssh.exe -i $SshKey -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=20 $BridgeHost "ssh -o BatchMode=yes -o ConnectTimeout=20 $GpuHost '$remote'" 2>&1
    $text = ($result | Out-String).Trim()

    if ($text.StartsWith("DONE")) {
        Write-LocalLog $text
        Show-Notice "Bridge30 LLaVA 完成" "全层 target0003 训练与统一评测已完成。详情见服务器 DONE 文件。"
        break
    }

    if ($text.StartsWith("FAILED")) {
        Write-LocalLog $text
        Show-Notice "Bridge30 LLaVA 失败" "全层自动任务失败，请查看服务器 FAILED 文件和 eval/train 日志。"
        break
    }

    Write-LocalLog "Still running."
    Start-Sleep -Seconds $IntervalSeconds
}
