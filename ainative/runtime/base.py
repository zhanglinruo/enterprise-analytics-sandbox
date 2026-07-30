from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AgentRuntime(ABC):
    """Boundary for LangGraph, AgentScope or another runtime."""

    @abstractmethod
    def execute_task(self, task: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def resume_task(self, checkpoint: dict[str, Any]) -> dict[str, Any]:
        return checkpoint

    def cancel_task(self, task_id: str) -> None:
        return None

