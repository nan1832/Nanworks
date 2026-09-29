"""User-authorized order: profile L20/L17, resume L8, then restore eval-first queue."""
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time
import traceback

ROOT = Path(__file__).resolve().parent
CAL = ROOT.parent
BASE = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2')
SERVER = BASE / 'server_results'
PROJECT = BASE / 'VisEdit-main'
D = SERVER / 'tukey_top3_two_gpu_20260926'
PY = '/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python'


def atomic(path, value):
    path = Path(path)
    temp = path.with_name(path.name + '.partial')
    temp.write_text(json.dumps(value, indent=2))
    temp.replace(path)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def state(name, **kwargs):
    value = dict(time=time.strftime('%FT%T%z'), state=name, node='g09',
                 job='3443209', pid=os.getpid(),
                 scheduling='profile_L20_L17_then_resume_L8_then_eval_then_formal_instruct',
                 priority_status=str(ROOT / 'status.json'), **kwargs)
    atomic(ROOT / 'status.json', value)
    if name != 'WAITING_FOR_AUTHORIZED_GPU_HANDOFF':
        atomic(D / 'control/g09/status.json', value)
        atomic(SERVER / 'visual_track_cosine_20260928/priority_switch/status.json', value)
    print(json.dumps(value), flush=True)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def alive(pid):
    path = Path('/proc') / str(pid) / 'stat'
    return path.exists() and path.read_text().split(') ', 1)[1].split()[0] != 'Z'


def resume_command(command, checkpoint):
    result = list(command)
    assert result[result.index('--epochs') + 1] == '50'
    assert result[result.index('--layers') + 1] == '8'
    index = result.index('--resume-checkpoint') + 1
    result[index] = str(checkpoint)
    assert [i for i, (a, b) in enumerate(zip(command, result)) if a != b] == [index]
    return result


def profile_then_resume(profile, resume):
    receipts, failures = [], []
    for layer in (20, 17):
        try:
            receipts.append(profile(layer))
        except Exception:
            failures.append(dict(layer=layer, error=traceback.format_exc()))
    resume(receipts, failures)
    return receipts, failures


