# CMA-ModelPred 原知识因果恢复正式重算实验手册

> 适用任务：视觉语言模型视觉编辑层定位第一阶段中的 CMA 候选层重算。  
> 首要诊断组合：`MMKE-entity × Qwen2.5-VL-3B`。  
> 后续正式范围：7 个模型 × 3 个数据集的全部 CMA 组合。  
> 使用对象：负责检查工程、实现目标切换、执行重算和汇总结果的 Codex。  
> 本手册只重算 CMA 候选层，不直接训练或重复训练 Adapter。

---

## 0. 本次重算的最终决定

本次新增独立诊断版本，规范实验ID为：

```text
CMA-ModelPred-Direct
```

`CMA-CausalTrace-ModelPred`只作为描述性别名，不作为结果目录、CSV或JSON中的正式方法ID。

它回答：

> 当视觉输入被污染后，恢复第 l 层的 clean visual-token hidden states，能否恢复基础模型在 clean 输入下原本生成的答案 `model_pred`？

现有七方法正式表中的方法ID继续保留为：

```text
CMA-Direct
```

需要与本诊断版本并列时，可将其写成消歧别名 `CMA-Direct-AltSeq`，但不得重命名或覆盖既有正式产物。

它回答：

> 恢复第 l 层的 clean visual-token hidden states，能否恢复基础模型对反事实编辑目标 `alt` 的支持？

| 版本 | 恢复目标 | 科学含义 | 建议用途 |
|---|---|---|---|
| `CMA-ModelPred-Direct` | `model_pred` | 定位基础模型已有输出的因果恢复层 | 语义更接近经典因果追踪的项目诊断变体 |
| `CMA-Direct`（消歧：`CMA-Direct-AltSeq`） | `alt` | 定位尚未编辑的新答案的恢复层 | 当前七方法正式表所用版本 |

本项目使用“完整生成序列的teacher-forcing平均logprob”，而经典ROME因果追踪主要考察clean模型已支持事实对象的概率。因此，`CMA-ModelPred-Direct`是遵循其目标语义的视觉语言模型扩展，不得写成对ROME原实验协议的逐项完全复现。

首轮只在 `MMKE-entity × Qwen2.5-VL-3B` 上运行 ModelPred 版本，用于验证目标语义是否是当前低覆盖率的主要原因。不得只因为该版本覆盖率更高，就直接替换论文主表中的单个组合。

如果后续决定把 ModelPred 版本作为正式 CMA 基线，必须对全部模型—数据集组合统一重算，不能只替换当前低覆盖组合。

---

# 1. 方法依据与字段选择

## 1.1 经典因果追踪恢复的是 clean 状态已有答案

ROME 的 Causal Tracing 对同一个原事实对象 (o) 执行三次计算：

1. clean run：模型正常预测原事实对象 (o)；
2. corrupt run：污染输入，使模型对 (o) 的预测受损；
3. restore run：在污染输入下恢复某层 clean hidden state，检查 (o) 的概率是否恢复。

其核心量为：

\[
TE=P[o]-P^{corrupt}[o],
\]

\[
IE_l=P^{restore(l)}[o]-P^{corrupt}[o].
\]

这里的 (o) 是 clean 模型已经支持的原事实答案。反事实编辑目标 (o^*) 出现在后续权重编辑阶段，不是 Causal Tracing 阶段的恢复对象。

原文：Kevin Meng et al., *Locating and Editing Factual Associations in GPT*, NeurIPS 2022：  
https://proceedings.neurips.cc/paper_files/paper/2022/file/6f1d43d5a82a37e89b0665b33bf3a182-Paper-Conference.pdf

## 1.2 为什么本项目使用 `model_pred`

ROME 原实验中的 (o) 通常是模型能够预测的旧事实对象。本项目跨 7 个视觉语言模型、3 个数据集运行，而数据集字段 `pred` 存在空值或与当前冻结模型实际输出不一致的问题。因此，本项目使用对应冻结模型确定性生成并缓存的 `model_pred`，作为每个模型 clean 行为的操作化定义。

| 科学概念 | 数据字段 |
|---|---|
| 当前模型 clean 状态的已有输出 | `model_pred` |
| 数据集提供的旧答案 | `pred`，仅附加分析可用 |
| 反事实编辑目标 | `alt` |

本次重算必须使用 `model_pred`，不得运行时回退到 `pred` 或 `alt`。

---

# 2. 已有 AltSeq 结果与本次假设

当前 `MMKE-entity × Qwen2.5-VL-3B` 的 `CMA-Direct`（`CMA-Direct-AltSeq`）正式结果为：

