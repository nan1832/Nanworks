# v2.1 手册与 P0 实际证据冲突

核验日期：2026-09-11。本轮只记录冲突，不改写手册，不实施 G2—G6。

手册路径：`md/TODO/Second_prashe/第二阶段实验手册_知识图谱增强视觉语言模型编辑_v2.1.md`。
以下行号均针对本轮哈希清单记录的版本；第一阶段代码简写路径相对于 `md/TODO/Second_prashe/第一阶段真实代码_BLIP2_MMKE-Entity/`。

## 1. P0 硬编码 L0 与 E.1.5 的关系

- 手册 L39、155–175、207 和 P3 L879 预设 L0；E.1.5（L2850–2870）却列为待澄清阻塞项。这种“未核验但可直接执行”的表达冲突成立。
- E.1.5 将 L0 定位结论与 L1 的一次训练证据并列为层号冲突，但两者描述的对象不同。YAML `[19]` 是模板默认值；`--layers 1` 是 Job 3126082 的实际训练层；L1 checkpoint 与此一致。这三项并不决定定位 Top-1。
- 本轮已发现并复算正式主公式 `M_abscos_x_newn = abs(S_v_cos) * S_v_new_norm` 的原始分数，Top-1 为 **L0**，Top-3 为 **L0、L1、L2**。因此 E.1.5“L0 无任何证据文件支持”的说法仅适用于其原先提供的小包范围，不适用于完整项目证据。本轮没有把 L0 改为 L1。
- 旧 `conflict_main / S_ours` 或带深度权重的 `Ours-Direct-Conflict` 得到 L20、L19、L18，不能替代已冻结的无深度权重主公式。正式排名虽然可复算，定位有效样本为 284/636（44.6541%），不能把汇总表 `done` 扩写为全样本高可信定位。
- L0 另有真实 selected checkpoint：epoch 24 / step 7632；L1 为 epoch 11 / step 3498。不得交换引用。

## 2. P3 与 E.1.3 / 真实协议冲突

| 项目 | P3 草案（L874–911） | 第一阶段有效行为 | 影响 |
|---|---|---|---|
| Config 接口 | `model_name, hidden_size, num_layers, edit_layer, ...` 平铺构造 | `VEADConfig` 使用 `edit_model_name, llm_hidden_size, edit_layers, train_cfg, IT, ...`；runner 从 YAML 加载再覆盖层号 | 不能直接运行该代码块 |
| Editor 构造 | `VEAD(config)` | `VEAD(vllm, config, device, vllm_data_proc, data_proc_device, cache_root)` | 缺模型及必要初始化 |
| 训练调用 | `editor.train(train_data, seed=42)` | 先 `train_init(...)`，再 `train(total_epochs)` | 参数签名不匹配 |
| 保存 | `save_checkpoint(...epoch_15.pt)` | `save_ckpt(i, epoch, loss, ema_loss)`；selected TSV 指向最小 checkpoint EMA | 不存在该同名接口 |
| 数据类 | `dataset.mmke_entity.MMKEEntity` | 真实 runner 使用 EVQA-compatible JSON + `EVQA` | 新数据接口是草案 |
| 学习率 | `5e-5` | `1e-4` | 严格复现不得混用 |
| Locality 权重 | `0.1` | `1`，每个 locality 项分别加权 | 损失尺度不同 |
| InfluenceMapper 权重 | `0.01` | `0.1`，相对分布、rel/gen 上调和 locality 下调三项分别参与 | 不能简化成另一训练目标 |
| `infm_dim` | `256` | `1024`，由 `IT.mid_dim` 覆盖形参默认值 | 结构及 checkpoint 形状不同 |
| 预算 | 15 epoch | L1 日志和 50 行历史确认完成 50 epoch / 15,900 步 | selected epoch 11 不是训练预算 |
| seed | 42 | CLI base seed 20260601；`train_init` 使用 `base + layer`，L1 日志实证 20260602 | E.1.3 的“实跑种子=20260601”不够准确 |
| 选点 | 固定 epoch 15 或 dev_val 选择 | epoch 边界 checkpoint 的最小 EMA；EMA 按每个 batch 更新 | 新 dev 选点是不同协议 |

E.1.3 对 lr、权重、Adam 和预算的修正有源码支持，但没有同步回 P3。E.1.3 L2816 若意指 CLI seed，可保留 20260601；若意指 L1 所有 RNG 的实际 seed，则必须写 20260602。checkpoint 路径里的 `lr-1-t-1-v-1` 来自缺失命名元数据的占位值，不代表学习率为 -1。

