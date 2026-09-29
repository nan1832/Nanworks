/* Read-only local review: no network requests and no writes to experiment files. */
(()=>{'use strict';
const $=id=>document.getElementById(id),D=window.REVIEW_DATA;
if(!D){$('load-error').hidden=false;return;}
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pretty=x=>JSON.stringify(x,null,2);
const key='mmke-review:'+D.manifest.version;
let reviews={},storageOK=true;
try{reviews=JSON.parse(localStorage.getItem(key)||'{}');if(!reviews||Array.isArray(reviews))reviews={};}catch{storageOK=false;reviews={};}
let split='eval',index=10,tab='json',group='G3_Overlay1hop',filtered=[],graphState=null,images=new Map(),imageURL=null;
const names={G3_Overlay1hop:'G3 一跳叠加图',G3_EditOnly0hop:'G3 仅编辑零跳图',G3_RealOnly:'G3 pred 旧知识图',G4_RandomMatched:'G4 匹配随机对照'};
const colors={subject:'#3975c4',edit:'#cb8e2c',neighbor:'#348e89',old:'#9576b6',excluded:'#ca5874',random:'#8290a5',loop:'#9aa7b5'};
const fills={subject:'#3975c4',edit:'#ffedc6',neighbor:'#d9f0eb',old:'#eee4f7',excluded:'#fbe5ec',random:'#e8ecf2',loop:'#edf0f4'};
const row=()=>D.datasets[split][index];
const currentGraph=()=>row().graphs[group].raw;
const category=status=>status.includes('real_neighbor')?'neighbor':status.includes('reference')?'old':status.includes('random')?'random':status==='self_loop'?'loop':'edit';
const statusName=s=>({counterfactual_active:'alt 编辑事实',real_neighbor_of_counterfactual_object:'冻结真实邻域',dataset_pred_reference_active:'pred 旧事实',random_matched_control:'随机对照，不作真实关系',self_loop:'自环'}[s]||s);
const verdictName=s=>({pending:'未审核',pass:'通过',issue:'有问题',uncertain:'存疑'}[s]||'未审核');
const reviewKey=()=>`${split}:${row().sample_id}`;
function toast(t){$('toast').textContent=t;$('toast').hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('toast').hidden=true,4500);}
function download(name,value,type='application/json'){const u=URL.createObjectURL(new Blob([typeof value==='string'?value:pretty(value)],{type}));const a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),3000);}
function jsonHTML(o){return esc(pretty(o)).replace(/(&quot;(?:[^&]|&(?!quot;))*?&quot;)(\s*:)?|\b(-?\d+(?:\.\d+)?|true|false|null)\b/g,(m,s,c,n)=>s?`<span class="${c?'json-key':'json-string'}">${s}</span>${c||''}`:`<span class="json-num">${n}</span>`);}
function updateList(){
 const q=$('search').value.trim().toLowerCase(),f=$('filter').value;
 filtered=D.datasets[split].filter(e=>{
  const r=reviews[`${split}:${e.sample_id}`];
  const match=!q||(q.match(/^#?\d+$/)?e.index===Number(q.replace('#','')):(`${e.subject} ${e.sample_id} ${e.record.pred} ${e.record.alt}`).toLowerCase().includes(q));
  return match&&(f==='all'||f==='neighbors'&&e.coverage.real_neighbor_count>0||f==='empty'&&!e.coverage.edit_root_count||f==='excluded'&&e.excluded.length>0||f==='pending'&&(!r||r.verdict==='pending')||f==='issue'&&r?.verdict==='issue');
 });
 $('list-summary').textContent=`匹配 ${filtered.length} / ${D.datasets[split].length} 条 · 索引从 0 开始`;
 const frag=document.createDocumentFragment();
 for(const e of filtered){const b=document.createElement('button');b.className='sample'+(e.index===index?' active':'');b.dataset.index=e.index;b.setAttribute('aria-current',e.index===index?'true':'false');b.innerHTML=`<strong>#${e.index}　${esc(e.subject)}</strong><span>${e.coverage.edit_root_count} 根边 · ${e.coverage.real_neighbor_count} 邻域边 · ${verdictName(reviews[`${split}:${e.sample_id}`]?.verdict)}</span>`;b.onclick=()=>selectSample(e.index);frag.append(b);}
 if(!filtered.length){const p=document.createElement('p');p.className='empty';p.textContent='没有匹配记录。可清空搜索或切换筛选。';frag.append(p);}
 $('samples').replaceChildren(frag);
 $('review-progress').textContent=`已审核 ${D.datasets[split].filter(e=>reviews[`${split}:${e.sample_id}`]&&reviews[`${split}:${e.sample_id}`].verdict!=='pending').length} / ${D.datasets[split].length}`;
 const p=filtered.findIndex(e=>e.index===index);$('previous').disabled=p<=0;$('next').disabled=p<0||p===filtered.length-1;
}
function selectSample(i){index=i;render();try{history.replaceState(null,'',`#${split}/${index}`);}catch{}}
function renderSource(){
 const e=row(),r=e.record,el=$('source-content');
 if(imageURL){URL.revokeObjectURL(imageURL);imageURL=null;}
 document.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.tab===tab)));
 if(tab==='json'){el.innerHTML='<pre>'+jsonHTML(r)+'</pre>';return;}
 if(tab==='compare'){el.innerHTML=`<div class="text-label">src · 编辑请求</div><div class="text-block">${esc(r.src)}</div><div class="text-label">pred · 原始描述（不是本次重新生成）</div><div class="text-block">${esc(r.pred)}</div><div class="text-label">alt · 编辑目标（反事实）</div><div class="text-block alt">${esc(r.alt)}</div>`;return;}
 if(tab==='diff'){
  el.innerHTML=(e.diff.sentence_diffs||[]).map((x,i)=>`<div class="diff-item"><div class="text-label">${i+1}. ${esc(x.operation)}</div><div class="text-block">${esc(x.old_sentence||'（无旧句）')}</div><div class="text-block alt">${esc(x.new_sentence||'（无新句）')}</div><details><summary>断句 / 对齐证据</summary><pre>${esc(pretty(x))}</pre></details></div>`).join('')||'<p class="empty">此记录没有逐句差异产物。</p>';return;
 }
 const file=images.get(r.image);const src=file?(imageURL=URL.createObjectURL(file)):e.imageData;
 el.innerHTML=`<div class="text-label">image · 官方记录指定图片</div><p class="image-path">${esc(r.image)}</p>${src?`<img alt="原始记录 image 字段对应图片" src="${src}">`:'<p class="empty">本地审核包未包含此图。可以选择 MMKE data_image 文件夹，按原始相对路径加载。</p>'}<button id="choose-images">选择本地图像文件夹</button><p class="small" style="margin-top:12px">图片只在当前浏览器读取，不会上传。文件名与目标实体可能不同；这里严格按原始 image 字段配对，不按实体名替换。</p>`;
 $('choose-images').onclick=()=>$('image-folder').click();
}
function showDetail(title,content){$('detail-title').textContent=title;$('detail-content').innerHTML=content;}
function showFact(i){const f=row().facts[i];showDetail('抽取事实 · '+f.relation_canonical,`<p><strong>${esc(f.subject_text)} → ${esc(f.new_object_text)}</strong></p><p>关系：${esc(f.relation_canonical)}</p><p>旧值：${esc(f.old_object_text)}</p><p>原始证据与来源标记：</p><pre>${esc(pretty(f))}</pre>`);}
function edgesFromRaw(raw){return raw.edge_src.map((s,i)=>({i,id:raw.edge_ids[i],source:raw.edge_dst[i],target:s,relation:D.relations[raw.edge_relation_ids[i]]||raw.edge_relation_ids[i],relationId:raw.edge_relation_ids[i],status:raw.edge_truth_status[i],cat:category(raw.edge_truth_status[i])}));}
function showEdge(edge){
 if(edge.excluded){const f=row().facts[edge.factIndex];showDetail('未入图事实 · 不参与当前模型计算',`<p><strong>${esc(f.subject_text)} → ${esc(f.new_object_text)}</strong></p><p>关系：${esc(f.relation_canonical)}；原因：${esc(edge.reason)}</p><pre>${esc(pretty(f))}</pre>`);return;}
 const e=row(),r=currentGraph(),ev=e.graphs[group].edgeEvidence[edge.i];
 const candidates=e.facts.filter(f=>f.relation_canonical===edge.relation&&(f.new_object_text===r.node_labels[edge.target]||f.old_object_text===r.node_labels[edge.target]));
 showDetail(`边 #${edge.i} · ${statusName(edge.status)}`,`<p><strong>${esc(r.node_labels[edge.source])} → ${esc(r.node_labels[edge.target])}</strong></p><p>关系：${esc(edge.relation)} <code>${esc(edge.relationId)}</code></p><p>事实方向：节点 ${edge.source} → ${edge.target}；RGCN 消息：节点 ${r.edge_src[edge.i]} → ${r.edge_dst[edge.i]}</p><p class="small">边 ID：${esc(edge.id)}</p>${edge.cat==='random'?'<p class="pill bad">随机重连，仅作控制实验，不代表真实关系。</p>':''}<pre>${esc(pretty({runtime_edge:{id:edge.id,relation:edge.relationId,truth_status:edge.status,edge_src:r.edge_src[edge.i],edge_dst:r.edge_dst[edge.i]},source_evidence:ev||null,...(!ev?{candidate_fact_matches:candidates,match_note:'按关系与原始对象文本匹配的候选证据；无精确 edge→fact ID 映射时不冒充确定来源。'}:{})}))}</pre>`);
}
function showNode(n){
 const raw=currentGraph();document.querySelectorAll('.node').forEach(el=>el.classList.toggle('selected',el.dataset.id===String(n.idx)));
 const linked=graphState.edges.filter(e=>e.source===n.idx||e.target===n.idx);
 showDetail(n.excluded?'未入图事实的显示节点':'节点 · '+n.label,`<p><strong>${esc(n.label)}</strong></p><p>${n.excluded?'仅为审核显示，不是运行时节点。':`节点类型：${esc(raw.node_kinds[n.idx])}`}</p><p class="mono small">${esc(n.id)}</p><p>${linked.length} 条当前可见连接</p>${linked.map(e=>`<p>• ${esc(graphState.nodes[e.source].label)} — ${esc(e.relation)} → ${esc(graphState.nodes[e.target].label)}</p>`).join('')}`);
}
function renderFacts(){
 const e=row(),ex=new Map(e.excluded.map(x=>[x.fact_root_id,x])),raw=e.graphs.G3_Overlay1hop.raw,edges=edgesFromRaw(raw);
 $('fact-summary').textContent=`${e.facts.length} 条冻结事实 · ${split==='eval'?e.excluded.length+' 条明确排除':'仅展示已冻结的高置信子集'}`;
 $('fact-rows').innerHTML=e.facts.map((f,i)=>{
  const excludedFact=ex.get(f.fact_root_id);
  const direct=edges.some(x=>e.graphs.G3_Overlay1hop.edgeEvidence[x.i]?.evidence?.fact_root_id===f.fact_root_id);
  const match=edges.some(x=>x.relation===f.relation_canonical&&raw.node_labels[x.target]===f.new_object_text&&x.status==='counterfactual_active');
  const status=excludedFact?'未入图：未知冻结关系':direct?'已入图 · fact ID 核对':match?'已入图 · 关系/文本核对':'未匹配，请核查';
  return `<tr data-fact="${i}" tabindex="0"><td>${esc(f.relation_canonical)}</td><td>${esc(f.old_object_text||'—')}</td><td>${esc(f.new_object_text)}</td><td><span class="pill ${excludedFact?'bad':direct||match?'good':''}">${status}</span></td><td>${esc(f.provenance||f.evidence_status||'见原始证据')} ↗</td></tr>`;
 }).join('');
 $('fact-rows').querySelectorAll('tr').forEach(tr=>{tr.onclick=()=>showFact(Number(tr.dataset.fact));tr.onkeydown=ev=>{if(ev.key==='Enter')tr.click();};});
}
function renderEdges(){const raw=currentGraph(),edges=edgesFromRaw(raw);$('edge-total').textContent=`${edges.length} 条`;$('edge-rows').innerHTML=edges.map(e=>`<tr data-edge="${e.i}" tabindex="0"><td>#${e.i}</td><td>${esc(raw.node_labels[e.source])}</td><td>${esc(e.relation)}</td><td>${esc(raw.node_labels[e.target])}</td><td>${esc(statusName(e.status))}</td></tr>`).join('');$('edge-rows').querySelectorAll('tr').forEach(tr=>{tr.onclick=()=>showEdge(edges[Number(tr.dataset.edge)]);tr.onkeydown=ev=>{if(ev.key==='Enter')tr.click();};});}
const NS='http://www.w3.org/2000/svg';
function sv(tag,attrs,parent){const n=document.createElementNS(NS,tag);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);parent?.append(n);return n;}
function wrapLabel(s,max=15){let out=[],line='';for(const w of s.split(/\s+/)){if(line.length+w.length+1>max&&line){out.push(line);line='';}if(w.length>max){if(line)out.push(line);for(let j=0;j<w.length;j+=max)out.push(w.slice(j,j+max));line='';}else line+=(line?' ':'')+w;}if(line)out.push(line);if(out.length>3)out=[...out.slice(0,2),out[2].slice(0,max-1)+'…'];return out;}
function renderGraph(){
 const raw=currentGraph(),e=row(),svg=$('graph');svg.replaceChildren();
 const root=raw.subject_node_index;
 const nodes=raw.node_ids.map((id,i)=>({idx:i,id,label:raw.node_labels[i],cat:i===root?'subject':raw.node_kinds[i].includes('neighbor')?'neighbor':group==='G3_RealOnly'?'old':group==='G4_RandomMatched'?'random':'edit',r:i===root?44:34}));
 let edges=edgesFromRaw(raw).filter(x=>$('show-loops').checked||x.relationId!=='SELF_LOOP');
 if($('show-excluded').checked){
  for(const ex of e.excluded){const i=e.facts.findIndex(f=>f.fact_root_id===ex.fact_root_id);if(i<0)continue;const f=e.facts[i],idx=nodes.length;nodes.push({idx,id:'excluded:'+ex.fact_root_id,label:f.new_object_text,cat:'excluded',r:34,excluded:true});edges.push({i:'x'+i,source:root,target:idx,relation:f.relation_canonical,status:'excluded',cat:'excluded',excluded:true,factIndex:i,reason:ex.reason});}
 }
 const warnings=[];if(group==='G4_RandomMatched')warnings.push('当前是匹配随机对照图，不代表语义正确的知识关系。');
 if($('show-excluded').checked&&e.excluded.length)warnings.push(`额外叠加 ${e.excluded.length} 条未入图事实（红色虚线），仅供审核。`);
 if(!raw.semantic_edge_count)warnings.push('当前实际图没有语义边，仅保留主体及自环；不是数据加载失败。');
 if(nodes.length>70)warnings.push('当前为大图，全部节点与边均保留；远景隐藏密集标签，放大或点击节点查看。');
 $('graph-warning').textContent=warnings.join(' ');$('graph-warning').hidden=!warnings.length;
 const adj=nodes.map(()=>[]);for(const edge of edges){if(edge.source!==edge.target){adj[edge.source].push(edge.target);adj[edge.target].push(edge.source);}}
 const depth=Array(nodes.length).fill(-1),parent=Array(nodes.length).fill(root);depth[root]=0;const queue=[root];
 for(let i=0;i<queue.length;i++)for(const j of adj[queue[i]])if(depth[j]===-1){depth[j]=depth[queue[i]]+1;parent[j]=queue[i];queue.push(j);}
 depth.forEach((d,i)=>{if(d<0)depth[i]=1;});
 nodes[root].x=0;nodes[root].y=0;nodes[root].angle=-Math.PI/2;
 const maxDepth=Math.max(...depth);let previousRadius=0;
 for(let d=1;d<=maxDepth;d++){
  const level=nodes.filter(n=>depth[n.idx]===d).sort((a,b)=>(nodes[parent[a.idx]].angle??0)-(nodes[parent[b.idx]].angle??0)||a.idx-b.idx);
  const radius=Math.max(previousRadius+210,level.length*90/(2*Math.PI));previousRadius=radius;
  level.forEach((n,i)=>{const angle=2*Math.PI*i/level.length-Math.PI/2;n.angle=angle;n.x=radius*Math.cos(angle);n.y=radius*Math.sin(angle);});
 }
 const defs=sv('defs',{},svg);for(const [cat,color]of Object.entries(colors)){const m=sv('marker',{id:'arrow-'+cat,viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:6,markerHeight:6,orient:'auto-start-reverse'},defs);sv('path',{d:'M 0 0 L 10 5 L 0 10 z',fill:color},m);}
 const viewport=sv('g',{class:'viewport'},svg),edgeLayer=sv('g',{},viewport),nodeLayer=sv('g',{},viewport);
 const groupsByPair=new Map();for(const edge of edges){const pair=[edge.source,edge.target].sort((a,b)=>a-b).join(':');if(!groupsByPair.has(pair))groupsByPair.set(pair,[]);groupsByPair.get(pair).push(edge);}
 for(const pair of groupsByPair.values())pair.forEach((x,i)=>{x.bend=(i-(pair.length-1)/2)*44;});
 for(const edge of edges){
  const g=sv('g',{},edgeLayer);edge.path=sv('path',{class:'edge-path',stroke:colors[edge.cat],'marker-end':`url(#arrow-${edge.cat})`,...(edge.excluded?{'stroke-dasharray':'6 5'}:{})},g);
  edge.hit=sv('path',{class:'edge-hit',tabindex:'0',role:'button','aria-label':`${nodes[edge.source].label} ${edge.relation} ${nodes[edge.target].label}`},g);edge.hit.onclick=()=>showEdge(edge);edge.hit.onkeydown=ev=>{if(ev.key==='Enter')showEdge(edge);};
  edge.text=sv('text',{class:'edge-label'+(edge.excluded?' excluded':''),'text-anchor':'middle'},g);const caption=edge.relation;edge.text.textContent=caption.length>32?caption.slice(0,30)+'…':caption;edge.text.onclick=()=>showEdge(edge);sv('title',{},g).textContent=`${nodes[edge.source].label} — ${caption} → ${nodes[edge.target].label}`;
 }
 for(const n of nodes){
  n.el=sv('g',{class:'node','data-id':n.idx,tabindex:'0',role:'button','aria-label':n.label},nodeLayer);
  sv('circle',{r:n.r,fill:fills[n.cat],stroke:colors[n.cat],...(n.excluded?{'stroke-dasharray':'5 3'}:{})},n.el);
  n.text=sv('text',{'text-anchor':'middle',fill:n.cat==='subject'?'#fff':'#263d54','font-size':n.cat==='subject'?12:11},n.el);
  const lines=wrapLabel(n.label,n.cat==='subject'?16:13);lines.forEach((s,i)=>sv('tspan',{x:0,y:-(lines.length-1)*7+i*14+4},n.text).textContent=s);
  sv('title',{},n.el).textContent=n.label+'\n'+n.id;
  n.el.onclick=()=>{if(!graphState?.moved)showNode(n);};n.el.onkeydown=ev=>{if(ev.key==='Enter')showNode(n);};n.el.onpointerdown=ev=>beginDrag(ev,n);
 }
 graphState={nodes,edges,viewport,root,k:1,tx:0,ty:0,moved:false};
 drawGraph();fit();
 $('graph-counts').textContent=`实际图 ${raw.node_ids.length} 节点 / ${raw.semantic_edge_count} 语义边 / ${raw.self_loop_count} 自环${$('show-loops').checked?'（已显示）':'（未绘制）'}；${$('direction').value==='semantic'?'箭头：事实主体 → 客体；消息沿反方向传入主体。':'箭头：运行时 edge_src → edge_dst。'}${$('show-excluded').checked?` 审核叠加 ${e.excluded.length} 条。`:''}`;
}
function drawGraph(){const s=graphState;if(!s)return;const narrow=$('graph').clientWidth<500;for(const n of s.nodes){n.el.setAttribute('transform',`translate(${n.x},${n.y})`);n.renderR=s.nodes.length<=30?Math.max(n.r,(n.idx===s.root?(narrow?25:39):(narrow?21:32))/s.k):n.r;n.el.querySelector('circle').setAttribute('r',n.renderR);const font=s.nodes.length<=30?Math.max(11,(narrow?9:12)/s.k):11;n.text.setAttribute('font-size',font);const lines=n.text.querySelectorAll('tspan');lines.forEach((t,i)=>t.setAttribute('y',-(lines.length-1)*font*.6+i*font*1.2+font*.35));}for(const edge of s.edges){let a=s.nodes[edge.source],b=s.nodes[edge.target];if($('direction').value==='message'&&!edge.excluded)[a,b]=[b,a];let p,lx,ly,ang=0;
 if(a===b){p=`M ${a.x-20} ${a.y-27} C ${a.x-80} ${a.y-105},${a.x+80} ${a.y-105},${a.x+20} ${a.y-27}`;lx=a.x;ly=a.y-79;}
 else {const dx=b.x-a.x,dy=b.y-a.y,len=Math.max(1,Math.hypot(dx,dy)),ux=dx/len,uy=dy/len,cx=(a.x+b.x)/2-uy*edge.bend,cy=(a.y+b.y)/2+ux*edge.bend;const ax=a.x+ux*(a.renderR+3),ay=a.y+uy*(a.renderR+3),bx=b.x-ux*(b.renderR+6),by=b.y-uy*(b.renderR+6);p=`M ${ax} ${ay} Q ${cx} ${cy} ${bx} ${by}`;lx=.25*ax+.5*cx+.25*bx;ly=.25*ay+.5*cy+.25*by-5;ang=Math.atan2(dy,dx)*180/Math.PI;if(ang>90)ang-=180;if(ang<-90)ang+=180;}
 edge.path.setAttribute('d',p);edge.hit.setAttribute('d',p);edge.text.setAttribute('transform',`translate(${lx},${ly}) rotate(${ang})`);edge.text.style.fontSize=(s.nodes.length<=30?Math.max(11,(narrow?8:10)/s.k):11)+'px';
 }transformGraph();}
