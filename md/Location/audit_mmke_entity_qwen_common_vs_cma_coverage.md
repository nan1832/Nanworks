# MMKE-entity × Qwen2.5-VL 定位实验样本覆盖率只读审计

- 审计日期：2026-09-03（Asia/Shanghai）
- 目标组合：`MMKE-entity × Qwen2.5-VL-3B`
- 预期样本数：636
- 审计性质：只读；未修改服务器代码、配置、JSON、CSV、汇总文件，未重跑定位实验或 Adapter 训练
- 唯一 ID 口径：统一规范为 `mmke_<row_index>`；VisEdit 原始整数 ID 在比较时仅做等价规范化
- 集合哈希：对唯一 ID 做字典序排序，以换行连接后计算 SHA-256

## 1. 核心结论

```text
total_samples
→ nonempty_model_pred_samples
→ common_localization_samples
→ cma_valid_samples

636 → 636 → 636 → 9
```

```text
classification = B_cma_specific_low_valid_coverage
```

**已证实：** 六种基于样本的定位方法均实际输入了同一批636条样本；Ours、LGA、SaLEM、Perturb-KL、VisEdit均有636条样本进入各自层分数计算，只有CMA在内部污染有效性过滤后降到9条。CMA逐样本日志中其余627条全部明确记录为`low_corruption_gap`，而不是空`model_pred`、缺图、空`alt`或运行异常。

因此，当前`9/636`不是“所有方法共同低覆盖”，而是当前CMA污染设置（`noise_scale=1.0`、`seed/repeat=2026`、`gap>0.05`）的**方法内部有效覆盖率过低**。

`Middle-Prior-Direct`只依赖层深先验，不依赖定位样本，因此不纳入本次样本集合交集。

## 2. 实际读取的文件路径

### 2.1 基础数据与模型输出

- `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000/data/vqa_mmke_entity_train_evqa_compat.json`
- `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/ours_direct_qwen_chatfix_repair_g09_gpu1_20260630_091304/mmke-entity/qwen2.5-vl-3b/model_pred_cache.jsonl`
- LGA目录中的同名`model_pred_cache.jsonl`也已交叉读取；其ID和内容口径与Ours修复版缓存一致。

### 2.2 Ours-Direct

- `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/ours_direct_qwen_chatfix_repair_g09_gpu1_20260630_091304/mmke-entity/qwen2.5-vl-3b/ours_direct_sample_layer_scores.jsonl`
- 同目录`progress.jsonl`、`ours_direct_layer_scores.csv`、`summary.json`

### 2.3 LGA-Param-Direct-AltModelPred

- `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/lga_param_direct_altmodelpred_7models_3datasets_g09_gpu0_optimized_20260702_114900/mmke-entity/qwen2.5-vl-3b/progress.jsonl`
- 同目录`skipped_samples.jsonl`、`layer_failure_log.jsonl`、`layer_scores.csv`、`summary.json`

### 2.4 SaLEM-Alt-Direct

- `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/salem_candidate_layers_7models_3data_current_alloc_20260621_203335/mmke-entity/qwen2.5-vl-3b/progress.jsonl`
- 同目录`salem_layer_scores.csv`、`summary.json`

### 2.5 Perturb-KL-Direct-AltSeq

- `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/perturb_kl_direct_7models_3datasets_g08_gpu0_20260622_211701/mmke-entity/qwen2.5-vl-3b/progress.jsonl`
- 同目录`perturb_kl_scores_long.csv`、`perturb_kl_layer_scores.csv`、`summary.json`

### 2.6 VisEdit-Contrib-Pre-KeyToken

- `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/visedit_keytoken_mmke_7models_job3044841_20260704_192247/full/mmke-entity/qwen2.5-vl-3b/sample_manifest.csv`
- 同目录`key_token_manifest.csv`、`sample_layer_contribution.csv`、`summary.json`

### 2.7 CMA-Direct

- `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/cma_direct_v13_full_g09_gpu0_20260703_134818/mmke-entity/qwen2.5-vl-3b/progress.jsonl`
- 同目录`cma_direct_layer_scores.csv`、`summary.json`、`candidates_clean.json`

### 2.8 为解释逐样本状态而只读检查的实现

