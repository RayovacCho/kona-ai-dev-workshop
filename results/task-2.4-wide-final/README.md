# 任务 2.4 广泛场景最终结果

输入为优化及评审修复后的 Kona 提交
`0c13d1af75d6809546cb660836bef57836c3d181`，与本轮广泛场景基线使用相同的 JMH 源码、
参数、机器和顺序实验约束。

- `jmh-result.json`：6 类载荷、3 条操作路径的 18 项正式结果；
- `environment.txt`：clean Kona 提交、JDK 镜像、基准源码与依赖锁哈希；
- `SHA256SUMS`：以上两个证据文件的 SHA-256。

目标写路径分配下降 10.25%～12.56%，但耗时未证明稳定提升。完整分析见
[任务 2.4 报告](../../docs/reports/task-2.4-wide-serialization-validation.md)。
