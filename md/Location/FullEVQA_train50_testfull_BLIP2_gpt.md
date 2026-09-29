# CrossModel CrossDataset Visual GoldenLayer Localization 实验二：BLIP2 Full E-VQA Train

## 0. 审核状态

本手册用于审核，当前不启动训练。

实验二只改变训练数据规模：把 `pilot500` 训练集替换为 full E-VQA 训练集；其余训练、checkpoint 选择、评测、loss 曲线和结果回填方式保持与 `pilot500` 修正版一致。

原始手册不修改：

```text
md/Location/CrossModel_CrossDataset_Visual_GoldenLayer_Localization_实验计划_gpt.md
```

审核通过后，按本手册连接服务器执行实验，并把训练 loss、选用 checkpoint、full E-VQA 评测结果追加回本文件。

---

## 1. 实验目的

本实验验证：在 BLIP2-OPT-2.7B 上，使用 full E-VQA train 训练 visual-only VisEdit adapter 后，`L0/L5/L10/L15/L19/L25/L30` 七个候选层的真实性能排序是否更接近 VisEdit 论文中的 full-train 结论。

重点回答三个问题：

- `pilot500` 训练得到的层排序是否只是小数据现象。
- full E-VQA train 是否能恢复论文中 `L19` 最优或接近最优的趋势。
- request-only 视觉梯度定位推荐层与 full-train 真实高性能层是否一致。

本实验不是重新计算 LGA，也不是训练文本 adapter；只做 BLIP2 visual-only VisEdit adapter 的 full-train 层验证。

---

## 2. 与 pilot500 实验的唯一区别

| 项目 | pilot500 修正版 | 实验二 full E-VQA train |
|---|---|---|
| 模型 | BLIP2-OPT-2.7B | BLIP2-OPT-2.7B |
| adapter | visual-only VisEdit / VEAD | visual-only VisEdit / VEAD |
| 层集合 | `0,5,10,15,19,25,30` | `0,5,10,15,19,25,30` |
| batch size | `2` | `2` |
| epoch | `50` | `50` |
| checkpoint 选择 | 每层最小 EMA loss | 每层最小 EMA loss |
| 评测集 | full E-VQA eval/test | full E-VQA eval/test |
| 训练集 | `vqa_train_proxy500.json` | full `vqa_train.json` |
| 图片根目录 | proxy images | full E-VQA images |

除训练数据路径和输出命名外，其余逻辑保持一致。

---

## 3. 数据与模型路径

服务器项目目录：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main
```

模型路径：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/models/blip2-opt-2.7b
```

训练数据：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/vqa/vqa_train.json
```

训练样本数：

```text
6345
```

评测数据：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/vqa/vqa_eval.json
```

评测样本数：

```text
2093
```

图片根目录：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images
```

输出目录建议：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/cross_dataset_visual_layer_localization/blip2_fullevqa_train_visedit_sweep_YYYYMMDD_HHMM
```

---

## 4. 训练配置

| 配置项 | 值 |
|---|---|
| Model | `blip2-opt-2.7b` |
| Editor | visual-only VisEdit / VEAD |
| Layers | `0,5,10,15,19,25,30` |
| Epochs per layer | `50` |
| Batch size | `2` |
| LR / optimizer | 沿用 `configs/vead/blip2-opt-2.7b.yaml` 与 pilot500 修正版脚本 |
| Save interval | 每 epoch 保存一次 checkpoint |
| Checkpoint selection | 每层选择 EMA loss 最小 checkpoint |
| Checkpoint cleanup | 保留 EMA loss TopK、raw loss TopK、last K，其余自动清理 |
| Evaluation | 所有层训练完成后，逐层独立进程评测 full E-VQA eval/test |

---

## 5. 层集合与论文参考

本实验固定扫描论文表中 BLIP2-OPT-2.7B 的七个代表层：

```text
L0, L5, L10, L15, L19, L25, L30
```

