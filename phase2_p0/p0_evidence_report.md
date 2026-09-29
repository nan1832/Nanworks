# 第二阶段 P0 实际证据核验报告

日期：2026-09-11。范围：第一阶段真实代码、配置、定位排名、训练/评测记录、selected checkpoint 元数据与单样本接口。本轮未启动训练，未修改 v2.1 手册，未开展 G2—G6。

## 1. 独立结论

| 核验项 | 结论 | 边界 |
|---|---|---|
| 静态证据核验 | **完成** | 明确列出未取得的历史信息；不是“所有未知值已消除” |
| 单样本接口探测 | **通过** | 3178538 / g08，真实加载器、eval 第 0 条、L0 selected checkpoint；原始日志已保存 |
| Ours 目标层 | **已确认 L0，Top-3 为 L0/L1/L2** | 对应正式无深度权重主公式；定位覆盖率仅 284/636，44.6541% |
| Adapter hook | **已确认 post-block** | `language_model.model.decoder.layers.0` 输出的视觉 `[0,32)`；静态路径与动态观察一致 |
| 能否进入 P1 数据核验 | **可以** | 服务器实际 train/eval 和图片可访问；尚未宣称官方来源、去重及泄漏检查通过 |
| 能否进入 G1 复现 | **P0 层号与接口前置已满足，可进入复现准备；本轮不启动训练** | 启动前完成 P1、冻结“严格第一阶段复现”或“新 dev 协议”、分别确定 L0/L1 对照及资源窗口。若要求 L0 历史 seed 逐项严格重放，还需其原始 seed 日志 |

单样本通过只证明当前环境下已选 checkpoint 的接口、hook 和前向可运行，不证明重新训练可复现全部历史指标，也不证明第二阶段新模块或 Portability 已实现。

## 2. 证据范围与来源可靠性

- 本地项目根：`D:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset`。
- 服务器可运行工程根：`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main`；其上级 `Visedit2` 存放数据和 server_results。
- 报告目录：两端各自工程根下 `phase2_p0`。下文简写 `B/` 为 `md/TODO/Second_prashe/第一阶段真实代码_BLIP2_MMKE-Entity/`，`R/` 为服务器可运行工程根。
- `B/SHA256SUMS.txt` 的 **17/17** 项本地内容匹配；详见 [bundle_integrity.json](bundle_integrity.json)。服务器当前 runner、VEAD、Adapter、训练基类、BLIP2 加载器/基类、utils、GLOBAL、nethook、数据类、评测器和 YAML 共 **12 项**与包内对应文件匹配，详见 [server_bundle_hash_comparison.json](server_bundle_hash_comparison.json)。没有拿已修改的本地同名工程文件代替训练快照。
- 原始 Ours layer score 在服务器与本地哈希一致：`b6f741b9f13b2d3b82bd9efa685f078126a0267fc92a6918b3effa21c831dff7`。定位复算没有依赖手册的 L0 假设。
- [evidence_manifest.json](evidence_manifest.json) 保存关键输入路径、大小与哈希；历史日志的提取见 [runtime_log_excerpts.json](runtime_log_excerpts.json)。日志行号按 `splitlines()` 展开 CR/LF 后计数，源码行号是普通文本行号。
- 搜索使用文件名与文本关键词，未对模型权重做文本扫描。动态探测通过真实加载器读入基础模型；额外只对明确选中的 L0/L1 checkpoint 在 CPU 读取优化器/模块键等元数据。没有重算定位梯度，也没有做参数更新。
- 默认 SSH 认证最初失败，随后使用项目既有密钥 `id_ed25519_bridge` 成功连接；密码未写入本轮文件。探测使用既有 job 3178538 的一个临时 `srun --overlap` step，没有新增 Slurm job。

## 3. 定位到 Adapter 的证据链

### 3.1 Ours 原始分数、公式和排名

原始服务器文件：

