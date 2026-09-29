# No-Edit Alt Baseline 7 模型评测结果汇总

生成时间：2026-06-13

本文档汇总两个 no-edit baseline 手册中的 `alt` 目标答案评测结果：

- Full E-VQA 来源：`md/Location/no_edit_full_evqa_alt_7models_eval_manual.md`
- MMKE 来源：`md/Location/no_edit_mmke_alt_7models_eval_manual.md`

## 1. Full E-VQA

Source server directory: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/no_edit_full_evqa_alt_7models_g07_fixed_20260612_105148`

Backfill time: `2026-06-12 17:21:07`

| Dataset | Task | Split | Model | Samples | Rel-alt | T-Gen-alt | M-Gen-alt | T-Loc | M-Loc | Average | Status |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Full E-VQA | VQA | full eval/test | blip2-opt-2.7b | 2093 | 15.62 | 9.13 | 15.13 | 100.00 | 100.00 | 47.97 | DONE |
| Full E-VQA | VQA | full eval/test | instructblip-vicuna-7b | 2093 | 3.35 | 1.22 | 2.06 | 100.00 | 100.00 | 41.33 | DONE |
| Full E-VQA | VQA | full eval/test | minigpt-4-vicuna-7b | 2093 | 23.88 | 24.05 | 25.44 | 100.00 | 100.00 | 54.68 | DONE |
| Full E-VQA | VQA | full eval/test | llava-v1.5-7b | 2093 | 32.21 | 30.16 | 28.01 | 100.00 | 100.00 | 58.08 | DONE |
| Full E-VQA | VQA | full eval/test | qwen2.5-vl-3b-instruct | 2093 | 49.91 | 37.43 | 22.23 | 100.00 | 100.00 | 61.91 | DONE |
| Full E-VQA | VQA | full eval/test | paligemma-3b | 2093 | 0.18 | 0.23 | 0.14 | 100.00 | 100.00 | 40.11 | DONE |
| Full E-VQA | VQA | full eval/test | smolvlm-1.7b | 2093 | 31.43 | 29.62 | 22.88 | 100.00 | 100.00 | 56.79 | DONE |

## 2. MMKE

Source server directory: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/no_edit_mmke_alt_eval_7models_20260612_161034`

Split: `eval`

Backfill time: `2026-06-13 01:49:26`

| Dataset | Task | Split | Model | Samples | Rel-alt | T-Gen-alt | M-Gen-alt | T-Loc | M-Loc | Average | Status |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| MMKE | visual | eval | blip2-opt-2.7b | 293 | 38.23 | 37.71 | 38.05 | 100.00 | 100.00 | 62.80 | DONE |
| MMKE | visual | eval | instructblip-vicuna-7b | 293 | 0.04 | 0.04 | 0.04 | 100.00 | 100.00 | 40.02 | DONE |
| MMKE | visual | eval | minigpt-4-vicuna-7b | 293 | 47.21 | 46.58 | 46.99 | 100.00 | 100.00 | 68.15 | DONE |
| MMKE | visual | eval | llava-v1.5-7b | 293 | 47.50 | 47.15 | 47.71 | 100.00 | 100.00 | 68.47 | DONE |
| MMKE | visual | eval | qwen2.5-vl-3b-instruct | 293 | 41.61 | 41.20 | 41.51 | 100.00 | 100.00 | 64.86 | DONE |
| MMKE | visual | eval | paligemma-3b | 293 | 0.09 | 0.09 | 0.09 | 100.00 | 100.00 | 40.05 | DONE |
| MMKE | visual | eval | smolvlm-1.7b | 293 | 40.60 | 40.40 | 40.66 | 100.00 | 100.00 | 64.33 | DONE |
| MMKE | entity | eval | blip2-opt-2.7b | 955 | 50.99 | 50.82 | 50.97 | 100.00 | 100.00 | 70.56 | DONE |
| MMKE | entity | eval | instructblip-vicuna-7b | 955 | 0.20 | 0.20 | 0.20 | 100.00 | 100.00 | 40.12 | DONE |
| MMKE | entity | eval | minigpt-4-vicuna-7b | 955 | 60.69 | 59.93 | 60.71 | 100.00 | 100.00 | 76.27 | DONE |
| MMKE | entity | eval | llava-v1.5-7b | 955 | 59.16 | 58.84 | 59.17 | 100.00 | 100.00 | 75.43 | DONE |
| MMKE | entity | eval | qwen2.5-vl-3b-instruct | 955 | 56.39 | 56.16 | 56.48 | 100.00 | 100.00 | 73.81 | DONE |
| MMKE | entity | eval | paligemma-3b | 955 | 0.56 | 0.55 | 0.55 | 100.00 | 100.00 | 40.33 | DONE |
| MMKE | entity | eval | smolvlm-1.7b | 955 | 53.97 | 53.62 | 54.02 | 100.00 | 100.00 | 72.32 | DONE |

