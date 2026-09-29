param(
    [string]$SshHost = "bridge-server",
    [string]$KeyPath = "$HOME\.ssh\id_ed25519_bridge",
    [int]$Tail = 18
)

$remote = @'
ssh g09 'TAIL_N=__TAIL__
VR=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_visual_top3_union_train_eval_7models_20260613_014644
ER=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000
PY=/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python

echo "=== time ==="
date "+%F %T %Z"

echo
echo "=== slurm jobs ==="
squeue -j 3044208,3044841 -o "%.18i %.9P %.20j %.8u %.2t %.12M %.6D %R" 2>/dev/null || true

echo
echo "=== gpu usage on g09 ==="
nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits

echo
echo "=== gpu processes ==="
nvidia-smi --query-compute-apps=gpu_uuid,pid,process_name,used_memory --format=csv,noheader,nounits 2>/dev/null || true

echo
echo "=== active mmke train processes ==="
ps -eo pid,ppid,stat,etime,cmd \
  | egrep "launch_mmke_visual_minigpt_repair|launch_mmke_visual_3p4|launch_mmke_entity|run_evqa_pilot500_blip2_visedit_sweep.py --out-root .*mmke_(visual|entity)" \
  | grep -v -E "egrep|grep -E" || true

echo
echo "=== process -> job/gpu mapping ==="
for p in $(ps -eo pid=,cmd= | grep "run_evqa_pilot500_blip2_visedit_sweep.py --out-root" | grep -E "mmke_(visual|entity)" | grep -v grep | awk "{print \$1}"); do
  cmd=$(tr "\0" " " < /proc/$p/cmdline 2>/dev/null)
  job=$(tr "\0" "\n" < /proc/$p/environ 2>/dev/null | sed -n "s/^SLURM_JOB_ID=//p" | tail -n 1)
  step_gpu=$(tr "\0" "\n" < /proc/$p/environ 2>/dev/null | sed -n "s/^SLURM_STEP_GPUS=//p" | tail -n 1)
  cuda=$(tr "\0" "\n" < /proc/$p/environ 2>/dev/null | sed -n "s/^CUDA_VISIBLE_DEVICES=//p" | tail -n 1)
  model=$(printf "%s\n" "$cmd" | sed -n "s/.*--model-name \([^ ]*\).*/\1/p")
  layer=$(printf "%s\n" "$cmd" | sed -n "s/.*--layers \([^ ]*\).*/\1/p")
  dataset=unknown
  printf "%s\n" "$cmd" | grep -q "mmke_visual" && dataset=MMKE-visual
  printf "%s\n" "$cmd" | grep -q "mmke_entity" && dataset=MMKE-entity
  echo "pid=$p job=$job step_gpu=$step_gpu cuda=$cuda dataset=$dataset model=$model layer=L$layer"
done

echo
echo "=== parsed progress ==="
"$PY" - "$VR" "$ER" <<PY
import os, re, sys, glob
vr, er = sys.argv[1], sys.argv[2]

def latest(pattern):
    files = glob.glob(pattern, recursive=True)
    return max(files, key=os.path.getmtime) if files else None

items = [
    ("MMKE-visual", latest(os.path.join(vr, "minigpt-4-vicuna-7b", "train_L*_repair_*.log"))),
    ("MMKE-entity", latest(os.path.join(er, "*", "train_L*_3p4_*.log"))),
]
for label, path in items:
    print(f"--- {label} ---")
    if not path:
        print("no train log found")
        continue
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        f.seek(max(0, size - 400000))
        data = f.read().decode("utf-8", "ignore")
    ckpts = re.findall(r"\[[^\]]+\] \[ckpt\].*", data)
    epochs = re.findall(r"Epoch\s+(\d+):\s+([0-9]+)%.*?\|\s*([0-9]+)/(\d+)", data)
    waits = re.findall(r"Waiting data: ([0-9]+) s", data)
    print(path)
    if ckpts:
        print("last_ckpt:", ckpts[-1])
    if epochs:
        e, pct, cur, total = epochs[-1]
        print(f"last_epoch_progress: epoch={e} {pct}% {cur}/{total}")
    if waits:
        print("last_wait_s:", waits[-1])
    print("mtime:", __import__("datetime").datetime.fromtimestamp(os.path.getmtime(path)).strftime("%F %T"), "size:", size)
PY

echo
echo "=== visual status tail ==="
vf=$(ls -t "$VR"/mmke_visual_minigpt_repair_*_status.log 2>/dev/null | head -n 1)
if [ -n "$vf" ]; then
  echo "--- $vf ---"
  tail -n "$TAIL_N" "$vf"
else
  echo "missing visual repair status"
fi

echo
echo "=== visual layer csv tail ==="
vc=$(ls -t "$VR"/mmke_visual_minigpt_repair_*_layer_status.csv 2>/dev/null | head -n 1)
if [ -n "$vc" ]; then
  echo "--- $vc ---"
  tail -n 12 "$vc"
else
  echo "missing visual repair csv"
fi

echo
echo "=== entity status tail ==="
tail -n "$TAIL_N" "$ER/mmke_entity_3p4_pending_job3044841_status.log" 2>/dev/null || true

echo
echo "=== entity layer csv tail ==="
tail -n 12 "$ER/mmke_entity_3p4_pending_job3044841_layer_status.csv" 2>/dev/null || true

echo
echo "=== recent hard errors, last 3h ==="
hit=0
for f in $(find "$VR" "$ER" -maxdepth 3 -type f \( -name "train*.log" -o -name "eval*.log" \) -mmin -180 2>/dev/null | sort); do
  if grep -qiE "Traceback|CUDA out of memory|OutOfMemory|No space left|Killed|RuntimeError|ValueError|AttributeError" "$f"; then
    hit=1
    echo "--- $f ---"
    grep -inE "Traceback|CUDA out of memory|OutOfMemory|No space left|Killed|RuntimeError|ValueError|AttributeError" "$f" | tail -n 8
  fi
done
[ "$hit" = 0 ] && echo "none"
'
'@

$remote = $remote.Replace("__TAIL__", [string]$Tail)
$remote | & C:\Windows\System32\OpenSSH\ssh.exe -i $KeyPath $SshHost "tr -d '\r' | bash -s"
