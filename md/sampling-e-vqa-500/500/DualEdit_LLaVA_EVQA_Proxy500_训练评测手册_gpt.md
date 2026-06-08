# DualEdit LLaVA E-VQA Proxy500 训练评测手册

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 LLaVA-v1.5-7B 上复现 DualEdit 的视觉 adapter + 文本 adapter 联合训练，用 E-VQA proxy 训练集 500 条、验证集 500 条完成小规模复现实验。

**Architecture:** 同时比较两组 DualEdit 挂载位置：组合 A 为视觉 adapter `layers[19]` + 文本 adapter `layers[16]`，组合 B 为视觉 adapter `layers[6]` + 文本 adapter `layers[18]`。每个组合内 visual/text adapter 共同参与 `rel + gen + loc` 损失反传；两个组合都训练完成后，再分别选择各自最小 loss checkpoint，最后统一评测。测试时开启余弦相似度门控，LLaVA 使用阈值 `tau=0.6`。实验只使用 proxy 子集和 proxy 图片目录，不修改原始 E-VQA 数据集。

**Tech Stack:** DualEdit-main, PyTorch, HuggingFace Transformers, LLaVA-v1.5-7B, E-VQA proxy500, Adam, fp16/bf16, Markdown/CSV/JSON result logging.

---

## 1. 实验目标

本实验复现的是 **DualEdit**，不是 VisEdit 作者的“仅视觉表征编辑”版本。

必须保留：

- Visual adapter：编辑视觉 token 表征。
- Text adapter：编辑文本 token 表征。
- 两类 adapter 一起训练。
- 测试阶段开启 cosine-similarity gating。

本实验只做 proxy 规模：

| 项目 | 设置 |
|---|---:|
| train samples | 500 |
| val samples | 500 |
| train source | E-VQA proxy train |
| eval source | E-VQA proxy eval |
| backbone | LLaVA-v1.5-7B |
| adapter combinations | A: text `layers[16]` + visual `layers[19]`; B: text `layers[18]` + visual `layers[6]` |
| batch size | 4 |
| max steps | 4000 |
| fallback max steps | 6000 |
| checkpoint interval | 200 steps，必要时改 100 steps |
| eval strategy | 训练完成后统一评测 |
| learning rate | `1e-4` |
| precision | fp16 或 bf16 |
| optimizer | Adam |
| LLaVA gating threshold | `tau=0.6` |

层号说明：

| 论文/代码写法 | Python/HF 索引 | 如果按中文“第几层”从 1 开始数 |
|---|---|---|
| Text layer = 16 | `layers[16]` | 第 17 个 Transformer block |
| Visual layer = 19 | `layers[19]` | 第 20 个 Transformer block |
| Text layer = 18 | `layers[18]` | 第 19 个 Transformer block |
| Visual layer = 6 | `layers[6]` | 第 7 个 Transformer block |

本次比较的两个组合：

| 组合 | Text adapter | Visual adapter | 说明 |
|---|---|---|---|
| A | `layers[16]` | `layers[19]` | 作者推荐/默认 DualEdit 组合 |
| B | `layers[18]` | `layers[6]` | 新增对照组合 |

---

## 2. 数据路径

服务器 proxy 数据目录：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528
```

训练 JSON：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/data/vqa_train_proxy500.json
```

验证 JSON：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/data/vqa_eval_proxy500.json
```

合并 JSON，仅用于检查或调试，不作为训练输入：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/data/vqa_proxy_train500_eval500.json
```

proxy 图片根目录：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/images
```

JSON 里的 `image`、`image_rephrase`、`m_loc` 已经加了 `proxy/` 前缀，因此 loader 应当用上面的 `images` 作为图片根目录。例如：

```json
"image": "proxy/val2014/COCO_val2014_000000262197.jpg"
```

已校验：

| 文件 | 数量 | 图片路径前缀 | 缺失图片 |
|---|---:|---:|---:|
| `vqa_train_proxy500.json` | 500 | 500/500 | 0 |
| `vqa_eval_proxy500.json` | 500 | 500/500 | 0 |
| `vqa_proxy_train500_eval500.json` | 1000 | 1000/1000 | 0 |

---

## 3. 模型与代码路径

服务器 DualEdit 目录：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/DualEdit-main
```

