# Job 3044841 关键完成层备份清单

备份日期：2026-07-28  
来源节点：g09  
服务器中转备份：`/var/tmp/ph_teacher3/job3044841_20260728/essential_completed_layers_backup_20260728`  
备份有效载荷：71 个文件，3,371,652,453 bytes（约 3.14 GiB）；另含本清单。  
本机归档：`D:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\server_handoff\job3044841_20260728\job3044841_essential_completed_layers_backup_20260728.tar`  
归档大小：3,371,806,720 bytes  
归档 SHA-256：`e6115c18c426bd56c757d5774763c6e97f33b40c708f48d24b307bbb46270449`

## 备份范围

每层保存：selected checkpoint、`train.done`、`selected_checkpoint.tsv`、`eval_full.done`、`eval_full` 内完整 `results.json`/`mean_results.json`、loss history、训练日志和评测日志。模型级 run config 也已保存。

| 模型 | 层 | Checkpoint SHA-256 | Eval 文件核验 |
|---|---:|---|---|
| InstructBLIP-Vicuna-7B | L1 | `ea84f19d77fc0c4ef9cba831e66c3872484e59a80c086f980f03b0e1e793bb5b` | 2/2，大小与 g09 一致 |
| InstructBLIP-Vicuna-7B | L3 | `d32984e162f5cf28a5d62521f7b0889ea8337c0af455ecf28a2907198e7d42d4` | 2/2，大小与 g09 一致 |
| InstructBLIP-Vicuna-7B | L4 | `6a58527c3a8834018d0937b9f8236da991c54d4fa8a36246dfa7ee605bb3d501` | 2/2，大小与 g09 一致 |
| InstructBLIP-Vicuna-7B | L22 | `e30b54461cac5c2951f14f216cdda5aba104971ac00485888d7bc8c81c0ea19b` | 2/2，大小与 g09 一致 |
| InstructBLIP-Vicuna-7B | L23 | `b7906bcc3694f950abc648116a0c80701a255f87266a9fb70727d1001265b0a9` | 2/2，大小与 g09 一致 |
| InstructBLIP-Vicuna-7B | L24 | `3fff70781f87a3dbac371922390b975c414ca7c07b927dbfb1a1a09da207c800` | 2/2，大小与 g09 一致 |
| InstructBLIP-Vicuna-7B | L25 | `251de5f6b2a096ae482e24ead571371e86a49f6d8acafaf556814c23725f891e` | 2/2，大小与 g09 一致 |
| MiniGPT-4-Vicuna-7B | L2 | `38b868235d942d9a469e63ee588073635f0b1f3a9ec6d658ec27e4d3e6a769ee` | 2/2，4,869,930 bytes，与 g09 一致 |

## MiniGPT-4 L2 正式评测

- Selected checkpoint：Epoch 48，`i=15264`
- Raw loss：0.2744022607803345
- EMA loss：0.2806833764152165
- Eval 样本：954
- Rel：59.89
- T-Gen：59.84
- M-Gen：59.78
- T-Loc：100.00
- M-Loc：98.24
- Average：75.55

## 验收结论

8 个 selected checkpoint 的 SHA-256 均已分别与 g09 源文件重新计算并匹配；各层正式评测目录均包含 `results.json` 和 `mean_results.json`。本清单不能替代实际归档文件，关闭 Job 前应同时保留服务器中转副本和本机归档。
