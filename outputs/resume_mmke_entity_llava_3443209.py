"""Job-scoped L1 recovery; durable checkpoints, node-local disposable caches."""
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

BASE = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2')
PROJ = BASE / 'VisEdit-main'
PY = '/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python'
SHARED = BASE / 'server_results/mmke_entity_llava_job3443209_20260926'
ROOT = SHARED / 'work'
TMP = Path('/tmp/ph_teacher3/mmke_entity_llava_job3443209_20260926')
OLD = Path('/tmp/ph_teacher3/formal_top3_stage2_job3126082_20260812')
OLD_SHARED = BASE / 'server_results/formal_top3_stage2_20260812/job3126082'
BACKUP = OLD_SHARED / 'pause_snapshots/20260921_110450-before_p0'
COMBO = Path('mmke-entity/llava-v1.5-7b')
LAYERS = [1, 0, 2, 13, 11, 12, 4]
CP_NAME = 'epoch-17-i-5406-ema_loss-0.7862'
CP_HASH = '18149e4dcc14c199d00eb768568d04b31637b1d4ccab574138b92e50fd6ddc37'
PINNED = {
    'scripts/launch_formal_top3_stage2_20260812.sh': '71caef0de33bd7d2d7aa1b8ea9f27b03ef2b0489fbbedfbf391e5fd396d04194',
    'scripts/run_mmke_llava_shared_gpu_sweep.py': '936ccf7e4b13365b3fe8f3d8d7d07573448342507c7a75572b63a75d9e06cd56',
    'configs/vead/llava-v1.5-7b.yaml': 'b6a5f7cd5c29012cee2e84de580acdcc7aef460f7238c156759e69072f992b52',
}

def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

def log(s):
    print(time.strftime('%F %T %Z') + ' ' + s, flush=True)

