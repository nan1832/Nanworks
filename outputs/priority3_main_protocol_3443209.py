"""Three authorized missing-layer runs; no automatic LLaVA restart."""
import csv
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

BASE = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2')
PROJ = BASE / 'VisEdit-main'
SR = BASE / 'server_results'
ROOT = SR / 'priority3_main_protocol_job3443209_20260926'
TMP = Path('/tmp/ph_teacher3/priority3_main_protocol_job3443209_20260926')
LLAVA = SR / 'mmke_entity_llava_job3443209_20260926'
PY = '/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python'
RUNNER = PROJ / 'scripts/run_evqa_pilot500_blip2_visedit_sweep.py'
JOBS = [('visual', 'instructblip-vicuna-7b', 20, 214, 293),
        ('entity', 'instructblip-vicuna-7b', 20, 636, 954),
        ('entity', 'smolvlm-1.7b', 8, 636, 954)]
OLD = {k: SR / v for k, v in {
    'visual': 'mmke_visual_top3_union_train_eval_7models_20260613_014644',
    'entity': 'mmke_entity_top3_union_train_eval_7models_20260616_155000'}.items()}
METRICS = ['Rel', 'T-Gen', 'M-Gen', 'T-Loc', 'M-Loc', 'Average']

def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

def write_json(p, data):
    tmp = p.with_name(p.name + '.partial')
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(p)

def status(state, **kwargs):
    d = dict(time=time.strftime('%F %T %Z'), state=state, job=3443209,
             node='g09', pid=os.getpid(), llava_auto_resume=False, **kwargs)
    write_json(ROOT / 'control/status.json', d)
    print(json.dumps(d), flush=True)

def copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    assert not dst.exists(), str(dst)
    h = sha(src)
    shutil.copy2(str(src), str(dst))
    assert sha(src) == sha(dst) == h
    return h

def read_json(p):
    # Shared filesystem writers may expose a brief empty/partial JSON.
    for n in range(6):
        try:
            return json.loads(p.read_text())
        except (ValueError, FileNotFoundError):
            if n == 5:
                raise
            time.sleep(2)

def prepare():
    import yaml
    assert not (ROOT / 'work').exists(), 'Already prepared; do not overwrite'
    pause = read_json(LLAVA / 'pause_for_priority3_20260926/pause.json')
    assert pause['state'] == 'PAUSED_VERIFIED'
    manifest = {'created': time.strftime('%F %T %Z'), 'jobs': JOBS, 'files': {},
                'protocol': {'epochs': 50, 'batch_size': 2, 'lr': 0.0001,
                             'seed_parameter': 20260601, 'train_init_seed': '20260601 + layer',
                             'ema_alpha': 0.1, 'data_buffer_size': 4, 'keep_top_ckpts': 5,
                             'keep_last_ckpts': 2, 'selection': 'minimum finite EMA',
                             'main_only': True, 'automatic_config_fallback': False},
                'references': [], 'llava_auto_resume': False}
    files = {RUNNER, PROJ / 'utils/GLOBAL.py'}
    for folder in ['editor', 'dataset', 'evaluation', 'utils', 'vllms']:
        files.update((PROJ / folder).rglob('*.py'))
    for ds, model, layer, nt, ne in JOBS:
        old_run = OLD[ds] / model / 'run_config.json'
        args = read_json(old_run)
        for key, val in [('epochs', '50'), ('batch_size', '2'), ('seed', '20260601'),
                         ('ema_alpha', '0.1'), ('data_buffer_size', '4')]:
            assert str(args[key]) == val, (old_run, key, args[key])
        cfg = PROJ / 'configs/vead' / (model + '.yaml')
        if 'instruct' in model:
            ref_cfg = next((OLD[ds] / model / 'layer_14').glob('records/**/config.yaml'))
        else:
            ref_cfg = next((SR / 'cma_modelpred_top3_missing3_adapter_backfill_20260913_job3178423/mmke-visual/smolvlm-1.7b/layer_05').glob('records/**/config.yaml'))
        a, b = yaml.safe_load(ref_cfg.read_text()), yaml.safe_load(cfg.read_text())
        a.pop('edit_layers'); b.pop('edit_layers')
        assert a == b, 'Historical main config mismatch: ' + model
        assert b['train_cfg'] == dict(lr=1e-4, rel_lambda=1, gen_lambda=1, loc_lambda=1, inf_mapper_lambda=0.1)
        assert b['IT']['add_it'] is True
        refdir = ROOT / 'provenance/references' / ('mmke-' + ds) / model
        copy(old_run, refdir / 'historical_run_config.json')
        copy(ref_cfg, refdir / 'historical_record_config.yaml')
        manifest['references'].append({'dataset': ds, 'model': model, 'run_args': str(old_run),
                                      'record_config': str(ref_cfg),
                                      'config_match_excluding_layer': True,
                                      'note': 'SmolVLM entity historical args use the same main YAML; archived main YAML cross-checked against completed visual L5.' if 'smol' in model else ''})
        files.add(cfg)
        out = ROOT / 'work' / ('mmke-' + ds) / model
        out.mkdir(parents=True)
        for kind in ['cache', 'eval_cache']:
            target = TMP / ('mmke-' + ds) / model / kind
            target.mkdir(parents=True, exist_ok=True)
            (out / kind).symlink_to(target, target_is_directory=True)
        for split, count in [('train', nt), ('eval', ne)]:
            p = OLD[ds] / 'data' / ('vqa_mmke_%s_%s_evqa_compat.json' % (ds, split))
            assert str(p) == args[split + '_data']
            rows = read_json(p)
            assert len(rows) == count, (p, len(rows))
            for r in rows:
                for key in ['image', 'image_rephrase', 'm_loc']:
                    assert (BASE / 'datasets/MMKE-Bench/data_image' / r[key]).is_file(), (key, r[key])
            manifest['files'][str(p)] = sha(p)
        assert not (OLD[ds] / model / ('layer_%02d' % layer) / 'eval_full.done').exists(), 'Existing eval: inspect before rerun'
    for p in sorted(files):
        manifest['files'][str(p)] = copy(p, ROOT / 'provenance/code' / p.relative_to(PROJ))
    for name in ['safe_cleanup_manifest.py', 'verify_result_tree.py']:
        copy(LLAVA / 'control' / name, ROOT / 'control' / name)
    write_json(ROOT / 'provenance/protocol.json', manifest)
    status('PREPARED', queue=JOBS)

