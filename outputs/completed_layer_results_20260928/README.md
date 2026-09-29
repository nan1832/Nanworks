# 最新已完成逐层评测结果图

- 总览：[PNG](completed_layers_average_main_stable.png) / [SVG](completed_layers_average_main_stable.svg)
- EVQA：[PNG](evqa_pilot500_completed_layers.png) / [SVG](evqa_pilot500_completed_layers.svg)
- MMKE-visual：[PNG](mmke_visual_completed_layers.png) / [SVG](mmke_visual_completed_layers.svg)
- MMKE-entity：[PNG](mmke_entity_completed_layers.png) / [SVG](mmke_entity_completed_layers.svg)

## 数据与绘制口径

图中展示最新扫层台账已登记的全部评测；没有候选并集筛选、Top-3 并集总数、完成率或待测候选框。
同一层的 main / stable 分行绘制，每个有分数的格内重复标注实际版本。当前 stable 结果来自 PaliGemma；未用 stable 替换 main，未跨配方取最高分。
BLIP2 × EVQA L18 的 main 复测有独立行，原 main 结果也保留。

未收敛、训练中断后恢复评测和低分结果均保留；是否有完整 50 轮、选中 epoch、EMA、训练状态及来源见 source_data.json。
常规流程按训练后的最低有限 EMA 选点；图只复用真实评测，不重新选点。
台账已提示的三项现存 history / selected 不一致（EVQA/PaliGemma main L14、MMKE-visual/PaliGemma stable L2/L13）保留原分数和 notes，不能把所有历史记录统称为本次重新验证的全程最小 EMA。
MMKE-visual/PaliGemma stable L8 是历史手工选择 Epoch13 的恢复评测，保持这一身份。

颜色为全图统一 0–100 的 Average，数值保留两位小数；图像颜色使用完整精度。白格表示当前没有已登记结果，不能解读为未推荐；灰格表示模型没有该层。
继承台账历史记录的条目仍保留原 evidence 属性；本次绘图没有再次声称全部历史原件已经在服务器核验。
SVG 文字转路径，可不依赖本机字体无损放大；PNG 使用 300 dpi。

## 后续更新

在项目根目录依次运行：

```powershell
python scripts/update_sweeplayers.py
python scripts/plot_completed_sweep_results.py
```

前者只读核对服务器并更新台账，后者从最新台账重画。

数据更新时间（服务器，北京时区）：2026-09-28T11:10:16+08:00。