| 项目 | AltSeq 结果 |
|---|---:|
| 输入不同样本 | 636 |
| 非空 `alt` | 636 |
| 样本—alpha—seed 参数对 | 5,724 |
| 有效不同样本 | 43/636（6.76%） |
| 完整有效恢复参数对 | 96/5,724（1.68%） |
| `low_corruption_gap` 参数对 | 5,628 |
| runtime/span/mask/nonfinite 错误 | 0 |
| Top-3 | `L1,L0,L2` |
| 状态 | `low_valid_coverage` |

| alpha | gap 中位数 | 有效不同样本 |
|---:|---:|---:|
| 0.5 | -0.01236 | 13/636 |
| 1.0 | -0.03450 | 19/636 |
| 2.0 | -0.05697 | 27/636 |

预注册假设：`alt` 尚未写入基础模型，clean 输入未必支持 `alt`。视觉污染可能削弱旧答案证据，却不一定降低 `alt` 分数。切换到 clean 模型实际生成的 `model_pred` 后，正向 clean-corrupt gap 和有效恢复覆盖率预计增加。

这只是待验证假设，不得预写成实验结论。

---

# 3. 实验范围

## 3.1 阶段 A：单组合受控诊断

```yaml
dataset: MMKE-entity
model: Qwen2.5-VL-3B
input_unique_samples: 636
```

设计上唯一允许改变的科学变量：

```text
target_field: alt → model_pred
```

其他设置必须与已完成的多噪声、多 seed AltSeq 正式结果一致。但由于现有历史ModelPred缓存缺少部分生成元数据，是否真正达到严格单变量条件还要按第5.1节核验；证据不全时只能称为受控工程诊断。

## 3.2 阶段 B：全组合正式重算

只有明确决定“论文中的正式 CMA 基线采用 `CMA-ModelPred-Direct`”后启动。随后对全部 7 模型 × 3 数据集统一执行，不得只重算覆盖率低的组合。阶段A的单组合结果只能用于目标语义诊断，不能直接替换七方法主表中的 `CMA-Direct`。

---

# 4. 冻结配置

```yaml
method: CMA-ModelPred-Direct
variant: direct_modelpred
dataset: MMKE-entity
model: Qwen2.5-VL-3B

target_field: model_pred
target_source: frozen_deterministic_generation_cache
target_scope: complete_model_pred_sequence
score_type: teacher_forcing_mean_logprob

corruption_location: decoder_visual_input_embeddings
corruption_scope: visual_tokens
noise_type: gaussian
noise_definition: alpha_times_visual_embedding_std
noise_alpha_list: [0.5, 1.0, 2.0]
noise_seeds: [0, 1, 2]
seed_key: dataset/model/sample_id/alpha/seed

restore_location: decoder_block_output
restore_scope: visual_tokens

delta_logprob: 0.05
rank_metric: CR_mean
aux_metric: KCR_mean
primary_aggregation: pair_weighted_mean_CR
ranking_population: common_restore_pairs_all_layers

minimum_valid_unique_samples: 128
minimum_valid_ratio: 0.20
top_k_list: [3, 5]
```

本轮禁止同时修改：

- alpha、seed、delta；
- 噪声定义及视觉 embedding 标准差计算方式；
- visual-token span；
- teacher-forcing shift 和 target mask；
- restore hook 位置；
- CR、KCR 公式；
- 层编号和聚合方式；
- 模型权重、processor、prompt 模板和图像预处理。

否则无法将结果变化归因于 `alt → model_pred`。

---

# 5. ModelPred 缓存与样本验收

## 5.1 缓存要求

`model_pred` 必须由对应冻结模型使用确定性解码提前生成并缓存。CMA 只能读取该缓存，不得在运行过程中重新生成答案。

