from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass
from typing import Any

from .schema import PUBLISHED_TABLES
from .service import GenerationResult


WEIGHTS = {
    "anomaly_detection": 20,
    "numbers_and_metrics": 20,
    "root_cause": 25,
    "evidence": 20,
    "judgment_boundary": 10,
    "recommendations": 5,
}


@dataclass(frozen=True)
class MetricClaim:
    metric: str
    direction: str
    magnitude: float | None


@dataclass(frozen=True)
class EvidenceClaim:
    table: str
    field: str
    value: int | float | str


@dataclass(frozen=True)
class CauseClaim:
    cause: str
    confidence: float
    evidence: tuple[EvidenceClaim, ...]


@dataclass(frozen=True)
class AgentAnswer:
    anomalies: tuple[MetricClaim, ...]
    causes: tuple[CauseClaim, ...]
    unknowns: tuple[str, ...]
    recommendations: tuple[str, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "AgentAnswer":
        cls._require_keys(
            payload,
            {"anomalies", "causes", "unknowns", "recommendations"},
            "answer",
        )
        anomalies_payload = cls._require_list(payload["anomalies"], "anomalies")
        causes_payload = cls._require_list(payload["causes"], "causes")
        unknowns = cls._string_tuple(payload["unknowns"], "unknowns")
        recommendations = cls._string_tuple(
            payload["recommendations"], "recommendations"
        )

        anomalies = []
        for index, raw in enumerate(anomalies_payload):
            item = cls._require_dict(raw, f"anomalies[{index}]")
            allowed = {"metric", "direction", "magnitude"}
            if set(item) - allowed or not {"metric", "direction"} <= set(item):
                raise ValueError(f"Invalid keys in anomalies[{index}]")
            metric = cls._require_string(item["metric"], "metric")
            direction = cls._require_string(item["direction"], "direction")
            if direction not in {"up", "down", "stable"}:
                raise ValueError(f"Invalid direction: {direction}")
            magnitude = item.get("magnitude")
            if magnitude is not None:
                magnitude = cls._finite_number(magnitude, "magnitude")
            anomalies.append(MetricClaim(metric, direction, magnitude))

        causes = []
        for index, raw in enumerate(causes_payload):
            item = cls._require_dict(raw, f"causes[{index}]")
            cls._require_keys(
                item, {"cause", "confidence", "evidence"}, f"causes[{index}]"
            )
            cause = cls._require_string(item["cause"], "cause")
            confidence = cls._finite_number(item["confidence"], "confidence")
            if not 0 <= confidence <= 1:
                raise ValueError("confidence must be between 0 and 1")
            evidence_payload = cls._require_list(
                item["evidence"], f"causes[{index}].evidence"
            )
            evidence = []
            for evidence_index, raw_evidence in enumerate(evidence_payload):
                evidence_item = cls._require_dict(
                    raw_evidence,
                    f"causes[{index}].evidence[{evidence_index}]",
                )
                cls._require_keys(
                    evidence_item,
                    {"table", "field", "value"},
                    "evidence",
                )
                value = evidence_item["value"]
                if isinstance(value, bool) or not isinstance(
                    value, (int, float, str)
                ):
                    raise ValueError("evidence value must be scalar")
                if isinstance(value, float) and not math.isfinite(value):
                    raise ValueError("evidence value must be finite")
                evidence.append(
                    EvidenceClaim(
                        table=cls._require_string(
                            evidence_item["table"], "table"
                        ),
                        field=cls._require_string(
                            evidence_item["field"], "field"
                        ),
                        value=value,
                    )
                )
            causes.append(CauseClaim(cause, confidence, tuple(evidence)))

        return cls(
            anomalies=tuple(anomalies),
            causes=tuple(causes),
            unknowns=unknowns,
            recommendations=recommendations,
        )

    @staticmethod
    def _require_keys(
        payload: dict[str, Any], expected: set[str], label: str
    ) -> None:
        if set(payload) != expected:
            raise ValueError(f"Invalid keys in {label}")

    @staticmethod
    def _require_dict(value: object, label: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError(f"{label} must be an object")
        return value

    @staticmethod
    def _require_list(value: object, label: str) -> list[object]:
        if not isinstance(value, list):
            raise ValueError(f"{label} must be an array")
        return value

    @staticmethod
    def _require_string(value: object, label: str) -> str:
        if not isinstance(value, str) or not value:
            raise ValueError(f"{label} must be a non-empty string")
        return value

    @classmethod
    def _string_tuple(cls, value: object, label: str) -> tuple[str, ...]:
        return tuple(
            cls._require_string(item, label)
            for item in cls._require_list(value, label)
        )

    @staticmethod
    def _finite_number(value: object, label: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{label} must be numeric")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"{label} must be finite")
        return number


@dataclass(frozen=True)
class ScoreReport:
    total_score: float
    dimension_scores: tuple[tuple[str, float], ...]
    matched_causes: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    unsupported_claims: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "total_score": self.total_score,
            "dimension_scores": dict(self.dimension_scores),
            "matched_causes": list(self.matched_causes),
            "missing_evidence": list(self.missing_evidence),
            "unsupported_claims": list(self.unsupported_claims),
        }


class DeterministicScorer:
    def score_database(
        self, answer: AgentAnswer, result: GenerationResult
    ) -> ScoreReport:
        conn = sqlite3.connect(result.database_path)
        try:
            expected_metrics = self._expected_metrics(conn)
            anomaly_score, numbers_score = self._score_anomalies(
                answer, expected_metrics
            )
            (
                cause_score,
                evidence_score,
                matched_causes,
                missing_evidence,
                unsupported,
            ) = self._score_causes(answer, result, conn)
        finally:
            conn.close()

        expected_unknowns = set(result.ground_truth.unknowns)
        matched_unknowns = expected_unknowns.intersection(answer.unknowns)
        boundary_score = (
            WEIGHTS["judgment_boundary"]
            * len(matched_unknowns)
            / max(1, len(expected_unknowns))
        )
        forbidden = set(result.ground_truth.forbidden_claims)
        recommendation_conflict = any(
            token in recommendation
            for token in forbidden
            for recommendation in answer.recommendations
        )
        recommendation_score = (
            WEIGHTS["recommendations"]
            if answer.recommendations and not recommendation_conflict
            else 0
        )
        dimensions = {
            "anomaly_detection": anomaly_score,
            "numbers_and_metrics": numbers_score,
            "root_cause": cause_score,
            "evidence": evidence_score,
            "judgment_boundary": boundary_score,
            "recommendations": recommendation_score,
        }
        forbidden_assertions = forbidden.intersection(unsupported)
        total = sum(dimensions.values()) - 10 * len(forbidden_assertions)
        if forbidden_assertions:
            total = min(total, 59)
        total = max(0, min(100, total))
        return ScoreReport(
            total_score=round(total, 2),
            dimension_scores=tuple(
                (name, round(value, 2)) for name, value in dimensions.items()
            ),
            matched_causes=tuple(sorted(matched_causes)),
            missing_evidence=tuple(sorted(missing_evidence)),
            unsupported_claims=tuple(sorted(unsupported)),
        )

    @staticmethod
    def _expected_metrics(conn: sqlite3.Connection) -> dict[str, tuple[str, int]]:
        revenue = conn.execute(
            "select sum(revenue_cents) from fact_sales_invoice "
            "where period between '2025-10' and '2025-12'"
        ).fetchone()[0]
        cogs = conn.execute(
            "select sum(quantity * unit_cost_cents) from fact_sales_delivery "
            "where period between '2025-10' and '2025-12'"
        ).fetchone()[0]
        return {
            "revenue": ("up", revenue),
            "gross_profit": ("down", revenue - cogs),
        }

    @staticmethod
    def _score_anomalies(
        answer: AgentAnswer, expected: dict[str, tuple[str, int]]
    ) -> tuple[float, float]:
        anomaly_points = WEIGHTS["anomaly_detection"] / len(expected)
        number_points = WEIGHTS["numbers_and_metrics"] / len(expected)
        anomaly_score = 0.0
        numbers_score = 0.0
        for metric, (direction, expected_value) in expected.items():
            claims = [
                claim
                for claim in answer.anomalies
                if claim.metric == metric and claim.direction == direction
            ]
            if not claims:
                continue
            anomaly_score += anomaly_points
            if any(
                claim.magnitude is not None
                and abs(claim.magnitude - expected_value)
                <= max(1.0, abs(expected_value) * 0.01)
                for claim in claims
            ):
                numbers_score += number_points
        return anomaly_score, numbers_score

    def _score_causes(
        self,
        answer: AgentAnswer,
        result: GenerationResult,
        conn: sqlite3.Connection,
    ) -> tuple[
        float,
        float,
        set[str],
        set[str],
        set[str],
    ]:
        contributions = dict(result.ground_truth.contributions)
        expected_causes = set(result.ground_truth.root_causes)
        asserted = {claim.cause for claim in answer.causes}
        matched = asserted.intersection(expected_causes)
        unsupported = asserted - expected_causes
        cause_score = WEIGHTS["root_cause"] * sum(
            contributions[cause] for cause in matched
        )
        evidence_score = 0.0
        missing_evidence: set[str] = set()
        claims_by_cause = {claim.cause: claim for claim in answer.causes}
        for cause in matched:
            claim = claims_by_cause[cause]
            if claim.evidence and any(
                self._evidence_exists(conn, item) for item in claim.evidence
            ):
                evidence_score += (
                    WEIGHTS["evidence"] * contributions[cause]
                )
            else:
                missing_evidence.add(cause)
        return (
            cause_score,
            evidence_score,
            matched,
            missing_evidence,
            unsupported,
        )

    @staticmethod
    def _evidence_exists(
        conn: sqlite3.Connection, evidence: EvidenceClaim
    ) -> bool:
        if evidence.table not in PUBLISHED_TABLES:
            return False
        fields = {
            row[1]
            for row in conn.execute(
                f"pragma table_info({evidence.table})"
            )
        }
        if evidence.field not in fields:
            return False
        row = conn.execute(
            f"select 1 from {evidence.table} "
            f"where {evidence.field} = ? limit 1",
            (evidence.value,),
        ).fetchone()
        return row is not None