def copy_verified(src, dst):
    src, dst = Path(src), Path(dst)
    assert not dst.exists(), str(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    h = sha(src)
    shutil.copy2(str(src), str(dst))
    assert sha(src) == sha(dst) == h

def generate():
    for p, h in PINNED.items():
        assert sha(PROJ / p) == h, 'changed source: ' + p
    t = (PROJ / 'scripts/launch_formal_top3_stage2_20260812.sh').read_text()
    replacements = {
        'RUN_ROOT=' + str(OLD): 'RUN_ROOT=' + str(ROOT),
        'SHARED_ROOT=' + str(OLD_SHARED): 'SHARED_ROOT=' + str(SHARED / 'accepted'),
        'EXPECTED_JOB=3126082': 'EXPECTED_JOB=3443209',
        'GPU_TRAIN_FREE_MIN_MIB=61440': 'GPU_TRAIN_FREE_MIN_MIB=73728',
        "'15,16,14,28,27,26,23,22,24,1,9,7,0,2,13,11,12,4'": "'1,0,2,13,11,12,4'",
        'wait_gpu_clean "$GPU_EVAL_FREE_MIN_MIB" 1': 'wait_gpu_clean "$GPU_EVAL_FREE_MIN_MIB" 0',
        'eval_allow_non_kernel=1': 'eval_allow_non_kernel=0',
    }
    for old, new in replacements.items():
        assert old in t, old
        t = t.replace(old, new)
    # No other dataset/model may execute in this scoped replacement queue.
    t = '\n'.join(line for line in t.splitlines() if not line.strip().startswith(
        ('run_combo evqa-pilot500 ', 'combo_complete evqa-pilot500 '))) + '\n'
    old = '    cleanup_nonselected_checkpoints "$d" || note=${note:+$note;}\'cleanup_warning\''
    assert t.count(old) == 1
    t = t.replace(old, '    if ! "$PY" "' + str(SHARED / 'control/resume_mmke_entity_llava_3443209.py') +
                  '" archive "$d"; then\n      log_status "ARCHIVE_FAILED_STOP_QUEUE layer=$layer"\n      exit 75\n    fi')
    # Never continue to the next layer after an unsuccessful current layer.
    old = '    run_layer "$dataset" "$model" "$layer" "$runner" "$config" "$train_json" "$train_img" "$eval_json" "$eval_img" "$lowmem" "$shared_model"'
    assert t.count(old) == 1
    t = t.replace(old, old + '\n    if ! complete_exists "$RUN_ROOT/$dataset/$model/layer_$(printf \'%02d\' "$layer")" && ! archived_complete_exists "$SHARED_ROOT/$dataset/$model/layer_$(printf \'%02d\' "$layer")"; then\n      log_status "STOP_INCOMPLETE layer=$layer"\n      exit 76\n    fi')
    subprocess.run(['bash', '-n'], input=t, universal_newlines=True, check=True)
    return t

def prepare():
    assert os.uname()[1].split('.')[0] == 'g09'
    t = generate()
    assert not ROOT.exists(), 'work root exists; inspect instead of overwriting'
    assert sha(BACKUP / CP_NAME) == CP_HASH
    import torch
    ck = torch.load(str(BACKUP / CP_NAME), map_location='cpu', weights_only=False)
    assert ck['epoch'] == 17 and ck['i'] == 5406 and ck['opt']['state']
    assert list(ck['train_modules']) == ['language_model.model.layers.1']
    assert math.isfinite(ck['ema_loss'])
    del ck
    (ROOT / COMBO).mkdir(parents=True)
    for kind in ['cache', 'eval_cache']:
        target = TMP / kind
        target.mkdir(parents=True, exist_ok=True)
        (ROOT / COMBO / kind).symlink_to(target, target_is_directory=True)
    layer = ROOT / COMBO / 'layer_01'
    hist = list(csv.DictReader((BACKUP / 'loss_history.csv').open()))
    last = next(r for r in hist if int(r['epoch']) == 17)
    oldcp = Path(last['ckpt_path'])
    newcp = ROOT / oldcp.relative_to(OLD)
    copy_verified(BACKUP / CP_NAME, newcp)
    for name in ['loss_history.csv', 'run_config.json', 'SHA256SUMS.txt']:
        copy_verified(BACKUP / name, SHARED / 'provenance/l1_epoch17' / name)
    (layer / 'loss_history.csv').write_text((BACKUP / 'loss_history.csv').read_text().replace(str(OLD), str(ROOT)))
    # Preserve original metadata, do not create train.done for unfinished training.
    for p in PINNED:
        copy_verified(PROJ / p, SHARED / 'provenance/code' / p)
    for p in ['editor/vllm_editors/base.py', 'editor/vllm_editors/vead/vead.py',
              'editor/vllm_editors/vead/adpt_model.py', 'utils/GLOBAL.py']:
        copy_verified(PROJ / p, SHARED / 'provenance/code' / p)
    (SHARED / 'control/launcher_scoped.sh').write_text(t)
    manifest = {
        'job': 3443209, 'node': 'g09', 'previous_job': 3178423,
        'sequence': LAYERS, 'deferred_layers': [7],
        'l7_status': 'old log epoch12 sample520/636; g07 tmp inaccessible after job expiry; no matching shared checkpoint found',
        'l1_resume_checkpoint': str(newcp), 'sha256': CP_HASH,
        'loaded_epoch': 17, 'loaded_i': 5406, 'next_epoch': 18, 'next_i': 5407,
        'training_protocol_changed': False, 'epochs': 50, 'batch_size': 2,
        'seed': 20260601, 'lr': 1e-4, 'ema_alpha': 0.1,
        'selection': 'minimum finite EMA over original and resumed epoch history',
        'eval_count': 954, 'train_gate_mib': 73728, 'eval_gate_mib': 56320,
        'storage': 'checkpoints/history/logs/results directly on shared filesystem; disposable caches on g09 tmp',
        'rng_note': 'optimizer/epoch/step restored; original checkpoint has no RNG state, not bitwise uninterrupted equivalence',
        'completion_scope': '7 resumed/pending layers only; 10 previous complete layers and deferred L7 are separate',
        'created': time.strftime('%F %T %Z'),
    }
    (SHARED / 'provenance/recovery.json').write_text(json.dumps(manifest, indent=2))
    log('PREPARED L1 epoch17 hash and optimizer verified; L7 deferred')

def clean_exact(paths, scope, label):
    paths = [p.resolve() for p in paths if p.is_file() and not p.is_symlink()]
    if not paths:
        return
    audit = SHARED / 'cleanup_audits' / (label + '_' + time.strftime('%Y%m%d_%H%M%S'))
    audit.mkdir(parents=True, exist_ok=False)
    manifest = audit / 'manifest.tsv'
    with manifest.open('w') as f:
        f.write('path\treason\n')
        for p in paths:
            p.relative_to(scope.resolve())
            f.write(str(p) + '\tcompleted_954_eval_and_sha256_verified_shared_archive\n')
    args = [PY, str(SHARED / 'control/safe_cleanup_manifest.py'), '--root', str(scope), '--manifest', str(manifest)]
    subprocess.run(args + ['--mode', 'audit', '--audit-output', str(audit / 'audit.json')], check=True)
    log('CLEANUP_AUDIT label=%s files=%d bytes=%d sha256=%s' % (label, len(paths), sum(p.stat().st_size for p in paths), sha(manifest)))
    subprocess.run(args + ['--mode', 'delete', '--audit-report', str(audit / 'audit.json'),
                          '--confirm-sha256', sha(manifest), '--confirm-text', 'DELETE-EXACT-VALIDATED-MANIFEST',
                          '--delete-log', str(audit / 'deleted.json')], check=True)

def archive(d):
    d = Path(d).resolve()
    rel = d.relative_to(ROOT)
    assert rel in [COMBO / ('layer_%02d' % l) for l in LAYERS]
    sel = list(csv.DictReader((d / 'selected_checkpoint.tsv').open(), delimiter='\t'))[0]
    cp = Path(sel['checkpoint']).resolve()
    cp.relative_to(d)
    ev = json.load((d / 'eval_full.done').open())
    assert (d / 'train.done').is_file() and cp.is_file()
    assert ev['status'] == 'EVAL_DONE' and ev['eval_samples'] == 954
    assert all(math.isfinite(float(ev[k])) for k in ['Rel', 'T-Gen', 'M-Gen', 'T-Loc', 'M-Loc', 'Average'])
    result = next(d.glob('eval_full/**/results.json'))
    assert len(json.load(result.open())) == 954
    hist = list(csv.DictReader((d / 'loss_history.csv').open()))
    valid = [r for r in hist if math.isfinite(float(r['ema_loss'])) and math.isfinite(float(r['loss']))]
    assert abs(min(float(r['ema_loss']) for r in valid) - float(sel['ema_loss'])) < 1e-8
    dest = SHARED / 'accepted' / rel
    if not dest.exists():
        stage = Path(str(dest) + '.partial')
        stage.mkdir(parents=True, exist_ok=False)
        files = [cp] + [d / n for n in ['train.done', 'selected_checkpoint.tsv', 'eval_full.done', 'loss_history.csv']]
        files += [p for p in (d / 'eval_full').rglob('*') if p.is_file()]
        hashes = []
        for p in files:
            target = stage / p.relative_to(d)
            copy_verified(p, target)
            hashes.append({'path': str(p.relative_to(d)), 'sha256_source': sha(p), 'bytes': p.stat().st_size})
        for n in ['train.done', 'selected_checkpoint.tsv', 'eval_full.done', 'loss_history.csv']:
            p = stage / n
            p.write_text(p.read_text().replace(str(d), str(dest)))
        for item in hashes:
            item['sha256_archive'] = sha(stage / item['path'])
        (stage / 'ARCHIVE_MANIFEST.json').write_text(json.dumps(hashes, indent=2))
        (stage / 'SYNC_VERIFIED').write_text(time.strftime('%F %T %Z') + '\n')
        stage.rename(dest)
    assert sha(dest / cp.relative_to(d)) == sha(cp)
    subprocess.run([PY, str(SHARED / 'control/verify_result_tree.py'), '--root', str(dest),
                    '--dataset', 'mmke-entity', '--strict', '--output', str(dest / 'verification.json')], check=True)
    clean_exact([p for p in cp.parent.iterdir() if p.name.startswith('epoch-') and not p.name.endswith('.lock') and p.resolve() != cp], d, d.name + '_nonselected')
    cache = TMP / 'cache' / d.name
    if cache.exists():
        clean_exact([p for p in cache.rglob('*') if p.is_file() and not p.name.endswith('.lock')], cache, d.name + '_cache')
    log('ARCHIVE_VERIFIED ' + str(dest))

def launch():
    assert os.environ.get('SLURM_JOB_ID') == '3443209'
    assert os.uname()[1].split('.')[0] == 'g09'
    t = generate()
    script = SHARED / 'control/launcher_scoped.sh'
    assert script.read_text() == t
    locks = []
    for p in [SHARED / 'control/controller.lock', BASE / 'server_results/gpu_locks/g09_gpu0.lock']:
        p.parent.mkdir(parents=True, exist_ok=True)
        f = p.open('a')
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        locks.append(f)
    assert not subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader,nounits'], universal_newlines=True).strip(), 'GPU became occupied; inspect before launch'
    env = os.environ.copy()
    env['GPU_TRAIN_ALLOW_NON_KERNEL'] = '0'
    log('LAUNCH job3443209 L1(epoch18)->L0->L2->L13->L11->L12->L4; L7 deferred')
    rc = subprocess.call(['bash', str(script), 'job3126082'], env=env)
    log('CONTROLLER_EXIT rc=%s' % rc)
    sys.exit(rc)

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'prepare': prepare()
    elif mode == 'launch': launch()
    elif mode == 'archive': archive(sys.argv[2])
    elif mode == 'validate': generate(); log('VALIDATION_OK')
    else: raise ValueError(mode)
