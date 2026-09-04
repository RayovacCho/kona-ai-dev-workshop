# 任务 2.4 广泛场景基线

输入为未优化 Kona 提交 `3dfb920595202df2dfa5b9f5b6c3b124cf32aabf`，使用扩展后的
6 类载荷、3 条操作路径，共 18 项 JMH 正式结果。

- `jmh-result.json`：3 forks、5 次预热、5 次测量及 GC profiler 原始结果；
- `environment.txt`：clean Kona 提交、JDK 镜像、基准源码与依赖锁哈希；
- `SHA256SUMS`：以上两个证据文件的 SHA-256。

完整分析见[任务 2.4 报告](../../docs/reports/task-2.4-wide-serialization-validation.md)。
