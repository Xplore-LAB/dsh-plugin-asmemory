"""分析层：趋势 / 异常 / 因果关联 / 统计摘要。

纯标准库（statistics），零 numpy 依赖，保证 demo 可复现。
因果关联用「动作发生前后状态变化对比」，是 PKC 的脱敏通用版：
只回答「动作 X 发生后，状态 Y 平均怎么变」，不涉及论文的 9 字段 / 拓扑。
"""
from __future__ import annotations

from statistics import mean, stdev
from typing import List, Optional

from .store import MemoryStore


def _split(values, timestamps):
    return [v for v in values], [t for t in timestamps]


def trend(values: List[float], timestamps: List[float]) -> dict:
    """线性回归斜率 + 方向判断。"""
    n = len(values)
    if n < 2:
        return {"direction": "flat", "slope": 0.0, "n": n}
    xs, ys = timestamps, values
    xm, ym = mean(xs), mean(ys)
    sxx = sum((x - xm) ** 2 for x in xs)
    if sxx == 0:
        return {"direction": "flat", "slope": 0.0, "n": n}
    slope = sum((x - xm) * (y - ym) for x, y in zip(xs, ys)) / sxx
    # 方向阈值：斜率相对均值量级
    if abs(ym) > 1e-9:
        rel = slope / abs(ym)
    else:
        rel = slope
    if rel > 0.01:
        direction = "rising"
    elif rel < -0.01:
        direction = "falling"
    else:
        direction = "flat"
    return {"direction": direction, "slope": round(slope, 6), "n": n}


def detect_anomalies(values: List[float], timestamps: List[float],
                     threshold: float = 2.0) -> List[dict]:
    """z-score 异常点检测（|z| > threshold）。"""
    n = len(values)
    if n < 3:
        return []
    mu, sd = mean(values), stdev(values)
    if sd == 0:
        return []
    out = []
    for t, v in zip(timestamps, values):
        z = (v - mu) / sd
        if abs(z) > threshold:
            out.append({"ts": t, "value": v, "z": round(z, 2)})
    return out


def causal_effect(store: MemoryStore, verb: str, entity: str, metric: str,
                  window: float = 3600.0) -> dict:
    """动作→状态 因果关联（脱敏版）。

    对比「该动作发生后 window 秒内」该状态指标的均值，
    与「动作发生前 window 秒内」的均值，给出平均变化量。
    """
    actions = store.query_actions(verb=verb)
    if not actions:
        return {"verb": verb, "metric": metric, "n_actions": 0,
                "delta": None, "direction": "unknown"}

    before_vals, after_vals = [], []
    for a in actions:
        t = a["ts"]
        # 动作前 window 内最近一个状态值（作为基线），严格排除动作时刻本身
        pre = store.query_states(entity, metric, start=t - window, end=t, end_exclusive=True)
        # 动作后 window 内所有状态值（含动作时刻起的第一个采样）
        post = store.query_states(entity, metric, start=t, end=t + window)
        if pre:
            before_vals.append(pre[-1]["value"])
        if post:
            after_vals.extend([p["value"] for p in post])

    if not before_vals or not after_vals:
        return {"verb": verb, "metric": metric, "n_actions": len(actions),
                "delta": None, "direction": "insufficient_data"}

    mb, ma = mean(before_vals), mean(after_vals)
    delta = ma - mb
    direction = "up" if delta > 0 else ("down" if delta < 0 else "flat")
    return {
        "verb": verb, "metric": metric, "n_actions": len(actions),
        "delta": round(delta, 4),
        "before_mean": round(mb, 4),
        "after_mean": round(ma, 4),
        "direction": direction,
    }


def summary(store: MemoryStore) -> dict:
    """库级统计摘要。"""
    return {
        "n_states": store.count_states(),
        "n_actions": store.count_actions(),
        "entities": store.list_entities(),
        "verbs": store.list_verbs(),
    }