首要组合的已审计缓存为：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/
ours_direct_qwen_chatfix_repair_g09_gpu1_20260630_091304/
mmke-entity/qwen2.5-vl-3b/model_pred_cache.jsonl
```

实际SHA-256：

```text
fda0e151f948a72ea073d51c0b461069a414d3a1045c8bd97f7c32579c62d4c6
```

该文件共有636行，实际字段为 `sample_i`、`sample_id`、`prompt`、`answer`、`status`、`old_field`；其中 `answer` 才是缓存的 `model_pred` 文本。runner不得假设基础数据JSON自身存在 `model_pred` 字段，必须按唯一 `sample_id` 将缓存连接到636条正式manifest，并验证 `old_field=model_pred`、`status=ok`。

至少记录：

```yaml
do_sample: false
model_revision: <实际值>
processor_revision: <实际值>
prompt_template_hash: <实际值>
image_preprocess_hash: <实际值>
generation_config_hash: <实际值>
model_pred_cache_hash: <实际值>
```

旧缓存没有保存 `generated_token_ids`、首token/EOS、`effective_token_length`、模型revision及完整generation config。不得为这些字段伪造值。阶段A应如实标记旧缓存元数据缺失，并以缓存文本、缓存SHA-256和当前冻结tokenizer建立不可变的 `modelpred_target_manifest`；若未来重新生成缓存，必须新建版本，不能覆盖或混入本次阶段A。

因此，阶段A使用该历史缓存时必须写入 `cache_provenance_status=limited_historical_cache`。只有在模型权重、processor、prompt模板、图像预处理和生成配置均能由同期日志或配置文件核验后，才能改为 `verified`。若无法补齐这些证据，实验仍可作为“固定历史缓存上的工程诊断”运行，但不得声称它与AltSeq构成严格的单变量因果对照。重新生成ModelPred缓存属于新实验版本，不能与本轮历史缓存结果拼接。

## 5.2 逐样本检查字段

```text
sample_id
model_pred_raw
model_pred_normalized
model_pred_token_count
alt
pred
model_pred_is_empty
model_pred_equals_alt
model_pred_equals_pred
target_truncated
skip_reason
```

还必须记录：

```text
cache_value_key = answer
cache_status
cache_old_field
cache_prompt
runtime_prompt
prompt_exact_match
target_token_ids_hash
tokenizer_revision_or_hash
```

缓存中的 `prompt` 必须与本次运行实际送入模型的prompt逐样本完全一致；不一致时应判为 `cache_prompt_mismatch` 并停止受控实验，不能继续把差异只归因于目标字段。

只允许执行与 AltSeq 管线一致的最小文本处理。不得为提高覆盖率对 `model_pred` 做语义改写、答案抽取或人工纠正。允许使用冻结tokenizer把缓存的 `answer` 文本转换为目标token，但这不是重新生成 `model_pred`；转换后的token序列和哈希必须在运行前冻结。

## 5.3 序列边界

ModelPred 版本必须复用 AltSeq 完全相同的：

- 答案拼接方式；
- BOS/EOS 处理；
- 最大目标长度和截断方向；
- label shift；
- target mask。

不得只给 `model_pred` 新增或删除 EOS。若截断，必须记录原 token 数、保留 token 数和原因。

这里的 `complete_model_pred_sequence` 仅表示“使用缓存 `answer` 字符串经冻结tokenizer得到的全部目标token”，不表示缓存文本一定是语义完整句子，也不能据此还原原始生成时未保存的token流。即使缓存文本以半句结束，也必须原样使用，禁止自动补全、清洗或追加标点。BOS/EOS只能由与AltSeq相同的目标构造函数统一处理。

## 5.4 排除规则

| 状态 | 处理 |
|---|---|
| `model_pred` 为空 | 排除并记录 `empty_model_pred` |
| 图像缺失/损坏 | 排除并记录实际原因 |
| visual span 无法确定 | 标记工程失败，不静默跳过 |
| target mask 为空 | 标记工程失败，不静默跳过 |
| 非有限 clean/corrupt 分数 | 排除相应参数对并记录 |
| `model_pred == alt` | 不作为空样本；单独记录目标重合 |

已知首要组合中636条缓存记录均为 `status=ok`、`answer`文本非空，且0条 `model_pred == alt`；唯一sample ID哈希为 `c98a15ccaaeb48a46a1a1536f1ba7891d0b00184029d5550434cc3306c70215b`。但旧缓存缺少token级生成元数据，因此目前只能证实文本非空，不能倒推出首token是否EOS或原始生成时的有效token长度。正式运行前仍需按实际缓存重新校验，并在报告中保留这项证据边界。

---

# 6. CMA-ModelPred 计算公式

设缓存模型输出为：

\[
y_i^{old}=y_i^{model\_pred}=(y_{i,1},\ldots,y_{i,T_i}).
\]

## 6.1 Clean

\[
s_i^{clean}=\frac{1}{T_i}\sum_{t=1}^{T_i}
\log p_\theta(y_{i,t}^{old}\mid x_i^{clean},y_{i,<t}^{old}).
\]

同时缓存各层 clean visual-token hidden states：

\[
H_{i,l}^{v,clean}.
\]

## 6.2 Corrupt

只对 decoder 输入端 visual embeddings 加噪声：

\[
H_i^{v,corrupt}=H_i^{v,clean}+\alpha\sigma_v\epsilon,
\qquad \epsilon\sim\mathcal N(0,I).
\]

\[
s_i^{corrupt}=\frac{1}{T_i}\sum_{t=1}^{T_i}
\log p_\theta(y_{i,t}^{old}\mid x_i^{corrupt},y_{i,<t}^{old}).
\]

\[
gap_i=s_i^{clean}-s_i^{corrupt}.
\]

只有满足下式的样本—alpha—seed 参数对进入逐层恢复：

\[
gap_i>0.05.
\]

## 6.3 Restore

在污染输入下恢复第 (l) 层 visual-token hidden states：

\[
H_{i,l}^{v,corrupt}\leftarrow H_{i,l}^{v,clean}.
\]

\[
s_i^{restore}(l)=\frac{1}{T_i}\sum_{t=1}^{T_i}
\log p_\theta(y_{i,t}^{old}\mid x_i^{restore(l)},y_{i,<t}^{old}).
\]

## 6.4 分数

\[
CR_i(l)=\frac{s_i^{restore}(l)-s_i^{corrupt}}
{s_i^{clean}-s_i^{corrupt}+\epsilon}.
\]

\[
KCR_i(l)=\frac{KL_i^{corrupt}-KL_i^{restore}(l)}
{KL_i^{corrupt}+\epsilon}.
\]

\[
S_{CMA}(l)=\operatorname{mean}_{i,\alpha,r}CR_i(l,\alpha,r).
\]

主排序仅使用 `CR_mean`；`KCR_mean` 只用于诊断和并列层排序。

---

# 7. 代码实施流程

## 7.1 只读检查仓库

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2

git status --short

rg -n "CMA-Direct|CMA_Direct|target_field|delta_logprob|noise_alpha|s_clean|s_corrupt|s_restore|CR_mean" .
```