- `VisEdit-main/scripts/run_ours_direct_candidate_layers_qwen_chatfix.py`
- `scripts/run_lga_param_direct_altmodelpred_candidate_layers.py`
- `scripts/run_lga_param_direct_altmodelpred_lowmem_candidate_layers.py`
- `VisEdit-main/scripts/run_salem_candidate_layers.py`
- `VisEdit-main/scripts/run_perturb_kl_direct_candidate_layers.py`
- `VisEdit-main/scripts/run_visedit_keytoken_candidate_layers.py`
- `VisEdit-main/scripts/run_cma_direct_candidate_layers.py`

## 3. 基础模型输出统计

| 项目 | 独立重算值 |
|---|---:|
| total_samples | 636 |
| generated_model_pred_samples | 636 |
| nonempty_model_pred_samples | 636 |
| empty_model_pred_samples | 0 |
| model_pred_equal_alt_samples | 0 |
| model_pred_not_equal_alt_samples | 636 |
| missing_model_pred_samples | 0 |
| duplicate_sample_ids | 0 |
| 唯一ID哈希 | `c98a15ccaaeb48a46a1a1536f1ba7891d0b00184029d5550434cc3306c70215b` |

### 3.1 token级空输出核验限制

**已证实：** 636条缓存记录均存在，`status=ok`且原始保存的`answer`均为非空文本。

**当前证据不足：** 这批正式缓存的636条记录全部未保存`generated_token_ids`、首个生成token、EOS标记和`effective_token_length`。因此无法仅凭现存文件重新验证“首token是否EOS”和“有效token长度是否为0”。这不是发现了空输出，而是旧缓存缺少token级审计字段。现存文本证据足以否定“Qwen只有9条非空输出”，但如需完整token级可复现证明，只能在未来重新生成缓存时增加这些字段；本次按限制没有重跑。

### 3.2 空model_pred随机样本

空输出为0条，因此没有可列出的20条空样本。

### 3.3 非空model_pred固定随机样本20条

随机种子固定为`20260903`。为控制报告长度，长文本显示节选；原文仍保存在上述数据与缓存文件中。由于缓存未保留token元数据，首token、EOS和有效token长度均记为`NA`。

| sample_id | src | alt（节选） | model_pred（节选） | 首token | EOS | 有效token长度 |
|---|---|---|---|---|---|---|
| mmke_528 | bird information | Common eider | Herring Gull (Larus argentatus) | NA | NA | NA |
| mmke_347 | bird information | Blue-winged warbler | tailorbird | NA | NA | NA |
| mmke_241 | musical group information | The Boswell Sisters | The Wanted | NA | NA | NA |
| mmke_313 | bird information | Emperor penguin | Caracara | NA | NA | NA |
| mmke_542 | plant information | Cirsium vulgare | spider lily / Lycoris radiata | NA | NA | NA |
| mmke_418 | insect information | Episyrphus balteatus | cicada | NA | NA | NA |
| mmke_324 | plant information | Lysichiton americanus | scabious / scabiosa | NA | NA | NA |
| mmke_508 | cat information | African wildcat | blue-eyed fluffy cat | NA | NA | NA |
| mmke_405 | dog information | Pomeranian dog | black German Shepherd | NA | NA | NA |
| mmke_221 | human information | Alicia Keys | Richard Nixon | NA | NA | NA |
| mmke_563 | human information | Stephen Decatur | Sachin Tendulkar | NA | NA | NA |
| mmke_573 | bird information | Canada jay | Great Grey Owl | NA | NA | NA |
| mmke_212 | monkey information | Geoffroy's spider monkey | Colobus monkey | NA | NA | NA |
| mmke_293 | human information | Robert Morris | Oliver Cromwell | NA | NA | NA |
| mmke_307 | human information | Jacqueline Kennedy Onassis | born on 1980-02-13 | NA | NA | NA |
| mmke_478 | bird information | Downy woodpecker | Java sparrow | NA | NA | NA |
| mmke_114 | car information | Nissan Juke | BMW X5 | NA | NA | NA |
| mmke_349 | plant information | Eremalche rotundifolia | Fuchsia magellanica | NA | NA | NA |
| mmke_471 | beetle information | Pelidnota punctata | stag/rhinoceros beetle | NA | NA | NA |
| mmke_351 | musical group information | The Drifters | Fleetwood Mac | NA | NA | NA |

