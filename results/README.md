# 序列化基准结果索引

本目录同时保存当前正式性能证据和历史候选数据，二者用途不同。

## 当前正式结果

| 结果 | Kona 提交 | 产物来源 |
|---|---|---|
| [任务 2.1 基线](task-2.1-baseline/README.md) | `3dfb92059520` | schema 2，release `images/jdk` |
| [任务 2.3 最终](task-2.3-final/README.md) | `0c13d1af75d6` | schema 2，release `images/jdk` |

正式性能结论只使用这两组于 2026-09-03 在同一硬件、同一 macOS 版本下顺序重测的数据。
完整对比和解释见[任务 2.3 报告](../docs/reports/task-2.3-serialization-followup.md)。

## 历史候选

- [Round 1](task-2.3-round1/README.md)
- [Round 2](task-2.3-round2/README.md)
- [Round 3](task-2.3-round3/README.md)

这些目录保留用于追溯 GPT-5.6 的设计决策，但环境清单不满足当前 schema 2 的 JDK
二进制绑定规则，因此不用于当前正式性能结论。

## 新增复现实验

新的实验应放入 `results/reproductions/<唯一目录>/`。除上述三个精确命名的 legacy
目录外，`make check-results` 会要求所有结果使用 schema 2，并校验 Kona 提交、JDK
`SOURCE`、`release`、`bin/java`、`lib/modules`、JMH 源码和依赖锁定信息。
