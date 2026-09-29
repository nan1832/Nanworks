"""Read-only remote sweep inventory; run through SSH stdin, never write remotely."""
import csv
import datetime
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import socket
import subprocess

MODELS = ['blip2-opt-2.7b', 'instructblip-vicuna-7b', 'minigpt-4-vicuna-7b',
          'llava-v1.5-7b', 'qwen2.5-vl-3b', 'paligemma-3b', 'smolvlm-1.7b']
SHARED = '/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results'
SKIP = {'records', 'checkpoints', 'eval_full', 'images', 'data_image', 'data',
        'datasets', 'tokenizers', 'models', '__pycache__', 'cache', 'eval_cache',
        'train_cache', 'node_cache', 'wandb', 'provenance', 'site-packages'}


def now():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='seconds')


def capture(p):
    b = p.read_bytes()
    return dict(path=str(p), size=len(b), sha256=hashlib.sha256(b).hexdigest(),
                mtime=datetime.datetime.fromtimestamp(p.stat().st_mtime, datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='seconds'),
                text=b.decode('utf-8', 'replace'))


def inventory(roots):
    rows, errors, visited = [], [], 0
    for rootname in roots:
        root = Path(rootname)
        if not root.exists():
            continue
        for cur, dirs, files in os.walk(str(root), onerror=lambda e: errors.append(str(e))):
            visited += 1
            p = Path(cur)
            dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith('.') and len(p.relative_to(root).parts) < 13]
            match = re.fullmatch(r'layer[_-](\d+)', p.name)
            if not match:
                continue
            dirs[:] = []
            if not set(files) & {'train.done', 'eval_full.done', 'selected_checkpoint.tsv', 'loss_history.csv'}:
                continue
            row = dict(host=socket.gethostname(), path=str(p), layer=int(match[1]), files=sorted(files), artifacts={})
            try:
                for name in ['train.done', 'eval_full.done', 'selected_checkpoint.tsv', 'run_config.json',
                             'SYNC_VERIFIED', 'verification.json', 'ARCHIVE_MANIFEST.json']:
                    f = p/name
                    if f.is_file() and f.stat().st_size < 250000:
                        row['artifacts'][name] = capture(f)
                text = str(p) + '\n' + '\n'.join(x['text'] for x in row['artifacts'].values())
                s = text.lower().replace('_', '-')
                row['model'] = next((m for m in MODELS if m in s), None)
                row['dataset'] = next((d for d in ['mmke-visual', 'mmke-entity'] if d in s), None)
                if row['dataset'] is None and any(x in s for x in ['evqa', 'pilot500', 'vqa-eval']):
                    row['dataset'] = 'evqa-pilot500'
                row['recipe'] = 'stable' if 'stable' in str(p).lower() else 'main'
                if any(token in str(p).lower() for token in ['fullevqa', 'fulltrain']):
                    row['dataset'] = 'evqa-fulltrain-out-of-scope'
                if 'blip2_pilot500_visedit_sweep_L18_2_' in str(p) and row['layer'] == 18:
                    row['recipe'] = 'main-rerun'
                for anc in [p, p.parent, p.parent.parent, p.parent.parent.parent]:
                    f = anc/'run_config.json'
                    if f.is_file() and f.stat().st_size < 50000:
                        row['config'] = capture(f)
                        break
                f = p/'loss_history.csv'
                if f.is_file():
                    a = capture(f)
                    hist = list(csv.DictReader(a['text'].splitlines()))
                    finite = []
                    epochs = []
                    for h in hist:
                        try:
                            epochs.append(int(h['epoch']))
                            ema = float(h.get('ema_loss', 'nan'))
                            if math.isfinite(ema):
                                finite.append((ema, h))
                        except (ValueError, KeyError):
                            pass
                    row['history'] = dict(epochs=epochs, rows=len(hist), min_row=min(finite, key=lambda z:z[0])[1] if finite else None, tail=hist[-1:] )
                    row['artifacts']['loss_history.csv'] = a
                if 'eval_full.done' in row['artifacts']:
                    try:
                        row['evaluation'] = json.loads(row['artifacts']['eval_full.done']['text'])
                    except ValueError:
                        row['evaluation_parse_error'] = True
                if 'selected_checkpoint.tsv' in row['artifacts']:
                    selected = list(csv.DictReader(io.StringIO(row['artifacts']['selected_checkpoint.tsv']['text']), delimiter='\t'))
                    row['selected'] = selected
                rows.append(row)
            except Exception as exc:
                errors.append(str(p) + ': ' + repr(exc))
    return dict(started=START, finished=now(), host=socket.gethostname(), roots=roots, visited=visited, errors=errors, layers=rows)


START = now()
if __name__ == '__main__':
    roots = globals().get('AUDIT_ROOTS', [SHARED])
    result = inventory(roots)
    result['queue'] = subprocess.run(['squeue', '-u', 'ph_teacher3', '-h', '-o', '%i|%j|%T|%N|%M|%L'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True).stdout
    print(json.dumps(result, ensure_ascii=False))