VisEdit 论文 full-train 参考值：

| Layer | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 95.10 | 93.70 | 94.43 | 100.00 | 84.51 | 93.55 |
| 5 | 95.16 | 94.63 | 94.49 | 100.00 | 86.51 | 94.16 |
| 10 | 96.36 | 95.79 | 95.60 | 100.00 | 85.83 | 94.72 |
| 15 | 97.69 | 97.48 | 97.08 | 100.00 | 92.20 | 96.89 |
| 19 | 98.83 | 98.63 | 97.90 | 100.00 | 92.30 | 97.53 |
| 25 | 97.54 | 96.97 | 95.87 | 100.00 | 88.83 | 95.80 |
| 30 | 86.22 | 84.18 | 83.62 | 100.00 | 85.98 | 88.00 |

预期：如果 full-train 复现成功，`L19` 应该是本组七层中 Average 最高或接近最高的层。

---

## 6. 执行前脚本要求

不能直接覆盖 pilot500 脚本。审核通过后，在服务器上复制一个 full-train 专用脚本：

```text
scripts/run_evqa_pilot500_blip2_visedit_sweep.py
-> scripts/run_evqa_fullevqa_blip2_visedit_sweep.py
```

full-train 脚本需要做以下命名修正，避免输出里继续写 `pilot500`：

- `train_name_prefix` 改为 `fullevqa_blip2_visedit_L{layer:02d}`。
- `eval_name` 改为 `EVQA_full_test_fullevqa_blip2_visedit_L{layer:02d}`。
- loss 图标题改为 `BLIP2 VisEdit full E-VQA train loss`。
- outcome md 章节名改为 `fullevqa-blip2-visedit-sweep-outcome`。
- 输出文件名改为 `fullevqa-blip2-visedit-sweep-outcome.md`。

必须保留 pilot500 修正版中的安全修复：

- `VEAD.init_wrap_get_llm_outpt()` 必须能绑定当前 editor，不能复用 stale wrapper。
- visual adapter 打开但缺少 `vt_range / set_input_info()` 时必须直接报错，不能静默跳过。
- checkpoint 保存过多导致磁盘压力时，自动清理非 selected / 非 top checkpoint。

---

## 7. 强制隔离规则

为避免再次出现 stale wrapper / stale checkpoint，本实验训练和评测都采用逐层独立进程。

训练规则：

- 每个 layer 单独启动一个 Python 进程。
- 每个 layer 重新 load base model。
- 每个 layer 重新创建当前 layer 的 VEAD editor。
- 每个 layer 训练结束后释放模型、hook、CUDA cache。
- 全部 7 层训练结束后，再统一进入评测阶段。

评测规则：

- 每个 layer 单独启动一个 Python 进程。
- 每个 eval 进程重新 load base model。
- 每个 eval 进程只 load 当前 layer 的 selected checkpoint。
- 每个 eval 进程重新注册当前 layer hook / wrapper。
- 若多个层评测结果完全一致，优先怀疑 eval stale checkpoint / stale wrapper，不直接解释为模型现象。

---

## 8. 审核通过后的训练命令模板

以下命令只作为审核后的执行模板，当前不运行。

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main

OUT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/cross_dataset_visual_layer_localization/blip2_fullevqa_train_visedit_sweep_$(date +%Y%m%d_%H%M)
TRAIN_DATA=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/vqa/vqa_train.json
EVAL_DATA=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/vqa/vqa_eval.json
IMG_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images
LAYERS="0 5 10 15 19 25 30"

mkdir -p "$OUT/logs"

