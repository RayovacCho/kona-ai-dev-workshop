# 任务 1.2 报告：利用 AI 分析 JVM 崩溃

## 交付物

- 智能体技能：`skills/hotspot-crash-analysis/`
- MCP 服务器：`mcp/hotspot-crash-analyzer/`
- 测试样本：1.1 产生并提交的七份完整 `apps/controlled-crash/crash-logs/hs_err_pid*.log`

技能规定证据优先级和 JBS 关联标准；MCP 负责可重复的日志解析、直接原因初判、JBS
公开 REST API 查询以及建议生成。二者明确区分“搜索候选”和“确认匹配”，避免仅凭
SIGSEGV 等宽泛关键词错误关联。

## GPT-5.6 实验过程（输入与输出）

### 1. 实验输入

2026-08-30 在仓库根目录使用 GPT-5.6 检查并分析本地完整日志。给 GPT-5.6 的任务要求为：

```text
分析 apps/controlled-crash/crash-logs/hs_err_pid*.log。每种 controlledCrash 类型选择一份
日志，提取错误类型、错误消息或信号、Problematic frame 和受控崩溃调用链；判断直接原因、
是否为人为注入以及结论置信度。不要仅根据 SIGSEGV/SIGFPE 关联 JBS；最后把实际输入、
输出和分析结论写入 docs/reports/task-1.2-ai-crash-analysis.md。
```

日志目录本地共有 21 份完整日志，即 7 个用例的三轮运行。本次选择并提交第一轮连续生成的
7 份日志作为输入，分别对应编号 1、2、14、15、16、17 和 99；其余 14 份重复运行日志不提交：

```text
apps/controlled-crash/crash-logs/hs_err_pid16569.log
apps/controlled-crash/crash-logs/hs_err_pid16574.log
apps/controlled-crash/crash-logs/hs_err_pid16579.log
apps/controlled-crash/crash-logs/hs_err_pid16584.log
apps/controlled-crash/crash-logs/hs_err_pid16589.log
apps/controlled-crash/crash-logs/hs_err_pid16594.log
apps/controlled-crash/crash-logs/hs_err_pid16599.log
```

GPT-5.6 先用以下命令查看每份日志的致命错误头。该步骤直接读取完整 `hs_err`，没有使用测试
fixture 或手工构造数据：

```bash
for f in apps/controlled-crash/crash-logs/hs_err_pid165{69,74,79,84,89,94,99}.log; do
  printf '\nFILE %s\n' "$f"
  rg -n -m1 \
    'assert\(|guarantee\(|SIGSEGV|SIGFPE|Force crash|Crashing with number' "$f"
done
```

输入日志的关键行输出如下：

```text
hs_err_pid16569.log:5: assert(how == 0) failed: test assert
hs_err_pid16574.log:5: guarantee(how == 0) failed: test guarantee
hs_err_pid16579.log:4: SIGSEGV (0xb) ... pid=16579
hs_err_pid16584.log:4: SIGFPE (0x8) ... pid=16584
hs_err_pid16589.log:5: fatal error: Force crash with an active ThreadsListHandle.
hs_err_pid16594.log:5: fatal error: Force crash with a nested ThreadsListHandle.
hs_err_pid16599.log:5: fatal error: Crashing with number 99
```

### 2. GPT-5.6 分析方法

GPT-5.6 调用仓库内 `mcp/hotspot-crash-analyzer/analyzer.py` 的 `parse_log_file` 逐份解析完整
日志，并同时检查原始文本中的 `WhiteBox.controlledCrash`、`WB_ControlledCrash`、
`VMError::controlled_crash` 和 `-XX:+WhiteBoxAPI`。解析器负责确定性提取，GPT-5.6 负责把
结构化证据与实验触发方式结合起来作最终判断。可用下面的最小 Python 调用复现单份输入：

```python
from analyzer import parse_log_file

result = parse_log_file(
    "../../apps/controlled-crash/crash-logs/hs_err_pid16579.log"
)
print(result["error"])
print(result["problematic_frame"])
print(result["controlled_crash"])
print(result["direct_cause"])
```

