# 任务 2.3 报告：JMH 对比、Codex 分析与进一步改进

## 结论

任务 2.3 已完成数据驱动的多轮实现迭代，并根据后续评审修复了产物绑定和长生命周期缓存保留风险。
正式性能镜像对应的 Kona 实现提交为 `0c13d1af7`；补强边界测试后的分支提交为
`a8af697e4`（仅修改 jtreg，不改变被测 JDK 源码）。实现审阅入口为
[Kona PR #1](https://github.com/RayovacCho/TencentKona-25/pull/1)。

当前正式基线与最终结果于 2026-09-04 在同一台 Apple M5 MacBook Air、同一 macOS 26.6.2
环境中顺序重测，两边均使用与 Kona 提交匹配的 release `images/jdk`。在最能体现写路径改动的
`GRAPH serialize` 场景中：

- 分配量从 **18,664 B/op** 降到 **16,320 B/op**，减少 **2,344 B/op（12.56%）**；
- 首轮耗时从 **5.618 ± 0.084 us/op** 变为 **5.890 ± 0.090 us/op**，点估计高 4.84%；
  反向顺序聚焦复测则从 **5.942 ± 0.156 us/op** 变为 **5.889 ± 0.162 us/op**（-0.89%），
  因此不能认定存在稳定加速或回退；
- `SMALL` 与 `CUSTOM` 写路径均保持基线分配量；
- 读取路径没有修改，其耗时和 fork 分配波动不用于评价此次优化。

正式 JMH 已扩展为 18 项：除原有英文小对象、英文对象图与自定义序列化外，还覆盖中文
小对象、中文对象图和 4096 元素中英文混合对象数组。中文对象图写入分配同样下降 12.56%，
大数组下降 10.25%；大数组每次减少约 98,248 B，约等于每个元素 24 B，符合消除逐对象
临时引用数组的实现机制。由此可以证明分配优化具有广泛性，但延迟加速仍未得到证明。

最终实现只在当前顶层对象图内复用递归嵌套层的字段快照数组。顶层写入返回时会丢弃嵌套缓存，
不再让长生命周期 `ObjectOutputStream` 保留历史最深、最宽对象图的数组容量。新增目标测试和完整序列化 jtreg
**163/163 全部通过**。

## 正式实验约束

两轮当前正式结果都使用 6 类载荷、3 条操作路径，并采用：

```text
Mode: AverageTime; Threads: 1; Forks: 3
Warmup: 5 × 1 s; Measurement: 5 × 1 s
Profiler: gc; 结果单位: us/op 与 B/op
OS: macOS 26.6.2; JDK image: images/jdk
```

当前归档结果的 `environment_schema=2` 记录了 Kona commit、JDK `SOURCE` 修订、JMH 源码与依赖锁定哈希，
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
两轮正式基准均完整生成了 18 项 JSON，不是 Kona 修改的测试失败。

## 实现迭代与评审修复

历史候选轮次保留在 `results/task-2.3-round1` 至 `round3`，用于追溯 Codex 的决策过程：

| 阶段 | Kona 提交 | 设计 | 历史观测 |
|---|---|---|---|
| Round 1 | `122f6b52a` | 单个深度二维缓存 | GRAPH 分配下降，SMALL 多 24 B 固定容器 |
| Round 2 | `9fa7ed6fa` | 根缓存与嵌套缓存分成两字段 | 第二个引用字段使 CUSTOM 多分配 8 B |
| Round 3 | `53975e470` | 单字段惰性状态 | 恢复浅层分配，但增加状态判断 |
| 原最终 | `cb9164b6b` | 根层不缓存，只缓存嵌套层 | 保留单个对象图内的复用收益 |
| 评审修复 | `0c13d1af7` | 顶层写入结束时释放嵌套缓存 | 消除长生命周期流保留历史最大容量的风险 |
| 测试补强 | `a8af697e4` | 扩展同一目标 jtreg | 覆盖异常、重复写入、宽窄复用和扩容 |

Round 1–3 的环境清单没有 schema 2 的 JDK 二进制哈希，因此现在明确标记为 legacy
候选决策证据，不作为当前最终性能结论。正式结论只使用重新生成的 2.1 基线与 2.3 最终结果。

Kona 最终实现修改：

- `ObjectOutputStream.java`：嵌套深度缓存、容量增长、逐槽引用清理、异常路径剩余区间清理，
  并在顶层 `writeObject0` 返回时释放整个嵌套缓存；
- `FieldValuesBuffer.java`：验证字段快照语义、100 层递归链、宽窄对象缓冲复用、重复顶层
  写入，以及成功和异常退出后 `nestedObjFieldVals` 均已释放。

序列化格式、字段顺序和“先读取全部字段，再递归写出”的快照语义均未改变。

## 广泛场景设计

- `SMALL` / `SMALL_CHINESE`：字段结构相同，仅字符串内容不同；
- `GRAPH` / `GRAPH_CHINESE`：均为 100 节点对象图，仅字符串内容不同；
- `LARGE_OBJECT_ARRAY`：4096 个普通对象，名称交替使用英文和中文；
- `CUSTOM`：自定义 `writeObject/readObject`，作为非目标路径对照；
- 每类载荷均在 JMH setup 阶段校验反序列化后的标量、集合和数组内容。

原三类载荷的名称和构造逻辑保持不变。扩展后先用未优化 JDK 建立新基线，再原样切换到
最终 JDK；smoke 只用于验证矩阵，正式结论均来自完整参数结果。

## 当前正式完整结果

下表直接由重测的基线和最终 JSON 按操作/载荷配对。耗时和分配均越低越好；
变化列以当前任务 2.1 基线为参照。

| 操作 | 载荷 | 基线 us/op | 最终 us/op | 耗时变化 | 基线 B/op | 最终 B/op | 分配变化 |
|---|---|---:|---:|---:|---:|---:|---:|
| `deserialize` | SMALL | 1.159 ± 0.007 | 1.145 ± 0.011 | -1.16% | 3,672 | 3,653 | -0.51% |
| `deserialize` | SMALL_CHINESE | 1.183 ± 0.005 | 1.198 ± 0.008 | +1.21% | 3,685 | 3,704 | +0.51% |
| `deserialize` | GRAPH | 11.363 ± 0.111 | 11.428 ± 0.060 | +0.58% | 34,021 | 34,021 | +0.00% |
| `deserialize` | GRAPH_CHINESE | 11.963 ± 0.167 | 11.641 ± 0.072 | -2.69% | 39,043 | 39,035 | -0.02% |
| `deserialize` | LARGE_OBJECT_ARRAY | 341.003 ± 3.220 | 340.607 ± 3.461 | -0.12% | 1,255,426 | 1,255,426 | -0.00% |
| `deserialize` | CUSTOM | 0.668 ± 0.003 | 0.684 ± 0.012 | +2.38% | 2,856 | 2,840 | -0.56% |
| `roundTrip` | SMALL | 1.601 ± 0.010 | 1.600 ± 0.006 | -0.11% | 10,312 | 10,304 | -0.08% |
| `roundTrip` | SMALL_CHINESE | 1.611 ± 0.002 | 1.619 ± 0.009 | +0.49% | 10,344 | 10,344 | +0.00% |
| `roundTrip` | GRAPH | 17.913 ± 0.224 | 17.688 ± 0.320 | -1.26% | 54,840 | 52,496 | -4.27% |
| `roundTrip` | GRAPH_CHINESE | 19.233 ± 0.685 | 18.797 ± 0.371 | -2.27% | 58,776 | 56,448 | -3.96% |
| `roundTrip` | LARGE_OBJECT_ARRAY | 631.181 ± 16.029 | 624.437 ± 15.618 | -1.07% | 2,213,572 | 2,115,324 | -4.44% |
| `roundTrip` | CUSTOM | 1.089 ± 0.004 | 1.094 ± 0.003 | +0.50% | 9,392 | 9,392 | +0.00% |
| `serialize` | SMALL | 0.398 ± 0.002 | 0.400 ± 0.002 | +0.33% | 6,624 | 6,624 | +0.00% |
| `serialize` | SMALL_CHINESE | 0.404 ± 0.001 | 0.403 ± 0.001 | -0.25% | 6,624 | 6,624 | -0.00% |
| `serialize` | GRAPH | 5.618 ± 0.084 | 5.890 ± 0.090 | +4.84% | 18,664 | 16,320 | -12.56% |
| `serialize` | GRAPH_CHINESE | 6.596 ± 0.220 | 6.624 ± 0.145 | +0.41% | 18,664 | 16,320 | -12.56% |
| `serialize` | LARGE_OBJECT_ARRAY | 271.210 ± 6.586 | 280.373 ± 8.284 | +3.38% | 958,146 | 859,898 | -10.25% |
| `serialize` | CUSTOM | 0.364 ± 0.001 | 0.365 ± 0.002 | +0.28% | 6,560 | 6,560 | +0.00% |

可确认的结论是目标写路径分配下降 10.25%～12.56%，浅层和自定义写路径没有额外分配。
首轮 `GRAPH serialize` 耗时回退未被反向顺序复测重现，其他目标场景也没有一致的耗时方向，
因此延迟结论为中性、不确定。反序列化实现没有修改，相关差异仅作为系统波动对照。

## GRAPH 反向顺序复测

完整实验固定按“基线、最终”运行。为检查顺序和机器状态偏差，又按“最终、基线”的反向
顺序聚焦复测 GRAPH；参数仍为 3 forks × 5 次测量，原始 JSON 已提交。

| 操作 | 反向复测基线 us/op | 反向复测最终 us/op | 基线 B/op | 最终 B/op |
|---|---:|---:|---:|---:|
| `deserialize` | 11.568 ± 0.422 | 11.460 ± 0.117 | 34,021 | 32,944 |
| `roundTrip` | 18.020 ± 0.306 | 17.690 ± 0.304 | 54,824 | 52,496 |
| `serialize` | 5.942 ± 0.156 | 5.889 ± 0.162 | 18,664 | 16,320 |

写路径分配下降在反向顺序下保持一致；耗时方向与完整实验不同，支持“不宣称稳定延迟
加速或回退”的保守结论。读取侧分配差异不是本次代码修改目标，不作为收益归因。

## 正确性测试

最终提交上的完整命令：

```bash
make CONF=macosx-aarch64-server-release test-only \
  TEST='test/jdk/java/io/Serializable test/jdk/java/io/Externalizable test/jdk/java/io/ObjectInputStream test/jdk/java/io/ObjectStreamClass' \
  JTREG='JOBS=4;TIMEOUT_FACTOR=4'
```

重新 configure 并完整干净构建后的输出：

```text
TEST                                              TOTAL  PASS  FAIL ERROR SKIP
jtreg:test/jdk/java/io/Serializable                 151   151     0     0    0
jtreg:test/jdk/java/io/Externalizable                 2     2     0     0    0
jtreg:test/jdk/java/io/ObjectInputStream              4     4     0     0    0
jtreg:test/jdk/java/io/ObjectStreamClass              6     6     0     0    0
合计                                                163   163     0     0    0
TEST SUCCESS
```

## 可审计产物

- [当前任务 2.1 基线](../../results/task-2.1-baseline/README.md)：schema 2 正式结果；
- [Round 1](../../results/task-2.3-round1/README.md)、[Round 2](../../results/task-2.3-round2/README.md)、
  [Round 3](../../results/task-2.3-round3/README.md)：legacy 候选决策证据；
- [当前最终结果](../../results/task-2.3-final/README.md)：schema 2、18 项正式结果；
- [GRAPH 反向顺序复测](../../results/task-2.3-repeat/README.md)：3 条操作路径的原始 JSON
  与 SHA-256，用于核验顺序效应。

`make check-results` 会验证五组正式结果和一组反向复测的校验和、与基准源码版本匹配的
场景矩阵、3×5 原始样本、JMH 参数和 GC 分配指标；
对当前基线和最终结果还会强制 schema 2，校验 JMH `jvm` 路径与环境清单一致，
拒绝重复或空的环境字段与非有限指标，确认两组结果的 OS、架构、CPU 和内存一致，
并核对本报告中的正式数字。
