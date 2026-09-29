# VisEdit 式 Module Output Attribution 高贡献层定位实验手册（修订完整版·补充版）

> 适用范围：`E-VQA / pilot500`、`MMKE-Entity`、`MMKE-Visual`  
> 适用模型：BLIP2-OPT-2.7B、InstructBLIP-Vicuna-7B、MiniGPT-4-Vicuna-7B、LLaVA-v1.5-7B、Qwen2.5-VL-3B-Instruct、PaliGemma-3B、SmolVLM-Instruct-1.7B  
> 主实验名称：`VisEdit-Contrib-Pre-KeyToken`  
> 目标：参考 VisEdit 论文第 3.1 节和官方 `contribution_module.py` / `p_track.py` 的实现，计算 VLLM 解码器各层 Attention / MLP 输出对任务相关 key token 的贡献度，识别高贡献区域，并按照 VisEdit-style 前置插入规则生成 Top-3 / Top-5 adapter 候选层。

---

## 修订核心说明

当前已经完成的 `alt` 第一个 token 贡献度结果可以保留为诊断实验，但不能直接作为最终主基线。原因是：

```text
key_mode = "alt"
predict_word = " " + target_new.strip()
predict_id = tokenizer(predict_word, add_special_tokens=False).input_ids[0]
```

该写法实际计算的是 `alt / target_new` 经 tokenizer 后的第一个 token 的贡献度，而不是一定代表编辑知识的 key token。

对三个数据集的影响不同：

| 数据集 | `alt` 第一个 token 是否基本可用 | 原因 |
|---|---:|---|
| E-VQA / pilot500 | 基本可用 | `alt` 多为短答案，例如 `yes`、`no`、`banana`、`red`，第一个 token 通常就是答案核心 token |
| MMKE-Entity | 不够可用 | `alt` 多为自由长句，句首可能是 `The`、`A`、`This` 等功能词或模板词 |
| MMKE-Visual | 不够可用 | `alt` 多为解释性长句，句首可能是 `This`、`The`、`It` 等功能词或模板词 |

因此本文主实验不再使用盲目的 `AltFirstToken` 作为 MMKE 的主 key token，而是使用 dataset-specific key-token extraction。

实验命名边界如下：

| 实验名 | 含义 | 是否进入主定位表 |
|---|---|---:|
| `VisEdit-Contrib-Diagnostic-AltFirstToken` | 直接取 `alt` 的第一个 tokenizer token，保留当前已跑结果 | 否 |
| `VisEdit-Contrib-Direct-KeyToken` | 使用数据集专用 key token，直接按贡献度排序 | 附加分析 |
| `VisEdit-Contrib-Pre-KeyToken` | 使用数据集专用 key token，识别高贡献区并取前置层 | 是 |
| `VisEdit-Contrib-Direct-PredToken` | 使用 `pred` 或 `model_pred` 的 key token 分析旧答案支持 | 诊断 |
| `VisEdit-Contrib-Delta-KeyToken` | `target key token` 分数减 `old key token` 分数 | 诊断 / 消融 |
| `VisEdit-Contrib-AltSeq` | 完整 `alt` 序列逐 token teacher-forcing 平均贡献度 | 消融，不替代主基线 |

---

## 本次补充说明

本补充版在原手册基础上进一步加入以下正式运行约束，专门用于将 `MMKE-Entity` 与 `MMKE-Visual` 在 7 个模型上的 key-token 补充实验升级为可进入主表的 `VisEdit-Contrib-Pre-KeyToken` 主基线：

1. 增加 key-token manifest 的人工抽查步骤，防止 MMKE 长答案中抽到 `The`、`This`、`human`、`image` 等模板词；
2. 增加有效 key-token 覆盖率门槛，低覆盖率组合不得直接进入主结果；
3. 固定 MMKE-Entity 与 MMKE-Visual 的 key-token 优先级，避免不同字段混入同一主排序；
4. 增加跨模型 tokenizer 切分记录，保留 key phrase 与实际使用 subtoken 的对应关系；
5. 明确旧的 `AltFirstToken` 结果只能作为诊断结果，新跑的 `VisEdit-Contrib-Pre-KeyToken` 才进入主定位表；
6. 增加正式运行顺序、异常检查项和结果回填规则。

---

# 1. 贡献度到底衡量什么

VisEdit 第 3.1 节计算的是：

> 每一层 Attention 输出和 MLP 输出对某个 key token 的 next-token prediction 贡献度。

也就是说，对于一个图像-文本输入：

```text
image + prompt  ->  预测下一个 token
```

我们不让模型完整生成答案，而是让输入停在答案前一个位置，分析模型下一步要预测某个 key token 时，各层 Attention / MLP 模块输出对该 key token 的支持程度。

例如 E-VQA 样本：

```json
{
  "src": "Is it sunny?",
  "pred": "no",
  "alt": "yes",
  "image": "proxy/val2014/COCO_val2014_000000393513.jpg"
}
```

构造输入：

```text
Is it sunny? The answer is:
```

选择 key token：

```text
yes
```

计算每一层 Attention / MLP 输出对 `yes` 的贡献度。

注意：

1. 贡献度高不等于真实编辑效果最好；
2. 贡献度高说明该层对 key token 预测有更强直接支持；
3. VisEdit-style 主规则不是直接选贡献最高层挂 adapter，而是识别高贡献区，再取高贡献区之前的层作为 adapter 候选层；
4. 对 MMKE 这类自由长文本数据，必须先抽取真正的知识 key token，不能盲取 `alt` 首 token。

---

# 2. 数据集字段与评价指标映射

## 2.1 统一编辑样本表示

三类数据集统一表示为：

\[
(x_i^v, x_i^t, y_i^{new}, y_i^{old})
\]

| 符号 | 原始字段 | 含义 |
|---|---|---|
| \(x_i^v\) | `image` | 编辑图像 |
| \(x_i^t\) | `src` / prompt | 编辑问题或描述 |
| \(y_i^{new}\) | `alt` / `target_new` | 编辑后希望模型输出的新知识 |
| \(y_i^{old}\) | `pred` 或 `model_pred` | 编辑前旧知识或冻结基础模型当前输出 |

其中：

- `alt` 是所有目标相关方法的新知识来源；
- `pred` 是数据集提供的旧知识，不一定等于某个特定 VLLM 的实时输出；
- `model_pred` 是冻结基础模型在当前图像与问题上的确定性生成结果，应预先缓存；
- VisEdit 主实验只需要一个代表 `alt` 的 key token，不需要完整 `alt` 序列。

## 2.2 E-VQA / pilot500

E-VQA 是视觉问答编辑任务。目标是让 VLLM 在给定图像和问题下输出编辑后的短答案。

| 字段 | 含义 | 评价作用 |
|---|---|---|
| `image` | 编辑图像 | Reliability |
| `src` | 原始 VQA 问题 | Reliability |
| `alt` | 编辑后目标答案，通常很短 | 目标 key token 来源 |
| `pred` | 数据集提供的旧答案 | 旧答案诊断 |
| `rephrase` | 文本改写问题 | T-Gen |
| `image_rephrase` | 图像改写样本 | M-Gen |
| `loc`, `loc_ans` | 无关文本问题与答案 | T-Loc |
| `m_loc`, `m_loc_q`, `m_loc_a` | 无关图像、问题与答案 | M-Loc |

主 key token：

```text
E-VQA 主 key token = alt 的第一个有效内容 token
```

