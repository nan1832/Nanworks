"""
LLaVA E-VQA 视觉模态 pilot 1000 预测指标折线图
公式：
  M_rel = cos × nn × (l/30)^1.8
  M_gen = cos × nn × (l/30)^2.5
  M_loc = cos × √nn × (l/30)^2
  M_avg = cos × nn × (l/30)^2
"""
import numpy as np
import matplotlib.pyplot as plt
import csv
import os

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

csv_path = r'D:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\downloads\Temp\evqa_request_only_llava_lga_candidate_20260525\pilot_1000\virtual_delta_h_lga_layer_scores.csv'

layers, cos_vals, nn_vals = [], [], []
with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['S_v_zero_grad'].strip() == 'True':
            continue
        layers.append(int(row['layer']))
        cos_vals.append(float(row['S_v_cos']))
        nn_vals.append(float(row['S_v_new_norm']))

idx = np.argsort(layers)
layers = np.array(layers)[idx]
cos_vals = np.array(cos_vals)[idx]
nn_vals = np.array(nn_vals)[idx]

L = 30.0
feasible = cos_vals > 0
cos_pos = np.where(feasible, cos_vals, 0)
nn_pos = np.where(feasible, nn_vals, 0)
sqrt_nn = np.where(feasible, np.sqrt(nn_vals), 0)

d18 = np.where(layers > 0, (layers / L) ** 1.8, 0)
d20 = np.where(layers > 0, (layers / L) ** 2.0, 0)
d25 = np.where(layers > 0, (layers / L) ** 2.5, 0)

M_rel = cos_pos * nn_pos * d18
M_gen = cos_pos * nn_pos * d25
M_loc = cos_pos * sqrt_nn * d20
M_avg = cos_pos * nn_pos * d20

# Plot
fig, ax = plt.subplots(figsize=(13, 6))

ax.plot(layers, M_rel, 'g-o', markersize=5, linewidth=2, label='M_rel = cos × nn × (l/30)$^{1.8}$')
ax.plot(layers, M_gen, 'm-^', markersize=5, linewidth=2, label='M_gen = cos × nn × (l/30)$^{2.5}$')
ax.plot(layers, M_loc, color='orange', marker='v', markersize=5, linewidth=2,
        label='M_loc = cos × √nn × (l/30)$^{2}$')
ax.plot(layers, M_avg, 'c-D', markersize=5, linewidth=2, label='M_avg = cos × nn × (l/30)$^{2}$')

# Mark OOF zone
oof_mask = cos_vals <= 0
if np.any(oof_mask):
    oof_start = layers[oof_mask].min()
    oof_end = layers[oof_mask].max()
    ax.axvspan(oof_start - 0.5, oof_end + 0.5, alpha=0.12, color='gray')
    ax.text(oof_start + 0.5, ax.get_ylim()[1] * 0.9 if ax.get_ylim()[1] > 0 else 0.03,
            'OOF\n(cos<0)', fontsize=9, color='gray', ha='left')

# Mark Top1 for each metric
top1_rel = layers[np.argmax(M_rel)]
top1_gen = layers[np.argmax(M_gen)]
top1_loc = layers[np.argmax(M_loc)]
top1_avg = layers[np.argmax(M_avg)]

ymax = max(M_rel.max(), M_gen.max(), M_loc.max(), M_avg.max())
offset = ymax * 0.02

ax.annotate(f'Top1={top1_rel}', xy=(top1_rel, M_rel.max()), fontsize=8, color='g',
            xytext=(top1_rel + 0.5, M_rel.max() + offset), ha='left')
ax.annotate(f'Top1={top1_gen}', xy=(top1_gen, M_gen.max()), fontsize=8, color='m',
            xytext=(top1_gen + 0.5, M_gen.max() + offset), ha='left')
ax.annotate(f'Top1={top1_loc}', xy=(top1_loc, M_loc.max()), fontsize=8, color='orange',
            xytext=(top1_loc - 3, M_loc.max() + offset), ha='left')
ax.annotate(f'Top1={top1_avg}', xy=(top1_avg, M_avg.max()), fontsize=8, color='c',
            xytext=(top1_avg - 4, M_avg.max() - offset * 2), ha='left')

ax.set_xlabel('Layer', fontsize=12)
ax.set_ylabel('Prediction Score', fontsize=12)
ax.set_title('LLaVA E-VQA Visual v3 Prediction Scores (Pilot n=1000)', fontsize=13)
ax.set_xticks(layers)
ax.legend(loc='upper left', fontsize=10)
ax.grid(True, alpha=0.3)
ax.set_xlim(-0.5, layers.max() + 0.5)

plt.tight_layout()
save_path = r'D:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\downloads\Temp\Images\LLaVA_EVQA_Visual_v3_Scores_Pilot1000.png'
os.makedirs(os.path.dirname(save_path), exist_ok=True)
plt.savefig(save_path, dpi=150, bbox_inches='tight')
plt.close()
print(f'Saved: {save_path}')
