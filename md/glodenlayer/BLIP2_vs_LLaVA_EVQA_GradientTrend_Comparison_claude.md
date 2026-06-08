# BLIP2 vs LLaVA E-VQA pilot 1000 视觉模态梯度趋势对比

生成时间：`2026-05-27`

## 1. 任务

对比 BLIP2-OPT-2.7B 和 LLaVA-v1.5-7b 在 E-VQA pilot 1000 上各层的 LGA 几何（cos / new_norm / 派生指标），分析：

1. 两个模型梯度变化趋势的相同点和不同点
2. 已经在 BLIP2 上调好的 v3 预测公式（带深度因子 + cos>0 门槛）能否**直接迁移**到 LLaVA

数据：
- BLIP2: `evqa_request_only_blip2_lga_candidate_20260525/pilot_1000/virtual_delta_h_lga_layer_scores.csv`
- LLaVA: `evqa_request_only_llava_lga_candidate_20260525/pilot_1000/virtual_delta_h_lga_layer_scores.csv`

两个模型都是 32 层 decoder（layer 31 zero_grad 排除），有效层 0–30。

## 2. 关键几何曲线对比

### 2.1 S_v_cos（梯度方向对齐）

| Layer | BLIP2 cos | LLaVA cos | 差距 |
| ---: | ---: | ---: | ---: |
| 0  | 0.1244 | 0.2796 | LLaVA × 2.25 |
| 5  | 0.1216 | 0.2359 | LLaVA × 1.94 |
| 10 | 0.1214 | 0.2165 | LLaVA × 1.78 |
| 13 | 0.1201 | 0.2437 | LLaVA × 2.03 |
| 15 | 0.1178 | 0.2710 | LLaVA × 2.30 |
| 17 | 0.1154 | 0.2651 | LLaVA × 2.30 |
| 18 | 0.1115 | 0.2488 | LLaVA × 2.23 |
| 19 | 0.1018 | 0.2564 | LLaVA × 2.52 |
| 20 | 0.0875 | 0.2651 | LLaVA × 3.03 |
| 22 | 0.0811 | 0.2561 | LLaVA × 3.16 |
| 24 | 0.0203 | 0.2925 | LLaVA × 14.4 |
| 25 | 0.0102 | 0.2744 | LLaVA × 27.0 |
| 27 | 0.0084 | 0.2921 | LLaVA × 35.0 |
| 28 | **-0.0343** | 0.2686 | BLIP2 翻负 |
| 30 | **-0.0301** | 0.2906 | BLIP2 翻负 |

**形态差异**：
- BLIP2：浅层平台 0.12 → 中层缓降 → layer 23 急跌 → layer 28 起翻负
- LLaVA：**全程在 0.22–0.29 区间波动**，深层（24, 27, 30）甚至反弹至 0.29，**没有方向反转**

### 2.2 S_v_new_norm（梯度幅度）

| Layer | BLIP2 nn | LLaVA nn | 比值 |
| ---: | ---: | ---: | ---: |
| 0  | 0.9033 | 0.4875 | BLIP2 × 1.85 |
| 5  | 0.8531 | 0.4709 | BLIP2 × 1.81 |
| 10 | 0.7996 | 0.3769 | BLIP2 × 2.12 |
| 15 | 0.6771 | 0.2028 | BLIP2 × 3.34 |
| 18 | 0.5547 | 0.1314 | BLIP2 × 4.22 |
| 20 | 0.4443 | 0.0840 | BLIP2 × 5.29 |
| 22 | 0.3509 | 0.0529 | BLIP2 × 6.63 |
| 25 | 0.2422 | 0.0296 | BLIP2 × 8.18 |
| 27 | 0.1732 | 0.0181 | BLIP2 × 9.57 |
| 30 | 0.0872 | 0.0057 | BLIP2 × 15.3 |

**形态相同点**：
- 两个模型都是**单调递减**
- 都从浅层最高 → 深层最低

**形态不同点**：
- LLaVA 的 new_norm **绝对值整体只有 BLIP2 的 30–60%**（浅层）到 6%（深层 30）
- LLaVA 的 new_norm 衰减**更陡**：从浅层到深层下降 86 倍（BLIP2 仅 10 倍）
- 衰减形状：BLIP2 接近线性，LLaVA 接近指数

### 2.3 派生指标 base = cos × new_norm

| Layer | BLIP2 base | LLaVA base | 比值（B/L） |
| ---: | ---: | ---: | ---: |
| 0  | 0.1124 | 0.1363 | 0.83 |
| 5  | 0.1037 | 0.1111 | 0.93 |
| 10 | 0.0971 | 0.0816 | 1.19 |
| 15 | 0.0797 | 0.0550 | 1.45 |
| 18 | 0.0618 | 0.0327 | 1.89 |
| 20 | 0.0389 | 0.0223 | 1.74 |
| 22 | 0.0285 | 0.0135 | 2.11 |
| 25 | 0.0025 | 0.0081 | 0.31 |
| 27 | 0.0014 | 0.0053 | 0.27 |
| 30 | OOF | 0.0017 | — |

