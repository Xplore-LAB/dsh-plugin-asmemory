"""SQLite 存储层：动作与状态的 typed event 落库 + 索引。

零重依赖，纯标准库 sqlite3。时序数据量在个人观测规模下足够，
且完全脱敏（不暴露 PKMemory 的 Neo4j 图结构）。
"""
from __future__ import annotations

import json
import sqlite3
from typing import List, Optional

from .schema import StateEvent, ActionEvent


class MemoryStore:
    def __init__(self, path: str = ":memory:"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity TEXT NOT NULL,
                metric TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT DEFAULT '',
                ts REAL NOT NULL,
                tags TEXT DEFAULT '{}'
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor TEXT NOT NULL,
                verb TEXT NOT NULL,
                object TEXT DEFAULT '',
                amount REAL DEFAULT 0,
                ts REAL NOT NULL,
                metadata TEXT DEFAULT '{}'
            )
        """)
        # 时间 + 实体 + 指标 三路索引（对应「混合检索」的时间/实体维度）
        cur.execute("CREATE INDEX IF NOT EXISTS idx_states_em ON states(entity, metric, ts)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_states_ts ON states(ts)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_actions_av ON actions(actor, verb, ts)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_actions_ts ON actions(ts)")
        self.conn.commit()

    # ---- 写入 ----
    def add_state(self, e: StateEvent) -> int:
        cur = self.conn.execute(
            "INSERT INTO states(entity, metric, value, unit, ts, tags) VALUES (?,?,?,?,?,?)",
            (e.entity, e.metric, e.value, e.unit, e.ts, json.dumps(e.tags, ensure_ascii=False)),
        )
        self.conn.commit()
        return cur.lastrowid

    def add_action(self, e: ActionEvent) -> int:
        cur = self.conn.execute(
            "INSERT INTO actions(actor, verb, object, amount, ts, metadata) VALUES (?,?,?,?,?,?)",
            (e.actor, e.verb, e.object, e.amount, e.ts, json.dumps(e.metadata, ensure_ascii=False)),
        )
        self.conn.commit()
        return cur.lastrowid

    # ---- 查询 ----
    def query_states(self, entity: str, metric: str,
                     start: Optional[float] = None, end: Optional[float] = None,
                     end_exclusive: bool = False) -> List[dict]:
        sql = "SELECT * FROM states WHERE entity=? AND metric=?"
        args: list = [entity, metric]
        if start is not None:
            sql += " AND ts>=?"; args.append(start)
        if end is not None:
            sql += (" AND ts<?" if end_exclusive else " AND ts<=?"); args.append(end)
        sql += " ORDER BY ts"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def query_actions(self, verb: Optional[str] = None, actor: Optional[str] = None,
                      start: Optional[float] = None, end: Optional[float] = None) -> List[dict]:
        sql = "SELECT * FROM actions WHERE 1=1"
        args: list = []
        if verb is not None:
            sql += " AND verb=?"; args.append(verb)
        if actor is not None:
            sql += " AND actor=?"; args.append(actor)
        if start is not None:
            sql += " AND ts>=?"; args.append(start)
        if end is not None:
            sql += " AND ts<=?"; args.append(end)
        sql += " ORDER BY ts"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def list_entities(self) -> List[str]:
        return [r[0] for r in self.conn.execute("SELECT DISTINCT entity FROM states")]

    def list_metrics(self, entity: str) -> List[str]:
        return [r[0] for r in self.conn.execute(
            "SELECT DISTINCT metric FROM states WHERE entity=?", (entity,))]

    def list_verbs(self) -> List[str]:
        return [r[0] for r in self.conn.execute("SELECT DISTINCT verb FROM actions")]

    def count_states(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM states").fetchone()[0]

    def count_actions(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM actions").fetchone()[0]

    def close(self) -> None:
        self.conn.close()
