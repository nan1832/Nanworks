"""Read-only shared-storage audit. No training or server files are changed."""
from pathlib import Path
from collections import Counter
import os, json, csv, math, re, hashlib, datetime, socket, subprocess

ROOT=Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2')
SR=ROOT/'server_results'
print(json.dumps(dict(kind='snapshot',time=datetime.datetime.now().astimezone().isoformat(),host=socket.gethostname()),ensure_ascii=False),flush=True)
models=[]
for here,dirs,files in os.walk(str(SR)):
    p=Path(here); depth=len(p.relative_to(SR).parts)
    if p.name=='paligemma-3b':
        models.append(p); dirs[:]=[]; continue
    dirs[:]=[d for d in dirs if depth<6 and not d.startswith(('layer_','.')) and
             d not in {'records','data','data_image','cache','train_cache','eval_cache','checkpoints','models','datasets','data_cache','tensorboard','logs'}]
print(json.dumps(dict(kind='model_directories',paths=[str(p) for p in models]),ensure_ascii=False),flush=True)

def text(p): return p.read_text(encoding='utf-8',errors='replace')
def capture(p):
    b=p.read_bytes()
    return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),text=b.decode('utf-8','replace'))
def layer_audit(p):
    z=dict(kind='layer',path=str(p),files=[x.name for x in p.iterdir() if x.is_file()])
    for name in ['selected_checkpoint.tsv','train.done','eval_full.done','run_config.json']:
        f=p/name
        if f.is_file() and f.stat().st_size<30000: z[name]=capture(f)
    f=p/'loss_history.csv'
    if f.exists():
        rr=list(csv.DictReader(text(f).splitlines()))
        vals=[float(r['ema_loss']) for r in rr if r.get('ema_loss') and math.isfinite(float(r['ema_loss']))]
        z['loss_history']=dict(path=str(f),sha256=hashlib.sha256(f.read_bytes()).hexdigest(),rows=len(rr),
            max_epoch=max([int(r.get('epoch',0)) for r in rr],default=0),min_ema=min(vals) if vals else None,
            max_ema=max(vals) if vals else None,head=rr[:2],tail=rr[-2:],negative_count=sum(v<0 for v in vals))
        surviving=[]
        for r in rr:
            cp=Path(r.get('ckpt_path','/nonexistent'))
            if cp.is_file(): surviving.append(dict(epoch=r.get('epoch'),ema=r.get('ema_loss'),path=str(cp),bytes=cp.stat().st_size))
        z['surviving_checkpoints']=surviving
    cc=list(p.glob('records/vead/paligemma-3b/*/config.yaml'))
    z['configs']=[capture(f) for f in cc]
    print(json.dumps(z,ensure_ascii=False),flush=True)

for p in models:
    if 'visual' not in str(p).lower():
        # The later formal run stores dataset as a parent directory.
        continue
    print(json.dumps(dict(kind='model_root',path=str(p),files=[x.name for x in p.iterdir() if x.is_file()])),flush=True)
    for layer in sorted(p.glob('layer_*')):
        if layer.is_dir(): layer_audit(layer)
    archived=[x for x in p.iterdir() if x.is_dir() and not x.name.startswith('layer_')]
    print(json.dumps(dict(kind='archived_directories',parent=str(p),paths=[str(x) for x in archived])),flush=True)
    for f in p.glob('*.log'):
        if 'train' not in f.name.lower() and 'status' not in f.name.lower(): continue
        # Scan linewise; retain only relevant diagnostics and a bounded tail.
        counts=Counter(); samples=[]; tail=[]
        with f.open(encoding='utf-8',errors='replace') as fh:
            for raw in fh:
                line=raw.replace('\r','\n')
                for token in ['SANITIZE_NONFINITE_GRAD_BEFORE_STEP','PALIGEMMA_STABLE_SKIP_NONFINITE_STEP',
                              'PALIGEMMA_STABLE_SKIP_NONFINITE_LOSS','CUDA out of memory','PytorchStreamWriter',
                              'No space left','Traceback','TRAIN_END','TRAIN_FAILED','TRAIN_STALLED','EVAL_END']:
                    if token in line: counts[token]+=line.count(token)
                if any(t in line for t in ['Traceback','Error','grad_bad=','TRAIN_FAILED','TRAIN_STALLED']):
                    if len(samples)<6: samples.append(line[-1600:])
                tail.append(line[-1800:]); tail=tail[-5:]
        print(json.dumps(dict(kind='training_log',path=str(f),bytes=f.stat().st_size,
            modified=datetime.datetime.fromtimestamp(f.stat().st_mtime).isoformat(),counts=dict(counts),samples=samples,tail=tail),ensure_ascii=False),flush=True)

DIAG=SR/'paligemma_l0_nonconvergent_eval_20260921'
for f in sorted(DIAG.glob('mmke-visual*/*')):
    if f.name in ['selection_audit.json','original_config.yaml'] and f.is_file():
        print(json.dumps(dict(kind='diagnostic',**capture(f))),flush=True)
for f in sorted(DIAG.glob('mmke-visual*/layer_00/eval_full.done')):
    print(json.dumps(dict(kind='diagnostic_eval',**capture(f))),flush=True)
print(json.dumps(dict(kind='audit_end',time=datetime.datetime.now().astimezone().isoformat())),flush=True)
