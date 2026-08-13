"""asmemory — Action-State Memory Engine（脱敏版）。

把 agent / 人 / 系统的「动作」与「状态」自动沉淀为 typed 时序记忆，
提供趋势 / 异常 / 因果关联 / 统计摘要四类分析能力。
"""
from .schema import StateEvent, ActionEvent
from .store import MemoryStore
from . import analysis

__all__ = ["StateEvent", "ActionEvent", "MemoryStore", "analysis"]
__version__ = "0.1.0"
