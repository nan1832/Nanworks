# 服务器实验脚本说明

## 1) 归因定位扫描

脚本路径：
- `VisEdit-main/scripts/vlm_attr_localize_scan.py`

在服务器上进入 `VisEdit-main` 后执行：

```bash
python scripts/vlm_attr_localize_scan.py \
  --model-name llava-v1.5-7b \
  --device cuda:0 \
  --config-path configs/p_track/llava-v1.5-7b.yaml \
  --dataset-type evqa \
  --max-samples 32 \
  --noise-level 0.30 \
  --topk-layers 5 \
  --pair-scan-topk 4 \
  --run-token-scan \
  --token-scan-samples 2 \
  --token-scan-stride 4 \
  --output-dir records/attr_localize/run1
```

如果你要跑自定义数据：

```bash
python scripts/vlm_attr_localize_scan.py \
  --model-name llava-v1.5-7b \
  --device cuda:0 \
  --config-path configs/p_track/llava-v1.5-7b.yaml \
  --dataset-type jsonl \
  --jsonl-path /path/to/your_samples.jsonl \
  --image-root /path/to/images \
  --max-samples 32 \
  --output-dir records/attr_localize/custom1
```

`jsonl` 每行至少包含：
- `image` 或 `img`
- `prompt`
- 可选 `id`

## 2) 结果文件解读

输出目录里关键文件：
- `phaseA_layer_scores.csv`：单层视觉/文本/联合扰动 KL 贡献分数
- `phaseC_pair_scores.csv`：视觉层-文本层组合的耦合分数
- `phaseB_token_scores.csv`：细粒度视觉 token 贡献（开启 `--run-token-scan` 时）
- `summary.json`：Top 视觉层、Top 文本层、最佳层位组合

你可以用 `summary.json` 的：
- `top_visual_layers` 作为 `edit_layers` 候选
- `top_text_layers` 作为 `edit_text_layers` 候选
- `best_pair` 作为首选组合

## 3) 生成 DualEdit 分层扫参配置

脚本路径：
- `DualEdit-main/scripts/generate_layer_sweep.py`

在服务器上进入 `DualEdit-main` 后执行：

```bash
python scripts/generate_layer_sweep.py \
  --base-config configs/vead/llava-v1.5-7b.yaml \
  --visual-layers 18,19,20 \
  --text-layers 14,15,16 \
  --output-dir configs/vead_sweeps/run1 \
  --edit-model-name llava-v1.5-7b \
  --data-name EVQA \
  --batch-size 1 \
  --device cuda:0 \
  --data-n 512 \
  --epochs 1 \
  --extra-devices 1 \
  --name-prefix sweep1
```

生成结果：
- `commands.json`
- `run_all.sh`
- `run_all.ps1`

你可以直接执行 `run_all.sh` 或按 `commands.json` 逐条提交任务。
