# Qwen2.5-VL-3B 7基础公式 + 4 Ours指标候选层重算

Source run root: `/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/ours_direct_qwen_chatfix_repair_g09_gpu1_20260630_091304`

说明：clean Top-K 已删除 `S_v_zero_grad=true`、非有限分数、带 `invalid_reason` 的层；`Ours-Direct-Conflict` 额外要求分数 > 0。

## 4 个 Ours 系列指标

| Dataset | Method | Status | Clean Top-3 | Clean Top-5 | Failure |
|---|---|---|---|---|---|
| EVQA-pilot500 | Ours-Direct-Conflict | insufficient_valid_layers | L34 | L34 | clean_topk_less_than_3 |
| EVQA-pilot500 | Ours-AbsDirection-Direct | done | L24,L21,L22 | L24,L21,L22,L23,L26 |  |
| EVQA-pilot500 | Ours-NoDirection-Direct | done | L20,L18,L19 | L20,L18,L19,L21,L17 |  |
| EVQA-pilot500 | Ours-1MinusCos-Direct | done | L20,L18,L19 | L20,L18,L19,L17,L21 |  |
| MMKE-visual | Ours-Direct-Conflict | unavailable |  |  | no_valid_negative_cosine_layer |
| MMKE-visual | Ours-AbsDirection-Direct | done | L22,L17,L18 | L22,L17,L18,L20,L21 |  |
| MMKE-visual | Ours-NoDirection-Direct | done | L20,L18,L19 | L20,L18,L19,L17,L22 |  |
| MMKE-visual | Ours-1MinusCos-Direct | done | L20,L18,L19 | L20,L18,L19,L21,L17 |  |
| MMKE-entity | Ours-Direct-Conflict | unavailable |  |  | no_valid_negative_cosine_layer |
| MMKE-entity | Ours-AbsDirection-Direct | done | L22,L21,L20 | L22,L21,L20,L17,L18 |  |
| MMKE-entity | Ours-NoDirection-Direct | done | L22,L20,L21 | L22,L20,L21,L18,L19 |  |
| MMKE-entity | Ours-1MinusCos-Direct | done | L26,L20,L25 | L26,L20,L25,L18,L21 |  |

## 7 个基础视觉公式

| Dataset | Method | Status | Clean Top-3 | Clean Top-5 | Failure |
|---|---|---|---|---|---|
| EVQA-pilot500 | M_dot | done | L6,L5,L7 | L6,L5,L7,L11,L9 |  |
| EVQA-pilot500 | M_cos | done | L24,L23,L27 | L24,L23,L27,L22,L25 |  |
| EVQA-pilot500 | M_new_norm | done | L0,L1,L2 | L0,L1,L2,L3,L4 |  |
| EVQA-pilot500 | M_pos_ratio | done | L29,L27,L25 | L29,L27,L25,L30,L26 |  |
| EVQA-pilot500 | M_conflict | done | L30,L31,L32 | L30,L31,L32,L34,L33 |  |
| EVQA-pilot500 | M_newn_x_1mcos | done | L0,L1,L2 | L0,L1,L2,L3,L4 |  |
| EVQA-pilot500 | M_abscos_x_newn | done | L21,L19,L17 | L21,L19,L17,L20,L18 |  |
| MMKE-visual | M_dot | done | L0,L1,L2 | L0,L1,L2,L3,L4 |  |
| MMKE-visual | M_cos | done | L12,L10,L11 | L12,L10,L11,L9,L13 |  |
| MMKE-visual | M_new_norm | done | L0,L1,L2 | L0,L1,L2,L3,L4 |  |
| MMKE-visual | M_pos_ratio | done | L5,L6,L7 | L5,L6,L7,L12,L13 |  |
| MMKE-visual | M_conflict | done | L34,L33,L32 | L34,L33,L32,L31,L30 |  |
| MMKE-visual | M_newn_x_1mcos | done | L0,L1,L2 | L0,L1,L2,L3,L4 |  |
| MMKE-visual | M_abscos_x_newn | done | L0,L1,L2 | L0,L1,L2,L3,L4 |  |
| MMKE-entity | M_dot | done | L0,L1,L2 | L0,L1,L2,L7,L3 |  |
| MMKE-entity | M_cos | done | L12,L11,L10 | L12,L11,L10,L13,L7 |  |
| MMKE-entity | M_new_norm | done | L0,L1,L2 | L0,L1,L2,L3,L4 |  |
| MMKE-entity | M_pos_ratio | done | L17,L16,L11 | L17,L16,L11,L12,L15 |  |
| MMKE-entity | M_conflict | done | L34,L33,L32 | L34,L33,L32,L31,L30 |  |
| MMKE-entity | M_newn_x_1mcos | done | L0,L1,L2 | L0,L1,L2,L3,L4 |  |
| MMKE-entity | M_abscos_x_newn | done | L0,L1,L2 | L0,L1,L2,L3,L6 |  |