for L in $LAYERS; do
  echo "[train] layer=$L"
  CUDA_VISIBLE_DEVICES=0 python scripts/run_evqa_fullevqa_blip2_visedit_sweep.py \
    --out-root "$OUT" \
    --layers "$L" \
    --epochs 50 \
    --batch-size 2 \
    --model-name blip2-opt-2.7b \
    --train-data "$TRAIN_DATA" \
    --train-img-root "$IMG_ROOT" \
    --eval-data "$EVAL_DATA" \
    --eval-img-root "$IMG_ROOT" \
    --skip-eval \
    2>&1 | tee "$OUT/logs/train_layer_${L}.log"
done
```

训练阶段完成标志：

```text
layer_00/selected_checkpoint.tsv
layer_05/selected_checkpoint.tsv
layer_10/selected_checkpoint.tsv
layer_15/selected_checkpoint.tsv
layer_19/selected_checkpoint.tsv
layer_25/selected_checkpoint.tsv
layer_30/selected_checkpoint.tsv
```

---

## 9. 审核通过后的评测命令模板

全部训练完成后再评测：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main

TRAIN_DATA=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/vqa/vqa_train.json
EVAL_DATA=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/vqa/vqa_eval.json
IMG_ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/data/easy-edit-mm/images
LAYERS="0 5 10 15 19 25 30"

for L in $LAYERS; do
  echo "[eval] layer=$L"
  CUDA_VISIBLE_DEVICES=0 python scripts/run_evqa_fullevqa_blip2_visedit_sweep.py \
    --out-root "$OUT" \
    --layers "$L" \
    --epochs 50 \
    --batch-size 2 \
    --model-name blip2-opt-2.7b \
    --train-data "$TRAIN_DATA" \
    --train-img-root "$IMG_ROOT" \
    --eval-data "$EVAL_DATA" \
    --eval-img-root "$IMG_ROOT" \
    --skip-train \
    --overwrite-eval \
    2>&1 | tee "$OUT/logs/eval_layer_${L}.log"
done

python scripts/run_evqa_fullevqa_blip2_visedit_sweep.py \
  --out-root "$OUT" \
  --layers "0,5,10,15,19,25,30" \
  --epochs 50 \
  --batch-size 2 \
  --model-name blip2-opt-2.7b \
  --train-data "$TRAIN_DATA" \
  --train-img-root "$IMG_ROOT" \
  --eval-data "$EVAL_DATA" \
  --eval-img-root "$IMG_ROOT" \
  --skip-train \
  --skip-eval
```

评测阶段完成标志：

```text
layer_00/eval_full.done
layer_05/eval_full.done
layer_10/eval_full.done
layer_15/eval_full.done
layer_19/eval_full.done
layer_25/eval_full.done
layer_30/eval_full.done
full_eval_results.csv
fullevqa-blip2-visedit-sweep-outcome.md
```

---

## 10. 结果回填模板

### fullevqa-blip2-visedit-sweep-outcome

#### 10.1 Selected Checkpoints

| Layer | ckpt | epoch | step | raw loss | EMA loss | 判断 |
|---:|---|---:|---:|---:|---:|---|
| L0 |  |  |  |  |  |  |
| L5 |  |  |  |  |  |  |
| L10 |  |  |  |  |  |  |
| L15 |  |  |  |  |  |  |
| L19 |  |  |  |  |  |  |
| L25 |  |  |  |  |  |  |
| L30 |  |  |  |  |  |  |

#### 10.2 Full E-VQA Evaluation

| Layer | ckpt epoch | EMA loss | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Paper Average | Delta |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| L0 |  |  |  |  |  |  |  |  | 93.55 |  |
| L5 |  |  |  |  |  |  |  |  | 94.16 |  |
| L10 |  |  |  |  |  |  |  |  | 94.72 |  |
| L15 |  |  |  |  |  |  |  |  | 96.89 |  |
| L19 |  |  |  |  |  |  |  |  | 97.53 |  |
| L25 |  |  |  |  |  |  |  |  | 95.80 |  |
| L30 |  |  |  |  |  |  |  |  | 88.00 |  |

#### 10.3 Loss Curve

训练完成后回填：

