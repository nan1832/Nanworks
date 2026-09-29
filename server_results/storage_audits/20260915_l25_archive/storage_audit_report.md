# L25归档、临时存储审计与L0耗时估算

日期：2026-09-15；服务器动作限定为用户明确授权的EVQA-pilot500/LLaVA L25归档与临时副本删除。其他层仅检查。

## 执行结果

**共享归档完成；L25临时副本删除完成。** 结果重新核验2,093条，selected Epoch50/step12500/EMA0.3291842153238946，Average60.888。

共享目录：`/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/formal_top3_stage2_20260812/job3150065/evqa-pilot500/llava-v1.5-7b/layer_25`。

selected checkpoint SHA-256：`1d68657620140b5c3c4ecf3cdf618b9b23d7b6d5b1a170ec902ab52554743871`。

归档保留唯一selected实体、train.done、selected_checkpoint.tsv、eval_full.done、完整results/mean_results、loss_history、训练配置、TensorBoard日志、两份L25训练/评测日志、当前launcher/runner快照及来源说明。运行标记中的L25绝对路径已改为共享路径，原始内容另存provenance/source_metadata。模型级run_config快照属于L0，明确标注，未冒充L25历史配置。

11份源文件/独立日志对应项均核验SHA-256；修改路径的文本另验精确prefix替换；checkpoint源/目的SHA-256一致。共享目录写入SYNC_VERIFIED后再次进行完整性验证。

删除4个精确目标：L25层目录、cache/layer_25、两份L25独立日志。2011个文件；删除前无活动引用、外国所有者、符号链接或路径重叠。所有目标在后验检查中均已不存在，L0进程与缓存仍在。没有清空父目录或改动原队列锁、配置、其他层。

标准cleanup脚本默认拒绝包含正式结果标记的目录。本轮使用限定包装器：只对本次L25逐文件已验证且由用户明确授权的重复副本允许删除；原脚本的路径/所有权/符号链接/活动引用/冻结manifest SHA/删除前重新审计保持有效。未修改Skill源文件，也未把共享正式结果列入删除清单。

删除manifest SHA-256：`88b71ac6f5ab6de00bcc5e963e9497e3ca2626fa436b6f3d7f1ee03fa635d204`。审计及删除日志已保存在g08 `/var/tmp/ph_teacher3/cleanup_audits/20260915_l25_archive`；本地副本见本目录。

g08项目/tmp实占从 46.16 GiB降至23.08 GiB，观察到减少23.08 GiB。统计为文件系统磁盘块，不是RAM或GPU显存；活动L0可能同时写日志，因此精确范围以删除清单为准。

## L0训练剩余时间

08:48:41完成Epoch34/50（step8500），08:59后验日志为Epoch35、42/500样本。最近5个完整epoch耗时：2.95小时, 2.91小时, 2.63小时, 4.05小时, 3.75小时。

按近期速度，剩余约42～65小时，中心估计约47小时，约9月17日凌晨至9月18日凌晨完成L0训练。此估计从9月15日早上起算，不含L0正式评测，不含后续L1/L2/L4；共享GPU负载变化会改变速度。未按selected checkpoint epoch估算训练进度。

## /tmp中其他评测副本

| 节点 | 数据集/模型/层 | 实占 | 存储内容 | 迁移判断 |
|---|---|---:|---|---|
| g08 | evqa-pilot500/llava-v1.5-7b/layer_24 | 4.90 MiB | results、mean_results、完成标记、训练历史与少量记录 | 共享盘已完整归档且SYNC_VERIFIED；属于待清理残留，本轮未删除 |
| g07 | mmke-entity/llava-v1.5-7b/layer_26 | 4.89 MiB | results、mean_results、完成标记、训练历史与少量记录 | 共享盘已完整归档且SYNC_VERIFIED；属于待清理残留，本轮未删除 |
| g07 | mmke-entity/llava-v1.5-7b/layer_23 | 4.90 MiB | results、mean_results、完成标记、训练历史与少量记录 | 共享盘已完整归档且SYNC_VERIFIED；属于待清理残留，本轮未删除 |

