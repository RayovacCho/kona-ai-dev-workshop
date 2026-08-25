# Kona AI 开发工作坊

本仓库是课程作业的**规划、代码、报告与工具**集合，对应两项工作：

1. 用 AI 辅助分析 JVM 崩溃  
2. 加速 Java 序列化  

JDK 源码改动在独立的 [Tencent Kona JDK 25 fork](https://github.com/RayovacCho/TencentKona-25) 中完成。本仓库不包含完整 JDK 源码，只保存说明、小程序、智能体技能、MCP 以及报告。

---

## 仓库怎么读

| 你想看什么 | 去哪里 |
|------------|--------|
| 总规划与进度 | [docs/](docs/) |
| 崩溃分析、JMH 等报告 | [docs/reports/](docs/reports/) |
| 触发 JVM 崩溃的小程序、JMH 程序 | [apps/](apps/) |
| 崩溃分析智能体技能 | [skills/](skills/) |
| 崩溃分析 MCP 服务器 | [mcp/](mcp/) |

建议阅读顺序：本 README → `docs/` 规划 → 对应 `apps/` / `skills/` / `mcp/` → `docs/reports/` 结论。

---

## 任务 1：AI 辅助分析 JVM 崩溃

### 1.1 扩展 WhiteBox API，在运行期触发 JVM 崩溃

- 构建 Kona 的 **fastdebug** 版本  
- 在 WhiteBox 中增加 `controlledCrash` 接口（底层对接已有的 `VMError::controlled_crash`）  
- 提供应用程序，按指定编号触发崩溃  
- 测试多种崩溃类型，收集 HotSpot Error Log（`hs_err_pid*.log`）

相关位置：`apps/`（触发程序）以及 Kona fork 上的
[实现提交](https://github.com/Tencent/TencentKona-25/commit/3dfb920595202df2dfa5b9f5b6c3b124cf32aabf)。

### 1.2 利用 AI 分析 JVM 崩溃

- 解析 HotSpot Error Log  
- 分析崩溃的直接原因  
- 关联 [Java Bug System](https://bugs.openjdk.org/) 中的已知问题  
- 给出解决方案或建议  
- 编写智能体技能与 MCP 服务器，使 AI 可重复执行上述流程

相关位置：`skills/`、`mcp/`、`docs/reports/`。

---

## 任务 2：序列化加速

### 2.1 获取测试基准

- 构建 Kona JDK，运行相关 **jtreg** 测试，记录基准  
- 编写 **JMH** 程序，测量当前序列化实现性能，记录基准数字  

### 2.2 使用 Codex 优化

- 规划优化方案（写入 `docs/`）  
- 在 Kona 源码中实现（主要涉及 `java.io` 序列化路径），并跑测试  

### 2.3 进一步改进

- 对优化后的实现再跑 JMH，得到优化后性能  
- 用 Codex 分析与基准的差异  
- 根据分析做下一轮改进  

相关位置：`apps/`（JMH）、Kona fork、`docs/reports/`。

---

## 目录说明

```text
kona-ai-dev-workshop/
├── README.md              ← 本文件
├── docs/                  ← 规划、步骤说明
│   └── reports/           ← 崩溃分析、JMH 对比等报告
├── apps/                  ← 崩溃触发程序、JMH 等独立小项目
├── skills/                ← 智能体技能（如 SKILL.md）
└── mcp/                   ← MCP 服务器源码
```

各目录会随作业推进逐步填入文件。尚未完成的部分在对应文档中用 TODO 标明。

---

## 本仓库与 Kona 源码的分工

| 内容 | 放哪里 |
|------|--------|
| 规划、报告、技能、MCP、小工具 | **本仓库**（给导师看） |
| WhiteBox、`java.io` 序列化等 JDK 修改 | **Kona 个人分支**（完整源码与构建） |
| fastdebug 构建产物、`hs_err` 全文、JMH 原始超大输出 | **不提交**；报告里只放摘要和关键数字 |

---

## 环境与构建（Kona）

在 Kona 源码树中构建 fastdebug（具体依赖以官方文档为准）：

```bash
cd /Users/rayovac9/TencentKona-25
bash configure --with-debug-level=fastdebug
make images
```

jtreg、JMH 的具体测试命令，以及崩溃触发程序的用法，将写在 `docs/` 与 `apps/` 各自的说明中（完成后补链接）。

参考：

- [Tencent Kona JDK 25](https://github.com/Tencent/TencentKona-25)  
- [Kona Wiki](https://github.com/Tencent/TencentKona-25/wiki)

---

## 进度

| 项 | 状态 |
|----|------|
| 1.1 WhiteBox `controlledCrash` + 触发程序 + 崩溃测试 | 已完成（[规划](docs/task-1.1-plan.md) / [报告](docs/reports/task-1.1-controlled-crash.md)） |
| 1.2 Error Log 分析 + JBS 关联 + Skill / MCP | 已完成（[报告](docs/reports/task-1.2-ai-crash-analysis.md) / [Skill](skills/hotspot-crash-analysis/SKILL.md) / [MCP](mcp/hotspot-crash-analyzer/README.md)） |
| 2.1 jtreg / JMH 基准 | 未开始 |
| 2.2 Codex 方案与实现 | 未开始 |
| 2.3 JMH 对比与再优化 | 未开始 |

完成一项后把上表改为「进行中」或「已完成」，并在 `docs/` 中补对应文档链接。

---
