# CMA-Direct / Visual Causal Restoration 实验手册修改建议

> 适用文件：`CMA-Direct.md`  
> 目的：补充当前实验手册中仍需明确的工程实现口径，使其能够更稳定地指导 `Visual Causal Restoration / CMA-Direct` 实验实现。  
> 核心结论：当前手册总体方向正确，已经明确“污染进入语言解码器的视觉表征、恢复指定层的视觉 hidden states”。但正式指导代码实现前，建议补充 **视觉 token span、非整层恢复、噪声校准、teacher-forcing 对齐、restore hook 实现和异常诊断**。

---

## 1. 总体判断

当前手册可以用于指导实验，尤其是以下口径已经正确：

1. 污染位置设定在进入语言解码器时的视觉表征；
2. 恢复操作发生在 decoder block 输出后的 hidden states；
3. 主恢复对象是视觉 token hidden states；
4. 不恢复文本 token；
5. 实验定位为 causal restoration analysis，而不是 Adapter 编辑层真值；
6. 结果通过 CR / KCR 等恢复指标衡量；
7. 可以输出 Top-3 / Top-5 作为候选层诊断结果。

但如果要把该手册交给代码实现或用于 `7 models × 3 datasets` 批量实验，还需要补充若干工程级规范，否则容易出现以下问题：

- 不同模型 visual token 位置识别不一致；
- 恢复时误把整层 hidden states 全部替换；
- 恢复 text / answer token，导致结果偏高甚至近似“作弊”；
- 噪声强度不合适，导致污染过弱或过强；
- teacher-forcing 的 target answer token mask 不准确；
- hook 位置、shape、batch 对齐不一致；
- CR 出现异常值但没有记录；
- 结果高度偏向浅层但缺少诊断解释。

---

## 2. 必须明确：恢复视觉 token，而不是恢复整层 hidden states

### 当前手册状态

当前手册已经写到：

- `restore_target: visual_tokens_only`；
- 实验中只恢复视觉 token 对应位置，不恢复文本 token；
- 在指定 decoder 层处，将该层视觉 hidden states 替换为 clean forward 中缓存的对应状态。

这个方向是对的。

### 仍需补充的问题

建议在 `Step 3: Restore Forward` 后面新增一个更明确的小节，避免代码实现时误写成整层恢复。

### 建议新增内容

```markdown
### 主实验恢复范围说明

主实验只恢复指定 decoder 层输出后的视觉 token hidden states，而不是恢复整层 hidden states。

设第 l 层输出 hidden states 为：

H^{l,corrupt} = [H_v^{l,corrupt}; H_t^{l,corrupt}]

其中 H_v 表示视觉 token hidden states，H_t 表示文本 token 和答案 token hidden states。

恢复操作定义为：

H_v^{l,corrupt} <- H_v^{l,clean}

而非：

H^{l,corrupt} <- H^{l,clean}

也就是说，恢复后状态为：

H^{l,restore} = [H_v^{l,clean}; H_t^{l,corrupt}]

本文不恢复整层 hidden states，因为整层恢复会同时恢复文本 token 和答案 token 表征，使实验不再专门衡量视觉表征的因果恢复作用。
```

### 为什么必须这样写？

如果恢复整层 hidden state：

```text
H^{l,corrupt} <- H^{l,clean}
```

那么被恢复的不只是视觉 token，还包括：

- question / prompt token；
- instruction token；
- teacher-forcing 下的 answer token；
- 已经被污染视觉信息影响过的文本位置。

这样测到的是“整层状态恢复能力”，而不是“视觉表征恢复能力”。对于本文任务，Adapter 修改的是视觉表征，因此 CMA-Direct 主实验必须只恢复视觉 token slice。

---

## 3. 必须修改：不要默认视觉 token 是 `1:N_v`

### 当前手册问题

当前手册中写到：

```math
H_v^l = H^l_{1:N_v}
```

这个写法只在视觉 token 位于序列最前面时成立。

但不同 VLM 的输入拼接方式不一样，例如：

- LLaVA 中 `<image>` token 可能在 prompt 中间展开；
- Qwen2.5-VL 的 image token span 由 processor / chat template 决定；
- PaliGemma / SmolVLM 的视觉 token 组织方式也不一定是简单前缀；
- BLIP2 / InstructBLIP 中视觉 query token 经过 Q-Former 压缩，进入 decoder 的位置需要单独确认。

### 建议替换为

