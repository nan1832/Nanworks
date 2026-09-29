"""One-shot, additive backup. Never changes source files or running processes."""
import csv
import datetime
import glob
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tarfile

BASE = Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2')
PROJECT = BASE / 'VisEdit-main'
LOCAL = Path('/tmp/ph_teacher3/formal_top3_stage2_job3150065_20260812')
ARCHIVE = BASE / 'server_results/formal_top3_stage2_20260812/job3150065'
COMBO = 'evqa-pilot500/llava-v1.5-7b'
DEST = BASE / 'server_results/resume_handoffs/evqa_llava_job3178538_20260924_1340'

def sha(path):
    h = hashlib.sha256()
    with open(str(path), 'rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def main():
    assert subprocess.check_output(['hostname'], universal_newlines=True).strip() == 'g08'
    DEST.mkdir(parents=True, exist_ok=False)
    manifest = {'time_beijing': datetime.datetime.now().isoformat(), 'job': 3178538,
                'node': 'g08', 'source_root': str(LOCAL), 'backup_root': str(DEST),
                'remaining_order': [2, 4], 'old_job_stopped': False,
                'files': [], 'layers': [], 'path_remap_required': True,
                'note': 'Point-in-time snapshot. Original markers retain original paths. No active eval completion claimed.'}

    def copy(src, relative, live=False):
        src, dst = Path(src), DEST / relative
        assert src.is_file(), str(src)
        assert not dst.exists(), str(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        before = src.stat()
        digest = hashlib.sha256()
        # For growing logs, copy exactly the initial length; do not chase the writer.
        left = before.st_size
        with src.open('rb') as inp, dst.open('xb') as out:
            while left:
                block = inp.read(min(8 * 1024 * 1024, left))
                if not block:
                    raise RuntimeError('source truncated: ' + str(src))
                out.write(block); digest.update(block); left -= len(block)
        h = digest.hexdigest()
        assert dst.stat().st_size == before.st_size and sha(dst) == h
        if not live:
            assert src.stat().st_size == before.st_size and sha(src) == h, str(src)
        manifest['files'].append({'source': str(src), 'relative_path': str(relative),
                                  'size': before.st_size, 'sha256': h, 'live_prefix_snapshot': live})

    for layer in [15,16,14,7,6,5,24,25,0,1,2,4]:
        rel = Path(COMBO) / ('layer_%02d' % layer)
        # Existing durable archives are kept in place, never overwritten.
        source = ARCHIVE / rel if (ARCHIVE / rel / 'eval_full.done').is_file() else LOCAL / rel
        entry = {'layer': layer, 'source': str(source)}
        sel = source / 'selected_checkpoint.tsv'
        if not sel.is_file():
            entry['state'] = 'not_started'; manifest['layers'].append(entry); continue
        selected = list(csv.DictReader(sel.open(), delimiter='\t'))[0]
        cp = Path(selected['checkpoint'])
        if not cp.is_file():
            candidates = list(source.glob('records/**/' + cp.name))
            cp = next(x for x in candidates if x.is_file())
        assert cp.stat().st_size > 0
        history = source / 'loss_history.csv'
        rows = list(csv.DictReader(history.open())) if history.is_file() else []
        finite = [r for r in rows if math.isfinite(float(r['ema_loss']))]
        if finite:
            assert abs(min(float(r['ema_loss']) for r in finite) - float(selected['ema_loss'])) < 1e-8
        entry.update(selected=selected, selected_source=str(cp), selected_sha256=sha(cp),
                     selected_size=cp.stat().st_size, train_marker=(source/'train.done').is_file())
        marker = source / 'eval_full.done'
        if marker.is_file():
            ev = json.load(marker.open())
            result = list(source.glob('eval_full/**/results.json'))
            assert ev['status'] == 'EVAL_DONE' and ev['eval_samples'] == 2093
            assert result and len(json.load(result[0].open())) == 2093
            assert all(math.isfinite(float(ev[k])) for k in ['Rel','T-Gen','M-Gen','T-Loc','M-Loc','Average'])
            entry.update(state='train_eval_complete', evaluation=ev)
        else:
            entry['state'] = 'training_complete_evaluation_pending_or_active'
        if source == LOCAL / rel:
            copy(cp, Path('layers') / rel / cp.relative_to(source))
            entry['durable_checkpoint'] = str(DEST / 'layers' / rel / cp.relative_to(source))
            # Only selected binary; don't copy caches, lock files or unselected weights.
            for name in ['selected_checkpoint.tsv','train.done','loss_history.csv','eval_full.done']:
                f=source/name
                if f.is_file():copy(f, Path('layers')/rel/name)
            if marker.is_file():
                for f in source.glob('eval_full/**/*'):
                    if f.is_file():copy(f, Path('layers')/rel/f.relative_to(source))
            else:
                for f in source.glob('eval_full/**/*.json'):
                    if f.is_file():copy(f, Path('partial_eval')/rel/f.relative_to(source), live=True)
        else:
            entry['durable_checkpoint']=str(cp)
        manifest['layers'].append(entry)

    for f in LOCAL.glob('logs/evqa-pilot500_llava-v1.5-7b_*.log'):
        copy(f, Path('runtime')/f.relative_to(LOCAL), live=True)
    for name in ['queue.status.log','layer_status.csv']:
        copy(LOCAL/name,Path('runtime')/name,live=True)
    # Preserve actual source/config files, without weights, caches or credentials.
    for folder in ['scripts','configs','dataset','editor','evaluation','utils','models']:
        d=PROJECT/folder
        if not d.is_dir():continue
        for f in d.rglob('*'):
            if f.is_file() and f.suffix in ['.py','.yaml','.yml','.sh'] and '__pycache__' not in f.parts:
                if f.stat().st_size < 4*1024*1024:copy(f,Path('code')/f.relative_to(PROJECT))
    for f in PROJECT.glob('*.py'):copy(f,Path('code')/f.name)
    data_paths=[BASE/'server_results/evqa_proxy_train500_eval500_20260528/data/vqa_train_proxy500.json',
                PROJECT/'data/easy-edit-mm/vqa/vqa_eval.json']
    for f in data_paths:copy(f,Path('data')/f.name)
    manifest['data_roots']={'train_images':str(BASE/'server_results/evqa_proxy_train500_eval500_20260528/images'),
                            'eval_images':str(PROJECT/'data/easy-edit-mm/images')}
    manifest['copied_bytes']=sum(x['size'] for x in manifest['files'])
    manifest['finished_beijing']=datetime.datetime.now().isoformat()
    with (DEST/'manifest.json').open('x') as f:json.dump(manifest,f,ensure_ascii=False,indent=2)
    with (DEST/'SHA256SUMS').open('x') as f:
        for item in manifest['files']:f.write(item['sha256']+'  '+item['relative_path']+'\n')
    # Compact Windows copy excludes checkpoint binaries; selected binaries stay on shared storage.
    with tarfile.open(str(DEST/'compact_handoff.tar.gz'),'w:gz') as tar:
        for item in manifest['files']:
            if '/checkpoints/' not in item['relative_path']:
                tar.add(str(DEST/item['relative_path']),arcname=item['relative_path'])
        for n in ['manifest.json','SHA256SUMS']:tar.add(str(DEST/n),arcname=n)
    print(json.dumps({'backup':str(DEST),'files':len(manifest['files']),
                     'copied_bytes':manifest['copied_bytes'],'compact_sha256':sha(DEST/'compact_handoff.tar.gz'),
                     'layers':[{k:e[k] for k in ['layer','state','durable_checkpoint'] if k in e} for e in manifest['layers']]},indent=2),flush=True)

if __name__=='__main__':main()
