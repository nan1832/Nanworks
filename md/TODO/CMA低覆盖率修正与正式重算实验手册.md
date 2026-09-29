# CMA低覆盖率修正与正式重算实验手册

> 适用任务：视觉语言模型视觉编辑层定位第一阶段中的 `CMA-Direct` 候选层重算。  
> 首要组合：`MMKE-entity × Qwen2.5-VL-3B`。  
> 使用对象：负责检查工程、修正记录逻辑并执行候选层重算的 Codex。  
> 本手册只处理 CMA 候选层定位，不直接启动或重复训练 Adapter。

---

## 1. 实验背景与已确认事实

当前 `MMKE-entity × Qwen2.5-VL-3B` 的只读审计结果为：

```text
total_samples
→ nonempty_model_pred_samples
→ common_localization_samples
→ cma_valid_samples

636 → 636 → 636 → 9
```

已经确认：

1. 636条样本均存在非空 `model_pred`；
2. 0条 `model_pred == alt`；
3. Ours、LGA、SaLEM、Perturb-KL、VisEdit和CMA实际读取的是同一批636条样本；
4. CMA读取并完成了636条样本的基础处理；
5. 其中627条在CMA内部被标记为 `low_corruption_gap`；
   其中525条gap为负，即污染后目标序列分数反而高于clean；
6. 只有9条满足当前有效性条件并进入36层恢复；
7. 未发现空目标、visual-token span错误、target mask为空、非有限 `clean_corrupt_gap` 或运行异常；但现有产物没有保存9条通过样本的逐样本 `s_clean/s_corrupt/s_restore`，因此尚不能独立确认每一层恢复分数均为有限值；
8. 当前 `summary.json` 将 `excluded_sample_count` 写为0，但逐样本实际排除数为627；
9. 当前CMA候选层为 `L1,L0,L2`，它们来自9条有效样本，只能视为低置信历史结果；
10. 当前结果明确属于 `B_cma_specific_low_valid_coverage`，不是所有方法共同低覆盖。

当前服务器实际运行协议为：

```yaml
noise_alpha_list: [1.0]
noise_seeds_semantic: [2026]
runner_repeats: [2026]  # 现有runner实际参数名，repeat值进入确定性噪声种子
delta_logprob: 0.05
min_valid_ratio: 0.05
```

上述配置是历史runner的实际默认协议，历史结果本身没有“配置执行错误”。本手册从现在起预先冻结新的多噪声、多种子稳健性协议，用于生成独立版本的正式重算结果；不得将新协议追溯描述成历史任务本应使用却未使用的配置。

---

## 2. 本次实验目的

本次实验需要回答以下问题：

1. 当前 `9/636` 是否主要由单一噪声强度和单一随机种子造成；
2. 在预先固定的正式协议下，CMA有效样本覆盖率能否恢复；
3. 不同噪声强度和随机种子得到的层排序是否稳定；
4. 正式CMA候选层是否仍为 `L1,L0,L2`；
5. 是否需要将新增CMA候选层加入真实Adapter训练并集。

本实验的目标是修正CMA运行协议、统计记录和结果置信度，不是为了让CMA获得更高的Adapter编辑分数，也不是为了通过事后放宽阈值强行提高覆盖率。

---

## 3. 执行边界

Codex必须遵守以下边界：

1. 先检查现有代码、配置、结果目录和运行脚本，再修改或新增实现；
2. 不覆盖当前单参数历史结果；
3. 不删除任何已有候选层、日志、缓存或Adapter训练结果；
4. 不修改其他六种定位方法的候选层；
5. 不根据真实Adapter编辑结果选择噪声强度、随机种子或有效性阈值；
6. 不将 `delta_logprob=0.05` 在主实验中放宽；
7. 不在CMA候选层重算完成前启动新的Adapter训练；
8. 不把低覆盖结果静默标记为普通 `done`；
9. 不使用Middle、Ours或其他方法的候选层作为CMA fallback；
10. 所有新增输出写入新的版本目录，并保留配置哈希、代码版本和样本清单哈希。

如发现手册要求与当前代码结构无法直接兼容，Codex应先输出差异和最小修改方案，不得静默改变方法定义。

---

## 4. 正式方法定义

### 4.1 输入与目标

对第 (i) 条样本：

- 输入：图像与原始问题 `image + src`；
- 新知识目标：完整 `alt` 答案序列；
- 评分口径：完整 `alt` 序列的teacher-forcing mean token log-probability；
- prompt、visual tokens和padding位置不计入目标loss。

### 4.2 三种前向状态

干净输入得分：

\[
s_i^{clean}
\]

污染视觉输入后的得分：

\[
s_i^{corrupt}(\alpha,r)
\]

在第 (l) 个decoder block输出处恢复clean visual-token hidden states后的得分：

\[
s_i^{restore}(l,\alpha,r)
\]

### 4.3 CMA有效条件

只有污染确实降低目标答案支持时，该“样本—噪声强度—种子”组合才进入恢复计算：

