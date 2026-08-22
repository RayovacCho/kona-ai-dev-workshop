# 任务 1.2 报告：利用 AI 分析 JVM 崩溃

## 交付物

- 智能体技能：`skills/hotspot-crash-analysis/`
- MCP 服务器：`mcp/hotspot-crash-analyzer/`
- 测试样本：1.1 产生的本地 `apps/controlled-crash/crash-logs/hs_err_pid*.log`

技能规定证据优先级和 JBS 关联标准；MCP 负责可重复的日志解析、直接原因初判、JBS
公开 REST API 查询以及建议生成。二者明确区分“搜索候选”和“确认匹配”，避免仅凭
SIGSEGV 等宽泛关键词错误关联。

## 样本分析结论

对 1.1 七类日志各取一份分析，直接原因如下：

| 编号 | 日志证据 | 直接原因 | JBS 结论 | 建议 |
|---:|---|---|---|---|
| 1 | `assert(how == 0) failed: test assert` | `controlled_crash(1)` 主动触发断言 | 不适用：测试注入，并非产品缺陷 | 仅在隔离 fastdebug 测试进程使用 |
| 2 | `guarantee(how == 0) failed: test guarantee` | `controlled_crash(2)` 主动触发 guarantee | 不适用 | 同上 |
| 14 | `SIGSEGV`，问题帧为 `VMError::controlled_crash` | 主动空地址访问 | 不适用 | 不把普通 SIGSEGV 问题当作匹配 |
| 15 | `SIGFPE`，栈含 `VMError::controlled_crash` | 主动发送/触发 SIGFPE；macOS 顶帧为 `__pthread_kill` | 不适用 | 判断原始信号时以 fatal header 和调用链为准 |
| 16 | `Force crash with an active ThreadsListHandle` | 主动 fatal 测试活动 handle 下的错误报告 | 不适用 | 保留为错误处理回归样本 |
| 17 | `Force crash with a nested ThreadsListHandle` | 主动 fatal 测试嵌套 handle | 不适用 | 保留为错误处理回归样本 |
| 99 | `fatal error: Crashing with number 99` | 通用受控 fatal 分支 | 不适用 | 不需要升级或打 JVM 补丁 |

所有样本的共同调用链包含 `WhiteBox.controlledCrash`、`WB_ControlledCrash` 和
`VMError::controlled_crash`，且命令行启用了 `-XX:+WhiteBoxAPI`。因此高置信度结论是：
这些崩溃均为 1.1 有意注入，不是 Kona/OpenJDK 的未知缺陷。MCP 对这类日志返回空的
JBS 问题列表并说明跳过原因；若强制用宽泛关键词查询，得到的问题只能算无关候选。

## JBS 已知问题关联

使用精确函数名和测试名检索可找到下列历史问题。它们解释受控崩溃机制的演进，但没有
一个与当前日志表现出相同的非预期故障，所以不能将它们写成本次崩溃的根因。

| JBS | 状态 / 版本 | 与样本的关系 | 判定 |
|---|---|---|---|
| [JDK-8202509](https://bugs.openjdk.org/browse/JDK-8202509) `controlled_crash` 有意触发未定义行为 | 已关闭 / 不修复；影响 11 | 说明早期实现的可靠性风险 | 历史背景；当前日志按预期稳定产出，非本次缺陷 |
| [JDK-8296906](https://bugs.openjdk.org/browse/JDK-8296906) 编号 14 使用错误的代码/地址 | 已在 20 中修复；影响 20 | 与 SIGSEGV 编号 14 精确相关 | 当前为 25.0.4，且目标是主动触发崩溃；无证据表明旧问题复现 |
| [JDK-8252148](https://bugs.openjdk.org/browse/JDK-8252148) 将 `controlled_crash` 改为 `#ifdef ASSERT` | 已在 17 中修复；影响 16 | 解释为何 API 只应暴露在 fastdebug/debug 测试环境 | 当前源码和技能建议均符合该设计，不是故障 |
| [JDK-8231627](https://bugs.openjdk.org/browse/JDK-8231627) ThreadsListHandle 测试打印线程失败 | 已在 17 中修复；影响 14/15 | 与编号 16/17 的错误报告路径相关 | 当前日志成功输出 Java 线程/SMR 信息，没有相同二次 SIGSEGV |

因此，“关联 JBS”的最终结论不是简单的“没有搜索结果”，而是：存在上述机制相关历史
问题，但当前 JDK 25 样本没有命中其故障条件；直接原因仍是 WhiteBox 有意调用
`VMError::controlled_crash`。

## 验证范围

自动化测试覆盖 assert、SIGSEGV、SIGFPE、非 hs_err 输入、JQL 转义、MCP 初始化、
工具枚举和工具调用。真实 JBS 查询依赖网络；断网时服务降级返回手工查询 URL，不影响
本地直接原因分析。

JBS 集成测试分别使用 `VMError::controlled_crash`、
`ThreadsListHandleInErrorHandlingTest` 和 `VMError::report_and_die` 作为检索签名，并用
`get_jbs_issue` 读取候选的描述、状态、resolution 和版本字段。该测试只验证关联能力；
最终是否匹配仍由技能按日志特征逐项判断。
