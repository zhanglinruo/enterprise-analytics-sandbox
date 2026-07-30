from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class FinanceAnalysisPack:
    name = "finance-analysis-pack"

    def __init__(self, data_path: str | Path):
        self.data_path = Path(data_path)

    def load_metrics(self) -> list[dict[str, Any]]:
        return json.loads(self.data_path.read_text(encoding="utf-8"))["metrics"]

    def detect_anomalies(self, threshold_percent: float = -10.0) -> list[dict[str, Any]]:
        anomalies = []
        for row in self.load_metrics():
            variance = (row["actual_profit"] - row["budget_profit"]) / row["budget_profit"] * 100
            if variance <= threshold_percent:
                anomalies.append({**row, "profit_variance_percent": round(variance, 1)})
        return anomalies