Codex 必须：

1. 保留用户已有修改；
2. 不猜测 runner 文件名；
3. 找到 AltSeq runner、配置、汇总程序和输出目录；
4. 记录代码 commit、工作树状态和现有配置哈希；
5. 查明 `target_field: alt` 是配置项还是硬编码。

## 7.2 建立独立版本

优先采用“同一 runner + 显式配置”的方式：

```yaml
target_field: model_pred
target_cache_value_key: answer
method_name: CMA-ModelPred-Direct
variant: direct_modelpred
```

禁止全局替换源代码中的 `alt`。实现应显式读取：

```python
cache_row = model_pred_cache_by_sample_id[sample["sample_id"]]
assert cache_row["status"] == "ok"
assert cache_row["old_field"] == "model_pred"
assert cache_row["prompt"] == runtime_prompt
target_text = cache_row["answer"]
```

并验证：

```text
target_field ∈ {alt, model_pred}
```

这里的 `target_field=model_pred` 是科学口径标识，不代表数据集样本中一定存在同名字段。首要组合必须从经过SHA-256固定的独立缓存读取 `answer`，按 `sample_id` 一对一连接；缺失ID、重复ID、额外ID或prompt不一致均应拒绝运行。

日志首部必须打印：

```text
method_name
variant
dataset
model
target_field
target_scope
noise_alpha_list
noise_seeds
delta_logprob
output_dir
config_hash
model_pred_cache_hash
```

## 7.3 输出目录隔离

建议新目录：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/
cma_modelpred_formal_multinoise_multiseed_v1_<YYYYMMDD>/
mmke_entity/qwen2_5_vl_3b/formal636
```

不得覆盖：

```text
cma_direct_formal_multinoise_multiseed_v1_20260906/formal636
```

## 7.4 配置冻结

运行前生成：

```text
config_frozen.yaml
config_hash.txt
run_manifest.json
```

哈希至少覆盖方法名、目标字段、模型/processor/prompt/image preprocess、ModelPred 缓存、alpha/seed/delta、visual span、hook、score、aggregation、Top-K 和代码 commit。

50 条预检通过后不得修改冻结配置；修改时必须新建版本目录和哈希。

---

# 8. 单元测试与两条冒烟测试

## 8.1 单元测试

- [ ] 实际读取 `model_pred`，没有读取 `alt` 或 `pred`；
- [ ] target token 解码后与缓存一致；
- [ ] target mask 非空且只覆盖目标序列；
- [ ] prompt、visual、padding label 均为 `-100`；
- [ ] visual-token count 与 decoder visual embeddings 数一致；
- [ ] 空 visual mask 加噪后 logits 不变化；
- [ ] 正常 visual mask 加噪后输出分布发生变化；
- [ ] restore hook 只替换指定层 visual tokens；
- [ ] 同一样本、alpha、seed 在全部层使用相同噪声；
- [ ] seed key 不包含 layer；
- [ ] 层号与 Adapter 插入层定义一致；
- [ ] AltSeq 旧目录没有被修改。

## 8.2 两条样本

固定：

1. 一条 visual span、mask、hook 已知正常的工程正控制样本；
2. 一条 `model_pred` 与 `alt` 明显不同的代表性样本。

每条至少保存：

```text
sample_id
model_pred
alt
target_token_ids
target_mask_count
visual_token_start/end/count
s_clean
s_corrupt(alpha, seed)
clean_corrupt_gap
s_restore(layer, alpha, seed)
CR(layer, alpha, seed)
```

## 8.3 冒烟验收

冒烟不要求两条样本都通过 gap，但必须满足：

1. clean、corrupt 分数有限；
2. 污染确实改变输出分布；
3. 通过 gap 的参数对完成全部合法层恢复；
4. 不同层恢复分数不是完全常数；
5. 同 seed 重跑结果一致，换 seed 后噪声变化；
6. 日志明确显示 `target_field=model_pred`。

未通过时停止，不得进入 50 条预检。

---

# 9. 固定 50 条预检

从正式 manifest 按确定性规则选择 50 条并保存：

```text
precheck50_sample_ids.txt
```

不得根据 gap 或结果事后换样本。运行完整的 `3 alpha × 3 seed`；只有通过 gap 的参数对执行全层恢复。

至少输出：

```text
input_unique_samples
nonempty_model_pred_samples
cache_prompt_exact_match_samples
cache_prompt_mismatch_samples
cache_provenance_status
model_pred_token_count_min_p25_median_p75_p95_max
alt_token_count_min_p25_median_p75_p95_max
model_pred_target_truncated_samples
alt_target_truncated_samples
total_sample_alpha_seed_pairs
finite_corruption_pairs
positive_gap_pairs
valid_restore_pairs
valid_unique_samples
low_corruption_gap_pairs
missing_restore_pairs
nonfinite_gap_pairs
nonfinite_restore_pairs
runtime_error_pairs
```

每个 alpha 输出 gap 均值、中位数、P05、P25、P75、P95、正值比例、`gap > 0.05` 比例、有效不同样本和有效参数对。

工程通过条件：

- 50 条全部完成基础处理；
- 非空目标数量符合预期；
- nonfinite、runtime、span、mask、hook 错误均为 0；
- 每个有效参数对都有全部合法层的有限恢复记录；
- 汇总计数能从长表逐行重算；
- 所有产物配置哈希一致。
- 50条的缓存prompt与运行时prompt逐条一致；
- 两类目标的token长度、截断数量均可由冻结manifest重算。

覆盖率不是工程通过的硬条件。即使仍低，也不得临时修改 alpha 或 delta。

---

# 10. 636 条正式重算

## 10.1 启动前检查

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2

git status --short

sha256sum <实际ModelPred配置文件>

test -s <实际model_pred缓存文件>

test ! -e <正式输出目录>/summary.json
```

