# Ours-Direct 21 组候选层实验与补跑记录

更新时间：2026-06-29 19:47:43 CST

结果来源：

`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/ours_direct_7models_3datasets_g08_gpu0_20260626_131624`

最终汇总文件：

- `ours_direct_candidates_summary.csv`
- `ours_direct_candidates_summary.md`
- `repair/ours_direct_repair_decisions_20260628_205558.md`
- `repair/ours_direct_repair_decisions_20260629_172248.md`

## 1. 计分口径

### 1.1 当前 Ours-Direct 主公式

主实验使用有方向约束的视觉梯度冲突分数：

```text
S_ours(l) = max(0, -S_v_cos(l)) * S_v_new_norm(l) * ((l + 1) / num_layers)^2
```

含义：

- `S_v_cos(l)`：候选层 visual span 中 old/model_pred 梯度与 new/alt 梯度的 cosine。
- `max(0, -S_v_cos(l))`：只保留方向冲突层，即梯度方向相反的层。
- `S_v_new_norm(l)`：new/alt 梯度强度。
- `((l + 1) / num_layers)^2`：深度先验，偏向后层但不直接指定中层。

`Top-3` 和 `Top-5` 是主公式清洗后的候选层；非法层、零梯度层、无有效方向冲突层会被删除。

### 1.2 不考虑方向的诊断公式

为排查“方向正负约束是否导致空候选”，额外记录忽略方向的诊断版本：

```text
S_ours_abs_direction(l) = abs(S_v_cos(l)) * S_v_new_norm(l) * ((l + 1) / num_layers)^2
```

该版本不是主实验正式结果，只作为诊断/补跑参考。若后续决定采用“不考虑方向正负”的变体，应另开方法名或消融记录，不能和当前 Ours-Direct 主结果混用。

## 2. 当前 21 组最终状态

状态统计：

- `done`: 8
- `low_confidence`: 3
- `failed`: 10
- 合计：21