`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/ours_direct_7models_3datasets_g08_gpu0_20260626_131624/mmke-entity/blip2-opt-2.7b/ours_direct_layer_scores.csv`

本地副本：`md/Location/VisualGradient_11formula_analysis_files_20260720/raw_layer_scores/mmke-entity/blip2-opt-2.7b/ours_direct_layer_scores.csv`。

正式公式来源：`md/Location/6location_7model_3datas_top_3_5_layers_outcome.md:260–282,830` 明确指定 `M_abscos_x_newn = abs(S_v_cos) * S_v_new_norm`，不含深度权重。`analysis_outputs_20260731/formula_topk_all_21.csv` 对应行记录 Top-1 L0，Top-3 L0/L1/L2。`scripts/analyze_visual_gradient_formula_evidence.py:235–282` 给出有效层过滤及降序排序规则。

本轮 [collect_evidence.py](collect_evidence.py) 从原始 CSV 独立复算，排除 zero-grad、invalid_reason、缺失视觉 span、非有限 cos/norm/score，按分数降序、同分层号升序，结果与历史排名一致：

| Rank | 层号 | `abs(cos) * new_norm` | 原始 module path |
|---:|---:|---:|---|
| 1 | 0 | 0.05071359254856098 | `language_model.model.decoder.layers.0` |
| 2 | 1 | 0.023807711423021117 | `language_model.model.decoder.layers.1` |
| 3 | 2 | 0.017035812060378103 | `language_model.model.decoder.layers.2` |

原始 CSV 自带的 `ours_rank` 按旧 `S_ours` 排序，不能直接用该列代表新主公式排名。旧 conflict_main / 深度加权公式 Top-3 是 L20/L19/L18。完整复算结果保存在 [ranking_recomputed.json](ranking_recomputed.json)。有效请求 284/636；历史冻结表报告 352 条 empty_model_pred，覆盖率不足，因此这里只确认“该公式在现有有效数据上的排名”，不宣称全量高可信定位。

现有定位源码 `VisEdit-main/scripts/run_ours_direct_candidate_layers.py:566–602` 在 block **输出**注册 forward hook 保留 hidden gradient；`:787–789` 用 `range(num_layers)` 和完整 layer_path。该实现与原始 CSV 的路径/视觉 span 相符；本轮未重新执行梯度定位，也未取得该历史定位进程的完整依赖锁。

### 3.2 实际训练链与本轮探测链

**Job 3126082 / L1**：L1 属于当前主公式 Top-3 → launcher `B/launcher/launch_actual_job3126082.sh:279` 显式 `run_layer ... blip2-opt-2.7b 1` → `:188–205` 组装 `--layers 1` → runner `parse_layers:120–131` 得到整数 1 → `make_config:290–293` 将 YAML `[19]` 覆盖为 `[1]` → `VEAD.init_hook_adaptors:161–171` 定位 `language_model.model.decoder.layers.1` → 注册 post-block Adapter。日志、TSV、checkpoint 内 `train_modules` 键全部一致。

launcher 是人工冻结的补层队列，**没有读取排名 CSV 的自动接口**；现有材料支持“补训 Top-3 中缺少的 L1”，不能声称程序自动将 Top-1 映射到 L1。当前 Top-1 L0 的原始历史 CLI 日志未全部取得，但它自己的 saved config、selected、loss_history、checkpoint module key 和 eval.done 已取得。

**本轮 Ours Top-1 / L0**：原始分数复算 L0 → [probe_command.json](probe_command.json) 的 `--layer 0` → 导入真实 runner 的 `make_config(...,0)` → `[0]` → `language_model.model.decoder.layers.0` → 实际 Adapter forward hook → 加载 module key 同为该路径的 L0 selected checkpoint → 单样本动态通过。此链没有用 L1 checkpoint 冒充 L0。

### 3.3 层号基准和必须分开的四类信息

