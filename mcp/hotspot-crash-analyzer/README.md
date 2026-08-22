# HotSpot Crash Analyzer MCP

零第三方依赖的 stdio MCP server，提供四个工具：

- `parse_hotspot_error_log`：把路径或日志文本解析为结构化证据；
- `search_jbs`：调用 JBS 公开只读 REST API，返回待核验候选；
- `get_jbs_issue`：读取候选的描述、版本、状态和关联 issue，供 Skill 逐项比对；
- `analyze_hotspot_crash`：完成解析、直接原因判断、可选 JBS 查询和建议。

`analyze_hotspot_crash` 遇到 1.1 的 `VMError::controlled_crash` 测试日志时会主动跳过
JBS 关键词查询，防止把普通 SIGSEGV/SIGFPE issue 误认为本次受控崩溃的根因。

## 配置

在支持 stdio MCP 的客户端中加入（按本机路径调整）：

```json
{
  "mcpServers": {
    "hotspot-crash-analyzer": {
      "command": "python3",
      "args": [
        "/Users/rayovac9/kona-ai-dev-workshop/mcp/hotspot-crash-analyzer/server.py"
      ]
    }
  }
}
```

服务 stdout 只输出一行一个 JSON-RPC 消息，诊断信息写 stderr。JBS 不可访问时，分析
结果仍会返回解析结论和可手工打开的 `browse_url`。

## 验证

```bash
cd /Users/rayovac9/kona-ai-dev-workshop/mcp/hotspot-crash-analyzer
python3 -m unittest discover -s tests -v
```
