# 第一阶段真实评测数据与 Ours-Direct 推荐层

> 生成日期：2026-09-15（Asia/Shanghai）  
> 来源：`md/Location/6location_7model_3datas_top_3_5_layers_outcome.md`；第4节漏行补证：`outputs/firstphase_oursdirect_verified_eval_supplement_20260915.csv`  
> 来源文件 SHA-256：`a28f5f58314939f2428da44fceebf5f965a5ed94ab31a184c06f28311dab961c`

## 1. 口径与使用规则

- Ours-Direct正式主公式固定为 `M_abscos_x_newn = abs(S_v_cos) * S_v_new_norm`，不含深度权重。
- `Top-1`是公式分数排名第一的预测层；`Top-3`是前三个预测层，顺序即公式排名。
- 第二阶段没有独立validation时，主实验直接使用Ours预测Top-1；有预先划分且与test/eval隔离的validation时，才允许在Top-3内选层。
- 本文件展示的真实评测值只能用于第一阶段方法分析与证据核验，禁止依据test/eval中Average最高的层反向选择第二阶段主实验层，否则会产生测试集泄漏。
- 真实结果继承原手册第4节验收口径：只有完成训练、选出minimum-EMA checkpoint并完成独立test/eval的层才进入明细。
- `stable`结果与`main`不是同一配置；stable-only只能作为已有证据展示，不能直接并入主配置公平比较。
- 原手册第3.4.6节把EVQA×InstructBLIP L0/L1/L11、EVQA×MiniGPT-4 L19、MMKE-entity×MiniGPT-4 L26/L27及MMKE-visual×LLaVA L3登记为完成，但第4节漏了详细行；逐层服务器审计又查出另外34条第4节漏行。本文件从共享盘逐层`eval_full.done`、`selected_checkpoint.tsv`、实体checkpoint和`results.json`补录指标，证据路径保存在补证CSV；源手册不在本次操作中修改。
- EVQA×InstructBLIP L14/L15/L16/L19虽完成2093条独立eval，但共享盘`loss_history.csv`和`train.done`分别只记录到Epoch 40/38/37/41，属于`main/recovered-early`，不可冒充训练满50 epoch的常规主配置结果；在严格50-epoch公平比较中应单独分栏或待后续续训。
- MMKE-visual×LLaVA L3的评测输出目录沿用`EVQA_full_test_pilot500`旧命名；评测日志实际加载`vqa_mmke_visual_eval_evqa_compat.json`，`results.json`的293条可靠性图像全部来自MMKE-Bench visual，不能按目录名误判为EVQA评测。

## 2. 21组 Ours-Direct Top-1 / Top-3 与推荐层

| 数据集 | 模型 | Ours Top-1 | Ours Top-3（有序） | Top-1真实评测 | Top-3已有评测 | 主配置可比 | 第二阶段推荐层 |
|---|---|---:|---|---|---:|---:|---:|
| EVQA-pilot500 | BLIP2-OPT-2.7B | **L0** | L0,L1,L2 | Average 58.16（main/legacy） | 3/3 | 3/3 | **L0** |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | **L1** | L1,L0,L11 | Average 54.470（main） | 3/3 | 3/3 | **L1** |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | **L18** | L18,L19,L16 | Average 59.56（main/legacy） | 3/3 | 3/3 | **L18** |
| EVQA-pilot500 | LLaVA-v1.5-7B | **L0** | L0,L1,L2 | 待完成 | 0/3 | 0/3 | **L0** |
| EVQA-pilot500 | Qwen2.5-VL-3B | **L21** | L21,L19,L17 | Average 63.74（main/legacy） | 3/3 | 3/3 | **L21** |
| EVQA-pilot500 | PaliGemma-3B | **L5** | L5,L4,L3 | Average 78.17（main） | 3/3 | 3/3 | **L5** |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | **L0** | L0,L1,L2 | Average 69.97（main/legacy） | 3/3 | 3/3 | **L0** |
| MMKE-visual | BLIP2-OPT-2.7B | **L0** | L0,L1,L2 | Average 62.37（main/legacy） | 3/3 | 3/3 | **L0** |
| MMKE-visual | InstructBLIP-Vicuna-7B | **L1** | L1,L0,L3 | Average 70.28（main/legacy） | 3/3 | 3/3 | **L1** |
| MMKE-visual | MiniGPT-4-Vicuna-7B | **L9** | L9,L10,L11 | Average 76.582（main/legacy） | 3/3 | 3/3 | **L9** |
| MMKE-visual | LLaVA-v1.5-7B | **L0** | L0,L3,L1 | Average 75.158（main/legacy） | 3/3 | 3/3 | **L0** |
| MMKE-visual | Qwen2.5-VL-3B | **L0** | L0,L1,L2 | Average 70.42（main/legacy） | 3/3 | 3/3 | **L0** |
| MMKE-visual | PaliGemma-3B | **L5** | L5,L4,L3 | Average 98.58（stable） | 3/3 | 1/3 | **L5** |
| MMKE-visual | SmolVLM-Instruct-1.7B | **L0** | L0,L1,L2 | Average 71.36（main/legacy） | 3/3 | 3/3 | **L0** |
| MMKE-entity | BLIP2-OPT-2.7B | **L0** | L0,L1,L2 | Average 65.86（main/legacy） | 3/3 | 3/3 | **L0** |
| MMKE-entity | InstructBLIP-Vicuna-7B | **L1** | L1,L0,L3 | Average 69.18（main/legacy） | 3/3 | 3/3 | **L1** |
| MMKE-entity | MiniGPT-4-Vicuna-7B | **L27** | L27,L28,L26 | Average 75.824（main） | 3/3 | 3/3 | **L27** |
| MMKE-entity | LLaVA-v1.5-7B | **L13** | L13,L11,L12 | 待完成 | 0/3 | 0/3 | **L13** |
| MMKE-entity | Qwen2.5-VL-3B | **L0** | L0,L1,L2 | Average 72.22（main/legacy） | 3/3 | 3/3 | **L0** |
| MMKE-entity | PaliGemma-3B | **L5** | L5,L4,L3 | Average 90.81（main） | 3/3 | 3/3 | **L5** |
| MMKE-entity | SmolVLM-Instruct-1.7B | **L0** | L0,L1,L2 | Average 70.47（main/legacy） | 3/3 | 3/3 | **L0** |

**当前Top-3证据覆盖：** 19/21组的Ours前三层均已有正式评测；严格不混用stable-only时，主配置可比为18/21组。缺失层及stable-only层分别见第5.1、5.2节。

### 2.1 第二阶段直接配置表

下表可直接转成第二阶段配置；`recommended_layer`严格等于Ours预测Top-1，而不是Top-3中测试分数最高层。

| dataset | model | recommended_layer | fallback_top3 | selection_policy |
|---|---|---:|---|---|
| EVQA-pilot500 | BLIP2-OPT-2.7B | L0 | L0,L1,L2 | Top-1 direct；仅独立validation可在Top-3内选择 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | L1 | L1,L0,L11 | Top-1 direct；仅独立validation可在Top-3内选择 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | L18 | L18,L19,L16 | Top-1 direct；仅独立validation可在Top-3内选择 |
| EVQA-pilot500 | LLaVA-v1.5-7B | L0 | L0,L1,L2 | Top-1 direct；仅独立validation可在Top-3内选择 |
| EVQA-pilot500 | Qwen2.5-VL-3B | L21 | L21,L19,L17 | Top-1 direct；仅独立validation可在Top-3内选择 |
| EVQA-pilot500 | PaliGemma-3B | L5 | L5,L4,L3 | Top-1 direct；仅独立validation可在Top-3内选择 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | L0 | L0,L1,L2 | Top-1 direct；仅独立validation可在Top-3内选择 |
| MMKE-visual | BLIP2-OPT-2.7B | L0 | L0,L1,L2 | Top-1 direct；仅独立validation可在Top-3内选择 |
| MMKE-visual | InstructBLIP-Vicuna-7B | L1 | L1,L0,L3 | Top-1 direct；仅独立validation可在Top-3内选择 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | L9 | L9,L10,L11 | Top-1 direct；仅独立validation可在Top-3内选择 |
| MMKE-visual | LLaVA-v1.5-7B | L0 | L0,L3,L1 | Top-1 direct；仅独立validation可在Top-3内选择 |
| MMKE-visual | Qwen2.5-VL-3B | L0 | L0,L1,L2 | Top-1 direct；仅独立validation可在Top-3内选择 |
| MMKE-visual | PaliGemma-3B | L5 | L5,L4,L3 | Top-1 direct；仅独立validation可在Top-3内选择 |
| MMKE-visual | SmolVLM-Instruct-1.7B | L0 | L0,L1,L2 | Top-1 direct；仅独立validation可在Top-3内选择 |
| MMKE-entity | BLIP2-OPT-2.7B | L0 | L0,L1,L2 | Top-1 direct；仅独立validation可在Top-3内选择 |
| MMKE-entity | InstructBLIP-Vicuna-7B | L1 | L1,L0,L3 | Top-1 direct；仅独立validation可在Top-3内选择 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | L27 | L27,L28,L26 | Top-1 direct；仅独立validation可在Top-3内选择 |
| MMKE-entity | LLaVA-v1.5-7B | L13 | L13,L11,L12 | Top-1 direct；仅独立validation可在Top-3内选择 |
| MMKE-entity | Qwen2.5-VL-3B | L0 | L0,L1,L2 | Top-1 direct；仅独立validation可在Top-3内选择 |
| MMKE-entity | PaliGemma-3B | L5 | L5,L4,L3 | Top-1 direct；仅独立validation可在Top-3内选择 |
| MMKE-entity | SmolVLM-Instruct-1.7B | L0 | L0,L1,L2 | Top-1 direct；仅独立validation可在Top-3内选择 |

## 3. Ours Top-3候选层的真实训练与评测证据

指标为原手册及服务器补证登记的百分制结果：`Rel`（Reliability）、`T-Gen`/`M-Gen`（文本/多模态Generality）、`T-Loc`/`M-Loc`（文本/多模态Locality），`Average`为五项平均。`—`表示尚无完成评测，不能填0。

### 3.1 EVQA-pilot500

#### BLIP2-OPT-2.7B

- Ours Top-1 / 第二阶段直接推荐：`L0`
- Ours Top-3：`L0,L1,L2`

| 排名 | 层 | 配置 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 状态 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | L0 | main/legacy | 43 | 0.375991 | 0.368115 | 2093 | 44.15 | 40.43 | 40.29 | 100.00 | 65.95 | 58.16 | TRAIN_DONE |
| 2 | L1 | main/legacy | 45 | 0.521112 | 0.425138 | 2093 | 46.63 | 42.52 | 44.03 | 100.00 | 59.35 | 58.506 | TRAIN_DONE |
| 3 | L2 | main/legacy | 49 | 0.347236 | 0.417455 | 2093 | 32.99 | 28.69 | 30.45 | 100.00 | 58.51 | 50.128 | TRAIN_DONE |

#### InstructBLIP-Vicuna-7B

- Ours Top-1 / 第二阶段直接推荐：`L1`
- Ours Top-3：`L1,L0,L11`

| 排名 | 层 | 配置 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 状态 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | L1 | main | 43 | 0.711665 | 0.678210 | 2093 | 42.00 | 40.44 | 37.89 | 100.00 | 52.02 | 54.470 | TRAIN_DONE_MAIN_EVAL_DONE_JOB3150065 |
| 2 | L0 | main | 49 | 0.599338 | 0.568572 | 2093 | 37.99 | 36.92 | 33.84 | 100.00 | 52.52 | 52.254 | TRAIN_DONE_MAIN_RECOVERED_EVAL_DONE_JOB3150065 |
| 3 | L11 | main | 46 | 1.284068 | 1.214271 | 2093 | 28.72 | 28.18 | 27.18 | 100.00 | 62.10 | 49.236 | TRAIN_DONE_MAIN_EVAL_DONE_JOB3150065 |

#### MiniGPT-4-Vicuna-7B

- Ours Top-1 / 第二阶段直接推荐：`L18`
- Ours Top-3：`L18,L19,L16`

| 排名 | 层 | 配置 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 状态 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | L18 | main/legacy | 44 | 0.305323 | 0.302507 | 2093 | 40.16 | 37.37 | 38.18 | 100.00 | 82.09 | 59.56 | TRAIN_DONE |
| 2 | L19 | main | 49 | 0.293260 | 0.293898 | 2093 | 38.47 | 36.52 | 37.19 | 100.00 | 79.71 | 58.378 | TRAIN_DONE_MAIN_EVAL_DONE_JOB3126082 |
| 3 | L16 | main/legacy | 50 | 0.314161 | 0.297508 | 2093 | 49.34 | 46.11 | 46.47 | 100.00 | 82.77 | 64.94 | TRAIN_DONE |

#### LLaVA-v1.5-7B

- Ours Top-1 / 第二阶段直接推荐：`L0`
- Ours Top-3：`L0,L1,L2`

| 排名 | 层 | 配置 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 状态 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | L0 | — | — | — | — | — | — | — | — | — | — | — | **待完成正式评测** |
| 2 | L1 | — | — | — | — | — | — | — | — | — | — | — | **待完成正式评测** |
| 3 | L2 | — | — | — | — | — | — | — | — | — | — | — | **待完成正式评测** |

#### Qwen2.5-VL-3B

- Ours Top-1 / 第二阶段直接推荐：`L21`
- Ours Top-3：`L21,L19,L17`

| 排名 | 层 | 配置 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 状态 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | L21 | main/legacy | 49 | 0.444941 | 0.365603 | 2093 | 53.83 | 43.82 | 36.61 | 100.00 | 84.45 | 63.74 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| 2 | L19 | main/legacy | 41 | 0.417306 | 0.385106 | 2093 | 53.54 | 43.09 | 35.50 | 100.00 | 83.90 | 63.21 | TRAIN_DONE |
| 3 | L17 | main/legacy | 45 | 0.369272 | 0.384334 | 2093 | 53.21 | 42.57 | 34.62 | 100.00 | 82.62 | 62.60 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |

#### PaliGemma-3B

- Ours Top-1 / 第二阶段直接推荐：`L5`
- Ours Top-3：`L5,L4,L3`

| 排名 | 层 | 配置 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 状态 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | L5 | main | 2 | 2.871534 | 4.631819 | 2093 | 85.30 | 83.96 | 86.80 | 100.00 | 34.78 | 78.17 | TRAIN_DONE_MAIN_JOB3044208 |
| 2 | L4 | main | 38 | 7.798694 | 6.942612 | 2093 | 74.08 | 76.08 | 74.69 | 100.00 | 30.78 | 71.13 | TRAIN_DONE_MAIN_JOB3044208 |
| 3 | L3 | main | 38 | 0.605178 | 0.531071 | 2093 | 85.63 | 85.86 | 89.21 | 100.00 | 67.90 | 85.720 | TRAIN_DONE_MAIN_FORMAL_TOP3_JOB3117562 |