| Dataset | Model | Method | Score source | Top-3 | Top-5 | Status | Valid | Total | Coverage |
|---|---|---|---|---|---|---|---:|---:|---:|
| EVQA-pilot500 | BLIP2-OPT-2.7B | Ours-Direct | virtual_delta_h_visual_gradient | - | - | failed; n=465/500 | 465 | 500 | 0.930 |
| EVQA-pilot500 | InstructBLIP-Vicuna-7B | Ours-Direct | virtual_delta_h_visual_gradient | - | - | failed; n=500/500 | 500 | 500 | 1.000 |
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | Ours-Direct | virtual_delta_h_visual_gradient | L29,L28,L30 | L29,L28,L30,L27,L24 | done; n=499/500 | 499 | 500 | 0.998 |
| EVQA-pilot500 | LLaVA-v1.5-7B | Ours-Direct | virtual_delta_h_visual_gradient | L17,L16,L15 | L17,L16,L15,L14,L18 | done; n=500/500 | 500 | 500 | 1.000 |
| EVQA-pilot500 | Qwen2.5-VL-3B | Ours-Direct | virtual_delta_h_visual_gradient | - | - | failed; n=457/500 | 457 | 500 | 0.914 |
| EVQA-pilot500 | PaliGemma-3B | Ours-Direct | virtual_delta_h_visual_gradient | - | - | failed; n=500/500 | 500 | 500 | 1.000 |
| EVQA-pilot500 | SmolVLM-Instruct-1.7B | Ours-Direct | virtual_delta_h_visual_gradient | L14,L13,L12 | L14,L13,L12,L11,L10 | done; n=500/500 | 500 | 500 | 1.000 |
| MMKE-visual | BLIP2-OPT-2.7B | Ours-Direct | virtual_delta_h_visual_gradient | L30 | L30 | done; n=175/214 | 175 | 214 | 0.818 |
| MMKE-visual | InstructBLIP-Vicuna-7B | Ours-Direct | virtual_delta_h_visual_gradient | - | - | failed; n=214/214 | 214 | 214 | 1.000 |
| MMKE-visual | MiniGPT-4-Vicuna-7B | Ours-Direct | virtual_delta_h_visual_gradient | L29,L28,L27 | L29,L28,L27,L26,L30 | done; n=214/214 | 214 | 214 | 1.000 |
| MMKE-visual | LLaVA-v1.5-7B | Ours-Direct | virtual_delta_h_visual_gradient | L13,L14,L15 | L13,L14,L15,L16,L12 | done; n=214/214 | 214 | 214 | 1.000 |
| MMKE-visual | Qwen2.5-VL-3B | Ours-Direct | virtual_delta_h_visual_gradient | L18,L19,L20 | L18,L19,L20,L16,L17 | low_confidence; n=96/214 | 96 | 214 | 0.449 |
| MMKE-visual | PaliGemma-3B | Ours-Direct | virtual_delta_h_visual_gradient | - | - | failed; n=214/214 | 214 | 214 | 1.000 |
| MMKE-visual | SmolVLM-Instruct-1.7B | Ours-Direct | virtual_delta_h_visual_gradient | - | - | failed; n=214/214 | 214 | 214 | 1.000 |
| MMKE-entity | BLIP2-OPT-2.7B | Ours-Direct | virtual_delta_h_visual_gradient | L20,L19,L18 | L20,L19,L18,L17,L22 | low_confidence; n=284/636 | 284 | 636 | 0.447 |
| MMKE-entity | InstructBLIP-Vicuna-7B | Ours-Direct | virtual_delta_h_visual_gradient | - | - | failed; n=636/636 | 636 | 636 | 1.000 |
| MMKE-entity | MiniGPT-4-Vicuna-7B | Ours-Direct | virtual_delta_h_visual_gradient | L28,L29,L27 | L28,L29,L27,L26,L25 | done; n=636/636 | 636 | 636 | 1.000 |
| MMKE-entity | LLaVA-v1.5-7B | Ours-Direct | virtual_delta_h_visual_gradient | L13,L30,L12 | L13,L30,L12,L14,L15 | done; n=636/636 | 636 | 636 | 1.000 |
| MMKE-entity | Qwen2.5-VL-3B | Ours-Direct | virtual_delta_h_visual_gradient | L8,L7,L6 | L8,L7,L6,L5,L9 | low_confidence; n=5/636 | 5 | 636 | 0.008 |
| MMKE-entity | PaliGemma-3B | Ours-Direct | virtual_delta_h_visual_gradient | - | - | failed; n=636/636 | 636 | 636 | 1.000 |
| MMKE-entity | SmolVLM-Instruct-1.7B | Ours-Direct | virtual_delta_h_visual_gradient | - | - | failed; n=636/636 | 636 | 636 | 1.000 |

## 3. Abs-direction 诊断/修复候选记录

下表来自最新 repair decisions。`Action=repaired_by_abs_direction` 表示主公式失败，但不考虑方向正负时能给出诊断候选层；这些候选层暂不计入 Ours-Direct 主实验正式结果。