| 信息 | 值 | 证据性质 |
|---|---|---|
| YAML 默认 `edit_layers` | `[19]` | 配置模板 |
| Job 3126082 实际训练/评测层 | `[1]` | CLI、源码覆盖、历史日志 |
| L1 selected checkpoint | epoch 11 / step 3498 / EMA 5.9904003300769855 | TSV + checkpoint 内容 |
| Ours 正式预测 | Top-1 L0；Top-3 L0/L1/L2 | 原始分数 + 公式 + 排名复算 |

层号从 **0** 开始。`layer_01` 的 `01` 是补零格式，不是第 1 个 block：runner 数值 1 → decoder 索引 1 → 第 2 个 decoder block。`layer_00` → 索引 0 → 第 1 个 block。无 +1/-1 换算。

## 4. 真实 hook 语义

| 路径 | 执行内容 | 可否证明 Adapter 输入编辑 |
|---|---|---|
| `VEAD.init_hook_adaptors:149–174` | `register_forward_hook`；tuple 转 list，修改 `outpt[0]`；Tensor 输出直接交 Adapter | **不能**；它明确是 post-block |
| runner `official_visual_forward:50–95,116` | 覆盖类的 forward；仅改视觉段残差，保留 dtype | 真实输出编辑执行体 |
| `get_edit_signal_for_one_request:245–257` | 关闭 Adapter；TraceDict 读取编辑层输出，stop=True；编码 prompt+image+target_new | 观测/建立编辑信号 |
| `preprocess_train_data:333–378` | Trace 读取最早所需层的输入并缓存 | 读取 block 输入，不等于在输入处编辑 |
| `infer_from_mid_layer:264–284` | L0 直接调用；其他层临时跳过更早 block，并用 `edit_input` 重放缓存输入 | 中间层重放可用 pre-hook，但 Adapter 仍在输出处 |
| `utils/nethook.py:89–141` | retain_input 在 forward hook 保存；通用 pre-hook 可选执行 edit_input | pre-hook 的存在不能独立说明 Adapter 位置 |

`infer_from_mid_layer` 中关于“Layer-0 input edit runs as a forward pre-hook”的注释不是注册证据，与当前统一 post-block Adapter 路径不符。

输入到 LLM 的结构为 `{'inputs_embeds': [B,S,2560], 'attention_mask': [B,S]}`，另传 `vt_range`。BLIP2 先生成 Q-Former query，经 `language_projection` 后与文本 embedding 拼接；`vt_range=[0,num_query_tokens)`，本轮实测 `[0,32)`。`get_llm_outpt` 包装器在每次推理前调用 Adapter `set_input_info`。

Adapter 接收的是 block 第 0 个输出 Tensor `[B,S,D]`；不是 `(args,kwargs)` 输入结构。真实 block 输出 tuple 被 hook 转为 list，第 0 项替换，其他项保留。当前 Transformers 4.46.3 路径实测接受此结构，不把该版本观察推广到其他版本。

`official_visual_forward` 在关闭 Adapter、序列长为 1 或无图时直接返回；激活时用 `edit_reps`/mask/prompt_end 构造跨注意力与 InfluenceMapper 门控，只写 `[:,vt_begin:vt_end]`。**只直接修改视觉 token 不代表下游文本 logits 不变**；后续 decoder 自注意力仍可传播影响。

## 5. 第一阶段有效训练协议

