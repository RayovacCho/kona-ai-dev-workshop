# 任务 2.3 报告：JMH 对比、Codex 分析与进一步改进

## 结论

任务 2.3 已完成两次正式对照和三次数据驱动的实现迭代。最终 Kona 提交为
`cb9164b6b`。在最能体现本次写路径改动的 `GRAPH serialize` 场景中：

- 分配量从基线 **18,664 B/op** 降到 **16,320 B/op**，减少 **2,344 B/op
  （12.56%）**；
- 耗时从 **5.589 ± 0.124 us/op** 变为 **5.682 ± 0.151 us/op**，点估计高
  1.66%，但 99.9% 置信区间重叠，不能认定存在确定性加速或回退；
- `SMALL` 与 `CUSTOM` 写路径均恢复到基线分配量，消除了第一轮的浅对象固定开销；
- `GRAPH roundTrip` 为 **16.535 ± 0.029 us/op**、**52,496 B/op**，相对基线点
  估计分别为 -7.45% 和 -4.27%。不过读取源码没有修改，且读取分配在不同 fork 间存在
  离散簇，因此不能把全部往返耗时变化归因于本次写路径优化。

最终实现只缓存递归嵌套层的对象字段快照数组，根层继续使用原有的一次性数组；正常路径
逐槽清空，只有异常路径才批量清理剩余引用。新增目标测试及完整序列化 jtreg
**161/161 全部通过**。

## Codex 输入与执行规划

给 Codex 的任务输入是：

```text
继续完成 2.3：对优化实现执行 JMH 得到性能，使用 Codex 分析差异，并根据分析结果做
进一步改进。规划、代码、报告和结果都放入仓库。
```

Codex 先固定实验约束，再按“测量 → 分析 → 修改 → 正确性验证 → 复测”推进。完整规划见
[任务 2.3 规划](../task-2.3-plan.md)。所有正式轮次都使用同一台 Apple M5 MacBook Air、
同一 JMH 1.37 程序和以下参数：

```text
Mode: AverageTime; Threads: 1; Forks: 3
Warmup: 5 × 1 s; Measurement: 5 × 1 s
Profiler: gc; 结果单位: us/op 与 B/op
```

基准命令（每轮只替换 clean Kona 提交和结果目录）：

```bash
KONA_SRC=/Users/rayovac9/TencentKona-25-task-2.2 \
KONA_HOME=/Users/rayovac9/TencentKona-25-task-2.2/build/macosx-aarch64-server-release/jdk \
RESULT_DIR=results/task-2.3-final make jmh-baseline

KONA_SRC=/Users/rayovac9/TencentKona-25-task-2.2 \
KONA_HOME=/Users/rayovac9/TencentKona-25-task-2.2/build/macosx-aarch64-server-release/jdk \
RESULT_DIR=results/task-2.3-final make capture-environment
```

正式输出为：

```text
# JMH version: 1.37
# Warmup: 5 iterations, 1 s each
# Measurement: 5 iterations, 1 s each
# Fork: 1 of 3 ... 3 of 3
# Run complete. Total time: 00:04:35
Benchmark result is saved to results/task-2.3-final/jmh-result.json
```

JMH 输出中的 `sun.misc.Unsafe::objectFieldOffset` 终止弃用警告来自 JMH 1.37 自身，基准
仍完整结束并生成了九项 JSON，不是 Kona 修改的测试失败。

## 第一轮结果与 Codex 分析

Round 1 输入是任务 2.2 提交 `122f6b52a`。完整结果位于
[`results/task-2.3-round1/`](../../results/task-2.3-round1/README.md)。与任务 2.1 基线
相比，关键写路径结果为：

| 场景 | 基线耗时 | Round 1 耗时 | 基线分配 | Round 1 分配 | Codex 判断 |
|---|---:|---:|---:|---:|---|
| `serialize SMALL` | 0.398 ± 0.002 | 0.395 ± 0.001 | 6,624 | 6,648 | 多出 24 B 固定容器 |
| `serialize GRAPH` | 5.589 ± 0.124 | 5.927 ± 0.285 | 18,664 | 16,344 | 分配 -12.43%，耗时点估计 +6.04% |
| `serialize CUSTOM` | 0.366 ± 0.004 | 0.362 ± 0.001 | 6,560 | 6,560 | 没有默认字段缓存，不受影响 |

Codex 从数字和源码得出三点：

1. 任务 2.2 的深度缓存确实消除了对象图中大量短命 `Object[]`；
2. 任何浅对象也会创建 `Object[][]` 容器，所以 SMALL 固定多分配 24 B；
3. TLAB 中创建小数组成本很低，而每个对象都执行深度索引、清理和状态判断，可能抵消
   部分 CPU 收益，不能只看分配量宣布加速。

读取路径源码未改，因此其差异不用于评价优化。原始 JSON 还显示 `deserialize GRAPH` 的
分配量按 fork 落在约 32,944、36,152 或 36,176 B/op 的离散簇：基线前两个 fork 是
32,944，而第三个是 36,176；Round 1 三个 fork 都是 32,944。聚合平均数因此会产生看似
明显但不可归因的变化。

## 根据分析进行的改进

实验保留了每个正式中间版本，以免只展示成功结果：

