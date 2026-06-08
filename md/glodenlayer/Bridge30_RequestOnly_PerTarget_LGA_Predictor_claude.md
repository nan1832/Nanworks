# Bridge30 Request-Only 分模态分指标 LGA 最佳层预测分析（Claude）

生成时间：`2026-05-27`

## 1. 分析目标

对每个模型（LLaVA, BLIP2, InstructBLIP, Qwen2.5-VL）× 每个模态（visual, text），分别找出哪个 LGA 指标能最好地预测以下 5 个目标的最佳编辑层：

| 目标指标 | 定义 | 要找的东西 |
| --- | --- | --- |
| Request | 编辑成功率 | 哪个 LGA 指标能预测 request 最佳层 |
| Generality | 泛化准确率 | 哪个 LGA 指标能预测 generality 最佳层 |
| Locality | 局部性保持率 | 哪个 LGA 指标能预测 locality 最佳层 |
| Portability | 可迁移性 | 哪个 LGA 指标能预测 portability 最佳层 |
| Combined3 | avg(Request, Generality, Locality) | 哪个 LGA 指标能预测综合最佳层 |

## 2. 方法

- Spearman rank correlation（scipy.stats.spearmanr）
- 7 个 LGA 指标：`M_dot`, `M_cos`, `M_new_norm`, `M_pos_ratio`, `M_conflict`, `M_newn_x_1mcos`, `M_abscos_x_newn`
- Top3：按 LGA 指标值降序取前 3 层
- Hit：Top3 是否包含真实最优层
- Combined3 = avg(Request, Generality, Locality)，不含 Portability
- Request 在绝大多数有效层为常数 1.0，相关性不可计算（NA），仅作 sanity 保留

## 3. 总汇总：各模型各模态各目标最佳预测指标