示例：

| `alt` | key token |
|---|---|
| `yes` | `yes` |
| `no` | `no` |
| `banana` | `banana` |
| `red` | `red` |

## 2.3 MMKE-Entity

MMKE-Entity 是实体级视觉知识编辑。它围绕图像中的实体修改相关事实，`alt` 通常是长段反事实实体描述。

| 字段 | 含义 | 评价作用 |
|---|---|---|
| `knowledge_type` | 通常为 `entity_level` | 标识实体级知识编辑 |
| `type_self` | 实体类型，例如 `human` | 细粒度实体类别 |
| `image` | 编辑实体图像 | Reliability |
| `src` | 编辑问题 | Reliability |
| `rephrase` | 文本改写问题 | T-Gen |
| `image_rephrase` | 同实体或同类实体改写图像 | M-Gen |
| `pred` | 编辑前实体知识描述 | 旧知识诊断 |
| `alt` | 编辑后目标实体知识，通常为反事实描述 | 主目标知识来源 |
| `loc`, `loc_ans` | 无关文本问答 | T-Loc |
| `m_loc`, `m_loc_q`, `m_loc_a` | 无关图像问答 | M-Loc |
| `rel_1`, `rel_2` | 与编辑后实体知识相关的文本问题 | Reliability / relation check |
| `rel_ans_1`, `rel_ans_2` | 对应编辑后答案 | 关系 key token 诊断 |
| `m_rel_1`, `m_rel_2` | 带图像实体指代的多模态问题 | Multimodal reliability |
| `m_rel_ans_1`, `m_rel_ans_2` | 对应编辑后答案 | 多模态关系 key token 诊断 |
| `port_new` | 基于编辑后知识的一跳推理问答 | Portability |

主 key token：

```text
MMKE-Entity 主 key token = alt 中第一个非模板、非功能词的实体/事实锚点 token
```

示例：

```json
{
  "alt": "The human in the image corresponds to Stone Cold Steve Austin. Steve Austin ...",
  "rel_ans_1": "Steven Jay Smith",
  "rel_ans_2": "New Japan Pro-Wrestling (NJPW)",
  "m_rel_ans_2": "Hiroshi Tanahashi"
}
```

| 目标 | key token |
|---|---|
| 主实体锚点 | `Stone` 或 `Steve` |
| birth name 诊断 | `Steven` |
| 组织关系诊断 | `New` / `Japan` / `NJPW` |
| 对手关系诊断 | `Hiroshi` |

主表只使用统一主规则，不把 `rel_ans_*` 与 `m_rel_ans_*` 混入同一个主排序；这些字段只用于诊断或消融。

## 2.4 MMKE-Visual

MMKE-Visual 是视觉语义知识编辑。目标不是编辑具体实体身份，而是编辑视觉语义、动作、手势、属性、关系或规则的含义。

| 字段 | 含义 | 评价作用 |
|---|---|---|
| `knowledge_type` | 通常为 `visual_knowledge` | 标识视觉语义知识编辑 |
| `type_self` | 视觉语义子类，例如 `life_gesture` | 细粒度语义类别 |
| `image` | 编辑图像 | Reliability |
| `src` | 编辑问题 | Reliability |
| `rephrase` | 文本改写问题 | T-Gen |
| `image_rephrase` | 视觉改写图像 | M-Gen |
| `image_rephrase_question` | 图像改写问题 | M-Gen |
| `pred` | 原始旧知识，可能为空 | 旧知识诊断 |
| `alt` | 编辑后目标视觉语义描述 | 目标知识来源 |
| `loc`, `loc_ans` | 无关文本问答 | T-Loc |
| `m_loc`, `m_loc_q`, `m_loc_a` | 无关图像问答 | M-Loc |
| `rel`, `rel_ans` | 编辑知识相关文本问答 | Reliability / relation check |
| `m_rel`, `m_rel_ans` | 图像语义相关多模态问答 | Multimodal reliability |
| `one_hop_img` | 一跳推理图像 | Portability 辅助图像 |
| `port_new` | 一跳推理问答 | Portability |

主 key token：

```text
MMKE-Visual 主 key token = m_rel_ans 的第一个内容 token；若无 m_rel_ans，则使用 rel_ans；若仍无，则从 alt 中抽取视觉语义锚点。
```

示例：

```json
{
  "alt": "This is the prayer gesture in life gestures. It involves clasping both hands together ...",
  "rel_ans": "Temples",
  "m_rel_ans": "Prayer or blessing"
}
```

| 字段来源 | key token |
|---|---|
| `m_rel_ans = Prayer or blessing` | `Prayer` |
| `rel_ans = Temples` | `Temples` |
| `alt = This is the prayer gesture ...` | `prayer` |

---

# 3. Key token 模式与主实验规则

## 3.1 模式定义

| 模式 | `predict_word` 来源 | 用途 | 是否主实验 |
|---|---|---|---:|
| `model_pred` | `None`，使用模型 top-1 next token | 复现 VisEdit 官方默认贡献图 | 否 |
| `alt_first_token` | `" " + alt.strip()` 的第一个 tokenizer token | 保留当前已跑诊断结果 | 否 |
| `dataset_key_token` | 按数据集规则抽取知识 key token | 主实验 | 是 |
| `pred_token` | `pred` 或 `model_pred` 的关键 token | 旧知识支持诊断 | 否 |
| `rel_ans_token` | `rel_ans*` 或 `m_rel_ans*` | 关系/多模态诊断 | 否 |
| `alt_seq` | 完整 `alt` 逐 token teacher-forcing | 消融 | 否 |

主实验固定：

```text
key_mode = dataset_key_token
method = VisEdit-Contrib-Pre-KeyToken
rank_metric = score_positive_key_token
candidate_conversion = pre_before_high_contribution_region
```

## 3.2 功能词与模板词过滤表

以下 token 不可作为 MMKE 主 key token，除非没有任何替代并且必须标记 `generic_key_token=true`：

```text
the, a, an, this, that, these, those, it, there,
human, person, people, man, woman, image, picture, photo, depicted, shown,
corresponds, correspond, called, named, is, are, was, were,
in, on, of, to, with, and, or, as, for, about, usually, commonly,
gesture, life, visual, object, thing
```

注意：

- 过滤只用于选择 key token，不修改原始 `alt`；
- 大小写归一化仅用于判断是否为功能词，实际 `key_token_text` 保留原始大小写；
- 对 tokenizer 加 leading space 时，应同时保存原始 `key_token_text` 和实际 `predict_word`。

## 3.3 Dataset-specific key token 抽取伪代码

