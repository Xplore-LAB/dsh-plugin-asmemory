"""Demo：空分场景「记忆 → DataLens 导出」全链路（通用导出器验证）。

场景：氧纯度（监控指标）+ 导叶开度（控制手段），模拟「过度控制」——
氧纯度已经很高（99.7~99.9），但导叶开度仍保持大（60~85%），
这正是 DataLens 要找的「安全区还在过量控制」的节能空间。

跑法：
    python examples/demo_datalens_export.py
输出 data_datalens.csv 与 data_datalens.config.json，双击 DataLens index.html 导入即可。
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from asmemory import StateEvent, ActionEvent, MemoryStore, analysis
from asmemory.export import export_datalens


def simulate_asu(store: MemoryStore, minutes: int = 240):
    """模拟空分装置 240 分钟运行：氧纯度 + 导叶开度（过量控制）。"""
    base = 1_723_500_000.0
    for m in range(minutes):
        ts = base + m * 60
        # 氧纯度：基础 99.7，双重正弦波动，每 60 分钟一次工况扰动
        purity = 99.7 + 0.15 * math.sin(m / 30) + 0.05 * math.sin(m / 7)
        if m % 60 == 0:
            purity -= 0.15
        purity = round(min(max(purity, 99.4), 99.95), 3)
        store.add_state(StateEvent("oxygen", "purity", purity, "%", ts))

        # 导叶开度：保守控制——即使纯度高也保持 60~85%（过量控制）
        valve = 70 + 8 * math.sin(m / 40) - (purity - 99.7) * 50
        valve = round(min(max(valve, 40), 85), 2)
        store.add_action(ActionEvent("operator", "valve_adjust", "air_compressor", amount=valve, ts=ts))


def main():
    store = MemoryStore(":memory:")
    simulate_asu(store, minutes=240)

    # 1) 记忆 + 因果分析
    s = analysis.summary(store)
    causal = analysis.causal_effect(store, "valve_adjust", "oxygen", "purity", window=600)
    print("=" * 60)
    print("空分场景：记忆 + 因果分析")
    print("=" * 60)
    print(f"【记忆】状态 {s['n_states']} 条 | 动作 {s['n_actions']} 条")
    print(f"【因果】valve_adjust → oxygen.purity: Δ={causal['delta']} ({causal['direction']})")

    # 2) 导出 DataLens
    result = export_datalens(
        store,
        indicator_entity="oxygen", indicator_metric="purity",
        control_verb="valve_adjust",
        regulatory_limit=99.5,
        indicator_name="氧纯度", indicator_unit="%",
        control_name="导叶开度", control_unit="%",
        site_name="空分装置", section="空分节能控制性能分析",
    )

    csv_path = Path("data_datalens.csv")
    cfg_path = Path("data_datalens.config.json")
    csv_path.write_text(result["csv"], encoding="utf-8")
    cfg_path.write_text(json.dumps(result["config"], ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 60)
    print("DataLens 导出结果")
    print("=" * 60)
    print(f"✅ CSV → {csv_path}")
    print(f"✅ config → {cfg_path}")
    print("\n【CSV 前 6 行】")
    for line in result["csv"].splitlines()[:6]:
        print("  " + line)
    print("\n【config 关键字段】")
    print(f"  pollutant={result['config']['pollutant']} ({result['config']['pollutantUnit']})")
    print(f"  regulator={result['config']['regulator']} ({result['config']['regulatorUnit']})")
    print(f"  regulatoryLimit={result['config']['regulatoryLimit']}")
    print("\n下一步：双击 DataLens index.html → 📊 导入 CSV → 📋 加载 config → 看节能空间")


if __name__ == "__main__":
    main()