\[
s_i^{clean}>s_i^{corrupt}(\alpha,r)+0.05
\]

即：

```text
clean_corrupt_gap = s_clean - s_corrupt
is_valid = clean_corrupt_gap > 0.05
```

无效组合必须保留记录，并写明：

```text
invalid_reason = low_corruption_gap
```

### 4.4 因果恢复分数

对有效的“样本—alpha—seed”组合，在每一层计算：

\[
CR_i(l,\alpha,r)
=
\frac{
s_i^{restore}(l,\alpha,r)-s_i^{corrupt}(\alpha,r)
}{
s_i^{clean}-s_i^{corrupt}(\alpha,r)+\epsilon
}
\]

其中 `epsilon` 必须与实现保持一致并写入冻结配置。只有 `s_clean`、`s_corrupt`、`s_restore` 和最终 `CR` 均为有限值的记录才能进入层分数聚合；不能仅因执行过恢复前向就计为有效恢复。

正式层分数为：

\[
S_{CMA}(l)
=
\operatorname{mean}_{i,\alpha,r}
CR_i(l,\alpha,r)
\]

主排序指标固定为 `CR_mean`；`KCR_mean`只用于辅助诊断和并列层tie-break。

### 4.5 候选层规则

1. 按 `CR_mean` 从大到小排序；
2. 并列时优先 `KCR_mean` 更高的层；
3. 仍并列时优先有效恢复数量更多的层；
4. 仍并列时优先层号较小的层；
5. 输出Direct Top-3和Top-5；
6. 候选层 (L_l) 表示Adapter接在decoder block (l) 输出之后；
7. 不执行Pre-shift。

---

## 5. 正式冻结参数

以下参数作为本次新版本稳健性重算的预先冻结协议，不是对历史单参数运行配置的追溯性更名：

```yaml
method: CMA-Direct
target_field: alt
target_scope: complete_alt_sequence
score_type: teacher_forcing_mean_logprob

corruption_location: decoder_visual_input_embeddings
corruption_scope: visual_tokens
noise_type: gaussian
noise_alpha_list: [0.5, 1.0, 2.0]
noise_seeds: [0, 1, 2]
seed_key: dataset/model/sample_id/alpha/seed

restore_location: decoder_block_output
restore_scope: visual_tokens
delta_logprob: 0.05
min_valid_samples: 30
min_valid_ratio: 0.20
epsilon: 1.0e-8  # 最终以runner实现中的真实值为准，冻结前必须核验并记录

rank_metric: CR_mean
aux_metric: KCR_mean
candidate_k: [3, 5]
candidate_mode: direct
```

必须确认 `seed_key` 不包含layer，从而保证同一样本在所有层使用同一份污染噪声，即common random numbers。

正式主结果同时聚合预先声明的3个alpha和3个seed，不允许运行结束后只挑覆盖率最高或候选层编辑效果最好的单个alpha/seed作为主结果。

---

## 6. 结果版本与目录保护

### 6.1 历史结果

当前结果只在新manifest和报告中登记别名，禁止重命名、移动或修改历史目录及原始文件：

```text
CMA-Direct-v0-single-alpha-single-seed
alpha = 1.0
seed = 2026
valid_unique_samples = 9/636
Top-3 = L1,L0,L2
Top-5 = L1,L0,L2,L3,L6
artifact_status = low_confidence
coverage_status = low_valid_coverage_severe
```

只登记身份，不修改其原始分数。

### 6.2 新结果

新结果必须写入独立目录，例如：

```text
server_results/cma_direct_formal_multinoise_multiseed_v1/
```

禁止覆盖旧目录。新目录中必须保存：

```text
config_frozen.yaml
code_version.txt
sample_manifest.json
sample_manifest.sha256
run_manifest.json
```

---

## 7. 阶段0：运行前只读审计

Codex先完成以下检查：

- [ ] 定位现有CMA runner、配置解析器、模型wrapper和结果汇总脚本；
- [ ] 逐样本确认Qwen2.5-VL的视觉token范围与该样本visual feature数量一致；动态分辨率允许不同样本的范围不同，不能强制使用全局固定span；
- [ ] 确认teacher-forcing shift和target mask正确；
- [ ] 确认污染只作用于decoder输入端visual tokens；
- [ ] 确认恢复的是decoder block输出中的visual-token hidden states；
- [ ] 确认同一alpha、seed、sample在所有层复用相同噪声；
- [ ] 确认36层恢复分数均能保存；
- [ ] 确认636条共同样本清单的ID和哈希；
- [ ] 确认旧结果目录不会被新任务覆盖；
- [ ] 确认当前脚本是否支持3个alpha和3个seed；
- [ ] 核验runner中的 `repeat` 与报告中的 `seed` 映射，保证每个冻结seed都真实进入确定性噪声生成；
- [ ] 核验有效计数只在36层恢复值及CR均有限、完整后增加，而不是在开始恢复前增加；
- [ ] 确认断点续跑依据是“样本—alpha—seed—layer”，而不是只依据样本ID；
- [ ] 确认已有clean前向结果是否可以安全缓存复用。