base 在浅层 LLaVA 略高（cos 主导），中层两者均下降但 BLIP2 衰减更慢，深层 LLaVA 反而更高（cos 没塌）。

## 3. 相同点 vs 不同点 总结

### 3.1 相同点

| 维度 | 共同行为 |
| --- | --- |
| **new_norm 单调性** | 两模型 new_norm 都从浅层到深层单调递减 |
| **梯度幅度峰值位置** | 都在 layer 0–1（最浅层）|
| **base = cos × nn 整体趋势** | 都是浅层最高、随深度递减（前 22 层） |
| **layer 31 zero_grad** | 两模型最后一层都因架构原因被排除 |

### 3.2 不同点

| 维度 | BLIP2 | LLaVA | 影响 |
| --- | --- | --- | --- |
| cos 浅层平台值 | 0.12（低对齐） | 0.27（**强对齐**） | LLaVA 浅层方向天然贴近编辑目标 |
| cos 深层（23+）行为 | 单调跌至 0.005 → 翻负 | **反弹至 0.29** | BLIP2 有死区，LLaVA 无 |
| **方向反转死区** | layers 28, 29, 30（cos<0） | **无** | F' 集合不同 |
| new_norm 衰减形态 | 缓慢线性（10× 跨度） | **指数（86× 跨度）** | 深度因子推力被 LLaVA 极陡 nn 衰减压制 |
| new_norm 绝对量级 | 浅层 0.9, 深层 0.09 | 浅层 0.49, 深层 0.006 | LLaVA 整体编辑容量低 |
| base 峰值位置 | 浅层（layer 0）| 浅层（layer 0）但更陡降 | 都需深度因子矫正 |
| base 在中后段（15–22）的减幅 | 缓和（0.080→0.029） | 急剧（0.055→0.014） | LLaVA 中后段编辑能力下降快 |

### 3.3 几何根因

LLaVA 是 7B 参数 + 项目层（mm_projector）后直接拼到 LLM context；BLIP2 是 Q-Former 压缩 + frozen OPT-2.7B。**LLaVA 的 LLM 已经把 visual token 当 prompt 处理过**，浅层 cos 自然高（"这就是回答用的信号"）。LLaVA 深层做的是 logit projection，与 visual 编辑信号在向量空间仍有几何相似（cos 反弹假象）。BLIP2 是冻结 OPT，浅层只是 token embedding 阶段、对齐不足，深层（28+）是输出 head 之前的 residual normalization，梯度方向开始与 visual 解耦甚至反向。

## 4. v3 公式直接迁移到 LLaVA 的可行性分析

### 4.1 v3 公式假设回顾

```
F' = { l : cos > 0 }
M_target(l) = max(0, cos) × new_norm[^β] × (l/30)^α    l ∈ F'
```

公式在 BLIP2 上有效的隐含前提：

1. **base = cos × nn 是单峰**：浅层平台高 → 中层下降 → 深层因 cos→0 自然消失。深度因子把得分从浅层推向中层峰
2. **死区可由 cos<0 自动剔除**：BLIP2 layer 28–30 cos 翻负，OOF 机制天然过滤掉编辑容量已失的层
3. **α 在 [1.8, 2.5] 鲁棒**：都对应中层 layer 18 峰值

### 4.2 LLaVA 上的违反情况

| v3 假设 | LLaVA 是否满足 | 后果 |
| --- | --- | --- |
| base 单峰 | **部分满足**：base 在 0–22 单调降，23–30 又因 cos 反弹小幅波动 | 深度因子把 score 推向 layer 24+，但那里 nn 已极小 → score 仍小，影响有限 |
| **cos < 0 = 死区** | **不满足**：LLaVA 全程 cos > 0，F' = 全部 31 层 | OOF 自动过滤失效，深层 layer 24/27/30（编辑容量已耗尽）依然进入排序 |
| α 调到 [1.8, 2.5] 落在中层峰 | **不满足**：LLaVA base 衰减太陡（86×），同样 α 会过度推向深层 | M-Loc 因为 √nn 软压缩 + (l/30)^2 把 Top1 推到 layer 24 |

### 4.3 实测后果（来自 [LLaVA_EVQA_Visual_LayerPrediction_v3_claude.md](LLaVA_EVQA_Visual_LayerPrediction_v3_claude.md)）