服务器 LLaVA 模型目录：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/models/llava-v1.5-7b-hf
```

当前服务器 `DualEdit-main/utils/GLOBAL.py` 中 LLaVA 权重路径已经指向：

```python
model_path_map = {
    "llava-v1.5-7b": "/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/models/llava-v1.5-7b-hf",
}
```

注意：服务器 `ROOT_PATH = 'DualEdit-main'`，因此推荐从父目录运行：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2
```

不要直接在 `DualEdit-main` 目录里运行原始命令，否则相对路径可能解析成 `DualEdit-main/DualEdit-main/...`。

---

## 4. 当前代码与复现要求的差异

本地/服务器 DualEdit 代码已有视觉 + 文本 adapter 联合训练能力，但要严格按本实验复现 proxy 版本，需要对齐下面几点。

| 项目 | 当前代码状态 | 本实验要求 | 处理方式 |
|---|---|---|---|
| 训练数据路径 | `dualedit_train.py` 硬编码原始 `vqa_train.json` | 使用 proxy train 500 | 给训练入口新增 `--data_path` 与 `--img_root_dir` |
| 评测数据路径 | `dualedit_test.py` 硬编码原始 `vqa_eval.json` | 使用 proxy eval 500 | 给评测入口新增 `--data_path` 与 `--img_root_dir` |
| Visual adapter | 支持 `edit_layers` | 组合 A `edit_layers: [19]`；组合 B `edit_layers: [6]` | 为两个组合分别新建 proxy yaml |
| Text adapter | 支持 `edit_text_layers` | 组合 A `edit_text_layers: [16]`；组合 B `edit_text_layers: [18]` | 为两个组合分别新建 proxy yaml |
| optimizer | 当前 `Adam` | 原始 DualEdit 代码使用 `Adam` | 保持 Adam，不改 AdamW |
| gating threshold | 代码常量 `0.8` | LLaVA 用 `0.6` | 参数化或在 proxy 实验中设为 `0.6` |
| max steps | 原脚本按 epochs | 4000 steps | 500/4=125 step/epoch，因此主实验用 32 epochs |
| eval strategy | 原脚本可直接评测指定 checkpoint | 训练完成后统一评测 | 先从 `records/.../checkpoints` 选择最小 loss checkpoint，再评测一次 |

说明：

- 训练阶段门控关闭，阈值只影响评测/测试阶段。
- 当前代码训练 locality loss 时会跳过 `image=None` 的 `text_loc`，实际训练的 locality 是 `image_loc` KL；`text_loc` 仍用于评测指标。
- 如果不做上述路径参数改造，命令会错误地跑全量原始 E-VQA，而不是 proxy500。

---

## 5. Proxy YAML 配置

建议新建两个服务器配置，分别对应两个挂载组合。

组合 A 配置：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/DualEdit-main/configs/vead/llava-v1.5-7b-evqa-proxy500-dualedit-l19-t16.yaml
```

组合 A 配置内容：

```yaml
edit_model_name: "llava-v1.5-7b"
llm_hidden_size: 4096
adaptor_mid_dim: 1024
adaptor_cross_att_head_n: 8
llm_layer_tmp: "language_model.model.layers.{}"
llm_att_tmp: "language_model.model.layers.{}.self_attn"

edit_layers: [19]
edit_text_layers: [16]

train_cfg:
  lr: 1.e-4
  rel_lambda: 1
  gen_lambda: 1
  loc_lambda: 1
  inf_mapper_lambda: 0.1

