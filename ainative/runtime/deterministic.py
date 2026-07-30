from __future__ import annotations

from typing import Any

from .base import AgentRuntime


class DeterministicRuntime(AgentRuntime):
    """Auditable demo runtime; keeps model uncertainty out of scaffold validation."""

    def execute_task(self, task: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        rows = context["metrics"]
        target = next(row for row in rows if row["region"] == context["target_region"])
        profit_variance = round(
            (target["actual_profit"] - target["budget_profit"]) / target["budget_profit"] * 100,
            1,
        )
        revenue_impact = round(target["actual_revenue"] - target["budget_revenue"], 1)
        cost_impact = round(target["budget_cost"] - target["actual_cost"], 1)
        main_driver = "收入未达预算" if abs(revenue_impact) >= abs(cost_impact) else "成本高于预算"
        return {
            "summary": f"{target['region']}利润较预算偏差 {profit_variance}%",
            "severity": "high" if profit_variance <= -10 else "medium",
            "confidence": 0.94,
            "main_driver": main_driver,
            "drivers": [
                {"name": "收入影响", "amount": revenue_impact, "unit": "万元"},
                {"name": "成本改善", "amount": cost_impact, "unit": "万元"},
            ],
            "questions": [
                "重点客户订单延迟是否为收入缺口的主要业务原因？",
                "促销调整是否影响了高毛利产品销售占比？",
            ],
            "recommendations": [
                "由区域财务确认前三大收入缺口客户及订单状态",
                "补充产品结构和客户结构拆解后再发布正式结论",
            ],
            "source_row": target,
        }

