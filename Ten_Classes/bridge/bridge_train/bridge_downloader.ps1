param(
  [string]$srcPath,
  [string]$destDir,
  [int]$batchSize = 8,
  [int]$sleepSec = 3,
  [int]$maxRetries = 6,
  [int]$timeoutSec = 120,
  [string]$userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TraeIDE/BridgeDownloader"
)
New-Item -ItemType Directory -Force -Path $destDir | Out-Null
$lines = Get-Content -Path $srcPath
$entries = @()
foreach ($line in $lines) {
  try { $obj = $line | ConvertFrom-Json } catch { $obj = $null }
  if ($obj -and $obj.image_name -and $obj.image_url) { $entries += $obj }
}
$unique = $entries | Group-Object image_name | ForEach-Object { $_.Group[0] }
$existing = 0
$pending = @()
foreach ($e in $unique) {
  $outfile = Join-Path $destDir $e.image_name
  if (Test-Path $outfile) { $existing++ } else { $pending += $e }
}
$retryMap = @{}
$downloaded = 0
$failedPermanently = @()
$attempt = 0
while ($pending.Count -gt 0) {
  $attempt++
  $batch = $pending | Select-Object -First $batchSize
  $remaining = $pending | Select-Object -Skip $batchSize
  $failedThisBatch = @()
  foreach ($e in $batch) {
    $outfile = Join-Path $destDir $e.image_name
    try {
      Invoke-WebRequest -Uri $e.image_url -OutFile $outfile -UseBasicParsing -TimeoutSec $timeoutSec -Headers @{ "User-Agent" = $userAgent; "Referer" = "https://commons.wikimedia.org" }
      $downloaded++
      Write-Output ("DOWNLOADED " + $e.image_name)
    } catch {
      $name = $e.image_name
      if (-not $retryMap.ContainsKey($name)) { $retryMap[$name] = 0 }
      $retryMap[$name] = $retryMap[$name] + 1
      $code = ""
      if ($_.Exception.Response -and $_.Exception.Response.StatusCode) { $code = $_.Exception.Response.StatusCode.value__ }
      Write-Output ("FAILED " + $name + " code=" + $code + " try=" + $retryMap[$name] + " msg=" + $_.Exception.Message)
      if ($retryMap[$name] -lt $maxRetries) {
        $failedThisBatch += $e
      } else {
        $failedPermanently += $e
      }
    }
    Start-Sleep -Seconds $sleepSec
  }
  $pending = $remaining + $failedThisBatch
  if ($failedThisBatch.Count -gt 0) {
    $retryAfter = 0
    foreach ($fe in $failedThisBatch) {
      if ($_.Exception -and $_.Exception.Response -and $_.Exception.Response.Headers) {
        $ra = $_.Exception.Response.Headers["Retry-After"]
        if ($ra) {
          $n = 0
          [int]::TryParse($ra, [ref]$n) | Out-Null
          if ($n -gt $retryAfter) { $retryAfter = $n }
        }
      }
    }
    $backoff = [Math]::Min($sleepSec * [Math]::Pow(2, $attempt), 300)
    if ($retryAfter -gt 0) { $backoff = [Math]::Max($backoff, $retryAfter) }
    Start-Sleep -Seconds [int]$backoff
  }
}
Write-Output ("SUMMARY total=" + $unique.Count + " downloaded=" + $downloaded + " skipped=" + $existing + " failed=" + $failedPermanently.Count)
