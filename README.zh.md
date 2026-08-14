# asmemory — 动作-状态记忆引擎

> 给 agent 装上**时间记忆**：记录**发生了什么、什么变了**，做**趋势、异常、因果**分析——而不只是「说过什么」。

**语言:** [English](README.md) | 简体中文

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![DSH Plugin](https://img.shields.io/badge/DeepSeek_Harness-plugin-blueviolet.svg)](#)
[![Zero dependencies](https://img.shields.io/badge/dependencies-zero-green.svg)](#)
[![Verified on DSH](https://img.shields.io/badge/verified-DSH_headless-00b894.svg)](#verified)

> ⭐ 如果它对你有用，**点个 star** 是最好的感谢——让更多人看到它。

---

## 它做什么

asmemory 存两类 **typed 事件**，而非裸文本：

- **状态 State** — 某实体某指标在某个时刻的值（`gpu.temperature = 78°C`）
- **动作 Action** — 某时刻发生的某事（`agent 启动训练`、`操作工调了阀门`）

在此之上提供四类分析：

| 分析 | 回答的问题 |
|---|---|
| **趋势 Trend** | 这个指标在升还是降？（斜率 + 方向） |
| **异常 Anomaly** | 哪些读数是离群点？（z-score） |
| **因果 Causal** | 动作 X 是否推动了指标 Y？（前后差值） |
| **统计 Summary** | 记忆库里有什么？（计数 + 实体） |

## 为什么是 asmemory

多数记忆插件存对话或文档，只能回答「你说过什么」。asmemory 存**动作与状态**，能回答「**发生了什么、为什么**」：

> 「训练启动后 GPU 温度升了吗？」→ **因果**
> 「这周睡眠在下降吗？」→ **趋势**
> 「哪些读数是离群点？」→ **异常**

它是**物理与运营世界**的记忆层——agent 观测自己、工业过程、个人指标。

## 范例：agent 自我观测

记录 agent 自己的动作与资源状态，然后追问「GPU 为什么变热」：

```python
from asmemory import StateEvent, ActionEvent, MemoryStore, analysis

store = MemoryStore("memory.db")
store.add_state(StateEvent("gpu", "temperature", 78.5, "celsius"))
store.add_action(ActionEvent("agent", "run_training", "qwen3.6", ts=1723500000))

# 训练真的让 GPU 变热了吗？
causal = analysis.causal_effect(store, "run_training", "gpu", "temperature")
print(causal["before_mean"], "->", causal["after_mean"], f"(Δ={causal['delta']})")
```

**真实输出**（24h 模拟 agent，72 条状态 + 20 条动作）：

```
【因果】run_training → gpu.temperature:  45.3 → 78.7  (Δ=33.4, up)   ← 显著
【因果对照】git_commit → gpu.temperature: 53.7 → 56.4  (Δ=2.7, up)    ← 无效应
【异常】ram.usage: 1 个离群点 (z=-2.4)
```

引擎干净地分开**真因果**（训练）与**巧合**（git 提交）——不靠 LLM 猜，纯时序数学。

## 范例：工业监控 → DataLens

空分装置：氧纯度（监控指标）vs 导叶开度（控制动作）。asmemory 记因果，导出给 [DataLens](https://github.com/Xplore-LAB/DataLens) 找「过量控制」优化空间：

```python
from asmemory.export import export_datalens

export_datalens(store, entity="oxygen", metric="purity",
                action_verb="valve_adjust",
                pollutant="氧纯度", regulator="导叶开度",
                regulatory_limit=99.5)
# → data_datalens.csv + data_datalens.config.json
```

**真实输出**（240 分钟，240 条状态 + 240 条动作）：

```
【因果】valve_adjust → oxygen.purity: Δ=0.0009 (up)
✅ CSV → data_datalens.csv          (时间,指标值,控制量,整点标记)
✅ config → data_datalens.config.json (pollutant/regulator/limit)
```

把 `data_datalens.csv` 导入 DataLens，即可可视化「安全区还在过量控制」的节能空间。

## 工具

7 个 MCP 工具，对模型暴露为 `mcp__asmemory__<tool>`：

| 工具 | 作用 |
|---|---|
| `memory_store_state` | 存状态事件（实体/指标/值/单位/标签） |
| `memory_store_action` | 存动作事件（主体/动作/对象/控制量） |
| `memory_trend` | 指标趋势方向 + 斜率 |
| `memory_anomaly` | z-score 离群点检测 |
| `memory_causal` | 动作前后指标均值变化 |
| `memory_summary` | 记忆库统计 |
| `memory_export_datalens` | 导出 CSV + config 供 DataLens 可视化 |

## 安装

server 通过 `asmemory-mcp` 命令运行（也可用 `ASMEMORY_MCP_PATH` 指向脚本绝对路径）。先安装命令，再把 MCP 桥接注册到 DSH。

1. 安装 `asmemory-mcp` 命令：

   ```sh
   pip install .
   ```

   （或者跳过安装，直接设 `ASMEMORY_MCP_PATH=/path/to/bin/asmemory-mcp`。）

2. 带插件 patch 启动 DSH：

   ```sh
   dsh web --patch "$PWD/cordis.yml"
   ```

   （包发布后，也可用 `dsh plugin add dsh-plugin-asmemory` 安装。）

3. 完成。server 是单个 stdio 进程，只用 Python 3.10+ 标准库。

持久化默认 `~/.asmemory/memory.db`（可用 `ASMEMORY_DB_PATH` 覆盖）。

<a id="verified"></a>
## 已验证

全链路在真实 DSH 实例上端到端跑通（headless profile + 本地 Qwen3.6）：agent 实际调用了 `memory_store_state`、`memory_store_action`、`memory_summary`，事件正确落入 SQLite——正是它被要求记录的数据。

## 快速上手

```sh
python3 examples/demo_agent_self_tracking.py   # agent 自我观测 demo
python3 examples/demo_datalens_export.py       # 工业 → DataLens 导出 demo
```

## 使用场景

- **agent 自我观测** — 记录 agent 自身的动作与资源状态
- **工业监控** — 过程变量与操作工动作（空分、排放控制）
- **个人数据** — 睡眠、体重、花销、运动趋势

## License

MIT — 随便用、随便改、随便发。如果它顺便帮你收获一颗 star 形状的回报，那就更好了。⭐
