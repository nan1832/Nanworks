"""Append a fresh L7 run after the existing seven-layer queue, without editing it."""
import csv
import fcntl
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

PARENT = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_entity_llava_job3443209_20260926')
TAIL = PARENT / 'l7_restart_tail'
CONTROL = TAIL / 'control'
SELF = CONTROL / 'append_mmke_llava_l7_3443209.py'
PY = '/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python'
COMBO = Path('mmke-entity/llava-v1.5-7b')
PARENT_PID = 1864444
PARENT_START = '261714540'
PARENT_HASH = 'b2b19c691213309c4bbd3e539d38067575bc462648c2b2d08d4df7f81b70c4fd'
PREREQUISITES = [1, 0, 2, 13, 11, 12, 4]

def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for data in iter(lambda: f.read(8388608), b''):
            h.update(data)
    return h.hexdigest()

def identity(pid):
    try:
        s = Path('/proc/%s/stat' % pid).read_text()
        # Fields after the final ')' start at field 3; starttime is field 22.
        return s.rsplit(')', 1)[1].split()[19]
    except FileNotFoundError:
        return None

def status(state, **details):
    row = dict(state=state, time=time.strftime('%F %T %Z'), job=3443209,
               parent_pid=PARENT_PID, parent_start=PARENT_START, **details)
    p = CONTROL / 'status.json.partial'
    p.write_text(json.dumps(row, indent=2))
    p.replace(CONTROL / 'status.json')
    print(row['time'], state, json.dumps(details), flush=True)

def backend():
    p = CONTROL / 'base_controller_snapshot.py'
    assert sha(p) == PARENT_HASH, 'base controller snapshot changed'
    spec = importlib.util.spec_from_file_location('l7_backend', str(p))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.SHARED = TAIL
    m.ROOT = TAIL / 'work'
    m.TMP = Path('/tmp/ph_teacher3/mmke_entity_llava_job3443209_20260926_l7_restart')
    m.LAYERS = [7]
    return m

def generate(m):
    t = m.generate()
    old = "'1,0,2,13,11,12,4'"
    assert t.count(old) == 2
    t = t.replace(old, "'7'")
    helper = str(CONTROL / 'resume_mmke_entity_llava_3443209.py')
    assert t.count(helper) == 1
    t = t.replace(helper, str(SELF))
    subprocess.run(['bash', '-n'], input=t, universal_newlines=True, check=True)
    return t

def prerequisites():
    assert (PARENT / 'work/QUEUE_DONE').is_file(), 'original queue did not complete'
    authorized = json.load((CONTROL / 'authorization_and_sequence.json').open())
    assert (PARENT / 'work/QUEUE_DONE').stat().st_mtime >= authorized['created_epoch'], 'stale completion marker'
    log = (PARENT / 'control/controller.log').read_text(errors='replace')
    assert 'CONTROLLER_EXIT rc=0' in log, 'parent did not exit successfully'
    for layer in PREREQUISITES:
        d = PARENT / 'accepted' / COMBO / ('layer_%02d' % layer)
        for n in ['train.done', 'selected_checkpoint.tsv', 'eval_full.done', 'SYNC_VERIFIED']:
            assert (d / n).is_file(), str(d / n)
        ev = json.load((d / 'eval_full.done').open())
        assert ev['status'] == 'EVAL_DONE' and ev['eval_samples'] == 954
        assert all(math.isfinite(float(ev[k])) for k in ['Rel','T-Gen','M-Gen','T-Loc','M-Loc','Average'])
        row = list(csv.DictReader((d / 'selected_checkpoint.tsv').open(), delimiter='\t'))[0]
        cp = Path(row['checkpoint']).resolve()
        cp.relative_to(d.resolve())
        assert cp.is_file() and cp.stat().st_size > 0
        assert len(json.load(next(d.glob('eval_full/**/results.json')).open())) == 954
        manifest = json.load((d / 'ARCHIVE_MANIFEST.json').open())
        expected = next(r['sha256_archive'] for r in manifest if r['path'] == str(cp.relative_to(d)))
        assert sha(cp) == expected

