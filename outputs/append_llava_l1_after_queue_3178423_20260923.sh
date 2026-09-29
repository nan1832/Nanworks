#!/usr/bin/env bash
# One retry of MMKE-entity/LLaVA L1, only after the registered queue terminates normally.
set -euo pipefail
PROJ=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
ROOT=/tmp/ph_teacher3/formal_top3_stage2_job3126082_20260812
DEST=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/formal_top3_stage2_20260812/job3126082
if [[ ${1:-} == --validate ]]; then
  export VALIDATE_ONLY=1
else
  [[ ${SLURM_JOB_ID:-} == 3178423 && $(hostname -s) == g07 ]] || exit 20
  exec 8>"$ROOT/l1_tail_followup_20260923.lock"
  flock -n 8 || { echo ALREADY_REGISTERED; exit 21; }
fi
export PROJ ROOT DEST
python3 - <<'PY'
import os, pathlib, hashlib, re, subprocess, time
from datetime import datetime

root = pathlib.Path(os.environ['ROOT'])
proj = pathlib.Path(os.environ['PROJ'])
dest = pathlib.Path(os.environ['DEST'])
launcher = proj / 'scripts/launch_formal_top3_stage2_20260812.sh'
expected_sha = '71caef0de33bd7d2d7aa1b8ea9f27b03ef2b0489fbbedfbf391e5fd396d04194'
parent_pid = 3213837
parent_ticks = '228313765'
offset = 9287922
status = root / 'queue.status.log'

def log(s):
    print(datetime.now().astimezone().isoformat(), s, flush=True)

def prepare():
    raw = launcher.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        raise RuntimeError('Launcher changed; refusing unreviewed continuation')
    source = raw.decode()
    old = "'15,16,14,28,27,26,23,22,24,1,9,7,0,2,13,11,12,4'"
    if source.count(old) != 2:
        raise RuntimeError('Unexpected MMKE-entity queue definition')
    # Change the execution list only; final whole-queue validation keeps all 18 layers.
    source = source.replace(old, "'1'", 1)
    source, n1 = re.subn(r'^    run_combo evqa-pilot500 minigpt-4-vicuna-7b .*$', '    : # completed earlier; tail retry is L1 only', source, flags=re.M)
    # The tail's one-layer loop must not claim the whole combination is complete.
    source = source.replace('touch "$RUN_ROOT/$dataset/$model/COMBO_DONE"', ': # completion is checked against the full original queue below')
    source = source.replace('log_status "COMBO_DONE dataset=', 'log_status "TAIL_LOOP_DONE dataset=')
    if n1 != 1 or source.count('GPU_TRAIN_FREE_MIN_MIB=61440') != 1:
        raise RuntimeError('Unexpected source layout')
    return source.replace('GPU_TRAIN_FREE_MIN_MIB=61440','GPU_TRAIN_FREE_MIN_MIB=73728')

source = prepare()
if os.environ.get('VALIDATE_ONLY') == '1':
    subprocess.run(['bash','-n'],input=source,universal_newlines=True,check=True)
    print('VALIDATED: job3126082 tail contains only MMKE-entity L1; train=73728 MiB, eval=56320 MiB')
    raise SystemExit(0)

def parent_alive():
    try:
        fields = pathlib.Path('/proc/%d/stat'%parent_pid).read_text().split(') ',1)[1].split()
        return fields[19] == parent_ticks and fields[0] != 'Z'
    except FileNotFoundError:
        return False

log('REGISTERED sequence=L9,L7,L0,L2,L13,L11,L12,L4,then_L1 parent_pid=%d no_GPU_allocation'%parent_pid)
while parent_alive():
    log('WAITING_FOR_ORIGINAL_QUEUE_END')
    time.sleep(60)
with status.open('rb') as f:
    f.seek(offset)
    tail = f.read().decode(errors='replace')
if not re.search(r'^QUEUE_(?:DONE|FINISHED_WITH_FAILURES) time=',tail,re.M):
    log('STOPPED: original queue ended without terminal marker; manual pause/crash must not auto-resume')
    raise SystemExit(23)
if not re.search(r'^LAYER_BEGIN dataset=mmke-entity model=llava-v1.5-7b layer=4 ',tail,re.M):
    log('STOPPED: original queue did not reach L4')
    raise SystemExit(24)
source = prepare()
env = os.environ.copy()
env.update(ALLOW_REPLACEMENT_JOB='1',GPU_TRAIN_ALLOW_NON_KERNEL='0')
monitor = subprocess.Popen(['bash',str(proj/'scripts/sync_completed_layers_to_shared_monitor_20260810.sh'),str(root),str(dest)],stdin=subprocess.DEVNULL)
try:
    log('START_L1_ONLY: preserve config; latest finite existing checkpoint; same launcher.lock; 72GiB training gate')
    result = subprocess.run(['bash','-s','--','job3126082'],input=source,universal_newlines=True,env=env,cwd=str(proj))
    log('L1_TAIL_EXIT rc=%d'%result.returncode)
    if result.returncode == 0 and (root/'QUEUE_DONE').exists():
        try:
            monitor.wait(timeout=1800)
        except subprocess.TimeoutExpired:
            log('Archive monitor timeout; inspect sync_monitor.log')
finally:
    if monitor.poll() is None:
        monitor.terminate()
        monitor.wait()
PY