```text
loss_curves_all_layers.png
loss_history_all_layers.csv
```

#### 10.4 分析要点

- 若 `L19` 为 Average 最优或接近最优，说明 pilot500 的偏差主要来自训练集规模不足，full-train 恢复论文趋势。
- 若 `L10/L15/L19` 明显优于 `L0`，说明中层视觉编辑位置比浅层更适合 BLIP2 full E-VQA。
- 若 `L0` 仍然最优，需要优先排查 full-train 脚本是否仍有 stale wrapper / eval loading 问题，再考虑与论文实现差异。
- 将本实验 full-train 真实排序与 BLIP2 request-only 视觉 LGA 排序做 Hit@1、Hit@3、RankOfBest、Regret@3 对齐分析。

---

## 11. 启动前检查清单

- [ ] 确认 `vqa_train.json` 样本数为 `6345`。
- [ ] 确认 `vqa_eval.json` 样本数为 `2093`。
- [ ] 确认图片根目录为 full E-VQA images，不是 proxy images。
- [ ] 确认脚本名为 `run_evqa_fullevqa_blip2_visedit_sweep.py`，不覆盖 pilot500 脚本。
- [ ] 确认输出目录包含 `fullevqa_train` 或 `fullevqa` 字段。
- [ ] 确认每层训练单独 Python 进程。
- [ ] 确认每层评测单独 Python 进程。
- [ ] 确认 checkpoint 按 EMA loss 最小选择。
- [ ] 确认保存过多 checkpoint 时自动清理非必要 checkpoint。
- [ ] 确认所有训练结束后再统一评测。
- [ ] 确认结果回填到本文件，不写回原始总手册。

---

## 12. L19/L17/L18 full E-VQA 补评与汇总结果

更新时间：2026-06-12。

远端输出目录：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/cross_dataset_visual_layer_localization/blip2_fullevqa_train50_testfull_L19_L17_L18_20260604_234559
```

说明：
- L19 是此前已完成的 full E-VQA 评测结果。
- L17、L18 于 2026-06-12 补跑 full E-VQA eval/test 评测。
- 评测数据为 full `vqa_eval.json`，共 `2093` 个样本。
- checkpoint 选择规则为每层 minimum EMA loss。
- `full_eval_results.csv` 已重新聚合为 L17/L18/L19 三行；同时保留备份 `full_eval_results_L17_L18_L19_combined.csv`。

### 12.1 Selected Checkpoints

| Layer | ckpt | epoch | step | raw loss | EMA loss | 判断 |
|---:|---|---:|---:|---:|---:|---|
| L17 | `epoch-46-i-145958-ema_loss-0.3239` | 46 | 145958 | 0.384464 | 0.323929 | done |
| L18 | `epoch-50-i-158650-ema_loss-0.3016` | 50 | 158650 | 0.261427 | 0.301585 | done |
| L19 | `epoch-49-i-155477-ema_loss-0.3477` | 49 | 155477 | 0.385825 | 0.347696 | done |

### 12.2 Full E-VQA Evaluation

| Layer | ckpt epoch | EMA loss | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Paper Average | Delta |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| L17 | 46 | 0.323929 | 97.87 | 97.36 | 97.77 | 100.00 | 90.62 | 96.72 |  |  |
| L18 | 50 | 0.301585 | 97.86 | 97.44 | 97.76 | 100.00 | 92.72 | 97.16 |  |  |
| L19 | 49 | 0.347696 | 97.38 | 96.85 | 97.41 | 100.00 | 89.16 | 96.16 | 97.53 | -1.37 |

### 12.3 当前结论

当前已完成的 full E-VQA train50 层中，`L18` 的 Average 最高，为 `97.16`；`L17` 为 `96.72`，`L19` 为 `96.16`。三层整体都接近 VisEdit 论文中 BLIP2 L19 的 full-train 结果，但本次 train50 复现里 L18 暂时优于 L19。