#### SmolVLM-Instruct-1.7B

- Ours Top-1 / 第二阶段直接推荐：`L0`
- Ours Top-3：`L0,L1,L2`

| 排名 | 层 | 配置 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 状态 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | L0 | main/legacy | 50 | 0.445026 | 0.452992 | 2093 | 64.02 | 59.53 | 57.19 | 100.00 | 69.10 | 69.97 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| 2 | L1 | main/legacy | 47 | 0.449670 | 0.456147 | 2093 | 46.20 | 40.21 | 35.59 | 100.00 | 71.86 | 58.77 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| 3 | L2 | main/legacy | 48 | 0.429149 | 0.437729 | 2093 | 55.62 | 51.14 | 47.70 | 100.00 | 67.59 | 64.41 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |


### 3.2 MMKE-visual

#### BLIP2-OPT-2.7B

- Ours Top-1 / 第二阶段直接推荐：`L0`
- Ours Top-3：`L0,L1,L2`

| 排名 | 层 | 配置 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 状态 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | L0 | main/legacy | 50 | 1.835244 | 2.004923 | 293 | 53.13 | 53.14 | 53.20 | 100.00 | 52.38 | 62.37 | TRAIN_DONE |
| 2 | L1 | main/legacy | 50 | 0.516416 | 0.520349 | 293 | 52.09 | 51.80 | 51.97 | 100.00 | 92.60 | 69.69 | TRAIN_DONE |
| 3 | L2 | main/legacy | 44 | 0.813470 | 1.107170 | 293 | 52.04 | 51.91 | 51.58 | 100.00 | 93.80 | 69.87 | TRAIN_DONE |

#### InstructBLIP-Vicuna-7B

- Ours Top-1 / 第二阶段直接推荐：`L1`
- Ours Top-3：`L1,L0,L3`

| 排名 | 层 | 配置 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 状态 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | L1 | main/legacy | 50 | 0.231107 | 0.292772 | 293 | 51.70 | 51.67 | 51.55 | 100.00 | 96.48 | 70.28 | TRAIN_DONE |
| 2 | L0 | main/legacy | 50 | 0.171615 | 0.222510 | 293 | 52.26 | 52.42 | 52.17 | 100.00 | 99.62 | 71.29 | TRAIN_DONE |
| 3 | L3 | main/legacy | 47 | 5.070473 | 6.227147 | 293 | 19.40 | 17.34 | 19.20 | 100.00 | 99.85 | 51.16 | TRAIN_DONE |

#### MiniGPT-4-Vicuna-7B

- Ours Top-1 / 第二阶段直接推荐：`L9`
- Ours Top-3：`L9,L10,L11`

| 排名 | 层 | 配置 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 状态 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | L9 | main/legacy | 49 | 0.247979 | 0.257039 | 293 | 61.34 | 61.27 | 61.41 | 100.00 | 98.89 | 76.582 | TRAIN_DONE_RECOVERED_G09_NODEFAIL_JOB3126082 |
| 2 | L10 | main/legacy | 36 | 0.247014 | 0.260045 | 293 | 61.51 | 61.48 | 61.42 | 100.00 | 98.74 | 76.630 | TRAIN_DONE_RECOVERED_SELECTION_G09_NODEFAIL_JOB3126082 |
| 3 | L11 | main/legacy | 39 | 0.287227 | 0.272469 | 293 | 62.03 | 61.78 | 61.97 | 100.00 | 98.37 | 76.830 | TRAIN_DONE_RECOVERED_SELECTION_G09_NODEFAIL_JOB3126082 |

#### LLaVA-v1.5-7B

- Ours Top-1 / 第二阶段直接推荐：`L0`
- Ours Top-3：`L0,L3,L1`

| 排名 | 层 | 配置 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 状态 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | L0 | main/legacy | 40 | 0.229806 | 0.314945 | 293 | 60.74 | 60.79 | 60.88 | 100.00 | 93.38 | 75.158 | TRAIN_DONE_LOCAL_TMP_JOB3117562 |
| 2 | L3 | main | 22 | 0.185736 | 0.301791 | 293 | 62.32 | 62.23 | 62.34 | 100.00 | 94.04 | 76.186 | TRAIN_DONE_MAIN_EVAL_DONE_JOB3126082 |
| 3 | L1 | main/legacy | 47 | 0.268086 | 0.302343 | 293 | 61.27 | 61.21 | 61.56 | 100.00 | 94.16 | 75.640 | TRAIN_DONE_LOCAL_TMP_JOB3117562 |

#### Qwen2.5-VL-3B

- Ours Top-1 / 第二阶段直接推荐：`L0`
- Ours Top-3：`L0,L1,L2`

| 排名 | 层 | 配置 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 状态 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | L0 | main/legacy | 45 | 0.470173 | 0.677373 | 293 | 52.74 | 52.90 | 52.28 | 100.00 | 94.20 | 70.42 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| 2 | L1 | main/legacy | 47 | 1.164370 | 0.680025 | 293 | 51.09 | 51.08 | 51.24 | 100.00 | 94.01 | 69.48 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| 3 | L2 | main/legacy | 43 | 0.670088 | 0.893235 | 293 | 51.75 | 51.64 | 51.72 | 100.00 | 94.52 | 69.93 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |

#### PaliGemma-3B

- Ours Top-1 / 第二阶段直接推荐：`L5`
- Ours Top-3：`L5,L4,L3`

| 排名 | 层 | 配置 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 状态 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | L5 | stable | 45 | 0.351702 | 0.347726 | 293 | 98.91 | 98.89 | 97.91 | 100.00 | 97.20 | 98.58 | TRAIN_DONE_STABLE_JOB3044208 |
| 2 | L4 | main | 39 | 0.332606 | 0.330234 | 293 | 99.23 | 99.22 | 98.68 | 100.00 | 98.00 | 99.026 | TRAIN_DONE_MAIN_FORMAL_TOP3_JOB3117562 |
| 3 | L3 | stable | 46 | 0.342673 | 0.347433 | 293 | 97.33 | 97.26 | 96.68 | 100.00 | 98.23 | 97.90 | TRAIN_DONE_STABLE_JOB3044208 |

#### SmolVLM-Instruct-1.7B

- Ours Top-1 / 第二阶段直接推荐：`L0`
- Ours Top-3：`L0,L1,L2`

| 排名 | 层 | 配置 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 状态 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | L0 | main/legacy | 41 | 0.450055 | 0.435366 | 293 | 54.33 | 54.21 | 54.12 | 100.00 | 94.16 | 71.36 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| 2 | L1 | main/legacy | 50 | 0.362595 | 0.523996 | 293 | 52.51 | 52.19 | 52.52 | 100.00 | 93.68 | 70.18 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| 3 | L2 | main/legacy | 46 | 0.367433 | 0.411423 | 293 | 52.96 | 52.77 | 53.14 | 100.00 | 93.74 | 70.522 | TRAIN_DONE_LOCAL_TMP_JOB3126082 |


### 3.3 MMKE-entity

#### BLIP2-OPT-2.7B

- Ours Top-1 / 第二阶段直接推荐：`L0`
- Ours Top-3：`L0,L1,L2`

| 排名 | 层 | 配置 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 状态 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | L0 | main/legacy | 24 | 5.307720 | 6.124232 | 954 | 57.71 | 57.63 | 57.62 | 100.00 | 56.32 | 65.86 | TRAIN_DONE |
| 2 | L1 | main/legacy | 11 | 5.893988 | 5.990400 | 954 | 57.94 | 57.91 | 57.96 | 100.00 | 88.71 | 72.504 | TRAIN_DONE_LOCAL_TMP_JOB3126082 |
| 3 | L2 | main/legacy | 3 | 6.995899 | 6.229083 | 954 | 57.81 | 57.83 | 57.85 | 100.00 | 83.12 | 71.32 | TRAIN_DONE |

#### InstructBLIP-Vicuna-7B

- Ours Top-1 / 第二阶段直接推荐：`L1`
- Ours Top-3：`L1,L0,L3`

| 排名 | 层 | 配置 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 状态 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | L1 | main/legacy | 43 | 0.994486 | 1.514755 | 954 | 48.72 | 48.85 | 48.71 | 100.00 | 99.61 | 69.18 | TRAIN_DONE_RESUMED_EPOCH45_CPU_SYNC_ACTIVATION_CKPT_JOB3044841 |
| 2 | L0 | main/legacy | 45 | 0.791271 | 0.933128 | 954 | 48.70 | 48.77 | 48.74 | 100.00 | 95.38 | 68.32 | TRAIN_DONE_LOCAL_TMP_JOB3044841 |
| 3 | L3 | main/legacy | 47 | 8.834968 | 9.652104 | 954 | 17.12 | 16.72 | 17.08 | 100.00 | 99.19 | 50.02 | TRAIN_DONE_LOCAL_TMP_JOB3044841 |

#### MiniGPT-4-Vicuna-7B

- Ours Top-1 / 第二阶段直接推荐：`L27`
- Ours Top-3：`L27,L28,L26`

| 排名 | 层 | 配置 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 状态 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | L27 | main | 44 | 0.747977 | 1.406714 | 954 | 60.48 | 60.61 | 60.44 | 100.00 | 97.59 | 75.824 | TRAIN_DONE_MAIN_EVAL_DONE_JOB3117562 |
| 2 | L28 | main/legacy | 48 | 1.072329 | 1.784545 | 954 | 60.66 | 60.69 | 60.67 | 100.00 | 98.20 | 76.04 | TRAIN_DONE |
| 3 | L26 | main | 46 | 0.877820 | 1.221248 | 954 | 59.71 | 59.89 | 59.60 | 100.00 | 98.40 | 75.520 | TRAIN_DONE_MAIN_EVAL_DONE_JOB3117562 |

#### LLaVA-v1.5-7B

- Ours Top-1 / 第二阶段直接推荐：`L13`
- Ours Top-3：`L13,L11,L12`

| 排名 | 层 | 配置 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 状态 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | L13 | — | — | — | — | — | — | — | — | — | — | — | **待完成正式评测** |
| 2 | L11 | — | — | — | — | — | — | — | — | — | — | — | **待完成正式评测** |
| 3 | L12 | — | — | — | — | — | — | — | — | — | — | — | **待完成正式评测** |

#### Qwen2.5-VL-3B

- Ours Top-1 / 第二阶段直接推荐：`L0`
- Ours Top-3：`L0,L1,L2`

| 排名 | 层 | 配置 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 状态 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | L0 | main/legacy | 50 | 1.760615 | 1.334659 | 954 | 54.78 | 54.49 | 54.88 | 100.00 | 96.93 | 72.22 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| 2 | L1 | main/legacy | 50 | 1.050795 | 1.466707 | 954 | 54.69 | 54.59 | 54.85 | 100.00 | 97.25 | 72.28 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| 3 | L2 | main/legacy | 49 | 0.828287 | 1.272041 | 954 | 54.88 | 54.78 | 54.96 | 100.00 | 95.57 | 72.04 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |

#### PaliGemma-3B

- Ours Top-1 / 第二阶段直接推荐：`L5`
- Ours Top-3：`L5,L4,L3`

| 排名 | 层 | 配置 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 状态 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | L5 | main | 4 | 1.668180 | 2.039312 | 954 | 88.46 | 88.47 | 88.73 | 100.00 | 88.39 | 90.81 | TRAIN_DONE_MAIN_JOB3044208 |
| 2 | L4 | main | 2 | 0.704963 | 0.882321 | 954 | 96.56 | 96.55 | 96.83 | 100.00 | 90.74 | 96.136 | TRAIN_DONE_MAIN_LOCAL_TMP_JOB3126082 |
| 3 | L3 | main | 7 | 2.865983 | 2.230218 | 954 | 91.52 | 91.49 | 91.94 | 100.00 | 89.89 | 92.97 | TRAIN_DONE_MAIN_JOB3044208 |

#### SmolVLM-Instruct-1.7B

- Ours Top-1 / 第二阶段直接推荐：`L0`
- Ours Top-3：`L0,L1,L2`

| 排名 | 层 | 配置 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 状态 |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | L0 | main/legacy | 47 | 0.717729 | 0.663257 | 954 | 51.76 | 51.75 | 51.71 | 100.00 | 97.11 | 70.47 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| 2 | L1 | main/legacy | 45 | 0.510274 | 0.635121 | 954 | 52.58 | 52.50 | 52.64 | 100.00 | 97.52 | 71.05 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| 3 | L2 | main/legacy | 49 | 0.532231 | 0.734351 | 954 | 52.80 | 52.79 | 52.69 | 100.00 | 97.30 | 71.12 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |

## 4. 原手册已完成候选层与服务器补证评测明细

本节保留原手册第4节中所有已登记的逐层状态，并追加41条服务器补证评测记录，不只包含Ours候选。`Ours标记`用于指出该层是否为本组合的主公式Top-1/Top-3；未标记不表示结果无效，只表示不是Ours主公式前三名。原表中PaliGemma stable L0失败行继续保留，但它无正式评测，不能计入完成数。

### 4.1 EVQA-pilot500

#### BLIP2-OPT-2.7B

Ours Top-1：`L0`；Top-3：`L0,L1,L2`。

