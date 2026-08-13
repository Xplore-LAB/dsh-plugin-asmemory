"""asmemory MCP server（零依赖，标准库手写 MCP stdio 协议）。

通过 stdio 暴露 asmemory 的工具给 DSH（或任何 MCP client）。
只实现 MCP 核心三件套：initialize / tools/list / tools/call，
满足 DSH mcp-client 的发现与调用需求，无需任何第三方库。
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time

from .analysis import trend, detect_anomalies, causal_effect, summary
from .export import export_datalens
from .schema import StateEvent, ActionEvent
from .store import MemoryStore

SERVER_NAME = "asmemory"
SERVER_VERSION = "0.1.0"

# ---- 全局持久化 store（懒加载，SQLite 文件）----
_store: MemoryStore | None = None
_store_lock = threading.Lock()


def _default_db_path() -> str:
    return os.path.join(os.path.expanduser("~"), ".asmemory", "memory.db")


def get_store() -> MemoryStore:
    global _store
    with _store_lock:
        if _store is None:
            path = os.environ.get("ASMEMORY_DB_PATH", _default_db_path())
            os.makedirs(os.path.dirname(path), exist_ok=True)
            _store = MemoryStore(path)
        return _store


# ---- 工具定义（name / description / inputSchema）----
TOOLS = [
    {
        "name": "memory_store_state",
        "description": "存一条状态事件到记忆库：某实体(entity)在某个指标(metric)上的数值(value)，可带单位与标签。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity": {"type": "string", "description": "实体名，如 gpu/cpu/user/repo"},
                "metric": {"type": "string", "description": "指标名，如 temperature/usage/purity"},
                "value": {"type": "number", "description": "数值"},
                "unit": {"type": "string", "description": "单位，可选"},
                "ts": {"type": "number", "description": "unix 时间戳秒，默认当前"},
                "tags": {"type": "object", "description": "标签，可选"},
            },
            "required": ["entity", "metric", "value"],
        },
    },
    {
        "name": "memory_store_action",
        "description": "存一条动作事件：actor 对 object 执行了 verb，可带控制量 amount 与元数据。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "actor": {"type": "string", "description": "谁做的，如 agent/user/operator"},
                "verb": {"type": "string", "description": "做了什么，如 run_training/git_commit/喷氨"},
                "object": {"type": "string", "description": "对象，可选"},
                "amount": {"type": "number", "description": "控制量数值（喷氨量/功率/开度），可选"},
                "ts": {"type": "number", "description": "unix 时间戳秒，默认当前"},
                "metadata": {"type": "object", "description": "元数据，可选"},
            },
            "required": ["actor", "verb"],
        },
    },
    {
        "name": "memory_trend",
        "description": "分析某指标的时间趋势（rising/falling/flat + 斜率）。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity": {"type": "string"},
                "metric": {"type": "string"},
            },
            "required": ["entity", "metric"],
        },
    },
    {
        "name": "memory_anomaly",
        "description": "检测某指标的异常点（z-score，|z|>threshold 视为异常）。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity": {"type": "string"},
                "metric": {"type": "string"},
                "threshold": {"type": "number", "description": "z-score 阈值，默认 2.0"},
            },
            "required": ["entity", "metric"],
        },
    },
    {
        "name": "memory_causal",
        "description": "因果关联：某动作(verb)对某指标(entity.metric)的影响，返回动作前后均值变化量。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "verb": {"type": "string"},
                "entity": {"type": "string"},
                "metric": {"type": "string"},
                "window": {"type": "number", "description": "时间窗秒，默认 3600"},
            },
            "required": ["verb", "entity", "metric"],
        },
    },
    {
        "name": "memory_summary",
        "description": "记忆库统计摘要：状态数/动作数/实体列表/动作类型列表。",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "memory_export_datalens",
        "description": "导出 DataLens 格式（监控指标+控制手段+红线）的 CSV 与 config，用于可视化优化分析。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "indicator_entity": {"type": "string", "description": "指标实体，如 oxygen"},
                "indicator_metric": {"type": "string", "description": "指标名，如 purity"},
                "control_verb": {"type": "string", "description": "控制动作 verb，如 valve_adjust"},
                "regulatory_limit": {"type": "number", "description": "法规红线"},
                "indicator_name": {"type": "string", "description": "指标显示名（中文），可选"},
                "indicator_unit": {"type": "string"},
                "control_name": {"type": "string"},
                "control_unit": {"type": "string"},
                "site_name": {"type": "string"},
                "section": {"type": "string"},
            },
            "required": ["indicator_entity", "indicator_metric", "control_verb", "regulatory_limit"],
        },
    },
]


def _now() -> float:
    return time.time()


def _call_tool(name: str, args: dict) -> dict:
    store = get_store()

    if name == "memory_store_state":
        ts = args.get("ts") or _now()
        e = StateEvent(args["entity"], args["metric"], args["value"],
                       args.get("unit", ""), ts, args.get("tags", {}))
        rid = store.add_state(e)
        return {"stored": True, "id": rid, "entity": e.entity, "metric": e.metric, "value": e.value}

    if name == "memory_store_action":
        ts = args.get("ts") or _now()
        e = ActionEvent(args["actor"], args["verb"], args.get("object", ""),
                        args.get("amount", 0.0), ts, args.get("metadata", {}))
        rid = store.add_action(e)
        return {"stored": True, "id": rid, "actor": e.actor, "verb": e.verb, "amount": e.amount}

    if name == "memory_trend":
        states = store.query_states(args["entity"], args["metric"])
        return trend([r["value"] for r in states], [r["ts"] for r in states])

    if name == "memory_anomaly":
        states = store.query_states(args["entity"], args["metric"])
        th = args.get("threshold", 2.0)
        anoms = detect_anomalies([r["value"] for r in states], [r["ts"] for r in states], th)
        return {"n": len(anoms), "anomalies": anoms}

    if name == "memory_causal":
        return causal_effect(store, args["verb"], args["entity"], args["metric"],
                             args.get("window", 3600.0))

    if name == "memory_summary":
        return summary(store)

    if name == "memory_export_datalens":
        return export_datalens(
            store,
            indicator_entity=args["indicator_entity"],
            indicator_metric=args["indicator_metric"],
            control_verb=args["control_verb"],
            regulatory_limit=args["regulatory_limit"],
            indicator_name=args.get("indicator_name"),
            indicator_unit=args.get("indicator_unit", ""),
            control_name=args.get("control_name"),
            control_unit=args.get("control_unit", ""),
            site_name=args.get("site_name", ""),
            section=args.get("section", ""),
        )

    raise ValueError(f"未知工具: {name}")


def _send(rid, result: dict) -> None:
    out = {"jsonrpc": "2.0", "id": rid, "result": result}
    sys.stdout.write(json.dumps(out, ensure_ascii=False, default=str) + "\n")
    sys.stdout.flush()


def _send_error(rid, code: int, message: str) -> None:
    out = {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}
    sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _handle_initialize(params: dict) -> dict:
    protocol = params.get("protocolVersion", "2024-11-05")
    return {
        "protocolVersion": protocol,
        "capabilities": {"tools": {}},
        "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
    }


def _handle_call(params: dict) -> dict:
    name = params.get("name", "")
    args = params.get("arguments") or {}
    try:
        result = _call_tool(name, args)
        return {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, default=str)}],
            "structuredContent": result,
            "isError": False,
        }
    except Exception as e:  # noqa: BLE001
        return {
            "content": [{"type": "text", "text": f"Error: {e}"}],
            "isError": True,
        }


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(req, dict) or "id" not in req:
            # 通知（如 notifications/initialized）——忽略
            continue
        method = req.get("method")
        rid = req.get("id")
        if method == "initialize":
            _send(rid, _handle_initialize(req.get("params", {})))
        elif method == "tools/list":
            _send(rid, {"tools": TOOLS})
        elif method == "tools/call":
            _send(rid, _handle_call(req.get("params", {})))
        else:
            _send_error(rid, -32601, f"Method not found: {method}")


if __name__ == "__main__":
    main()
