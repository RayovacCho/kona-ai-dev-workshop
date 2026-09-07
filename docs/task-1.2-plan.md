# 任务 1.2 规划：利用 AI 分析 JVM 崩溃

## 目标与验收条件

1. 提供可被智能体发现的 `hotspot-crash-analysis` Skill，明确证据优先级、JBS 关联标准和
   输出格式。
2. 提供零第三方运行时依赖的 stdio MCP server，至少暴露日志解析、直接原因分析、JBS
   搜索和 JBS 问题详情四类能力。
3. 能从 HotSpot Error Log 中提取致命错误头、错误消息、Problematic frame、VM/Java 栈、
   JVM 版本、命令行和 VM 状态，并标明日志是否完整。
4. 对直接原因给出证据、置信度和“是否为人工注入”的判断；受控崩溃不得误报为产品缺陷。
5. JBS 搜索结果只作为候选。只有错误指纹、版本、平台和触发条件相符时，才能报告为可信
   匹配；断网时返回可手工访问的查询 URL。
6. 自动化测试覆盖受控和非受控崩溃、不同错误类型、协议调用、非法输入以及 JBS 响应解析。

## 组件边界

```text
用户 / Agent
  -> Skill：规定分析顺序、判断标准和报告结构
  -> MCP server：提供确定性解析和 JBS 查询工具
       -> analyzer.py：解析 hs_err、生成直接原因和搜索指纹
       -> bugs.openjdk.org：公开 JBS REST API（可选网络步骤）
```

Skill 不复制解析器实现；MCP 也不替代智能体对候选问题的证据核验。离线解析必须可用，
联网失败不能影响直接原因分析。

## 实施步骤

1. 用任务 1.1 的真实日志定义字段模型和受控崩溃识别规则。
2. 实现 `parse_hotspot_error_log` 和 `analyze_hotspot_crash`，再补充 `search_jbs` 与
   `get_jbs_issue`。
3. 在 Skill 中规定“日志证据 → 直接原因 → JBS 候选 → 解决建议”的顺序，并将详细的
   JBS 匹配准则放入按需读取的 reference。
4. 使用合成的最小 fixture 测边界情况，使用任务 1.1 的七份完整日志做交付验收。
5. 在报告中保存实际输入、结构化输出、JBS 判定和适用限制。

## 安全与质量约束

- 单份日志限制为 10 MiB，拒绝不存在或并非普通文件的路径。
- 报告引用命令行和环境变量时隐去凭据；提交真实日志前运行敏感字段检查。
- SIGSEGV、SIGFPE 或 libc 顶帧本身不是可用于匹配 JBS 的唯一指纹。
- `VMError::controlled_crash`、WhiteBox 调用链和 `-XX:+WhiteBoxAPI` 是人工注入的强证据。
- MCP 的本地路径参数具有读取调用进程可访问文件的能力，只应连接到可信客户端。

## 验证命令

```bash
make test-mcp
make check-crash-logs
make check
```

完整结论和七类样本分析见
[任务 1.2 报告](reports/task-1.2-ai-crash-analysis.md)。