判断顺序为：致命错误头决定原始错误类型；`Problematic frame` 和 VM/Java 栈确定发生位置；
WhiteBox 调用链与 JVM 参数确定是否为受控注入；只有排除受控测试后，才把 JBS 搜索结果
作为可能的产品缺陷候选。

### 3. 实际输出

GPT-5.6 得到的结构化摘要如下。地址等与进程相关的字段已省略，但错误类型、消息、问题帧和
判断结果均保持原始输出内容：

```json
[
  {"file":"hs_err_pid16569.log","kind":"assertion","message":"assert(how == 0) failed: test assert","controlled_crash":true,"cause":"有意触发的 WhiteBox 受控崩溃触发了 HotSpot assertion 错误","confidence":"high","intentional":true},
  {"file":"hs_err_pid16574.log","kind":"guarantee","message":"guarantee(how == 0) failed: test guarantee","controlled_crash":true,"cause":"有意触发的 WhiteBox 受控崩溃触发了 HotSpot guarantee 错误","confidence":"high","intentional":true},
  {"file":"hs_err_pid16579.log","kind":"signal","signal":"SIGSEGV","problematic_frame":"V [libjvm.dylib+0x14b4304] VMError::controlled_crash(int)+0x58","controlled_crash":true,"cause":"有意触发的 WhiteBox 受控崩溃引发了 SIGSEGV","confidence":"high","intentional":true},
  {"file":"hs_err_pid16584.log","kind":"signal","signal":"SIGFPE","problematic_frame":"C [libsystem_kernel.dylib+0x95e8] __pthread_kill+0x8","controlled_crash":true,"cause":"有意触发的 WhiteBox 受控崩溃引发了 SIGFPE","confidence":"high","intentional":true},
  {"file":"hs_err_pid16589.log","kind":"fatal","message":"fatal error: Force crash with an active ThreadsListHandle.","controlled_crash":true,"cause":"有意触发的 WhiteBox 受控崩溃触发了 HotSpot fatal 错误","confidence":"high","intentional":true},
  {"file":"hs_err_pid16594.log","kind":"fatal","message":"fatal error: Force crash with a nested ThreadsListHandle.","controlled_crash":true,"cause":"有意触发的 WhiteBox 受控崩溃触发了 HotSpot fatal 错误","confidence":"high","intentional":true},
  {"file":"hs_err_pid16599.log","kind":"fatal","message":"fatal error: Crashing with number 99","controlled_crash":true,"cause":"有意触发的 WhiteBox 受控崩溃触发了 HotSpot fatal 错误","confidence":"high","intentional":true}
]
```

### 4. GPT-5.6 输出结论

GPT-5.6 的最终判读是：7 份日志分别记录预期的 assertion、guarantee、SIGSEGV、SIGFPE 和
三种 fatal 分支；它们都包含受控崩溃证据，且均来自启用了 WhiteBoxAPI 的隔离测试进程。
因此 `intentional=true`、置信度为 `high`，不应把这些日志报告为 Kona/OpenJDK 的未知产品
缺陷。编号 14 的 `VMError::controlled_crash` 问题帧是最直接的证据；编号 15 在 macOS 上
显示 `__pthread_kill`，但致命错误头和调用链仍表明原始事件是测试主动触发的 SIGFPE。

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

所有样本的共同调用链都包含 `WhiteBox.controlledCrash` 和 `WB_ControlledCrash`，且命令行
启用了 `-XX:+WhiteBoxAPI`；除编号 16 外还直接打印了 `VMError::controlled_crash` 帧。编号
16 在活动 `ThreadsListHandle` 分支的日志从 `WB_ControlledCrash` 开始打印原生帧，但错误消息
与 Java/VM 调用链仍完整标识了受控入口。因此高置信度结论是：这些崩溃均为 1.1 有意注入，
不是 Kona/OpenJDK 的未知缺陷。MCP 对这类日志返回空的 JBS 问题列表并说明跳过原因；若强制
用宽泛关键词查询，得到的问题只能算无关候选。

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