## 3. 合并总表

| Dataset | Task | Split | Model | Samples | Rel-alt | T-Gen-alt | M-Gen-alt | T-Loc | M-Loc | Average | Status |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Full E-VQA | VQA | full eval/test | blip2-opt-2.7b | 2093 | 15.62 | 9.13 | 15.13 | 100.00 | 100.00 | 47.97 | DONE |
| Full E-VQA | VQA | full eval/test | instructblip-vicuna-7b | 2093 | 3.35 | 1.22 | 2.06 | 100.00 | 100.00 | 41.33 | DONE |
| Full E-VQA | VQA | full eval/test | minigpt-4-vicuna-7b | 2093 | 23.88 | 24.05 | 25.44 | 100.00 | 100.00 | 54.68 | DONE |
| Full E-VQA | VQA | full eval/test | llava-v1.5-7b | 2093 | 32.21 | 30.16 | 28.01 | 100.00 | 100.00 | 58.08 | DONE |
| Full E-VQA | VQA | full eval/test | qwen2.5-vl-3b-instruct | 2093 | 49.91 | 37.43 | 22.23 | 100.00 | 100.00 | 61.91 | DONE |
| Full E-VQA | VQA | full eval/test | paligemma-3b | 2093 | 0.18 | 0.23 | 0.14 | 100.00 | 100.00 | 40.11 | DONE |
| Full E-VQA | VQA | full eval/test | smolvlm-1.7b | 2093 | 31.43 | 29.62 | 22.88 | 100.00 | 100.00 | 56.79 | DONE |
| MMKE | visual | eval | blip2-opt-2.7b | 293 | 38.23 | 37.71 | 38.05 | 100.00 | 100.00 | 62.80 | DONE |
| MMKE | visual | eval | instructblip-vicuna-7b | 293 | 0.04 | 0.04 | 0.04 | 100.00 | 100.00 | 40.02 | DONE |
| MMKE | visual | eval | minigpt-4-vicuna-7b | 293 | 47.21 | 46.58 | 46.99 | 100.00 | 100.00 | 68.15 | DONE |
| MMKE | visual | eval | llava-v1.5-7b | 293 | 47.50 | 47.15 | 47.71 | 100.00 | 100.00 | 68.47 | DONE |
| MMKE | visual | eval | qwen2.5-vl-3b-instruct | 293 | 41.61 | 41.20 | 41.51 | 100.00 | 100.00 | 64.86 | DONE |
| MMKE | visual | eval | paligemma-3b | 293 | 0.09 | 0.09 | 0.09 | 100.00 | 100.00 | 40.05 | DONE |
| MMKE | visual | eval | smolvlm-1.7b | 293 | 40.60 | 40.40 | 40.66 | 100.00 | 100.00 | 64.33 | DONE |
| MMKE | entity | eval | blip2-opt-2.7b | 955 | 50.99 | 50.82 | 50.97 | 100.00 | 100.00 | 70.56 | DONE |
| MMKE | entity | eval | instructblip-vicuna-7b | 955 | 0.20 | 0.20 | 0.20 | 100.00 | 100.00 | 40.12 | DONE |
| MMKE | entity | eval | minigpt-4-vicuna-7b | 955 | 60.69 | 59.93 | 60.71 | 100.00 | 100.00 | 76.27 | DONE |
| MMKE | entity | eval | llava-v1.5-7b | 955 | 59.16 | 58.84 | 59.17 | 100.00 | 100.00 | 75.43 | DONE |
| MMKE | entity | eval | qwen2.5-vl-3b-instruct | 955 | 56.39 | 56.16 | 56.48 | 100.00 | 100.00 | 73.81 | DONE |
| MMKE | entity | eval | paligemma-3b | 955 | 0.56 | 0.55 | 0.55 | 100.00 | 100.00 | 40.33 | DONE |
| MMKE | entity | eval | smolvlm-1.7b | 955 | 53.97 | 53.62 | 54.02 | 100.00 | 100.00 | 72.32 | DONE |