```markdown
设视觉 token 位置集合为 V，则第 l 层视觉 hidden states 定义为：

H_v^l = H^l[:, V, :]

其中 V 由各模型的 processor、chat template 或 input embedding 拼接逻辑显式确定，不默认等于 1:N_v。
```

### 代码实现要求

每个样本必须保存：

```text
visual_start
visual_end
num_visual_tokens
visual_token_indices
```

如果模型无法确定 visual token span，应标记：

```text
visual_span_failed
```

不能 fallback 到全部 prompt token 或文本 token。

---

## 4. 需要补充：模型级 hook path 与 visual span 适配表

当前手册列出了各模型的合法层号，但还缺少每个模型的实际 hook 路径与 visual span 获取方式。

建议新增表格：

| Model | Decoder block path | Visual span source | 注意事项 |
|---|---|---|---|
| `blip2-opt-2.7b` | 待代码确认 | Q-Former 输出后进入 OPT 的视觉 query token | 不在原始 patch 上恢复 |
| `instructblip-vicuna-7b` | 待代码确认 | Q-Former 输出后的视觉 query token | 注意 Vicuna decoder 层路径 |
| `minigpt-4-vicuna-7b` | 待代码确认 | projected visual tokens | 需要确认视觉 token 在 prompt 中的位置 |
| `llava-v1.5-7b` | 待代码确认 | image token span / projector output | 不要默认视觉 token 一定位于开头 |
| `qwen2.5-vl-3b-instruct` | 待代码确认 | processor 生成的 image token span | chat template 可能影响 token 位置 |
| `paligemma-3b` | 待代码确认 | image token positions | 架构特殊，需单独验证 |
| `smolvlm-1.7b` | 待代码确认 | processor 返回的 image token positions | 需保存 token span 日志 |

运行时必须保存：

```text
layer_id -> module_name
visual_token_indices
input_embeds.shape
hidden_states[layer].shape
```

这样后续才能排查 hook 是否真的挂在了正确位置。

---

## 5. 需要补充：噪声强度预校准 Noise Calibration

### 当前手册状态

当前手册推荐：

```yaml
relative_noise_alpha_list:
  - 0.5
  - 1.0
  - 2.0
```

这个可以作为默认搜索范围，但不同模型 hidden-state 尺度差异很大，直接全量跑可能出现两种问题：

- 噪声太弱：`s_clean - s_corrupt` 很小，有效样本过少；
- 噪声太强：模型输出完全崩溃，浅层恢复占绝对优势。

### 建议新增小节

```markdown
## Noise Calibration：噪声强度预校准

正式运行前，每个 model / dataset 先用 50 个样本进行噪声校准。

候选 alpha：

alpha_list = [0.1, 0.3, 0.5, 1.0, 2.0]

选择规则：

1. 计算每个 alpha 下满足 gap = s_clean - s_corrupt > delta 的有效样本比例；
2. 优先选择有效样本比例位于 30%-80% 的 alpha；
3. 如果所有 alpha 有效比例都低于 30%，说明污染太弱，应增大 alpha；
4. 如果所有 alpha 有效比例都高于 80% 且 s_corrupt 极低，说明污染可能太强，应降低 alpha；
5. 最终正式实验可使用 1-3 个稳定 alpha。
```

### 推荐配置

```yaml
noise_calibration:
  enabled: true
  pilot_samples: 50
  candidate_alpha_list: [0.1, 0.3, 0.5, 1.0, 2.0]
  target_valid_ratio_range: [0.3, 0.8]
  delta_logprob: 0.05
```

---

## 6. 需要补充：teacher-forcing 答案 token 对齐规则

当前手册已经建议用完整答案序列 mean log probability，这是正确的。但还需要补充更细的 token mask 规则。

### 建议新增内容

```markdown
## Teacher-forcing 答案 token 对齐规则

目标答案评分必须使用 teacher-forcing，不使用 generate()。

输入形式：

[prompt tokens] + [target answer tokens]

其中：

- prompt 部分 label 全部设为 -100；
- 只对 target answer token 计算 log probability；
- 如果当前任务有 target_new / alt answer，优先使用编辑目标答案作为 target_answer；
- 如果 target answer 为空，样本无效；
- 如果 tokenizer 后 answer token 长度为 0，样本无效；
- 如果 answer 被截断，样本无效；
- 不同模型需要保持各自 chat template 的合法格式；
- 需要记录 answer_start、answer_end、answer_token_count。
```

### 为什么重要？

如果答案 token mask 错误，CR/KCR 计算就不是目标答案恢复，而可能混入 prompt token 或 padding token，导致层分数失真。

---