| Dataset | Model | Main Status | Valid | Main Top-3 | Abs Top-3 | Abs Top-5 | Abs Status | Action |
|---|---|---|---:|---|---|---|---|---|
| evqa-pilot500 | blip2-opt-2.7b | failed | 465 | - | L16,L17,L15 | L16,L17,L15,L18,L14 | computed_from_layer_scores | repaired_by_abs_direction |
| evqa-pilot500 | instructblip-vicuna-7b | failed | 500 | - | L21,L22,L20 | L21,L22,L20,L19,L23 | computed_from_layer_scores | repaired_by_abs_direction |
| evqa-pilot500 | minigpt-4-vicuna-7b | done | 499 | L29,L28,L30 | L21,L18,L22 | L21,L18,L22,L19,L20 | computed_from_layer_scores | done |
| evqa-pilot500 | llava-v1.5-7b | done | 500 | L17,L16,L15 | L17,L16,L15 | L17,L16,L15,L14,L18 | computed_from_layer_scores | done |
| evqa-pilot500 | qwen2.5-vl-3b | missing | - | - | - | - | no_summary | gpu_rerun |
| evqa-pilot500 | paligemma-3b | failed | 500 | - | L7,L8,L6 | L7,L8,L6,L9,L5 | computed_from_layer_scores | repaired_by_abs_direction |
| evqa-pilot500 | smolvlm-1.7b | done | 500 | L14,L13,L12 | L14,L13,L12 | L14,L13,L12,L11,L10 | computed_from_layer_scores | done |
| mmke-visual | blip2-opt-2.7b | done | 175 | L30 | L15,L17,L14 | L15,L17,L14,L16,L13 | computed_from_layer_scores | done |
| mmke-visual | instructblip-vicuna-7b | failed | 214 | - | L27,L26,L25 | L27,L26,L25,L24,L23 | computed_from_layer_scores | repaired_by_abs_direction |
| mmke-visual | minigpt-4-vicuna-7b | done | 214 | L29,L28,L27 | L29,L28,L27 | L29,L28,L27,L26,L30 | computed_from_layer_scores | done |
| mmke-visual | llava-v1.5-7b | done | 214 | L13,L14,L15 | L13,L14,L15 | L13,L14,L15,L16,L12 | computed_from_layer_scores | done |
| mmke-visual | qwen2.5-vl-3b | missing | - | - | - | - | no_summary | gpu_rerun |
| mmke-visual | paligemma-3b | failed | 214 | - | L5,L7,L8 | L5,L7,L8,L6,L4 | computed_from_layer_scores | repaired_by_abs_direction |
| mmke-visual | smolvlm-1.7b | failed | 214 | - | L10,L7,L9 | L10,L7,L9,L8,L11 | computed_from_layer_scores | repaired_by_abs_direction |
| mmke-entity | blip2-opt-2.7b | low_confidence | 284 | L20,L19,L18 | L20,L19,L18 | L20,L19,L18,L17,L22 | computed_from_layer_scores | low_confidence |
| mmke-entity | instructblip-vicuna-7b | failed | 636 | - | L27,L26,L25 | L27,L26,L25,L29,L24 | computed_from_layer_scores | repaired_by_abs_direction |
| mmke-entity | minigpt-4-vicuna-7b | done | 636 | L28,L29,L27 | L28,L29,L27 | L28,L29,L27,L26,L25 | computed_from_layer_scores | done |
| mmke-entity | llava-v1.5-7b | done | 636 | L13,L30,L12 | L13,L30,L12 | L13,L30,L12,L14,L15 | computed_from_layer_scores | done |
| mmke-entity | qwen2.5-vl-3b | missing | - | - | - | - | no_summary | gpu_rerun |
| mmke-entity | paligemma-3b | failed | 636 | - | L7,L5,L6 | L7,L5,L6,L8,L4 | computed_from_layer_scores | repaired_by_abs_direction |
| mmke-entity | smolvlm-1.7b | failed | 636 | - | L10,L11,L9 | L10,L11,L9,L8,L7 | computed_from_layer_scores | repaired_by_abs_direction |

## 4. GPU 补跑记录

### 4.1 第一轮补跑：20260628_205558

第一轮 repair 根据当时的缺失/失败状态触发 GPU rerun，主要修复 `no_common_valid_samples` 或 `missing_summary`。

