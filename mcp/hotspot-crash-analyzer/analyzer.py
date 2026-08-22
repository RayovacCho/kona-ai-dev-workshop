#!/usr/bin/env python3
"""以确定性方式解析 HotSpot 错误日志并查询公开 JBS。"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

MAX_LOG_BYTES = 10 * 1024 * 1024
JBS_BASE = "https://bugs.openjdk.org"


class AnalysisError(ValueError):
    pass


def _first(pattern: str, text: str, flags: int = re.MULTILINE) -> str | None:
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else None


def _section(text: str, start: str) -> str:
    begin = text.find(start)
    return "" if begin < 0 else text[begin + len(start) :]


def _frames(text: str, heading: str, limit: int = 20) -> list[str]:
    result: list[str] = []
    for line in _section(text, heading).splitlines():
        value = line.strip()
        if not value and result:
            break
        if re.match(r"^(?:[VvCJj]\s|v\s|\[|0x)", value):
            result.append(value)
        if len(result) >= limit:
            break
    return result


def _problematic_frame(text: str) -> dict[str, str] | None:
    raw = _first(r"^# Problematic frame:\s*\n#\s*(.+)$", text)
    if not raw:
        return None
    match = re.match(
        r"(?P<kind>[VvCJj])\s+\[(?P<library>[^+\]]+)(?:\+(?P<offset>0x[0-9a-fA-F]+))?\]\s*(?P<symbol>.*)",
        raw,
    )
    result = {"raw": raw}
    if match:
        result.update({key: value for key, value in match.groupdict().items() if value})
    return result


def _error_details(text: str) -> dict[str, Any]:
    signal_match = re.search(
        r"^#\s+(SIG[A-Z0-9]+|EXCEPTION_[A-Z_]+)\s+\(([^)]+)\) at pc=([^,]+), pid=(\d+), tid=(\d+)",
        text,
        re.MULTILINE,
    )
    internal_match = re.search(
        r"^#\s+Internal Error \((.+):(\d+)\), pid=(\d+), tid=(\d+)", text, re.MULTILINE
    )
    message_match = re.search(
        r"^#\s+((?:assert|guarantee)\(.+|fatal error:.+|Out of Memory Error \(.+)\s*$",
        text,
        re.MULTILINE,
    )
    message = message_match.group(1).strip() if message_match else None

    if signal_match:
        return {
            "kind": "signal",
            "signal": signal_match.group(1),
            "signal_code": signal_match.group(2),
            "pc": signal_match.group(3),
            "pid": int(signal_match.group(4)),
            "tid": int(signal_match.group(5)),
            "message": message,
        }
    if internal_match:
        kind = "internal_error"
        if message and message.startswith("assert("):
            kind = "assertion"
        elif message and message.startswith("guarantee("):
            kind = "guarantee"
        elif message and message.startswith("fatal error:"):
            kind = "fatal"
        return {
            "kind": kind,
            "message": message,
            "source_file": internal_match.group(1),
            "source_line": int(internal_match.group(2)),
            "pid": int(internal_match.group(3)),
            "tid": int(internal_match.group(4)),
        }
    if "A fatal error has been detected by the Java Runtime Environment" not in text:
        raise AnalysisError("文件看起来不像 HotSpot 致命错误日志")
    return {"kind": "unknown", "message": message}


def _advice(error: dict[str, Any], frame: dict[str, str] | None) -> list[str]:
    advice = ["在同一 JDK 系列最新的受支持更新版上复现，并保留完整的 hs_err 日志。"]
    frame_kind = frame.get("kind") if frame else None
    if error["kind"] == "signal" and frame_kind == "C":
        advice.append("对原生栈帧进行符号化，并优先检查 JNI/JVMTI 代理和原生库版本。")
    elif error["kind"] in {"assertion", "guarantee", "fatal", "internal_error"}:
        advice.append("将准确的消息、源码位置和顶部 VM 栈帧与 JBS 比对；调试断言可能无法在发布版构建中复现。")
    else:
        advice.append("如果故障可以复现，请收集 core/minidump 和符号化原生堆栈。")
    advice.append("根据受影响/修复版本、平台、触发条件和堆栈特征核验每个 JBS 候选项。")
    return advice


def _direct_cause(error: dict[str, Any], frame: dict[str, str] | None, controlled: bool) -> dict[str, Any]:
    evidence: list[str] = []
    if error.get("message"):
        evidence.append(error["message"])
    if error.get("signal"):
        evidence.append(f"{error['signal']} ({error.get('signal_code', 'unknown code')})")
    if frame:
        evidence.append(frame["raw"])

    if controlled:
        summary = (
            f"有意触发的 WhiteBox 受控崩溃引发了 {error['signal']}"
            if error["kind"] == "signal"
            else f"有意触发的 WhiteBox 受控崩溃触发了 HotSpot {error['kind']} 错误"
        )
        return {
            "summary": summary,
            "confidence": "high",
            "intentional": True,
            "evidence": evidence,
            "advice": [
                "无需修复 JVM 产品：此日志记录的是有意注入的测试崩溃。",
                "WhiteBoxAPI 和 controlledCrash 只能用于隔离的 fastdebug 测试进程。",
                "如果生产环境发生意外崩溃，应分析相应的生产 hs_err 日志，而不是此测试样本。",
            ],
        }

    if error["kind"] == "signal":
        symbol = frame.get("symbol") if frame else None
        summary = f"原生代码在 {symbol or '未解析的原生栈帧'} 中触发 {error['signal']}"
    elif error.get("message"):
        summary = error["message"]
    else:
        summary = "HotSpot 致命错误；解析出的错误头中没有直接触发原因"
    return {
        "summary": summary,
        "confidence": "medium" if error["kind"] == "unknown" else "high",
        "intentional": False,
        "evidence": evidence,
        "advice": _advice(error, frame),
    }


def _search_terms(error: dict[str, Any], frame: dict[str, str] | None) -> list[str]:
    terms: list[str] = []
    message = error.get("message") or ""
    if message:
        cleaned = re.sub(r"^fatal error:\s*", "", message)
        cleaned = re.sub(r"0x[0-9a-fA-F]+|\b\d{4,}\b", "", cleaned)
        terms.append(cleaned[:160].strip())
    if frame and frame.get("symbol"):
        symbol = re.sub(r"\+0x[0-9a-fA-F]+$", "", frame["symbol"])
        terms.append(symbol[:160].strip())
    if error.get("source_file"):
        terms.append(Path(error["source_file"]).name)
    if error.get("signal") and not terms:
        terms.append(error["signal"])
    return list(dict.fromkeys(term for term in terms if len(term) >= 3))[:3]


def parse_log_text(text: str, source: str = "<content>") -> dict[str, Any]:
    error = _error_details(text)
    frame = _problematic_frame(text)
    controlled = (
        "VMError::controlled_crash" in text
        or "WhiteBox.controlledCrash" in text
        or ("-XX:+WhiteBoxAPI" in text and "workshop.crash.ControlledCrash" in text)
    )
    terms = _search_terms(error, frame)
    return {
        "schema_version": 1,
        "source": source,
        "error": error,
        "direct_cause": _direct_cause(error, frame, controlled),
        "problematic_frame": frame,
        "jre_version": _first(r"^# JRE version:\s*(.+)$", text),
        "vm_version": _first(r"^# Java VM:\s*(.+)$", text),
        "command_line": _first(r"^Command Line:\s*(.+)$", text),
        "host": _first(r"^Host:\s*(.+)$", text),
        "time": _first(r"^Time:\s*(.+)$", text),
        "current_thread": _first(r"^Current thread \([^)]*\):\s*(.+)$", text),
        "vm_state": _first(r"^VM state:\s*(.+)$", text),
        "native_frames": _frames(text, "Native frames:", 20),
        "java_frames": _frames(text, "Java frames:", 20),
        "controlled_crash": controlled,
        "jbs_search_terms": terms,
        "jbs_search_url": build_jbs_browse_url(terms[0]) if terms else None,
    }


def parse_log_file(path: str) -> dict[str, Any]:
    log_path = Path(path).expanduser()
    if not log_path.is_file():
        raise AnalysisError(f"日志文件不存在或不是常规文件：{log_path}")
    size = log_path.stat().st_size
    if size > MAX_LOG_BYTES:
        raise AnalysisError(f"日志大小为 {size} 字节；最大允许 {MAX_LOG_BYTES} 字节")
    return parse_log_text(log_path.read_text(encoding="utf-8", errors="replace"), str(log_path.resolve()))


def _escape_jql(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def build_jql(query: str) -> str:
    query = " ".join(query.split())[:200]
    if len(query) < 3:
        raise AnalysisError("JBS 查询必须包含至少 3 个非空白字符")
    # JBS 默认优先显示文本最接近的结果。按更新时间排序会让宽泛的崩溃词汇
    # 淹没具有辨识度的特征。
    return f'project = JDK AND component = hotspot AND text ~ "{_escape_jql(query)}"'


def build_jbs_browse_url(query: str) -> str:
    return f"{JBS_BASE}/issues/?jql={urllib.parse.quote(build_jql(query))}"


def search_jbs(query: str, max_results: int = 5, timeout_seconds: float = 12.0) -> dict[str, Any]:
    max_results = max(1, min(int(max_results), 20))
    jql = build_jql(query)
    params = urllib.parse.urlencode(
        {
            "jql": jql,
            "maxResults": max_results,
            "fields": "key,summary,status,resolution,fixVersions,versions,components,updated",
        }
    )
    url = f"{JBS_BASE}/rest/api/2/search?{params}"
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "kona-hotspot-crash-analyzer/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise AnalysisError(f"JBS 查询失败：{exc}") from exc

    issues = []
    for item in payload.get("issues", []):
        fields = item.get("fields", {})
        issues.append(
            {
                "key": item.get("key"),
                "summary": fields.get("summary"),
                "status": (fields.get("status") or {}).get("name"),
                "resolution": (fields.get("resolution") or {}).get("name"),
                "affected_versions": [v.get("name") for v in fields.get("versions", [])],
                "fix_versions": [v.get("name") for v in fields.get("fixVersions", [])],
                "components": [v.get("name") for v in fields.get("components", [])],
                "updated": fields.get("updated"),
                "url": f"{JBS_BASE}/browse/{item.get('key')}",
                "match_status": "candidate_requires_validation",
            }
        )
    return {
        "query": query,
        "jql": jql,
        "browse_url": build_jbs_browse_url(query),
        "total": payload.get("total", len(issues)),
        "issues": issues,
        "warning": "关键词搜索结果只是候选项，并非确认匹配；请核验特征、触发条件、平台和版本。",
    }


def get_jbs_issue(key: str, timeout_seconds: float = 12.0) -> dict[str, Any]:
    key = key.strip().upper()
    if not re.fullmatch(r"JDK-\d+", key):
        raise AnalysisError("JBS 问题编号的格式必须类似 JDK-1234567")
    fields_arg = "summary,status,resolution,description,fixVersions,versions,components,labels,issuelinks,updated"
    url = f"{JBS_BASE}/rest/api/2/issue/{key}?{urllib.parse.urlencode({'fields': fields_arg})}"
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "kona-hotspot-crash-analyzer/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            item = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise AnalysisError(f"JBS 问题查询失败：{exc}") from exc
    fields = item.get("fields", {})
    links = []
    for link in fields.get("issuelinks", []):
        linked = link.get("outwardIssue") or link.get("inwardIssue") or {}
        if linked:
            links.append({"key": linked.get("key"), "summary": (linked.get("fields") or {}).get("summary")})
    description = fields.get("description")
    if isinstance(description, str):
        description = description[:16000]
    return {
        "key": key,
        "summary": fields.get("summary"),
        "status": (fields.get("status") or {}).get("name"),
        "resolution": (fields.get("resolution") or {}).get("name"),
        "description": description,
        "affected_versions": [v.get("name") for v in fields.get("versions", [])],
        "fix_versions": [v.get("name") for v in fields.get("fixVersions", [])],
        "components": [v.get("name") for v in fields.get("components", [])],
        "labels": fields.get("labels", []),
        "linked_issues": links,
        "updated": fields.get("updated"),
        "url": f"{JBS_BASE}/browse/{key}",
        "match_status": "candidate_requires_log_comparison",
    }


def analyze_file(path: str, include_jbs: bool = True, max_results: int = 5) -> dict[str, Any]:
    result = parse_log_file(path)
    if result["controlled_crash"]:
        result["jbs"] = {
            "searched": False,
            "reason": "这是有意触发 VMError::controlled_crash 的测试样本；通用崩溃搜索结果会造成误报。",
            "issues": [],
            "browse_url": result["jbs_search_url"],
        }
    elif include_jbs and result["jbs_search_terms"]:
        try:
            result["jbs"] = {"searched": True, **search_jbs(result["jbs_search_terms"][0], max_results)}
        except AnalysisError as exc:
            result["jbs"] = {"searched": False, "error": str(exc), "issues": [], "browse_url": result["jbs_search_url"]}
    else:
        result["jbs"] = {"searched": False, "issues": [], "browse_url": result["jbs_search_url"]}
    return result
