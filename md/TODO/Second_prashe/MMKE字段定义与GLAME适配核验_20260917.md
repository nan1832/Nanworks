# MMKE字段定义与GLAME适配核验（2026-09-17）

## 1. 核验范围和一手来源

本记录用于补充P1中四个问题：`pred`的真实语义、Portability的一跳认定、508/128是否按连通分量划分完毕，以及GLAME的数据条件能否直接复制到MMKE-Entity。

一手来源：

- [MMKE-Bench论文（ICLR 2025）](https://arxiv.org/pdf/2502.19870)
- [MMKE-Bench官方仓库](https://github.com/MMKE-Bench-ICLR/MMKE-Bench)，本次核验提交：`d34455ae621ff587795eae1b562c5f37a3b626d9`
- [MMKE-Bench官方Hugging Face数据页](https://huggingface.co/datasets/kailinjiang/MMKE-Bench-dataset)
- [GLAME论文（EMNLP 2024）](https://aclanthology.org/2024.emnlp-main.1261.pdf)
- [GLAME官方仓库](https://github.com/Acruxos/GLAME)，本次核验提交：`393658abe2e0101fcd73e03f76fdc6ad2b999f7a`

下载的只读源码和GLAME数据压缩包保存在`phase2_p1/references`。它们只作来源核验，不进入训练。

## 2. MMKE字段结论

### 2.1 `pred`

结论：`pred`是**编辑前的原始/旧知识描述**，不是本项目运行BLIP2后生成的预测，也不是`model_pred`。

证据链：

1. MMKE论文第4节说明，数据先收集原始知识，再通过反事实修改生成编辑知识；视觉实体和视觉语义任务同时修改原图和原描述。
2. 官方数据首条中，`pred`为Steve Austin的原始描述，`alt`为反事实修改后的目标描述。
3. 官方`KE/src/data/mmkb_dataset.py`把`pred`原样读入，并构造：

   ```text
   pred >> alt || src
   ```

   同一loader把`alt`作为`target`。这明确表示`pred`是旧侧知识、`alt`是新侧知识。
4. 第一阶段真实EVQA loader不读取`pred`，而是把完整`alt`作为编辑目标。因此`pred`的官方用途与第一阶段实际用途必须分别记录。

剩余缺口仅是制作溯源：官方论文说明描述由LLM辅助生成并经人工检查，但仓库没有给出每条`pred`具体使用的模型版本、提示词和人工修订记录。这不再影响字段语义判断。

### 2.2 `alt`

`alt`是编辑后的完整自由文本目标描述，可能同时修改实体识别、地点、类别、年代、行为等多个事实。它不是标准的单一`(subject, relation, object)`记录。

`alt`第一句通常包含自然语言实体名，但不能直接当作经过验证的主体QID。原因是：

- 没有Wikidata QID；
- 没有关系P-ID；
- 单条`alt`可能包含多个被修改的事实；
- 实体别名和同名实体需要消歧；
- `image`中的视觉实体、`pred`描述的旧知识主体和`alt`中的反事实目标必须分别辨认。

### 2.3 `model_pred`

`model_pred`不在MMKE官方JSON中。它是本项目Ours定位阶段调用模型生成后保存的旧侧输出缓存，与官方`pred`不是同一字段。

## 3. Portability一跳结论

官方train 636/636、eval 955/955均包含：

```json
{
  "port_type": "1-hop",
  "Q&A": {
    "Question": "...",
    "Answer": "..."
  }
}
```

MMKE论文说明，视觉实体Portability先围绕编辑内容形成一个相关问题，再利用Wikipedia补充信息形成最终问题；官方loader用运行参数`hop=1`映射到`port_type="1-hop"`并选择该问答。因此本项目按官方定义将其记为**1-hop**。

数据没有额外保存中间推理链或逐步三元组。这不是数据损坏，也不阻止P1判定Portability结构可用。若后续研究需要显式路径，那是第二阶段新增的图谱构建产物，不能写成MMKE原生字段。

Portability仍保持评测专用：不用于训练、开发集分组、实体链接或子图构建。兼容格式丢失`port_new`时，只能通过稳定sample ID从官方记录恢复。

## 4. 508/128是否已经按连通分量划分

是，但范围必须写完整：**已经按当前可核验的图片身份连通分量划分完毕**。

重新读取`candidate_split_manifest.json`逐组检查结果：

| 检查项 | 结果 |
|---|---:|
| 官方train样本 | 636 |
| 图片连通分量 | 417 |
| 覆盖的分量成员 | 636 |
| 被拆到两侧的连通分量 | 0 |
| dev_train | 508 |
| dev_val | 128 |

当前图的连接身份为`image`、`image_rephrase`、`m_loc`的路径和文件内容哈希。同一连通分量被整体分配到一侧，所以图片身份互斥已经完成。

候选状态仍为`CANDIDATE_NOT_ACCEPTED`，原因不是连通分量算法没有执行完，而是当前连通图尚未加入可靠主体实体ID和编辑事实根ID；这两项重叠状态仍为`null`。

## 5. GLAME的数据为什么没有遇到同样的ID问题

GLAME不是在任意自由文本上解决实体发现，而是选择了原生具有Wikidata结构的数据：CounterFact、CounterFactPlus和MQuAKE。

GLAME仓库中的实际数据结构如下。

### 5.1 CounterFact/CounterFactPlus

每条记录有`case_id`，编辑请求包含：

```json
{
  "subject": "Danielle Darrieux",
  "relation_id": "P103",
  "target_true": {"str": "French", "id": "Q150"},
  "target_new": {"str": "English", "id": "Q1860"}
}
```

主体在该请求中是文本标签，但GLAME采样的是新目标实体`target_new.id`的Wikidata邻居，因此现成的Q-ID已经满足其入口需要。

### 5.2 MQuAKE

除`case_id`和`requested_rewrite`外，记录直接包含Q-ID/P-ID三元组：

```json
{
  "triples": [["Q72077", "P27", "Q30"], ["Q30", "P35", "Q22686"]],
  "new_triples": [["Q72077", "P27", "Q224"], ["Q224", "P35", "Q3176299"]],
  "edit_triples": [["Q72077", "P27", "Q224"]]
}
```

因此GLAME可以直接知道编辑事实、关系、新旧对象和多跳链。

### 5.3 GLAME图采样入口

官方`wikidata_tools/extract_subgraph.py`直接读取：

```python
target_id = rewrite["target_new"]["id"]
target_neighbors = get_entity_triplets(target_id, target_label)
```

随后通过Wikidata SPARQL查询该Q-ID的出边。论文附录也明确说明：所用数据集直接由Wikidata构造，每个编辑实体已有对应Wikidata item ID，因此能够精确采样。

GLAME论文同时将以下情况列为限制：非结构化编辑或没有显式KG关联时，需要额外实体抽取算法或工具来识别关键实体。这正是MMKE自由文本适配当前要补的步骤。

## 6. MMKE与GLAME的直接对照

| 条件 | GLAME所用数据 | MMKE-Entity |
|---|---|---|
| 稳定记录ID | 有`case_id` | 官方无`sample_id/id/case_id`，本项目只能派生稳定ID |
| 编辑表示 | 单个或明确列出的三元组 | 自由文本描述，可能一次改变多个事实 |
| 关系ID | 有Wikidata P-ID | 无 |
| 新旧对象ID | 有Wikidata Q-ID | 无 |
| 多跳链 | MQuAKE有原/新QID三元组链 | `port_new`只有一跳标签和最终QA |
| 图采样种子 | 直接使用`target_new.id` | 需要先做实体识别、链接和消歧 |
| 图像身份 | 不涉及图像 | 有`image/image_rephrase/m_loc`，需要额外防止图片跨集合 |

因此，GLAME已经解决的是“给定可靠Q-ID以后如何采样、编码并注入相关子图”。它没有解决MMKE当前的“从多模态自由文本记录中得到可靠Q-ID和事实根”问题。

## 7. 哪些可以复用，哪些不能照抄

可以复用：

- 以新目标实体为种子查询Wikidata出边；
- 关系标签和实体标签规范化；
- 邻居排序、限制子图阶数和最大节点数；
- 将`(subject, relation, target)`三元组构造成图；
- RGCN/图编码及其消融设计；
- 图查询缓存、`case_id`式稳定样本对齐和失败状态记录。

不能直接照抄：

- 用`target_new.id`直接查询：MMKE没有这个字段；
- 假定每条样本只有一个事实根：MMKE的`alt`可能修改多个事实；
- 假定主体、关系和新旧对象已结构化；
- 按行号将样本与子图ZIP对应；MMKE已有历史删行，必须使用稳定sample ID；
- 用Portability答案反推实体或路径；P1已冻结其评测专用用途；
- 忽略图像身份重叠；GLAME是纯文本LLM编辑，没有这个约束。

## 8. 对当前P1/P2的实际影响

1. `pred`字段语义核验完成；只保留逐记录生成溯源缺口。
2. Portability按官方定义确认为1-hop；显式推理链不存在，不再作为P1阻塞项。
3. 508/128已按图片连通分量完整划分；当前未验收仅因主体/事实身份未加入连通图。
4. MMKE缺少的是结构化编辑身份：稳定主体/目标实体Q-ID、关系P-ID和事实根ID，而不仅是“某个编辑目标没有ID”。
5. 进入P2时可参考GLAME建立单独的实体链接与图缓存层，但必须先为MMKE设计自由文本到结构化编辑请求的转换和人工/规则复核机制。
6. 在该转换完成前，不能把GLAME的成功当作MMKE dev已证明主体/事实无泄漏，也不能把当前508/128候选改名为已验收划分。
