from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


class TaskStatus(StrEnum):
    OPEN = "open"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class GovernanceDecision(StrEnum):
    ALLOW = "allow"
    ALLOW_AND_NOTIFY = "allow_and_notify"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


@dataclass
class ResponsibilitySpace:
    name: str
    objective: str
    owner_id: str
    indicators: list[str]
    id: str = field(default_factory=lambda: new_id("space"))
    status: str = "active"
    created_at: str = field(default_factory=now_iso)


@dataclass
class AIColleague:
    name: str
    role: str
    objective: str
    responsibility_space_ids: list[str]
    capabilities: list[str]
    success_metrics: list[str]
    id: str = field(default_factory=lambda: new_id("colleague"))
    autonomy_level: int = 2
    status: str = "active"
    created_at: str = field(default_factory=now_iso)


@dataclass
class Task:
    goal: str
    responsibility_space_id: str
    owner_id: str
    source: str
    success_criteria: list[str]
    id: str = field(default_factory=lambda: new_id("task"))
    risk_level: str = "low"
    status: TaskStatus = TaskStatus.OPEN
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)


@dataclass
class Evidence:
    label: str
    value: Any
    source: str


@dataclass
class Action:
    task_id: str
    actor_id: str
    type: str
    risk_level: str
    reversible: bool
    evidence: list[Evidence]
    id: str = field(default_factory=lambda: new_id("action"))
    governance_decision: GovernanceDecision | None = None
    status: str = "proposed"
    created_at: str = field(default_factory=now_iso)


@dataclass
class Artifact:
    task_id: str
    type: str
    title: str
    content: dict[str, Any]
    evidence: list[Evidence]
    id: str = field(default_factory=lambda: new_id("artifact"))
    version: int = 1
    status: str = "draft"
    created_at: str = field(default_factory=now_iso)


@dataclass
class Approval:
    action_id: str
    task_id: str
    reason: str
    id: str = field(default_factory=lambda: new_id("approval"))
    status: ApprovalStatus = ApprovalStatus.PENDING
    decided_by: str | None = None
    created_at: str = field(default_factory=now_iso)
    decided_at: str | None = None


@dataclass
class Evaluation:
    task_id: str
    metrics: dict[str, float]
    notes: str
    id: str = field(default_factory=lambda: new_id("evaluation"))
    created_at: str = field(default_factory=now_iso)


@dataclass
class Event:
    type: str
    payload: dict[str, Any]
    id: str = field(default_factory=lambda: new_id("event"))
    created_at: str = field(default_factory=now_iso)


def serialize(value: Any) -> dict[str, Any]:
    return asdict(value)