尖括号内容必须按仓库实际路径替换，不能原样执行。

## 10.2 命令模板

Codex 必须先识别实际 runner 接口，再生成最终命令，不得猜脚本名。

```bash
nohup python <实际CMA运行脚本> \
  --config <冻结的ModelPred配置文件> \
  --dataset mmke_entity \
  --model qwen2_5_vl_3b \
  --target-field model_pred \
  --output-dir <独立ModelPred正式结果目录> \
  > <独立日志文件> 2>&1 &
```

如果实际 runner 不支持这些参数，以真实接口生成等价命令，并把最终展开配置写入 `run_manifest.json`。

## 10.3 断点续跑

断点至少记录：

```text
sample_id
alpha
seed
layer
output_offset
config_hash
model_pred_cache_hash
```

哈希不一致时拒绝恢复；不得把旧 AltSeq 记录作为 ModelPred 已完成记录。

## 10.4 运行监控

只监控进程、日志、GPU/显存、错误数、完成参数对和预计剩余时间。不得在运行中根据覆盖率调整 alpha、seed 或 delta。

---

# 11. 输出文件与计数规范

正式目录至少包含：

```text
config_frozen.yaml
config_hash.txt
run_manifest.json
sample_manifest_modelpred.csv
modelpred_target_manifest.csv
precheck50_sample_ids.txt
cma_corruption_pairs.csv
cma_restore_long.csv
cma_sample_alpha_seed_long.csv
cma_layer_alpha_seed_scores.csv
cma_candidate_stability.csv
cma_formal_top3_top5.json
cma_coverage_summary.json
alt_vs_modelpred_comparison.csv
summary.json
run.log
```

为使实现层面尽量做到相对已完成AltSeq正式runner只改变目标字段，主产物优先沿用上述CSV/JSON文件名与schema。可额外输出Parquet镜像以便分析，但Parquet不得成为唯一真值来源，也不得因此改变聚合逻辑。

## 11.1 污染阶段长表

每个样本—alpha—seed 一行：

```text
dataset
model
sample_id
target_field
target_hash
target_token_count
alpha
seed
s_clean
s_corrupt
clean_corrupt_gap
gap_pass
pair_status
skip_reason
config_hash
```

gap 不通过也必须保留记录，不能只增加计数器。

## 11.2 恢复阶段长表

每个有效样本—alpha—seed—layer 一行：

```text
dataset
model
sample_id
target_field
alpha
seed
layer
s_clean
s_corrupt
s_restore
CR
KCR
visual_token_count
restore_complete
config_hash
```

只有全部合法层均完整、有限的参数对才能进入正式共同排序总体。