```python
GENERIC_WORDS = {
    "the", "a", "an", "this", "that", "these", "those", "it", "there",
    "human", "person", "people", "man", "woman", "image", "picture", "photo",
    "depicted", "shown", "corresponds", "correspond", "called", "named",
    "is", "are", "was", "were", "in", "on", "of", "to", "with", "and", "or",
    "as", "for", "about", "usually", "commonly", "gesture", "life", "visual",
    "object", "thing"
}

TEMPLATE_PHRASES_ENTITY = [
    "the human in the image corresponds to",
    "the person in the image corresponds to",
    "the human in the picture corresponds to",
    "the person in the picture corresponds to",
    "the image shows",
    "the picture shows"
]

TEMPLATE_PHRASES_VISUAL = [
    "this is the",
    "this is a",
    "this is an",
    "the image shows",
    "the picture shows",
    "it usually signifies",
    "it means"
]


def first_content_word(text):
    # 实现时可先用简单英文分词，也可用 tokenizer 反查；主要求是跳过功能词和标点
    words = basic_word_tokenize(text)
    for w in words:
        w_norm = normalize_word(w)
        if not w_norm:
            continue
        if w_norm not in GENERIC_WORDS:
            return w
    return words[0] if words else None


def strip_template(text, templates):
    low = text.lower().strip()
    for t in templates:
        if low.startswith(t):
            return text[len(t):].strip(" :,.\n\t")
    return text


def extract_entity_anchor_from_alt(alt):
    text = strip_template(alt, TEMPLATE_PHRASES_ENTITY)
    return first_content_word(text)


def extract_visual_semantic_anchor_from_alt(alt):
    text = strip_template(alt, TEMPLATE_PHRASES_VISUAL)
    return first_content_word(text)


def extract_visedit_key_token(sample, dataset_name):
    if dataset_name in ["E-VQA", "pilot500", "E-VQA/pilot500"]:
        return first_content_word(sample["alt"]), "alt_short_answer"

    if dataset_name == "MMKE-Entity":
        token = extract_entity_anchor_from_alt(sample.get("alt", ""))
        if token and normalize_word(token) not in GENERIC_WORDS:
            return token, "alt_entity_anchor"

        for field in ["rel_ans_1", "rel_ans_2", "m_rel_ans_1", "m_rel_ans_2"]:
            if sample.get(field):
                return first_content_word(sample[field]), field

        return first_content_word(sample.get("alt", "")), "alt_first_content_or_generic"

    if dataset_name == "MMKE-Visual":
        for field in ["m_rel_ans", "rel_ans"]:
            if sample.get(field):
                token = first_content_word(sample[field])
                if token:
                    return token, field

        token = extract_visual_semantic_anchor_from_alt(sample.get("alt", ""))
        if token:
            return token, "alt_visual_semantic_anchor"

        return first_content_word(sample.get("alt", "")), "alt_first_content_or_generic"

    raise ValueError(dataset_name)
```

## 3.4 Leading space 与 tokenization 规则

多数 OPT / LLaMA / Vicuna / Qwen / Gemma 类 tokenizer 对句中词和句首词编码不同。例如：

```python
tokenizer(" yes", add_special_tokens=False).input_ids
tokenizer("yes", add_special_tokens=False).input_ids
```

主实验要求：

```text
predict_word = leading_space + key_token_text
```

其中 `leading_space` 由模型 tokenizer 与 prompt 模板决定。默认：

```text
leading_space = true
```

但必须保存诊断字段：

```text
key_token_text
predict_word
key_token_id
key_token_position
leading_space
tokenizer_decoded_key_token
target_answer_token_ids
```

如果 `predict_word` 被 tokenizer 切成多个 token，主实验取第一个 token，并保存：

```text
key_token_subtoken_ids
used_subtoken_index = 0
```

## 3.5 Generic key token 处理

如果最终抽到的 key token 属于功能词或模板词，标记：

```text
generic_key_token = true
```

主实验默认处理：

```text
若 generic_key_token=true，样本不进入主贡献度平均；保留在诊断文件中。
```

如果某个数据集/模型过滤后有效样本数过少，记录：

```text
status = low_valid_key_token_coverage
```

建议阈值：

```text
min_valid_samples = 100  # E-VQA pilot500 可用
min_valid_ratio = 0.7
```

对于 MMKE 如果训练集规模较小，可将 `min_valid_samples` 按数据集实际规模调整，但必须在 `config.json` 记录。

---

## 3.6 Key-token 人工抽查与有效覆盖率门槛

在正式运行 7 模型之前，必须先只生成 `key_token_manifest.csv`，并进行人工抽查。

### 3.6.1 人工抽查

每个数据集至少随机抽查：

```text
50 samples per dataset
```

对于样本数较小的数据集，可抽查：

```text
min(50, 20% of total samples)
```

抽查内容包括：

```text
key_token_text 是否是真正的实体 / 事实 / 视觉语义锚点
key_token_source 是否符合数据集规则
generic_key_token 是否正确
predict_word 是否符合当前模型 tokenizer 的句中词写法
key_token_id 是否非空
tokenizer_decoded_key_token 是否与 key_token_text 语义一致
```

若人工抽查发现明显错误 token 的比例超过：

```text
manual_error_ratio > 10%
```

则不得直接运行贡献度计算，必须先修正 key-token 抽取规则并重新生成 manifest。

### 3.6.2 有效覆盖率

每个 `dataset × model` 组合必须统计：

```text
total_sample_count
valid_key_token_count
generic_key_token_count
generic_key_token_ratio
used_in_main_score_count
used_in_main_score_ratio
manual_checked_count
manual_error_count
manual_error_ratio
```

主实验默认门槛：

```text
min_valid_ratio = 0.70
min_valid_samples = 100
manual_error_ratio <= 0.10
```

如果 MMKE 的训练集规模较小，可将 `min_valid_samples` 调整为：

```text
min_valid_samples = min(100, 0.7 × total_sample_count)
```

但必须在 `config.json` 中记录。

若不满足覆盖率要求，结果只能标记为：

```text
status = low_valid_key_token_coverage
```

不得作为正常 `VisEdit-Contrib-Pre-KeyToken` 主结果进入主表。

## 3.7 MMKE key-token 优先级细化

### 3.7.1 MMKE-Entity

`MMKE-Entity` 主实验必须优先使用 `alt` 中的编辑后实体或事实锚点，不能让 `rel_ans_*` 抢先替代主目标。固定优先级如下：

```text
Priority 1: strip alt template → extract edited entity / factual anchor token
Priority 2: if Priority 1 fails, use rel_ans_1 / rel_ans_2 / m_rel_ans_1 / m_rel_ans_2 as diagnostic fallback
Priority 3: if still fails, exclude the sample from main average and keep it in diagnostics
```

因此，`rel_ans_*` 与 `m_rel_ans_*` 只能作为 fallback 或诊断来源，不得与 `alt_entity_anchor` 混在一起形成不可解释的主排序。

推荐字段：

```text
key_token_source = alt_entity_anchor
key_token_source = rel_ans_1_fallback
key_token_source = rel_ans_2_fallback
key_token_source = m_rel_ans_1_fallback
key_token_source = m_rel_ans_2_fallback
key_token_source = excluded_no_entity_anchor
```

如果某个组合中 fallback 来源占比过高，例如：

```text
fallback_key_token_ratio > 0.30
```

则标记：

```text
status = low_confidence
failure_reason = high_fallback_key_token_ratio
```

### 3.7.2 MMKE-Visual

`MMKE-Visual` 主实验优先使用多模态语义答案，因为它更直接代表图像语义编辑目标。固定优先级如下：

```text
Priority 1: m_rel_ans first valid semantic content token
Priority 2: rel_ans first valid semantic content token
Priority 3: strip alt template → extract visual semantic anchor
Priority 4: if still fails, exclude the sample from main average and keep it in diagnostics
```

但 `m_rel_ans` 与 `rel_ans` 也必须经过 `GENERIC_WORDS` 过滤。若出现以下情况，不得机械使用：

```text
Yes / No
It / This / That
It is shown ...
This means ...
```

这类答案应 fallback 到下一优先级来源，或者标记为：

```text
generic_key_token = true
used_in_main_score = false
```

