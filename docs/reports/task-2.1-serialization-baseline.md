# 任务 2.1：Java 序列化基准

## 结论

Kona JDK 25 release 镜像构建成功，序列化相关 jtreg 测试共 **160 项全部通过**。
独立 JMH 程序完成 9 个基准场景；在本机上，小对象完整往返为
**1.593 ± 0.005 us/op**，100 元素对象图完整往返为
**17.828 ± 0.632 us/op**。这些数字作为任务 2.2 和 2.3 的优化前基准。

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

测试时 Kona 工作树中已有 5 个未提交的 HotSpot 编译兼容性改动和一个未跟踪的
WhiteBox 测试；它们不涉及 `java.io` 序列化代码。本任务没有修改这些文件。后续对比必须
保留相同基础提交、构建类型、机器和 JMH 参数，并单独记录序列化优化补丁。

## 构建与 jtreg 正确性基准

release 镜像使用以下流程构建和测试：

```bash
cd /Users/rayovac9/TencentKona-25
bash configure \
  --with-boot-jdk=/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home \
  --with-jtreg=/Users/rayovac9/tools/jtreg-8+2/jtreg
make CONF=macosx-aarch64-server-release images
make CONF=macosx-aarch64-server-release build-test-lib
make CONF=macosx-aarch64-server-release test-only \
  TEST='test/jdk/java/io/Serializable test/jdk/java/io/ObjectInputStream test/jdk/java/io/ObjectStreamClass' \
  JTREG='JOBS=4;TIMEOUT_FACTOR=4'
```

| 测试组 | 总数 | 通过 | 失败/错误/跳过 |
|---|---:|---:|---:|
| `java/io/Serializable` | 150 | 150 | 0 |
| `java/io/ObjectInputStream` | 4 | 4 | 0 |
| `java/io/ObjectStreamClass` | 6 | 6 | 0 |
| **合计** | **160** | **160** | **0** |

完整本地报告位于 Kona 构建目录的
`build/macosx-aarch64-server-release/test-results/jtreg_test_jdk_java_io_*/`。

本机直接执行 `make test` 会预先编译整个 HotSpot jtreg 原生库，并被无关的
`vmTestbase/.../ma04t002.cpp` Clang `-Werror` 告警阻断。因此这里先显式构建所需的
Java 测试库，再用 `test-only` 运行选定目录；这不会跳过选定目录中的任何测试。

## JMH 设计

基准代码位于 [`apps/serialization-jmh`](../../apps/serialization-jmh/README.md)，包含：

- 操作：`serialize`、`deserialize` 和 `roundTrip`；
- 数据：普通小对象 `SMALL`、含 100 个元素的对象图 `GRAPH`、实现自定义
  `writeObject/readObject` 的 `CUSTOM`；
- 每次操作创建新的独立对象流，使流头、类描述符和句柄表的成本都计入结果；
- 返回或消费被测结果，防止 JVM 将工作消除。

固定参数为 AverageTime、`us/op`、单线程、3 forks、每个 fork 预热 5 × 1 秒并测量
5 × 1 秒。运行命令为：

```bash
cd /Users/rayovac9/kona-ai-dev-workshop/apps/serialization-jmh
./build.sh
./run.sh
```

## JMH 基准结果

误差为 JMH 输出的 99.9% 置信区间；每个结果含 15 次测量。

| 操作 | SMALL (us/op) | GRAPH (us/op) | CUSTOM (us/op) |
|---|---:|---:|---:|
| `serialize` | 0.397 ± 0.003 | 5.892 ± 0.159 | 0.369 ± 0.007 |
| `deserialize` | 1.147 ± 0.007 | 11.456 ± 0.062 | 0.669 ± 0.001 |
| `roundTrip` | 1.593 ± 0.005 | 17.828 ± 0.632 | 1.118 ± 0.052 |

原始 JSON 保存在本地
`apps/serialization-jmh/results/baseline-20260826-020803.json`，按仓库约定不提交。

## 后续对比规则

优化后应使用同一条 `run.sh` 命令复跑，避免改变 fork、预热、数据模型或 JVM 构建类型。
报告时同时给出绝对值和变化率：

```text
变化率 = (优化后 - 基准) / 基准 × 100%
加速比 = 基准 / 优化后
```

数值越低越好。`GRAPH roundTrip` 的本次误差相对较大（约 3.5%），若优化幅度接近该
误差范围，应延长测量时间并至少重复整轮基准一次后再下结论。

