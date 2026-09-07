#!/usr/bin/env python3
"""比较 JMH 中成对的中文和英文载荷，输出中文 Markdown 摘要。"""

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


PAYLOAD_PAIRS = (
    ("SMALL", "SMALL_CHINESE", "小对象"),
    ("GRAPH", "GRAPH_CHINESE", "100 元素对象图"),
)
OPERATION_LABELS = {
    "serialize": "序列化",
    "deserialize": "反序列化",
    "roundTrip": "完整往返",
}
ROOT = Path(__file__).resolve().parent.parent


def _finite_number(value: Any, field: str) -> float:
    if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{field} 必须是大于零的有限数值")
    return float(value)


def load_results(path: Path) -> Dict[Tuple[str, str], Dict[str, float]]:
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 JMH JSON：{path}：{exc}") from exc
    if not isinstance(content, list):
        raise ValueError(f"JMH JSON 顶层必须是数组：{path}")

    results: Dict[Tuple[str, str], Dict[str, float]] = {}
    for entry in content:
        if not isinstance(entry, dict):
            raise ValueError(f"JMH 结果项必须是对象：{path}")
        operation = str(entry.get("benchmark", "")).rsplit(".", 1)[-1]
        payload = entry.get("params", {}).get("payloadType")
        if operation not in OPERATION_LABELS or not isinstance(payload, str):
            continue
        key = (operation, payload)
        if key in results:
            raise ValueError(f"JMH 结果包含重复场景：{operation}/{payload}")
        primary = entry.get("primaryMetric", {})
        allocation = entry.get("secondaryMetrics", {}).get("gc.alloc.rate.norm", {})
        if primary.get("scoreUnit") != "us/op" or allocation.get("scoreUnit") != "B/op":
            raise ValueError(f"JMH 指标单位不符合预期：{operation}/{payload}")
        results[key] = {
            "time": _finite_number(primary.get("score"), "耗时"),
            "allocation": _finite_number(allocation.get("score"), "分配量"),
        }
    return results


def comparisons(
    results: Dict[Tuple[str, str], Dict[str, float]]
) -> Iterable[Dict[str, Any]]:
    for english, chinese, payload_label in PAYLOAD_PAIRS:
        for operation, operation_label in OPERATION_LABELS.items():
            english_key = (operation, english)
            chinese_key = (operation, chinese)
            if english_key not in results or chinese_key not in results:
                raise ValueError(
                    f"缺少中文对照场景：{operation}/{english} 或 {operation}/{chinese}"
                )
            english_metrics = results[english_key]
            chinese_metrics = results[chinese_key]
            yield {
                "payload": payload_label,
                "operation": operation_label,
                "english_time": english_metrics["time"],
                "chinese_time": chinese_metrics["time"],
                "time_delta": (
                    chinese_metrics["time"] / english_metrics["time"] - 1.0
                ) * 100.0,
                "english_allocation": english_metrics["allocation"],
                "chinese_allocation": chinese_metrics["allocation"],
                "allocation_delta": (
                    chinese_metrics["allocation"] / english_metrics["allocation"] - 1.0
                ) * 100.0,
            }


def render_section(title: str, path: Path) -> str:
    rows: List[str] = [
        f"## {title}",
        "",
        "| 载荷 | 操作 | 英文 us/op | 中文 us/op | 中文耗时变化 | 英文 B/op | 中文 B/op | 中文分配变化 |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in comparisons(load_results(path)):
        rows.append(
            "| {payload} | {operation} | {english_time:.3f} | {chinese_time:.3f} | "
            "{time_delta:+.2f}% | {english_allocation:,.0f} | "
            "{chinese_allocation:,.0f} | {allocation_delta:+.2f}% |".format(**item)
        )
    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="分析 JMH 中中文载荷相对英文载荷的差异")
    parser.add_argument(
        "--baseline",
        type=Path,
        default=ROOT / "results/task-2.1-baseline/jmh-result.json",
        help="基线 JMH JSON",
    )
    parser.add_argument(
        "--optimized",
        type=Path,
        default=ROOT / "results/task-2.3-final/jmh-result.json",
        help="优化后 JMH JSON",
    )
    args = parser.parse_args()
    print("# 中文序列化场景对照\n")
    print("正值表示中文载荷的指标更高。中英文样本的字符数和编码后字节数并不完全相同，")
    print("因此结果用于发现中文场景风险，不能单独归因于语言或字符编码。\n")
    print(render_section("基线实现", args.baseline))
    print()
    print(render_section("优化后实现", args.optimized))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