推荐字段：

```text
key_token_source = m_rel_ans_visual_semantic
key_token_source = rel_ans_visual_semantic
key_token_source = alt_visual_semantic_anchor
key_token_source = excluded_no_visual_semantic_anchor
```

## 3.8 跨模型 tokenizer 差异记录

同一个 key phrase 在不同模型 tokenizer 下可能被切成不同 subtoken。主实验仍遵循 VisEdit-style key-token attribution，只使用 key phrase 的第一个可用 subtoken，但必须保存完整 key phrase 与 subtoken 信息。

`key_token_manifest.csv` 需要额外保存：

```text
key_phrase_text
key_phrase_source
key_phrase_token_ids
key_phrase_token_count
key_token_is_first_subtoken_of_phrase
key_token_subtoken_ids
used_subtoken_index
tokenizer_decoded_key_token
tokenizer_family
```

说明：

```text
key_phrase_text = Stone Cold Steve Austin
key_token_text = Stone
key_phrase_token_ids = tokenizer(" Stone Cold Steve Austin")
key_token_id = key_phrase_token_ids[0]
key_token_is_first_subtoken_of_phrase = true
```

这样既保持 VisEdit 的单 key-token 口径，又能解释 MMKE 长实体在不同 tokenizer 下的切分差异。

## 3.9 主结果与诊断结果边界

本补充实验完成后，结果表中的 VisEdit 相关命名统一如下：

| 结果名 | 作用 | 是否进入主定位表 |
|---|---|---:|
| `VisEdit-Contrib-Diagnostic-AltFirstToken` | 旧结果，盲取 `alt` 第一个 tokenizer token | 否 |
| `VisEdit-Contrib-Pre-KeyToken` | 新主结果，dataset-specific key token + Pre 候选层 | 是 |
| `VisEdit-Contrib-Direct-KeyToken` | 直接贡献度最高层，用于解释高贡献峰 | 否，附加分析 |
| `VisEdit-Contrib-Delta-KeyToken` | target key token 减 old key token | 否，诊断 / 消融 |
| `VisEdit-Contrib-AltSeq` | 完整序列贡献度扩展 | 否，消融 |

旧的 `AltFirstToken` 结果可以在论文或附录中作为 “why key-token extraction is needed” 的诊断证据，但不得替代 MMKE 上的主 VisEdit-style baseline。

# 4. 论文公式与代码实现

## 4.1 Transformer 残差分解

对于 Transformer 中第 \(l\) 层、第 \(n\) 个 token 的隐藏表示：

\[
h_n^l = h_n^{l-1} + a_n^l + m_n^l,
\quad l \in \{1,\ldots,L\},\ n \in \{1,\ldots,N\}
\]

其中：

| 符号 | 含义 |
|---|---|
| \(h_n^l\) | 第 \(l\) 层第 \(n\) 个 token 的 hidden state |
| \(a_n^l\) | 第 \(l\) 层 Attention 模块在第 \(n\) 个 token 位置的输出 |
| \(m_n^l\) | 第 \(l\) 层 MLP / FFN 模块在第 \(n\) 个 token 位置的输出 |
| \(N\) | 输入序列最后一个 prompt token 位置 |

Attention 和 MLP 输出定义为：

\[
a_n^l = \mathrm{Attn}^l(h_1^{l-1}, \ldots, h_n^{l-1})
\]

\[
m_n^l = \mathrm{MLP}^l(h_n^{l-1}+a_n^l)
\]

## 4.2 模块输出映射到词表空间

给定 VLLM：

\[
f_\theta: X_v \times X_t \rightarrow O
\]

内部语言 Transformer 记为：

\[
\hat{f}_\theta: E_v \times E_t \rightarrow Y
\]

图像和文本 embedding 拼接为：

\[
\varepsilon = \varepsilon_v \oplus \varepsilon_t \in \mathbb{R}^{N \times d_h}
\]

最终 next-token 分布为：

\[
p = \delta(h_N^L W_V)
\]

由残差结构展开：

\[
h_N^L W_V
=
h_N^0 W_V
+
\sum_{l=1}^{L}(a_N^l W_V + m_N^l W_V)
\]

因此可以单独分析每层 Attention / MLP 模块输出对目标 key token 的贡献。

## 4.3 单模块贡献度

对于模块输出：

\[
r \in \{a_N^l, m_N^l\}
\]

目标 key token 为 \(o^*\)。

Probability part：

\[
C^p_{o^*}(r) = \delta(rW_V)_{o^*}
\]

Value / logit part：

\[
C^v_{o^*}(r)
=
\frac{(rW_V)_{o^*}}
{\max_{l=1}^{L} \max\left(|(a_N^l W_V)_{o^*}|, |(m_N^l W_V)_{o^*}|\right) + \epsilon}
\]

论文简写的正贡献形式：

\[
C_{o^*}(r) = \sqrt{C^p_{o^*}(r) \cdot C^v_{o^*}(r)}
\]

实际代码建议采用 signed contribution：

\[
I_{s,l,t}
=
\mathrm{sign}\left(\tilde v_{s,l,t}\right)
\sqrt{|\tilde v_{s,l,t}|}
\sqrt{p_{s,l,t}}
\]

其中：

\[
\tilde v_{s,l,t}
=
\frac{v_{s,l,t}}{M_s}
\]

\[
M_s
=
\max\left(
\max_l |v_{s,l,attn}|,
\max_l |v_{s,l,mlp}|
\right)+\epsilon
\]

## 4.4 官方实现对应关系

官方 `p_tracking()` 中模块输出先经过 final norm，再经过 LM head：

```python
logits = self.voc(self.norm(reps))
```

对应：

\[
z_r = \mathrm{LMHead}(\mathrm{FinalNorm}(r))
\]

然后记录：

```python
total_p[tm].append(float(torch.softmax(logits, 0)[predict_id]))
total_v[tm].append(float(logits[predict_id]))
```

对应：

\[
p_{s,l,t} = \delta(z_{s,l,t})_{o_s^*}
\]

\[
v_{s,l,t} = (z_{s,l,t})_{o_s^*}
\]

---

# 5. 全流程实验安排

## 5.1 阶段 A：实验注册与文件准备

每个 `dataset × model` 组合先建立运行目录：

```text
results/visedit_contrib/{dataset}/{model}/
├── config.json
├── model_registry.yaml
├── sample_manifest.csv
├── key_token_manifest.csv
├── key_token_manual_audit.csv
├── key_token_coverage_report.json
├── raw_module_pv.npz
├── sample_layer_contribution.csv
├── layer_scores.csv
├── high_contribution_region.json
├── candidate_layers_topk.csv
├── contribution_plot.svg
└── run_log.txt
```

`model_registry.yaml` 至少包含：

```text
model_name
checkpoint_or_repo_id
revision_or_commit
num_decoder_layers
decoder_module_path
layer_module_tmp
mlp_module_tmp
attn_module_tmp
norm_path
voc_path
visual_token_rule
prompt_template
tokenizer_name
processor_name
dtype
quantization
wrapper_commit_or_hash
```

`config.json` 至少包含：

