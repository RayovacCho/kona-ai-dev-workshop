#!/usr/bin/env python3
"""验证提交的受控崩溃原始日志及其校验和。"""

import hashlib
import re
import sys
from pathlib import Path
from typing import Dict, Mapping, Optional


ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "apps" / "controlled-crash" / "crash-logs"
ANALYZER_DIR = ROOT / "mcp" / "hotspot-crash-analyzer"
sys.path.insert(0, str(ANALYZER_DIR))

from analyzer import parse_log_text  # noqa: E402


EXPECTED_LOGS: Mapping[str, Dict[str, object]] = {
    "hs_err_pid16569.log": {"case": 1, "kind": "assertion", "message": "test assert"},
    "hs_err_pid16574.log": {"case": 2, "kind": "guarantee", "message": "test guarantee"},
    "hs_err_pid16579.log": {"case": 14, "kind": "signal", "signal": "SIGSEGV"},
    "hs_err_pid16584.log": {"case": 15, "kind": "signal", "signal": "SIGFPE"},
    "hs_err_pid16589.log": {"case": 16, "kind": "fatal", "message": "active ThreadsListHandle"},
    "hs_err_pid16594.log": {"case": 17, "kind": "fatal", "message": "nested ThreadsListHandle"},
    "hs_err_pid16599.log": {"case": 99, "kind": "fatal", "message": "Crashing with number 99"},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_manifest(path: Path) -> Dict[str, str]:
    entries: Dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            raise SystemExit(f"崩溃日志校验和行格式无效：{line!r}")
        digest, name = parts
        name = name.lstrip("*")
        if Path(name).name != name:
            raise SystemExit(f"崩溃日志校验和包含非法路径：{name}")
        if name in entries:
            raise SystemExit(f"崩溃日志校验和包含重复文件：{name}")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
            raise SystemExit(f"崩溃日志校验和格式无效：{name}")
        entries[name] = digest.lower()
    return entries


def check_manifest(
    log_dir: Path = LOG_DIR,
    expected_logs: Mapping[str, Dict[str, object]] = EXPECTED_LOGS,
) -> None:
    manifest_path = log_dir / "SHA256SUMS"
    if not manifest_path.is_file():
        raise SystemExit(f"缺少崩溃日志校验和清单：{manifest_path}")
    manifest = read_manifest(manifest_path)
    expected_names = set(expected_logs)
    if set(manifest) != expected_names:
        raise SystemExit(
            "崩溃日志校验和文件集合不符合预期；"
            f"实际 {sorted(manifest)}，期望 {sorted(expected_names)}"
        )
    for name, expected_digest in manifest.items():
        path = log_dir / name
        if not path.is_file():
            raise SystemExit(f"缺少完整崩溃日志：{path}")
        if sha256(path) != expected_digest:
            raise SystemExit(f"崩溃日志校验和不匹配：{path}")


def check_log(path: Path, expected: Mapping[str, object]) -> None:
    raw = path.read_bytes()
    if len(raw) < 50_000:
        raise SystemExit(f"崩溃日志疑似被裁剪：{path}（仅 {len(raw)} 字节）")
    text = raw.decode("utf-8", errors="replace")
    if not text.rstrip().endswith("END."):
        raise SystemExit(f"崩溃日志缺少完整结束标记：{path}")
    for heading in ("VM Arguments:", "Environment Variables:"):
        if heading not in text:
            raise SystemExit(f"崩溃日志缺少诊断章节 {heading}：{path}")

    result = parse_log_text(text, str(path))
    error = result["error"]
    if not result["controlled_crash"]:
        raise SystemExit(f"日志不包含受控崩溃调用链：{path}")
    if error["kind"] != expected["kind"]:
        raise SystemExit(
            f"日志错误类型不符：{path}；实际 {error['kind']}，期望 {expected['kind']}"
        )
    if expected.get("signal") != error.get("signal"):
        raise SystemExit(
            f"日志信号不符：{path}；实际 {error.get('signal')}，期望 {expected.get('signal')}"
        )
    expected_message: Optional[str] = expected.get("message")  # type: ignore[assignment]
    if expected_message and expected_message not in (error.get("message") or ""):
        raise SystemExit(f"日志错误消息不符：{path}")
    command_line = result.get("command_line") or ""
    case = expected["case"]
    if not re.search(rf"workshop\.crash\.ControlledCrash\s+{case}(?:\s|$)", command_line):
        raise SystemExit(f"日志命令行与用例 {case} 不匹配：{path}")


def main() -> None:
    check_manifest()
    for name, expected in EXPECTED_LOGS.items():
        check_log(LOG_DIR / name, expected)
    print(f"崩溃日志证据：{len(EXPECTED_LOGS)} 份检查通过")


if __name__ == "__main__":
    main()
