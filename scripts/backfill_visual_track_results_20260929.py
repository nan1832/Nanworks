"""Publish verified 21-group visual-track results without rewriting real-edit rows."""
import csv
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/visual_track_cosine_20260928/targets_v2'
DOC=ROOT/'md/Location'
BACKUP=OUT/'backfill_20260929/backups'
MODELS={'blip2-opt-2.7b':'BLIP2','instructblip-vicuna-7b':'InstructBLIP','minigpt-4-vicuna-7b':'MiniGPT4','llava-v1.5-7b':'LLaVA','qwen2.5-vl-3b':'Qwen2.5-VL','paligemma-3b':'PaliGemma','smolvlm-1.7b':'SmolVLM'}
DATASETS={'evqa-pilot500':500,'mmke-visual':214,'mmke-entity':636}
VARIANTS=['none','alt','model_pred']
LINK='../../outputs/visual_track_cosine_20260928/targets_v2/'


def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(name):return list(csv.DictReader((OUT/name).open(encoding='utf-8-sig',newline='')))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def layers(a):return ', '.join('L'+str(i) for i in a) or '—'
def number(x):return '待补' if x in [None,''] else f'{float(x):.3f}'
def table(headers,rr):return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(map(str,r))+' |' for r in rr])+'\n'
def text(p):return Path(p).read_bytes().decode('utf-8-sig')
def replace_block(original,key,body,before=None):
    start='<!-- '+key+'_START -->';end='<!-- '+key+'_END -->'
    block=start+'\n'+body.strip()+'\n'+end
    if start in original:
        assert original.count(start)==original.count(end)==1
        return re.sub(re.escape(start)+r'.*?'+re.escape(end),lambda _:block,original,flags=re.S)
    if before:
        assert original.count(before)==1,before
        return original.replace(before,block+'\n\n'+before,1)
    return original.rstrip()+'\n\n'+block+'\n'


