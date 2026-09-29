"""Replace only the positively identified, idle G09 controller after approval."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import time

D = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/tukey_top3_two_gpu_20260926')
OLD = D.parent / 'tukey_top3_tail_job3443209_20260926'
A = D / 'control/g09/fast_results_order_20260928'
PY = '/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python'


def node(code):
    proc = subprocess.run(['ssh', '-o', 'ConnectTimeout=12', 'g09', 'python3', '-'],
                          input=code, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, timeout=40)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


def dump(name, data):
    with (A / name).open('x') as f:
        json.dump(data, f, indent=2)


def main():
    assert not (A / 'launch.json').exists(), 'Already deployed; no duplicate retry'
    assert subprocess.check_output(['squeue', '-j', '3443209', '-h', '-o', '%T %N'], universal_newlines=True).strip() == 'RUNNING g09'
    assert hashlib.sha256((D / 'control/two_gpu_queue.py').read_bytes()).hexdigest() == 'e3f71a8ca7db25099d5271048683e8f035a656c915179b5c81f1132dfef906dd'
    spec = importlib.util.spec_from_file_location('frozen_tail_preflight', str(OLD / 'control/top3_tail_3443209.py'))
    t = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(t)
    t.pincheck()
    accepted = OLD / 'accepted/mmke-entity/minigpt-4-vicuna-7b/layer_07'
    assert (accepted / 'SYNC_VERIFIED').is_file()
    t.validate_eval(t.spec('mmke-entity', 'minigpt-4-vicuna-7b', 7), accepted)
    order = [('evqa-pilot500', 'instructblip-vicuna-7b', 20),
             ('evqa-pilot500', 'instructblip-vicuna-7b', 17),
             ('mmke-entity', 'minigpt-4-vicuna-7b', 8)]
    for ds, model, layer in order:
        job = t.spec(ds, model, layer)
        assert not (t.out(job) / ('train_L%d.log' % layer)).exists(), 'Task started; inspect before changing order'
        assert not any((t.layer(job) / n).exists() for n in ('loss_history.csv', 'train.done', 'eval_full.done'))
    dump('authorization.json', dict(time=time.strftime('%F %T %Z'), authorized=True,
         user_choice='Confirmed L20 -> L17 -> MiniGPT-4 L8', order=order,
         unchanged=['training/evaluation protocol', 'training gates', 'eval memory-only policy',
                    'shared locks', 'archive validation', 'G08 LLaVA waiter', 'other GPU processes']))
    dump('commands.json', [dict(dataset=ds, model=model, layer=l,
         train=t.command(t.spec(ds, model, l), 'train'), eval=t.command(t.spec(ds, model, l), 'eval')) for ds, model, l in order])
    code = """
import hashlib,json,os,time
from pathlib import Path
p=Path('/proc/2268980')
expected='/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python -u /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/tukey_top3_two_gpu_20260926/control/g09/eval_memory_gate_20260928/g09_eval_memory_gate.py'
assert (p/'cmdline').read_bytes().replace(b'\\0',b' ').decode().strip()==expected
assert (p/'stat').read_text().split(') ',1)[1].split()[19]=='275447658'
assert 'job_3443209/step_5' in (p/'cgroup').read_text()
assert not (p/'task/2268980/children').read_text().strip(),'Controller has active child'
s=json.loads(Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/tukey_top3_two_gpu_20260926/control/g09/status.json').read_text())
assert s['pid']==2268980 and s['state']=='GPU_GATE' and s['phase']=='train',s
"""
    evidence = node(code + "print(json.dumps(dict(time=time.strftime('%F %T %Z'),status=s,child_processes=0)))\n")
    dump('before.json', evidence)
    for src, name in [(D / 'control/g09/status.json', 'previous_status.json'),
                      (D / 'control/g09/eval_memory_gate_20260928/launch.json', 'previous_launch.json')]:
        assert not (A / name).exists()
        shutil.copy2(str(src), str(A / name))
    stopped = node(code + """
import signal
os.kill(2268980,signal.SIGTERM)
for unused in range(40):
 if not p.exists():break
 time.sleep(.25)
assert not p.exists(),'Controller did not exit: do not launch duplicate'
print(json.dumps(dict(time=time.strftime('%F %T %Z'),stopped_idle_controller=2268980,others_untouched=True)))
""")
    dump('idle_controller_stopped.json', stopped)
    command = ['srun', '--jobid=3443209', '--overlap', '--nodes=1', '--ntasks=1', '--cpus-per-task=8',
               '--nodelist=g09', PY, '-u', str(A / 'fast_results_queue.py')]
    with (A / 'controller.log').open('xb') as log:
        child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
                                 stderr=subprocess.STDOUT, start_new_session=True)
    launch = dict(time=time.strftime('%F %T %Z'), login_srun_pid=child.pid, command=command)
    dump('launch.json', launch)
    time.sleep(2)
    assert child.poll() is None, 'Replacement exited; inspect log, no automatic retry'
    print(json.dumps(launch))


if __name__ == '__main__':
    main()
