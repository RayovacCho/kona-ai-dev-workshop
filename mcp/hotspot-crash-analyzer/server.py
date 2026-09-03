#!/usr/bin/env python3
"""用于 HotSpot 崩溃分析的零依赖 stdio MCP 服务器。"""

import json
import sys
import traceback
from typing import Any, Dict, Optional

from analyzer import AnalysisError, analyze_file, get_jbs_issue, parse_log_file, parse_log_text, search_jbs

SERVER_INFO = {"name": "hotspot-crash-analyzer", "version": "1.0.0"}

TOOLS = [
    {
        "name": "parse_hotspot_error_log",
        "description": "从本地路径或提供的文本解析 HotSpot hs_err_pid 日志，生成结构化崩溃证据。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "hs_err_pid*.log 的本地路径"},
                "content": {"type": "string", "description": "没有本地路径时提供的日志文本"},
            },
            "oneOf": [{"required": ["path"]}, {"required": ["content"]}],
            "additionalProperties": False,
        },
    },
    {
        "name": "search_jbs",
        "description": "在公开的 OpenJDK JBS 中搜索 HotSpot 问题候选项。结果需要核验特征和版本。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "具有辨识度的断言、致命错误消息或栈帧符号"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_jbs_issue",
        "description": "获取一项公开 JBS 问题的描述和版本元数据，用于与崩溃指纹比较。",
        "inputSchema": {
            "type": "object",
            "properties": {"key": {"type": "string", "pattern": "^JDK-[0-9]+$"}},
            "required": ["key"],
            "additionalProperties": False,
        },
    },
    {
        "name": "analyze_hotspot_crash",
        "description": "解析本地 hs_err 日志，识别直接原因，按需查询 JBS，并返回按优先级排列的建议。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "include_jbs": {"type": "boolean", "default": True},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
]


def _tool_result(data: Any, is_error: bool = False) -> Dict[str, Any]:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    result = {"content": [{"type": "text", "text": text}], "isError": is_error}  # type: Dict[str, Any]
    if not is_error and isinstance(data, dict):
        result["structuredContent"] = data
    return result


def _call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if name == "parse_hotspot_error_log":
        if bool(arguments.get("path")) == bool(arguments.get("content")):
            raise AnalysisError("path 和 content 必须且只能提供一个")
        return parse_log_file(arguments["path"]) if arguments.get("path") else parse_log_text(arguments["content"])
    if name == "search_jbs":
        return search_jbs(arguments.get("query", ""), arguments.get("max_results", 5))
    if name == "get_jbs_issue":
        return get_jbs_issue(arguments.get("key", ""))
    if name == "analyze_hotspot_crash":
        return analyze_file(
            arguments.get("path", ""),
            arguments.get("include_jbs", True),
            arguments.get("max_results", 5),
        )
    raise AnalysisError(f"未知工具：{name}")


def handle(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    method = message.get("method")
    request_id = message.get("id")
    if request_id is None:
        return None
    if method == "initialize":
        requested = (message.get("params") or {}).get("protocolVersion", "2025-03-26")
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": requested,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
                "instructions": "先解析 hs_err 证据。将 JBS 搜索结果视为尚未核验的候选项。",
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = message.get("params") or {}
        try:
            data = _call_tool(params.get("name", ""), params.get("arguments") or {})
            result = _tool_result(data)
        except (AnalysisError, OSError, TypeError, ValueError) as exc:
            result = _tool_result({"error": str(exc)}, is_error=True)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"未找到方法：{method}"},
    }


def main() -> int:
    for raw in sys.stdin:
        try:
            message = json.loads(raw)
            response = handle(message)
            if response is not None:
                print(json.dumps(response, ensure_ascii=False), flush=True)
        except Exception as exc:  # 协议诊断信息不能写入 stdout。
            print(f"hotspot-crash-analyzer: {exc}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