| Dataset | Model | Log | Final status after all repairs | Final Top-3 | Final Top-5 |
|---|---|---|---|---|---|
| EVQA-pilot500 | MiniGPT-4-Vicuna-7B | `logs/ours_direct_repair_evqa-pilot500_minigpt-4-vicuna-7b_20260628_205558.log` | done; n=499/500 | L29,L28,L30 | L29,L28,L30,L27,L24 |
| EVQA-pilot500 | Qwen2.5-VL-3B | `logs/ours_direct_repair_evqa-pilot500_qwen2.5-vl-3b_20260628_205558.log` | failed; n=457/500 | - | - |
| EVQA-pilot500 | PaliGemma-3B | `logs/ours_direct_repair_evqa-pilot500_paligemma-3b_20260628_205558.log` | failed; n=500/500 | - | - |
| MMKE-visual | MiniGPT-4-Vicuna-7B | `logs/ours_direct_repair_mmke-visual_minigpt-4-vicuna-7b_20260628_205558.log` | done; n=214/214 | L29,L28,L27 | L29,L28,L27,L26,L30 |
| MMKE-visual | Qwen2.5-VL-3B | `logs/ours_direct_repair_mmke-visual_qwen2.5-vl-3b_20260628_205558.log` | low_confidence; n=96/214 | L18,L19,L20 | L18,L19,L20,L16,L17 |
| MMKE-visual | PaliGemma-3B | `logs/ours_direct_repair_mmke-visual_paligemma-3b_20260628_205558.log` | failed; n=214/214 | - | - |
| MMKE-entity | MiniGPT-4-Vicuna-7B | `logs/ours_direct_repair_mmke-entity_minigpt-4-vicuna-7b_20260628_205558.log` | done; n=636/636 | L28,L29,L27 | L28,L29,L27,L26,L25 |
| MMKE-entity | Qwen2.5-VL-3B | `logs/ours_direct_repair_mmke-entity_qwen2.5-vl-3b_20260628_205558.log` | low_confidence; n=5/636 | L8,L7,L6 | L8,L7,L6,L5,L9 |

### 4.2 第二轮补跑：20260629_172248

第二轮 repair 在 G09 恢复后执行，针对三组 Qwen `missing_summary` 重新跑 GPU 任务。

| Dataset | Model | Start | Finish | Log | Final status | Final Top-3 | Final Top-5 | Main issue |
|---|---|---|---|---|---|---|---|---|
| EVQA-pilot500 | Qwen2.5-VL-3B | 2026-06-29 17:22:50 | 2026-06-29 19:17:41 | `logs/ours_direct_repair_evqa-pilot500_qwen2.5-vl-3b_20260629_172248.log` | failed; n=457/500 | - | - | `empty_model_pred` 较多，仍无合法主候选层 |
| MMKE-visual | Qwen2.5-VL-3B | 2026-06-29 19:17:43 | 2026-06-29 19:43:45 | `logs/ours_direct_repair_mmke-visual_qwen2.5-vl-3b_20260629_172248.log` | low_confidence; n=96/214 | L18,L19,L20 | L18,L19,L20,L16,L17 | coverage 低 |
| MMKE-entity | Qwen2.5-VL-3B | 2026-06-29 19:43:46 | 2026-06-29 19:47:42 | `logs/ours_direct_repair_mmke-entity_qwen2.5-vl-3b_20260629_172248.log` | low_confidence; n=5/636 | L8,L7,L6 | L8,L7,L6,L5,L9 | coverage 极低 |

## 5. 结论

1. Ours-Direct 21 组流程与补跑流程均已结束；当前没有 Ours-Direct 相关进程继续运行。
2. 主公式有效完成 `8/21`，低置信 `3/21`，失败 `10/21`。
3. 失败的主要类型不是进程崩溃，而是主公式方向约束清洗后没有合法候选层，即 `no_valid_ours_direct_layer`。
4. Qwen 补跑后仍存在 `empty_model_pred` 问题；其中 MMKE-entity/Qwen 只有 `5/636` 个有效样本，不能作为可靠主结果。
5. Abs-direction 诊断能为部分 failed 组给出候选层，但它属于诊断/消融，不应直接并入 Ours-Direct 主实验结果。