IT:
  add_it: false
  layers: [20,21,22,23,24,25,26,27,28,29,30]
  test_n: 1
  noise_level: 0.7
  window: 0
  vt_sample_n: 24
  mid_dim: 1024
```

组合 B 配置：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/DualEdit-main/configs/vead/llava-v1.5-7b-evqa-proxy500-dualedit-l6-t18.yaml
```

组合 B 配置内容：

```yaml
edit_model_name: "llava-v1.5-7b"
llm_hidden_size: 4096
adaptor_mid_dim: 1024
adaptor_cross_att_head_n: 8
llm_layer_tmp: "language_model.model.layers.{}"
llm_att_tmp: "language_model.model.layers.{}.self_attn"

edit_layers: [6]
edit_text_layers: [18]

train_cfg:
  lr: 1.e-4
  rel_lambda: 1
  gen_lambda: 1
  loc_lambda: 1
  inf_mapper_lambda: 0.1

IT:
  add_it: false
  layers: [20,21,22,23,24,25,26,27,28,29,30]
  test_n: 1
  noise_level: 0.7
  window: 0
  vt_sample_n: 24
  mid_dim: 1024
```

本实验不打开 `IT.add_it`，因为这里复现重点是 DualEdit 的 visual/text dual adapter 与 gating，而不是额外 influence mapper ablation。

---

## 6. 必要代码对齐

### 6.1 数据路径参数

给 `dualedit_train.py` 增加：

```python
parser.add_argument("--data_path", type=str, default=None)
parser.add_argument("--img_root_dir", type=str, default=None)
parser.add_argument("--max_steps", type=int, default=None)
```

训练数据加载处改成：

```python
data_path = cfg.data_path or os.path.join(ROOT_PATH, "data/easy-edit-mm/vqa/vqa_train.json")
img_root_dir = cfg.img_root_dir or os.path.join(ROOT_PATH, "data/easy-edit-mm/images")
train_data = EVQA(data_path, img_root_dir, cfg.data_n)
```

给 `dualedit_test.py` 增加：

```python
parser.add_argument("--data_path", type=str, default=None)
parser.add_argument("--img_root_dir", type=str, default=None)
```

评测数据加载处改成：

```python
data_path = cfg.data_path or os.path.join(ROOT_PATH, "data/easy-edit-mm/vqa/vqa_eval.json")
img_root_dir = cfg.img_root_dir or os.path.join(ROOT_PATH, "data/easy-edit-mm/images")
eval_data = EVQA(data_path, img_root_dir, cfg.data_sample_n)
```

### 6.2 Optimizer

原始 DualEdit 代码使用 `torch.optim.Adam`，不是 AdamW。为了保持和原始论文/官方代码一致，本 proxy 复现实验不修改 optimizer。

当前实现位于：

```text
DualEdit-main/editor/vllm_editors/vead/vead.py
```

对应代码：

```python
from torch.optim import Adam

def get_a_new_optimizer(self):
    para_lr = [
        {"params": adaptor.parameters(), "lr": self.cfg.train_cfg.lr}
        for adaptor in self.adaptors.values()
    ]
    return Adam(para_lr)
```

### 6.3 LLaVA gating threshold

当前阈值在：

```text
DualEdit-main/editor/vllm_editors/vead/adpt_model.py
```

当前代码：

```python
THREHSHOLD = 0.8
```

LLaVA proxy 实验应设为：

```python
THREHSHOLD = 0.6
```

建议后续把这个阈值参数化到 yaml，例如：

```yaml
gating:
  threshold: 0.6
```

首轮 proxy 复现实验可以先用最小改动保证结果可跑。

### 6.4 评测时 gating 开关

为了分析 adapter 本身与完整 DualEdit 机制，需要支持评测时显式控制 gating。

每个被选中的 checkpoint 都做两次评测：

