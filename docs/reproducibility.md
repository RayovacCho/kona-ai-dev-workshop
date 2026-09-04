# 构建与基准复现约定

本文是所有任务的统一约定；单项报告只记录该次实验的参数与结果。

## 仓库边界

- 本仓库保存规划、程序、工具、精简测试样本、正式结构化结果和报告。
- Kona 源码修改只进入 `TencentKona-25` fork，并以 commit 标识。
- JDK/JMH 构建目录、依赖 JAR、临时日志和试跑结果不提交。
- 按导师要求，任务 1.1 的七类受控崩溃各提交第一轮的一份完整 `hs_err` 及校验和；重复运行日志仍不提交。
- 可审计且体积小的正式结果（JMH JSON、环境清单）必须提交。

## 正式基准前置条件

正式结果必须满足：

1. Kona 工作树 `git status --porcelain` 为空；
2. 报告和环境文件记录完整 Kona commit；
3. 环境文件记录 JMH 源码与依赖锁文件的 SHA-256；
4. 使用 release/product JDK 测性能，fastdebug JDK 只用于 WhiteBox/诊断测试；
5. 基准前后使用相同硬件、JMH 参数、数据模型和 JDK 配置；
6. JMH 至少 3 forks、5 次预热、5 次测量，并记录 `-prof gc` 分配指标；
7. 正确性 jtreg 全部通过后，性能结果才可作为优化结论。
8. 所有正式 JMH 只使用 `$KONA_SRC/build/$KONA_CONF/images/jdk`，不得与构建树中的
   exploded `jdk` 混用；`release` 文件中的 `SOURCE` 修订必须匹配 Kona HEAD；
9. 严格比较耗时时，基线与候选还必须使用相同 OS 版本和 JVM 镜像形式。
10. 场景矩阵至少包含中英文字符串、普通对象图和大对象数组；每种载荷都必须在 setup
    阶段完成内容级往返校验。

根目录 `Makefile` 会拒绝 dirty Kona 工作树、错误的 `KONA_HOME`，以及源码修订不匹配的
JDK 镜像。环境清单 schema 2 同时记录 `release`、`bin/java` 和 `lib/modules` 的 SHA-256，
将源码提交与被测产物绑定起来。

## 环境变量

仓库脚本不包含个人绝对路径。运行前设置：

```bash
export KONA_SRC=/path/to/TencentKona-25
export KONA_CONF=macosx-aarch64-server-release
export KONA_HOME="$KONA_SRC/build/$KONA_CONF/images/jdk"
export BOOT_JDK=/path/to/bootstrap-jdk
export JT_HOME=/path/to/jtreg
```

Linux 或其他配置通过覆盖 `KONA_CONF` 处理。

## 统一命令

```bash
make check
make check-crash-logs
make configure-kona
make jdk-images
make jtreg-baseline
RESULT_DIR=results/<新目录> make jmh-baseline
RESULT_DIR=results/<新目录> make capture-environment
make check-results
```

`RESULT_DIR=results/<新目录> make benchmark` 会依次构建镜像、跑 jtreg、执行带 GC
profiler 的正式 JMH，并采集环境。目标默认拒绝覆盖已有结果；只有明确重建同一基准时才
使用 `ALLOW_BASELINE_OVERWRITE=1`。

`make check-results` 会递归发现 `results/` 下的基准结果和新增复现实验，要求校验和清单
恰好包含 `jmh-result.json` 与 `environment.txt`，并验证 JMH 使用的 JVM 与环境清单一致。
它还会拒绝重复或空的环境字段、无效数值，并验证每一对正式基线与最终结果使用相同的 OS、
架构、CPU 和内存；场景矩阵依据环境中绑定的基准源码版本校验。`make check-crash-logs`
则验证提交的七份完整崩溃日志及其 `SHA256SUMS`、错误
类别、用例编号和受控 WhiteBox 调用链。这两个校验均包含在 `make check` 和 CI 中。
除明确列出的 Round 1–3 legacy 候选外，当前正式基线、最终结果以及以后新增的复现实验
都必须使用 `environment_schema=2`。Round 1–3 只作为历史候选的决策证据，不再作为
满足当前产物绑定规则的正式性能证据；该例外按精确目录名限制，不能被新结果继承。

## 结果解释

- AverageTime 的 `us/op` 越低越好；分配量 `gc.alloc.rate.norm` 的 `B/op` 越低越好。
- 同时报告绝对值、99.9% 置信区间、变化率和加速比。
- 若优化幅度不超过基准误差，应增加测量时间并重复整轮实验。
- 控制台输出可以忽略；提交的 JSON 是数字的权威来源，Markdown 表格必须由其核对。
