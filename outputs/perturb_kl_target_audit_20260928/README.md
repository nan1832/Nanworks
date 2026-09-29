# Perturb-KL 答案条件版本核验

服务器原始产物核验时间：2026-09-28 20:12:34 +08:00（服务器时钟）。

结论：当前可核验的正式 Perturb-KL 实验为 alt 序列条件版，7 个模型 × 3 个数据集共 21 组；未找到 Perturb-KL-model_pred 已完成结果。此结论针对本项目可访问的代码和归档，不将“未找到”扩展为对已删除或未归档历史运行的保证。

| 数据集 | 正式结果组数 | target_sequence | score_source | 完成凭据 |
|---|---:|---|---|---|
| EVQA-pilot500 | 7 | complete alt sequence | visual_token_noise_altseq_kl | summary status=done、DONE、层分数 CSV |
| MMKE-visual | 7 | complete alt sequence | visual_token_noise_altseq_kl | summary status=done、DONE、层分数 CSV |
| MMKE-entity | 7 | complete alt sequence | visual_token_noise_altseq_kl | summary status=done、DONE、层分数 CSV |

正式服务器目录：

`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/perturb_kl_direct_7models_3datasets_g08_gpu0_20260622_211701`

同名 `_backup_20260623_104143` 旧备份中的 3 份 summary 也全部标记为 `complete alt sequence`，并非另一个 model_pred 版本。本地正式 21 份 summary 与本次服务器版本的 SHA-256 全部一致。

扩展只读检索覆盖本项目两处 `server_results`、`eval_results`、`records` 及 `custom_runs`、`scripts`、项目 `tmp`、`trae` 等 10 个根目录；枚举 49,879 个文件，读取 870 份小型 JSON 元数据，命中 215 个扰动相关路径和 10 份相关脚本（含历史副本），未发生读取错误。排除模型权重、数据集、环境、检查点及逐样本子目录；没有检查计算节点的独立 `/tmp` 或已删除的运行。

代码交叉核验：本地运行脚本、服务器运行脚本、2026-09-24 交接归档中的脚本 SHA-256 相同，均为 `e09d30f5409eba5a9727f94a4a6f04b74fe555ca5939c948d65c5f4d576bf9d7`。

- `VisEdit-main/scripts/run_perturb_kl_direct_candidate_layers.py:31`：`SCORE_SOURCE = "visual_token_noise_altseq_kl"`。
- 第 174 行：MMKE 数据映射 `target_new = row["alt"]`。
- 第 380 行：计算时读取 `target = req["target_new"]`。
- 第 724 行：输出 `target_sequence = "complete alt sequence"`。
- 命令行参数没有 model_pred 目标切换选项。

`md/Location/PerturbKLPre_outputs_20260704/perturb_kl_pre_candidate_layers_topk.md` 第 1、3 行明确表明：Pre 为 `Perturb-KL-Pre-AltSeq`，复用 Direct-AltSeq 分数进行派生，没有另做模型前向或扰动实验。因此 Direct/Pre 也不是 alt/model_pred 两个版本。

审计证据：

- [服务器原始产物与脚本](targeted_server_audit.json)
- [扩展检索的范围、路径、元数据及代码摘录](server_audit.json)
- [本地与服务器 21 份 summary 的哈希核对](local_server_verification.json)

本次只读取服务器并保存本地核验材料，没有启动实验，也没有改动推荐层或评测数值。
