# 任务 2.3 Round 3（中间候选）

输入为 Kona 提交 `53975e470`。该候选以单字段惰性升级状态对象，恢复了 SMALL/CUSTOM
分配基线，但 GRAPH 写耗时仍有可见回退，因此继续简化为最终的“只缓存嵌套层”方案。

目录包含完整九场景 JMH JSON、clean 提交环境清单和 SHA-256 校验和。详见
[任务 2.3 报告](../../docs/reports/task-2.3-serialization-followup.md)。

审计说明：该轮使用构建树中的 exploded `jdk`，Round 1/2 使用 `images/jdk`。因此跨镜像
形式的微秒级耗时只作为候选筛选依据。修正后的自动化已强制后续正式实验统一使用与
Kona HEAD 匹配的 `images/jdk`。