| 评测方式 | 目的 |
|---|---|
| w/o gating | 看 adapter 插入层本身的编辑效果和副作用 |
| w/ gating, `tau=0.6` | 看完整 DualEdit 设置下 locality 是否被保护 |

当前代码中 `set_train(False)` 会把 `open_gating=True`，因此常规测试默认是 w/ gating。若要做 w/o gating，需要在评测入口加载 checkpoint 后，把所有 adapter 的 `open_gating` 设为 `False`；w/ gating 则设为 `True` 且阈值为 `0.6`。

建议给 `dualedit_test.py` 增加参数：

```python
parser.add_argument("--gating_mode", choices=["on", "off"], default="on")
parser.add_argument("--gating_threshold", type=float, default=0.6)
```

并在加载 editor 后设置：

```python
from editor.vllm_editors.vead import adpt_model

adpt_model.THREHSHOLD = float(cfg.gating_threshold)
for adaptor in editor.adaptors.values():
    if hasattr(adaptor, "open_gating"):
        adaptor.open_gating = (cfg.gating_mode == "on")
```

注意：训练阶段仍然关闭 gating；这里的开关只用于评测。

---

## 7. 训练计划

500 条训练样本，batch size 4：

```text
steps_per_epoch = ceil(500 / 4) = 125
4000 steps = 32 epochs
6000 steps = 48 epochs
```

主实验：

```text
32 epochs ~= 4000 steps
```

保险实验：

```text
48 epochs ~= 6000 steps
```

checkpoint 策略：

- 推荐每 200 steps 保存一次。
- 如果需要更细 loss 曲线，改成每 100 steps。
- 训练期间不做评测，不用 watcher 每隔 200 steps 评测。
- 训练结束后，从 `records/.../checkpoints` 中按 checkpoint 文件名或 checkpoint metadata 选择 **loss 最小** 的 checkpoint。
- checkpoint 文件名格式通常为 `epoch-<epoch>-i-<step>-ema_loss-<loss>`；若文件名包含 `ema_loss`，以 `ema_loss` 为选择依据。
- 若存在相同最小 loss，选择 step 更大的 checkpoint。
- 训练完成后保留：
  - 最小 loss checkpoint。
  - 最终 checkpoint。
  - `checkpoint_loss_ranking.tsv`。
  - 评测结果写入 manifest 后，其余 checkpoint 可清理，避免磁盘满。

---

## 8. 训练命令

两个组合都需要训练完成后，才能进入统一评测阶段。推荐顺序：

1. 先训练组合 A：text L16 + visual L19。
2. 再训练组合 B：text L18 + visual L6。
3. 两个组合都完成后，分别选择各自最小 loss checkpoint。
4. 最后统一对两个最小 loss checkpoint 跑 proxy eval 500。

组合 A 单卡训练命令：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2
conda activate dualedit

CUDA_VISIBLE_DEVICES=0 python DualEdit-main/dualedit_train.py \
  -mn llava \
  -dna EVQA \
  -bs 4 \
  -dvc "cuda:0" \
  -edvc 0 \
  -eps 32 \
  -sci 200 \
  -lpi 10 \
  -ea 0.1 \
  -rs 20260528 \
  -tnp dualedit_llava_evqa_proxy500_A_t16_v19_s4000 \
  -cp configs/vead/llava-v1.5-7b-evqa-proxy500-dualedit-l19-t16.yaml \
  --data_path /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/data/vqa_train_proxy500.json \
  --img_root_dir /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/images \
  --max_steps 4000
```

组合 B 单卡训练命令：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2
conda activate dualedit

CUDA_VISIBLE_DEVICES=0 python DualEdit-main/dualedit_train.py \
  -mn llava \
  -dna EVQA \
  -bs 4 \
  -dvc "cuda:0" \
  -edvc 0 \
  -eps 32 \
  -sci 200 \
  -lpi 10 \
  -ea 0.1 \
  -rs 20260528 \
  -tnp dualedit_llava_evqa_proxy500_B_t18_v6_s4000 \
  -cp configs/vead/llava-v1.5-7b-evqa-proxy500-dualedit-l6-t18.yaml \
  --data_path /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/data/vqa_train_proxy500.json \
  --img_root_dir /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/images \
  --max_steps 4000
```

