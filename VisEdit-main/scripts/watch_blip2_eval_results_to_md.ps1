param(
  [string]$MdPath = "md/glodenlayer/Bridge30_RequestOnly_BLIP2_FullLayerSweep_训练评测手册.md",
  [int]$PollSeconds = 600,
  [string]$SshKey = "$env:USERPROFILE\.ssh\id_ed25519_bridge",
  [string]$SshHost = "bridge-server",
  [string]$GpuHost = "g07",
  [string]$OutRoot = "/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/bridge_request_only_layer_sweep/blip2",
  [string]$ModelName = "blip2-opt-2.7b"
)

$ErrorActionPreference = "Stop"

$sshExe = "C:\Windows\System32\OpenSSH\ssh.exe"
$logPath = Join-Path (Split-Path -Parent $PSCommandPath) "watch_blip2_eval_results_to_md.log"

function Write-Log {
  param([string]$Message)
  $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
  Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
}

function Invoke-RemoteBash {
  param([string]$Script)
  $normalized = $Script -replace "`r`n", "`n"
  $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($normalized))
  & $sshExe -i $SshKey -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=10 $SshHost "ssh -o BatchMode=yes -o ConnectTimeout=10 $GpuHost 'printf %s $b64 | base64 -d | bash'"
}

function Invoke-RemotePython {
  param([string]$Script)
  $normalized = $Script -replace "`r`n", "`n"
  $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($normalized))
  & $sshExe -i $SshKey -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=10 $SshHost "ssh -o BatchMode=yes -o ConnectTimeout=10 $GpuHost 'printf %s $b64 | base64 -d | python3 -'"
}

function Get-RemoteStatus {
  $statusScript = @"
OUT="$OutRoot"
if [ -f "`$OUT/FULL_LAYER_TARGET0003_FAILED.txt" ]; then
  echo "STATE=FAILED"
  cat "`$OUT/FULL_LAYER_TARGET0003_FAILED.txt"
  exit 0
fi
if [ -f "`$OUT/FULL_LAYER_TARGET0003_DONE.txt" ]; then
  echo "STATE=DONE"
else
  echo "STATE=RUNNING"
fi
echo "SUMMARY_TMP_LINES=`$(test -f "`$OUT/eval/selected_eval_summary.tsv.tmp" && wc -l < "`$OUT/eval/selected_eval_summary.tsv.tmp" || echo 0)"
echo "SUMMARY_LINES=`$(test -f "`$OUT/eval/selected_eval_summary.tsv" && wc -l < "`$OUT/eval/selected_eval_summary.tsv" || echo 0)"
for split in train_request val_request val_full; do
  manifest_count=`$(find "`$OUT/eval/`$split" -name eval_manifest.json -type f 2>/dev/null | wc -l)
  result_count=`$(find "`$OUT/eval/`$split" -path "*/single_edit/mean_results.json" -type f 2>/dev/null | wc -l)
  echo "MANIFEST_`$split=`$manifest_count"
  echo "MEAN_`$split=`$result_count"
done
"@
  Invoke-RemoteBash $statusScript
}