function transformGraph(){const s=graphState;if(!s)return;s.viewport.setAttribute('transform',`translate(${s.tx},${s.ty}) scale(${s.k})`);for(const e of s.edges)e.text.style.display=$('show-labels').checked&&(s.nodes.length<=70||s.k>.65)?'':'none';for(const n of s.nodes)n.text.style.display=s.nodes.length<=70||s.k>.4||n.idx===s.root?'':'none';}
function fit(){const s=graphState;if(!s)return;const {width:w,height:h}=$('graph').getBoundingClientRect();const xs=s.nodes.map(n=>n.x),ys=s.nodes.map(n=>n.y);const minx=Math.min(...xs)-100,maxx=Math.max(...xs)+100,miny=Math.min(...ys)-100,maxy=Math.max(...ys)+100;s.k=Math.min(1.4,(w-30)/(maxx-minx),(h-50)/(maxy-miny));s.tx=w/2-(minx+maxx)*s.k/2;s.ty=h/2-10-(miny+maxy)*s.k/2;drawGraph();}
function zoom(f,cx,cy){const s=graphState;if(!s)return;const box=$('graph').getBoundingClientRect();cx??=box.width/2;cy??=box.height/2;const k=Math.min(4,Math.max(.02,s.k*f));s.tx=cx-(cx-s.tx)*k/s.k;s.ty=cy-(cy-s.ty)*k/s.k;s.k=k;drawGraph();}
let drag=null;
function beginDrag(ev,n){ev.preventDefault();ev.stopPropagation();const s=graphState;s.moved=false;drag={node:n,x:ev.clientX,y:ev.clientY,nx:n.x,ny:n.y};$('graph').setPointerCapture(ev.pointerId);}
$('graph').onpointerdown=ev=>{if(ev.button!==0||!graphState)return;graphState.moved=false;drag={x:ev.clientX,y:ev.clientY,tx:graphState.tx,ty:graphState.ty};$('graph').setPointerCapture(ev.pointerId);};
$('graph').onpointermove=ev=>{if(!drag||!graphState)return;const dx=ev.clientX-drag.x,dy=ev.clientY-drag.y;if(Math.hypot(dx,dy)>4)graphState.moved=true;if(drag.node){drag.node.x=drag.nx+dx/graphState.k;drag.node.y=drag.ny+dy/graphState.k;drawGraph();}else{graphState.tx=drag.tx+dx;graphState.ty=drag.ty+dy;transformGraph();}};
$('graph').onpointerup=ev=>{if(drag?.node&&!graphState.moved)showNode(drag.node);drag=null;if($('graph').hasPointerCapture(ev.pointerId))$('graph').releasePointerCapture(ev.pointerId);};$('graph').onpointercancel=()=>{drag=null;};
$('graph').addEventListener('wheel',ev=>{ev.preventDefault();const box=$('graph').getBoundingClientRect();zoom(Math.exp(-ev.deltaY*.001),ev.clientX-box.left,ev.clientY-box.top);},{passive:false});
function saveReview(){const e=row();reviews[reviewKey()]={sample_id:e.sample_id,split,index:e.index,subject:e.subject,graphGroup:group,verdict:$('verdict').value,note:$('note').value,updatedAt:new Date().toISOString()};try{localStorage.setItem(key,JSON.stringify(reviews));$('save-state').textContent='已暂存 · 请导出备份';storageOK=true;}catch{storageOK=false;$('save-state').textContent='浏览器禁用存储，请导出备份';}updateList();}
function render(){
 const e=row(),r=reviews[reviewKey()];$('record-label').textContent=`MMKE-entity / ${split==='eval'?'正式评测集 955':'官方训练集 636'} / #${e.index}（零基索引） / ${e.record.type_self}`;
 $('entity-name').textContent=e.subject;$('sample-id').textContent=e.sample_id;
 $('coverage-note').textContent=`${e.coverage.edit_root_count} 条编辑根边 · ${e.coverage.real_neighbor_count} 条真实邻域边 · ${split==='eval'?e.excluded.length+' 条明确过滤事实':'未展示被排除的训练候选'}${split==='eval'?' ｜ 冻结版本 2026-09-26 · 审核不回流正式测试':' ｜ 冻结版本 2026-09-21 · 训练集不与评测集混合'}`;
 $('verdict').value=r?.verdict||'pending';$('note').value=r?.note||'';$('save-state').textContent=storageOK?(r?'已载入本地意见':'未填写'):'浏览器存储不可用';
 showDetail('节点与边的来源证据','<p class="empty">点击图中节点、连线或下方事实，检查完整文本与来源。</p>');
 renderSource();renderFacts();renderEdges();renderGraph();updateList();
}
$('split').onchange=ev=>{split=ev.target.value;index=0;$('search').value='';$('filter').value='all';selectSample(0);};
$('search').oninput=updateList;$('filter').onchange=updateList;
for(const [id,delta]of [['previous',-1],['next',1]])$(id).onclick=()=>{const p=filtered.findIndex(e=>e.index===index);if(filtered[p+delta])selectSample(filtered[p+delta].index);};
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{tab=b.dataset.tab;renderSource();});
$('group').onchange=ev=>{group=ev.target.value;showDetail('节点与边的来源证据','<p class="empty">已切换图谱版本，请选择节点或边。</p>');renderGraph();renderEdges();};
for(const id of ['show-loops','show-excluded','direction'])$(id).onchange=renderGraph;
$('show-labels').onchange=transformGraph;$('fit').onclick=fit;$('zoom-in').onclick=()=>zoom(1.3);$('zoom-out').onclick=()=>zoom(1/1.3);
$('raw-graph').onclick=()=>showDetail('运行时原始 JSON · '+names[group],'<pre>'+esc(pretty(currentGraph()))+'</pre>');
$('verdict').onchange=saveReview;$('note').oninput=saveReview;
$('export-reviews').onclick=()=>download('MMKE-构图审核意见-'+new Date().toISOString().slice(0,10)+'.json',{version:D.manifest.version,exportedAt:new Date().toISOString(),sourceHashes:D.manifest.hashes,annotations:reviews});
$('export-sample').onclick=()=>download(`${split}-${index}-构图证据.json`,{manifest:D.manifest,sample:row(),review:reviews[reviewKey()]||null});
$('import-reviews').onclick=()=>$('review-file').click();
$('review-file').onchange=async ev=>{try{const v=JSON.parse(await ev.target.files[0].text());if(v.version!==D.manifest.version||!v.annotations||typeof v.annotations!=='object')throw new Error('文件版本或结构不匹配');const valid=new Map(Object.entries(D.datasets).flatMap(([sp,rs])=>rs.map(r=>[`${sp}:${r.sample_id}`,r])));const entries=Object.entries(v.annotations);for(const[k,a]of entries){const s=valid.get(k);if(!s||!a||a.sample_id!==s.sample_id||a.index!==s.index||!['pending','pass','issue','uncertain'].includes(a.verdict)||typeof a.note!=='string')throw new Error('文件包含不匹配的样本或无效意见');}let n=0,conflicts=0;for(const[k,a]of entries){if(reviews[k]){conflicts++;continue;}reviews[k]=a;n++;}try{localStorage.setItem(key,JSON.stringify(reviews));}catch{storageOK=false;}render();toast(`导入 ${n} 条；${conflicts} 条已有本地意见，保留原值。`);}catch(err){toast('导入失败：'+err.message);}ev.target.value='';};
$('image-folder').onchange=ev=>{images=new Map();for(const f of ev.target.files){const parts=f.webkitRelativePath.replaceAll('\\','/').split('/');const i=parts.indexOf('entity');if(i>=0)images.set(parts.slice(i).join('/'),f);}renderSource();toast(`已关联 ${images.size} 个 entity 图像文件，未上传。`);};
$('provenance-content').innerHTML=`<p>范围：官方训练集 636 条 + 正式评测集 955 条，分别保留四种冻结运行时图。全量 JSON 未删字段；仅显示格式化，不改原值。</p><p>图中事实箭头与运行时消息方向相反。自环默认省略绘制，但可开启，且完整保存在边表与原始图 JSON 中。图上节点长名称可能缩略，点击查看全文。G4 随机图不是语义正确性证据。</p><p>这是冻结数据的人工审核副本；不会自动将官方评测答案用于构图，不会修改服务器或训练队列。审核意见只写入本浏览器存储，导出后方可作为独立审计材料使用。</p><p>原始数据来自官方 JSON；抽取过程中首尾空白可能被去除，对照校验仅忽略首尾空白，原始 JSON 展示仍保留。训练集冻结事实子集与评测集自动共识事实来源不同。</p><details><summary>查看全部 SHA256 与核验范围</summary><pre>${esc(pretty(D.manifest))}</pre></details>`;
const h=location.hash.match(/^#(train|eval)\/(\d+)$/);if(h&&D.datasets[h[1]][Number(h[2])]){split=h[1];index=Number(h[2]);$('split').value=split;}
new ResizeObserver(()=>fit()).observe($('graph-area'));
render();
window.REVIEW_APP={get split(){return split;},get index(){return index;},get graph(){return graphState;},select:(sp,i)=>{if(!D.datasets[sp]?.[i])throw Error('Invalid index');split=sp;$('split').value=sp;selectSample(i);},stats:D.manifest.stats};
})();