如果单卡显存吃紧，用两张卡时只改 `CUDA_VISIBLE_DEVICES` 和 `-edvc`：

```bash
CUDA_VISIBLE_DEVICES=0,1 ... -dvc "cuda:0" -edvc 1 ...
```

若某个组合 4000-step 结果不稳定，再对该组合单独跑 6000-step 保险版。下面以组合 B 为例，组合 A 只需换回 `-tnp` 和 `-cp`：

```bash
CUDA_VISIBLE_DEVICES=0 python DualEdit-main/dualedit_train.py \
  -mn llava \
  -dna EVQA \
  -bs 4 \
  -dvc "cuda:0" \
  -edvc 0 \
  -eps 48 \
  -sci 200 \
  -lpi 10 \
  -ea 0.1 \
  -rs 20260528 \
  -tnp dualedit_llava_evqa_proxy500_B_t18_v6_s6000 \
  -cp configs/vead/llava-v1.5-7b-evqa-proxy500-dualedit-l6-t18.yaml \
  --data_path /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/data/vqa_train_proxy500.json \
  --img_root_dir /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/images \
  --max_steps 6000
```

---

## 9. 评测计划

评测数据：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/data/vqa_eval_proxy500.json
```

图片根目录：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/images
```

评测指标采用 E-VQA 的 6 个指标：

| 指标 | 含义 | 对应数据字段 |
|---|---|---|
| Rel | reliability，编辑请求是否答到新答案 | `src` + `image` -> `alt` |
| T-Gen | text generality，文本改写泛化 | `rephrase` + `image` -> `alt` |
| M-Gen | modal generality，同实体换图泛化 | `src` + `image_rephrase` -> `alt` |
| T-Loc | text locality，文本无关问题保持原答案 | `loc` -> `loc_ans` |
| M-Loc | modal locality，图像无关问题保持原答案 | `m_loc` + `m_loc_q` -> `m_loc_a` |
| Average | 五项均值 | `(Rel + T-Gen + M-Gen + T-Loc + M-Loc) / 5` |

训练完成后先选择最小 loss checkpoint：

```bash
export CKPT_DIR=<TRAIN_RECORD_DIR>/checkpoints

python - <<'PY'
import os
import re
from pathlib import Path

ckpt_dir = Path(os.environ["CKPT_DIR"]).resolve()
pat = re.compile(r"^epoch-(?P<epoch>\d+)-i-(?P<step>\d+)-(?P<kind>ema_loss|loss)-(?P<loss>\d+(?:\.\d+)?)$")
rows = []
for path in ckpt_dir.iterdir():
    if not path.is_file():
        continue
    m = pat.match(path.name)
    if not m:
        continue
    rows.append({
        "epoch": int(m.group("epoch")),
        "step": int(m.group("step")),
        "kind": m.group("kind"),
        "loss": float(m.group("loss")),
        "path": str(path),
    })

if not rows:
    raise SystemExit(f"No checkpoint with loss found in {ckpt_dir}")

# Primary rule: minimum loss. Tie-breaker: later step.
rows.sort(key=lambda x: (x["loss"], -x["step"]))
best = rows[0]

out = ckpt_dir.parent / "checkpoint_loss_ranking.tsv"
with out.open("w", encoding="utf-8") as f:
    f.write("rank\tepoch\tstep\tkind\tloss\tcheckpoint\n")
    for rank, item in enumerate(rows, 1):
        f.write(f"{rank}\t{item['epoch']}\t{item['step']}\t{item['kind']}\t{item['loss']:.6f}\t{item['path']}\n")

print(best["path"])
print(f"Selected checkpoint summary: {out}")
PY
```

