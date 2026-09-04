# HotSpot 崩溃分析器 MCP

零第三方依赖的 stdio MCP 服务器，提供四个工具：

- `parse_hotspot_error_log`：把路径或日志文本解析为结构化证据；
- `search_jbs`：调用 JBS 公开只读 REST API，返回待核验候选；
- `get_jbs_issue`：读取候选的描述、版本、状态和关联问题，供技能逐项比对；
- `analyze_hotspot_crash`：完成解析、直接原因判断、可选 JBS 查询和建议。

`analyze_hotspot_crash` 遇到 1.1 的 `VMError::controlled_crash` 测试日志时会主动跳过
JBS 关键词查询，防止把普通 SIGSEGV/SIGFPE 问题误认为本次受控崩溃的根因。
返回的 `browse_url` 仅搜索 `VMError::controlled_crash` 这一精确机制，
作为可选的历史背景，不会使用 `__pthread_kill` 等通用顶帧。

## 配置

运行时要求 **Python 3.9 或更高版本**，不需要第三方 Python 包。

在支持 stdio MCP 的客户端中加入（按本机路径调整）：

```json
{
  "mcpServers": {
    "hotspot-crash-analyzer": {
      "command": "python3",
      "args": [
        "/path/to/kona-ai-dev-workshop/mcp/hotspot-crash-analyzer/server.py"
      ]
    }
  }
}
```

服务 stdout 只输出一行一个 JSON-RPC 消息，诊断信息写 stderr。JBS 不可访问时，分析
结果仍会返回解析结论和可手工打开的 `browse_url`。路径输入和文本输入都限制为 10 MiB；
畸形 JSON-RPC 请求会收到明确的协议错误响应，不会让客户端无响应等待。服务明确协商
其支持的 MCP `2025-03-26` 协议版本，不会回显一个实际未实现的客户端版本。

## 验证

测试使用 `tests/fixtures/` 中随仓库提交的精简 `hs_err` 样本，不依赖
`apps/controlled-crash/crash-logs/` 中按导师要求提交的七份完整日志，也不依赖本机生成并被
忽略的重复日志。覆盖受控崩溃、非受控原生库 SIGSEGV、Windows access violation、OOM、
截断日志标记、JBS 搜索/详情响应解析和 MCP stdio 调用；JBS 响应使用确定性 mock，因此
CI 不依赖外部网络。

```bash
cd /path/to/kona-ai-dev-workshop/mcp/hotspot-crash-analyzer
python3 -m unittest discover -s tests -v
```

在仓库根目录也可执行 `make test-mcp`；如需指定解释器，使用
`make test-mcp PYTHON=/path/to/python3`。