## 11.3 参数对状态

每个参数对只能有一个最终状态：

```text
runtime_error
→ nonfinite_gap
→ low_corruption_gap
→ missing_or_nonfinite_restore
→ valid_restore_pair
```

必须分开统计：唯一 `sample_id`、样本—alpha—seed 参数对、参数对—layer 恢复记录。不得混用。

---

# 12. 层排序与 Top-K

正式排序总体仅使用：

```text
gap > 0.05
AND 所有合法层均有完整有限的 s_restore/CR
```

主聚合使用 `pair_weighted_mean_CR`，同时输出 `sample_balanced_mean_CR` 诊断。

排序规则：

1. `CR_mean` 从大到小；
2. 并列时 `KCR_mean` 大者优先；
3. 再并列时有效恢复数更多者优先；
4. 最后按层号从小到大。

输出：

```text
raw_top3
clean_top3
raw_top5
clean_top5
removed_layers
```

本方法为 Direct，不执行 Pre-shift。

---

# 13. 覆盖率与状态

```text
minimum_valid_ratio = 0.20
minimum_valid_samples_floor = 30
minimum_valid_unique_samples
= max(30, ceil(0.20 × input_unique_samples))
```

对本次636条首要组合，`minimum_valid_unique_samples=128`。扩展到其他数据集时不得固定沿用128：例如214条输入对应43，500条输入对应100，636条输入对应128。

| 条件 | 状态 |
|---|---|
| 无有效恢复参数对 | `no_valid_cma_sample` |
| `0 < valid_unique_samples < minimum_valid_unique_samples` | `low_valid_coverage` |
| 覆盖达标、工程验收通过且候选稳定 | `done` |
| 覆盖达标、工程验收通过但候选不稳定 | `candidate_ranking_unstable` |
| span/mask/hook/恢复完整性错误 | `engineering_failure` |

同时报告 `valid_unique_ratio`、`valid_pair_ratio`、按 alpha、seed、alpha×seed 的覆盖率。

候选稳定性沿用现有AltSeq正式实验的验收口径，不得因ModelPred结果而另设标准：

1. 多数有支持的 alpha×seed 组与汇总Top-3至少重合2层；
2. 各有支持组相对汇总Top-3的平均Jaccard不低于0.50；
3. 汇总Top-3至少同时得到2个不同alpha和2个不同seed的有效支持；
4. 任一条件未满足时，即使覆盖率达到20%，也标记为 `candidate_ranking_unstable`，不得标记为 `done`。

---

# 14. AltSeq 与 ModelPred 受控对照

对照设计必须保证样本 ID、模型/processor、prompt、图像预处理、visual span、alpha、seed、delta、hook、层范围、聚合和 Top-K 规则一致；设计上唯一允许差异是目标字段和目标token序列。若历史缓存的模型或生成配置来源不能完整核验，比较表必须显式标记 `limited_historical_cache`，结论降级为诊断性证据。

| 项目 | CMA-Direct（AltSeq） | CMA-ModelPred-Direct |
|---|---:|---:|
| 输入样本 | 636 | 待回填 |
| 非空目标 | 636 | 待回填 |
| 有效不同样本 | 43 | 待回填 |
| 唯一样本有效率 | 6.76% | 待回填 |
| 有效恢复参数对 | 96/5,724 | 待回填 |
| 参数对覆盖率 | 1.68% | 待回填 |
| gap 中位数 | -0.02793 | 待回填 |
| 负 gap 比例 | 4,690/5,724（81.94%） | 待回填 |
| 目标token长度分布 | 运行前用同一冻结tokenizer补算 | 待回填 |
| 目标截断样本数 | 运行前用同一目标构造函数补算 | 待回填 |
| Top-3 | L1,L0,L2 | 待回填 |
| Top-5 | L1,L0,L2,L3,L4 | 待回填 |
| 状态 | low_valid_coverage | 待回填 |

计算：

```text
Top3_overlap_count
Top3_Jaccard
Top5_overlap_count
Top5_Jaccard
Spearman_all_layers
Kendall_all_layers
rank_shift_per_layer
```

并比较 pair-weighted 与 sample-balanced 排名、9 个 alpha×seed 组、每组支持量、bootstrap Top-K 入选频率和层分数置信区间。

---

# 15. 结果判断规则

## 15.1 M1：覆盖率明显恢复

本次636条首要组合的典型条件：

```text
valid_unique_samples >= 128
```

且正 gap 比例和 gap 中位数明显高于 AltSeq。

结论：在工程检查、样本口径和冻结配置均一致的前提下，结果支持AltSeq低覆盖主要来自目标语义不匹配，CMA更适合定位clean模型已有输出的因果恢复层。由于ModelPred序列的内容和长度同时改变，还必须报告两类目标的token长度与截断分布，不能把所有差异无条件归因于“语义”单一因素。