## 3. “已由项目代码验证”标签超出了证据

| 代码块 | 标签与行号 | 实际问题 | 可支持的结论 |
|---|---|---|---|
| P0 视觉 span | 已验证，L117–136 | 依赖上一个 LAVIS 草案；`inputs_opt`、`inputs_embeds` 没有实际赋值 | 第一阶段源码支持视觉前缀布局，不能证明该示例跑过 |
| P0 hook | 已验证，L146–170 | `lm` 来源为 LAVIS，输入变量未定义；观察 hook 只打印、不调用真实 Adapter | `vead.py` 支持 post-block 语义；该代码块不是 Adapter 动态验证 |
| P3 G1 训练 | 已验证，L864–911 | Config/Editor/train/save 的真实签名均不匹配，且参数、预算与 E.1.3 矛盾 | 整块只能作为待适配方案 |
| P5 G0 | 已验证，L1231–1244 | LAVIS 重新加载，`evaluate(model, eval_data)` 未定义；不是第一阶段工厂和评测器 | “无 Adapter 的对照组”是研究要求，不是执行记录 |

P0 步骤 1（L82）及 model_registry（L182）已明确标注伪代码，本轮不把它们误报为“声称运行通过”。模型字段 `model.opt_model / model.Qformer / model.opt_proj` 属于 LAVIS 示例；真实接口是 Transformers `model.language_model / model.qformer / model.language_projection`。

## 4. Hook 与路径的具体修正点

- `vead.py:149–174` 用 `register_forward_hook`，在 block 输出修改视觉 token；不是 Adapter pre-hook。收到 tuple 时，函数先转 **list**，替换第 0 项，然后返回 list，没有转回 tuple。
- `infer_from_mid_layer:264–284` 的 L0 pre-hook 注释与当前 Adapter 注册不符。其 L0 分支只是调用 `get_llm_outpt`；其他层分支用 TraceDict 临时替换早期 forward 并重放缓存输入。这是中间层推理路径，不是将 Adapter 移到输入端。
- Trace 的 `retain_input=True` 是在 forward hook 中保存输入；通用 Trace 还会注册 pre-hook，但未给 `edit_input` 时不执行输入编辑。不能按 pre-hook 数量认定 Adapter 编辑位置。
- 实际模块路径相对于完整 `vllm.model` 是 `language_model.model.decoder.layers.0`；只有相对于 `vllm.model.language_model` 时才可省略 `language_model.`。
- 第一阶段 README 的模型源文件映射写为 `editor/vllms_for_edit/blip2.py`；服务器实际文件是 `editor/vllms_for_edit/blip2/blip2.py`。本轮核对后者哈希与快照 `code/model/blip2.py` 一致。
- E.1 的 2560 是配置证据；“不需 P0 探测”不能替代本轮要求的真实对象及张量形状核验。

## 5. 严格复现与第二阶段新划分必须独立记账

**第一阶段严格复现**：使用已存档 EVQA-compatible train 636 / eval 954、同一 prompt 改写、视觉 post-block Adapter、同一 IT/损失/优化器、50 epoch、CLI base seed 加层号、最小 checkpoint EMA 选点。先按 L1 复核现成 baseline；Ours Top-1 的 L0 对照则使用自己的 checkpoint 和指标。两层分别报告。

**第二阶段新 dev 实验**：在确认官方数据来源后，按实体/图像 group split 划分 dev_train/dev_val，固定样本 ID 与 split manifest；超参和选点只在 dev_val 上决定，official eval 保留最终评测。509/127 只是理想近似，不能在 group split 前当作实际样本数。相同新划分和预算下重新运行 G1，供后续新模块比较；不能把它称为对 L1/636 样本协议的严格数值复现。

第一阶段指标是 masked teacher-forced token accuracy / 编辑前后 argmax 保持率，不是自由生成整句 EM；其正式结果无 Portability。新增 1-hop Portability、自由生成评测或 dev 选点，均需单列第二阶段协议。本轮没有实现这些变更。

## 6. 新发现的记录覆盖问题

服务器原始 Top-3 union 模型目录的 `run_config.json` 已被后续 `layers="23"` 的评测调用覆盖，不能用它反推 L0 的历史命令。L0 需要自己的 selected、训练记录中的 config、loss_history 和 checkpoint 内 module key；本轮独立保存了这些证据。与此类似，小包 `actual_run_config.json` 的 `skip_train=True` 是 L1 末次评测阶段，不表示 L1 没训练。