审计完成后输出：

```text
cma_formal_rerun_preflight_audit.md
```

如果存在visual span、mask、hook或层号映射错误，应先停止实验并修复，不能继续进入参数校准。

---

## 8. 阶段1：修正统计与状态记录

### 8.1 逐样本长表

每条“样本—alpha—seed—layer”记录至少包含：

```text
dataset
model
sample_id
layer
alpha
seed
s_clean
s_corrupt
s_restore
clean_corrupt_gap
cr
kcr
gap_valid
restore_valid
included_in_formal_aggregate
invalid_reason
restore_status
```

即使 `clean_corrupt_gap <= 0.05`、没有进入逐层恢复，也必须保存不带layer或使用明确空layer的污染阶段记录，不能只增加一个计数器。

### 8.2 汇总字段

汇总必须把“唯一样本”“样本—alpha—seed参数对”和“逐层恢复记录”三个统计单位分开。汇总文件至少包含：

```text
total_samples
input_unique_samples
nonempty_target_samples
valid_unique_samples
fully_excluded_unique_samples
total_sample_alpha_seed_pairs
valid_corruption_pairs
valid_restore_pairs
low_corruption_gap_pair_count
nonfinite_gap_pair_count
runtime_error_pair_count
missing_restore_pair_count
nonfinite_restore_pair_count
excluded_pair_count
common_restore_pairs_all_layers
nonfinite_restore_records
missing_restore_records
valid_ratio_unique
valid_ratio_pairs
status
```

对本任务：

```text
total_sample_alpha_seed_pairs = 636 × 3 × 3 = 5724
excluded_pair_count
= low_corruption_gap_pair_count
+ nonfinite_gap_pair_count
+ runtime_error_pair_count
+ missing_restore_pair_count
+ nonfinite_restore_pair_count
+ 其他互斥的参数对级排除原因数量
```

每个参数对只分配一个最终状态，优先级固定为：`runtime_error` → `nonfinite_gap` → `low_corruption_gap` → `missing_or_nonfinite_restore` → `valid_restore_pair`。其中 `valid_restore_pair` 必须具有完整且有限的36层恢复记录。

`valid_unique_samples`定义为至少存在一个通过gap条件且具有完整、有限36层恢复记录的唯一 `sample_id` 数。`fully_excluded_unique_samples`定义为在全部9个参数组中均无这种有效恢复记录的唯一 `sample_id` 数。

不同计数单位不得放入同一个加法恒等式。逐层 `missing_restore_records` 和参数对级 `missing_restore_pair_count` 必须分别统计；同一唯一样本可能在多个参数组被排除，按原因统计的唯一样本集合也可能重叠。旧字段 `excluded_sample_count` 语义含混，新版本不得作为主字段；若为兼容旧代码保留，必须明确定义为 `fully_excluded_unique_samples`。

不得再次出现“历史逐样本实际排除627条，但summary中 `excluded_sample_count=0`”的情况。

### 8.3 状态规则

覆盖率按不同样本计算，不按重复的alpha/seed对计算：

\[
Coverage_{CMA}
=
\frac{N_{valid,unique}}{N_{input,unique}}
\]

同时必须报告参数对覆盖率：

\[
Coverage_{pair}
=
\frac{N_{valid\_restore\_pairs}}{N_{sample\_alpha\_seed\_pairs}}
\]

并按每个alpha、seed及alpha×seed分别报告覆盖率。正式层排序使用的 `common_restore_pairs_all_layers` 必须单独给出。

对636条样本，正式合格线为：

\[
N_{valid,unique}
\ge
\max(30,\lceil636\times0.20\rceil)
=128
\]

状态固定为：

| 条件 | 状态 |
|---|---|
| `valid_unique_samples >= 128` | `eligible` |
| `30 <= valid_unique_samples < 128` | `low_valid_coverage` |
| `1 <= valid_unique_samples < 30` | `low_valid_coverage_severe` |
| `valid_unique_samples == 0` | `no_valid_cma_sample` |
| 覆盖率合格但层排序不稳定 | `candidate_ranking_unstable` |
| 存在实现或数据错误 | `failed` |

---

## 9. 阶段2：最小样本冒烟测试

在正式50条预检前使用2条样本进行冒烟测试：

1. 一条从历史9条有效样本中固定选择的工程正控制样本（例如审计报告中的 `mmke_120`），用于确保恢复路径确实被执行；
2. 一条按确定性哈希从636条manifest中选择的普通样本，用于检查低gap分支和一般数据路径。

正控制样本只用于工程回归，不得用于选择alpha、阈值或正式候选层；冒烟输出写入隔离目录，不能混入正式聚合。若历史正控制样本在 `alpha=1.0/repeat=2026` 下不再通过gap条件，应先调查代码、模型、数据或随机性复现差异。

对每条样本运行：

```text
3 alpha × 3 seed × 36 layers
```

验收条件：

