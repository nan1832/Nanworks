# VisEdit alt / pred / model_pred 存在性复核

2026-09-28 重新核对两份主文档、本地原始分数、服务器相关归档、启动器及目标选择分支。结论：结果并非“两份文件里都没有”，缺的是 MMKE 当前模型预测目标的贡献度结果。

| 数据集 | alt 结果 | 真正 model_pred 结果 | 数据集 pred 历史归档 |
|---|---|---|---|
| EVQA-pilot500 | 七模型已有 | 七模型已有，见推荐层总表 6.1.2 | 不用于本次判断 |
| MMKE-visual | 七模型已有 | 已检查归档中未找到，七组待补 | 七模型已有，见附录 A；当前原数据 pred 全空，不能解释为有效旧知识归因 |
| MMKE-entity | 七模型已有 | 已检查归档中未找到，七组待补 | 七模型已有，见附录 A；使用数据集给定旧答案 |

`model_pred` 在这个 VisEdit 实验里指基础模型在原输入上的下一 token argmax；不等于 LGA/CMA 的完整生成答案序列。`pred` 指数据集字段，不能因名称相近就把它换名成 model_pred。

证据链：

1. [MMKE 原始实验手册](../../md/Location/MMKE_visual_entity_module_contribution_experiment_manual.md)第 4 节明确记录本轮是 alt 与 pred；如需模型输出，应另开 model_pred mode。
2. [历史启动器](../../VisEdit-main/scripts/run_mmke_module_contribution_g08.sh)第 66 行枚举 `for mode in alt pred`。
3. [实际计算代码](../../VisEdit-main/scripts/run_evqa_module_contribution_pilot500_multi.py)第 482–485 行：model_pred 传 `predict_word=None`；pred 读取 `raw_data[sample_idx].get("pred", "")`。第 366–369 行：None 才走模型 logits 的 argmax，其他字符串走 tokenizer 首 token。BLIP2 脚本也有相同的目标分支，服务器代码摘要及 SHA-256 一并保存在核验文件。
4. 十四份 MMKE pred 的 `config.json` 都是 `key_mode=pred`，且本地配置 SHA-256 与服务器逐份一致，存在对应的 `contribution_layer.csv`。
5. [最新服务器核验](server_audit.json)检查了项目两处 server_results 根目录下按 contribution / visedit_key / keytoken 命名的十一个归档目录，共提取 165 份带目标模式的配置/摘要记录，读取无错误。找到的 model_pred 贡献度配置全部属于 EVQA，未找到 MMKE 对应产物。这个范围不是全服务器、所有节点临时目录的穷举，因此结论是“已核验归档缺少”，不声称任何位置绝对不存在。

额外核对了配置指向的当前原始数据：[字段核验](dataset_pred_field_audit.json)。visual_train.json 共 214 条，pred 全为空；entity_train.json 共 636 条，pred 全非空。脚本 `make_predict_word` 将空字符串变成一个前导空格，不会自动切换为 model_pred。历史文件没有单独记录当时数据输入的 SHA-256，因此这里保留该时间边界，不把当前数据哈希冒充历史输入哈希。

截图中的“MMKE model_pred 实验还没跑完”应改为“MMKE model_pred 尚未发现可核验贡献度结果，待补；已有 pred 字段历史归档另列”。目前这些归档只能证明结果缺失，不能证明实验正在运行。

本次仅补充存在性与目标来源说明，保留所有原有推荐层数值和真实扫层结果。没有启动新的 VisEdit 实验。
