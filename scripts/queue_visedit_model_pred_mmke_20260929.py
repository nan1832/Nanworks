"""One serialized, GPU-lock-protected VisEdit queue on the free g08 allocation."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time
from run_visedit_model_pred_mmke_20260929 import write, now

BASE = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2')
ROOT = BASE / 'server_results/visedit_model_pred_mmke_20260929'
MODELS = ['blip2-opt-2.7b', 'instructblip-vicuna-7b', 'minigpt-4-vicuna-7b', 'llava-v1.5-7b',
          'qwen2.5-vl-3b', 'paligemma-3b', 'smolvlm-1.7b']


def main():
    assert subprocess.check_output(['squeue', '-j', '3435286', '-h', '-o', '%T %N'], universal_newlines=True).strip() == 'RUNNING g08'
    assert os.uname().nodename.split('.')[0] == 'g08'
    lockpath = BASE / 'server_results/gpu_locks/g08_gpu0.lock'
    lockpath.parent.mkdir(parents=True, exist_ok=True)
    lock = lockpath.open('a+')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    env = os.environ.copy()
    env.update(CUDA_VISIBLE_DEVICES='0', SLURM_JOB_ID='3435286', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
               PYTHONUNBUFFERED='1', OMP_NUM_THREADS='2', MKL_NUM_THREADS='2')
    control = ROOT / 'control'; control.mkdir(exist_ok=True)
    outcomes = []
    for model in MODELS:
        if (control / 'STOP').exists():
            write(control/'status.json', dict(state='STOPPED', time=now(), outcomes=outcomes)); return
        free = int(subprocess.check_output(['nvidia-smi', '--query-gpu=memory.free', '--format=csv,noheader,nounits'], universal_newlines=True).strip().splitlines()[0])
        if free < 45000:
            write(control/'status.json', dict(state='WAITING_MEMORY', free_mib=free, model=model, time=now()))
            raise RuntimeError('GPU free memory changed; no work started on this model')
        log = control / (model + '_' + time.strftime('%H%M%S') + '.log')
        command = [str(BASE/'envs/qwen25vl/bin/python'), '-u', str(ROOT/'code/run_visedit_model_pred_mmke_20260929.py'),
                   '--project', str(BASE/'VisEdit-main'), '--root', str(ROOT), '--model', model]
        with log.open('wb') as stream:
            child = subprocess.Popen(command, env=env, cwd=str(BASE/'VisEdit-main'), stdin=subprocess.DEVNULL,
                                     stdout=stream, stderr=subprocess.STDOUT)
            write(control/'status.json', dict(state='RUNNING', time=now(), model=model, pid=os.getpid(), child_pid=child.pid,
                                              job='3435286', node='g08', log=str(log), command=command, outcomes=outcomes))
            rc = child.wait()
        outcomes.append(dict(model=model, returncode=rc, log=str(log), time=now()))
    complete = len(list((ROOT/'results').glob('*/*/summary.json')))
    state = 'DONE' if complete == 14 and all(r['returncode'] == 0 for r in outcomes) else 'NEEDS_REPAIR'
    write(control/'status.json', dict(state=state, time=now(), completed_groups=complete, outcomes=outcomes))


if __name__ == '__main__':
    main()