- [ ] 3个alpha和3个seed均真正进入运行；
- [ ] `s_clean`对同一样本只计算或缓存一次；
- [ ] `s_corrupt`随alpha/seed变化；
- [ ] 同一alpha/seed在不同层使用相同污染；
- [ ] 每个有效组合均得到36个有限的`s_restore`；
- [ ] 只有在36层 `s_restore/CR` 均完整且有限后，该参数对才计入有效恢复；
- [ ] 层间恢复分数不是完全常数；
- [ ] 逐样本长表字段齐全；
- [ ] summary可以由长表独立重建；
- [ ] 中断后能够从正确粒度续跑，不重复覆盖完整记录。

任何一项不通过，停止后续任务。

---

## 10. 阶段3：固定50条样本预检

### 10.1 校准样本选择

从636条共同样本中使用确定性哈希规则选择50条，保存为：

```text
cma_calibration_manifest_50.json
```

要求：

1. 样本选择不能使用 `s_clean-s_corrupt`、层分数、候选层或Adapter结果；
2. manifest生成后保存样本ID、原始顺序、选择规则和SHA-256；
3. 后续不得替换校准样本；
4. 所有alpha和seed必须使用相同50条样本。

### 10.2 预检运行

执行：

```text
50 samples × 3 alpha × 3 seed
```

对满足gap条件的组合继续完成全部36层恢复。

### 10.3 预检输出

分别对每个alpha、每个seed和每个alpha×seed组合报告：

- 输入样本数；
- 有效不同样本数；
- 有效样本—参数对数量；
- `clean_corrupt_gap`的min、P25、median、P75、P90、P95、max；
- `low_corruption_gap`数量；
- 非有限值、运行错误、缺失恢复数量；
- 36层 `CR_mean` 的动态范围；
- Top-3和Top-5候选层；
- 不同alpha/seed参数组之间的候选层重合度，以及与历史单参数候选层的重合度；完整636条聚合尚未运行，预检阶段不得声称已与其比较。

### 10.4 预检通过条件

进入636条正式重算前必须满足：

1. 50条输入均有完整污染阶段记录；
2. 所有预期alpha和seed均出现；
3. 无visual span、target mask、hook或层号映射错误；
4. 无系统性nonfinite和runtime error；
5. 唯一样本、参数对和逐层记录三种统计可由长表分别准确重建，不混用计数单位；
6. 至少一个预先声明的alpha×seed组合产生非零有效样本；
7. 有效组合的恢复分数具有层间区分度；
8. 预检过程中没有根据候选层或Adapter结果改变参数。

预检还必须报告预计全量计算量、运行时间、显存峰值和参数对覆盖率的不确定性。50条预检只用于工程验收和资源估算；不得据此删除低覆盖参数组、替换冻结参数或宣称正式覆盖率已恢复。

预检结果保存为：

```text
cma_calibration_alpha_seed_summary.csv
cma_calibration_report.md
```

预检只用于确认协议能正确执行和评估计算成本，不用于事后挑选单一alpha作为主方法。正式主结果仍聚合全部预先声明参数。

---

## 11. 阶段4：636条正式重算

### 11.1 正式输入

固定使用审计确认的636条共同样本：

```text
dataset = MMKE-entity
model = Qwen2.5-VL-3B
input_unique_samples = 636
```

正式运行规模：

```text
636 samples × 3 alpha × 3 seed
```

仅对满足 `clean_corrupt_gap > 0.05` 的样本—alpha—seed组合执行36层恢复。

### 11.2 运行顺序

对每个样本执行：

1. 计算或读取 `s_clean`；
2. 对3个alpha和3个seed生成确定性视觉噪声；
3. 计算每个组合的 `s_corrupt`；
4. 保存所有gap，无论是否有效；
5. 对有效组合依次恢复36层visual-token hidden states；
6. 计算并保存 `s_restore`、`CR`和`KCR`；
7. 完成后清理hook和临时缓存；
8. 按可验证粒度写入断点，保证异常重启不丢失已完成结果。

### 11.3 资源控制

1. `s_clean`标量结果按样本缓存，避免为9个参数组合重复计算；clean hidden states只在当前样本生命周期内复用，样本完成后及时释放GPU张量；
2. 先完成污染有效性判定，再对有效组合执行昂贵的逐层恢复；
3. 同一时间只挂载当前需要的恢复hook；
4. 长表增量写入，避免全部结果只保存在内存；
5. 每完成固定数量样本生成一次可恢复进度状态文件；该文件不是模型权重checkpoint，至少记录sample、alpha、seed、layer、配置哈希和输出文件偏移；
6. 发生OOM时只能调整batch、分层或缓存策略，不能改变方法参数和评分定义；
7. 重启后必须验证已完成记录的配置哈希与本次任务一致。

---

## 12. 阶段5：层分数聚合与候选层生成

### 12.1 正式聚合

为保证各层使用完全一致的样本—参数对口径，先取36层均存在有限 `s_restore/CR` 的参数对交集：

```text
common_restore_pairs_all_layers
= intersection(valid sample-alpha-seed pairs of every layer)
```

