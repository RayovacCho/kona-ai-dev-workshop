---
name: hotspot-crash-analysis
description: 分析 HotSpot hs_err_pid 错误日志，识别 JVM 崩溃的直接原因，关联可信的 OpenJDK JBS 问题，并给出缓解建议。适用于 JVM 致命错误、原生信号、内部错误和崩溃日志分诊；不适用于普通 Java 异常堆栈。
---

# HotSpot 崩溃分析

如果 `hotspot-crash-analyzer` MCP 工具可用，请优先使用。先调用
`analyze_hotspot_crash`；如果无法联网查询，则使用它的解析结果，并提供生成的 JBS
搜索 URL，便于用户手动继续调查。

将日志作为首要证据。根据致命错误头、错误消息、问题帧、当前线程以及顶部原生/Java
栈帧确定直接原因。不要把 HotSpot 致命错误终止流程使用的信号误认为错误头中记录的
原始故障。

在声称某项 JBS 问题与日志匹配前，先阅读
[references/jbs-correlation.md](references/jbs-correlation.md)。在通过
`get_jbs_issue` 获取问题描述，并将其特征、受影响构建/平台、触发条件和堆栈上下文与
日志逐项比较之前，只能把搜索结果称为候选项。报告中应包含 JBS 编号、标题、状态、
受影响版本、修复版本、URL 和置信度。得出“未发现可信的已知问题”这一结论是合理的，
而且通常更可取。

识别有意触发的崩溃测试。`VMError::controlled_crash`、
`WhiteBox.controlledCrash`、`-XX:+WhiteBoxAPI`，以及 `test assert`、
`Crashing with number` 等消息，都是崩溃由人工注入的有力证据。此时应明确说明，这不能
证明产品存在缺陷，也不要把仅与通用信号相关的 JBS 搜索结果当作匹配项。
如果用户需要历史背景，应搜索精确的机制或测试符号，例如
`VMError::controlled_crash` 或 `ThreadsListHandleInErrorHandlingTest`；除非观察到的输出
与问题描述中的故障相同，否则应将这些问题标为与机制相关的背景资料。

返回一份简洁的报告，包含：

1. 结论和置信度；
2. 直接原因及引用的日志证据；
3. 故障路径和相关环境；
4. JBS 评估，必要时包括已排除的误报；
5. 按优先级排列的修复措施或后续诊断操作。

清楚区分事实、推断和建议。引用日志片段时，应隐去凭据和敏感的命令行参数值。
