# No-Edit Full E-VQA Alt Baseline 7 模型评测手册

## 1. 实验目的

本实验用于回答：

1. 原始未编辑 VLM 在 full E-VQA eval/test 上本来有多少比例会输出 `alt`。
2. 已完成的 adapter 编辑结果是否真的超过 no-edit baseline。
3. InstructBLIP `L28/L27/L26` 编辑后 Rel/T-Gen/M-Gen 约 29% 的结果，是弱提升、无提升，还是低于原始模型。

该实验只做评测，不训练、不加载 adapter、不修改模型参数。

## 2. 评测对象

| 序号 | 模型 | model_name |
|---:|---|---|
| 1 | BLIP2-OPT-2.7B | `blip2-opt-2.7b` |
| 2 | InstructBLIP-Vicuna-7B | `instructblip-vicuna-7b` |
| 3 | MiniGPT-4-Vicuna-7B | `minigpt-4-vicuna-7b` |
| 4 | LLaVA-v1.5-7B | `llava-v1.5-7b` |
| 5 | Qwen2.5-VL-3B | `qwen2.5-vl-3b` |
| 6 | PaliGemma-3B | `paligemma-3b` |
| 7 | SmolVLM-Instruct-1.7B | `smolvlm-1.7b` |

## 3. 数据与目标答案

| 项目 | 路径 / 规则 |
|---|---|
| full E-VQA eval JSON | `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/vqa/vqa_eval.json` |
| full E-VQA image root | `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images` |
| 样本数 | `2093` |
| Reliability 目标 | `request.target_new = alt` |
| Text generality 目标 | `generality.text_rephrase[*].target = alt` |
| Modal generality 目标 | `generality.image_rephrase[*].target = alt` |
| Text locality | no-edit 前后同一 base model 输出一致性 |
| Image locality | no-edit 前后同一 base model 输出一致性 |

注意：这里的 `Rel/T-Gen/M-Gen` 不是“原始模型答对旧知识”的能力，而是“原始模型未编辑时是否已经答到新知识 alt”。

## 4. 指标定义

| 指标 | 计算方式 | 解释 |
|---|---|---|
| Rel | `src + image -> alt` token accuracy | 未编辑模型直接输出新知识的比例 |
| T-Gen | `rephrase + image -> alt` token accuracy | 未编辑模型在文本改写问题上输出新知识的比例 |
| M-Gen | `src + image_rephrase -> alt` token accuracy | 未编辑模型在换图问题上输出新知识的比例 |
| T-Loc | no-edit 前后 text locality 输出一致性 | sanity check，理论上接近 100 |
| M-Loc | no-edit 前后 image locality 输出一致性 | sanity check，理论上接近 100 |
| Average | 五项均值 | 只用于和现有表格格式对齐；no-edit 的 Average 会被 locality 拉高 |

解释编辑提升时，应优先看 `Rel/T-Gen/M-Gen`，不要把 no-edit 的 `Average` 当作编辑性能。

## 5. 输出目录

服务器输出：

`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/no_edit_full_evqa_alt_7models_YYYYMMDD_HHMMSS`

每个模型输出：

```text
MODEL/
  no_edit_results.json
  no_edit_mean_results.json
  no_edit_metrics.json
  no_edit_eval.log
```

总表输出：

```text
no_edit_full_evqa_alt_7models_metrics.csv
no_edit_full_evqa_alt_7models_metrics.md
run_status.log
```

## 6. 运行策略

1. 优先使用 G08，不打断 G07 训练。
2. 按模型串行运行，避免多个 7B VLM 同时占用显存。
3. Qwen2.5-VL-3B 使用独立环境：
   `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/envs/qwen25vl/bin/python`
4. 其他模型使用现有 jupyter 环境：
   `/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python`
5. 如果某个模型失败，记录 `FAILED`，继续下一个模型。

## 7. 服务器脚本

