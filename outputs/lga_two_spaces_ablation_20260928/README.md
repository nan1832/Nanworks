# LGA 去旧强度、去新强度：参数 / 视觉两套严格补算

2026-09-28 已建立补算队列；当前没有新的已完成消融结果，详见 [最新同步状态](sync_status.json)。正式推荐层只在整组通过复核后导入。

本次覆盖七模型×三数据集×两种梯度空间。参数版沿用原始 LGA 的 MLP/FFN 权重集合，不含 bias；BLIP2 为 fc1/fc2 权重。视觉版对候选层输出的视觉 token 隐状态求梯度，等价于该位置虚拟增量 ΔHᵥ 的梯度，不是 adapter 权重梯度。

令每个样本的旧、新梯度范数为 a、b，c=dot/(a×b+1e-12)：去旧强度为 mean(c×b)，去新强度为 mean(c×a)，去方向为 mean(a×b)。逐样本计算后求均值，不能用层均值相乘或相除恢复。每个公式分别报告全部有限层的 Raw Top-3，以及全层一次 Tukey 过滤后的 Top-3（κ=1、linear 四分位数、边界保留、同分浅层优先）。

两个空间分别复用各自原始实验的冻结 model_pred 缓存及样本集合。参数版保留原来的 old=new 排除规则；视觉版严格匹配原成功样本日志。它们的样本覆盖率可能不同，因此不能把跨空间比较描述为完全相同样本的配对实验。

## 执行安排

- g08 / 作业 3435286：二十一组视觉表征补算。等待原 LLaVA L4 的 `completion_verified.json`，其中必须确认训练与完整评测已归档。
- g09 / 作业 3443209：二十一组参数梯度补算。等待原扫层队列的 `control/g09/DONE.json`。
- 等待后还需项目 GPU 锁和连续三次显存检查；视觉版空闲显存门槛 60000 MiB，参数版 74000 MiB。这是保守的启动门槛，不是实测峰值。
- 原实验失败退出不算完成，补算不会据此抢先启动。脚本不会停止其他进程或更改原实验配置。
- 新产物保存于服务器共享盘 `server_results/lga_two_spaces_ablation_20260928/results/{space}/{dataset}/{model}`。每个样本保存完整统计，参数版可按已完成层批次恢复。
- 不做 optimizer step，不训练 adapter。不会把未收敛训练、main/stable 配置混入本次定位梯度补算。

## 验证与自动导入

[样本核验](cohort_audit.json)通过全部四十二组；两种空间的 BLIP2/EVQA 实图预检查分别恢复 465（视觉）和 404（参数）个原始样本。[CPU 求导校验](autograd_validation.log)通过八次视觉梯度张量精确比较和八次参数分块梯度比较。真实模型首次计算仍会比较浅、中、深三层的新旧目标梯度，验证多层 hook 与原单层实现相符。

整组完成后复现原来的 dot、cos、旧/新范数；视觉版另检查联合范数。浮点复现门槛为 rtol=1e-3、atol=1e-8，逐层记录原值、新值及判定，任一不通过则标记 `needs_reproduction_review`，禁止自动回填。该门槛检验数值复现，不代表方法排名的统计显著性。

同步脚本检查全部逐样本文件 SHA-256，重新聚合验证层分数，再核查来源、样本数、层数和复现结果。正式表不会导入部分样本、烟测结果或失败组。旧主公式与视觉去方向结果保留归档口径；新增列只有验证通过后才回填。

在本地项目根目录按需运行：

```powershell
python -X utf8 scripts/lga_ablation_remote.py sync
```

此命令只读服务器、同步已完成组合，并重新生成 [ALL_Methods_Recommends_layers.md](../../md/Location/ALL_Methods_Recommends_layers.md) 与主总账方法目录。不会启动 GPU 工作。主总账第 3–6 节的真实扫层记录保持不变。

脚本：[严格补算](../../scripts/run_lga_two_space_ablation.py)、[排队执行](../../scripts/queue_lga_two_space_ablation.py)、[同步回填](../../scripts/lga_ablation_remote.py)。[部署哈希](deployment.json)与[进程启动凭据](launch_receipts.json)可用于后续核对。

若某组失败，查看对应 `summary.json` 和 `run_*.log`；不自动切换精度、样本或求导对象来掩盖失败。恢复时须保留原协议和逐样本文件。