正式主聚合只使用该共同参数对集合：

```text
formal_score[layer] = mean(CR over common_restore_pairs_all_layers)
```

该均值是预先声明的“参数对加权”主指标：同一样本若在更多alpha/seed下有效，会贡献更多记录。同时必须输出不改变主排名的样本平衡诊断指标：先在每个样本内部对有效alpha/seed求均值，再跨唯一样本求均值。报告两种排名是否一致，不得看结果后切换主指标。

同时保存：

```text
CR_mean
CR_std
KCR_mean
valid_unique_samples_per_layer
valid_sample_alpha_seed_pairs_per_layer
restore_forward_count
common_restore_pairs_all_layers
sample_balanced_CR_mean
pair_weighted_vs_sample_balanced_rank_agreement
```

禁止：

- 只选择覆盖率最高的alpha；
- 只选择结果最好的seed；
- 根据旧候选层或Adapter性能加权；
- 将无效记录的CR填成0后参与平均；
- 让不同层使用不同的有效参数对集合进行正式排名；
- 跨模型比较CR绝对值。

### 12.2 正式候选层

输出：

```text
formal_top3
formal_top5
raw_rank_all_layers
clean_rank_all_layers
```

raw与clean候选均需保留；重复层、越界层和清洗原因必须可追溯。

---

## 13. 阶段6：候选层稳定性分析

除完整聚合外，还要生成：

1. 每个alpha聚合3个seed后的全层排序与Top-3/Top-5；
2. 每个seed聚合3个alpha后的全层排序与Top-3/Top-5；
3. 9个alpha×seed组合各自的全层排序与Top-3/Top-5；
4. 完整聚合的正式排序与Top-3/Top-5。

每个参数组还必须报告其有效共同恢复样本数。0条有效记录的组标记为 `no_valid_group`，不足30条的组标记为 `low_support_group`；不得为无有效记录的组伪造排名，也不得静默删除低支持组。稳定性统计需同时说明纳入了哪些组及其支持量。

稳定性指标：

```text
Top3 Jaccard
Top5 Jaccard
Top1 agreement
Spearman rank correlation
Kendall rank correlation
candidate frequency per layer
```

预先使用以下候选稳定性判据：

1. 多数组合的Top-3与正式Top-3至少重合2层；
2. Top-3平均Jaccard不低于0.50；
3. 正式Top-3不能完全由单一alpha或单一seed决定；
4. 至少2个alpha和2个seed对正式候选层提供支持。

若有效覆盖率达标但不满足上述条件，标记：

```text
status = candidate_ranking_unstable
```

不得查看Adapter结果后修改稳定性标准。

---

## 14. 正式结果判定

### 14.1 情况一：覆盖率恢复且候选稳定

条件：

```text
valid_unique_samples >= 128
status = eligible
candidate stability passed
common_restore_pairs_all_layers is nonempty
no unresolved engineering error
```

处理：

1. 将多噪声、多种子结果作为正式CMA结果；
2. 旧 `L1,L0,L2` 保留为历史单参数诊断；
3. 更新七方法Top-3/Top-5候选层并集；
4. 对比新旧CMA候选层重合度；
5. 输出新候选层差集及已完成主配置结果核验清单，待人工确认后才补做Adapter训练；
6. 已完成且仍在新候选中的层直接复用，不重复训练。

### 14.2 情况二：覆盖率恢复但候选不稳定

条件：

```text
valid_unique_samples >= 128
status = candidate_ranking_unstable
```

处理：

1. 完整报告不同alpha/seed候选差异；
2. 保留完整聚合候选，但标注稳定性不足；
3. 不根据Adapter结果挑选某个参数组；
4. CMA只作为敏感性或低置信基线解释。

### 14.3 情况三：正式协议下仍低覆盖

条件：

```text
valid_unique_samples < 128
```

处理：

1. 保持 `delta_logprob=0.05` 不变；
2. 根据实际数量标记 `low_valid_coverage` 或 `low_valid_coverage_severe`；
3. 说明在预先规定的视觉污染协议下，大部分样本的目标答案支持没有显著降低；
4. 保留候选层及其覆盖率，但不能与其他方法作同等置信度解释；
5. 不继续为提高覆盖率反复搜索噪声参数；
6. 如需测试其他阈值或更强噪声，只能另建明确命名的敏感性实验，不得替换主结果。

### 14.4 情况四：发现工程错误

如果正式重算中发现visual span、mask、hook、恢复位置、层号映射或缓存污染错误：

1. 停止当前任务；
2. 保存失败日志和已完成记录；
3. 输出根因分析；
4. 修复后重新进行2条冒烟测试和50条预检；
5. 未通过重新验收前不得继续全量任务。

### 14.5 本次正式重算已完成结果（2026-09-06）

本组合已经按照本手册冻结的正式协议完成636条全量计算。本节记录实际结果，后续分析不得再将其写成 `pending`。

#### 14.5.1 实际参数配置