def main():
    verification=load(OUT/'verification.json');receipt=load(OUT/'completion_receipt.json')
    assert verification['formal_groups_done']==21 and verification['formal_groups_pending']==0
    assert len(receipt['completion']['groups'])==21
    completed=receipt['completion']['time'];checked=receipt['time']
    summaries={}
    for group in receipt['completion']['groups']:
        ds,model=group['dataset'],group['model'];p=OUT/'results'/ds/model
        assert sha(p/'summary.json')==group['summary_sha256']
        s=load(p/'summary.json');assert s['status']=='done' and s['sample_count']==DATASETS[ds]
        for name,key in [('protocol.json','protocol_sha256'),('layer_scores.json','scores_sha256'),('diagnostics.json','diagnostics_sha256')]:assert sha(p/name)==s[key]
        summaries[ds,model]=s
    recs=load(OUT/'recommendations.json')
    assert len(recs)==252
    primary={(r['dataset'],r['model'],r['variant'],r['flavor']):r for r in recs if r['cohort']=='matched_gradient'}
    assert len(primary)==126
    performance=[r for r in rows('performance.csv') if r['cohort']=='matched_gradient']
    assert len(performance)==126
    fixed=rows('three_variant_fixed_cohort.csv');paired=rows('paired_summary.csv')
    common=table(['版本','排序','三版共同可比组数','Top-1','Best@3','Mean@3'],[[r['variant'],r['flavor'],r['n'],number(r['top1']),number(r['best3']),number(r['mean3'])] for r in fixed])
    evidence=(f'**完成时间：{completed}；服务器核验时间：{checked}。** 7 个模型 × 3 个数据集均已完成，'
              '每组含 none、alt、model_pred 三版，共 63 份定位统计；各自报告 Raw / Tukey，共 126 份主推荐。\n\n')
    definitions=('VisualTrack-Cos-none：视觉 token 平均表征与最后提示词位置的余弦。'
                 'VisualTrack-Cos-alt / VisualTrack-Cos-model_pred：固定同一图像与提示词前缀，追加对应答案，'
                 '对完整答案的有效预测位置先取余弦均值，再对样本等权平均。预测 yₜ 的位置是 P−1+t；'
                 '不使用读入 yₜ 后的位置代替。单个普通答案 token 时可退化为 none。'
                 'model_pred 使用冻结历史缓存的全部可用文本，不补写被历史生成长度截断的内容。\n\n'
                 '这是表征余弦方法，与梯度方向余弦、LGA 梯度内积及 VisEdit 贡献度分别报告。'
                 '主表复用历史视觉梯度有效样本 ID（matched_gradient）；available_train 单列于机器文件。'
                 'Raw 按有符号余弦降序，Tukey 按每组每版全部有限层分数、κ=1、linear 四分位一次过滤；同分取浅层。'
                 '表中首层为 Top-1 推荐层，最高层分数不等于最高编辑效果。\n\n')
    scope=('编辑性能配对固定使用 **2026-09-28T11:10:16+08:00** 的扫层快照，396 条 main；'
           '36 条 stable 与 1 条 main-rerun 不代填或择优替换。此处未添加任何新训练结果。'
           'Top-1 是第一推荐层的 Average；Best@3、Mean@3 分别为完整三候选层的最大值、均值。'
           '缺任一候选的 main 评测就不计算完整 Best/Mean@3。'
           '以下三版汇总固定使用同一批三方 Top-3 都有评测且定位覆盖率 ≥80% 的组合；'
           'Raw 与 Tukey 的共同组合可能不同，不能直接把跨表均值差当作过滤收益。\n\n')
    sections=[]
    for idx,(ds,total) in enumerate(DATASETS.items(),1):
        rr=[]
        for model,label in MODELS.items():
            for variant in VARIANTS:
                raw=primary[ds,model,variant,'raw'];tukey=primary[ds,model,variant,'tukey']
                n=raw['n'];coverage=f'{n}/{total}'+('（低覆盖）' if n/total<.8 else '')
                rr.append([label,variant,coverage,layers(raw['top3']),layers(raw['top5']),layers(tukey['top3']),layers(tukey['top5']),layers(tukey['outlier_layers'])])
        sections += [f'### 8.{idx} {ds}\n',table(['模型','版本','有效样本','Raw Top-3','Raw Top-5','Tukey Top-3','Tukey Top-5','Tukey 剔除层'],rr)]
    section='<a id="visual-track-three-variants"></a>\n\n## 8. 视觉表征余弦三版本（VisualTrack-Cos；本阶段不做，仅留档）\n\n'
    section+='**当前状态（2026-09-29，用户决定）：本阶段不做本方法。** none、alt、model_pred 三版的已有定位统计、候选层和历史比较保留追溯；不再为本方法补算、补训或补评测，不纳入当前公式筛选和候选补跑并集。此前 9 层、15 层峰顶及 75 层峰值区间等补跑方案不执行；后续工作集中于第七类 V01–V10 与前六类方法的比较。下方“完成时间”仅指历史定位统计完成，不表示已完成全部候选层编辑评测或仍需继续本方法。\n\n'
    section+=evidence+definitions+'\n'.join(sections)
    section+='\n### 8.4 已有真实编辑结果上的三版共同组合比较\n\n'+scope+common
    section+=f'\n逐组合性能、缺失评测层及与既有公式的配对结果见[三版本结果报告](VisualTrack_Three_Variants_Results_20260929.md)。\n\n[全部推荐与全层排序]({LINK}recommendations.json) · [逐组合性能]({LINK}performance.csv) · [各分项指标 Spearman]({LINK}correlations.csv) · [Tukey 阈值与剔除层]({LINK}recommendations.csv) · [完成及恢复训练回执]({LINK}completion_receipt.json)\n'
    section='<!-- VISUAL_TRACK_RESULTS_START -->\n'+section+'<!-- VISUAL_TRACK_RESULTS_END -->\n'
    (OUT/'recommendation_section.md').write_text(section,encoding='utf-8')
    index=('### 2.9 补充：视觉表征余弦三版本\n\n'
           f'21/21 组已于 {completed} 完成。分别报告 VisualTrack-Cos-none、-alt、-model_pred 的 Raw/Tukey Top-3、Top-5、异常层和有效样本数。'
           '推荐层见[推荐总表第 8 节](ALL_Methods_Recommends_layers.md#visual-track-three-variants)，'
           '真实编辑表现及缺失候选评测见[三版本结果报告](VisualTrack_Three_Variants_Results_20260929.md)。'
           '沿用既定扫层快照比较；本次不重写历史候选并集或把定位补算视为新训练评测。')
    (OUT/'main_index_section.md').write_text('<!-- VISUAL_TRACK_INDEX_START -->\n'+index+'\n<!-- VISUAL_TRACK_INDEX_END -->\n',encoding='utf-8')
    report='# 视觉表征余弦三版本：完整定位结果与已有编辑效果\n\n'+evidence+definitions
    report+='## 比较口径与覆盖率\n\n'+scope+'BLIP2 × MMKE-entity 的主定位样本为 284/636（44.65%），逐组结果保留，≥80% 汇总中排除；全样本统计仅作独立补充。T-Loc 在冻结 main 结果中为常量，其层级相关性未定义，不记为零。\n\n'
    report+='## 三版共同组合的 Top-1、Best@3、Mean@3\n\n'+common+f'\n共同组合清单见[固定组合 CSV]({LINK}three_variant_fixed_cohort.csv)。\n\n'
    report+='## 与既有公式的同组合配对\n\n以下按相同 Raw/Tukey 规则、相同模型×数据集及候选评测齐全的组合配对；各行组合数可能不同。参数与视觉梯度方法本身的样本协议不同，不能把这里解释为逐样本梯度对齐实验。Δ 为 VisualTrack 减参照，单位为百分点评测分数；正数表示 VisualTrack 较高。\n\n'
    pp=[r for r in paired if r['flavor']==r['baseline_flavor']]
    report+=table(['版本','排序','参照','配对组数','ΔTop-1','ΔBest@3','ΔMean@3','Best@3 胜/平/负'],[[r['variant'],r['flavor'],r['baseline'],r['n'],number(r['delta_top1']),number(r['delta_best3']),number(r['delta_mean3']),'/'.join(r[k] for k in ['wins_best3','ties_best3','losses_best3'])] for r in pp])
    report+='\n## 逐组合推荐性能与缺失评测层\n\n“待补”表示冻结扫层快照缺少所需 main 评测，不代表零分。样本不足 80% 的行单独标记。\n\n'
    for ds,total in DATASETS.items():
        rr=[]
        for model,label in MODELS.items():
            for variant in VARIANTS:
                for flavor in ['raw','tukey']:
                    r=next(z for z in performance if (z['dataset'],z['model'],z['variant'],z['flavor'])==(ds,model,variant,flavor))
                    rr.append([label,variant,flavor,'L'+str(r['top1_layer']),number(r['top1']),number(r['best3']),number(r['mean3']),layers(json.loads(r['missing_main_layers'])),r['n']+f'/{total}'+('（低覆盖）' if float(r['coverage'])<.8 else '')])
        report+='### '+ds+'\n\n'+table(['模型','版本','排序','Top-1 层','Top-1','Best@3','Mean@3','缺失 main 层','定位样本'],rr)+'\n'
    report+='## 核验、文件与复算\n\n'
    report+=f'[推荐层完整表](ALL_Methods_Recommends_layers.md#visual-track-three-variants) · [全部逐组推荐]({LINK}recommendations.json) · [性能明细]({LINK}performance.csv) · [逐层相关性六项指标]({LINK}correlations.csv) · [全部同组合配对]({LINK}paired_summary.csv) · [21 组来源状态]({LINK}source_status.csv) · [完成回执]({LINK}completion_receipt.json)。\n\n'
    report+='复算顺序：`python scripts/visual_track_targets_remote_20260928.py fetch` → `python scripts/analyze_visual_track_targets_20260928.py` → `python scripts/backfill_visual_track_results_20260929.py`。本次先逐样本验证服务器 SHA-256，再同步紧凑统计；回填脚本再次核对 21 份完成回执、样本数、协议与分数哈希。原始程序及 SmolVLM 修复版本均保留于协议中。\n'
    changes={}
    p=DOC/'ALL_Methods_Recommends_layers.md';old=text(p)
    body=section.split('\n',1)[1].rsplit('<!-- VISUAL_TRACK_RESULTS_END -->',1)[0]
    changes[p]=replace_block(old,'VISUAL_TRACK_RESULTS',body,before='<a id="visedit-pred-archive"></a>')
    p=DOC/'6location_7model_3datas_top_3_5_layers_outcome.md';old=text(p)
    changes[p]=replace_block(old,'VISUAL_TRACK_INDEX',index,before='> **以下第 3 节是历史冻结比较')
    assert old.split('## 3. 数据集分表',1)[1]==changes[p].split('## 3. 数据集分表',1)[1]
    p=DOC/'SWeeplayers.md';old=text(p)
    ledger_note='## 视觉表征余弦三版本推荐比较（2026-09-29）\n\n'+evidence+scope+common+'\n本次增加定位推荐的比较与索引，不新增或改写本台账的真实训练评测条目。完整逐组合表见[三版本结果报告](VisualTrack_Three_Variants_Results_20260929.md)，推荐层见[总表第 8 节](ALL_Methods_Recommends_layers.md#visual-track-three-variants)。'
    changes[p]=replace_block(old,'VISUAL_TRACK_PERFORMANCE',ledger_note)
    assert changes[p].split('<!-- VISUAL_TRACK_PERFORMANCE_START -->')[0].rstrip()==old.split('<!-- VISUAL_TRACK_PERFORMANCE_START -->')[0].rstrip()
    changes[DOC/'VisualTrack_Three_Variants_Results_20260929.md']=report
    p=DOC/'VisualTrack_Three_Variants_20260928.md';old=text(p)
    current='## 完成与回填（2026-09-29）\n\n'+evidence+'全部完成后 MiniGPT4 L8 已于 '+receipt['state']['time']+' 自动进入续训。此处是采集时快照，当前轮次以后续训练日志为准。\n\n推荐层与性能已回填至[总表第 8 节](ALL_Methods_Recommends_layers.md#visual-track-three-variants)和[完整结果报告](VisualTrack_Three_Variants_Results_20260929.md)。下方为保留的定义、暂停和修复历史。'
    changes[p]=replace_block(old,'VISUAL_TRACK_COMPLETION',current,before='## 2026-09-29 修复与继续执行')
    p=DOC/'VisualTrack_Cosine_Recommendation_Analysis.md';old=text(p)
    start=old.index('## 正式数据补算与比较');end=old.index('## 复核与文件',start)
    replacement='## 正式数据补算与比较\n\n'+evidence+'正式三版本结果已经完成；本页上方桥梁候选仅作原始曲线追溯，不与 E-VQA/MMKE 编辑成绩混配。完整结果见[三版本结果报告](VisualTrack_Three_Variants_Results_20260929.md)，候选表见[推荐总表第 8 节](ALL_Methods_Recommends_layers.md#visual-track-three-variants)。\n\n'+scope+common+'\n'
    changes[p]=old[:start]+replacement+old[end:]
    for a,b in [('formal_source_status.csv','targets_v2/source_status.csv'),('](../../outputs/visual_track_cosine_20260928/recommendations.json)','](../../outputs/visual_track_cosine_20260928/targets_v2/recommendations.json)'),('](../../outputs/visual_track_cosine_20260928/paired_summary.csv)','](../../outputs/visual_track_cosine_20260928/targets_v2/paired_summary.csv)'),('](../../outputs/visual_track_cosine_20260928/status.json)','](../../outputs/visual_track_cosine_20260928/targets_v2/status.json)'),('- 已有 main 上的 Top-1/3/5：待正式前向统计完成后生成。',f'- [已有 main 上的 Top-1、Best@3、Mean@3]({LINK}performance.csv)。'),('- 各分项指标的层级相关性：待正式前向统计完成后生成。',f'- [各分项指标层级相关性]({LINK}correlations.csv)。'),('运行 `python scripts/visual_track_remote_20260928.py fetch` 同步完成组合，再运行 `python scripts/analyze_visual_track_cosine_20260928.py` 更新本报告。','当前正式三版本的复算与回填入口见[完整结果报告](VisualTrack_Three_Variants_Results_20260929.md)；原桥梁曲线程序仅用于历史结果追溯。')]:changes[p]=changes[p].replace(a,b)
    BACKUP.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for p,new in changes.items():
        prior=p.read_bytes() if p.exists() else b'';backup=BACKUP/p.name
        if p.exists() and not backup.exists():backup.write_bytes(prior)
        if prior!=new.encode('utf-8'):p.write_bytes(new.encode('utf-8'))
        manifest.append({'file':str(p.relative_to(ROOT)),'before_sha256':hashlib.sha256(prior).hexdigest(),'after_sha256':sha(p),'backup':str(backup.relative_to(ROOT)) if backup.exists() else None})
    for p in changes:
        for target in re.findall(r'\]\(([^)]+)\)',text(p)):
            target=target.strip('<>')
            if '://' in target or target.startswith('#'):continue
            assert (p.parent/target.split('#')[0]).exists(),(p.name,target)
    result={'status':'PASS','server_checked_at':checked,'completion_time':completed,'groups':21,'variants':63,'primary_recommendations':126,'secondary_recommendations':126,'performance_rows':126,'original_real_editing_rows_unchanged':True,'method_formula_unchanged':True,'files':manifest,'input_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [OUT/'recommendations.json',OUT/'performance.csv',OUT/'correlations.csv',OUT/'paired_summary.csv',OUT/'completion_receipt.json']}}
    (OUT/'backfill_20260929/verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':'PASS','groups':21,'documents_updated':len(changes),'primary_recommendations':126},ensure_ascii=False))


if __name__=='__main__':main()
