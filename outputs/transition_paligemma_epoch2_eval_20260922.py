"""User-authorized stop of the stalled child; existing controller evaluates epoch 2."""
import csv
import json
import math
import os
from pathlib import Path
import signal
import time

OUT = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_paligemma_l0_main_retrain_job3178538_20260921')
PID = 660670
PARENT = 660581


def identity(pid):
    p = Path('/proc') / str(pid)
    stat = (p / 'stat').read_text().split(') ', 1)[1].split()
    env = dict(v.split('=', 1) for v in (p / 'environ').read_bytes().decode().split('\0') if '=' in v)
    cmd = (p / 'cmdline').read_bytes().replace(b'\0', b' ').decode()
    return stat[19], int(stat[1]), env, cmd


assert os.uname().nodename.split('.')[0] == 'g08'
token, parent, env, cmd = identity(PID)
assert parent == PARENT
assert env.get('SLURM_JOB_ID') == '3178538' and env.get('SLURM_STEP_ID') == '108'
assert 'run_evqa_pilot500_blip2_visedit_sweep_l0_snapshot_20260921.py' in cmd and '--skip-eval' in cmd
assert 'retrain_evqa_paligemma_l0_20260921.py' in identity(PARENT)[3]
rows = list(csv.DictReader((OUT / 'layer_00/loss_history.csv').open()))
valid = [r for r in rows if math.isfinite(float(r['ema_loss'])) and math.isfinite(float(r['loss'])) and Path(r['ckpt_path']).is_file()]
best = min(valid, key=lambda r: float(r['ema_loss']))
assert int(best['epoch']) == 2 and abs(float(best['ema_loss']) - 3209.824509720526) < 1e-6
request = dict(time=time.strftime('%F %T %Z'), user_instruction='Stop training; evaluate existing epoch 2 only; do not resume PaliGemma training',
               requested_epoch=2, checkpoint=best['ckpt_path'], checkpoint_sha256='TO_BE_VERIFIED',
               training_complete_50_epochs=False, historical_nonconvergence=True,
               diagnostic_only=True, stalled_last_progress='2026-09-21 23:25:56 CST, epoch 31, 100/500',
               target_pid=PID, target_start_ticks=token, controller_pid=PARENT)
import hashlib
request['checkpoint_sha256'] = hashlib.sha256(Path(best['ckpt_path']).read_bytes()).hexdigest()
assert request['checkpoint_sha256'] == '9405c64d2e1d5b96f5ab96b0109a25b8dcde2697f46faec319b37727efbef260'
with (OUT / 'diagnostic_epoch2_request.json').open('x') as f:
    json.dump(request, f, indent=2)
assert identity(PID)[0] == token
os.kill(PID, signal.SIGTERM)
print('SIGTERM_SENT_TO_STALLED_TRAINING_ONLY', PID, flush=True)
for _ in range(20):
    time.sleep(1)
    try:
        current = identity(PID)
    except FileNotFoundError:
        print('TRAINING_PROCESS_EXITED; existing controller will select and evaluate epoch 2', flush=True)
        break
    assert current[0] == token, 'PID reused; no further signal allowed'
else:
    assert identity(PID)[0] == token
    os.kill(PID, signal.SIGKILL)
    print('SIGKILL_SENT_ONLY_TO_VERIFIED_STALLED_TRAINING_PID', PID, flush=True)