## 4. 各方法样本覆盖率

| 方法 | method_input_samples | method_valid_samples | method_excluded_samples | excluded_reason_counts | valid_sample_id_hash | 证据类型 |
|---|---:|---:|---:|---|---|---|
| Ours-Direct | 636 | 636 | 0 | `{}` | `c98a15ccaaeb48a46a1a1536f1ba7891d0b00184029d5550434cc3306c70215b` | 逐样本layer score直接提取 |
| LGA-Param-Direct-AltModelPred | 636 | 636 | 0 | `{}` | `c98a15ccaaeb48a46a1a1536f1ba7891d0b00184029d5550434cc3306c70215b` | progress逐ID直接提取；skipped为空 |
| SaLEM-Alt-Direct | 636 | 636 | 0 | `{}` | `c98a15ccaaeb48a46a1a1536f1ba7891d0b00184029d5550434cc3306c70215b` | **根据过滤逻辑重建**：progress保存0–635顺序索引但未保存sample_id；无错误 |
| Perturb-KL-Direct-AltSeq | 636 | 636 | 0 | `{}` | `c98a15ccaaeb48a46a1a1536f1ba7891d0b00184029d5550434cc3306c70215b` | progress逐ID直接提取 |
| VisEdit-Contrib-Pre-KeyToken | 636 | 636 | 0 | `{}` | `c98a15ccaaeb48a46a1a1536f1ba7891d0b00184029d5550434cc3306c70215b` | sample_manifest直接提取；整数ID规范化为mmke前缀 |
| CMA-Direct | 636 | 9 | 627 | `low_corruption_gap=627` | `b6f0a83274cb9f18ab338a795c61f232fcdd27bb9b18ac738083367b7474fcb4` | progress逐ID与最终状态直接提取 |

本组合没有发现`empty_model_pred`、`model_pred_equal_alt`、`old_new_same_after_norm`、`missing_image`、`empty_alt`、`nonfinite_gradient`、`invalid_visual_span`、`target_mask_empty`或`runtime_error`造成的样本排除。CMA的627条排除全部是`low_corruption_gap`。

注意：Ours本次样本覆盖是636/636，但其修复版summary仍因层级`S_v_zero_grad`/主分数有效性规则标记为`failed`并仅保留raw候选。这是**层级候选有效性问题**，不是样本输入覆盖问题，不能把它误写为只有少量样本。

## 5. 共同定位样本集合

| 项目 | 值 |
|---|---|
| common_localization_samples | 636 |
| common_localization_sample_id_hash | `c98a15ccaaeb48a46a1a1536f1ba7891d0b00184029d5550434cc3306c70215b` |
| 相对636样本manifest缺失ID | 0 |
| 额外ID | 0 |
| 重复ID | 0 |

这里的共同集合按用户指定，取六种方法**实际输入sample_id集合**的交集。CMA虽然只有9条通过内部过滤，但它同样读取并处理了全部636条输入。

## 6. 任意两种方法输入集合的交集/差集

六种方法的输入集合完全相同，因此所有差异ID列表均为空，不存在可列出的“前20个差异ID”。

| 方法A | 方法B | intersection_count | only_in_A | only_in_B | Jaccard |
|---|---|---:|---:|---:|---:|
| Ours | LGA | 636 | 0 | 0 | 1.000 |
| Ours | SaLEM | 636 | 0 | 0 | 1.000 |
| Ours | Perturb-KL | 636 | 0 | 0 | 1.000 |
| Ours | VisEdit | 636 | 0 | 0 | 1.000 |
| Ours | CMA | 636 | 0 | 0 | 1.000 |
| LGA | SaLEM | 636 | 0 | 0 | 1.000 |
| LGA | Perturb-KL | 636 | 0 | 0 | 1.000 |
| LGA | VisEdit | 636 | 0 | 0 | 1.000 |
| LGA | CMA | 636 | 0 | 0 | 1.000 |
| SaLEM | Perturb-KL | 636 | 0 | 0 | 1.000 |
| SaLEM | VisEdit | 636 | 0 | 0 | 1.000 |
| SaLEM | CMA | 636 | 0 | 0 | 1.000 |
| Perturb-KL | VisEdit | 636 | 0 | 0 | 1.000 |
| Perturb-KL | CMA | 636 | 0 | 0 | 1.000 |
| VisEdit | CMA | 636 | 0 | 0 | 1.000 |