## 7. 需要补充：Restore Hook 实现规范

建议在手册中给出明确的 hook 伪代码，防止误恢复整层。

### 推荐伪代码

```python
def restore_hook(module, inputs, outputs):
    # outputs may be Tensor or tuple
    hidden = outputs[0] if isinstance(outputs, tuple) else outputs

    # clone to avoid in-place side effects
    hidden_new = hidden.clone()

    # only restore visual token slice
    hidden_new[:, visual_token_indices, :] = clean_cache[layer][:, visual_token_indices, :]

    if isinstance(outputs, tuple):
        return (hidden_new,) + outputs[1:]
    else:
        return hidden_new
```

### 必须满足

- 只替换视觉 token slice；
- 不替换文本 token；
- 不替换答案 token；
- 不 inplace 修改原 tensor；
- clean cache 与当前 batch 样本顺序一致；
- hidden shape 必须一致；
- `model.eval()`；
- `torch.no_grad()`；
- `use_cache=False`。

---

## 8. 需要补充：运行时设置

建议新增配置：

```yaml
runtime:
  model_eval: true
  torch_no_grad: true
  use_cache: false
  deterministic: true
  do_sample: false
  use_generate: false
```

### 原因

本实验应使用 forward teacher-forcing，而不是 generation。若 `use_cache=True`，某些模型可能跳过完整 hidden states 计算或影响 hook 行为，导致恢复无效或结果不稳定。

---

## 9. 需要补充：CR 异常值处理

当前手册定义了 CR：

```math
CR(l) = (s_restore(l) - s_corrupt) / (s_clean - s_corrupt + eps)
```

该定义可以使用，但实际运行会出现：

- `CR > 1`；
- `CR < 0`；
- denominator 太小；
- NaN / Inf；
- 少数极端样本拉高均值。

### 建议新增字段

```csv
cr_raw_mean
cr_clip01_mean
cr_gt1_ratio
cr_lt0_ratio
nonfinite_count
```

### 推荐处理方式

```markdown
主排序默认使用 cr_raw_mean，但必须同时报告 cr_clip01_mean、cr_gt1_ratio 和 cr_lt0_ratio。若某个 model/dataset 出现大量 CR>1 或 CR<0，需要在 summary.md 中标记为 unstable_restoration。
```

也可以使用 clipped CR 作为稳健性分析：

```math
CR_{clip01}(l) = clip(CR(l), 0, 1)
```

但不建议只保存 clipped 结果，必须保留 raw CR。

---

## 10. 需要补充：浅层偏置诊断

当前手册已经提醒“恢复全部视觉 token 会产生浅层偏置”，但建议把它变成强制输出的诊断项。

### 建议新增配置

```yaml
diagnostics:
  shallow_bias_check: true
  shallow_layers: first_20_percent
  middle_layers: middle_40_percent
  deep_layers: last_20_percent
```

### 建议输出字段

```csv
shallow_mean_cr
middle_mean_cr
deep_mean_cr
top_layer_depth_ratio
```

### 解释规则

如果 Top-3 全部集中在最前 20% 层，应在 summary 中自动写入：

```text
The restoration scores are strongly concentrated in shallow layers, indicating that the result may be dominated by remaining downstream propagation depth rather than adapter editability.
```

中文：

```text
因果恢复分数明显集中在浅层，说明结果可能主要受到恢复后剩余传播深度影响，而不应直接解释为浅层具有最高 Adapter 编辑适宜性。
```

---

## 11. 需要补充：候选层用途说明

当前手册中已经写到该实验不是 Adapter 编辑层真值。建议在用于候选层实验的第 29 节中再强调一次：

```markdown
CMA-Direct 输出的 Top-K 层只能作为 causal restoration candidates，用于与其他定位方法进行诊断性比较。其最终有效性仍需通过真实 Adapter 编辑实验验证。若 CMA-Direct 的 Top-K 与真实 Adapter 最优层不一致，不应视为实现错误，而可能反映 causal restoration 与 editability 之间的目标差异。
```

---

## 12. 建议新增：分阶段运行计划

不要直接全量跑 `7 models × 3 datasets`。

### Stage 1：最小可行 pilot

```yaml
models:
  - llava-v1.5-7b

datasets:
  - EVQA-pilot500

sample_size: 50

alpha_list:
  - 0.5
  - 1.0

seeds:
  - 0
```

检查：

- visual span 是否正确；
- clean/corrupt gap 是否合理；
- 有效样本比例是否在 30%-80%；
- CR 是否大量异常；
- 是否全部集中在 L0/L1。