| 项目 | 核验结果 | 状态与入口 |
|---|---|---|
| Adapter 类及构造 | `VisionEditAdaptor(2560,1024,8,32,True,1024)` | 配置记录、源码确认、本轮 L0 构造实测；`vead.py:168–170` |
| active forward | runner 的 `official_visual_forward` monkey patch | 源码确认、本轮日志确认 |
| 冻结范围 | 基础 VLM eval + requires_grad=False；仅 adaptors 可训练 | 源码 `vead.py:733–741` |
| optimizer | Adam；每个 adaptor 一组，包含 InfluenceMapper，L0/L1 各 1 组、26 个 parameter tensor | 源码 `:728–731` + 两个 selected checkpoint 的 opt 参数组 |
| lr / betas / eps | 1e-4 / (0.9,0.999) / 1e-8 | YAML + saved config + checkpoint 内容确认 |
| weight_decay / amsgrad | 0 / false | checkpoint 内容确认，不是从库常识推测 |
| 其他 optimizer 字段 | maximize=false, capturable=false, differentiable=false, foreach=null, fused=null | checkpoint 原值；null 在此是合法 None，而非缺失 |
| loss | rel CE×1；text/image generality 各 CE×1；text/image locality 各 KL×1；IT 三分量各系数 0.1 | 配置+源码 `vead.py:641–704,743–776` |
| Influence Trace | add_it=true；层20–30；test_n=1，noise=0.7，window=0，vt_sample_n=24，mid_dim=1024 | YAML 与两层 saved config；不是视觉 token 总数24 |
| 训练预算 | 50 epoch；batch=2；636 条，318 step/epoch，共15,900 step | 配置、L1 日志、L0/L1 各50行 loss_history |
| CLI seed / L1 有效 seed | 20260601 / **20260602** | runner `random_seed=args.seed+layer`；日志两处确认20260602 |
| L0 历史 seed | 本轮未取得原始 seed 日志，配置中保留 null | 当前根 run_config 已被 L23 调用覆盖；不把推导值当运行实证 |
| RNG / 初始化 | torch/CUDA/NumPy/random 全设种子，cudnn benchmark=False、deterministic=True；无恢复时重新初始化训练模块 | `base_editor_training.py:152–226`；L1有重初始化日志 |
| EMA / 选点 | 每 batch 更新 EMA，alpha=.1，初值1；每318步存档，选择存在且有限的最小 checkpoint EMA | 源码+历史复算；不是 dev accuracy 或最后一个epoch |
| 数据 buffer / scheduler | buffer=4；追踪路径中无 scheduler | CLI+源码 |
| 保留规则 | L1 CLI keep_top=1、keep_last=0；训练期清理取 EMA-best 与 raw-loss-best 的并集；launcher 完成评测后仅保留 selected | `runner:193–241`、`launcher:153–179`；不能理解为训练期永远只有1个文件 |

训练数据缓存包含每个 request 的 edit signal 和 rel/gen/loc 中间输入。`train_a_batch` 用当前 batch 的请求信号调节共享 Adapter，累加损失并优化 Adapter 参数；不逐样本从头训练新的编辑器。训练还加载独立的数据处理 VLM，原 L1 日志显示两次模型加载；本轮无训练，仅加载一次推理模型。

### 5.1 Selected checkpoint 与实际预算

| 层 | 训练完成 | selected | checkpoint module key | 历史 Average |
|---|---|---|---|---:|
| L0 | 50 epoch / 15,900 step | epoch24 / step7632 / EMA6.1242322191733995 | `language_model.model.decoder.layers.0` | 65.856 |
| L1 | 50 epoch / 15,900 step | epoch11 / step3498 / EMA5.9904003300769855 | `language_model.model.decoder.layers.1` | 72.504 |

L1 的 50 行历史由本轮独立求最小 EMA，与 TSV 和 checkpoint 内容一致；L0 服务器历史亦同。`train.done` 的 `epoch` 是 selected epoch，不是训练停止 epoch。

L1 原 `/tmp/...job3126082...` 路径已经迁移到共享盘：

`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/tmp_archives_20260810/g09/mabscos_top3_completion_job3126082_20260801/mmke-entity/blip2-opt-2.7b/layer_01/records/vead/blip2-opt-2.7b/pilot500_blip2_visedit_L01-lr-1-t-1-v-1/checkpoints/epoch-11-i-3498-ema_loss-5.9904`

L0 完整路径、两层 saved config、checkpoint 元数据、optimizer 参数组及历史选点保存在 [server_protocol_audit.json](server_protocol_audit.json)。未复制大 checkpoint 到本地。

