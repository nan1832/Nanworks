"""Plot all recorded layer evaluations; main/stable never substitute for each other.

python scripts/plot_completed_sweep_results.py
Run scripts/update_sweeplayers.py first when a fresh server audit is needed.
"""
import argparse
from collections import Counter
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import colors, font_manager
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parents[1]
MODELS = [
    ('blip2-opt-2.7b', 'BLIP2', 32),
    ('instructblip-vicuna-7b', 'InstructBLIP', 32),
    ('minigpt-4-vicuna-7b', 'MiniGPT-4', 32),
    ('llava-v1.5-7b', 'LLaVA-1.5', 32),
    ('qwen2.5-vl-3b', 'Qwen2.5-VL', 36),
    ('paligemma-3b', 'PaliGemma', 18),
    ('smolvlm-1.7b', 'SmolVLM', 24),
]
DATASETS = [('evqa-pilot500', 'EVQA'), ('mmke-visual', 'MMKE-V'), ('mmke-entity', 'MMKE-E')]
DS_FULL = {'evqa-pilot500':'EVQA-pilot500', 'mmke-visual':'MMKE-visual', 'mmke-entity':'MMKE-entity'}
RECIPES = ['main', 'main-rerun', 'stable']
NAVY = '#173b57'
MUTED = '#637b8f'
BORDER = '#dce5ed'
ABSENT = '#e3e8ee'
CMAP = colors.LinearSegmentedColormap.from_list('sweep_average',
    ['#f2f7fb','#c5dfed','#83bad4','#418cae','#1e6389','#0b385a'])
NORM = colors.Normalize(0,100)


def key(r):
    return (r['dataset'],r['model'],r['layer'],r['recipe'])


