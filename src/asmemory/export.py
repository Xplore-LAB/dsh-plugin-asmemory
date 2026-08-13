"""DataLens 导出器（通用）：动作-状态记忆 → DataLens CSV + config.json。

把「指标状态 State + 控制动作 Action」映射成 DataLens 的 4 列 CSV
（时间 / 指标值 / 控制量 / 整点标记）+ 场景 config.json，双击 index.html 导入即分析。

完全场景无关：任意「监控指标 + 控制手段 + 红线」都能导出。
"""
from __future__ import annotations

import csv
import datetime
import io
from typing import Optional

from .store import MemoryStore


def _fmt_ts(ts: float) -> str:
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def export_datalens(
    store: MemoryStore,
    indicator_entity: str,        # 指标实体，如 "oxygen" / "flue_gas"
    indicator_metric: str,        # 指标名，如 "purity" / "nox"
    control_verb: str,            # 控制动作 verb，如 "valve_adjust" / "ammonia_spray"
    regulatory_limit: float,      # 法规红线（硬天花板）
    *,
    indicator_name: Optional[str] = None,   # 显示名（中文），默认用 metric
    indicator_unit: str = "",
    control_name: Optional[str] = None,     # 控制显示名，默认用 verb
    control_unit: str = "",
    amount_field: str = "amount",           # Action 里控制量字段
    site_name: str = "",
    section: str = "",
    hour_window: float = 3600.0,            # 整点标记窗口（秒）
) -> dict:
    """返回 {"csv": str, "config": dict}。"""
    states = store.query_states(indicator_entity, indicator_metric)
    if not states:
        raise ValueError(f"指标状态为空：{indicator_entity}.{indicator_metric}")

    actions = sorted(store.query_actions(verb=control_verb), key=lambda a: a["ts"])

    # 时间对齐：以指标采样点为时间轴，控制量 = 该时刻之前最近一次动作的 amount
    rows = []
    last_hour = None
    ai = 0
    for s in states:
        t = s["ts"]
        amount = 0.0
        while ai < len(actions) and actions[ai]["ts"] <= t:
            amount = actions[ai].get(amount_field, 0.0) or 0.0
            ai += 1
        hour = int(t // hour_window)
        mark = 1 if hour != last_hour else 0
        last_hour = hour
        rows.append([_fmt_ts(t), round(s["value"], 4), round(amount, 4), mark])

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["时间", "指标值", "控制量", "整点标记"])
    w.writerows(rows)
    csv_text = buf.getvalue()

    iname = indicator_name or indicator_metric
    cname = control_name or control_verb

    config = {
        "siteName": site_name or indicator_entity,
        "section": section or f"{iname} 控制性能分析",
        "pollutant": iname,
        "pollutantUnit": indicator_unit,
        "regulator": cname,
        "regulatorShort": cname,
        "regulatorUnit": control_unit,
        "regulatoryLimit": regulatory_limit,
        "sliders": {
            "trigger": {
                "label": f"{iname} 触发线", "val": round(regulatory_limit * 0.8, 2),
                "min": round(regulatory_limit * 0.7, 2), "max": regulatory_limit,
                "unit": indicator_unit,
            },
            "spray": {"label": "控制识别阈值", "val": 2, "min": 0.5, "max": 20},
            "discount": {"label": "节约折扣系数", "val": 15, "min": 5, "max": 30, "unit": "%"},
        },
    }
    return {"csv": csv_text, "config": config}
