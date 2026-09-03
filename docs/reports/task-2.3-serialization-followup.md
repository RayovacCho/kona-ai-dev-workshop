# 任务 2.3 报告：JMH 对比、Codex 分析与进一步改进

## 结论

任务 2.3 已完成数据驱动的多轮实现迭代，并根据后续评审修复了产物绑定和长生命周期缓存保留风险。
最终 Kona 提交为 `0c13d1af7`，实现审阅入口为
[Kona PR #1](https://github.com/RayovacCho/TencentKona-25/pull/1)。

当前正式基线与最终结果于 2026-09-03 在同一台 Apple M5 MacBook Air、同一 macOS 26.6.2
环境中顺序重测，两边均使用与 Kona 提交匹配的 release `images/jdk`。在最能体现写路径改动的
`GRAPH serialize` 场景中：

- 分配量从 **18,664 B/op** 降到 **16,320 B/op**，减少 **2,344 B/op（12.56%）**；
- 耗时从 **6.077 ± 0.216 us/op** 变为 **6.284 ± 0.029 us/op**，点估计高 3.40%，
  但 99.9% 置信区间仍重叠，不能认定存在确定性加速或回退；
- `SMALL` 与 `CUSTOM` 写路径均保持基线分配量；
- 读取路径没有修改，其耗时和 fork 分配波动不用于评价此次优化。

最终实现只在当前顶层对象图内复用递归嵌套层的字段快照数组。顶层写入返回时会丢弃嵌套缓存，
不再让长生命周期 `ObjectOutputStream` 保留历史最深、最宽对象图的数组容量。新增目标测试和完整序列化 jtreg
**161/161 全部通过**。

## 正式实验约束

两轮当前正式结果都使用：

```text
Mode: AverageTime; Threads: 1; Forks: 3
Warmup: 5 × 1 s; Measurement: 5 × 1 s
Profiler: gc; 结果单位: us/op 与 B/op
OS: macOS 26.6.2; JDK image: images/jdk
```

`environment_schema=2` 记录了 Kona commit、JDK `SOURCE` 修订、JMH 源码与依赖锁定哈希，
以及 `release`、`bin/java`、`lib/modules` 的 SHA-256。`make verify-kona-home` 会在测量前拒绝
dirty 工作树、exploded JDK、错误路径或 `SOURCE` 不匹配的镜像。

复现时先对相应 Kona 提交执行 `configure` 和 `make images`，然后使用新结果目录：

```bash
KONA_SRC=/path/to/clean/TencentKona-25 \
KONA_HOME=/path/to/clean/TencentKona-25/build/macosx-aarch64-server-release/images/jdk \
RESULT_DIR=results/reproductions/task-2.3-YYYYMMDD make jmh-baseline

KONA_SRC=/path/to/clean/TencentKona-25 \
KONA_HOME=/path/to/clean/TencentKona-25/build/macosx-aarch64-server-release/images/jdk \
RESULT_DIR=results/reproductions/task-2.3-YYYYMMDD make capture-environment
```

JMH 1.37 在 JDK 25 上的 `sun.misc.Unsafe::objectFieldOffset` 终止弃用警告来自 JMH 自身，
两轮基准均完整生成了九项 JSON，不是 Kona 修改的测试失败。

## 实现迭代与评审修复

历史候选轮次保留在 `results/task-2.3-round1` 至 `round3`，用于追溯 Codex 的决策过程：

| 阶段 | Kona 提交 | 设计 | 历史观测 |
|---|---|---|---|
| Round 1 | `122f6b52a` | 单个深度二维缓存 | GRAPH 分配下降，SMALL 多 24 B 固定容器 |
| Round 2 | `9fa7ed6fa` | 根缓存与嵌套缓存分成两字段 | 第二个引用字段使 CUSTOM 多分配 8 B |
| Round 3 | `53975e470` | 单字段惰性状态 | 恢复浅层分配，但增加状态判断 |
| 原最终 | `cb9164b6b` | 根层不缓存，只缓存嵌套层 | 保留单个对象图内的复用收益 |
| 评审修复 | `0c13d1af7` | 顶层写入结束时释放嵌套缓存 | 消除长生命周期流保留历史最大容量的风险 |

Round 1–3 的环境清单没有 schema 2 的 JDK 二进制哈希，因此现在明确标记为 legacy
候选决策证据，不作为当前最终性能结论。正式结论只使用重新生成的 2.1 基线与 2.3 最终结果。

Kona 最终实现修改：

- `ObjectOutputStream.java`：嵌套深度缓存、容量增长、逐槽引用清理、异常路径剩余区间清理，
  并在顶层 `writeObject0` 返回时释放整个嵌套缓存；
- `FieldValuesBuffer.java`：验证字段快照语义、100 层递归链正确往返，以及顶层写入后
  `nestedObjFieldVals` 已释放。

序列化格式、字段顺序和“先读取全部字段，再递归写出”的快照语义均未改变。

## 当前正式完整结果

下表直接由重测的基线和最终 JSON 按操作/载荷配对。耗时和分配均越低越好；
变化列以当前任务 2.1 基线为参照。

| 操作 | 载荷 | 基线 us/op | 最终 us/op | 耗时变化 | 基线 B/op | 最终 B/op | 分配变化 |
|---|---|---:|---:|---:|---:|---:|---:|
| `serialize` | SMALL | 0.407 ± 0.008 | 0.427 ± 0.061 | +4.85% | 6,624 | 6,624 | 0 (+0.00%) |
| `serialize` | GRAPH | 6.077 ± 0.216 | 6.284 ± 0.029 | +3.40% | 18,664 | 16,320 | -2,344 (-12.56%) |
| `serialize` | CUSTOM | 0.374 ± 0.010 | 0.366 ± 0.003 | -2.15% | 6,560 | 6,560 | 0 (0.00%) |
| `deserialize` | SMALL | 1.162 ± 0.002 | 1.196 ± 0.031 | +2.93% | 3,664 | 3,661 | -3 (-0.07%) |
| `deserialize` | GRAPH | 11.541 ± 0.229 | 12.563 ± 0.550 | +8.85% | 34,013 | 34,021 | +8 (+0.02%) |
| `deserialize` | CUSTOM | 0.702 ± 0.012 | 0.765 ± 0.063 | +8.94% | 2,832 | 2,848 | +16 (+0.56%) |
| `roundTrip` | SMALL | 1.613 ± 0.015 | 1.888 ± 0.283 | +17.03% | 10,304 | 10,312 | +8 (+0.08%) |
| `roundTrip` | GRAPH | 18.578 ± 1.214 | 19.711 ± 0.754 | +6.10% | 54,832 | 52,496 | -2,336 (-4.26%) |
| `roundTrip` | CUSTOM | 1.126 ± 0.025 | 1.168 ± 0.095 | +3.71% | 9,392 | 9,392 | 0 (0.00%) |

可确认的结论是 GRAPH 写路径分配下降 12.56%，浅层写路径没有额外分配，且 GRAPH 写耗时
没有统计上可确认的加速或回退。反序列化及其对 roundTrip 的影响作为观测值保留，
不作为代码改动的因果结论。

## 正确性测试

最终提交上的完整命令：

```bash
make CONF=macosx-aarch64-server-release test-only \
  TEST='test/jdk/java/io/Serializable test/jdk/java/io/ObjectInputStream test/jdk/java/io/ObjectStreamClass' \
  JTREG='JOBS=4;TIMEOUT_FACTOR=4'
```

重新 configure 并完整干净构建后的输出：

```text
TEST                                              TOTAL  PASS  FAIL ERROR SKIP
jtreg:test/jdk/java/io/Serializable                 151   151     0     0    0
jtreg:test/jdk/java/io/ObjectInputStream              4     4     0     0    0
jtreg:test/jdk/java/io/ObjectStreamClass              6     6     0     0    0
TEST SUCCESS
```

## 可审计产物

- [当前任务 2.1 基线](../../results/task-2.1-baseline/README.md)：schema 2 正式结果；
- [Round 1](../../results/task-2.3-round1/README.md)、[Round 2](../../results/task-2.3-round2/README.md)、
  [Round 3](../../results/task-2.3-round3/README.md)：legacy 候选决策证据；
- [当前最终结果](../../results/task-2.3-final/README.md)：schema 2 正式结果。

`make check-results` 会验证五组结果的校验和、九场景矩阵、JMH 参数和 GC 分配指标；
对当前基线和最终结果还会强制 schema 2，校验 JMH `jvm` 路径与环境清单一致，
拒绝重复或空的环境字段与非有限指标，确认两组结果的 OS、架构、CPU 和内存一致，
并核对本报告中的正式数字。
