# 任务 2.3 Round 3（中间候选）

输入为 Kona 提交 `53975e470`。该候选以单字段惰性升级状态对象，恢复了 SMALL/CUSTOM
分配基线，但 GRAPH 写耗时仍有可见回退，因此继续简化为最终的“只缓存嵌套层”方案。

目录包含完整九场景 JMH JSON、clean 提交环境清单和 SHA-256 校验和。详见
[任务 2.3 报告](../../docs/reports/task-2.3-serialization-followup.md)。