```json
{
  "method": "VisEdit-Contrib-Pre-KeyToken",
  "dataset": "MMKE-Entity",
  "model_name": "llava-v1.5-7b",
  "key_mode": "dataset_key_token",
  "key_token_rule": "entity_anchor_from_alt",
  "candidate_conversion": "pre_before_high_contribution_region",
  "score_formula": "sign(v_norm)*sqrt(abs(v_norm))*sqrt(p)",
  "rank_metric": "score_positive_key_token",
  "smoothing_window": 3,
  "lambda": 0.5,
  "top_k": [3, 5],
  "generic_key_token_policy": "exclude_from_main_average",
  "leading_space": true
}
```

## 5.2 阶段 B：样本 manifest 与数据清洗

对每条样本生成 `sample_manifest.csv`：

```text
dataset
subset
sample_id
image_path
image_exists
src
alt
pred
has_rephrase
has_image_rephrase
has_loc
has_m_loc
used_for_localization
skip_reason
```

过滤规则：

1. 图像路径不存在：`skip_reason=image_missing`；
2. `src` 为空：`skip_reason=empty_prompt`；
3. `alt` 为空：`skip_reason=empty_alt`；
4. 模型 wrapper 无法处理图像：`skip_reason=wrapper_preprocess_failed`；
5. key token 抽取失败：`skip_reason=no_valid_key_token`。

所有方法必须使用同一个 localization 样本集合，不允许不同模型或不同 key 模式随意改变样本。

## 5.3 阶段 C：Key-token 抽取与诊断

对每个样本执行 `extract_visedit_key_token()`，输出 `key_token_manifest.csv`：

```text
dataset
subset
sample_id
model
alt_raw
pred_raw
key_phrase_text
key_phrase_source
key_phrase_token_ids
key_phrase_token_count
key_token_text
predict_word
key_token_source
key_token_id
key_token_position
key_token_subtoken_ids
used_subtoken_index
leading_space
tokenizer_decoded_key_token
tokenizer_family
key_token_is_first_subtoken_of_phrase
generic_key_token
used_in_main_score
skip_reason
```

主实验样本条件：

```text
used_in_main_score = true
and generic_key_token = false
and key_token_id is not null
```

必须统计：

```text
total_sample_count
valid_key_token_count
generic_key_token_count
generic_key_token_ratio
excluded_sample_count
```

若 `generic_key_token_ratio` 很高，尤其在 MMKE-Entity / MMKE-Visual 上，应先修复 key-token 抽取规则，再跑贡献度。

## 5.4 阶段 D：Hook 单元测试

每个模型正式跑贡献度前，必须通过以下测试：

1. 能正确 hook 每层 Attention 输出；
2. 能正确 hook 每层 MLP 输出；
3. hook 到的层数等于 `num_decoder_layers`；
4. `norm_path` 与 `voc_path` 能将模块输出映射到词表 logits；
5. 指定 `predict_word` 时能得到合法 `key_token_id`；
6. `predict_word=None` 时能得到模型 top-1 next token；
7. 同一样本重复前向，贡献度结果一致。

失败时记录：

```text
status = unavailable
failure_reason = hook_or_vocab_projection_failed
```

不得用其他模型或其他方法结果 fallback。

## 5.5 阶段 E：前向传播与 p/v 记录

对每个有效样本：

```python
pt.forward_and_trace(prompt, image)
_, _, total_p, total_v = pt.p_tracking(
    save_results=False,
    predict_word=predict_word
)
```

其中：

```text
total_p['att'][l]
total_v['att'][l]
total_p['mlp'][l]
total_v['mlp'][l]
```

必须保留 raw p/v 到 `raw_module_pv.npz` 或等价格式，便于复算：

```text
sample_id
layer
module_type
p_value
v_logit
key_token_id
```

## 5.6 阶段 F：样本级贡献度计算

对第 \(s\) 个样本：

```python
M_s = max(max(abs(vs['mlp'][s])), max(abs(vs['att'][s]))) + 1e-12
mlp_v_norm = vs['mlp'][s] / M_s
att_v_norm = vs['att'][s] / M_s
mlp_infl = sign(mlp_v_norm) * sqrt(abs(mlp_v_norm)) * sqrt(mlp_p)
att_infl = sign(att_v_norm) * sqrt(abs(att_v_norm)) * sqrt(att_p)
```

输出 `sample_layer_contribution.csv`：

```text
dataset
subset
model
sample_id
layer
key_token_text
key_token_id
key_token_source
generic_key_token
attn_p
attn_v
attn_contrib
mlp_p
mlp_v
mlp_contrib
score_positive_sample
score_signed_sample
score_abs_sample
used_in_main_score
```

其中：

\[
S^{+}_{s,l}
=
\max(0, I_{s,l,attn}) + \max(0, I_{s,l,mlp})
\]

\[
S^{signed}_{s,l}
=
I_{s,l,attn}+I_{s,l,mlp}
\]

\[
S^{abs}_{s,l}
=
|I_{s,l,attn}|+|I_{s,l,mlp}|
\]

## 5.7 阶段 G：数据集级层分数

只对 `used_in_main_score=true` 的样本取平均：

\[
\bar I_{l,attn}
=
\frac{1}{N_{valid}}
\sum_{s=1}^{N_{valid}} I_{s,l,attn}
\]

\[
\bar I_{l,mlp}
=
\frac{1}{N_{valid}}
\sum_{s=1}^{N_{valid}} I_{s,l,mlp}
\]

主排序分数：

\[
S_l^{+}
=
\max(0, \bar I_{l,attn}) + \max(0, \bar I_{l,mlp})
\]

辅助分数：

\[
S_l^{signed}
=
\bar I_{l,attn}+\bar I_{l,mlp}
\]

\[
S_l^{abs}
=
|\bar I_{l,attn}|+|\bar I_{l,mlp}|
\]

输出 `layer_scores.csv`：

```text
dataset
subset
model
method
key_mode
key_token_rule
layer
attn_mean
mlp_mean
score_positive
score_signed
score_abs
rank_positive
rank_signed
rank_abs
total_sample_count
valid_sample_count
generic_key_token_count
generic_key_token_ratio
status
failure_reason
```

注意：

- 主排序只使用 `score_positive`；
- `score_signed` 与 `score_abs` 只用于诊断；
- 不允许只输出 Top-10，必须保存所有层。

## 5.8 阶段 H：高贡献区识别

对 `score_positive` 做 3 层移动平均：

\[
\tilde S(l)
=
\operatorname{Mean}(S(l-1), S(l), S(l+1))
\]

边界层只对存在的邻居取均值。

计算：

\[
\mu = \operatorname{Mean}_l \tilde S(l)
\]

\[
\sigma = \operatorname{Std}_l \tilde S(l)
\]

阈值：

\[
\tau = \mu + \lambda \sigma
\]

默认：

```text
lambda = 0.5
```

高贡献层集合：

\[
\mathcal H
=
\{l: \tilde S(l) \ge \tau\}
\]

取最长连续高贡献区：

\[
[s_{\mathcal H}, e_{\mathcal H}]
\]

如果存在多个长度相同的连续区，tie-break：

```text
1. 区间内平均 smoothed score 更高者优先；
2. 仍并列时，较浅起点优先；
3. 仍并列时，较短模型归一化深度更接近 0.6 的优先。
```

输出 `high_contribution_region.json`：

```json
{
  "method": "VisEdit-Contrib-Pre-KeyToken",
  "rank_metric": "score_positive_key_token",
  "smoothing_window": 3,
  "lambda": 0.5,
  "mean": 0.0123,
  "std": 0.0045,
  "threshold": 0.01455,
  "high_layers": [20, 21, 22, 23, 24],
  "selected_region": [20, 24]
}
```

