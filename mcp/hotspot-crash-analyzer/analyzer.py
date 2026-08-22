#!/usr/bin/env python3
"""Deterministic HotSpot error-log parsing and public JBS lookup."""

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
        raise AnalysisError("file does not look like a HotSpot fatal error log")
    return {"kind": "unknown", "message": message}


def _advice(error: dict[str, Any], frame: dict[str, str] | None) -> list[str]:
    advice = ["Reproduce on the latest supported update of the same JDK line and preserve the complete hs_err log."]
    frame_kind = frame.get("kind") if frame else None
    if error["kind"] == "signal" and frame_kind == "C":
        advice.append("Symbolize the native frame and check JNI/JVMTI agents and native-library versions first.")
    elif error["kind"] in {"assertion", "guarantee", "fatal", "internal_error"}:
        advice.append("Match the exact message, source location, and top VM frames against JBS; debug assertions may not reproduce in release builds.")
    else:
        advice.append("Collect a core/minidump and symbolized native stack if the failure is reproducible.")
    advice.append("Validate any JBS candidate against affected/fixed versions, platform, trigger, and stack signature.")
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
            f"Intentional WhiteBox controlled crash raised {error['signal']}"
            if error["kind"] == "signal"
            else f"Intentional WhiteBox controlled crash triggered a HotSpot {error['kind']}"
        )
        return {
            "summary": summary,
            "confidence": "high",
            "intentional": True,
            "evidence": evidence,
            "advice": [
                "No JVM product fix is indicated: this log records a deliberately injected test crash.",
                "Keep WhiteBoxAPI and controlledCrash restricted to isolated fastdebug test processes.",
                "For an unexpected production crash, analyze that production hs_err log instead of this fixture.",
            ],
        }

    if error["kind"] == "signal":
        symbol = frame.get("symbol") if frame else None
        summary = f"Native {error['signal']} in {symbol or 'an unresolved native frame'}"
    elif error.get("message"):
        summary = error["message"]
    else:
        summary = "HotSpot fatal error; the direct trigger is not present in the parsed header"
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
        raise AnalysisError(f"log file does not exist or is not a regular file: {log_path}")
    size = log_path.stat().st_size
    if size > MAX_LOG_BYTES:
        raise AnalysisError(f"log is {size} bytes; maximum is {MAX_LOG_BYTES}")
    return parse_log_text(log_path.read_text(encoding="utf-8", errors="replace"), str(log_path.resolve()))


def _escape_jql(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def build_jql(query: str) -> str:
    query = " ".join(query.split())[:200]
    if len(query) < 3:
        raise AnalysisError("JBS query must contain at least 3 non-whitespace characters")
    # JBS's default ordering puts the closest text matches first. Sorting by update
    # time makes broad crash vocabulary drown the distinctive signature.
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
        raise AnalysisError(f"JBS lookup failed: {exc}") from exc

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
        "warning": "Keyword results are candidates, not confirmed matches; validate signature, trigger, platform, and versions.",
    }


def get_jbs_issue(key: str, timeout_seconds: float = 12.0) -> dict[str, Any]:
    key = key.strip().upper()
    if not re.fullmatch(r"JDK-\d+", key):
        raise AnalysisError("JBS issue key must look like JDK-1234567")
    fields_arg = "summary,status,resolution,description,fixVersions,versions,components,labels,issuelinks,updated"
    url = f"{JBS_BASE}/rest/api/2/issue/{key}?{urllib.parse.urlencode({'fields': fields_arg})}"
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "kona-hotspot-crash-analyzer/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            item = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise AnalysisError(f"JBS issue lookup failed: {exc}") from exc
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
            "reason": "Intentional VMError::controlled_crash fixture; generic crash hits would be false positives.",
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
