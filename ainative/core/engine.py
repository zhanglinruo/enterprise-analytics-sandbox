from __future__ import annotations

from pathlib import Path
from typing import Any

from ainative.domain.finance_analysis import FinanceAnalysisPack
from ainative.runtime.base import AgentRuntime

from .governance import GovernancePolicy
from .models import (
    AIColleague,
    Action,
    Approval,
    ApprovalStatus,
    Artifact,
    Evaluation,
    Event,
    Evidence,
    ResponsibilitySpace,
    Task,
    TaskStatus,
    now_iso,
    serialize,
)
from .store import JsonStore


class AINativeEngine:
    def __init__(
        self,
        store: JsonStore,
        runtime: AgentRuntime,
        domain: FinanceAnalysisPack,
        policy: GovernancePolicy | None = None,
    ):
        self.store = store
        self.runtime = runtime
        self.domain = domain
        self.policy = policy or GovernancePolicy()

    def seed(self, reset: bool = False) -> None:
        self.store.initialize(reset=reset)
        if self.store.all("spaces"):
            return
        colleague = AIColleague(
            name="林析",
            role="AI 经营分析同事",
            objective="持续识别经营异常，形成可信分析，并推动业务原因确认",
            responsibility_space_ids=[],
            capabilities=["指标监测", "偏差分析", "归因分析", "报告生成"],
            success_metrics=["异常召回率", "归因确认率", "结论采纳率", "闭环时长"],
            autonomy_level=2,
        )
        space = ResponsibilitySpace(
            name="月度利润经营分析",
            objective="在数据更新后识别利润重大偏差并推动闭环",
            owner_id=colleague.id,
            indicators=["收入", "成本", "利润", "利润预算偏差"],
        )
        colleague.responsibility_space_ids = [space.id]
        self.store.add("spaces", serialize(space))
        self.store.add("colleagues", serialize(colleague))

    def run_monitoring(self) -> dict[str, Any]:
        self.store.clear_runtime()
        space = self.store.all("spaces")[0]
        colleague = self.store.all("colleagues")[0]
        event = Event(type="finance.metrics.updated", payload={"period": "2026-07"})
        self.store.add("events", serialize(event))
        anomalies = self.domain.detect_anomalies()
        created_tasks = [self._analyze(anomaly, space, colleague) for anomaly in anomalies]
        return {"event": serialize(event), "tasks": created_tasks}

    def _analyze(
        self,
        anomaly: dict[str, Any],
        space: dict[str, Any],
        colleague: dict[str, Any],
    ) -> dict[str, Any]:
        task = Task(
            goal=f"分析{anomaly['region']}本月利润预算偏差",
            responsibility_space_id=space["id"],
            owner_id=colleague["id"],
            source="ai_detected",
            success_criteria=["定位主要影响因素", "形成可核验数据证据", "列出待业务确认事项"],
            risk_level="low",
            status=TaskStatus.RUNNING,
        )
        self.store.add("tasks", serialize(task))

        read_action = Action(
            task_id=task.id,
            actor_id=colleague["id"],
            type="read_data",
            risk_level="low",
            reversible=True,
            evidence=[Evidence("数据期间", "2026-07", "经营分析宽表")],
        )
        self._record_action(read_action)

        result = self.runtime.execute_task(
            serialize(task),
            {
                "metrics": self.domain.load_metrics(),
                "target_region": anomaly["region"],
            },
        )
        evidence = [
            Evidence("预算利润", anomaly["budget_profit"], "经营分析宽表"),
            Evidence("实际利润", anomaly["actual_profit"], "经营分析宽表"),
            Evidence("预算偏差", anomaly["profit_variance_percent"], "确定性计算"),
        ]
        artifact = Artifact(
            task_id=task.id,
            type="variance_analysis",
            title=f"{anomaly['region']}利润偏差分析",
            content=result,
            evidence=evidence,
        )
        self.store.add("artifacts", serialize(artifact))

        publish_action = Action(
            task_id=task.id,
            actor_id=colleague["id"],
            type="publish_official_report",
            risk_level="high",
            reversible=False,
            evidence=evidence,
        )
        decision = self._record_action(publish_action)
        if decision == "require_approval":
            approval = Approval(
                action_id=publish_action.id,
                task_id=task.id,
                reason="正式经营分析结论可能影响管理判断，需业务负责人确认",
            )
            self.store.add("approvals", serialize(approval))
            self.store.update(
                "tasks",
                task.id,
                {"status": TaskStatus.WAITING_APPROVAL, "updated_at": now_iso()},
            )
        return self.store.get("tasks", task.id) or {}

    def _record_action(self, action: Action) -> str:
        decision = self.policy.decide(action)
        action.governance_decision = decision
        action.status = "executed" if decision in ("allow", "allow_and_notify") else "pending"
        self.store.add("actions", serialize(action))
        return str(decision)

    def decide_approval(self, approval_id: str, approved: bool, decided_by: str) -> dict[str, Any]:
        approval = self.store.get("approvals", approval_id)
        if not approval:
            raise KeyError(f"approval/{approval_id} not found")
        if approval["status"] != ApprovalStatus.PENDING:
            raise ValueError("Approval has already been decided")
        status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        self.store.update(
            "approvals",
            approval_id,
            {"status": status, "decided_by": decided_by, "decided_at": now_iso()},
        )
        action_status = "executed" if approved else "rejected"
        self.store.update("actions", approval["action_id"], {"status": action_status})
        task_status = TaskStatus.COMPLETED if approved else TaskStatus.FAILED
        task = self.store.update(
            "tasks",
            approval["task_id"],
            {"status": task_status, "updated_at": now_iso()},
        )
        artifact = next(
            item for item in self.store.all("artifacts") if item["task_id"] == approval["task_id"]
        )
        self.store.update(
            "artifacts",
            artifact["id"],
            {"status": "published" if approved else "rejected"},
        )
        evaluation = Evaluation(
            task_id=approval["task_id"],
            metrics={
                "analysis_confidence": float(artifact["content"]["confidence"]),
                "human_acceptance": 1.0 if approved else 0.0,
                "unauthorized_action_count": 0.0,
            },
            notes="正式结论已获人工确认" if approved else "结论被退回，需补充业务证据",
        )
        self.store.add("evaluations", serialize(evaluation))
        return task

    def dashboard(self) -> dict[str, Any]:
        data = self.store.snapshot()
        return {
            **data,
            "summary": {
                "active_spaces": len([x for x in data["spaces"] if x["status"] == "active"]),
                "open_tasks": len(
                    [x for x in data["tasks"] if x["status"] not in ("completed", "failed")]
                ),
                "pending_approvals": len(
                    [x for x in data["approvals"] if x["status"] == "pending"]
                ),
                "published_artifacts": len(
                    [x for x in data["artifacts"] if x["status"] == "published"]
                ),
            },
        }


def default_engine(base_dir: str | Path) -> AINativeEngine:
    from ainative.runtime.deterministic import DeterministicRuntime

    root = Path(base_dir)
    return AINativeEngine(
        store=JsonStore(root / "data" / "state.json"),
        runtime=DeterministicRuntime(),
        domain=FinanceAnalysisPack(root / "sample_data" / "monthly_metrics.json"),
    )