### Stage 2：跨架构验证

```yaml
models:
  - llava-v1.5-7b
  - blip2-opt-2.7b
  - paligemma-3b
```

目的：

- 验证不同视觉接入方式下 hook 是否稳定；
- 验证 visual span 是否能够统一定位；
- 验证 Q-Former / projector / image token 模型都能跑通。

### Stage 3：全量运行

```yaml
models:
  - blip2-opt-2.7b
  - instructblip-vicuna-7b
  - minigpt-4-vicuna-7b
  - llava-v1.5-7b
  - qwen2.5-vl-3b-instruct
  - paligemma-3b
  - smolvlm-1.7b

datasets:
  - EVQA-pilot500
  - MMKE-visual
  - MMKE-entity
```

只有前两阶段通过后，再进入全量运行。

---

## 13. 建议新增章节清单

建议在当前手册末尾新增以下章节：

```markdown
## 30. 模型适配表：hook路径与visual span获取

## 31. Noise Calibration：噪声强度预校准

## 32. Teacher-forcing答案token对齐规则

## 33. Restore Hook实现规范

## 34. CR异常值与浅层偏置诊断

## 35. 分阶段运行计划

## 36. 主实验恢复范围补充说明
```

其中最重要的是：

1. `主实验恢复范围补充说明`；
2. `visual token span 不默认等于 1:N_v`；
3. `Restore Hook 实现规范`；
4. `Noise Calibration`；
5. `Teacher-forcing 答案 token 对齐规则`。

---

## 14. 可直接替换到手册中的关键文本

### 14.1 恢复范围说明

```markdown
主实验只恢复指定 decoder 层输出后的视觉 token hidden states，而不是恢复整层 hidden states。设第 l 层输出 hidden states 为 H^{l,corrupt}=[H_v^{l,corrupt};H_t^{l,corrupt}]，其中 H_v 表示视觉 token hidden states，H_t 表示文本及答案 token hidden states。恢复操作为 H_v^{l,corrupt}<-H_v^{l,clean}，恢复后得到 H^{l,restore}=[H_v^{l,clean};H_t^{l,corrupt}]。本文不恢复整层 H^l，因为整层恢复会同时恢复文本和答案 token 表征，使分数不再专门反映视觉表征的因果恢复作用。
```

### 14.2 视觉 token span 说明

```markdown
视觉 token 位置集合记为 V，则第 l 层视觉 hidden states 定义为 H_v^l=H^l[:,V,:]。V 必须由具体模型的 processor、chat template 或 input embedding 拼接逻辑显式确定，不默认等于 1:N_v。每次运行必须保存 visual_token_indices、visual_start、visual_end 和 num_visual_tokens；若无法确定视觉 token 位置，样本或模型状态标记为 visual_span_failed。
```

### 14.3 实验定位说明

```markdown
CMA-Direct / Visual Causal Restoration 衡量的是污染视觉输入后，恢复某一层 clean visual hidden states 对目标答案分布的挽救能力。该分数反映 causal restoration capacity，而不是 Adapter editability 本身。由于浅层恢复具有更长的下游传播路径，CR/KCR 可能偏向浅层，因此最终候选层优劣仍应以真实 Adapter 编辑实验中的 Reliability、Generality 和 Locality 为准。
```

---

## 15. 最终建议

当前手册可以继续作为实验基础，但正式运行前建议按以下优先级修改：

### 必改

- 明确恢复视觉 token slice，不恢复整层 hidden state；
- 将 `H_v^l = H^l_{1:N_v}` 改为 `H_v^l = H^l[:, V, :]`；
- 增加每个模型 visual token span 获取方式；
- 增加 restore hook 伪代码；
- 增加 teacher-forcing answer token mask 规则。

### 强烈建议

- 增加 noise calibration；
- 增加 CR 异常值统计；
- 增加浅层偏置诊断；
- 增加分阶段 pilot 运行计划。

### 可选

- 增加目标区域视觉 token 恢复；
- 增加 full-state restoration 作为 ablation；
- 增加 clipped CR 排名作为稳健性分析。

---

## 16. 一句话总结

当前 `CMA-Direct.md` 的实验思想和主流程是可行的，但要作为可执行实验手册，还需要把 **视觉 token 定位、非整层恢复、噪声校准、teacher-forcing 对齐、hook 实现和异常诊断** 写得更明确。补完这些后，可以先跑 LLaVA + EVQA-pilot500 的小规模 pilot，再逐步扩展到多模型多数据集。