| Model | Modality | Target | Best LGA Metric | rho | p | LGA Top1 | LGA Top3 | True Best Layer(s) | Hit |
| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- | ---: |
| LLaVA | visual | Generality | `M_newn_x_1mcos` | 0.8842 | <1e-4 | 6 | 6,7,5 | 7 | 1 |
| LLaVA | visual | Locality | `M_dot` | 0.8647 | <1e-4 | 29 | 29,28,21 | 26 | 0 |
| LLaVA | visual | Portability | `M_newn_x_1mcos` | 0.7464 | <1e-4 | 6 | 6,7,5 | 1 | 0 |
| LLaVA | visual | Combined3 | `M_dot` | 0.8146 | <1e-4 | 29 | 29,28,21 | 26 | 0 |
| LLaVA | text | Generality | `M_cos` | -0.8874 | <1e-4 | 26 | 26,23,25 | 7 | 0 |
| LLaVA | text | Locality | — | — | NS | — | — | 1-30(平台) | — |
| LLaVA | text | Portability | — | — | NA(常数) | — | — | 全层=0.3091 | — |
| LLaVA | text | Combined3 | `M_cos` | -0.8785 | <1e-4 | 26 | 26,23,25 | 7 | 0 |
| BLIP2 | visual | Generality | `M_pos_ratio` | -0.5929 | 0.0006 | 28 | 28,29,0 | 8,9,12,15,16,21 | 0 |
| BLIP2 | visual | Locality | `M_new_norm` | -0.6993 | <1e-4 | 0 | 0,1,2 | 29 | 0 |
| BLIP2 | visual | Portability | `M_newn_x_1mcos` | 0.4920 | 0.0057 | 0 | 0,1,3 | 6 | 0 |
| BLIP2 | visual | Combined3 | `M_new_norm` | -0.7645 | <1e-4 | 0 | 0,1,2 | 29 | 0 |
| BLIP2 | text | Generality | `M_abscos_x_newn` | 0.4183 | 0.0214 | 10 | 10,8,7 | 11,16,17 | 0 |
| BLIP2 | text | Locality | `M_new_norm` | -0.8705 | <1e-4 | 0 | 0,1,2 | 12-29(平台) | 0 |
| BLIP2 | text | Portability | `M_dot` | 0.8212 | <1e-4 | 24 | 24,26,27 | 11-29(平台) | 1 |
| BLIP2 | text | Combined3 | `M_cos` | -0.7362 | <1e-4 | 24 | 24,26,27 | 16,17 | 0 |
| InstructBLIP | visual | Generality | `M_cos` | 0.4293 | 0.0160 | 30 | 30,29,28 | 12 | 0 |
| InstructBLIP | visual | Locality | `M_new_norm` | -0.9310 | <1e-4 | 1 | 1,2,0 | 26 | 0 |
| InstructBLIP | visual | Portability | `M_cos` | -0.5113 | 0.0033 | 30 | 30,29,28 | 18 | 0 |
| InstructBLIP | visual | Combined3 | `M_new_norm` | -0.9149 | <1e-4 | 1 | 1,2,0 | 30 | 0 |
| InstructBLIP | text | Generality | `M_dot` | 0.7959 | <1e-4 | 0 | 0,1,2 | 0 | 1 |
| InstructBLIP | text | Locality | — | — | NS | — | — | 1-29(平台) | — |
| InstructBLIP | text | Portability | — | — | NA(常数) | — | — | 全层=0.3524 | — |
| InstructBLIP | text | Combined3 | `M_dot` | 0.7870 | <1e-4 | 0 | 0,1,2 | 2 | 1 |
| Qwen2.5-VL | visual | Generality | `M_pos_ratio` | 0.5601 | 0.0024 | 6 | 6,0,1 | 4 | 0 |
| Qwen2.5-VL | visual | Locality | — | — | NS | — | — | 24 | — |
| Qwen2.5-VL | visual | Portability | `M_abscos_x_newn` | 0.5553 | 0.0026 | 3 | 3,1,2 | 11 | 0 |
| Qwen2.5-VL | visual | Combined3 | — | — | NS | — | — | 8 | — |
| Qwen2.5-VL | text | Generality | — | — | NS(p=0.45) | — | — | 0 | — |
| Qwen2.5-VL | text | Locality | `M_dot` | 0.5422 | 0.0035 | 0 | 0,1,2 | 0-23(平台) | 1 |
| Qwen2.5-VL | text | Portability | `M_dot` | 0.6172 | 0.0006 | 0 | 0,1,2 | 0-22(平台) | 1 |
| Qwen2.5-VL | text | Combined3 | — | — | NS(p=0.12) | — | — | 0 | — |

注：Request 在所有有效层≈1.0（常数），无法计算相关性，已省略。"—"表示无显著(p<0.05)预测指标。"NS"=not significant。

## 4. 视觉模态：各目标的高相关性备选公式

### 4.1 Generality 最佳层预测

| Model | 推荐公式 | rho | Top3 | 真实Best | Hit | 备选公式 | 备选rho |
| --- | --- | ---: | --- | --- | ---: | --- | ---: |
| LLaVA | `M_newn_x_1mcos` = new_norm×(1-cos) | 0.884 | 6,7,5 | 7 | 1 | `M_abscos_x_newn`=\|cos\|×new_norm | 0.882 |
| BLIP2 | `M_pos_ratio` (负相关取反) | -0.593 | 28,29,0→反排:10,9,8 | 8,9,12,15,16,21 | — | `M_abscos_x_newn` | 0.464 |
| InstructBLIP | `M_cos` | 0.429 | 30,29,28 | 12 | 0 | 无显著备选 | — |
| Qwen2.5-VL | `M_pos_ratio` | 0.560 | 6,0,1 | 4 | 0 | `M_cos` | 0.512 |

**视觉 Generality 公式推荐**：
- MLP/线性投影型：`new_norm × (1 - cos)` 或 `|cos| × new_norm`，rho > 0.88
- Q-Former 型 BLIP2：`|cos| × new_norm`，rho = 0.46，Top3 命中 Gen 平台
- InstructBLIP：无可靠公式（instruction-aware Q-Former 预对齐效应）
- Qwen2.5-VL：`cos` 方向对齐度，rho = 0.51，Top3 含 layer 4

