# Bridge30 RelGenLoc Adapter GLA Result

实验时间：2026-05-07  
服务器：`g07`  
数据：`bridge_train/edit_30_bridge_train_only_vis.json`，30 cases  
层范围：`0-31`  
梯度目标：`adapter_output_delta_h_vis`  
损失模式：

```text
L_total = 1 * Entity + 1 * Generality + 1 * Locality
```

其中 `Locality = KL(pre_logits || post_logits)`，`Portability = 0`，`Fluency = 0`。

---

## 1. 输出目录

本地结果已同步到：

```text
server_results/bridge_vlm_relgenloc_adapter_gla_llava_train30/
server_results/bridge_vlm_relgenloc_adapter_gla_blip2_train30/
```

每个目录包含：

```text
run_config.json
old_answer_mapping_report.json
generality_old_answers_*.jsonl
sample_component_scores.jsonl
layer_scores.csv
topk_layers.json
summary.md
run.log
```

完整性检查：

| Model | Sample rows | Layer rows | Top-k file |
|---|---:|---:|---|
| LLaVA-v1.5-7B | 960 | 32 | yes |
| BLIP2-OPT-2.7B | 960 | 32 | yes |

---

## 2. LLaVA-v1.5-7B

主排序使用 `S_total_norm`。

| Rank | Layer | S_total_norm | S_total_cos | EG conflict | zero_grad |
|---:|---:|---:|---:|---:|---|
| 1 | 5 | 0.295521 | -0.165176 | 0.964684 | false |
| 2 | 3 | 0.295298 | -0.159578 | 0.858965 | false |
| 3 | 0 | 0.291946 | -0.143945 | 0.739700 | false |
| 4 | 6 | 0.290970 | -0.162312 | 0.736544 | false |
| 5 | 4 | 0.289428 | -0.159103 | 0.780672 | false |

Top-k：

```json
{
  "primary_total_norm_topk": [5, 3, 0, 6, 4],
  "total_dot_topk": [21, 20, 30, 29, 31],
  "total_cos_topk": [31, 29, 21, 23, 22],
  "eg_conflict_topk": [5, 3, 4, 0, 6],
  "zero_grad_layers": [31],
  "recommended_candidate_pool": [5, 3, 0, 6, 4, 29, 21, 23, 22, 24]
}
```

结论：LLaVA 在三项训练目标下，主候选集中在浅层到中浅层，优先看 `[5, 3, 0, 6, 4]`。第 31 层是零梯度层，虽然 cosine 排名里出现，但不能作为有效候选层。

---

## 3. BLIP2-OPT-2.7B

主排序使用 `S_total_norm`。

| Rank | Layer | S_total_norm | S_total_cos | EG conflict | zero_grad |
|---:|---:|---:|---:|---:|---|
| 1 | 0 | 0.630071 | 0.066342 | -0.278771 | false |
| 2 | 4 | 0.628552 | 0.078840 | -0.321859 | false |
| 3 | 5 | 0.621584 | 0.085123 | -0.379853 | false |
| 4 | 1 | 0.614166 | 0.061417 | -0.229005 | false |
| 5 | 3 | 0.598403 | 0.051541 | -0.089257 | false |

Top-k：

```json
{
  "primary_total_norm_topk": [0, 4, 5, 1, 3],
  "total_dot_topk": [5, 4, 8, 10, 9],
  "total_cos_topk": [5, 8, 9, 10, 4],
  "eg_conflict_topk": [15, 14, 31, 20, 16],
  "zero_grad_layers": [31],
  "recommended_candidate_pool": [0, 4, 5, 1, 3, 8, 9, 10, 15, 14, 20, 16, 27]
}
```

结论：BLIP2 在三项训练目标下，主候选也是浅层为主，优先看 `[0, 4, 5, 1, 3]`。EG conflict 指标给出中层 `[15, 14, 20, 16, 27]` 作为解释性候选，但它不是本实验主排序。

---

## 4. 解释口径

本次实验不是 request-only，而是训练目标一致版 GLA：

```text
Entity + Generality + Locality
```

因此主分数 `S_total_norm` 会同时受写入、泛化和局部保持影响。它和只看 request 的 LGA、只看 visual-hidden 的敏感层、以及最终暴力扫层编辑指标都不是同一个量。

建议后续暴力扫层优先覆盖：

```text
LLaVA: 0, 3, 4, 5, 6，附加 21, 22, 23, 24, 29
BLIP2: 0, 1, 3, 4, 5，附加 8, 9, 10, 14, 15, 16, 20, 27
```

第 31 层在两个模型中都被标记为 `zero_grad_layers`，不应作为候选层直接使用。
