# 原始 LGA 公式整理表

## 1. LGA 公式形式

| 公式形式 | 数学表达 | 含义 | 解释 |
|---|---|---|---|
| 原始 LGA 形式 | $S_{\mathrm{LGA}}(l)=\sum_i \left\langle g^{l}_{old,i}, g^{l}_{new,i} \right\rangle$ | 计算旧知识梯度与新知识梯度在第 $l$ 层的整体内积 | 若内积越大，说明旧知识梯度与新知识梯度方向越一致，该层越可能适合知识编辑 |
| 向量分解形式 | $S_{\mathrm{LGA}}(l)=\sum_i \left\|g^{l}_{old,i}\right\|\cdot \left\|g^{l}_{new,i}\right\|\cdot \cos\left(g^{l}_{old,i},g^{l}_{new,i}\right)$ | 将梯度内积分解为梯度强度与方向一致性 | 该公式说明 LGA 分数同时受到旧知识梯度强度、新知识梯度强度和二者方向一致性的影响 |

## 2. 符号说明

| 符号 | 含义 |
|---|---|
| $l$ | 模型层编号 |
| $i$ | 第 $i$ 个编辑样本 |
| $g^{l}_{old,i}$ | 第 $i$ 个样本在第 $l$ 层对应旧知识的梯度 |
| $g^{l}_{new,i}$ | 第 $i$ 个样本在第 $l$ 层对应新知识的梯度 |
| $\left\langle g^{l}_{old,i}, g^{l}_{new,i} \right\rangle$ | 旧知识梯度与新知识梯度的内积 |
| $\left\|g^{l}_{old,i}\right\|$ | 旧知识梯度强度 |
| $\left\|g^{l}_{new,i}\right\|$ | 新知识写入强度 |
| $\cos\left(g^{l}_{old,i},g^{l}_{new,i}\right)$ | 旧知识梯度与新知识梯度的方向一致性 |

## 3. 文字解释

原始 LGA 分数本质上是旧知识梯度与新知识梯度在各编辑样本上的内积求和。进一步展开可知，该分数由三个因素共同决定：旧知识梯度强度、新知识写入强度以及二者的方向一致性。因此，LGA 不仅衡量梯度幅度大小，也刻画新旧知识更新方向是否一致。

## 4. LGA 视觉候选层公式池（待检验）

本节把 `md/glodenlayer` 中出现过的 LGA 视觉候选层排序公式集中到一起。检验时建议不要只看 Top1，而是同时看 Top3/Top5 是否覆盖真实 sweep 最优层。

### 4.1 基础视觉 LGA 指标

这些指标来自 Virtual Delta-h / visual hidden LGA 逐层统计，是后续所有排序公式的输入。

| 编号 | 指标 | 公式 | 排序方向 | 含义 |
|---|---|---|---|---|
| V1 | `M_dot` | $S_v^{dot}(l)$ | 通常降序 | 视觉分支 raw dot，表示旧/新方向的原始内积 |
| V2 | `M_cos` | $S_v^{cos}(l)$ | 视目标而定 | 方向一致性 |
| V3 | `M_new_norm` | $S_v^{new\_norm}(l)$ | 视目标而定 | 新知识写入强度 |
| V4 | `M_old_norm` | $S_v^{old\_norm}(l)$ | 视目标而定 | 旧知识梯度强度 |
| V5 | `M_joint_norm` | $S_v^{joint\_norm}(l)$ | 视目标而定 | 旧/新联合强度 |
| V6 | `M_conflict` | $S_v^{conflict}(l)$ | 视目标而定 | 梯度冲突程度 |
| V7 | `M_pos_ratio` | $S_v^{positive\_ratio}(l)$ | 视目标而定 | 正向梯度比例 |
| V8 | `M_newn_x_1mcos` | $S_v^{new\_norm}(l)\cdot(1-S_v^{cos}(l))$ | 通常降序 | 强度乘方向偏移 |
| V9 | `M_newn_x_pos` | $S_v^{new\_norm}(l)\cdot S_v^{positive\_ratio}(l)$ | 通常降序 | 强度乘正向比例 |
| V10 | `M_abscos_x_newn` | $\left|S_v^{cos}(l)\right|\cdot S_v^{new\_norm}(l)$ | 通常降序 | BLIP2 Bridge30 中曾作为视觉主指标 |