| 阶段 | Kona 提交 | 设计 | SMALL B/op | GRAPH B/op | GRAPH us/op |
|---|---|---|---:|---:|---:|
| 2.1 基线 | 基线环境文件记录 | 每对象新建数组 | 6,624 | 18,664 | 5.589 ± 0.124 |
| Round 1 | `122f6b52a` | 单个深度二维缓存 | 6,648 | 16,344 | 5.927 ± 0.285 |
| Round 2 | `9fa7ed6fa` | 根缓存与嵌套缓存分成两个字段 | 6,632 | 16,328 | 5.974 ± 0.172 |
| Round 3 | `53975e470` | 单字段惰性升级为状态对象 | 6,624 | 16,344 | 5.905 ± 0.166 |
| 最终 | `cb9164b6b` | 根层不缓存，只缓存嵌套层；异常才批量清理 | 6,624 | 16,320 | 5.682 ± 0.151 |

Round 2 暴露出第二个引用字段会使 `ObjectOutputStream` 实例增大 8 B，CUSTOM 也从
6,560 增到 6,568 B/op。Round 3 用一个多态字段消除了浅层分配，但每个对象增加了
`instanceof` 和状态解包。最终方案利用“每次 JMH 操作都会新建对象流”的事实：根缓存只
使用一次，没有复用价值；仅在发生嵌套默认序列化时创建二维缓存，既简化热路径，也保留
对象图复用收益。Round 1、2、3 的完整 JSON 均在 `results/` 中，属于负面结果与决策证据。

Kona 最终实现修改：

- `src/java.base/share/classes/java/io/ObjectOutputStream.java`：嵌套深度缓存、容量增长、
  正常路径逐槽清空、异常路径剩余区间清理；
- `test/jdk/java/io/Serializable/fieldValuesBuffer/FieldValuesBuffer.java`：验证字段快照
  语义，并验证 100 层递归链可正确往返。

序列化格式、字段顺序和“先读取全部字段，再递归写出”的快照语义均未改变。

## 最终完整结果

下表直接由基线、Round 1 和最终 JSON 按操作/载荷配对生成。耗时和分配均越低越好；
变化列以任务 2.1 基线为参照。

| 操作 | 载荷 | 基线 us/op | Round 1 us/op | 最终 us/op | 最终耗时变化 | 基线 B/op | Round 1 B/op | 最终 B/op | 最终分配变化 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `serialize` | SMALL | 0.398 ± 0.002 | 0.395 ± 0.001 | 0.408 ± 0.016 | +2.45% | 6,624 | 6,648 | 6,624 | +0 (+0.00%) |
| `serialize` | GRAPH | 5.589 ± 0.124 | 5.927 ± 0.285 | 5.682 ± 0.151 | +1.66% | 18,664 | 16,344 | 16,320 | -2,344 (-12.56%) |
| `serialize` | CUSTOM | 0.366 ± 0.004 | 0.362 ± 0.001 | 0.362 ± 0.001 | -1.15% | 6,560 | 6,560 | 6,560 | 0 (0.00%) |
| `deserialize` | SMALL | 1.152 ± 0.011 | 1.143 ± 0.008 | 1.122 ± 0.006 | -2.61% | 3,653 | 3,664 | 3,669 | +16 (+0.44%) |
| `deserialize` | GRAPH | 11.452 ± 0.120 | 11.268 ± 0.049 | 10.588 ± 0.289 | -7.54% | 34,021 | 32,944 | 36,160 | +2,139 (+6.29%) |
| `deserialize` | CUSTOM | 0.681 ± 0.008 | 0.673 ± 0.008 | 0.669 ± 0.010 | -1.69% | 2,840 | 2,848 | 2,848 | +8 (+0.28%) |
| `roundTrip` | SMALL | 1.594 ± 0.012 | 1.600 ± 0.017 | 1.572 ± 0.014 | -1.39% | 10,296 | 10,328 | 10,312 | +16 (+0.16%) |
| `roundTrip` | GRAPH | 17.866 ± 0.345 | 18.225 ± 0.931 | 16.535 ± 0.029 | -7.45% | 54,840 | 52,520 | 52,496 | -2,344 (-4.27%) |
| `roundTrip` | CUSTOM | 1.096 ± 0.003 | 1.111 ± 0.009 | 1.088 ± 0.024 | -0.65% | 9,392 | 9,392 | 9,392 | 0 (0.00%) |

可确认的结论是 GRAPH 写路径分配下降 12.56%，浅层写路径没有额外分配，且 GRAPH 写
耗时没有统计上可确认的回退。反序列化及其对 roundTrip 的影响作为观测值保留，不作为
代码改动的因果结论。

## 正确性测试

最终提交上的命令：

```bash
make CONF=macosx-aarch64-server-release test-only \
  TEST='test/jdk/java/io/Serializable test/jdk/java/io/ObjectInputStream test/jdk/java/io/ObjectStreamClass' \
  JTREG='JOBS=4;TIMEOUT_FACTOR=4'
```

输出：

```text
TEST                                              TOTAL  PASS  FAIL ERROR SKIP
jtreg:test/jdk/java/io/Serializable                 151   151     0     0    0
jtreg:test/jdk/java/io/ObjectInputStream              4     4     0     0    0
jtreg:test/jdk/java/io/ObjectStreamClass              6     6     0     0    0
TEST SUCCESS
```

## 可审计产物

- [任务 2.1 基线](../../results/task-2.1-baseline/README.md)
- [Round 1：任务 2.2 原实现](../../results/task-2.3-round1/README.md)
- [Round 2：双字段候选](../../results/task-2.3-round2/README.md)
- [Round 3：惰性状态候选](../../results/task-2.3-round3/README.md)
- [最终结果](../../results/task-2.3-final/README.md)

每个目录包含 JMH JSON、环境清单和 SHA-256 校验和；`make check-results` 会验证五组
结果的完整性、clean Kona 提交、九场景矩阵、JMH 参数和 GC 分配指标，并核对本报告中的
最终数字。
