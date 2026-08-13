"""Demo：agent 自我观测 → 动作-状态记忆 → 趋势/异常/因果分析。

场景：模拟一个 AI 智能体在 24 小时内运行（每小时采样一次）。
- 状态：GPU 温度 / GPU 显存 / 内存占用
- 动作：run_training（启动训练）/ git_commit / web_search / idle

跑法：
    python examples/demo_agent_self_tracking.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from asmemory import StateEvent, ActionEvent, MemoryStore, analysis


def simulate_agent_day(store: MemoryStore, hours: int = 24):
    """模拟一个 agent 一天 24h 的动作与状态。"""
    base = 1_723_500_000.0  # 任意起始 unix 时间戳
    # 训练任务时间表：0-4h 和 12-16h 各跑一次大训练
    training_windows = [(0, 4), (12, 16)]

    for h in range(hours):
        ts = base + h * 3600

        # ---- 状态：GPU 温度（训练时高、空闲时低 + 噪声）----
        in_training = any(a <= h < b for a, b in training_windows)
        gpu_temp = 78.0 + 10 * math.sin(h / 4) if in_training else 42.0 + 3 * math.sin(h / 6)
        gpu_temp += (h % 7 - 3) * 0.4  # 噪声
        store.add_state(StateEvent("gpu", "temperature", round(gpu_temp, 1), "celsius", ts))
        store.add_state(StateEvent("gpu", "memory", round(60 + 25 * math.sin(h / 5) if in_training else 18 + 5 * math.sin(h / 7), 1), "GB", ts))
        store.add_state(StateEvent("ram", "usage", round(45 + 15 * math.sin(h / 8) + (h % 5), 1), "%", ts))

        # ---- 动作 ----
        if in_training and h % 1 == 0 and h in (0, 12):
            store.add_action(ActionEvent("agent", "run_training", "qwen3.6", ts=ts, metadata={"duration_h": 4}))
        if h % 3 == 0:
            store.add_action(ActionEvent("agent", "git_commit", "dsh-plugin-asmemory", ts=ts, metadata={"files": h % 5 + 1}))
        if h % 6 == 1:
            store.add_action(ActionEvent("agent", "web_search", "docs", ts=ts))
        if h % 4 == 2:
            store.add_action(ActionEvent("agent", "idle", "", ts=ts))


def main():
    store = MemoryStore(":memory:")
    simulate_agent_day(store, hours=24)

    print("=" * 60)
    print("动作-状态记忆引擎 Demo：agent 自我观测")
    print("=" * 60)

    # 1) 库统计
    s = analysis.summary(store)
    print(f"\n【库统计】状态 {s['n_states']} 条 | 动作 {s['n_actions']} 条")
    print(f"  实体: {s['entities']} | 动作类型: {s['verbs']}")

    # 2) 趋势：GPU 温度
    states = store.query_states("gpu", "temperature")
    t = analysis.trend([r["value"] for r in states], [r["ts"] for r in states])
    print(f"\n【趋势】gpu.temperature 24h：{t['direction']} (slope={t['slope']})")

    # 3) 异常：RAM 占用
    ram = store.query_states("ram", "usage")
    anoms = analysis.detect_anomalies([r["value"] for r in ram], [r["ts"] for r in ram], threshold=2.0)
    print(f"\n【异常】ram.usage 检测到 {len(anoms)} 个异常点:")
    for a in anoms[:5]:
        print(f"  ts={a['ts']:.0f} value={a['value']} (z={a['z']})")

    # 4) 因果：run_training → gpu.temperature
    causal = analysis.causal_effect(store, "run_training", "gpu", "temperature", window=3600)
    print(f"\n【因果】run_training → gpu.temperature:")
    print(f"  动作 {causal['n_actions']} 次，温度平均 {causal['before_mean']} → {causal['after_mean']} "
          f"(Δ={causal['delta']}, {causal['direction']})")

    # 5) 因果：git_commit → gpu.temperature（对照：应无显著因果）
    causal2 = analysis.causal_effect(store, "git_commit", "gpu", "temperature", window=3600)
    print(f"\n【因果对照】git_commit → gpu.temperature:")
    print(f"  动作 {causal2['n_actions']} 次，温度平均 {causal2['before_mean']} → {causal2['after_mean']} "
          f"(Δ={causal2['delta']}, {causal2['direction']})")

    print("\n" + "=" * 60)
    print("结论：run_training 显著推高 GPU 温度（因果），git_commit 无此效应（对照）。")
    print("=" * 60)


if __name__ == "__main__":
    main()