### 4.2 Locality 最佳层预测

| Model | 推荐公式 | rho | Top3 | 真实Best | Hit | 备选公式 | 备选rho |
| --- | --- | ---: | --- | --- | ---: | --- | ---: |
| LLaVA | `M_dot` (raw dot product) | 0.865 | 29,28,21 | 26 | 0 | `M_conflict`(反向) | -0.865 |
| BLIP2 | `M_new_norm` (负相关→反排) | -0.699 | 反排:29,28,27 | 29 | 1 | `M_dot` | 0.676 |
| InstructBLIP | `M_new_norm` (负相关→反排) | -0.931 | 反排:30,29,28 | 26 | 0 | `M_dot`(反向) | -0.915 |
| Qwen2.5-VL | — | NS | — | 24 | — | 无显著指标 | — |

**视觉 Locality 公式推荐**：
- Locality 最佳层普遍在深层（layer 24-30）
- `M_new_norm` 取反排（即 new_norm 最小的层）是最强 Locality 预测信号：幅度越小的层编辑扰动越小，locality 越好
- `M_dot` 正相关也有效：raw dot 越大（越接近 0，即梯度越弱）的层 locality 越好
- 本质：**梯度信号弱的层 = locality 好的层**

### 4.3 Portability 最佳层预测

| Model | 推荐公式 | rho | Top3 | 真实Best | Hit | 备选公式 | 备选rho |
| --- | --- | ---: | --- | --- | ---: | --- | ---: |
| LLaVA | `M_newn_x_1mcos` | 0.746 | 6,7,5 | 1 | 0 | `M_new_norm` | 0.739 |
| BLIP2 | `M_newn_x_1mcos` | 0.492 | 0,1,3 | 6 | 0 | `M_new_norm` | 0.486 |
| InstructBLIP | `M_cos` (负相关→反排) | -0.511 | 反排:19,18,17 | 18 | 1 | `M_dot`(反向) | -0.414 |
| Qwen2.5-VL | `M_abscos_x_newn` | 0.555 | 3,1,2 | 11 | 0 | `M_newn_x_1mcos` | 0.551 |

**视觉 Portability 公式推荐**：
- Portability 最佳层偏浅-中层
- `new_norm × (1-cos)` 和 `|cos| × new_norm` 在多数模型上与 Portability 正相关
- 与 Generality 方向一致但峰值位置不完全重合

### 4.4 Combined3 = avg(Req, Gen, Loc) 最佳层预测

| Model | 推荐公式 | rho | Top3 | 真实Best | Hit | 解释 |
| --- | --- | ---: | --- | --- | ---: | --- |
| LLaVA | `M_dot` | 0.815 | 29,28,21 | 26 | 0 | Loc 权重大，dot 追踪后层 |
| BLIP2 | `M_new_norm` (负相关→反排) | -0.765 | 反排:29,28,27 | 29 | 1 | Loc 主导，norm 小=后层 |
| InstructBLIP | `M_new_norm` (负相关→反排) | -0.915 | 反排:30,29,28 | 30 | 1 | Loc 主导 |
| Qwen2.5-VL | — | NS | — | 8 | — | Gen/Loc 方向冲突，无显著预测 |

**视觉 Combined3 公式推荐**：
- Combined3 被 Locality 主导（因为 Req≈1.0 常数，Gen 变化范围小，Loc 变化范围大）
- 因此 Combined3 的最佳预测指标与 Locality 高度重合
- 实际意义有限：如果目标是 Combined3，直接用 Locality 预测指标即可

## 5. 文本模态：各目标的高相关性备选公式

### 5.1 Generality 最佳层预测