| 层 | 配置 | Ours标记 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| L0 | main/legacy | Top-1 | 43 | 0.375991 | 0.368115 | 2093 | 44.15 | 40.43 | 40.29 | 100.00 | 65.95 | 58.16 | TRAIN_DONE |
| L1 | main/legacy | Top-3 | 45 | 0.521112 | 0.425138 | 2093 | 46.63 | 42.52 | 44.03 | 100.00 | 59.35 | 58.506 | TRAIN_DONE |
| L2 | main/legacy | Top-3 | 49 | 0.347236 | 0.417455 | 2093 | 32.99 | 28.69 | 30.45 | 100.00 | 58.51 | 50.128 | TRAIN_DONE |
| L3 | main/legacy | — | 48 | 0.326949 | 0.366410 | 2093 | 51.06 | 48.13 | 49.59 | 100.00 | 63.52 | 62.460 | TRAIN_DONE |
| L4 | main/legacy | — | 48 | 0.376648 | 0.397449 | 2093 | 43.82 | 40.43 | 40.51 | 100.00 | 61.56 | 57.264 | TRAIN_DONE |
| L5 | main/legacy | — | 49 | 0.300460 | 0.396571 | 2093 | 62.10 | 59.42 | 59.48 | 100.00 | 63.45 | 68.89 | TRAIN_DONE |
| L10 | main/legacy | — | 48 | 0.253585 | 0.299741 | 2093 | 64.79 | 61.72 | 62.38 | 100.00 | 76.55 | 73.09 | TRAIN_DONE |
| L14 | main/legacy | — | 46 | 0.206319 | 0.309126 | 2093 | 69.08 | 66.40 | 67.19 | 100.00 | 73.29 | 75.192 | TRAIN_DONE |
| L15 | main/legacy | — | 42 | 0.238769 | 0.336919 | 2093 | 66.35 | 62.89 | 63.90 | 100.00 | 72.05 | 73.04 | TRAIN_DONE |
| L16 | main/legacy | — | 48 | 0.342088 | 0.393885 | 2093 | 65.67 | 61.31 | 63.96 | 100.00 | 78.04 | 73.80 | TRAIN_DONE |
| L17 | main/legacy | — | 49 | 0.377570 | 0.384648 | 2093 | 66.89 | 63.79 | 65.36 | 100.00 | 81.94 | 75.60 | TRAIN_DONE |
| L18 | main/legacy | — | 50 | 0.346307 | 0.392374 | 2093 | 61.31 | 58.54 | 59.58 | 100.00 | 81.57 | 72.20 | TRAIN_DONE |
| L18-2 | main/legacy | — | 50 | 0.338767 | 0.385482 | 2093 | 63.29 | 59.64 | 62.24 | 100.00 | 81.51 | 73.34 | TRAIN_DONE |
| L19 | main/legacy | — | 41 | 0.277514 | 0.291689 | 2093 | 68.80 | 65.80 | 65.01 | 100.00 | 74.65 | 74.85 | TRAIN_DONE |
| L20 | main/legacy | — | 49 | 0.330291 | 0.379787 | 2093 | 62.38 | 58.49 | 60.65 | 100.00 | 82.90 | 72.88 | TRAIN_DONE |
| L21 | main/legacy | — | 44 | 0.369473 | 0.378125 | 2093 | 59.31 | 55.13 | 59.29 | 100.00 | 82.94 | 71.33 | TRAIN_DONE |
| L24 | main/legacy | — | 43 | 0.348283 | 0.361316 | 2093 | 46.55 | 42.21 | 48.30 | 100.00 | 80.82 | 63.58 | TRAIN_DONE |
| L25 | main/legacy | — | 45 | 0.205779 | 0.232244 | 2093 | 60.27 | 56.49 | 57.02 | 100.00 | 80.14 | 70.78 | TRAIN_DONE |
| L26 | main/legacy | — | 49 | 0.359013 | 0.363611 | 2093 | 37.61 | 34.55 | 38.48 | 100.00 | 77.07 | 57.54 | TRAIN_DONE |
| L29 | main/legacy | — | 48 | 0.387346 | 0.414155 | 2093 | 27.57 | 25.43 | 27.64 | 100.00 | 71.54 | 50.44 | TRAIN_DONE |
| L30 | main/legacy | — | 48 | 0.246737 | 0.557950 | 2093 | 32.60 | 30.53 | 30.22 | 100.00 | 74.86 | 53.64 | TRAIN_DONE |

#### InstructBLIP-Vicuna-7B

Ours Top-1：`L1`；Top-3：`L1,L0,L11`。

| 层 | 配置 | Ours标记 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| L0 | main | Top-3 | 49 | 0.599338 | 0.568572 | 2093 | 37.99 | 36.92 | 33.84 | 100.00 | 52.52 | 52.254 | TRAIN_DONE_MAIN_RECOVERED_EVAL_DONE_JOB3150065 |
| L1 | main | Top-1 | 43 | 0.711665 | 0.678210 | 2093 | 42.00 | 40.44 | 37.89 | 100.00 | 52.02 | 54.470 | TRAIN_DONE_MAIN_EVAL_DONE_JOB3150065 |
| L2 | main | — | 37 | 3.260540 | 1.270162 | 2093 | 30.81 | 29.74 | 27.73 | 100.00 | 61.48 | 49.952 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3150065 |
| L3 | main | — | 47 | 0.504032 | 0.941844 | 2093 | 32.54 | 31.38 | 30.53 | 100.00 | 57.92 | 50.474 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3150065 |
| L4 | main | — | 37 | 0.620709 | 1.438048 | 2093 | 28.72 | 27.31 | 27.50 | 100.00 | 55.88 | 47.882 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3150065 |
| L11 | main | Top-3 | 46 | 1.284068 | 1.214271 | 2093 | 28.72 | 28.18 | 27.18 | 100.00 | 62.10 | 49.236 | TRAIN_DONE_MAIN_EVAL_DONE_JOB3150065 |
| L14 | main/recovered-early | — | 40 | 0.440674 | 0.989394 | 2093 | 29.79 | 27.44 | 28.18 | 100.00 | 64.14 | 49.910 | TRAIN_DONE_MAIN_RECOVERED_EARLY_EPOCH40_EVAL_DONE_JOB3150065 |
| L15 | main/recovered-early | — | 38 | 0.579282 | 1.232926 | 2093 | 27.75 | 26.46 | 26.74 | 100.00 | 66.35 | 49.460 | TRAIN_DONE_MAIN_RECOVERED_EARLY_EPOCH38_EVAL_DONE_JOB3150065 |
| L16 | main/recovered-early | — | 37 | 0.312248 | 1.197859 | 2093 | 27.57 | 26.55 | 26.17 | 100.00 | 69.22 | 49.902 | TRAIN_DONE_MAIN_RECOVERED_EARLY_EPOCH37_EVAL_DONE_JOB3150065 |
| L18 | main | — | 50 | 0.409738 | 1.225163 | 2093 | 23.54 | 22.45 | 22.63 | 100.00 | 55.67 | 44.858 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3150065 |
| L19 | main/recovered-early | — | 41 | 2.461512 | 1.400177 | 2093 | 27.69 | 26.05 | 26.68 | 100.00 | 70.67 | 50.218 | TRAIN_DONE_MAIN_RECOVERED_EARLY_EPOCH41_EVAL_DONE_JOB3150065 |
| L25 | main | — | 50 | 3.241802 | 0.924779 | 2093 | 28.93 | 28.26 | 28.23 | 100.00 | 73.06 | 51.696 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3150065 |
| L26 | main/legacy | — | 50 | 0.202061 | 0.881081 | 2093 | 29.65 | 28.92 | 27.94 | 100.00 | 70.70 | 51.44 | TRAIN_DONE |
| L27 | main/legacy | — | 36 | 0.274748 | 0.888490 | 2093 | 29.64 | 28.66 | 28.71 | 100.00 | 74.34 | 52.27 | TRAIN_DONE |
| L28 | main/legacy | — | 49 | 1.700526 | 1.100682 | 2093 | 29.86 | 28.72 | 28.78 | 100.00 | 79.00 | 53.27 | TRAIN_DONE |

#### MiniGPT-4-Vicuna-7B

Ours Top-1：`L18`；Top-3：`L18,L19,L16`。

| 层 | 配置 | Ours标记 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| L0 | main | — | 50 | 0.481247 | 0.429186 | 2093 | 41.06 | 36.90 | 38.31 | 100.00 | 72.88 | 57.830 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3126082 |
| L1 | main | — | 48 | 0.386813 | 0.384318 | 2093 | 61.31 | 58.27 | 59.27 | 100.00 | 76.67 | 71.104 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3126082 |
| L2 | main | — | 50 | 0.479588 | 0.420997 | 2093 | 49.22 | 45.30 | 46.13 | 100.00 | 76.83 | 63.496 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3126082 |
| L7 | main | — | 47 | 0.352282 | 0.320426 | 2093 | 51.98 | 49.54 | 49.79 | 100.00 | 84.01 | 67.064 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3126082 |
| L8 | main | — | 50 | 0.370879 | 0.330787 | 2093 | 55.69 | 53.42 | 53.67 | 100.00 | 82.39 | 69.034 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3126082 |
| L9 | main | — | 48 | 0.370514 | 0.374562 | 2093 | 40.32 | 38.08 | 38.41 | 100.00 | 81.62 | 59.686 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3126082 |
| L10 | main | — | 50 | 0.311659 | 0.304353 | 2093 | 68.30 | 65.63 | 65.89 | 100.00 | 85.53 | 77.070 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3126082 |
| L14 | main | — | 43 | 0.376951 | 0.329464 | 2093 | 46.89 | 43.63 | 44.99 | 100.00 | 81.65 | 63.432 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3126082 |
| L15 | main | — | 50 | 0.266809 | 0.307395 | 2093 | 49.54 | 46.31 | 46.96 | 100.00 | 77.54 | 64.070 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3126082 |
| L16 | main/legacy | Top-3 | 50 | 0.314161 | 0.297508 | 2093 | 49.34 | 46.11 | 46.47 | 100.00 | 82.77 | 64.94 | TRAIN_DONE |
| L17 | main/legacy | — | 50 | 0.351717 | 0.299282 | 2093 | 47.77 | 46.10 | 45.82 | 100.00 | 79.85 | 63.91 | TRAIN_DONE |
| L18 | main/legacy | Top-1 | 44 | 0.305323 | 0.302507 | 2093 | 40.16 | 37.37 | 38.18 | 100.00 | 82.09 | 59.56 | TRAIN_DONE |
| L19 | main | Top-3 | 49 | 0.293260 | 0.293898 | 2093 | 38.47 | 36.52 | 37.19 | 100.00 | 79.71 | 58.378 | TRAIN_DONE_MAIN_EVAL_DONE_JOB3126082 |
| L22 | main | — | 49 | 0.243635 | 0.275690 | 2093 | 40.11 | 37.70 | 37.85 | 100.00 | 77.11 | 58.554 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3126082 |
| L24 | main/legacy | — | 45 | 0.289782 | 0.297207 | 2093 | 39.76 | 33.96 | 37.35 | 100.00 | 77.44 | 57.70 | TRAIN_DONE |
| L25 | main/legacy | — | 36 | 0.283050 | 0.298860 | 2093 | 40.09 | 37.73 | 37.59 | 100.00 | 76.92 | 58.47 | TRAIN_DONE |
| L26 | main/legacy | — | 43 | 0.306680 | 0.374355 | 2093 | 39.33 | 34.25 | 36.79 | 100.00 | 75.97 | 57.27 | TRAIN_DONE |
| L28 | main/legacy | — | 34 | 0.372540 | 0.349210 | 2093 | 39.42 | 36.54 | 37.36 | 100.00 | 78.49 | 58.36 | TRAIN_DONE |
| L29 | main | — | 43 | 0.359531 | 0.372103 | 2093 | 39.52 | 37.33 | 37.85 | 100.00 | 77.93 | 58.526 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3126082 |
| L30 | main/legacy | — | 48 | 0.461325 | 0.481391 | 2093 | 41.56 | 38.68 | 39.48 | 100.00 | 69.49 | 57.84 | TRAIN_DONE |
| L31 | main/legacy | — | 14 | 8.763226 | 10.222642 | 2093 | 23.88 | 24.05 | 25.44 | 100.00 | 100.00 | 54.67 | TRAIN_DONE |

#### LLaVA-v1.5-7B

Ours Top-1：`L0`；Top-3：`L0,L1,L2`。

| 层 | 配置 | Ours标记 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| L5 | main/legacy | — | 30 | 0.429168 | 0.437470 | 2093 | 60.31 | 55.48 | 56.61 | 100.00 | 78.07 | 70.094 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3178538 |
| L6 | main/legacy | — | 50 | 0.255764 | 0.419622 | 2093 | 58.35 | 54.30 | 57.43 | 100.00 | 72.90 | 68.596 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3150065 |
| L7 | main/legacy | — | 31 | 0.418494 | 0.478424 | 2093 | 42.91 | 36.99 | 40.64 | 100.00 | 68.55 | 57.818 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3150065 |
| L14 | main/legacy | — | 43 | 0.350849 | 0.365037 | 2093 | 42.87 | 37.36 | 40.65 | 100.00 | 77.10 | 59.596 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3150065 |
| L15 | main/legacy | — | 37 | 0.309543 | 0.366532 | 2093 | 44.52 | 39.02 | 40.63 | 100.00 | 78.98 | 60.630 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3150065 |
| L16 | main/legacy | — | 48 | 0.436350 | 0.350793 | 2093 | 50.40 | 45.63 | 47.45 | 100.00 | 81.11 | 64.918 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3150065 |
| L24 | main/legacy | — | 41 | 0.278317 | 0.351265 | 2093 | 52.26 | 44.18 | 42.27 | 100.00 | 73.38 | 62.418 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3178538 |
| L25 | main/legacy | — | 50 | 0.358062 | 0.329184 | 2093 | 50.28 | 44.06 | 41.17 | 100.00 | 68.93 | 60.888 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3178538_TMP_CLEANED_20260915 |
| L26 | main/legacy | — | 43 | 0.269856 | 0.355572 | 2093 | 51.51 | 43.55 | 42.16 | 100.00 | 77.72 | 62.99 | TRAIN_DONE |
| L27 | main/legacy | — | 50 | 0.311770 | 0.367348 | 2093 | 52.84 | 44.73 | 41.45 | 100.00 | 73.17 | 62.44 | TRAIN_DONE |
| L28 | main/legacy | — | 47 | 0.462426 | 0.498747 | 2093 | 50.13 | 43.50 | 41.14 | 100.00 | 69.48 | 60.85 | TRAIN_DONE |
| L30 | main/legacy | — | 46 | 0.304285 | 0.531518 | 2093 | 41.93 | 37.89 | 35.70 | 100.00 | 70.70 | 57.24 | TRAIN_DONE |
| L31 | main/legacy | — | 32 | 12.569068 | 9.569223 | 2093 | 32.21 | 30.16 | 28.01 | 100.00 | 100.00 | 58.08 | TRAIN_DONE |

#### Qwen2.5-VL-3B

Ours Top-1：`L21`；Top-3：`L21,L19,L17`。

