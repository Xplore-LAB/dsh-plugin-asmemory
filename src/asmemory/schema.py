"""Action-State Memory 核心 schema（脱敏版）。

两个时序原语：
- StateEvent  状态：某实体某时刻某个指标的数值
- ActionEvent 动作：某时刻发生的某个事件

刻意与 PKMemory 论文的 9 字段 MemoryUnit / 一致性筛选 / PKC 拓扑解耦，
只保留「typed event」这一通用理念。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict


def _now() -> float:
    return time.time()


@dataclass
class StateEvent:
    """状态事件：entity 在 metric 上的取值 value，带单位与标签。"""
    entity: str                 # 实体：gpu / cpu / memory / user / repo ...
    metric: str                 # 指标：temperature / usage / weight / price ...
    value: float                # 数值
    unit: str = ""              # 单位：celsius / % / GB / kg ...
    ts: float = field(default_factory=_now)   # unix 时间戳（秒）
    tags: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ActionEvent:
    """动作事件：actor 对 object 执行了 verb，可带控制量 amount 与元数据。"""
    actor: str                  # 谁：agent / user / system ...
    verb: str                   # 做了什么：run_training / git_commit ...
    object: str = ""            # 对什么做：qwen3.6 / repo ...
    amount: float = 0.0         # 控制量数值（喷氨量/功率/开度），非控制类动作填 0
    ts: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)