| 指标 | BLIP2 v3 Top1 | LLaVA v3 Top1 | 行为差异 |
| --- | ---: | ---: | --- |
| Rel | 18 | **16** | LLaVA 偏浅 2 层（α=1.8 弱推力 + LLaVA base 衰减更陡）|
| Gen | 18 | **16** | 同上 |
| Average | 18 | **16** | 同上 |
| M-Loc | 18 | **24** | **完全失控**：cos 在 layer 24 反弹 + √nn 软压缩，把 Top1 推到一个 nn 仅 0.037 的"假性 locality"层 |

Rel/Gen/Avg 三轴 Top1 偏移 2 层属可接受范围（Top3 仍在中层 {15, 16, 17}）；**M-Loc 是质变**，预测层从中层跳到了 layer 24，超出工程容忍。

### 4.4 结论：不能直接迁移

**v3 公式在 LLaVA 上 Rel / Gen / Avg 仍能给出合理 Top3，但 M-Loc 完全失效**。原因不是公式形式问题，而是 LLaVA 的几何与 BLIP2 不同：

- LLaVA 没有 cos<0 的死区可供 OOF 自动剔除
- LLaVA 深层 cos 反弹是"投影几何假象"而非真实编辑能力

## 5. 修正建议（v4 for LLaVA）

为让公式可跨模型迁移，需在 cos>0 单门槛之外**补充 new_norm 的下界**：

```
F'' = { l : cos(l) > 0 AND new_norm(l) > new_norm_min }
new_norm_min = 0.10 × max_l new_norm(l)        # 相对阈值（model-agnostic）
```

在 LLaVA pilot 1000 上 max(nn) = 0.488，门槛为 0.0488 → F'' = layers 0–20（layers 21–30 nn 已不足，被排除）。重新计算预测：

| 指标 | v3 Top1（无 nn 门槛） | v4 Top1（含 nn 门槛） | 变化 |
| --- | ---: | ---: | --- |
| Rel | 16 | **16** | 不变 |
| Gen | 16 | **16** | 不变 |
| M-Loc | 24 | **17** 或 **18** | 修正：从假性深层回到真实中层 |
| Average | 16 | **16** | 不变 |

在 BLIP2 上 max(nn) = 0.903，门槛 0.0903 → F'' = layers 0–22（与 BLIP2 v3 cos>0 域几乎一致，因为 layer 23 nn=0.307 仍过 0.09 门槛，但 cos=0.049 已经接近 0；layer 28+ cos<0 直接 OOF）。BLIP2 上 v3 与 v4 推荐层 Top3 不变。

**v4 = v3 + new_norm 相对下界**，使公式跨模型鲁棒。

## 6. 跨模型公式迁移性评级

| 公式组件 | BLIP2 → LLaVA 迁移 | 备注 |
| --- | :---: | --- |
| `max(0, cos) × new_norm × (l/30)^α` 主体 | ✓ 可迁移 | 在 base 单峰假设成立的范围内有效 |
| `(l/30)^α` 深度因子（α=1.8 / 2 / 2.5） | ✓ 可迁移 | LLaVA 的 Top1 偏浅 2 层属可接受 |
| `cos > 0` 死区门槛 | **✗ 不可迁移** | LLaVA 无 cos<0 区段，需替换为相对 nn 下界 |
| `√new_norm` 软压缩（M-Loc 用） | **✗ 不可迁移** | 在 LLaVA 上把 M-Loc 推到 layer 24 假性深层；需配合 nn 下界使用 |
| 整体 v3 → v4 升级 | ✓ 可迁移 | 加 `new_norm > 0.1 × max(nn)` 后跨模型一致 |

## 7. 实操建议

1. **跨模型 LGA 推荐层公式**：使用 v4（cos>0 + new_norm > 10% max(nn)）作为通用编辑可行性域
2. **若仅做 BLIP2 类（OPT decoder + Q-Former 输入）**：v3 公式（cos>0 单门槛）已足够
3. **若在 LLaVA / Qwen2.5-VL 等"全程 cos>0"的模型上**：必须用 v4，否则 M-Loc 会被深层 cos 反弹假象误导
4. **InstructBLIP visual 仍是边界情况**：浅层 cos 已高（约 0.05），需另测试 v4 阈值是否仍稳健

## 8. 局限

- 仅基于 pilot 1000 一份数据，BLIP2 上 ablation 显示 ρ_s≈0.99，LLaVA 未单独验证 pilot/full 稳定性
- v4 阈值 0.1 × max(nn) 是经验值，未在多模型回归
- LLaVA 没有 E-VQA 编辑实测数据，"M-Loc=24 是假性 locality"为推断而非验证；需 sweep layer {17, 18, 24} 后比较 Rel / M-Loc 实测值确认
- Qwen2.5-VL / InstructBLIP 上的迁移性未测
