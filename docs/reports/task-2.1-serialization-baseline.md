# 任务 2.1：Java 序列化基准

## 结论

Kona JDK 25 release 镜像构建成功，序列化相关 jtreg 测试共 **162 项全部通过**。
独立 JMH 程序完成 18 项基准，覆盖中英文小对象、中英文 100 元素对象图、4096 元素
中英文混合对象数组和自定义序列化。在本机上，英文小对象完整往返为
**1.601 ± 0.010 us/op**，英文对象图为 **17.913 ± 0.224 us/op**，大对象数组为
**631.181 ± 16.029 us/op**。这些数字与最终结果在同一环境中顺序重测，作为当前可审计基准。

## 基准环境

| 项目 | 值 |
|---|---|
| 日期 | 2026-09-04 |
| 机器 | MacBook Air，Apple M5（4 性能核 + 6 能效核），16 GB |
| 系统 | macOS 26.6.2（arm64） |
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
| `java/io/Externalizable` | 2 | 2 | 0 |
| `java/io/ObjectInputStream` | 4 | 4 | 0 |
| `java/io/ObjectStreamClass` | 6 | 6 | 0 |
| **合计** | **162** | **162** | **0** |

`jtreg-baseline` 会显式构建 Java 测试库和 JDK jtreg native 测试镜像，再使用
`test-only` 运行四个选定目录。完整本地报告位于 Kona 构建目录的
`build/macosx-aarch64-server-release/test-results/jtreg_test_jdk_java_io_*/`。

## JMH 设计

基准代码位于 [`apps/serialization-jmh`](../../apps/serialization-jmh/README.md)，包含：

- 操作：`serialize`、`deserialize` 和 `roundTrip`；
- 数据：英文/中文小对象 `SMALL` / `SMALL_CHINESE`、英文/中文 100 元素对象图
  `GRAPH` / `GRAPH_CHINESE`、4096 元素中英文混合对象数组 `LARGE_OBJECT_ARRAY`，以及
  实现自定义 `writeObject/readObject` 的 `CUSTOM`；
- 每次操作创建新的独立对象流，使流头、类描述符和句柄表的成本都计入结果；
- 返回或消费被测结果，防止 JVM 将工作消除；
- setup 对标量、集合和数组执行内容级往返校验，避免只检查类型而遗漏功能回归。

固定参数为 AverageTime、`us/op`、单线程、3 forks、每个 fork 预热 5 × 1 秒并测量
5 × 1 秒；正式运行同时启用 GC profiler。运行命令为：

```bash
make jmh-baseline
make capture-environment
```

## JMH 基准结果

误差为 JMH 输出的 99.9% 置信区间；每个结果含 15 次测量。耗时与 GC profiler 的
归一化分配量均越低越好。

| 操作 | 载荷 | 耗时 (us/op) | 分配量 (B/op) |
|---|---|---:|---:|
| `serialize` | SMALL | 0.398 ± 0.002 | 6,624 |
| `serialize` | SMALL_CHINESE | 0.404 ± 0.001 | 6,624 |
| `serialize` | GRAPH | 5.618 ± 0.084 | 18,664 |
| `serialize` | GRAPH_CHINESE | 6.596 ± 0.220 | 18,664 |
| `serialize` | LARGE_OBJECT_ARRAY | 271.210 ± 6.586 | 958,146 |
| `serialize` | CUSTOM | 0.364 ± 0.001 | 6,560 |
| `deserialize` | SMALL | 1.159 ± 0.007 | 3,672 |
| `deserialize` | SMALL_CHINESE | 1.183 ± 0.005 | 3,685 |
| `deserialize` | GRAPH | 11.363 ± 0.111 | 34,021 |
| `deserialize` | GRAPH_CHINESE | 11.963 ± 0.167 | 39,043 |
| `deserialize` | LARGE_OBJECT_ARRAY | 341.003 ± 3.220 | 1,255,426 |
| `deserialize` | CUSTOM | 0.668 ± 0.003 | 2,856 |
| `roundTrip` | SMALL | 1.601 ± 0.010 | 10,312 |
| `roundTrip` | SMALL_CHINESE | 1.611 ± 0.002 | 10,344 |
| `roundTrip` | GRAPH | 17.913 ± 0.224 | 54,840 |
| `roundTrip` | GRAPH_CHINESE | 19.233 ± 0.685 | 58,776 |
| `roundTrip` | LARGE_OBJECT_ARRAY | 631.181 ± 16.029 | 2,213,572 |
| `roundTrip` | CUSTOM | 1.089 ± 0.004 | 9,392 |

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

数值越低越好。若优化幅度接近误差范围，应延长测量时间并至少重复一轮；中英文和大对象
数组必须分别报告，不能用单一载荷概括总体收益。