| 层 | 配置 | Ours标记 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| L0 | main/legacy | — | 50 | 0.388003 | 0.443953 | 2093 | 53.71 | 43.50 | 34.56 | 100.00 | 82.68 | 62.89 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L1 | main/legacy | — | 41 | 0.409356 | 0.454254 | 2093 | 53.67 | 42.77 | 34.98 | 100.00 | 75.90 | 61.46 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L2 | main/legacy | — | 42 | 0.378063 | 0.448366 | 2093 | 53.64 | 45.58 | 36.81 | 100.00 | 75.24 | 62.25 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L3 | main/legacy | — | 49 | 0.411333 | 0.434602 | 2093 | 53.03 | 43.57 | 34.87 | 100.00 | 76.49 | 61.59 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L11 | main/legacy | — | 41 | 0.450617 | 0.448930 | 2093 | 53.17 | 43.40 | 35.12 | 100.00 | 77.48 | 61.83 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L12 | main/legacy | — | 39 | 0.416423 | 0.436754 | 2093 | 54.69 | 44.29 | 35.21 | 100.00 | 79.14 | 62.67 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L14 | main/legacy | — | 43 | 0.435669 | 0.420537 | 2093 | 54.34 | 44.45 | 35.20 | 100.00 | 82.94 | 63.39 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L15 | main/legacy | — | 49 | 0.459994 | 0.405599 | 2093 | 52.84 | 42.30 | 35.61 | 100.00 | 81.23 | 62.396 | TRAIN_DONE_CMA_MODELPRED_TOP3_BACKFILL_SHARED_JOB3178423 |
| L16 | main/legacy | — | 49 | 0.443011 | 0.411539 | 2093 | 52.90 | 41.96 | 36.70 | 100.00 | 82.23 | 62.76 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L17 | main/legacy | Top-3 | 45 | 0.369272 | 0.384334 | 2093 | 53.21 | 42.57 | 34.62 | 100.00 | 82.62 | 62.60 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L18 | main/legacy | — | 49 | 0.444120 | 0.399728 | 2093 | 53.09 | 44.11 | 37.70 | 100.00 | 82.87 | 63.55 | TRAIN_DONE |
| L19 | main/legacy | Top-3 | 41 | 0.417306 | 0.385106 | 2093 | 53.54 | 43.09 | 35.50 | 100.00 | 83.90 | 63.21 | TRAIN_DONE |
| L20 | main/legacy | — | 48 | 0.343881 | 0.375257 | 2093 | 52.62 | 41.40 | 33.99 | 100.00 | 82.55 | 62.11 | TRAIN_DONE |
| L21 | main/legacy | Top-1 | 49 | 0.444941 | 0.365603 | 2093 | 53.83 | 43.82 | 36.61 | 100.00 | 84.45 | 63.74 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L22 | main/legacy | — | 50 | 0.413212 | 0.390550 | 2093 | 54.06 | 43.14 | 35.30 | 100.00 | 81.58 | 62.82 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L24 | main/legacy | — | 47 | 0.328337 | 0.385822 | 2093 | 52.54 | 43.06 | 35.30 | 100.00 | 83.06 | 62.79 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L26 | main/legacy | — | 48 | 0.407629 | 0.382820 | 2093 | 52.76 | 42.32 | 35.42 | 100.00 | 81.15 | 62.33 | TRAIN_DONE |
| L27 | main/legacy | — | 35 | 0.303852 | 0.368658 | 2093 | 52.34 | 41.68 | 33.11 | 100.00 | 82.59 | 61.94 | TRAIN_DONE |
| L28 | main/legacy | — | 50 | 0.374178 | 0.364763 | 2093 | 53.48 | 43.14 | 35.20 | 100.00 | 80.81 | 62.53 | TRAIN_DONE |
| L29 | main/legacy | — | 49 | 0.396721 | 0.371691 | 2093 | 53.43 | 43.60 | 34.39 | 100.00 | 80.43 | 62.37 | TRAIN_DONE |
| L30 | main/legacy | — | 49 | 0.402044 | 0.378223 | 2093 | 53.30 | 42.72 | 34.77 | 100.00 | 81.81 | 62.52 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L31 | main/legacy | — | 49 | 0.233540 | 0.360590 | 2093 | 52.68 | 42.05 | 35.47 | 100.00 | 85.06 | 63.05 | TRAIN_DONE |
| L34 | main/legacy | — | 42 | 0.436983 | 0.584563 | 2093 | 53.15 | 42.20 | 33.65 | 100.00 | 84.86 | 62.77 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L35 | main/legacy | — | 49 | 8.960615 | 7.367229 | 2093 | 49.91 | 37.43 | 22.23 | 100.00 | 100.00 | 61.91 | TRAIN_DONE |

#### PaliGemma-3B

Ours Top-1：`L5`；Top-3：`L5,L4,L3`。

| 层 | 配置 | Ours标记 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| L1 | main | — | 14 | 13.376622 | 14.049339 | 2093 | 8.24 | 13.07 | 8.79 | 100.00 | 63.99 | 38.82 | TRAIN_DONE_MAIN_JOB3044208 |
| L1 | stable | — | 46 | 0.945888 | 1.149873 | 2093 | 77.65 | 77.27 | 93.93 | 100.00 | 56.47 | 81.06 | TRAIN_DONE_STABLE_JOB3044208 |
| L3 | main | Top-3 | 38 | 0.605178 | 0.531071 | 2093 | 85.63 | 85.86 | 89.21 | 100.00 | 67.90 | 85.720 | TRAIN_DONE_MAIN_FORMAL_TOP3_JOB3117562 |
| L4 | main | Top-3 | 38 | 7.798694 | 6.942612 | 2093 | 74.08 | 76.08 | 74.69 | 100.00 | 30.78 | 71.13 | TRAIN_DONE_MAIN_JOB3044208 |
| L4 | stable | Top-3 | 50 | 0.591566 | 0.491418 | 2093 | 66.09 | 64.75 | 85.62 | 100.00 | 77.50 | 78.79 | TRAIN_DONE_STABLE_RETRY_NUMERIC_GUARD_NONFINITE_SKIP16_JOB3044208 |
| L5 | main | Top-1 | 2 | 2.871534 | 4.631819 | 2093 | 85.30 | 83.96 | 86.80 | 100.00 | 34.78 | 78.17 | TRAIN_DONE_MAIN_JOB3044208 |
| L5 | stable | Top-1 | 46 | 0.596487 | 0.554996 | 2093 | 77.02 | 77.96 | 89.71 | 100.00 | 69.93 | 82.92 | TRAIN_DONE_STABLE_JOB3044208 |
| L6 | main | — | 31 | 3.886672 | 5.983205 | 2093 | 58.14 | 64.42 | 67.89 | 100.00 | 42.92 | 66.67 | TRAIN_DONE_MAIN_JOB3044208 |
| L6 | stable | — | 50 | 0.423632 | 0.468850 | 2093 | 69.94 | 69.13 | 89.83 | 100.00 | 68.92 | 79.56 | TRAIN_DONE_STABLE_RETRY_BUFFER1_JOB3044208 |
| L7 | main | — | 10 | 3.521098 | 4.525994 | 2093 | 82.02 | 80.30 | 84.32 | 100.00 | 31.60 | 75.65 | TRAIN_DONE_MAIN_JOB3044208 |
| L7 | stable | — | 43 | 0.973857 | 0.609388 | 2093 | 82.25 | 81.34 | 91.16 | 100.00 | 67.18 | 84.39 | TRAIN_DONE_STABLE_JOB3044208 |
| L8 | main | — | 3 | 4.863270 | 3.294556 | 2093 | 91.11 | 91.37 | 93.32 | 100.00 | 29.18 | 81.00 | TRAIN_DONE_MAIN_JOB3044208 |
| L8 | stable | — | 38 | 0.801614 | 0.593724 | 2093 | 78.95 | 76.17 | 93.02 | 100.00 | 65.09 | 82.65 | TRAIN_DONE_STABLE_JOB3044208 |
| L9 | main | — | 1 | 17.538765 | 20.548170 | 2093 | 0.54 | 0.81 | 0.45 | 100.00 | 78.98 | 36.16 | TRAIN_RECOVERED_FROM_STALL_MAIN |
| L10 | main | — | 1 | 6.230244 | 9.293444 | 2093 | 77.44 | 82.52 | 79.77 | 100.00 | 12.85 | 70.52 | TRAIN_DONE_MAIN |
| L11 | main | — | 2 | 2.080458 | 3.296938 | 2093 | 87.13 | 87.76 | 88.63 | 100.00 | 41.44 | 80.99 | TRAIN_DONE_MAIN |
| L12 | main | — | 1 | 4.603746 | 5.001783 | 2093 | 84.51 | 85.98 | 85.00 | 100.00 | 24.43 | 75.98 | TRAIN_DONE_MAIN |
| L14 | main | — | 1 | 14.575245 | -1369.521638 | 2093 | 5.59 | 9.06 | 4.75 | 100.00 | 40.89 | 32.06 | TRAIN_DONE_MAIN_NUMERIC_ANOMALY |
| L15 | main | — | 25 | 22.580488 | 31.500783 | 2093 | 0.18 | 0.23 | 0.14 | 100.00 | 100.00 | 40.11 | TRAIN_DONE_MAIN |
| L17 | main | — | 2 | 30.357973 | 30.934000 | 2093 | 0.18 | 0.23 | 0.14 | 100.00 | 100.00 | 40.11 | TRAIN_DONE_MAIN_JOB3044208 |
| L17 | stable | — | 23 | 26.938894 | 29.851553 | 2093 | 0.18 | 0.23 | 0.14 | 100.00 | 100.00 | 40.11 | TRAIN_DONE_STABLE_JOB3044208 |

#### SmolVLM-Instruct-1.7B

Ours Top-1：`L0`；Top-3：`L0,L1,L2`。

| 层 | 配置 | Ours标记 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| L0 | main/legacy | Top-1 | 50 | 0.445026 | 0.452992 | 2093 | 64.02 | 59.53 | 57.19 | 100.00 | 69.10 | 69.97 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L1 | main/legacy | Top-3 | 47 | 0.449670 | 0.456147 | 2093 | 46.20 | 40.21 | 35.59 | 100.00 | 71.86 | 58.77 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L2 | main/legacy | Top-3 | 48 | 0.429149 | 0.437729 | 2093 | 55.62 | 51.14 | 47.70 | 100.00 | 67.59 | 64.41 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L3 | main/legacy | — | 45 | 0.445100 | 0.442415 | 2093 | 58.43 | 52.94 | 49.94 | 100.00 | 71.47 | 66.56 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L5 | main/legacy | — | 42 | 0.402913 | 0.428878 | 2093 | 56.18 | 50.60 | 45.96 | 100.00 | 74.07 | 65.362 | TRAIN_DONE_CMA_MODELPRED_TOP3_BACKFILL_SHARED_JOB3178423 |
| L7 | main/legacy | — | 45 | 0.398488 | 0.419556 | 2093 | 60.39 | 55.03 | 51.65 | 100.00 | 75.17 | 68.45 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L8 | main/legacy | — | 48 | 0.401016 | 0.404693 | 2093 | 53.38 | 48.67 | 43.40 | 100.00 | 74.44 | 63.98 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L9 | main/legacy | — | 50 | 0.390892 | 0.384298 | 2093 | 58.69 | 54.30 | 50.42 | 100.00 | 76.89 | 68.06 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L10 | main/legacy | — | 48 | 0.404036 | 0.384991 | 2093 | 61.90 | 58.08 | 53.55 | 100.00 | 75.51 | 69.81 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L11 | main/legacy | — | 46 | 0.406657 | 0.396586 | 2093 | 57.70 | 52.14 | 47.72 | 100.00 | 78.63 | 67.24 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L12 | main/legacy | — | 42 | 0.376879 | 0.402297 | 2093 | 49.12 | 42.07 | 38.85 | 100.00 | 79.60 | 61.93 | TRAIN_DONE |
| L13 | main/legacy | — | 50 | 0.364526 | 0.381850 | 2093 | 44.80 | 40.22 | 34.16 | 100.00 | 78.07 | 59.45 | TRAIN_DONE |
| L14 | main/legacy | — | 50 | 0.405853 | 0.384188 | 2093 | 58.45 | 52.68 | 49.76 | 100.00 | 80.21 | 68.22 | TRAIN_DONE |
| L15 | main/legacy | — | 46 | 0.347375 | 0.362945 | 2093 | 45.80 | 39.49 | 34.58 | 100.00 | 78.83 | 59.74 | TRAIN_DONE |
| L16 | main/legacy | — | 41 | 0.373067 | 0.409362 | 2093 | 46.25 | 39.29 | 33.88 | 100.00 | 75.06 | 58.90 | TRAIN_DONE |
| L17 | main/legacy | — | 46 | 0.357996 | 0.383906 | 2093 | 44.36 | 39.14 | 33.17 | 100.00 | 77.57 | 58.85 | TRAIN_DONE |
| L19 | main/legacy | — | 40 | 0.380004 | 0.381024 | 2093 | 45.04 | 38.91 | 33.38 | 100.00 | 69.21 | 57.31 | TRAIN_DONE |
| L20 | main/legacy | — | 48 | 0.382679 | 0.383377 | 2093 | 45.09 | 39.20 | 33.92 | 100.00 | 67.53 | 57.15 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L21 | main/legacy | — | 47 | 0.500128 | 0.415271 | 2093 | 43.91 | 37.52 | 33.37 | 100.00 | 67.03 | 56.37 | TRAIN_DONE |
| L22 | main/legacy | — | 50 | 0.427672 | 0.488335 | 2093 | 42.44 | 36.70 | 31.77 | 100.00 | 68.45 | 55.87 | TRAIN_DONE |


### 4.2 MMKE-visual

#### BLIP2-OPT-2.7B

Ours Top-1：`L0`；Top-3：`L0,L1,L2`。

| 层 | 配置 | Ours标记 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| L0 | main/legacy | Top-1 | 50 | 1.835244 | 2.004923 | 293 | 53.13 | 53.14 | 53.20 | 100.00 | 52.38 | 62.37 | TRAIN_DONE |
| L1 | main/legacy | Top-3 | 50 | 0.516416 | 0.520349 | 293 | 52.09 | 51.80 | 51.97 | 100.00 | 92.60 | 69.69 | TRAIN_DONE |
| L2 | main/legacy | Top-3 | 44 | 0.813470 | 1.107170 | 293 | 52.04 | 51.91 | 51.58 | 100.00 | 93.80 | 69.87 | TRAIN_DONE |
| L3 | main/legacy | — | 50 | 0.584310 | 0.958273 | 293 | 52.01 | 51.65 | 52.37 | 100.00 | 87.68 | 68.74 | TRAIN_DONE |
| L4 | main/legacy | — | 49 | 0.491591 | 0.601247 | 293 | 51.78 | 51.72 | 51.60 | 100.00 | 90.85 | 69.19 | TRAIN_DONE |
| L14 | main/legacy | — | 50 | 0.476014 | 0.465106 | 293 | 51.32 | 51.11 | 50.76 | 100.00 | 97.16 | 70.07 | TRAIN_DONE |
| L15 | main/legacy | — | 47 | 0.360871 | 0.334112 | 293 | 53.41 | 53.31 | 53.20 | 100.00 | 97.03 | 71.39 | TRAIN_DONE |
| L16 | main/legacy | — | 48 | 0.384157 | 0.416895 | 293 | 52.71 | 52.60 | 52.19 | 100.00 | 97.33 | 70.97 | TRAIN_DONE |
| L17 | main/legacy | — | 48 | 0.385966 | 0.438426 | 293 | 53.09 | 53.05 | 52.89 | 100.00 | 97.05 | 71.22 | TRAIN_DONE |
| L18 | main/legacy | — | 45 | 0.326844 | 0.400918 | 293 | 53.00 | 52.95 | 53.12 | 100.00 | 97.37 | 71.29 | TRAIN_DONE |
| L19 | main/legacy | — | 49 | 0.241281 | 0.346198 | 293 | 53.87 | 53.61 | 53.41 | 100.00 | 95.95 | 71.37 | TRAIN_DONE |
| L20 | main/legacy | — | 45 | 0.679693 | 0.413794 | 293 | 53.80 | 53.80 | 53.53 | 100.00 | 97.94 | 71.81 | TRAIN_DONE |
| L21 | main/legacy | — | 49 | 0.364866 | 0.352452 | 293 | 53.54 | 53.67 | 53.37 | 100.00 | 98.09 | 71.73 | TRAIN_DONE |
| L22 | main/legacy | — | 49 | 0.330121 | 0.370491 | 293 | 54.38 | 54.32 | 54.20 | 100.00 | 97.69 | 72.12 | TRAIN_DONE |
| L24 | main/legacy | — | 44 | 0.414978 | 0.417396 | 293 | 53.86 | 53.79 | 53.65 | 100.00 | 95.48 | 71.36 | TRAIN_DONE |
| L25 | main/legacy | — | 46 | 0.387067 | 0.575704 | 293 | 53.67 | 53.55 | 53.47 | 100.00 | 96.65 | 71.47 | TRAIN_DONE |
| L26 | main/legacy | — | 49 | 0.681283 | 0.788690 | 293 | 53.06 | 53.29 | 53.23 | 100.00 | 95.84 | 71.08 | TRAIN_DONE |
| L29 | main/legacy | — | 48 | 4.021954 | 2.907863 | 293 | 49.96 | 49.85 | 49.73 | 100.00 | 96.97 | 69.30 | TRAIN_DONE |
| L30 | main/legacy | — | 48 | 5.169809 | 5.331725 | 293 | 44.26 | 44.01 | 44.24 | 100.00 | 96.33 | 65.77 | TRAIN_DONE |