def run_resume(q, plan, receipts, failures):
    atomic(ROOT / 'profile_outcome.json', dict(receipts=receipts, failures=failures))
    if len(receipts) == 2:
        atomic(CAL / 'measured_gate.json',
               dict(state='CALIBRATED_BEFORE_L8_RESUME',
                    required_mib=max(x['required_mib'] for x in receipts),
                    policy='maximum of both layer measurements plus 2048 MiB margin, rounded up to 256 MiB',
                    layers=receipts))
    checkpoint = plan['checkpoint']
    assert sha(checkpoint['path']) == checkpoint['sha256']
    q.t.pincheck()
    good = 0
    while good < 3:
        free = int(subprocess.check_output(
            ['nvidia-smi', '-i', '0', '--query-gpu=memory.free', '--format=csv,noheader,nounits'],
            universal_newlines=True).strip())
        good = good + 1 if free >= 72166 else 0
        state('WAITING_TO_RESUME_L8', free_mib=free, required_mib=72166,
              stable=good, measured_layers=len(receipts), profile_failures=failures)
        if good < 3:
            time.sleep(10)
    command = resume_command(plan['original_train_command'], checkpoint['path'])
    atomic(ROOT / 'resume_command.json', dict(command=command, checkpoint=checkpoint))
    env = os.environ.copy()
    env.update(CUDA_VISIBLE_DEVICES='0', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
               OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', PYTHONUNBUFFERED='1',
               PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True',
               PYTHONPATH=str(PROJECT)+':'+env.get('PYTHONPATH',''))
    log = ROOT / 'resume_L8_epoch41.log'
    with log.open('x') as stream:
        child = subprocess.Popen(command, cwd=str(PROJECT), env=env, stdin=subprocess.DEVNULL,
                                 stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        atomic(ROOT / 'resume_launch.json', dict(pid=child.pid, time=time.time(), command=command))
        last_report = 0
        while child.poll() is None:
            if time.monotonic() - last_report >= 60:
                state('RESUMING_L8_AFTER_MEMORY_PROBES', child_pid=child.pid,
                      dataset='mmke-entity', model='minigpt-4-vicuna-7b', layer=8,
                      resume_epoch=checkpoint['epoch']+1, resume_i=checkpoint['i']+1,
                      log=str(log), measured_layers=len(receipts), profile_failures=failures,
                      gpu_process_memory=q.apps())
                last_report = time.monotonic()
            time.sleep(5)
    atomic(ROOT / 'resume_exit.json', dict(returncode=child.returncode, time=time.time()))
    assert child.returncode == 0, 'L8 resumed training failed; inspect ' + str(log)
    job = q.t.spec('mmke-entity', 'minigpt-4-vicuna-7b', 8)
    q.t.validate(job)
    q.t.copy(q.t.out(job) / 'run_config.json', q.t.layer(job) / 'train_run_config.json')
    atomic(ROOT / 'L8_TRAINING_DONE.json',
           dict(time=time.time(), train_done=json.loads((q.t.layer(job) / 'train.done').read_text())))


def main():
    assert os.uname()[1].split('.')[0] == 'g09'
    assert os.environ.get('SLURM_JOB_ID') == '3443209'
    assert subprocess.check_output(
        ['squeue', '-j', '3443209', '-h', '-o', '%T|%N'],
        universal_newlines=True).strip() == 'RUNNING|g09'
    plan = json.loads((ROOT / 'plan.json').read_text())
    for path, digest in plan['pins'].items():
        assert sha(path) == digest, 'Code changed: ' + path
    own = (ROOT / 'controller.lock').open('a')
    fcntl.flock(own, fcntl.LOCK_EX | fcntl.LOCK_NB)
    gpu = (SERVER / 'gpu_locks/g09_gpu0.lock').open('a')
    state('WAITING_FOR_AUTHORIZED_GPU_HANDOFF', old_pids=[2500705, 2512011])
    fcntl.flock(gpu, fcntl.LOCK_EX)
    deadline = time.monotonic() + 90
    while not (ROOT / 'handoff.json').exists() and time.monotonic() < deadline:
        time.sleep(.2)
    assert (ROOT / 'handoff.json').exists()
    assert not alive(2500705) and not alive(2512011)
    q = module('original_queue_for_calibration', D / 'control/two_gpu_queue.py')
    q.state = state
    q.t.pincheck()
    cal = module('original_memory_probe', CAL / 'calibration.py')

    def profile(layer):
        claim = D / 'claims/evqa-pilot500_instructblip-vicuna-7b.lock'
        with claim.open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return cal.probe_layer(q, layer)

    receipts, failures = profile_then_resume(
        profile, lambda receipts, failures: run_resume(q, plan, receipts, failures))
    # The existing eligible queue prioritizes trained L8 evaluation and archive.
    # Its calibration module reuses successful receipts instead of profiling again.
    gpu.close()
    env = os.environ.copy()
    env.update(CUDA_VISIBLE_DEVICES='0', PYTHONUNBUFFERED='1')
    with (ROOT / 'restored_eval_first_queue.log').open('x') as log:
        child = subprocess.Popen(plan['original_queue_command'], cwd=str(BASE),
                                 env=env, stdin=subprocess.DEVNULL, stdout=log,
                                 stderr=subprocess.STDOUT, start_new_session=True)
    time.sleep(5)
    assert child.poll() is None, 'Restored queue exited early; inspect its log'
    state('L8_TRAINED_RESTORED_EVAL_FIRST_QUEUE', controller_pid=child.pid,
          next='L8 full evaluation and verified archive before any formal InstructBLIP training',
          measured_layers=len(receipts), profile_failures=failures)
    atomic(ROOT / 'QUEUE_RESTORED.json', json.loads((ROOT / 'status.json').read_text()))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        state('STOPPED_REQUIRES_INSPECTION', error=traceback.format_exc())
        raise