来源：`EVQA_RequestOnly_BLIP2_LGA_候选层计算实验计划_gpt.md`、`Bridge30_RequestOnly_PerTarget_LGA_Predictor_claude.md`、`CrossModel_VisualText_GoldenLayer_LGA_汇总分析_gpt.md`。

### 4.2 Bridge30 迁移得到的视觉候选层公式

这些公式主要来自 Bridge30 的相关性分析，后来直接迁移到 E-VQA BLIP2 时出现过偏浅或偏深的问题，因此适合作为对照组。

| 编号 | 目标 | 公式 | 排序方向 | 在 BLIP2 visual 上的记录/风险 |
|---|---|---|---|---|
| B1 | Generality | $M_{abscos\_x\_newn}(l)=\left|S_v^{cos}(l)\right|\cdot S_v^{new\_norm}(l)$ | 降序 Top | Bridge30 上可给中层候选；E-VQA 上会偏向 layer 0 |
| B2 | Locality | $M_{new\_norm}(l)=S_v^{new\_norm}(l)$ | 升序 Top，即反排 | Bridge30 上指向深层；E-VQA 上会推到 layer 30，但该层 cos 反向 |
| B3 | Combined/Average | $M_{new\_norm}(l)=S_v^{new\_norm}(l)$ | 升序 Top，即反排 | Loc 主导假设；E-VQA 真实编辑中失效 |
| B4 | Portability | $M_{newn\_x\_1mcos}(l)=S_v^{new\_norm}(l)(1-S_v^{cos}(l))$ | 降序 Top | Bridge30 BLIP2 visual 备选公式 |
| B5 | Generality 备选 | $M_{pos\_ratio}(l)=S_v^{positive\_ratio}(l)$ | 若 rho 为负则反排 | Bridge30 表中 BLIP2 visual Gen 的强相关项，但解释不稳定 |

来源：`BLIP2_EVQA_Visual_LayerPrediction_claude.md`、`Bridge30_RequestOnly_PerTarget_LGA_Predictor_claude.md`。

### 4.3 E-VQA BLIP2 旧版拐点公式

该公式在旧版文件的失败诊断后提出，核心思想是不用单调取极值，而是在可写入区域内找 cos 曲线松动/塌陷前的拐点。

```text
有效层判据:
S_v_cos(l) > cos_min AND S_v_new_norm(l) > norm_min

建议:
cos_min = 0.08
norm_min = 0.30

评分:
M_edit_sweet(l) = -|S_v_cos(l) - S_v_cos(l+1)|

或等价写成:
argmax_l { S_v_cos(l) - S_v_cos(l+k) }, k = 2 或 3
```

在 `BLIP2_EVQA_Visual_LayerPrediction_claude.md` 中，该规则给出 E-VQA BLIP2 visual 的 **Top1 = layer 19**，Top3 可取 `{19, 20, 18}` 或保守 `{18, 19, 20, 22}`。风险是拐点检测对噪声敏感，且属于事后规则。

### 4.4 E-VQA BLIP2 修正版 v2 公式

v2 的思想是先排除编辑死区，再用“方向对齐 × 写入强度 × 深度权重”制造中段峰值。

```text
L = 30
F = { l : 0 <= l <= 22, S_v_cos(l) > 0.08, S_v_new_norm(l) > 0.25 }
```

| 编号 | 目标 | 公式 | 排序方向 | v2 记录 |
|---|---|---|---|---|
| E1 | Request / Rel | $M_{rel}(l)=\max(0,S_v^{cos}(l))\cdot S_v^{new\_norm}(l)\cdot(l/30)^{1.8}$, $l\in F$ | 降序 Top | Top1 约为 18，Top3 覆盖 17/18/19 |
| E2 | Generality | $M_{gen}(l)=\max(0,S_v^{cos}(l))\cdot S_v^{new\_norm}(l)\cdot(l/30)^{2.5}$, $l\in F$ | 降序 Top | Top3 `{18,19,17}` |
| E3 | Locality / M-Loc | $M_{loc}(l)=\max(0,S_v^{cos}(l))\cdot\sqrt{S_v^{new\_norm}(l)}\cdot(l/30)^2$, $l\in F$ | 降序 Top | Top3 `{18,19,17}` |
| E4 | Average | $M_{avg}(l)=\max(0,S_v^{cos}(l))\cdot S_v^{new\_norm}(l)\cdot(l/30)^2$, $l\in F$ | 降序 Top | Top3 `{18,17,19}` |

