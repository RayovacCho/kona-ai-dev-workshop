# 任务 2.1：Java 序列化基准

## 结论

Kona JDK 25 release 镜像构建成功，序列化相关 jtreg 测试共 **160 项全部通过**。
独立 JMH 程序完成 9 个基准场景；在本机上，小对象完整往返为
**1.594 ± 0.012 us/op**，100 元素对象图完整往返为
**17.866 ± 0.345 us/op**。这些数字作为任务 2.2 和 2.3 的优化前基准。

## 基准环境

| 项目 | 值 |
|---|---|
| 日期 | 2026-08-26 |
| 机器 | MacBook Air，Apple M5（4 性能核 + 6 能效核），16 GB |
| 系统 | macOS 26.5.1（arm64） |
| Kona 源码 | `3dfb920595202df2dfa5b9f5b6c3b124cf32aabf` |
| JVM | Kona/OpenJDK `25.0.4-internal`，release/product build |
| jtreg | `8-dev+0`（OpenJDK 配置使用的 `jtreg-8+2` 包） |
| JMH | 1.37 |

正式基准使用固定提交的独立工作树，运行前 `git status --porcelain` 为空。Apple Clang 21
会对部分既有 HotSpot `memset` 代码产生新告警，因此 configure 使用
`--disable-warnings-as-errors`，没有为构建修改或提交任何 JDK 源码。原开发工作树中的
用户改动保持不变，不参与本次正式结果。

## 构建与 jtreg 正确性基准

仓库根目录的统一入口负责检查 clean worktree、构建和测试：

```bash
export KONA_SRC=/path/to/clean/TencentKona-25
export KONA_HOME="$KONA_SRC/build/macosx-aarch64-server-release/images/jdk"
export BOOT_JDK=/path/to/bootstrap-jdk
export JT_HOME=/path/to/jtreg

make configure-kona
make jdk-images
make jtreg-baseline
```

| 测试组 | 总数 | 通过 | 失败/错误/跳过 |
|---|---:|---:|---:|
| `java/io/Serializable` | 150 | 150 | 0 |
| `java/io/ObjectInputStream` | 4 | 4 | 0 |
| `java/io/ObjectStreamClass` | 6 | 6 | 0 |
| **合计** | **160** | **160** | **0** |

`jtreg-baseline` 会显式构建 Java 测试库和 JDK jtreg native 测试镜像，再使用
`test-only` 运行三个选定目录。完整本地报告位于 Kona 构建目录的
`build/macosx-aarch64-server-release/test-results/jtreg_test_jdk_java_io_*/`。

## JMH 设计

基准代码位于 [`apps/serialization-jmh`](../../apps/serialization-jmh/README.md)，包含：

- 操作：`serialize`、`deserialize` 和 `roundTrip`；
- 数据：普通小对象 `SMALL`、含 100 个元素的对象图 `GRAPH`、实现自定义
  `writeObject/readObject` 的 `CUSTOM`；
- 每次操作创建新的独立对象流，使流头、类描述符和句柄表的成本都计入结果；
- 返回或消费被测结果，防止 JVM 将工作消除。

固定参数为 AverageTime、`us/op`、单线程、3 forks、每个 fork 预热 5 × 1 秒并测量
5 × 1 秒；正式运行同时启用 GC profiler。运行命令为：

```bash
make jmh-baseline
make capture-environment
```

## JMH 基准结果

误差为 JMH 输出的 99.9% 置信区间；每个结果含 15 次测量。

| 操作 | SMALL (us/op) | GRAPH (us/op) | CUSTOM (us/op) |
|---|---:|---:|---:|
| `serialize` | 0.398 ± 0.002 | 5.589 ± 0.124 | 0.366 ± 0.004 |
| `deserialize` | 1.152 ± 0.011 | 11.452 ± 0.120 | 0.681 ± 0.008 |
| `roundTrip` | 1.594 ± 0.012 | 17.866 ± 0.345 | 1.096 ± 0.003 |

GC profiler 记录的归一化分配量如下；数值越低越好：

| 操作 | SMALL (B/op) | GRAPH (B/op) | CUSTOM (B/op) |
|---|---:|---:|---:|
| `serialize` | 6,624 | 18,664 | 6,560 |
| `deserialize` | 3,653 | 34,021 | 2,840 |
| `roundTrip` | 10,296 | 54,840 | 9,392 |

正式原始数据与环境清单已提交到
[`results/task-2.1-baseline`](../../results/task-2.1-baseline/README.md)。JMH JSON 是数字的
权威来源，`SHA256SUMS` 记录文件校验和并由 `make check-results` 自动验证。

## 后续对比规则

优化后应使用同一条 `run.sh` 命令复跑，避免改变 fork、预热、数据模型或 JVM 构建类型。
报告时同时给出绝对值和变化率：

```text
变化率 = (优化后 - 基准) / 基准 × 100%
加速比 = 基准 / 优化后
```

数值越低越好。`GRAPH roundTrip` 的本次误差相对较大（约 1.9%），若优化幅度接近该
误差范围，应延长测量时间并至少重复整轮基准一次后再下结论。