## 7. CMA逐级过滤独立重算

### 7.1 参数分组

现存正式结果只包含一个参数组，未混合不同参数：

| noise_scale/alpha | seed/repeat | gap阈值 |
|---:|---:|---:|
| 1.0 | 2026 | `gap > 0.05` |

### 7.2 逐级统计

| 项目 | 独立重算值 | 证据 |
|---|---:|---|
| cma_input_samples | 636 | progress唯一ID |
| cma_finite_samples | 636 | 627条低gap均为有限数；另9条只有通过有限gap检查后才能进入恢复阶段 |
| cma_valid_samples | 9 | 最终`status=ok`且`valid_noise_repeat_count=1` |
| low_corruption_gap_count | 627 | 627个唯一ID，各1条低gap记录 |
| nonfinite_score_count | 0 | 无非有限gap记录；层汇总为有限值 |
| missing_restore_score_count | 0（按runner状态） | 9条均完成36层restore forward；层表每层`valid_restore_forward_count=9` |
| runtime_error_count | 0 | 最终记录无error，summary errors为空 |
| CMA实际排除总数 | 627 | 最终`status=excluded`的唯一ID |
| summary.json excluded_sample_count | 0 | summary原字段 |
| 是否一致 | **否** | summary少报627条 |

### 7.3 9条有效样本

| sample_id | clean-corrupt gap |
|---|---|
| mmke_120 | 未被现有文件保存；已知严格大于0.05 |
| mmke_223 | 未被现有文件保存；已知严格大于0.05 |
| mmke_228 | 未被现有文件保存；已知严格大于0.05 |
| mmke_302 | 未被现有文件保存；已知严格大于0.05 |
| mmke_457 | 未被现有文件保存；已知严格大于0.05 |
| mmke_484 | 未被现有文件保存；已知严格大于0.05 |
| mmke_493 | 未被现有文件保存；已知严格大于0.05 |
| mmke_505 | 未被现有文件保存；已知严格大于0.05 |
| mmke_634 | 未被现有文件保存；已知严格大于0.05 |

**证据限制：** CMA实现只在`gap <= 0.05`时把gap写入progress；通过阈值后，最终`ok`记录只保存`valid_noise_repeat_count`，未保存`s_clean`、`s_corrupt`、逐样本`s_restore`或通过样本的gap。因此可以从实际控制流和状态独立确定这9条均通过有限gap且gap>0.05，并完成逐层恢复，但不能从现存结果还原它们的精确gap。此次没有重跑，未补造数值。

### 7.4 627条低gap样本的gap分布

| min | P25 | median | P75 | P90 | P95 | max |
|---:|---:|---:|---:|---:|---:|---:|
| -0.256544 | -0.058552 | -0.036138 | -0.011975 | 0.009421 | 0.021753 | 0.048962 |

补充：627条中有525条gap为负（污染后目标序列分数反而高于clean），这进一步说明问题发生在CMA污染有效性环节，而不是模型输出为空。

### 7.5 距离0.05最近的阈值下方20条

| sample_id | gap |
|---|---:|
| mmke_118 | 0.048962 |
| mmke_384 | 0.045401 |
| mmke_548 | 0.041064 |
| mmke_591 | 0.040957 |
| mmke_88 | 0.040674 |
| mmke_8 | 0.040085 |
| mmke_315 | 0.039844 |
| mmke_327 | 0.039620 |
| mmke_359 | 0.039002 |
| mmke_297 | 0.038502 |
| mmke_525 | 0.036530 |
| mmke_164 | 0.034927 |
| mmke_417 | 0.033798 |
| mmke_169 | 0.033700 |
| mmke_55 | 0.033355 |
| mmke_390 | 0.033086 |
| mmke_434 | 0.030629 |
| mmke_333 | 0.029158 |
| mmke_632 | 0.026660 |
| mmke_230 | 0.026265 |

阈值上方最近20条无法列出：现存progress没有保存9条通过样本的gap，且总共也只有9条通过样本。这属于当前证据不足，不应通过推测补齐。

## 8. 四个核心数字

| 核心项 | 数值 |
|---|---:|
| total_samples | 636 |
| nonempty_model_pred_samples | 636 |
| common_localization_samples | 636 |
| cma_valid_samples | 9 |