## 5.9 阶段 I：Pre 候选层生成

VisEdit-style 主候选层不是贡献度最高层本身，而是高贡献区之前的层：

\[
\mathcal C_{VisEdit\text{-}Pre,K}
=
\{s_{\mathcal H}-1,
  s_{\mathcal H}-2,
  \ldots,
  s_{\mathcal H}-K\}
\]

删除越界层，不自动用其他方法补齐。

Top-3：

```text
[s_H - 1, s_H - 2, s_H - 3]
```

Top-5：

```text
[s_H - 1, s_H - 2, s_H - 3, s_H - 4, s_H - 5]
```

如果候选不足，记录：

```text
status = insufficient_pre_layers
```

输出 `candidate_layers_topk.csv`：

```text
dataset
subset
model
method
variant
top_k
rank
layer
score_positive
smoothed_score
high_contribution_region_start
high_contribution_region_end
candidate_conversion
status
failure_reason
```

主方法名称固定为：

```text
VisEdit-Contrib-Pre-KeyToken
```

如果同时输出直接贡献度最高层，必须命名为：

```text
VisEdit-Contrib-Direct-KeyToken
```

## 5.10 阶段 J：当前 AltFirstToken 结果保留方式

当前已完成的三个 CSV：

```text
crossmodel_pilot500_module_contribution_summary.csv
all7_module_contribution_summary_mmke_entity_alt.csv
all7_module_contribution_summary_mmke-visual-alt.csv
```

建议归档到：

```text
results/visedit_contrib_diagnostic_alt_first_token/
```

并在 manifest 中标记：

```text
method = VisEdit-Contrib-Diagnostic-AltFirstToken
key_mode = alt_first_token
used_for_main_baseline = false
reason = MMKE alt is free-form long text; first token may be generic function word
```

论文或报告中可写：

```text
We keep the alt-first-token contribution results as a diagnostic analysis. Since the alt field in MMKE-Entity and MMKE-Visual is usually a long free-form description, this setting may select generic function words such as The or This and is therefore not used as the main VisEdit-style baseline.
```

## 5.11 阶段 K：统一 adapter 训练验证

贡献度定位只产生候选层，不能直接证明编辑性能。最终必须进入统一 adapter 编辑实验验证。

对每个 `dataset × model` 组合：

1. 读取 `VisEdit-Contrib-Pre-KeyToken` 的 Top-3 / Top-5 候选层；
2. 与其他定位方法候选层合并，构成 candidate union；
3. 每个候选层训练同一结构的视觉编辑 adapter；
4. 使用同一训练数据、同一 optimizer、同一 learning rate、同一训练步数；
5. 使用至少 3 个训练随机种子；
6. 在最终 eval/test 上评测：Rel、T-Gen、M-Gen、T-Loc、M-Loc、Average；
7. 报告 Top1 / Mean@K / Best@K / Regret@K / Hit@K。

贡献度方法在定位评价中使用：

```text
Top1Perf = A(candidate_layer_rank1)
Mean@K = mean A(l), l in TopK
Best@K = max A(l), l in TopK
Regret@K = OracleBest - Best@K
Hit@K = whether OracleBestLayer in TopK
```

其中 \(A(l)\) 是真实 adapter 编辑评测分数，而不是贡献度分数。

---

# 6. 推荐运行矩阵

## 6.1 主实验运行矩阵

主实验只跑：

```text
method = VisEdit-Contrib-Pre-KeyToken
key_mode = dataset_key_token
score = score_positive
candidate_conversion = Pre
```

| 数据集 | 样本来源 | key token 规则 | 输出 |
|---|---|---|---|
| E-VQA / pilot500 | `pilot500 train` | `alt` 第一个有效内容 token | Top-3 / Top-5 Pre 候选层 |
| MMKE-Entity | `entity/train.json` | `alt` 中实体/事实锚点 token | Top-3 / Top-5 Pre 候选层 |
| MMKE-Visual | `visual/train.json` | `m_rel_ans` / `rel_ans` / 视觉语义锚点 token | Top-3 / Top-5 Pre 候选层 |

每个数据集在 7 个模型上都跑一次，共：

```text
3 datasets × 7 models = 21 combinations
```

## 6.2 诊断实验运行矩阵

可选诊断：

| 实验 | 目的 |
|---|---|
| `VisEdit-Contrib-Diagnostic-AltFirstToken` | 对照当前已跑结果 |
| `VisEdit-Contrib-Direct-KeyToken` | 看高贡献峰本身在什么层 |
| `VisEdit-Contrib-Direct-PredToken` | 分析旧答案支持层 |
| `VisEdit-Contrib-Delta-KeyToken` | 分析目标支持相对旧答案支持的差值 |
| `VisEdit-Contrib-AltSeq` | 检查完整长答案序列是否改变层趋势 |

诊断实验不得覆盖主实验命名，也不得混入主候选层表。

---

## 6.3 推荐正式运行顺序

不要直接一次性跑完 21 个组合。推荐顺序如下：

```text
Step 1: 只构建 MMKE-Entity / MMKE-Visual 的 key_token_manifest.csv
Step 2: 每个数据集人工抽查 50 条，并修正 key-token 规则
Step 3: 运行 MMKE-Entity × BLIP2-OPT-2.7B 或 LLaVA-v1.5-7B pilot
Step 4: 检查 layer_scores、high_contribution_region、Top-3/Top-5 Pre 候选层
Step 5: 运行 MMKE-Entity × 7 models
Step 6: 运行 MMKE-Visual × 7 models
Step 7: 回填总表，用 KeyToken 主结果替换旧 AltFirstToken 主表位置
```

pilot 必须检查：

```text
valid_key_token_ratio 是否 ≥ 0.70
manual_error_ratio 是否 ≤ 0.10
Direct 高贡献层是否与 Pre 候选层区分清楚
high_contribution_region 是否不是由极少数异常层造成
Top-3 / Top-5 是否无重复、无越界
contribution_plot 是否呈现合理层间差异
```

若 pilot 出现明显异常，应先检查 `key_token_manifest.csv`、hook 路径、prompt 模板和 tokenizer leading space，而不是直接进入全量 7 模型运行。

# 7. 结果有效性标准

一组 VisEdit 高贡献层实验要作为主实验，必须满足：

- [ ] 使用 `dataset_key_token`，而不是盲取 `alt` 第一个 token；
- [ ] E-VQA、MMKE-Entity、MMKE-Visual 分别记录 key token 规则；
- [ ] 保存 `key_token_text`、`predict_word`、`key_token_id`、`key_token_source`；
- [ ] 标记 `generic_key_token=true/false`；
- [ ] 统计 `generic_key_token_ratio`；
- [ ] 输出完整每层贡献度，而不是只输出 Top-10；
- [ ] 同时保存 positive、signed、abs 三种分数；
- [ ] 主排序使用 `score_positive`；
- [ ] 使用 3 层移动平均和 `mean + 0.5 std` 识别高贡献区；
- [ ] 按高贡献区起点之前的层生成 Top-3 / Top-5 Pre 候选层；
- [ ] 明确区分 `Direct` 排名和 `Pre` 候选层；
- [ ] 当前 `AltFirstToken` 结果只作为诊断，不进入主表；
- [ ] 最终候选层通过统一 adapter 训练和编辑评测验证。



正式回填主表前还必须检查以下异常：