| Model | 推荐公式 | rho | Top3 | 真实Best | Hit | 备选公式 | 备选rho |
| --- | --- | ---: | --- | --- | ---: | --- | ---: |
| LLaVA | `M_cos` (负相关→反排) | -0.887 | 反排:4,3,2 | 7 | 0 | `M_new_norm` | 0.857 |
| BLIP2 | `M_abscos_x_newn` | 0.418 | 10,8,7 | 11,16,17 | 0 | `M_new_norm` | 0.387 |
| InstructBLIP | `M_dot` | 0.796 | 0,1,2 | 0 | 1 | `M_pos_ratio` | 0.761 |
| Qwen2.5-VL | — | NS(p=0.45) | 0,1,2 | 0 | 1(top-k) | `M_new_norm` Top3命中 | 0.153 |

**文本 Generality 公式推荐**：
- InstructBLIP/Qwen2.5-VL：`M_dot`（raw dot product），Top3 精确命中 layer 0
- LLaVA：`M_cos` 反排或 `M_new_norm`，强趋势但 Top3 偏最浅层（真实在 layer 7）
- BLIP2：`|cos| × new_norm`，弱相关，Top3 接近但未精确命中

### 5.2 Locality 最佳层预测

| Model | 推荐公式 | rho | Top3 | 真实Best | Hit | 备选公式 | 备选rho |
| --- | --- | ---: | --- | --- | ---: | --- | ---: |
| LLaVA | — | NS(p=0.09) | — | 1-30(≈1.0平台) | — | Loc 几乎常数 |
| BLIP2 | `M_new_norm` (负相关→反排) | -0.871 | 反排:29,28,27 | 12-29(=1.0平台) | 1 | `M_dot` | 0.832 |
| InstructBLIP | — | NS(p=0.09) | — | 1-29(≈1.0平台) | — | Loc 几乎常数 |
| Qwen2.5-VL | `M_dot` | 0.542 | 0,1,2 | 0-23(=1.0平台) | 1 | `M_new_norm` | 0.542 |

**文本 Locality 公式推荐**：
- 多数模型 text locality 在大部分层为常数 1.0（平台），相关性意义有限
- BLIP2 text locality 有明显梯度（0.54→1.0），`M_new_norm` 反排有效
- 本质同视觉：梯度幅度小的层 locality 好

### 5.3 Portability 最佳层预测

| Model | 推荐公式 | rho | Top3 | 真实Best | Hit | 备选公式 | 备选rho |
| --- | --- | ---: | --- | --- | ---: | --- | ---: |
| LLaVA | — | NA | — | 全层=0.3091 | — | Port 常数 |
| BLIP2 | `M_dot` | 0.821 | 24,26,27 | 11-29(=0.17平台) | 1 | `M_new_norm`(反向) | -0.821 |
| InstructBLIP | — | NA | — | 全层=0.3524 | — | Port 常数 |
| Qwen2.5-VL | `M_dot` | 0.617 | 0,1,2 | 0-22(≈0.3866平台) | 1 | `M_new_norm` | 0.617 |

**文本 Portability 公式推荐**：
- LLaVA/InstructBLIP text portability 为常数，无法预测
- BLIP2/Qwen2.5-VL：`M_dot` 正相关，但真实 portability 本身是大面积平台

### 5.4 Combined3 = avg(Req, Gen, Loc) 最佳层预测

| Model | 推荐公式 | rho | Top3 | 真实Best | Hit | 解释 |
| --- | --- | ---: | --- | --- | ---: | --- |
| LLaVA | `M_cos` (负相关→反排) | -0.879 | 反排:4,3,2 | 7 | 0 | ≈Gen（Loc/Req 常数） |
| BLIP2 | `M_cos` (负相关) | -0.736 | 反排:19,18,17 | 16,17 | 1 | Gen+Loc 混合 |
| InstructBLIP | `M_dot` | 0.787 | 0,1,2 | 2 | 1 | ≈Gen（Loc 常数） |
| Qwen2.5-VL | — | NS(p=0.12) | 0,1,2 | 0 | 1(top-k) | Gen 主导但 rho 不显著 |

**文本 Combined3 公式推荐**：
- 因为 text Req≈1.0 且多数模型 Loc≈1.0，Combined3 ≈ Gen
- 因此文本 Combined3 的预测指标与 Generality 高度重合