function Get-RemoteResultsMarkdown {
  $python = @"
import csv
import json
import pathlib
from datetime import datetime

out = pathlib.Path("$OutRoot")
model_name = "$ModelName"
splits = ["train_request", "val_request", "val_full"]

def selected_file(layer):
    candidates = [
        out / f"layer_{layer}_target0003" / "selected_checkpoint.tsv",
        out / f"layer_{layer}_ep200" / "selected_checkpoint.tsv",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None

def read_selected(layer):
    path = selected_file(layer)
    if path is None:
        return {
            "layer": layer,
            "status": "MISSING",
            "epoch": "",
            "ema_loss": "",
            "diff": "",
            "checkpoint": "",
        }
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    row = rows[-1]
    return {
        "layer": layer,
        "status": row["status"],
        "epoch": row["epoch"],
        "ema_loss": row["ema_loss"],
        "diff": row["diff"],
        "checkpoint": pathlib.Path(row["checkpoint"]).name,
    }

def read_acc(split, layer):
    result = (
        out
        / "eval"
        / split
        / f"layer_{layer}"
        / "vead"
        / model_name
        / f"{split}_l{layer}_target0003"
        / "single_edit"
        / "mean_results.json"
    )
    if not result.exists():
        return "", ""
    data = json.loads(result.read_text(encoding="utf-8"))
    acc = data.get("reliability", {}).get("acc", "")
    count = data.get("sample_count", "")
    if isinstance(acc, float):
        acc = f"{acc:.4f}"
    return acc, count

selected_rows = [read_selected(layer) for layer in range(32)]

eval_rows = []
for row in selected_rows:
    layer = row["layer"]
    metrics = {}
    counts = {}
    for split in splits:
        acc, count = read_acc(split, layer)
        metrics[split] = acc
        counts[split] = count
    eval_rows.append((row, metrics, counts))

done_file = out / "FULL_LAYER_TARGET0003_DONE.txt"
done_text = done_file.read_text(encoding="utf-8").strip().replace("\n", "<br>") if done_file.exists() else ""

print(f"自动回填时间：`{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")
print()
print(f"远端结果目录：`{out}`")
if done_text:
    print()
    print(f"完成标记：{done_text}")
print()
print("### 12.1 Selected Checkpoints")
print()
print("| Layer | Status | Epoch | EMA Loss | Diff | Checkpoint |")
print("|---:|---|---:|---:|---:|---|")
for row in selected_rows:
    print(f"| {row['layer']} | {row['status']} | {row['epoch']} | {row['ema_loss']} | {row['diff']} | `{row['checkpoint']}` |")

print()
print("### 12.2 Evaluation Results")
print()
print("| Layer | Status | Epoch | EMA Loss | train_request acc | val_request acc | val_full acc |")
print("|---:|---|---:|---:|---:|---:|---:|")
for row, metrics, counts in eval_rows:
    print(
        f"| {row['layer']} | {row['status']} | {row['epoch']} | {row['ema_loss']} | "
        f"{metrics['train_request']} | {metrics['val_request']} | {metrics['val_full']} |"
    )

print()
print("样本数：`train_request=30`，`val_request=70`，`val_full=70`。这里的 acc 来自各 split 的 `single_edit/mean_results.json` 中 `reliability.acc`。")
print()
print("注意：当前 `val_request` 与 `val_full` 的 request/reliability 样本一致，且 generality/locality 为空，因此两列 reliability acc 预期相同。")
"@
  Invoke-RemotePython $python
}

function Update-Markdown {
  param([string]$Markdown)
  $resolved = (Resolve-Path -LiteralPath $MdPath).Path
  $text = [IO.File]::ReadAllText($resolved, [Text.Encoding]::UTF8)
  $start = "<!-- REQUEST_ONLY_BLIP2_SWEEP_RESULTS_START -->"
  $end = "<!-- REQUEST_ONLY_BLIP2_SWEEP_RESULTS_END -->"
  $replacement = "$start`r`n`r`n$Markdown`r`n`r`n$end"
  $pattern = "(?s)<!-- REQUEST_ONLY_BLIP2_SWEEP_RESULTS_START -->.*?<!-- REQUEST_ONLY_BLIP2_SWEEP_RESULTS_END -->"
  if ([regex]::IsMatch($text, $pattern)) {
    $newText = [regex]::Replace($text, $pattern, [Text.RegularExpressions.MatchEvaluator]{ param($m) $replacement })
  } else {
    $newText = $text.TrimEnd() + "`r`n`r`n## 12. 选用 checkpoint 与评测结果`r`n`r`n$replacement`r`n"
  }
  $utf8NoBom = [Text.UTF8Encoding]::new($false)
  [IO.File]::WriteAllText($resolved, $newText, $utf8NoBom)
}

Write-Log "watcher started md=$MdPath poll=${PollSeconds}s out=$OutRoot model=$ModelName"

while ($true) {
  try {
    $status = Get-RemoteStatus
    $statusText = ($status -join " | ")
    Write-Log "status: $statusText"

    if ($status -match "STATE=FAILED") {
      Write-Log "remote evaluation failed; watcher stopped"
      break
    }

    if ($status -match "STATE=DONE") {
      Write-Log "remote evaluation done; collecting markdown"
      $markdown = (Get-RemoteResultsMarkdown) -join "`r`n"
      Update-Markdown $markdown
      Write-Log "markdown updated"
      break
    }
  } catch {
    Write-Log "error: $($_.Exception.Message)"
  }

  Start-Sleep -Seconds $PollSeconds
}
