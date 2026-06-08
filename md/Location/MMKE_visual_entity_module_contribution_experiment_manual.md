# MMKE-Bench visual/entity 模块贡献度实验手册

## 1. 实验目标

对 MMKE-Bench 的 `visual` 与 `entity` 两个子任务，计算 7 个 VLM 在文本解码器各层 `attn` 与 `mlp` 对目标 token 的 Module Output Contribution，并生成与 E-VQA pilot500 贡献度实验一致的输出格式。

参考输出格式：

`downloads/evqa_module_contribution/evqa_pilot500_module_contribution_model_pred_20260606_193500`

本实验不使用 `vlm-attribution-localization` 框架；只沿用 VisEdit-style Module Output Attribution 的计算方式。

## 2. 数据位置

服务器数据根目录：

`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench`

已下载并验证的文件：

- `data_json/entity_train.json`
- `data_json/entity_eval.json`
- `data_json/visual_train.json`
- `data_json/visual_eval.json`
- `data_image/entity/`
- `data_image/visual/`

本轮贡献度分析默认使用 train split：

- entity: `data_json/entity_train.json`，636 条
- visual: `data_json/visual_train.json`，214 条

若后续需要 eval split，只替换 `--data-path` 即可。

## 3. 字段映射

每条 MMKE 样本转换成贡献度脚本内部的 request：

| 内部字段 | MMKE 字段 | 含义 |
|---|---|---|
| `request.prompt` | `src` | 主问题 |
| `request.image` | `image` | 主图 |
| `request.target_new` | `alt` | 新知识目标答案 |
| old target | `pred` | 旧知识/原答案 |

prompt 后缀沿用 E-VQA 的贡献度实验格式：

`{src} The answer is:`

图片路径规则：

- JSON 中如 `entity/xxx.jpg` 或 `visual/xxx.jpg`，相对 `data_image/` 解析。
- visual 子任务有多级目录，例如 `visual/handball/xxx.jpg`。
- `image_rephrase`、`one_hop_img` 只用于数据完整性验证，不参与本轮主请求贡献度计算。

## 4. Target Mode

本轮做两套目标 token 贡献度：

| mode | 目标 token | 用途 |
|---|---|---|
| `alt` | `alt` 字段首 token | 新知识目标贡献度 |
| `pred` | `pred` 字段首 token | 旧知识/原答案贡献度 |

与 pilot500 一致，默认只追踪目标答案的第一个 tokenizer token，并启用 leading space。

如需模型自己输出 token，另开 `model_pred` mode；本轮用户要求是 `alt` 与 `pred`。

## 5. 实验模型

7 个模型：

1. `blip2-opt-2.7b`
2. `instructblip-vicuna-7b`
3. `minigpt-4-vicuna-7b`
4. `llava-v1.5-7b`
5. `qwen2.5-vl-3b`
6. `paligemma-3b`
7. `smolvlm-1.7b`

BLIP2 使用单独脚本入口；其余 6 个模型使用 multi 脚本入口。

## 6. 贡献度计算公式

对每个样本、每层、每个模块 `attn/mlp`：

1. hook 模块输出 hidden state；
2. 通过模型最终 norm + lm head 投影到词表；
3. 对目标 token 记录：
   - `p`: softmax probability
   - `v`: vocab logit
4. 对每个样本按层内最大幅值归一化：

`M = max(max(abs(v_attn)), max(abs(v_mlp)), eps)`

5. 模块贡献度：

`contribution = sign(v / M) * sqrt(abs(v / M)) * sqrt(max(p, 0))`

数值防护：

- 若某个样本/层的 `p` 或 `v` 出现 `NaN/Inf`，该位置贡献度按 0 处理。
- `M` 只由有限的 `attn/mlp` logit 幅值计算。
- 原始 `p/v` 仍保存在 `contribution_raw.npz` 中，便于之后检查数值异常样本。

6. 跨样本平均得到：

- `attn_mean`
- `mlp_mean`

排序指标：

- `score_positive = max(0, attn_mean) + max(0, mlp_mean)`
- `score_signed = attn_mean + mlp_mean`
- `score_abs = abs(attn_mean) + abs(mlp_mean)`

默认主排序使用 `score_positive`。

## 7. 输出目录规范

服务器输出根目录：

`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_module_contribution_YYYYMMDD_HHMMSS`

本地拉回目录：

`downloads/mmke_module_contribution/mmke_module_contribution_YYYYMMDD_HHMMSS`

建议目录结构：

```text
mmke_module_contribution_YYYYMMDD_HHMMSS/
  entity/
    alt/
      blip2-opt-2.7b/
      instructblip-vicuna-7b/
      ...
      all7_module_contribution_bar_positive.svg
      all7_module_contribution_summary.csv
    pred/
      ...
  visual/
    alt/
      ...
    pred/
      ...
```

每个模型目录必须包含：

- `config.json`
- `summary.json`
- `contribution_layer.csv`
- `contribution_rank.csv`
- `contribution_sample_layer.csv`
- `contribution_raw.npz`
- `module_contribution_bar.{png,pdf,svg}`
- `module_contribution_bar_positive.{png,pdf,svg}`

每个子任务/mode 目录必须包含：

- `all7_module_contribution_summary.csv`
- `all7_module_contribution_bar.{png,pdf,svg}`
- `all7_module_contribution_bar_positive.{png,pdf,svg}`

## 8. 运行策略

使用服务器 g08 上已有 Slurm job，避免影响 g07 训练。

检查命令：

```bash
squeue -u ph_teacher3
```

运行方式：

```bash
srun --jobid=2906639 --overlap python scripts/<script>.py ...
```

每次只跑一个模型，顺序跑，避免显存互相污染。

## 9. 验证标准

每个模型结果验证：

- `summary.json.sample_count` 等于对应 train split 样本数。
- `summary.json.key_mode` 等于 `alt` 或 `pred`。
- `contribution_layer.csv` 行数 = 文本解码器层数 + 1 表头。
- `module_contribution_bar_positive.png/svg` 文件非空。

每个子任务/mode 的 all7 汇总验证：

- 7 个模型都出现在 `all7_module_contribution_summary.csv`。
- 合并图标题包含正确 target mode。
- 合并图可正常打开，且每行对应一个模型。

## 10. 本轮计划

运行 4 组实验：

1. `entity / alt`
2. `entity / pred`
3. `visual / alt`
4. `visual / pred`

每组包含 7 个模型，共 28 个模型任务。