#### InstructBLIP-Vicuna-7B

Ours Top-1：`L1`；Top-3：`L1,L0,L3`。

| 层 | 配置 | Ours标记 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| L0 | main/legacy | Top-3 | 50 | 0.171615 | 0.222510 | 293 | 52.26 | 52.42 | 52.17 | 100.00 | 99.62 | 71.29 | TRAIN_DONE |
| L1 | main/legacy | Top-1 | 50 | 0.231107 | 0.292772 | 293 | 51.70 | 51.67 | 51.55 | 100.00 | 96.48 | 70.28 | TRAIN_DONE |
| L2 | main/legacy | — | 46 | 6.189603 | 6.830468 | 293 | 18.67 | 16.65 | 18.50 | 100.00 | 99.57 | 50.68 | TRAIN_DONE |
| L3 | main/legacy | Top-3 | 47 | 5.070473 | 6.227147 | 293 | 19.40 | 17.34 | 19.20 | 100.00 | 99.85 | 51.16 | TRAIN_DONE |
| L4 | main/legacy | — | 49 | 7.357730 | 7.321517 | 293 | 17.38 | 15.28 | 17.58 | 100.00 | 99.05 | 49.86 | TRAIN_DONE |
| L5 | main/legacy | — | 49 | 6.999227 | 7.345585 | 293 | 17.03 | 14.84 | 17.13 | 100.00 | 99.51 | 49.70 | TRAIN_DONE |
| L14 | main/legacy | — | 50 | 5.457262 | 6.049061 | 293 | 17.34 | 15.97 | 17.24 | 100.00 | 99.57 | 50.02 | TRAIN_DONE |
| L15 | main/legacy | — | 47 | 7.049882 | 6.446094 | 293 | 17.08 | 16.01 | 16.99 | 100.00 | 99.85 | 49.99 | TRAIN_DONE |
| L16 | main/legacy | — | 48 | 8.969355 | 7.001298 | 293 | 18.08 | 17.11 | 17.96 | 100.00 | 99.63 | 50.56 | TRAIN_DONE |
| L17 | main/legacy | — | 50 | 7.270292 | 6.931965 | 293 | 18.47 | 16.80 | 18.64 | 100.00 | 99.73 | 50.73 | TRAIN_DONE |
| L18 | main/legacy | — | 50 | 6.697884 | 6.893876 | 293 | 18.08 | 16.55 | 18.22 | 100.00 | 99.60 | 50.49 | TRAIN_DONE |
| L19 | main/legacy | — | 49 | 5.929656 | 5.769108 | 293 | 18.56 | 16.42 | 18.60 | 100.00 | 99.59 | 50.63 | TRAIN_DONE |
| L22 | main/legacy | — | 46 | 6.008149 | 6.773030 | 293 | 17.87 | 16.80 | 17.62 | 100.00 | 100.00 | 50.46 | TRAIN_DONE |
| L23 | main/legacy | — | 50 | 5.294744 | 6.377842 | 293 | 18.06 | 16.63 | 17.96 | 100.00 | 99.73 | 50.48 | TRAIN_DONE |
| L24 | main/legacy | — | 47 | 6.654134 | 7.255629 | 293 | 18.21 | 16.78 | 18.19 | 100.00 | 99.76 | 50.59 | TRAIN_DONE |
| L25 | main/legacy | — | 46 | 5.746799 | 6.995333 | 293 | 17.41 | 15.67 | 17.23 | 100.00 | 99.73 | 50.01 | TRAIN_DONE |
| L26 | main/legacy | — | 49 | 6.737056 | 7.514501 | 293 | 17.55 | 15.30 | 17.37 | 100.00 | 99.63 | 49.97 | TRAIN_DONE |
| L27 | main/legacy | — | 48 | 6.786605 | 7.596408 | 293 | 18.47 | 16.75 | 18.57 | 100.00 | 99.18 | 50.59 | TRAIN_DONE |
| L28 | main/legacy | — | 49 | 5.810029 | 7.744205 | 293 | 17.32 | 15.62 | 17.06 | 100.00 | 99.83 | 49.97 | TRAIN_DONE |
| L30 | main/legacy | — | 45 | 10.282062 | 11.521651 | 293 | 11.75 | 11.08 | 11.62 | 100.00 | 99.32 | 46.75 | TRAIN_DONE |
| L31 | main/legacy | — | 28 | 36.477367 | 36.696703 | 293 | 0.04 | 0.04 | 0.04 | 100.00 | 100.00 | 40.02 | TRAIN_DONE |

#### MiniGPT-4-Vicuna-7B

Ours Top-1：`L9`；Top-3：`L9,L10,L11`。

| 层 | 配置 | Ours标记 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| L0 | main/legacy | — | 50 | 0.269117 | 0.267466 | 293 | 59.95 | 60.02 | 60.14 | 100.00 | 98.95 | 75.812 | TRAIN_DONE_REPAIRED_SELECTION_LOCAL_TMP_JOB3044841 |
| L1 | main/legacy | — | 50 | 0.272173 | 0.281973 | 293 | 60.32 | 60.32 | 60.55 | 100.00 | 97.93 | 75.824 | TRAIN_DONE_REPAIRED_SELECTION_LOCAL_TMP_JOB3044841 |
| L2 | main/legacy | — | 41 | 0.253623 | 0.267989 | 293 | 60.35 | 60.40 | 60.64 | 100.00 | 98.93 | 76.064 | TRAIN_DONE_REPAIRED_SELECTION_LOCAL_TMP_JOB3044841 |
| L3 | main/legacy | — | 36 | 0.254035 | 0.288644 | 293 | 61.41 | 61.60 | 61.07 | 100.00 | 99.09 | 76.634 | TRAIN_DONE_REPAIRED_SELECTION_LOCAL_TMP_JOB3044841 |
| L5 | main/legacy | — | 35 | 0.258817 | 0.281105 | 293 | 62.09 | 62.04 | 61.86 | 100.00 | 98.73 | 76.94 | TRAIN_DONE |
| L8 | main/legacy | — | 49 | 0.265526 | 0.256176 | 293 | 61.75 | 61.62 | 61.68 | 100.00 | 97.91 | 76.59 | TRAIN_DONE |
| L9 | main/legacy | Top-1 | 49 | 0.247979 | 0.257039 | 293 | 61.34 | 61.27 | 61.41 | 100.00 | 98.89 | 76.582 | TRAIN_DONE_RECOVERED_G09_NODEFAIL_JOB3126082 |
| L10 | main/legacy | Top-3 | 36 | 0.247014 | 0.260045 | 293 | 61.51 | 61.48 | 61.42 | 100.00 | 98.74 | 76.630 | TRAIN_DONE_RECOVERED_SELECTION_G09_NODEFAIL_JOB3126082 |
| L11 | main/legacy | Top-3 | 39 | 0.287227 | 0.272469 | 293 | 62.03 | 61.78 | 61.97 | 100.00 | 98.37 | 76.830 | TRAIN_DONE_RECOVERED_SELECTION_G09_NODEFAIL_JOB3126082 |
| L14 | main/legacy | — | 50 | 0.234949 | 0.249512 | 293 | 61.07 | 60.94 | 60.84 | 100.00 | 98.88 | 76.35 | TRAIN_DONE |
| L15 | main/legacy | — | 50 | 0.242507 | 0.251438 | 293 | 60.39 | 60.22 | 60.11 | 100.00 | 98.64 | 75.87 | TRAIN_DONE |
| L16 | main/legacy | — | 33 | 0.238199 | 0.268302 | 293 | 61.01 | 60.87 | 60.75 | 100.00 | 97.86 | 76.10 | TRAIN_DONE |
| L17 | main/legacy | — | 49 | 0.249406 | 0.265122 | 293 | 59.81 | 59.86 | 59.90 | 100.00 | 97.14 | 75.34 | TRAIN_DONE |
| L18 | main/legacy | — | 46 | 0.269364 | 0.262238 | 293 | 59.33 | 59.18 | 59.41 | 100.00 | 98.00 | 75.18 | TRAIN_DONE |
| L24 | main/legacy | — | 49 | 0.502779 | 0.438395 | 293 | 57.99 | 57.94 | 58.05 | 100.00 | 97.30 | 74.26 | TRAIN_DONE |
| L25 | main/legacy | — | 50 | 0.759646 | 0.611862 | 293 | 57.89 | 57.73 | 57.74 | 100.00 | 98.25 | 74.32 | TRAIN_DONE |
| L26 | main/legacy | — | 49 | 0.676290 | 0.788584 | 293 | 57.32 | 56.97 | 57.30 | 100.00 | 98.06 | 73.93 | TRAIN_DONE |
| L27 | main/legacy | — | 43 | 0.908072 | 1.413074 | 293 | 57.88 | 57.60 | 57.52 | 100.00 | 97.97 | 74.19 | TRAIN_DONE |
| L28 | main/legacy | — | 45 | 1.148645 | 1.711778 | 293 | 57.96 | 57.92 | 57.85 | 100.00 | 98.46 | 74.44 | TRAIN_DONE |
| L29 | main/legacy | — | 48 | 3.022602 | 2.115868 | 293 | 56.55 | 56.18 | 56.37 | 100.00 | 97.23 | 73.266 | TRAIN_DONE_REPAIRED_SELECTION_LOCAL_TMP_JOB3044841 |
| L31 | main/legacy | — | 43 | 6.683348 | 7.304613 | 293 | 47.21 | 46.58 | 46.99 | 100.00 | 100.00 | 68.16 | TRAIN_DONE |

#### LLaVA-v1.5-7B

Ours Top-1：`L0`；Top-3：`L0,L3,L1`。

| 层 | 配置 | Ours标记 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| L0 | main/legacy | Top-1 | 40 | 0.229806 | 0.314945 | 293 | 60.74 | 60.79 | 60.88 | 100.00 | 93.38 | 75.158 | TRAIN_DONE_LOCAL_TMP_JOB3117562 |
| L1 | main/legacy | Top-3 | 47 | 0.268086 | 0.302343 | 293 | 61.27 | 61.21 | 61.56 | 100.00 | 94.16 | 75.640 | TRAIN_DONE_LOCAL_TMP_JOB3117562 |
| L2 | main/legacy | — | 33 | 0.281384 | 0.305978 | 293 | 63.43 | 63.24 | 63.39 | 100.00 | 93.87 | 76.786 | TRAIN_DONE_RECOVERED_G09_NODEFAIL_JOB3117562 |
| L3 | main | Top-3 | 22 | 0.185736 | 0.301791 | 293 | 62.32 | 62.23 | 62.34 | 100.00 | 94.04 | 76.186 | TRAIN_DONE_MAIN_EVAL_DONE_JOB3126082 |
| L7 | main/legacy | — | 35 | 0.214817 | 0.286848 | 293 | 62.21 | 62.15 | 62.30 | 100.00 | 96.10 | 76.552 | TRAIN_DONE_RECOVERED_G09_NODEFAIL_JOB3117562 |
| L8 | main/legacy | — | 47 | 0.181363 | 0.260420 | 293 | 62.93 | 62.85 | 62.66 | 100.00 | 96.60 | 77.008 | TRAIN_DONE_RECOVERED_G09_NODEFAIL_JOB3117562 |
| L9 | main/legacy | — | 40 | 0.400646 | 0.281962 | 293 | 62.64 | 62.66 | 62.69 | 100.00 | 96.56 | 76.910 | TRAIN_DONE_RECOVERED_G09_NODEFAIL_JOB3117562 |
| L12 | main/legacy | — | 47 | 0.173525 | 0.243153 | 293 | 61.63 | 61.64 | 61.52 | 100.00 | 95.56 | 76.070 | TRAIN_DONE_RECOVERED_G09_NODEFAIL_JOB3117562 |
| L14 | main | — | 47 | 0.146300 | 0.248103 | 293 | 62.03 | 62.07 | 62.33 | 100.00 | 96.14 | 76.514 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3126082 |
| L15 | main/legacy | — | 40 | 0.119042 | 0.231111 | 293 | 61.02 | 61.00 | 60.91 | 100.00 | 95.83 | 75.752 | TRAIN_DONE_FORMAL_TOP3_JOB3126082 |
| L16 | main | — | 21 | 0.202061 | 0.291990 | 293 | 60.64 | 60.33 | 60.58 | 100.00 | 97.15 | 75.740 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3126082 |
| L22 | main | — | 50 | 0.280591 | 0.381777 | 293 | 57.52 | 57.34 | 57.48 | 100.00 | 96.86 | 73.840 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3126082 |
| L24 | main | — | 48 | 0.199074 | 0.292995 | 293 | 58.40 | 58.07 | 58.42 | 100.00 | 98.04 | 74.586 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3126082 |
| L26 | main | — | 49 | 0.432336 | 0.546802 | 293 | 57.41 | 57.08 | 57.27 | 100.00 | 95.36 | 73.424 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3126082 |
| L27 | main | — | 48 | 0.281177 | 0.556985 | 293 | 58.83 | 58.38 | 58.66 | 100.00 | 96.11 | 74.396 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3126082 |
| L28 | main/legacy | — | 49 | 0.446779 | 0.996580 | 293 | 57.58 | 57.49 | 57.99 | 100.00 | 94.57 | 73.53 | TRAIN_DONE |