def prepare():
    assert os.uname()[1].split('.')[0] == 'g09'
    assert identity(PARENT_PID) == PARENT_START, 'original controller changed; inspect first'
    source = PARENT / 'control/resume_mmke_entity_llava_3443209.py'
    assert sha(source) == PARENT_HASH
    assert not (TAIL / 'work').exists(), 'tail work root already exists'
    for name in ['resume_mmke_entity_llava_3443209.py', 'safe_cleanup_manifest.py', 'verify_result_tree.py']:
        dest = CONTROL / ('base_controller_snapshot.py' if name.startswith('resume_') else name)
        assert not dest.exists()
        shutil.copy2(str(PARENT / 'control' / name), str(dest))
        assert sha(dest) == sha(PARENT / 'control' / name)
    m = backend()
    text = generate(m)
    (m.ROOT / COMBO).mkdir(parents=True)
    for kind in ['cache', 'eval_cache']:
        target = m.TMP / kind
        target.mkdir(parents=True, exist_ok=True)
        (m.ROOT / COMBO / kind).symlink_to(target, target_is_directory=True)
    (CONTROL / 'launcher_l7_only.sh').write_text(text)
    manifest = {
        'authorized_action': 'fresh L7 from epoch1 after previous seven layers, not resume of old g07 L7',
        'queue': [1,0,2,13,11,12,4,7], 'parent_pid': PARENT_PID,
        'parent_start_ticks': PARENT_START, 'old_l7_progress': 'epoch12, last observed520/636; checkpoint inaccessible',
        'new_l7_start': 'epoch1, original seed/config, 50 epochs, minimum finite EMA, full954 evaluation',
        'parent_controller_sha256': PARENT_HASH, 'parent_queue_unmodified': True,
        'created': time.strftime('%F %T %Z'), 'created_epoch': time.time(),
        'protocol': {'epochs':50,'batch_size':2,'seed':20260601,'lr':1e-4,'ema_alpha':0.1},
    }
    (CONTROL / 'authorization_and_sequence.json').write_text(json.dumps(manifest, indent=2))
    status('PREPARED_WAITING_FOR_ORIGINAL_SEVEN_LAYERS')

def follow():
    assert os.environ.get('SLURM_JOB_ID') == '3443209'
    assert os.uname()[1].split('.')[0] == 'g09'
    lock = (CONTROL / 'tail_controller.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    assert not (CONTROL / 'L7_RESTART_STARTED').exists(), 'tail already started; no implicit retry'
    m = backend()
    text = generate(m)
    assert (CONTROL / 'launcher_l7_only.sh').read_text() == text
    while identity(PARENT_PID) == PARENT_START:
        status('WAITING_FOR_ORIGINAL_SEVEN_LAYERS', gpu_memory_used_by_waiter=0)
        time.sleep(30)
    try:
        prerequisites()
    except Exception as e:
        status('BLOCKED_ORIGINAL_QUEUE_INCOMPLETE', error=str(e))
        return 76
    # Reuse the same project GPU lock as the original queue, without evicting anyone.
    gpu = (m.BASE / 'server_results/gpu_locks/g09_gpu0.lock').open('a')
    while True:
        try:
            fcntl.flock(gpu, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            status('WAITING_FOR_GPU_LOCK', gpu_memory_used_by_waiter=0)
            time.sleep(30)
    prerequisites()
    generate(m)  # revalidate source/config immediately before scheduling
    layer = m.ROOT / COMBO / 'layer_07'
    assert not layer.exists(), 'fresh L7 must not import old checkpoints'
    (CONTROL / 'L7_RESTART_STARTED').write_text(time.strftime('%F %T %Z') + '\n')
    status('L7_FRESH_RUN_SCHEDULED', gpu_train_gate_mib=73728, gpu_eval_gate_mib=56320)
    env = os.environ.copy()
    env['GPU_TRAIN_ALLOW_NON_KERNEL'] = '0'
    rc = subprocess.call(['bash', str(CONTROL / 'launcher_l7_only.sh'), 'job3126082'], env=env)
    if rc == 0 and (m.ROOT / 'QUEUE_DONE').is_file():
        m.archive(layer)
        (CONTROL / 'ALL_REMAINING_8_DONE').write_text(time.strftime('%F %T %Z') + '\n')
        status('ALL_REMAINING_8_DONE')
    else:
        status('L7_INCOMPLETE_NO_AUTOMATIC_RETRY', rc=rc)
        return rc or 76
    return 0

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'prepare': prepare()
    elif mode == 'follow': sys.exit(follow())
    elif mode == 'archive': backend().archive(sys.argv[2])
    elif mode == 'validate': generate(backend()); print('VALIDATION_OK')
    else: raise ValueError(mode)
