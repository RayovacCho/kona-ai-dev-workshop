# 任务 2.3 Round 1

输入为任务 2.2 Kona 提交 `122f6b52a`。这是 Codex 差异分析的第一轮完整九场景 JMH，
用于发现 GRAPH 分配收益、SMALL 的 24 B 固定开销及耗时回退风险。

- `jmh-result.json`：JMH 1.37、3 forks、5 次预热、5 次测量、GC profiler；
- `environment.txt`：机器、JDK、clean Kona 提交及基准源码哈希；
- `SHA256SUMS`：JSON 与环境文件的完整性校验。

分析见[任务 2.3 报告](../../docs/reports/task-2.3-serialization-followup.md)。
