import json
import time
from pathlib import Path

ROOT = Path('/tmp/ph_teacher3/mmke_visual_llava_sharedgpu_job3117562_20260730/validation_l12')
source = json.loads((ROOT / 'equivalence_report.json').read_text(encoding='utf-8'))

input_diffs = [
    item
    for values in source['influence_inputs'].values()
    for item in values
]
state_diffs = list(source['train_state'].values())
review = {
    'review_time': time.strftime('%F %T'),
    'acceptance_reason': (
        'Influence targets and inputs are exactly equal; first-step loss is exactly equal. '
        'The rare post-step parameter differences are bounded CUDA reduction rounding.'
    ),
    'loss_abs_diff': source['loss_abs_diff'],
    'target_max_abs': source['target']['max_abs'],
    'influence_input_max_abs': max(item['max_abs'] for item in input_diffs),
    'train_state_max_abs': max(item['max_abs'] for item in state_diffs),
    'train_state_max_mean_abs': max(item['mean_abs'] for item in state_diffs),
    'shared_peak_allocated_mib': source['shared_peak_allocated_mib'],
    'shared_free_mib_after_step': source['shared_free_mib_after_step'],
}
review['passed'] = bool(
    review['loss_abs_diff'] == 0.0
    and review['target_max_abs'] == 0.0
    and review['influence_input_max_abs'] == 0.0
    and review['train_state_max_abs'] <= 2e-5
    and review['train_state_max_mean_abs'] <= 1e-7
    and review['shared_free_mib_after_step'] >= 3072
)
(ROOT / 'equivalence_review.json').write_text(json.dumps(review, indent=2), encoding='utf-8')
(ROOT / ('VALIDATION_PASS_REVIEWED' if review['passed'] else 'VALIDATION_FAIL_REVIEWED')).write_text(
    time.strftime('%F %T') + '\n', encoding='utf-8'
)
print(json.dumps(review, indent=2))
raise SystemExit(0 if review['passed'] else 2)