def save_json(p,z):
    p.write_text(json.dumps(z,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def configure_fonts():
    # Use installed local font files directly so the CJK output is reproducible.
    candidates=[Path('C:/Windows/Fonts/msyh.ttc'),Path('C:/Windows/Fonts/msyhbd.ttc')]
    for p in candidates:
        if p.exists():font_manager.fontManager.addfont(str(p))
    installed={f.name for f in font_manager.fontManager.ttflist}
    font=next((x for x in ['Microsoft YaHei','Noto Sans CJK SC','SimHei','DejaVu Sans'] if x in installed),'DejaVu Sans')
    plt.rcParams.update({'font.family':font,'axes.unicode_minus':False,'svg.fonttype':'path',
                         'savefig.facecolor':'white','svg.hashsalt':'completed-layer-main-stable'})
    return font


def make_rows(records, datasets):
    index={key(r):r for r in records}
    rows=[];groups=[]
    for model,name,depth in MODELS:
        start=len(rows)
        for dataset,label in DATASETS:
            if dataset not in datasets:continue
            for recipe in RECIPES:
                cells={l:index[(dataset,model,l,recipe)] for l in range(depth)
                       if (dataset,model,l,recipe) in index}
                if recipe!='main' and not cells:continue
                rows.append(dict(model=model,name=name,depth=depth,dataset=dataset,
                                 dataset_label=label,recipe=recipe,cells=cells))
        groups.append(dict(model=model,name=name,depth=depth,start=start,end=len(rows)))
    return rows,groups


def luminance(rgb):
    vals=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in rgb[:3]]
    return .2126*vals[0]+.7152*vals[1]+.0722*vals[2]


def ink_for(face):
    lum=luminance(face)
    white=1.05/(lum+.05)
    dark=(lum+.05)/(luminance(colors.to_rgb(NAVY))+.05)
    return 'white' if white>=dark else NAVY


def plot(records,datasets,updated_at,out,stem,dpi):
    rows,groups=make_rows(records,datasets)
    n=len(rows)
    # Two lines in every evaluated cell: score, then literal main/stable label.
    # Recipes with no observations have no extra row.
    height=3.05+n*.47
    fig=plt.figure(figsize=(28,height),facecolor='white')
    bottom=1.0/height;top=1-1.70/height
    ax=fig.add_axes([.021,bottom,.924,top-bottom])
    ax.set_xlim(-6.6,36.12);ax.set_ylim(n+.08,-1.53);ax.axis('off')
    title='已完成逐层编辑评测结果' if len(datasets)>1 else DS_FULL[datasets[0]]+' · 已完成逐层编辑评测结果'
    fig.text(.027,1-.38/height,title,fontsize=24,fontweight='bold',color=NAVY,va='center')
    fig.text(.027,1-.79/height,'main / stable 分行展示 · 每格标注运行版本 · 保留未收敛及恢复评测的实际分数',
             fontsize=11.5,color=MUTED,va='center')
    stamp=updated_at[:16].replace('T',' ')
    fig.text(.944,1-.37/height,'结果更新：'+stamp+'（服务器时间）',ha='right',va='center',fontsize=11.5,color=NAVY)
    fig.text(.944,1-.79/height,'白格：暂无已登记评测     灰格：模型无此层',ha='right',va='center',fontsize=10.5,color=MUTED)

    ax.text(-6.38,-.36,'模型',color=NAVY,fontsize=10,fontweight='bold',va='center')
    ax.text(-2.43,-.36,'数据集',color=NAVY,fontsize=10,fontweight='bold',ha='center',va='center')
    ax.text(-.73,-.36,'版本',color=NAVY,fontsize=10,fontweight='bold',ha='center',va='center')
    for start in range(0,36,5):
        end=min(start+5,36)
        ax.add_patch(Rectangle((start,-1.45),end-start,.57,facecolor=NAVY if start%10==0 else '#356381',edgecolor='white',lw=.7))
        ax.text((start+end)/2,-1.16,f'{start}–{end-1}' if end-start>1 else str(start),fontsize=9.4,color='white',ha='center',va='center')
    for l in range(36):
        ax.text(l+.5,-.36,str(l),fontsize=9.2,color=NAVY,ha='center',va='center')

    plotted=[];label_boxes=[]
    for gi,group in enumerate(groups):
        y0,y1=group['start'],group['end']
        if y0==y1:continue
        ax.add_patch(Rectangle((-6.58,y0),3.06,y1-y0,facecolor='#eef4f8' if gi%2==0 else '#f7f9fb',edgecolor='none'))
        center=(y0+y1)/2
        ax.text(-3.80,center-.16,group['name'],fontsize=12.7,fontweight='bold',color=NAVY,ha='right',va='center')
        ax.text(-3.80,center+.36,f"L0–L{group['depth']-1}",fontsize=8.5,color=MUTED,ha='right',va='center')
        for y in range(y0,y1):
            row=rows[y]
            recipe_label='main · 复测' if row['recipe']=='main-rerun' else row['recipe']
            stable=row['recipe']=='stable'
            if stable:
                ax.add_patch(Rectangle((-3.47,y),3.45,1,facecolor='#f2f0fa',edgecolor='none'))
            ax.text(-2.44,y+.50,row['dataset_label'],ha='center',va='center',fontsize=10.0,fontweight='bold',color=NAVY)
            ax.text(-.78,y+.50,recipe_label,ha='center',va='center',fontsize=8.5,
                    color='#6c4c95' if stable else MUTED,fontweight='bold' if stable else 'normal')
            for layer in range(36):
                r=row['cells'].get(layer)
                face=ABSENT if layer>=row['depth'] else 'white'
                if r is not None:face=CMAP(NORM(r['average']))
                ax.add_patch(Rectangle((layer,y),1,1,facecolor=face,edgecolor=BORDER,lw=.40))
                if r is None:continue
                ink=ink_for(face)
                score=ax.text(layer+.5,y+.36,f"{r['average']:.2f}",ha='center',va='center',
                              fontsize=8.8,color=ink,fontweight='medium')
                recipe_text='stable' if row['recipe']=='stable' else 'main'
                version=ax.text(layer+.5,y+.75,recipe_text,ha='center',va='center',fontsize=6.8,color=ink)
                plotted.append(key(r));label_boxes.append((score,version,layer,y))
            if y+1<y1 and row['dataset']!=rows[y+1]['dataset']:
                ax.plot([-3.48,36],[y+1,y+1],color='#b9cbd8',lw=.65)
        ax.plot([-3.48,36],[y0,y0],color='#8ba5b9',lw=1.12)
    ax.plot([-3.48,36],[n,n],color='#8ba5b9',lw=1.12)
    ax.plot([36,36],[0,n],color='#8ba5b9',lw=.9)

    cb_height=min(.52,6.8/height)
    cbax=fig.add_axes([.961,bottom+(top-bottom-cb_height)/2,.010,cb_height])
    cb=fig.colorbar(plt.cm.ScalarMappable(norm=NORM,cmap=CMAP),cax=cbax,ticks=[0,20,40,60,80,100])
    cb.ax.tick_params(labelsize=10,length=2.8,color=MUTED,labelcolor=NAVY)
    cb.outline.set_edgecolor(BORDER)
    cb.ax.set_title('Average\n(%)',fontsize=11,color=NAVY,pad=12)

    fig.text(.027,.54/height,'颜色与数字：Average（五项评测指标均值，%）；层编号从 0 开始。main 与 stable 不相互替代，也不跨版本选最高分。',
             fontsize=10.2,color=MUTED,va='center')
    footer='图中保留全部已登记评测，不以训练是否收敛筛选；checkpoint 按原运行选点记录。'
    if any(r['recipe']=='main-rerun' for r in rows):footer+=' BLIP2 / EVQA 的 L18 main 复测单独列出。'
    fig.text(.027,.25/height,footer,fontsize=9.8,color=MUTED,va='center')

    expected={key(r) for r in records if r['dataset'] in datasets}
    assert len(plotted)==len(set(plotted)) and set(plotted)==expected
    fig.canvas.draw()
    renderer=fig.canvas.get_renderer()
    # Check actual text extents against the cell borders, not just font sizes.
    for score,version,l,y in label_boxes:
        x0,y0=ax.transData.transform((l,y));x1,y1=ax.transData.transform((l+1,y+1))
        left,right=min(x0,x1),max(x0,x1);low,high=min(y0,y1),max(y0,y1)
        for text in [score,version]:
            box=text.get_window_extent(renderer)
            assert box.x0>=left and box.x1<=right and box.y0>=low and box.y1<=high,(key,score.get_text())
    fig.savefig(out/(stem+'.png'),dpi=dpi,facecolor='white')
    fig.savefig(out/(stem+'.svg'),facecolor='white')
    if len(datasets)>1:
        fig.savefig(out/'preview.png',dpi=110,facecolor='white')
    plt.close(fig)
    return dict(stem=stem,plot_rows=n,plotted_records=len(plotted),datasets=datasets,
                records_sha256=hashlib.sha256(json.dumps(sorted(plotted)).encode()).hexdigest())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger',type=Path,default=ROOT/'outputs/sweep_ledger/latest.json')
    parser.add_argument('--output',type=Path,default=ROOT/'outputs/completed_layer_results_20260928')
    parser.add_argument('--dpi',type=int,default=300)
    args=parser.parse_args()
    z=json.loads(args.ledger.read_text(encoding='utf-8'))
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    records=[]
    for r in z['rows']:
        assert r['recipe'] in RECIPES,r['recipe']
        assert math.isfinite(r['metrics']['Average']) and 0<=r['metrics']['Average']<=100
        assert 0<=r['layer']<dict((m,d) for m,_,d in MODELS)[r['model']]
        records.append({k:r.get(k) for k in ['dataset','model','layer','recipe','epoch','raw_loss','ema_loss','samples',
                                           'training','evidence','status','original_status','source','notes']} |
                       dict(average=r['metrics']['Average'],metrics=r['metrics']))
    assert len(records)==len({key(r) for r in records})
    font=configure_fonts()
    payload=dict(source_ledger=str(args.ledger.resolve()),source_sha256=hashlib.sha256(args.ledger.read_bytes()).hexdigest(),
                 updated_at=z['updated_at'],scope='All recorded evaluations; recipes shown separately; no candidate-union filtering or denominator',
                 records=records)
    save_json(out/'source_data.json',payload)
    outputs=[plot(records,list(DS_FULL),z['updated_at'],out,'completed_layers_average_main_stable',args.dpi)]
    for ds in DS_FULL:
        outputs.append(plot(records,[ds],z['updated_at'],out,ds.replace('-','_')+'_completed_layers',args.dpi))
    manifest=dict(font=font,color_scale=[0,100],display_decimals=2,recipe_records=Counter(r['recipe'] for r in records),
                  updated_at=z['updated_at'],source_ledger_sha256=payload['source_sha256'],figures=outputs,
                  files={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                         for p in sorted(out.iterdir()) if p.suffix in ['.png','.svg']})
    save_json(out/'manifest.json',manifest)
    notes='''# 最新已完成逐层评测结果图

- 总览：[PNG](completed_layers_average_main_stable.png) / [SVG](completed_layers_average_main_stable.svg)
- EVQA：[PNG](evqa_pilot500_completed_layers.png) / [SVG](evqa_pilot500_completed_layers.svg)
- MMKE-visual：[PNG](mmke_visual_completed_layers.png) / [SVG](mmke_visual_completed_layers.svg)
- MMKE-entity：[PNG](mmke_entity_completed_layers.png) / [SVG](mmke_entity_completed_layers.svg)

## 数据与绘制口径

图中展示最新扫层台账已登记的全部评测；没有候选并集筛选、Top-3 并集总数、完成率或待测候选框。
同一层的 main / stable 分行绘制，每个有分数的格内重复标注实际版本。当前 stable 结果来自 PaliGemma；未用 stable 替换 main，未跨配方取最高分。
BLIP2 × EVQA L18 的 main 复测有独立行，原 main 结果也保留。

未收敛、训练中断后恢复评测和低分结果均保留；是否有完整 50 轮、选中 epoch、EMA、训练状态及来源见 source_data.json。
常规流程按训练后的最低有限 EMA 选点；图只复用真实评测，不重新选点。
台账已提示的三项现存 history / selected 不一致（EVQA/PaliGemma main L14、MMKE-visual/PaliGemma stable L2/L13）保留原分数和 notes，不能把所有历史记录统称为本次重新验证的全程最小 EMA。
MMKE-visual/PaliGemma stable L8 是历史手工选择 Epoch13 的恢复评测，保持这一身份。

颜色为全图统一 0–100 的 Average，数值保留两位小数；图像颜色使用完整精度。白格表示当前没有已登记结果，不能解读为未推荐；灰格表示模型没有该层。
继承台账历史记录的条目仍保留原 evidence 属性；本次绘图没有再次声称全部历史原件已经在服务器核验。
SVG 文字转路径，可不依赖本机字体无损放大；PNG 使用 300 dpi。

## 后续更新

在项目根目录依次运行：

```powershell
python scripts/update_sweeplayers.py
python scripts/plot_completed_sweep_results.py
```

前者只读核对服务器并更新台账，后者从最新台账重画。
'''
    notes+='\n数据更新时间（服务器，北京时区）：'+z['updated_at']+'。\n'
    (out/'README.md').write_text(notes,encoding='utf-8')
    print(json.dumps(dict(output=str(out),records=len(records),recipe_records=manifest['recipe_records'],figures=outputs),ensure_ascii=False,indent=2))


if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    main()
