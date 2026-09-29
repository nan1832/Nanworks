"""Authorized one-shot L4 continuation; GPU-free watcher, unchanged experiment."""
import csv
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

B = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2')
P = B / 'VisEdit-main'
S = B / 'server_results'
BASE = S / 'evqa_llava_job3435286_20260924'
OLD = BASE / 'resume_after_eval955_20260926'
A = BASE / 'resume_L4_wait_memory_20260928'
M = S / 'tukey_top3_two_gpu_20260926/llava_L4_pause/resume_manifest.json'
JOB = '3435286'
TRAIN_FREE_MIB = 72000  # Original L4 continuation gate, not a claimed exact peak.
EVAL_FREE_MIB = 56320
POLL_SECONDS = 20
METRICS = ('Rel', 'T-Gen', 'M-Gen', 'T-Loc', 'M-Loc', 'Average')


def read(p):
    return json.loads(Path(p).read_text())


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def dump(p, value):
    p = Path(p)
    temp = p.with_name(p.name + '.partial')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False))
    temp.replace(p)


def state(name, **kwargs):
    value = dict(state=name, time=time.strftime('%F %T %Z'), job=JOB,
                 node='g08', controller_pid=os.getpid(), dataset='evqa-pilot500',
                 model='llava-v1.5-7b', layer=4, automatic_resume=True,
                 status_path=str(A / 'status.json'), **kwargs)
    dump(A / 'status.json', value)
    # Only the old LIVE status is superseded; archived pause records stay intact.
    dump(OLD / 'status.json', value)
    print(json.dumps(value), flush=True)


def command_value(command, flag):
    return command[command.index(flag) + 1]


def eval_command(train_command):
    command = []
    i = 0
    while i < len(train_command):
        arg = train_command[i]
        if arg in ('--resume-checkpoint', '--resume-layer'):
            i += 2
            continue
        command.append('--skip-train' if arg == '--skip-eval' else arg)
        i += 1
    return command


def history(layer):
    with (layer / 'loss_history.csv').open() as f:
        return list(csv.DictReader(f))


