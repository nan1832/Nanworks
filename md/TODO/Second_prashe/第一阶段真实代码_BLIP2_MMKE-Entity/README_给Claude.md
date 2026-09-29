# 第一阶段真实代码包：BLIP2 × MMKE-Entity

## 1. 用途与来源

本目录用于向 Claude 提供第二阶段实验计划所需的第一阶段真实实现。代码以服务器上实际完成 `BLIP2 × MMKE-Entity / L1` 训练与独立评测的版本为准，不以本地可能已演化的同名文件代替。

- 实际任务：Job `3126082`，节点 `g09`，GPU0。
- 模型：`blip2-opt-2.7b`。
- 数据集：MMKE-Entity，经 EVQA-compatible 字段转换后由 `EVQA` 数据类读取。
- 训练集和评测集为不同 JSON；评测没有使用训练集。
- 训练协议：50 epoch、batch size 2、seed 20260601、学习率 `1e-4`、EMA alpha 0.1。
- 选点协议：从 epoch checkpoint 中选择 EMA loss 最小者。
- 清理协议：保留 selected checkpoint，删除未选中的 checkpoint。

本包只包含理解第一阶段方法所需的代码、配置、数据结构样例和一组真实完成证据，不包含模型权重、完整数据集、图片或大型 checkpoint 二进制。

## 2. 建议上传给 Claude 的文件

| 用户要求 | 本包文件 | 服务器原路径/作用 |
|---|---|---|
| BLIP2 模型加载及前向传播 | `code/model/blip2.py` | `VisEdit-main/editor/vllms_for_edit/blip2.py` |
| BLIP2 抽象接口 | `code/model/base_vllm.py` | `VisEdit-main/editor/vllms_for_edit/base.py` |
| 模型工厂 | `code/utils/model_factory_and_helpers.py` | `VisEdit-main/utils/__init__.py` |
| Adapter 定义 | `code/adapter/adpt_model.py` | `VisEdit-main/editor/vllm_editors/vead/adpt_model.py` |
| 层插入 / hook 实现 | `code/editor/vead.py`、`code/utils/nethook.py` | `init_hook_adaptors()` 注册 forward hook；`nethook.py` 提供模块定位工具 |
| MMKE 数据加载器 | `code/data/vllm_dataset.py`、`code/data/dataset_base.py` | `EVQA`/`CaptionDataset` 与基础 Dataset；本实验读取 MMKE-Entity 转换文件 |
| 训练与 checkpoint 选择 | `code/runner/run_blip2_mmke_entity_sweep.py`、`code/editor/base_editor_training.py` | 真实 runner、训练循环、EMA 选点和清理逻辑 |
| Reliability / Generality / Locality 评测 | `code/evaluation/vllm_editor_eval.py` | `eval()`、`eval_batch()` 与各指标计算 |
| 第一阶段配置 | `config/blip2-opt-2.7b.yaml`、`config/actual_run_config.json` | YAML 模型/Adapter 配置及 L1 实际运行参数快照 |
| 实际启动方式 | `launcher/launch_actual_job3126082.sh` | Job 3126082 原 launcher；其中 MMKE-Entity × BLIP2 的 L1 调用是真实完成调用 |
| 数据对象结构 | `data_schema/MMKE-entity_完整数据示例_3条.json` | 三条完整 MMKE-Entity 样例，仅用于理解字段 |
| 完成证据 | `evidence/*` | selected checkpoint 记录、eval 完成标记和正式评测均值 |

若上传文件数受限，优先上传：runner、`blip2.py`、`adpt_model.py`、`vead.py`、`vllm_dataset.py`、`vllm_editor_eval.py`、YAML、actual run config 和本 README。

## 3. 代码流程