计划新增：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/scripts/eval_evqa_no_edit_full_alt_7models.py
```

脚本逻辑：

1. `load_vllm_for_edit(model_name, device)` 加载原始模型。
2. `EVQA(eval_json, eval_img_root)` 加载 full E-VQA eval/test。
3. 不创建 `VEAD`，不注册 adapter hook，不加载 checkpoint。
4. 对每个样本直接 forward：
   - request prompt/image 对 `target_new=alt` 算 token accuracy。
   - text_rephrase 对 `target=alt` 算 token accuracy。
   - image_rephrase 对 `target=alt` 算 token accuracy。
   - locality 先记录 base prediction，再用同一 base model 重算一次，检查输出一致性。
5. 写出 per-sample JSON、mean JSON、metrics CSV/MD。

## 8. 结果回填

跑完后需要把总表追加到：

`md/Location/6location_7model_3datas_top_3_5_layers_outcome.md`

建议回填表：

| Model | Eval samples | Rel-alt | T-Gen-alt | M-Gen-alt | T-Loc | M-Loc | Average | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| BLIP2-OPT-2.7B | 2093 | - | - | - | - | - | - | pending |
| InstructBLIP-Vicuna-7B | 2093 | - | - | - | - | - | - | pending |
| MiniGPT-4-Vicuna-7B | 2093 | - | - | - | - | - | - | pending |
| LLaVA-v1.5-7B | 2093 | - | - | - | - | - | - | pending |
| Qwen2.5-VL-3B | 2093 | - | - | - | - | - | - | pending |
| PaliGemma-3B | 2093 | - | - | - | - | - | - | pending |
| SmolVLM-Instruct-1.7B | 2093 | - | - | - | - | - | - | pending |

## 9. 判读规则

以 InstructBLIP 为例：

| 情况 | 解释 |
|---|---|
| no-edit Rel-alt 远低于 29% | L28/L27/L26 视觉 adapter 有提升，但提升弱 |
| no-edit Rel-alt 接近 29% | 视觉 adapter 基本没有把新知识写进去 |
| no-edit Rel-alt 高于 29% | 编辑可能损害了原本会输出 alt 的行为，需要检查训练目标或 adapter 位置 |

同理，对 7 个模型都需要比较 `no-edit alt baseline` 与真实扫层后的 `Rel/T-Gen/M-Gen`。

<!-- NO_EDIT_EVQA_RESULTS_START -->
## Results Backfill

Source server directory: /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/no_edit_full_evqa_alt_7models_g07_fixed_20260612_105148

Backfill time: 2026-06-12 17:21:07

| Model | Eval samples | Rel-alt | T-Gen-alt | M-Gen-alt | T-Loc | M-Loc | Average | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| blip2-opt-2.7b | 2093 | 15.62 | 9.13 | 15.13 | 100.00 | 100.00 | 47.97 | DONE |
| instructblip-vicuna-7b | 2093 | 3.35 | 1.22 | 2.06 | 100.00 | 100.00 | 41.33 | DONE |
| minigpt-4-vicuna-7b | 2093 | 23.88 | 24.05 | 25.44 | 100.00 | 100.00 | 54.68 | DONE |
| llava-v1.5-7b | 2093 | 32.21 | 30.16 | 28.01 | 100.00 | 100.00 | 58.08 | DONE |
| qwen2.5-vl-3b-instruct | 2093 | 49.91 | 37.43 | 22.23 | 100.00 | 100.00 | 61.91 | DONE |
| paligemma-3b | 2093 | 0.18 | 0.23 | 0.14 | 100.00 | 100.00 | 40.11 | DONE |
| smolvlm-1.7b | 2093 | 31.43 | 29.62 | 22.88 | 100.00 | 100.00 | 56.79 | DONE |
<!-- NO_EDIT_EVQA_RESULTS_END -->

<!-- NO_EDIT_EVQA_RESULTS_START -->
## Results Backfill

Source server directory: /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/no_edit_full_evqa_alt_7models_g07_fixed_20260612_105148

Backfill time: 2026-06-13 01:46:42

| Model | Eval samples | Rel-alt | T-Gen-alt | M-Gen-alt | T-Loc | M-Loc | Average | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| blip2-opt-2.7b | 2093 | 15.62 | 9.13 | 15.13 | 100.00 | 100.00 | 47.97 | DONE |
| instructblip-vicuna-7b | 2093 | 3.35 | 1.22 | 2.06 | 100.00 | 100.00 | 41.33 | DONE |
| minigpt-4-vicuna-7b | 2093 | 23.88 | 24.05 | 25.44 | 100.00 | 100.00 | 54.68 | DONE |
| llava-v1.5-7b | 2093 | 32.21 | 30.16 | 28.01 | 100.00 | 100.00 | 58.08 | DONE |
| qwen2.5-vl-3b-instruct | 2093 | 49.91 | 37.43 | 22.23 | 100.00 | 100.00 | 61.91 | DONE |
| paligemma-3b | 2093 | 0.18 | 0.23 | 0.14 | 100.00 | 100.00 | 40.11 | DONE |
| smolvlm-1.7b | 2093 | 31.43 | 29.62 | 22.88 | 100.00 | 100.00 | 56.79 | DONE |
<!-- NO_EDIT_EVQA_RESULTS_END -->
