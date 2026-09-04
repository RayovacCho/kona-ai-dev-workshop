# Java 序列化 JMH 基准

该程序测量 Kona JDK 内置 `java.io` 序列化实现，覆盖三条操作路径：

- `serialize`：对象写为新的独立字节流；
- `deserialize`：从预先生成的字节流读取对象；
- `roundTrip`：完整序列化与反序列化。

每条路径分别使用英文小对象（`SMALL`）、中文小对象（`SMALL_CHINESE`）、100 个元素的
英文/中文对象图（`GRAPH` / `GRAPH_CHINESE`）、4096 元素的中英文混合对象数组
（`LARGE_OBJECT_ARRAY`）和自定义 `writeObject/readObject` 对象（`CUSTOM`）。每次操作
新建对象流，结果包含真实的流头、类描述符和句柄表成本，不会受到跨对象流缓存的影响。
每类载荷在 JMH setup 阶段还会执行内容级往返校验，避免仅凭类型相同掩盖字段或数组回归。

同目录还包含 `SerializationFocusedBenchmark`，用于下一轮观测写路径本身：

- `serializePreSized` 按已知输出大小预分配缓冲区，减少扩容噪声；
- `serializeSteadyState` 复用 `ObjectOutputStream` 并在每次调用前 reset，减少流构造噪声；
- 聚焦英文/中文对象图和 4096 元素数组，不改变已经归档的 18 项正式结果。

## 运行

设置 Kona release 镜像后运行：

```bash
export KONA_HOME=/path/to/kona-release-jdk
./build.sh
./run.sh
```

也可以指定另一个 JDK，并透传 JMH 参数：

```bash
KONA_HOME=/path/to/jdk ./run.sh -f 1 -wi 2 -i 3
```

聚焦基准可执行：

```bash
KONA_HOME=/path/to/jdk \
JMH_INCLUDE=workshop.serialization.SerializationFocusedBenchmark \
./run.sh -prof gc
```

首次构建会从 Maven Central 下载 JMH 1.37 及其运行依赖，并按
`dependencies.sha256` 校验。默认配置为 3 个 fork、
5 次预热和 5 次测量，每次 1 秒；结果以 `us/op` 输出，并保存到 `results/` 下的 JSON
文件。`lib/`、`build/` 和普通试跑结果不提交版本库。

`run.sh` 会在基准源码、构建脚本或依赖锁文件比现有 JAR 更新时自动重建，避免源码修改后
误用旧基准产物。CI 使用 `make jmh-smoke` 编译并短时执行完整场景矩阵；正式数据仍只能由
根目录的受控流程生成。

正式基准使用根目录 `make jmh-baseline`，同时启用 GC profiler，并将 JSON 保存到
版本控制中的 `results/`。任务 2.1 基线见
[基准报告](../../docs/reports/task-2.1-serialization-baseline.md)，任务 2.3 的多轮对比、
Codex 分析与最终结果见[进一步优化报告](../../docs/reports/task-2.3-serialization-followup.md)
和[`results/task-2.3-final/`](../../results/task-2.3-final/README.md)。