两个组合分别运行上面的最小 loss checkpoint 选择脚本，然后统一评测。组合 A 与组合 B 的评测只允许使用各自的 yaml 和各自的最小 loss checkpoint。

每个最小 loss checkpoint 都必须跑两次评测：

| 评测方式 | 目的 |
|---|---|
| w/o gating | 看 adapter 插入层本身的编辑效果和副作用 |
| w/ gating, `tau=0.6` | 看完整 DualEdit 设置下 locality 是否被保护 |

组合 A w/o gating 评测命令：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2
conda activate dualedit

CUDA_VISIBLE_DEVICES=0 python DualEdit-main/dualedit_test.py \
  -mn llava \
  -dn EVQA \
  -dvc "cuda:0" \
  -edvc 0 \
  -ckpt <MIN_LOSS_CHECKPOINT_PATH> \
  -cp configs/vead/llava-v1.5-7b-evqa-proxy500-dualedit-l19-t16.yaml \
  -enp proxy500_A_t16_v19_nogating_minloss \
  --gating_mode off \
  --gating_threshold 0.6 \
  --data_path /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/data/vqa_eval_proxy500.json \
  --img_root_dir /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/images
```

组合 A w/ gating, `tau=0.6` 评测命令：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2
conda activate dualedit

CUDA_VISIBLE_DEVICES=0 python DualEdit-main/dualedit_test.py \
  -mn llava \
  -dn EVQA \
  -dvc "cuda:0" \
  -edvc 0 \
  -ckpt <MIN_LOSS_CHECKPOINT_PATH> \
  -cp configs/vead/llava-v1.5-7b-evqa-proxy500-dualedit-l19-t16.yaml \
  -enp proxy500_A_t16_v19_tau06_minloss \
  --gating_mode on \
  --gating_threshold 0.6 \
  --data_path /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/data/vqa_eval_proxy500.json \
  --img_root_dir /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/images
```

组合 B w/o gating 评测命令：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2
conda activate dualedit

CUDA_VISIBLE_DEVICES=0 python DualEdit-main/dualedit_test.py \
  -mn llava \
  -dn EVQA \
  -dvc "cuda:0" \
  -edvc 0 \
  -ckpt <MIN_LOSS_CHECKPOINT_PATH> \
  -cp configs/vead/llava-v1.5-7b-evqa-proxy500-dualedit-l6-t18.yaml \
  -enp proxy500_B_t18_v6_nogating_minloss \
  --gating_mode off \
  --gating_threshold 0.6 \
  --data_path /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/data/vqa_eval_proxy500.json \
  --img_root_dir /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/images
```

组合 B w/ gating, `tau=0.6` 评测命令：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2
conda activate dualedit

CUDA_VISIBLE_DEVICES=0 python DualEdit-main/dualedit_test.py \
  -mn llava \
  -dn EVQA \
  -dvc "cuda:0" \
  -edvc 0 \
  -ckpt <MIN_LOSS_CHECKPOINT_PATH> \
  -cp configs/vead/llava-v1.5-7b-evqa-proxy500-dualedit-l6-t18.yaml \
  -enp proxy500_B_t18_v6_tau06_minloss \
  --gating_mode on \
  --gating_threshold 0.6 \
  --data_path /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/data/vqa_eval_proxy500.json \
  --img_root_dir /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/evqa_proxy_train500_eval500_20260528/images
```

评测 checkpoint 选择：

- 训练完成前不评测。
- 主报告只评测每个组合 `records/.../checkpoints` 中最小 loss checkpoint。
- 每个最小 loss checkpoint 评测两次：w/o gating 与 w/ gating `tau=0.6`。
- 如果 checkpoint 文件名是 `ema_loss`，以 `ema_loss` 最小为准；否则以 `loss` 最小为准。
- 若最小 loss 出现并列，选择 step 更大的 checkpoint。
- 最终 checkpoint 可作为 sanity 对照评测，但不作为主结果选择依据。

