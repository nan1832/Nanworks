"""Run inside the existing allocation. Persist stdout on durable project storage."""
from pathlib import Path
import csv,hashlib,json,os,subprocess,sys
root=Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main')
out=root/'phase2_p0'
out.mkdir(exist_ok=True)
data=root.parent/'server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000/data/vqa_mmke_entity_eval_evqa_compat.json'
layer_dir=root.parent/'server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000/blip2-opt-2.7b/layer_00'
selected=list(csv.DictReader((layer_dir/'selected_checkpoint.tsv').open(),delimiter='\t'))[0]
assert int(selected['layer'])==0
checkpoint=Path(selected['checkpoint'])
assert checkpoint.is_file(),str(checkpoint)
metadata={'selected':selected,'checkpoint_exists':True,'checkpoint_bytes':checkpoint.stat().st_size,
          'loader_path':str(root/'editor/vllms_for_edit/blip2/blip2.py'),
          'loader_sha256':hashlib.sha256((root/'editor/vllms_for_edit/blip2/blip2.py').read_bytes()).hexdigest()}
for f in ['eval_full.done','run_config.json']:
 p=layer_dir/f if f=='eval_full.done' else layer_dir.parent/f
 if p.exists():metadata[f]=json.loads(p.read_text())
(out/'probe_L0_source_metadata.json').write_text(json.dumps(metadata,indent=2))
print(json.dumps(metadata),flush=True)
cmd=[sys.executable,'-u',str(out/'probe_single_sample.py'),'--project-root',str(root),
     '--data',str(data),'--image-root',str(root.parent/'datasets/MMKE-Bench/data_image'),
     '--layer','0','--checkpoint',str(checkpoint),'--device','cuda:0']
(out/'probe_command.json').write_text(json.dumps({'argv':cmd,'job_id':os.environ.get('SLURM_JOB_ID')},indent=2))
with (out/'probe_L0.log').open('wb') as log:
 process=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 for line in iter(process.stdout.readline,b''):
  log.write(line);log.flush();sys.stdout.buffer.write(line);sys.stdout.buffer.flush()
 raise SystemExit(process.wait())