```yaml
method: CMA-Direct
variant: direct
dataset: MMKE-entity
model: Qwen2.5-VL-3B
input_unique_samples: 636
target_field: alt
target_scope: complete_alt_sequence
score_type: teacher_forcing_mean_logprob
corruption_location: decoder_visual_input_embeddings
corruption_scope: visual_tokens
restore_location: decoder_block_output
restore_scope: visual_tokens
noise_type: gaussian
noise_definition: alpha_times_visual_embedding_std
noise_alpha_list: [0.5, 1.0, 2.0]
noise_seeds: [0, 1, 2]
seed_key: dataset/model/sample_id/alpha/seed
delta_logprob: 0.05
rank_metric: CR_mean
aux_metric: KCR_mean
primary_aggregation: pair_weighted_mean_CR
ranking_population: common_restore_pairs_all_layers
minimum_valid_unique_samples: 128
```

冻结配置哈希：`23888338cc13308d1ed2519d20eac9977070dafab61f0c4fae08ab6738c49e4e`。

正式结果目录：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/
cma_direct_formal_multinoise_multiseed_v1_20260906/formal636
```

#### 14.5.2 覆盖率与错误统计

| 项目 | 实际结果 |
|---|---:|
| 输入不同样本 | 636 |
| 非空目标样本 | 636 |
| 总样本—alpha—seed参数对 | 5,724 |
| 有限污染参数对 | 5,724 |
| 有效不同样本 | 43/636（6.76%） |
| 完全排除的不同样本 | 593 |
| 有效且36层完整恢复的参数对 | 96/5,724（1.68%） |
| `low_corruption_gap`参数对 | 5,628 |
| nonfinite gap | 0 |
| runtime error | 0 |
| missing restore pair | 0 |
| nonfinite restore | 0 |
| 覆盖状态 | `low_valid_coverage` |

按alpha合并3个seed后的覆盖情况：

| alpha | 有效不同样本 | 有效参数对 | 参数对覆盖率 | gap中位数 | gap P95 |
|---:|---:|---:|---:|---:|---:|
| 0.5 | 13/636 | 21/1,908 | 1.10% | -0.01236 | 0.02234 |
| 1.0 | 19/636 | 31/1,908 | 1.62% | -0.03450 | 0.02853 |
| 2.0 | 27/636 | 44/1,908 | 2.31% | -0.05697 | 0.02694 |

噪声增强带来了有限的覆盖提升，但即使 `alpha=2.0`，绝大多数参数对仍未通过预先声明的 `gap > 0.05` 条件。9个alpha×seed组均存在有效记录，但每组只有4至16条有效样本，全部属于 `low_support_group`。

#### 14.5.3 候选层与稳定性

```text
formal_top3 = [L1, L0, L2]
formal_top5 = [L1, L0, L2, L3, L4]
historical_top3 = [L1, L0, L2]
historical_top5 = [L1, L0, L2, L3, L6]
```

稳定性结果：

- 新旧Top-3完全一致，Top-3 Jaccard为1.0000；
- 新旧Top-5重合4/5，Jaccard为0.6667；
- 9个支持组与正式汇总Top-3的平均Jaccard为0.9444；
- 参数对加权与样本均衡聚合的Top-3均为 `L1,L0,L2`；
- 两种聚合全层排序的Spearman为0.9900，Kendall为0.9429；
- Top-5中新增加 `L4`，历史结果中的 `L6`退出正式Top-5。

因此，本结果呈现“候选层方向稳定，但有效样本覆盖不足”的特征。稳定性不能抵消覆盖率不足，正式状态仍为 `low_valid_coverage`。

#### 14.5.4 低覆盖率原因

已证实：低覆盖不是由样本缺失、空目标、visual-token span错误、target mask错位、hook失败、nonfinite、运行异常或恢复结果缺失造成。636条样本和5,724个污染参数对均被完整处理，样本减少集中发生在CMA内部的 `clean_corrupt_gap > 0.05` 过滤步骤。

高度可能的机制原因是：CMA的经典污染—恢复逻辑更适合解释基础模型在clean输入下已经支持的答案，而本实验使用的是尚未编辑进基础模型的反事实新答案 `alt`。clean状态下Qwen2.5-VL对 `alt` 的支持本来就可能较低；污染视觉表示后，模型对 `alt` 的平均对数概率未必继续下降，甚至可能因旧视觉证据被削弱而上升。因此大量gap为负或接近0，无法通过0.05阈值。这是当前 `CMA-Direct-AltSeq` 在该模型—数据集组合上的适用边界，不是共同定位样本不足。

#### 14.5.5 正式处理建议

1. 当前多噪声、多seed结果作为本组合的正式CMA结果保留，但必须同时报告 `43/636` 与 `low_valid_coverage`，不能与高覆盖方法作同等置信度解释。
2. 不降低 `delta_logprob=0.05`，也不根据当前结果事后扩大噪声网格来替换正式主结果。
3. 不继续反复搜索能提高覆盖率的alpha；更强噪声可能产生离开真实视觉表示分布的扰动，并使少量极端gap主导排名。
4. 如论文需要，可另建预先冻结参数、明确命名的“更强噪声敏感性实验”，但只能作为附加分析，不能替换本次正式结果。
5. 如需验证CMA对基础模型既有知识的适用性，可另设 `CMA-ModelPred` 或旧答案目标诊断版本；它回答的是“原知识在哪里”，不得静默替换面向反事实新答案的 `CMA-Direct-AltSeq`。
6. 正式Top-3没有变化，因此不新增Top-3 Adapter训练层。Top-5新增的 `L4`只作为低置信候选记录，不自动启动Adapter训练。

---

## 15. 新旧候选层比较与Adapter训练规则

旧候选层：

```text
old_top3 = [L1, L0, L2]
old_top5 = [L1, L0, L2, L3, L6]
```

正式重算后计算：

```text
unchanged_layers = old_topK ∩ new_topK
new_layers_to_train = new_topK - already_trained_layers
historical_only_layers = old_topK - new_topK
```

处理规则：

1. `unchanged_layers`复用已有主配置Adapter训练结果；
2. `new_layers_to_train`才进入新增Adapter训练队列；
3. `historical_only_layers`不删除，保留旧方法来源和历史训练结果；
4. 新候选确定前不启动Adapter训练；
5. 新增训练必须使用与七方法真实扫层相同的Adapter结构、epoch、checkpoint选择和独立评测协议；
6. 不跨配置取最大值，不因stable/recovered结果更高而替换main结果。

---

## 16. 其他组合扩展顺序

`MMKE-entity × Qwen2.5-VL-3B` 已于2026-09-06跑通完整流程，正式结果见14.5节。后续如扩展到其他组合，应先对现有结果中真正低覆盖且协议不符合正式手册的CMA组合逐一审计，再决定是否重算。

以下顺序仅为待审计的暂定优先级，不等于这些组合已经证实需要重算：

1. `MMKE-entity × Qwen2.5-VL-3B`；
2. `MMKE-entity × MiniGPT-4`；
3. `MMKE-visual × PaliGemma`；
4. `MMKE-visual × Qwen2.5-VL`；
5. 其余经逐样本审计确认的CMA低覆盖组合。

每个组合开始前都必须重新确认：

- 总样本数；
- 共同定位样本数；
- CMA输入样本数；
- low corruption gap数量；
- 实际alpha/seed；
- 当前候选层及其置信度；
- 是否存在汇总记录错误。

不要仅依据旧汇总表中的 `done` 或 `low_candidate_coverage` 标签决定是否重算。每个组合必须先完成与本次Qwen审计同等级的逐样本只读审计；只有确认是CMA内部低覆盖、统计缺陷或新协议适用后，才进入重算队列。

---

## 17. 必须生成的文件

```text
cma_formal_rerun_preflight_audit.md
config_frozen.yaml
code_version.txt
sample_manifest.json
sample_manifest.sha256
cma_smoke_test_report.md
cma_calibration_manifest_50.json
cma_calibration_alpha_seed_summary.csv
cma_calibration_report.md
cma_corruption_pairs.csv
cma_restore_long.csv
cma_sample_alpha_seed_long.csv
cma_layer_alpha_seed_scores.csv
cma_candidate_stability.csv
cma_formal_top3_top5.json
cma_coverage_summary.json
cma_v0_vs_formal_comparison.md
run_manifest.json
```

所有CSV/JSON必须包含schema版本；manifest和主要结果文件必须保存SHA-256。`cma_corruption_pairs.csv`以唯一 `sample_id × alpha × seed` 为粒度，`cma_restore_long.csv`以唯一 `sample_id × alpha × seed × layer` 为粒度，二者不得依赖汇总数量反推。

`cma_formal_top3_top5.json`至少包含：

```json
{
  "method": "CMA-Direct",
  "variant": "direct",
  "dataset": "MMKE-entity",
  "model": "Qwen2.5-VL-3B",
  "target_field": "alt",
  "target_scope": "complete_alt_sequence",
  "corruption_scope": "visual_tokens",
  "noise_alpha_list": [0.5, 1.0, 2.0],
  "noise_seeds": [0, 1, 2],
  "delta_logprob": 0.05,
  "input_unique_samples": 636,
  "total_sample_alpha_seed_pairs": 5724,
  "valid_unique_samples": 43,
  "valid_ratio_unique": 0.06761006289308176,
  "valid_restore_pairs": 96,
  "common_restore_pairs_all_layers": 96,
  "valid_ratio_pairs": 0.016771488469601678,
  "rank_metric": "CR_mean",
  "aux_metric": "KCR_mean",
  "top3": ["L1", "L0", "L2"],
  "top5": ["L1", "L0", "L2", "L3", "L4"],
  "status": "low_valid_coverage"
}
```

上述字段已由2026-09-06正式全量结果回填。后续重算其他组合时同样不得保留 `null` 或 `pending`。若因无有效样本而没有候选层，允许空候选层，但状态必须为 `no_valid_cma_sample` 并填写原因；若实验失败，必须填写 `failure_reason`。

---

## 18. 新旧结果对比表

最终报告必须包含：

| 项目 | 历史单参数结果 | 正式多参数结果 |
|---|---:|---:|
| 输入样本数 | 636 | 636 |
| 非空目标数 | 636 | 636 |
| 有效不同样本数 | 9 | 43 |
| 唯一样本有效率 | 1.42% | 6.76% |
| 有效恢复参数对数 | 9/636 | 96/5,724 |
| alpha | 1.0 | 0.5、1.0、2.0 |
| seed | 2026 | 0、1、2 |
| low corruption gap参数对数 | 627 | 5,628 |
| Top-3 | L1、L0、L2 | L1、L0、L2 |
| Top-5 | L1、L0、L2、L3、L6 | L1、L0、L2、L3、L4 |
| Top-3稳定性 | 无法判断 | 9组平均Jaccard=0.9444 |
| 原始产物状态 | low_confidence | 已完成、可追溯、低覆盖解释 |
| 覆盖状态 | low_valid_coverage_severe | low_valid_coverage |

本次差集统计：

```text
Top3_overlap_count = 3
Top3_Jaccard = 1.0000
Top5_overlap_count = 4
Top5_Jaccard = 0.6667
new_formal_only_top5_layer = L4
historical_only_top5_layer = L6
new_top3_layers_to_train = none
```

同时报告：

```text
Top3_overlap_count
Top3_Jaccard
Top5_overlap_count
Top5_Jaccard
new_layers_to_train
reusable_trained_layers
```

---

## 19. Codex最终验收清单

- [ ] 旧CMA结果未被覆盖或删除；
- [ ] 新结果使用同一636条样本；
- [ ] 正式参数为3个alpha和3个seed；
- [ ] `delta_logprob=0.05`未改变；
- [ ] 完整alt序列teacher forcing口径未改变；
- [ ] 污染和恢复均只作用于visual tokens；
- [ ] seed key不包含layer；
- [ ] 逐样本gap全部保存；
- [ ] 低gap排除被正确计入参数对级summary；
- [ ] 唯一样本、参数对和逐层恢复记录的计数单位没有混用；
- [ ] 覆盖率按有效不同样本计算；
- [ ] 参数对覆盖率与36层共同恢复参数对数量已经报告；
- [ ] 正式层排序的各层使用同一 `common_restore_pairs_all_layers`；
- [ ] 主排序仅使用`CR_mean`；
- [ ] `KCR_mean`只作辅助和tie-break；
- [ ] Top-3、Top-5和全层排序均已输出；
- [ ] alpha/seed候选稳定性已经计算；
- [ ] 结果状态符合覆盖率和稳定性规则；
- [ ] 未使用Adapter结果调节CMA参数；
- [ ] 未重算其他定位方法；
- [ ] 尚未自动启动Adapter训练；
- [ ] 已输出新增候选层差集列表；
- [ ] 所有输出路径、配置哈希、代码版本和样本哈希可追溯。

---

## 20. 交给Codex的执行指令

> 状态提示（2026-09-06）：下述指令已经执行完成，仅作为复现实验模板保留；不得因再次打开本手册而重复启动本组合全量计算。

将本文件放在项目中后，可向Codex发送：

```text
请严格按照《CMA低覆盖率修正与正式重算实验手册.md》执行。

