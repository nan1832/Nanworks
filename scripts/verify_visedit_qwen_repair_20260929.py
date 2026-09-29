"""Check the finished two-group repair and publish the local completion evidence."""
import hashlib
import json
from pathlib import Path
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'outputs/visedit_model_pred_mmke_20260929'

def load(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    status=load(BASE/'sync_status.json')
    assert len(status['verified_complete_groups'])==14
    assert status['repair_worker']['state']=='DONE'
    receipt=load(BASE/'completion_receipt.json')
    assert receipt['state']=='DONE' and receipt['verified_groups']==14 and receipt['module_variants']==42
    groups=[g for g in status['groups'] if g['state']=='DONE']
    assert len(groups)==14
    for group in groups:
        folder=BASE/'results'/group['dataset']/group['model']
        summary,verified=load(folder/'summary.json'),load(folder/'local_verification.json')
        assert verified['passed'] and verified['summary_sha256']==sha(folder/'summary.json')
        assert verified['samples_verified']==summary['total']==summary['completed']
        assert summary['failed']==0 and len(verified['variants_verified'])==3
    diag=load(BASE/'qwen_repair_bf16_v2/diagnosis.json')
    assert diag['fp16_nonfinite']==6 and diag['bf16_nonfinite']==0
    assert len(diag['fp16'])==len(diag['bf16'])==8
    dtype_audit=load(BASE/'qwen_repair/checkpoint_dtype_audit.json')
    assert dtype_audit['config_dtype']=='bfloat16' and dtype_audit['shards']
    assert all(set(s['tensor_dtypes'])=={'BF16'} for s in dtype_audit['shards'])
    evidence=[]
    for item in diag['fp16']:
        if not item['finite']:
            evidence.append(dict(dataset=item['dataset'],sample_idx=item['sample_idx'],
                                 first_nonfinite_module=next((n for n,v in item['activations'].items() if v and not v['finite']),None)))
    rows=load(ROOT/'outputs/all_methods_recommendations_20260928/visedit_full_rankings.json')
    rows=[r for r in rows if r['target']=='model_pred' and r['dataset'].startswith('mmke') and r['status']=='done' and not r['historical']]
    assert len(rows)==42 and all(r['attribution_scope']=='next_token_argmax' for r in rows)
    qwen=[r for r in rows if r['model']=='qwen2.5-vl-3b']
    assert len(qwen)==6
    for r in qwen:
        assert r['torch_dtype']=='bfloat16' and len(r['contribution_ranking'])==36
        assert set(r['contribution_ranking'])==set(range(36))
    doc=ROOT/'md/Location/ALL_Methods_Recommends_layers.md'
    text=doc.read_text(encoding='utf-8')
    assert '已核验回填 14/14 组' in text and 'Qwen 数值修复' in text
    for heading,end in [('### 6.2.2','### 6.3.1'),('### 6.3.2','## 7.')]:
        section=text.split(heading,1)[1].split(end,1)[0]
        assert '待补' not in section and section.count('（BF16）')==3
    summary=dict(state='DONE',time=datetime.now().astimezone().isoformat(),
                 completed_groups=14,total_groups=14,repaired_groups=2,recomputed_samples=850,
                 module_variants=42,attribution_scope='next_token_argmax',full_response_attribution_completed=False,
                 precision_change='Qwen MMKE: full-cohort FP16 -> BF16; original partial run retained on server',
                 checkpoint_dtype_audit_sha256=sha(BASE/'qwen_repair/checkpoint_dtype_audit.json'),
                 diagnostics=evidence,local_backfill_verified=True,
                 server_finished_at=status['repair_worker']['time'],documents=receipt['documents'])
    save(BASE/'finalizer_status.json',summary)
    save(BASE/'qwen_repair/completion_audit.json',summary)
    lines=['# VisEdit 首预测位置对照：补算完成','',
           f"服务器完成时间：{summary['server_finished_at']}。本地复算与回填已通过，14/14 组、42 个模块版本全部完成。",'',
           '- 本次补算 Qwen × MMKE-visual：214/214，失败 0；Qwen × MMKE-entity：636/636，失败 0。',
           '- 根因验证：原 auto 加载器固定使用 FP16；8 个诊断样本中，6 个历史失败样本均复现非有限输出。模型原生 BF16 下 8/8 通过。',
           '- 权重文件头核验：Qwen 两个 safetensors 分片的 824 个权重张量均为 BF16（含视觉编码器 390 个张量），与模型配置一致。',
           '- 两组均按 BF16 全量重算，没有混用原 FP16 的部分成功样本；精度可能改变预测与贡献度数值，表格已单独标注。',
           '- 数据、提示词、贡献度公式和 Pre 候选规则沿用原版。完整输出的哈希、逐样本 p/v、三种排名和 Pre 已本地复算核验。',
           '- 当前结果是 model_pred-NextTokenArgmax 首预测位置对照；完整 model_pred 回答逐 token 贡献度尚未执行。',
           '- 修复诊断第一版因检查超大词表张量触发 INT_MAX 索引限制而退出；第二版只检查实际计分预测位置的 logits，保留原始诊断日志。',
           '- 原始 FP16 部分结果和诊断第一版均保留于服务器；正式修复来源为 qwen_repair_bf16_v2/results。',
           '- g09 MiniGPT4 L8 及已停止的 LGA 队列未改动；GPU 通过共享项目锁使用，结束后自动释放。','',
           '本地 Qwen 逐样本文件以 samples.json.gz 保存（gzip JSON：文件名到原始 JSON 字节的 base64 映射），summary.json 记录压缩包及每条原始记录的哈希。',
           '证据：completion_receipt.json、qwen_repair/completion_audit.json、qwen_repair_bf16_v2/diagnosis.json 和各组 local_verification.json。','']
    (BASE/'STATUS_20260929.md').write_text('\n'.join(lines),encoding='utf-8')
    handoff=BASE/'HANDOFF.md'
    old=handoff.read_text(encoding='utf-8')
    marker='## 最新完成记录：Qwen BF16 全量修复'
    if marker not in old:
        prefix=marker+'\n\n'+ '\n'.join(lines[2:])+'\n\n以下为历史执行记录，进度、进程号与等待安排以本节和最新状态文件为准。\n\n---\n\n'
        handoff.write_text(prefix+old,encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    main()
