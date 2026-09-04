# 任务 2.3 最终正式结果

输入为评审修复后的 Kona 提交 `0c13d1af7`。实现只缓存递归嵌套层的对象字段数组，
根层保留一次性数组，并在顶层写入结束时释放嵌套缓存。

- `jmh-result.json`：完整 18 项 JMH 1.37 结果，覆盖中英文、小对象、对象图、大对象数组与
  自定义序列化，使用 3 forks、5 次预热、5 次测量并启用 GC profiler；
- `environment.txt`：schema 2 环境信息、clean Kona 提交、JDK 与基准源码哈希；
- `SHA256SUMS`：JSON 与环境文件的 SHA-256 完整性清单。

主要结果：GRAPH 序列化为 `5.890 ± 0.090 us/op`、`16,320 B/op`；同环境基准为
`5.618 ± 0.084 us/op`、`18,664 B/op`。分配减少 2,344 B/op（12.56%）。首轮耗时出现
回退，但反向顺序聚焦复测未复现，因此耗时结论为中性、不确定，而非稳定回退或加速。
完整解释见[任务 2.3 报告](../../docs/reports/task-2.3-serialization-followup.md)。

当前基线与最终结果于 2026-09-04 在同一 macOS 26.6.2 环境中顺序重测，都使用与
Kona HEAD 匹配的 `images/jdk`。schema 2 环境清单记录了 `release`、`bin/java`
和 `lib/modules` 哈希。Round 1–3 是保留的 legacy 候选决策证据，不用作当前最终性能结论。