来源：`BLIP2_EVQA_Visual_LayerPrediction_v2_claude.md`。

### 4.5 E-VQA BLIP2 v3 可行域松弛公式

v3 保持 v2 的得分公式不变，但把可行域从固定阈值放宽为只排除方向反对齐层。

```text
F' = { l : S_v_cos(l) > 0 }
E-VQA BLIP2 上 F' = layers 0-27
死区 OOF = layers 28, 29, 30
```

使用的排序公式仍是：

```text
M_rel(l) = max(0, S_v_cos(l)) * S_v_new_norm(l) * (l/30)^1.8
M_gen(l) = max(0, S_v_cos(l)) * S_v_new_norm(l) * (l/30)^2.5
M_loc(l) = max(0, S_v_cos(l)) * sqrt(S_v_new_norm(l)) * (l/30)^2
M_avg(l) = max(0, S_v_cos(l)) * S_v_new_norm(l) * (l/30)^2
```

`BLIP2_EVQA_Visual_PilotVsFull_DataVolumeAblation_claude.md` 记录：pilot 1000 与 full 6345 在这些公式下 Top1/Top3 基本一致，Top1 多数指向 layer 18，论文采样实测最佳是 layer 19。

### 4.6 通用 LGA 视觉候选层公式

通用公式把候选层选择拆成两步：先确定可行域，再在可行域内排序。

```text
F = { l : cos(l) > 0 AND nn(l) > τ * max(nn) }
τ 推荐 0.10
L = num_layers - 1
```

通用排序式：

```text
M_gen(l) = cos(l) * nn(l)      * (l/L)^α_gen    l in F
M_loc(l) = cos(l) * nn(l)^β    * (l/L)^α_loc    l in F
M_avg(l) = cos(l) * nn(l)      * (l/L)^α_avg    l in F
M_rel(l) = cos(l) * nn(l)      * (l/L)^α_rel    l in F
```

推荐参数：

| 参数 | 推荐值 | 解释 |
|---|---:|---|
| $\tau$ | 0.10 | 排除写入强度耗尽层 |
| $\alpha_{gen}$ | 2.5 | Gen 需要更强深度推力 |
| $\alpha_{loc}$ | 2.0 | Loc 用中等深度推力 |
| $\alpha_{avg}$ | 2.0 | Average 折中 |
| $\alpha_{rel}$ | 1.8 | Rel 深度需求略弱 |
| $\beta$ | 0.5 | Loc 用 $\sqrt{nn}$ 软压缩写入强度 |

来源：`Universal_LGA_LayerPrediction_Formula_claude.md`。

### 4.7 Locality 双轨检验公式

Loc 最难通用化，建议同时检验保守和激进两条轨道：

| 轨道 | 公式 | 适用场景 |
|---|---|---|
| 保守轨 | $M_{loc}(l)=\cos(l)\cdot\sqrt{nn(l)}\cdot(l/L)^2$, $l\in F$ | E-VQA 这类复杂编辑，深层可能崩盘 |
| 激进轨 | 在 $F$ 内取 $nn(l)$ 最小的层 | Bridge30 这类简单编辑，深层仍可写入 |

### 4.8 检验建议

1. 先用真实 sweep 结果定义 ground truth：每个目标分别记录 Rel / Gen / M-Loc / Avg 的最佳层。
2. 对每个公式分别算 Top1、Top3、Top5，并记录是否命中 ground truth。
3. 对 E-VQA BLIP2 visual，重点比较这几组：`M_edit_sweet`、v2/v3 深度加权公式、通用公式、Bridge30 旧公式。
4. 如果公式把 Top1 推到 layer 0 或 layer 30，要检查是否只是单调极值假象：layer 0 可能是浅层词法重叠，layer 30 可能是 cos 反向或写不进去。
5. 最终不要只选一个公式直接定层，建议取各公式 Top3 并集后做小规模 sweep。