```text
636 → 636 → 636 → 9
```

## 9. classification与直接证据

```text
classification = B_cma_specific_low_valid_coverage
```

直接证据：

1. 基础`model_pred`缓存有636个唯一ID，636条保存文本均非空，无缺失、无重复，且没有一条与`alt`归一化后相同。
2. Ours、LGA、SaLEM、Perturb-KL、VisEdit和CMA输入集合的共同交集为636，所有两两输入集合Jaccard均为1.0。
3. Ours、LGA、SaLEM、Perturb-KL和VisEdit均以636条样本形成层级聚合；不存在“所有方法只能共同使用9条”的现象。
4. CMA实际处理636条，其中627条逐样本明确标记`low_corruption_gap`，仅9条标记`ok`并进入36层恢复。
5. CMA未发现运行异常、空target、无效visual span或空target mask；627条减少发生在`gap > 0.05`这一步。

## 10. 当前候选层是否可以继续使用

**高度可能：仅适合保留为低置信度/敏感性结果，不适合作为与其他六种方法同等可信度的正式主比较结果。**

现有CMA候选层`L1,L0,L2`确实由当前实现和9条有效样本计算得到，不能称为“计算错误”；但1.42%的覆盖率太低，容易受个别样本支配。用于当前训练并集时可以保留来源和`low_confidence; n=9/636`标签，不能隐去覆盖率，也不能把它解释成对整个636样本组合稳定成立。

## 11. 是否需要重算CMA候选层

**需要，但应作为预先声明的CMA稳健性/参数校准重算，不应事后只为提高分数而放宽阈值。**

建议在下一轮正式CMA实验前：

1. 固定同一636条sample manifest。
2. 预先声明多个`noise_scale`和seed，逐组独立报告覆盖率与候选稳定性。
3. 保持`gap>0.05`主阈值不变；如考察其他阈值，作为单独敏感性分析。
4. 新结果必须逐样本保存`s_clean`、`s_corrupt`、各层`s_restore`、gap、noise scale、seed、运行状态和恢复有效性。
5. 修复汇总生成逻辑，使`excluded_sample_count`包含低gap排除；当前summary的0与实际627不一致。

本次审计没有执行上述重算或修改。

## 12. 是否需要重算其他定位方法

- **LGA、SaLEM、Perturb-KL、VisEdit：不因本次覆盖率问题而需要重算。** 它们均覆盖636/636。
- **Ours：不因样本覆盖率需要重算。** 它也是636/636；但其Qwen修复版存在独立的层级有效分数/零梯度判定问题，应与“CMA只有9条”分开审计，不能混为共同样本不足。
- **Middle-Prior：不依赖样本，无需做覆盖率重算。**

## 13. 证据等级汇总

### 已证实

- 636条基础样本、636条非空缓存文本、0缺失ID、0重复ID。
- 六种方法输入共同集合为636。
- CMA只有9条进入恢复聚合，627条因低corruption gap排除。
- CMA summary的`excluded_sample_count=0`与逐样本实际627不一致。
- 分类为`B_cma_specific_low_valid_coverage`。

### 高度可能

- 当前污染强度/单seed设置对Qwen/MMKE-entity不足以稳定降低目标序列分数，是CMA覆盖过低的主要实验原因。
- 9条CMA候选层排序对样本扰动较敏感，应标记低置信度。

### 当前证据不足

- 636条model_pred的首token、EOS状态和effective token length：缓存未保存token IDs。
- 9条CMA有效样本的精确gap及逐样本`s_clean/s_corrupt/s_restore`：正式progress未保存这些数值。
- 不重跑的前提下，无法判断换不同noise scale/seed后覆盖率和候选排序是否稳定。

## 14. 最终判断

当前结果明确属于**情况B**：共同定位样本充分（636），但CMA内部过滤后只剩9条。不能把CMA的`9/636`解释为Qwen只有9条非空输出，也不能归因于所有定位方法共同低覆盖。当前CMA候选层可作为带明确`low_confidence`标签的既有结果保留；若要进入正式公平主比较，应按预先声明的多noise-scale、多seed协议重算CMA，并完整保存逐样本审计字段。其他方法不需要因为这一CMA覆盖问题重算。