## Ours 系列 Top-5 候选层池

| Dataset | Layer | Source Methods |
|---|---|---|
| EVQA-pilot500 | L17 | Ours-NoDirection-Direct#5, Ours-1MinusCos-Direct#4 |
| EVQA-pilot500 | L18 | Ours-NoDirection-Direct#2, Ours-1MinusCos-Direct#2 |
| EVQA-pilot500 | L19 | Ours-NoDirection-Direct#3, Ours-1MinusCos-Direct#3 |
| EVQA-pilot500 | L20 | Ours-NoDirection-Direct#1, Ours-1MinusCos-Direct#1 |
| EVQA-pilot500 | L21 | Ours-AbsDirection-Direct#2, Ours-NoDirection-Direct#4, Ours-1MinusCos-Direct#5 |
| EVQA-pilot500 | L22 | Ours-AbsDirection-Direct#3 |
| EVQA-pilot500 | L23 | Ours-AbsDirection-Direct#4 |
| EVQA-pilot500 | L24 | Ours-AbsDirection-Direct#1 |
| EVQA-pilot500 | L26 | Ours-AbsDirection-Direct#5 |
| EVQA-pilot500 | L34 | Ours-Direct-Conflict#1 |
| MMKE-visual | L17 | Ours-AbsDirection-Direct#2, Ours-NoDirection-Direct#4, Ours-1MinusCos-Direct#5 |
| MMKE-visual | L18 | Ours-AbsDirection-Direct#3, Ours-NoDirection-Direct#2, Ours-1MinusCos-Direct#2 |
| MMKE-visual | L19 | Ours-NoDirection-Direct#3, Ours-1MinusCos-Direct#3 |
| MMKE-visual | L20 | Ours-AbsDirection-Direct#4, Ours-NoDirection-Direct#1, Ours-1MinusCos-Direct#1 |
| MMKE-visual | L21 | Ours-AbsDirection-Direct#5, Ours-1MinusCos-Direct#4 |
| MMKE-visual | L22 | Ours-AbsDirection-Direct#1, Ours-NoDirection-Direct#5 |
| MMKE-entity | L17 | Ours-AbsDirection-Direct#4 |
| MMKE-entity | L18 | Ours-AbsDirection-Direct#5, Ours-NoDirection-Direct#4, Ours-1MinusCos-Direct#4 |
| MMKE-entity | L19 | Ours-NoDirection-Direct#5 |
| MMKE-entity | L20 | Ours-AbsDirection-Direct#3, Ours-NoDirection-Direct#2, Ours-1MinusCos-Direct#2 |
| MMKE-entity | L21 | Ours-AbsDirection-Direct#2, Ours-NoDirection-Direct#3, Ours-1MinusCos-Direct#5 |
| MMKE-entity | L22 | Ours-AbsDirection-Direct#1, Ours-NoDirection-Direct#1 |
| MMKE-entity | L25 | Ours-1MinusCos-Direct#3 |
| MMKE-entity | L26 | Ours-1MinusCos-Direct#1 |