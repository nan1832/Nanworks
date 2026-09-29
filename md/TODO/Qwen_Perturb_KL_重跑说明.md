Qwen 的问题已经定位清楚了：

> **不是数据、显存、CUDA、视觉 token 或 hook 的问题，而是当前 Python 环境里的 `transformers` 不支持 Qwen2.5-VL 对应的模型类。**

日志显示500张图片已经全部正常加载，随后在加载模型时执行：

```python
from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
```

但当前环境：

```text
/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/
```

中的 `transformers` 无法导入 `Qwen2_5_VLForConditionalGeneration`，因此模型尚未初始化就退出了。fileciteturn19file0

## 当前影响

这次失败发生在：

```text
图片加载完成
→ 加载Qwen模型
→ 导入模型类失败
```

因此：

- 没有开始任何层的 KL 计算；
- 没有产生候选层分数；
- 没有 `summary.json` 和 `DONE`；
- EVQA-pilot500 的 Qwen 组合缺失；
- MMKE-visual 和 MMKE-entity 的 Qwen 组合如果继续使用同一环境，也会同样失败。

## 推荐修复方式

不要直接升级当前共享 Jupyter 环境，避免影响正在跑的其他模型。优先使用项目中已有的 Qwen 专用 Python 环境。

先查找：

```bash
PROJECT="/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main"

grep -RIn \
'PY_QWEN=' \
"$PROJECT/scripts" \
--include='*.sh' |
head -n 30
```

找到类似：

```bash
PY_QWEN=/某个环境/bin/python
```

然后测试该环境：

```bash
PY_QWEN="/查到的Qwen Python完整路径"

"$PY_QWEN" - <<'PY'
import transformers

print("transformers version:", transformers.__version__)
print("transformers path:", transformers.__file__)

from transformers import AutoProcessor
from transformers import Qwen2_5_VLForConditionalGeneration

print("Qwen2.5-VL import: OK")
PY
```

如果输出：

```text
Qwen2.5-VL import: OK
```

说明这个环境可以补跑 Qwen。

## 对比当前错误环境

```bash
PY_OLD="/datapool/home/ph_teacher3/lzh/.lico_env/jupyter/env/bin/python"

"$PY_OLD" - <<'PY'
import transformers

print("version:", transformers.__version__)
print("path:", transformers.__file__)
print(
    "has Qwen class:",
    hasattr(transformers, "Qwen2_5_VLForConditionalGeneration")
)
PY
```

预计会显示：

```text
has Qwen class: False
```

## 下一步处理建议

当前其他模型可以继续跑，不必停止。等找到可用的 `PY_QWEN` 后，单独补跑以下三个组合：

```text
EVQA-pilot500 × Qwen2.5-VL-3B
MMKE-visual × Qwen2.5-VL-3B
MMKE-entity × Qwen2.5-VL-3B
```

补跑之前先查看命令参数：

```bash
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main

"$PY_QWEN" \
scripts/run_perturb_kl_direct_candidate_layers.py \
run-one --help
```

核心结论是：

> **Qwen 被列入了任务，但通用 Jupyter 环境中的 `transformers` 版本或构建不兼容 Qwen2.5-VL，导致模型导入失败。需要改用能够成功导入 `Qwen2_5_VLForConditionalGeneration` 的 Qwen 专用环境后补跑。**
