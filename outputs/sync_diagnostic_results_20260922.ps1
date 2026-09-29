param(
    [Parameter(Mandatory = $true)][string]$ManifestPath,
    [Parameter(Mandatory = $true)][string]$LocalRoot,
    [string]$Node = "g08",
    [string]$BridgeHost = "bridge-server",
    [string]$KeyPath = "$HOME/.ssh/id_ed25519_bridge",
    [string]$BridgeStageRoot = "/var/tmp/ph_teacher3/codex_sync_staging",
    [switch]$IncludeCheckpoint,
    [switch]$DryRun,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$manifest = Get-Content -Raw -LiteralPath $ManifestPath | ConvertFrom-Json
$complete = @($manifest.layers | Where-Object { $_.diagnostic_only -eq $true -and $_.evaluation_verified -eq $true -and $_.training_complete_50_epochs -eq $false })
if ($complete.Count -ne 1) { throw 'Expected exactly one verified diagnostic evaluation, not a normal completed training run.' }
$rootFull = [IO.Path]::GetFullPath($LocalRoot).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
$remoteStage = "$BridgeStageRoot/$([guid]::NewGuid().ToString('N'))"
$remoteStageFiles = [Collections.Generic.List[string]]::new()

function Assert-ChildPath([string]$Candidate, [string]$Root) {
    $candidateFull = [IO.Path]::GetFullPath($Candidate)
    $prefix = $Root + [IO.Path]::DirectorySeparatorChar
    if (-not $candidateFull.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing path outside LocalRoot: $candidateFull"
    }
    return $candidateFull
}

function Assert-RemotePath([string]$Candidate) {
    if (-not $Candidate.StartsWith('/') -or $Candidate.IndexOfAny([char[]]"`r`n`t'`"") -ge 0) {
        throw "Unsafe remote path: $Candidate"
    }
}

foreach ($layer in $complete) {
    $layerName = "layer_{0:D2}" -f [int]$layer.layer
    $destination = Assert-ChildPath (Join-Path $rootFull (Join-Path $manifest.dataset (Join-Path $layer.model $layerName))) $rootFull
    if ((Test-Path -LiteralPath $destination) -and -not $Force) {
        throw "Destination exists; compare hashes and use -Force explicitly: $destination"
    }
    $artifacts = @($layer.artifacts)
    if ($IncludeCheckpoint -and $layer.selected_checkpoint) {
        if (-not $layer.selected_checkpoint.sha256) {
            throw "Checkpoint hash missing for $layerName; rebuild the manifest with --hash-checkpoints"
        }
        $artifacts += $layer.selected_checkpoint
    }

    if ($DryRun) {
        foreach ($artifact in $artifacts) { Write-Output "DRY_RUN`t$($artifact.path)`t$($artifact.relative_path)`t$destination" }
        continue
    }

    $stage = "$destination.partial"
    if (Test-Path -LiteralPath $stage) { throw "Staging directory already exists: $stage" }
    New-Item -ItemType Directory -Path $stage -Force | Out-Null
    try {
        Assert-RemotePath $remoteStage
        & ssh.exe -i $KeyPath $BridgeHost "mkdir -p '$remoteStage'"
        if ($LASTEXITCODE -ne 0) { throw "Cannot create bridge staging directory: $remoteStage" }
        $artifactIndex = 0
        foreach ($artifact in $artifacts) {
            Assert-RemotePath ([string]$artifact.path)
            $relative = ([string]$artifact.relative_path).Replace('/', [IO.Path]::DirectorySeparatorChar)
            $localFile = Assert-ChildPath (Join-Path $stage $relative) ([IO.Path]::GetFullPath($stage).TrimEnd([IO.Path]::DirectorySeparatorChar))
            $localParent = Split-Path -Parent $localFile
            if (-not (Test-Path -LiteralPath $localParent)) { New-Item -ItemType Directory -Path $localParent -Force | Out-Null }
            $stageName = ("artifact_{0:D4}.bin" -f $artifactIndex)
            $artifactIndex += 1
            $remoteStageFile = "$remoteStage/$stageName"
            $remoteStageFiles.Add($remoteStageFile)
            $innerCommand = "cat -- '$($artifact.path)'"
            $innerEncoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($innerCommand))
            $bridgeCommand = "ssh '$Node' 'echo $innerEncoded | base64 -d | bash' > '$remoteStageFile'"
            & ssh.exe -i $KeyPath $BridgeHost $bridgeCommand
            if ($LASTEXITCODE -ne 0) { throw "node-to-bridge stream failed for $($artifact.path)" }
            & scp.exe -q -i $KeyPath "$BridgeHost`:$remoteStageFile" $localFile
            if ($LASTEXITCODE -ne 0) { throw "bridge-to-local copy failed for $($artifact.path)" }
            $actualSize = (Get-Item -LiteralPath $localFile).Length
            if ($actualSize -ne [int64]$artifact.size) { throw "Size mismatch for $($artifact.path)" }
            $actualHash = (Get-FileHash -LiteralPath $localFile -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($actualHash -ne ([string]$artifact.sha256).ToLowerInvariant()) {
                throw "SHA-256 mismatch for $($artifact.path)"
            }
        }
        $hashes = Get-ChildItem -LiteralPath $stage -File -Recurse | Get-FileHash -Algorithm SHA256
        $hashes | Select-Object Hash, Path | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $stage "SHA256SUMS.json")
        if (Test-Path -LiteralPath $destination) { Remove-Item -LiteralPath $destination -Recurse -Force }
        Move-Item -LiteralPath $stage -Destination $destination
    }
    catch {
        throw
    }
    finally {
        foreach ($remoteFile in $remoteStageFiles) {
            & ssh.exe -i $KeyPath $BridgeHost "rm -f -- '$remoteFile'" 2>$null
        }
        & ssh.exe -i $KeyPath $BridgeHost "rmdir -- '$remoteStage'" 2>$null
        $remoteStageFiles.Clear()
    }
}

Write-Output ("verified_layers={0} dry_run={1} include_checkpoint={2}" -f $complete.Count, $DryRun.IsPresent, $IncludeCheckpoint.IsPresent)
