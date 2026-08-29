# 任务 2.3 Round 2（中间候选）

输入为 Kona 提交 `9fa7ed6fa`。该候选把根缓存和嵌套缓存拆成两个字段；正式数据证明
第二个引用字段使 `ObjectOutputStream` 增大，CUSTOM 也多分配 8 B，因此未被采用。

目录包含完整九场景 JMH JSON、clean 提交环境清单和 SHA-256 校验和。负面结果被保留，
用于复核 Codex 后续设计决策。详见[任务 2.3 报告](../../docs/reports/task-2.3-serialization-followup.md)。
