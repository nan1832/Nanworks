"""One-shot migration of the verified idle G09 queue, never other GPU processes."""
import hashlib
import importlib.util
import json
import subprocess
import time
from pathlib import Path

D = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/tukey_top3_two_gpu_20260926')
OLD = D.parent / 'tukey_top3_tail_job3443209_20260926'
A = D / 'control/g09/eval_memory_gate_20260928'
PY = '/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python'
SOURCE_SHA = 'e3f71a8ca7db25099d5271048683e8f035a656c915179b5c81f1132dfef906dd'
OLD_PID = 1903963


def dump(name, data):
    with (A / name).open('x') as f:
        json.dump(data, f, indent=2)


def node(code):
    p = subprocess.run(['ssh', '-o', 'ConnectTimeout=12', 'g09', 'python3', '-'],
                       input=code, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True, timeout=45)
    if p.returncode:
        raise RuntimeError(p.stdout + p.stderr)
    return json.loads(p.stdout)


def main():
    assert not (A / 'launch.json').exists(), 'Already launched: inspect, do not duplicate'
    mapping = subprocess.check_output(['squeue', '-j', '3443209', '-h', '-o', '%T %N'], universal_newlines=True).strip()
    assert mapping == 'RUNNING g09', mapping
    assert hashlib.sha256((D / 'control/two_gpu_queue.py').read_bytes()).hexdigest() == SOURCE_SHA
    for name in ['g09_eval_memory_gate.py', 'deploy_eval_gate.py']:
        compile((A / name).read_text(), str(A / name), 'exec')
    spec = importlib.util.spec_from_file_location('frozen_tail_preflight', str(OLD / 'control/top3_tail_3443209.py'))
    t = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(t)
    t.pincheck()
    j = t.spec('mmke-entity', 'minigpt-4-vicuna-7b', 7)
    cp = t.validate(j)
    assert not (t.layer(j) / 'eval_full.done').exists()
    assert not (t.out(j) / 'eval_L7.log').exists(), 'Evaluation already attempted; inspect'
    dump('protocol_verified.json', dict(time=time.strftime('%F %T %Z'), selected_checkpoint=str(cp),
         selected_checkpoint_sha256=t.sha(cp), evaluation_command=t.command(j, 'eval'),
         eval_samples=j['eval_count'], frozen_queue_sha256=SOURCE_SHA,
         wrapper_sha256=t.sha(A / 'g09_eval_memory_gate.py'),
         unchanged=['training gates', 'protocol and inputs', 'selected checkpoint', 'queue order',
                    'shared locks', 'three stable memory checks', 'LLaVA remains paused'],
         user_authorization='Evaluation may run when free GPU memory is sufficient; other GPU processes need not exit'))
    preflight = """
import hashlib,json,os,subprocess,time
from pathlib import Path
p=Path('/proc/1903963')
cmd=p.joinpath('cmdline').read_bytes().replace(b'\\0',b' ').decode().strip()
expected='/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python -u /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/tukey_top3_two_gpu_20260926/control/two_gpu_queue.py'
assert cmd==expected,cmd
assert 'job_3443209/step_4' in (p/'cgroup').read_text()
assert not (p/'task/1903963/children').read_text().strip(),'Controller has a child; do not stop'
s=json.loads(Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/tukey_top3_two_gpu_20260926/control/g09/status.json').read_text())
assert s['pid']==1903963 and s['state']=='GPU_GATE' and s['phase']=='eval',s
free=int(subprocess.check_output(['nvidia-smi','-i','0','--query-gpu=memory.free','--format=csv,noheader,nounits'],universal_newlines=True))
assert free>=56320,free
apps=subprocess.check_output(['nvidia-smi','-i','0','--query-compute-apps=pid,used_memory','--format=csv,noheader,nounits'],universal_newlines=True)
assert '1903963,' not in apps
print(json.dumps(dict(time=time.strftime('%F %T %Z'),status=s,free_mib=free,apps=apps,start_ticks=(p/'stat').read_text().split(') ',1)[1].split()[19],cmdline_sha256=hashlib.sha256((p/'cmdline').read_bytes()).hexdigest())))
"""
    evidence = node(preflight)
    dump('before.json', evidence)
    stop_code = preflight.rsplit('print(json.dumps', 1)[0] + """
import signal
assert (p/'stat').read_text().split(') ',1)[1].split()[19]==%r
assert hashlib.sha256((p/'cmdline').read_bytes()).hexdigest()==%r
os.kill(1903963,signal.SIGTERM)
for unused in range(40):
 if not p.exists():break
 time.sleep(.25)
assert not p.exists(),'Old controller did not exit; do not start duplicate'
print(json.dumps(dict(stopped_pid=1903963,time=time.strftime('%%F %%T %%Z'),other_processes_untouched=True)))
""" % (evidence['start_ticks'], evidence['cmdline_sha256'])
    dump('idle_controller_stopped.json', node(stop_code))
    # New controller reacquires all original locks before opening any stage.
    cmd = ['srun', '--jobid=3443209', '--overlap', '--nodes=1', '--ntasks=1',
           '--cpus-per-task=8', '--nodelist=g09', PY, '-u', str(A / 'g09_eval_memory_gate.py')]
    with (A / 'controller.log').open('xb') as log:
        child = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=log,
                                 stderr=subprocess.STDOUT, start_new_session=True)
    launch = dict(time=time.strftime('%F %T %Z'), login_srun_pid=child.pid, command=cmd,
                  original_controller_log_preserved=str(D / 'control/g09/controller.log'),
                  new_controller_log=str(A / 'controller.log'))
    dump('launch.json', launch)
    time.sleep(2)
    assert child.poll() is None, 'New controller exited; inspect its log, no automatic retry'
    print(json.dumps(launch))


if __name__ == '__main__':
    main()