#### Qwen2.5-VL-3B

Ours Top-1：`L0`；Top-3：`L0,L1,L2`。

| 层 | 配置 | Ours标记 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| L0 | main/legacy | Top-1 | 45 | 0.470173 | 0.677373 | 293 | 52.74 | 52.90 | 52.28 | 100.00 | 94.20 | 70.42 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L1 | main/legacy | Top-3 | 47 | 1.164370 | 0.680025 | 293 | 51.09 | 51.08 | 51.24 | 100.00 | 94.01 | 69.48 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L2 | main/legacy | Top-3 | 43 | 0.670088 | 0.893235 | 293 | 51.75 | 51.64 | 51.72 | 100.00 | 94.52 | 69.93 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L6 | main/legacy | — | 45 | 0.499272 | 0.734185 | 293 | 52.38 | 52.01 | 51.85 | 100.00 | 94.51 | 70.15 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L7 | main/legacy | — | 49 | 0.474863 | 0.731563 | 293 | 52.59 | 52.39 | 52.38 | 100.00 | 94.97 | 70.47 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L8 | main/legacy | — | 47 | 0.389735 | 0.593588 | 293 | 52.58 | 52.64 | 52.33 | 100.00 | 96.67 | 70.84 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L9 | main/legacy | — | 50 | 0.394751 | 0.598401 | 293 | 51.68 | 51.27 | 51.61 | 100.00 | 92.83 | 69.48 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L11 | main/legacy | — | 48 | 0.539290 | 0.561360 | 293 | 53.34 | 53.13 | 53.01 | 100.00 | 95.51 | 71.00 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L12 | main/legacy | — | 47 | 0.458533 | 0.499579 | 293 | 52.61 | 52.22 | 52.87 | 100.00 | 97.30 | 71.00 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L13 | main/legacy | — | 48 | 0.461817 | 0.418149 | 293 | 51.51 | 51.34 | 52.22 | 100.00 | 96.89 | 70.39 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L14 | main/legacy | — | 43 | 0.517781 | 0.504366 | 293 | 52.10 | 51.90 | 51.96 | 100.00 | 93.12 | 69.82 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L16 | main/legacy | — | 49 | 0.419709 | 0.486438 | 293 | 51.80 | 51.51 | 51.76 | 100.00 | 93.99 | 69.81 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L17 | main/legacy | — | 49 | 0.335644 | 0.397961 | 293 | 51.16 | 51.10 | 51.51 | 100.00 | 94.25 | 69.60 | TRAIN_DONE_EXISTING_CKPT_EVAL_LOCAL_TMP_JOB3044208 |
| L18 | main/legacy | — | 46 | 0.441055 | 0.438478 | 293 | 52.69 | 52.25 | 52.48 | 100.00 | 95.82 | 70.65 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L19 | main/legacy | — | 50 | 0.359075 | 0.417327 | 293 | 51.61 | 51.09 | 51.45 | 100.00 | 95.52 | 69.93 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L20 | main/legacy | — | 45 | 0.245531 | 0.482954 | 293 | 51.94 | 51.65 | 51.86 | 100.00 | 96.56 | 70.40 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L22 | main/legacy | — | 50 | 0.550950 | 0.494701 | 293 | 51.81 | 51.30 | 51.86 | 100.00 | 96.73 | 70.34 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L26 | main/legacy | — | 43 | 0.537117 | 0.583348 | 293 | 49.13 | 48.83 | 48.95 | 100.00 | 94.40 | 68.26 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L27 | main/legacy | — | 48 | 0.393821 | 0.756435 | 293 | 48.99 | 48.98 | 48.75 | 100.00 | 93.87 | 68.12 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L28 | main/legacy | — | 43 | 0.595793 | 1.006616 | 293 | 49.89 | 49.35 | 49.90 | 100.00 | 92.60 | 68.35 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L30 | main/legacy | — | 48 | 1.174112 | 1.430872 | 293 | 47.65 | 47.29 | 47.56 | 100.00 | 92.74 | 67.05 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |

#### PaliGemma-3B

Ours Top-1：`L5`；Top-3：`L5,L4,L3`。

| 层 | 配置 | Ours标记 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| L0 | stable | — | - | - | - | 0 | - | - | - | - | - | - | FAILED_STABLE_L0_NONCONVERGENT_CKPT_WRITE_ERROR_NO_EVAL |
| L1 | stable | — | 49 | 0.334160 | 0.355574 | 293 | 97.76 | 97.70 | 96.65 | 100.00 | 98.39 | 98.10 | TRAIN_DONE_STABLE_JOB3044208 |
| L2 | stable | — | 44 | 0.346728 | 0.154633 | 293 | 99.34 | 99.35 | 97.65 | 100.00 | 96.00 | 98.47 | TRAIN_DONE_STABLE_JOB3044208 |
| L3 | stable | Top-3 | 46 | 0.342673 | 0.347433 | 293 | 97.33 | 97.26 | 96.68 | 100.00 | 98.23 | 97.90 | TRAIN_DONE_STABLE_JOB3044208 |
| L4 | main | Top-3 | 39 | 0.332606 | 0.330234 | 293 | 99.23 | 99.22 | 98.68 | 100.00 | 98.00 | 99.026 | TRAIN_DONE_MAIN_FORMAL_TOP3_JOB3117562 |
| L5 | stable | Top-1 | 45 | 0.351702 | 0.347726 | 293 | 98.91 | 98.89 | 97.91 | 100.00 | 97.20 | 98.58 | TRAIN_DONE_STABLE_JOB3044208 |
| L6 | stable | — | 47 | 0.334160 | 0.348006 | 293 | 97.49 | 97.56 | 96.67 | 100.00 | 98.12 | 97.97 | TRAIN_DONE_STABLE_JOB3044208 |
| L7 | stable | — | 49 | 0.354043 | 0.352879 | 293 | 98.54 | 98.45 | 98.17 | 100.00 | 96.84 | 98.40 | TRAIN_DONE_STABLE_JOB3044208 |
| L8 | main | — | 2 | 3.971717 | 2.536566 | 293 | 95.13 | 95.16 | 95.19 | 100.00 | 70.96 | 91.29 | TRAIN_DONE_MAIN |
| L8 | main/legacy | — | 13 | 0.498305 | 0.587410 | 293 | 96.90 | 96.93 | 96.43 | 100.00 | 94.33 | 96.92 | TRAIN_DONE_MANUAL_EPOCH13 |
| L9 | main | — | 6 | 0.444634 | 0.517213 | 293 | 98.79 | 98.83 | 98.69 | 100.00 | 94.16 | 98.09 | TRAIN_DONE_MAIN |
| L9 | stable | — | 50 | 0.351273 | 0.358913 | 293 | 98.50 | 98.47 | 98.23 | 100.00 | 96.39 | 98.32 | TRAIN_DONE_STABLE |
| L10 | main | — | 24 | 0.343096 | 0.348760 | 293 | 98.97 | 98.98 | 98.91 | 100.00 | 98.42 | 99.06 | TRAIN_DONE_MAIN |
| L10 | stable | — | 47 | 0.343897 | 0.354527 | 293 | 98.43 | 98.42 | 98.49 | 100.00 | 97.24 | 98.52 | TRAIN_DONE_STABLE |
| L11 | main | — | 7 | 0.579804 | 0.737678 | 293 | 96.10 | 96.05 | 95.71 | 100.00 | 97.49 | 97.07 | TRAIN_DONE_MAIN |
| L11 | stable | — | 50 | 0.404692 | 0.473600 | 293 | 96.34 | 96.21 | 96.33 | 100.00 | 96.85 | 97.15 | TRAIN_DONE_STABLE |
| L12 | main | — | 50 | 0.290716 | 0.401058 | 293 | 95.53 | 95.58 | 95.55 | 100.00 | 97.74 | 96.88 | TRAIN_DONE_MAIN |
| L12 | stable | — | 33 | 0.785029 | 0.381374 | 293 | 94.82 | 94.82 | 94.73 | 100.00 | 94.93 | 95.86 | TRAIN_DONE_STABLE |
| L13 | stable | — | 48 | 1.357916 | 1.455967 | 293 | 87.34 | 87.26 | 87.56 | 100.00 | 95.49 | 91.53 | TRAIN_DONE_STABLE_JOB3044208 |
| L14 | main | — | 1 | 17.459480 | -351.953961 | 293 | 0.90 | 1.01 | 0.88 | 100.00 | 92.34 | 39.03 | TRAIN_DONE_MAIN |
| L14 | stable | — | 50 | 10.762311 | 11.484160 | 293 | 32.64 | 32.85 | 32.57 | 100.00 | 96.28 | 58.87 | TRAIN_DONE_STABLE |
| L17 | main | — | 6 | 30.490068 | 30.831037 | 293 | 0.08 | 0.08 | 0.09 | 100.00 | 100.00 | 40.05 | TRAIN_DONE_MAIN |
| L17 | stable | — | 6 | 30.519789 | 30.862625 | 293 | 0.08 | 0.08 | 0.09 | 100.00 | 100.00 | 40.05 | TRAIN_DONE_STABLE |

#### SmolVLM-Instruct-1.7B

Ours Top-1：`L0`；Top-3：`L0,L1,L2`。

| 层 | 配置 | Ours标记 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| L0 | main/legacy | Top-1 | 41 | 0.450055 | 0.435366 | 293 | 54.33 | 54.21 | 54.12 | 100.00 | 94.16 | 71.36 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L1 | main/legacy | Top-3 | 50 | 0.362595 | 0.523996 | 293 | 52.51 | 52.19 | 52.52 | 100.00 | 93.68 | 70.18 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L2 | main/legacy | Top-3 | 46 | 0.367433 | 0.411423 | 293 | 52.96 | 52.77 | 53.14 | 100.00 | 93.74 | 70.522 | TRAIN_DONE_LOCAL_TMP_JOB3126082 |
| L4 | main/legacy | — | 44 | 0.394254 | 0.523291 | 293 | 52.73 | 52.96 | 52.59 | 100.00 | 94.39 | 70.53 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L5 | main/legacy | — | 49 | 0.532208 | 0.448303 | 293 | 52.16 | 52.31 | 52.52 | 100.00 | 94.62 | 70.322 | TRAIN_DONE_CMA_MODELPRED_TOP3_BACKFILL_SHARED_JOB3178423 |
| L6 | main/legacy | — | 44 | 0.388501 | 0.489452 | 293 | 51.88 | 51.72 | 52.37 | 100.00 | 93.44 | 69.88 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L7 | main/legacy | — | 47 | 1.079098 | 0.479630 | 293 | 53.44 | 53.30 | 53.54 | 100.00 | 93.58 | 70.77 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L8 | main/legacy | — | 50 | 0.445105 | 0.519847 | 293 | 51.72 | 51.44 | 51.80 | 100.00 | 93.35 | 69.66 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L9 | main/legacy | — | 50 | 0.425834 | 0.489161 | 293 | 51.15 | 50.99 | 51.22 | 100.00 | 93.88 | 69.45 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L10 | main/legacy | — | 50 | 0.374906 | 0.415141 | 293 | 51.35 | 51.25 | 51.26 | 100.00 | 92.85 | 69.34 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L11 | main/legacy | — | 42 | 0.577633 | 0.520159 | 293 | 51.49 | 51.39 | 51.34 | 100.00 | 93.86 | 69.62 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L12 | main/legacy | — | 50 | 0.359039 | 0.477444 | 293 | 50.02 | 49.73 | 49.95 | 100.00 | 92.88 | 68.52 | TRAIN_DONE |
| L13 | main/legacy | — | 50 | 0.324814 | 0.407615 | 293 | 52.18 | 51.90 | 51.81 | 100.00 | 93.27 | 69.83 | TRAIN_DONE |
| L14 | main/legacy | — | 40 | 0.521079 | 0.537226 | 293 | 49.68 | 49.32 | 49.61 | 100.00 | 94.60 | 68.64 | TRAIN_DONE |
| L15 | main/legacy | — | 47 | 0.543355 | 0.544850 | 293 | 49.66 | 49.27 | 49.84 | 100.00 | 93.64 | 68.48 | TRAIN_DONE |
| L16 | main/legacy | — | 48 | 0.553617 | 0.595523 | 293 | 47.77 | 47.40 | 47.34 | 100.00 | 93.43 | 67.19 | TRAIN_DONE |
| L17 | main/legacy | — | 48 | 0.749514 | 0.654440 | 293 | 47.84 | 47.70 | 48.11 | 100.00 | 92.58 | 67.25 | TRAIN_DONE |
| L18 | main/legacy | — | 50 | 1.323157 | 1.739675 | 293 | 50.04 | 49.60 | 49.99 | 100.00 | 89.84 | 67.89 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L19 | main/legacy | — | 49 | 2.573995 | 2.826347 | 293 | 48.91 | 48.48 | 48.83 | 100.00 | 90.48 | 67.34 | TRAIN_DONE |
| L20 | main/legacy | — | 49 | 6.606372 | 4.496605 | 293 | 48.57 | 48.32 | 48.73 | 100.00 | 91.40 | 67.40 | TRAIN_DONE |
| L21 | main/legacy | — | 42 | 2.808244 | 3.857834 | 293 | 49.34 | 49.05 | 49.22 | 100.00 | 88.17 | 67.16 | TRAIN_DONE |


### 4.3 MMKE-entity

#### BLIP2-OPT-2.7B

Ours Top-1：`L0`；Top-3：`L0,L1,L2`。

