"""Fetch completed similarity score artifacts without changing remote state."""
from pathlib import Path
from collections import Counter
import json,sys,hashlib,statistics,csv
import numpy as np
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lga_ablation_remote import ssh
sys.stdout.reconfigure(encoding='utf-8')
code=r'''
from pathlib import Path
import json,datetime
root=Path('/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/visual_track_cosine_20260928/targets_v2/results')
groups=[]
for p in sorted(root.glob('*/*/summary.json')):
 s=json.loads(p.read_text())
 if s.get('status')!='done':continue
 d=p.parent
 groups.append({'remote_dir':str(d),'files':{name:(d/name).read_text() for name in ['summary.json','protocol.json','layer_scores.json','diagnostics.json']}})
print(json.dumps({'checked_at':datetime.datetime.now().astimezone().isoformat(),'groups':groups}))
'''
bundle=json.loads(ssh(code,timeout=60))
with (ROOT/'outputs/all_methods_performance_20260928/outcomes_used.csv').open(encoding='utf-8-sig',newline='') as f:
 pool={(r['dataset'],r['model'],int(r['layer'])):float(r['Average']) for r in csv.DictReader(f) if r['recipe']=='main'}
recs=[]; verified=[]
for g in bundle['groups']:
 files=g['files'];s=json.loads(files['summary.json'])
 for fn,key in [('protocol.json','protocol_sha256'),('layer_scores.json','scores_sha256'),('diagnostics.json','diagnostics_sha256')]:
  assert hashlib.sha256(files[fn].encode()).hexdigest()==s[key]
 d=OUT/'similarity_sources'/s['dataset']/s['model'];d.mkdir(parents=True,exist_ok=True)
 for fn,content in files.items():(d/fn).write_text(content,encoding='utf-8')
 score=json.loads(files['layer_scores.json']); rr=score['rows'] if isinstance(score,dict) else score
 for variant in ['none','alt','model_pred']:
  v=[r for r in rr if r['variant']==variant and r['cohort']=='matched_gradient']
  assert v and all(r['n']==s['matched_sample_count'] for r in v)
  values={r['layer']:r['visual_track_cos'] for r in v}
  assert len(values)==len(v)
  for flavor in ['raw','tukey']:
   q1,q3=np.quantile(list(values.values()),[.25,.75],method='linear');lo,hi=q1-(q3-q1),q3+(q3-q1)
   order=sorted((l for l in values if flavor=='raw' or lo<=values[l]<=hi),key=lambda l:(-values[l],l));top=order[:3]
   missing=[l for l in top if (s['dataset'],s['model'],l) not in pool]
   recs.append(dict(dataset=s['dataset'],model=s['model'],variant=variant,flavor=flavor,top3=top,all_ranking=order,n=v[0]['n'],missing_main=missing,mean3=statistics.mean(pool[s['dataset'],s['model'],l] for l in top) if len(top)==3 and not missing else None))
 verified.append(dict(dataset=s['dataset'],model=s['model'],matched_sample_count=s['matched_sample_count'],available_counts=s['available_counts'],source_hashes_verified=True))
result=dict(checked_at=bundle['checked_at'],completed_groups=len(verified),completed_target_variants=3*len(verified),verified=verified,recommendations=recs,peak_region_middle_implemented=False)
(OUT/'similarity_verified.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
doc=['','## 绿色表征相似度：本次读取服务器完成产物','',f"服务器采集时间：{bundle['checked_at']}；完成 {len(verified)}/21 组，三种目标共 {3*len(verified)}/63 个组×目标。summary、分数、协议和诊断文件哈希已互相核对。这里只重新派生已有分数的推荐，不启动计算。",'',
 '三版分别为不加答案 none、新答案 alt、缓存旧答案 model_pred；有答案版在每个答案 token 的预测位置计算相似度，先在样本内平均，再跨样本等权平均。matched_gradient 使用与视觉梯度相同的样本集合。首答案预测位置只有固定前缀，三版应一致；差异来自后续答案前缀。', '',
 '当前运行和分析代码只包含相似度降序 Raw/Tukey；没有实现截图中的“极大值区间中层”选层。后者仍需明确区间阈值、多峰处理、中心及邻层 Top-3 规则，不能把 Tukey 当作区间中层。','',
 '| 数据集 | 模型 | 已完成目标 | 匹配梯度样本数 |','| --- | --- | --- | --- |']
doc += [f"| {r['dataset']} | {r['model']} | none / alt / model_pred | {r['matched_sample_count']} |" for r in verified]
doc += ['','[全部已核验相似度 Top-3](similarity_verified.json)','']
with (OUT/'核验附表.md').open('a',encoding='utf-8') as f:f.write('\n'.join(doc))
print(json.dumps({k:v for k,v in result.items() if k!='recommendations'},ensure_ascii=False,indent=2))
