# 任务 2.1 规划：建立序列化测试基准

## 目标与验收条件

1. 从干净的 Kona 源码提交构建 release/product `images/jdk`；性能测试不得使用 fastdebug。
2. 运行 `Serializable`、`Externalizable`、`ObjectInputStream` 和 `ObjectStreamClass` 相关
   jtreg，记录测试选择、总数和通过/失败结果。
3. 提供独立 JMH 程序，覆盖序列化、反序列化和完整往返，并同时记录耗时与每操作分配量。
4. 场景至少覆盖中英文小对象、中英文对象图、大对象数组和自定义序列化；setup 必须对
   每类载荷执行内容级往返校验。
5. 正式 JMH 使用 3 forks、5 次预热、5 次测量和 GC profiler，保存原始 JSON、环境清单
   与 SHA-256 校验和。
6. 基准结果必须绑定 Kona 提交、JDK 镜像、JMH 源码、脚本和依赖版本，且不可覆盖。

## 基准矩阵

| 维度 | 取值 |
|---|---|
| 操作 | `serialize`、`deserialize`、`roundTrip` |
| 载荷 | `SMALL`、`SMALL_CHINESE`、`GRAPH`、`GRAPH_CHINESE`、`LARGE_OBJECT_ARRAY`、`CUSTOM` |
| 主指标 | AverageTime，`us/op`，越低越好 |
| 辅助指标 | `gc.alloc.rate.norm`，`B/op`，越低越好 |

完整矩阵共 18 项。JMH 每次操作新建对象流，用于衡量包含流头、类描述符和句柄表成本的
端到端实现；聚焦或流复用基准只能作为补充，不能替换这组基线。

## 执行步骤

1. 固定干净的 Kona 基线提交，配置 release 构建并生成 `images/jdk`。
2. 构建 jtreg 所需的 Java/native 测试库，执行四个序列化测试目录。
3. 使用该 JDK 构建 JMH benchmark JAR，先 smoke test，再运行完整正式矩阵。
4. 采集系统、CPU、内存、JDK `release` 信息、源码与二进制哈希。
5. 用仓库校验器检查场景矩阵、原始样本数、单位、有限数值、路径绑定和校验和。
6. 把 JSON 作为数字的权威来源，将摘要写入基准报告。

## 统一命令

```bash
export KONA_SRC=/path/to/clean/TencentKona-25
export KONA_CONF=macosx-aarch64-server-release
export KONA_HOME="$KONA_SRC/build/$KONA_CONF/images/jdk"
export BOOT_JDK=/path/to/bootstrap-jdk
export JT_HOME=/path/to/jtreg

make configure-kona
RESULT_DIR=results/reproductions/task-2.1-YYYYMMDD make benchmark
make check-results
```

结果解释、环境和正式数字见
[任务 2.1 基准报告](reports/task-2.1-serialization-baseline.md)。
