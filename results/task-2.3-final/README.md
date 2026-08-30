# 任务 2.3 最终正式结果

输入为最终 Kona 提交 `cb9164b6b`。实现只缓存递归嵌套层的对象字段数组，根层保留一次性
数组，并将批量引用清理限制到异常路径。

- `jmh-result.json`：完整九场景 JMH 1.37 结果，3 forks、5 次预热、5 次测量并启用 GC profiler；
- `environment.txt`：Apple M5 环境、clean Kona 提交、JDK 与基准源码哈希；
- `SHA256SUMS`：JSON 与环境文件的 SHA-256 完整性清单。

主要结果：GRAPH 序列化为 `5.682 ± 0.151 us/op`、`16,320 B/op`；相对基线分配减少
2,344 B/op（12.56%），耗时置信区间重叠。完整解释见
[任务 2.3 报告](../../docs/reports/task-2.3-serialization-followup.md)。

审计说明：该历史轮次使用构建树中的 exploded `jdk`，而任务 2.1 基线使用
`images/jdk`，且两轮 macOS 小版本不同。分配量结论保留；跨轮耗时只作为观测值。
修正后的自动化已强制后续正式实验使用与 Kona HEAD 匹配的 `images/jdk` 并记录产物哈希。
