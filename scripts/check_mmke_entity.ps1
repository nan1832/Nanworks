param(
    [string]$SshHost = "bridge-server",
    [string]$KeyPath = "$HOME\.ssh\id_ed25519_bridge",
    [int]$Tail = 25,
    [string]$JobId = "3044841"
)

$remote = @'
ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000
STATUS="$ROOT/mmke_entity_3p4_pending_job3044841_status.log"
CSV="$ROOT/mmke_entity_3p4_pending_job3044841_layer_status.csv"
JOB_ID="__JOB_ID__"

echo "=== time ==="
date '+%F %T %Z'

echo
echo "=== slurm jobs ==="
squeue -u ph_teacher3 -o '%.18i %.9P %.35j %.8u %.2t %.12M %.12l %.6D %R' 2>/dev/null || true

echo
echo "=== mmke entity process ==="
ps -eo pid,ppid,stat,etime,cmd | egrep 'launch_mmke_entity_3p4_pending_epoch50_job3044841.sh|mmke_entity_top3_union_train_eval_7models_20260616_155000|run_evqa_pilot500_blip2_visedit_sweep.py' | grep -v egrep || true

echo
echo "=== job ${JOB_ID} gpu ==="
srun --jobid="$JOB_ID" --overlap bash -lc 'nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits' </dev/null 2>/dev/null || true

echo
echo "=== status tail ==="
tail -n __TAIL__ "$STATUS" 2>/dev/null || echo "missing status log: $STATUS"

echo
echo "=== layer csv tail ==="
tail -n 15 "$CSV" 2>/dev/null || echo "missing layer csv: $CSV"

echo
echo "=== newest train/eval log tail ==="
latest=$(find "$ROOT" -maxdepth 2 -type f \( -name 'train_L*_3p4_*.log' -o -name 'eval_L*_3p4_*.log' \) -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -n 1 | cut -d' ' -f2-)
if [ -n "$latest" ]; then
  echo "$latest"
  tail -n __TAIL__ "$latest" 2>/dev/null || true
else
  echo "no train/eval log found"
fi
'@

$remote = $remote.Replace("__TAIL__", [string]$Tail).Replace("__JOB_ID__", $JobId)
$remote | & C:\Windows\System32\OpenSSH\ssh.exe -i $KeyPath $SshHost "tr -d '\r' | bash -s"
