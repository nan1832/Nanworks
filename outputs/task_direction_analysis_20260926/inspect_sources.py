from pathlib import Path
import json
R=Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results')
roots=[R/'ours_direct_7models_3datasets_g08_gpu0_20260626_131624',R/'ours_direct_qwen_chatfix_repair_g09_gpu1_20260630_091304']
for root in roots:
    print(json.dumps(dict(root=str(root),exists=root.exists())))
    for p in sorted(root.glob('*/*/ours_direct_sample_layer_scores.jsonl')):
        with p.open() as f:
            line=next(f,'');first=json.loads(line) if line else None
        print(json.dumps(dict(path=str(p),bytes=p.stat().st_size,first=first),ensure_ascii=False))
    for p in sorted(root.glob('*/*/run_config.json'))[:1]: print(json.dumps(dict(config=str(p),text=p.read_text())))
    for p in sorted(root.glob('*/*/ours_direct_summary.json'))[:1]: print(json.dumps(dict(summary=str(p),text=p.read_text())))
    for p in sorted(root.glob('*/*/model_pred_cache.jsonl'))[:1]:
        with p.open() as f: first=json.loads(next(f))
        print(json.dumps(dict(pred_path=str(p),bytes=p.stat().st_size,first=first),ensure_ascii=False))
