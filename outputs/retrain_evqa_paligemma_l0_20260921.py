"""Authorized isolated main-config L0 rerun, exclusively inside Job 3178538."""
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
import traceback

ROOT = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2')
PROJECT = ROOT / 'VisEdit-main'
OUT = ROOT / 'server_results/evqa_paligemma_l0_main_retrain_job3178538_20260921'
RUNNER = PROJECT / 'scripts/run_evqa_pilot500_blip2_visedit_sweep_l0_snapshot_20260921.py'
CLEANER = PROJECT / 'scripts/safe_cleanup_manifest_l0_20260921.py'
LAUNCHER = 2905258
EXPECTED_CMD = 'launch_formal_top3_stage2_20260812.sh job3150065'
CHILD = None


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def record(name, data):
    data = dict(data, time=time.strftime('%Y-%m-%d %H:%M:%S %Z'))
    p = OUT / (name + '.json')
    tmp = p.with_suffix('.partial')
    tmp.write_text(json.dumps(data, indent=2), encoding='utf-8')
    tmp.replace(p)
    print(name.upper(), json.dumps(data), flush=True)


def process(pid):
    p = Path('/proc') / str(pid)
    stat = (p / 'stat').read_text().split(') ', 1)[1].split()
    return stat[19], stat[0], (p / 'cmdline').read_bytes().replace(b'\0', b' ').decode()


def descendants(pid):
    found = []
    for child in (Path('/proc') / str(pid) / 'task' / str(pid) / 'children').read_text().split():
        found.append((int(child), process(int(child))))
        found.extend(descendants(int(child)))
    return found


def gpu_gate(minimum):
    values = subprocess.check_output(['nvidia-smi', '-i', '0', '--query-gpu=memory.total,memory.used,memory.free,utilization.gpu', '--format=csv,noheader,nounits'], text=True).strip()
    free = int(values.split(',')[2])
    if free < minimum:
        raise RuntimeError('GPU gate failed: ' + values)
    raw = subprocess.check_output(['nvidia-smi', '-i', '0', '--query-compute-apps=pid,used_memory', '--format=csv,noheader,nounits'], text=True)
    for line in raw.splitlines():
        pid = int(line.split(',')[0])
        try:
            cmd = process(pid)[2]
        except FileNotFoundError:
            continue
        if 'ipykernel_launcher' not in cmd:
            raise RuntimeError('Unrelated non-kernel GPU process exists: ' + str(pid))
    record('gpu_preflight', dict(gpu=values, processes=raw, minimum_free_mib=minimum))


