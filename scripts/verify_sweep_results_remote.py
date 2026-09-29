"""Read-only verification of supplied layer paths. No weights are loaded or copied."""
from pathlib import Path
import csv
import datetime
import hashlib
import io
import json
import math
import socket

FIELDS = ['Rel', 'T-Gen', 'M-Gen', 'T-Loc', 'M-Loc', 'Average']
EXPECTED = {'evqa-pilot500': 2093, 'mmke-visual': 293, 'mmke-entity': 954}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def verify(item):
    p = Path(item['path'])
    out = dict(path=str(p), host=socket.gethostname(), errors=[], warnings=[], artifacts={})
    try:
        def read(f):
            b = f.read_bytes()
            out['artifacts'][str(f)] = dict(size=len(b), sha256=sha(b))
            return b
        e = json.loads(read(p/'eval_full.done'))
        selected = list(csv.DictReader(io.StringIO(read(p/'selected_checkpoint.tsv').decode()), delimiter='\t'))
        if len(selected) != 1:
            raise ValueError('selected checkpoint row count is not one')
        s = selected[0]
        out['evaluation'] = e
        out['selected'] = s
        expected = EXPECTED[item['dataset']]
        if int(e.get('eval_samples', 0)) != expected:
            out['errors'].append('evaluation_sample_count')
        for f in FIELDS:
            if not math.isfinite(float(e[f])) or not 0 <= float(e[f]) <= 100:
                out['errors'].append('invalid_metric:' + f)
        if abs(sum(float(e[f]) for f in FIELDS[:5])/5 - float(e['Average'])) > .011:
            out['errors'].append('average_mismatch')
        for a, b in [('epoch','ckpt_epoch'), ('i','ckpt_i'), ('ema_loss','ckpt_ema_loss')]:
            if a in s and b in e and abs(float(s[a])-float(e[b])) > 1e-5:
                out['errors'].append('selected_eval_mismatch:' + a)
        cp = Path(s.get('checkpoint', s.get('ckpt_path', '')))
        if cp.name != Path(e.get('checkpoint', '')).name:
            out['errors'].append('checkpoint_name_mismatch')
        # Archives often retain old absolute paths: prefer the checkpoint in this layer.
        local = list(p.glob('records/**/checkpoints/' + cp.name)) if cp.name else []
        if local:
            cp = local[0]
        out['checkpoint'] = dict(path=str(cp), exists=cp.is_file(), size=cp.stat().st_size if cp.is_file() else 0)
        if not out['checkpoint']['size']:
            out['warnings'].append('checkpoint_binary_not_at_recorded_path')
        result_path = p/'eval_full'/Path(e.get('result_dir','')).name/'results.json'
        result_paths = list(p.glob('eval_full/**/results.json'))
        if not result_paths:
            candidate = Path(e.get('result_dir', ''))/'results.json'
            if candidate.is_file():
                result_paths = [candidate]
        if len(result_paths) != 1:
            out['errors'].append('result_file_count:' + str(len(result_paths)))
        else:
            result_path = result_paths[0]
            results = json.loads(read(result_path))
            out['results_path'] = str(result_path)
            out['results_count'] = len(results) if isinstance(results, list) else -1
            if out['results_count'] != expected:
                out['errors'].append('results_length')
            elif isinstance(results, list):
                sums = [0.0]*5
                try:
                    for r in results:
                        metrics = [float(r['reliability']['acc'])]
                        for group, sub in [('generality','text_rephrase'),('generality','image_rephrase'),('locality','text_loc'),('locality','image_loc')]:
                            vals = r[group][sub]
                            if not isinstance(vals,list): vals = [vals]
                            metrics.append(sum(float(v['acc']) for v in vals)/len(vals))
                        if not all(math.isfinite(v) for v in metrics):
                            raise ValueError('nonfinite sample metric')
                        sums = [a+b for a,b in zip(sums, metrics)]
                    derived = [round(v/len(results)*100, 2) for v in sums]
                    out['recomputed_metrics'] = dict(zip(FIELDS[:5],derived))
                    if any(abs(float(e[f])-v) > .021 for f,v in zip(FIELDS,derived)):
                        out['errors'].append('per_sample_metric_mismatch')
                except (KeyError, ValueError, TypeError, ZeroDivisionError) as exc:
                    out['warnings'].append('sample_schema:' + str(exc))
            m = result_path.parent/'mean_results.json'
            if m.is_file():
                b=read(m)
                out['mean_results'] = json.loads(b)
                out['mean_results_text'] = b.decode('utf-8')
        train = p/'train.done'
        out['train_done'] = train.is_file() and train.stat().st_size > 0
        if out['train_done']: read(train)
        hist = p/'loss_history.csv'
        if hist.is_file():
            rows = list(csv.DictReader(io.StringIO(read(hist).decode())))
            epochs = [int(r['epoch']) for r in rows]
            out['history_rows'] = len(rows)
            out['max_epoch'] = max(epochs, default=0)
            out['all_50_epochs_present'] = set(range(1,51)).issubset(epochs)
            finite = [r for r in rows if math.isfinite(float(r.get('ema_loss','nan')))]
            if finite:
                best = min(finite, key=lambda r: float(r['ema_loss']))
                out['minimum_ema_row'] = best
                out['minimum_ema_matches'] = abs(float(best['ema_loss'])-float(s['ema_loss'])) < 1e-5
                if not out['minimum_ema_matches']:
                    out['warnings'].append('selected_not_minimum_of_available_history')
        for name in ['run_config.json','train_run_config.json','eval_run_config.json']:
            f=p/name
            if f.is_file() and f.stat().st_size<50000:
                b=read(f)
                out[name]=b.decode('utf-8')
        configs=list(p.glob('records/**/config.yaml'))
        if len(configs)==1:
            out['model_config_text']=read(configs[0]).decode('utf-8')
        out['evaluation_verified'] = not out['errors']
    except Exception as exc:
        out['errors'].append(repr(exc))
        out['evaluation_verified'] = False
    return out


if __name__ == '__main__':
    for item in VERIFY_ITEMS:
        print(json.dumps(verify(item), ensure_ascii=False), flush=True)
