# asmemory — Action-State Memory Engine

> Turn an agent's actions and states into typed time-series memory, then analyze **trends, anomalies, and causality**.

**Language:** English | [简体中文](README.zh.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![DSH Plugin](https://img.shields.io/badge/DeepSeek_Harness-plugin-blueviolet.svg)](#)
[![Zero dependencies](https://img.shields.io/badge/dependencies-zero-green.svg)](#)

A [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) MCP plugin that gives an agent a *time memory* — it records what happened and what changed, instead of just what was said.

## What it does

asmemory stores two kinds of typed events, not raw text:

- **State** — a value of some entity/metric at a point in time (`gpu.temperature = 78°C`)
- **Action** — something that happened (`agent ran training`, `operator adjusted a valve`)

On top of this memory it provides four analyses: **trend**, **anomaly**, **causal**, and **summary**.

## Why asmemory

Most memory plugins store conversations or documents, so they answer *"what did you say"*. asmemory stores *actions and states*, so it answers *"what happened, and why"*:

- "Did GPU temperature rise after training started?" → **causal**
- "Is my sleep trending down this week?" → **trend**
- "Which readings are outliers?" → **anomaly**

## Tools

Seven MCP tools, exposed to the model as `mcp__asmemory__<tool>`:

| Tool | What it does |
|---|---|
| `memory_store_state` | Record a state event (entity / metric / value / unit) |
| `memory_store_action` | Record an action event (actor / verb / object / amount) |
| `memory_trend` | Trend direction + slope of a metric |
| `memory_anomaly` | z-score outlier detection |
| `memory_causal` | Mean change of a metric before/after an action |
| `memory_summary` | Library statistics |
| `memory_export_datalens` | Export CSV + config for DataLens visualization |

## Installation

1. Clone this repository.
2. Launch DSH with the plugin patch:

   ```sh
   dsh web --patch "$PWD/cordis.yml"
   ```

3. Done. No `pip install`, no `npm install` — the server is a single stdio process using **only the Python 3.10+ standard library**.

Persistence defaults to `~/.asmemory/memory.db` (override with `ASMEMORY_DB_PATH`).

## Quick start

```sh
python3 examples/demo_agent_self_tracking.py   # agent self-tracking demo
python3 examples/demo_datalens_export.py       # industrial → DataLens export demo
```

## DataLens integration

asmemory exports any "monitored metric + control action + regulatory limit" into a CSV + config that [DataLens](https://github.com/Xplore-LAB/DataLens) opens directly for over-control optimization analysis — memory for the causality, DataLens for the visualization.

## Use cases

- **Agent self-tracking** — record the agent's own actions and resource states
- **Industrial monitoring** — process variables and operator actions (air separation, emission control)
- **Personal data** — sleep, weight, spending, exercise trends

## License

MIT