- [ ] 高贡献区不是从第 0 层开始导致 Pre 候选层大量越界；
- [ ] `generic_key_token_ratio` 不高于预设阈值；
- [ ] `fallback_key_token_ratio` 不高于预设阈值；
- [ ] 7 个模型没有因为代码复用错误而产生完全相同的候选层；
- [ ] Qwen2.5-VL、PaliGemma、SmolVLM 的 tokenizer 没有把 key token 切成异常符号；
- [ ] MMKE-Entity 的 key token 主要来自 `alt_entity_anchor`，而不是过度依赖 `rel_ans_*` fallback；
- [ ] MMKE-Visual 的 key token 主要来自 `m_rel_ans` / `rel_ans` / `alt_visual_semantic_anchor`，而不是 `Yes/No/This/It` 等泛化词；
- [ ] `VisEdit-Contrib-Pre-KeyToken` 与旧的 `VisEdit-Contrib-Diagnostic-AltFirstToken` 文件路径和方法名完全分开。

若任何一项不满足，该结果只能标记为：

```text
status = diagnostic_only
```

不得作为 `VisEdit-Contrib-Pre-KeyToken` 主基线。

---

# 8. 输出文件规范

## 8.1 `sample_manifest.csv`

```text
dataset
subset
sample_id
image_path
image_exists
src_hash
alt_hash
pred_hash
used_for_localization
skip_reason
```

## 8.2 `key_token_manifest.csv`

```text
dataset
subset
model
sample_id
alt_raw
pred_raw
key_phrase_text
key_phrase_source
key_phrase_token_ids
key_phrase_token_count
key_token_text
predict_word
key_token_source
key_token_id
key_token_position
key_token_subtoken_ids
used_subtoken_index
leading_space
tokenizer_decoded_key_token
tokenizer_family
key_token_is_first_subtoken_of_phrase
generic_key_token
used_in_main_score
skip_reason
```

## 8.3 `sample_layer_contribution.csv`

```text
dataset
subset
model
sample_id
layer
module_type
key_token_text
key_token_id
p_value
v_logit
v_norm
contribution_signed
used_in_main_score
```

## 8.4 `layer_scores.csv`

```text
dataset
subset
model
method
key_mode
key_token_rule
layer
attn_mean
mlp_mean
score_positive
score_signed
score_abs
score_positive_smoothed
rank_positive
rank_signed
rank_abs
total_sample_count
valid_sample_count
generic_key_token_count
generic_key_token_ratio
status
failure_reason
```

## 8.5 `high_contribution_region.json`

```json
{
  "dataset": "MMKE-Visual",
  "model": "llava-v1.5-7b",
  "method": "VisEdit-Contrib-Pre-KeyToken",
  "rank_metric": "score_positive_key_token",
  "smoothing_window": 3,
  "lambda": 0.5,
  "threshold_rule": "mean + lambda * std",
  "high_layers": [27, 28, 29, 30, 31],
  "selected_region": [27, 31],
  "status": "done"
}
```

## 8.6 `candidate_layers_topk.csv`

```text
dataset
subset
model
method
variant
top_k
rank
layer
score_positive
score_positive_smoothed
high_contribution_region_start
high_contribution_region_end
candidate_conversion
status
failure_reason
```

## 8.7 `contribution_summary.csv`

```text
dataset
model
method
key_mode
valid_sample_count
generic_key_token_ratio
top3_direct_layers
top5_direct_layers
high_contribution_region
top3_pre_layers
top5_pre_layers
status
failure_reason
```

---

## 8.8 `key_token_coverage_report.json`

```json
{
  "dataset": "MMKE-Visual",
  "model": "qwen2.5-vl-3b-instruct",
  "total_sample_count": 1000,
  "valid_key_token_count": 820,
  "generic_key_token_count": 60,
  "generic_key_token_ratio": 0.06,
  "used_in_main_score_count": 820,
  "used_in_main_score_ratio": 0.82,
  "fallback_key_token_count": 95,
  "fallback_key_token_ratio": 0.095,
  "manual_checked_count": 50,
  "manual_error_count": 3,
  "manual_error_ratio": 0.06,
  "status": "pass"
}
```

## 8.9 `key_token_manual_audit.csv`

```text
dataset
subset
model
sample_id
alt_raw
rel_ans_raw
m_rel_ans_raw
key_phrase_text
key_token_text
key_token_source
predict_word
key_token_id
tokenizer_decoded_key_token
generic_key_token
manual_is_valid
manual_error_type
manual_comment
```

# 9. 推荐代码结构

```text
scripts/
├── build_visedit_key_token_manifest.py
├── run_visedit_module_contribution.py
├── aggregate_visedit_layer_scores.py
├── select_visedit_pre_candidates.py
└── summarize_visedit_contribution_runs.py
```

## 9.1 `build_visedit_key_token_manifest.py`

输入：

```text
--dataset-name
--data-path
--image-root
--model-name
--tokenizer-path
--output key_token_manifest.csv
```

功能：

1. 读取原始数据；
2. 抽取 dataset-specific key token；
3. tokenizer 编码；
4. 标记 generic key token；
5. 输出 manifest。

## 9.2 `run_visedit_module_contribution.py`

输入：

```text
--dataset-name
--data-path
--image-root
--model-name
--p-track-config
--key-token-manifest
--key-mode dataset_key_token
--output-dir
```

功能：

1. 加载模型；
2. 通过 hook 单元测试；
3. 对每个有效样本前向；
4. 保存 raw p/v 和样本级贡献度。

## 9.3 `aggregate_visedit_layer_scores.py`

输入：

```text
--sample-layer-contribution sample_layer_contribution.csv
--output layer_scores.csv
```

功能：

1. 按层平均 Attention / MLP 贡献；
2. 计算 positive、signed、abs；
3. 输出完整层表。

## 9.4 `select_visedit_pre_candidates.py`

输入：

```text
--layer-scores layer_scores.csv
--lambda 0.5
--smoothing-window 3
--top-k 3 5
--output candidate_layers_topk.csv
```

功能：

1. 3 层移动平均；
2. 计算高贡献区；
3. 输出 Direct 诊断排名；
4. 输出 Pre 主候选层。

---

# 10. 可直接使用的主流程伪代码

