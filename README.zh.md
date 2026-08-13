# asmemory — 动作-状态记忆引擎

> 把 agent 的动作与状态沉淀为 typed 时序记忆，做**趋势、异常、因果**分析。

**语言:** [English](README.md) | 简体中文

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![DSH Plugin](https://img.shields.io/badge/DeepSeek_Harness-plugin-blueviolet.svg)](#)
[![Zero dependencies](https://img.shields.io/badge/dependencies-zero-green.svg)](#)

一个 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) MCP 插件，给 agent 装上「时间记忆」——记住**发生了什么、什么变了**，而不只是「说过什么」。

## 它做什么

asmemory 存两类 typed 事件，而非裸文本：

- **状态 State** — 某实体某指标在某个时刻的值（`gpu.temperature = 78°C`）
- **动作 Action** — 某时刻发生的某事（`agent 启动了训练`、`操作工调了阀门`）

在此之上提供四类分析：**趋势 / 异常 / 因果 / 统计摘要**。

## 为什么是 asmemory

多数记忆插件存对话或文档，只能回答「你说过什么」。asmemory 存**动作与状态**，能回答「**发生了什么、为什么**」：

- 「训练启动后 GPU 温度升了吗？」→ **因果**
- 「这周睡眠在下降吗？」→ **趋势**
- 「哪些读数是离群点？」→ **异常**

## 工具

7 个 MCP 工具，对模型暴露为 `mcp__asmemory__<tool>`：

| 工具 | 作用 |
|---|---|
| `memory_store_state` | 存状态事件（实体/指标/值/单位） |
| `memory_store_action` | 存动作事件（主体/动作/对象/控制量） |
| `memory_trend` | 指标趋势方向 + 斜率 |
| `memory_anomaly` | z-score 离群点检测 |
| `memory_causal` | 动作前后指标均值变化 |
| `memory_summary` | 记忆库统计 |
| `memory_export_datalens` | 导出 CSV + config 供 DataLens 可视化 |

## 安装

1. Clone 本仓库。
2. 带插件 patch 启动 DSH：

   ```sh
   dsh web --patch "$PWD/cordis.yml"
   ```

3. 完成。**无需 `pip install`、无需 `npm install`**——server 是单个 stdio 进程，只用 Python 3.10+ 标准库。

持久化默认 `~/.asmemory/memory.db`（可用 `ASMEMORY_DB_PATH` 覆盖）。

## 快速上手

```sh
python3 examples/demo_agent_self_tracking.py   # agent 自我观测 demo
python3 examples/demo_datalens_export.py       # 工业 → DataLens 导出 demo
```

## DataLens 集成

asmemory 把任意「监控指标 + 控制手段 + 法规红线」导出为 CSV + config，[DataLens](https://github.com/Xplore-LAB/DataLens) 直接打开即可做「过量控制」优化分析——asmemory 负责记忆与因果，DataLens 负责可视化。

## 使用场景

- **agent 自我观测** — 记录 agent 自身的动作与资源状态
- **工业监控** — 过程变量与操作工动作（空分、排放控制）
- **个人数据** — 睡眠、体重、花销、运动趋势

## License

MIT
