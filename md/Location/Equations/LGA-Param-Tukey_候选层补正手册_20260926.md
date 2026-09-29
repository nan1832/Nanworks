# LGA 参数版：Tukey 候选层补正手册（2026-09-26）

本文件取代历史 LGA 手册中“未经 Tukey 的 raw 排序代表原始 LGA”“Tukey 只作诊断”的规定。旧分数与旧候选保留为 LGA-Param-Raw 消融；补齐过滤后的版本记为 LGA-Param-Tukey（完整名：LGA-Param-Tukey-Direct-AltModelPred）。

## 固定执行规则

1. 沿用历史冻结模型、model_pred/alt、MLP/FFN weight 范围与输入过滤，不重抽样，不更改训练配置。
2. 每个模型与数据集内，对全部 finite/ok 层的带符号原始内积分数计算 Q1、Q3；本次固定 linear 分位数，kappa=1。
3. IQR=Q3−Q1，剔除 score<Q1−IQR 或 score>Q3+IQR 的层，边界保留。
4. 对保留层按分数降序、并列层号升序取 Top-1/3/5，不做 Pre 偏移，不按编辑结果挑选 Raw/Tukey 或阈值。
5. 保存 raw_rank、tukey_rank、Q1/Q3/IQR、上下界、异常层及排除原因、样本覆盖、所有原始文件哈希。
6. 21 组内部每层样本数相同，均值分数与论文求和分数的筛选与排序等价，已验证。
7. 缺少真实编辑评测不填 0；Top-K 全部可比才计算完整指标。main 不收敛实测和 clean 敏感性分别报告；stable 单列。

## 当前执行结果

21/21 定位重算完成，618 条层记录中剔除 76 条；15 组 Top-3/5 改变。Tukey Top-3 尚缺 17 个 main 评测位置，Top-5 尚缺 35 个。这不等于第一阶段真实编辑验证已经全部完成。

[完整报告、候选表和新比较指标](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/outputs/lga_tukey_correction_20260926/LGA_Tukey补正报告.md>)；[待补层清单](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/outputs/lga_tukey_correction_20260926/待补层清单.md>)。

## 原论文依据与复现范围

[Golden Layers v3 附录 A](https://arxiv.org/html/2602.20207v3#A1) 要求 Tukey 剔除并给出默认常数 1。论文未说明分位插值方式；本次显式固定 linear，另存敏感性结果。本次补齐该步骤，不宣称项目的 VLM adapter 编辑设置与原论文 LLM 参数编辑设置完全相同。

## 执行入口

[复算脚本](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/outputs/lga_tukey_correction_20260926/recompute.py>)；[独立核验脚本](<D:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/outputs/lga_tukey_correction_20260926/verify.py>)。输入和输出均在本地补正目录；不覆盖原始服务器结果。