---

## 10. 输出目录建议

训练输出根目录建议：

```text
/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/dualedit_llava_evqa_proxy500_two_combo_20260528
```

建议结构：

```text
dualedit_llava_evqa_proxy500_two_combo_20260528/
  combo_A_t16_v19/
    config/
      llava-v1.5-7b-evqa-proxy500-dualedit-l19-t16.yaml
      run_args.json
    checkpoints/
    eval/
      min_loss/
    logs/
      train.log
      post_train_eval.log
    summary/
      checkpoint_loss_ranking.tsv
      selected_checkpoint.json
      proxy500_dualedit_result.md
  combo_B_t18_v6/
    config/
      llava-v1.5-7b-evqa-proxy500-dualedit-l6-t18.yaml
      run_args.json
    checkpoints/
    eval/
      min_loss/
    logs/
      train.log
      post_train_eval.log
    summary/
      checkpoint_loss_ranking.tsv
      selected_checkpoint.json
      proxy500_dualedit_result.md
  summary/
    two_combo_minloss_eval_comparison.md
    two_combo_minloss_eval_comparison.csv
```

---

## 11. 结果回填表

### 11.1 最终汇总表

训练完成后，最终结果必须优先汇总成下面 4 行表格：

| Combo | Gating | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Avg |
|---|---|---:|---:|---:|---:|---:|---:|
| A: T16/V19 | X |  |  |  |  |  |  |
| A: T16/V19 | √ |  |  |  |  |  |  |
| B: T18/V6 | X |  |  |  |  |  |  |
| B: T18/V6 | √ |  |  |  |  |  |  |

其中：

- `X` 表示 w/o gating。
- `√` 表示 w/ gating, `tau=0.6`。
- `Avg = (Rel + T-Gen + M-Gen + T-Loc + M-Loc) / 5`。

这张表用于同时说明两件事：

- 层位置组合如何影响 `Rel / T-Gen / M-Gen / T-Loc / M-Loc / Avg`。
- gating 是否主要提升 `T-Loc / M-Loc`，以及是否牺牲 `Rel / T-Gen / M-Gen`。

否则如果只看 w/ gating 评测，locality 可能都被 gating 拉高，层间副作用差异会被掩盖。

### 11.2 Checkpoint 明细表

下面的明细表用于记录每行最终汇总结果对应的 checkpoint、step 和训练 loss：

| Combo | Eval Mode | Text Layer | Visual Layer | Run | Max Steps | Selected Rule | Checkpoint | Step | Train Loss | Rel | T-Gen | M-Gen | T-Loc | M-Loc | Average | Notes |
|---|---|---:|---:|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| A | w/o gating | 16 | 19 | main | 4000 | min loss |  |  |  |  |  |  |  |  |  | adapter-only |
| A | w/ gating tau=0.6 | 16 | 19 | main | 4000 | min loss |  |  |  |  |  |  |  |  |  | full DualEdit |
| B | w/o gating | 18 | 6 | main | 4000 | min loss |  |  |  |  |  |  |  |  |  | adapter-only |
| B | w/ gating tau=0.6 | 18 | 6 | main | 4000 | min loss |  |  |  |  |  |  |  |  |  | full DualEdit |
| A | w/o gating | 16 | 19 | fallback | 6000 | min loss |  |  |  |  |  |  |  |  |  | only if needed |
| A | w/ gating tau=0.6 | 16 | 19 | fallback | 6000 | min loss |  |  |  |  |  |  |  |  |  | only if needed |
| B | w/o gating | 18 | 6 | fallback | 6000 | min loss |  |  |  |  |  |  |  |  |  | only if needed |
| B | w/ gating tau=0.6 | 18 | 6 | fallback | 6000 | min loss |  |  |  |  |  |  |  |  |  | only if needed |

每个组合各自填写 checkpoint loss 排名表：

