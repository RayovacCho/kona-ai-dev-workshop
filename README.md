# Kona AI 开发工作坊

本仓库是课程作业的**规划、代码、报告与工具**集合，对应两项工作：

1. 用 AI 辅助分析 JVM 崩溃  
2. 加速 Java 序列化  

JDK 源码改动在独立的 [Tencent Kona JDK 25 fork](https://github.com/RayovacCho/TencentKona-25) 中完成。本仓库不包含完整 JDK 源码，保存规划与报告、演示程序、智能体技能、MCP、正式基准结果以及复现自动化。

---

## 仓库怎么读

| 你想看什么 | 去哪里 |
|------------|--------|
| 总规划与进度 | [docs/](docs/) |
| 崩溃分析、JMH 等报告 | [docs/reports/](docs/reports/) |
| 触发 JVM 崩溃的小程序、JMH 程序 | [apps/](apps/) |
| 当前正式结果与历史候选数据 | [results/](results/) |
| 崩溃分析智能体技能 | [skills/](skills/) |
| 崩溃分析 MCP 服务器 | [mcp/](mcp/) |

建议阅读顺序：本 README → `docs/` 规划 → 对应 `apps/` / `skills/` / `mcp/` → `docs/reports/` 结论。

---

## 快速开始

仓库内的 Python 工具要求 **Python 3.6 或更高版本**，且不依赖第三方 Python 包。
验证仓库内的脚本、MCP 测试、七份完整崩溃日志和已提交的正式基准结果：

```bash
make check
```

默认使用 `python3`；如需指定解释器，执行
`make check PYTHON=/path/to/python3`。

在新的结果目录中完整复跑 Kona release 构建、序列化 jtreg 和 JMH：

```bash
export KONA_SRC=/path/to/clean/TencentKona-25
export KONA_CONF=macosx-aarch64-server-release
export KONA_HOME="$KONA_SRC/build/$KONA_CONF/images/jdk"
export BOOT_JDK=/path/to/bootstrap-jdk
export JT_HOME=/path/to/jtreg

make configure-kona
RESULT_DIR=results/reproductions/task-2.1-YYYYMMDD make benchmark
```

正式结果默认不可覆盖；重复实验必须使用新的 `RESULT_DIR`。完整前置条件与命令说明见
[构建与基准复现约定](docs/reproducibility.md)。

---

## 任务 1：AI 辅助分析 JVM 崩溃

### 1.1 扩展 WhiteBox API，在运行期触发 JVM 崩溃

- 构建 Kona 的 **fastdebug** 版本  
- 在 WhiteBox 中增加 `controlledCrash` 接口（底层对接已有的 `VMError::controlled_crash`）  
- 提供应用程序，按指定编号触发崩溃  
- 测试多种崩溃类型，收集 HotSpot Error Log（`hs_err_pid*.log`）

相关内容：[受控崩溃应用](apps/controlled-crash/README.md)、
[任务报告](docs/reports/task-1.1-controlled-crash.md)以及 Kona fork 上的
[接口实现提交](https://github.com/RayovacCho/TencentKona-25/commit/3dfb920595202df2dfa5b9f5b6c3b124cf32aabf)和
[回归测试提交](https://github.com/RayovacCho/TencentKona-25/commit/5b6cb179a)。

### 1.2 利用 AI 分析 JVM 崩溃

- 解析 HotSpot Error Log  
- 分析崩溃的直接原因  
- 关联 [Java Bug System](https://bugs.openjdk.org/) 中的已知问题  
- 给出解决方案或建议  
- 编写智能体技能与 MCP 服务器，使 AI 可重复执行上述流程

相关内容：[任务报告](docs/reports/task-1.2-ai-crash-analysis.md)、
[崩溃分析 Skill](skills/hotspot-crash-analysis/SKILL.md)和
[MCP 服务器](mcp/hotspot-crash-analyzer/README.md)。

---

## 任务 2：序列化加速

### 2.1 获取测试基准

- 构建 Kona JDK，运行相关 **jtreg** 测试，记录基准  
- 编写 **JMH** 程序，测量当前序列化实现性能，记录基准数字  

相关内容：[JMH 程序](apps/serialization-jmh/README.md)、
[基准报告](docs/reports/task-2.1-serialization-baseline.md)和
[机器可读结果](results/task-2.1-baseline/README.md)。

### 2.2 使用 Codex 优化

- 规划优化方案（写入 `docs/`）  
- 在 Kona 源码中实现（主要涉及 `java.io` 序列化路径），并跑测试  

已完成：[优化规划](docs/task-2.2-plan.md)、
[实现与测试报告](docs/reports/task-2.2-codex-serialization-optimization.md)和
[Kona PR #1](https://github.com/RayovacCho/TencentKona-25/pull/1)。

### 2.3 进一步改进

- 对优化后的实现再跑 JMH，得到优化后性能  
- 用 Codex 分析与基准的差异
- 根据分析做下一轮改进  

已完成：[实验规划](docs/task-2.3-plan.md)、
[完整分析报告](docs/reports/task-2.3-serialization-followup.md)和
[最终机器可读结果](results/task-2.3-final/README.md)。中间候选数据保存在
`results/task-2.3-round1/` 至 `task-2.3-round3/`，仅用于审计 Codex 的改进依据，
不作为当前正式性能结论。

根据导师评审，正式 JMH 已自然扩充为 18 项，覆盖中英文小对象、中英文对象图、4096 元素
中英文混合对象数组和自定义序列化，并完成同机 A/B 与反向复测。结论是目标写路径分配
稳定下降，但尚未证明稳定的延迟加速；数据与解释已并入 2.1 基线和 2.3 最终报告。

---

## 目录说明

```text
kona-ai-dev-workshop/
├── .github/workflows/    ← 持续集成检查
├── README.md              ← 本文件
├── Makefile               ← 构建、测试与基准统一入口
├── LICENSE                ← MIT 许可证
├── docs/                  ← 规划、步骤说明
│   └── reports/           ← 崩溃分析、JMH 对比等报告
├── apps/                  ← 崩溃触发程序、JMH 等独立小项目
├── results/               ← 正式 JSON、环境清单和校验和
├── scripts/               ← 环境采集与结果校验脚本
├── skills/                ← 智能体技能（如 SKILL.md）
└── mcp/                   ← MCP 服务器源码
```

各目录会随作业推进逐步填入文件，任务状态以本文末尾的进度表和对应报告为准。

---

## 本仓库与 Kona 源码的分工

| 内容 | 放哪里 |
|------|--------|
| 规划、报告、技能、MCP、小工具 | **本仓库**（给导师看） |
| WhiteBox、`java.io` 序列化等 JDK 修改 | **Kona 个人分支**（完整源码与构建） |
| 构建产物、依赖 JAR、临时日志和试跑结果 | **不提交** |
| 任务 1.1 第一轮七类完整 `hs_err` 及校验和 | **提交**到 `apps/controlled-crash/crash-logs/`，重复运行日志不提交 |
| 正式 JMH JSON 与环境清单 | **提交**到 `results/`，保证结果可审计 |

---

## Kona 构建类型

两类任务使用不同构建，不能混用：

| 构建 | 用途 |
|---|---|
| fastdebug | WhiteBox、受控崩溃和诊断测试 |
| release/product | jtreg 正确性基准和 JMH 性能测试 |

fastdebug 示例：

```bash
export KONA_SRC=/path/to/TencentKona-25
cd "$KONA_SRC"
bash configure --with-debug-level=fastdebug
make images
```

release 性能基准应使用“快速开始”中的统一 Make 命令，具体测试选择和参数见
[任务 2.1 基准报告](docs/reports/task-2.1-serialization-baseline.md)。

参考：

- [Tencent Kona JDK 25](https://github.com/Tencent/TencentKona-25)  
- [Kona Wiki](https://github.com/Tencent/TencentKona-25/wiki)
- [MIT License](LICENSE)

---

## 进度

| 项 | 状态 |
|----|------|
| 1.1 WhiteBox `controlledCrash` + 触发程序 + 崩溃测试 | 已完成（[规划](docs/task-1.1-plan.md) / [报告](docs/reports/task-1.1-controlled-crash.md)） |
| 1.2 Error Log 分析 + JBS 关联 + Skill / MCP | 已完成（[报告](docs/reports/task-1.2-ai-crash-analysis.md) / [Skill](skills/hotspot-crash-analysis/SKILL.md) / [MCP](mcp/hotspot-crash-analyzer/README.md)） |
| 2.1 jtreg / JMH 基准 | 已完成（[报告](docs/reports/task-2.1-serialization-baseline.md) / [JMH](apps/serialization-jmh/README.md)） |
| 2.2 Codex 方案与实现 | 已完成（[规划](docs/task-2.2-plan.md) / [报告](docs/reports/task-2.2-codex-serialization-optimization.md)） |
| 2.3 JMH 对比与再优化 | 已完成（[规划](docs/task-2.3-plan.md) / [报告](docs/reports/task-2.3-serialization-followup.md) / [结果](results/task-2.3-final/README.md)） |

完成一项后把上表改为「进行中」或「已完成」，并在 `docs/` 中补对应文档链接。

---
