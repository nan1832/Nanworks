// Offline packaging only. Source experiment files are never modified.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
const OUT=path.dirname(fileURLToPath(import.meta.url));
const ROOT=path.resolve(OUT,'../../..');
const EP='phase2_p4/eval_request_graphs_repaired_20260926';
const ES='phase2_p4/eval_request_graphs_20260925';
const TP='phase2_p4/runtime_graph_cache_20260921';
const audit=path.join(ROOT,'dataset/outputs/mmke_graph_quality_audit_20260926');
const hashes={};
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
function read(p,lines=false,expected){const f=path.isAbsolute(p)?p:path.join(ROOT,p); const h=sha(f); if(expected)assert.equal(h,expected,`SHA256 mismatch: ${p}`); hashes[path.relative(ROOT,f).replaceAll('\\','/')]={sha256:h,expected:expected||null,verified:expected?h===expected:null}; const text=fs.readFileSync(f,'utf8').replace(/^\uFEFF/,'');return lines?text.split(/\r?\n/).filter(x=>x.trim()).map(JSON.parse):JSON.parse(text);}
const frozen=read(EP+'/INPUTS_FROZEN.json');
const cfg=read('phase2_p3/frozen_graph_config.json');
const summary=read(TP+'/runtime_graph_cache_summary.json');
const fr=(p,l=false)=>read(p,l,frozen.input_hashes[p]);
const vocab=fr('phase2_p2/dynamic_graphs_20260921/relation_vocabulary.json');
const relations=Object.fromEntries(Object.entries(vocab.custom_counterfactual_relations).map(([k,v])=>[v,k]));
const neighbors=fr('phase2_p2/real_1hop_snapshot_20260921/new_object_real_neighborhoods.jsonl',true);
const tripleByKey={};
for(const r of neighbors)for(const t of r.triples){relations[t.property_id]=t.relation;tripleByKey[[t.subject_qid,t.property_id,t.target_qid].join('|')]=t;}
const evalRows=read(path.join(audit,'evidence/entity_eval.json'),false,cfg.data.official_eval_sha256);
const trainRows=read(path.join(OUT,'entity_train.json'),false,cfg.data.official_train_sha256);
const evalFacts=fr(ES+'/consensus/full_fact_chains_consensus.jsonl',true);
const trainFacts=read('phase2_p2/fact_chain_conservative_frozen_20260920/high_confidence_fact_chains_frozen.jsonl',true);
const groupBy=(rows,key)=>{const m=new Map();for(const r of rows){const k=r[key];if(!m.has(k))m.set(k,[]);m.get(k).push(r);}return m;};
const coverage=fr(EP+'/sample_coverage.jsonl',true);
const excluded=groupBy(read(EP+'/unmapped_relations_excluded.jsonl',true),'sample_id');
const diffs={eval:new Map(fr(ES+'/fact_diff_samples.jsonl',true).map(x=>[x.sample_id,x])),train:new Map(read('phase2_p2/fact_diff_candidates_20260919/fact_diff_samples.jsonl',true).map(x=>[x.sample_id,x]))};
const facts={eval:groupBy(evalFacts,'sample_id'),train:groupBy(trainFacts,'sample_id')};
const requests=fr(ES+'/requests_whitelist.jsonl',true);
const groupKeys=['G3_Overlay1hop','G3_EditOnly0hop','G3_RealOnly','G4_RandomMatched'];
const caches={eval:{},train:{}},sourceGraphs={};
for(const name of groupKeys){
 caches.eval[name]=fr(EP+'/runtime/'+name+'.jsonl',true);
 caches.train[name]=read(TP+'/'+name+'.jsonl',true,summary.groups[name].output_sha256);
 sourceGraphs[name]=new Map(read(cfg.graph_inputs.groups[name].path,true,cfg.graph_inputs.groups[name].sha256).map(x=>[x.sample_id,x]));
}
const groups=Object.fromEntries(groupKeys.map(k=>[k,{eval:new Map(caches.eval[k].map(x=>[x.sample_id,x])),train:new Map(caches.train[k].map(x=>[x.sample_id,x]))}]));
const dataset={};
for(const [split,rows,count] of [['eval',evalRows,955],['train',trainRows,636]]){
 assert.equal(rows.length,count);assert.equal(caches[split].G3_Overlay1hop.length,count);
 const seen=new Set();dataset[split]=[];
 for(const base of caches[split].G3_Overlay1hop){
  const i=base.official_mmke_index; assert(!seen.has(i));seen.add(i);
  assert(i>=0&&i<rows.length);const record=rows[i],sid=base.sample_id,diff=diffs[split].get(sid);assert(diff,`Missing diff ${sid}`);
  for(const field of ['src','pred','alt','image','image_rephrase','type_self']){
   if(split==='eval')assert.deepEqual(requests[i][field],record[field]);
   if(['pred','alt'].includes(field))assert.equal(diff[field].trim(),record[field].trim(),`Bad original match ${split}/${i}/${field}`);
  }
  const gs={};
  for(const key of groupKeys){
   const raw=groups[key][split].get(sid);assert(raw);assert.equal(raw.official_mmke_index,i);
   const n=raw.node_ids.length;assert.equal(new Set(raw.node_ids).size,n);assert.equal(raw.node_labels.length,n);
   for(const attr of ['edge_src','edge_dst','edge_type','edge_relation_ids','edge_truth_status','edge_ids'])assert.equal(raw[attr].length,raw.edge_src.length);
   assert.equal(raw.edge_src.length,raw.semantic_edge_count+raw.self_loop_count);
   assert.equal(raw.evaluation_fields_consumed.length,0);
   const src=split==='train'?sourceGraphs[key].get(sid):null;
   const byEdge=new Map((src?.active_edges||[]).map(e=>[e.edge_id,e]));
   const edgeEvidence={};
   raw.edge_src.forEach((s,j)=>{
    const d=raw.edge_dst[j],rel=raw.edge_relation_ids[j];assert(s>=0&&s<n&&d>=0&&d<n);
    if(rel==='SELF_LOOP'){assert.equal(s,d);return;}
    let evidence=byEdge.get(raw.edge_ids[j]);
    if(evidence)assert.equal(evidence.source_node_id,raw.node_ids[d]);
    if(!evidence&&split==='eval'&&raw.edge_truth_status[j]==='real_neighbor_of_counterfactual_object'){
     const triple=tripleByKey[[raw.node_ids[d].replace(/^wd:/,''),rel,raw.node_ids[s].replace(/^wd:/,'')].join('|')];
     if(triple)evidence={source:'frozen_new_object_real_neighborhoods',triple};
    }
    if(evidence)edgeEvidence[j]=evidence;
   });
   gs[key]={raw,edgeEvidence};
  }
  const fsample=facts[split].get(sid)||[];let c;
  if(split==='eval'){c=coverage.find(x=>x.index===i);assert.equal(c.sample_id,sid);}
  else c={index:i,sample_id:sid,subject:base.node_labels[base.subject_node_index],edit_root_count:base.edge_truth_status.filter(x=>x==='counterfactual_active').length,real_neighbor_count:base.edge_truth_status.filter(x=>x==='real_neighbor_of_counterfactual_object').length};
  const sample={index:i,key:split+':'+i,sample_id:sid,subject:c.subject,record,coverage:c,facts:fsample,excluded:split==='eval'?(excluded.get(sid)||[]):[],diff,graphs:gs};
  if(split==='train')sample.construction=sourceGraphs.G3_Overlay1hop.get(sid);
  if(split==='eval'&&[10,14].includes(i))sample.imageData='data:image/jpeg;base64,'+fs.readFileSync(path.join(audit,`evidence/sample${i}.jpg`)).toString('base64');
  dataset[split].push(sample);
 }
 dataset[split].sort((a,b)=>a.index-b.index);
 assert.equal(seen.size,count);
}
function stats(rows){return {samples:rows.length,facts:rows.reduce((s,x)=>s+x.facts.length,0),excluded:rows.reduce((s,x)=>s+x.excluded.length,0),withNeighbors:rows.filter(x=>x.coverage.real_neighbor_count>0).length,withoutEditRoots:rows.filter(x=>!x.coverage.edit_root_count).length,nodes:rows.reduce((s,x)=>s+x.graphs.G3_Overlay1hop.raw.node_ids.length,0),edges:rows.reduce((s,x)=>s+x.graphs.G3_Overlay1hop.raw.semantic_edge_count,0)};}
const stat={eval:stats(dataset.eval),train:stats(dataset.train)};
assert.equal(stat.eval.facts,4329);assert.equal(stat.eval.excluded,1541);assert.equal(stat.eval.withNeighbors,21);assert.equal(stat.eval.withoutEditRoots,28);assert.equal(stat.train.edges,8379);
const manifest={version:'mmke-graph-review-20260927-v1',builtAt:new Date().toISOString(),evalProtocol:frozen.protocol_name,trainProtocol:'runtime_graph_cache_20260921',stats:stat,hashes,scope:'Offline inspection only; no source graph or evaluation change; test answers displayed for audit only.'};
const packed={manifest,relations,datasets:dataset};
fs.writeFileSync(path.join(OUT,'review-data.js'),'window.REVIEW_DATA='+JSON.stringify(packed).replace(/</g,'\\u003c').replace(/\u2028/g,'\\u2028').replace(/\u2029/g,'\\u2029')+';\n');
fs.writeFileSync(path.join(OUT,'data-verification.json'),JSON.stringify(manifest,null,2)+'\n');
console.log(JSON.stringify({status:'PASS',stats:stat,filesChecked:Object.keys(hashes).length,bytes:fs.statSync(path.join(OUT,'review-data.js')).size},null,2));