def prepare():
    assert not (A / 'provenance.json').exists(), 'Already prepared: inspect instead of overwriting'
    manifest = read(M)
    assert manifest['state'] == 'PAUSED_VERIFIED'
    assert manifest['metadata']['epoch'] == 38 and manifest['metadata']['step'] == 9500
    train = manifest['resume_command']
    expected = {'--layers': '4', '--epochs': '50', '--batch-size': '2',
                '--model-name': 'llava-v1.5-7b', '--seed': '20260601',
                '--ema-alpha': '0.1', '--resume-layer': '4', '--data-buffer-size': '1',
                '--keep-top-ckpts': '1', '--keep-last-ckpts': '0'}
    assert all(command_value(train, k) == v for k, v in expected.items())
    assert '--share-data-proc-vllm' in train and '--skip-eval' in train
    output = Path(command_value(train, '--out-root'))
    assert output == OLD / 'run/evqa-pilot500/llava-v1.5-7b'
    layer = output / 'layer_04'
    assert not any((layer / n).exists() for n in ('train.done', 'eval_full.done'))
    records = history(layer)
    assert [int(x['epoch']) for x in records] == list(range(1, 39))
    assert int(records[-1]['i']) == 9500
    resume = command_value(train, '--resume-checkpoint')
    assert resume == manifest['checkpoint']
    for item in manifest['files']:
        if item['source'] == resume or item['source'].endswith('/loss_history.csv') or '/VisEdit-main/' in item['source']:
            assert sha(item['source']) == sha(item['backup']) == item['sha256'], item['source']
    # Pin the already-frozen project implementation, plus this run's input files.
    pins = read(S / 'tukey_top3_tail_job3443209_20260926/provenance/plan.json')['pins']
    for flag in ('--train-data', '--eval-data', '--config-path'):
        p = Path(command_value(train, flag))
        p = p if p.is_absolute() else P / p
        pins[str(p)] = sha(p)
    for item in manifest['files']:
        if '/VisEdit-main/' in item['source']:
            pins[item['source']] = item['sha256']
    for p, expected_hash in pins.items():
        assert sha(p) == expected_hash, 'Code/input changed: ' + p
    assert len(read(command_value(train, '--train-data'))) == 500
    assert len(read(command_value(train, '--eval-data'))) == 2093
    for name, source in [('previous_live_status.json', OLD / 'status.json'),
                         ('pause_manifest.json', M), ('loss_history_before_resume.csv', layer / 'loss_history.csv')]:
        assert not (A / name).exists()
        shutil.copy2(str(source), str(A / name))
    provenance = dict(time=time.strftime('%F %T %Z'), train_command=train,
        eval_command=eval_command(train), output=str(output), layer=str(layer), pins=pins,
        checkpoint=resume, checkpoint_sha256=sha(resume), backup_checkpoint=manifest['backup_checkpoint'],
        history_sha256=sha(layer / 'loss_history.csv'), pause_manifest_sha256=sha(M),
        completed_epoch=38, next_epoch=39, next_step=9501, target_epoch=50,
        training_free_mib=TRAIN_FREE_MIB, eval_free_mib=EVAL_FREE_MIB, stable_samples=3,
        interval_seconds=POLL_SECONDS, selection='minimum finite EMA over epochs 1-50',
        eval_samples=2093, rng_note='Original checkpoint RNG availability is not assumed; original resume semantics retained',
        environment=dict(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', PYTHONPATH=str(P),
                         OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', PYTHONUNBUFFERED='1', CUDA_VISIBLE_DEVICES='0'))
    dump(A / 'provenance.json', provenance)
    print(json.dumps(dict(prepared=True, **{k: provenance[k] for k in ['checkpoint', 'next_epoch', 'training_free_mib', 'eval_free_mib']})))


def check_pins(provenance, initial=False):
    for p, expected in provenance['pins'].items():
        assert sha(p) == expected, 'Frozen code/input changed: ' + p
    assert sha(M) == provenance['pause_manifest_sha256'], 'Pause manifest changed'
    if initial:
        assert sha(provenance['checkpoint']) == sha(provenance['backup_checkpoint']) == provenance['checkpoint_sha256']
        assert sha(Path(provenance['layer']) / 'loss_history.csv') == provenance['history_sha256']


def gpu():
    line = subprocess.check_output(['nvidia-smi', '-i', '0', '--query-gpu=memory.free,memory.used,utilization.gpu',
                                    '--format=csv,noheader,nounits'], universal_newlines=True).strip()
    free, used, util = [int(x) for x in line.split(',')]
    apps = subprocess.check_output(['nvidia-smi', '-i', '0', '--query-compute-apps=pid,used_memory',
                                    '--format=csv,noheader,nounits'], universal_newlines=True).strip()
    return dict(free_mib=free, used_mib=used, utilization=util,
                processes={int(x.split(',')[0]): int(x.split(',')[1]) for x in apps.splitlines() if x.strip()})


def memory_ready(snapshot, phase):
    return snapshot['free_mib'] >= (TRAIN_FREE_MIB if phase == 'train' else EVAL_FREE_MIB)


def check_allocation():
    info = subprocess.check_output(['squeue', '-j', JOB, '-h', '-o', '%T %N %L'], universal_newlines=True).strip().split()
    assert len(info) == 3 and info[:2] == ['RUNNING', 'g08'], info
    if info[2] != 'UNLIMITED':
        days, clock = info[2].split('-', 1) if '-' in info[2] else ('0', info[2])
        seconds = int(days) * 86400 + sum(int(v) * 60 ** i for i, v in enumerate(reversed(clock.split(':'))))
        assert seconds >= 86400, 'Less than 24h left; stop for migration'


def cancel_check():
    assert not (A / 'CANCEL_AUTO_RESUME').exists(), 'New continuation cancelled by marker'


def lock_paths():
    return [S / 'gpu_locks/g08_gpu0.lock', OLD / 'watcher.lock',
            Path('/tmp/ph_teacher3/evqa_llava_job3435286_20260924/launcher.lock'),
            P / 'phase2_p4/formal_eval955_20260926/launcher.lock',
            P / 'phase2_p4/formal_eval955_20260926/evaluation.lock',
            P / 'phase2_p4/formal_queue_20260925_v3/queue.lock']


def acquire_project_locks():
    held = []
    try:
        for path in lock_paths():
            assert path.parent.is_dir(), 'Expected lock directory missing: ' + str(path)
            handle = path.open('a')
            held.append(handle)
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return held
    except BlockingIOError:
        for handle in held:
            handle.close()
        return []
    except Exception:
        for handle in held:
            handle.close()
        raise


def wait_ready(phase, need_locks=False):
    stable = 0
    while True:
        cancel_check()
        check_allocation()
        snapshot = gpu()
        stable = stable + 1 if memory_ready(snapshot, phase) else 0
        state('WAITING_GPU_MEMORY', phase=phase, stable=stable,
              required_mib=TRAIN_FREE_MIB if phase == 'train' else EVAL_FREE_MIB, **snapshot)
        if stable >= 3:
            held = acquire_project_locks() if need_locks else []
            if need_locks and not held:
                stable = 0
                state('WAITING_PROJECT_LOCKS', phase=phase)
            elif memory_ready(gpu(), phase):
                return held
            else:
                for handle in held:
                    handle.close()
                stable = 0
        time.sleep(POLL_SECONDS)


def run_stage(provenance, phase):
    while True:
        check_pins(provenance, initial=phase == 'train')
        cancel_check()
        check_allocation()
        if memory_ready(gpu(), phase):
            break
        # A transient VRAM dip should wait again, not permanently disable recovery.
        wait_ready(phase)
    command = provenance[phase + '_command']
    log = A / (phase + '_L4.log')
    with (A / (phase + '_launch_intent.json')).open('x') as f:
        json.dump(dict(time=time.strftime('%F %T %Z'), command=command), f, indent=2)
    env = os.environ.copy()
    env.update(provenance['environment'])
    with log.open('xb') as stream:
        child = subprocess.Popen(command, cwd=str(P), env=env, stdin=subprocess.DEVNULL,
                                 stdout=stream, stderr=subprocess.STDOUT)
        state('RUNNING', phase=phase, child_pid=child.pid, log=str(log), next_epoch=39 if phase == 'train' else None)
        while child.poll() is None:
            time.sleep(POLL_SECONDS)
            state('RUNNING', phase=phase, child_pid=child.pid, log=str(log),
                  log_bytes=log.stat().st_size, log_idle_seconds=time.time() - log.stat().st_mtime)
        assert child.returncode == 0, '{} exited {}; no automatic retry'.format(phase, child.returncode)
    src = Path(provenance['output']) / 'run_config.json'
    assert not (A / (phase + '_run_config.json')).exists()
    shutil.copy2(str(src), str(A / (phase + '_run_config.json')))


def validate_train(provenance):
    layer = Path(provenance['layer'])
    records = history(layer)
    assert [int(x['epoch']) for x in records] == list(range(1, 51))
    assert int(records[-1]['i']) == 12500
    assert read(layer / 'train.done')['status'] == 'TRAIN_DONE'
    with (layer / 'selected_checkpoint.tsv').open() as f:
        selected = list(csv.DictReader(f, delimiter='\t'))
    assert len(selected) == 1
    selected = selected[0]
    good = [x for x in records if all(math.isfinite(float(x[k])) for k in ('loss', 'ema_loss'))]
    assert abs(float(selected['ema_loss']) - min(float(x['ema_loss']) for x in good)) < 1e-8
    cp = Path(selected['checkpoint'])
    cp.resolve().relative_to(layer.resolve())
    assert cp.is_file() and cp.stat().st_size > 0
    return selected, cp


def validate_complete(provenance):
    selected, cp = validate_train(provenance)
    layer = Path(provenance['layer'])
    ev = read(layer / 'eval_full.done')
    assert ev['status'] == 'EVAL_DONE' and int(ev['eval_samples']) == 2093
    assert Path(ev['checkpoint']).resolve() == cp.resolve()
    assert all(math.isfinite(float(ev[k])) for k in METRICS)
    assert abs(sum(float(ev[k]) for k in METRICS[:5]) / 5 - float(ev['Average'])) < 1e-6
    result_dir = Path(ev['result_dir'])
    result_dir.resolve().relative_to(layer.resolve())
    results = result_dir / 'results.json'
    assert len(read(results)) == 2093
    receipt = dict(time=time.strftime('%F %T %Z'), status='TRAIN50_FULL2093_VERIFIED_SHARED',
                   selected=selected, metrics=ev, output=str(layer),
                   checkpoint_sha256=sha(cp), results_sha256=sha(results),
                   results_on_shared_storage=True, local_sync_complete=False)
    dump(A / 'completion_verified.json', receipt)
    state('COMPLETE_VERIFIED_SHARED', metrics=ev, selected_checkpoint=str(cp),
          local_sync_complete=False, other_layers_started=False)


def watch():
    assert os.uname()[1].split('.')[0] == 'g08' and os.environ.get('SLURM_JOB_ID') == JOB
    assert read(A / 'authorization.json')['authorized'] is True
    own = (A / 'controller.lock').open('a')
    fcntl.flock(own, fcntl.LOCK_EX | fcntl.LOCK_NB)
    assert not (A / 'train_launch_intent.json').exists(), 'Already launched: no duplicate or silent retry'
    provenance = read(A / 'provenance.json')
    check_pins(provenance, initial=True)
    layer = Path(provenance['layer'])
    assert not (layer / 'train.done').exists() and not (layer / 'eval_full.done').exists()
    held = wait_ready('train', need_locks=True)
    try:
        run_stage(provenance, 'train')
        validate_train(provenance)
        state('TRAIN50_VERIFIED_EVAL_PENDING', phase='eval')
        wait_ready('eval')
        run_stage(provenance, 'eval')
        validate_complete(provenance)
    finally:
        for handle in held:
            handle.close()


if __name__ == '__main__':
    if sys.argv[1:] == ['--prepare']:
        prepare()
    else:
        try:
            watch()
        except Exception as error:
            state('STOPPED_REQUIRES_INSPECTION', error=repr(error))
            raise