## 6. 数据、评测和编辑请求生命周期

真实 train/eval 位于：

`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/mmke_entity_top3_union_train_eval_7models_20260616_155000/data/`

| 文件 | 当前服务器条数 | 当前 SHA-256 |
|---|---:|---|
| `vqa_mmke_entity_train_evqa_compat.json` | 636 | `8871706ce094f683418bd576954d231c6354e3dd53e7b8c2200f54e129df012d` |
| `vqa_mmke_entity_eval_evqa_compat.json` | 954 | `18e17ad906a313b79c5c3e6c7af340bf8aa5bb8f415490ee95b320184579bf68` |

图片根：`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/datasets/MMKE-Bench/data_image`。本轮检查两份 JSON 首条记录所需的3种图片路径存在；动态样本加载成功。没有在 P0 对全量图片做验证。

`EVQA:58–104` 读取前 `min(data_n,len(data))` 条，None=全量，无额外过滤。train/eval 两个 sample_n 均为 None。训练不是只用定位有效的284条；954是 eval 外层 request 条数，评测源码 `sample_count=len(results)`，不是五项指标相加得到的数量。

字段映射：`src→request.prompt`、`alt→target_new`、image、rephrase、image_rephrase、loc/loc_ans、m_loc/m_loc_q/m_loc_a。编辑/两种泛化/图像locality prompt追加 ` The answer is:`；文本locality追加 `?`。`pred` 不进入该 EVQA 编辑信号。runner 对图片加载作 RGB copy + 文件关闭兼容处理。

**指标入口**：runner `eval_one_layer:371–407` 创建 `VLLMEditorEvaluation` 并调用 `evaluate_single_edit`；后者 `:29–98` 对每个独立请求先记录 locality 的原始 argmax，再 `edit_one_piece`，计算 rel/gen/loc 后 `restore_to_original_model`。`get_mean_results:100–149` 做平均，`save_results:151–166` 保留4位小数；runner 再乘100并取五项均值。

- Reliability / T-Gen / M-Gen：target-conditioned、teacher-forced masked token accuracy；不是自由生成整句精确匹配。`prompts_imgs_target_to_xym:76–110` 拼接 prompt+target，shift labels并构造mask。
- T-Loc / M-Loc：同一 target-conditioned 输入上的编辑前后 argmax token 一致率。源码打印字段 `predict_before_edit` 解码的是 label_ids，不能用这个展示字段替代真正计算使用的 `before_edit_ids`。
- `BLIP2.get_llm_outpt:65–71` 使用 `use_cache=False, return_dict=True`；训练和本次历史评测路径没有调用 generate，num_beams/max_new_tokens/temperature 等解码配置不适用。定位阶段为了 old=model_pred 的生成是另一个协议，不能混入编辑指标口径。
- 第一阶段正式结果中没有 Portability；未知值不能填0，也不能将 P3 的 Portability 阈值当已测证据。

**测试时编辑请求**：共享 Adapter 参数从 selected checkpoint 加载；每个请求用 prompt+image+target_new 在关闭 Adapter 时提取编辑层输出，设置 edit_reps、mask、prompt_end，再打开 Adapter。`restore_to_original_model` 关闭 Adapter并清空请求信号；并非重新初始化共享权重。测试不调用 optimizer.step。

原始官方 JSON 与 EVQA-compatible 转换是否逐条等价、实体/图像对应是否属于预期反事实编辑、train/eval是否有重叠及如何 group split，留给 P1；本轮不由文件名或不同路径推断这些已通过。

## 7. 单样本探测记录

脚本：[probe_single_sample.py](probe_single_sample.py)。原始日志：[probe_L0.log](probe_L0.log)。命令：[probe_command.json](probe_command.json)。probe 不构造替代 LAVIS 模型；导入第一阶段 runner，只触发其接口定义及已知 monkey patch，不调用 main/train/train_init。使用真实 `EVQA(...,data_n=1)`、`load_vllm_for_edit`、`make_config`、`VEAD`、`load_ckpt(...,load_opt=False)` 和 request 编码。

