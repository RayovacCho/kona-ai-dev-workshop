# Java 序列化 JMH 基准

该程序测量 Kona JDK 内置 `java.io` 序列化实现，覆盖三条操作路径：

- `serialize`：对象写为新的独立字节流；
- `deserialize`：从预先生成的字节流读取对象；
- `roundTrip`：完整序列化与反序列化。

每条路径分别使用小对象（`SMALL`）、100 个元素的对象图（`GRAPH`）和自定义
`writeObject/readObject` 对象（`CUSTOM`）。每次操作新建对象流，结果包含真实的流头、
类描述符和句柄表成本，不会受到跨对象流缓存的影响。

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

首次构建会从 Maven Central 下载 JMH 1.37 及其运行依赖，并按
`dependencies.sha256` 校验。默认配置为 3 个 fork、
5 次预热和 5 次测量，每次 1 秒；结果以 `us/op` 输出，并保存到 `results/` 下的 JSON
文件。`lib/`、`build/` 和普通试跑结果不提交版本库。

正式基准使用根目录 `make jmh-baseline`，同时启用 GC profiler，并将 JSON 保存到
版本控制中的 `results/task-2.1-baseline/`。完整结果见
[任务 2.1 基准报告](../../docs/reports/task-2.1-serialization-baseline.md)。
