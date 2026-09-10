# 任务 2.3 focused A/B/B/A 复测

本目录归档 2026-09-10 对 `SerializationFocusedBenchmark` 的交错复测。顺序固定为
基线 A1、优化 B1、优化 B2、基线 A2；每段包含 3 forks、5 次 1 秒预热和 5 次 3 秒测量，
相比原正式实验把单次测量时间从 1 秒延长到 3 秒。全部运行在同一台 Apple M5 机器上，
使用与任务 2.1/2.3 正式结果相同的两套 release JDK 二进制。

## 结果

表中 A/B 是同版本两段运行的 JMH 点估计均值，仅用于紧凑展示总体方向；统计判断同时检查
每段 JMH 的 99.9% 置信区间和两组相邻配对，不把 30 个 iteration 当作完全独立样本。

| 操作 | 载荷 | A1 us/op | B1 us/op | B2 us/op | A2 us/op |
|---|---|---:|---:|---:|---:|
| serializePreSized | GRAPH | 4.549 ± 0.024 | 4.693 ± 0.080 | 4.673 ± 0.061 | 4.581 ± 0.048 |
| serializePreSized | GRAPH_CHINESE | 5.289 ± 0.285 | 5.360 ± 0.085 | 5.328 ± 0.047 | 5.239 ± 0.112 |
| serializePreSized | LARGE_OBJECT_ARRAY | 254.700 ± 6.928 | 263.247 ± 7.414 | 268.952 ± 7.377 | 261.064 ± 17.792 |
| serializeSteadyState | GRAPH | 3.751 ± 0.086 | 3.992 ± 0.057 | 4.003 ± 0.058 | 3.837 ± 0.043 |
| serializeSteadyState | GRAPH_CHINESE | 5.144 ± 0.943 | 4.622 ± 0.095 | 4.652 ± 0.057 | 4.502 ± 0.083 |
| serializeSteadyState | LARGE_OBJECT_ARRAY | 213.065 ± 1.698 | 215.283 ± 5.596 | 213.640 ± 2.988 | 222.365 ± 5.343 |

| 操作 | 载荷 | A 均值 us/op | B 均值 us/op | 耗时变化 | A B/op | B B/op | 分配变化 |
|---|---|---:|---:|---:|---:|---:|---:|
| `serializePreSized` | GRAPH | 4.565 | 4.683 | +2.60% | 17,416 | 15,072 | -13.46% |
| `serializePreSized` | GRAPH_CHINESE | 5.264 | 5.344 | +1.52% | 17,416 | 15,072 | -13.46% |
| `serializePreSized` | LARGE_OBJECT_ARRAY | 257.882 | 266.100 | +3.19% | 563,913 | 465,665 | -17.42% |
| `serializeSteadyState` | GRAPH | 3.794 | 3.998 | +5.37% | 2,400 | 56 | -97.67% |
| `serializeSteadyState` | GRAPH_CHINESE | 4.823 | 4.637 | -3.86% | 2,400 | 56 | -97.67% |
| `serializeSteadyState` | LARGE_OBJECT_ARRAY | 217.715 | 214.461 | -1.49% | 98,305 | 56 | -99.94% |

英文 `GRAPH` 是唯一在两种 focused 操作中都表现出稳定同向延迟代价的载荷：
`serializePreSized` 两组相邻配对分别为 +3.17% 和 +2.03%，`serializeSteadyState` 分别为
+6.42% 和 +4.34%。中文图和大数组存在置信区间重叠或顺序漂移，仍判为延迟不确定。

因此本轮定量收敛后的边界是：优化能确定降低目标写路径分配，但不是无条件延迟改进；在
没有明显 GC 压力、元素只有一个引用字段的扁平对象图中，新增分支、边界检查和异常安全控制
可能超过廉价 TLAB `Object[1]` 分配的成本。高频深/宽对象图且 GC 敏感的负载更可能获得
净收益，具体应用仍应以自身延迟与 GC 指标做 A/B。

## 原始产物

- `a1-baseline.json` / `a2-baseline.json`：基线提交 `3dfb92059520`；
- `b1-optimized.json` / `b2-optimized.json`：优化提交 `0c13d1af75d6`；
- `environment.txt`：顺序、参数、源码/JAR/JDK 二进制哈希；
- `SHA256SUMS`：上述五个文件的完整性校验。

四份 JSON 均为 JMH 原始输出，不删除离群 iteration。`make check-results` 会检查校验和、
JVM 路径、2×3 场景矩阵、3×5 原始样本、3 秒测量参数、GC 分配指标和本页关键数字。
