"""Deploy one memory-only L4 waiter inside the already-authorized allocation."""
import json
from pathlib import Path
import subprocess
import time

B = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2')
A = B / 'server_results/evqa_llava_job3435286_20260924/resume_L4_wait_memory_20260928'
PY = '/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python'


def main():
    assert not (A / 'launch.json').exists(), 'Already deployed: inspect, never duplicate'
    mapping = subprocess.check_output(['squeue', '-j', '3435286', '-h', '-o', '%T %N'], universal_newlines=True).strip()
    assert mapping == 'RUNNING g08', mapping
    code = """
import fcntl,json,subprocess,time
from pathlib import Path
matches=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  c=(p/'cmdline').read_bytes().decode(errors='replace').replace('\\0',' ')
  if '/zhounan/' in c and any(x in c for x in ['run_mmke_llava_shared_gpu_sweep.py','resume_llava_after_eval_20260926.py','wait_resume_l4.py']):matches.append({'pid':p.name,'cmd':c})
 except OSError:pass
assert not matches,('Existing LLaVA controller/process',matches)
S=Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results')
held=[]
for p in [S/'gpu_locks/g08_gpu0.lock',S/'evqa_llava_job3435286_20260924/resume_after_eval955_20260926/watcher.lock']:
 f=p.open('r');held.append(f);fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
for p in [Path('/tmp/ph_teacher3/evqa_llava_job3435286_20260924'),Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/phase2_p4/formal_eval955_20260926'),Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/phase2_p4/formal_queue_20260925_v3')]:assert p.is_dir(),str(p)
gpu=subprocess.check_output(['nvidia-smi','--query-gpu=memory.total,memory.used,memory.free,utilization.gpu','--format=csv,noheader,nounits'],universal_newlines=True)
apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_memory','--format=csv,noheader,nounits'],universal_newlines=True)
print(json.dumps(dict(time=time.strftime('%F %T %Z'),gpu=gpu,apps=apps,existing_llava=matches,locks_free=True)))
"""
    result = subprocess.run(['ssh', '-o', 'ConnectTimeout=12', 'g08', 'python3', '-'],
                            input=code, universal_newlines=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=40)
    assert result.returncode == 0, result.stdout + result.stderr
    with (A / 'before.json').open('x') as f:
        json.dump(json.loads(result.stdout), f, indent=2)
    with (A / 'authorization.json').open('x') as f:
        json.dump(dict(authorized=True, time=time.strftime('%F %T %Z'),
                       user_instruction='When enough GPU memory is free, immediately resume EVQA-pilot500 LLaVA L4',
                       job='3435286', node='g08', layer=4, next_epoch=39, target_epoch=50,
                       formal_eval_after_training=2093, no_other_process_stopped=True,
                       supersedes_pause_scheduling_only=True, historical_cancel_markers_preserved=True,
                       waiting_gpu_allocation_mib=0, train_free_mib=72000, eval_free_mib=56320,
                       poll_seconds=20, stable_samples=3, other_gpu_processes_allowed=True), f, indent=2)
    subprocess.run([PY, str(A / 'wait_resume_l4.py'), '--prepare'], check=True)
    command = ['srun', '--jobid=3435286', '--overlap', '--nodes=1', '--ntasks=1',
               '--cpus-per-task=8', '--nodelist=g08', PY, '-u', str(A / 'wait_resume_l4.py')]
    with (A / 'controller.log').open('xb') as stream:
        child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=stream,
                                 stderr=subprocess.STDOUT, start_new_session=True)
    launch = dict(time=time.strftime('%F %T %Z'), login_srun_pid=child.pid, command=command,
                  controller_log=str(A / 'controller.log'), status_file=str(A / 'status.json'))
    with (A / 'launch.json').open('x') as f:
        json.dump(launch, f, indent=2)
    time.sleep(2)
    assert child.poll() is None, 'Watcher exited; inspect log before taking further action'
    print(json.dumps(launch))


if __name__ == '__main__':
    main()
