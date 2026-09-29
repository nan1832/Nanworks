param(
    [string]$SshHost = "bridge-server",
    [string]$KeyPath = "$HOME\.ssh\id_ed25519_bridge",
    [int]$Tail = 25
)

$remote = @'
ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644
STATUS="$ROOT/mmke_visual_3p4_pending_job3044208_status.log"
CSV="$ROOT/mmke_visual_3p4_pending_job3044208_layer_status.csv"

echo "=== time ==="
date '+%F %T %Z'

echo
echo "=== slurm jobs ==="
squeue -u ph_teacher3 -o '%.18i %.9P %.35j %.8u %.2t %.12M %.12l %.6D %R' 2>/dev/null || true

echo
echo "=== mmke visual process ==="
pgrep -af 'launch_mmke_visual_3p4_pending_epoch50_job3044208.sh|run_evqa_pilot500_blip2_visedit_sweep.py' || true

echo
echo "=== job 3044208 gpu ==="
srun --jobid=3044208 --overlap bash -lc 'nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits' </dev/null 2>/dev/null || true

echo
echo "=== status tail ==="
tail -n __TAIL__ "$STATUS" 2>/dev/null || echo "missing status log: $STATUS"

echo
echo "=== layer csv tail ==="
tail -n 15 "$CSV" 2>/dev/null || echo "missing layer csv: $CSV"

echo
echo "=== newest train log tail ==="
latest=$(find "$ROOT" -path '*/train_L*_3p4_*.log' -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -n 1 | cut -d' ' -f2-)
if [ -n "$latest" ]; then
  echo "$latest"
  tail -n __TAIL__ "$latest" 2>/dev/null || true
else
  echo "no train log found"
fi
'@

$remote = $remote.Replace("__TAIL__", [string]$Tail)
$remote | & C:\Windows\System32\OpenSSH\ssh.exe -i $KeyPath $SshHost "tr -d '\r' | bash -s"
