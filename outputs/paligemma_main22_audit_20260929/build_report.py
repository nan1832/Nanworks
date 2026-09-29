"""Create a local evidence report; never change the existing result ledger."""
import hashlib,json,pathlib,tarfile

out=pathlib.Path(__file__).resolve().parent
root=out.parents[1]
audit=json.loads((out/'target22_verification.json').read_text(encoding='utf-8'))
ledger=json.loads((root/'outputs/sweep_ledger_20260928/ledger.json').read_text(encoding='utf-8'))
historical={(r['dataset'],r['layer']):r for r in ledger['rows'] if r['model']=='paligemma-3b' and r['recipe']=='main' and r['training']=='历史验收'}
assert len(historical)==len(audit['rows'])==22
assert set(historical)=={(r['dataset'],r['layer']) for r in audit['rows']}
for r in audit['rows']:
    assert all(p['exists'] and p['file_count']==0 and not p['errors'] for p in r['paths'])
for name in ['search_login01.json','search_g09.json','search_g08.json','alternates_login01.json','alternates_g09.json','alternates_g08.json']:
    assert not json.loads((out/name).read_text(encoding='utf-8'))['errors'],name

archive_checks=[]
for rel in ['server_results/live_backfill/recovered_g09_nodefail_20260810/structured_results.tar.gz','server_results/g09r/flat/flat.tar.gz']:
    p=root/rel
    with tarfile.open(p,'r:*') as tf:
        matches=[{'name':m.name,'size':m.size} for m in tf if any(s in m.name.lower() for s in ['paligemma','3044208','followup'])]
    archive_checks.append({'path':rel,'matches':matches,'note':'匹配文件仅涉及MMKE-entity L4（不属于本次22层），或无匹配文件。'})
(out/'local_archive_checks.json').write_text(json.dumps(archive_checks,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

rows=[]
for r in audit['rows']:
    h=historical[(r['dataset'],r['layer'])]
    rows.append(dict(dataset=r['dataset'],layer=r['layer'],recipe='main',
        historical_selected_epoch=h['epoch'],historical_ema=h['ema_loss'],historical_average=h['metrics']['Average'],
        historical_status=h['original_status'],historical_training_complete_50_epochs=None,
        historical_minimum_ema_selection_verified=None,
        current_source_file_count=sum(p['file_count'] for p in r['paths']),
        current_recoverable_checkpoint_found=False,verification_status='ORIGINAL_ARTIFACTS_NOT_FOUND',
        needs_retraining_if_no_other_backup=True,reason='在本次核验范围未找到原始训练、选点、权重与逐样本评测文件；无法重验50轮或直接恢复训练。',
        audited_paths=[p['path'] for p in r['paths']]))
summary={'verified_at_server_time':audit['server_time'],'scope':'22 historical main records only',
    'remote_actions':'read-only; no training, evaluation, deletion, copying, or remote file writes',
    'count':22,'complete_original_artifact_sets_found':0,'proven_historical_incomplete_count':0,
    'requires_new_training_and_evaluation_if_no_backup':22,
    'meaning':'产物缺失不等于证明当时未满50轮。严格可复核协议下须恢复完整备份，无法恢复则重新训练评测。',
    'rows':rows}
(out/'audit_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

lines=['# PaliGemma 22个历史 main 层：原件与重训必要性核验','',
    '**服务器核验时间：'+audit['server_time']+'（北京时间）。**','',
    '结论：本次22层均未找回可核验的原始训练/选点/权重/逐样本评测产物。若正式实验要求“main协议、完整50轮、同一run最低有效EMA选点、可复核完整评测”，在没有其他可恢复备份的条件下，这22层均需要重新训练并评测。', '',
    '**这不是确认它们当时没训练满50轮。** 历史台账仍保留TRAIN_DONE及分数；本次确认的是当前可访问原件不足以重验训练完成与最低EMA，也未找到可直接续训的checkpoint。历史记录与分数未被删除或改写。','',
    '## 逐层结果','',
    '以下checkpoint epoch、EMA、Average来自历史台账，仅用于识别旧运行，不代表本次重新验证了这些值。','',
    '| 数据集 | 层 | 历史selected epoch | 历史EMA | 历史Average | 当前归档文件数 | 结论 |',
    '|---|---:|---:|---:|---:|---:|---|']
for r in rows:
    lines.append('| %s | L%d | %d | %.6f | %.3f | 0 | 无其他备份则重训重评 |'%(r['dataset'],r['layer'],r['historical_selected_epoch'],r['historical_ema'],r['historical_average']))
lines += ['', 'EVQA共7层：L1、L4、L5、L6、L7、L8、L17。',
    'MMKE-entity共15层：L0、L1、L2、L3、L5、L6、L7、L8、L9、L10、L11、L12、L13、L16、L17。','',
    '## 证据与搜索范围','',
    '1. 对上述22层逐一递归读取原共享归档目录，23个候选层目录（MMKE-entity L16另查rollback补跑目录）均存在，但层目录内文件数均为0，无权限/遍历错误。见 [逐层原始检查](target22_verification.json)。',
    '2. 两组2026-08-10归档均明确登记MOVED_METADATA_ONLY，ARCHIVE_MANIFEST.txt记录completed_layers_verified=0。该字段说明当次归档未验收完整层，不能用作训练失败次数。原始文本见 [归档清单](manifests.json)。',
    '3. 搜索login01共享server_results、项目records、/var/tmp/ph_teacher3，以及项目其他目录（含VisEdit-main、eval_results）；搜索G08/G09的用户临时目录及用户拥有的其他临时目录。未发现这22层的替代原件。排除可重建cache、模型与数据集等无关目录；没有扫描其他用户的数据。见 search_*.json 与 alternates_*.json。',
    '4. 本地结构化备份structured_results.tar.gz和flat.tar.gz没有这22层原件；其中PaliGemma相关有效匹配为MMKE-entity L4，属于此前已验收层。见 [本地压缩包检查](local_archive_checks.json)。',
    '5. 已留存历史Markdown分数不等同于loss_history.csv、selected_checkpoint.tsv、实体checkpoint或逐样本results.json，不能据此生成伪造的50轮验收。','',
    '## 执行边界与后续','',
    '- 本次服务器操作全部只读；未启动训练、续训或评测，未删除或更改服务器文件。仅在本机保存核验脚本、原始返回和报告。',
    '- 本次只审计这22个历史层；不包含已明确中断的MMKE-visual L0/L3/L5、EVQA L9的恢复评测，以及EVQA L14选点异常。',
    '- 若另外找到完整备份，应先恢复/核验，可减少重训数量；本次不声称所有未检查存储都不存在副本。',
    '- 无其他备份时应创建独立main重跑记录，并保留旧历史结果。训练预算完成、数值收敛、选点正确和评测完成分别记录，不以分数高低择优替换旧run。',
    '- MMKE-entity L16历史记录含main-rollback及34次nonfinite安全跳步；如果重新训练，须明确main实现及数值保护版本，不能仅凭YAML名称认定协议一致。','',
    '[机器可读结论](audit_summary.json) · [文件校验清单](SHA256SUMS.json)','']
(out/'PaliGemma_main22核验报告.md').write_text('\n'.join(lines),encoding='utf-8')
hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file() and p.name!='SHA256SUMS.json'}
(out/'SHA256SUMS.json').write_text(json.dumps(hashes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'count':22,'empty_layer_paths':sum(len(r['paths']) for r in audit['rows']),'report':str(out/'PaliGemma_main22核验报告.md')},ensure_ascii=False))