```text
MMKE-Entity train/eval JSON
        │
        ▼
EVQA 数据类读取并组装 src / alt / rephrase / image / locality
        │
        ▼
BLIP2 模型及 processor 加载
        │
        ▼
VEAD 在指定语言层注册 Adapter forward hook
        │
        ▼
生成/缓存影响目标与训练 batch
        │
        ▼
50 epoch Adapter 训练，每个 epoch 保存 checkpoint 并计算 EMA loss
        │
        ▼
选择最小 EMA checkpoint，删除未选中 checkpoint
        │
        ▼
在独立 MMKE-Entity eval JSON 上计算
Reliability / T-Generality / M-Generality / T-Locality / M-Locality
```

## 4. 实际实现中的重要细节

### 4.1 Adapter 和层插入

`code/editor/vead.py` 的 `init_hook_adaptors()` 根据 `llm_layer_tmp` 定位语言模型层，并通过 `register_forward_hook` 插入 `VisionEditAdaptor`。Adapter 的网络结构在 `code/adapter/adpt_model.py`。

实际 runner 还对 `VisionEditAdaptor.forward` 应用了 `official_visual_forward`，固定为视觉编辑所需的执行方式，并对图像加载行为做了运行期兼容处理。Claude 制定第二阶段方案时应保留这些真实约束，不能只参考抽象伪代码。

### 4.2 MMKE-Entity 数据读取

实际运行文件为：

- train：`vqa_mmke_entity_train_evqa_compat.json`
- eval：`vqa_mmke_entity_eval_evqa_compat.json`
- 图片根目录：`datasets/MMKE-Bench/data_image`

因此代码层面使用 `EVQA` 类，但数据语义仍为 MMKE-Entity。训练日志加载了 636 条训练样本。完整数据没有复制进本包；三条结构样例见 `data_schema/`。

### 4.3 YAML 的 `edit_layers: [19]` 不是 L1 的真实层

YAML 是基础模板。runner 的 `make_config()` 会在每层启动时覆盖 `edit_layers`。本包真实完成证据对应 L1，launcher 也显式传入 `--layers 1`。因此不能因为 YAML 模板中写 `[19]` 就把这次实验误认为 L19。

### 4.4 `actual_run_config.json` 中 `skip_train=true` 的含义

该文件在训练完成后的独立评测调用中被最后一次写入，因此记录的是“复用已选 checkpoint、跳过训练、执行 eval”的末次阶段参数，并不表示该层没有训练。训练及选点由 launcher 的前一阶段完成，`evidence/selected_checkpoint_L1.tsv` 给出了训练选点证据。

### 4.5 指标口径

- Reliability：编辑问题命中率。
- T-Generality：文本改写问题的泛化命中率。
- M-Generality：图像改写问题的泛化命中率。
- T-Locality：文本无关问题保持率。
- M-Locality：图像无关问题保持率。
- Average：上述五项百分制指标的算术平均。

L1 的真实结果为：Rel 57.94、T-Gen 57.91、M-Gen 57.96、T-Loc 100.00、M-Loc 88.71、Average 72.504。`mean_results_L1.json` 报告 `sample_count=954`，这是评测程序输出的聚合条目数；不要将其误写成训练集样本数，训练集为 636 条。

## 5. 给 Claude 的使用约束

1. 将这些文件视为第一阶段真实实现证据，第二阶段计划应明确哪些代码复用、哪些新增。
2. 不要把文件名中的 `pilot500` 当成实际数据集；真实数据路径和 launcher 表明此运行是 MMKE-Entity。
3. 保持训练与评测数据隔离，禁止用训练集代替正式 test/eval。
4. 不应仅凭进程退出或 `train.done` 判定完成；正式完成需要 selected checkpoint、完整评测结果和 `eval_full.done`。
5. 若第二阶段改变数据结构、编辑目标、Adapter 位置或指标定义，应单独声明，不能与第一阶段结果直接混合比较。
6. 本包为阅读与设计快照，目录按功能重新归类，并非完整可直接启动的 Python 工程；真实 import 关系以“服务器原路径”列为准。

## 6. 完整性核验

服务器原文件与本包核心代码/配置的 SHA-256 已逐项核对一致。哈希清单见 `SHA256SUMS.txt`。