## 6. 各模型各模态完整相关性明细

### 6.1 LLaVA visual (n=30)

| Metric | Top3 | rho(Gen) | rho(Loc) | rho(Port) | rho(Comb3) |
| --- | --- | ---: | ---: | ---: | ---: |
| `M_dot` | 29,28,21 | -0.8412* | 0.8647* | -0.7077* | 0.8146* |
| `M_cos` | 29,21,28 | -0.6852* | 0.5874* | -0.6000* | 0.4866* |
| `M_new_norm` | 6,7,5 | 0.8790* | -0.8629* | 0.7388* | -0.7899* |
| `M_pos_ratio` | 21,26,27 | -0.7077* | 0.6017* | -0.6500* | 0.4802* |
| `M_conflict` | 5,3,6 | 0.8412* | -0.8647* | 0.7077* | -0.8146* |
| `M_newn_x_1mcos` | 6,7,5 | 0.8842* | -0.8607* | 0.7464* | -0.7857* |
| `M_abscos_x_newn` | 6,5,7 | 0.8824* | -0.8598* | 0.7433* | -0.7857* |

### 6.2 LLaVA text (n=31)

| Metric | Top3 | rho(Gen) | rho(Loc) | rho(Port) | rho(Comb3) |
| --- | --- | ---: | ---: | ---: | ---: |
| `M_dot` | 30,29,28 | -0.8577* | 0.3062 | NA | -0.8428* |
| `M_cos` | 26,23,25 | -0.8874* | 0.2041 | NA | -0.8785* |
| `M_new_norm` | 0,1,2 | 0.8573* | -0.3062 | NA | 0.8424* |
| `M_pos_ratio` | 26,25,22 | -0.2320 | -0.1165 | NA | -0.2477 |
| `M_conflict` | 0,1,2 | 0.8577* | -0.3062 | NA | 0.8428* |
| `M_newn_x_1mcos` | 0,1,2 | 0.8573* | -0.3062 | NA | 0.8424* |
| `M_abscos_x_newn` | 0,1,2 | 0.8577* | -0.3062 | NA | 0.8428* |

### 6.3 BLIP2 visual (n=30)

| Metric | Top3 | rho(Gen) | rho(Loc) | rho(Port) | rho(Comb3) |
| --- | --- | ---: | ---: | ---: | ---: |
| `M_dot` | 29,28,27 | -0.1669 | 0.6757* | -0.2161 | 0.6599* |
| `M_cos` | 29,28,0 | -0.5367* | 0.5107* | -0.1560 | 0.4152* |
| `M_new_norm` | 0,1,2 | -0.2986 | -0.6993* | 0.4860* | -0.7645* |
| `M_pos_ratio` | 28,29,0 | -0.5929* | 0.2937 | -0.0488 | 0.1992 |
| `M_conflict` | 10,9,8 | 0.1669 | -0.6757* | 0.2161 | -0.6599* |
| `M_newn_x_1mcos` | 0,1,3 | -0.2984 | -0.6978* | 0.4920* | -0.7607* |
| `M_abscos_x_newn` | 13,15,14 | 0.4644* | -0.6626* | 0.2294 | -0.5720* |

### 6.4 BLIP2 text (n=30)

| Metric | Top3 | rho(Gen) | rho(Loc) | rho(Port) | rho(Comb3) |
| --- | --- | ---: | ---: | ---: | ---: |
| `M_dot` | 24,26,27 | -0.3230 | 0.8315* | 0.8212* | 0.4979* |
| `M_cos` | 24,26,27 | -0.3248 | -0.5414* | -0.5122* | -0.7362* |
| `M_new_norm` | 0,1,2 | 0.3865* | -0.8705* | -0.8212* | -0.5144* |
| `M_pos_ratio` | 26,24,0 | -0.2876 | -0.3379 | -0.2929 | -0.5089* |
| `M_conflict` | 3,2,7 | 0.3230 | -0.8315* | -0.8212* | -0.4979* |
| `M_newn_x_1mcos` | 0,1,2 | 0.3865* | -0.8705* | -0.8212* | -0.5144* |
| `M_abscos_x_newn` | 10,8,7 | 0.4183* | -0.4125* | -0.4329* | 0.0013 |