```python
for dataset_name in ["E-VQA/pilot500", "MMKE-Entity", "MMKE-Visual"]:
    for model_name in MODEL_LIST:
        # A. build manifests
        samples = load_dataset(dataset_name)
        sample_manifest = build_sample_manifest(samples)

        # B. dataset-specific key-token extraction
        key_rows = []
        for sample in samples:
            key_text, key_source = extract_visedit_key_token(sample, dataset_name)
            predict_word = add_leading_space_if_needed(key_text, model_name)
            token_ids = tokenizer(predict_word, add_special_tokens=False).input_ids
            key_token_id = token_ids[0] if token_ids else None
            generic = is_generic_key_token(key_text)
            key_rows.append({
                "sample_id": sample["id"],
                "key_token_text": key_text,
                "predict_word": predict_word,
                "key_token_source": key_source,
                "key_token_id": key_token_id,
                "key_token_subtoken_ids": token_ids,
                "generic_key_token": generic,
                "used_in_main_score": key_token_id is not None and not generic,
            })
        save_csv(key_rows, "key_token_manifest.csv")

        # C. hook test
        pt = PTrack(model_name, p_track_config)
        assert_hook_test_passed(pt)

        # D. contribution forward
        contribution_rows = []
        for sample, key in zip(samples, key_rows):
            if not key["used_in_main_score"]:
                continue
            prompt = build_prompt(sample, dataset_name)
            image = load_image(sample["image"])

            pt.forward_and_trace(prompt, image)
            _, _, total_p, total_v = pt.p_tracking(
                save_results=False,
                predict_word=key["predict_word"]
            )

            M = max(max_abs(total_v["mlp"]), max_abs(total_v["att"])) + 1e-12
            for l in range(num_layers):
                for module in ["att", "mlp"]:
                    p = total_p[module][l]
                    v = total_v[module][l]
                    v_norm = v / M
                    contrib = sign(v_norm) * sqrt(abs(v_norm)) * sqrt(p)
                    contribution_rows.append({
                        "sample_id": sample["id"],
                        "layer": l,
                        "module_type": module,
                        "p_value": p,
                        "v_logit": v,
                        "v_norm": v_norm,
                        "contribution_signed": contrib,
                    })
        save_csv(contribution_rows, "sample_layer_contribution.csv")

        # E. aggregate layer scores
        layer_scores = aggregate_by_layer(contribution_rows)
        save_csv(layer_scores, "layer_scores.csv")

        # F. select high-contribution region and Pre candidates
        region = find_high_contribution_region(
            layer_scores["score_positive"],
            smoothing_window=3,
            lambda_value=0.5,
        )
        candidates = pre_candidates(region.start, top_k=[3, 5])
        save_json(region, "high_contribution_region.json")
        save_csv(candidates, "candidate_layers_topk.csv")
```

---

# 11. Prompt 模板规则

## 11.1 E-VQA / pilot500

默认：

```text
{src} The answer is:
```

示例：

```text
Is it sunny? The answer is:
```

## 11.2 MMKE-Entity

默认尽量保持原始 `src`，并让模型停在答案前：

```text
{src}
```

如果模型 wrapper 需要统一回答模板，可以使用：

```text
{src} Answer:
```

但必须全模型、全样本固定，并在 `config.json` 记录。

## 11.3 MMKE-Visual

默认：

```text
{src}
```

或：

```text
{src} Answer:
```

注意：prompt 模板不能根据样本内容动态变化，否则贡献度层排序不可复现。

---

# 12. 常见问题与处理

## 12.1 为什么不能直接使用 `alt` 第一个 token？

E-VQA 中 `alt` 多为短答案，首 token 通常就是答案。但 MMKE-Entity / MMKE-Visual 的 `alt` 通常是长句，例如：

```text
The human in the image corresponds to Stone Cold Steve Austin...
This is the prayer gesture in life gestures...
```

首 token 可能是 `The` 或 `This`，它们不能代表编辑知识。若直接计算这些功能词贡献度，层排序反映的是模型如何生成英文句首模板，而不是如何支持实体或视觉语义知识。

## 12.2 如果 key token 抽取错了怎么办？

必须通过 `key_token_manifest.csv` 人工抽查。建议每个数据集随机抽 50 条，检查：

```text
key_token_text 是否是实体/语义/属性/关系锚点
key_token_source 是否合理
generic_key_token 是否正确
```

抽查失败率高时，先修规则再跑贡献度。

## 12.3 Direct 和 Pre 的区别是什么？

`Direct`：直接选择贡献度最高层。

```text
TopK(score_positive)
```

`Pre`：先找高贡献区，再选高贡献区之前的层。

```text
high contribution region = [s_H, e_H]
TopK_pre = [s_H-1, s_H-2, ...]
```

VisEdit-style 主基线应使用 `Pre`，因为 adapter 需要在高贡献层之前注入编辑信号，使后续高贡献层利用该信号影响预测。

## 12.4 如果高贡献区从第 0 层开始怎么办？

候选层会越界，此时记录：

```text
status = insufficient_pre_layers
```

不要自动改成中层先验，也不要用 Direct 层替代。可在附加分析中报告 `Direct-KeyToken` 结果。

## 12.5 如果 MMKE-Visual 的 `pred` 为空怎么办？

主实验不依赖 `pred`。`VisEdit-Contrib-Pre-KeyToken` 只需要 `alt` 相关 key token。若做旧知识诊断，可使用缓存的 `model_pred` 生成 `pred_token` 版本，但必须另命名。

---

## 12.6 这次 MMKE key-token 补充实验能否替代旧 AltFirstToken 结果？

可以，但前提是满足本手册的主实验有效性标准。

旧结果：

```text
VisEdit-Contrib-Diagnostic-AltFirstToken
```

只能作为诊断结果，因为它可能测到 MMKE 长答案句首功能词的贡献。

新结果：

```text
VisEdit-Contrib-Pre-KeyToken
```

使用 dataset-specific key token，并完成人工抽查、覆盖率检查、高贡献区识别和 Pre 候选层生成后，可以作为 MMKE 上正式的 VisEdit-style 主基线。

回填总表时应保留旧结果的路径和说明，但主表只使用 `VisEdit-Contrib-Pre-KeyToken`。

# 13. 论文中推荐表述

## 13.1 中文表述

> 对于 VisEdit-style 贡献度基线，本文遵循其 key-token prediction attribution 的设定，对每层 Attention 与 MLP 模块输出映射到词表空间后的 key token 概率与归一化 logit 进行组合，得到模块级 signed contribution。考虑到 MMKE-Entity 和 MMKE-Visual 中 `alt` 通常为自由长文本，直接使用 `alt` 的第一个 token 可能会落在 The、This 等功能词上，无法代表实际编辑知识。因此，本文为不同数据集定义了任务相关的 key-token 抽取规则：E-VQA 使用短答案 `alt` 的首个有效 token；MMKE-Entity 使用编辑后实体或事实锚点 token；MMKE-Visual 使用视觉语义标签或含义 token。随后在定位集上平均贡献度，识别高贡献区域，并按照 VisEdit 的 adapter 前置思想选择高贡献区之前的 Top-K 层作为候选编辑层。

## 13.2 English wording

> For the VisEdit-style contribution baseline, we follow the key-token prediction attribution setting and map the attention and MLP outputs of each decoder layer into the vocabulary space. The probability and normalized logit of the selected key token are combined into a signed module contribution score. Since the `alt` field in MMKE-Entity and MMKE-Visual is usually a free-form long textual description, directly using the first token of `alt` may select generic function words such as “The” or “This”, which do not represent the edited knowledge. Therefore, we define dataset-specific key-token extraction rules: for E-VQA, we use the first valid token of the short target answer; for MMKE-Entity, we use the edited entity or factual anchor token; and for MMKE-Visual, we use the visual semantic label or meaning token. The layer-wise contribution scores are averaged over the localization set, and the candidate adapter layers are selected immediately before the identified high-contribution region following the VisEdit-style pre-insertion rule.

---

# 14. 一句话总结

VisEdit 贡献度层排序的主实验应计算“任务相关 key token”的贡献度，而不是机械取 `alt` 第一个 token。E-VQA 中 `alt` 首 token 通常可近似 key token；MMKE-Entity 和 MMKE-Visual 必须抽取实体/事实锚点或视觉语义锚点。最终主基线命名为 `VisEdit-Contrib-Pre-KeyToken`，需要输出完整 layer scores、key token 诊断、高贡献区和 Top-3 / Top-5 前置候选层，并通过统一 adapter 真实编辑实验验证。