先完成阶段0只读审计、阶段1统计记录修正和阶段2两条样本冒烟测试。不得覆盖旧结果，不得修改delta_logprob=0.05，不得根据Adapter编辑结果选择参数。

冒烟测试通过后，执行固定50条样本预检，生成手册规定的校准报告。先向我汇报：实际配置、各alpha/seed覆盖率、错误统计、预计全量计算量和是否满足预检验收条件。未经确认不要启动636条全量任务。

获得确认后，再按冻结的[0.5,1.0,2.0]×[0,1,2]协议完成636条CMA正式重算、层排序聚合、候选稳定性分析和新旧候选层差集输出。候选层确定后停止，不要自动启动Adapter训练。
```

---

## 21. 最终原则

本次重算必须遵循以下结论：

> 已证实的是：历史 `9/636` 出现在 `alpha=1.0、repeat=2026、delta_logprob=0.05` 的单参数条件下，且627条由CMA内部 `low_corruption_gap` 过滤；共同定位输入并不低。2026-09-06已按预先冻结的 `[0.5,1.0,2.0] × [0,1,2]` 多噪声、多seed协议完成636条全量重算，有效不同样本提高到43条，但仍低于128条合格线；5,628/5,724个参数对因gap不足被排除，且未发现样本、span、mask、hook、nonfinite或运行错误。正式Top-3仍为 `L1,L0,L2`，候选方向稳定但证据覆盖不足。不得通过查看Adapter编辑结果、事后降低阈值或继续搜索噪声参数来制造更高覆盖率；本结果应作为 `low_valid_coverage` CMA结果如实保留，并明确说明CMA在反事实 `alt` 目标上的适用边界。
