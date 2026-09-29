import json, hashlib
from pathlib import Path
from collections import Counter, defaultdict

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
P4=ROOT/'phase2_p4'
G=P4/'eval_request_graphs_repaired_20260926'
S=P4/'eval_request_graphs_20260925'
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
freeze=read(G/'INPUTS_FROZEN.json')
checks={}
for path,h in freeze['input_hashes'].items():
    p=ROOT/path
    if p.is_file() and not str(p).endswith('.pt'):checks[path]=digest(p)==h
assert all(checks.values()), [k for k,v in checks.items() if not v]
cov=rows(G/'sample_coverage.jsonl')
requests=rows(S/'requests_whitelist.jsonl')
facts=rows(S/'consensus/full_fact_chains_consensus.jsonl')
diffs=rows(S/'fact_diff_samples.jsonl')
excluded=rows(G/'unmapped_relations_excluded.jsonl')
data=read(OUT/'evidence/entity_eval.json')
assert len(data)==len(cov)==955
graphs={p.stem:rows(p) for p in (G/'runtime').glob('G*.jsonl')}
vocab=read(ROOT/'phase2_p2/dynamic_graphs_20260921/relation_vocabulary.json')['custom_counterfactual_relations']
rev={v:k for k,v in vocab.items()}
by=defaultdict(list);ex=defaultdict(list)
for f in facts:by[f['sample_id']].append(f)
for f in excluded:ex[f['sample_id']].append(f)
def edge_set(g):return {(g['node_ids'][s],r,g['node_ids'][d]) for s,r,d in zip(g['edge_src'],g['edge_relation_ids'],g['edge_dst'])}
same=sum(edge_set(a)==edge_set(b) for a,b in zip(graphs['G3_Overlay1hop'],graphs['G3_EditOnly0hop']))
results={}
for p in (OUT/'evidence').glob('G*/results.partial.jsonl'):
    a=rows(p);assert len(a)==955
    results[p.parent.name]={x['source_record_index']:x for x in a}
ids=[0,next(x['index'] for x in cov if x['real_neighbor_count']),next(x['index'] for x in cov if x['edit_root_count']==0)]
examples=[]
for i in ids:
    sid=cov[i]['sample_id']
    assert all(requests[i][k]==data[i][k] for k in requests[i])
    gs={}
    for name,rs in graphs.items():
        a=rs[i];assert a['sample_id']==sid
        edges=[]
        for s,r,d,status in zip(a['edge_src'],a['edge_relation_ids'],a['edge_dst'],a['edge_truth_status']):
            if r=='SELF_LOOP':continue
            edges.append({'subject':a['node_labels'][d],'relation':rev.get(r,r),'object':a['node_labels'][s],
                          'source_id':a['node_ids'][d],'target_id':a['node_ids'][s], 'status':status,'relation_id':r,
                          'message_src':s,'message_dst':d})
        gs[name]={'nodes':[dict(id=n,label=l,kind=k) for n,l,k in zip(a['node_ids'],a['node_labels'],a['node_kinds'])],
                  'edges':edges,'self_loops':a['self_loop_count'],'raw':a}
    e={'index':i,'coverage':cov[i],'record':data[i],'diff':diffs[i],'facts':by[sid],
       'excluded':ex[sid],'graphs':gs,'results':{k:v[i] for k,v in results.items()}}
    examples.append(e)
summary={'total':955,'facts':len(facts),'excluded_facts':len(excluded),'excluded_pct':100*len(excluded)/len(facts),
         'root_edges':sum(c['edit_root_count'] for c in cov),'real_neighbor_samples':sum(bool(c['real_neighbor_count']) for c in cov),
         'empty_samples':sum(not c['edit_root_count'] for c in cov),'overlay_equals_zero_hop':same,
         'excluded_relations_top20':Counter(f['relation'] for f in excluded).most_common(20),
         'hash_checks':checks,'selection':'Dataset order: first record, first with real neighbors, first without edit roots; independent of scores.',
         'selected_indices':ids}
(OUT/'audit_evidence.json').write_text(json.dumps({'summary':summary,'examples':examples},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k!='hash_checks'},ensure_ascii=False))
for e in examples:
 print('\nEXAMPLE',e['index'],e['coverage'])
 print('RECORD',json.dumps(e['record'],ensure_ascii=False))
 print('FACTS',[(f['relation_canonical'],f['old_object_text'],f['new_object_text']) for f in e['facts']])
 print('EXCLUDED',e['excluded'])
 print('GRAPH',e['graphs']['G3_Overlay1hop']['edges'])
 print('RESULTS',{k:{'main':v['main'],'port':[x for x in v['additional'] if 'portability' in x['group']]} for k,v in e['results'].items() if k in ['G3_Overlay1hop','G3_EditOnly0hop']})
