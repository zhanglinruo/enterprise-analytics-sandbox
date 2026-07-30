from __future__ import annotations

from dataclasses import dataclass

from .models import Action, GovernanceDecision


@dataclass(frozen=True)
class GovernancePolicy:
    """Opinionated defaults; replace with an enterprise policy engine later."""

    denied_actions: tuple[str, ...] = ("modify_source_data",)
    approval_actions: tuple[str, ...] = (
        "publish_official_report",
        "send_external_message",
        "modify_business_system",
    )

    def decide(self, action: Action) -> GovernanceDecision:
        if action.type in self.denied_actions:
            return GovernanceDecision.DENY
        if action.type in self.approval_actions or not action.reversible:
            return GovernanceDecision.REQUIRE_APPROVAL
        if action.risk_level == "medium":
            return GovernanceDecision.ALLOW_AND_NOTIFY
        return GovernanceDecision.ALLOW

