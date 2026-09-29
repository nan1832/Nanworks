# MMKE-Entity `pred`、`alt` 与图片语义核验

核验日期：2026-09-18

## 确定结论

MMKE-Entity不是要求`alt`保持现实世界事实正确。它把一条原始多模态知识 `k=(i,d)` 改成编辑知识 `k_e=(i_e,d_e)`：

1. 视觉侧把原实体图片替换为同类的另一个实体图片；
2. 文本侧把原实体描述中的关键属性改为反事实内容；
3. 编辑后模型应对`image + src`产生`alt`，并在`image_rephrase`与改写问题上保持该编辑；
4. 评测以数据集给定的`alt`及其派生问答为准，不以现实事实或`pred`为目标。

因此，`alt`里出现现实上错误的信息是基准构造的一部分。它通常不是一段与主体完全无关的随机文字，而是保留主体和描述框架，再有意替换若干关键属性。

## 字段对应

| 字段 | 协议含义 | 本项目实际入口 |
|---|---|---|
| `pred` | 原始、现实知识描述 `d`；固定数据字段，不是具体模型现场预测 | 第一阶段加载器不把它作为训练目标 |
| `alt` | 反事实编辑目标描述 `d_e` | `target_new=d['alt']` |
| `image` | 被替换后的主编辑图片 `i_e` | 与`src`组成可靠性编辑请求 |
| `image_rephrase` | 同一替代视觉实体的另一张图片 | 图像泛化评测，目标仍为`alt` |
| `rephrase` | `src`的文本改写 | 文本泛化评测，目标仍为`alt` |

发布的单条MMKE-Entity JSON没有`original_image`、`pred_image`或“目标主体正确图片”字段。`image`和`image_rephrase`已经是编辑后的替换实体图片；`m_loc`是无关局部性图片，也不是目标主体原图。目标主体的正确图片可能在作者上游收集和数据构造阶段使用过，但没有作为该发布记录的可直接恢复字段保留下来。

第一阶段真实加载代码位于：

```text
dataset/md/TODO/Second_prashe/第一阶段真实代码_BLIP2_MMKE-Entity/code/data/vllm_dataset.py
```

其中第70—78行明确执行：`image + src -> alt`、`image + rephrase -> alt`、`image_rephrase + src -> alt`。

## 论文与官方来源

- ICLR 2025论文第3.1节把知识表示为`k=(i,d)`，并说明视觉实体编辑把它变换为`k_e=(i_e,d_e)`。
- 第3.2节说明视觉实体编辑会把原实体图片替换为同类型另一实体的图片，同时把关键实体信息改成反事实内容。
- 第4.2节再次说明：视觉模态采用同类型实体的随机图片替换；文本模态修改关键实体信息为反事实内容。
- 官方仓库说明该基准以自由文本表示编辑知识，并评测视觉实体、视觉语义和用户知识三类编辑。

来源：

- https://proceedings.iclr.cc/paper_files/paper/2025/file/01fb6de3360f9e32862665580e2c5853-Paper-Conference.pdf
- https://github.com/MMKE-Bench-ICLR/MMKE-Bench
- https://huggingface.co/datasets/kailinjiang/MMKE-Bench-dataset

## 服务器官方train的全量静态核对

核对文件：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_json/entity_train.json
```

其SHA-256为`1c1ed7d25bbcfcf52ba315217970d33b09f36265e5742ef98567a04946b60edc`，共636条。

- 636/636条的`pred`与`alt`不同。
- 636/636条的`alt`都含有“the ... in the image corresponds to <主体>”式主体声明。
- 606/636条的该主体名称逐字出现在`pred`中。
- 剩余30条逐条查看后属于别名、全名/简称、单复数或原始文本省略名称等情况，例如`Erbil Citadel/Citadel of Erbil`、`Steven/Steve McManaman`、`Kenshin Himura/Himura Kenshin`；没有证据表明它们把`alt`主体随机换成无关实体。
- 636条中没有一条的`image`文件主名与`alt`主体标准化后完全相同。这与论文规定的视觉实体替换一致。
- `rel_ans_1`有615/636条可在`alt`中逐字找到，`rel_ans_2`有609/636条可逐字找到；其余主要涉及表述变化。关系问题和答案由编辑目标而来。

## John Stewart样本

官方索引53：

```text
image: entity/Spider-Man+2.jpg
image_rephrase: entity/Spider-Man+11.jpg
pred主体: John Stewart（DC Comics的Green Lantern）
alt主体: John Stewart
```

`alt`将出版方改成Marvel Comics、创作者改成Jack Kirby和Stan Lee、首次登场改成第55期、原型改成Denzel Washington、族裔改成Native American、配音改成Kevin Conroy。这些不是对现实人物/角色的可靠介绍，而是作者有意生成的反事实编辑目标。

### John Stewart字段如何进入第一阶段真实训练和评测

| 用途 | 图片 | 问题 | 目标或比较对象 |
|---|---|---|---|
| 编辑信号/可靠性训练 | `image=Spider-Man+2.jpg` | `src` | `alt`全文 |
| 可靠性评测 | `image=Spider-Man+2.jpg` | `src` | 与`alt`逐token比较 |
| 文本泛化训练与评测 | `image=Spider-Man+2.jpg` | `rephrase` | `alt`全文 |
| 图像泛化训练与评测 | `image_rephrase=Spider-Man+11.jpg` | `src` | `alt`全文 |
| 文本局部性评测 | 无图 | `loc` | 编辑后输出与编辑前输出保持一致 |
| 图像局部性训练与评测 | `m_loc` | `m_loc_q` | 编辑前后输出/分布保持一致；`m_loc_a`用于构造目标长度和掩码 |

第一阶段真实加载器没有读取`pred`作为目标，也没有读取`rel_1/rel_2`、`m_rel_1/m_rel_2`或`port_new`。因此第一阶段已有指标只覆盖可靠性、文本泛化、图像泛化、文本局部性和图像局部性；不能把未接入的关系问答或Portability字段说成已经在第一阶段完成评测。

Q-ID审核应只判断`alt`主体“John Stewart”指的是谁。正确Wikidata实体是：

```text
Q2556873 — John Stewart，DC Comics的虚构超级英雄/Green Lantern
```

自动建议的`Q1393453`是同名美国歌手，属于错误链接。

## 对当前P2人工审核的约束

1. 用`pred`确认主体的原始身份和消歧上下文。
2. 用`alt`第一句确认编辑目标主体名称。
3. 不审核`alt`后续属性是否符合现实；它们按协议就是反事实。
4. 不要求`image/image_rephrase`外观对应目标Q-ID；它们按协议是替换实体图片。
5. 只把“Q-ID链接到了错误的同名实体或错误概念”标为建议错误。
