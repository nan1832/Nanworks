"""Plot the eight-method Top-3 union; no method-specific recommendation overlays."""
import contextlib
import hashlib
import io
import json
import runpy
from datetime import datetime, timezone, timedelta
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import colors, font_manager
from matplotlib.patches import Rectangle

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/formal8_union_heatmap_20260922'
OUT.mkdir(exist_ok=True)
with contextlib.redirect_stdout(io.StringIO()):
    d=runpy.run_path(str(ROOT/'outputs/calculate_formal8_metrics_20260922.py'))
audit=json.loads((ROOT/'outputs/localization_audit_20260922/formal8_union_status.json').read_text(encoding='utf-8'))
lookup={(r['dataset'],r['model']):r for r in audit['combinations']}
models=list(d['DM'].values()); datasets=list(d['DS'].values())
depths=[32,32,32,32,36,18,24]
names=['BLIP2','InstructBLIP','MiniGPT-4','LLaVA-1.5','Qwen2.5-VL','PaliGemma','SmolVLM']
dslabels=['EVQA','MMKE-V','MMKE-E']
variants=['main','main_diagnostic','stable']
records=[]
for model,depth in zip(models,depths):
    for ds in datasets:
        union=lookup[(ds,model)]['top3']
        for layer in union:
            assert 0<=layer<depth
            method_ranks={m:d['candidates'][(ds,model,m)].index(layer)+1
                          for m in d['METHODS'] if layer in d['candidates'][(ds,model,m)]}
            value=None; variant=None; source=None
            for v in variants:
                key=(ds,model,layer,v)
                if key in d['scores']:
                    value=d['scores'][key]; variant=v; source=d['provenance'][key]; break
            status=lookup[(ds,model)]['states'][str(layer)]['status']
            if value is None:
                assert model=='LLaVA-v1.5-7B'
                assert not status.startswith(('evaluated_','diagnostic_eval_only'))
            records.append(dict(dataset=ds,model=model,layer=layer,method_recommended_ranks=method_ranks,
                                average=value,variant=variant,status=status,source=source))
assert len(records)==324
assert sum(r['average'] is not None for r in records)==313
assert sum(r['variant']=='stable' for r in records)==7
assert sum(r['variant']=='main_diagnostic' for r in records)==2
assert sum(r['average'] is None for r in records)==11
matrix={(r['dataset'],r['model'],r['layer']):r for r in records}
timestamp=datetime.now(timezone(timedelta(hours=8))).isoformat()
payload=dict(generated_at=timestamp,scope='Eight-method Top-3 union only',
             methods=d['METHODS'],combinations=21,candidate_cells=324,evaluated_cells=313,pending_cells=11,
             policy='main > main_diagnostic > stable; no maximization across variants',
             color_scale=[0,100],display_decimals=2,records=records)
(OUT/'source_data.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')

installed={f.name for f in font_manager.fontManager.ttflist}
font=next(f for f in ['Microsoft YaHei','SimHei','Noto Sans CJK SC','DejaVu Sans'] if f in installed)
plt.rcParams.update({'font.family':font,'axes.unicode_minus':False,'svg.fonttype':'none'})
fig=plt.figure(figsize=(25,12.2),facecolor='white')
ax=fig.add_axes([.025,.035,.943,.815])
ax.set_xlim(-5.15,38.3); ax.set_ylim(21.05,-1.55); ax.axis('off')
navy='#193c59'; muted='#647e94'; border='#d5e0e9'; purple='#8e44c4'
cmap=colors.LinearSegmentedColormap.from_list('performance',['#f0f6fb','#c3dce9','#80b6d1','#3e89b2','#185c84','#0b3556'])
norm=colors.Normalize(0,100)
fig.text(.028,.946,'八方法 Top-3 并集 × 真实编辑性能',fontsize=23,fontweight='bold',color=navy)
fig.text(.029,.911,'7 模型 × 3 数据集  |  CMA-alt v1.3 + CMA-model_pred v2  |  2026-09-22',fontsize=11,color=muted)
fig.text(.966,.947,'313 / 324 已评测',fontsize=14,color=navy,ha='right')
fig.text(.966,.912,'紫框：待评测     白格：非候选并集     灰格：无此层',fontsize=10,color=muted,ha='right')
ax.text(-4.95,-.36,'模型',fontsize=10,color=navy,fontweight='bold',va='center')
ax.text(-1.38,-.36,'数据集',fontsize=10,color=navy,fontweight='bold',va='center',ha='center')
for start in range(0,36,5):
    end=min(start+5,36)
    ax.add_patch(Rectangle((start,-1.48),end-start,.65,facecolor=navy if start%10==0 else '#315e7d',edgecolor='white',lw=.6))
    ax.text((start+end)/2,-1.155,f'{start}–{end-1}' if end-start>1 else str(start),color='white',fontsize=9,ha='center',va='center')
