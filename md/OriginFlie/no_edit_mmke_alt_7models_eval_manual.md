# No-Edit MMKE Alt Baseline 7 模型评测手册

## 1. 实验目的

本实验用于评估原始未编辑 VLM 在 MMKE-Bench `visual` / `entity` 子任务上，是否本来就会输出新知识目标 `alt`。

实验只做 no-edit forward 评测：

- 不训练 adapter
- 不加载 adapter checkpoint
- 不修改模型参数
- 目标答案固定按 `alt` 字段计算

## 2. 数据与 split

服务器数据根目录：

`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench`

本轮 no-edit baseline 默认使用 `eval` split。原因是该实验用于衡量原始模型在验证/评测集上的未编辑输出，后续应和真实编辑评测结果对齐，而不是和候选层贡献度统计 split 对齐。

| Task | JSON | 样本数 |
|---|---|---:|
| MMKE-visual | `data_json/visual_eval.json` | 293 |
| MMKE-entity | `data_json/entity_eval.json` | 955 |

`train` split 只用于和前面贡献度 / 候选层统计对齐时的补充分析，本轮不作为主结果：

| Task | JSON | 样本数 |
|---|---|---:|
| MMKE-visual | `data_json/visual_train.json` | 214 |
| MMKE-entity | `data_json/entity_train.json` | 636 |

## 3. 字段映射

| 指标 | Prompt / Image | Target | 含义 |
|---|---|---|---|
| Rel-alt | `src` + `image` | `alt` | 原始模型是否直接输出新知识 |
| T-Gen-alt | `rephrase` + `image` | `alt` | 文本改写后是否输出新知识 |
| M-Gen-alt | `src` + `image_rephrase` | `alt` | 换图后是否输出新知识 |
| T-Loc | `loc` | no-edit 前后同一 base 输出一致性 | sanity check |
| M-Loc | `m_loc_q` + `m_loc` | no-edit 前后同一 base 输出一致性 | sanity check |
| Average | 五项均值 | - | 只用于表格对齐 |

Prompt 后缀统一为：

`{question} The answer is:`

## 4. 实验模型

| 序号 | model_name |
|---:|---|
| 1 | `blip2-opt-2.7b` |
| 2 | `instructblip-vicuna-7b` |
| 3 | `minigpt-4-vicuna-7b` |
| 4 | `llava-v1.5-7b` |
| 5 | `qwen2.5-vl-3b-instruct` |
| 6 | `paligemma-3b` |
| 7 | `smolvlm-1.7b` |

## 5. 服务器脚本

已上传：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/scripts/eval_mmke_no_edit_alt_7models.py
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/scripts/launch_no_edit_mmke_alt_7models_g07.sh
```

## 6. 当前运行

当前 G07/G08 没有完全空卡：

- G07 GPU1 正在跑 `No-Edit Full E-VQA Alt` 的 LLaVA 补跑。
- G07 GPU0 被其他训练占用约 41GB。
- G08 两张卡都有活跃任务。

因此 MMKE no-edit 已作为等待型任务挂在 G07 GPU1，不抢当前任务。它会等物理 GPU1 显存低于 10GB 后串行启动。

服务器输出目录：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/no_edit_mmke_alt_eval_7models_YYYYMMDD_HHMMSS
```

注意：`no_edit_mmke_alt_7models_20260612_154457` 是误用 `train` split 且等待逻辑误判后的废弃 run，不作为结果使用。

当前正确 run 状态日志以 `no_edit_mmke_alt_eval_7models_*` 目录为准。

```text
NO_EDIT_MMKE_START ... split=eval
```

## 7. 输出格式

每个模型输出：

```text
TASK/alt/MODEL/
  no_edit_eval.log
  no_edit_results.json
  no_edit_metrics.json
  run_config.json
```

总表输出：

```text
no_edit_mmke_alt_7models_metrics.csv
no_edit_mmke_alt_7models_metrics.md
run_status.log
```

<!-- NO_EDIT_MMKE_RESULTS_START -->
## Results Backfill

Source server directory: /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/no_edit_mmke_alt_eval_7models_20260612_161034

Split: eval. Backfill time: 2026-06-13 01:49:26

| Task | Split | Model | Samples | Rel-alt | T-Gen-alt | M-Gen-alt | T-Loc | M-Loc | Average | Status |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| visual | eval | blip2-opt-2.7b | 293 | 38.23 | 37.71 | 38.05 | 100.00 | 100.00 | 62.80 | DONE |
| visual | eval | instructblip-vicuna-7b | 293 | 0.04 | 0.04 | 0.04 | 100.00 | 100.00 | 40.02 | DONE |
| visual | eval | minigpt-4-vicuna-7b | 293 | 47.21 | 46.58 | 46.99 | 100.00 | 100.00 | 68.15 | DONE |
| visual | eval | llava-v1.5-7b | 293 | 47.50 | 47.15 | 47.71 | 100.00 | 100.00 | 68.47 | DONE |
| visual | eval | qwen2.5-vl-3b-instruct | 293 | 41.61 | 41.20 | 41.51 | 100.00 | 100.00 | 64.86 | DONE |
| visual | eval | paligemma-3b | 293 | 0.09 | 0.09 | 0.09 | 100.00 | 100.00 | 40.05 | DONE |
| visual | eval | smolvlm-1.7b | 293 | 40.60 | 40.40 | 40.66 | 100.00 | 100.00 | 64.33 | DONE |
| entity | eval | blip2-opt-2.7b | 955 | 50.99 | 50.82 | 50.97 | 100.00 | 100.00 | 70.56 | DONE |
| entity | eval | instructblip-vicuna-7b | 955 | 0.20 | 0.20 | 0.20 | 100.00 | 100.00 | 40.12 | DONE |
| entity | eval | minigpt-4-vicuna-7b | 955 | 60.69 | 59.93 | 60.71 | 100.00 | 100.00 | 76.27 | DONE |
| entity | eval | llava-v1.5-7b | 955 | 59.16 | 58.84 | 59.17 | 100.00 | 100.00 | 75.43 | DONE |
| entity | eval | qwen2.5-vl-3b-instruct | 955 | 56.39 | 56.16 | 56.48 | 100.00 | 100.00 | 73.81 | DONE |
| entity | eval | paligemma-3b | 955 | 0.56 | 0.55 | 0.55 | 100.00 | 100.00 | 40.33 | DONE |
| entity | eval | smolvlm-1.7b | 955 | 53.97 | 53.62 | 54.02 | 100.00 | 100.00 | 72.32 | DONE |
<!-- NO_EDIT_MMKE_RESULTS_END -->
