"""Replace only the verified idle G09 controller; never touch GPU processes."""
import hashlib
import importlib.util
import json
import shutil
import subprocess
import time
from pathlib import Path

D = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/tukey_top3_two_gpu_20260926')
A = D / 'control/g09/memory_eligible_20260928'
OLD = D.parent / 'tukey_top3_tail_job3443209_20260926'
PY = '/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python'


def dump(name, data):
    with (A / name).open('x') as f:
        json.dump(data, f, indent=2)


def node(code):
    r = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=12', 'g09', 'python3', '-'],
                       input=code, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True, timeout=40)
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(r.stdout)


def main():
    assert not (A / 'launch.json').exists(), 'No duplicate deployment'
    assert subprocess.check_output(['squeue', '-j', '3443209', '-h', '-o', '%T %N'], universal_newlines=True).strip() == 'RUNNING g09'
    assert hashlib.sha256((D / 'control/two_gpu_queue.py').read_bytes()).hexdigest() == 'e3f71a8ca7db25099d5271048683e8f035a656c915179b5c81f1132dfef906dd'
    spec = importlib.util.spec_from_file_location('tail_preflight', str(OLD / 'control/top3_tail_3443209.py'))
    t = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(t)
    t.pincheck()
    tasks = [('evqa-pilot500', 'instructblip-vicuna-7b', 20),
             ('evqa-pilot500', 'instructblip-vicuna-7b', 17),
             ('mmke-entity', 'minigpt-4-vicuna-7b', 8)]
    t.validate_eval(t.spec('mmke-entity', 'minigpt-4-vicuna-7b', 7), OLD / 'accepted/mmke-entity/minigpt-4-vicuna-7b/layer_07')
    for task in tasks:
        j = t.spec(*task)
        assert not (t.out(j) / ('train_L%d.log' % j['layer'])).exists(), 'Task already started'
        assert not any((t.layer(j) / n).exists() for n in ['train.done', 'loss_history.csv', 'eval_full.done'])
    samples = []
    for line in (D / 'control/g09/controller.log').open():
        try:
            x = json.loads(line)
        except ValueError:
            continue
        if (x.get('state'), x.get('phase'), x.get('model'), x.get('layer')) == ('RUNNING', 'train', 'minigpt-4-vicuna-7b', 7):
            own = x.get('gpu_process_memory', {}).get(str(x.get('child_pid')))
            if own is not None:
                samples.append(own)
    assert len(samples) == 983 and max(samples) == 70118
    dump('authorization.json', dict(time=time.strftime('%F %T %Z'), user_request='Run whichever remaining layer fits current memory first',
         tasks=tasks, training_minigpt_mib=72166, training_instruct_mib=77824, eval_mib=56320,
         memory_evidence=dict(source=str(D / 'control/g09/controller.log'), count=len(samples), sampled_peak=max(samples), margin=2048),
         risk='Neighbor-layer sampled peak is not a guaranteed full-run peak; shared GPU may change',
         unchanged=['training/evaluation commands and pins', 'epochs/batch/LR/seed/objective', 'locks', 'G08 waiter', 'other processes']))
    dump('commands.json', [dict(task=task, train=t.command(t.spec(*task), 'train'), eval=t.command(t.spec(*task), 'eval')) for task in tasks])
    code = """
import json,os,time,subprocess
from pathlib import Path
p=Path('/proc/2280456')
expected='/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python -u /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/tukey_top3_two_gpu_20260926/control/g09/fast_results_order_20260928/fast_results_queue.py'
assert (p/'cmdline').read_bytes().replace(b'\\0',b' ').decode().strip()==expected
assert (p/'stat').read_text().split(') ',1)[1].split()[19]=='275763567'
assert 'job_3443209/step_6' in (p/'cgroup').read_text()
assert not (p/'task/2280456/children').read_text().strip()
s=json.loads(Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/tukey_top3_two_gpu_20260926/control/g09/status.json').read_text())
assert s['pid']==2280456 and s['state']=='GPU_GATE' and s['phase']=='train'
assert s['model']=='instructblip-vicuna-7b' and s['layer']==20
free=int(subprocess.check_output(['nvidia-smi','-i','0','--query-gpu=memory.free','--format=csv,noheader,nounits'],universal_newlines=True))
"""
    evidence = node(code + "print(json.dumps(dict(time=time.strftime('%F %T %Z'),status=s,free_mib=free)))\n")
    dump('before.json', evidence)
    shutil.copy2(str(D / 'control/g09/status.json'), str(A / 'previous_status.json'))
    shutil.copy2(str(D / 'control/g09/fast_results_order_20260928/launch.json'), str(A / 'previous_launch.json'))
    stopped = node(code + """
import signal
os.kill(2280456,signal.SIGTERM)
for unused in range(40):
 if not p.exists():break
 time.sleep(.25)
assert not p.exists(),'No duplicate replacement while old controller remains'
print(json.dumps(dict(time=time.strftime('%F %T %Z'),stopped_idle_controller=2280456,others_untouched=True)))
""")
    dump('stopped.json', stopped)
    command = ['srun', '--jobid=3443209', '--overlap', '--nodes=1', '--ntasks=1', '--cpus-per-task=8',
               '--nodelist=g09', PY, '-u', str(A / 'eligible_queue.py')]
    with (A / 'controller.log').open('xb') as log:
        child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    launch = dict(time=time.strftime('%F %T %Z'), login_srun_pid=child.pid, command=command)
    dump('launch.json', launch)
    time.sleep(2)
    assert child.poll() is None, 'Inspect error; never automatically redeploy'
    print(json.dumps(launch))


if __name__ == '__main__':
    main()