for l in range(36): ax.text(l+.5,-.37,str(l),ha='center',va='center',color=navy,fontsize=8.5)

for mi,(model,depth,name) in enumerate(zip(models,depths,names)):
    y0=mi*3
    ax.add_patch(Rectangle((-5.1,y0),3.0,3,facecolor='#eff4f8' if mi%2==0 else '#f8fafc',edgecolor='none'))
    ax.text(-2.38,y0+1.25,name,ha='right',va='center',fontsize=12,color=navy,fontweight='bold')
    ax.text(-2.38,y0+1.87,f'{depth} layers',ha='right',va='center',fontsize=8,color=muted)
    for di,(ds,label) in enumerate(zip(datasets,dslabels)):
        y=y0+di
        ax.text(-.23,y+.5,label,ha='right',va='center',fontsize=9.5,color=navy,fontweight='bold')
        for l in range(36):
            r=matrix.get((ds,model,l))
            face='#e1e7ed' if l>=depth else 'white'
            if r and r['average'] is not None: face=cmap(norm(r['average']))
            ax.add_patch(Rectangle((l,y),1,1,facecolor=face,edgecolor=border,lw=.45))
            if r:
                if r['average'] is None:
                    ax.add_patch(Rectangle((l+.055,y+.065),.89,.87,facecolor='#faf5ff',edgecolor=purple,lw=1.9))
                    ax.text(l+.5,y+.5,'—',ha='center',va='center',fontsize=11,color=purple)
                else:
                    value=r['average']
                    # Choose label contrast using rendered cell luminance.
                    rr,gg,bb,_=cmap(norm(value))
                    lum=.2126*rr+.7152*gg+.0722*bb
                    ink='white' if lum<.56 else navy
                    ax.text(l+.5,y+.5,f'{value:.2f}',ha='center',va='center',fontsize=7.9,color=ink)
    ax.plot([-2.02,36],[y0,y0],color='#93aabd',lw=.95)
ax.plot([-2.02,36],[21,21],color='#93aabd',lw=.95)
ax.plot([36,36],[0,21],color='#93aabd',lw=.9)
cbax=fig.add_axes([.966,.19,.010,.48])
cb=fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=cmap),cax=cbax,ticks=[0,20,40,60,80,100])
cb.ax.tick_params(labelsize=9,length=2,color=muted,labelcolor=navy)
cb.outline.set_edgecolor(border)
cb.ax.set_title('Average',fontsize=10,color=navy,pad=11)
png=OUT/'formal8_top3_union_average_heatmap.png'
fig.savefig(png,dpi=260,facecolor='white')
fig.savefig(OUT/'formal8_top3_union_average_heatmap.svg',facecolor='white')
fig.savefig(OUT/'preview.png',dpi=100,facecolor='white')
plt.close(fig)
notes=f'''# 八方法Top-3联合候选真实评测热力图

生成时间：{timestamp}

- 图中仅填充八方法Top-3并集324项，不扩展至Top-5或并集外已评测层；313项数值、11项紫框待评测。
- 紫框：EVQA/LLaVA L2,L4；MMKE-entity/LLaVA L0,L1,L2,L4,L7,L9,L11,L12,L13。
- Average全图固定0—100；格内保留两位小数，颜色使用未舍入数值。白格为并集外、灰格为模型不存在该层；没有任何方法Top-3/Top-5推荐框。
- 图下方按用户要求不放说明；图顶端仅保留标题、版本、色块状态与覆盖数量。
- 数据采用main优先，main缺失才使用stable；不跨配置取最高分。7项stable-only是MMKE-visual/PaliGemma L1,L2,L3,L5,L6,L7,L13。
- 两项main诊断结果：EVQA/PaliGemma L0=35.492，MMKE-visual/PaliGemma L0=38.520，非完整50轮、不收敛标签保留；历史数值异常同样不隐藏。
- 21组展示不表示21组公平可比：17组历史主口径、加EVQA/Pali诊断为18组，加MMKE-visual/Pali stable补齐为19组混合扩展；EVQA及entity的LLaVA仍缺评测。
- CMA两版单独保留；CMA-modelpred的EVQA/Qwen、EVQA/SmolVLM、visual/PaliGemma、visual/SmolVLM有推荐稳定性警告。图展示真实Adapter分数，不表示候选定位置信度。
- source_data.json逐格保存完整分数、配置类别、状态、来源、八方法版本和推荐层序号。来源为当前手册4.0、历史验收CSV和20260922逐层核验记录；未重新连接服务器或训练。
'''
(OUT/'README.md').write_text(notes,encoding='utf-8')
print(json.dumps(dict(png=str(png),source=str(OUT/'source_data.json'),font=font,
    cells=len(records),evaluated=313,pending=11,sha256=hashlib.sha256(png.read_bytes()).hexdigest()),ensure_ascii=False))
