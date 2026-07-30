from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ainative.core.engine import AINativeEngine
from ainative.core.governance import GovernancePolicy
from ainative.core.store import JsonStore
from ainative.domain.finance_analysis import FinanceAnalysisPack
from ainative.runtime.deterministic import DeterministicRuntime


ROOT = Path(__file__).resolve().parents[1]


class EngineFlowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.engine = AINativeEngine(
            store=JsonStore(Path(self.temp.name) / "state.json"),
            runtime=DeterministicRuntime(),
            domain=FinanceAnalysisPack(ROOT / "sample_data" / "monthly_metrics.json"),
            policy=GovernancePolicy(),
        )
        self.engine.seed()

    def tearDown(self):
        self.temp.cleanup()

    def test_seed_creates_responsibility_contract(self):
        data = self.engine.dashboard()
        self.assertEqual(1, len(data["spaces"]))
        self.assertEqual(1, len(data["colleagues"]))
        self.assertEqual(data["spaces"][0]["owner_id"], data["colleagues"][0]["id"])

    def test_monitoring_creates_only_material_anomaly_task(self):
        result = self.engine.run_monitoring()
        data = self.engine.dashboard()
        self.assertEqual("finance.metrics.updated", result["event"]["type"])
        self.assertEqual(1, len(data["tasks"]))
        self.assertEqual("waiting_approval", data["tasks"][0]["status"])
        self.assertEqual("华东区域利润偏差分析", data["artifacts"][0]["title"])
        self.assertEqual("require_approval", data["actions"][-1]["governance_decision"])

    def test_approval_completes_task_and_writes_evaluation(self):
        self.engine.run_monitoring()
        approval = self.engine.dashboard()["approvals"][0]
        task = self.engine.decide_approval(approval["id"], True, "测试负责人")
        data = self.engine.dashboard()
        self.assertEqual("completed", task["status"])
        self.assertEqual("published", data["artifacts"][0]["status"])
        self.assertEqual(1.0, data["evaluations"][0]["metrics"]["human_acceptance"])
        self.assertEqual(0.0, data["evaluations"][0]["metrics"]["unauthorized_action_count"])

    def test_source_data_modification_is_denied(self):
        from ainative.core.models import Action

        decision = self.engine.policy.decide(
            Action(
                task_id="task",
                actor_id="agent",
                type="modify_source_data",
                risk_level="high",
                reversible=False,
                evidence=[],
            )
        )
        self.assertEqual("deny", decision)


if __name__ == "__main__":
    unittest.main()