def pin_check():
    for p, h in read_json(ROOT / 'provenance/protocol.json')['files'].items():
        assert sha(p) == h, 'Source or dataset changed; stopped for review: ' + p

def gpu_wait(label):
    good = 0
    while good < 3:
        pids = subprocess.check_output(['nvidia-smi', '-i', '0', '--query-compute-apps=pid', '--format=csv,noheader,nounits'], universal_newlines=True).strip()
        free = int(subprocess.check_output(['nvidia-smi', '-i', '0', '--query-gpu=memory.free', '--format=csv,noheader,nounits'], universal_newlines=True).strip())
        # Keep historical configs intact; an idle full card is available, no OOM-driven fallback.
        good = good + 1 if not pids and free >= 73728 else 0
        status('GPU_GATE', phase=label, free_mib=free, required_mib=73728, stable=good, gpu_pids=pids)
        if good < 3:
            time.sleep(20)

def stage(job, phase):
    ds, model, layer, nt, ne = job
    out = ROOT / 'work' / ('mmke-' + ds) / model
    data = OLD[ds] / 'data'
    cfg = ROOT / 'provenance/code/configs/vead' / (model + '.yaml')
    args = [PY, '-u', str(RUNNER), '--out-root', str(out), '--layers', str(layer),
            '--epochs', '50', '--batch-size', '2', '--model-name', model, '--device', 'cuda:0',
            '--train-data', str(data / ('vqa_mmke_%s_train_evqa_compat.json' % ds)),
            '--eval-data', str(data / ('vqa_mmke_%s_eval_evqa_compat.json' % ds)),
            '--train-img-root', str(BASE / 'datasets/MMKE-Bench/data_image'),
            '--eval-img-root', str(BASE / 'datasets/MMKE-Bench/data_image'),
            '--config-path', str(cfg), '--seed', '20260601', '--ema-alpha', '0.1',
            '--data-buffer-size', '4', '--keep-top-ckpts', '5', '--keep-last-ckpts', '2',
            '--skip-eval' if phase == 'train' else '--skip-train']
    pin_check()
    gpu_wait('%s/%s/L%d/%s' % (ds, model, layer, phase))
    logfile = out / (phase + '_L%d.log' % layer)
    assert not logfile.exists(), 'Never silently retry a stage'
    env = os.environ.copy()
    env['PYTHONPATH'] = str(PROJ) + ':' + env.get('PYTHONPATH', '')
    env['CUDA_VISIBLE_DEVICES'] = '0'
    with logfile.open('x') as log:
        child = subprocess.Popen(args, cwd=str(PROJ), env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        status('RUNNING', dataset=ds, model=model, layer=layer, phase=phase, child_pid=child.pid, log=str(logfile), command=args)
        last_size, last_change = -1, time.time()
        while child.poll() is None:
            size = logfile.stat().st_size
            if size != last_size:
                last_size, last_change = size, time.time()
            if time.time() - last_change > 7200:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
                raise RuntimeError('Own child stopped after 2h without log progress: ' + str(logfile))
            time.sleep(15)
        assert child.returncode == 0, (phase, child.returncode, str(logfile))
    copy(out / 'run_config.json', out / (phase + '_run_config.json'))

def validate_train(job):
    ds, model, layer, nt, ne = job
    d = ROOT / 'work' / ('mmke-' + ds) / model / ('layer_%02d' % layer)
    assert read_json(d / 'train.done')['status'] == 'TRAIN_DONE'
    hist = list(csv.DictReader((d / 'loss_history.csv').open()))
    assert [int(r['epoch']) for r in hist] == list(range(1, 51)), 'Not full 50-epoch history'
    assert int(hist[-1]['i']) == 50 * math.ceil(nt / 2)
    sel = list(csv.DictReader((d / 'selected_checkpoint.tsv').open(), delimiter='\t'))
    assert len(sel) == 1
    sel = sel[0]
    finite = [r for r in hist if all(math.isfinite(float(r[k])) for k in ['loss', 'ema_loss'])]
    assert abs(min(float(r['ema_loss']) for r in finite) - float(sel['ema_loss'])) < 1e-9
    cp = Path(sel['checkpoint']).resolve()
    cp.relative_to(d.resolve())
    assert cp.is_file() and cp.stat().st_size > 0
    return d, cp, sel

def archive_and_clean(job):
    ds, model, layer, nt, ne = job
    d, cp, sel = validate_train(job)
    ev = read_json(d / 'eval_full.done')
    assert ev['status'] == 'EVAL_DONE' and ev['eval_samples'] == ne
    assert all(math.isfinite(float(ev[k])) for k in METRICS)
    assert Path(ev['checkpoint']).resolve() == cp
    assert len(read_json(next(d.glob('eval_full/**/results.json')))) == ne
    dest = ROOT / 'accepted' / ('mmke-' + ds) / model / d.name
    staging = Path(str(dest) + '.partial')
    staging.mkdir(parents=True, exist_ok=False)
    files = [cp] + [d / x for x in ['train.done', 'selected_checkpoint.tsv', 'eval_full.done', 'loss_history.csv']]
    files += [p for p in (d / 'eval_full').rglob('*') if p.is_file()]
    files += list(d.glob('records/**/config.yaml'))
    hashes = []
    for src in files:
        target = staging / src.relative_to(d)
        h = copy(src, target)
        hashes.append({'file': str(src.relative_to(d)), 'source_sha256': h, 'bytes': src.stat().st_size})
    for name in ['train.done', 'selected_checkpoint.tsv', 'eval_full.done', 'loss_history.csv']:
        q = staging / name
        q.write_text(q.read_text().replace(str(d), str(dest)))
    for item in hashes:
        item['archive_sha256'] = sha(staging / item['file'])
    write_json(staging / 'ARCHIVE_MANIFEST.json', hashes)
    staging.rename(dest)
    subprocess.run([PY, str(ROOT / 'control/verify_result_tree.py'), '--root', str(dest),
                    '--dataset', 'mmke-' + ds, '--strict', '--output', str(dest / 'verification.json')], check=True)
    assert sha(cp) == sha(dest / cp.relative_to(d))
    (dest / 'SYNC_VERIFIED').write_text(time.strftime('%F %T %Z'))
    # Only this finished layer's nonselected checkpoints, never LLaVA or active caches.
    redundant = [p for p in cp.parent.iterdir() if p.is_file() and not p.is_symlink() and p.name.startswith('epoch-') and not p.name.endswith('.lock') and p.resolve() != cp]
    if redundant:
        audit = ROOT / 'cleanup_audits' / ('%s_%s_L%d' % (ds, model, layer))
        audit.mkdir(parents=True)
        manifest = audit / 'manifest.tsv'
        manifest.write_text('path\treason\n' + ''.join(str(p.resolve()) + '\tcompleted_independent_eval_and_hash_verified_selected_archive\n' for p in redundant))
        cmd = [PY, str(ROOT / 'control/safe_cleanup_manifest.py'), '--root', str(d), '--manifest', str(manifest)]
        subprocess.run(cmd + ['--mode', 'audit', '--audit-output', str(audit / 'audit.json')], check=True)
        subprocess.run(cmd + ['--mode', 'delete', '--audit-report', str(audit / 'audit.json'),
                             '--confirm-sha256', sha(manifest), '--confirm-text', 'DELETE-EXACT-VALIDATED-MANIFEST',
                             '--delete-log', str(audit / 'deleted.json')], check=True)
    status('LAYER_COMPLETE', dataset=ds, model=model, layer=layer, eval_samples=ne, metrics=ev, archive=str(dest))

def launch():
    assert os.environ.get('SLURM_JOB_ID') == '3443209'
    assert os.uname()[1].split('.')[0] == 'g09'
    assert read_json(LLAVA / 'pause_for_priority3_20260926/pause.json')['state'] == 'PAUSED_VERIFIED'
    locks = []
    for p in [ROOT / 'control/controller.lock', SR / 'gpu_locks/g09_gpu0.lock']:
        f = p.open('a')
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        locks.append(f)
    once = ROOT / 'control/STARTED'
    with once.open('x') as f:
        f.write(time.strftime('%F %T %Z'))
    for job in JOBS:
        stage(job, 'train')
        validate_train(job)
        stage(job, 'eval')
        archive_and_clean(job)
    (ROOT / 'control/ALL_THREE_DONE').write_text(time.strftime('%F %T %Z'))
    status('ALL_THREE_DONE_LLAVA_STAYS_PAUSED', queue=JOBS)

if __name__ == '__main__':
    try:
        if sys.argv[1] == 'prepare':
            prepare()
        elif sys.argv[1] == 'launch':
            launch()
        else:
            raise ValueError(sys.argv[1])
    except Exception as e:
        if (ROOT / 'control').exists():
            status('STOPPED_ERROR_NO_AUTORETRY', error=repr(e))
        raise
