# VisEdit-Contrib-Pre-Alt pilot500 六模型真实扫层实验手册

## 0. 审核状态

本手册用于指导 `EVQA-pilot500` 上的真实扫层实验。当前阶段先写实验手册，不在本地直接启动训练。

实验目标：根据 [edit_layer_candidate_layers_for_real_sweep.md](</d:/开题/正式开题/Model Edit/bli2-reasonvqa/dataset/md/Location/edit_layer_candidate_layers_for_real_sweep.md>) 中的 `VisEdit-Contrib-Pre-Alt` 候选层，对除 BLIP2 外的 6 个模型继续做 pilot500 真实扫层实验。

BLIP2-OPT-2.7B 的 pilot500 候选层扫层已经完成，因此本手册默认不重跑 BLIP2；如果后续发现 BLIP2 某个候选层缺结果，再单独补跑。

---

## 1. 实验边界

只做以下定位方法对应的真实编辑验证：

```text
VisEdit-Contrib-Pre-Alt
```

本实验不重新计算贡献度，不训练文本 adapter，不做 MMKE，不做其他定位方法。

训练数据：

```text
EVQA-pilot500 train
```

评测数据建议同时保留两套：

```text
EVQA-pilot500 eval/test
full E-VQA eval/test
```

其中 pilot500 eval/test 用于快速检查训练是否有效；full E-VQA eval/test 用于和 BLIP2 已有结果保持可比。

---

## 2. 服务器与数据路径

服务器项目目录：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
```

pilot500 数据目录：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528
```

训练 JSON：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/data/vqa_train_proxy500.json
```

eval500 JSON：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/data/vqa_eval_proxy500.json
```

pilot500 图片目录：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/images
```

full E-VQA eval JSON：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/vqa/vqa_eval.json
```

full E-VQA 图片目录：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images
```

输出根目录建议：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/visedit_pre_alt_pilot500_6models_YYYYMMDD_HHMM
```

GPU 调度原则：

- 优先使用 G08。
- 不打断 G07 上已有训练任务。
- 每次提交前检查 `squeue`，确认不会抢占正在跑的关键任务。

---

## 3. 模型与候选层

候选层来自 `EVQA-pilot500` 的 `alt` 关键 token 贡献度结果，按 VisEdit-Contrib-Pre 规则生成：

```text
Top-K = {s_H - 1, s_H - 2, ..., s_H - K}
```

其中 `s_H` 是高贡献区间起始层。真实扫层以 Top-5 为完整候选集合，Top-3 是低预算统计子集。

| Model | 高贡献区间 | Top-3 | Top-5，本实验训练层 |
|---|---|---|---|
| InstructBLIP-Vicuna-7B | L29-L31 | L28,L27,L26 | L28,L27,L26,L25,L24 |
| MiniGPT-4-Vicuna-7B | L27-L31 | L26,L25,L24 | L26,L25,L24,L23,L22 |
| LLaVA-v1.5-7B | L29-L31 | L28,L27,L26 | L28,L27,L26,L25,L24 |
| Qwen2.5-VL-3B | L30-L35 | L29,L28,L27 | L29,L28,L27,L26,L25 |
| PaliGemma-3B | L13-L16 | L12,L11,L10 | L12,L11,L10,L9,L8 |
| SmolVLM-Instruct-1.7B | L18-L23 | L17,L16,L15 | L17,L16,L15,L14,L13 |

BLIP2 参考，不默认重跑：

| Model | 高贡献区间 | Top-3 | Top-5 |
|---|---|---|---|
| BLIP2-OPT-2.7B | L21-L29 | L20,L19,L18 | L20,L19,L18,L17,L16 |

---

## 4. 训练配置

| 配置项 | 值 |
|---|---|
| Method | `VisEdit-Contrib-Pre-Alt` |
| Dataset | `EVQA-pilot500` |
| Adapter | visual-only VisEdit / VEAD |
| Epochs per layer | `50` |
| Batch size | 默认 `2`，若模型显存允许可记录实际值，但同一模型内部必须一致 |
| Checkpoint save | 每个 epoch 至少保存可选 checkpoint 或记录足够选择 best EMA |
| Checkpoint selection | 每层单独选择 minimum EMA loss checkpoint |
| Evaluation | 每层独立进程评测 |
| Final metrics | `Rel / T-Gen / M-Gen / T-Loc / M-Loc / Average` |

如果某模型在 `bs=2` 下 OOM，先不要改已有层结果；记录 OOM 层和显存，再单独决定是否对该模型统一降 batch 或跳过 adapter 训练。

Qwen2.5-VL 额外要求：

- 固定输入分辨率，例如 `448x448`。
- 记录 visual token 数量和 `visual_token_start/end`。
- 同一模型所有候选层必须使用同一分辨率策略。

---

## 5. 严格禁止混层

这是本实验最重要的执行约束。

每个候选层必须是完全独立训练：

1. 换层时必须重新初始化 adapter。
2. 换层时不能加载上一层或其他层保存的 adapter checkpoint。
3. 不能使用 `resume_from_checkpoint` 指向其他 layer 的目录。
4. 不能把多个层训练写入同一个 adapter 输出目录。
5. 每个 layer 的 checkpoint 内部 adapter key 必须对应当前 layer。
6. 每个 layer 的训练日志必须记录当前 layer 的 hook path。
7. 每个 layer 评测时必须重新加载 base model，并只加载当前 layer 的 selected checkpoint。

推荐目录结构：