运行环境：job **3178538**、node **g08**、Python3.8.16、torch2.2.0、transformers4.46.3、cuda:0。入口空闲显存51,829,342,208 bytes；探测是临时已有 allocation step。job3178423/g07未被用于模型探测。基础模型权重使用服务器已有目录，设置 offline 模式。

样本：实际 eval JSON 第0条；image=`entity/Secret (South Korean group)+12.jpg`；使用原 EVQA prompt后缀和该记录完整 alt，没有另建手工样本。L0 checkpoint epoch24/step7632，不是小包内 L1 epoch11。

| 实测项 | 结果 |
|---|---|
| 模型 | BLIP2OPTForEdit / Blip2ForConditionalGeneration / OPTForCausalLM |
| decoder | OPTDecoderLayer，32层，hidden size2560 |
| 输入 embedding | float32 `[1,201,2560]` |
| LLM attention mask | int64 `[1,201]`；block收到 attention_mask=None、position_ids `[1,201]` 等kwargs，原样记录 |
| 视觉 token | `[0,32)`；文本从32开始 |
| labels / mask | `[1,120]` / `[1,120]` |
| block原始输出 | tuple，第0项float32 `[1,201,2560]` |
| Adapter后block输出 | list，第0项float32 `[1,201,2560]` |
| logits | CausalLMOutputWithPast.logits，float32 `[1,201,50304]`，全有限 |
| 编辑请求编码阶段 | Adapter关闭；观察pre、block原始输出、Adapter输入/输出、block最终输出各1次；视觉/非视觉差均0 |
| 编辑后查询阶段 | 同五处各1次；Adapter打开；视觉max abs delta=**15.878780364990234**，非视觉直接delta=**0** |
| 参数更新 | **0**；no_grad，基础模型与Adapter均冻结，参数_version前后相同、grad全None；无optimizer step |

总共是**同一个样本的两次语言路径调用**：一次编辑信号提取（在L0 stop），一次完整编辑后查询；没有把两次触发误报为一次。探测额外注册的 pre-hook仅观测，真正的表征改写仍由原 Adapter post-hook执行。程序结束移除观察hook、关闭Adapter并移除其hook，进程退出。

本轮不验证训练中 `infer_from_mid_layer` 的 backward/optimizer，也不进行生成、完整指标重评或性能回归。当前前向通过不能替代这些未来验证。

## 8. 已知缺口及下一步边界

1. **P1可开始**：全量官方源文件/转换来源、ID和图片对应、缺图/重复、train/eval交叉污染、实体/图像group规则仍待正式核验。新增dev split没有创建。
2. **G1要先确定协议**：严格第一阶段数值复现使用636训练/954评测、相同层和checkpoint选点规则；新dev实验另建manifest、重新训练G1。不得混用两者结果。新dev划分不阻止先做严格复现准备，但训练启动仍不在本轮授权范围。
3. **历史精确环境**：当前12项核心源码与包一致、模型可运行；没有取得原始训练完整依赖锁和基础权重全文件哈希。需要逐位/严格数值复现时应补齐环境冻结。本轮配置中这些项为null。
4. **L0历史seed**：历史saved config不含有效seed；model根run_config已被后续L23评测覆盖。L1有效seed有明确日志；L0若要求历史seed逐项确认，需补原始启动/seed日志，不能冒用L1的20260602。
5. **定位可信度**：L0排名真实可复算且hook已验证，但44.65%的有效样本覆盖率应保留在研究报告；是否重做低覆盖定位属于后续研究决策，本轮未重跑。
6. 手册冲突详见 [p0_manual_conflicts.md](p0_manual_conflicts.md)。可机读有效值与未知值详见 [p0_effective_config.json](p0_effective_config.json)。该JSON是证据记录，不是已获授权的训练启动配置。
