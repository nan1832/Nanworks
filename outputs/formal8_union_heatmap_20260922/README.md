# 八方法Top-3联合候选真实评测热力图

生成时间：2026-09-22T09:46:16.006779+08:00

- 图中仅填充八方法Top-3并集324项，不扩展至Top-5或并集外已评测层；313项数值、11项紫框待评测。
- 紫框：EVQA/LLaVA L2,L4；MMKE-entity/LLaVA L0,L1,L2,L4,L7,L9,L11,L12,L13。
- Average全图固定0—100；格内保留两位小数，颜色使用未舍入数值。白格为并集外、灰格为模型不存在该层；没有任何方法Top-3/Top-5推荐框。
- 图下方按用户要求不放说明；图顶端仅保留标题、版本、色块状态与覆盖数量。
- 数据采用main优先，main缺失才使用stable；不跨配置取最高分。7项stable-only是MMKE-visual/PaliGemma L1,L2,L3,L5,L6,L7,L13。
- 两项main诊断结果：EVQA/PaliGemma L0=35.492，MMKE-visual/PaliGemma L0=38.520，非完整50轮、不收敛标签保留；历史数值异常同样不隐藏。
- 21组展示不表示21组公平可比：17组历史主口径、加EVQA/Pali诊断为18组，加MMKE-visual/Pali stable补齐为19组混合扩展；EVQA及entity的LLaVA仍缺评测。
- CMA两版单独保留；CMA-modelpred的EVQA/Qwen、EVQA/SmolVLM、visual/PaliGemma、visual/SmolVLM有推荐稳定性警告。图展示真实Adapter分数，不表示候选定位置信度。
- source_data.json逐格保存完整分数、配置类别、状态、来源、八方法版本和推荐层序号。来源为当前手册4.0、历史验收CSV和20260922逐层核验记录；未重新连接服务器或训练。