def run_phase(phase, command):
    global CHILD
    record('status', dict(phase=phase, command=command))
    with (OUT / (phase + '.log')).open('x') as log:
        CHILD = subprocess.Popen(command, cwd=str(PROJECT), stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        record(phase + '_process', dict(pid=CHILD.pid, command=command))
        rc = CHILD.wait()
        CHILD = None
    record(phase + '_exit', dict(returncode=rc))
    cfg = OUT / 'run_config.json'
    if cfg.exists():
        shutil.copy2(cfg, OUT / (phase + '_run_config.json'))
    return rc


def command(config):
    return [sys.executable, '-u', str(RUNNER), '--out-root', str(OUT), '--layers', '0',
            '--epochs', '50', '--batch-size', '2', '--model-name', 'paligemma-3b', '--device', 'cuda:0',
            '--train-data', str(ROOT / 'server_results/evqa_proxy_train500_eval500_20260528/data/vqa_train_proxy500.json'),
            '--train-img-root', str(ROOT / 'server_results/evqa_proxy_train500_eval500_20260528/images'),
            '--eval-data', str(PROJECT / 'data/easy-edit-mm/vqa/vqa_eval.json'),
            '--eval-img-root', str(PROJECT / 'data/easy-edit-mm/images'), '--config-path', str(config),
            '--seed', '20260601', '--ema-alpha', '0.1', '--data-buffer-size', '4',
            '--keep-top-ckpts', '5', '--keep-last-ckpts', '2']


def select_finite(rows):
    candidates = [r for r in rows if math.isfinite(float(r['ema_loss'])) and math.isfinite(float(r['loss']))
                  and Path(r['ckpt_path']).is_file()]
    if not candidates:
        raise RuntimeError('No finite surviving checkpoint; evaluation cannot start')
    return min(candidates, key=lambda r: float(r['ema_loss']))


def finish(train_rc, config):
    import torch
    layer = OUT / 'layer_00'
    rows = list(csv.DictReader((layer / 'loss_history.csv').open()))
    best = select_finite(rows)
    checkpoint = Path(best['ckpt_path']).resolve(strict=True)
    checkpoint.relative_to(layer.resolve())
    saved = torch.load(str(checkpoint), map_location='cpu')
    assert int(saved['epoch']) == int(best['epoch'])
    assert abs(float(saved['ema_loss']) - float(best['ema_loss'])) < 1e-6
    assert all(not torch.is_tensor(t) or torch.isfinite(t).all().item()
               for state in saved['train_modules'].values() for t in state.values()), 'Nonfinite selected parameters'
    del saved
    trained50 = train_rc == 0 and (layer / 'train.done').exists() and max(int(r['epoch']) for r in rows) >= 50
    nonfinite = any(not math.isfinite(float(r['ema_loss'])) or not math.isfinite(float(r['loss'])) for r in rows)
    selected = dict(layer=0, status='TRAIN_DONE' if trained50 else 'TRAIN_INCOMPLETE_FINITE_RECOVERED',
                    epoch=int(best['epoch']), i=int(best['i']), loss=float(best['loss']),
                    ema_loss=float(best['ema_loss']), checkpoint=str(checkpoint))
    with (layer / 'selected_checkpoint.tsv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(selected), delimiter='\t')
        w.writeheader()
        w.writerow(selected)
    checkpoint_hash = digest(checkpoint)
    record('selection_audit', dict(selected=selected, training_complete_50_epochs=trained50,
           historical_layer_nonconvergent=True, current_convergence='requires loss-curve review',
           nonfinite_history=nonfinite, checkpoint_sha256=checkpoint_hash, training_returncode=train_rc,
           selection='minimum finite EMA within this new main-config run, never mixed with historical or stable runs'))
    gpu_gate(24576)
    rc = run_phase('eval', command(config) + ['--skip-train'])
    if rc:
        raise RuntimeError('Independent evaluation failed: ' + str(rc))
    result = json.loads((layer / 'eval_full.done').read_text())
    assert int(result['eval_samples']) == 2093
    assert Path(result['checkpoint']).resolve() == checkpoint
    assert all(math.isfinite(float(result[k])) for k in ['Rel', 'T-Gen', 'M-Gen', 'T-Loc', 'M-Loc', 'Average'])
    detail = Path(result['result_dir']) / 'results.json'
    assert len(json.loads(detail.read_text())) == 2093
    assert digest(checkpoint) == checkpoint_hash
    record('verified_evaluation', dict(result=result, results_sha256=digest(detail),
           training_complete_50_epochs=trained50, historical_layer_nonconvergent=True,
           current_convergence='requires loss-curve review', checkpoint_sha256=checkpoint_hash))
    if trained50:
        targets = []
        for p in checkpoint.parent.iterdir():
            if p.is_file() and not p.is_symlink() and p.resolve() != checkpoint:
                assert p.name.startswith('epoch-') and '-ema_loss-' in p.name, 'Unexpected checkpoint sibling; cleanup stopped'
                targets.append((p.resolve(), 'nonselected checkpoint after verified 2093-sample eval'))
        if targets:
            manifest = OUT / 'cleanup_manifest.tsv'
            with manifest.open('w', newline='') as f:
                w = csv.writer(f, delimiter='\t')
                w.writerow(['path', 'reason'])
                w.writerows(targets)
            audit = OUT / 'cleanup_audit.json'
            base = [sys.executable, str(CLEANER), '--root', str(layer), '--manifest', str(manifest)]
            subprocess.run(base + ['--mode', 'audit', '--audit-output', str(audit)], check=True)
            subprocess.run(base + ['--mode', 'delete', '--audit-report', str(audit),
                '--confirm-sha256', digest(manifest), '--confirm-text', 'DELETE-EXACT-VALIDATED-MANIFEST',
                '--delete-log', str(OUT / 'cleanup_deleted.json')], check=True)
            audit_dir = Path('/var/tmp/ph_teacher3/cleanup_audits/evqa_paligemma_l0_20260921')
            audit_dir.mkdir(parents=True, exist_ok=True)
            for name in ('cleanup_manifest.tsv', 'cleanup_audit.json', 'cleanup_deleted.json'):
                shutil.copy2(OUT / name, audit_dir / name)
    record('status', dict(phase='EVAL_VERIFIED', training_complete_50_epochs=trained50,
                          result=result, note='Retain historical nonconvergence; new loss curve requires review'))


def stop_handler(signum, frame):
    raise SystemExit('Controller received signal ' + str(signum))


def main():
    assert os.environ.get('SLURM_JOB_ID') == '3178538'
    assert os.uname().nodename.split('.')[0] == 'g08'
    OUT.mkdir(parents=True, exist_ok=True)
    lock = (OUT / 'controller.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    assert not (OUT / 'training.log').exists(), 'Never restart or overwrite an existing rerun'
    token, state, cmd = process(LAUNCHER)
    assert EXPECTED_CMD in cmd and state != 'T'
    assert all(p[1][2].strip().startswith('sleep ') for p in descendants(LAUNCHER)), 'Launcher is not idle'
    gpu_gate(49152)
    config = OUT / 'original_main_config.yaml'
    shutil.copy2(PROJECT / 'configs/vead/paligemma-3b.yaml', config)
    record('protocol', dict(job=3178538, node='g08', gpu=0, epochs=50, batch_size=2, seed=20260601,
           ema_alpha=0.1, learning_rate=1e-4, data_buffer_size=4, train_samples=500, eval_samples=2093,
           runner_sha256=digest(RUNNER), config_sha256=digest(config), launcher_pid=LAUNCHER,
           launcher_start_ticks=token, tmp_policy='TMPDIR and all outputs on shared storage'))
    signal.signal(signal.SIGTERM, stop_handler)
    signal.signal(signal.SIGINT, stop_handler)
    suspended = False
    queue_lock = None
    try:
        assert process(LAUNCHER)[0] == token
        os.kill(LAUNCHER, signal.SIGSTOP)
        suspended = True
        time.sleep(0.2)
        assert process(LAUNCHER)[1] == 'T'
        assert all(p[1][2].strip().startswith('sleep ') for p in descendants(LAUNCHER)), 'Launcher raced; abort'
        queue_lock = Path('/tmp/ph_teacher3/formal_top3_stage2_job3150065_20260812/launcher.lock').open('a')
        fcntl.flock(queue_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        record('launcher_hold', dict(pid=LAUNCHER, start_ticks=token, action='SIGSTOP idle waiter only'))
        gpu_gate(49152)
        scratch = OUT / 'scratch'
        scratch.mkdir(exist_ok=True)
        os.environ.update(TMPDIR=str(scratch), PYTHONPATH=str(PROJECT), CUDA_VISIBLE_DEVICES='0',
                          PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True', TOKENIZERS_PARALLELISM='false',
                          OMP_NUM_THREADS='4', MKL_NUM_THREADS='4')
        train_rc = run_phase('training', command(config) + ['--skip-eval'])
        finish(train_rc, config)
    except BaseException as exc:
        record('controller_error', dict(error=repr(exc), traceback=traceback.format_exc()))
        raise
    finally:
        if CHILD is not None and CHILD.poll() is None:
            os.killpg(CHILD.pid, signal.SIGTERM)
            try:
                CHILD.wait(timeout=30)
            except subprocess.TimeoutExpired:
                os.killpg(CHILD.pid, signal.SIGKILL)
                CHILD.wait()
        if queue_lock is not None:
            queue_lock.close()
        if suspended:
            try:
                current = process(LAUNCHER)
                if current[0] == token and EXPECTED_CMD in current[2]:
                    os.kill(LAUNCHER, signal.SIGCONT)
                    record('launcher_released', dict(pid=LAUNCHER, action='SIGCONT original waiter'))
            except FileNotFoundError:
                record('launcher_released', dict(pid=LAUNCHER, action='already exited; no replacement started'))


if __name__ == '__main__':
    main()
