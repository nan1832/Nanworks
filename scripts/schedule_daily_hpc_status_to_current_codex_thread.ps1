$ErrorActionPreference = "Stop"

# VS Code Codex thread that requested this daily status report.
$ThreadId = "019f6358-31e4-78d1-9732-919c10a576e6"
$Workspace = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $env:USERPROFILE ".codex\scheduled-task-logs"
$LogFile = Join-Path $LogDir "daily-hpc-status-3178538-3178423.log"

$MessageBase64 = "6K+35Y+q6K+75qOA5p+l5pyN5Yqh5Zmo5a6e6aqM54q25oCB5bm25Zyo5b2T5YmN5a+56K+d5Lit5oql5ZGK77yaCjEuIEpvYiAzMTc4NTM4IC8gRVZRQS1waWxvdDUwMCDDlyBMTGFWQSDnmoTlvZPliY3orq3nu4PmiJbor4TmtYvpmLbmrrXjgIHmqKHlnovlsYLjgIFlcG9jaC9zdGVw44CB5a6M5oiQ5qCH6K6w44CB5LiL5LiA5q2l6Zif5YiX5Y+K5piv5ZCm5a2Y5ZyoIE9PTeOAgW5vbmZpbml0ZeOAgVRyYWNlYmFja+OAgeejgeebmOmUmeivr+aIluWNoeS9j++8mwoyLiBKb2IgMzE3ODUzOCDkuI4gSm9iIDMxNzg0MjMg5ZCE6Ieq5omA5Zyo6IqC54K55ZKMIEdQVSDnmoTmgLvmmL7lrZjjgIHlt7LnlKjmmL7lrZjjgIHnqbrpl7LmmL7lrZjjgIFHUFUg5Yip55So546H77ybCjMuIOWIhuWIq+WIl+WHuuaIkeeahOWunumqjOS4u+i/m+eoi+aYvuWtmOWNoOeUqOS4juWFtuS7lui/m+eoi+WQiOiuoeWNoOeUqO+8mwo0LiDlpoLmnpzku7vliqHmraPlnKjnrYnlvoXvvIzor7TmmI7lhbfkvZPpl6jmp5vlkoznrYnlvoXljp/lm6DjgIIK5LuF5omn6KGM5Y+q6K+75p+l6K+i77yM5LiN5ZCv5Yqo44CB5YGc5q2i44CB6YeN5ZCv5oiW5L+u5pS55Lu75L2V5pyN5Yqh5Zmo6L+b56iL44CB6ISa5pys44CB6YWN572u44CB6Zif5YiX5ZKM5paH5Lu244CC5oql5ZGK5p+l6K+i5pe255qE5YyX5Lqs5pe26Ze044CC"
$Message = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($MessageBase64))

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

$Codex = Get-Command codex -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1
if (-not $Codex) {
    $Codex = Get-ChildItem -Path (Join-Path $env:USERPROFILE ".vscode\extensions\openai.chatgpt-*\bin\windows-x86_64\codex.exe") -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -ExpandProperty FullName -First 1
}
if (-not $Codex -or -not (Test-Path -LiteralPath $Codex)) {
    throw "Cannot locate the Codex CLI executable."
}

$Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"
Add-Content -LiteralPath $LogFile -Encoding UTF8 -Value "[$Timestamp] Queueing daily status request to thread $ThreadId"

$Output = & $Codex queue --thread $ThreadId --message $Message -C $Workspace 2>&1
$ExitCode = $LASTEXITCODE
$Output | ForEach-Object { Add-Content -LiteralPath $LogFile -Encoding UTF8 -Value ([string]$_) }
Add-Content -LiteralPath $LogFile -Encoding UTF8 -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')] ExitCode=$ExitCode`r`n"

if ($ExitCode -ne 0) {
    exit $ExitCode
}