处理：保留两套结果；若论文采用原语义基线，再启动全部 7×3 ModelPred 重算，不立即以单组合替换全局主表。

## 15.2 M2：覆盖提高但仍低于 128

结论：目标语义解释了部分低覆盖，但视觉污染协议、模型视觉依赖或完整序列计分仍限制覆盖率。

处理：保留 `low_valid_coverage`；比较完整 gap 分布；不降低 delta；不继续搜索 alpha。

## 15.3 M3：覆盖几乎不变或更低

结论：AltSeq 目标语义不是唯一原因，或视觉污染对该模型生成序列的破坏较弱。

检查 clean 模型对自身生成序列的分数、模型是否主要依赖文本先验、完整序列是否包含大量视觉无关模板文本。如需测试第一 token、实体 span 或更强噪声，另建明确命名的敏感性实验。

## 15.4 M4：工程错误

发现 visual span、mask、hook、层号、缓存错配或恢复缺失时：停止任务、保存日志、修复后重新完成单元测试、2 条冒烟和 50 条预检，并使用新哈希和目录重跑。

---

# 16. 候选层并集与 Adapter 训练

阶段 A 的单组合 ModelPred 结果暂不替换原候选层，也不自动启动 Adapter 训练。先输出：

```text
old_alt_topK
new_modelpred_topK
overlap_layers
modelpred_only_layers
alt_only_layers
```

若正式采用 ModelPred 基线，在统一范围重算后更新候选来源：

```text
new_layers_to_train = ModelPred_CMA_TopK - already_trained_layers
```

已训练层复用；只训练新增差集；保留历史 AltSeq 候选和训练结果；不得根据 Adapter 得分反向选择 CMA target、alpha、seed 或 delta。

---

# 17. 7 模型 × 3 数据集扩展规则

统一流程：

```text
读取对应模型的 model_pred 缓存
→ 样本/缓存审计
→ 2 条冒烟
→ 固定 50 条预检
→ 全量 ModelPred CMA
→ 覆盖率/层排序/稳定性
→ 与同组合 AltSeq 比较
```

禁止：

- 只对低覆盖组合使用 ModelPred；
- 某些模型使用 `pred`、另一些使用 `model_pred`；
- `model_pred` 为空时回退到 `alt`；
- 按最终候选效果选择不同噪声网格；
- 把无法回答样本写成零分继续排序；
- 跨模型比较绝对 CR 值并直接解释为定位能力强弱。

---

# 18. summary.json 最低字段

```json
{
  "method": "CMA-ModelPred-Direct",
  "variant": "direct_modelpred",
  "dataset": "MMKE-entity",
  "model": "Qwen2.5-VL-3B",
  "target_field": "model_pred",
  "target_cache_value_key": "answer",
  "target_scope": "complete_model_pred_sequence",
  "score_type": "teacher_forcing_mean_logprob",
  "cache_provenance_status": "limited_historical_cache",
  "cache_prompt_exact_match_samples": null,
  "cache_prompt_mismatch_samples": null,
  "model_pred_token_count_summary": null,
  "alt_token_count_summary": null,
  "model_pred_target_truncated_samples": null,
  "alt_target_truncated_samples": null,
  "input_unique_samples": 636,
  "nonempty_target_samples": null,
  "noise_alpha_list": [0.5, 1.0, 2.0],
  "noise_seeds": [0, 1, 2],
  "delta_logprob": 0.05,
  "total_sample_alpha_seed_pairs": null,
  "finite_corruption_pairs": null,
  "low_corruption_gap_pairs": null,
  "valid_restore_pairs": null,
  "common_restore_pairs_all_layers": null,
  "valid_unique_samples": null,
  "valid_ratio_unique": null,
  "valid_ratio_pairs": null,
  "rank_metric": "CR_mean",
  "aux_metric": "KCR_mean",
  "primary_aggregation": "pair_weighted_mean_CR",
  "top3": null,
  "top5": null,
  "coverage_status": null,
  "config_hash": null,
  "model_pred_cache_hash": null,
  "code_commit": null,
  "failure_reason": null
}
```

正式结束时不得保留 `null`，除非实验失败，并填写 `failure_reason`。

---

# 19. Codex 交付物

1. 代码与配置改动清单；
2. 2 条冒烟测试报告；
3. 50 条预检报告；
4. 636 条正式日志与配置哈希；
5. 污染阶段和恢复阶段长表；
6. 覆盖率、gap 分布、Top-3/Top-5；
7. 9 个 alpha×seed 组稳定性；
8. AltSeq 与 ModelPred 对照表；
9. M1/M2/M3/M4 判定；
10. 是否建议启动全部 7×3 重算；
11. 候选变化时输出新增 Adapter 层差集，但不自动开训。

---

# 20. 最终检查清单