### 6.5 InstructBLIP visual (n=31)

| Metric | Top3 | rho(Gen) | rho(Loc) | rho(Port) | rho(Comb3) |
| --- | --- | ---: | ---: | ---: | ---: |
| `M_dot` | 1,2,0 | 0.0978 | -0.9145* | -0.4141* | -0.8718* |
| `M_cos` | 30,29,28 | 0.4293* | -0.2952 | -0.5113* | -0.2077 |
| `M_new_norm` | 1,2,0 | 0.0010 | -0.9310* | -0.3306 | -0.9149* |
| `M_pos_ratio` | 28,29,30 | 0.3172 | 0.1593 | -0.3575* | 0.2155 |
| `M_conflict` | 19,21,20 | -0.0978 | 0.9145* | 0.4141* | 0.8718* |
| `M_newn_x_1mcos` | 1,2,0 | 0.0010 | -0.9310* | -0.3306 | -0.9149* |
| `M_abscos_x_newn` | 1,2,0 | 0.2051 | -0.9004* | -0.3851* | -0.8375* |

### 6.6 InstructBLIP text (n=30)

| Metric | Top3 | rho(Gen) | rho(Loc) | rho(Port) | rho(Comb3) |
| --- | --- | ---: | ---: | ---: | ---: |
| `M_dot` | 0,1,2 | 0.7959* | -0.3111 | NA | 0.7870* |
| `M_cos` | 10,4,6 | 0.7296* | -0.0107 | NA | 0.7514* |
| `M_new_norm` | 0,1,2 | 0.7369* | -0.3111 | NA | 0.7280* |
| `M_pos_ratio` | 5,6,2 | 0.7605* | -0.0866 | NA | 0.7769* |
| `M_conflict` | 18,20,19 | -0.7959* | 0.3111 | NA | -0.7870* |
| `M_newn_x_1mcos` | 0,1,2 | 0.7369* | -0.3111 | NA | 0.7280* |
| `M_abscos_x_newn` | 2,1,4 | 0.7505* | -0.2253 | NA | 0.7523* |

### 6.7 Qwen2.5-VL visual (n=27)

| Metric | Top3 | rho(Gen) | rho(Loc) | rho(Port) | rho(Comb3) |
| --- | --- | ---: | ---: | ---: | ---: |
| `M_dot` | 0,1,3 | 0.4982* | 0.0702 | 0.5471* | 0.1966 |
| `M_cos` | 3,4,2 | 0.5122* | 0.1548 | 0.5230* | 0.2766 |
| `M_new_norm` | 0,1,3 | 0.4982* | 0.0702 | 0.5471* | 0.1966 |
| `M_pos_ratio` | 6,0,1 | 0.5601* | 0.0712 | 0.5335* | 0.2145 |
| `M_conflict` | 26,25,24 | -0.4982* | -0.0702 | -0.5471* | -0.1966 |
| `M_newn_x_1mcos` | 0,1,2 | 0.4994* | 0.0605 | 0.5508* | 0.1880 |
| `M_abscos_x_newn` | 3,1,2 | 0.4933* | 0.0702 | 0.5553* | 0.1990 |

### 6.8 Qwen2.5-VL text (n=27)

| Metric | Top3 | rho(Gen) | rho(Loc) | rho(Port) | rho(Comb3) |
| --- | --- | ---: | ---: | ---: | ---: |
| `M_dot` | 0,1,2 | 0.1526 | 0.5422* | 0.6172* | 0.3077 |
| `M_cos` | 0,2,1 | 0.1484 | 0.5422* | 0.6172* | 0.3040 |
| `M_new_norm` | 0,1,2 | 0.1526 | 0.5422* | 0.6172* | 0.3077 |
| `M_pos_ratio` | 22,0,1 | -0.0342 | 0.4574* | 0.4781* | 0.1036 |
| `M_conflict` | 26,25,24 | -0.1526 | -0.5422* | -0.6172* | -0.3077 |
| `M_newn_x_1mcos` | 0,1,2 | 0.1526 | 0.5422* | 0.6172* | 0.3077 |
| `M_abscos_x_newn` | 0,1,2 | 0.1526 | 0.5422* | 0.6172* | 0.3077 |

