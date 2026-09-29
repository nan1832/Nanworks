# 视觉—答案表征余弦：三版本补算方案与执行状态

记录时间：2026-09-28，北京时间。以下为预先确定的定义、代码验证与调度状态，不包含预测性能结论。

<!-- VISUAL_TRACK_COMPLETION_START -->
## 完成与回填（2026-09-29）

**完成时间：2026-09-29T08:37:52+0800；服务器核验时间：2026-09-29T09:18:13.102942+08:00。** 7 个模型 × 3 个数据集均已完成，每组含 none、alt、model_pred 三版，共 63 份定位统计；各自报告 Raw / Tukey，共 126 份主推荐。

全部完成后 MiniGPT4 L8 已于 2026-09-29T08:44:35+0800 自动进入续训。此处是采集时快照，当前轮次以后续训练日志为准。

推荐层与性能已回填至[总表第 8 节](ALL_Methods_Recommends_layers.md#visual-track-three-variants)和[完整结果报告](VisualTrack_Three_Variants_Results_20260929.md)。下方为保留的定义、暂停和修复历史。
<!-- VISUAL_TRACK_COMPLETION_END -->

## 2026-09-29 修复与继续执行

07:33 核验：LLaVA、BLIP2、InstructBLIP、MiniGPT4、PaliGemma 的三个数据集均已完成，共 15/21 组。原队列于 09-28 22:45 在 SmolVLM 首组停止，原因是 `append_answer` 未接纳封装保留的 `pixel_values=None`、`pixel_attention_mask=None`，并非显存不足。L8 当时尚未恢复。

07:38 按用户“继续”指令启动修复控制器。新版本仅允许上述两个像素字段为空；非空像素仍拒绝，图像继续只在固定前缀阶段编码，公式、答案位置和聚合方式均不变。原运行程序保留，已完成 15 组的协议和结果不重写。SmolVLM 的 3 个失败样本及旧协议完整归档后，剩余组使用新程序生成独立协议。5 项 CPU 测试通过；控制器先对 SmolVLM、Qwen 各验证三个数据集的前 3 个样本，通过后再补算剩余 6 组。

07:43 GPU 验证通过：SmolVLM 与 Qwen 均完成 9 个真实样本（每个数据集 3 个）的三版本检查。SmolVLM 验证样本包含 125 token 的新答案；固定图像/提示词前缀在追加答案后保持不变，输出层数与有限值检查通过。控制器已进入剩余组合的正式补算准备阶段。已完成 15 组的完整性核验、紧凑结果同步和本地推荐表生成也已完成；比较程序将 `top1_layer`（层号）与 `top1`（编辑评测分数）分开存储，避免原字段重名阻断结果生成。

07:44 核验：正式 SmolVLM 子进程已于 07:43:48 启动，控制器状态为 `RUNNING_THREE_VARIANTS`。Qwen 验证样本的新答案最长 120 token，验证通过后已排在 SmolVLM 后继续执行。[恢复运行与两模型验证回执](../../outputs/visual_track_cosine_20260928/priority_switch/repair_20260929/live_receipt.json)。

07:45 首批正式样本核验：SmolVLM × E-VQA 已保存 34/500 个样本，最近一次进度日志为 26/500、失败 0。首样本 none、alt、model_pred 均成功输出 24 层结果，原输入字段错误未再出现。[正式运行回执](../../outputs/visual_track_cosine_20260928/priority_switch/repair_20260929/first_formal_samples.json)。

仍沿用“全部 21 组校验通过 → 等待原显存门槛 → 从第 14 轮检查点继续 L8 → 恢复原队列”的顺序。修复与测试失败时保留检查点，不提前恢复训练。

- [修复部署及归档回执](../../outputs/visual_track_cosine_20260928/priority_switch/repair_20260929/stage_receipt.json)
- [修复控制器启动回执](../../outputs/visual_track_cosine_20260928/priority_switch/repair_20260929/launch.json)
- [修复运行状态与 GPU 验证](../../outputs/visual_track_cosine_20260928/priority_switch/repair_20260929/status_snapshot.json)

## 2026-09-28 历史执行记录

**19:29 执行更新：**用户授权暂停 g09 的 MMKE-entity × MiniGPT4 L8，优先完成三版本再继续。L8 的训练进程及原队列控制器已停止；第 14 轮、i=4452 的完整检查点已复制到持久共享盘并验证权重、优化器状态及 SHA-256。第 15 轮未保存的进度会在续训时重算。三版程序现由 **Job 3443209** 内的优先控制器运行，首个任务为 LLaVA；最初申请额外 GPU 的 `3463118` 已取消。g08 的 Job 3435286 原训练进程继续运行。

**19:34 运行核验：**LLaVA × E-VQA 已报告处理 26/500 个样本、失败 0。首个样本的 none、alt、model_pred 三版均已成功保存 32 层结果；当前组尚未完成，因此正式完成组合仍为 0/21。此时 g09 GPU 剩余显存约 42.56 GiB，利用率 100%，3443209 与 3435286 均为 RUNNING。[首批 GPU 输出核验](../../outputs/visual_track_cosine_20260928/priority_switch/first_gpu_verification.json)。

自动后续顺序为：7 模型 × 3 数据集的三版本结果全部校验通过 → 按原显存准入门槛等待 → 从第 14 轮检查点恢复 L8（下一轮 15、下一步 4453，目标仍为 50 轮）→ 恢复原队列的评测、归档与其他待跑层。若三版执行失败，控制器会记录错误并保留暂停检查点，不会把失败当成完成。

原检查点保存了权重、优化器、epoch、step 和 EMA，没有完整随机数状态；本次采用现有程序的检查点续训流程，不能宣称与从未暂停的训练轨迹逐位相同。恢复命令、原日志快照与此次暂停记录均已归档。[切换状态](../../outputs/visual_track_cosine_20260928/priority_switch/status_snapshot.json)、[检查点校验](../../outputs/visual_track_cosine_20260928/priority_switch/checkpoint_audit_receipt.json)、[控制器续接回执](../../outputs/visual_track_cosine_20260928/priority_switch/continue_launch.json)。

## 三个主版本

| 名称 | 答案来源 | 每个样本的分数 |
|---|---|---|
| VisualTrack-Cos-none | 不提供答案 | 视觉 token 平均表征与最后一个提示词位置表征的余弦 |
| VisualTrack-Cos-alt | 数据的 `request.target_new`，对应 alt | 视觉 token 平均表征与完整新答案各有效预测位置的余弦，先在答案内平均 |
| VisualTrack-Cos-model_pred | 同模型历史 `model_pred_cache.jsonl` | 按历史模型回答的全部可用文本，对各有效预测位置的余弦先在答案内平均 |

令图像与提示词前缀长度为 P，目标答案为 y₀,…,yₘ₋₁，第 l 层视觉 token 的平均向量为 vᵢ,l。对于答案版本，主分数为：

`S_l(y) = mean_i [ mean_{t in valid_answer_tokens(i)} cos(v_i,l, h_i,l[P_i - 1 + t]) ]`。

每个样本具有相同权重；不把全数据的所有 token 混在一起平均。`h[P−1+t]` 是预测 yₜ 的位置，只读入该答案的前缀。PAD、BOS、EOS 等特殊 token 不纳入普通答案 token 的均值，原文中的标点与普通词保留。不按编辑成绩挑选答案片段、翻转符号或调整权重。

## 为什么长回答不能仅取首 token

三版共用同一份图像与提示词前缀。在因果解码器内，预测首个答案 token 的位置尚未读入答案，其隐藏状态与 alt/model_pred 的取值无关。因此，首个预测位置无法区分两个目标；若有效答案只有一个 token，完整答案预测位置均值也会退化为该分数。这是测量对象的性质。

答案 token 自身的位置是 `P+t`，它已读入 yₜ，与预测该 token 的 `P−1+t` 不同。程序另存 `answer_read_cos` 作为“已读入答案表征”的诊断，不把它混入上述三个主版本的排名。首位置、末位置、答案有效 token 数、分词方式也逐样本记录。

实际训练数据的 alt 长度（英文词数，不是模型 token 数）：

| 数据集 | 样本数 | 中位数 | 最短—最长 |
|---|---:|---:|---:|
| E-VQA pilot500 | 500 | 1 | 1—4 |
| MMKE-visual | 214 | 41 | 20—87 |
| MMKE-entity | 636 | 74 | 29—151 |

MMKE 的新答案确实较长。model_pred 的长度取决于模型，不能认为它也都是长回答：例如历史 InstructBLIP 的两个 MMKE 缓存中，非空回答词数中位数均为 1。历史生成程序默认 `max_new_tokens=32`，缓存中存在句子未结束的回答；本轮保留缓存全部可用文本，暂不重新生成或把缺失后半段补成“完整回答”。默认值并不等于已核实每次运行的实际参数，后续长度统计仍以缓存与模型分词为准。

## 控制输入与可比样本

三版首先共同编码一次图像与提示词，再将 alt 或 model_pred 的 token embedding 追加到语言模型输入。答案不进入视觉编码器或 Q-Former。此控制尤其适用于 InstructBLIP：其现有封装会把传入文本交给 Q-Former，直接拼接答案再做视觉编码会同时改变视觉输入表征。

目标 token ID 在文本前缀稳定时采用现有教师强制分词的答案后缀；遇到拼接处 BPE 边界变化时，采用显式 continuation 分词并逐样本标记。固定图像与提示词前缀有助于独立检验答案条件的作用。这是新表示指标的预定测量协议；不改已有训练、评测或梯度数据。

主比较复用历史视觉梯度的相同有效样本 ID，三个版本在每组上具有相同覆盖率。额外保存 `available_train` 统计，空的历史 model_pred 标为不可用；不以空字符串、数据集 pred 或 alt 替代。Qwen 使用 chatfix 修复后的历史模型回答缓存。

每个版本分别计算 signed Raw 与 Tukey（κ=1，linear 四分位）推荐。与冻结的 main 扫层结果配对计算 Top-1、Best@3、Mean@3 及 Rel/T-Gen/M-Gen/T-Loc/M-Loc/Average 的层级 Spearman 相关性。Top-3 不完整时不填完整 Best/Mean@3；T-Loc 等常量指标相关性记为未定义。三版本之间的汇总只使用三方候选均完整的共同组合，覆盖率不足 80% 的组合单列。

## 切换前的部署与验证记录

- 已部署三个版本，沿用待执行 Job `3463118`，结果目录为 `server_results/visual_track_cosine_20260928/targets_v2/results`。
- v1 原始补算代码已备份。仅更新了本轮尚未启动的补算任务，3435286、3443209 的训练和既有 LGA 队列未调整。
- 调度时间上限改为 12 小时，**这是作业上限，不是运行时长预测**。
- 已通过 4 项 CPU 测试：答案预测位置与读入位置偏移、特殊 token 过滤/空答案处理、长短答案样本等权、因果前缀与单 token 退化行为。
- 尚未完成七个真实 VLM 的 GPU 运行验证。正式完成组合为 **0/21**，三版本数据均待 GPU 补算。
- 18:09 调度状态为 `PENDING (QOSMaxGRESPerUser)`；提交的额外 GPU 作业仍受账户配额限制。当前没有改变既有实验的执行顺序，也没有把绿线插入两张已用 GPU 的队列。

切换前快照：截至 **2026-09-28 18:09:55 +08:00**，两项训练状态如下；19:29 后以本文开头的暂停与补算记录为准：

| Job | 当前任务 | 轮次 | 本轮已处理 | 当前层训练进度约值 | 最近完成的轮次检查点 |
|---|---|---|---|---|---|
| 3435286 / g08 | E-VQA × LLaVA，L4 | 44/50 | 330/500 | 87.32% | epoch 43，i=10750 |
| 3443209 / g09 | MMKE-entity × MiniGPT4，L8 | 14/50 | 124/636 | 26.39% | epoch 13，i=4134 |

上述百分比只表示当前层训练的轮次进度，不包括后续评测、其他层或整个 Job。两份日志均在更新，最近读取的尾部没有新异常栈；两张卡 GPU 利用率均为 100%，剩余显存分别约 3.52 GiB、1.72 GiB。两条 LGA 后续队列仍等待原实验完成标记。

## 文件与复算

- [三版本运行程序](../../scripts/run_visual_track_targets_20260928.py)
- [位置与因果前缀测试](../../scripts/test_visual_track_targets_20260928.py)
- [部署、同步与状态程序](../../scripts/visual_track_targets_remote_20260928.py)
- [已有编辑结果的配对比较程序](../../scripts/analyze_visual_track_targets_20260928.py)
- [部署及 CPU 测试回执](../../outputs/visual_track_cosine_20260928/targets_v2/stage_receipt.json)
- [待执行作业更新回执](../../outputs/visual_track_cosine_20260928/targets_v2/upgrade_receipt.json)
- [答案长度审计](../../outputs/visual_track_cosine_20260928/targets_v2/answer_length_audit.json)
- [训练进度原始快照](../../outputs/visual_track_cosine_20260928/targets_v2/current_training_progress.json)
- [21 组补算状态](../../outputs/visual_track_cosine_20260928/targets_v2/source_status.csv)

完成组合的同步命令：`python scripts/visual_track_targets_remote_20260928.py fetch`。更新比较结果：`python scripts/analyze_visual_track_targets_20260928.py`。刷新两张卡上的训练状态：`python scripts/check_two_jobs_visual_track_20260928.py`。