| 层 | 配置 | Ours标记 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| L0 | main/legacy | Top-1 | 24 | 5.307720 | 6.124232 | 954 | 57.71 | 57.63 | 57.62 | 100.00 | 56.32 | 65.86 | TRAIN_DONE |
| L1 | main/legacy | Top-3 | 11 | 5.893988 | 5.990400 | 954 | 57.94 | 57.91 | 57.96 | 100.00 | 88.71 | 72.504 | TRAIN_DONE_LOCAL_TMP_JOB3126082 |
| L2 | main/legacy | Top-3 | 3 | 6.995899 | 6.229083 | 954 | 57.81 | 57.83 | 57.85 | 100.00 | 83.12 | 71.32 | TRAIN_DONE |
| L3 | main/legacy | — | 50 | 2.827587 | 3.004137 | 954 | 53.51 | 53.53 | 53.60 | 100.00 | 94.42 | 71.01 | TRAIN_DONE |
| L4 | main/legacy | — | 3 | 5.593518 | 6.027703 | 954 | 57.63 | 57.63 | 57.63 | 100.00 | 88.32 | 72.24 | TRAIN_DONE |
| L13 | main/legacy | — | 50 | 0.539618 | 0.736236 | 954 | 50.51 | 50.41 | 50.56 | 100.00 | 98.09 | 69.91 | TRAIN_DONE |
| L14 | main/legacy | — | 49 | 0.580979 | 0.732211 | 954 | 50.78 | 50.81 | 50.70 | 100.00 | 98.03 | 70.06 | TRAIN_DONE |
| L15 | main/legacy | — | 47 | 0.589422 | 0.932563 | 954 | 51.17 | 51.22 | 51.14 | 100.00 | 95.41 | 69.79 | TRAIN_DONE |
| L16 | main/legacy | — | 50 | 0.516484 | 0.527484 | 954 | 51.01 | 50.98 | 50.99 | 100.00 | 94.25 | 69.45 | TRAIN_DONE |
| L17 | main/legacy | — | 48 | 0.710702 | 0.651066 | 954 | 51.25 | 51.31 | 51.27 | 100.00 | 97.48 | 70.26 | TRAIN_DONE |
| L18 | main/legacy | — | 50 | 0.401966 | 0.597055 | 954 | 50.97 | 51.01 | 50.96 | 100.00 | 97.64 | 70.12 | TRAIN_DONE |
| L19 | main/legacy | — | 49 | 0.557689 | 0.554307 | 954 | 51.60 | 51.48 | 51.60 | 100.00 | 97.25 | 70.39 | TRAIN_DONE |
| L20 | main/legacy | — | 49 | 0.607764 | 0.626840 | 954 | 51.61 | 51.53 | 51.66 | 100.00 | 98.37 | 70.63 | TRAIN_DONE |
| L21 | main/legacy | — | 50 | 0.611507 | 0.947310 | 954 | 51.03 | 51.02 | 50.93 | 100.00 | 95.54 | 69.70 | TRAIN_DONE |
| L22 | main/legacy | — | 47 | 0.476664 | 0.634711 | 954 | 51.91 | 51.96 | 51.87 | 100.00 | 97.01 | 70.55 | TRAIN_DONE |
| L23 | main/legacy | — | 49 | 0.889130 | 1.210585 | 954 | 51.97 | 52.04 | 51.99 | 100.00 | 97.12 | 70.62 | TRAIN_DONE |
| L24 | main/legacy | — | 47 | 1.978343 | 1.652320 | 954 | 52.18 | 52.33 | 52.03 | 100.00 | 97.45 | 70.80 | TRAIN_DONE |
| L25 | main/legacy | — | 50 | 1.257574 | 1.250349 | 954 | 52.23 | 52.30 | 52.30 | 100.00 | 96.99 | 70.76 | TRAIN_DONE |
| L26 | main/legacy | — | 46 | 1.123006 | 1.444681 | 954 | 51.81 | 51.77 | 51.78 | 100.00 | 94.20 | 69.91 | TRAIN_DONE |
| L29 | main/legacy | — | 48 | 3.541405 | 3.073246 | 954 | 52.75 | 52.77 | 52.67 | 100.00 | 96.40 | 70.92 | TRAIN_DONE |
| L30 | main/legacy | — | 50 | 4.810149 | 5.183463 | 954 | 52.61 | 52.52 | 52.64 | 100.00 | 97.95 | 71.14 | TRAIN_DONE |

#### InstructBLIP-Vicuna-7B

Ours Top-1：`L1`；Top-3：`L1,L0,L3`。

| 层 | 配置 | Ours标记 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| L0 | main/legacy | Top-3 | 45 | 0.791271 | 0.933128 | 954 | 48.70 | 48.77 | 48.74 | 100.00 | 95.38 | 68.32 | TRAIN_DONE_LOCAL_TMP_JOB3044841 |
| L1 | main/legacy | Top-1 | 43 | 0.994486 | 1.514755 | 954 | 48.72 | 48.85 | 48.71 | 100.00 | 99.61 | 69.18 | TRAIN_DONE_RESUMED_EPOCH45_CPU_SYNC_ACTIVATION_CKPT_JOB3044841 |
| L2 | main/legacy | — | 49 | 10.099280 | 9.843736 | 954 | 16.71 | 16.24 | 16.61 | 100.00 | 99.38 | 49.79 | TRAIN_DONE |
| L3 | main/legacy | Top-3 | 47 | 8.834968 | 9.652104 | 954 | 17.12 | 16.72 | 17.08 | 100.00 | 99.19 | 50.02 | TRAIN_DONE_LOCAL_TMP_JOB3044841 |
| L4 | main/legacy | — | 50 | 13.571908 | 11.388381 | 954 | 15.15 | 14.54 | 15.05 | 100.00 | 99.72 | 48.89 | TRAIN_DONE_LOCAL_TMP_JOB3044841 |
| L5 | main/legacy | — | 49 | 12.275386 | 11.474885 | 954 | 13.91 | 13.44 | 13.84 | 100.00 | 99.82 | 48.20 | TRAIN_DONE_LOCAL_TMP_JOB3044841 |
| L14 | main/legacy | — | 48 | 10.428762 | 10.631304 | 954 | 14.62 | 14.47 | 14.57 | 100.00 | 99.53 | 48.64 | TRAIN_DONE |
| L15 | main/legacy | — | 49 | 11.955615 | 11.116361 | 954 | 14.99 | 14.60 | 14.88 | 100.00 | 99.75 | 48.84 | TRAIN_DONE |
| L16 | main/legacy | — | 50 | 8.842422 | 10.171081 | 954 | 14.85 | 14.33 | 14.81 | 100.00 | 99.61 | 48.72 | TRAIN_DONE |
| L17 | main/legacy | — | 50 | 11.998194 | 11.095907 | 954 | 15.27 | 14.50 | 15.24 | 100.00 | 99.63 | 48.93 | TRAIN_DONE |
| L18 | main/legacy | — | 48 | 11.101890 | 10.146582 | 954 | 14.76 | 14.27 | 14.75 | 100.00 | 99.34 | 48.62 | TRAIN_DONE |
| L19 | main/legacy | — | 48 | 13.396421 | 11.298227 | 954 | 14.60 | 14.37 | 14.49 | 100.00 | 99.53 | 48.60 | TRAIN_DONE |
| L22 | main/legacy | — | 49 | 12.596491 | 11.504756 | 954 | 14.08 | 13.22 | 14.08 | 100.00 | 99.25 | 48.13 | TRAIN_DONE_LOCAL_TMP_JOB3044841 |
| L23 | main/legacy | — | 46 | 11.005220 | 10.972629 | 954 | 14.24 | 13.63 | 14.15 | 100.00 | 99.64 | 48.33 | TRAIN_DONE_LOCAL_TMP_JOB3044841 |
| L24 | main/legacy | — | 50 | 10.610746 | 10.732185 | 954 | 12.35 | 11.97 | 12.24 | 100.00 | 99.78 | 47.27 | TRAIN_DONE_LOCAL_TMP_JOB3044841 |
| L25 | main/legacy | — | 50 | 12.247351 | 10.972824 | 954 | 13.10 | 12.44 | 13.08 | 100.00 | 99.27 | 47.58 | TRAIN_DONE_LOCAL_TMP_JOB3044841 |
| L26 | main/legacy | — | 46 | 10.188010 | 11.535521 | 954 | 12.93 | 12.35 | 12.89 | 100.00 | 99.42 | 47.52 | TRAIN_DONE |
| L27 | main/legacy | — | 49 | 11.816212 | 11.171924 | 954 | 12.24 | 11.65 | 12.20 | 100.00 | 98.63 | 46.94 | TRAIN_DONE |
| L28 | main/legacy | — | 47 | 9.575759 | 11.254244 | 954 | 11.90 | 11.49 | 11.74 | 100.00 | 99.24 | 46.87 | TRAIN_DONE |
| L29 | main/legacy | — | 48 | 12.351160 | 11.742287 | 954 | 11.66 | 10.67 | 11.61 | 100.00 | 99.58 | 46.70 | TRAIN_DONE |
| L30 | main/legacy | — | 45 | 13.693354 | 14.488698 | 954 | 11.25 | 10.29 | 11.08 | 100.00 | 99.80 | 46.48 | TRAIN_DONE |
| L31 | main/legacy | — | 37 | 33.016987 | 38.583624 | 954 | 0.20 | 0.20 | 0.20 | 100.00 | 100.00 | 40.12 | TRAIN_DONE |

#### MiniGPT-4-Vicuna-7B

Ours Top-1：`L27`；Top-3：`L27,L28,L26`。

| 层 | 配置 | Ours标记 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| L0 | main | — | 50 | 0.296119 | 0.316450 | 954 | 59.30 | 59.23 | 59.19 | 100.00 | 98.96 | 75.336 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3117562 |
| L1 | main | — | 44 | 0.401454 | 0.342019 | 954 | 59.31 | 59.25 | 59.26 | 100.00 | 97.99 | 75.162 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3117562 |
| L2 | main/legacy | — | 48 | 0.274402 | 0.280683 | 954 | 59.89 | 59.84 | 59.78 | 100.00 | 98.24 | 75.55 | TRAIN_DONE_LOCAL_TMP_JOB3044841_BACKED_UP |
| L3 | main | — | 47 | 0.311317 | 0.324533 | 954 | 59.67 | 59.71 | 59.64 | 100.00 | 98.04 | 75.412 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3117562 |
| L4 | main | — | 44 | 0.315207 | 0.294066 | 954 | 60.51 | 60.48 | 60.57 | 100.00 | 98.13 | 75.938 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3117562 |
| L6 | main | — | 47 | 0.292086 | 0.298080 | 954 | 59.29 | 59.21 | 59.30 | 100.00 | 98.35 | 75.230 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3117562 |
| L14 | main | — | 45 | 0.318980 | 0.312375 | 954 | 60.86 | 60.83 | 60.84 | 100.00 | 98.65 | 76.236 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3117562 |
| L15 | main/legacy | — | 46 | 0.303345 | 0.305240 | 954 | 60.02 | 60.06 | 60.10 | 100.00 | 98.36 | 75.71 | TRAIN_DONE |
| L16 | main | — | 44 | 0.338442 | 0.331353 | 954 | 60.27 | 60.33 | 60.24 | 100.00 | 98.42 | 75.852 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3117562 |
| L22 | main | — | 47 | 0.416511 | 0.552444 | 954 | 58.82 | 58.82 | 58.76 | 100.00 | 98.50 | 74.980 | TRAIN_DONE_MAIN_EVAL_DONE_SHARED_JOB3117562 |
| L23 | main/legacy | — | 50 | 0.380379 | 0.484842 | 954 | 59.08 | 59.10 | 58.97 | 100.00 | 98.00 | 75.03 | TRAIN_DONE |
| L24 | main/legacy | — | 50 | 0.425550 | 0.585518 | 954 | 59.20 | 59.28 | 59.13 | 100.00 | 97.57 | 75.04 | TRAIN_DONE |
| L25 | main/legacy | — | 49 | 0.918550 | 1.143279 | 954 | 59.21 | 59.32 | 59.25 | 100.00 | 98.13 | 75.18 | TRAIN_DONE |
| L26 | main | Top-3 | 46 | 0.877820 | 1.221248 | 954 | 59.71 | 59.89 | 59.60 | 100.00 | 98.40 | 75.520 | TRAIN_DONE_MAIN_EVAL_DONE_JOB3117562 |
| L27 | main | Top-1 | 44 | 0.747977 | 1.406714 | 954 | 60.48 | 60.61 | 60.44 | 100.00 | 97.59 | 75.824 | TRAIN_DONE_MAIN_EVAL_DONE_JOB3117562 |
| L28 | main/legacy | Top-3 | 48 | 1.072329 | 1.784545 | 954 | 60.66 | 60.69 | 60.67 | 100.00 | 98.20 | 76.04 | TRAIN_DONE |
| L31 | main/legacy | — | 41 | 5.441149 | 5.627008 | 954 | 60.69 | 59.93 | 60.71 | 100.00 | 100.00 | 76.27 | TRAIN_DONE |

#### LLaVA-v1.5-7B

Ours Top-1：`L13`；Top-3：`L13,L11,L12`。

| 层 | 配置 | Ours标记 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| L14 | main/legacy | — | 49 | 0.159782 | 0.290381 | 954 | 61.31 | 61.45 | 61.29 | 100.00 | 96.12 | 76.034 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3126082 |
| L15 | main/legacy | — | 45 | 0.423595 | 0.272476 | 954 | 61.07 | 61.18 | 61.01 | 100.00 | 95.43 | 75.738 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3126082 |
| L16 | main/legacy | — | 41 | 0.172495 | 0.248927 | 954 | 61.13 | 61.25 | 61.10 | 100.00 | 96.57 | 76.010 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3126082 |
| L23 | main/legacy | — | 49 | 0.284640 | 0.374458 | 954 | 60.39 | 60.41 | 60.34 | 100.00 | 96.56 | 75.540 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3178423 |
| L26 | main/legacy | — | 46 | 0.452505 | 0.778010 | 954 | 59.95 | 60.07 | 59.97 | 100.00 | 95.73 | 75.144 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3178423 |
| L27 | main/legacy | — | 50 | 0.859437 | 1.028096 | 954 | 60.03 | 60.08 | 60.00 | 100.00 | 95.63 | 75.148 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3178423 |
| L28 | main/legacy | — | 48 | 1.354002 | 1.707617 | 954 | 59.47 | 59.54 | 59.50 | 100.00 | 95.20 | 74.742 | TRAIN_DONE_FORMAL_TOP3_SHARED_JOB3178423 |

#### Qwen2.5-VL-3B

Ours Top-1：`L0`；Top-3：`L0,L1,L2`。