## 方法语义

- [ ] 正式实验ID为 `CMA-ModelPred-Direct`；
- [ ] 目标字段为缓存 `model_pred`；
- [ ] 解释为原有 clean 输出的因果恢复层；
- [ ] AltSeq 以独立名称保留。

## 工程一致性

- [ ] 样本 ID、模型、processor、prompt、图像预处理与 AltSeq 一致；
- [ ] visual span、hook、层号、alpha、seed、delta 一致；
- [ ] teacher-forcing 与序列归一化一致；
- [ ] 已按唯一 `sample_id` 连接缓存，并核验 `answer`、`status=ok`、`old_field=model_pred`；
- [ ] 缓存prompt与运行时prompt逐样本完全一致；
- [ ] 已冻结目标token manifest及其哈希；
- [ ] 已记录缓存来源为 `verified` 或 `limited_historical_cache`；
- [ ] 只有缓存来源核验完整时才声明唯一变化是 target field；
- [ ] 旧结果未覆盖；
- [ ] 配置和缓存有哈希。

## 统计可靠性

- [ ] 三种计数单位分开；
- [ ] gap 不通过的参数对有记录；
- [ ] 有效参数对具有全层完整有限恢复值；
- [ ] 汇总可由长表重算；
- [ ] 两种聚合和各 alpha×seed 稳定性已报告；
- [ ] 已报告AltSeq/ModelPred目标token长度与截断分布；
- [ ] 未降低 delta 或事后搜索噪声。

## 正式比较

- [ ] 已与 AltSeq 做受控对照；
- [ ] 已比较覆盖率、gap 和 Top-K；
- [ ] 已判定 M1/M2/M3/M4；
- [ ] 单组合结果未静默替换全局主表；
- [ ] 若采用正式 ModelPred 基线，计划统一覆盖全部组合。

---

# 21. 可直接交给 Codex 的执行指令

```text
请严格按照《CMA-ModelPred 原知识因果恢复正式重算实验手册》执行。

当前先完成阶段 A：MMKE-entity × Qwen2.5-VL-3B 的 CMA-ModelPred-Direct 受控重算。

1. 先只读检查仓库、现有 CMA-AltSeq runner、配置、缓存和结果目录，不猜测脚本名；
2. 保留用户已有修改和全部历史结果；
3. 建立独立的 CMA-ModelPred-Direct 版本和输出目录；
4. 只将目标从alt切换为冻结缓存中按sample_id连接的 `answer`（科学字段标记为 `target_field=model_pred`），不得假设基础数据JSON包含同名字段，不得补全或改写缓存文本；
5. alpha=[0.5,1.0,2.0]、seed=[0,1,2]、delta=0.05 及其他协议保持不变；
6. 依次完成单元测试、2 条冒烟、固定 50 条预检和 636 条正式重算；
7. 每阶段通过验收后再进入下一阶段；
8. 保存污染阶段全量长表和有效参数对的全层恢复长表；
9. 输出覆盖率、gap、Top-3/Top-5、稳定性、目标token长度/截断分布和 AltSeq/ModelPred 对照；
10. 按手册判定 M1/M2/M3/M4；
11. 不降低阈值、不搜索更强噪声、不启动 Adapter 训练；
12. 实际接口与模板不同时以代码真实接口为准，但保持冻结科学协议并保存生效配置和哈希；
13. 旧缓存生成元数据无法完整核验时标记 `limited_historical_cache`，不得把结果表述为严格单变量因果对照。

遇到 visual span、mask、hook、缓存错配或恢复完整性问题时立即停止，保存证据并报告，不得带错继续全量运行。
```

---

# 22. 论文表述模板

若 ModelPred 覆盖率明显恢复：

> Following the causal-tracing target semantics, CMA-ModelPred-Direct measures whether restoring clean visual hidden states recovers an output already produced by the frozen base model. On MMKE-Entity with Qwen2.5-VL, replacing the counterfactual target sequence with the cached clean model prediction substantially increased the proportion of corruption conditions that produced a measurable probability drop. Under matched samples, model, corruption, restoration, and aggregation settings, this supports the interpretation that the low coverage of CMA-Direct-AltSeq primarily reflects a mismatch between causal restoration and a target answer not yet encoded in the base model, rather than a shared sample-availability or implementation failure. This project variant uses full-sequence teacher-forced mean log-probability and is not an exact reproduction of the original token-level causal-tracing protocol.

若覆盖率仍低：

> CMA-ModelPred-Direct retained low valid coverage under the preregistered visual corruption protocol. Because the engineering checks passed and the threshold was not relaxed post hoc, the result suggests that target choice alone cannot explain the low coverage; weak dependence on the corrupted visual representation, full-sequence scoring, or target-length composition may also contribute.

不得在得到实际结果前预选其中一种表述。