```text
{RUN_ROOT}/
  instructblip-vicuna-7b/
    L28/
      train.log
      checkpoints/
      selected_checkpoint.json
      eval_proxy500.json
      eval_fullevqa.json
    L27/
    ...
  minigpt-4-vicuna-7b/
  llava-v1.5-7b/
  qwen2.5-vl-3b/
  paligemma-3b/
  smolvlm-1.7b/
```

禁止目录结构：

```text
{RUN_ROOT}/{model}/shared_adapter/
{RUN_ROOT}/{model}/latest/
{RUN_ROOT}/{model}/resume/
```

除非这些目录只是软链接到当前 layer 的 checkpoint，并且日志中明确记录目标路径。

---

## 6. 执行顺序

默认按以下顺序继续 BLIP2 之后的实验：

```text
1. InstructBLIP-Vicuna-7B: L28,L27,L26,L25,L24
2. MiniGPT-4-Vicuna-7B: L26,L25,L24,L23,L22
3. LLaVA-v1.5-7B: L28,L27,L26,L25,L24
4. Qwen2.5-VL-3B: L29,L28,L27,L26,L25
5. PaliGemma-3B: L12,L11,L10,L9,L8
6. SmolVLM-Instruct-1.7B: L17,L16,L15,L14,L13
```

如果资源有限，每个模型先跑 Top-3：

```text
Top-3 -> 评测 -> 检查是否有训练/评测异常 -> 再补 Top-5 剩余两层
```

如果资源允许，直接跑 Top-5，但每层仍必须独立训练、独立评测。

---

## 7. 训练前检查清单

每个模型启动前检查：

- 模型目录存在。
- tokenizer / processor 能正常加载。
- pilot500 train/eval JSON 存在。
- 图片路径能解析。
- 当前模型的 candidate layer 与模型层数匹配。
- adapter hook path 和候选层编号一致。
- 输出目录为空或只包含当前本次 run 的文件。
- Slurm 脚本没有复用其他模型或其他层的 adapter path。
- `resume` 参数为空。

每个 layer 启动前检查：

```text
MODEL_NAME
LAYER_ID
RUN_ROOT
LAYER_OUTPUT_DIR
TRAIN_JSON
IMAGE_ROOT
EPOCHS=50
BATCH_SIZE
RESUME_FROM_CHECKPOINT=None
```

---

## 8. 训练完成后检查

每层训练结束后必须产出：

```text
train.log
loss_curve.csv
checkpoint manifest
selected_checkpoint.json
```

`selected_checkpoint.json` 至少记录：

```json
{
  "model": "llava-v1.5-7b",
  "layer": 28,
  "selection_rule": "min_ema_loss",
  "selected_epoch": 49,
  "selected_checkpoint": ".../L28/checkpoints/epoch_49.pt",
  "ema_loss": 0.0,
  "raw_loss": 0.0,
  "adapter_key_check": "must_contain_layer_28"
}
```

如果某层 50 epoch 内 loss 完全不下降，仍保留日志和 checkpoint manifest，但结果表中标记为 `not_converged`，不要把它静默删除。

---

## 9. 评测隔离要求

每个 layer 评测必须独立 Python 进程：

1. 重新加载 base model。
2. 重新注册当前 layer adapter hook。
3. 只加载当前 layer 的 selected checkpoint。
4. 评测结束后释放模型、adapter、hook、CUDA cache。

严禁在同一个 Python 进程里连续评测多个 layer，除非脚本已经显式验证 wrapper rebind 和 hook cleanup。

如果多个 layer 的 `Rel / T-Gen / M-Gen / T-Loc / M-Loc / Average` 完全一致，先判定为疑似 stale hook / stale wrapper / stale checkpoint，不直接解释为真实模型现象。

---

## 10. 汇总表模板

每个模型一张训练表：

| Model | Layer | Epochs | Best epoch | Raw loss | EMA loss | Status | Checkpoint |
|---|---:|---:|---:|---:|---:|---|---|
| InstructBLIP-Vicuna-7B | 28 | 50 | - | - | - | pending | - |

每个模型一张评测表：

| Model | Layer | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Eval set | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| InstructBLIP-Vicuna-7B | 28 | - | - | - | - | - | - | full E-VQA | pending |

定位方法比较表：

| Model | Method | Top-3 | Best@3 Avg | Top-5 | Best@5 Avg | Best layer in Top-5 |
|---|---|---|---:|---|---:|---:|
| InstructBLIP-Vicuna-7B | VisEdit-Contrib-Pre-Alt | L28,L27,L26 | - | L28,L27,L26,L25,L24 | - | - |

---

## 11. 本地回收结果

服务器训练完成后，把结果拉回本地：

```text
downloads/visedit_pre_alt_pilot500_6models/visedit_pre_alt_pilot500_6models_YYYYMMDD_HHMM
```

本地至少保留：

```text
summary.csv
summary.json
per_model/*.csv
per_model/*.json
loss_curves/*.csv
eval_logs/*.log
selected_checkpoints_manifest.csv
```

大体积 checkpoint 可只保留 manifest 和服务器路径，不默认全部拉回本地。

---

## 12. 通过/暂停标准

可以继续下一个模型的条件：

- 当前模型 Top-3 至少有 2 层训练成功并完成评测。
- 每层 checkpoint key 与 layer id 一致。
- 评测指标不是多层完全重复。
- 日志中没有加载其他层 adapter 的记录。

需要暂停排查的条件：

- 当前 layer 训练日志显示加载了其他 layer checkpoint。
- 多个 layer 指标完全一致。
- checkpoint 内部 adapter key 与当前 layer 不一致。
- hook path 不包含当前 layer id。
- loss 曲线全程 NaN/Inf。
- Qwen2.5-VL 的视觉 token 范围随样本变化但未固定分辨率。

