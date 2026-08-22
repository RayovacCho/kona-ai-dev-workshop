#!/usr/bin/env python3
"""Dependency-free MCP stdio server for HotSpot crash analysis."""

from __future__ import annotations

import json
import sys
import traceback
from typing import Any

from analyzer import AnalysisError, analyze_file, get_jbs_issue, parse_log_file, parse_log_text, search_jbs

SERVER_INFO = {"name": "hotspot-crash-analyzer", "version": "1.0.0"}

TOOLS = [
    {
        "name": "parse_hotspot_error_log",
        "description": "Parse a HotSpot hs_err_pid log from a local path or supplied text into structured crash evidence.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Local path to hs_err_pid*.log"},
                "content": {"type": "string", "description": "Log text when no local path is available"},
            },
            "oneOf": [{"required": ["path"]}, {"required": ["content"]}],
            "additionalProperties": False,
        },
    },
    {
        "name": "search_jbs",
        "description": "Search public OpenJDK JBS for HotSpot issue candidates. Results require signature and version validation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Distinctive assertion, fatal message, or frame symbol"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_jbs_issue",
        "description": "Fetch one public JBS issue's description and version metadata for comparison with a crash fingerprint.",
        "inputSchema": {
            "type": "object",
            "properties": {"key": {"type": "string", "pattern": "^JDK-[0-9]+$"}},
            "required": ["key"],
            "additionalProperties": False,
        },
    },
    {
        "name": "analyze_hotspot_crash",
        "description": "Parse a local hs_err log, identify its direct cause, optionally query JBS, and return prioritized advice.",
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


def _tool_result(data: Any, is_error: bool = False) -> dict[str, Any]:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    result: dict[str, Any] = {"content": [{"type": "text", "text": text}], "isError": is_error}
    if not is_error and isinstance(data, dict):
        result["structuredContent"] = data
    return result


def _call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "parse_hotspot_error_log":
        if bool(arguments.get("path")) == bool(arguments.get("content")):
            raise AnalysisError("provide exactly one of path or content")
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
    raise AnalysisError(f"unknown tool: {name}")


def handle(message: dict[str, Any]) -> dict[str, Any] | None:
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
                "instructions": "Parse hs_err evidence first. Treat JBS search hits as unverified candidates.",
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
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main() -> int:
    for raw in sys.stdin:
        try:
            message = json.loads(raw)
            response = handle(message)
            if response is not None:
                print(json.dumps(response, ensure_ascii=False), flush=True)
        except Exception as exc:  # Keep protocol diagnostics off stdout.
            print(f"hotspot-crash-analyzer: {exc}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