| Rank | Epoch | Step | Loss Kind | Loss | Checkpoint | Eval |
|---:|---:|---:|---|---:|---|---|
| 1 |  |  |  |  |  | evaluated |
| 2 |  |  |  |  |  | not evaluated |
| 3 |  |  |  |  |  | not evaluated |

---

## 12. 执行 Checklist

- [ ] 确认 proxy train/eval JSON 和 proxy 图片目录存在。
- [ ] 确认 `vqa_train_proxy500.json` 为 500 条。
- [ ] 确认 `vqa_eval_proxy500.json` 为 500 条。
- [ ] 确认 proxy 图片缺失数为 0。
- [ ] 新建组合 A yaml，设置 `edit_layers: [19]`、`edit_text_layers: [16]`。
- [ ] 新建组合 B yaml，设置 `edit_layers: [6]`、`edit_text_layers: [18]`。
- [ ] 给训练/评测入口增加 `--data_path`、`--img_root_dir` 参数。
- [ ] 将 LLaVA gating threshold 设为 `0.6`。
- [ ] 确认训练 optimizer 保持原始 DualEdit 的 Adam。
- [ ] 启动组合 A 4000-step 主训练。
- [ ] 启动组合 B 4000-step 主训练。
- [ ] 两个组合训练期间都不启动 proxy eval。
- [ ] 每个组合每 200 steps 保存 checkpoint。
- [ ] 两个组合都训练完成后，分别解析各自 `records/.../checkpoints`。
- [ ] 分别选择各自最小 loss checkpoint；若并列，选择 step 更大的 checkpoint。
- [ ] 对组合 A 最小 loss checkpoint 跑 w/o gating proxy eval 500。
- [ ] 对组合 A 最小 loss checkpoint 跑 w/ gating `tau=0.6` proxy eval 500。
- [ ] 对组合 B 最小 loss checkpoint 跑 w/o gating proxy eval 500。
- [ ] 对组合 B 最小 loss checkpoint 跑 w/ gating `tau=0.6` proxy eval 500。
- [ ] 记录两个组合、两种评测方式的五项指标和 Average。
- [ ] 优先回填 4 行最终汇总表：`A: T16/V19` X/√ 与 `B: T18/V6` X/√。
- [ ] 再回填 checkpoint 明细表，记录每行结果对应的 checkpoint、step 和 train loss。
- [ ] 如果某个组合 4000-step 不稳定，只对该组合启动 6000-step fallback。
- [ ] 每个组合保留最小 loss checkpoint、最终 checkpoint 和 `checkpoint_loss_ranking.tsv`。
- [ ] 清理两个组合的非保留 checkpoint，避免磁盘写满。
- [ ] 将两个组合的最终 checkpoint 信息和评测表回填到本手册。

---

## 13. 预期结论口径

本 proxy 实验不能直接替代全量 E-VQA 结论，它回答的是：

1. DualEdit 在小样本 proxy 上是否能稳定跑通。
2. 组合 A：text L16 + visual L19 的作者推荐组合，在 LLaVA proxy500 上是否有合理的 Rel/T-Gen/M-Gen/T-Loc/M-Loc 表现。
3. 组合 B：text L18 + visual L6 是否能作为浅层视觉 + 中后层文本的对照组合。
4. w/o gating 能反映 adapter 插入层本身的编辑效果和副作用。
5. w/ gating `tau=0.6` 能反映完整 DualEdit 设置下 locality 是否被保护。

如果 proxy 结果与作者全量 E-VQA 结果差异明显，优先检查：

- 是否误用了原始 full train/eval，而非 proxy。
- 是否只训练了 visual adapter，漏掉 text adapter。
- 是否阈值仍是 `0.8`。
- 是否误改 optimizer 为 AdamW；本复现实验应保持 Adam。
- 是否评测时门控未开启。
- 是否图片根目录没有指向 proxy `images`。