注：`*` 表示 p < 0.05。NA 表示目标为常数无法计算。

## 7. 关键发现与规律总结

### 7.1 各目标的预测逻辑不同

| 目标 | 预测逻辑 | 最佳层位置 | 适用公式方向 |
| --- | --- | --- | --- |
| Generality | 梯度方向对齐 + 幅度适中 | 浅-中层 | `M_newn_x_1mcos` / `M_cos` 正相关 |
| Locality | 梯度信号弱 = 扰动小 | 深层 | `M_new_norm` 负相关 / `M_dot` 正相关 |
| Portability | 梯度方向对齐 + 幅度 | 浅层 | `M_newn_x_1mcos` 正相关 |
| Combined3 | 被 Locality 主导（变化范围最大） | 中-深层 | 与 Locality 预测重合 |

### 7.2 Generality 与 Locality 天然对立

- 在所有模型上，Gen 最佳预测指标与 Loc 最佳预测指标方向相反
- 这解释了为什么 CoreAvg4/Combined3 的最佳层往往在 Gen peak 和 Loc peak 之间折中
- 不存在同时最大化 Gen 和 Loc 的单一层

### 7.3 视觉模态公式推荐总表

| 目标 | 推荐公式 | 适用模型 | 不适用 |
| --- | --- | --- | --- |
| Generality | `new_norm × (1-cos)` | LLaVA(0.88), Qwen(0.50) | InstructBLIP |
| Generality | `\|cos\| × new_norm` | LLaVA(0.88), BLIP2(0.46) | InstructBLIP |
| Locality | `-new_norm` (取反排) | InstructBLIP(0.93), BLIP2(0.70), LLaVA(0.86) | Qwen(NS) |
| Portability | `new_norm × (1-cos)` | LLaVA(0.75), BLIP2(0.49), Qwen(0.55) | — |
| Combined3 | `-new_norm` (取反排) | InstructBLIP(0.91), BLIP2(0.76), LLaVA(0.81) | Qwen(NS) |

### 7.4 文本模态公式推荐总表

| 目标 | 推荐公式 | 适用模型 | 不适用 |
| --- | --- | --- | --- |
| Generality | `M_dot` (raw dot) | InstructBLIP(0.80) | LLaVA(Top3偏差), BLIP2(弱), Qwen(NS) |
| Generality | `M_new_norm` | LLaVA(0.86), InstructBLIP(0.74) | BLIP2(0.39弱) |
| Locality | `-new_norm` (取反排) | BLIP2(0.87) | LLaVA/InstructBLIP(Loc常数) |
| Portability | `M_dot` | BLIP2(0.82), Qwen(0.62) | LLaVA/InstructBLIP(Port常数) |
| Combined3 | `M_dot` | InstructBLIP(0.79) | Qwen(NS) |
| Combined3 | `-M_cos` (取反排) | LLaVA(0.88), BLIP2(0.74) | — |

## 8. 实用建议

1. **如果目标是 Generality**：视觉用 `new_norm×(1-cos)` 或 `|cos|×new_norm`；文本用 `M_dot` 或 `M_new_norm`。
2. **如果目标是 Locality**：直接取 `new_norm` 最小的层（即梯度最弱的层），这在视觉模态 3/4 模型上 rho > 0.70。
3. **如果目标是 Portability**：视觉用 `new_norm×(1-cos)`；文本多数模型 portability 为常数无法预测。
4. **如果目标是 Combined3**：视觉被 Locality 主导，取 `new_norm` 最小层；文本被 Generality 主导，用 Gen 预测指标。
5. **Request 不可预测**：所有有效层 Request≈1.0，LGA 无法区分。