以上三层合计 14.68 MiB。已分别运行逐层verifier检查临时及共享根；不是根据/tmp残留标记缺失误判历史已归档层为失败。其他空层目录或仅selected指针的小目录占用接近0～4 KiB，保留原队列结构。

## 大块占用与迁移条件

| 节点 | 内容 | 实占 | 判断 |
|---|---|---:|---|
| g08 | EVQA/LLaVA L0训练预处理缓存 | 22.68 GiB | 当前训练使用，不能搬走或删除；完成正式评测后可删除可重建缓存 |
| g08 | L0 checkpoint、TensorBoard及训练历史 | 396.80 MiB | 未完成层，保留恢复所需checkpoint；可另做已落盘checkpoint备份，但不能移动活动写入路径 |
| g07 | MMKE-entity/LLaVA L22缓存 | 33.89 GiB | L22训练完成但正式评测未完成，暂按受保护数据保留；可评估备份selected和元数据，不冒充正式完成 |
| g07 | L22 checkpoint和训练记录 | 396.89 MiB | 训练完成、评测等待；selected是恢复/评测所需产物 |
| g07 | CMA-ModelPred补层残余小目录 | 3.13 MiB | 少量日志/状态等，归属本项目；本轮未进一步删除 |

g07 `/tmp/ph_teacher3`总占用约34.30 GiB。g08删除L25后约23.08 GiB。/tmp挂载于节点root磁盘，未将其解释为内存文件系统。审计范围为两节点 `/tmp/ph_teacher3`下本项目实验目录，未处理其他用户/project文件。

缓存目录名为vead_train_cache，来自训练数据预处理，保存编辑请求表征、rel/gen/loc中间输入/标签mask、InfluenceMapper监督等张量；不是正式评测结果或模型基础权重。L25缓存有2000个文件，未把这22.68 GiB可重建数据复制到共享盘。

## 当前训练写入位置

当前L0进程PID71731，归属Job3178538/step30；CLI --out-root仍是：

```text
/tmp/ph_teacher3/formal_top3_stage2_job3150065_20260812/evqa-pilot500/llava-v1.5-7b
```

- `layer_00/records/.../checkpoints/`：checkpoint；`layer_00/loss_history.csv`：选点历史；`records/.../logs/`：TensorBoard。
- `cache/layer_00/vead_train_cache/`：当前层可重建训练缓存。
- 父级`logs/evqa-pilot500_llava-v1.5-7b_L0_train_20260906_121304.log`：stdout训练日志。
- 父级`queue.status.log`、`layer_status.csv`：整个队列共享日志/状态，不能按L25删除。
- 未来该层评测通常写入`layer_00/eval_full/`并生成`eval_full.done`；当前没有该完成标记。

本轮没有改变正在运行训练的out-root。正式产物应在逐层完成评测后及时归档；本轮未新增后台监控程序或自动删除其他层。

## 本地记录与连接限制

本地总表已将L25改为共享归档、临时副本已清理状态；历史指标及完成数量不变。清理后再次检查两节点结果根，当前没有发现新的未登记正式完成层。

额外尝试把共享目录的20个compact artifacts（约9.75 MiB，不含checkpoint）同步到本地；标准同步脚本在SSH连接超时后中断，随后只读重连也超时。保留`.partial`目录并逐项记录成功/缺失文件，未宣称这次额外本地复制完成；本次共享归档、哈希检查、删除和服务器后验均在连接中断前成功。

最后成功后验时间：g08 2026-09-15T08:59:29.659704+08:00；g07 2026-09-15T08:59:29.099482+08:00。连接超时不能推断训练已停止。详见summary.json及原始postcheck日志。

## 证据索引

- `archive_manifest.json`、`archive_verifier.json`、`source_verifier.json`：归档与评测合同。
- `cleanup_manifest.tsv`、`cleanup_audit.json`、`cleanup_delete.json`：精确范围和删除证据。
- `inventory_g08.json`、`inventory_g07.json`：清理前占用与epoch时间。
- `postcheck_g08.json`、`postcheck_g07.json`：清理后活动状态和其他层核验。
- `summary.json`：机器可读结论，包括额外本地复制的未完成状态。