| 层 | 配置 | Ours标记 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| L0 | main/legacy | Top-1 | 50 | 1.760615 | 1.334659 | 954 | 54.78 | 54.49 | 54.88 | 100.00 | 96.93 | 72.22 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L1 | main/legacy | Top-3 | 50 | 1.050795 | 1.466707 | 954 | 54.69 | 54.59 | 54.85 | 100.00 | 97.25 | 72.28 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L2 | main/legacy | Top-3 | 49 | 0.828287 | 1.272041 | 954 | 54.88 | 54.78 | 54.96 | 100.00 | 95.57 | 72.04 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L13 | main/legacy | — | 49 | 1.519723 | 1.238898 | 954 | 53.29 | 53.17 | 53.31 | 100.00 | 97.43 | 71.44 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L14 | main/legacy | — | 49 | 0.686763 | 0.980262 | 954 | 53.46 | 53.41 | 53.44 | 100.00 | 97.10 | 71.48 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L15 | main/legacy | — | 50 | 1.871835 | 1.463023 | 954 | 52.94 | 52.85 | 52.95 | 100.00 | 96.87 | 71.12 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L16 | main/legacy | — | 47 | 1.531398 | 1.362743 | 954 | 53.68 | 53.56 | 53.73 | 100.00 | 96.98 | 71.59 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L17 | main/legacy | — | 46 | 0.521832 | 1.285736 | 954 | 53.59 | 53.47 | 53.61 | 100.00 | 96.73 | 71.48 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L18 | main/legacy | — | 49 | 0.705021 | 0.883009 | 954 | 53.65 | 53.56 | 53.61 | 100.00 | 95.17 | 71.20 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L20 | main/legacy | — | 49 | 0.910451 | 0.666375 | 954 | 53.24 | 53.16 | 53.35 | 100.00 | 96.30 | 71.21 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L21 | main/legacy | — | 50 | 0.532463 | 0.822907 | 954 | 52.65 | 52.37 | 52.65 | 100.00 | 95.62 | 70.66 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L22 | main/legacy | — | 49 | 1.156874 | 0.733265 | 954 | 53.59 | 53.36 | 53.53 | 100.00 | 96.00 | 71.30 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L25 | main/legacy | — | 44 | 0.686750 | 0.649926 | 954 | 54.00 | 53.87 | 54.03 | 100.00 | 96.58 | 71.70 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L26 | main/legacy | — | 46 | 0.741123 | 1.065371 | 954 | 52.78 | 52.53 | 52.82 | 100.00 | 95.18 | 70.66 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L27 | main/legacy | — | 50 | 1.188038 | 0.983534 | 954 | 53.91 | 53.67 | 54.05 | 100.00 | 95.07 | 71.34 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L28 | main/legacy | — | 50 | 0.872761 | 1.150297 | 954 | 54.69 | 54.54 | 54.83 | 100.00 | 95.01 | 71.81 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L29 | main/legacy | — | 48 | 1.635255 | 1.636492 | 954 | 55.81 | 55.61 | 55.91 | 100.00 | 95.95 | 72.66 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L30 | main/legacy | — | 50 | 1.664727 | 2.286476 | 954 | 55.97 | 55.74 | 55.92 | 100.00 | 94.42 | 72.41 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |

#### PaliGemma-3B

Ours Top-1：`L5`；Top-3：`L5,L4,L3`。

| 层 | 配置 | Ours标记 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| L0 | main | — | 8 | 2887.873291 | 2815.587779 | 954 | 0.00 | 0.00 | 0.00 | 100.00 | 0.00 | 20.00 | TRAIN_DONE_MAIN_NUMERIC_DEGENERATE_JOB3044208 |
| L1 | main | — | 3 | 3.320363 | 2.964910 | 954 | 93.20 | 93.23 | 93.41 | 100.00 | 64.47 | 88.86 | TRAIN_DONE_MAIN_JOB3044208 |
| L1 | stable | — | 37 | 0.333475 | 0.368120 | 954 | 99.34 | 99.34 | 99.57 | 100.00 | 96.30 | 98.91 | TRAIN_DONE_STABLE_JOB3044208 |
| L2 | main | — | 3 | 4.878585 | 6.100427 | 954 | 84.24 | 84.22 | 84.72 | 100.00 | 57.00 | 82.04 | TRAIN_DONE_MAIN_JOB3044208 |
| L2 | stable | — | 38 | 0.323105 | 0.361797 | 954 | 99.34 | 99.34 | 99.53 | 100.00 | 95.78 | 98.80 | TRAIN_DONE_STABLE_JOB3044208 |
| L3 | main | Top-3 | 7 | 2.865983 | 2.230218 | 954 | 91.52 | 91.49 | 91.94 | 100.00 | 89.89 | 92.97 | TRAIN_DONE_MAIN_JOB3044208 |
| L3 | stable | Top-3 | 47 | 0.345626 | 0.346825 | 954 | 98.87 | 98.88 | 99.07 | 100.00 | 97.39 | 98.84 | TRAIN_DONE_STABLE_JOB3044208 |
| L4 | main | Top-3 | 2 | 0.704963 | 0.882321 | 954 | 96.56 | 96.55 | 96.83 | 100.00 | 90.74 | 96.136 | TRAIN_DONE_MAIN_LOCAL_TMP_JOB3126082 |
| L5 | main | Top-1 | 4 | 1.668180 | 2.039312 | 954 | 88.46 | 88.47 | 88.73 | 100.00 | 88.39 | 90.81 | TRAIN_DONE_MAIN_JOB3044208 |
| L5 | stable | Top-1 | 35 | 0.340905 | 0.359304 | 954 | 98.98 | 98.97 | 99.32 | 100.00 | 96.52 | 98.76 | TRAIN_DONE_STABLE_JOB3044208 |
| L6 | main | — | 2 | 1.206908 | 1.361229 | 954 | 95.85 | 95.89 | 95.96 | 100.00 | 97.22 | 96.98 | TRAIN_DONE_MAIN_JOB3044208 |
| L6 | stable | — | 47 | 0.330504 | 0.359201 | 954 | 99.09 | 99.08 | 99.39 | 100.00 | 97.22 | 98.96 | TRAIN_DONE_STABLE_JOB3044208 |
| L7 | main | — | 10 | 2.394458 | 2.547924 | 954 | 84.71 | 84.65 | 84.72 | 100.00 | 96.53 | 90.12 | TRAIN_DONE_MAIN_JOB3044208 |
| L7 | stable | — | 49 | 0.329062 | 0.344094 | 954 | 99.32 | 99.31 | 99.44 | 100.00 | 95.35 | 98.68 | TRAIN_DONE_STABLE_JOB3044208 |
| L8 | main | — | 3 | 0.592419 | 1.096720 | 954 | 95.94 | 95.81 | 96.00 | 100.00 | 93.73 | 96.30 | TRAIN_DONE_MAIN_JOB3044208 |
| L8 | stable | — | 49 | 0.342368 | 0.348620 | 954 | 99.32 | 99.31 | 99.39 | 100.00 | 97.94 | 99.19 | TRAIN_DONE_STABLE_JOB3044208 |
| L9 | main | — | 2 | 4.133635 | 3.973418 | 954 | 78.51 | 78.36 | 78.55 | 100.00 | 91.62 | 85.41 | TRAIN_DONE_MAIN_JOB3044208 |
| L9 | stable | — | 50 | 0.339769 | 0.346904 | 954 | 99.35 | 99.34 | 99.35 | 100.00 | 97.35 | 99.08 | TRAIN_DONE_STABLE_JOB3044208 |
| L10 | main | — | 1 | 18.536318 | 17.571920 | 954 | 15.04 | 15.09 | 15.00 | 100.00 | 46.26 | 38.28 | TRAIN_DONE_MAIN_JOB3044208 |
| L10 | stable | — | 49 | 0.347619 | 0.345262 | 954 | 99.03 | 99.00 | 99.00 | 100.00 | 97.25 | 98.86 | TRAIN_DONE_STABLE_JOB3044208 |
| L11 | main | — | 1 | 12.053761 | 12.271097 | 954 | 21.41 | 21.14 | 21.52 | 100.00 | 59.04 | 44.62 | TRAIN_DONE_MAIN_JOB3044208 |
| L11 | stable | — | 47 | 0.577410 | 0.686626 | 954 | 94.89 | 94.83 | 94.83 | 100.00 | 97.34 | 96.38 | TRAIN_DONE_STABLE_JOB3044208 |
| L12 | main | — | 2 | 2.737614 | 2.109276 | 954 | 88.78 | 88.73 | 88.85 | 100.00 | 87.00 | 90.67 | TRAIN_DONE_MAIN_JOB3044208 |
| L12 | stable | — | 48 | 0.538605 | 0.830285 | 954 | 93.40 | 93.26 | 93.41 | 100.00 | 96.41 | 95.30 | TRAIN_DONE_STABLE_RETRY_BUFFER1_GPU0_JOB3044208 |
| L13 | main | — | 2 | 10.599213 | 11.613107 | 954 | 17.60 | 17.58 | 17.52 | 100.00 | 90.57 | 48.65 | TRAIN_DONE_MAIN_JOB3044208 |
| L13 | stable | — | 49 | 1.960766 | 2.245620 | 954 | 81.47 | 81.04 | 81.51 | 100.00 | 97.54 | 88.31 | TRAIN_DONE_STABLE_JOB3044208 |
| L16 | main | — | 49 | 15.929332 | 18.301300 | 954 | 12.43 | 12.21 | 12.41 | 100.00 | 98.17 | 47.04 | TRAIN_DONE_MAIN_RETRY_NUMERIC_GUARD_NONFINITE_SKIP34_JOB3044208 |
| L16 | stable | — | 42 | 18.220282 | 19.640825 | 954 | 12.38 | 12.42 | 12.37 | 100.00 | 96.65 | 46.76 | TRAIN_DONE_STABLE_JOB3044208 |
| L17 | main | — | 22 | 31.180017 | 31.213888 | 954 | 0.56 | 0.55 | 0.55 | 100.00 | 100.00 | 40.33 | TRAIN_DONE_MAIN_JOB3044208 |
| L17 | stable | — | 38 | 30.471798 | 30.907994 | 954 | 0.56 | 0.55 | 0.55 | 100.00 | 100.00 | 40.33 | TRAIN_DONE_STABLE_JOB3044208 |

#### SmolVLM-Instruct-1.7B

Ours Top-1：`L0`；Top-3：`L0,L1,L2`。

| 层 | 配置 | Ours标记 | Ckpt Epoch | Raw Loss | EMA Loss | Samples | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Train Status |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| L0 | main/legacy | Top-1 | 47 | 0.717729 | 0.663257 | 954 | 51.76 | 51.75 | 51.71 | 100.00 | 97.11 | 70.47 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L1 | main/legacy | Top-3 | 45 | 0.510274 | 0.635121 | 954 | 52.58 | 52.50 | 52.64 | 100.00 | 97.52 | 71.05 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L2 | main/legacy | Top-3 | 49 | 0.532231 | 0.734351 | 954 | 52.80 | 52.79 | 52.69 | 100.00 | 97.30 | 71.12 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L6 | main/legacy | — | 47 | 0.546545 | 0.688924 | 954 | 51.98 | 51.99 | 52.03 | 100.00 | 96.46 | 70.49 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L7 | main/legacy | — | 50 | 1.166944 | 0.670295 | 954 | 51.42 | 51.40 | 51.38 | 100.00 | 97.32 | 70.30 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L9 | main/legacy | — | 50 | 0.814315 | 0.769834 | 954 | 51.86 | 51.94 | 51.85 | 100.00 | 96.55 | 70.44 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L10 | main/legacy | — | 48 | 0.795752 | 0.811847 | 954 | 52.21 | 52.14 | 52.14 | 100.00 | 96.59 | 70.62 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L11 | main/legacy | — | 50 | 0.662297 | 0.798535 | 954 | 50.22 | 50.39 | 50.18 | 100.00 | 96.97 | 69.55 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L12 | main/legacy | — | 50 | 0.663954 | 0.936153 | 954 | 52.31 | 52.27 | 52.31 | 100.00 | 97.32 | 70.84 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L13 | main/legacy | — | 50 | 0.489384 | 0.820767 | 954 | 50.63 | 50.76 | 50.62 | 100.00 | 96.22 | 69.65 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L14 | main/legacy | — | 50 | 0.687138 | 0.851731 | 954 | 50.21 | 50.31 | 50.02 | 100.00 | 96.08 | 69.32 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L15 | main/legacy | — | 50 | 0.973436 | 0.839188 | 954 | 50.24 | 50.42 | 50.08 | 100.00 | 96.91 | 69.53 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L16 | main/legacy | — | 50 | 1.646834 | 1.453352 | 954 | 50.85 | 50.96 | 50.69 | 100.00 | 95.45 | 69.59 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L17 | main/legacy | — | 48 | 2.262018 | 2.741290 | 954 | 52.45 | 52.62 | 52.32 | 100.00 | 95.55 | 70.59 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |
| L18 | main/legacy | — | 50 | 3.508034 | 3.420248 | 954 | 53.75 | 53.91 | 53.65 | 100.00 | 96.03 | 71.47 | TRAIN_DONE_LOCAL_TMP_JOB3044208 |

## 5. 当前缺失与解释限制

### 5.1 Ours Top-3尚无任何正式评测的层

| 数据集 | 模型 | 缺失层 |
|---|---|---|
| EVQA-pilot500 | LLaVA-v1.5-7B | L0,L1,L2 |
| MMKE-entity | LLaVA-v1.5-7B | L13,L11,L12 |

### 5.2 已有评测但仅为stable配置的Ours层

| 数据集 | 模型 | stable-only层 | 说明 |
|---|---|---|---|
| MMKE-visual | PaliGemma-3B | L5,L3 | 有真实评测，但不能替代main配置结果 |

### 5.3 解释限制

- 表中Top-3行出现`待完成正式评测`时，只能说明定位预测已经存在，不能声称该层已有真实编辑效果。
- PaliGemma的stable与main必须分开解释；本文件保留二者，但第二阶段主配置证据优先读取main。
- 当前正在服务器运行且尚无完整正式评测的层不会提前进入本文件；新完成层须凭selected与独立eval补录，不能只凭状态文字。
- 第二阶段跨模型扩展时，每个组合读取本文件第2.1节自己的`recommended_layer`，禁止把BLIP2的L0直接类推给其他模型。

## 6. 可复核来源

- Ours Top-1/Top-3：来源手册第2.7.0节。
- 真实训练与评测值：来源手册第4、4.1节。
- 第4节漏行的6层完整评测补证：`outputs/firstphase_oursdirect_verified_eval_supplement_20260915.csv`，每行附共享盘`eval_full.done`绝对路径。
- 原始Ours排名CSV：`md/Location/VisualGradient_11formula_analysis_files_20260720/analysis_outputs_20260731/formula_topk_all_21.csv`。
- 本文件生成脚本：`outputs/build_firstphase_testvalue_oursdirect_recommend.py`。

## 7. 最新诊断评测补录（2026-09-22，历史表不覆盖）

EVQA/PaliGemma L0使用新补跑中现存最低有限EMA的Epoch2/step500，按用户指示只评测、不续训。完成独立2093条eval；原训练保存30轮记录后停在Epoch31，**没有完成50轮、不收敛，不能混入正常主配置验收或自动改写方法比较**。

| 数据集 | 模型 | 层 | Epoch | raw loss | EMA loss | eval数 | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | 状态 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| EVQA-pilot500 | PaliGemma-3B | L0 | 2 | 3187.056885 | 3209.824510 | 2093 | 0.16 | 0.18 | 0.16 | 100.00 | 76.96 | 35.492 | EVAL_DONE_NONCONVERGENT_DIAGNOSTIC / TRAIN_INCOMPLETE |

评测于2026-09-22 08:47:15 CST结束，rc=0；本地证据：`server_results/live_backfill/pali_l0_diag_20260922/evqa-pilot500/paligemma-3b/layer_00/`。selected权重保留共享盘，历史失败记录不删。主手册3.5.3有完整SHA-256及协议说明。本补录不修改Ours的Top-1/Top-3推荐层；八方法联合Top-3当前313/324已有评测（含2项诊断、7项stable-only），剩余11个LLaVA层见主手册3.4.8，不能误读为313项均正常训练完成。
